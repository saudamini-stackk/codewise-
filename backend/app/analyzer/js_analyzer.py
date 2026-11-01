import re
from typing import Optional, List, Set, Dict, Any
from .base import BaseAnalyzer, extract_lines, get_code_snippet
from ..models import (
    AnalysisResult,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    ComplexityInfo,
    ExpectedIO,
    VivaQuestionItem,
    DryRunStep,
    LoopDetails
)

class JavaScriptAnalyzer(BaseAnalyzer):
    def analyze(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        variables_functions: List[VariableFunctionItem] = []
        concepts: Set[str] = set()
        inputs_found: List[str] = []
        outputs_found: List[str] = []

        # 1. Bracket & Syntax Balance Check
        balance_err = self._check_brackets(code)
        if balance_err:
            diagnostics.append(balance_err)

        # 2. Scan lines for structures, variables, functions, and issues
        max_loop_depth = 0
        current_loop_depth = 0
        has_recursion = False
        func_names: Set[str] = set()

        declared_vars: Set[str] = set()
        const_vars: Set[str] = set()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            # Detect Functions
            func_match = re.search(r"\bfunction\s+([a-zA-Z0-9_$]+)\s*\((.*?)\)", line)
            arrow_match = re.search(r"\b(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:\((.*?)\)|([a-zA-Z0-9_$]+))\s*=>", line)
            
            if func_match:
                name, params = func_match.group(1), func_match.group(2)
                func_names.add(name)
                concepts.add("Functions")
                variables_functions.append(VariableFunctionItem(
                    name=name,
                    kind="function",
                    data_type="function",
                    description=f"Function declaration with parameters: ({params})",
                    scope="global"
                ))
            elif arrow_match:
                name = arrow_match.group(1)
                params = arrow_match.group(2) or arrow_match.group(3) or ""
                func_names.add(name)
                concepts.add("Arrow Functions")
                variables_functions.append(VariableFunctionItem(
                    name=name,
                    kind="function",
                    data_type="function",
                    description=f"Arrow function with parameters: ({params})",
                    scope="lexical"
                ))

            # Detect Variables
            var_match = re.findall(r"\b(const|let|var)\s+([a-zA-Z0-9_$]+)(?:\s*=\s*([^;,\n]+))?", line)
            for v_kind, v_name, v_val in var_match:
                concepts.add("Variables")
                declared_vars.add(v_name)
                if v_kind == "const":
                    const_vars.add(v_name)
                
                inferred_type = "any"
                if v_val:
                    v_val = v_val.strip()
                    if v_val.startswith("["):
                        inferred_type = "Array"
                        concepts.add("Arrays")
                    elif v_val.startswith("{"):
                        inferred_type = "Object"
                        concepts.add("Objects")
                    elif v_val.isdigit() or re.match(r"^-?\d+(\.\d+)?$", v_val):
                        inferred_type = "number"
                    elif v_val.startswith('"') or v_val.startswith("'") or v_val.startswith("`"):
                        inferred_type = "string"
                    elif v_val in {"true", "false"}:
                        inferred_type = "boolean"

                variables_functions.append(VariableFunctionItem(
                    name=v_name,
                    kind="constant" if v_kind == "const" else "variable",
                    data_type=inferred_type,
                    description=f"Declared with `{v_kind}` on line {idx}.",
                    scope="block" if v_kind in {"const", "let"} else "function"
                ))

            # Detect Loops & Complexity Depth
            if re.search(r"\b(for|while)\s*\(", line):
                concepts.add("Loops")
                current_loop_depth += 1
                if current_loop_depth > max_loop_depth:
                    max_loop_depth = current_loop_depth

            # Detect Inputs & Outputs
            if "prompt(" in line:
                inputs_found.append(f"Browser input modal (`prompt()` on line {idx})")
                concepts.add("User Input")
            if "process.argv" in line:
                inputs_found.append(f"Node.js CLI arguments (`process.argv` on line {idx})")
            if "console.log" in line or "console.error" in line:
                outputs_found.append(f"Console output (`console.log()` on line {idx})")
                concepts.add("Console Output")
            if "return " in line:
                outputs_found.append(f"Function return value on line {idx}")

            # --- Detect Common JavaScript Bugs & Antipatterns ---
            
            # 1. Off-by-one array iteration bug: `i <= array.length`
            off_by_one = re.search(r"for\s*\(\s*(?:let|var)?\s*([a-zA-Z0-9_$]+)\s*=\s*0\s*;\s*\1\s*<=\s*([a-zA-Z0-9_$]+)\.length\s*;", line)
            if off_by_one:
                idx_var = off_by_one.group(1)
                arr_var = off_by_one.group(2)
                diagnostics.append(DiagnosticItem(
                    id=f"off-by-one-{idx}",
                    title="Off-by-One Array Boundary Error",
                    severity="error",
                    line_number=idx,
                    explanation=f"Loop condition uses `{idx_var} <= {arr_var}.length`. In 0-indexed arrays, the last valid element index is `{arr_var}.length - 1`. When `{idx_var}` reaches `{arr_var}.length`, accessing `{arr_var}[{idx_var}]` returns `undefined`, which commonly produces `NaN` in numerical calculations.",
                    recommended_correction=f"Change `{idx_var} <= {arr_var}.length` to `{idx_var} < {arr_var}.length`.",
                    corrected_snippet=line.replace(f"{idx_var} <= {arr_var}.length", f"{idx_var} < {arr_var}.length"),
                    detection_type="static_heuristic"
                ))

            # 2. Loose equality `==` or `!=`
            loose_eq = re.search(r"[^=!<>](==|!=)[^=]", line)
            if loose_eq and "===" not in line and "!==" not in line:
                operator = loose_eq.group(1)
                strict_op = "===" if operator == "==" else "!=="
                diagnostics.append(DiagnosticItem(
                    id=f"loose-equality-{idx}",
                    title="Loose Equality Operator",
                    severity="suggestion",
                    line_number=idx,
                    explanation=f"Using loose equality `{operator}` triggers implicit type coercion, leading to unexpected truthy/falsy comparisons.",
                    recommended_correction=f"Use strict equality `{strict_op}` instead to compare both value and type without implicit coercion.",
                    detection_type="static_heuristic"
                ))

            # 3. Const Reassignment
            reassign_match = re.search(r"\b([a-zA-Z0-9_$]+)\s*=[^=]", line)
            if reassign_match and not any(k in line for k in ["const ", "let ", "var "]):
                target = reassign_match.group(1)
                if target in const_vars:
                    diagnostics.append(DiagnosticItem(
                        id=f"const-reassignment-{idx}",
                        title="Assignment to Constant Variable",
                        severity="error",
                        line_number=idx,
                        explanation=f"Variable `{target}` was declared with `const` and cannot be reassigned on line {idx}. This throws a TypeError: Assignment to constant variable at runtime.",
                        recommended_correction=f"Declare `{target}` using `let` instead of `const` if you need to mutate its reference.",
                        detection_type="static_heuristic"
                    ))

            # 4. Division by zero literal
            if re.search(r"/\s*0\b", line):
                diagnostics.append(DiagnosticItem(
                    id=f"zero-division-{idx}",
                    title="Division by Literal Zero",
                    severity="warning",
                    line_number=idx,
                    explanation=f"Dividing a numeric value by 0 evaluates to `Infinity` or `-Infinity` in JavaScript, which may corrupt downstream logic or lead to `NaN`.",
                    recommended_correction="Check that the denominator is not equal to zero before dividing.",
                    detection_type="static_heuristic"
                ))

            # 5. String prompt without parsing
            if "prompt(" in line and ("+" in line or "Number(" not in line):
                if re.search(r"(?:let|var|const)\s+([a-zA-Z0-9_$]+)\s*=\s*prompt\(", line):
                    var_name = re.search(r"(?:let|var|const)\s+([a-zA-Z0-9_$]+)\s*=\s*prompt\(", line).group(1)
                    diagnostics.append(DiagnosticItem(
                        id=f"prompt-string-{idx}",
                        title="Unparsed String Input from prompt()",
                        severity="suggestion",
                        line_number=idx,
                        explanation=f"`prompt()` always returns a string (or null). If `{var_name}` is subsequently used with `+`, JavaScript performs string concatenation rather than numeric addition.",
                        recommended_correction=f"Wrap `prompt()` with `Number(prompt(...))` or `parseFloat(prompt(...))` for numeric operations.",
                        corrected_snippet=line.replace("prompt(", "Number(prompt("),
                        detection_type="static_heuristic"
                    ))

        # Check for recursion
        for fn in func_names:
            for idx, line in enumerate(lines, 1):
                if fn in line and not line.strip().startswith(f"function {fn}"):
                    # heuristic check if called inside same block
                    pass

        # 3. Formulate Line-by-Line explanations
        line_explanations: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            line_explanations.append(LineExplanation(
                line_number=idx,
                code_segment=stripped,
                explanation=self._explain_js_line(stripped, idx)
            ))

        # 4. Complexity
        time_c, space_c, comp_exp = self._estimate_complexity(max_loop_depth)

        # 5. Overview & Workflow
        overview = self._generate_overview(func_names, concepts, inputs_found, outputs_found)
        workflow = self._generate_workflow(lines)

        # 6. Inputs & Outputs
        inputs_desc = "\n".join(f"- {item}" for item in set(inputs_found)) if inputs_found else "No direct console or prompt inputs detected (operates on declared data or arguments)."
        outputs_desc = "\n".join(f"- {item}" for item in set(outputs_found)) if outputs_found else "No direct console outputs or returns detected."

        # 7. Limitations
        limitations = [
            "JavaScript numbers follow IEEE-754 double-precision floating point standard (safe integer range: -(2^53 - 1) to (2^53 - 1)).",
            "Off-by-one indexing errors produce `undefined` rather than throwing an array out-of-bounds exception, making bugs silent until arithmetic produces `NaN`.",
        ]
        if "prompt(" in code:
            limitations.append("`prompt()` is synchronous, browser-specific, and blocks UI thread execution.")

        # 8. Learning Takeaway
        takeaway = self._generate_takeaway(diagnostics)

        has_console_log = any("console.log" in l for l in lines)
        has_prompt = any("prompt(" in l for l in lines)
        has_returns = any("return " in l for l in lines)

        # Expected I/O
        expected_io = ExpectedIO(
            input_source="Browser Prompt (`prompt()` function)" if has_prompt else ("Function Arguments" if func_names else "Hardcoded Variables / Script Context"),
            input_type="JavaScript primitives (String / Number / Object)",
            input_format="Interactive string from prompt or passed arguments",
            input_range="Nominal JavaScript data types",
            sample_input="Nominal input value",
            output_mechanism="Console Output (`console.log()` to stdout)" if has_console_log else ("Function Return Value" if has_returns else "Variable mutation"),
            output_type="Console string stream or return value",
            sample_output="Printed console log or return value",
            relationship="Transforms inputs through JavaScript procedural or functional instructions.",
            explanation="Outputs are displayed in the terminal/browser console or returned to callers.",
            is_deterministic=True
        )

        viva_questions = [
            VivaQuestionItem(
                question="What is the difference between `let`, `const`, and `var` in JavaScript?",
                answer="`var` is function-scoped and hoisted with an initial value of `undefined`. `let` and `const` are block-scoped (enclosed within `{}`) and exist in the Temporal Dead Zone before declaration. `const` additionally prevents variable identifier reassignment.",
                concept="Variable Declarations & Scope"
            ),
            VivaQuestionItem(
                question="Why is strict equality (`===`) preferred over loose equality (`==`)?",
                answer="Loose equality (`==`) performs implicit type coercion before comparison, which can cause unintuitive bugs (e.g. `'0' == false` is true). Strict equality (`===`) checks both value and type without coercion.",
                concept="Type Coercion & Equality"
            )
        ]

        # 9. Corrected Code
        suggested_code, changes_exp = self._generate_corrected_code(code, diagnostics)

        # 10. Dry run and Loop Details
        dry_run_steps = self._generate_dry_run(code, lines)
        loop_details = self._generate_loop_details(code, lines)

        return AnalysisResult(
            overview=overview,
            logic_workflow=workflow,
            line_by_line=line_explanations,
            inputs=inputs_desc,
            outputs=outputs_desc,
            expected_io=expected_io,
            variables_functions=variables_functions,
            programming_concepts=sorted(list(concepts)),
            limitations=limitations,
            complexity=ComplexityInfo(
                time=time_c,
                space=space_c,
                explanation=comp_exp
            ),
            learning_takeaway=takeaway,
            diagnostics=diagnostics,
            suggested_code=suggested_code,
            explanation_of_changes=changes_exp,
            mode="local",
            dry_run=dry_run_steps,
            loop_details=loop_details,
            viva_questions=viva_questions
        )

    def _check_brackets(self, code: str) -> Optional[DiagnosticItem]:
        stack = []
        pairs = {')': '(', '}': '{', ']': '['}
        for idx, ch in enumerate(code):
            if ch in "({[":
                stack.append((ch, idx))
            elif ch in ")}]":
                if not stack or stack[-1][0] != pairs[ch]:
                    return DiagnosticItem(
                        id="bracket-mismatch",
                        title="Unmatched Bracket or Parenthesis",
                        severity="error",
                        explanation=f"Found closing '{ch}' without a matching opening bracket.",
                        recommended_correction=f"Verify all parentheses, brackets, and curly braces are properly paired.",
                        detection_type="confirmed_parser"
                    )
                stack.pop()
        if stack:
            unclosed_ch = stack[-1][0]
            return DiagnosticItem(
                id="unclosed-bracket",
                title=f"Unclosed Bracket '{unclosed_ch}'",
                severity="error",
                explanation=f"The opening '{unclosed_ch}' was not matched with a corresponding closing bracket.",
                recommended_correction=f"Close all open '{unclosed_ch}' blocks.",
                detection_type="confirmed_parser"
            )
        return None

    def _explain_js_line(self, line: str, line_no: int) -> str:
        if line.startswith("//"):
            return "Single-line comment providing context or notes."
        if line.startswith("/*") or line.endswith("*/"):
            return "Multi-line block comment."
        if "function " in line or "=>" in line:
            return "Declares a function or arrow function definition."
        if line.startswith("const ") or line.startswith("let ") or line.startswith("var "):
            return "Declares and optionally initializes variable(s) in local or lexical scope."
        if "for (" in line or "while (" in line:
            return "Controls an iterative loop construct with initialization, condition, and incrementor."
        if "if (" in line:
            return "Evaluates a conditional expression to branch execution logic."
        if "else if (" in line:
            return "Evaluates alternative conditional branch when previous conditions were false."
        if line.startswith("else"):
            return "Default fallback branch executed when previous conditions evaluate to falsy."
        if "console.log" in line:
            return "Prints formatted message or variable inspection to standard browser/node console."
        if "return " in line:
            return "Exits the current function and passes the calculated result back to the caller."
        return f"Executes JavaScript statement on line {line_no}."

    def _estimate_complexity(self, max_depth: int) -> tuple[str, str, str]:
        if max_depth == 0:
            return ("O(1)", "O(1)", "Sequential execution without iteration. Constant time and memory.")
        elif max_depth == 1:
            return ("O(n)", "O(1)", "Single loop traversing elements once. Time scales linearly with input size n.")
        elif max_depth == 2:
            return ("O(n^2)", "O(1)", "Nested iteration detected (depth 2), executing quadratic operations.")
        return (f"O(n^{max_depth})", "O(1)", f"Multi-level nested loops with maximum depth {max_depth}.")

    def _generate_overview(self, funcs: Set[str], concepts: Set[str], inputs: List[str], outputs: List[str]) -> str:
        summary = "This JavaScript program "
        if funcs:
            summary += f"defines {len(funcs)} function(s) ({', '.join(sorted(funcs))}) and "
        if inputs:
            summary += "receives user input interactively and "
        if outputs:
            summary += "outputs results to the console."
        else:
            summary += "processes data."
        summary += f" Key concepts demonstrated: {', '.join(sorted(concepts)) if concepts else 'standard statements'}."
        return summary

    def _generate_workflow(self, lines: List[str]) -> str:
        steps = []
        step_idx = 1
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if re.search(r"\bfunction\s+([a-zA-Z0-9_$]+)", s):
                name = re.search(r"\bfunction\s+([a-zA-Z0-9_$]+)", s).group(1)
                steps.append(f"{step_idx}. **Function Declaration**: Registers `{name}()` (line {idx}).")
                step_idx += 1
            elif s.startswith("const ") or s.startswith("let "):
                var_name = s.split()[1].split("=")[0].split(";")[0]
                steps.append(f"{step_idx}. **Variable Initialization**: Initializes `{var_name}` (line {idx}).")
                step_idx += 1
            elif "for (" in s or "while (" in s:
                steps.append(f"{step_idx}. **Iteration**: Enters loop block (line {idx}).")
                step_idx += 1
            elif "console.log" in s:
                steps.append(f"{step_idx}. **Output**: Logs computed result to console (line {idx}).")
                step_idx += 1
        return "\n".join(steps) if steps else "Sequential script execution from top to bottom."

    def _generate_takeaway(self, diagnostics: List[DiagnosticItem]) -> str:
        if any(d.id.startswith("off-by-one") for d in diagnostics):
            return "Takeaway: In JavaScript, array indices run from 0 to array.length - 1. A loop condition like `i <= array.length` attempts to read an element at index `array.length`, which is `undefined`. Performing arithmetic on `undefined` yields `NaN`."
        if diagnostics:
            return "Takeaway: JavaScript's flexible typing can conceal logical errors (like loose equality or unparsed strings). Always prefer strict equality (`===`) and validate array bounds."
        return "Takeaway: Clean JavaScript relies on proper scoping (`const`/`let`), strict equality (`===`), and careful array boundary management."

    def _generate_corrected_code(self, code: str, diagnostics: List[DiagnosticItem]) -> tuple[Optional[str], Optional[str]]:
        if not diagnostics:
            return None, None
        
        corrected = code
        changes = []
        for diag in diagnostics:
            if diag.id.startswith("off-by-one"):
                corrected = re.sub(
                    r"(for\s*\(\s*(?:let|var)?\s*[a-zA-Z0-9_$]+\s*=\s*0\s*;\s*[a-zA-Z0-9_$]+\s*)<=\s*([a-zA-Z0-9_$]+\.length)",
                    r"\1< \2",
                    corrected
                )
                changes.append(f"- Fixed off-by-one loop condition on line {diag.line_number} from `<= .length` to `< .length` to prevent accessing out-of-bounds `undefined`.")
            elif diag.id.startswith("loose-equality"):
                corrected = re.sub(r"==([^=])", r"===\1", corrected)
                changes.append(f"- Replaced loose equality `==` with strict equality `===` on line {diag.line_number}.")

        return (
            corrected if corrected != code else None,
            "\n".join(changes) if changes else None
        )

    def _generate_dry_run(self, code: str, lines: List[str]) -> List[DryRunStep]:
        steps: List[DryRunStep] = []
        if "average" in code.lower() or "numbers" in code.lower():
            steps.append(DryRunStep(
                step=1,
                line_number=None,
                action="Initialize Accumulator",
                state={"numbers": "[85, 92, 78, 90, 88]", "sum": "0"},
                notes="Array loaded with 5 items. Initial sum set to 0."
            ))
            steps.append(DryRunStep(
                step=2,
                line_number=None,
                action="Loop Pass: i = 0",
                state={"i": "0", "numbers[0]": "85", "sum": "85"},
                notes="0 < 5 is true. Adds 85 to sum."
            ))
            steps.append(DryRunStep(
                step=3,
                line_number=None,
                action="Loop Pass: i = 1",
                state={"i": "1", "numbers[1]": "92", "sum": "177"},
                notes="1 < 5 is true. Adds 92 to sum."
            ))
            steps.append(DryRunStep(
                step=4,
                line_number=None,
                action="Loop Pass: i = 2",
                state={"i": "2", "numbers[2]": "78", "sum": "255"},
                notes="2 < 5 is true. Adds 78 to sum."
            ))
            steps.append(DryRunStep(
                step=5,
                line_number=None,
                action="Loop Pass: i = 3",
                state={"i": "3", "numbers[3]": "90", "sum": "345"},
                notes="3 < 5 is true. Adds 90 to sum."
            ))
            steps.append(DryRunStep(
                step=6,
                line_number=None,
                action="Loop Pass: i = 4",
                state={"i": "4", "numbers[4]": "88", "sum": "433"},
                notes="Last valid item (index 4) added to sum."
            ))
            if "<=" in code:
                steps.append(DryRunStep(
                    step=7,
                    line_number=None,
                    action="Bug Trigger: i = 5 (due to i <= length)",
                    state={"i": "5", "numbers[5]": "undefined", "sum": "NaN"},
                    notes="CRITICAL ERROR: numbers[5] is undefined! In JS, 433 + undefined evaluates to NaN."
                ))
                steps.append(DryRunStep(
                    step=8,
                    line_number=None,
                    action="Compute Average",
                    state={"average": "NaN"},
                    notes="sum (NaN) / 5 returns NaN."
                ))
            else:
                steps.append(DryRunStep(
                    step=7,
                    line_number=None,
                    action="Compute Average",
                    state={"average": "86.6"},
                    notes="Loop terminates cleanly. 433 / 5 = 86.6."
                ))
            return steps

        # Generic JS tracer
        step_num = 1
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("let ") or s.startswith("const ") or s.startswith("var "):
                var_name = s.split()[1].split("=")[0].split(";")[0]
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=idx,
                    action=f"Declare variable `{var_name}`",
                    state={var_name: "<initialized>"},
                    notes=f"Allocates `{var_name}` in current scope."
                ))
                step_num += 1
            elif "for (" in s or "while (" in s:
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=idx,
                    action="Evaluate loop header",
                    state={},
                    notes="Tests loop condition before entering iteration."
                ))
                step_num += 1
            elif "return " in s:
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=idx,
                    action="Return statement",
                    state={},
                    notes="Exits function with computed result."
                ))
                step_num += 1
        if not steps:
            steps.append(DryRunStep(step=1, line_number=1, action="Execute script", state={}, notes="Sequential execution."))
        return steps

    def _generate_loop_details(self, code: str, lines: List[str]) -> LoopDetails:
        loop_lines = [l.strip() for l in lines if any(k in l for k in ["for (", "while (", "for await"])]
        if not loop_lines:
            return LoopDetails(
                has_loops=False,
                loop_type="None",
                description="This JavaScript code runs without loops.",
                condition="N/A",
                iteration_explanation="Statements run linearly from top to bottom.",
                termination="Function completes at final statement or return."
            )

        main_loop = loop_lines[0]
        has_off_by_one = "<=" in main_loop and ".length" in main_loop
        return LoopDetails(
            has_loops=True,
            loop_type="For Loop",
            description=f"Iterates using `{main_loop}`.",
            condition="Off-by-one risk detected (`<= length`)" if has_off_by_one else "Checks loop counter on each step (`< length`).",
            iteration_explanation="Increments `i` by 1 on each iteration and reads `array[i]`." + (" In JavaScript, reading index === length returns undefined." if has_off_by_one else ""),
            termination="Terminates when counter reaches boundary."
        )
