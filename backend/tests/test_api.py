from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["product"] == "codewise"

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["product_name"] == "codewise"
    assert "status" in data

def test_samples_endpoint():
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) >= 3
    assert any(s["language"] == "python" for s in samples)
    assert any(s["language"] == "javascript" for s in samples)
    assert any(s["language"] == "cpp" for s in samples)

def test_analyze_and_chat_flow():
    # 1. Analyze python code
    payload = {
        "code": "x = 42\nprint('Answer is', x)",
        "language": "python",
        "filename": "answer.py"
    }
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200
    analysis_data = res.json()
    assert "session_id" in analysis_data
    session_id = analysis_data["session_id"]
    version_id = analysis_data["version_id"]
    assert analysis_data["analysis"]["complexity"]["time"] == "O(1)"

    # 2. Get session details
    sess_res = client.get(f"/api/sessions/{session_id}")
    assert sess_res.status_code == 200
    sess_data = sess_res.json()
    assert len(sess_data["versions"]) == 1

    # 3. Ask follow-up question
    chat_payload = {
        "message": "can you show a dry run?",
        "session_id": session_id,
        "code_version_id": version_id
    }
    chat_res = client.post(f"/api/sessions/{session_id}/chat", json=chat_payload)
    assert chat_res.status_code == 200
    msg = chat_res.json()
    assert msg["role"] == "assistant"
    assert len(msg["content"]) > 10

    # 4. Check session messages updated
    sess_res2 = client.get(f"/api/sessions/{session_id}")
    assert len(sess_res2.json()["messages"]) >= 2

