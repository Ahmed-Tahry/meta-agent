from pathlib import Path

from src.tools import Tool


async def file_reader(path: str) -> str:
    p = Path(path).resolve()
    if not p.exists():
        return f"File not found: {path}"
    if not p.is_file():
        return f"Not a file: {path}"
    return p.read_text(encoding="utf-8")


tool_file_reader = Tool(
    name="file_reader",
    fn=file_reader,
    description="Read the contents of a file at the specified path",
)
