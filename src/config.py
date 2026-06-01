import os


GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

MAX_TOOL_CALLS: int = int(os.environ.get("MAX_TOOL_CALLS", "10"))
MAX_RETRIES: int = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_DELAY: float = float(os.environ.get("RETRY_DELAY", "1.0"))
LLM_TIMEOUT: float = float(os.environ.get("LLM_TIMEOUT", "60.0"))
TOOL_CALL_DELAY: float = float(os.environ.get("TOOL_CALL_DELAY", "1.0"))
