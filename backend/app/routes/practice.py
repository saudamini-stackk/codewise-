import json
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from ..models import (
    PracticeTest,
    SubmitPracticeAnswersRequest,
    PracticeEvaluationResult
)
from ..database import get_db, get_iso_now
from ..analyzer.practice_engine import PracticeEngine
from ..auth import optional_current_user

router = APIRouter(prefix="/api/practice", tags=["Practice Tests"])
practice_engine = PracticeEngine()

@router.post("/generate", response_model=PracticeTest)
def generate_practice_test(
    payload: Dict[str, Any] = Body(...),
    user: Optional[dict] = Depends(optional_current_user)
):
    code = payload.get("code") or ""
    language = payload.get("language") or "python"
    session_id = payload.get("session_id")

    if not code.strip():
        raise HTTPException(status_code=400, detail="Cannot generate practice test for empty code.")

    # Enforce session ownership if session_id is provided
    if session_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,))
            s_row = cursor.fetchone()
            if s_row and s_row["user_id"]:
                if not user or (user["id"] != s_row["user_id"] and s_row["user_id"] != "demo-user-0000-0000-000000000001"):
                    raise HTTPException(status_code=403, detail="Access denied to session.")

    test = practice_engine.generate_practice_test(code, language, session_id)
    now = get_iso_now()
    user_id = user["id"] if user else None

    # Persist practice test
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO practice_tests (id, user_id, session_id, code_hash, questions_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (test.id, user_id, session_id, test.code_hash, json.dumps([q.dict() for q in test.questions]), now)
        )

    return test

@router.post("/evaluate", response_model=PracticeEvaluationResult)
def evaluate_practice_test(
    req: SubmitPracticeAnswersRequest,
    user: Optional[dict] = Depends(optional_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM practice_tests WHERE id = ?", (req.test_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Practice test not found.")

        # Reconstruct PracticeTest
        raw_questions = json.loads(row["questions_json"])
        test = PracticeTest(
            id=row["id"],
            session_id=row["session_id"],
            code_hash=row["code_hash"],
            questions=raw_questions,
            created_at=row["created_at"]
        )

        eval_result = practice_engine.evaluate_test(test, req.answers)
        now = get_iso_now()
        user_id = user["id"] if user else row["user_id"]

        # Persist evaluation result
        cursor.execute(
            """INSERT INTO practice_evaluations (id, test_id, user_id, total_questions, correct_count, score_percentage, evaluations_json, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                eval_result.id,
                test.id,
                user_id,
                eval_result.total_questions,
                eval_result.correct_count,
                eval_result.score_percentage,
                json.dumps([e.dict() for e in eval_result.evaluations]),
                now
            )
        )

    return eval_result

@router.get("/history")
def get_practice_history(
    session_id: Optional[str] = Query(None),
    user: Optional[dict] = Depends(optional_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        sql = """
            SELECT e.id, e.test_id, e.user_id, e.total_questions, e.correct_count, e.score_percentage,
                   e.evaluations_json, e.completed_at, t.session_id, t.code_hash
            FROM practice_evaluations e
            JOIN practice_tests t ON e.test_id = t.id
            WHERE 1=1
        """
        params = []
        if session_id:
            sql += " AND t.session_id = ?"
            params.append(session_id)
        if user:
            sql += " AND (e.user_id = ? OR e.user_id IS NULL)"
            params.append(user["id"])

        sql += " ORDER BY e.completed_at DESC LIMIT 20"
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        history = []
        for r in rows:
            history.append({
                "id": r["id"],
                "test_id": r["test_id"],
                "session_id": r["session_id"],
                "total_questions": r["total_questions"],
                "correct_count": r["correct_count"],
                "score_percentage": r["score_percentage"],
                "evaluations": json.loads(r["evaluations_json"]),
                "completed_at": r["completed_at"]
            })
        return history
