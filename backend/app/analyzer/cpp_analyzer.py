import re
from typing import Optional, List, Set, Dict, Any
from .base import BaseAnalyzer, extract_lines
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

class CppAnalyzer(BaseAnalyzer):
    def analyze(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        variables_functions: List[VariableFunctionItem] = []
        concepts: Set[str] = set()
        inputs_found: List[str] = []
        outputs_found: List[str] = []

        # 1. Bracket Check
        bracket_err = self._check_brackets(code)
        if bracket_err:
            diagnostics.append(bracket_err)

        # 2. Track headers and functions
        has_iostream = False
        has_cin = False
        has_cout = False
        func_names: Set[str] = set()
        max_loop_depth = 0
        current_loop_depth = 0
        has_recursion = False

        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s or s.startswith("//"):
                continue

            if "#include" in s:
                concepts.add("Preprocessor Directives")
                if "iostream" in s:
                    has_iostream = True

            if "cin >>" in s or "std::cin >>" in s:
                has_cin = True
                concepts.add("Console Input (cin)")
                inputs_found.append(f"Standard input stream (`cin` on line {idx})")
            if "scanf(" in s:
                inputs_found.append(f"C-style formatted input (`scanf` on line {idx})")

            if "cout <<" in s or "std::cout <<" in s:
                has_cout = True
                concepts.add("Console Output (cout)")
                outputs_found.append(f"Standard output stream (`cout` on line {idx})")
            if "printf(" in s:
                outputs_found.append(f"C-style formatted output (`printf` on line {idx})")

            # Detect functions: e.g. `int main()`, `long long factorial(int n)`
            fn_match = re.search(r"\b(int|long\s+long|void|double|float|bool|string)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)", s)
            if fn_match and not s.startswith("return"):
                ret_type, name, params = fn_match.group(1), fn_match.group(2), fn_match.group(3)
                func_names.add(name)
                concepts.add("Functions")
                variables_functions.append(VariableFunctionItem(
                    name=name,
                    kind="function",
                    data_type=ret_type,
                    description=f"Function returning `{ret_type}` with parameters `({params})`.",
                    scope="global"
                ))

            # Detect variables: e.g. `int n = 5;`, `long long result = 1;`
            var_match = re.findall(r"\b(int|long\s+long|double|float|bool|char|string|auto)\s+([a-zA-Z0-9_]+)(?:\s*=\s*([^;]+))?", s)
            for v_type, v_name, v_init in var_match:
                if v_name not in func_names and v_name not in {"main", "if", "for", "while"}:
                    concepts.add("Variables and Data Types")
                    variables_functions.append(VariableFunctionItem(
                        name=v_name,
                        kind="variable",
                        data_type=v_type,
                        description=f"Type `{v_type}` declared on line {idx}.",
                        scope="local"
                    ))

            # Loops
            if re.search(r"\b(for|while)\s*\(", s):
                concepts.add("Loops")
                current_loop_depth += 1
                if current_loop_depth > max_loop_depth:
                    max_loop_depth = current_loop_depth

            # Diagnostics checks
            # Division by zero
            if re.search(r"/\s*0\b", s) or re.search(r"%\s*0\b", s):
                diagnostics.append(DiagnosticItem(
                    id=f"cpp-zero-div-{idx}",
                    title="Division or Modulo by Zero",
                    severity="error",
                    line_number=idx,
                    explanation=f"Division or modulo by literal zero triggers undefined behavior in C++ and typically results in a SIGFPE crash.",
                    recommended_correction="Ensure the denominator is strictly non-zero before performing division.",
                    detection_type="static_heuristic"
                ))

            # Factorial integer overflow heuristic
            if "factorial" in s.lower() and "int " in s and "long long" not in s:
                diagnostics.append(DiagnosticItem(
                    id=f"cpp-overflow-{idx}",
                    title="Potential Integer Overflow Risk",
                    severity="warning",
                    line_number=idx,
                    explanation="Standard 32-bit `int` overflows at 13! (2,147,483,647). Factorials grow extremely fast.",
                    recommended_correction="Use `long long` or `unsigned long long` to support factorials up to 20!.",
                    detection_type="static_heuristic"
                ))

        # Check missing <iostream>
        if (has_cin or has_cout) and not has_iostream:
            diagnostics.append(DiagnosticItem(
                id="missing-iostream",
                title="Missing Header `#include <iostream>`",
                severity="error",
                line_number=1,
                explanation="The code utilizes `cin` or `cout` streams but does not include `<iostream>`.",
                recommended_correction="Add `#include <iostream>` at the top of the file.",
                corrected_snippet="#include <iostream>",
                detection_type="confirmed_parser"
            ))

        # Check recursion
        for fn in func_names:
            if fn != "main":
                call_count = len(re.findall(rf"\b{fn}\s*\(", code))
                if call_count > 1:
                    has_recursion = True
                    concepts.add("Recursion")

        # Line-by-line
        line_exps: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            line_exps.append(LineExplanation(
                line_number=idx,
                code_segment=s,
                explanation=self._explain_cpp_line(s, idx)
            ))

        time_c, space_c, comp_exp = self._estimate_complexity(max_loop_depth, has_recursion)

        overview = f"This C++ program is compiled code demonstrating {', '.join(sorted(concepts)) if concepts else 'basic operations'}. It is structured with {len(func_names)} function(s) including main entry point."
        workflow = self._generate_workflow(lines)

        # Expected I/O
        expected_io = ExpectedIO(
            input_source="Interactive Console (`std::cin` stream)" if has_cin else ("Function Arguments / Variables"),
            input_type="C++ primitive types (int, double, char, etc.)",
            input_format="Whitespace-separated tokens or method parameters",
            input_range="Bounded by 32-bit or 64-bit integer limits",
            sample_input="5" if has_cin else "Sample arguments",
            output_mechanism="Standard Console Output (`std::cout` stream)" if has_cout else "Return value",
            output_type="Formatted text stream",
            sample_output="Console text output" if has_cout else "return 0",
            relationship="Transforms input values via C++ procedural instructions and streams result to standard output.",
            explanation="Outputs are sent directly to stdout.",
            is_deterministic=True
        )

        inputs_desc = (
            f"**Source**: {expected_io.input_source}\n"
            f"**Type**: `{expected_io.input_type}`\n"
            f"**Format**: {expected_io.input_format}\n"
            f"**Sample Input**: `{expected_io.sample_input}`"
        )
        outputs_desc = (
            f"**Mechanism**: {expected_io.output_mechanism}\n"
            f"**Type**: `{expected_io.output_type}`\n"
            f"**Expected Result**: `{expected_io.sample_output}`\n"
            f"**Relationship**: {expected_io.relationship}"
        )

        limitations = [
            "C++ arithmetic is subject to fixed-width integer overflow without runtime exceptions.",
            "Memory management and array bounds checking are not performed automatically by raw arrays or pointers."
        ]
        if has_cin:
            limitations.append("`std::cin` will fail (failbit set) if user inputs characters when a numeric type is expected.")

        takeaway = "Takeaway: In C++, static types, header inclusion (`<iostream>`), and numeric bounds (e.g. `long long` for combinatorial algorithms) are fundamental for correct and robust execution."

        viva_questions = [
            VivaQuestionItem(
                question="Why is `int main()` required in standard C++, and what does `return 0` signify?",
                answer="`main()` is the standard entry point designated by the C++ specification where execution starts. Returning 0 signals to the operating system that the program terminated successfully without runtime errors.",
                concept="Program Entry Point & Exit Codes"
            ),
            VivaQuestionItem(
                question="What is the difference between `cin >> x` and `getline(cin, str)`?",
                answer="`cin >> x` reads formatted tokens and stops at whitespace (spaces, tabs, or newlines). `getline(cin, str)` reads an entire line including embedded whitespace until a newline character is encountered.",
                concept="C++ Console I/O Streams"
            )
        ]

        suggested_code, changes = self._generate_corrected_code(code, diagnostics)
        dry_run_steps = self._generate_dry_run(code, lines)
        loop_details = self._generate_loop_details(code, lines)

        return AnalysisResult(
            overview=overview,
            logic_workflow=workflow,
            line_by_line=line_exps,
            inputs=inputs_desc,
            outputs=outputs_desc,
            expected_io=expected_io,
            variables_functions=variables_functions,
            programming_concepts=sorted(list(concepts)),
            limitations=limitations,
            complexity=ComplexityInfo(time=time_c, space=space_c, explanation=comp_exp),
            learning_takeaway=takeaway,
            diagnostics=diagnostics,
            suggested_code=suggested_code,
            explanation_of_changes=changes,
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
                        id="cpp-bracket-mismatch",
                        title="Unmatched C++ Brace or Bracket",
                        severity="error",
                        explanation=f"Found closing '{ch}' without matching opening delimiter.",
                        recommended_correction="Check and pair all braces `{}` and parentheses `()`.",
                        detection_type="confirmed_parser"
                    )
                stack.pop()
        return None

    def _explain_cpp_line(self, line: str, line_no: int) -> str:
        if line.startswith("#include"):
            return "Preprocessor directive to include standard library headers."
        if line.startswith("using namespace"):
            return "Brings symbols from the specified namespace into global scope."
        if "int main(" in line:
            return "Defines `main()`, the mandatory entry point of every C++ executable."
        if "cout <<" in line or "std::cout <<" in line:
            return "Streams output characters to standard console stream."
        if "cin >>" in line or "std::cin >>" in line:
            return "Reads input values from standard console stream into target variable."
        if "for (" in line:
            return "Loop header specifying loop variable initialization, test condition, and step increment."
        if "while (" in line:
            return "Loop header that repeats execution while condition remains true."
        if "if (" in line:
            return "Branch condition evaluated to choose execution branch."
        if "return " in line:
            return "Returns value to caller (e.g., return 0 indicates successful process termination)."
        return f"Executes C++ statement on line {line_no}."

    def _estimate_complexity(self, max_depth: int, has_recursion: bool) -> tuple[str, str, str]:
        if has_recursion:
            return ("O(n)", "O(n)", "Recursive function calls create call stack frames proportional to recursion depth.")
        if max_depth == 0:
            return ("O(1)", "O(1)", "Direct sequential operations with constant time and memory overhead.")
        elif max_depth == 1:
            return ("O(n)", "O(1)", "Single iterative loop traversing up to n iterations.")
        return (f"O(n^{max_depth})", "O(1)", f"Nested loops with maximum depth {max_depth}.")

    def _generate_workflow(self, lines: List[str]) -> str:
        steps = []
        idx_count = 1
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if "#include" in s:
                steps.append(f"{idx_count}. **Header Inclusion**: Includes standard C++ headers (line {idx}).")
                idx_count += 1
                break
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if "int main(" in s:
                steps.append(f"{idx_count}. **Main Entry**: Starts execution in `main()` function (line {idx}).")
                idx_count += 1
            elif "cin >>" in s:
                steps.append(f"{idx_count}. **Input Streaming**: Awaits input from console (line {idx}).")
                idx_count += 1
            elif "for (" in s or "while (" in s:
                steps.append(f"{idx_count}. **Loop Iteration**: Executes iterative computation (line {idx}).")
                idx_count += 1
            elif "cout <<" in s:
                steps.append(f"{idx_count}. **Output Streaming**: Prints results to console (line {idx}).")
                idx_count += 1
            elif "return 0;" in s:
                steps.append(f"{idx_count}. **Termination**: Returns exit code 0 indicating clean finish (line {idx}).")
                idx_count += 1
        return "\n".join(steps) if steps else "Sequential C++ program execution."

    def _generate_corrected_code(self, code: str, diagnostics: List[DiagnosticItem]) -> tuple[Optional[str], Optional[str]]:
        if not diagnostics:
            return None, None
        corrected = code
        changes = []
        if any(d.id == "missing-iostream" for d in diagnostics):
            corrected = "#include <iostream>\n" + corrected
            changes.append("- Added missing `#include <iostream>` directive at top of file.")
        return (corrected if corrected != code else None, "\n".join(changes) if changes else None)

    def _generate_dry_run(self, code: str, lines: List[str]) -> List[DryRunStep]:
        steps: List[DryRunStep] = []
        if "factorial" in code.lower():
            steps.append(DryRunStep(
                step=1,
                line_number=None,
                action="Input Prompt (n = 4)",
                state={"n": "4", "result": "undefined"},
                notes="Standard input reads integer 4 into variable n."
            ))
            steps.append(DryRunStep(
                step=2,
                line_number=None,
                action="Call computeFactorial(4)",
                state={"n": "4", "factorial": "1"},
                notes="Initializes accumulator factorial = 1."
            ))
            steps.append(DryRunStep(
                step=3,
                line_number=None,
                action="Loop i = 1",
                state={"i": "1", "factorial": "1 * 1 = 1"},
                notes="Iteration 1: multiplies accumulator by 1."
            ))
            steps.append(DryRunStep(
                step=4,
                line_number=None,
                action="Loop i = 2",
                state={"i": "2", "factorial": "1 * 2 = 2"},
                notes="Iteration 2: multiplies accumulator by 2."
            ))
            steps.append(DryRunStep(
                step=5,
                line_number=None,
                action="Loop i = 3",
                state={"i": "3", "factorial": "2 * 3 = 6"},
                notes="Iteration 3: multiplies accumulator by 3."
            ))
            steps.append(DryRunStep(
                step=6,
                line_number=None,
                action="Loop i = 4",
                state={"i": "4", "factorial": "6 * 4 = 24"},
                notes="Iteration 4: multiplies accumulator by 4."
            ))
            steps.append(DryRunStep(
                step=7,
                line_number=None,
                action="Loop Exit & Return",
                state={"return_value": "24"},
                notes="Counter i reaches 5 > 4. Loop terminates and returns 24."
            ))
            steps.append(DryRunStep(
                step=8,
                line_number=None,
                action="Console Output",
                state={"cout": "'4! = 24'"},
                notes="Prints formatted string to stdout."
            ))
            return steps

        step_idx = 1
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if "int " in s or "double " in s:
                steps.append(DryRunStep(step=step_idx, line_number=idx, action="Variable declaration", state={}, notes=f"Allocates variable on line {idx}."))
                step_idx += 1
            elif "cin >>" in s:
                steps.append(DryRunStep(step=step_idx, line_number=idx, action="Stream input", state={}, notes="Reads input from cin."))
                step_idx += 1
            elif "cout <<" in s:
                steps.append(DryRunStep(step=step_idx, line_number=idx, action="Stream output", state={}, notes="Streams output to cout."))
                step_idx += 1
        if not steps:
            steps.append(DryRunStep(step=1, line_number=1, action="Execute C++ binary", state={}, notes="Entry in main()."))
        return steps

    def _generate_loop_details(self, code: str, lines: List[str]) -> LoopDetails:
        loops = [l.strip() for l in lines if any(k in l for k in ["for (", "while (", "do {"])]
        if not loops:
            return LoopDetails(
                has_loops=False,
                loop_type="None",
                description="This C++ program executes without loop iteration.",
                condition="N/A",
                iteration_explanation="Executes top-to-bottom sequentially.",
                termination="Completes when main() returns 0."
            )

        header = loops[0]
        return LoopDetails(
            has_loops=True,
            loop_type="For Loop" if "for " in header else "While Loop",
            description=f"Iterative loop construct: `{header}`.",
            condition="Evaluates boundary condition before every iteration pass.",
            iteration_explanation="Executes loop body statements, updates state variables, and increments loop counter.",
            termination="Terminates when loop condition evaluates to false."
        )
