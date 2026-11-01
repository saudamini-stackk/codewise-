import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

# Complete Language Registry
LANGUAGES_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Programming Languages
    "python": {
        "id": "python",
        "name": "Python",
        "category": "programming",
        "extensions": [".py", ".pyw"],
        "executable": True,
        "runtime_required": "Python 3 (python3)",
        "previewable": False,
        "description": "General-purpose high-level interpreted programming language."
    },
    "javascript": {
        "id": "javascript",
        "name": "JavaScript",
        "category": "programming",
        "extensions": [".js", ".mjs", ".cjs"],
        "executable": True,
        "runtime_required": "Node.js (node)",
        "previewable": False,
        "description": "Dynamic web and server-side scripting language."
    },
    "typescript": {
        "id": "typescript",
        "name": "TypeScript",
        "category": "programming",
        "extensions": [".ts", ".mts", ".cts"],
        "executable": True,
        "runtime_required": "Node.js (node with native type-stripping)",
        "previewable": False,
        "description": "Typed superset of JavaScript providing static types and compile-time checks."
    },
    "java": {
        "id": "java",
        "name": "Java",
        "category": "programming",
        "extensions": [".java"],
        "executable": False,
        "runtime_required": "Java Development Kit (javac & java)",
        "previewable": False,
        "description": "Class-based object-oriented language for enterprise and Android development."
    },
    "c": {
        "id": "c",
        "name": "C",
        "category": "programming",
        "extensions": [".c", ".h"],
        "executable": True,
        "runtime_required": "Clang / GCC (clang)",
        "previewable": False,
        "description": "Low-level procedural systems programming language."
    },
    "cpp": {
        "id": "cpp",
        "name": "C++",
        "category": "programming",
        "extensions": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
        "executable": True,
        "runtime_required": "Clang++ / G++ (clang++)",
        "previewable": False,
        "description": "High-performance systems language with object-oriented and generic features."
    },
    "csharp": {
        "id": "csharp",
        "name": "C#",
        "category": "programming",
        "extensions": [".cs"],
        "executable": False,
        "runtime_required": ".NET SDK (dotnet)",
        "previewable": False,
        "description": "Modern type-safe object-oriented language for the .NET platform."
    },
    "go": {
        "id": "go",
        "name": "Go",
        "category": "programming",
        "extensions": [".go"],
        "executable": False,
        "runtime_required": "Go Compiler (go)",
        "previewable": False,
        "description": "Fast statically-typed concurrent language developed by Google."
    },
    "rust": {
        "id": "rust",
        "name": "Rust",
        "category": "programming",
        "extensions": [".rs"],
        "executable": False,
        "runtime_required": "Rust Compiler (rustc / cargo)",
        "previewable": False,
        "description": "Memory-safe systems programming language without garbage collection."
    },
    "php": {
        "id": "php",
        "name": "PHP",
        "category": "programming",
        "extensions": [".php", ".phtml"],
        "executable": False,
        "runtime_required": "PHP CLI (php)",
        "previewable": False,
        "description": "Popular server-side scripting language for web development."
    },
    "ruby": {
        "id": "ruby",
        "name": "Ruby",
        "category": "programming",
        "extensions": [".rb"],
        "executable": True,
        "runtime_required": "Ruby Interpreter (ruby)",
        "previewable": False,
        "description": "Dynamic open-source object-oriented language with natural syntax."
    },
    "kotlin": {
        "id": "kotlin",
        "name": "Kotlin",
        "category": "programming",
        "extensions": [".kt", ".kts"],
        "executable": False,
        "runtime_required": "Kotlin Compiler (kotlinc)",
        "previewable": False,
        "description": "Concise modern language targeting the JVM and Android."
    },
    "swift": {
        "id": "swift",
        "name": "Swift",
        "category": "programming",
        "extensions": [".swift"],
        "executable": False,
        "runtime_required": "Apple Swift Compiler (requires matching Xcode macOS SDK)",
        "previewable": False,
        "description": "Modern high-performance language for Apple platforms and systems."
    },
    "bash": {
        "id": "bash",
        "name": "Bash",
        "category": "programming",
        "extensions": [".sh", ".bash", ".zsh"],
        "executable": True,
        "runtime_required": "GNU Bash (/bin/bash)",
        "previewable": False,
        "description": "Standard Unix shell and command scripting language."
    },

    # 2. Web Technologies
    "html": {
        "id": "html",
        "name": "HTML",
        "category": "web",
        "extensions": [".html", ".htm"],
        "executable": False,
        "runtime_required": "Browser rendering engine (Sandboxed Live Preview)",
        "previewable": True,
        "description": "Standard markup language for documents designed to be displayed in a web browser."
    },
    "css": {
        "id": "css",
        "name": "CSS",
        "category": "web",
        "extensions": [".css"],
        "executable": False,
        "runtime_required": "Browser layout engine (Sandboxed Live Preview)",
        "previewable": True,
        "description": "Style sheet language used for describing the presentation of a document."
    },
    "scss": {
        "id": "scss",
        "name": "SCSS",
        "category": "web",
        "extensions": [".scss", ".sass"],
        "executable": False,
        "runtime_required": "SASS/SCSS preprocessor (Sandboxed Live Preview)",
        "previewable": True,
        "description": "CSS preprocessor adding variables, nesting, and mixins to CSS."
    },
    "jsx": {
        "id": "jsx",
        "name": "JSX",
        "category": "web",
        "extensions": [".jsx"],
        "executable": False,
        "runtime_required": "React Babel / Vite transpile",
        "previewable": False,
        "description": "JavaScript syntax extension for describing React UI components."
    },
    "tsx": {
        "id": "tsx",
        "name": "TSX",
        "category": "web",
        "extensions": [".tsx"],
        "executable": False,
        "runtime_required": "TypeScript React compiler",
        "previewable": False,
        "description": "TypeScript syntax extension for strongly typed React UI components."
    },

    # 3. Data & Query Formats
    "sql": {
        "id": "sql",
        "name": "SQL",
        "category": "data",
        "extensions": [".sql"],
        "executable": False,
        "runtime_required": "Relational Database Engine (e.g. SQLite, PostgreSQL, MySQL)",
        "previewable": False,
        "description": "Domain-specific language used in programming and managing relational databases."
    },
    "json": {
        "id": "json",
        "name": "JSON",
        "category": "data",
        "extensions": [".json"],
        "executable": False,
        "runtime_required": "Data interchange parser (Validates syntax & schema)",
        "previewable": False,
        "description": "Lightweight data-interchange format easily readable by humans and machines."
    },
    "xml": {
        "id": "xml",
        "name": "XML",
        "category": "data",
        "extensions": [".xml", ".svg"],
        "executable": False,
        "runtime_required": "XML document parser (Validates well-formedness)",
        "previewable": False,
        "description": "Extensible Markup Language defining a set of rules for encoding documents."
    },
    "yaml": {
        "id": "yaml",
        "name": "YAML",
        "category": "data",
        "extensions": [".yaml", ".yml"],
        "executable": False,
        "runtime_required": "YAML parser (Validates structure & key-value hierarchy)",
        "previewable": False,
        "description": "Human-readable data-serialization language commonly used for configuration."
    },

    # 4. Other Formats (Config & Docs)
    "markdown": {
        "id": "markdown",
        "name": "Markdown",
        "category": "config",
        "extensions": [".md", ".markdown"],
        "executable": False,
        "runtime_required": "Markdown renderer (Sandboxed Live Preview)",
        "previewable": True,
        "description": "Lightweight markup language with plain-text formatting syntax."
    },
    "toml": {
        "id": "toml",
        "name": "TOML",
        "category": "config",
        "extensions": [".toml"],
        "executable": False,
        "runtime_required": "TOML parser (Validates configuration schema)",
        "previewable": False,
        "description": "Tom's Obvious Minimal Language for unambiguous configuration files."
    },
    "dockerfile": {
        "id": "dockerfile",
        "name": "Dockerfile",
        "category": "config",
        "extensions": ["Dockerfile", ".dockerfile"],
        "executable": False,
        "runtime_required": "Docker Container Engine (docker build)",
        "previewable": False,
        "description": "Text document that contains instructions to assemble a Docker container image."
    }
}

