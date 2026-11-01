from abc import ABC, abstractmethod
from typing import Optional, List
from ..models import AnalysisResult, LineExplanation, VariableFunctionItem, DiagnosticItem, ComplexityInfo

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, code: str, filename: Optional[str] = None) -> AnalysisResult:
        """Analyze source code and return a structured AnalysisResult."""
        pass

def extract_lines(code: str) -> List[str]:
    return code.splitlines()

def get_code_snippet(lines: List[str], line_no: Optional[int], context: int = 1) -> Optional[str]:
    if not line_no or line_no < 1 or line_no > len(lines):
        return None
    start = max(0, line_no - 1 - context)
    end = min(len(lines), line_no + context)
    return "\n".join(lines[start:end])
