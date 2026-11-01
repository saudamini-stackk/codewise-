import uuid
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from ..models import ChatRequest, MessageItem, AnalysisResult, RunCodeResponse
from ..database import get_db, get_iso_now
from ..analyzer.chat_engine import ChatEngine
from ..auth import optional_current_user
from .sessions import parse_analysis_row, verify_session_ownership

router = APIRouter(prefix="/api/sessions", tags=["Chat"])
chat_engine = ChatEngine()

@router.post("/{session_id}/chat", response_model=MessageItem)
async def chat_with_assistant(
    session_id: str,
    req: ChatRequest,
    user: Optional[dict] = Depends(optional_current_user)
):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Cannot send empty chat message.")

    now = get_iso_now()

    with get_db() as conn:
        cursor = conn.cursor()

        # Check session exists and verify ownership (IDOR defense)
        cursor.execute("SELECT id, user_id FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(session_row, user, "chat in")

        # Get relevant code version
        version_id = req.code_version_id
        if not version_id:
            cursor.execute(
                "SELECT id, code, language, execution_result_json FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1",
                (session_id,)
            )
            v_row = cursor.fetchone()
        else:
            cursor.execute(
                "SELECT id, code, language, execution_result_json FROM code_versions WHERE id = ? AND session_id = ?",
                (version_id, session_id)
            )
            v_row = cursor.fetchone()

        if not v_row:
            raise HTTPException(status_code=404, detail="No code version found for this session")

        version_id = v_row["id"]
        code = v_row["code"]
        language = v_row["language"]
        exec_json = v_row["execution_result_json"]
        runtime_res = None
        if exec_json:
            try:
                runtime_res = RunCodeResponse(**json.loads(exec_json))
            except Exception:
                runtime_res = None

        # Get analysis
        cursor.execute("SELECT * FROM analyses WHERE code_version_id = ? LIMIT 1", (version_id,))
        a_row = cursor.fetchone()
        analysis_obj = parse_analysis_row(dict(a_row)) if a_row else None

        # Get most recent 10 messages in chronological order
        cursor.execute(
            """SELECT role, content FROM (
                SELECT role, content, created_at FROM messages
                WHERE session_id = ?
                ORDER BY created_at DESC LIMIT 10
            ) ORDER BY created_at ASC""",
            (session_id,)
        )
        history = [dict(r) for r in cursor.fetchall()]

        # 1. Save user message
        user_msg_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO messages (id, session_id, code_version_id, role, content, mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_msg_id, session_id, version_id, "user", req.message.strip(), "local", now)
        )

    # 2. Get assistant response
    answer_res = await chat_engine.answer_question(
        question=req.message.strip(),
        code=code,
        language=language,
        analysis=analysis_obj,
        history=history,
        runtime_result=runtime_res
    )

    # 3. Save assistant message
    asst_msg_id = str(uuid.uuid4())
    asst_now = get_iso_now()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (id, session_id, code_version_id, role, content, mode, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (asst_msg_id, session_id, version_id, "assistant", answer_res["reply"], answer_res["mode"], asst_now)
        )
        # Update session timestamp
        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (asst_now, session_id))

    return MessageItem(
        id=asst_msg_id,
        session_id=session_id,
        code_version_id=version_id,
        role="assistant",
        content=answer_res["reply"],
        mode=answer_res["mode"],
        created_at=asst_now
    )
