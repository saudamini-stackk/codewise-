import uuid
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from ..models import (
    SessionSummary,
    SessionDetail,
    CodeVersionItem,
    AnalysisResult,
    ComplexityInfo,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    MessageItem,
    SessionCreateRequest,
    SessionUpdateRequest,
    SaveVersionRequest,
    RestoreVersionRequest,
    RunCodeResponse,
    ExpectedIO,
    VivaQuestionItem
)
from ..database import get_db, get_iso_now
from ..detector import detect_language, LANGUAGES_REGISTRY
from ..auth import optional_current_user, require_current_user

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

DEMO_USER_ID = "demo-user-0000-0000-000000000001"

def verify_session_ownership(session_row: Any, user: Optional[dict], action: str = "access") -> None:
    """Enforces strict session ownership to prevent IDOR attacks while allowing demo access."""
    if not session_row:
        return
    s_user = session_row["user_id"] if isinstance(session_row, dict) or hasattr(session_row, "__getitem__") else getattr(session_row, "user_id", None)
    if not s_user or s_user == DEMO_USER_ID:
        return
    if not user or user["id"] != s_user:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: You do not have permission to {action} this session."
        )

def is_runnable_format(language: Optional[str], filename: Optional[str] = None) -> bool:
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in [".json", ".xml", ".yaml", ".yml", ".toml", ".md", ".sql", ".html", ".htm", ".css", ".scss"]:
            return False
        if ext in [".py", ".js", ".ts", ".java", ".c", ".cpp", ".cc", ".cs", ".go", ".rs", ".php", ".rb", ".kt", ".swift", ".sh"]:
            return True
    if language:
        lang = language.lower()
        if lang in ["html", "css", "scss", "json", "xml", "yaml", "sql", "markdown", "toml", "dockerfile"]:
            return False
        info = LANGUAGES_REGISTRY.get(lang)
        if info and info.get("category") == "programming":
            return True
    return True

def parse_analysis_row(row: Dict[str, Any]) -> AnalysisResult:
    dry_run = []
    if row.get("dry_run_json"):
        try:
            dry_run = json.loads(row["dry_run_json"])
        except Exception:
            dry_run = []

    loop_details = None
    if row.get("loop_details_json"):
        try:
            loop_details = json.loads(row["loop_details_json"])
        except Exception:
            loop_details = None

    expected_io = None
    if row.get("expected_io_json"):
        try:
            expected_io = ExpectedIO(**json.loads(row["expected_io_json"]))
        except Exception:
            expected_io = None

    viva_questions = []
    if row.get("viva_questions_json"):
        try:
            raw_v = json.loads(row["viva_questions_json"])
            viva_questions = [VivaQuestionItem(**x) if isinstance(x, dict) else x for x in raw_v]
        except Exception:
            viva_questions = []

    return AnalysisResult(
        overview=row["overview"],
        logic_workflow=row["logic_workflow"],
        line_by_line=[LineExplanation(**x) for x in json.loads(row["line_by_line_json"])],
        inputs=row["inputs_text"],
        outputs=row["outputs_text"],
        expected_io=expected_io,
        variables_functions=[VariableFunctionItem(**x) for x in json.loads(row["variables_functions_json"])],
        programming_concepts=json.loads(row["concepts_json"]),
        limitations=json.loads(row["limitations_json"]),
        complexity=ComplexityInfo(
            time=row["complexity_time"],
            space=row["complexity_space"],
            explanation=row["complexity_explanation"]
        ),
        learning_takeaway=row["learning_takeaway"],
        diagnostics=[DiagnosticItem(**x) for x in json.loads(row["diagnostics_json"])],
        suggested_code=row["suggested_code"],
        explanation_of_changes=row["explanation_of_changes"],
        mode=row["mode"],
        dry_run=dry_run,
        loop_details=loop_details,
        viva_questions=viva_questions
    )

