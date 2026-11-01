import re
from typing import Optional, List, Dict, Any
from ..models import (
    AnalysisResult,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    ComplexityInfo
)
from .base import BaseAnalyzer, extract_lines

class DevOpsAnalyzer(BaseAnalyzer):
    """
    Specialized analyzer for Dockerfile, Bash/Shell scripts, and Markdown documentation.
    """

    def analyze(self, code: str, filename: Optional[str] = None, language: str = "dockerfile") -> AnalysisResult:
        lang = language.lower().strip()
        if lang in {"bash", "sh", "zsh"}:
            return self._analyze_bash(code, filename)
        elif lang in {"markdown", "md"}:
            return self._analyze_markdown(code, filename)
        else:
            return self._analyze_dockerfile(code, filename)

    def _analyze_dockerfile(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []

        # Instructions parsing
        instructions = re.findall(r"^\s*(FROM|RUN|WORKDIR|COPY|ADD|ENV|ARG|EXPOSE|USER|ENTRYPOINT|CMD|VOLUME|HEALTHCHECK)\s+(.+)$", code, re.M)

        base_images = [arg for inst, arg in instructions if inst == "FROM"]
        exposed_ports = [arg for inst, arg in instructions if inst == "EXPOSE"]
        has_user = any(inst == "USER" for inst, _ in instructions)
        uses_add = any(inst == "ADD" for inst, _ in instructions)

        # Diagnostics:
        # 1. Running as root container
        if not has_user:
            diagnostics.append(DiagnosticItem(
                id="diag-docker-root-user",
                title="Container Security: Container runs as default root",
                severity="warning",
                explanation="No 'USER' directive was specified. By default, processes inside the container will execute with root privileges, increasing risk if the container is compromised.",
                recommended_correction="Create and switch to a non-privileged user before the ENTRYPOINT/CMD (e.g. USER appuser).",
                corrected_snippet="RUN useradd -m -u 1000 appuser\nUSER appuser",
                detection_type="static_docker_linter"
            ))

        # 2. Using ADD instead of COPY
        if uses_add:
            diagnostics.append(DiagnosticItem(
                id="diag-docker-use-copy",
                title="Best Practice: Prefer COPY over ADD for local files",
                severity="suggestion",
                explanation="'ADD' has implicit tar auto-extraction and remote URL download behaviors. 'COPY' is more transparent and preferred for local files.",
                recommended_correction="Replace 'ADD' with 'COPY' unless auto-tar extraction is explicitly needed.",
                detection_type="static_docker_linter"
            ))

        variables_functions: List[VariableFunctionItem] = []
        for inst, arg in instructions[:12]:
            variables_functions.append(VariableFunctionItem(
                name=inst,
                kind="Docker Instruction",
                data_type="Image Layer",
                description=f"Args: {arg[:50]}",
                scope="Build Layer"
            ))

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "Dockerfile build instruction."
            if s.startswith("#"):
                exp = "Comment documenting Docker build step."
            elif s.upper().startswith("FROM"):
                exp = f"Base image: establishes parent OS/runtime image foundation."
            elif s.upper().startswith("WORKDIR"):
                exp = "Sets active working directory inside container for subsequent instructions."
            elif s.upper().startswith("COPY"):
                exp = "Copies files from host filesystem into the container image."
            elif s.upper().startswith("RUN"):
                exp = "Executes command during image build to install packages or dependencies."
            elif s.upper().startswith("EXPOSE"):
                exp = "Documents container network ports intended for runtime publishing."
            elif s.upper().startswith("ENV"):
                exp = "Sets environment variable accessible during build and runtime."
            elif s.upper().startswith("USER"):
                exp = "Switches active security user for subsequent commands and runtime."
            elif s.upper().startswith("CMD") or s.upper().startswith("ENTRYPOINT"):
                exp = "Specifies default executable and arguments executed when container starts."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        base_img_str = f"based on {base_images[0]}" if base_images else "custom image"
        overview = (
            f"Dockerfile container specification {base_img_str} with {len(lines)} line(s) and {len(instructions)} build instructions. "
            f"{f'Exposes network port(s) {', '.join(exposed_ports)}. ' if exposed_ports else ''}"
            "Defines isolated container assembly steps for reproducible production deployment."
        )

        logic_workflow = (
            "1. Docker daemon pulls or verifies cached base image specified in FROM.\n"
            "2. Evaluates instructions sequentially, creating cached image layers for each step.\n"
            "3. Copies application artifacts into container filesystem via COPY.\n"
            "4. Executes dependency installations and build steps via RUN.\n"
            "5. Tags final container image with entrypoint/CMD ready for execution via 'docker run'."
        )

        return AnalysisResult(
            overview=overview,
            logic_workflow=logic_workflow,
            line_by_line=line_by_line[:40],
            inputs="Host project source code, base operating system images, build arguments.",
            outputs="Immutable, portable OCI/Docker container image ready for deployment.",
            variables_functions=variables_functions,
            programming_concepts=[
                "OCI Container Image Specification",
                "Immutable Layer Caching",
                "Principle of Least Privilege (USER)",
                "Microservice Packaging",
                "Cloud-Native Deployments"
            ],
            limitations=[
                "Building requires the Docker daemon or a container runtime (Podman / containerd).",
                "Unoptimized layer ordering can invalidate build caches and cause slow build times.",
                "Environment variables declared in ENV are embedded into image metadata."
            ],
            complexity=ComplexityInfo(
                time="N/A (Container Image Build)",
                space="N/A (Container Image Layers)",
                explanation="Dockerfiles are declarative container recipes; they assemble filesystem layers rather than evaluating runtime algorithms."
            ),
            learning_takeaway="To optimize Docker builds, place slow-changing dependencies (e.g. requirements.txt or package.json) BEFORE copying the entire project source to maximize build cache hits.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )

    def _analyze_bash(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []

        # Diagnostics:
        # Check for unquoted variable expansion
        unquoted = re.findall(r"\brm\s+-[rf]+\s+\$[a-zA-Z_0-9]+", code)
        if unquoted:
            diagnostics.append(DiagnosticItem(
                id="diag-bash-unquoted-rm",
                title="Critical Safety Concern: Unquoted Variable in 'rm -rf'",
                severity="error",
                explanation=f"Found unquoted variable in destructive command: '{unquoted[0]}'. If the variable is unset or contains spaces, this can delete unintended root or home directories.",
                recommended_correction='Always wrap variables in double quotes: rm -rf "$VAR"',
                detection_type="static_shell_linter"
            ))

        # Check for missing set -e
        if not re.search(r"set\s+-[a-zA-Z]*e", code):
            diagnostics.append(DiagnosticItem(
                id="diag-bash-set-e",
                title="Script Robustness: Missing 'set -e' error handling",
                severity="suggestion",
                explanation="By default, bash scripts continue running even if an intermediate command fails. Adding 'set -e' or 'set -euo pipefail' exits immediately upon error.",
                recommended_correction="Add 'set -euo pipefail' near the top of the script.",
                corrected_snippet="#!/bin/bash\nset -euo pipefail",
                detection_type="static_shell_linter"
            ))

        commands = re.findall(r"^\s*([a-zA-Z0-9_.-]+)\s+", code, re.M)
        unique_cmds = sorted(set(c for c in commands if c not in {"if", "then", "else", "elif", "fi", "for", "while", "do", "done", "case", "esac"}))

        variables_functions: List[VariableFunctionItem] = []
        for cmd in unique_cmds[:10]:
            variables_functions.append(VariableFunctionItem(
                name=cmd,
                kind="Shell Utility / Command",
                data_type="Subprocess Executable",
                description="Invoked in script pipeline or statement.",
                scope="PATH Binary"
            ))

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "Shell command or control statement."
            if s.startswith("#!"):
                exp = "Shebang line specifying the interpreter binary (/bin/bash)."
            elif s.startswith("#"):
                exp = "Comment line documenting shell automation step."
            elif s.startswith("echo "):
                exp = "Prints message or variable to standard output (stdout)."
            elif "=" in s and not s.startswith("if"):
                exp = f"Assigns shell variable '{s.split('=', 1)[0].strip()}'."
            elif s.startswith("if ") or s == "then" or s == "fi":
                exp = "Conditional branching statement evaluating command exit code or test expression."
            elif s.startswith("for ") or s.startswith("while "):
                exp = "Loop structure iterating over items or until condition is met."
            elif "|" in s:
                exp = "Pipeline operator connecting stdout of left command to stdin of right command."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        return AnalysisResult(
            overview=f"Bash shell script with {len(lines)} line(s). Automates system tasks using {len(unique_cmds)} distinct command utility invocation(s) ({', '.join(unique_cmds[:5])}).",
            logic_workflow=(
                "1. Shell interpreter initializes environment variables and positional parameters ($1, $2, etc.).\n"
                "2. Reads and parses commands sequentially or conditionally.\n"
                "3. Forks child processes to execute external binaries and connects IPC pipes (|).\n"
                "4. Evaluates exit status ($?) after each command (0 = success, non-zero = error)."
            ),
            line_by_line=line_by_line[:40],
            inputs="Standard input (stdin), environment variables, command-line arguments ($1, $2), and filesystem state.",
            outputs="Standard output (stdout), standard error (stderr), and process exit code ($?).",
            variables_functions=variables_functions,
            programming_concepts=[
                "Unix Philosophy (Composing Small Tools)",
                "Standard Streams (stdin, stdout, stderr)",
                "Process Forking & Exit Codes",
                "Pipes & Stream Redirection (>, >>, 2>&1)",
                "Variable Quoting & Word Splitting"
            ],
            limitations=[
                "Shell scripts are sensitive to operating system tool variations (e.g. GNU Linux coreutils vs BSD macOS).",
                "Lacks native high-level data structures like multidimensional arrays or complex objects.",
                "Error handling is fragile without explicit 'set -e' or error traps."
            ],
            complexity=ComplexityInfo(
                time="O(N) command sequence",
                space="O(1) shell state memory",
                explanation="Execution time is determined by external child process execution and I/O throughput."
            ),
            learning_takeaway="Always quote shell variables (\"$VAR\") to prevent accidental word splitting or wildcard glob expansion bugs.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )

    def _analyze_markdown(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        headings = re.findall(r"^(#{1,6})\s+(.+)$", code, re.M)

        variables_functions: List[VariableFunctionItem] = []
        for level, title in headings[:10]:
            variables_functions.append(VariableFunctionItem(
                name=f"{level} {title}",
                kind=f"Heading Level {len(level)}",
                data_type="Document Section",
                description=f"Outline heading in document hierarchy.",
                scope="Table of Contents"
            ))

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "Formatted text paragraph or block."
            if s.startswith("#"):
                exp = "Section heading defining document structure."
            elif s.startswith("```"):
                exp = "Fenced code block delimiter with optional syntax highlighting language."
            elif s.startswith("* ") or s.startswith("- "):
                exp = "Unordered bullet point list item."
            elif re.match(r"^\d+\.\s+", s):
                exp = "Ordered numbered list item."
            elif s.startswith(">"):
                exp = "Blockquote callout section."
            elif s.startswith("|") and s.endswith("|"):
                exp = "Markdown table row."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        return AnalysisResult(
            overview=f"Markdown documentation file containing {len(lines)} line(s) and {len(headings)} outline section(s). Formats developer documentation, READMEs, or project notes.",
            logic_workflow=(
                "1. Markdown parser scans text and recognizes formatting syntax (# headings, * lists, ```` code).\n"
                "2. Converts markdown tokens into an AST (Abstract Syntax Tree).\n"
                "3. Generates HTML elements (<h1-h6>, <ul>, <pre><code>) for browser or reader display."
            ),
            line_by_line=line_by_line[:40],
            inputs="Plain text formatted with GitHub Flavored Markdown (GFM) syntax.",
            outputs="Structured, styled documentation rendered in browsers, GitHub, or static site generators.",
            variables_functions=variables_functions,
            programming_concepts=[
                "Lightweight Markup Syntax",
                "Document Outline & Hierarchy",
                "Fenced Code Blocks & Syntax Highlighting",
                "Developer Documentation Standards"
            ],
            limitations=[
                "Markdown defines visual document presentation; it does not execute application logic.",
                "Dialect differences exist between CommonMark, GFM, and various CMS renderers."
            ],
            complexity=ComplexityInfo(
                time="N/A (Documentation)",
                space="N/A (Formatted Document)",
                explanation="Markdown documents are parsed for reading; they do not perform algorithmic calculations."
            ),
            learning_takeaway="Clear documentation is as important as clean code. Use consistent heading hierarchy and code snippets to make READMEs easy to navigate.",
            diagnostics=[],
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )
