from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class LineExplanation(BaseModel):
    line_number: int
    code_segment: str
    explanation: str

class VariableFunctionItem(BaseModel):
    name: str
    kind: str = "variable"
    data_type: Optional[str] = "unknown"
    description: str
    scope: Optional[str] = "global"

class DiagnosticItem(BaseModel):
    id: str
    title: str
    severity: str = "warning"
    line_number: Optional[int] = None
    explanation: str
    recommended_correction: str
    corrected_snippet: Optional[str] = None
    detection_type: str = "static_heuristic"

class ComplexityInfo(BaseModel):
    time: str
    space: str
    explanation: str

class DryRunStep(BaseModel):
    step: int
    line_number: Optional[int] = None
    action: str
    state: Optional[dict] = {}
    notes: str = ""

class LoopDetails(BaseModel):
    has_loops: bool = False
    loop_type: str = "None"
    description: str = "No loops present in this code."
    condition: str = ""
    iteration_explanation: str = ""
    termination: str = ""

class ExpectedIO(BaseModel):
    input_source: str = "None"
    input_type: str = "None"
    input_format: str = "None"
    input_range: str = "None"
    sample_input: Optional[str] = None
    output_mechanism: str = "None"
    output_type: str = "None"
    sample_output: Optional[str] = None
    relationship: str = ""
    explanation: Optional[str] = ""
    is_deterministic: bool = True

class VivaQuestionItem(BaseModel):
    question: str
    answer: str
    concept: Optional[str] = None

class AnalysisResult(BaseModel):
    overview: str
    logic_workflow: str
    line_by_line: List[LineExplanation] = []
    inputs: str
    outputs: str
    expected_io: Optional[ExpectedIO] = None
    variables_functions: List[VariableFunctionItem] = []
    programming_concepts: List[str] = []
    limitations: List[str] = []
    complexity: ComplexityInfo
    learning_takeaway: str
    diagnostics: List[DiagnosticItem] = []
    suggested_code: Optional[str] = None
    explanation_of_changes: Optional[str] = None
    mode: str = "local"
    dry_run: List[DryRunStep] = []
    loop_details: Optional[LoopDetails] = None
    viva_questions: Optional[List[VivaQuestionItem]] = []

class RunCodeRequest(BaseModel):
    code: str = Field(..., max_length=250000)
    language: str = "python"
    input_data: Optional[str] = ""
    session_id: Optional[str] = None
    code_version_id: Optional[str] = None

class RunCodeResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int
    status: str

class VerifySampleRequest(BaseModel):
    code: str = Field(..., max_length=250000)
    language: str = "python"
    sample_input: Optional[str] = ""
    expected_output: Optional[str] = ""

class VerifySampleResponse(BaseModel):
    is_match: bool
    actual_output: str
    expected_output: str
    exit_code: int
    execution_time_ms: int
    notes: str

class DetectLanguageRequest(BaseModel):
    code: str = Field(..., max_length=250000)
    filename: Optional[str] = None

class AnalyzeRequest(BaseModel):
    code: str = Field(..., max_length=250000, description="Source code text to analyze")
    language: str = Field("python", description="Programming language: python, javascript, cpp, etc.")
    filename: Optional[str] = None
    session_id: Optional[str] = None
    code_version_id: Optional[str] = None

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=5000)
    session_id: Optional[str] = None
    code_version_id: Optional[str] = None

class SessionCreateRequest(BaseModel):
    title: Optional[str] = None
    filename: Optional[str] = "main.py"
    language: Optional[str] = "python"
    code: Optional[str] = ""
    is_runnable: Optional[bool] = None

class SessionUpdateRequest(BaseModel):
    title: Optional[str] = None
    filename: Optional[str] = None

class SaveVersionRequest(BaseModel):
    code: str = Field(..., max_length=250000)
    language: Optional[str] = None
    filename: Optional[str] = None

class RestoreVersionRequest(BaseModel):
    version_id: Optional[str] = None
    version_number: Optional[int] = None

class MessageItem(BaseModel):
    id: str
    session_id: str
    code_version_id: Optional[str] = None
    role: Literal["user", "assistant", "system"]
    content: str
    mode: str
    created_at: str

class CodeVersionItem(BaseModel):
    id: str
    session_id: str
    version_number: int
    code: str
    language: str
    filename: Optional[str] = None
    created_at: str
    analysis: Optional[AnalysisResult] = None
    execution_result: Optional[RunCodeResponse] = None

class SessionSummary(BaseModel):
    id: str
    title: str
    filename: Optional[str] = None
    language: Optional[str] = None
    is_runnable: bool = True
    version_count: int = 1
    active_version_number: Optional[int] = 1
    created_at: str
    updated_at: str

class SessionDetail(BaseModel):
    id: str
    title: str
    filename: Optional[str] = None
    language: Optional[str] = None
    is_runnable: bool = True
    created_at: str
    updated_at: str
    versions: List[CodeVersionItem] = []
    messages: List[MessageItem] = []

class SystemStatusResponse(BaseModel):
    product_name: str = "codewise"
    tagline: str = "understand the code. master the logic."
    status: str = "healthy"
    active_mode: str
    configured_provider: str
    database_path: str
    python_version: str
    total_sessions: int

# ==============================================================================
# Authentication Models
# ==============================================================================

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: str

class AuthResponse(BaseModel):
    token: str
    user: UserResponse
    expires_at: str
    recovery_key: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str

class ForgotPasswordRequest(BaseModel):
    email: str
    recovery_key: str
    new_password: str
    confirm_password: str

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class DemoCredentialsResponse(BaseModel):
    email: str
    password: str
    recovery_key: str
