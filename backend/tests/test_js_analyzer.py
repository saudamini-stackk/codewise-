from backend.app.analyzer.js_analyzer import JavaScriptAnalyzer

def test_js_analyzer_off_by_one_detection():
    analyzer = JavaScriptAnalyzer()
    code = """
function calculateAverage(numbers) {
    let sum = 0;
    for (let i = 0; i <= numbers.length; i++) {
        sum += numbers[i];
    }
    return sum / numbers.length;
}
"""
    result = analyzer.analyze(code)
    off_by_one = [d for d in result.diagnostics if "off-by-one" in d.id]
    assert len(off_by_one) == 1
    assert off_by_one[0].severity == "error"
    assert result.suggested_code is not None
    assert "< numbers.length" in result.suggested_code

def test_js_analyzer_bracket_mismatch():
    analyzer = JavaScriptAnalyzer()
    code = "function test() { console.log('unclosed');"
    result = analyzer.analyze(code)
    assert len(result.diagnostics) > 0
    assert "Unclosed" in result.diagnostics[0].title
