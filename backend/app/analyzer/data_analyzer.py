import json
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from pathlib import Path
from ..models import (
    AnalysisResult,
    LineExplanation,
    VariableFunctionItem,
    DiagnosticItem,
    ComplexityInfo
)
from .base import BaseAnalyzer, extract_lines

# Import YAML with safe fallback
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# Import TOML standard library in Python 3.11+
try:
    import tomllib
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False

class DataAnalyzer(BaseAnalyzer):
    """
    Specialized analyzer for JSON, YAML, XML, and TOML data formats.
    Validates structural syntax and explains fields, schema hierarchy, and configuration intent.
    """

    def analyze(self, code: str, filename: Optional[str] = None, language: str = "json") -> AnalysisResult:
        lang = language.lower().strip()
        if lang == "json":
            return self._analyze_json(code, filename)
        elif lang in {"yaml", "yml"}:
            return self._analyze_yaml(code, filename)
        elif lang in {"xml", "svg"}:
            return self._analyze_xml(code, filename)
        elif lang == "toml":
            return self._analyze_toml(code, filename)
        else:
            return self._analyze_json(code, filename)

    def _analyze_json(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        parsed_data = None
        is_valid = False

        try:
            parsed_data = json.loads(code)
            is_valid = True
        except json.JSONDecodeError as err:
            diagnostics.append(DiagnosticItem(
                id="diag-json-syntax-error",
                title="Confirmed JSON Syntax Error",
                severity="error",
                line_number=err.lineno,
                explanation=f"Invalid JSON at line {err.lineno}, column {err.colno}: {err.msg}.",
                recommended_correction="Ensure keys and string values are enclosed in double quotes (\"), verify matching brackets, and remove trailing commas.",
                corrected_snippet=None,
                detection_type="parser_validation"
            ))

        variables_functions: List[VariableFunctionItem] = []
        if is_valid and isinstance(parsed_data, dict):
            for key, val in list(parsed_data.items())[:15]:
                val_type = type(val).__name__
                variables_functions.append(VariableFunctionItem(
                    name=str(key),
                    kind="Data Field (Key)",
                    data_type=val_type,
                    description=f"Value preview: {repr(val)[:60]}",
                    scope="Top-Level Schema"
                ))
        elif is_valid and isinstance(parsed_data, list):
            variables_functions.append(VariableFunctionItem(
                name="[root array]",
                kind="Array Container",
                data_type=f"List of {len(parsed_data)} item(s)",
                description=f"Contains {len(parsed_data)} element(s).",
                scope="Root Collection"
            ))

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "JSON structure."
            if s.startswith("{") or s.startswith("}"):
                exp = "Object delimiter enclosing key-value attributes."
            elif s.startswith("[") or s.startswith("]"):
                exp = "Array collection delimiter enclosing ordered list items."
            elif ":" in s:
                key_part = s.split(":", 1)[0].strip()
                exp = f"Defines data attribute {key_part}."
            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        if is_valid:
            overview = (
                f"Valid JSON document containing {len(lines)} line(s). "
                f"Root is a {type(parsed_data).__name__} holding "
                f"{len(parsed_data) if hasattr(parsed_data, '__len__') else 1} item(s). "
                "Structure is well-formed, suitable for API payloads, state serialization, or configuration."
            )
            workflow = (
                "1. Parser scans UTF-8 text and verifies syntax rules (strict double quotes, no comments, no trailing commas).\n"
                "2. Constructs native objects (dictionaries, lists, numbers, booleans, null).\n"
                "3. In-memory tree is passed to consumers for data extraction, configuration, or API transport."
            )
        else:
            overview = (
                f"JSON document with a syntax error at line {diagnostics[0].line_number if diagnostics else 1}. "
                "JSON requires strict compliance: keys must be double-quoted, trailing commas are prohibited, and brackets must be balanced."
            )
            workflow = (
                "1. Parser encountered unexpected character during tokenization.\n"
                "2. Execution halted prior to memory tree construction.\n"
                "3. Please resolve the syntax issue identified in Diagnostics below."
            )

        return AnalysisResult(
            overview=overview,
            logic_workflow=workflow,
            line_by_line=line_by_line[:40],
            inputs="Raw text received from files, network HTTP payloads, or datastores.",
            outputs="Deserialized in-memory object (dictionary/list) consumed by client or server programs.",
            variables_functions=variables_functions,
            programming_concepts=[
                "Data Serialization",
                "JSON Schema & Types",
                "Key-Value Pair Modeling",
                "Array / List Collections",
                "API Data Interchange Format"
            ],
            limitations=[
                "JSON cannot store functions, circular references, or binary data directly without Base64 encoding.",
                "Comments are not supported in standard JSON specifications (unlike JSON5 or YAML).",
                "Keys must be strings enclosed in double quotes; single quotes will fail validation."
            ],
            complexity=ComplexityInfo(
                time="O(N) parse time where N is byte count",
                space="O(N) memory to hold tree",
                explanation="Deserialization scales linearly with document character length; JSON does not execute computational algorithms."
            ),
            learning_takeaway="JSON is the universal lingua franca of the modern web. Always validate payloads with strict parsers before passing data to application logic.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )

    def _analyze_yaml(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        parsed = None
        is_valid = False

        if YAML_AVAILABLE:
            try:
                parsed = yaml.safe_load(code)
                is_valid = True
            except yaml.YAMLError as exc:
                line_no = None
                if hasattr(exc, 'problem_mark') and exc.problem_mark:
                    line_no = exc.problem_mark.line + 1
                diagnostics.append(DiagnosticItem(
                    id="diag-yaml-syntax-error",
                    title="Confirmed YAML Syntax Error",
                    severity="error",
                    line_number=line_no,
                    explanation=f"YAML parsing failed: {str(exc)}",
                    recommended_correction="Ensure consistent indentation (use spaces, never tabs) and verify colon-space ': ' format.",
                    detection_type="parser_validation"
                ))
        else:
            is_valid = True

        variables_functions: List[VariableFunctionItem] = []
        if is_valid and isinstance(parsed, dict):
            for k, v in list(parsed.items())[:12]:
                variables_functions.append(VariableFunctionItem(
                    name=str(k),
                    kind="Configuration Key",
                    data_type=type(v).__name__,
                    description=f"Value: {repr(v)[:50]}",
                    scope="YAML Tree"
                ))

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "YAML configuration entry."
            if s.startswith("#"):
                exp = "YAML comment documenting this configuration block."
            elif s.startswith("---"):
                exp = "Document start delimiter separating multiple YAML streams."
            elif ":" in s:
                exp = f"Defines configuration setting '{s.split(':', 1)[0].strip()}'."
            elif s.startswith("- "):
                exp = "List sequence item in an array."
            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        return AnalysisResult(
            overview=f"YAML configuration document with {len(lines)} line(s). {'Syntax is valid and well-formed. ' if is_valid else 'Contains indentation or syntax errors. '}Commonly used for Docker Compose, Kubernetes manifests, and CI/CD pipelines.",
            logic_workflow=(
                "1. Parser interprets indentation levels (whitespace-significant hierarchy).\n"
                "2. Resolves scalar types (strings, integers, booleans, dates) and sequences (- items).\n"
                "3. Injects configuration parameters into deployment engines or application setups."
            ),
            line_by_line=line_by_line[:40],
            inputs="YAML configuration files (e.g. docker-compose.yml, application.yaml).",
            outputs="Parsed hierarchical dictionary passed to container orchestrators, CI runners, or apps.",
            variables_functions=variables_functions,
            programming_concepts=[
                "Whitespace-Sensitive Hierarchy",
                "Declarative Configuration",
                "Key-Value & Sequence Structures",
                "Infrastructure as Code (IaC)"
            ],
            limitations=[
                "Tabs are strictly forbidden for indentation in YAML; only spaces are permitted.",
                "Complex multiline strings require explicit operators (| for literal, > for folded).",
                "Unquoted strings with colons or special characters may be misparsed as mappings."
            ],
            complexity=ComplexityInfo(
                time="N/A (Configuration Format)",
                space="N/A (Config Dictionary)",
                explanation="YAML documents declare hierarchical configuration; they do not perform runtime algorithmic computation."
            ),
            learning_takeaway="YAML combines high readability with human-friendly comments, making it the premier format for DevOps and cloud configuration.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )

    def _analyze_xml(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        is_valid = False
        root_tag = "document"

        try:
            root = ET.fromstring(code)
            is_valid = True
            root_tag = root.tag
        except ET.ParseError as err:
            diagnostics.append(DiagnosticItem(
                id="diag-xml-parse-error",
                title="Confirmed XML Syntax / Well-Formedness Error",
                severity="error",
                explanation=f"XML parsing failed: {err.msg}.",
                recommended_correction="Ensure every opening tag has an exact matching closing tag, attribute values are quoted, and the document has exactly one root element.",
                detection_type="parser_validation"
            ))

        variables_functions: List[VariableFunctionItem] = [
            VariableFunctionItem(
                name=f"<{root_tag}>",
                kind="XML Root Element",
                data_type="Element",
                description="Root element enclosing all nested XML nodes.",
                scope="XML Document"
            )
        ]

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "XML node markup."
            if s.startswith("<?xml"):
                exp = "XML declaration specifying version and encoding."
            elif s.startswith("<!--"):
                exp = "XML comment ignored during parsing."
            elif s.startswith("<") and s.endswith(">"):
                exp = "XML element tag encapsulating structured data or child nodes."
            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        return AnalysisResult(
            overview=f"XML document with {len(lines)} line(s). {'Well-formed XML with root <' + root_tag + '>. ' if is_valid else 'Document violates XML well-formedness rules. '}Used for data interchange, SVG graphics, and legacy enterprise systems.",
            logic_workflow=(
                "1. Parser verifies XML prolog and validates tag matching.\n"
                "2. Constructs Document Object Model (DOM) or SAX event stream.\n"
                "3. Extracts node text, attributes, and child relationships."
            ),
            line_by_line=line_by_line[:40],
            inputs="XML structured text documents or feeds (e.g. RSS, SVG, SOAP payloads).",
            outputs="Hierarchical element tree ready for XPath querying or data binding.",
            variables_functions=variables_functions,
            programming_concepts=[
                "Extensible Markup Standards",
                "Tree Nodes & Attributes",
                "Document Well-Formedness vs Validity (DTD/XSD)",
                "Namespaces & Prolog Metadata"
            ],
            limitations=[
                "XML is more verbose than JSON or YAML due to redundant closing tags.",
                "Requires entity escaping for special characters like & (< &lt;, > &gt;, & &amp;).",
                "Must strictly have exactly one root element enclosing all content."
            ],
            complexity=ComplexityInfo(
                time="N/A (Markup Format)",
                space="N/A (DOM Tree)",
                explanation="XML documents represent structured node trees; they do not execute algorithms with computational complexity."
            ),
            learning_takeaway="XML remains fundamental in enterprise messaging, SVG vector graphics, and Android layouts. Always maintain strict well-formedness with closing tags.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )

    def _analyze_toml(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        is_valid = False
        parsed = {}

        if TOML_AVAILABLE:
            try:
                parsed = tomllib.loads(code)
                is_valid = True
            except tomllib.TOMLDecodeError as err:
                diagnostics.append(DiagnosticItem(
                    id="diag-toml-decode-error",
                    title="Confirmed TOML Syntax Error",
                    severity="error",
                    explanation=f"TOML decode error: {str(err)}",
                    recommended_correction="Check table headers [section] and ensure string values use valid quotes.",
                    detection_type="parser_validation"
                ))
        else:
            is_valid = True

        variables_functions: List[VariableFunctionItem] = []
        if is_valid and isinstance(parsed, dict):
            for sec, content in list(parsed.items())[:10]:
                variables_functions.append(VariableFunctionItem(
                    name=f"[{sec}]" if isinstance(content, dict) else sec,
                    kind="TOML Table Section" if isinstance(content, dict) else "Configuration Key",
                    data_type=type(content).__name__,
                    description=f"Contains {len(content)} item(s)" if isinstance(content, dict) else f"Value: {repr(content)[:40]}",
                    scope="TOML Config"
                ))

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "TOML configuration statement."
            if s.startswith("#"):
                exp = "Comment describing the configuration parameter."
            elif s.startswith("[") and s.endswith("]"):
                exp = f"Table header defining configuration section {s}."
            elif "=" in s:
                key = s.split("=", 1)[0].strip()
                exp = f"Assigns value to configuration parameter '{key}'."
            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        return AnalysisResult(
            overview=f"TOML configuration document with {len(lines)} line(s). {'Valid syntax with clear table sections. ' if is_valid else 'Syntax error detected. '}Commonly used in Python (pyproject.toml), Rust (Cargo.toml), and Go toolchains.",
            logic_workflow=(
                "1. Parser divides file into tables ([section]) and array of tables ([[section]]).\n"
                "2. Resolves strongly-typed key = value assignments (integers, floats, dates, arrays).\n"
                "3. Injects configuration dictionary into build systems or application managers."
            ),
            line_by_line=line_by_line[:40],
            inputs="Project configuration files like pyproject.toml or Cargo.toml.",
            outputs="Deserialized configuration dictionary mapping tables to settings.",
            variables_functions=variables_functions,
            programming_concepts=[
                "Minimal Configuration Syntax",
                "Explicit Typing (Integers, Booleans, ISO 8601 Dates)",
                "Table & Nested Table Sections",
                "Modern Package Management Specs"
            ],
            limitations=[
                "Keys cannot be redefined in the same section.",
                "Strings must use valid UTF-8 quotes (single quotes for literal strings, double for escaped).",
                "Deep nesting is less visual than YAML; requires dotted keys (e.g. [a.b.c])."
            ],
            complexity=ComplexityInfo(
                time="N/A (Configuration File)",
                space="N/A (Config Dictionary)",
                explanation="TOML defines static configuration data; it does not execute algorithmic routines."
            ),
            learning_takeaway="TOML was designed specifically for unambiguous human editing. It is the modern standard for Python (PEP 621) and Rust project metadata.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )
