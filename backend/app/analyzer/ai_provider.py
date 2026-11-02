import json
import logging
from typing import Optional, Dict, Any, List
import httpx
from ..config import (
    get_gemini_api_key,
    get_gemini_model,
    get_ai_provider,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    CODEWISE_AI_KEY,
    AI_MODEL_NAME,
)
from ..models import (
    AnalysisResult,
    ComplexityInfo,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    DryRunStep,
    LoopDetails,
    ExpectedIO,
    VivaQuestionItem
)
from .static_engine import StaticEngine

logger = logging.getLogger(__name__)

# Benchmarked Academic Prompts
BENCHMARK_PROMPT_A = """Analyze the provided code and provide a clear, concise plain-language summary of its purpose and behavior."""

BENCHMARK_PROMPT_B = """You are the AI code explanation engine for codewise (tagline: "understand the code. master the logic.").
CRITICAL REQUIREMENTS:
1. Base all explanations strictly on the actual submitted code. Do NOT invent, assume, or hallucinate functions, variables, parameters, imports, or program behavior that does not exist in the code.
2. If the code has syntax errors or runtime issues, accurately detect and describe them under diagnostics.
3. Provide step-by-step logic workflow and an exact line-by-line breakdown for the lines of code.
4. Detail input sources, expected types/formats, expected outputs, limitations/edge cases, and time/space complexity (using Big-O notation, e.g. O(n), O(1)).
5. Return ONLY a single valid JSON object matching this schema:
{
  "overview": "Clear explanation of program purpose and problem it solves.",
  "logic_workflow": "Numbered step-by-step execution flow.",
  "line_by_line": [
    {"line_number": 1, "code_segment": "code here", "explanation": "what this line does"}
  ],
  "inputs": "Input sources, expected types, validation.",
  "outputs": "Outputs, returns, console logs, with sample input/output if applicable.",
  "variables_functions": [
    {"name": "x", "kind": "variable", "data_type": "int", "description": "purpose", "scope": "local"}
  ],
  "programming_concepts": ["Loops", "Recursion", ...],
  "limitations": ["Assumptions, edge cases, potential failures..."],
  "complexity": {
    "time": "O(...)",
    "space": "O(...)",
    "explanation": "concise derivation"
  },
  "learning_takeaway": "Student-friendly takeaway.",
  "diagnostics": [
    {
      "id": "diag-1",
      "title": "Title",
      "severity": "error",
      "line_number": 1,
      "explanation": "details",
      "recommended_correction": "how to fix",
      "corrected_snippet": "code snippet",
      "detection_type": "llm_inferred",
      "detection_source": "llm_inferred"
    }
  ],
  "suggested_code": "complete corrected or optimized code if helpful or null",
  "explanation_of_changes": "explanation of what changed and why or null"
}
Output ONLY raw valid JSON."""

BENCHMARK_PROMPT_C = """You are a patient programming tutor. Analyze this code for potential runtime errors, type mismatches, boundary bugs, and offer constructive pedagogical debugging guidance."""

SYSTEM_PROMPT = BENCHMARK_PROMPT_B


def safe_parse_json(text: str) -> dict:
    """Safely extracts and parses JSON even if wrapped in markdown code blocks."""
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(clean[start:end + 1])
        raise


