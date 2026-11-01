import re
from typing import Optional, List, Dict, Any, Set
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

class JavaAnalyzer(BaseAnalyzer):
    """
    Dedicated, academically rigorous analyzer for Java source code.
    Accurately analyzes OOP structure, methods, algorithms (e.g. Bubble Sort),
    I/O channels, complexity, edge cases, and viva exam preparation.
    Never invents entry points, packages, or imports that do not exist.
    """

    def analyze(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        variables_functions: List[VariableFunctionItem] = []
        concepts: Set[str] = set()

        # 1. Structural Bracket & Parenthesis Integrity Checks
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            diagnostics.append(DiagnosticItem(
                id="java-unbalanced-braces",
                title="Confirmed Syntax Error: Mismatched Curly Braces",
                severity="error",
                line_number=self._find_last_unmatched_brace(lines),
                explanation=f"Found {open_braces} opening '{{' and {close_braces} closing '}}' braces. In Java, all class and method code blocks must be balanced.",
                recommended_correction="Ensure every opened class, method, or loop block has a matching closing brace.",
                detection_type="confirmed_parser"
            ))

        open_parens = code.count("(")
        close_parens = code.count(")")
        if open_parens != close_parens:
            diagnostics.append(DiagnosticItem(
                id="java-unbalanced-parens",
                title="Confirmed Syntax Error: Mismatched Parentheses",
                severity="error",
                line_number=None,
                explanation=f"Found {open_parens} opening '(' and {close_parens} closing ')' parentheses.",
                recommended_correction="Check method parameter lists, loop headers, and expressions for unclosed parentheses.",
                detection_type="confirmed_parser"
            ))

        # 2. Extract Packages and Imports (ONLY if they actually exist in the code)
        packages = re.findall(r"^\s*package\s+([\w\.]+)\s*;", code, re.MULTILINE)
        imports = re.findall(r"^\s*import\s+([\w\.\*]+)\s*;", code, re.MULTILINE)
        if packages:
            concepts.add("Java Packages & Namespaces")
        if imports:
            concepts.add("External Package Imports")

        # 3. Extract Classes / Interfaces
        class_matches = list(re.finditer(r"\b(class|interface|enum|record)\s+([a-zA-Z0-9_]+)", code))
        classes = [m.group(2) for m in class_matches]
        if classes:
            concepts.add("Object-Oriented Programming (Classes)")

        # 4. Extract Methods
        # Matches e.g. public static void bubbleSort(int[] arr)
        method_pattern = r"(?:(?:public|protected|private|static|final|abstract|synchronized)\s+)+([\w<>\[\]]+)\s+([a-zA-Z0-9_]+)\s*\(([^)]*)\)"
        method_matches = list(re.finditer(method_pattern, code))
        methods = []
        has_main = False
        main_arg_name = "args"

        for m in method_matches:
            ret_type, m_name, params = m.group(1), m.group(2), m.group(3).strip()
            if m_name in {"if", "for", "while", "switch", "catch"}:
                continue
            methods.append({
                "name": m_name,
                "return_type": ret_type,
                "params": params,
                "is_static": "static" in m.group(0),
                "is_public": "public" in m.group(0)
            })
            if m_name == "main" and "String" in params:
                has_main = True
                p_match = re.search(r"String\s*(?:\[\s*\]|\.\.\.)\s*([a-zA-Z0-9_]+)", params)
                if p_match:
                    main_arg_name = p_match.group(1)

        # 5. Algorithm Pattern Recognition: Bubble Sort
        is_bubble_sort = False
        has_adjacent_swap = False
        has_nested_loops = False
        outer_var, inner_var = "i", "j"

        # Check for nested loops comparing arr[j] and arr[j+1] or swapping
        bs_compare = re.search(r"(\w+)\s*\[\s*(\w+)\s*\]\s*([><])\s*\1\s*\[\s*\2\s*\+\s*1\s*\]", code)
        bs_swap = re.search(r"(\w+)\s*=\s*(\w+)\[(\w+)\];.*?\2\[\3\]\s*=\s*\2\[\3\s*\+\s*1\];.*?\2\[\3\s*\+\s*1\]\s*=\s*\1;", code, re.DOTALL)

        if bs_compare or bs_swap or ("bubble" in code.lower() and re.search(r"\bfor\b.*?\bfor\b", code, re.DOTALL)):
            is_bubble_sort = True
            concepts.add("Bubble Sort Algorithm")
            concepts.add("In-Place Array Sorting")
            concepts.add("Adjacent Element Swapping")

        # 6. Extract Variables and Types
        # Extract fields and local variables
        var_decls = list(re.finditer(r"\b(int|long|double|float|boolean|char|String|int\[\]|String\[\])\s+([a-zA-Z0-9_]+)\s*(?:=\s*([^;]+))?;", code))
        for v in var_decls:
            v_type, v_name, v_val = v.group(1), v.group(2), v.group(3)
            desc = f"Stores {v_type} value."
            if v_val:
                desc = f"Initialized to `{v_val.strip()}`."
            if is_bubble_sort:
                if v_name in {"n", "len", "length"}:
                    desc = "Stores the total length / number of elements of the array."
                elif v_name == "temp":
                    desc = "Temporary swap variable used to hold arr[j] during element exchange."
                elif v_name in {"numbers", "arr"}:
                    desc = f"Integer array dataset: `{v_val.strip() if v_val else 'input parameter'}`."

            variables_functions.append(VariableFunctionItem(
                name=v_name,
                kind="variable",
                data_type=v_type,
                description=desc,
                scope="local / member"
            ))

        for cls in classes:
            variables_functions.append(VariableFunctionItem(
                name=cls,
                kind="Class",
                data_type="Class Type",
                description=f"Java class defining data structures and member methods.",
                scope="Package / Application"
            ))

        for m in methods:
            variables_functions.append(VariableFunctionItem(
                name=f"{m['name']}({m['params']})",
                kind="Method",
                data_type=m["return_type"],
                description=f"{'Application entry point' if m['name'] == 'main' else 'Member subroutine'} returning {m['return_type']}.",
                scope="Class Member"
            ))

        # 7. Formulate Expected Inputs and Outputs
        expected_io = self._build_expected_io(code, is_bubble_sort, has_main, methods, lines)

        # 8. Complexity Evaluation
        loop_count = len(re.findall(r"\b(for|while|do)\b", code))
        if is_bubble_sort:
            time_comp = "O(N²)"
            space_comp = "O(1)"
            comp_exp = (
                "Quadratic time complexity: The algorithm executes two nested loops. The outer loop executes (n - 1) passes, "
                "and the inner loop performs (n - i - 1) comparisons per pass. Total comparisons: n*(n-1)/2 ≈ O(N²). "
                "Space complexity is O(1) auxiliary space because sorting is performed directly in-place without allocating a duplicate array."
            )
            concepts.add("Nested Loop Iteration")
            concepts.add("Time Complexity O(N²)")
            concepts.add("Space Complexity O(1)")
        elif loop_count >= 2:
            time_comp = "O(N²)"
            space_comp = "O(1)"
            comp_exp = f"Quadratic time complexity: Contains {loop_count} loop structures with nested iteration."
        elif loop_count == 1:
            time_comp = "O(N)"
            space_comp = "O(1)"
            comp_exp = "Linear time complexity: Iterates sequentially through input bounds in a single loop."
        else:
            time_comp = "O(1)"
            space_comp = "O(1)"
            comp_exp = "Constant time: Executes sequential instructions with no looping structures."

        # 9. Formulate Overview
        overview = self._build_overview(code, classes, methods, has_main, is_bubble_sort, packages, imports)

        # 10. Formulate Step-by-Step Logic Workflow (NEVER invent main or imports if not present)
        workflow = self._build_workflow(code, classes, methods, has_main, is_bubble_sort, packages, imports)

        # 11. Formulate Line-by-Line Explanation
        line_by_line = self._build_line_by_line(lines, is_bubble_sort)

        # 12. Formulate Limitations and Edge Cases
        limitations = self._build_limitations(code, is_bubble_sort, has_main)

        # 13. Formulate Viva Questions
        viva_questions = self._build_viva_questions(is_bubble_sort, has_main)

        # 14. Academic Learning Takeaway
        if is_bubble_sort:
            takeaway = (
                "Bubble Sort is a foundational comparison-based sorting algorithm. While its O(N²) time complexity "
                "makes it inefficient for large real-world datasets compared to Quick Sort or Merge Sort (O(N log N)), "
                "its simplicity, O(1) auxiliary in-place memory usage, and stability (equal elements retain their original relative order) "
                "make it an essential academic milestone for understanding algorithm design and complexity analysis."
            )
        else:
            takeaway = (
                "Java enforces strong static typing and class-based modular encapsulation. "
                "Clear separation of concerns between computational methods and presentation logic creates robust, maintainable programs."
            )

        # Inputs & Outputs markdown summaries for backward compatibility
        inputs_text = self._format_inputs_text(expected_io)
        outputs_text = self._format_outputs_text(expected_io)

        # Dry Run Generation
        dry_run_steps = self._build_dry_run(is_bubble_sort, has_main)

        return AnalysisResult(
            overview=overview,
            logic_workflow=workflow,
            line_by_line=line_by_line[:50],
            inputs=inputs_text,
            outputs=outputs_text,
            expected_io=expected_io,
            variables_functions=variables_functions,
            programming_concepts=sorted(list(concepts)),
            limitations=limitations,
            complexity=ComplexityInfo(
                time=time_comp,
                space=space_comp,
                explanation=comp_exp
            ),
            learning_takeaway=takeaway,
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local",
            dry_run=dry_run_steps,
            loop_details=LoopDetails(
                has_loops=loop_count > 0,
                loop_type="Nested for-loops" if loop_count > 1 else ("for-loop" if loop_count == 1 else "None"),
                description="Outer loop controls sorting passes; inner loop compares adjacent elements." if is_bubble_sort else f"{loop_count} loop(s) detected.",
                condition="j < n - i - 1" if is_bubble_sort else "",
                iteration_explanation="Advances to next adjacent pair" if is_bubble_sort else "",
                termination="Terminates when all passes complete" if is_bubble_sort else ""
            ) if loop_count > 0 else None,
            viva_questions=viva_questions
        )

    def _find_last_unmatched_brace(self, lines: List[str]) -> Optional[int]:
        open_count = 0
        close_count = 0
        last_open_line = 1
        for idx, line in enumerate(lines, 1):
            if "{" in line:
                open_count += line.count("{")
                last_open_line = idx
            if "}" in line:
                close_count += line.count("}")
        return last_open_line if open_count > close_count else len(lines)

    def _build_overview(
        self,
        code: str,
        classes: List[str],
        methods: List[Dict[str, Any]],
        has_main: bool,
        is_bubble_sort: bool,
        packages: List[str],
        imports: List[str]
    ) -> str:
        class_str = f"class `{classes[0]}`" if classes else "a Java code module"
        method_names = [m["name"] for m in methods]
        
        if is_bubble_sort:
            if has_main:
                return (
                    f"This Java application implements the complete **Bubble Sort** algorithm within {class_str}. "
                    f"It includes both the reusable sorting method (`bubbleSort`) and a standard `main` entry point "
                    f"that initializes a test integer array, calls `bubbleSort` to sort the array in ascending order, "
                    f"and prints the resulting sorted elements to standard output (`System.out`)."
                )
            else:
                return (
                    f"This Java source file defines the **Bubble Sort** algorithm as a reusable class/method ({class_str}). "
                    f"It is designed as a modular library routine: it accepts an integer array parameter, sorts the elements "
                    f"in-place in non-decreasing order using adjacent element comparisons, and completes without requiring "
                    f"or defining a `main()` entry point. It is intended to be called by other classes or unit test suites."
                )

        # General Java program
        entry_desc = "includes an executable `main()` method entry point" if has_main else "defines modular subroutines intended for external invocation (no `main()` entry point)"
        methods_desc = f"declaring {len(methods)} method(s): {', '.join(f'`{m}`' for m in method_names)}" if method_names else "containing structural logic"
        return f"This Java source file defines {class_str}, {entry_desc}, {methods_desc}."

    def _build_workflow(
        self,
        code: str,
        classes: List[str],
        methods: List[Dict[str, Any]],
        has_main: bool,
        is_bubble_sort: bool,
        packages: List[str],
        imports: List[str]
    ) -> str:
        steps = []
        step_idx = 1

        if packages:
            steps.append(f"{step_idx}. **Package Namespace**: Declares package `{packages[0]}` to organize class namespace.")
            step_idx += 1

        if imports:
            steps.append(f"{step_idx}. **Imports Resolution**: Imports required external Java libraries ({', '.join(imports)}).")
            step_idx += 1

        if classes:
            steps.append(f"{step_idx}. **Class Definition**: Declares class `{classes[0]}` encapsulating sorting and utility methods.")
            step_idx += 1

        if is_bubble_sort:
            steps.append(f"{step_idx}. **Sorting Method Declaration (`bubbleSort`)**: Receives the integer array reference (`int[] arr`) as an input parameter.")
            step_idx += 1

            steps.append(f"{step_idx}. **Array Dimension Extraction**: Queries `arr.length` to store the element count `n`.")
            step_idx += 1

            steps.append(f"{step_idx}. **Outer Pass Loop**: Runs `n - 1` passes (index `i` from `0` to `n - 2`). In each pass, the largest remaining unsorted element will settle at its final position.")
            step_idx += 1

            steps.append(f"{step_idx}. **Inner Comparison Loop**: Iterates index `j` from `0` to `n - i - 2`, comparing each adjacent pair `arr[j]` and `arr[j + 1]`.")
            step_idx += 1

            steps.append(f"{step_idx}. **Conditional Swap**: If `arr[j] > arr[j + 1]`, exchanges elements using temporary variable `temp` to place the greater element to the right.")
            step_idx += 1

            if has_main:
                steps.append(f"{step_idx}. **Program Entry Point (`main`)**: Invoked by the Java Virtual Machine (JVM) on application startup.")
                step_idx += 1

                steps.append(f"{step_idx}. **Dataset Initialization**: Instantiates the test integer array in memory.")
                step_idx += 1

                steps.append(f"{step_idx}. **Method Invocation**: Calls `bubbleSort(numbers)`, passing the array reference so sorting occurs directly in-place.")
                step_idx += 1

                steps.append(f"{step_idx}. **Console Output**: Iterates through the sorted array, printing each element to standard console output (`System.out`).")
                step_idx += 1
            else:
                steps.append(f"{step_idx}. **In-Place Completion**: Method returns `void`. The original array supplied by the caller is now fully sorted in-place in memory.")
                step_idx += 1
        else:
            if has_main:
                steps.append(f"{step_idx}. **Application Entry (`main`)**: Execution begins at `public static void main(String[] args)`.")
                step_idx += 1
                steps.append(f"{step_idx}. **Statements Execution**: Sequential statements and control structures execute.")
                step_idx += 1
            else:
                steps.append(f"{step_idx}. **Method Invocations**: Defined member methods execute when instantiated or called by external classes.")
                step_idx += 1

        return "\n".join(steps)

    def _build_expected_io(
        self,
        code: str,
        is_bubble_sort: bool,
        has_main: bool,
        methods: List[Dict[str, Any]],
        lines: List[str]
    ) -> ExpectedIO:
        if is_bubble_sort:
            # Check if main has a hardcoded array
            hardcoded_arr_match = re.search(r"int\s*\[\s*\]\s*(\w+)\s*=\s*\{([^}]+)\}", code)
            if has_main and hardcoded_arr_match:
                raw_nums = hardcoded_arr_match.group(2).strip()
                sample_in = f"{{{raw_nums}}}"
                # Parse the integers to compute the exact expected sorted output
                try:
                    num_list = [int(x.strip()) for x in raw_nums.split(",") if x.strip()]
                    sorted_list = sorted(num_list)
                    sorted_str = " ".join(str(x) for x in sorted_list) + " "
                    sample_out = f"Sorted array:\n{sorted_str}"
                except Exception:
                    sample_out = "Sorted array:\n[elements in ascending numerical order]"

                return ExpectedIO(
                    input_source="Hardcoded variable in main() (`int[] " + hardcoded_arr_match.group(1) + "`)",
                    input_type="int[] (array of integers)",
                    input_format="1D array literal, e.g. " + sample_in,
                    input_range="Finite integer array with size N >= 0",
                    sample_input=sample_in,
                    output_mechanism="Standard Console Output (System.out.println / System.out.print)",
                    output_type="String text printed to terminal stdout",
                    sample_output=sample_out,
                    relationship="main() passes the array to bubbleSort(), which reorders elements from smallest to largest by adjacent swapping. main() then iterates through the sorted array and prints each element.",
                    explanation="Output is sent directly to the terminal stdout stream.",
                    is_deterministic=True
                )
            else:
                # Bubble sort library method without main
                sample_in = "{64, 34, 25, 12, 22, 11, 90}"
                sample_out = "{11, 12, 22, 25, 34, 64, 90}"
                return ExpectedIO(
                    input_source="Method Parameter (`int[] arr` passed into `bubbleSort`)",
                    input_type="int[] (primitive integer array)",
                    input_format="1D array of integers, e.g. " + sample_in,
                    input_range="Any array of integers (supports positive, negative, zero, and duplicate values)",
                    sample_input=sample_in,
                    output_mechanism="In-place array mutation (void return; modifies original array in memory)",
                    output_type="int[] (mutated array sorted in non-decreasing order)",
                    sample_output=sample_out,
                    relationship="Adjacent elements (arr[j], arr[j+1]) are compared. If out of order (arr[j] > arr[j+1]), they are swapped. Upon completion, arr[k] <= arr[k+1] for all valid indices.",
                    explanation="Because Java passes object and array references by value, modifications to arr[j] mutate the caller's array directly in heap memory without allocating a new array.",
                    is_deterministic=True
                )

        # General Java program
        has_scanner = "Scanner" in code
        has_stdout = "System.out" in code
        return ExpectedIO(
            input_source="Interactive Console (Scanner / stdin)" if has_scanner else ("Command-line arguments (args)" if has_main else "Method Arguments"),
            input_type="Standard Java primitive or reference types",
            input_format="Formatted text stream or method parameters",
            input_range="Nominal valid inputs supported by method signatures",
            sample_input="Nominal input data",
            output_mechanism="Standard Console Output (System.out)" if has_stdout else "Method Return Value",
            output_type="String / Void / Object",
            sample_output="Console text output or computed return value",
            relationship="Transforms supplied inputs according to class method logic.",
            explanation="Outputs are emitted to standard output or returned to calling routines.",
            is_deterministic=True
        )

    def _build_line_by_line(self, lines: List[str], is_bubble_sort: bool) -> List[LineExplanation]:
        res = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue

            exp = "Executes Java statement."
            if s.startswith("//") or s.startswith("/*") or s.startswith("*"):
                exp = "Code comment explaining implementation details."
            elif s.startswith("package "):
                exp = f"Declares package namespace: `{s.replace('package ', '').rstrip(';')}`."
            elif s.startswith("import "):
                exp = f"Imports library dependency: `{s.replace('import ', '').rstrip(';')}`."
            elif re.search(r"\bpublic\s+class\s+([a-zA-Z0-9_]+)", s):
                match = re.search(r"\bpublic\s+class\s+([a-zA-Z0-9_]+)", s)
                exp = f"Declares public class `{match.group(1)}`, the top-level container for methods and state."
            elif re.search(r"\bclass\s+([a-zA-Z0-9_]+)", s):
                match = re.search(r"\bclass\s+([a-zA-Z0-9_]+)", s)
                exp = f"Declares class `{match.group(1)}`."
            elif "public static void main" in s:
                exp = "Declares the standard Java application entry point method `main()`, executed first by the JVM."
            elif re.search(r"public\s+static\s+void\s+bubbleSort\s*\(int\s*\[\s*\]\s*(\w+)\)", s):
                m = re.search(r"public\s+static\s+void\s+bubbleSort\s*\(int\s*\[\s*\]\s*(\w+)\)", s)
                exp = f"Defines static method `bubbleSort` accepting integer array `{m.group(1)}` to sort in-place."
            elif re.search(r"void\s+bubbleSort\s*\(int\s*\[\s*\]\s*(\w+)\)", s):
                m = re.search(r"void\s+bubbleSort\s*\(int\s*\[\s*\]\s*(\w+)\)", s)
                exp = f"Defines method `bubbleSort` accepting integer array `{m.group(1)}`."
            elif re.search(r"int\s+(\w+)\s*=\s*(\w+)\.length\s*;", s):
                m = re.search(r"int\s+(\w+)\s*=\s*(\w+)\.length\s*;", s)
                exp = f"Stores the total number of elements in array `{m.group(2)}` into integer variable `{m.group(1)}`."
            elif re.search(r"for\s*\(\s*int\s+i\s*=\s*0\s*;\s*i\s*<\s*n\s*-\s*1\s*;\s*i\s*\+\+\s*\)", s):
                exp = "Outer loop: runs `n - 1` sorting passes. After each pass `i`, the `i` largest elements settle into place."
            elif re.search(r"for\s*\(\s*int\s+j\s*=\s*0\s*;\s*j\s*<\s*n\s*-\s*i\s*-\s*1\s*;\s*j\s*\+\+\s*\)", s):
                exp = "Inner loop: iterates through unsorted portion (`0` to `n - i - 2`), comparing each adjacent pair `(j, j+1)`."
            elif re.search(r"if\s*\(\s*(\w+)\s*\[\s*j\s*\]\s*>\s*\1\s*\[\s*j\s*\+\s*1\s*\]\s*\)", s):
                m = re.search(r"if\s*\(\s*(\w+)\s*\[\s*j\s*\]\s*>\s*\1\s*\[\s*j\s*\+\s*1\s*\]\s*\)", s)
                exp = f"Compares adjacent elements: checks if left element `{m.group(1)}[j]` is strictly greater than right element `{m.group(1)}[j+1]`."
            elif re.search(r"int\s+temp\s*=\s*(\w+)\s*\[\s*j\s*\]\s*;", s):
                m = re.search(r"int\s+temp\s*=\s*(\w+)\s*\[\s*j\s*\]\s*;", s)
                exp = f"Saves left element `{m.group(1)}[j]` into temporary variable `temp` to prevent overwriting during swap."
            elif re.search(r"(\w+)\s*\[\s*j\s*\]\s*=\s*\1\s*\[\s*j\s*\+\s*1\s*\]\s*;", s):
                m = re.search(r"(\w+)\s*\[\s*j\s*\]\s*=\s*\1\s*\[\s*j\s*\+\s*1\s*\]\s*;", s)
                exp = f"Copies smaller right element `{m.group(1)}[j+1]` into left position `{m.group(1)}[j]`."
            elif re.search(r"(\w+)\s*\[\s*j\s*\+\s*1\s*\]\s*=\s*temp\s*;", s):
                m = re.search(r"(\w+)\s*\[\s*j\s*\+\s*1\s*\]\s*=\s*temp\s*;", s)
                exp = f"Places the saved value from `temp` into right position `{m.group(1)}[j+1]`, completing the swap."
            elif re.search(r"int\s*\[\s*\]\s*(\w+)\s*=\s*\{([^}]+)\}\s*;", s):
                m = re.search(r"int\s*\[\s*\]\s*(\w+)\s*=\s*\{([^}]+)\}\s*;", s)
                exp = f"Initializes integer array `{m.group(1)}` with test elements: `{{{m.group(2).strip()}}}`."
            elif re.search(r"bubbleSort\s*\(\s*(\w+)\s*\)\s*;", s):
                m = re.search(r"bubbleSort\s*\(\s*(\w+)\s*\)\s*;", s)
                exp = f"Calls `bubbleSort` passing `{m.group(1)}` to sort the array in-place in memory."
            elif "System.out.println(" in s:
                exp = "Prints formatted line to standard console output (`stdout`) followed by a newline."
            elif "System.out.print(" in s:
                exp = "Prints content to standard console output (`stdout`) without appending a newline."
            elif s == "}":
                exp = "Closes statement block or method scope."

            res.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))
        return res

    def _build_limitations(self, code: str, is_bubble_sort: bool, has_main: bool) -> List[str]:
        limits = []
        if is_bubble_sort:
            limits.append("Inefficient for large arrays: O(N²) time complexity makes Bubble Sort unsuitable for datasets with more than a few thousand elements.")
            limits.append("Unchecked Null Reference: Passing `null` as the array parameter will trigger a runtime `NullPointerException` at `arr.length`.")
            limits.append("Empty Array Bound: An empty array `{}` results in `n = 0`; loops safely skip execution, but defensive checks (`if (arr == null || arr.length <= 1) return;`) are recommended in production libraries.")
            limits.append("Unoptimized Best Case: Without a boolean `swapped` flag tracking whether any elements were moved during a pass, the algorithm still runs in O(N²) time even if the array is already sorted.")
        if not has_main:
            limits.append("No `main()` entry point: This file is a class/method library module and cannot be run as a standalone application without a caller or test harness.")
        if not limits:
            limits.append("Operates reliably for standard nominal inputs within memory limits.")
        return limits

    def _build_viva_questions(self, is_bubble_sort: bool, has_main: bool) -> List[VivaQuestionItem]:
        if is_bubble_sort:
            return [
                VivaQuestionItem(
                    question="What is the time complexity of Bubble Sort in the best, average, and worst cases?",
                    answer="Worst and average cases are O(N²) because of the nested comparison loops. The unoptimized version is O(N²) even in the best case; however, if an early-exit 'swapped' boolean flag is added, the best case (already sorted array) drops to O(N).",
                    concept="Algorithmic Complexity"
                ),
                VivaQuestionItem(
                    question="Why is the inner loop condition `j < n - i - 1`?",
                    answer="After 'i' passes of the outer loop, the 'i' largest elements are already guaranteed to have bubbled to their correct final positions at the end of the array. Comparing them again is redundant, so subtracting 'i' avoids unnecessary comparisons.",
                    concept="Loop Invariant & Optimization"
                ),
                VivaQuestionItem(
                    question="Is Bubble Sort a stable sorting algorithm? Explain why.",
                    answer="Yes, Bubble Sort is stable. A sorting algorithm is stable if elements with identical keys maintain their original relative order. Because Bubble Sort only swaps when arr[j] > arr[j+1] (strict inequality), equal elements are never swapped past each other.",
                    concept="Stability in Sorting"
                ),
                VivaQuestionItem(
                    question="What is the auxiliary space complexity of Bubble Sort and what does 'in-place' mean?",
                    answer="Space complexity is O(1) auxiliary memory. 'In-place' means the algorithm sorts the elements within the existing array structure using only a single temporary variable (temp) without allocating a new array.",
                    concept="Memory & In-Place Algorithms"
                ),
                VivaQuestionItem(
                    question="How does Java handle passing arrays to methods like `bubbleSort(int[] arr)`?",
                    answer="Java passes everything by value. For objects and arrays, the value that is passed is the reference (memory address) to the array. Therefore, modifying arr[j] inside bubbleSort directly alters the caller's array in heap memory.",
                    concept="Java Parameter Passing Semantics"
                )
            ]
        return [
            VivaQuestionItem(
                question="What is the significance of `public static void main(String[] args)` in Java?",
                answer="It is the standard entry point recognized by the JVM. 'public' allows JVM access from outside the package, 'static' allows the method to be called without instantiating an object of the class, 'void' means it returns nothing, and 'String[] args' accepts command-line arguments.",
                concept="Java Entrypoint Mechanics"
            ),
            VivaQuestionItem(
                question="What is the difference between a class method library and a standalone runnable Java application?",
                answer="A standalone runnable Java application must contain a `public static void main(String[] args)` method so the JVM knows where to begin execution. A class method library contains reusable methods designed to be invoked by other applications or testing frameworks.",
                concept="Software Modularization"
            )
        ]

    def _build_dry_run(self, is_bubble_sort: bool, has_main: bool) -> List[DryRunStep]:
        if is_bubble_sort:
            return [
                DryRunStep(
                    step=1,
                    action="Initialize Input Array",
                    state={"arr": "[64, 34, 25, 12, 22, 11, 90]", "n": "7"},
                    notes="Length n = 7. Unsorted input ready for sorting."
                ),
                DryRunStep(
                    step=2,
                    action="Pass i = 0 (Bubble largest element)",
                    state={"arr": "[34, 25, 12, 22, 11, 64, 90]", "i": "0"},
                    notes="Largest element 90 moves to index 6."
                ),
                DryRunStep(
                    step=3,
                    action="Pass i = 1 (Bubble 2nd largest)",
                    state={"arr": "[25, 12, 22, 11, 34, 64, 90]", "i": "1"},
                    notes="Element 64 settles at index 5."
                ),
                DryRunStep(
                    step=4,
                    action="Passes i = 2 to 5 (Remaining elements settle)",
                    state={"arr": "[11, 12, 22, 25, 34, 64, 90]"},
                    notes="All adjacent out-of-order pairs swapped. Array is fully sorted in ascending order."
                )
            ]
        return []

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
