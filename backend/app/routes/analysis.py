import uuid
import json
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from ..models import (
    AnalyzeRequest,
    AnalysisResult,
    RunCodeRequest,
    RunCodeResponse,
    DetectLanguageRequest,
    VerifySampleRequest,
    VerifySampleResponse
)
from ..database import get_db, get_iso_now
from ..analyzer.static_engine import StaticEngine
from ..analyzer.ai_provider import AIProvider
from ..executor import CodeExecutor
from ..detector import LANGUAGES_REGISTRY, detect_language, detect_language_details
from ..auth import optional_current_user

router = APIRouter(prefix="/api", tags=["Analysis"])
logger = logging.getLogger(__name__)

static_engine = StaticEngine()
ai_provider = AIProvider(static_fallback=static_engine)

def is_runnable_format(language: str, filename: str = None) -> bool:
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

@router.get("/languages")
def list_languages():
    """Returns the complete list of supported languages, enriched with live runtime capabilities."""
    from ..executor import get_host_runtime_capabilities
    capabilities = get_host_runtime_capabilities()

    results = []
    for lang_id, info in LANGUAGES_REGISTRY.items():
        item = dict(info)
        if item.get("category") == "programming":
            runtime_info = capabilities.get(lang_id)
            if runtime_info:
                item["runtime_available"] = runtime_info["available"]
                item["executable"] = runtime_info["available"]
                item["unavailable_reason"] = runtime_info["missing_reason"] if not runtime_info["available"] else None
            else:
                item["runtime_available"] = False
                item["executable"] = False
        else:
            item["runtime_available"] = False
            item["executable"] = False
            item["unavailable_reason"] = None
        results.append(item)
    return results

@router.get("/capabilities")
def get_system_capabilities():
    """Returns the central language capability registry and live host runtime status."""
    from ..executor import get_host_runtime_capabilities
    runtimes = get_host_runtime_capabilities()
    return {
        "runtimes": runtimes,
        "executable_languages": [
            lang for lang, info in runtimes.items() if info["available"]
        ],
        "unavailable_languages": [
            lang for lang, info in runtimes.items() if not info["available"]
        ],
        "analysis_only_formats": [
            "json", "yaml", "xml", "sql", "markdown", "dockerfile", "toml", "jsx", "tsx"
        ],
        "previewable_formats": ["html", "css", "scss", "markdown"]
    }

@router.post("/detect-language")
def detect_code_language(req: DetectLanguageRequest):
    """Detects programming language and confidence from code content and optional filename."""
    return detect_language_details(req.code, req.filename)

