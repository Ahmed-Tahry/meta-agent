from src.tools.registry import Tool


async def code_executor(code: str, language: str = "python") -> str:
    return f"[code_executor] Executing {language} code: {code[:50]}..."


tool_code_executor = Tool(
    name="code_executor",
    fn=code_executor,
    description="Execute code in a sandboxed environment",
)
