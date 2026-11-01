import json
import logging
from typing import Optional, Dict, Any
import httpx
from ..config import (
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    CODEWISE_AI_KEY,
    AI_PROVIDER,
    AI_MODEL_NAME,
)
from ..models import AnalysisResult, ComplexityInfo, LineExplanation, VariableFunctionItem, DiagnosticItem
from .static_engine import StaticEngine

logger = logging.getLogger(__name__)

# Benchmarked Academic Prompts
BENCHMARK_PROMPT_A = """Analyze the provided code and provide a clear, concise plain-language summary of its purpose and behavior."""

BENCHMARK_PROMPT_B = """You are the AI engine for codewise (tagline: "understand the code. master the logic.").
Analyze the provided code and return a structured JSON response matching this exact schema:
{
  "overview": "Clear explanation of program purpose and problem it solves.",
  "logic_workflow": "Numbered step-by-step execution flow.",
  "line_by_line": [
    {"line_number": 1, "code_segment": "code here", "explanation": "what line does"}
  ],
  "inputs": "Input sources, expected types, validation.",
  "outputs": "Outputs, returns, console logs, with example input/output if applicable.",
  "variables_functions": [
    {"name": "x", "kind": "variable", "data_type": "int", "description": "purpose", "scope": "local"}
  ],
  "programming_concepts": ["Loops", "Recursion", ...],
  "limitations": ["Assumptions, edge cases, potential failures..."],
  "complexity": {
    "time": "O(...)",
    "space": "O(...)",
    "explanation": "concise explanation"
  },
  "learning_takeaway": "Student-friendly takeaway.",
  "diagnostics": [
    {
      "id": "diag-1",
      "title": "Title",
      "severity": "error" | "warning" | "suggestion",
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
Output ONLY raw valid JSON. Do not wrap in markdown quotes if possible, or use standard json blocks."""

BENCHMARK_PROMPT_C = """You are a patient programming tutor. Analyze this code for potential runtime errors, type mismatches, boundary bugs, and offer constructive pedagogical debugging guidance."""

SYSTEM_PROMPT = BENCHMARK_PROMPT_B

class AIProvider:
    def __init__(self, static_fallback: StaticEngine):
        self.static_fallback = static_fallback

    async def analyze_with_ai_or_fallback(
        self,
        code: str,
        language: str,
        filename: Optional[str] = None
    ) -> AnalysisResult:
        result = None
        # Strict provider selection honoring AI_PROVIDER configuration
        if AI_PROVIDER == "gemini":
            if GEMINI_API_KEY:
                try:
                    result = await self._call_gemini(code, language, GEMINI_API_KEY)
                except Exception as e:
                    logger.warning(f"Gemini API call failed: {e}")
        elif AI_PROVIDER == "openai":
            key = OPENAI_API_KEY or CODEWISE_AI_KEY
            if key:
                try:
                    result = await self._call_openai(code, language, key)
                except Exception as e:
                    logger.warning(f"OpenAI API call failed: {e}")
        else:
            # Auto-detection if AI_PROVIDER not explicitly constrained
            if GEMINI_API_KEY:
                try:
                    result = await self._call_gemini(code, language, GEMINI_API_KEY)
                except Exception as e:
                    logger.warning(f"Gemini API call failed: {e}")
            elif OPENAI_API_KEY or CODEWISE_AI_KEY:
                try:
                    result = await self._call_openai(code, language, OPENAI_API_KEY or CODEWISE_AI_KEY)
                except Exception as e:
                    logger.warning(f"OpenAI API call failed: {e}")

        if result:
            result.mode = "ai"
            return result

        # Fallback to local rule-based analysis
        res = self.static_fallback.analyze(code, language, filename)
        res.mode = "local"
        return res

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
                parsed = json.loads(raw_json)
                return AnalysisResult(**parsed)
            else:
                logger.error(f"OpenAI API returned {resp.status_code}: {resp.text}")
                return None

    async def _call_gemini(self, code: str, language: str, api_key: str) -> Optional[AnalysisResult]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = f"{SYSTEM_PROMPT}\n\nLanguage: {language}\n\nCode:\n{code}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text)
                return AnalysisResult(**parsed)
            else:
                logger.error(f"Gemini API returned {resp.status_code}: {resp.text}")
                return None
