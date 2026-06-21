"""APScheduler setup — creates cron jobs for each active niche."""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import SessionLocal
from app.models import AppSetting, Blog, BlogStatus, Niche

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_imap_task: asyncio.Task | None = None


async def _trigger_generation_for_niche(niche_id: int) -> None:
    """Create a new Blog row and kick off the generation pipeline."""
    from app.agents.orchestrator import generate_blog_pipeline

    async with SessionLocal() as db:
        niche = (
            await db.execute(select(Niche).where(Niche.id == niche_id))
        ).scalar_one_or_none()

        if not niche or not niche.active:
            return

        blog = Blog(niche_id=niche_id, status=BlogStatus.DRAFT)
        db.add(blog)
        await db.commit()
        await db.refresh(blog)
        blog_id = blog.id

    async with SessionLocal() as db:
        await generate_blog_pipeline(blog_id, db)


def _niche_to_cron(niche: Niche) -> CronTrigger | None:
    """Convert niche schedule to APScheduler CronTrigger."""
    hour, minute = "9", "0"
    if niche.schedule_time:
        parts = niche.schedule_time.split(":")
        hour = parts[0].lstrip("0") or "0"
        minute = parts[1].lstrip("0") or "0" if len(parts) > 1 else "0"

    if niche.frequency == "daily":
        return CronTrigger(hour=hour, minute=minute)

    if niche.frequency == "weekly":
        dow = (
            niche.schedule_day if niche.schedule_day is not None else 0
        )  # Monday default
        return CronTrigger(day_of_week=dow, hour=hour, minute=minute)

    if niche.frequency == "biweekly":
        # Fire every 2 weeks: use week modulo — APScheduler doesn't have a direct biweekly,
        # so we fire weekly and skip every other run via the job's own counter.
        # Simpler: fire on day 1 and day 15 of each month.
        return CronTrigger(day="1,15", hour=hour, minute=minute)

    if niche.frequency == "monthly":
        day = niche.schedule_day if niche.schedule_day else 1
        return CronTrigger(day=day, hour=hour, minute=minute)

    return None


async def reload_schedules() -> None:
    """Re-read all active niches from DB and sync scheduled jobs."""
    async with SessionLocal() as db:
        niches = (
            (await db.execute(select(Niche).where(Niche.active)))
            .scalars()
            .all()
        )  # noqa: E712

    # Remove all niche jobs
    for job in scheduler.get_jobs():
        if job.id.startswith("niche_"):
            job.remove()

    for niche in niches:
        trigger = _niche_to_cron(niche)
        if trigger:
            job_id = f"niche_{niche.id}"
            scheduler.add_job(
                _trigger_generation_for_niche,
                trigger=trigger,
                args=[niche.id],
                id=job_id,
                replace_existing=True,
            )
            logger.info(
                "Scheduled niche %d (%s) with trigger %s", niche.id, niche.name, trigger
            )


async def _imap_poll_loop() -> None:
    """Background loop: every 5 minutes, poll IMAP for email replies."""
    from app.services.email_service import classify_reply, poll_for_replies
    from app.agents.orchestrator import apply_email_revision

    while True:
        await asyncio.sleep(300)  # 5 minutes
        try:
            async with SessionLocal() as db:
                # Read email/IMAP settings
                def _s(key: str) -> asyncio.Future:
                    return db.execute(select(AppSetting).where(AppSetting.key == key))

                imap_host = (await _s("imap_host")).scalar_one_or_none()
                imap_host = imap_host.value if imap_host else ""
                imap_port = (await _s("imap_port")).scalar_one_or_none()
                imap_port = int(imap_port.value) if imap_port else 993
                smtp_user = (await _s("smtp_user")).scalar_one_or_none()
                smtp_user = smtp_user.value if smtp_user else ""
                smtp_pass = (await _s("smtp_password")).scalar_one_or_none()
                smtp_pass = smtp_pass.value if smtp_pass else ""

                if not all([imap_host, smtp_user, smtp_pass]):
                    continue

                # Find blogs awaiting review
                pending = (
                    (
                        await db.execute(
                            select(Blog).where(Blog.status == BlogStatus.REVIEW_PENDING)
                        )
                    )
                    .scalars()
                    .all()
                )

                if not pending:
                    continue

                pending_tuples = [
                    (b.id, b.email_message_id or "", b.review_email or "")
                    for b in pending
                    if b.email_message_id
                ]

            # IMAP polling is sync — run in thread pool
            if not pending_tuples:
                continue

            replies = await asyncio.to_thread(
                poll_for_replies,
                imap_host,
                imap_port,
                smtp_user,
                smtp_pass,
                pending_tuples,
            )

            for blog_id, reply_body in replies:
                decision = await classify_reply(reply_body)

                async with SessionLocal() as db:
                    blog = (
                        await db.execute(select(Blog).where(Blog.id == blog_id))
                    ).scalar_one_or_none()
                    if not blog:
                        continue

                    if decision["action"] == "approve":
                        blog.status = BlogStatus.APPROVED
                        await db.commit()
                        # Publish
                        from app.services import linkedin_service

                        url = await linkedin_service.publish_blog(blog, db)
                        blog.published_url = url
                        blog.published_at = datetime.utcnow()
                        blog.status = BlogStatus.PUBLISHED
                        await db.commit()
                        logger.info("Blog %d published to LinkedIn: %s", blog_id, url)
                    else:
                        blog.status = BlogStatus.CHANGES_REQUESTED
                        await db.commit()
                        await apply_email_revision(
                            blog, decision.get("changes", reply_body), db
                        )

        except Exception as exc:
            logger.error("IMAP poll error: %s", exc)


async def start_scheduler() -> None:
    scheduler.start()
    await reload_schedules()
    global _imap_task
    _imap_task = asyncio.create_task(_imap_poll_loop())
    logger.info("Scheduler started")


async def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    if _imap_task:
        _imap_task.cancel()
