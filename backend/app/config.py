import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_dotenv_safely() -> None:
    """Safely loads environment variables from backend/.env or root .env if present.
    Pure Python implementation, zero third-party dependencies required.
    Does not overwrite existing environment variables.
    """
    candidates = [
        BASE_DIR / "backend" / ".env",
        BASE_DIR / ".env"
    ]
    for env_path in candidates:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip()
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

# Initial environment variable load
load_dotenv_safely()

# Persistent database directory: use local data/ directory within workspace
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("CODEWISE_DB_PATH", str(DATA_DIR / "codewise.db")))

def get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        load_dotenv_safely()
        key = os.getenv("GEMINI_API_KEY", "").strip()
    return key

def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip() or "gemini-flash-lite-latest"

def get_ai_provider() -> str:
    return os.getenv("AI_PROVIDER", "auto").lower().strip()

def get_active_mode() -> str:
    if get_gemini_api_key() or os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("ANTHROPIC_API_KEY", "").strip() or os.getenv("CODEWISE_AI_KEY", "").strip():
        return "ai"
    return "local"

def get_configured_provider() -> str:
    prov = get_ai_provider()
    g_key = get_gemini_api_key()
    o_key = os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("CODEWISE_AI_KEY", "").strip()
    a_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    if (prov == "gemini" and g_key) or (prov == "auto" and g_key):
        return f"gemini ({get_gemini_model()})"
    if (prov == "openai" and o_key) or (prov == "auto" and o_key):
        return f"openai ({os.getenv('AI_MODEL_NAME', 'gpt-4o-mini')})"
    if (prov == "anthropic" and a_key) or (prov == "auto" and a_key):
        return "anthropic"
    return "none (local rule-based engine)"

# Backwards compatible module exports
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = get_gemini_api_key()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CODEWISE_AI_KEY = os.getenv("CODEWISE_AI_KEY", "").strip()
AI_PROVIDER = get_ai_provider()
GEMINI_MODEL = get_gemini_model()
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gemini-flash-lite-latest" if (GEMINI_API_KEY or AI_PROVIDER == "gemini") else "gpt-4o-mini").strip()
