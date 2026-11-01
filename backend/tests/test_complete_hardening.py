import pytest
import time
import json
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import get_db, get_iso_now
from backend.app.executor import CodeExecutor
from backend.app.analyzer.python_analyzer import PythonAnalyzer

client = TestClient(app)

def run_code(code: str, language: str = "python", stdin: str = "", timeout: float = 5.0):
    return CodeExecutor.run(code, language, stdin, timeout)

# ==============================================================================
# SECTION 15 COMPREHENSIVE AUTOMATED TEST SUITE: 25 SPECIFIC TEST CASES
# ==============================================================================

# Test 1: Valid Python execution
def test_01_valid_python_execution():
    code = "print(1 + 1)"
    res = run_code(code, "python", stdin="", timeout=5)
    assert res["status"] == "success"
    assert res["exit_code"] == 0
    assert "2" in res["stdout"].strip()
    assert res["stderr"] == ""

# Test 2: Mixed-type sum TypeError
def test_02_mixed_type_sum_typeerror():
    code = 'numbers = [10, 20, "30", 40]\ntotal = sum(numbers)\nprint(total)'
    # Static check
    analyzer = PythonAnalyzer()
    res_static = analyzer.analyze(code)
    diag_titles = [d.title.lower() for d in res_static.diagnostics]
    assert any("type mismatch" in t or "type" in t for t in diag_titles)

    # Runtime check
    res_run = run_code(code, "python", stdin="", timeout=5)
    assert res_run["status"] == "error"
    assert res_run["exit_code"] != 0
    assert "TypeError" in res_run["stderr"]
    assert res_run.get("runtime_diagnostic") is not None
    assert res_run["runtime_diagnostic"]["exception_type"] == "TypeError"

# Test 3: Python syntax error
def test_03_python_syntax_error():
    code = "def f("
    res_run = run_code(code, "python", stdin="", timeout=5)
    assert res_run["status"] in ("compilation_error", "error")
    assert res_run["exit_code"] != 0
    assert "SyntaxError" in res_run["stderr"] or "syntax error" in res_run["stderr"].lower()

# Test 4: Division by zero
def test_04_division_by_zero():
    code = "x = 10 / 0\nprint(x)"
    # Static check
    analyzer = PythonAnalyzer()
    res_static = analyzer.analyze(code)
    assert any("division by zero" in d.title.lower() for d in res_static.diagnostics)

    # Runtime check
    res_run = run_code(code, "python", stdin="", timeout=5)
    assert res_run["status"] == "error"
    assert "ZeroDivisionError" in res_run["stderr"]
    assert res_run.get("runtime_diagnostic") is not None
    assert res_run["runtime_diagnostic"]["exception_type"] == "ZeroDivisionError"

# Test 5: Undefined variables
def test_05_undefined_variable():
    code = 'name = "Aditya"\nprint(nam)'
    # Static check
    analyzer = PythonAnalyzer()
    res_static = analyzer.analyze(code)
    assert any("undefined variable" in d.title.lower() and "nam" in d.title.lower() for d in res_static.diagnostics)

    # Runtime check
    res_run = run_code(code, "python", stdin="", timeout=5)
    assert res_run["status"] == "error"
    assert "NameError" in res_run["stderr"]
    assert res_run.get("runtime_diagnostic") is not None
    assert res_run["runtime_diagnostic"]["exception_type"] == "NameError"

# Test 6: Invalid conversions
def test_06_invalid_conversions():
    code = 'val = int("hello")\nprint(val)'
    # Static check
    analyzer = PythonAnalyzer()
    res_static = analyzer.analyze(code)
    assert any("invalid type conversion" in d.title.lower() for d in res_static.diagnostics)

    # Runtime check
    res_run = run_code(code, "python", stdin="", timeout=5)
    assert res_run["status"] == "error"
    assert "ValueError" in res_run["stderr"]

# Test 7: List index error
def test_07_list_index_error():
    code = "numbers = [10, 20, 30]\nprint(numbers[5])"
    # Static check
    analyzer = PythonAnalyzer()
    res_static = analyzer.analyze(code)
    assert any("indexerror" in d.title.lower() or "boundary" in d.title.lower() for d in res_static.diagnostics)

    # Runtime check
    res_run = run_code(code, "python", stdin="", timeout=5)
    assert res_run["status"] == "error"
    assert "IndexError" in res_run["stderr"]
    assert res_run.get("runtime_diagnostic") is not None
    assert res_run["runtime_diagnostic"]["exception_type"] == "IndexError"

