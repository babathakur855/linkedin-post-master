"""Main pipeline: research → write → enhance visuals → send for review."""

from typing import Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Blog, BlogStatus, GenerationLog, Niche, AppSetting


async def _get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def _add_log(db: AsyncSession, blog_id: int, phase: str, message: str) -> None:
    log = GenerationLog(blog_id=blog_id, phase=phase, message=message)
    db.add(log)
    await db.commit()


async def generate_blog_pipeline(
    blog_id: int,
    db: AsyncSession,
    ws_send: Callable[[str, str], Awaitable[None]] | None = None,
) -> None:
    """Full generation pipeline. Updates the Blog row in-place."""

    from app.agents import research_agent, writer_agent, visual_agent
    from app.services import email_service

    async def log(phase: str, message: str) -> None:
        await _add_log(db, blog_id, phase, message)
        if ws_send:
            await ws_send(phase, message)

    # Load blog
    blog: Blog | None = (
        await db.execute(select(Blog).where(Blog.id == blog_id))
    ).scalar_one_or_none()

    if not blog:
        return

    niche: Niche | None = (
        await db.execute(select(Niche).where(Niche.id == blog.niche_id))
    ).scalar_one_or_none()

    if not niche:
        blog.status = BlogStatus.FAILED
        await db.commit()
        return

    try:
        # ── Phase 1: Research ──────────────────────────────────────────────────
        blog.status = BlogStatus.RESEARCHING
        await db.commit()

        research_data = await research_agent.find_trending_topics(
            niche.name, niche.keywords, log=log
        )

        # Pick the best blog idea
        ideas = research_data.get("blog_ideas", [])
        if not ideas:
            await log("error", "No blog ideas generated from research")
            blog.status = BlogStatus.FAILED
            await db.commit()
            return

        best_idea = ideas[0]
        # Honour niche publish_format unless the idea strongly recommends otherwise
        publish_format = niche.publish_format or best_idea.get(
            "recommended_format", "post"
        )

        topics_summary = "; ".join(
            t.get("topic", "") for t in research_data.get("trending_topics", [])[:3]
        )
        blog.research_summary = topics_summary
        blog.topic = best_idea.get("title", "")
        await db.commit()

        # ── Phase 2: Write ─────────────────────────────────────────────────────
        blog.status = BlogStatus.WRITING
        await db.commit()

        written = await writer_agent.write_blog(
            idea=best_idea,
            niche_name=niche.name,
            research_summary=topics_summary,
            publish_format=publish_format,
            log=log,
        )

        # ── Phase 3: Visuals ───────────────────────────────────────────────────
        recommended_visuals = written.get("recommended_visuals", ["flowchart", "table"])
        enhanced_markdown = await visual_agent.enhance_blog_with_visuals(
            written["content_markdown"],
            recommended_visuals,
            log=log,
        )

        # ── Save content ───────────────────────────────────────────────────────
        blog.title = written["title"]
        blog.content_markdown = enhanced_markdown
        blog.linkedin_post = written["linkedin_post"]
        blog.linkedin_article_title = written.get(
            "linkedin_article_title", written["title"]
        )
        blog.linkedin_article_body = written.get(
            "linkedin_article_body", enhanced_markdown
        )
        blog.publish_format = publish_format
        await db.commit()

        # ── Phase 4: Send for review ───────────────────────────────────────────
        review_email = await _get_setting(db, "review_email")
        if not review_email:
            await log("warning", "No review email configured — blog saved as draft")
            blog.status = BlogStatus.DRAFT
            await db.commit()
            return

        await log("email", f"Sending blog draft for review to {review_email}")

        frontend_url = await _get_setting(db, "frontend_url", "http://localhost:3040")

        message_id = await email_service.send_review_email(
            to_email=review_email,
            blog_id=blog.id,
            blog_title=blog.title,
            content_markdown=enhanced_markdown,
            linkedin_post=blog.linkedin_post,
            preview_url=f"{frontend_url}/blogs/{blog.id}",
            db=db,
        )

        blog.email_message_id = message_id
        blog.review_email = review_email
        blog.status = BlogStatus.REVIEW_PENDING
        await db.commit()

        await log("done", f"Blog '{blog.title}' sent for review — check {review_email}")

    except Exception as exc:
        blog.status = BlogStatus.FAILED
        await _add_log(db, blog_id, "error", str(exc))
        await db.commit()
        raise


async def apply_email_revision(
    blog: Blog,
    changes_requested: str,
    db: AsyncSession,
    ws_send: Callable[[str, str], Awaitable[None]] | None = None,
) -> None:
    """Revise a blog based on email feedback and resend for review."""

    from app.agents import writer_agent, visual_agent
    from app.services import email_service
    from app.models import BlogRevision

    async def log(phase: str, message: str) -> None:
        await _add_log(db, blog.id, phase, message)
        if ws_send:
            await ws_send(phase, message)

    niche: Niche | None = (
        await db.execute(select(Niche).where(Niche.id == blog.niche_id))
    ).scalar_one_or_none()

    # Save current state as a revision
    revision = BlogRevision(
        blog_id=blog.id,
        revision_number=blog.revision_count + 1,
        content_markdown=blog.content_markdown,
        linkedin_post=blog.linkedin_post,
        linkedin_article_body=blog.linkedin_article_body,
        changes_requested=changes_requested,
    )
    db.add(revision)

    blog.status = BlogStatus.WRITING
    blog.revision_count += 1
    await db.commit()

    await log(
        "revision",
        f"Applying revision #{blog.revision_count}: {changes_requested[:100]}",
    )

    revised = await writer_agent.apply_revisions(
        original_markdown=blog.content_markdown,
        changes_requested=changes_requested,
        niche_name=niche.name if niche else "general",
        log=log,
    )

    enhanced = await visual_agent.enhance_blog_with_visuals(
        revised["content_markdown"],
        ["flowchart", "table"],
        log=log,
    )

    blog.content_markdown = enhanced
    blog.linkedin_post = revised["linkedin_post"]
    await db.commit()

    review_email = await _get_setting(db, "review_email")
    frontend_url = await _get_setting(db, "frontend_url", "http://localhost:3040")

    message_id = await email_service.send_review_email(
        to_email=review_email or blog.review_email or "",
        blog_id=blog.id,
        blog_title=blog.title,
        content_markdown=enhanced,
        linkedin_post=blog.linkedin_post,
        preview_url=f"{frontend_url}/blogs/{blog.id}",
        db=db,
        revision_number=blog.revision_count,
    )

    blog.email_message_id = message_id
    blog.status = BlogStatus.REVIEW_PENDING
    await db.commit()

    await log(
        "done", f"Revised blog resent for review (revision #{blog.revision_count})"
    )
