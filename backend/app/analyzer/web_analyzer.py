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

class WebAnalyzer(BaseAnalyzer):
    """
    Specialized analyzer for HTML, CSS, and SCSS.
    Explains document structure, selectors, layout models, accessibility, and styling synergy.
    """

    def analyze(self, code: str, filename: Optional[str] = None, language: str = "html") -> AnalysisResult:
        lang = language.lower()
        if lang in {"css", "scss"}:
            return self._analyze_css(code, filename, lang)
        else:
            return self._analyze_html(code, filename)

    def _analyze_html(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []
        tags_found = re.findall(r"<\s*([a-zA-Z0-9]+)", code)
        unique_tags = sorted(set(t.lower() for t in tags_found))

        # Check for doctype and key structural sections
        has_doctype = bool(re.search(r"<!DOCTYPE\s+html", code, re.I))
        has_head = "<head" in code.lower()
        has_body = "<body" in code.lower()
        has_title = "<title" in code.lower()

        # Accessibility checks
        # 1. Images without alt attribute
        img_tags = re.findall(r"<img\s+[^>]*>", code, re.I)
        for img in img_tags:
            if "alt=" not in img.lower():
                diagnostics.append(DiagnosticItem(
                    id="diag-html-img-alt",
                    title="Accessibility: Missing Image alt Attribute",
                    severity="warning",
                    explanation=f"Image element '{img[:40]}...' is missing an 'alt' descriptive text attribute, reducing accessibility for screen readers and search engines.",
                    recommended_correction="Add an alt attribute describing the image content (e.g. alt=\"Company logo\").",
                    corrected_snippet=img.replace("<img", '<img alt="Description"', 1),
                    detection_type="static_html_linter"
                ))
                break

        # 2. Missing title in head
        if has_head and not has_title:
            diagnostics.append(DiagnosticItem(
                id="diag-html-title",
                title="SEO & Usability: Missing <title> Tag",
                severity="suggestion",
                explanation="The <head> section does not define a <title> tag. The page title is displayed in browser tabs and search engine search results.",
                recommended_correction="Add a descriptive <title>Page Title</title> inside <head>.",
                corrected_snippet="<head>\n    <title>Document</title>",
                detection_type="static_html_linter"
            ))

        # 3. Missing doctype in full documents
        if (has_head or has_body) and not has_doctype:
            diagnostics.append(DiagnosticItem(
                id="diag-html-doctype",
                title="Document Standards: Missing HTML5 <!DOCTYPE html>",
                severity="suggestion",
                explanation="Full HTML documents should include <!DOCTYPE html> as the first line to guarantee standards-compliant browser rendering mode.",
                recommended_correction="Add <!DOCTYPE html> at line 1.",
                corrected_snippet="<!DOCTYPE html>\n<html lang=\"en\">",
                detection_type="static_html_linter"
            ))

        # Elements inspection
        semantic_tags = [t for t in unique_tags if t in {"header", "nav", "main", "section", "article", "aside", "footer", "figure"}]
        form_tags = [t for t in unique_tags if t in {"form", "input", "button", "select", "textarea"}]

        variables_functions: List[VariableFunctionItem] = []
        for tag in unique_tags[:12]:
            count = len(re.findall(rf"<\s*{tag}\b", code, re.I))
            category = "Semantic Element" if tag in semantic_tags else ("Form Control" if tag in form_tags else "HTML Tag")
            variables_functions.append(VariableFunctionItem(
                name=f"<{tag}>",
                kind=category,
                data_type="DOM Element",
                description=f"Appears {count} time(s) in the document tree.",
                scope="DOM Structure"
            ))

        # Line-by-line explanation
        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "Structural HTML markup."
            if s.lower().startswith("<!doctype"):
                exp = "Declares the HTML5 document standard to web browsers."
            elif "<html" in s.lower():
                exp = "Root element enclosing the entire web document."
            elif "<head" in s.lower():
                exp = "Metadata container holding page title, scripts, and linked style sheets."
            elif "<meta" in s.lower():
                exp = "Metadata definition (e.g. character encoding or responsive viewport settings)."
            elif "<title" in s.lower():
                exp = "Specifies title shown in browser tab and search results."
            elif "<body" in s.lower():
                exp = "Main document body containing visible content rendered to the user."
            elif any(s.lower().startswith(f"<{t}") for t in ["h1", "h2", "h3", "h4"]):
                exp = "Heading element defining section hierarchy and topic titles."
            elif "<p" in s.lower():
                exp = "Paragraph container for body copy and readable text."
            elif "<div" in s.lower():
                exp = "Generic block-level division container for layout styling."
            elif "<a " in s.lower():
                exp = "Hyperlink anchor element pointing to a target destination or URL."
            elif "<img" in s.lower():
                exp = "Embeds a graphical image with source URL and alt description."
            elif "<form" in s.lower():
                exp = "Form container grouping user input fields for submission."
            elif "<input" in s.lower():
                exp = "Interactive input control allowing user data entry."
            elif "<button" in s.lower():
                exp = "Clickable action button triggering form submission or JS events."
            elif "<ul" in s.lower() or "<ol" in s.lower():
                exp = "List container grouping unordered bullet points or ordered steps."
            elif "<li" in s.lower():
                exp = "Individual list item within a list container."
            elif s.startswith("<!--"):
                exp = "HTML comment ignored by browsers during rendering."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        overview = (
            f"HTML document structure containing {len(lines)} line(s) and {len(unique_tags)} unique element tag type(s). "
            f"Primary elements include {', '.join(f'<{t}>' for t in unique_tags[:6])}. "
            f"{'Utilizes modern HTML5 semantic elements for improved readability and SEO. ' if semantic_tags else 'Structured with standard layout containers. '}"
            "Defines the visual hierarchy and DOM structure ready for browser presentation."
        )

        logic_workflow = (
            "1. Browser parses <!DOCTYPE> declaration to activate standards mode.\n"
            "2. Reads <head> metadata, establishes character set and responsive viewport.\n"
            "3. Constructs the DOM (Document Object Model) tree from nested elements.\n"
            "4. Renders visible elements in the <body> from top to bottom according to the CSS layout model.\n"
            "5. Sets up interactive form controls, links, and user interface actions."
        )

        inputs_text = "User interactions: Form inputs (<input>, <textarea>), button clicks (<button>), and navigation hyperlinks (<a href>)."
        outputs_text = "Visual rendered web page displayed within the browser viewport or sandboxed preview frame."

        concepts = [
            "Document Object Model (DOM)",
            "HTML5 Semantic Architecture",
            "Web Accessibility (WCAG / a11y)",
            "Responsive Web Design Viewport",
            "Client-Side Form Handling"
        ]

        limitations = [
            "HTML defines structure only; visual typography, colors, and layout positioning require CSS.",
            "Dynamic client-side behaviors, input validation, and asynchronous API calls require JavaScript.",
            "Form submission requires a backend server endpoint specified in the 'action' attribute."
        ]

        return AnalysisResult(
            overview=overview,
            logic_workflow=logic_workflow,
            line_by_line=line_by_line[:40],
            inputs=inputs_text,
            outputs=outputs_text,
            variables_functions=variables_functions,
            programming_concepts=concepts,
            limitations=limitations,
            complexity=ComplexityInfo(
                time="N/A (Document Markup)",
                space="N/A (DOM Tree Structure)",
                explanation="HTML is a declarative markup language that defines DOM elements; it does not execute computational algorithms with time/space complexity."
            ),
            learning_takeaway="HTML forms the semantic backbone of every web page. Always prefer meaningful tags (<header>, <main>, <nav>) over unstyled <div> containers for better accessibility and search engine ranking.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )

    def _analyze_css(self, code: str, filename: Optional[str] = None, lang: str = "css") -> AnalysisResult:
        lines = extract_lines(code)
        diagnostics: List[DiagnosticItem] = []

        # Find rules and selectors
        selectors = re.findall(r"([^{]+)\{", code)
        clean_selectors = [s.strip() for s in selectors if s.strip() and not s.strip().startswith("@keyframes")]

        # Layout models detection
        uses_flexbox = bool(re.search(r"display\s*:\s*flex", code, re.I))
        uses_grid = bool(re.search(r"display\s*:\s*grid", code, re.I))
        uses_media = bool(re.search(r"@media", code, re.I))
        uses_animations = bool(re.search(r"(@keyframes|animation\s*:|transition\s*:)", code, re.I))
        uses_vars = bool(re.search(r"(--[a-zA-Z0-9_-]+|\$[a-zA-Z0-9_-]+)", code))

        # Check for !important overuse
        important_matches = re.findall(r"!important", code, re.I)
        if len(important_matches) > 2:
            diagnostics.append(DiagnosticItem(
                id="diag-css-important",
                title="Specificity Concern: Frequent use of !important",
                severity="warning",
                explanation=f"Found {len(important_matches)} occurrences of '!important'. This breaks the natural CSS cascade and makes style maintenance fragile.",
                recommended_correction="Increase selector specificity (e.g. use higher-specificity class combinations or CSS modules) instead of forcing overrides with !important.",
                corrected_snippet="/* Prefer specific selector over !important */\n.parent .component-class { property: value; }",
                detection_type="static_css_linter"
            ))

        # Check for zero with units (e.g. 0px, 0rem, 0em)
        zero_units = re.findall(r"\b0(px|rem|em|%|pt)\b", code)
        if zero_units:
            diagnostics.append(DiagnosticItem(
                id="diag-css-zero-units",
                title="CSS Style Cleanliness: Zero with unnecessary units",
                severity="suggestion",
                explanation=f"Found unit specifiers on zero values (e.g. '0{zero_units[0]}'). Zero is unitless in CSS.",
                recommended_correction="Replace '0px' with '0' for cleaner, more concise style sheets.",
                corrected_snippet="margin: 0;\npadding: 0;",
                detection_type="static_css_linter"
            ))

        variables_functions: List[VariableFunctionItem] = []
        for sel in clean_selectors[:10]:
            sel_clean = re.sub(r"\s+", " ", sel)
            variables_functions.append(VariableFunctionItem(
                name=sel_clean,
                kind="CSS Selector",
                data_type="Style Rule",
                description=f"Applies styles to matching DOM elements.",
                scope="Global Cascading Stylesheet"
            ))

        layout_features = []
        if uses_flexbox: layout_features.append("Flexbox 1D layout model")
        if uses_grid: layout_features.append("CSS Grid 2D layout model")
        if uses_media: layout_features.append("Responsive media queries")
        if uses_animations: layout_features.append("Transitions/Animations")
        if uses_vars: layout_features.append("CSS Custom Properties / Variables")

        overview = (
            f"{lang.upper()} style sheet with {len(lines)} line(s) and {len(clean_selectors)} rule set(s). "
            f"Features utilized: {', '.join(layout_features) if layout_features else 'Standard box model styling'}. "
            "Defines presentation, color schemes, typography, and responsive visual layout."
        )

        logic_workflow = (
            "1. Browser matches selectors against the DOM tree (evaluating ID, class, tag, and pseudo-classes).\n"
            "2. Calculates CSS Specificity scores to resolve conflicting property declarations.\n"
            "3. Computes the Cascade: User agent defaults < external styles < inline styles < !important.\n"
            "4. Constructs the Render Tree and computes Box Model dimensions (content + padding + border + margin).\n"
            "5. Executes Layout (reflow) and Paints visual pixels to the screen."
        )

        line_by_line: List[LineExplanation] = []
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            exp = "CSS declaration or selector."
            if "{" in s and "}" not in s:
                exp = f"Rule block selector targeting matching HTML elements."
            elif s.startswith("display:"):
                exp = "Defines how the element is treated in the document layout flow (e.g. flex, grid, block)."
            elif s.startswith("color:") or s.startswith("background"):
                exp = "Configures color palette and background visual appearance."
            elif s.startswith("margin") or s.startswith("padding"):
                exp = "Configures box model spacing around or within the element container."
            elif s.startswith("font-") or s.startswith("line-height"):
                exp = "Configures typography font family, size, weight, and readability."
            elif s.startswith("@media"):
                exp = "Responsive media query applying styles conditionally based on viewport width or device characteristics."
            elif s.startswith("--") or (lang == "scss" and s.startswith("$")):
                exp = "Design token variable definition for reusable colors or measurements."
            elif s.startswith("border"):
                exp = "Defines element outline border width, style, and color."

            line_by_line.append(LineExplanation(line_number=idx, code_segment=s, explanation=exp))

        concepts = [
            "CSS Cascade & Specificity",
            "CSS Box Model (Margin/Border/Padding)",
            "Responsive Web Design (Media Queries)",
            "Modern Layout Systems (Flexbox / Grid)",
            "Design Tokens & CSS Variables"
        ]

        limitations = [
            "Styles only affect elements present in the target HTML DOM structure.",
            "Cross-browser inconsistencies can occur with bleeding-edge CSS properties without fallbacks.",
            "CSS does not store user state or execute business logic; use JavaScript for stateful interactivity."
        ]

        return AnalysisResult(
            overview=overview,
            logic_workflow=logic_workflow,
            line_by_line=line_by_line[:40],
            inputs="HTML DOM element class names, IDs, attributes, and browser viewport dimensions.",
            outputs="Visual rendered layout, styled typography, colors, animations, and responsive screen presentation.",
            variables_functions=variables_functions,
            programming_concepts=concepts,
            limitations=limitations,
            complexity=ComplexityInfo(
                time="N/A (Style Sheet Presentation)",
                space="N/A (Render Tree Cache)",
                explanation="CSS style sheets are parsed and computed by browser rendering engines; they do not perform algorithmic loop execution."
            ),
            learning_takeaway="Modern CSS relies on clean layout models (Flexbox & Grid) and design tokens (CSS variables) to build robust, maintainable responsive user interfaces without brittle float hacks.",
            diagnostics=diagnostics,
            suggested_code=None,
            explanation_of_changes=None,
            mode="local"
        )