@router.get("", response_model=List[SessionSummary])
def list_sessions(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query("all", description="Category: runnable, documents, or all"),
    user: Optional[dict] = Depends(optional_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        sql = """
            SELECT s.id, s.title, s.filename, s.language, s.is_runnable, s.created_at, s.updated_at,
                   (SELECT COUNT(*) FROM code_versions WHERE session_id = s.id) as version_count,
                   (SELECT MAX(version_number) FROM code_versions WHERE session_id = s.id) as active_version_number,
                   (SELECT language FROM code_versions WHERE session_id = s.id ORDER BY version_number DESC LIMIT 1) as latest_lang,
                   (SELECT filename FROM code_versions WHERE session_id = s.id ORDER BY version_number DESC LIMIT 1) as latest_filename
            FROM sessions s
            WHERE 1=1
        """
        params = []
        if user:
            sql += " AND (s.user_id = ? OR s.user_id IS NULL)"
            params.append(user["id"])

        if category == "runnable":
            sql += " AND s.is_runnable = 1"
        elif category == "documents":
            sql += " AND s.is_runnable = 0"

        if q and q.strip():
            query_param = f"%{q.strip()}%"
            sql += " AND (s.title LIKE ? OR s.filename LIKE ?)"
            params.extend([query_param, query_param])

        sql += " ORDER BY s.updated_at DESC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        return [
            SessionSummary(
                id=r["id"],
                title=r["title"],
                filename=r["filename"] or r["latest_filename"] or ("main.py" if r["is_runnable"] else "document.txt"),
                language=r["language"] or r["latest_lang"] or ("python" if r["is_runnable"] else "text"),
                is_runnable=bool(r["is_runnable"]),
                version_count=r["version_count"] or 1,
                active_version_number=r["active_version_number"] or 1,
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
            for r in rows
        ]

@router.post("", response_model=SessionSummary)
def create_session(
    req: SessionCreateRequest,
    user: Optional[dict] = Depends(optional_current_user)
):
    session_id = str(uuid.uuid4())
    now = get_iso_now()

    filename = req.filename or "main.py"
    language = req.language or "python"
    
    if req.is_runnable is not None:
        is_runnable = req.is_runnable
    else:
        is_runnable = is_runnable_format(language, filename)

    title = req.title or filename
    code = req.code or ""
    user_id = user["id"] if user else None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO sessions (id, title, filename, language, is_runnable, user_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, title, filename, language, 1 if is_runnable else 0, user_id, now, now)
        )

        version_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (version_id, session_id, 1, code, language, filename, now)
        )

    return SessionSummary(
        id=session_id,
        title=title,
        filename=filename,
        language=language,
        is_runnable=is_runnable,
        version_count=1,
        active_version_number=1,
        created_at=now,
        updated_at=now
    )

@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, user: Optional[dict] = Depends(optional_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, filename, language, is_runnable, user_id, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,)
        )
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(session_row, user, "view")

        # Fetch versions
        cursor.execute(
            """SELECT v.id, v.session_id, v.version_number, v.code, v.language, v.filename, v.created_at, v.execution_result_json
               FROM code_versions v
               WHERE v.session_id = ?
               ORDER BY v.version_number ASC""",
            (session_id,)
        )
        version_rows = cursor.fetchall()
        versions = []

        for v in version_rows:
            # Fetch analysis for this version
            cursor.execute(
                """SELECT * FROM analyses WHERE code_version_id = ? LIMIT 1""",
                (v["id"],)
            )
            analysis_row = cursor.fetchone()
            analysis_obj = parse_analysis_row(dict(analysis_row)) if analysis_row else None

            exec_res = None
            if v["execution_result_json"]:
                try:
                    exec_res = RunCodeResponse(**json.loads(v["execution_result_json"]))
                except Exception:
                    exec_res = None

            versions.append(CodeVersionItem(
                id=v["id"],
                session_id=v["session_id"],
                version_number=v["version_number"],
                code=v["code"],
                language=v["language"],
                filename=v["filename"],
                created_at=v["created_at"],
                analysis=analysis_obj,
                execution_result=exec_res
            ))

        # Fetch messages
        cursor.execute(
            """SELECT id, session_id, code_version_id, role, content, mode, created_at
               FROM messages
               WHERE session_id = ?
               ORDER BY created_at ASC""",
            (session_id,)
        )
        msg_rows = cursor.fetchall()
        messages = [
            MessageItem(
                id=m["id"],
                session_id=m["session_id"],
                code_version_id=m["code_version_id"],
                role=m["role"],
                content=m["content"],
                mode=m["mode"],
                created_at=m["created_at"]
            )
            for m in msg_rows
        ]

        return SessionDetail(
            id=session_row["id"],
            title=session_row["title"],
            filename=session_row["filename"],
            language=session_row["language"],
            is_runnable=bool(session_row["is_runnable"]),
            created_at=session_row["created_at"],
            updated_at=session_row["updated_at"],
            versions=versions,
            messages=messages
        )

