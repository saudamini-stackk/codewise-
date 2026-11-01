import re
from typing import Optional
from .base import BaseAnalyzer
from .python_analyzer import PythonAnalyzer
from .java_analyzer import JavaAnalyzer
from .js_analyzer import JavaScriptAnalyzer
from .cpp_analyzer import CppAnalyzer
from .web_analyzer import WebAnalyzer
from .data_analyzer import DataAnalyzer
from .sql_analyzer import SqlAnalyzer
from .devops_analyzer import DevOpsAnalyzer
from .general_code_analyzer import GeneralCodeAnalyzer
from ..detector import detect_language
from ..models import AnalysisResult

class StaticEngine:
    def __init__(self):
        self.python_analyzer = PythonAnalyzer()
        self.java_analyzer = JavaAnalyzer()
        self.js_analyzer = JavaScriptAnalyzer()
        self.cpp_analyzer = CppAnalyzer()
        self.web_analyzer = WebAnalyzer()
        self.data_analyzer = DataAnalyzer()
        self.sql_analyzer = SqlAnalyzer()
        self.devops_analyzer = DevOpsAnalyzer()
        self.general_code_analyzer = GeneralCodeAnalyzer()

    def detect_language(self, code: str, filename: Optional[str] = None) -> str:
        return detect_language(code, filename)

    def analyze(self, code: str, language: Optional[str] = None, filename: Optional[str] = None) -> AnalysisResult:
        lang = (language or self.detect_language(code, filename)).lower().strip()
        if lang == "auto":
            lang = self.detect_language(code, filename)

        # 1. Python
        if lang in {"python", "py"}:
            return self.python_analyzer.analyze(code, filename)

        # 2. Java (dedicated academic analyzer)
        elif lang == "java":
            return self.java_analyzer.analyze(code, filename)

        # 3. JavaScript / React JSX
        elif lang in {"javascript", "js", "jsx"}:
            return self.js_analyzer.analyze(code, filename)

        # 4. C / C++
        elif lang in {"cpp", "c++", "c", "cxx"}:
            return self.cpp_analyzer.analyze(code, filename)

        # 5. Web Technologies (HTML, CSS, SCSS)
        elif lang in {"html", "htm", "css", "scss", "sass"}:
            return self.web_analyzer.analyze(code, filename, language=lang)

        # 6. Data & Query Formats (JSON, YAML, XML, TOML)
        elif lang in {"json", "yaml", "yml", "xml", "svg", "toml"}:
            return self.data_analyzer.analyze(code, filename, language=lang)

        # 7. SQL
        elif lang == "sql":
            return self.sql_analyzer.analyze(code, filename)

        # 8. DevOps & Docs (Dockerfile, Bash, Markdown)
        elif lang in {"dockerfile", "bash", "sh", "zsh", "markdown", "md"}:
            return self.devops_analyzer.analyze(code, filename, language=lang)

        # 9. Modern Typed & Compiled Programming Languages (C#, Go, Rust, PHP, Ruby, Kotlin, Swift, TypeScript, TSX)
        elif lang in {"csharp", "cs", "go", "rust", "rs", "php", "ruby", "rb", "kotlin", "kt", "swift", "typescript", "ts", "tsx"}:
            return self.general_code_analyzer.analyze(code, filename, language=lang)

        # 9. Fallback: try python, then general code
        else:
            try:
                return self.general_code_analyzer.analyze(code, filename, language=lang)
            except Exception:
                return self.python_analyzer.analyze(code, filename)
