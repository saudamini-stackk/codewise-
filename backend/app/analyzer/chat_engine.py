import re
import logging
from typing import Optional, List, Dict, Any
import httpx
from ..config import (
    get_gemini_api_key,
    get_gemini_model,
    get_ai_provider,
    OPENAI_API_KEY,
    CODEWISE_AI_KEY,
    AI_MODEL_NAME,
)
from ..models import AnalysisResult, RunCodeResponse

logger = logging.getLogger(__name__)

class ChatEngine:
    async def answer_question(
        self,
        question: str,
        code: str,
        language: str,
        analysis: Optional[AnalysisResult],
        history: List[Dict[str, str]],
        runtime_result: Optional[RunCodeResponse] = None
    ) -> Dict[str, str]:
        gemini_key = get_gemini_api_key()
        provider = get_ai_provider()

        # Prefer Gemini if configured or in auto mode with GEMINI_API_KEY present
        if (provider == "gemini" or provider == "auto") and gemini_key:
            try:
                ai_reply = await self._answer_with_gemini(
                    question, code, language, analysis, history, gemini_key, runtime_result
                )
                if ai_reply:
                    return {"reply": ai_reply, "mode": "ai"}
            except Exception as e:
                logger.warning(f"Gemini AI Chat failed, falling back to rule engine: {e.__class__.__name__}")
        elif (provider == "openai" or not provider) and (OPENAI_API_KEY or CODEWISE_AI_KEY):
            api_key = OPENAI_API_KEY or CODEWISE_AI_KEY
            try:
                ai_reply = await self._answer_with_openai(
                    question, code, language, analysis, history, api_key, runtime_result
                )
                if ai_reply:
                    return {"reply": ai_reply, "mode": "ai"}
            except Exception as e:
                logger.warning(f"OpenAI Chat failed, falling back to rule engine: {e.__class__.__name__}")

        # Local Rule-Based Chat Assistant Fallback
        local_reply = self._answer_with_rules(question, code, language, analysis, runtime_result)
        return {"reply": local_reply, "mode": "local"}

    def _answer_with_rules(
        self,
        q: str,
        code: str,
        lang: str,
        analysis: Optional[AnalysisResult],
        runtime_result: Optional[RunCodeResponse] = None
    ) -> str:
        q_lower = q.lower().strip()

        # 0. Runtime execution inquiries
        if any(w in q_lower for w in ["runtime", "traceback", "crash", "exit code", "stdout", "stderr", "output of running"]) and runtime_result:
            diag_text = ""
            if runtime_result.runtime_diagnostic:
                rd = runtime_result.runtime_diagnostic
                diag_text = (
                    f"\n\n**Runtime Exception Extracted:** `{rd.exception_type}` on line {rd.line_number or 'N/A'}\n"
                    f"*Error Message:* {rd.error_message}\n"
                    f"*Traceback:* ```\n{rd.traceback_snippet}\n```"
                )
            return (
                f"### Execution Results Inspection\n\n"
                f"- **Status:** `{runtime_result.status}`\n"
                f"- **Exit Code:** `{runtime_result.exit_code}`\n"
                f"- **Execution Time:** `{runtime_result.execution_time_ms} ms`\n"
                f"- **Console Output (stdout):**\n```\n{runtime_result.stdout or '(none)'}\n```\n"
                f"- **Error Output (stderr):**\n```\n{runtime_result.stderr or '(none)'}\n```"
                f"{diag_text}"
            )

        # 1. Loop explanations
        if any(w in q_lower for w in ["loop", "iteration", "repeat", "while", "for"]):
            loops_found = [line.strip() for line in code.splitlines() if any(k in line for k in ["for ", "while "])]
            if loops_found:
                loop_code = "\n".join(f"  {l}" for l in loops_found)
                return (
                    f"### Understanding the Loop in Simpler Terms\n\n"
                    f"In this program, the loop structure is:\n```\n{loop_code}\n```\n\n"
                    f"**How it works step-by-step:**\n"
                    f"1. **Initialization:** The counter or iterator starts at its beginning value.\n"
                    f"2. **Condition Check:** Before every pass, the computer evaluates whether the loop condition is still True. If False, the loop stops immediately.\n"
                    f"3. **Body Execution:** The statements inside the loop run using the current iteration's value.\n"
                    f"4. **Increment/Step:** The loop counter progresses to the next value.\n\n"
                    f"**Why this matters:** Loops automate repetitive tasks without duplicate code. Ensure the condition will eventually become False to avoid infinite loops."
                )
            return "No loop was detected in this program. The execution flows sequentially from top to bottom."

        # 2. Input is zero / negative / edge case
        if any(w in q_lower for w in ["zero", "0", "negative", "empty", "null"]):
            if "even" in code.lower() or "%" in code:
                return (
                    f"### What Happens if the Input is Zero or Negative?\n\n"
                    f"- **If input is 0:** `0 % 2 == 0` evaluates to `True`. Mathematically and in programming, 0 is an even number, so the program will report it as even.\n"
                    f"- **If input is negative:** In Python, `-4 % 2 == 0` (even) and `-3 % 2 == 1` (odd). The modulo operator `%` preserves the remainder behavior, so negative even integers are identified as even and negative odd integers as odd.\n"
                    f"- **Edge Case Warning:** If the input is not a whole number (like a float `3.5` or text `'abc'`), an unhandled conversion `int(input())` will raise a `ValueError`."
                )
            elif "factorial" in code.lower():
                return (
                    f"### What Happens with Zero or Negative Input in Factorials?\n\n"
                    f"- **If input is 0:** By mathematical definition, `0! = 1`. If your code handles `n <= 1` or initializes `result = 1` and skips the loop for 0, it correctly returns 1.\n"
                    f"- **If input is negative:** The factorial of a negative integer is mathematically undefined. An unchecked loop or recursion with negative n may cause infinite recursion or return 1 inappropriately. You should add a guard clause: `if (n < 0) {{ /* handle error */ }}`."
                )
            return (
                f"### Edge Case Analysis for Zero / Negative Input\n\n"
                f"When handling zero or negative values:\n"
                f"1. Check if zero could cause a division by zero error (`x / 0`).\n"
                f"2. Ensure boundary conditions (e.g. `n >= 0` or `len > 0`) are explicitly checked before executing dependent logic."
            )

        # 3. Dry run / trace
        if any(w in q_lower for w in ["dry run", "trace", "walkthrough", "step by step", "example input"]):
            if "even" in code.lower() or "%" in code:
                return (
                    f"### Step-by-Step Dry Run (Sample Input: `7`)\n\n"
                    f"| Step | Action | State / Value | Notes |\n"
                    f"| :--- | :--- | :--- | :--- |\n"
                    f"| 1 | Prompt User | `num = 7` | User enters integer `7` |\n"
                    f"| 2 | Modulo Calculation | `7 % 2 -> 1` | Remainder of 7 divided by 2 is 1 |\n"
                    f"| 3 | Evaluate Condition | `1 == 0 -> False` | Condition fails, jumps to `else` branch |\n"
                    f"| 4 | Output | `7 is odd` | Prints odd result to console |\n\n"
                    f"**Now trace with `4`:** `4 % 2 == 0 -> True` -> executes `if` branch -> prints `4 is even`."
                )
            elif "average" in code.lower() or "sum" in code.lower():
                return (
                    f"### Step-by-Step Dry Run (Sample Array: `[10, 20, 30]`)\n\n"
                    f"| Step | Index `i` | Array Item | Running `sum` | Notes |\n"
                    f"| :--- | :--- | :--- | :--- | :--- |\n"
                    f"| 1 | `i = 0` | `10` | `0 + 10 = 10` | First element processed |\n"
                    f"| 2 | `i = 1` | `20` | `10 + 20 = 30` | Second element added |\n"
                    f"| 3 | `i = 2` | `30` | `30 + 30 = 60` | Last valid element added |\n"
                    f"| 4 | `i = 3` | *Out of Bounds* | `60 + undefined = NaN` | **Bug Triggered** if loop condition was `i <= length`! |\n"
                    f"| 5 | Division | `sum / 3` | Returns `NaN` or `20` depending on boundary check. |"
                )
            return (
                f"### Program Execution Dry Run\n\n"
                f"To trace this program:\n"
                f"1. **Input state:** Trace variables initialized at start.\n"
                f"2. **Iteration/Condition:** For each line, check how values update in memory.\n"
                f"3. **Termination:** Verify that exit conditions are met and expected return/output is generated."
            )

        # 4. Error explanations
        if any(w in q_lower for w in ["error", "bug", "mistake", "warning", "nan", "why does"]):
            if analysis and analysis.diagnostics:
                diags_text = "\n\n".join(
                    f"**{d.severity.upper()}: {d.title} (Line {d.line_number or 'N/A'})**\n"
                    f"{d.explanation}\n"
                    f"*Recommended Fix:* {d.recommended_correction}"
                    for d in analysis.diagnostics
                )
                return f"### Diagnostic Findings for this Code\n\n{diags_text}"
            return "No static errors were detected by the code parser. The program syntax and structure appear valid."

        # 5. Improvements & Optimization
        if any(w in q_lower for w in ["improve", "optimize", "better", "cleaner", "refactor"]):
            comp = analysis.complexity.time if analysis else "O(n)"
            return (
                f"### Suggested Improvements & Best Practices\n\n"
                f"1. **Input Validation:** Guard all user inputs with error handling (`try/except` in Python, bounds checks in C++, type validation in JS).\n"
                f"2. **Time Complexity ({comp}):** Ensure nested loops are minimized. If searching in collections, prefer Sets or Hash Maps (O(1) lookup) over linear Arrays (O(n) lookup).\n"
                f"3. **Meaningful Naming & Documentation:** Use descriptive variable names and document parameters and return types.\n"
                f"4. **Modularization:** Break monolithic code into smaller, single-responsibility helper functions."
            )

        # Fallback response
        return (
            f"### Assistant Explanation\n\n"
            f"Based on static analysis of your {lang.capitalize()} code:\n"
            f"- **Overview:** {analysis.overview if analysis else 'Source code loaded.'}\n"
            f"- **Concepts Involved:** {', '.join(analysis.programming_concepts) if analysis else 'Standard programming constructs.'}\n"
            f"- **Complexity:** {analysis.complexity.time if analysis else 'O(1)'} time, {analysis.complexity.space if analysis else 'O(1)'} space.\n\n"
            f"*(Tip: Ask specific questions such as \"explain the loop in simpler terms\", \"show a dry run\", \"what happens if input is zero\", or \"how can I improve this\"!)*"
        )

    def _build_context_prompt(
        self,
        lang: str,
        code: str,
        analysis: Optional[AnalysisResult],
        runtime_result: Optional[RunCodeResponse]
    ) -> str:
        ctx_parts = [
            "You are the conversational learning assistant for codewise (tagline: 'understand the code. master the logic.').",
            "CRITICAL INSTRUCTIONS:",
            "1. Base all answers strictly on the actual submitted code below. Never invent functions, variables, or behavior.",
            "2. Support simpler explanations, step-by-step dry runs, and debugging questions.",
            "3. Format answers cleanly using GitHub Flavored Markdown (headings, lists, code fences).",
            f"Programming Language: {lang}",
            f"Source Code:\n```\n{code}\n```"
        ]
        if analysis:
            ctx_parts.append(f"Analysis Overview: {analysis.overview}")
            ctx_parts.append(f"Logic Workflow: {analysis.logic_workflow}")
            if analysis.complexity:
                ctx_parts.append(f"Time Complexity: {analysis.complexity.time}, Space Complexity: {analysis.complexity.space}")
            if analysis.diagnostics:
                diags_summary = "; ".join(f"[{d.severity}] {d.title} (line {d.line_number})" for d in analysis.diagnostics)
                ctx_parts.append(f"Static Diagnostics: {diags_summary}")
        if runtime_result:
            ctx_parts.append(f"Runtime Execution Status: {runtime_result.status}, Exit Code: {runtime_result.exit_code}")
            if runtime_result.stdout:
                ctx_parts.append(f"Execution Output (stdout):\n{runtime_result.stdout}")
            if runtime_result.stderr:
                ctx_parts.append(f"Execution Stderr:\n{runtime_result.stderr}")
            if runtime_result.runtime_diagnostic:
                ctx_parts.append(f"Runtime Diagnostic: {runtime_result.runtime_diagnostic.exception_type}: {runtime_result.runtime_diagnostic.error_message}")
        return "\n\n".join(ctx_parts)

    async def _answer_with_openai(
        self,
        q: str,
        code: str,
        lang: str,
        analysis: Optional[AnalysisResult],
        history: List[Dict[str, str]],
        api_key: str,
        runtime_result: Optional[RunCodeResponse] = None
    ) -> Optional[str]:
        system_msg = self._build_context_prompt(lang, code, analysis, runtime_result)
        messages = [{"role": "system", "content": system_msg}]
        for h in history[-8:]:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
        messages.append({"role": "user", "content": q})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": AI_MODEL_NAME if AI_MODEL_NAME else "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.4
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenAI Chat API returned {resp.status_code}")
                return None

    async def _answer_with_gemini(
        self,
        q: str,
        code: str,
        lang: str,
        analysis: Optional[AnalysisResult],
        history: List[Dict[str, str]],
        api_key: str,
        runtime_result: Optional[RunCodeResponse] = None
    ) -> Optional[str]:
        model = get_gemini_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        system_msg = self._build_context_prompt(lang, code, analysis, runtime_result)
        full_prompt = f"{system_msg}\n\nRecent Conversation History:\n"
        for h in history[-8:]:
            full_prompt += f"{h.get('role', 'user')}: {h.get('content', '')}\n"
        full_prompt += f"user: {q}\nassistant:"

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.4}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                logger.warning(f"Gemini Chat network error: {exc.__class__.__name__}")
                rules_reply = self._answer_with_rules(q, code, lang, analysis, runtime_result)
                return (
                    f"> [!NOTE]\n"
                    f"> **Gemini API Network Unreachable:** Unable to contact Google Gemini API ({exc.__class__.__name__}). "
                    f"The answer below was generated by the built-in Codewise local tutor engine.\n\n"
                    f"{rules_reply}"
                )

            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except Exception as e:
                    logger.warning(f"Failed to read Gemini chat reply text: {e}")
                    return self._answer_with_rules(q, code, lang, analysis, runtime_result)

            elif resp.status_code == 429:
                logger.warning("Gemini Chat API rate limit or free-tier quota exceeded (HTTP 429).")
                rules_reply = self._answer_with_rules(q, code, lang, analysis, runtime_result)
                return (
                    f"> [!NOTE]\n"
                    f"> **Gemini Free-Tier Rate Limit Reached (HTTP 429):** The Google Gemini free-tier rate limit or quota has been reached. "
                    f"The answer below was generated by the built-in Codewise local tutor engine.\n\n"
                    f"{rules_reply}"
                )

            elif resp.status_code in (400, 401, 403):
                err_text = ""
                try:
                    err_text = resp.json().get("error", {}).get("message", "")
                except Exception:
                    pass
                logger.warning(f"Gemini Chat API key rejected or unauthorized (HTTP {resp.status_code}): {err_text}")
                rules_reply = self._answer_with_rules(q, code, lang, analysis, runtime_result)
                if "free tier is not available for this project" in err_text.lower():
                    notice = (
                        "> [!NOTE]\n"
                        "> **Gemini Free Tier Not Enabled For Project:** Google AI Studio reported that the free tier is not enabled for this project. "
                        "To use Gemini for free without billing, create an API key at https://aistudio.google.com/app/apikey choosing **'Create API key in new project'**. "
                        "The answer below was generated by the built-in Codewise local tutor engine.\n\n"
                    )
                else:
                    notice = (
                        f"> [!NOTE]\n"
                        f"> **Gemini API Key Authentication Issue (HTTP {resp.status_code}):** {err_text if err_text else 'The configured GEMINI_API_KEY in your backend/.env was not accepted.'} "
                        f"The answer below was generated by the built-in Codewise local tutor engine.\n\n"
                    )
                return f"{notice}{rules_reply}"

            else:
                logger.error(f"Gemini Chat API returned HTTP {resp.status_code}")
                return self._answer_with_rules(q, code, lang, analysis, runtime_result)
