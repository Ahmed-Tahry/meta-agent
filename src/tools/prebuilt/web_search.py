from src.tools import Tool


async def web_search(query: str) -> str:
    return (
        f"Web search results for: {query}\n"
        f"---\n"
        f"Result 1: Analysis of {query} shows significant developments in recent years. "
        f"Multiple sources report growing adoption across various sectors.\n"
        f"Result 2: Experts indicate that trends related to {query} are accelerating, "
        f"with implications for technology, policy, and industry practices.\n"
        f"Result 3: Data suggests that {query} continues to be an area of active "
        f"research and investment, with measurable outcomes emerging."
    )


tool_web_search = Tool(
    name="web_search",
    fn=web_search,
    description="Search the web for information on a given topic",
)
