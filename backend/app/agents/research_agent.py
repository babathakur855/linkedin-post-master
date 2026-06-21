import json
import re
from typing import Callable, Awaitable

import anthropic
from duckduckgo_search import DDGS

from app.config import settings


async def find_trending_topics(
    niche_name: str,
    keywords: list[str],
    log: Callable[[str, str], Awaitable[None]] | None = None,
) -> dict:
    """Search DuckDuckGo for trending content, then ask Claude to surface top topics and blog ideas."""

    async def _log(msg: str) -> None:
        if log:
            await log("research", msg)

    await _log(f"Searching trending topics for niche: {niche_name}")

    ddgs = DDGS()
    raw: list[dict] = []

    queries = [
        f"{niche_name} trending 2026",
        f"{niche_name} latest developments innovations",
        f"{niche_name} best practices new approaches 2026",
    ]
    for kw in keywords[:3]:
        queries.append(f"{kw} future trends insights")

    for q in queries:
        try:
            results = list(ddgs.text(q, max_results=5))
            raw.extend(results)
        except Exception:
            continue

    seen: set[str] = set()
    unique: list[dict] = []
    for r in raw:
        url = r.get("href", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    await _log(f"Found {len(unique)} unique search results — asking Claude to analyse")

    research_text = "\n\n".join(
        f"Title: {r.get('title', '')}\nSummary: {r.get('body', '')}\nURL: {r.get('href', '')}"
        for r in unique[:20]
    )

    prompt = f"""You are a content-strategy expert specialising in LinkedIn thought-leadership for professionals.

Based on these recent search results about the niche "{niche_name}" (target keywords: {", ".join(keywords)}):

---
{research_text}
---

Return a JSON object with EXACTLY this shape (no markdown wrapper, pure JSON):
{{
  "trending_topics": [
    {{"topic": "string", "description": "string", "why_trending": "string"}}
  ],
  "blog_ideas": [
    {{
      "title": "string",
      "angle": "string",
      "why_timely": "string",
      "key_points": ["string"],
      "target_audience": "string",
      "hook": "string",
      "recommended_format": "post|article",
      "recommended_visuals": ["flowchart|table|infographic|timeline|comparison_chart|sequence_diagram"]
    }}
  ]
}}

Rules:
- trending_topics: exactly 5 items
- blog_ideas: exactly 3 items, ranked best-first
- recommended_format: "article" for deep dives >1000 words, "post" for punchy insights
- recommended_visuals: 1-3 items per idea that would genuinely help communicate the concept"""

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text
    json_match = re.search(r"\{[\s\S]+\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            data = {"trending_topics": [], "blog_ideas": []}
    else:
        data = {"trending_topics": [], "blog_ideas": []}

    data["raw_results"] = unique[:10]
    await _log(f"Research complete — {len(data.get('blog_ideas', []))} ideas generated")
    return data
