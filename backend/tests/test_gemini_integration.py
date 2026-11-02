import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from backend.app.config import (
    load_dotenv_safely,
    get_gemini_api_key,
    get_gemini_model,
    get_active_mode,
    get_configured_provider,
)
from backend.app.analyzer.ai_provider import AIProvider, safe_parse_json, normalize_gemini_analysis
from backend.app.analyzer.chat_engine import ChatEngine
from backend.app.analyzer.static_engine import StaticEngine
from backend.app.models import AnalysisResult, ComplexityInfo

SAMPLE_PYTHON_CODE = """def is_even(n: int) -> bool:
    return n % 2 == 0
"""

GEMINI_SAMPLE_JSON = {
    "overview": "Determines whether an integer is even using the modulo operator.",
    "logic_workflow": "1. Accept integer n.\\n2. Compute n % 2.\\n3. Return True if remainder is 0, else False.",
    "line_by_line": [
        {"line_number": 1, "code_segment": "def is_even(n: int) -> bool:", "explanation": "Defines is_even function."},
        {"line_number": 2, "code_segment": "return n % 2 == 0", "explanation": "Checks if remainder when divided by 2 is 0."}
    ],
    "inputs": "An integer value n.",
    "outputs": "Boolean True if even, False if odd.",
    "variables_functions": [
        {"name": "is_even", "kind": "function", "data_type": "bool", "description": "Helper predicate", "scope": "global"},
        {"name": "n", "kind": "parameter", "data_type": "int", "description": "Input integer", "scope": "local"}
    ],
    "programming_concepts": ["Functions", "Modulo Operator", "Boolean Logic"],
    "limitations": ["Input must be an integer."],
    "complexity": {
        "time": "O(1)",
        "space": "O(1)",
        "explanation": "Single arithmetic comparison operation."
    },
    "learning_takeaway": "Modulo by 2 is the canonical standard for parity testing in computer systems.",
    "diagnostics": [],
    "suggested_code": None,
    "explanation_of_changes": None
}


def test_safe_parse_json_raw_and_markdown():
    """Verify safe_parse_json handles both plain JSON and markdown fenced JSON."""
    raw = json.dumps({"test": 123})
    assert safe_parse_json(raw) == {"test": 123}

    fenced = f"```json\n{raw}\n```"
    assert safe_parse_json(fenced) == {"test": 123}

    noisy = f"Here is the result:\n```\n{raw}\n```\nDone."
    assert safe_parse_json(noisy) == {"test": 123}


def test_normalize_gemini_analysis():
    """Verify normalize_gemini_analysis populates missing schema fields defensively."""
    partial = {
        "overview": "Simple test",
        "complexity": "O(n)",  # String instead of object
        "diagnostics": [{"explanation": "missing id and severity"}],
        "variables_functions": [{"name": "foo"}]
    }
    normalized = normalize_gemini_analysis(partial)
    assert isinstance(normalized["complexity"], dict)
    assert normalized["complexity"]["time"] == "O(n)"
    assert normalized["diagnostics"][0]["id"] == "diag-1"
    assert normalized["diagnostics"][0]["severity"] == "warning"
    assert normalized["variables_functions"][0]["kind"] == "variable"


@pytest.mark.anyio
async def test_gemini_analysis_success():
    """Verify AIProvider successfully calls Gemini and returns mode='ai'."""
    static_engine = StaticEngine()
    provider = AIProvider(static_fallback=static_engine)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(GEMINI_SAMPLE_JSON)}]
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response
        result = await provider._call_gemini(SAMPLE_PYTHON_CODE, "python", "AIzaSyTestFakeKey", "test.py")

        assert result is not None
        assert result.mode == "ai"
        assert "Determines whether an integer is even" in result.overview
        assert result.complexity.time == "O(1)"
        assert len(result.line_by_line) == 2


