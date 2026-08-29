def web_search(query: str, max_results: int = 5) -> list[dict]:
    from ddgs import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return [
        {
            "title": r.get("title"),
            "href": r.get("href") or r.get("url"),
            "body": r.get("body") or r.get("description"),
        }
        for r in results
    ]


def format_search(results: list[dict]) -> str:
    if not results:
        return "No search results."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.get('title')}\n{r.get('href')}\n{r.get('body')}")
    return "\n\n".join(lines)
