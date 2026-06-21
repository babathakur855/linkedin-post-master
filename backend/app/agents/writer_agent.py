"""Writes full blog content in Markdown and generates LinkedIn post/article versions."""

from typing import Callable, Awaitable

import anthropic

from app.config import settings


async def write_blog(
    idea: dict,
    niche_name: str,
    research_summary: str,
    publish_format: str = "post",
    log: Callable[[str, str], Awaitable[None]] | None = None,
) -> dict:
    """
    Returns:
        {
          title, content_markdown,
          linkedin_post,              # short text post (~1300 chars)
          linkedin_article_title,     # article headline
          linkedin_article_body,      # full article HTML-ish body (Markdown)
        }
    """

    async def _log(msg: str) -> None:
        if log:
            await log("writing", msg)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    title = idea.get("title", "Untitled")
    angle = idea.get("angle", "")
    key_points = idea.get("key_points", [])
    hook = idea.get("hook", "")
    target_audience = idea.get("target_audience", "professionals")
    recommended_visuals = idea.get("recommended_visuals", [])

    await _log(f"Writing blog: {title}")

    # ── Full Markdown blog ─────────────────────────────────────────────────────
    blog_prompt = f"""You are a senior tech writer and LinkedIn thought-leader writing a blog post for "{niche_name}" professionals.

Blog brief:
- Title: {title}
- Angle / unique take: {angle}
- Hook: {hook}
- Key points to cover: {", ".join(key_points)}
- Target audience: {target_audience}
- Research context: {research_summary[:1500]}

Write a COMPLETE, high-quality blog post in Markdown with the following structure:
1. Compelling title (##)
2. Executive summary / TL;DR (italic, 2-3 sentences)
3. Introduction (engaging, references the hook)
4. 3-5 main sections (## headings), each 150-250 words
5. Key takeaways / action items (bullet list)
6. Conclusion with a call-to-action for LinkedIn engagement
7. 5-7 relevant hashtags at the end (e.g. #AI #CloudComputing)

Tone: Professional but conversational. Data-driven where possible. Use examples.

Where you'd like a visual (chart, diagram, table), insert a placeholder comment like:
<!-- VISUAL: flowchart showing X -->
<!-- VISUAL: table comparing A vs B vs C -->
<!-- VISUAL: timeline of Y -->

Output ONLY the Markdown — no preamble, no explanation."""

    blog_msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": blog_prompt}],
    )
    content_markdown = blog_msg.content[0].text.strip()
    await _log("Full blog draft complete")

    # ── LinkedIn Post version ──────────────────────────────────────────────────
    await _log("Creating LinkedIn post version")
    post_prompt = f"""Convert this blog into a high-performing LinkedIn POST (NOT an article).

Blog title: {title}
Blog content:
{content_markdown[:2000]}

LinkedIn post rules:
- Max 3000 characters total (aim for ~1200-1500)
- Start with a STRONG first line (no "I" at start — use a stat, question, or bold statement)
- Use line breaks generously (every 1-2 sentences)
- 3-5 bullet points for key insights (use •)
- End with a question to drive comments
- 4-6 relevant hashtags on final line
- Emojis sparingly (1-2 per section max), only where they add meaning

Output ONLY the post text — no labels, no quotes."""

    post_msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": post_prompt}],
    )
    linkedin_post = post_msg.content[0].text.strip()

    # ── LinkedIn Article version ───────────────────────────────────────────────
    await _log("Creating LinkedIn article version")
    article_prompt = f"""Convert this blog into a LinkedIn ARTICLE (long-form, published on LinkedIn Pulse).

Blog content:
{content_markdown}

LinkedIn article rules:
- Article title: compelling, SEO-friendly (max 100 chars)
- Body: well-structured Markdown, can be 800-2000 words
- Use ## for section headers
- Include statistics, examples, and actionable advice
- Professional tone
- End with author call-to-action

Return JSON only:
{{
  "article_title": "...",
  "article_body": "full Markdown body here"
}}"""

    article_msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": article_prompt}],
    )

    import json
    import re

    json_match = re.search(r"\{[\s\S]+\}", article_msg.content[0].text)
    if json_match:
        try:
            art = json.loads(json_match.group())
            article_title = art.get("article_title", title)
            article_body = art.get("article_body", content_markdown)
        except json.JSONDecodeError:
            article_title = title
            article_body = content_markdown
    else:
        article_title = title
        article_body = content_markdown

    await _log("All content versions ready")

    return {
        "title": title,
        "content_markdown": content_markdown,
        "linkedin_post": linkedin_post,
        "linkedin_article_title": article_title,
        "linkedin_article_body": article_body,
        "recommended_visuals": recommended_visuals,
    }


async def apply_revisions(
    original_markdown: str,
    changes_requested: str,
    niche_name: str,
    log: Callable[[str, str], Awaitable[None]] | None = None,
) -> dict:
    """Apply user-requested changes to an existing blog draft."""

    async def _log(msg: str) -> None:
        if log:
            await log("revision", msg)

    await _log("Applying requested changes")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = f"""You are editing a LinkedIn blog post for the "{niche_name}" niche.

Original blog:
{original_markdown}

User-requested changes:
{changes_requested}

Apply ALL requested changes carefully. Maintain the same structure and quality.
Output ONLY the revised Markdown — no preamble."""

    msg = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    revised_markdown = msg.content[0].text.strip()

    # Re-generate LinkedIn versions for revised content

    post_prompt = f"""Create a LinkedIn post for this blog. Max 1500 chars. Strong opener, bullets, question at end, hashtags.

{revised_markdown[:1500]}

Output ONLY the post text."""

    post_msg = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": post_prompt}],
    )
    linkedin_post = post_msg.content[0].text.strip()

    await _log("Revision complete")

    return {
        "content_markdown": revised_markdown,
        "linkedin_post": linkedin_post,
    }
