from src.tools import Tool


async def code_executor(code: str, language: str = "python") -> str:
    return (
        f"Execution result ({language}):\n"
        f"---\n"
        f"[Code execution is not available in development mode.\n"
        f"Submitted code ({len(code)} chars) would run in a sandboxed "
        f"environment in production.]\n"
        f"---\n"
        f"Code preview:\n{code[:500]}"
    )


tool_code_executor = Tool(
    name="code_executor",
    fn=code_executor,
    description="Execute code in a sandboxed environment",
)
