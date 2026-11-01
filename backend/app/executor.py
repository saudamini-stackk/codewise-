import subprocess
import tempfile
import time
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from .detector import LANGUAGES_REGISTRY

MAX_OUTPUT_BYTES = 65536  # 64 KB output limit to prevent memory exhaustion
DEFAULT_TIMEOUT_SEC = 5.0

def get_sanitized_env(tmpdir: Path) -> Dict[str, str]:
    """
    Returns an isolated, sanitized environment dictionary.
    Completely scrubs any application secrets, API keys, or project environment variables.
    """
    safe_path = "/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
    return {
        "PATH": safe_path,
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "HOME": str(tmpdir),
        "TMPDIR": str(tmpdir),
        "PYTHONPATH": "",
        "NODE_PATH": ""
    }

def truncate_output(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncates output safely if it exceeds the maximum byte limit."""
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) > max_bytes:
        truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
        return truncated + "\n[Output truncated: exceeded 64 KB limit]"
    return text

def check_binary_available(binary_name: str) -> bool:
    """Checks if a binary is genuinely available in the safe PATH."""
    return shutil.which(binary_name) is not None

def is_java_available() -> bool:
    """Checks if a genuine Java compiler (javac) is available and functional."""
    try:
        proc = subprocess.run(["javac", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2.0)
        return proc.returncode == 0
    except Exception:
        return False

def is_node_ts_available() -> bool:
    """Checks if Node.js can execute TypeScript directly."""
    try:
        proc = subprocess.run(["node", "-e", "const x: number = 1;"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2.0)
        return proc.returncode == 0
    except Exception:
        return False

def get_host_runtime_capabilities() -> Dict[str, Dict[str, Any]]:
    """Probes and returns the genuine runtime capability status on this host."""
    has_python = check_binary_available("python3")
    has_node = check_binary_available("node")
    has_node_ts = has_node and is_node_ts_available()
    has_clang = check_binary_available("clang") or check_binary_available("gcc")
    has_clangpp = check_binary_available("clang++") or check_binary_available("g++")
    has_bash = check_binary_available("bash")
    has_ruby = check_binary_available("ruby")
    has_java = is_java_available()
    has_dotnet = check_binary_available("dotnet")
    has_go = check_binary_available("go")
    has_rust = check_binary_available("rustc")
    has_php = check_binary_available("php")
    has_kotlin = check_binary_available("kotlinc")

    return {
        "python": {"available": has_python, "runtime": "Python 3 (python3)", "missing_reason": "Python 3 interpreter not found"},
        "javascript": {"available": has_node, "runtime": "Node.js (node)", "missing_reason": "Node.js runtime not found"},
        "typescript": {"available": has_node_ts, "runtime": "Node.js (node >= 22.6 with native type-stripping)", "missing_reason": "TypeScript runtime not found"},
        "c": {"available": has_clang, "runtime": "Clang / GCC (clang)", "missing_reason": "C compiler (clang/gcc) not found"},
        "cpp": {"available": has_clangpp, "runtime": "Clang++ / G++ (clang++)", "missing_reason": "C++ compiler (clang++/g++) not found"},
        "bash": {"available": has_bash, "runtime": "GNU Bash (/bin/bash)", "missing_reason": "Bash shell not found"},
        "ruby": {"available": has_ruby, "runtime": "Ruby Interpreter (ruby)", "missing_reason": "Ruby interpreter not found"},
        "java": {"available": has_java, "runtime": "Java Development Kit (javac & java)", "missing_reason": "Java Development Kit (JDK/JRE) not installed"},
        "csharp": {"available": has_dotnet, "runtime": ".NET SDK (dotnet)", "missing_reason": ".NET SDK not installed"},
        "go": {"available": has_go, "runtime": "Go Compiler (go)", "missing_reason": "Go compiler not installed"},
        "rust": {"available": has_rust, "runtime": "Rust Compiler (rustc)", "missing_reason": "Rust compiler not installed"},
        "php": {"available": has_php, "runtime": "PHP CLI (php)", "missing_reason": "PHP CLI not installed"},
        "kotlin": {"available": has_kotlin, "runtime": "Kotlin Compiler (kotlinc)", "missing_reason": "Kotlin compiler not installed"},
        "swift": {"available": False, "runtime": "Apple Swift Compiler", "missing_reason": "Swift runtime unavailable: macOS CommandLineTools SDK mismatch"}
    }

def set_sandbox_limits() -> None:
    """Sets OS-level resource limits for the sandboxed child process."""
    try:
        import resource
        # Limit CPU time to 6 seconds (soft) / 8 seconds (hard)
        resource.setrlimit(resource.RLIMIT_CPU, (6, 8))
        # Limit maximum file size created to 10 MB to prevent disk exhaustion
        max_fsize = 10 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_fsize, max_fsize))
    except Exception:
        pass

class CodeExecutor:
    @staticmethod
    def run(code: str, language: str, input_data: str = "", timeout: float = DEFAULT_TIMEOUT_SEC) -> Dict[str, Any]:
        start_time = time.time()
        lang = (language or "").lower().strip()

        # 1. Validation: Empty Code
        if not code or not code.strip():
            return {
                "stdout": "",
                "stderr": "Error: Cannot execute empty source code.",
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "empty_code"
            }

        # 2. Honest Handling for Non-Executable Formats
        if lang in {"html", "css", "scss"}:
            return {
                "stdout": "",
                "stderr": (
                    f"Execution is unavailable for {lang.upper()}.\n"
                    f"Markup and style sheet formats are not standalone executable binaries.\n"
                    f"Tip: Use the 'Preview' action to inspect live visual rendering in a secure sandboxed iframe."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "unsupported_runtime"
            }

        if lang == "sql":
            return {
                "stdout": "",
                "stderr": (
                    "Execution is unavailable for SQL.\n"
                    "SQL queries require an active relational database instance (e.g., PostgreSQL, SQLite, MySQL) with provisioned tables.\n"
                    "Tip: Use 'Analyse Code' to inspect query logic, table joins, index considerations, and potential pitfalls."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "unsupported_runtime"
            }

        if lang in {"json", "yaml", "xml", "toml"}:
            return {
                "stdout": "",
                "stderr": (
                    f"Execution is unavailable for {lang.upper()}.\n"
                    f"Data serialization formats do not execute instructions.\n"
                    f"Tip: Use 'Analyse Code' to validate structural syntax and schema hierarchy."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "unsupported_runtime"
            }

        if lang in {"markdown", "dockerfile"}:
            return {
                "stdout": "",
                "stderr": (
                    f"Execution is unavailable for {lang.capitalize()}.\n"
                    f"Document and container specification files cannot be run as standalone scripts.\n"
                    f"Tip: Use 'Analyse Code' to review structure, build layers, and security practices."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "unsupported_runtime"
            }

        # 3. Honest Runtime Checks for Languages Without Real Host Runtimes
        if lang in {"java", "class", "jar"}:
            if not is_java_available():
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for Java.\n"
                        "The host machine does not have a functional Java Runtime Environment (JRE/JDK) installed.\n"
                        "(macOS /usr/bin/java and /usr/bin/javac are system shims that require installing OpenJDK or Oracle JDK).\n\n"
                        "Note: Full static code analysis, structure inspection, and logic breakdown are fully available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        if lang in {"csharp", "cs"}:
            if not check_binary_available("dotnet"):
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for C#.\n"
                        "The .NET SDK (dotnet CLI) is not installed on the host system.\n"
                        "To execute C#, please install the .NET SDK from https://dotnet.microsoft.com/download.\n\n"
                        "Note: Full static code analysis is available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        if lang == "go":
            if not check_binary_available("go"):
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for Go.\n"
                        "The Go compiler (go) is not installed on the host system.\n"
                        "To execute Go code, please install Go from https://go.dev/dl/.\n\n"
                        "Note: Full static code analysis is available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        if lang in {"rust", "rs"}:
            if not check_binary_available("rustc"):
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for Rust.\n"
                        "The Rust compiler (rustc / cargo) is not installed on the host system.\n"
                        "To execute Rust, please install Rust from https://rustup.rs/.\n\n"
                        "Note: Full static code analysis is available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        if lang == "php":
            if not check_binary_available("php"):
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for PHP.\n"
                        "The PHP command-line interpreter (php) is not installed on the host system.\n\n"
                        "Note: Full static code analysis is available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        if lang in {"kotlin", "kt"}:
            if not check_binary_available("kotlinc"):
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for Kotlin.\n"
                        "The Kotlin compiler (kotlinc) is not installed on the host system.\n\n"
                        "Note: Full static code analysis is available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        if lang == "swift":
            return {
                "stdout": "",
                "stderr": (
                    "Execution is unavailable for Swift.\n"
                    "The Swift runtime is unavailable due to an Apple CommandLineTools SDK mismatch.\n\n"
                    "Note: Full static code analysis is available."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "runtime_missing"
            }

        if lang in {"jsx", "tsx"}:
            return {
                "stdout": "",
                "stderr": (
                    f"Direct execution is unavailable for React {lang.upper()}.\n"
                    f"{lang.upper()} requires a React runtime bundling pipeline (e.g. Vite, Webpack, or Babel).\n"
                    f"Tip: Use 'Analyse Code' to inspect component state, props, and structure."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "unsupported_runtime"
            }

        if lang in {"typescript", "ts"}:
            if not check_binary_available("node"):
                return {
                    "stdout": "",
                    "stderr": (
                        "Execution is unavailable for TypeScript.\n"
                        "A compatible Node.js runtime was not found.\n\n"
                        "Note: Full static code analysis is available."
                    ),
                    "exit_code": 1,
                    "execution_time_ms": 0,
                    "status": "runtime_missing"
                }

        # 4. Unknown Language Check
        known_supported_exec = {"python", "py", "javascript", "js", "typescript", "ts", "cpp", "c++", "c", "bash", "sh", "ruby", "rb"}
        if is_java_available():
            known_supported_exec.update({"java", "class", "jar"})

        if lang not in known_supported_exec:
            return {
                "stdout": "",
                "stderr": (
                    f"Execution is unavailable for language '{language}'.\n"
                    f"Supported execution environments on this host: Python 3, Node.js (JavaScript & TypeScript), C (Clang), C++ (Clang C++17), Bash, Ruby.\n"
                    f"Note: Safe code analysis is fully supported for all languages."
                ),
                "exit_code": 1,
                "execution_time_ms": 0,
                "status": "unsupported_language"
            }

        # 5. Isolated Sandbox Execution for Verified Runtimes
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            env = get_sanitized_env(tmppath)

            try:
                # Python
                if lang in {"python", "py"}:
                    script_file = tmppath / "code.py"
                    script_file.write_text(code, encoding="utf-8")

                    # In an interactive terminal, user stdin is echoed to stdout immediately
                    # following the prompt on the same line, followed by a newline from pressing Enter.
                    # In a headless subprocess pipe, stdin is not echoed by the OS line discipline.
                    # Using sitecustomize ensures builtins.input() faithfully echoes the supplied
                    # input and trailing newline in exact execution order, preserving all stdout,
                    # stderr, tracebacks, line numbers, and multiple input()/print() calls.
                    sitecustomize_file = tmppath / "sitecustomize.py"
                    sitecustomize_file.write_text(
                        "import builtins, sys\n"
                        "_orig_input = builtins.input\n\n"
                        "def _echoing_input(prompt=''):\n"
                        "    val = _orig_input(prompt)\n"
                        "    sys.stdout.write(f'{val}\\n')\n"
                        "    sys.stdout.flush()\n"
                        "    return val\n\n"
                        "builtins.input = _echoing_input\n",
                        encoding="utf-8"
                    )
                    env["PYTHONPATH"] = str(tmppath) + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
                    cmd = ["python3", "-u", str(script_file)]

                # JavaScript (Node.js)
                elif lang in {"javascript", "js"}:
                    script_file = tmppath / "code.js"
                    script_file.write_text(code, encoding="utf-8")
                    cmd = ["node", str(script_file)]

                # TypeScript (Node.js)
                elif lang in {"typescript", "ts"}:
                    script_file = tmppath / "code.ts"
                    script_file.write_text(code, encoding="utf-8")
                    cmd = ["node", str(script_file)]

                # Java (when JDK is available)
                elif lang in {"java", "class", "jar"}:
                    import re
                    match = re.search(r"\bpublic\s+(final\s+)?class\s+([A-Za-z0-9_]+)", code)
                    class_name = match.group(2) if match else None
                    if not class_name:
                        match_any = re.search(r"\bclass\s+([A-Za-z0-9_]+)", code)
                        class_name = match_any.group(1) if match_any else "Main"

                    src_file = tmppath / f"{class_name}.java"
                    src_file.write_text(code, encoding="utf-8")

                    compile_proc = subprocess.run(
                        ["javac", str(src_file)],
                        capture_output=True,
                        text=True,
                        cwd=str(tmppath),
                        env=env,
                        preexec_fn=set_sandbox_limits,
                        timeout=8.0
                    )

                    if compile_proc.returncode != 0:
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        return {
                            "stdout": "",
                            "stderr": truncate_output(f"Compilation Error:\n{compile_proc.stderr}"),
                            "exit_code": compile_proc.returncode,
                            "execution_time_ms": elapsed_ms,
                            "status": "compilation_error"
                        }

                    cmd = ["java", class_name]

                # Bash / Shell Scripting
                elif lang in {"bash", "sh"}:
                    script_file = tmppath / "script.sh"
                    script_file.write_text(code, encoding="utf-8")
                    cmd = ["/bin/bash", str(script_file)]

                # Ruby
                elif lang in {"ruby", "rb"}:
                    script_file = tmppath / "code.rb"
                    script_file.write_text(code, encoding="utf-8")
                    cmd = ["ruby", str(script_file)]

                # C and C++ (Compiles with Clang, then executes binary)
                elif lang in {"cpp", "c++", "c"}:
                    is_c = lang == "c"
                    src_file = tmppath / ("code.c" if is_c else "code.cpp")
                    bin_file = tmppath / "run.out"
                    src_file.write_text(code, encoding="utf-8")

                    compiler = ["clang", "-O2"] if is_c else ["clang++", "-std=c++17", "-O2"]
                    compile_cmd = compiler + [str(src_file), "-o", str(bin_file)]

                    compile_proc = subprocess.run(
                        compile_cmd,
                        capture_output=True,
                        text=True,
                        cwd=str(tmppath),
                        env=env,
                        preexec_fn=set_sandbox_limits,
                        timeout=8.0
                    )

                    if compile_proc.returncode != 0:
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        return {
                            "stdout": "",
                            "stderr": truncate_output(f"Compilation Error:\n{compile_proc.stderr}"),
                            "exit_code": compile_proc.returncode,
                            "execution_time_ms": elapsed_ms,
                            "status": "compilation_error"
                        }

                    cmd = [str(bin_file)]

                # Normalize line endings and ensure interactive standard input terminates with a newline so input() reads a complete line
                clean_input = (input_data or "").replace("\r\n", "\n").replace("\r", "\n")
                if clean_input and not clean_input.endswith("\n"):
                    clean_input += "\n"

                # Execute with strict sandbox parameters and resource limits
                proc = subprocess.run(
                    cmd,
                    input=clean_input,
                    capture_output=True,
                    text=True,
                    cwd=str(tmppath),
                    env=env,
                    preexec_fn=set_sandbox_limits,
                    timeout=timeout
                )

                elapsed_ms = int((time.time() - start_time) * 1000)
                return {
                    "stdout": truncate_output(proc.stdout),
                    "stderr": truncate_output(proc.stderr),
                    "exit_code": proc.returncode,
                    "execution_time_ms": elapsed_ms,
                    "status": "success" if proc.returncode == 0 else "error"
                }

            except subprocess.TimeoutExpired:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return {
                    "stdout": "",
                    "stderr": (
                        f"Execution timed out after {timeout} seconds.\n"
                        f"Possible infinite loop detected (e.g. 'while True' without termination) "
                        f"or unfulfilled interactive input request."
                    ),
                    "exit_code": 124,
                    "execution_time_ms": elapsed_ms,
                    "status": "timeout"
                }
            except Exception as exc:
                elapsed_ms = int((time.time() - start_time) * 1000)
                return {
                    "stdout": "",
                    "stderr": f"Runtime execution failed: {str(exc)}",
                    "exit_code": 1,
                    "execution_time_ms": elapsed_ms,
                    "status": "error"
                }