@router.patch("/{session_id}", response_model=SessionSummary)
def update_session(
    session_id: str,
    req: SessionUpdateRequest,
    user: Optional[dict] = Depends(optional_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        now = get_iso_now()

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        curr = cursor.fetchone()
        if not curr:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(curr, user, "update")

        new_title = req.title.strip() if req.title else curr["title"]
        new_filename = req.filename.strip() if req.filename else curr["filename"]

        new_language = curr["language"]
        new_runnable = curr["is_runnable"]
        if req.filename:
            detected = detect_language("", new_filename)
            if detected and detected != "auto":
                new_language = detected
                new_runnable = 1 if is_runnable_format(new_language, new_filename) else 0

        cursor.execute(
            """UPDATE sessions
               SET title = ?, filename = ?, language = ?, is_runnable = ?, updated_at = ?
               WHERE id = ?""",
            (new_title, new_filename, new_language, new_runnable, now, session_id)
        )

        cursor.execute(
            """UPDATE code_versions SET filename = ?
               WHERE session_id = ? AND version_number = (
                   SELECT MAX(version_number) FROM code_versions WHERE session_id = ?
               )""",
            (new_filename, session_id, session_id)
        )

        cursor.execute(
            """SELECT s.id, s.title, s.filename, s.language, s.is_runnable, s.created_at, s.updated_at,
                      (SELECT COUNT(*) FROM code_versions WHERE session_id = s.id) as version_count,
                      (SELECT MAX(version_number) FROM code_versions WHERE session_id = s.id) as active_version_number
               FROM sessions s WHERE s.id = ?""",
            (session_id,)
        )
        row = cursor.fetchone()
        return SessionSummary(
            id=row["id"],
            title=row["title"],
            filename=row["filename"],
            language=row["language"],
            is_runnable=bool(row["is_runnable"]),
            version_count=row["version_count"] or 1,
            active_version_number=row["active_version_number"] or 1,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

@router.delete("/{session_id}")
def delete_session(session_id: str, user: Optional[dict] = Depends(optional_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        curr = cursor.fetchone()
        if not curr:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(curr, user, "delete")
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": f"Session {session_id} deleted."}

@router.post("/{session_id}/versions", response_model=CodeVersionItem)
def save_session_version(
    session_id: str,
    req: SaveVersionRequest,
    user: Optional[dict] = Depends(optional_current_user)
):
    """
    Rule B: Edits create versions (v1, v2, v3...) under that file.
    Unchanged content creates no duplicate version.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(session_row, user, "save version to")

        cursor.execute(
            "SELECT * FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1",
            (session_id,)
        )
        latest = cursor.fetchone()

        incoming_code = req.code
        # If latest exists and code is identical, return the existing latest version without incrementing
        if latest and latest["code"] == incoming_code:
            cursor.execute("SELECT * FROM analyses WHERE code_version_id = ?", (latest["id"],))
            a_row = cursor.fetchone()
            a_obj = parse_analysis_row(dict(a_row)) if a_row else None
            exec_res = None
            if latest["execution_result_json"]:
                try:
                    exec_res = RunCodeResponse(**json.loads(latest["execution_result_json"]))
                except Exception:
                    pass
            return CodeVersionItem(
                id=latest["id"],
                session_id=latest["session_id"],
                version_number=latest["version_number"],
                code=latest["code"],
                language=latest["language"],
                filename=latest["filename"],
                created_at=latest["created_at"],
                analysis=a_obj,
                execution_result=exec_res
            )

        now = get_iso_now()
        next_v = (latest["version_number"] if latest else 0) + 1
        new_v_id = str(uuid.uuid4())
        v_lang = req.language or (latest["language"] if latest else session_row["language"] or "python")
        v_file = req.filename or (latest["filename"] if latest else session_row["filename"])

        cursor.execute(
            """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (new_v_id, session_id, next_v, incoming_code, v_lang, v_file, now)
        )
        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

        return CodeVersionItem(
            id=new_v_id,
            session_id=session_id,
            version_number=next_v,
            code=incoming_code,
            language=v_lang,
            filename=v_file,
            created_at=now,
            analysis=None,
            execution_result=None
        )

@router.post("/{session_id}/restore", response_model=CodeVersionItem)
def restore_session_version(
    session_id: str,
    req: RestoreVersionRequest,
    user: Optional[dict] = Depends(optional_current_user)
):
    """
    Restores an earlier version by creating a new version with the target code,
    preserving full revision history.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(session_row, user, "restore version in")

        target = None
        if req.version_id:
            cursor.execute("SELECT * FROM code_versions WHERE id = ? AND session_id = ?", (req.version_id, session_id))
            target = cursor.fetchone()
        elif req.version_number is not None:
            cursor.execute("SELECT * FROM code_versions WHERE version_number = ? AND session_id = ?", (req.version_number, session_id))
            target = cursor.fetchone()

        if not target:
            raise HTTPException(status_code=404, detail="Target version not found")

        cursor.execute(
            "SELECT * FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1",
            (session_id,)
        )
        latest = cursor.fetchone()

        now = get_iso_now()
        next_v = (latest["version_number"] if latest else 0) + 1
        new_v_id = str(uuid.uuid4())

        # If latest code is already identical to target code, return latest
        if latest and latest["code"] == target["code"]:
            cursor.execute("SELECT * FROM analyses WHERE code_version_id = ?", (latest["id"],))
            a_row = cursor.fetchone()
            a_obj = parse_analysis_row(dict(a_row)) if a_row else None
            exec_res = None
            if latest["execution_result_json"]:
                try:
                    exec_res = RunCodeResponse(**json.loads(latest["execution_result_json"]))
                except Exception:
                    pass
            return CodeVersionItem(
                id=latest["id"],
                session_id=latest["session_id"],
                version_number=latest["version_number"],
                code=latest["code"],
                language=latest["language"],
                filename=latest["filename"],
                created_at=latest["created_at"],
                analysis=a_obj,
                execution_result=exec_res
            )

        cursor.execute(
            """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (new_v_id, session_id, next_v, target["code"], target["language"], target["filename"], now)
        )
        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

        return CodeVersionItem(
            id=new_v_id,
            session_id=session_id,
            version_number=next_v,
            code=target["code"],
            language=target["language"],
            filename=target["filename"],
            created_at=now,
            analysis=None,
            execution_result=None
        )

@router.post("/{session_id}/duplicate", response_model=SessionSummary)
def duplicate_session(session_id: str, user: Optional[dict] = Depends(optional_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(session_row, user, "duplicate")

        cursor.execute("SELECT * FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1", (session_id,))
        latest = cursor.fetchone()
        code = latest["code"] if latest else ""
        lang = latest["language"] if latest else (session_row["language"] or "python")

        old_filename = session_row["filename"] or "main.py"
        p = Path(old_filename)
        new_filename = f"{p.stem}_copy{p.suffix}"
        new_title = f"{session_row['title']} (Copy)"

        new_session_id = str(uuid.uuid4())
        now = get_iso_now()
        user_id = user["id"] if user else (session_row["user_id"] if "user_id" in session_row.keys() else None)

        cursor.execute(
            """INSERT INTO sessions (id, title, filename, language, is_runnable, user_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_session_id, new_title, new_filename, lang, session_row["is_runnable"], user_id, now, now)
        )

        new_v_id = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (new_v_id, new_session_id, 1, code, lang, new_filename, now)
        )

        return SessionSummary(
            id=new_session_id,
            title=new_title,
            filename=new_filename,
            language=lang,
            is_runnable=bool(session_row["is_runnable"]),
            version_count=1,
            active_version_number=1,
            created_at=now,
            updated_at=now
        )

@router.get("/{session_id}/versions/{version_id}")
def get_session_version(
    session_id: str,
    version_id: str,
    user: Optional[dict] = Depends(optional_current_user)
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        if not session_row:
            raise HTTPException(status_code=404, detail="Session not found")
        verify_session_ownership(session_row, user, "view version of")

        cursor.execute(
            "SELECT * FROM code_versions WHERE id = ? AND session_id = ?",
            (version_id, session_id)
        )
        v = cursor.fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Code version not found")

        cursor.execute("SELECT * FROM analyses WHERE code_version_id = ?", (version_id,))
        a_row = cursor.fetchone()
        analysis_obj = parse_analysis_row(dict(a_row)) if a_row else None

        exec_res = None
        if v["execution_result_json"]:
            try:
                exec_res = RunCodeResponse(**json.loads(v["execution_result_json"]))
            except Exception:
                pass

        return CodeVersionItem(
            id=v["id"],
            session_id=v["session_id"],
            version_number=v["version_number"],
            code=v["code"],
            language=v["language"],
            filename=v["filename"],
            created_at=v["created_at"],
            analysis=analysis_obj,
            execution_result=exec_res
        )

@router.get("/export/all")
def export_all_sessions(user: Optional[dict] = Depends(optional_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        if user:
            cursor.execute("SELECT * FROM sessions WHERE user_id = ? OR user_id = ? OR user_id IS NULL ORDER BY created_at ASC", (user["id"], DEMO_USER_ID))
        else:
            cursor.execute("SELECT * FROM sessions WHERE user_id = ? OR user_id IS NULL ORDER BY created_at ASC", (DEMO_USER_ID,))
        sessions = [dict(r) for r in cursor.fetchall()]
        session_ids = [s["id"] for s in sessions]

        if not session_ids:
            return {
                "application": "codewise",
                "export_version": "1.0",
                "timestamp": get_iso_now(),
                "data": {
                    "sessions": [],
                    "code_versions": [],
                    "analyses": [],
                    "messages": []
                }
            }

        placeholders = ",".join("?" for _ in session_ids)
        cursor.execute(f"SELECT * FROM code_versions WHERE session_id IN ({placeholders}) ORDER BY created_at ASC", session_ids)
        versions = [dict(r) for r in cursor.fetchall()]
        version_ids = [v["id"] for v in versions]

        analyses = []
        if version_ids:
            v_placeholders = ",".join("?" for _ in version_ids)
            cursor.execute(f"SELECT * FROM analyses WHERE code_version_id IN ({v_placeholders}) ORDER BY created_at ASC", version_ids)
            analyses = [dict(r) for r in cursor.fetchall()]

        cursor.execute(f"SELECT * FROM messages WHERE session_id IN ({placeholders}) ORDER BY created_at ASC", session_ids)
        messages = [dict(r) for r in cursor.fetchall()]

        return {
            "application": "codewise",
            "export_version": "1.0",
            "timestamp": get_iso_now(),
            "data": {
                "sessions": sessions,
                "code_versions": versions,
                "analyses": analyses,
                "messages": messages
            }
        }

@router.post("/import/all")
def import_all_sessions(
    payload: Dict[str, Any] = Body(...),
    user: Optional[dict] = Depends(optional_current_user)
):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid import format: Payload must be a JSON object.")

    if "data" in payload:
        if not isinstance(payload["data"], dict):
            raise HTTPException(status_code=400, detail="Invalid import format: 'data' property must be a JSON object.")
        data = payload["data"]
    else:
        data = payload

    sessions_list = data.get("sessions", [])
    if not isinstance(sessions_list, list):
        raise HTTPException(status_code=400, detail="Invalid import data: 'sessions' must be an array.")

    if len(sessions_list) > 500:
        raise HTTPException(status_code=400, detail="Import limit exceeded: Maximum 500 sessions allowed per backup import.")

    imported_sessions = 0
    with get_db() as conn:
        cursor = conn.cursor()
        for s in sessions_list:
            if not isinstance(s, dict) or "id" not in s or "title" not in s:
                continue
            # Associate imported session with current authenticated user
            s_user_id = user["id"] if user else (s.get("user_id") or DEMO_USER_ID)
            cursor.execute(
                """INSERT INTO sessions (id, title, filename, language, is_runnable, user_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                   title=excluded.title, filename=excluded.filename, language=excluded.language,
                   is_runnable=excluded.is_runnable, user_id=excluded.user_id, updated_at=excluded.updated_at""",
                (str(s["id"]), str(s["title"]), s.get("filename"), s.get("language"), s.get("is_runnable", 1), s_user_id, s.get("created_at", get_iso_now()), s.get("updated_at", get_iso_now()))
            )
            imported_sessions += 1

        cursor.execute("SELECT id FROM sessions")
        valid_session_ids = {r["id"] for r in cursor.fetchall()}

        for v in data.get("code_versions", []):
            if not isinstance(v, dict) or v.get("session_id") not in valid_session_ids:
                continue
            cursor.execute(
                """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at, execution_result_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                   session_id=excluded.session_id, version_number=excluded.version_number,
                   code=excluded.code, language=excluded.language, filename=excluded.filename,
                   execution_result_json=excluded.execution_result_json""",
                (str(v["id"]), str(v["session_id"]), v.get("version_number", 1), v.get("code", ""), v.get("language", "python"), v.get("filename"), v.get("created_at", get_iso_now()), v.get("execution_result_json"))
            )

        cursor.execute("SELECT id FROM code_versions")
        valid_version_ids = {r["id"] for r in cursor.fetchall()}

        for a in data.get("analyses", []):
            if not isinstance(a, dict) or a.get("code_version_id") not in valid_version_ids:
                continue
            cursor.execute(
                """INSERT INTO analyses (
                    id, code_version_id, mode, overview, logic_workflow, line_by_line_json,
                    inputs_text, outputs_text, variables_functions_json, concepts_json,
                    limitations_json, complexity_time, complexity_space, complexity_explanation,
                    learning_takeaway, diagnostics_json, suggested_code, explanation_of_changes,
                    dry_run_json, loop_details_json, expected_io_json, viva_questions_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    code_version_id=excluded.code_version_id, mode=excluded.mode, overview=excluded.overview,
                    logic_workflow=excluded.logic_workflow, line_by_line_json=excluded.line_by_line_json,
                    inputs_text=excluded.inputs_text, outputs_text=excluded.outputs_text,
                    variables_functions_json=excluded.variables_functions_json,
                    concepts_json=excluded.concepts_json, limitations_json=excluded.limitations_json,
                    complexity_time=excluded.complexity_time, complexity_space=excluded.complexity_space,
                    complexity_explanation=excluded.complexity_explanation, learning_takeaway=excluded.learning_takeaway,
                    diagnostics_json=excluded.diagnostics_json, suggested_code=excluded.suggested_code,
                    explanation_of_changes=excluded.explanation_of_changes, dry_run_json=excluded.dry_run_json,
                    loop_details_json=excluded.loop_details_json, expected_io_json=excluded.expected_io_json,
                    viva_questions_json=excluded.viva_questions_json""",
                (
                    str(a["id"]), str(a["code_version_id"]), a.get("mode", "local"), a.get("overview", ""), a.get("logic_workflow", ""),
                    a.get("line_by_line_json", "[]"), a.get("inputs_text", ""), a.get("outputs_text", ""),
                    a.get("variables_functions_json", "[]"), a.get("concepts_json", "[]"), a.get("limitations_json", "[]"),
                    a.get("complexity_time", "O(1)"), a.get("complexity_space", "O(1)"), a.get("complexity_explanation", ""),
                    a.get("learning_takeaway", ""), a.get("diagnostics_json", "[]"), a.get("suggested_code"),
                    a.get("explanation_of_changes"), a.get("dry_run_json"), a.get("loop_details_json"),
                    a.get("expected_io_json"), a.get("viva_questions_json"),
                    a.get("created_at", get_iso_now())
                )
            )

        for m in data.get("messages", []):
            if not isinstance(m, dict) or m.get("session_id") not in valid_session_ids:
                continue
            v_id = m.get("code_version_id")
            if v_id and v_id not in valid_version_ids:
                v_id = None
            cursor.execute(
                """INSERT INTO messages (id, session_id, code_version_id, role, content, mode, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                   session_id=excluded.session_id, code_version_id=excluded.code_version_id,
                   role=excluded.role, content=excluded.content, mode=excluded.mode""",
                (str(m["id"]), str(m["session_id"]), v_id, m.get("role", "user"), m.get("content", ""), m.get("mode", "local"), m.get("created_at", get_iso_now()))
            )

    return {"status": "success", "imported_sessions_count": imported_sessions}
