from src.tools import Tool


async def web_search(query: str) -> str:
    return f"[web_search] Searching for: {query}"


tool_web_search = Tool(
    name="web_search",
    fn=web_search,
    description="Search the web for information",
)
