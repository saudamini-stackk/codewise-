import re
from typing import Optional, List, Dict, Any
from ..models import (
    AnalysisResult,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    ComplexityInfo,
    ExpectedIO,
    VivaQuestionItem
)
from .base import BaseAnalyzer, extract_lines

LANGUAGE_META: Dict[str, Dict[str, Any]] = {
    "java": {
        "name": "Java",
        "paradigm": "Object-Oriented, Class-Based, JVM Runtime",
        "entrypoint_pattern": r"public\s+static\s+void\s+main\s*\(",
        "class_pattern": r"\b(class|interface|enum|record)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"(?:public|protected|private|static|\s)+[\w<>\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{",
        "requires_semicolon": True
    },
    "csharp": {
        "name": "C#",
        "paradigm": "Multi-Paradigm, Strongly Typed, .NET Platform",
        "entrypoint_pattern": r"\bstatic\s+(?:void|int|async\s+Task)\s+Main\s*\(",
        "class_pattern": r"\b(class|interface|struct|record)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"(?:public|protected|private|static|async|\s)+[\w<>\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{",
        "requires_semicolon": True
    },
    "go": {
        "name": "Go",
        "paradigm": "Concurrent, Statically Typed, Compiled",
        "entrypoint_pattern": r"\bfunc\s+main\s*\(\s*\)",
        "class_pattern": r"\btype\s+([a-zA-Z0-9_]+)\s+(struct|interface)",
        "func_pattern": r"\bfunc\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\([^)]*\)",
        "requires_semicolon": False
    },
    "rust": {
        "name": "Rust",
        "paradigm": "Memory-Safe, Zero-Cost Abstractions, Systems Language",
        "entrypoint_pattern": r"\bfn\s+main\s*\(\s*\)",
        "class_pattern": r"\b(struct|enum|trait|impl)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"\b(pub\s+)?fn\s+([a-zA-Z0-9_]+)\s*(?:<[^>]+>)?\s*\([^)]*\)",
        "requires_semicolon": True
    },
    "php": {
        "name": "PHP",
        "paradigm": "Server-Side Scripting, Dynamic, Web Backend",
        "entrypoint_pattern": None,
        "class_pattern": r"\b(class|interface|trait)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"\bfunction\s+([a-zA-Z0-9_]+)\s*\(",
        "requires_semicolon": True
    },
    "ruby": {
        "name": "Ruby",
        "paradigm": "Pure Object-Oriented, Dynamic, Expressive Scripting",
        "entrypoint_pattern": None,
        "class_pattern": r"\b(class|module)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"\bdef\s+([a-zA-Z0-9_!?]+)",
        "requires_semicolon": False
    },
    "kotlin": {
        "name": "Kotlin",
        "paradigm": "Modern Statically Typed, Concise, JVM & Android",
        "entrypoint_pattern": r"\bfun\s+main\s*\(",
        "class_pattern": r"\b(class|interface|data\s+class|object)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"\bfun\s+([a-zA-Z0-9_]+)\s*\(",
        "requires_semicolon": False
    },
    "swift": {
        "name": "Swift",
        "paradigm": "Protocol-Oriented, Fast, Safe, Apple Ecosystem",
        "entrypoint_pattern": r"\b(func\s+main|@main)\b",
        "class_pattern": r"\b(class|struct|protocol|enum)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"\bfunc\s+([a-zA-Z0-9_]+)\s*\(",
        "requires_semicolon": False
    },
    "typescript": {
        "name": "TypeScript",
        "paradigm": "Typed JavaScript, Compile-Time Safety, Web Systems",
        "entrypoint_pattern": None,
        "class_pattern": r"\b(class|interface|type)\s+([a-zA-Z0-9_]+)",
        "func_pattern": r"\b(?:function\s+([a-zA-Z0-9_]+)|const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?=>)",
        "requires_semicolon": False
    }
}

class GeneralCodeAnalyzer(BaseAnalyzer):
    """
    Extensible analyzer for Java, C#, Go, Rust, PHP, Ruby, Kotlin, Swift, and TypeScript.
    Extracts object structures, functions, control loops, computational complexity, and diagnostics.
    """

    def analyze(self, code: str, filename: Optional[str] = None, language: str = "java") -> AnalysisResult:
        lang = language.lower().strip()
        meta = LANGUAGE_META.get(lang, {
            "name": language.capitalize(),
            "paradigm": "General Programming Language",
            "entrypoint_pattern": None,
            "class_pattern": r"\b(class|struct)\s+([a-zA-Z0-9_]+)",
            "func_pattern": r"\b(function|def|fn|func)\s+([a-zA-Z0-9_]+)",
            "requires_semicolon": False
        })

        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []

        # 1. Bracket Matching Check
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            diagnostics.append(DiagnosticItem(
                id=f"diag-{lang}-unbalanced-braces",
                title="Potential Syntax Error: Unbalanced Curly Braces",
                severity="error",
                explanation=f"Found {open_braces} opening '{{' and {close_braces} closing '}}' braces. Mismatched block delimiters will cause compilation or parse errors.",
                recommended_correction="Ensure all opened code blocks, classes, and functions are properly closed.",
                detection_type="static_heuristic"
            ))

        # 2. Extract Types / Classes
        classes = []
        if meta["class_pattern"]:
            for match in re.finditer(meta["class_pattern"], code):
                classes.append(match.group(2) if len(match.groups()) >= 2 else match.group(1))

        # 3. Extract Functions / Methods
        functions = []
        if meta["func_pattern"]:
            for match in re.finditer(meta["func_pattern"], code):
                name = match.group(1) or (match.group(2) if len(match.groups()) > 1 else None)
                if name and name not in {"if", "for", "while", "switch"}:
                    functions.append(name)

        # 4. Check for Entrypoint
        has_entrypoint = False
        if meta.get("entrypoint_pattern"):
            has_entrypoint = bool(re.search(meta["entrypoint_pattern"], code))

        # 5. Algorithmic Complexity Heuristics
        loop_matches = re.findall(r"\b(for|while|loop)\b", code)
        loop_count = len(loop_matches)

        nested_loop = False
        curr_depth = 0
        max_loop_depth = 0
        for line in lines:
            if any(k in line for k in ["for ", "while "]):
                curr_depth += 1
                max_loop_depth = max(max_loop_depth, curr_depth)
            if "}" in line or "end" in line:
                if curr_depth > 0:
                    curr_depth -= 1

        if max_loop_depth >= 2:
            time_comp = "O(N²)"
            time_exp = f"Quadratic time complexity: Contains {max_loop_depth} nested loop layer(s)."
        elif loop_count >= 1:
            time_comp = "O(N)"
            time_exp = f"Linear time complexity: Contains {loop_count} sequential loop(s) iterating through input bounds."
        else:
            time_comp = "O(1)"
            time_exp = "Constant time: Executes sequential instructions with no looping structures."

        variables_functions: List[VariableFunctionItem] = []
        for cls in classes[:5]:
            variables_functions.append(VariableFunctionItem(
                name=cls,
                kind="Type / Class",
                data_type="User Defined Type",
                description=f"Class/type definition in {meta['name']}.",
                scope="Package / Namespace"
            ))

        for fn in functions[:8]:
            variables_functions.append(VariableFunctionItem(
                name=f"{fn}()",
                kind="Function / Method",
                data_type="Callable Routine",
                description="Subroutine executing program logic.",
                scope="Class Member"
            ))

        # Line-by-line explanation
        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = f"{meta['name']} statement."
            if s.startswith("//") or s.startswith("#") or s.startswith("/*"):
                exp = "Code comment explaining implementation details."
            elif any(s.startswith(k) for k in ["import ", "package ", "using ", "use ", "require "]):
                exp = "Module or package import binding external libraries and namespaces."
            elif any(k in s for k in ["class ", "interface ", "struct ", "type "]):
                exp = "Type declaration establishing data structure or class encapsulation."
            elif any(k in s for k in ["public static void main", "fun main", "fn main", "void Main"]):
                exp = "Program entrypoint invoked by runtime when application starts."
            elif "for " in s or "while " in s:
                exp = "Loop control structure iterating repeatedly over condition or collection."
            elif "if " in s:
                exp = "Conditional branch checking boolean condition."
            elif "return " in s:
                exp = "Returns result value from function back to caller."
            elif any(k in s for k in ["System.out.print", "Console.Write", "println!", "fmt.Print", "print(", "puts "]):
                exp = "Prints output message or formatted data to console (stdout)."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        entry_note = "Includes standard main() application entry point. " if has_entrypoint else "Modular routine / library component (no main entry point). "
        class_str = f" ({', '.join(classes)})" if classes else ""
        func_str = f" ({', '.join(functions[:4])})" if functions else ""
        overview = (
            f"{meta['name']} source code containing {len(lines)} line(s). "
            f"Defines {len(classes)} class/type(s){class_str} and {len(functions)} function/method(s){func_str}. "
            f"{entry_note}Follows {meta['paradigm']} conventions."
        )

        has_imports = any(
            re.match(r"^\s*(import|package|using|use|require)\b", line) for line in lines
        )
        has_console_out = any(
            any(k in line for k in ["System.out", "Console.Write", "println!", "fmt.Print", "print(", "puts "])
            for line in lines
        )
        has_returns = any("return " in line for line in lines)

        # Dynamic, honest workflow: NEVER invent imports, packages, or entrypoints that do not exist
        wf_steps = []
        w_idx = 1
        if has_imports:
            wf_steps.append(f"{w_idx}. **Imports Resolution**: Resolves declared package dependencies and namespaces.")
            w_idx += 1
        if classes:
            wf_steps.append(f"{w_idx}. **Type Declarations**: Defines structure and methods for {', '.join(classes[:3])}.")
            w_idx += 1
        if has_entrypoint:
            wf_steps.append(f"{w_idx}. **Program Entry Point (`main`)**: Runtime invokes application entry point to start execution.")
            w_idx += 1
        elif functions:
            wf_steps.append(f"{w_idx}. **Subroutine Execution**: Executes `{functions[0]}()` when invoked by an external caller or test.")
            w_idx += 1
        else:
            wf_steps.append(f"{w_idx}. **Sequential Execution**: Statements execute sequentially.")
            w_idx += 1

        if loop_count > 0:
            wf_steps.append(f"{w_idx}. **Iterative Logic**: Executes {loop_count} loop block(s) with {time_comp} complexity.")
            w_idx += 1
        if has_console_out:
            wf_steps.append(f"{w_idx}. **Console Output**: Formats and prints results to stdout stream.")
            w_idx += 1
        elif has_returns:
            wf_steps.append(f"{w_idx}. **Value Return**: Returns computed result value to caller.")
            w_idx += 1
        else:
            wf_steps.append(f"{w_idx}. **Completion**: Method completes execution.")
            w_idx += 1

        logic_workflow = "\n".join(wf_steps)

        # Expected I/O
        input_src = "Command-line arguments (args)" if has_entrypoint else (
            f"Function Arguments (passed to `{functions[0]}`)" if functions else "Standard input / variables"
        )
        out_mech = "Standard Console Output (stdout)" if has_console_out else (
            "Function Return Value" if has_returns else "In-Place Object State Mutation"
        )
        expected_io = ExpectedIO(
            input_source=input_src,
            input_type="Typed function arguments / strings",
            input_format="Values provided to subroutine or console",
            input_range="Valid domain according to type declarations",
            sample_input=f"{functions[0]}(...)" if functions else "Sample parameters",
            output_mechanism=out_mech,
            output_type="Formatted text / return value",
            sample_output="Console output or computed return value",
            relationship="Processes input arguments according to defined algorithmic flow.",
            explanation="Outputs are emitted via the identified mechanism.",
            is_deterministic=True
        )

        inputs_text = (
            f"**Source**: {expected_io.input_source}\n"
            f"**Type**: `{expected_io.input_type}`\n"
            f"**Format**: {expected_io.input_format}\n"
            f"**Range**: {expected_io.input_range}\n"
            f"**Sample Input**: `{expected_io.sample_input}`"
        )
        outputs_text = (
            f"**Mechanism**: {expected_io.output_mechanism}\n"
            f"**Type**: `{expected_io.output_type}`\n"
            f"**Expected Result**: `{expected_io.sample_output}`\n"
            f"**Relationship**: {expected_io.relationship}"
        )

        concepts = [
            f"{meta['name']} Syntax & Idioms",
            meta["paradigm"],
            "Static Type Safety & Verification" if meta["requires_semicolon"] else "Dynamic / Type-Inferred Execution",
            "Algorithmic Control Flow"
        ]

        limitations = [
            f"Analysis operates statically without requiring the {meta['name']} runtime to be installed.",
            "Static analysis does not guarantee runtime safety against null pointer dereferences or unhandled runtime exceptions."
        ]
        if not has_entrypoint:
            limitations.append("No `main` entry point: Code represents a reusable component / library method.")

        viva_questions = [
            VivaQuestionItem(
                question=f"What execution paradigm does {meta['name']} use?",
                answer=f"{meta['name']} utilizes {meta['paradigm']}. It balances compile-time or static verification with modular function/class composition.",
                concept=f"{meta['name']} Architecture"
            ),
            VivaQuestionItem(
                question="What is the difference between a standalone application and a reusable library module?",
                answer="A standalone application defines a standard entry point (such as `main()`) where runtime execution begins. A library module provides reusable functions or classes intended to be imported and called by other programs.",
                concept="Software Design & Modularization"
            )
        ]

        return AnalysisResult(
            overview=overview,
            logic_workflow=logic_workflow,
            line_by_line=line_by_line[:40],
            inputs=inputs_text,
            outputs=outputs_text,
            expected_io=expected_io,
            variables_functions=variables_functions,
            programming_concepts=concepts,
            limitations=limitations,
            complexity=ComplexityInfo(
                time=time_comp,
                space="O(1) to O(N) depending on allocated memory structures",
                explanation=time_exp
            ),
            learning_takeaway=f"Mastering {meta['name']} involves understanding both its syntax and its execution paradigm ({meta['paradigm']}). Clean modular functions and strict type usage enhance maintainability.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local",
            viva_questions=viva_questions
        )
