from src.tools.registry import Tool


async def file_reader(path: str) -> str:
    return f"[file_reader] Reading file: {path}"


tool_file_reader = Tool(
    name="file_reader",
    fn=file_reader,
    description="Read contents of a file",
)