@pytest.mark.anyio
async def test_gemini_analysis_quota_fallback_429():
    """Verify that HTTP 429 rate limit triggers local fallback with a clear user notice."""
    static_engine = StaticEngine()
    provider = AIProvider(static_fallback=static_engine)

    fake_response = MagicMock()
    fake_response.status_code = 429
    fake_response.text = "Quota exceeded"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response
        result = await provider._call_gemini(SAMPLE_PYTHON_CODE, "python", "AIzaSyTestFakeKey", "test.py")

        assert result is not None
        assert result.mode == "local"
        # Notice diagnostic inserted
        notices = [d for d in result.diagnostics if d.id == "gemini-quota-notice"]
        assert len(notices) == 1
        assert "Gemini Free-Tier Rate Limit Reached" in notices[0].title


@pytest.mark.anyio
async def test_gemini_analysis_auth_failure_400():
    """Verify that HTTP 400 invalid key triggers local fallback with an authentication notice."""
    static_engine = StaticEngine()
    provider = AIProvider(static_fallback=static_engine)

    fake_response = MagicMock()
    fake_response.status_code = 400
    fake_response.text = "API key not valid"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_response
        result = await provider._call_gemini(SAMPLE_PYTHON_CODE, "python", "AIzaSyInvalidKey", "test.py")

        assert result is not None
        assert result.mode == "local"
        notices = [d for d in result.diagnostics if d.id == "gemini-auth-notice"]
        assert len(notices) == 1
        assert "Authentication Issue" in notices[0].title


@pytest.mark.anyio
async def test_gemini_analysis_network_error():
    """Verify that network timeout or connection failure triggers local fallback seamlessly."""
    static_engine = StaticEngine()
    provider = AIProvider(static_fallback=static_engine)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        result = await provider._call_gemini(SAMPLE_PYTHON_CODE, "python", "AIzaSyTestFakeKey", "test.py")

        assert result is not None
        assert result.mode == "local"
        notices = [d for d in result.diagnostics if d.id == "gemini-network-notice"]
        assert len(notices) == 1
        assert "Network Unreachable" in notices[0].title


@pytest.mark.anyio
async def test_gemini_chat_success():
    """Verify ChatEngine uses Gemini when configured and returns mode='ai'."""
    engine = ChatEngine()
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "In simpler terms, this function tests if a number is divisible by 2 with no remainder."}]
                }
            }
        ]
    }

    with patch("backend.app.analyzer.chat_engine.get_gemini_api_key", return_value="AIzaSyTestFakeKey"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = fake_response
            res = await engine.answer_question(
                question="Explain more simply",
                code=SAMPLE_PYTHON_CODE,
                language="python",
                analysis=None,
                history=[]
            )
            assert res["mode"] == "ai"
            assert "divisible by 2" in res["reply"]


@pytest.mark.anyio
async def test_gemini_chat_quota_fallback():
    """Verify ChatEngine handles HTTP 429 by falling back to local rules with clear notice."""
    engine = ChatEngine()
    fake_response = MagicMock()
    fake_response.status_code = 429
    fake_response.text = "RESOURCE_EXHAUSTED"

    with patch("backend.app.analyzer.chat_engine.get_gemini_api_key", return_value="AIzaSyTestFakeKey"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = fake_response
            res = await engine.answer_question(
                question="Show a dry run",
                code=SAMPLE_PYTHON_CODE,
                language="python",
                analysis=None,
                history=[]
            )
            assert "Gemini Free-Tier Rate Limit Reached" in res["reply"]
            # Fallback dry run provided
            assert "Dry Run" in res["reply"]


@pytest.mark.anyio
async def test_fallback_when_no_api_key():
    """Verify that when no GEMINI_API_KEY is configured, the local static engine is used."""
    static_engine = StaticEngine()
    provider = AIProvider(static_fallback=static_engine)

    with patch("backend.app.analyzer.ai_provider.get_gemini_api_key", return_value=""):
        with patch("backend.app.analyzer.ai_provider.OPENAI_API_KEY", ""):
            with patch("backend.app.analyzer.ai_provider.CODEWISE_AI_KEY", ""):
                result = await provider.analyze_with_ai_or_fallback(SAMPLE_PYTHON_CODE, "python", "even.py")
                assert result.mode == "local"
                assert result.overview != ""
                assert len(result.line_by_line) > 0
