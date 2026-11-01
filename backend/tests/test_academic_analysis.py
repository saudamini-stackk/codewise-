import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.analyzer.static_engine import StaticEngine
from backend.app.models import AnalysisResult

client = TestClient(app)
static_engine = StaticEngine()

def test_python_even_odd_academic_analysis():
    """
    Test Python even/odd program:
    - Accurate language identification
    - Never invents functions, classes, or imports
    - Accurately details expected inputs and outputs (interactive stdin, sample: 8 -> 8 is even)
    - Explains modulo arithmetic and relationship
    - Does not flag valid code as broken; classifies int(input()) conversion as potential warning
    """
    code = """number = int(input("Enter a number: "))
if number % 2 == 0:
    print(f"{number} is even")
else:
    print(f"{number} is odd")
"""
    result: AnalysisResult = static_engine.analyze(code, language="python")

    # 1. No invented functions or classes
    assert len([v for v in result.variables_functions if v.kind == "function"]) == 0
    assert len([v for v in result.variables_functions if v.kind == "Class"]) == 0
    assert "def " not in result.overview
    assert "class " not in result.overview

    # 2. Accurate Overview and Workflow
    assert "even or odd" in result.overview.lower() or "parity" in result.overview.lower()
    assert "User Input" in result.logic_workflow
    assert "Conditional Parity Evaluation" in result.logic_workflow
    assert "Console Output" in result.logic_workflow
    assert "Module Imports" not in result.logic_workflow  # No imports in submitted code!

    # 3. Expected Inputs & Outputs
    assert result.expected_io is not None
    assert "stdin" in result.expected_io.input_source.lower() or "input()" in result.expected_io.input_source
    assert "int" in result.expected_io.input_type
    assert result.expected_io.sample_input == "8"
    assert "stdout" in result.expected_io.output_mechanism.lower() or "console" in result.expected_io.output_mechanism.lower()
    assert result.expected_io.sample_output == "8 is even"
    assert "number % 2 == 0" in result.expected_io.relationship

    # 4. Error Diagnostics: No false positive errors!
    error_diags = [d for d in result.diagnostics if d.severity == "error"]
    assert len(error_diags) == 0, f"Valid code should not have errors: {error_diags}"
    
    # 5. Viva Questions
    assert len(result.viva_questions) >= 1
    assert any("modulo" in q.question.lower() or "%" in q.question for q in result.viva_questions)

    # 6. Verify Sample Endpoint
    resp = client.post("/api/verify-sample", json={
        "code": code,
        "language": "python",
        "sample_input": "8",
        "expected_output": "8 is even"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_match"] is True
    assert "8 is even" in data["actual_output"]


def test_java_bubble_sort_without_main():
    """
    Test correct Java Bubble Sort WITHOUT a main method:
    - Never invents a main entry point or imports
    - Does NOT flag library / method code as broken
    - Accurately details expected inputs (int[] arr parameter)
    - Accurately details expected outputs (in-place mutation, void return, sorted array)
    - Details O(N^2) time and O(1) space complexity
    - Provides academic viva questions
    """
    code = """public class BubbleSort {
    public static void bubbleSort(int[] arr) {
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            for (int j = 0; j < n - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
    }
}
"""
    result: AnalysisResult = static_engine.analyze(code, language="java")

    # 1. No invented entry points or imports
    assert "main()" not in result.logic_workflow
    assert "public static void main" not in result.logic_workflow
    assert "Imports Resolution" not in result.logic_workflow  # No imports exist!
    assert "reusable" in result.overview.lower() or "no main" in result.overview.lower() or "bubble sort" in result.overview.lower()

    # 2. No false positive errors
    errors = [d for d in result.diagnostics if d.severity == "error"]
    assert len(errors) == 0, f"Valid Java method should not have errors: {errors}"

    # 3. Expected Inputs & Outputs
    assert result.expected_io is not None
    assert "Method Parameter" in result.expected_io.input_source or "arr" in result.expected_io.input_source
    assert "int[]" in result.expected_io.input_type
    assert "64" in result.expected_io.sample_input
    assert "In-place" in result.expected_io.output_mechanism or "mutation" in result.expected_io.output_mechanism
    assert "11" in result.expected_io.sample_output and "90" in result.expected_io.sample_output

    # 4. Complexity & Concepts
    assert result.complexity.time == "O(N²)"
    assert result.complexity.space == "O(1)"
    assert "Bubble Sort Algorithm" in result.programming_concepts
    assert "Adjacent Element Swapping" in result.programming_concepts

    # 5. Viva Preparation
    assert len(result.viva_questions) >= 4
    viva_topics = [q.question for q in result.viva_questions]
    assert any("time complexity" in q.lower() for q in viva_topics)
    assert any("stable" in q.lower() for q in viva_topics)


def test_java_bubble_sort_with_main():
    """
    Test complete Java Bubble Sort WITH a main method:
    - Recognizes main entry point
    - Accurately details workflow including main invoking bubbleSort and printing elements
    - Expected input: hardcoded array
    - Expected output: console output with sorted elements
    - 0 error diagnostics
    """
    code = """public class BubbleSortMain {
    public static void bubbleSort(int[] arr) {
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            for (int j = 0; j < n - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
    }

    public static void main(String[] args) {
        int[] numbers = {64, 34, 25, 12, 22, 11, 90};
        bubbleSort(numbers);
        System.out.println("Sorted array:");
        for (int num : numbers) {
            System.out.print(num + " ");
        }
        System.out.println();
    }
}
"""
    result: AnalysisResult = static_engine.analyze(code, language="java")

    # 1. Recognizes main entry point
    assert "main" in result.overview.lower()
    assert "main" in result.logic_workflow.lower()
    assert "Console Output" in result.logic_workflow

    # 2. No false positive errors
    errors = [d for d in result.diagnostics if d.severity == "error"]
    assert len(errors) == 0

    # 3. Expected Inputs & Outputs
    assert result.expected_io is not None
    assert "main()" in result.expected_io.input_source or "numbers" in result.expected_io.input_source
    assert "Console Output" in result.expected_io.output_mechanism or "System.out" in result.expected_io.output_mechanism
    assert "11 12 22 25 34 64 90" in result.expected_io.sample_output


def test_java_unbalanced_braces_error():
    """
    Test that confirmed syntax errors in Java (e.g. unclosed braces) ARE detected.
    """
    broken_code = """public class Broken {
    public static void main(String[] args) {
        System.out.println("Missing closing brace");
"""
    result: AnalysisResult = static_engine.analyze(broken_code, language="java")
    errors = [d for d in result.diagnostics if d.severity == "error"]
    assert len(errors) >= 1
    assert "Brace" in errors[0].title or "brace" in errors[0].explanation.lower()
