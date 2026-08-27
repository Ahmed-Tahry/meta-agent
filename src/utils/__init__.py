import os
from pathlib import Path
from typing import Any


def extract_llm_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", str(block)))
            elif hasattr(block, "text"):
                try:
                    parts.append(block.text)  # type: ignore[union-attr]
                except Exception:
                    parts.append(str(block))
            else:
                parts.append(str(block))
        return "\n".join(parts).strip()
    return str(content) if content is not None else ""


def load_env_file(path: str | Path | None = None) -> None:
    env_path = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)