@router.post("/run", response_model=RunCodeResponse)
def execute_code(req: RunCodeRequest):
    try:
        res = CodeExecutor.run(req.code, req.language, req.input_data or "")
        
        # If session_id and code_version_id are provided, persist execution output on that version
        if req.session_id and req.code_version_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE code_versions SET execution_result_json = ? WHERE id = ? AND session_id = ?",
                    (json.dumps(res), req.code_version_id, req.session_id)
                )
        elif req.session_id and not req.code_version_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE code_versions SET execution_result_json = ?
                       WHERE session_id = ? AND version_number = (
                           SELECT MAX(version_number) FROM code_versions WHERE session_id = ?
                       )""",
                    (json.dumps(res), req.session_id, req.session_id)
                )

        return RunCodeResponse(**res)
    except Exception as e:
        logger.exception("Error executing code")
        raise HTTPException(status_code=500, detail=str(e))

def generate_session_title(code: str, language: str, filename: str = None) -> str:
    if filename:
        return filename
    lines = code.splitlines()
    for line in lines[:10]:
        s = line.strip()
        if s.startswith("def ") or s.startswith("function ") or s.startswith("fun ") or s.startswith("fn "):
            parts = s.split()
            if len(parts) > 1:
                name = parts[1].split("(")[0]
                return f"{language.capitalize()}: {name}()"
        if "int main" in s or "public static void main" in s:
            return f"{language.capitalize()}: main()"
        if s.upper().startswith("SELECT") or s.upper().startswith("CREATE TABLE"):
            return f"SQL Query: {s[:25]}..."
        if "<!DOCTYPE" in s or "<html" in s:
            return "HTML Web Document"
    return f"{language.capitalize()} Analysis"

@router.post("/analyze")
async def analyze_code(req: AnalyzeRequest, user: Optional[dict] = Depends(optional_current_user)):
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="Cannot analyze empty source code.")

    try:
        # Resolve language if auto or blank
        resolved_language = req.language
        if not resolved_language or resolved_language.lower() == "auto":
            resolved_language = detect_language(req.code, req.filename) or "python"

        # 1. Run analysis
        analysis = await ai_provider.analyze_with_ai_or_fallback(
            code=req.code,
            language=resolved_language,
            filename=req.filename
        )

        session_id = req.session_id
        target_version_id = req.code_version_id
        now = get_iso_now()

        dry_run_data = json.dumps([s.model_dump() for s in analysis.dry_run]) if analysis.dry_run else None
        loop_data = json.dumps(analysis.loop_details.model_dump()) if analysis.loop_details else None
        expected_io_data = json.dumps(analysis.expected_io.model_dump()) if analysis.expected_io else None
        viva_data = json.dumps([v.model_dump() for v in analysis.viva_questions]) if analysis.viva_questions else None

        with get_db() as conn:
            cursor = conn.cursor()

            # Case 1: Existing session specified
            if session_id:
                cursor.execute("SELECT id, filename, is_runnable FROM sessions WHERE id = ?", (session_id,))
                session_row = cursor.fetchone()
                
                if session_row:
                    # Check whether code matches the target or latest version
                    if target_version_id:
                        cursor.execute(
                            "SELECT id, code, version_number FROM code_versions WHERE id = ?",
                            (target_version_id,)
                        )
                        v_row = cursor.fetchone()
                    else:
                        cursor.execute(
                            "SELECT id, code, version_number FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1",
                            (session_id,)
                        )
                        v_row = cursor.fetchone()

                    if v_row and v_row["code"] == req.code:
                        target_version_id = v_row["id"]
                    else:
                        # User modified code in editor: create new code revision so code & analysis stay synchronized
                        target_version_id = str(uuid.uuid4())
                        cursor.execute(
                            "SELECT MAX(version_number) as max_v FROM code_versions WHERE session_id = ?",
                            (session_id,)
                        )
                        max_row = cursor.fetchone()
                        next_v = (max_row["max_v"] if max_row and max_row["max_v"] is not None else 0) + 1
                        fname = req.filename or session_row["filename"]
                        cursor.execute(
                            """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (target_version_id, session_id, next_v, req.code, resolved_language, fname, now)
                        )

                    if target_version_id:
                        # Upsert analysis into analyses table under this version
                        cursor.execute("SELECT id FROM analyses WHERE code_version_id = ?", (target_version_id,))
                        existing_a = cursor.fetchone()
                        if existing_a:
                            cursor.execute(
                                """UPDATE analyses SET
                                    mode = ?, overview = ?, logic_workflow = ?, line_by_line_json = ?,
                                    inputs_text = ?, outputs_text = ?, variables_functions_json = ?,
                                    concepts_json = ?, limitations_json = ?, complexity_time = ?,
                                    complexity_space = ?, complexity_explanation = ?, learning_takeaway = ?,
                                    diagnostics_json = ?, suggested_code = ?, explanation_of_changes = ?,
                                    dry_run_json = ?, loop_details_json = ?, expected_io_json = ?, viva_questions_json = ?, created_at = ?
                                   WHERE code_version_id = ?""",
                                (
                                    analysis.mode, analysis.overview, analysis.logic_workflow,
                                    json.dumps([l.model_dump() for l in analysis.line_by_line]),
                                    analysis.inputs, analysis.outputs,
                                    json.dumps([v.model_dump() for v in analysis.variables_functions]),
                                    json.dumps(analysis.programming_concepts),
                                    json.dumps(analysis.limitations),
                                    analysis.complexity.time, analysis.complexity.space, analysis.complexity.explanation,
                                    analysis.learning_takeaway,
                                    json.dumps([d.model_dump() for d in analysis.diagnostics]),
                                    analysis.suggested_code, analysis.explanation_of_changes,
                                    dry_run_data, loop_data, expected_io_data, viva_data, now,
                                    target_version_id
                                )
                            )
                        else:
                            analysis_id = str(uuid.uuid4())
                            cursor.execute(
                                """INSERT INTO analyses (
                                    id, code_version_id, mode, overview, logic_workflow, line_by_line_json,
                                    inputs_text, outputs_text, variables_functions_json, concepts_json,
                                    limitations_json, complexity_time, complexity_space, complexity_explanation,
                                    learning_takeaway, diagnostics_json, suggested_code, explanation_of_changes,
                                    dry_run_json, loop_details_json, expected_io_json, viva_questions_json, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    analysis_id, target_version_id, analysis.mode, analysis.overview,
                                    analysis.logic_workflow,
                                    json.dumps([l.model_dump() for l in analysis.line_by_line]),
                                    analysis.inputs, analysis.outputs,
                                    json.dumps([v.model_dump() for v in analysis.variables_functions]),
                                    json.dumps(analysis.programming_concepts),
                                    json.dumps(analysis.limitations),
                                    analysis.complexity.time, analysis.complexity.space, analysis.complexity.explanation,
                                    analysis.learning_takeaway,
                                    json.dumps([d.model_dump() for d in analysis.diagnostics]),
                                    analysis.suggested_code, analysis.explanation_of_changes,
                                    dry_run_data, loop_data, expected_io_data, viva_data, now
                                )
                            )
                        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

                        return {
                            "session_id": session_id,
                            "version_id": target_version_id,
                            "code_version_id": target_version_id,
                            "language": resolved_language,
                            "analysis": analysis
                        }

            # Case 2: No session_id provided - check if a session with this filename already exists
            fname = req.filename or f"code.{resolved_language}"
            cursor.execute("SELECT id FROM sessions WHERE filename = ? ORDER BY updated_at DESC LIMIT 1", (fname,))
            existing_s = cursor.fetchone()

            if existing_s:
                session_id = existing_s["id"]
                cursor.execute(
                    "SELECT id, code, version_number FROM code_versions WHERE session_id = ? ORDER BY version_number DESC LIMIT 1",
                    (session_id,)
                )
                latest_v = cursor.fetchone()

                if latest_v and latest_v["code"] == req.code:
                    target_version_id = latest_v["id"]
                else:
                    target_version_id = str(uuid.uuid4())
                    next_v = (latest_v["version_number"] if latest_v else 0) + 1
                    cursor.execute(
                        """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (target_version_id, session_id, next_v, req.code, resolved_language, fname, now)
                    )

                cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
            else:
                session_id = str(uuid.uuid4())
                target_version_id = str(uuid.uuid4())
                title = generate_session_title(req.code, resolved_language, req.filename)
                is_runnable = 1 if is_runnable_format(resolved_language, fname) else 0

                user_id = user["id"] if user else None
                cursor.execute(
                    """INSERT INTO sessions (id, title, filename, language, is_runnable, user_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_id, title, fname, resolved_language, is_runnable, user_id, now, now)
                )

                cursor.execute(
                    """INSERT INTO code_versions (id, session_id, version_number, code, language, filename, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (target_version_id, session_id, 1, req.code, resolved_language, fname, now)
                )

            # Store or update analysis result for target_version_id
            cursor.execute("SELECT id FROM analyses WHERE code_version_id = ?", (target_version_id,))
            existing_a = cursor.fetchone()
            if existing_a:
                cursor.execute(
                    """UPDATE analyses SET
                        mode = ?, overview = ?, logic_workflow = ?, line_by_line_json = ?,
                        inputs_text = ?, outputs_text = ?, variables_functions_json = ?,
                        concepts_json = ?, limitations_json = ?, complexity_time = ?,
                        complexity_space = ?, complexity_explanation = ?, learning_takeaway = ?,
                        diagnostics_json = ?, suggested_code = ?, explanation_of_changes = ?,
                        dry_run_json = ?, loop_details_json = ?, expected_io_json = ?, viva_questions_json = ?, created_at = ?
                       WHERE code_version_id = ?""",
                    (
                        analysis.mode, analysis.overview, analysis.logic_workflow,
                        json.dumps([l.model_dump() for l in analysis.line_by_line]),
                        analysis.inputs, analysis.outputs,
                        json.dumps([v.model_dump() for v in analysis.variables_functions]),
                        json.dumps(analysis.programming_concepts),
                        json.dumps(analysis.limitations),
                        analysis.complexity.time, analysis.complexity.space, analysis.complexity.explanation,
                        analysis.learning_takeaway,
                        json.dumps([d.model_dump() for d in analysis.diagnostics]),
                        analysis.suggested_code, analysis.explanation_of_changes,
                        dry_run_data, loop_data, expected_io_data, viva_data, now,
                        target_version_id
                    )
                )
            else:
                analysis_id = str(uuid.uuid4())
                cursor.execute(
                    """INSERT INTO analyses (
                        id, code_version_id, mode, overview, logic_workflow, line_by_line_json,
                        inputs_text, outputs_text, variables_functions_json, concepts_json,
                        limitations_json, complexity_time, complexity_space, complexity_explanation,
                        learning_takeaway, diagnostics_json, suggested_code, explanation_of_changes,
                        dry_run_json, loop_details_json, expected_io_json, viva_questions_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        analysis_id, target_version_id, analysis.mode, analysis.overview,
                        analysis.logic_workflow,
                        json.dumps([l.model_dump() for l in analysis.line_by_line]),
                        analysis.inputs, analysis.outputs,
                        json.dumps([v.model_dump() for v in analysis.variables_functions]),
                        json.dumps(analysis.programming_concepts),
                        json.dumps(analysis.limitations),
                        analysis.complexity.time, analysis.complexity.space, analysis.complexity.explanation,
                        analysis.learning_takeaway,
                        json.dumps([d.model_dump() for d in analysis.diagnostics]),
                        analysis.suggested_code, analysis.explanation_of_changes,
                        dry_run_data, loop_data, expected_io_data, viva_data, now
                    )
                )

            return {
                "session_id": session_id,
                "version_id": target_version_id,
                "code_version_id": target_version_id,
                "language": resolved_language,
                "analysis": analysis
            }

    except Exception as e:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/verify-sample", response_model=VerifySampleResponse)
def verify_sample(req: VerifySampleRequest):
    """
    Executes code safely with representative sample input and compares actual output against expected output.
    Allows students to verify algorithm mechanics in real time.
    """
    try:
        res = CodeExecutor.run(req.code, req.language, req.sample_input or "")
        actual = (res.get("stdout") or "").strip()
        expected = (req.expected_output or "").strip()

        # Normalization helper for whitespace tolerance
        def norm(s: str) -> str:
            return "\n".join(" ".join(line.split()) for line in s.replace("\r\n", "\n").splitlines() if line.strip())

        norm_actual = norm(actual)
        norm_expected = norm(expected)
        is_match = (norm_actual == norm_expected) or (actual == expected) or (norm_expected in norm_actual)

        notes = "Actual output matches expected output." if is_match else "Output differs from expected result."
        if res.get("stderr"):
            err_snip = res.get("stderr")[:150]
            notes += f" (stderr: {err_snip})"

        return VerifySampleResponse(
            is_match=is_match,
            actual_output=res.get("stdout") or "",
            expected_output=req.expected_output or "",
            exit_code=res.get("exit_code", 0),
            execution_time_ms=res.get("execution_time_ms", 0),
            notes=notes
        )
    except Exception as e:
        logger.exception("Error executing sample verification")
        return VerifySampleResponse(
            is_match=False,
            actual_output="",
            expected_output=req.expected_output or "",
            exit_code=1,
            execution_time_ms=0,
            notes=f"Verification execution halted: {str(e)}"
        )
