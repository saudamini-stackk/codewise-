import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.executor import CodeExecutor, get_host_runtime_capabilities, is_java_available

client = TestClient(app)

def test_capabilities_endpoint():
    """Verify central /api/capabilities endpoint returns accurate host status."""
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert "runtimes" in data
    assert "executable_languages" in data
    assert "analysis_only_formats" in data
    assert "previewable_formats" in data

    # Python, JS, TS, C, C++, Bash, Ruby are available on this host
    assert "python" in data["executable_languages"]
    assert "javascript" in data["executable_languages"]
    assert "typescript" in data["executable_languages"]
    assert "c" in data["executable_languages"]
    assert "cpp" in data["executable_languages"]
    assert "bash" in data["executable_languages"]
    assert "ruby" in data["executable_languages"]

    # Analysis-only formats are explicitly listed
    for fmt in ["json", "yaml", "xml", "sql", "markdown", "dockerfile", "toml"]:
        assert fmt in data["analysis_only_formats"]
        assert fmt not in data["executable_languages"]

    # Java is recognized as missing JRE/JDK on host
    assert "java" in data["unavailable_languages"]
    assert "JDK" in data["runtimes"]["java"]["missing_reason"]

def test_python_output_and_stdin():
    """Test Python execution with stdout and stdin."""
    code = (
        "name = input('Enter name: ')\n"
        "age = int(input('Enter age: '))\n"
        "print(f'User {name} is {age} years old.')"
    )
    res = client.post("/api/run", json={"code": code, "language": "python", "input_data": "Sauda\n25\n"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "User Sauda is 25 years old." in data["stdout"]

def test_javascript_output_and_stdin():
    """Test JavaScript Node.js execution with stdout and stdin."""
    code = (
        "const fs = require('fs');\n"
        "const input = fs.readFileSync(0, 'utf-8').trim();\n"
        "console.log('Echo from Node:', input);"
    )
    res = client.post("/api/run", json={"code": code, "language": "javascript", "input_data": "CodewiseJS\n"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "Echo from Node: CodewiseJS" in data["stdout"]

def test_typescript_execution():
    """Test TypeScript execution natively via Node.js."""
    code = (
        "interface Point { x: number; y: number; }\n"
        "const p: Point = { x: 10, y: 20 };\n"
        "const dist = (pt: Point): number => pt.x + pt.y;\n"
        "console.log('Distance:', dist(p));"
    )
    res = client.post("/api/run", json={"code": code, "language": "typescript"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "Distance: 30" in data["stdout"]

def test_c_compilation_execution_and_stdin():
    """Test C compilation and execution with clang and standard input."""
    code = (
        "#include <stdio.h>\n"
        "int main() {\n"
        "    int val;\n"
        "    if (scanf(\"%d\", &val) == 1) {\n"
        "        printf(\"Tripled: %d\\n\", val * 3);\n"
        "    }\n"
        "    return 0;\n"
        "}"
    )
    res = client.post("/api/run", json={"code": code, "language": "c", "input_data": "14\n"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "Tripled: 42" in data["stdout"]

def test_cpp_compilation_execution_and_stdin():
    """Test C++ compilation and execution with clang++ and standard input."""
    code = (
        "#include <iostream>\n"
        "#include <vector>\n"
        "int main() {\n"
        "    int n;\n"
        "    if (std::cin >> n) {\n"
        "        std::vector<int> nums;\n"
        "        for (int i = 0; i < n; i++) nums.push_back(i + 1);\n"
        "        std::cout << \"Count: \" << nums.size() << std::endl;\n"
        "    }\n"
        "    return 0;\n"
        "}"
    )
    res = client.post("/api/run", json={"code": code, "language": "cpp", "input_data": "5\n"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "Count: 5" in data["stdout"]

def test_c_and_cpp_compilation_error_handling():
    """Test that C and C++ compilation errors are captured and returned clearly."""
    bad_c = "#include <stdio.h>\nint main() { non_existent_variable = 10; return 0; }"
    res_c = client.post("/api/run", json={"code": bad_c, "language": "c"})
    assert res_c.status_code == 200
    data_c = res_c.json()
    assert data_c["status"] == "compilation_error"
    assert data_c["exit_code"] != 0
    assert "Compilation Error:" in data_c["stderr"]

    bad_cpp = "#include <iostream>\nint main() { std::cout << missing_thing << std::endl; }"
    res_cpp = client.post("/api/run", json={"code": bad_cpp, "language": "cpp"})
    assert res_cpp.status_code == 200
    data_cpp = res_cpp.json()
    assert data_cpp["status"] == "compilation_error"
    assert "Compilation Error:" in data_cpp["stderr"]

def test_bash_shell_execution():
    """Test Bash execution with stdout and stdin."""
    code = (
        "read -r line\n"
        "echo \"Shell heard: $line\"\n"
    )
    res = client.post("/api/run", json={"code": code, "language": "bash", "input_data": "Testing123\n"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "Shell heard: Testing123" in data["stdout"]

def test_ruby_execution():
    """Test Ruby execution with stdout and stdin."""
    code = (
        "val = gets.chomp\n"
        "puts \"Ruby parsed: #{val.upcase}\"\n"
    )
    res = client.post("/api/run", json={"code": code, "language": "ruby", "input_data": "gemstone\n"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert "Ruby parsed: GEMSTONE" in data["stdout"]

def test_timeout_handling():
    """Test infinite loop timeout enforcement."""
    code = "while True:\n    pass\n"
    res = client.post("/api/run", json={"code": code, "language": "python"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "timeout"
    assert data["exit_code"] == 124
    assert "timed out" in data["stderr"].lower()

def test_missing_runtime_handling():
    """Test honest explanation when a language's runtime is missing on host."""
    # Java is missing on this macOS host
    java_code = "public class Main { public static void main(String[] args) { System.out.println(1); } }"
    res_java = client.post("/api/run", json={"code": java_code, "language": "java"})
    assert res_java.status_code == 200
    data_java = res_java.json()
    assert data_java["status"] == "runtime_missing"
    assert "Java Runtime Environment" in data_java["stderr"]

    # C# is missing on this macOS host
    cs_code = "using System; class Program { static void Main() { Console.WriteLine(1); } }"
    res_cs = client.post("/api/run", json={"code": cs_code, "language": "csharp"})
    assert res_cs.status_code == 200
    data_cs = res_cs.json()
    assert data_cs["status"] == "runtime_missing"
    assert ".NET SDK" in data_cs["stderr"]

def test_analysis_only_formats_rejection_for_execution():
    """Verify that data/config/markup formats cannot be run as programs."""
    formats = [
        ("json", '{"name": "test"}'),
        ("yaml", "name: test\nversion: 1.0"),
        ("xml", "<root><item>1</item></root>"),
        ("sql", "SELECT * FROM users;"),
        ("markdown", "# Title\nParagraph text"),
        ("dockerfile", "FROM alpine\nCMD [\"echo\", \"1\"]"),
        ("toml", "[package]\nname = \"test\""),
        ("html", "<h1>Hello</h1>"),
        ("css", "body { color: red; }")
    ]
    for lang, sample in formats:
        res = client.post("/api/run", json={"code": sample, "language": lang})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "unsupported_runtime"
        assert "Execution is unavailable" in data["stderr"]

def test_regression_analysis_and_preview():
    """Regression test: verify static analysis for JSON and YAML and HTML preview data."""
    # 1. JSON analysis
    res_json = client.post("/api/analyze", json={"code": '{"id": 1, "status": "active"}', "language": "json"})
    assert res_json.status_code == 200
    assert "JSON" in res_json.json()["analysis"]["overview"]

    # 2. YAML analysis
    res_yaml = client.post("/api/analyze", json={"code": "database:\n  host: localhost\n  port: 5432", "language": "yaml"})
    assert res_yaml.status_code == 200
    assert "YAML" in res_yaml.json()["analysis"]["overview"]

    # 3. HTML analysis
    res_html = client.post("/api/analyze", json={"code": "<!DOCTYPE html><html><body><h1>Title</h1></body></html>", "language": "html"})
    assert res_html.status_code == 200
    assert "HTML" in res_html.json()["analysis"]["overview"]