def normalize_gemini_analysis(data: dict) -> dict:
    """Normalizes parsed LLM output to match Pydantic schema strictly."""
    # Complexity normalization
    comp = data.get("complexity")
    if not isinstance(comp, dict):
        comp_str = str(comp or "O(1)")
        data["complexity"] = {
            "time": comp_str,
            "space": "O(1)",
            "explanation": "Estimated time/space complexity."
        }
    else:
        comp.setdefault("time", "O(1)")
        comp.setdefault("space", "O(1)")
        comp.setdefault("explanation", "")

    # Line by line normalization
    lbl = []
    for idx, item in enumerate(data.get("line_by_line", [])):
        if isinstance(item, dict):
            lbl.append({
                "line_number": item.get("line_number", idx + 1),
                "code_segment": str(item.get("code_segment", "")),
                "explanation": str(item.get("explanation", ""))
            })
    data["line_by_line"] = lbl

    # Diagnostics normalization
    diags = []
    for idx, d in enumerate(data.get("diagnostics", [])):
        if isinstance(d, dict):
            diags.append({
                "id": str(d.get("id") or f"diag-{idx+1}"),
                "title": str(d.get("title") or "Code Diagnostic"),
                "severity": str(d.get("severity") or "warning"),
                "line_number": d.get("line_number"),
                "explanation": str(d.get("explanation") or ""),
                "recommended_correction": str(d.get("recommended_correction") or "Review and correct this issue."),
                "corrected_snippet": d.get("corrected_snippet"),
                "detection_type": str(d.get("detection_type") or "llm_inferred"),
                "detection_source": str(d.get("detection_source") or "llm_inferred")
            })
    data["diagnostics"] = diags

    # Variables & functions normalization
    vf = []
    for item in data.get("variables_functions", []):
        if isinstance(item, dict):
            vf.append({
                "name": str(item.get("name", "variable")),
                "kind": str(item.get("kind", "variable")),
                "data_type": str(item.get("data_type", "unknown")),
                "description": str(item.get("description", "")),
                "scope": str(item.get("scope", "local"))
            })
    data["variables_functions"] = vf

    # Ensure text fields are strings (convert lists if returned as arrays)
    for field in ["logic_workflow", "inputs", "outputs", "overview", "learning_takeaway"]:
        val = data.get(field)
        if isinstance(val, list):
            data[field] = "\n".join(str(item) for item in val)
        elif val is not None and not isinstance(val, str):
            data[field] = str(val)

    data.setdefault("overview", "Code analysis completed.")
    data.setdefault("logic_workflow", "Sequential execution.")
    data.setdefault("inputs", "Standard input or arguments.")
    data.setdefault("outputs", "Console output or return value.")
    data.setdefault("programming_concepts", [])
    data.setdefault("limitations", [])
    data.setdefault("learning_takeaway", "Inspect execution flow and verify edge cases.")
    return data


