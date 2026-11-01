import re
import logging
from typing import Optional, List, Dict, Any
import httpx
from ..config import OPENAI_API_KEY, GEMINI_API_KEY, CODEWISE_AI_KEY, AI_MODEL_NAME, AI_PROVIDER
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
        # Strict provider selection honoring AI_PROVIDER
        if AI_PROVIDER == "gemini" and GEMINI_API_KEY:
            try:
                ai_reply = await self._answer_with_gemini(question, code, language, analysis, history, GEMINI_API_KEY, runtime_result)
                if ai_reply:
                    return {"reply": ai_reply, "mode": "ai"}
            except Exception as e:
                logger.warning(f"Gemini AI Chat failed, falling back to rule-based engine: {e}")
        elif (AI_PROVIDER == "openai" or not AI_PROVIDER) and (OPENAI_API_KEY or CODEWISE_AI_KEY):
            api_key = OPENAI_API_KEY or CODEWISE_AI_KEY
            try:
                ai_reply = await self._answer_with_openai(question, code, language, analysis, history, api_key, runtime_result)
                if ai_reply:
                    return {"reply": ai_reply, "mode": "ai"}
            except Exception as e:
                logger.warning(f"OpenAI Chat failed, falling back to rule-based engine: {e}")

        # Local Rule-Based Chat Assistant
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

        # 5. Practice question
        if any(w in q_lower for w in ["practice", "exercise", "question", "quiz", "test me", "challenge"]):
            if "even" in code.lower():
                return (
                    f"### Practice Challenge: Even/Odd Extensions\n\n"
                    f"**Problem: Categorize Numbers in a Range**\n"
                    f"Write a program that takes two integers `start` and `end`, and prints:\n"
                    f"1. All even numbers between `start` and `end` on one line.\n"
                    f"2. All odd numbers on the next line.\n"
                    f"3. The count of each.\n\n"
                    f"**Bonus Constraint:** Ensure your program works correctly even if `start` is greater than `end` (e.g. `start=10, end=2`) or when negative numbers are included!"
                )
            elif "average" in code.lower() or "array" in code.lower():
                return (
                    f"### Practice Challenge: Safe Array Aggregation\n\n"
                    f"**Problem: Trimmed Mean Calculator**\n"
                    f"Write a function that calculates the average of an array of numbers, but:\n"
                    f"1. Filters out any non-numeric values (`null`, `undefined`, strings) safely.\n"
                    f"2. Excludes the single smallest and single largest values before computing the average.\n"
                    f"3. Returns `0` if the array has fewer than 3 valid numbers."
                )
            return (
                f"### Practice Challenge\n\n"
                f"**Problem:** Implement a function that verifies whether an array/list of integers is strictly sorted in ascending order. If it is not sorted, return the index of the first out-of-order element."
            )

        # 6. Improvements & Optimization
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
            f"*(Tip: Ask specific questions such as \"explain the loop in simpler terms\", \"show a dry run\", \"what happens if input is zero\", or \"give me a practice challenge\"! For free-form reasoning, an AI API key can be set in your `.env` file.)*"
        )

    def _build_context_prompt(
        self,
        lang: str,
        code: str,
        analysis: Optional[AnalysisResult],
        runtime_result: Optional[RunCodeResponse]
    ) -> str:
        ctx_parts = [
            f"You are the conversational tutor for codewise (tagline: 'understand the code. master the logic.').",
            f"Programming language: {lang}",
            f"Source code:\n```\n{code}\n```"
        ]
        if analysis:
            ctx_parts.append(f"Analysis Overview: {analysis.overview}")
            ctx_parts.append(f"Logic Workflow: {analysis.logic_workflow}")
            if analysis.diagnostics:
                diags_summary = "; ".join(f"[{d.severity}] {d.title} (line {d.line_number})" for d in analysis.diagnostics)
                ctx_parts.append(f"Static Diagnostics: {diags_summary}")
        if runtime_result:
            ctx_parts.append(f"Runtime Status: {runtime_result.status}, Exit Code: {runtime_result.exit_code}")
            if runtime_result.runtime_diagnostic:
                ctx_parts.append(f"Runtime Diagnostic: {runtime_result.runtime_diagnostic.exception_type}: {runtime_result.runtime_diagnostic.error_message}")
        ctx_parts.append("Answer the student's question clearly, pedagogically, and concisely using GitHub Flavored Markdown.")
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
                logger.error(f"OpenAI Chat API returned {resp.status_code}: {resp.text}")
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
        system_msg = self._build_context_prompt(lang, code, analysis, runtime_result)
        full_prompt = f"{system_msg}\n\nRecent Conversation History:\n"
        for h in history[-8:]:
            full_prompt += f"{h.get('role', 'user')}: {h.get('content', '')}\n"
        full_prompt += f"user: {q}\nassistant:"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.4}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                logger.error(f"Gemini Chat API returned {resp.status_code}: {resp.text}")
                return None