# Test 8: Incorrect logical output
def test_08_incorrect_logical_output():
    # Code produces 4, but expected is 5
    code = "print(2 + 2)"
    res = client.post("/api/verify-sample", json={
        "code": code,
        "language": "python",
        "sample_input": "",
        "expected_output": "5"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_match"] is False
    assert "4" in data["actual_output"]
    assert "5" in data["expected_output"]

# Test 9: Edge cases (0, negative numbers)
def test_09_edge_cases_zero_negative():
    code = """
n = int(input())
if n > 0:
    print("positive")
elif n == 0:
    print("zero")
else:
    print("negative")
"""
    res_zero = run_code(code, "python", stdin="0\n", timeout=5)
    assert res_zero["status"] == "success"
    assert "zero" in res_zero["stdout"]

    res_neg = run_code(code, "python", stdin="-42\n", timeout=5)
    assert res_neg["status"] == "success"
    assert "negative" in res_neg["stdout"]

# Test 10: Empty input
def test_10_empty_input():
    code = "import sys\nline = sys.stdin.read()\nprint(f'read:{len(line)}')"
    res = run_code(code, "python", stdin="", timeout=5)
    assert res["status"] == "success"
    assert "read:0" in res["stdout"]

# Test 11: Negative input
def test_11_negative_input():
    code = "x = int(input())\nprint(x * 2)"
    res = run_code(code, "python", stdin="-15\n", timeout=5)
    assert res["status"] == "success"
    assert "-30" in res["stdout"]

# Test 12: Multiple stdin inputs
def test_12_multiple_stdin_inputs():
    code = "a = input()\nb = input()\nprint(f'{a}+{b}')"
    res = run_code(code, "python", stdin="apple\nbanana\n", timeout=5)
    assert res["status"] == "success"
    assert "apple+banana" in res["stdout"]

# Test 13: Execution timeout
def test_13_execution_timeout():
    code = "while True:\n    pass"
    start = time.time()
    res = run_code(code, "python", stdin="", timeout=2)
    elapsed = time.time() - start
    assert res["status"] == "timeout"
    assert elapsed < 5  # Ensure process tree was killed quickly
    assert "timed out" in res["stderr"].lower()

# Test 14: Excessive output truncation
def test_14_excessive_output_truncation():
    code = "for _ in range(50000):\n    print('A' * 100)"
    res = run_code(code, "python", stdin="", timeout=5)
    assert res["status"] == "success"
    assert len(res["stdout"]) <= 70000
    assert "truncated" in res["stdout"].lower()

# Test 15: Unsupported runtime
def test_15_unsupported_runtime():
    res = run_code("print 42", "brainfuck", stdin="", timeout=5)
    assert res["status"] in ("unsupported_runtime", "unsupported_language")
    assert res["exit_code"] != 0

# Test 16: Output comparison strict matching
def test_16_output_comparison_exact_vs_substring():
    # If code prints "100" and expected is "10", strict exact matching must NOT match
    code = "print(100)"
    res = client.post("/api/verify-sample", json={
        "code": code,
        "language": "python",
        "sample_input": "",
        "expected_output": "10"
    })
    assert res.status_code == 200
    assert res.json()["is_match"] is False

    # Exact match with trailing newline tolerance
    res_exact = client.post("/api/verify-sample", json={
        "code": code,
        "language": "python",
        "sample_input": "",
        "expected_output": "100\n"
    })
    assert res_exact.status_code == 200
    assert res_exact.json()["is_match"] is True

# Test 17: Analysis accuracy
def test_17_analysis_accuracy():
    code = """
def factorial(n: int) -> int:
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""
    analyzer = PythonAnalyzer()
    res = analyzer.analyze(code)
    assert "factorial" in res.overview.lower() or "function" in res.overview.lower()
    var_names = [v.name for v in res.variables_functions]
    assert "factorial" in var_names
    assert "result" in var_names
    assert res.complexity.time in ("O(n)", "O(N)")

# Test 18: Chat context retention
def test_18_chat_context_retention():
    # Create session
    s_res = client.post("/api/sessions", json={"title": "Chat Context Test", "code": "x = 42\nprint(x)", "language": "python"})
    s_id = s_res.json()["id"]

    # Send message 1
    m1 = client.post(f"/api/sessions/{s_id}/chat", json={"message": "What is the variable x initialized to?"})
    assert m1.status_code == 200

    # Send follow up message 2
    m2 = client.post(f"/api/sessions/{s_id}/chat", json={"message": "Show a dry run of this"})
    assert m2.status_code == 200
    assert len(m2.json()["content"]) > 10

# Test 19: Viva questions generation
def test_19_viva_questions_generation():
    analyzer = PythonAnalyzer()
    code = "def is_even(n):\n    return n % 2 == 0"
    res = analyzer.analyze(code)
    assert len(res.viva_questions) > 0
    assert any("modulo" in q.question.lower() or "parity" in q.concept.lower() for q in res.viva_questions)

# Test 20: Database persistence
def test_20_database_persistence():
    unique_title = f"Persistence Test {uuid.uuid4().hex[:8]}"
    create_res = client.post("/api/sessions", json={"title": unique_title, "code": "val = 99", "language": "python"})
    s_id = create_res.json()["id"]

    # Fetch detail
    fetch_res = client.get(f"/api/sessions/{s_id}")
    assert fetch_res.status_code == 200
    assert fetch_res.json()["title"] == unique_title
    assert fetch_res.json()["versions"][0]["code"] == "val = 99"

# Test 21: Authentication failures
def test_21_authentication_failures():
    # Wrong password
    res_bad_pw = client.post("/api/auth/login", json={"email": "demo@codewise.dev", "password": "WrongPassword!"})
    assert res_bad_pw.status_code == 401

    # Protected route without token
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.status_code == 401

# Test 22: Session expiration and invalid tokens
def test_22_invalid_tokens():
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer totally-invalid-token-12345"})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()

# Test 23: Cross-user access restrictions (IDOR prevention)
def test_23_cross_user_access_restrictions():
    # Register User A
    user_a_email = f"usera_{uuid.uuid4().hex[:6]}@codewise.dev"
    reg_a = client.post("/api/auth/register", json={
        "name": "User A", "email": user_a_email, "password": "UserAPassword2026!", "confirm_password": "UserAPassword2026!"
    })
    token_a = reg_a.json()["token"]

    # Register User B
    user_b_email = f"userb_{uuid.uuid4().hex[:6]}@codewise.dev"
    reg_b = client.post("/api/auth/register", json={
        "name": "User B", "email": user_b_email, "password": "UserBPassword2026!", "confirm_password": "UserBPassword2026!"
    })
    token_b = reg_b.json()["token"]

    # User A creates a private session
    create_res = client.post(
        "/api/sessions",
        json={"title": "User A Secret", "code": "secret_data = 123", "language": "python"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    secret_session_id = create_res.json()["id"]

    # User B attempts to access User A's session -> must be rejected with HTTP 403 Forbidden
    get_res = client.get(f"/api/sessions/{secret_session_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_res.status_code == 403

    # User B attempts to update User A's session -> must be rejected with HTTP 403
    patch_res = client.patch(
        f"/api/sessions/{secret_session_id}",
        json={"title": "Hacked Title"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert patch_res.status_code == 403

    # User B attempts to delete User A's session -> must be rejected with HTTP 403
    del_res = client.delete(f"/api/sessions/{secret_session_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_res.status_code == 403

# Test 24: Invalid backup uploads
def test_24_invalid_backup_uploads():
    # Malformed non-object JSON
    res_bad = client.post("/api/sessions/import/all", json={"data": "not a dictionary"})
    assert res_bad.status_code == 400

    # Malformed sessions array
    res_bad_arr = client.post("/api/sessions/import/all", json={"data": {"sessions": "not a list"}})
    assert res_bad_arr.status_code == 400

# Test 25: Backend execution engine status
def test_25_backend_execution_engine_status():
    # Empty code execution
    res_empty = client.post("/api/run", json={"code": "   ", "language": "python"})
    assert res_empty.status_code == 200
    assert res_empty.json()["status"] == "empty_code"

    # System status endpoint check
    res_sys = client.get("/api/system/status")
    assert res_sys.status_code == 200
    assert res_sys.json()["status"] in ("ok", "healthy")
    assert "python_version" in res_sys.json()