class AIProvider:
    def __init__(self, static_fallback: StaticEngine):
        self.static_fallback = static_fallback

    async def analyze_with_ai_or_fallback(
        self,
        code: str,
        language: str,
        filename: Optional[str] = None
    ) -> AnalysisResult:
        # Non-programming / markup formats (JSON, YAML, XML, Markdown, CSS) are handled deterministically
        if language and language.lower() in ["json", "yaml", "xml", "markdown", "toml", "css", "scss"]:
            res = self.static_fallback.analyze(code, language, filename)
            res.mode = "local"
            return res

        gemini_key = get_gemini_api_key()
        provider = get_ai_provider()
        result = None

        # Prefer Gemini when configured or in auto mode with GEMINI_API_KEY present
        if (provider == "gemini" or provider == "auto") and gemini_key:
            try:
                result = await self._call_gemini(code, language, gemini_key, filename)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e.__class__.__name__}")
        elif provider == "openai":
            key = OPENAI_API_KEY or CODEWISE_AI_KEY
            if key:
                try:
                    result = await self._call_openai(code, language, key)
                except Exception as e:
                    logger.warning(f"OpenAI API call failed: {e.__class__.__name__}")
        elif not gemini_key and (OPENAI_API_KEY or CODEWISE_AI_KEY):
            try:
                result = await self._call_openai(code, language, OPENAI_API_KEY or CODEWISE_AI_KEY)
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e.__class__.__name__}")

        if result:
            return result

        # Fallback to local rule-based analysis
        res = self.static_fallback.analyze(code, language, filename)
        res.mode = "local"
        return res

    def _create_quota_fallback(self, code: str, language: str, filename: Optional[str]) -> AnalysisResult:
        res = self.static_fallback.analyze(code, language, filename)
        res.mode = "local"
        res.diagnostics.insert(0, DiagnosticItem(
            id="gemini-quota-notice",
            title="Gemini Free-Tier Rate Limit Reached",
            severity="suggestion",
            line_number=None,
            explanation="The Gemini API returned HTTP 429 (rate limit or daily free-tier quota exceeded). Codewise has automatically provided analysis using the built-in deterministic local engine.",
            recommended_correction="Wait a minute before requesting another AI analysis, or continue working with the local rule-based engine.",
            detection_type="system_notice",
            detection_source="system_notice"
        ))
        return res

    def _create_auth_fallback(
        self,
        code: str,
        language: str,
        filename: Optional[str],
        status_code: int,
        err_msg: str = ""
    ) -> AnalysisResult:
        res = self.static_fallback.analyze(code, language, filename)
        res.mode = "local"
        if "free tier is not available for this project" in err_msg.lower():
            title = "Gemini Free Tier Not Enabled For Project"
            explanation = (
                "Google AI Studio returned: 'The Gemini API free tier is not available for this project.' "
                "This typically happens if the key was created under an existing enterprise/cloud project without free tier privileges."
            )
            correction = "In Google AI Studio (https://aistudio.google.com/app/apikey), click 'Create API key in new project' to get a free-tier key, or continue using the local engine."
        else:
            title = "Gemini API Key Authentication Issue"
            explanation = f"Gemini API returned HTTP {status_code}. {err_msg if err_msg else 'The configured GEMINI_API_KEY could not be authenticated.'}"
            correction = "Ensure GEMINI_API_KEY in backend/.env is a valid key from Google AI Studio (https://aistudio.google.com/app/apikey)."

        res.diagnostics.insert(0, DiagnosticItem(
            id="gemini-auth-notice",
            title=title,
            severity="suggestion",
            line_number=None,
            explanation=explanation,
            recommended_correction=correction,
            detection_type="system_notice",
            detection_source="system_notice"
        ))
        return res

    def _create_network_fallback(self, code: str, language: str, filename: Optional[str]) -> AnalysisResult:
        res = self.static_fallback.analyze(code, language, filename)
        res.mode = "local"
        res.diagnostics.insert(0, DiagnosticItem(
            id="gemini-network-notice",
            title="Gemini API Network Unreachable",
            severity="suggestion",
            line_number=None,
            explanation="Could not reach the Google Gemini API (network timeout or offline). Codewise analyzed your code using the local engine.",
            recommended_correction="Check internet connectivity or continue using the local offline engine.",
            detection_type="system_notice",
            detection_source="system_notice"
        ))
        return res

    async def _call_gemini(
        self,
        code: str,
        language: str,
        api_key: str,
        filename: Optional[str] = None
    ) -> Optional[AnalysisResult]:
        model = get_gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        prompt = f"{SYSTEM_PROMPT}\n\nLanguage: {language}\nFilename: {filename or 'source'}\n\nCode to analyze:\n```\n{code}\n```"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                logger.warning(f"Gemini API network failure: {exc.__class__.__name__}")
                return self._create_network_fallback(code, language, filename)

            if resp.status_code == 200:
                data = resp.json()
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = safe_parse_json(text)
                    normalized = normalize_gemini_analysis(parsed)

                    # Backfill rich offline metadata (dry_run, loop_details, viva_questions) if missing
                    local_res = self.static_fallback.analyze(code, language, filename)
                    if not normalized.get("dry_run") and local_res.dry_run:
                        normalized["dry_run"] = [s.model_dump() for s in local_res.dry_run]
                    if not normalized.get("loop_details") and local_res.loop_details:
                        normalized["loop_details"] = local_res.loop_details.model_dump()
                    if not normalized.get("expected_io") and local_res.expected_io:
                        normalized["expected_io"] = local_res.expected_io.model_dump()
                    if not normalized.get("viva_questions") and local_res.viva_questions:
                        normalized["viva_questions"] = [v.model_dump() for v in local_res.viva_questions]

                    normalized["mode"] = "ai"
                    return AnalysisResult(**normalized)
                except Exception as parse_err:
                    logger.warning(f"Failed to parse Gemini JSON response: {parse_err}")
                    return self.static_fallback.analyze(code, language, filename)

            elif resp.status_code == 429:
                logger.warning("Gemini API rate limit or free-tier quota exceeded (HTTP 429).")
                return self._create_quota_fallback(code, language, filename)

            elif resp.status_code in (400, 401, 403):
                err_text = ""
                try:
                    err_text = resp.json().get("error", {}).get("message", "")
                except Exception:
                    pass
                logger.warning(f"Gemini API key rejected or unauthorized (HTTP {resp.status_code}): {err_text}")
                return self._create_auth_fallback(code, language, filename, resp.status_code, err_text)

            else:
                logger.error(f"Gemini API returned HTTP {resp.status_code}.")
                return self.static_fallback.analyze(code, language, filename)

    async def _call_openai(self, code: str, language: str, api_key: str) -> Optional[AnalysisResult]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        prompt = f"Language: {language}\n\nCode:\n{code}"
        payload = {
            "model": AI_MODEL_NAME if AI_MODEL_NAME else "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_json = data["choices"][0]["message"]["content"]
                parsed = safe_parse_json(raw_json)
                normalized = normalize_gemini_analysis(parsed)
                normalized["mode"] = "ai"
                return AnalysisResult(**normalized)
            else:
                logger.error(f"OpenAI API returned {resp.status_code}")
                return None
