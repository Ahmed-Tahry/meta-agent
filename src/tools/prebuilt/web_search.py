from src.tools import Tool


async def web_search(query: str) -> str:
    return (
        f"Simulated search results for: {query}\n"
        "1) Renewable energy reduces greenhouse gas emissions and improves air quality.\n"
        "2) Renewables create jobs, lower long-term electricity costs, and improve energy independence.\n"
        "3) Social benefits include better public health outcomes and improved energy access."
    )


tool_web_search = Tool(
    name="web_search",
    fn=web_search,
    description="Search the web for information",
)
