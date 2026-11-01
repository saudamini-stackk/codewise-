from backend.app.analyzer.cpp_analyzer import CppAnalyzer

def test_cpp_analyzer_factorial():
    analyzer = CppAnalyzer()
    code = """
#include <iostream>
using namespace std;

long long computeFactorial(int n) {
    long long factorial = 1;
    for (int i = 1; i <= n; ++i) {
        factorial *= i;
    }
    return factorial;
}

int main() {
    int n = 5;
    cout << computeFactorial(n) << endl;
    return 0;
}
"""
    result = analyzer.analyze(code)
    assert "Functions" in result.programming_concepts
    assert "Loops" in result.programming_concepts
    assert result.complexity.time == "O(n)"
    assert len(result.line_by_line) > 5

def test_cpp_missing_iostream():
    analyzer = CppAnalyzer()
    code = """
int main() {
    cout << "Hello" << endl;
    return 0;
}
"""
    result = analyzer.analyze(code)
    missing = [d for d in result.diagnostics if "missing-iostream" in d.id]
    assert len(missing) == 1
    assert missing[0].severity == "error"
    assert result.suggested_code.startswith("#include <iostream>")
