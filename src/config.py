import os


GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
