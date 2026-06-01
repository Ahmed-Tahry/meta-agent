from src.tools import Tool


async def file_reader(path: str) -> str:
    return (
        f"File: {path}\n"
        f"Content: [File reading is not available in development mode. "
        f"The file at {path} would be read and returned in production.]"
    )


tool_file_reader = Tool(
    name="file_reader",
    fn=file_reader,
    description="Read the contents of a file at the specified path",
)