# Extension to language lookup
EXTENSION_MAP: Dict[str, str] = {}
for lang_id, info in LANGUAGES_REGISTRY.items():
    for ext in info["extensions"]:
        EXTENSION_MAP[ext.lower()] = lang_id


def detect_language_from_filename(filename: str) -> Optional[str]:
    """Detect language based on filename or file extension."""
    if not filename:
        return None
    name = Path(filename).name.lower()
    if name in {"dockerfile", "dockerfile.dev", "dockerfile.prod"}:
        return "dockerfile"
    ext = Path(filename).suffix.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    return None


def detect_language_from_content(code: str) -> Optional[str]:
    """Scoring-based content language detector.
    Returns detected language if confident, or None if code is ambiguous/insufficient."""
    res = detect_language_details(code)
    return res.get("detected_language")


def detect_language_details(code: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """Accurately detects programming language, confidence, and metadata from source code.
    Distinguishes complete programs, short snippets, and identifies ambiguous code without guessing."""
    if not code or not code.strip():
        file_ext = detect_language_from_filename(filename) if filename else None
        if file_ext:
            return {
                "detected_language": file_ext,
                "confidence": "medium",
                "message": None,
                "info": LANGUAGES_REGISTRY.get(file_ext, {"name": file_ext.capitalize(), "executable": False})
            }
        return {
            "detected_language": None,
            "confidence": "uncertain",
            "message": "Enter more code to detect language",
            "info": None
        }

    clean_code = code.strip()
    first_few_lines = clean_code.splitlines()[:20]
    header = "\n".join(first_few_lines).lower()

    scores: Dict[str, int] = {}

    def add_score(lang: str, points: int):
        scores[lang] = scores.get(lang, 0) + points

    # 1. Dockerfile
    if any(re.match(r"^\s*(FROM|RUN|WORKDIR|COPY|ADD|EXPOSE|ENTRYPOINT|CMD)\s+", line, re.I) for line in first_few_lines):
        add_score("dockerfile", 110)

    # 2. HTML
    if "<!doctype html" in header or "<html" in header or ("<body" in header and "<div" in header):
        add_score("html", 105)

    # 3. XML
    if "<?xml" in header or ("<root" in header and "</root>" in clean_code.lower()) or ("<urlset" in header):
        add_score("xml", 100)

    # 4. JSON
    if (clean_code.startswith("{") and clean_code.endswith("}")) or (clean_code.startswith("[") and clean_code.endswith("]")):
        try:
            parsed = json.loads(clean_code)
            if isinstance(parsed, (dict, list)) and len(parsed) > 0:
                add_score("json", 95)
        except Exception:
            pass

    # 5. Bash / Shell
    if header.startswith("#!/bin/bash") or header.startswith("#!/bin/sh") or header.startswith("#!/usr/bin/env bash"):
        add_score("bash", 120)
    elif re.search(r"\b(echo\s+[\"']|export\s+[A-Za-z0-9_]+=)\b", clean_code) and ";" not in clean_code and "{" not in clean_code:
        add_score("bash", 45)

    # 6. SQL
    if re.search(r"^\s*(select\s+.+\s+from|insert\s+into\s+|update\s+.+\s+set|delete\s+from\s+|create\s+table\s+|alter\s+table\s+|drop\s+table\s+|with\s+[a-zA-Z0-9_]+\s+as\s*\()", clean_code, re.I | re.DOTALL):
        add_score("sql", 110)

    # 7. C++ & C
    has_cpp_header = bool(re.search(r"#include\s*<(iostream|vector|string|map|set|algorithm|queue|stack|sstream|fstream|iomanip|cmath|climits|bits/stdc\+\+\.h)>", clean_code, re.I))
    has_cpp_std = bool(re.search(r"\bstd::(cout|cin|endl|vector|string|map|set|pair|make_pair|make_shared|unique_ptr)\b", clean_code))
    has_cpp_cout = bool(re.search(r"\b(cout\s*<<|cin\s*>>|using\s+namespace\s+std;)\b", clean_code))
    has_cpp_template = bool(re.search(r"\btemplate\s*<\s*(typename|class)\b", clean_code))

    if has_cpp_header:
        add_score("cpp", 110)
    if has_cpp_std:
        add_score("cpp", 95)
    if has_cpp_cout:
        add_score("cpp", 90)
    if has_cpp_template:
        add_score("cpp", 80)

    has_c_header = bool(re.search(r"#include\s*<(stdio\.h|stdlib\.h|string\.h|stdbool\.h|unistd\.h|time\.h|errno\.h|pthread\.h)>", clean_code, re.I))
    has_c_printf = bool(re.search(r"\b(printf|scanf|fprintf\s*\(\s*stderr|sprintf)\s*\(", clean_code))
    has_c_malloc = bool(re.search(r"\b(malloc|free|calloc|realloc)\s*\(", clean_code))

    if has_c_header:
        if has_cpp_header or has_cpp_std or has_cpp_cout:
            add_score("cpp", 40)
        else:
            add_score("c", 95)
    if has_c_printf and not has_cpp_std and not has_cpp_cout:
        add_score("c", 85)
    if has_c_malloc and not has_cpp_std and not has_cpp_cout:
        add_score("c", 60)
    if re.search(r"\bint\s+main\s*\(\s*(void|int\s+argc[^)]*)?\s*\)", clean_code) and (has_c_header or has_c_printf):
        if not has_cpp_header and not has_cpp_std and not has_cpp_cout:
            add_score("c", 45)

    # 8. Java
    if re.search(r"\bpublic\s+static\s+void\s+main\s*\(\s*String(\s*\[\]\s*|\s+)args\s*(\[\s*\]\s*)?\)", clean_code):
        add_score("java", 120)
    if re.search(r"\bSystem\.(out|err)\.(println|print|printf)\s*\(", clean_code):
        add_score("java", 100)
    if re.search(r"\bpackage\s+[a-z0-9_.]+;", clean_code):
        add_score("java", 85)
    if re.search(r"\bimport\s+java(x)?\.[a-z0-9_.*]+;", clean_code):
        add_score("java", 85)
    if re.search(r"\bpublic\s+(final\s+)?class\s+[A-Za-z0-9_]+(\s+extends\s+[A-Za-z0-9_]+)?(\s+implements\s+[A-Za-z0-9_,\s]+)?\s*\{", clean_code):
        add_score("java", 85)
    if "@Override" in clean_code:
        add_score("java", 65)
    if re.search(r"\b(private|protected|public)\s+(static\s+)?(final\s+)?(int|double|float|boolean|String|void|[A-Z]\w+)\s+[a-zA-Z0-9_]+\s*(\([^)]*\)|=)", clean_code) and ";" in clean_code:
        add_score("java", 75)
    if re.search(r"\bnew\s+(ArrayList|HashMap|HashSet|Scanner|StringBuilder)<[A-Za-z0-9_,\s]*>\s*\(", clean_code):
        add_score("java", 75)

    # 9. Python
    if re.search(r"\bint\s*\(\s*input\s*\(", clean_code):
        add_score("python", 105)
    if re.search(r"\binput\s*\([^)]*\)", clean_code):
        add_score("python", 80)
    if re.search(r"\bdef\s+[a-zA-Z0-9_]+\s*\([^)]*\)\s*:", clean_code):
        add_score("python", 95)
    if re.search(r"\bclass\s+[a-zA-Z0-9_]+(\([^)]*\))?\s*:", clean_code):
        add_score("python", 90)
    if re.search(r"\belif\s+.*:", clean_code):
        add_score("python", 90)
    if re.search(r"\bif\s+__name__\s*==\s*['\"]__main__['\"]\s*:", clean_code):
        add_score("python", 100)
    if re.search(r"^\s*(import\s+[a-zA-Z0-9_]+|from\s+[a-zA-Z0-9_.]+\s+import\s+)", clean_code, re.M) and "from '" not in clean_code and 'from "' not in clean_code:
        add_score("python", 85)
    if re.search(r"\bfor\s+[a-zA-Z0-9_]+\s+in\s+range\s*\(", clean_code):
        add_score("python", 90)
    if re.search(r"\bself\.[a-zA-Z0-9_]+", clean_code) or re.search(r"\bdef\s+__init__\s*\(", clean_code):
        add_score("python", 85)
    if re.search(r"\bprint\s*\([^)]*\)", clean_code):
        if ";" not in clean_code and "System.out" not in clean_code and "console.log" not in clean_code:
            add_score("python", 60)
    if re.search(r"^\s*(if|for|while|try|except|finally|with)\s+.*:\s*$", clean_code, re.M) and "{" not in clean_code:
        add_score("python", 55)

    # 10. JavaScript & TypeScript
    if re.search(r"\bconsole\.(log|error|warn|info|debug)\s*\(", clean_code):
        add_score("javascript", 95)
    if re.search(r"\b(const|let)\s+[a-zA-Z0-9_$]+\s*=", clean_code):
        add_score("javascript", 70)
    if re.search(r"\b(const|let|var)\s+[a-zA-Z0-9_$]+\s*=\s*require\s*\(", clean_code) or "module.exports" in clean_code:
        add_score("javascript", 100)
    if re.search(r"(\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>\s*(\{|[^{;]+)", clean_code):
        add_score("javascript", 80)
    if re.search(r"\bfunction\s+[a-zA-Z0-9_$]*\s*\([^)]*\)\s*\{", clean_code):
        add_score("javascript", 70)
    if re.search(r"\bdocument\.(getElementById|querySelector|addEventListener)\b", clean_code) or re.search(r"\bwindow\.(addEventListener|localStorage)\b", clean_code):
        add_score("javascript", 95)
    if re.search(r"\b(===|!==)\b", clean_code):
        add_score("javascript", 50)
    if re.search(r"\b(interface\s+[A-Z]\w+\s*\{|type\s+[A-Z]\w+\s*=)", clean_code) or re.search(r":\s*(string|number|boolean|any)\[\]", clean_code):
        add_score("typescript", 90)
    if "import React" in clean_code or "className=" in clean_code:
        add_score("jsx", 90)

    # 11. C#
    if re.search(r"\busing\s+System(\.[A-Za-z0-9_]+)*;", clean_code):
        add_score("csharp", 100)
    if re.search(r"\bConsole\.(WriteLine|Write)\s*\(", clean_code):
        add_score("csharp", 100)
    if re.search(r"\bnamespace\s+[A-Za-z0-9_.]+", clean_code):
        add_score("csharp", 90)

    # 12. Go
    if re.search(r"\bpackage\s+(main|[a-z0-9_]+)\b", clean_code):
        add_score("go", 95)
    if re.search(r"\bfunc\s+main\s*\(\s*\)", clean_code):
        add_score("go", 95)
    if re.search(r"\bfmt\.(Println|Printf|Print)\s*\(", clean_code):
        add_score("go", 95)

    # 13. Rust
    if re.search(r"\bfn\s+main\s*\(\s*\)", clean_code) or re.search(r"\bpub\s+fn\s+", clean_code):
        add_score("rust", 100)
    if re.search(r"\blet\s+mut\s+", clean_code):
        add_score("rust", 100)
    if re.search(r"\b(println!|eprintln!)\s*\(", clean_code):
        add_score("rust", 100)
    if "use std::" in clean_code:
        add_score("rust", 90)

    # 14. PHP
    if "<?php" in clean_code or re.search(r"\becho\s+\$[a-zA-Z_]", clean_code):
        add_score("php", 110)

    # 15. Ruby
    if re.search(r"\bdef\s+[a-zA-Z0-9_]+\b", clean_code) and re.search(r"\bend\b", clean_code) and ":" not in clean_code:
        add_score("ruby", 85)
    if re.search(r"\bputs\s+", clean_code) and ";" not in clean_code:
        add_score("ruby", 60)

    # 16. Kotlin
    if re.search(r"\bfun\s+main\s*\(", clean_code) or re.search(r"\bval\s+[a-zA-Z0-9_]+\s*:\s*[A-Z]", clean_code):
        add_score("kotlin", 95)

    # 17. Swift
    if re.search(r"\bimport\s+(UIKit|SwiftUI|Foundation)\b", clean_code):
        add_score("swift", 100)

    # 18. CSS / SCSS
    if re.search(r"(\.[a-zA-Z0-9_-]+|#[a-zA-Z0-9_-]+|\bbody|\bhtml)\s*\{[^}]*:[^}]*;[^}]*\}", clean_code, re.I):
        if "$" in clean_code or "@mixin" in clean_code or "@include" in clean_code:
            add_score("scss", 95)
        else:
            add_score("css", 85)

    # 19. TOML
    if re.search(r"^\s*\[[a-zA-Z0-9_.-]+\]\s*$", header, re.M) and "=" in header:
        add_score("toml", 85)

    # 20. Markdown
    if header.startswith("# ") or header.startswith("## ") or ("\n# " in header and "```" in clean_code):
        add_score("markdown", 80)

    # Sort scores
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    CONFIDENCE_THRESHOLD = 30

    if not sorted_scores or sorted_scores[0][1] < CONFIDENCE_THRESHOLD:
        file_ext = detect_language_from_filename(filename) if filename else None
        if file_ext and len(clean_code) > 0:
            return {
                "detected_language": file_ext,
                "confidence": "medium",
                "message": None,
                "info": LANGUAGES_REGISTRY.get(file_ext, {"name": file_ext.capitalize(), "executable": False})
            }
        # Ambiguous or insufficient code - do NOT guess!
        return {
            "detected_language": None,
            "confidence": "uncertain",
            "message": "Enter more code to detect language",
            "info": None
        }

    top_lang, top_score = sorted_scores[0]
    return {
        "detected_language": top_lang,
        "confidence": "high" if top_score >= 60 else "medium",
        "message": None,
        "info": LANGUAGES_REGISTRY.get(top_lang, {"name": top_lang.capitalize(), "executable": False})
    }


def detect_language(code: str, filename: Optional[str] = None) -> Optional[str]:
    """Unified detector: checks filename first if provided, then content heuristics."""
    if filename:
        detected_ext = detect_language_from_filename(filename)
        # If code is present and has confident content signals, let content take priority
        if code and code.strip():
            details = detect_language_details(code, filename)
            if details.get("detected_language"):
                return details["detected_language"]
        if detected_ext:
            return detected_ext
    details = detect_language_details(code, filename)
    return details.get("detected_language")
