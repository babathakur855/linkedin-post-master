"""Generates Mermaid diagrams and structured visual assets for blog sections."""

import json
import re
from typing import Callable, Awaitable

import anthropic

from app.config import settings

VISUAL_TYPES = {
    "flowchart": "Mermaid flowchart (graph TD/LR)",
    "sequence_diagram": "Mermaid sequence diagram",
    "timeline": "Mermaid gantt or timeline",
    "comparison_chart": "Markdown table comparing options/features",
    "infographic": "Mermaid mindmap or block diagram",
    "architecture": "Mermaid C4 context or component diagram",
    "pie_chart": "Mermaid pie chart",
    "er_diagram": "Mermaid ER diagram",
}


async def generate_visuals(
    section_title: str,
    section_content: str,
    visual_type: str,
    context: str = "",
    log: Callable[[str, str], Awaitable[None]] | None = None,
) -> str:
    """Return a Markdown-formatted visual block (```mermaid or table) for the given section."""

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    type_desc = VISUAL_TYPES.get(visual_type, visual_type)

    prompt = f"""Create a {type_desc} that visually represents the following blog section.

Section title: {section_title}
Section content:
{section_content}

Additional blog context: {context}

Rules:
- For Mermaid diagrams: output ONLY the fenced code block starting with ```mermaid and ending with ```.
- For Markdown tables: output ONLY the table starting with | header |.
- Keep it clean, minimal, and informative — no extra prose before/after.
- Mermaid node text must be short (≤5 words per node).
- Tables: max 6 columns, max 8 rows.

Output the visual now:"""

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


async def enhance_blog_with_visuals(
    content_markdown: str,
    recommended_visuals: list[str],
    log: Callable[[str, str], Awaitable[None]] | None = None,
) -> str:
    """Insert Mermaid/table visuals into the blog at appropriate section boundaries."""

    async def _log(msg: str) -> None:
        if log:
            await log("visuals", msg)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    await _log("Identifying sections for visual enhancement")

    # Ask Claude where to insert visuals
    placement_prompt = f"""Given this blog post in Markdown, identify up to {len(recommended_visuals)} places to insert a visual.

Blog content:
{content_markdown[:3000]}

Requested visual types: {", ".join(recommended_visuals)}

Return JSON only (no markdown wrapper):
{{
  "insertions": [
    {{
      "after_heading": "exact heading text from blog",
      "visual_type": "one of: {", ".join(VISUAL_TYPES.keys())}",
      "summary": "what the visual should show"
    }}
  ]
}}"""

    msg = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": placement_prompt}],
    )

    json_match = re.search(r"\{[\s\S]+\}", msg.content[0].text)
    if not json_match:
        return content_markdown

    try:
        plan = json.loads(json_match.group())
        insertions = plan.get("insertions", [])
    except json.JSONDecodeError:
        return content_markdown

    enhanced = content_markdown
    for ins in insertions[:4]:  # cap at 4 visuals
        heading = ins.get("after_heading", "")
        vtype = ins.get("visual_type", "flowchart")
        summary = ins.get("summary", "")

        if not heading:
            continue

        await _log(f"Generating {vtype} after: {heading}")

        # Extract the section text that follows this heading
        pattern = rf"(#{{}}\s*{re.escape(heading)}[^\n]*\n)(.*?)(?=\n#|\Z)"
        sec_match = re.search(pattern.format(""), enhanced, re.DOTALL | re.IGNORECASE)
        section_text = sec_match.group(2)[:500] if sec_match else summary

        visual_code = await generate_visuals(
            heading, section_text, vtype, context=summary
        )

        # Insert the visual after the heading + section intro paragraph
        insert_marker = f"## {heading}" if not heading.startswith("#") else heading
        if insert_marker in enhanced:
            # Find end of first paragraph after heading
            idx = enhanced.find(insert_marker)
            newline_after = enhanced.find("\n\n", idx)
            if newline_after != -1:
                enhanced = (
                    enhanced[: newline_after + 2]
                    + "\n"
                    + visual_code
                    + "\n\n"
                    + enhanced[newline_after + 2 :]
                )

    await _log("Visuals inserted into blog")
    return enhanced
