import ast
import re
from typing import Optional, List, Dict, Any, Set
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

class PythonAnalyzer(BaseAnalyzer):
    def analyze(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        
        # 1. Check for Syntax Errors via AST Parser
        try:
            tree = ast.parse(code)
        except SyntaxError as syn_err:
            return self._handle_syntax_error(code, lines, syn_err)
        except Exception as exc:
            return self._handle_generic_parse_error(code, lines, str(exc))

        # 2. Extract AST details
        diagnostics: List[DiagnosticItem] = []
        variables_functions: List[VariableFunctionItem] = []
        concepts: Set[str] = set()
        inputs_found: List[str] = []
        outputs_found: List[str] = []
        
        # Track defined functions and calls for recursion detection
        functions_defined: Dict[str, ast.FunctionDef] = {}
        function_calls: Dict[str, Set[str]] = {}
        current_func: Optional[str] = None
        
        loop_depth = 0
        max_loop_depth = 0
        has_recursion = False

        # Static checks state
        has_input_call = False
        has_input_inside_try = False
        in_try_block = False

        class CodeVisitor(ast.NodeVisitor):
            def __init__(self, outer):
                self.outer = outer
                self.current_func = None
                self.current_loop_depth = 0

            def visit_FunctionDef(self, node: ast.FunctionDef):
                concepts.add("Functions")
                functions_defined[node.name] = node
                function_calls[node.name] = set()
                
                # Check for recursion or mutable defaults
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        diagnostics.append(DiagnosticItem(
                            id=f"mutable-default-{node.lineno}",
                            title="Mutable Default Argument",
                            severity="warning",
                            line_number=node.lineno,
                            explanation=f"Function '{node.name}' uses a mutable default argument ({type(default).__name__.lower()}). In Python, default arguments are evaluated once at definition time, sharing state across invocations.",
                            recommended_correction="Use None as default argument and initialize the mutable object inside the function body.",
                            corrected_snippet=f"def {node.name}(..., param=None):\n    if param is None:\n        param = []",
                            detection_type="static_heuristic"
                        ))

                # Extract parameters
                params = [arg.arg for arg in node.args.args]
                param_str = f"({', '.join(params)})" if params else "()"
                doc = ast.get_docstring(node)
                desc = f"Function accepting {', '.join(params) if params else 'no arguments'}"
                if doc:
                    desc += f". Docstring: '{doc[:60]}...'" if len(doc) > 60 else f". Docstring: '{doc}'"

                variables_functions.append(VariableFunctionItem(
                    name=node.name,
                    kind="function",
                    data_type="function",
                    description=desc + f" {param_str}",
                    scope="module"
                ))

                prev_func = self.current_func
                self.current_func = node.name
                self.generic_visit(node)
                self.current_func = prev_func

            def visit_ClassDef(self, node: ast.ClassDef):
                concepts.add("Object-Oriented Programming (Classes)")
                variables_functions.append(VariableFunctionItem(
                    name=node.name,
                    kind="class",
                    data_type="type",
                    description=f"Class definition with {len(node.body)} members.",
                    scope="module"
                ))
                self.generic_visit(node)

            def visit_For(self, node: ast.For):
                nonlocal max_loop_depth
                concepts.add("For Loops")
                self.current_loop_depth += 1
                if self.current_loop_depth > max_loop_depth:
                    max_loop_depth = self.current_loop_depth
                self.generic_visit(node)
                self.current_loop_depth -= 1

            def visit_While(self, node: ast.While):
                nonlocal max_loop_depth
                concepts.add("While Loops")
                self.current_loop_depth += 1
                if self.current_loop_depth > max_loop_depth:
                    max_loop_depth = self.current_loop_depth
                
                # Check for infinite loop while True without break
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        diagnostics.append(DiagnosticItem(
                            id=f"infinite-loop-{node.lineno}",
                            title="Potential Infinite Loop",
                            severity="warning",
                            line_number=node.lineno,
                            explanation="Detected 'while True' loop with no explicit 'break' statement within its immediate block. This may run indefinitely.",
                            recommended_correction="Ensure there is a break condition or terminate based on user input or state change.",
                            detection_type="static_heuristic"
                        ))
                self.generic_visit(node)
                self.current_loop_depth -= 1

            def visit_If(self, node: ast.If):
                concepts.add("Conditional Branching (if/else)")
                self.generic_visit(node)

            def visit_Try(self, node: ast.Try):
                concepts.add("Exception Handling (try/except)")
                nonlocal in_try_block
                in_try_block = True
                
                # Check for bare except:
                for handler in node.handlers:
                    if handler.type is None:
                        diagnostics.append(DiagnosticItem(
                            id=f"bare-except-{handler.lineno}",
                            title="Bare Except Clause",
                            severity="warning",
                            line_number=handler.lineno,
                            explanation="Using bare 'except:' catches all exceptions, including KeyboardInterrupt and SystemExit, hiding critical issues.",
                            recommended_correction="Catch specific exceptions, e.g., 'except ValueError:' or 'except Exception:'.",
                            detection_type="static_heuristic"
                        ))
                self.generic_visit(node)
                in_try_block = False

            def visit_Assign(self, node: ast.Assign):
                concepts.add("Variable Assignment")
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        val_type = "unknown"
                        type_desc = "value"
                        if isinstance(node.value, ast.Constant):
                            val_type = type(node.value.value).__name__
                            type_desc = f"{val_type} literal ({repr(node.value.value)})"
                        elif isinstance(node.value, ast.List):
                            val_type = "list"
                            type_desc = "list collection"
                        elif isinstance(node.value, ast.Dict):
                            val_type = "dict"
                            type_desc = "dictionary collection"
                        elif isinstance(node.value, ast.Call):
                            func_id = getattr(node.value.func, "id", None)
                            if func_id in {"int", "float"}:
                                if node.value.args and isinstance(node.value.args[0], ast.Call) and getattr(node.value.args[0].func, "id", "") == "input":
                                    val_type = f"{func_id} (from user input)"
                                    type_desc = f"integer converted from console user input" if func_id == "int" else "floating-point number converted from user input"
                                else:
                                    val_type = func_id
                                    type_desc = f"{func_id} value"
                            elif func_id == "input":
                                val_type = "str (from user input)"
                                type_desc = "string read from console user input"
                            elif func_id == "str":
                                val_type = "str"
                                type_desc = "string value"
                            elif func_id and func_id in functions_defined:
                                val_type = f"return value of {func_id}()"
                                type_desc = f"value returned by function `{func_id}`"
                            else:
                                val_type = f"result of {func_id or 'function'}()"
                                type_desc = f"result of `{func_id or 'function'}()` call"
                        elif isinstance(node.value, ast.BinOp):
                            val_type = "computed numeric"
                            type_desc = "computed arithmetic result"

                        # Shadowing builtins check
                        if target.id in {"list", "dict", "str", "int", "float", "id", "type", "set", "max", "min"}:
                            diagnostics.append(DiagnosticItem(
                                id=f"shadow-builtin-{node.lineno}",
                                title="Shadowing Built-in Identifier",
                                severity="suggestion",
                                line_number=node.lineno,
                                explanation=f"Variable '{target.id}' shadows Python's built-in '{target.id}'. This overrides the built-in function/type in this scope.",
                                recommended_correction=f"Rename variable '{target.id}' to something more descriptive (e.g. '{target.id}_val' or 'item_{target.id}').",
                                detection_type="static_heuristic"
                            ))

                        variables_functions.append(VariableFunctionItem(
                            name=target.id,
                            kind="variable",
                            data_type=val_type,
                            description=f"Stores {type_desc} assigned on line {node.lineno}.",
                            scope=self.current_func or "module"
                        ))
                self.generic_visit(node)

            def visit_BinOp(self, node: ast.BinOp):
                if isinstance(node.op, ast.Mod):
                    concepts.add("Modulo Arithmetic (%)")
                elif isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Pow)):
                    concepts.add("Arithmetic Operations")

                # Check for division or modulo by literal zero
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    if isinstance(node.right, ast.Constant) and node.right.value == 0:
                        op_name = "Division" if isinstance(node.op, (ast.Div, ast.FloorDiv)) else "Modulo"
                        diagnostics.append(DiagnosticItem(
                            id=f"zero-div-{node.lineno}",
                            title=f"Definite {op_name} by Zero",
                            severity="error",
                            line_number=node.lineno,
                            explanation=f"A literal 0 is used as the divisor in a {op_name.lower()} operation on line {node.lineno}. This will raise a ZeroDivisionError at runtime.",
                            recommended_correction="Ensure the divisor is non-zero before performing the operation.",
                            detection_type="static_heuristic"
                        ))
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name:
                    if self.current_func:
                        function_calls[self.current_func].add(func_name)
                    
                    if func_name == "input":
                        nonlocal has_input_call
                        has_input_call = True
                        prompt_text = ""
                        if node.args and isinstance(node.args[0], ast.Constant):
                            prompt_text = f" with prompt: '{node.args[0].value}'"
                        inputs_found.append(f"Standard terminal input (`input()`{prompt_text} on line {node.lineno})")
                    
                    elif func_name == "print":
                        concepts.add("Console Output")
                        outputs_found.append(f"Standard console output (`print()` on line {node.lineno})")

                # Check if int(input()) or float(input()) is called outside a try/except block
                if isinstance(node.func, ast.Name) and node.func.id in {"int", "float"}:
                    if node.args and isinstance(node.args[0], ast.Call):
                        inner = node.args[0]
                        if isinstance(inner.func, ast.Name) and inner.func.id == "input":
                            if not in_try_block:
                                prompt_display = ""
                                if inner.args and isinstance(inner.args[0], ast.Constant):
                                    prompt_display = f" (prompt: '{inner.args[0].value}')"
                                diagnostics.append(DiagnosticItem(
                                    id=f"unhandled-input-conversion-{node.lineno}",
                                    title="Potential Input Risk: Unchecked User Input Conversion",
                                    severity="warning",
                                    line_number=node.lineno,
                                    explanation=(
                                        f"Direct conversion `{node.func.id}(input(...))` on line {node.lineno}{prompt_display} "
                                        f"executes normally with valid numeric input (such as 8 or 7), but poses a potential "
                                        f"runtime risk: entering non-numeric text (such as 'abc') will raise a ValueError."
                                    ),
                                    recommended_correction=(
                                        f"If you want to guard against non-numeric inputs, wrap the conversion in a "
                                        f"`try...except ValueError:` block."
                                    ),
                                    corrected_snippet=(
                                        f"try:\n    val = {node.func.id}(input(...))\nexcept ValueError:\n    print('Invalid input: please enter a valid number.')"
                                    ),
                                    detection_type="heuristic_warning"
                                ))

                self.generic_visit(node)

            def visit_Return(self, node: ast.Return):
                if self.current_func:
                    outputs_found.append(f"Return value from function `{self.current_func}` on line {node.lineno}")
                self.generic_visit(node)

        visitor = CodeVisitor(self)
        visitor.visit(tree)

        # Check for recursive calls
        for func_name, calls in function_calls.items():
            if func_name in calls:
                has_recursion = True
                concepts.add("Recursion")

        # 3. Formulate Line-by-Line explanations
        line_explanations: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                line_explanations.append(LineExplanation(
                    line_number=idx,
                    code_segment=stripped,
                    explanation="Comment providing documentation or context for the program."
                ))
            else:
                line_explanations.append(LineExplanation(
                    line_number=idx,
                    code_segment=stripped,
                    explanation=self._explain_python_line(stripped, idx, tree)
                ))

        # 4. Determine Complexity
        time_c, space_c, comp_exp = self._estimate_complexity(max_loop_depth, has_recursion)

        # 5. Formulate Overview & Logic Workflow
        overview = self._generate_overview(tree, functions_defined, concepts, has_input_call, outputs_found)
        workflow = self._generate_workflow(tree, lines)

        # 6. Inputs & Outputs descriptions and structured ExpectedIO
        expected_io = self._build_expected_io(tree, lines, code, has_input_call, outputs_found)
        inputs_desc = self._format_inputs_text(expected_io) if expected_io else ("\n".join(f"- {item}" for item in set(inputs_found)) if inputs_found else "No direct interactive inputs detected (operates on hardcoded variables or function arguments).")
        outputs_desc = self._format_outputs_text(expected_io) if expected_io else ("\n".join(f"- {item}" for item in set(outputs_found)) if outputs_found else "No direct console outputs or returns detected.")

        # 7. Limitations & Edge Cases
        limitations = self._determine_limitations(has_input_call, diagnostics, max_loop_depth, has_recursion)

        # 8. Learning Takeaway
        takeaway = self._generate_takeaway(concepts, diagnostics)

        # 9. Suggested Corrected Code if issues found
        suggested_code, changes_explanation = self._generate_suggestions(code, diagnostics)

        # 10. Dry Run & Loop Exploration
        dry_run_steps = self._generate_dry_run(tree, lines, code)
        loop_details = self._generate_loop_details(tree, lines)

        # 11. Viva Questions
        viva_questions = self._build_viva_questions(tree, concepts, has_input_call, diagnostics)

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
            explanation_of_changes=changes_explanation,
            mode="local",
            dry_run=dry_run_steps,
            loop_details=loop_details,
            viva_questions=viva_questions
        )

    def _handle_syntax_error(self, code: str, lines: List[str], err: SyntaxError) -> AnalysisResult:
        line_no = err.lineno or 1
        col_no = err.offset or 1
        snippet = get_code_snippet(lines, line_no)
        
        diagnostic = DiagnosticItem(
            id=f"syntax-error-{line_no}",
            title=f"Python Syntax Error: {err.msg}",
            severity="error",
            line_number=line_no,
            explanation=f"Python's syntax parser encountered an invalid token or structure on line {line_no}, column {col_no}: '{err.text.strip() if err.text else ''}'. Reason: {err.msg}.",
            recommended_correction="Verify correct indentation, matching colons, closed parentheses/brackets, or correct keywords.",
            corrected_snippet=snippet,
            detection_type="confirmed_parser"
        )

        return AnalysisResult(
            overview=f"The submitted Python code contains a syntax error on line {line_no} and cannot be executed or parsed into an abstract syntax tree.",
            logic_workflow=f"Parsing halted at line {line_no} due to invalid syntax: '{err.msg}'. No execution flow can occur until this syntax defect is resolved.",
            line_by_line=[LineExplanation(
                line_number=line_no,
                code_segment=lines[line_no - 1] if 0 < line_no <= len(lines) else "",
                explanation=f"Syntax Error: {err.msg}"
            )],
            inputs="Undetermined due to syntax error.",
            outputs="Undetermined due to syntax error.",
            variables_functions=[],
            programming_concepts=["Syntax Validation", "Parser Diagnostics"],
            limitations=["Code fails syntax validation and cannot run in a Python runtime environment."],
            complexity=ComplexityInfo(
                time="N/A",
                space="N/A",
                explanation="Cannot compute complexity for syntactically invalid code."
            ),
            learning_takeaway=f"In Python, proper syntax (including colons after statement headers and matching quotes/parentheses) is mandatory before code can be interpreted.",
            diagnostics=[diagnostic],
            suggested_code=None,
            explanation_of_changes=f"Fix the syntax error at line {line_no}: {err.msg}",
            mode="local"
        )

    def _handle_generic_parse_error(self, code: str, lines: List[str], msg: str) -> AnalysisResult:
        return AnalysisResult(
            overview=f"Could not parse Python code: {msg}",
            logic_workflow="Parsing failed.",
            line_by_line=[],
            inputs="Unknown",
            outputs="Unknown",
            variables_functions=[],
            programming_concepts=["Error Analysis"],
            limitations=["Code cannot be parsed."],
            complexity=ComplexityInfo(time="N/A", space="N/A", explanation="Parse failure."),
            learning_takeaway="Check code structure and encoding.",
            diagnostics=[DiagnosticItem(
                id="parse-failure",
                title="Code Parsing Failure",
                severity="error",
                explanation=msg,
                recommended_correction="Review submitted code for non-standard characters or severe structural corruption.",
                detection_type="confirmed_parser"
            )],
            suggested_code=None,
            mode="local"
        )

    def _explain_python_line(self, line: str, line_no: int, tree: ast.AST) -> str:
        stripped = line.strip()

        # Check for assignment with int(input(...)) or float(input(...))
        assign_num_input = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(int|float)\(input\((.*?)\)\)", stripped)
        if assign_num_input:
            var = assign_num_input.group(1)
            kind = "integer" if assign_num_input.group(2) == "int" else "floating-point number"
            prompt = assign_num_input.group(3).strip()
            prompt_desc = f" with prompt {prompt}" if prompt else ""
            return f"Prompts user for input{prompt_desc}, converts the entered string into an {kind}, and stores it in variable `{var}`."

        # Check for plain input assignment
        assign_input = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*input\((.*?)\)", stripped)
        if assign_input:
            var = assign_input.group(1)
            prompt = assign_input.group(2).strip()
            prompt_desc = f" with prompt {prompt}" if prompt else ""
            return f"Prompts user for terminal input{prompt_desc} and assigns the text to variable `{var}`."

        # Check if parity modulo check
        if re.match(r"^if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\s*2\s*==\s*0\s*:", stripped):
            match = re.match(r"^if\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\s*2\s*==\s*0\s*:", stripped)
            var = match.group(1)
            return f"Tests if `{var}` is divisible by 2 with remainder 0 to check if the number is even."

        # Check print
        print_match = re.match(r"^print\((.*?)\)", stripped)
        if print_match:
            args = print_match.group(1).strip()
            return f"Prints {args} to standard console output."

        if stripped == "else:":
            return "Fallback execution branch executed when the preceding condition evaluates to False."
        elif stripped.startswith("elif "):
            return f"Alternative conditional check evaluated if prior conditions were False: `{stripped[5:].rstrip(':')}`."
        elif stripped.startswith("if "):
            return f"Evaluates conditional expression `{stripped[3:].rstrip(':')}` to branch execution logic."
        elif stripped.startswith("def "):
            match = re.match(r"def\s+([a-zA-Z0-9_]+)\s*\((.*?)\):", stripped)
            if match:
                return f"Defines function `{match.group(1)}` with parameters `({match.group(2)})`."
            return "Declares a function definition."
        elif stripped.startswith("class "):
            return "Defines a new class construct."
        elif stripped.startswith("import ") or stripped.startswith("from "):
            return "Imports external module dependencies into the current script namespace."
        elif stripped.startswith("for "):
            return "Initializes an iterative loop iterating over a sequence or generator."
        elif stripped.startswith("while "):
            return "Repeats enclosed block as long as the loop condition remains truthy."
        elif stripped.startswith("try:"):
            return "Opens a protected execution block to catch and handle prospective runtime exceptions."
        elif stripped.startswith("except"):
            return f"Catches matching runtime exceptions raised within the guarded try block: `{stripped.rstrip(':')}`."
        elif stripped.startswith("return"):
            return "Terminates function execution and returns a value to the caller."
        elif "=" in stripped and not stripped.startswith("==") and "!=" not in stripped:
            parts = stripped.split("=", 1)
            return f"Assigns computed expression `{parts[1].strip()}` to target variable `{parts[0].strip()}`."
        return f"Executes Python statement on line {line_no}."

    def _estimate_complexity(self, max_depth: int, has_recursion: bool) -> tuple[str, str, str]:
        if has_recursion:
            return (
                "O(2^n) to O(n)",
                "O(n)",
                "The algorithm utilizes recursion. The call stack consumes O(n) auxiliary space proportional to recursion depth. Time complexity depends on whether subproblems branch (O(2^n)) or step linearly (O(n))."
            )
        if max_depth == 0:
            return (
                "O(1)",
                "O(1)",
                "The code executes sequentially with constant-time operations and no unbounded loops or recursive calls."
            )
        elif max_depth == 1:
            return (
                "O(n)",
                "O(1) to O(n)",
                "The program contains a single iteration loop that scales linearly with the size of the input sequence (n)."
            )
        elif max_depth == 2:
            return (
                "O(n^2)",
                "O(1)",
                "Nested loop structure detected with depth 2. For an input of size n, inner operations execute up to n * n times (quadratic complexity)."
            )
        else:
            return (
                f"O(n^{max_depth})",
                "O(1)",
                f"Polynomial complexity detected with maximum loop nesting depth of {max_depth}."
            )

    def _generate_overview(self, tree: ast.AST, funcs: Dict[str, Any], concepts: Set[str], has_input: bool, outputs: List[str]) -> str:
        # Check if it is a parity determination script
        has_modulo = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) for n in ast.walk(tree))
        has_even_odd = any(
            isinstance(n, ast.Constant) and isinstance(n.value, str) and ("even" in n.value.lower() or "odd" in n.value.lower())
            for n in ast.walk(tree)
        )
        if not funcs and has_input and has_modulo and has_even_odd:
            return (
                "This Python script prompts the user for numeric input via the console, converts it to an integer, "
                "and uses modulo arithmetic (`% 2`) within a conditional branch (`if/else`) to determine whether the "
                "entered number is even or odd, printing the result to standard output."
            )

        parts = []
        if funcs:
            func_names = ", ".join(f"`{k}`" for k in funcs.keys())
            parts.append(f"structured around {len(funcs)} declared function(s): {func_names}")
        else:
            parts.append("executes as a sequential top-level script")
        if has_input:
            parts.append("accepts interactive user input from the console")
        if has_modulo:
            parts.append("performs modulo arithmetic calculations")
        if outputs:
            parts.append("produces formatted console output")

        desc_core = "; ".join(parts) if parts else "performs direct sequential computation"
        return f"This Python program {desc_core}. Key programming concepts identified include {', '.join(sorted(concepts)) if concepts else 'basic sequential statements'}."

    def _generate_workflow(self, tree: ast.AST, lines: List[str]) -> str:
        steps = []
        step_idx = 1
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                steps.append(f"{step_idx}. **Module Imports**: Loads required Python libraries into module namespace (line {node.lineno}).")
                step_idx += 1
            elif isinstance(node, ast.FunctionDef):
                steps.append(f"{step_idx}. **Function Declaration**: Registers function `{node.name}` for subsequent invocation (lines {node.lineno}-{node.end_lineno or node.lineno}).")
                step_idx += 1
            elif isinstance(node, ast.ClassDef):
                steps.append(f"{step_idx}. **Class Declaration**: Registers class `{node.name}` (line {node.lineno}).")
                step_idx += 1
            elif isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                target_str = ", ".join(f"`{t}`" for t in targets) if targets else "variable"
                # Check if it is an int(input(...)) or input(...) call
                if isinstance(node.value, ast.Call):
                    f_id = getattr(node.value.func, "id", "")
                    if f_id in {"int", "float"} and node.value.args and isinstance(node.value.args[0], ast.Call) and getattr(node.value.args[0].func, "id", "") == "input":
                        num_type = "integer" if f_id == "int" else "float"
                        steps.append(f"{step_idx}. **User Input & Type Conversion**: Prompts for console input and converts the entered string to an {num_type}, assigning it to {target_str} (line {node.lineno}).")
                        step_idx += 1
                        continue
                    elif f_id == "input":
                        steps.append(f"{step_idx}. **User Input**: Prompts for console input and assigns the resulting string to {target_str} (line {node.lineno}).")
                        step_idx += 1
                        continue
                steps.append(f"{step_idx}. **Variable Assignment**: Computes and initializes {target_str} (line {node.lineno}).")
                step_idx += 1
            elif isinstance(node, ast.If):
                test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else "condition"
                has_prints_in_if = any(
                    isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call) and getattr(stmt.value.func, "id", "") == "print"
                    for stmt in node.body + node.orelse
                )
                if any(isinstance(op, ast.Mod) for op in ast.walk(node.test)):
                    steps.append(f"{step_idx}. **Conditional Parity Evaluation**: Evaluates condition `{test_str}` to test number divisibility. If True, executes the `if` block (lines {node.lineno}-{node.body[-1].lineno}); otherwise proceeds to the `else` block (line {node.orelse[0].lineno if node.orelse else node.lineno}).")
                else:
                    steps.append(f"{step_idx}. **Conditional Branch**: Evaluates condition `{test_str}` to select the execution path (lines {node.lineno}-{node.end_lineno or node.lineno}).")
                step_idx += 1

                if has_prints_in_if:
                    steps.append(f"{step_idx}. **Console Output**: Outputs the resulting formatted message to standard console stream (`stdout`).")
                    step_idx += 1
            elif isinstance(node, (ast.For, ast.While)):
                loop_type = "for-loop" if isinstance(node, ast.For) else "while-loop"
                steps.append(f"{step_idx}. **Iterative Execution**: Executes {loop_type} control block (lines {node.lineno}-{node.end_lineno or node.lineno}).")
                step_idx += 1
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                func_id = getattr(node.value.func, "id", "function")
                if func_id == "print":
                    steps.append(f"{step_idx}. **Console Output**: Formats and outputs message to standard output (line {node.lineno}).")
                else:
                    steps.append(f"{step_idx}. **Function Execution**: Invokes `{func_id}()` operation (line {node.lineno}).")
                step_idx += 1

        return "\n".join(steps) if steps else "Sequential line-by-line script execution."

    def _determine_limitations(self, has_input: bool, diagnostics: List[DiagnosticItem], loop_depth: int, has_recursion: bool) -> List[str]:
        limits = []
        if has_input:
            limits.append("Assumes valid numeric user input. The code executes normally for valid numbers (e.g. 8 or 7), but non-numeric input (such as 'abc') will trigger an uncaught ValueError during conversion unless guarded by try/except.")
        if any(d.severity == "error" for d in diagnostics):
            limits.append("Critical syntax or runtime errors detected that will halt execution if triggered.")
        if has_recursion:
            limits.append("Recursive algorithms are constrained by Python's default recursion depth limit (typically 1000 frames) and may fail with RecursionError on large inputs.")
        if loop_depth > 1:
            limits.append("Nested iteration may experience performance degradation on large datasets due to quadratic or higher time complexity.")
        if not limits:
            limits.append("Code operates reliably for standard nominal inputs within normal numeric limits.")
        return limits

    def _generate_takeaway(self, concepts: Set[str], diagnostics: List[DiagnosticItem]) -> str:
        if diagnostics:
            err_count = sum(1 for d in diagnostics if d.severity == "error")
            warn_count = sum(1 for d in diagnostics if d.severity == "warning")
            if err_count == 0 and warn_count > 0:
                return (
                    f"The code structure is sound and executes properly for valid inputs. "
                    f"However, {warn_count} advisory warning(s) were flagged (such as potential ValueError "
                    f"on non-numeric input) that can be handled defensively with exception handling."
                )
            return (
                f"This code demonstrates core concepts ({', '.join(list(concepts)[:3])}), "
                f"but contains {err_count} critical error(s) and {warn_count} warning(s). "
                f"Review the diagnostic recommendations to resolve errors and reinforce resilient error handling."
            )
        return "No syntax, runtime, or logic issues were detected. The program structure is clean, correct, and executes reliably."

    def _generate_suggestions(self, code: str, diagnostics: List[DiagnosticItem]) -> tuple[Optional[str], Optional[str]]:
        if not diagnostics:
            return None, None

        explanations = []
        has_unhandled_input = False

        for diag in diagnostics:
            explanations.append(f"- **Line {diag.line_number or 'N/A'}**: {diag.title} — {diag.recommended_correction}")
            if diag.id.startswith("unhandled-input-conversion"):
                has_unhandled_input = True

        corrected_code = code

        # Handle zero division if present
        if any(diag.id.startswith("zero-div") for diag in diagnostics):
            corrected_code = re.sub(r"/\s*0\b", "/ 1 # Corrected: Avoid division by zero", corrected_code)
            corrected_code = re.sub(r"%\s*0\b", "% 1 # Corrected: Avoid modulo by zero", corrected_code)

        # Proportional fix for unhandled input conversion: clean try...except ValueError:
        if has_unhandled_input and not re.search(r"^\s*try\s*:", code, re.MULTILINE):
            try:
                tree = ast.parse(code)
                input_lineno = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"int", "float"}:
                        if node.args and isinstance(node.args[0], ast.Call) and getattr(node.args[0].func, "id", "") == "input":
                            input_lineno = node.lineno
                            break

                if input_lineno is not None:
                    # Find top-level statement index corresponding to input_lineno
                    target_stmt_idx = 0
                    for idx, stmt in enumerate(tree.body):
                        if stmt.lineno <= input_lineno <= (stmt.end_lineno or stmt.lineno):
                            target_stmt_idx = idx
                            break

                    code_lines = code.split("\n")
                    split_line = tree.body[target_stmt_idx].lineno - 1
                    pre_lines = code_lines[:split_line]
                    post_lines = code_lines[split_line:]
                    indented_post = "\n".join("    " + l if l.strip() else "" for l in post_lines)

                    pre_text = "\n".join(pre_lines).rstrip()
                    if pre_text:
                        candidate = f"{pre_text}\n\ntry:\n{indented_post}\nexcept ValueError:\n    print(\"Invalid input: please enter a valid integer.\")"
                    else:
                        candidate = f"try:\n{indented_post}\nexcept ValueError:\n    print(\"Invalid input: please enter a valid integer.\")"

                    # Validate that candidate is syntactically valid
                    ast.parse(candidate)
                    corrected_code = candidate
            except Exception:
                pass

        if corrected_code != code:
            try:
                ast.parse(corrected_code)
                return corrected_code, "\n".join(explanations)
            except SyntaxError:
                return None, "\n".join(explanations)

        return None, "\n".join(explanations)

    def _generate_dry_run(self, tree: ast.AST, lines: List[str], code: str) -> List[DryRunStep]:
        steps: List[DryRunStep] = []

        # Check for top-level parity script: int(input(...)) followed by if modulo 2
        parity_assign = None
        parity_if = None
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                func_id = getattr(stmt.value.func, "id", "")
                if func_id in {"int", "float"} and stmt.value.args and isinstance(stmt.value.args[0], ast.Call) and getattr(stmt.value.args[0].func, "id", "") == "input":
                    parity_assign = stmt
            elif isinstance(stmt, ast.If) and parity_assign is not None:
                if isinstance(stmt.test, ast.Compare) and any(isinstance(op, ast.Mod) for op in ast.walk(stmt.test)):
                    parity_if = stmt
                    break

        if parity_assign and parity_if and not any(isinstance(s, ast.FunctionDef) for s in tree.body):
            var_name = parity_assign.targets[0].id if parity_assign.targets and isinstance(parity_assign.targets[0], ast.Name) else "number"
            prompt_val = "enter a number: "
            if parity_assign.value.args and parity_assign.value.args[0].args and isinstance(parity_assign.value.args[0].args[0], ast.Constant):
                prompt_val = str(parity_assign.value.args[0].args[0].value)

            even_msg = "the number is even"
            odd_msg = "the number is odd"
            even_line = parity_if.body[0].lineno if parity_if.body else parity_if.lineno + 1
            odd_line = parity_if.orelse[0].lineno if parity_if.orelse else None

            for node in parity_if.body:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "print":
                    if node.value.args and isinstance(node.value.args[0], ast.Constant):
                        even_msg = str(node.value.args[0].value)
            for node in parity_if.orelse:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "print":
                    if node.value.args and isinstance(node.value.args[0], ast.Constant):
                        odd_msg = str(node.value.args[0].value)

            return [
                DryRunStep(
                    step=1,
                    line_number=parity_assign.lineno,
                    action="User Input Prompt",
                    state={"prompt": f"'{prompt_val}'", "user_input": "'8'"},
                    notes="Pauses for user console input. Nominal example input: '8'."
                ),
                DryRunStep(
                    step=2,
                    line_number=parity_assign.lineno,
                    action="Type Conversion & Assignment",
                    state={var_name: 8},
                    notes=f"Converts string '8' to integer 8 and assigns to `{var_name}`. (Note: Non-numeric input like 'abc' would raise a ValueError here.)"
                ),
                DryRunStep(
                    step=3,
                    line_number=parity_if.lineno,
                    action=f"Conditional Parity Evaluation ({var_name} % 2 == 0)",
                    state={var_name: 8, "remainder": 0, "condition": True},
                    notes=f"Evaluates 8 % 2 == 0: 8 % 2 is 0 (0 == 0 is True). (Note: For odd input such as 7, 7 % 2 is 1 != 0, which evaluates to False.)"
                ),
                DryRunStep(
                    step=4,
                    line_number=even_line,
                    action="Execute If Branch (Console Output)",
                    state={var_name: 8, "output": f"'{even_msg}'"},
                    notes=f"Executes line {even_line} because the condition is True, printing '{even_msg}'. (For odd input like 7, line {odd_line or 'else'} executes printing '{odd_msg}'.)"
                )
            ]

        # Generic AST-derived step tracer
        step_num = 1
        curr_state = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=node.lineno,
                    action=f"Define function `{node.name}()`",
                    state=dict(curr_state),
                    notes=f"Function `{node.name}` registered in module namespace."
                ))
                step_num += 1
            elif isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                # Check if assign is from input
                if isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") in {"int", "float"}:
                    inner = node.value.args[0] if node.value.args and isinstance(node.value.args[0], ast.Call) else None
                    if inner and getattr(inner.func, "id", "") == "input":
                        for t in targets:
                            curr_state[t] = 8
                        steps.append(DryRunStep(
                            step=step_num,
                            line_number=node.lineno,
                            action=f"Input prompt & conversion for {', '.join(targets)}",
                            state=dict(curr_state),
                            notes=f"Reads user input and converts to number, storing in `{', '.join(targets)}`."
                        ))
                        step_num += 1
                        continue
                elif isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "input":
                    for t in targets:
                        curr_state[t] = "'user_text'"
                    steps.append(DryRunStep(
                        step=step_num,
                        line_number=node.lineno,
                        action=f"Read user input into {', '.join(targets)}",
                        state=dict(curr_state),
                        notes=f"Reads string from console input into `{', '.join(targets)}`."
                    ))
                    step_num += 1
                    continue

                for t in targets:
                    curr_state[t] = ast.unparse(node.value) if hasattr(ast, "unparse") else "<assigned>"
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=node.lineno,
                    action=f"Assign variable(s): {', '.join(targets)}",
                    state=dict(curr_state),
                    notes=f"Evaluates `{ast.unparse(node.value) if hasattr(ast, 'unparse') else 'expression'}` and assigns to `{', '.join(targets)}`."
                ))
                step_num += 1
            elif isinstance(node, (ast.For, ast.While)):
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=node.lineno,
                    action="Enter loop iteration",
                    state=dict(curr_state),
                    notes="Evaluates loop test condition and proceeds with iteration."
                ))
                step_num += 1
            elif isinstance(node, ast.If):
                steps.append(DryRunStep(
                    step=step_num,
                    line_number=node.lineno,
                    action=f"Evaluate condition: `{ast.unparse(node.test) if hasattr(ast, 'unparse') else 'if condition'}`",
                    state=dict(curr_state),
                    notes="Tests condition expression to choose execution branch."
                ))
                step_num += 1
            elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                func_name = getattr(node.value.func, "id", "function")
                if func_name == "print":
                    call_arg = ast.unparse(node.value.args[0]) if node.value.args and hasattr(ast, "unparse") else "''"
                    curr_state["output"] = call_arg
                    steps.append(DryRunStep(
                        step=step_num,
                        line_number=node.lineno,
                        action="Console Output",
                        state=dict(curr_state),
                        notes=f"Prints {call_arg} to standard terminal output."
                    ))
                else:
                    steps.append(DryRunStep(
                        step=step_num,
                        line_number=node.lineno,
                        action=f"Call function `{func_name}()`",
                        state=dict(curr_state),
                        notes=f"Executes call on line {node.lineno}."
                    ))
                step_num += 1

        if not steps:
            steps.append(DryRunStep(
                step=1,
                line_number=1,
                action="Program Execution",
                state={},
                notes="Program executes sequential statements from line 1."
            ))
        return steps

    def _generate_loop_details(self, tree: ast.AST, lines: List[str]) -> LoopDetails:
        loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
        if not loops:
            return LoopDetails(
                has_loops=False,
                loop_type="None",
                description="This program does not contain any loops. It executes sequentially without repetitive iteration.",
                condition="N/A",
                iteration_explanation="Statements execute once in linear top-to-bottom sequence.",
                termination="Completes upon executing the final statement or return."
            )

        loop_node = loops[0]
        if isinstance(loop_node, ast.For):
            target_var = getattr(loop_node.target, "id", "item")
            loop_line = lines[loop_node.lineno - 1].strip() if 0 < loop_node.lineno <= len(lines) else "for loop"
            return LoopDetails(
                has_loops=True,
                loop_type="For Loop",
                description=f"Iterates sequentially using `{loop_line}`.",
                condition=f"Loops as long as there are items left in the iterable sequence.",
                iteration_explanation=f"In each iteration, the variable `{target_var}` is assigned the next element in sequence, and the loop body executes.",
                termination=f"The loop cleanly terminates when all items in the sequence have been processed."
            )
        else:
            loop_line = lines[loop_node.lineno - 1].strip() if 0 < loop_node.lineno <= len(lines) else "while loop"
            return LoopDetails(
                has_loops=True,
                loop_type="While Loop",
                description=f"Repeats while condition remains truthy: `{loop_line}`.",
                condition="Evaluates the while condition before every pass.",
                iteration_explanation="If the condition is True, executes enclosed statements; then checks condition again.",
                termination="Terminates when the condition evaluates to False or a `break` statement is reached."
            )

    def _build_expected_io(self, tree: ast.AST, lines: List[str], code: str, has_input: bool, outputs: List[str]) -> Optional[ExpectedIO]:
        has_modulo = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) for n in ast.walk(tree))
        has_even_odd = any(
            isinstance(n, ast.Constant) and isinstance(n.value, str) and ("even" in n.value.lower() or "odd" in n.value.lower())
            for n in ast.walk(tree)
        )
        if has_input and has_modulo and has_even_odd:
            prompt_match = re.search(r'input\s*\(\s*["\'](.*?)["\']\s*\)', code)
            prompt_str = prompt_match.group(1) if prompt_match else "enter a number: "

            if "is even" in code:
                sample_out = "8 is even"
                alt_out = "7 is odd"
            elif "the number is even" in code.lower():
                sample_out = "the number is even"
                alt_out = "the number is odd"
            else:
                sample_out = "even"
                alt_out = "odd"

            return ExpectedIO(
                input_source="Interactive Console (`input()` prompt via stdin)",
                input_type="int (integer converted from terminal string input)",
                input_format=f"Single integer value entered at the prompt (`{prompt_str}`)",
                input_range="Any signed integer (... -2, -1, 0, 1, 2, ...)",
                sample_input="8",
                output_mechanism="Standard Console Output (`print()` to stdout)",
                output_type="str (formatted terminal message)",
                sample_output=sample_out,
                relationship="Evaluates `number % 2 == 0`. When remainder is 0 (even), executes the if branch and outputs the even message; when non-zero (odd), executes the else branch and outputs the odd message.",
                explanation=f"For sample input 8, 8 % 2 == 0 evaluates to True, resulting in output '{sample_out}'. For an odd input such as 7, output would be '{alt_out}'.",
                is_deterministic=True
            )

        if has_input:
            input_type = "str"
            if "int(input(" in code:
                input_type = "int"
            elif "float(input(" in code:
                input_type = "float"
            return ExpectedIO(
                input_source="Interactive Console (`input()` prompt via stdin)",
                input_type=input_type,
                input_format=f"Console user input formatted as {input_type}",
                input_range="Valid numeric input within Python precision limits" if input_type != "str" else "Any text string",
                sample_input="10" if input_type != "str" else "hello",
                output_mechanism="Standard Console Output (`print()` to stdout)" if outputs else "Variable state / computation",
                output_type="str / numeric console output",
                sample_output="Console text output based on user input",
                relationship="Reads input from stdin, processes logic, and prints output.",
                explanation="Outputs are written directly to stdout.",
                is_deterministic=True
            )

        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        if funcs:
            main_f = funcs[0]
            param_names = [arg.arg for arg in main_f.args.args]
            param_str = ", ".join(param_names) if param_names else "none"
            has_return = any(isinstance(n, ast.Return) for n in ast.walk(main_f))
            return ExpectedIO(
                input_source=f"Function Parameter(s) (`{param_str}` passed to `{main_f.name}`)",
                input_type="Function argument types",
                input_format=f"Arguments supplied during invocation `{main_f.name}(...)`",
                input_range="Nominal valid argument types",
                sample_input=f"{main_f.name}(...)",
                output_mechanism=f"Function Return Value (`return` statement in `{main_f.name}`)" if has_return else "Function side effects / state mutation",
                output_type="Computed return value" if has_return else "None",
                sample_output="Computed value returned to caller" if has_return else "None",
                relationship=f"Transforms argument `{param_str}` via `{main_f.name}` execution flow.",
                explanation=f"`{main_f.name}` executes its body and returns a result to the caller.",
                is_deterministic=True
            )

        return None

    def _format_inputs_text(self, io: ExpectedIO) -> str:
        return (
            f"**Source**: {io.input_source}\n"
            f"**Type**: `{io.input_type}`\n"
            f"**Format**: {io.input_format}\n"
            f"**Range**: {io.input_range}\n"
            f"**Sample Input**: `{io.sample_input}`"
        )

    def _format_outputs_text(self, io: ExpectedIO) -> str:
        return (
            f"**Mechanism**: {io.output_mechanism}\n"
            f"**Type**: `{io.output_type}`\n"
            f"**Expected Result**: `{io.sample_output}`\n"
            f"**Relationship**: {io.relationship}"
        )

    def _build_viva_questions(
        self,
        tree: ast.AST,
        concepts: Set[str],
        has_input: bool,
        diagnostics: List[DiagnosticItem]
    ) -> List[VivaQuestionItem]:
        questions = []
        has_modulo = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) for n in ast.walk(tree))
        if has_modulo:
            questions.append(VivaQuestionItem(
                question="How does the modulo operator (%) determine whether a number is even or odd?",
                answer="The modulo operator calculates the remainder after integer division. For any integer n, dividing by 2 yields a remainder of 0 if n is even, and 1 (or -1 in some languages, though 1 in Python) if n is odd. Thus, `n % 2 == 0` is the standard check for parity.",
                concept="Modulo Arithmetic & Parity"
            ))

        if has_input:
            questions.append(VivaQuestionItem(
                question="What happens if a user enters letters (like 'abc') into `int(input())`, and how do you prevent crashes?",
                answer="Python raises an unhandled `ValueError: invalid literal for int() with base 10`. To write defensive code, wrap the conversion inside a `try...except ValueError:` block, prompting the user again or displaying an informative error message.",
                concept="Exception Handling & Defensive Programming"
            ))

        if any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(tree)):
            questions.append(VivaQuestionItem(
                question="What is the difference between `for` loops and `while` loops in Python?",
                answer="A `for` loop iterates over a predetermined iterable sequence (such as a list or `range()`). A `while` loop repeatedly executes as long as a boolean condition evaluates to True, which is useful when the exact number of iterations is unknown in advance.",
                concept="Control Flow & Iteration"
            ))

        if any(isinstance(n, ast.FunctionDef) for n in ast.walk(tree)):
            questions.append(VivaQuestionItem(
                question="What is variable scope in Python and what is the difference between local and global variables?",
                answer="Scope defines the visibility and lifetime of a variable. Variables declared inside a function have local scope and cannot be accessed from outside that function. Variables declared at the script/module top-level have global scope.",
                concept="Variable Scope & Functions"
            ))

        if not questions:
            questions.append(VivaQuestionItem(
                question="How does Python execute sequential scripts?",
                answer="Python executes code top-to-bottom line by line. Variables are dynamically typed upon assignment, and expressions are evaluated sequentially unless redirected by conditional branches or loops.",
                concept="Python Execution Model"
            ))

        return questions

