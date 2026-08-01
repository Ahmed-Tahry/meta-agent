import httpx

from src.tools import Tool

_API_URL = "https://en.wikipedia.org/w/api.php"
_HEADERS = {
    "User-Agent": ("MetaAgent/1.0 (https://github.com/meta-agent; ahmed@example.com) httpx/0.28"),
}


async def _search(client: httpx.AsyncClient, query: str, max_results: int) -> list[dict] | str:
    resp = await client.get(
        _API_URL,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
        },
    )
    if resp.status_code == 403:
        return f"Wikipedia search blocked for '{query}' (403). Try again later."
    resp.raise_for_status()
    data = resp.json()
    return data.get("query", {}).get("search", [])


async def _extracts(client: httpx.AsyncClient, titles: list[str], max_results: int) -> dict:
    resp = await client.get(
        _API_URL,
        params={
            "action": "query",
            "titles": "|".join(titles),
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "exlimit": max_results,
            "format": "json",
        },
    )
    if resp.status_code == 403:
        return {}
    resp.raise_for_status()
    data = resp.json()
    return data.get("query", {}).get("pages", {})


async def web_search(query: str, max_results: int = 5) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=_HEADERS) as client:
        search_result = await _search(client, query, max_results)

    if isinstance(search_result, str):
        return search_result

    if not search_result:
        return f"No Wikipedia results found for '{query}'."

    titles = [p["title"] for p in search_result]

    async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=_HEADERS) as client:
        pages_map = await _extracts(client, titles, max_results)

    lines = [f"Wikipedia search results for: {query}", "---"]
    for i, page in enumerate(search_result, 1):
        page_id = str(page["pageid"])
        page_info = pages_map.get(page_id, {})
        extract = page_info.get("extract", "")
        snippet = (
            extract[:500]
            if extract
            else page.get("snippet", "")
            .replace('<span class="searchmatch">', "")
            .replace("</span>", "")
        )
        url = f"https://en.wikipedia.org/wiki/{page['title'].replace(' ', '_')}"
        lines.append(f"Result {i}: {page['title']}")
        lines.append(f"  URL: {url}")
        if snippet:
            lines.append(f"  {snippet}")
        lines.append("")

    return "\n".join(lines).strip()


tool_web_search = Tool(
    name="web_search",
    fn=web_search,
    description="Search Wikipedia for information on a given topic",
)
