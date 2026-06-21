"""LinkedIn OAuth 2.0 + UGC Posts + Articles API integration."""

from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting, Blog


LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com/v2"

SCOPES = ["r_liteprofile", "w_member_social"]


async def _get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def _set_setting(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
        row.updated_at = datetime.utcnow()
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()


def build_authorization_url(
    client_id: str, redirect_uri: str, state: str = "linkedin-oauth"
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(SCOPES),
    }
    return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(
    code: str,
    redirect_uri: str,
    db: AsyncSession,
) -> dict:
    """Exchange auth code for access token and persist it."""
    client_id = await _get_setting(db, "linkedin_client_id")
    client_secret = await _get_setting(db, "linkedin_client_secret")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 5184000)

    await _set_setting(db, "linkedin_access_token", access_token)
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
    await _set_setting(db, "linkedin_token_expires_at", expires_at)

    # Fetch person URN
    person_id = await _fetch_person_id(access_token)
    await _set_setting(db, "linkedin_person_id", person_id)

    return {"person_id": person_id, "expires_at": expires_at}


async def _fetch_person_id(access_token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{LINKEDIN_API_BASE}/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("id", "")


async def publish_blog(blog: Blog, db: AsyncSession) -> str:
    """Publish a blog as a LinkedIn post or article. Returns the published URL."""

    access_token = await _get_setting(db, "linkedin_access_token")
    person_id = await _get_setting(db, "linkedin_person_id")

    if not access_token or not person_id:
        raise ValueError("LinkedIn not connected — go to Settings → LinkedIn")

    author_urn = f"urn:li:person:{person_id}"

    if blog.publish_format == "article":
        return await _publish_article(blog, access_token, author_urn)
    else:
        return await _publish_post(blog, access_token, author_urn)


async def _publish_post(blog: Blog, access_token: str, author_urn: str) -> str:
    """Publish as a regular LinkedIn UGC post."""

    post_text = blog.linkedin_post or blog.title
    # LinkedIn posts allow max 3000 chars
    if len(post_text) > 3000:
        post_text = post_text[:2997] + "..."

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
        )
        resp.raise_for_status()

    person_id_clean = author_urn.split(":")[-1]
    return f"https://www.linkedin.com/in/{person_id_clean}/recent-activity/shares/"


async def _publish_article(blog: Blog, access_token: str, author_urn: str) -> str:
    """Publish as a LinkedIn Article via the Articles API."""

    title = blog.linkedin_article_title or blog.title
    body = blog.linkedin_article_body or blog.content_markdown

    _markdown_to_linkedin_html(body)  # reserved for future HTML body upload

    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": blog.linkedin_post[:1300] if blog.linkedin_post else title
                },
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": title},
                        "title": {"text": title},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
        )
        resp.raise_for_status()

    person_id_clean = author_urn.split(":")[-1]
    return f"https://www.linkedin.com/in/{person_id_clean}/recent-activity/shares/"


def _markdown_to_linkedin_html(md: str) -> str:
    """Minimal Markdown → LinkedIn-compatible text (strip mermaid blocks, preserve structure)."""
    import re

    # Remove mermaid code blocks
    md = re.sub(r"```mermaid[\s\S]*?```", "[Diagram]", md)
    # Remove other code blocks
    md = re.sub(r"```[\s\S]*?```", "", md)
    # Remove visual comments
    md = re.sub(r"<!--.*?-->", "", md)
    return md.strip()


async def get_connection_status(db: AsyncSession) -> dict:
    token = await _get_setting(db, "linkedin_access_token")
    person_id = await _get_setting(db, "linkedin_person_id")
    expires_at = await _get_setting(db, "linkedin_token_expires_at")

    connected = bool(token and person_id)
    expired = False
    if expires_at:
        try:
            expired = datetime.fromisoformat(expires_at) < datetime.utcnow()
        except ValueError:
            pass

    return {
        "connected": connected and not expired,
        "person_id": person_id,
        "expires_at": expires_at,
        "expired": expired,
    }