def test_code_execution_python():
    payload = {
        "code": 'print("hello from codewise")',
        "language": "python"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "hello from codewise" in data["stdout"]
    assert data["exit_code"] == 0
    assert data["status"] == "success"
    assert data["execution_time_ms"] >= 0

def test_code_execution_js():
    payload = {
        "code": 'console.log("hello from codewise")',
        "language": "javascript"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "hello from codewise" in data["stdout"]
    assert data["exit_code"] == 0
    assert data["status"] == "success"

def test_code_execution_cpp():
    payload = {
        "code": '#include <iostream>\nint main() { std::cout << "hello from codewise"; return 0; }',
        "language": "cpp"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "hello from codewise" in data["stdout"]
    assert data["exit_code"] == 0
    assert data["status"] == "success"

def test_code_execution_runtime_error():
    payload = {
        "code": "x = 1 / 0",
        "language": "python"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["exit_code"] != 0
    assert "ZeroDivisionError" in data["stderr"]
    assert data["status"] == "error"

def test_code_execution_timeout():
    payload = {
        "code": "import time\nwhile True:\n    time.sleep(0.1)",
        "language": "python"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "timeout"
    assert data["exit_code"] == 124
    assert "timed out" in data["stderr"].lower()

def test_code_execution_empty_code():
    payload = {
        "code": "   ",
        "language": "python"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "empty_code"
    assert data["exit_code"] == 1
    assert "empty" in data["stderr"].lower()

def test_code_execution_unsupported_language():
    payload = {
        "code": "program Hello; begin writeln('Hello'); end.",
        "language": "pascal"
    }
    res = client.post("/api/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "unsupported_language"
    assert data["exit_code"] == 1
    assert "unavailable for language 'pascal'" in data["stderr"]

def test_languages_endpoint():
    res = client.get("/api/languages")
    assert res.status_code == 200
    languages = res.json()
    assert len(languages) >= 20
    ids = [l["id"] for l in languages]
    for expected in ["python", "javascript", "typescript", "java", "c", "cpp", "csharp", "go", "rust", "php", "ruby", "kotlin", "swift", "bash", "html", "css", "scss", "sql", "json", "xml", "yaml", "markdown", "toml", "dockerfile"]:
        assert expected in ids

def test_java_analysis_and_honest_runtime_rejection():
    java_code = """
    public class BubbleSort {
        public static void sort(int[] arr) {
            for (int i = 0; i < arr.length; i++) {
                for (int j = 0; j < arr.length - 1; j++) {
                    if (arr[j] > arr[j + 1]) {
                        int temp = arr[j];
                        arr[j] = arr[j + 1];
                        arr[j + 1] = temp;
                    }
                }
            }
        }
        public static void main(String[] args) {
            System.out.println("Sorting array");
        }
    }
    """
    # 1. Test Analysis works fully
    res = client.post("/api/analyze", json={"code": java_code, "language": "java", "filename": "BubbleSort.java"})
    assert res.status_code == 200
    data = res.json()
    assert "BubbleSort" in data["analysis"]["overview"]
    assert "O(N²)" in data["analysis"]["complexity"]["time"]
    assert any("BubbleSort" in v["name"] for v in data["analysis"]["variables_functions"])

    # 2. Test Execution honestly reports missing JRE/JDK on host
    run_res = client.post("/api/run", json={"code": java_code, "language": "java"})
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "runtime_missing"
    assert "Java Runtime Environment" in run_data["stderr"]

def test_html_analysis():
    html_code = """<!DOCTYPE html>
    <html lang="en">
    <head><title>Test Page</title></head>
    <body>
        <h1>Hello World</h1>
        <img src="pic.jpg">
    </body>
    </html>"""
    res = client.post("/api/analyze", json={"code": html_code, "language": "html", "filename": "index.html"})
    assert res.status_code == 200
    data = res.json()
    assert "HTML" in data["analysis"]["overview"]
    assert data["analysis"]["complexity"]["time"].startswith("N/A")
    # Verify accessibility warning for img without alt was detected!
    assert any("alt" in d["explanation"].lower() for d in data["analysis"]["diagnostics"])

def test_css_analysis():
    css_code = """
    :root { --main-bg: #111; }
    .container {
        display: flex;
        justify-content: center;
        margin: 0px;
        color: red !important;
    }
    """
    res = client.post("/api/analyze", json={"code": css_code, "language": "css", "filename": "styles.css"})
    assert res.status_code == 200
    data = res.json()
    assert "CSS" in data["analysis"]["overview"]
    assert data["analysis"]["complexity"]["time"].startswith("N/A")
    assert any(".container" in v["name"] for v in data["analysis"]["variables_functions"])
    # Verify zero units check was detected (0px)
    assert any("0px" in d["explanation"].lower() or "zero" in d["title"].lower() for d in data["analysis"]["diagnostics"])

def test_sql_query_explanation():
    sql_code = """
    SELECT u.id, u.email, COUNT(o.id) as order_count
    FROM users u
    INNER JOIN orders o ON u.id = o.user_id
    WHERE o.status = 'active'
    GROUP BY u.id, u.email
    HAVING COUNT(o.id) > 5
    ORDER BY order_count DESC;
    """
    res = client.post("/api/analyze", json={"code": sql_code, "language": "sql", "filename": "orders.sql"})
    assert res.status_code == 200
    data = res.json()
    assert "users" in data["analysis"]["overview"] or "orders" in data["analysis"]["overview"]
    assert any("JOIN" in v["name"] for v in data["analysis"]["variables_functions"])
    assert any("COUNT" in v["name"] for v in data["analysis"]["variables_functions"])
    assert "FROM & JOIN" in data["analysis"]["logic_workflow"]

def test_json_valid_and_invalid():
    # Valid JSON
    valid_json = '{"name": "Codewise", "version": "2.0", "active": true, "items": [1, 2, 3]}'
    res1 = client.post("/api/analyze", json={"code": valid_json, "language": "json", "filename": "data.json"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert "Valid JSON" in data1["analysis"]["overview"]
    assert any("name" in v["name"] for v in data1["analysis"]["variables_functions"])
    assert len(data1["analysis"]["diagnostics"]) == 0

    # Invalid JSON (missing double quotes around key, trailing comma)
    invalid_json = '{\n  name: "Codewise",\n  "active": true,\n}'
    res2 = client.post("/api/analyze", json={"code": invalid_json, "language": "json", "filename": "bad.json"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["analysis"]["diagnostics"]) >= 1
    assert data2["analysis"]["diagnostics"][0]["severity"] == "error"
    assert "syntax error" in data2["analysis"]["diagnostics"][0]["title"].lower()

def test_auto_detection_endpoint():
    # 1. Detect Dockerfile from content
    dockerfile_content = "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"app.py\"]"
    res1 = client.post("/api/detect-language", json={"code": dockerfile_content})
    assert res1.status_code == 200
    assert res1.json()["detected_language"] == "dockerfile"

    # 2. Detect Rust from content
    rust_content = "fn main() {\n    let mut x = 5;\n    println!(\"{}\", x);\n}"
    res2 = client.post("/api/detect-language", json={"code": rust_content})
    assert res2.status_code == 200
    assert res2.json()["detected_language"] == "rust"

    # 3. Detect from file extension (.sql)
    res3 = client.post("/api/detect-language", json={"code": "SELECT 1;", "filename": "query.sql"})
    assert res3.status_code == 200
    assert res3.json()["detected_language"] == "sql"

    # 4. Detect Java, Python, JavaScript, C++
    res_java = client.post("/api/detect-language", json={
        "code": "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Hello\");\n    }\n}"
    })
    assert res_java.status_code == 200
    assert res_java.json()["detected_language"] == "java"
    assert res_java.json()["confidence"] == "high"

    res_py = client.post("/api/detect-language", json={
        "code": "number = int(input(\"enter: \"))\nif number % 2 == 0:\n    print(\"even\")"
    })
    assert res_py.status_code == 200
    assert res_py.json()["detected_language"] == "python"
    assert res_py.json()["confidence"] == "high"

    res_js = client.post("/api/detect-language", json={
        "code": "const x = 5;\nconsole.log(x * 2);"
    })
    assert res_js.status_code == 200
    assert res_js.json()["detected_language"] == "javascript"
    assert res_js.json()["confidence"] == "high"

    res_cpp = client.post("/api/detect-language", json={
        "code": "#include <iostream>\nint main() {\n    std::cout << \"Hello C++\" << std::endl;\n    return 0;\n}"
    })
    assert res_cpp.status_code == 200
    assert res_cpp.json()["detected_language"] == "cpp"
    assert res_cpp.json()["confidence"] == "high"

    # 5. Empty code and ambiguous code should return uncertain instead of guessing Python
    res_empty = client.post("/api/detect-language", json={"code": ""})
    assert res_empty.status_code == 200
    assert res_empty.json()["detected_language"] is None
    assert res_empty.json()["confidence"] == "uncertain"

    res_ambiguous = client.post("/api/detect-language", json={"code": "x = 10"})
    assert res_ambiguous.status_code == 200
    assert res_ambiguous.json()["detected_language"] is None
    assert res_ambiguous.json()["confidence"] == "uncertain"

    # 6. Analyze with "auto"
    res4 = client.post("/api/analyze", json={"code": "echo 'Deploying application'", "language": "auto", "filename": "deploy.sh"})
    assert res4.status_code == 200
    assert res4.json()["language"] == "bash"

def test_file_explorer_and_versioning_rules():
    # 1. Create a new runnable file
    create_res = client.post("/api/sessions", json={
        "filename": "calc.py",
        "language": "python",
        "code": "def add(a, b):\n    return a + b\n"
    })
    assert create_res.status_code == 200
    file_info = create_res.json()
    session_id = file_info["id"]
    assert file_info["filename"] == "calc.py"
    assert file_info["is_runnable"] is True
    assert file_info["version_count"] == 1

    # 2. Analyze the file (should update v1 analysis without creating a new session or version)
    sess_detail = client.get(f"/api/sessions/{session_id}").json()
    v1_id = sess_detail["versions"][0]["id"]
    analyze_res = client.post("/api/analyze", json={
        "code": "def add(a, b):\n    return a + b\n",
        "language": "python",
        "filename": "calc.py",
        "session_id": session_id,
        "code_version_id": v1_id
    })
    assert analyze_res.status_code == 200
    assert analyze_res.json()["session_id"] == session_id
    assert analyze_res.json()["code_version_id"] == v1_id

    # Verify no new versions created
    sess_after_analyze = client.get(f"/api/sessions/{session_id}").json()
    assert len(sess_after_analyze["versions"]) == 1
    assert sess_after_analyze["versions"][0]["analysis"] is not None

    # 3. Save identical code (Rule B: Unchanged content creates NO duplicate version)
    save_same_res = client.post(f"/api/sessions/{session_id}/versions", json={
        "code": "def add(a, b):\n    return a + b\n",
        "language": "python"
    })
    assert save_same_res.status_code == 200
    assert save_same_res.json()["version_number"] == 1
    sess_after_save_same = client.get(f"/api/sessions/{session_id}").json()
    assert len(sess_after_save_same["versions"]) == 1

    # 4. Save modified code (Edits create v2)
    save_mod_res = client.post(f"/api/sessions/{session_id}/versions", json={
        "code": "def add(a, b):\n    return a + b + 1  # buggy\n",
        "language": "python"
    })
    assert save_mod_res.status_code == 200
    assert save_mod_res.json()["version_number"] == 2
    sess_after_mod = client.get(f"/api/sessions/{session_id}").json()
    assert len(sess_after_mod["versions"]) == 2

    # 5. Restore v1 (creates v3 with v1's code)
    restore_res = client.post(f"/api/sessions/{session_id}/restore", json={
        "version_number": 1
    })
    assert restore_res.status_code == 200
    assert restore_res.json()["version_number"] == 3
    assert restore_res.json()["code"] == "def add(a, b):\n    return a + b\n"
    sess_after_restore = client.get(f"/api/sessions/{session_id}").json()
    assert len(sess_after_restore["versions"]) == 3

    # 6. Duplicate file
    dup_res = client.post(f"/api/sessions/{session_id}/duplicate")
    assert dup_res.status_code == 200
    dup_file = dup_res.json()
    assert "calc_copy.py" in dup_file["filename"]
    assert dup_file["id"] != session_id

    # 7. Category filtering (runnable vs documents)
    # Create a non-runnable document
    doc_res = client.post("/api/sessions", json={
        "filename": "config.yaml",
        "language": "yaml",
        "code": "app: codewise\nversion: 2.0"
    })
    assert doc_res.status_code == 200
    assert doc_res.json()["is_runnable"] is False

    runnable_list = client.get("/api/sessions?category=runnable").json()
    assert any(s["id"] == session_id for s in runnable_list)
    assert not any(s["id"] == doc_res.json()["id"] for s in runnable_list)

    doc_list = client.get("/api/sessions?category=documents").json()
    assert any(s["id"] == doc_res.json()["id"] for s in doc_list)
    assert not any(s["id"] == session_id for s in doc_list)


def test_execution_sandbox_security_and_limits():
    """Verify sandbox isolates environment variables, limits output size, and enforces timeouts."""
    import os
    os.environ["SECRET_KEY_FOR_TEST"] = "super_secret_codewise_val"
    try:
        # 1. Environment scrubbing check
        res = client.post("/api/run", json={
            "code": "import os; print('SECRET_FOUND' if 'SECRET_KEY_FOR_TEST' in os.environ else 'CLEAN_ENV')",
            "language": "python"
        })
        assert res.status_code == 200
        assert "CLEAN_ENV" in res.json()["stdout"]
        assert "SECRET_FOUND" not in res.json()["stdout"]

        # 2. Output truncation (64 KB limit)
        res_large = client.post("/api/run", json={
            "code": "print('X' * 100000)",
            "language": "python"
        })
        assert res_large.status_code == 200
        large_stdout = res_large.json()["stdout"]
        assert "[Output truncated: exceeded 64 KB limit]" in large_stdout
        assert len(large_stdout.encode("utf-8")) <= 65600

        # 3. Safe stdin passing
        res_stdin = client.post("/api/run", json={
            "code": "val = input()\nprint('ECHO:' + val)",
            "language": "python",
            "input_data": "safe_stdin_test"
        })
        assert res_stdin.status_code == 200
        assert "ECHO:safe_stdin_test" in res_stdin.json()["stdout"]
    finally:
        os.environ.pop("SECRET_KEY_FOR_TEST", None)


def test_non_executable_formats_honesty():
    """Ensure non-runnable formats and missing runtimes produce clear, honest error explanations."""
    formats = [
        ("sql", "unsupported_runtime", "SQL"),
        ("json", "unsupported_runtime", "JSON"),
        ("yaml", "unsupported_runtime", "YAML"),
        ("markdown", "unsupported_runtime", "Markdown"),
        ("dockerfile", "unsupported_runtime", "Dockerfile"),
        ("html", "unsupported_runtime", "HTML"),
        ("css", "unsupported_runtime", "CSS"),
        ("java", "runtime_missing", "Java"),
        ("csharp", "runtime_missing", "C#"),
        ("go", "runtime_missing", "Go"),
        ("rust", "runtime_missing", "Rust"),
    ]

    for lang, expected_status, display_name in formats:
        res = client.post("/api/run", json={
            "code": "sample test content",
            "language": lang
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == expected_status, f"Expected {expected_status} for {lang}, got {data['status']}"
        assert data["exit_code"] == 1
        assert display_name.lower() in data["stderr"].lower() or lang in data["stderr"].lower()


def test_follow_up_chat_context_and_guards():
    """Test follow-up chat engine: empty message validation, 404 on missing session, and context retention."""
    # 1. Create a session
    sess_res = client.post("/api/sessions", json={
        "filename": "chat_test.py",
        "language": "python",
        "code": "def multiply(x, y):\n    return x * y\n"
    })
    assert sess_res.status_code == 200
    sid = sess_res.json()["id"]

    try:
        # 2. Empty chat guard
        empty_res = client.post(f"/api/sessions/{sid}/chat", json={"message": "   "})
        assert empty_res.status_code == 400

        # 3. Valid question
        chat_res = client.post(f"/api/sessions/{sid}/chat", json={
            "message": "What does this multiply function do?"
        })
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert chat_data["role"] == "assistant"
        assert len(chat_data["content"]) > 20

        # 4. Non-existent session
        missing_res = client.post("/api/sessions/non-existent-id/chat", json={
            "message": "Hello?"
        })
        assert missing_res.status_code == 404
    finally:
        client.delete(f"/api/sessions/{sid}")

def test_execution_console_stdin_echoing_even_odd():
    code = """number = int(input("enter a number: "))
if number % 2 == 0:
    print(f"{number} is even")
else:
    print(f"{number} is odd")"""

    # 1. input 6: "enter a number: 6" followed by "6 is even" on next line
    res6 = client.post("/api/run", json={"code": code, "language": "python", "input_data": "6"})
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["exit_code"] == 0
    assert data6["stdout"] == "enter a number: 6\n6 is even\n"

    # 2. input 7: "enter a number: 7" followed by "7 is odd" on next line
    res7 = client.post("/api/run", json={"code": code, "language": "python", "input_data": "7"})
    assert res7.status_code == 200
    data7 = res7.json()
    assert data7["exit_code"] == 0
    assert data7["stdout"] == "enter a number: 7\n7 is odd\n"

    # 3. invalid input abc: prompt + input in stdout, genuine ValueError in stderr
    res_abc = client.post("/api/run", json={"code": code, "language": "python", "input_data": "abc"})
    assert res_abc.status_code == 200
    data_abc = res_abc.json()
    assert data_abc["exit_code"] == 1
    assert data_abc["stdout"] == "enter a number: abc\n"
    assert "ValueError" in data_abc["stderr"]

def test_execution_console_multiple_inputs():
    code = """user = input("Username: ")
role = input("Role: ")
print(f"Logged in as {user} ({role})")"""
    res = client.post("/api/run", json={"code": code, "language": "python", "input_data": "admin\nengineer"})
    assert res.status_code == 200
    data = res.json()
    assert data["exit_code"] == 0
    assert data["stdout"] == "Username: admin\nRole: engineer\nLogged in as admin (engineer)\n"

def test_execution_console_no_input_print_preserved():
    code = """print("Line 1: Normal output")
print("Line 2: Preserved")"""
    res = client.post("/api/run", json={"code": code, "language": "python", "input_data": ""})
    assert res.status_code == 200
    data = res.json()
    assert data["exit_code"] == 0
    assert data["stdout"] == "Line 1: Normal output\nLine 2: Preserved\n"


