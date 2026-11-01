import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Persistent database directory: use local data/ directory within workspace
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv("CODEWISE_DB_PATH", str(DATA_DIR / "codewise.db")))

# AI Provider Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CODEWISE_AI_KEY = os.getenv("CODEWISE_AI_KEY", "").strip()

# AI Model settings
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").lower()  # 'auto', 'openai', 'gemini'
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-4o-mini")

def get_active_mode() -> str:
    if OPENAI_API_KEY or GEMINI_API_KEY or ANTHROPIC_API_KEY or CODEWISE_AI_KEY:
        return "ai"
    return "local"

def get_configured_provider() -> str:
    if GEMINI_API_KEY:
        return "gemini"
    if OPENAI_API_KEY or CODEWISE_AI_KEY:
        return "openai"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    return "none (local rule-based engine)"
