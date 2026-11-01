import pytest
from backend.app.analyzer.python_analyzer import PythonAnalyzer

import ast
import pytest
from backend.app.analyzer.python_analyzer import PythonAnalyzer

def test_python_analyzer_user_parity_script():
    analyzer = PythonAnalyzer()
    code = """number = int(input("enter a number: "))

if number % 2 == 0:
    print("the number is even")
else:
    print("the number is odd")"""

    result = analyzer.analyze(code)

    # 1. Distinguish actual errors from potential risks (0 errors, 1 warning)
    errors = [d for d in result.diagnostics if d.severity == "error"]
    warnings = [d for d in result.diagnostics if d.severity == "warning"]
    assert len(errors) == 0, "Valid code with nominal inputs should not have errors"
    assert len(warnings) == 1, "Unchecked int(input(...)) should be flagged as advisory warning"
    assert "Risk" in warnings[0].title or "Warning" in warnings[0].title or "Unchecked" in warnings[0].title

    # 2. Classify unchecked input conversion as potential warning noting non-numeric 'abc'
    assert "abc" in warnings[0].explanation
    assert "ValueError" in warnings[0].explanation

    # 3. Improve code understanding: NO invented functions, variables or return values
    func_names = [v.name for v in result.variables_functions if v.kind == "function"]
    assert len(func_names) == 0, f"Expected 0 functions, found: {func_names}"
    var_names = [v.name for v in result.variables_functions if v.kind == "variable"]
    assert var_names == ["number"], f"Expected variable 'number', found: {var_names}"
    assert "return_value" not in [s.state.get("return_value") for s in result.dry_run if s.state]

    # Check dry run accurately references 'number' and explains 8, 7, and abc
    dry_run_text = " ".join([f"{s.action} {s.notes}" for s in result.dry_run])
    assert "check_even_odd" not in dry_run_text, "Hallucinated function check_even_odd found in dry run!"
    assert "8" in dry_run_text
    assert "7" in dry_run_text
    assert "abc" in dry_run_text

    # 4. Proportional suggested code: clean try...except ValueError without while True
    assert result.suggested_code is not None
    assert "while True" not in result.suggested_code, "Suggested code should be proportional, not a while loop"
    assert "try:" in result.suggested_code
    assert "except ValueError:" in result.suggested_code

    # 7. Syntactically valid suggested code
    parsed = ast.parse(result.suggested_code)
    assert parsed is not None

def test_python_analyzer_clean_code_no_issues():
    analyzer = PythonAnalyzer()
    code = """def add_numbers(a, b):
    return a + b

total = add_numbers(10, 20)
print(total)"""

    result = analyzer.analyze(code)
    assert len(result.diagnostics) == 0
    assert "No syntax, runtime, or logic issues were detected" in result.learning_takeaway
    assert result.suggested_code is None

def test_python_analyzer_even_odd_with_function():
    analyzer = PythonAnalyzer()
    code = """
def check_even_odd(number):
    if number % 2 == 0:
        return "Even"
    else:
        return "Odd"

num = int(input("Enter number: "))
print(check_even_odd(num))
"""
    result = analyzer.analyze(code)
    assert result.overview != ""
    assert "Functions" in result.programming_concepts
    assert "Conditional Branching (if/else)" in result.programming_concepts
    assert len(result.line_by_line) > 0
    assert result.complexity.time == "O(1)"
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].severity == "warning"
    # Ensure suggested code parses cleanly
    assert result.suggested_code is not None
    ast.parse(result.suggested_code)

def test_python_analyzer_zero_division():
    analyzer = PythonAnalyzer()
    code = """
x = 10
y = 0
result = x / 0
print(result)
"""
    result = analyzer.analyze(code)
    zero_div = [d for d in result.diagnostics if "zero" in d.title.lower()]
    assert len(zero_div) > 0
    assert zero_div[0].severity == "error"

def test_python_analyzer_syntax_error():
    analyzer = PythonAnalyzer()
    code = """
def broken_func(
    print("missing closing paren and colon"
"""
    result = analyzer.analyze(code)
    assert len(result.diagnostics) > 0
    assert result.diagnostics[0].severity == "error"
    assert result.diagnostics[0].detection_type == "confirmed_parser"

