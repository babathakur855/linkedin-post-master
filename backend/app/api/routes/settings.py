from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AppSetting
from app.services import linkedin_service

router = APIRouter(prefix="/settings", tags=["settings"])

# Keys the frontend can read/write (password-like fields are write-only)
READABLE_KEYS = {
    "smtp_host",
    "smtp_port",
    "smtp_user",
    "from_email",
    "imap_host",
    "imap_port",
    "review_email",
    "frontend_url",
    "linkedin_client_id",
}
SECRET_KEYS = {"smtp_password", "linkedin_client_secret"}


async def _get_all(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    return {r.key: r.value for r in rows}


async def _set(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    await db.commit()


@router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    all_settings = await _get_all(db)
    # Mask secrets
    return {
        k: ("***" if k in SECRET_KEYS and v else v)
        for k, v in all_settings.items()
        if k in READABLE_KEYS or k in SECRET_KEYS
    }


class SettingsUpdate(BaseModel):
    # Email
    smtp_host: str | None = None
    smtp_port: str | None = None
    smtp_user: str | None = None
    smtp_password: str | None = None
    from_email: str | None = None
    imap_host: str | None = None
    imap_port: str | None = None
    review_email: str | None = None
    # LinkedIn
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    # App
    frontend_url: str | None = None


@router.put("/")
async def update_settings(body: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    for k, v in body.model_dump(exclude_none=True).items():
        if v == "***":
            continue  # don't overwrite masked secrets
        await _set(db, k, v)
    return {"status": "saved"}


@router.get("/linkedin/status")
async def linkedin_status(db: AsyncSession = Depends(get_db)):
    status = await linkedin_service.get_connection_status(db)
    client_id = await _get_all(db)
    status["client_id_set"] = bool(client_id.get("linkedin_client_id"))
    return status


@router.get("/linkedin/auth-url")
async def linkedin_auth_url(request: Request, db: AsyncSession = Depends(get_db)):
    all_s = await _get_all(db)
    client_id = all_s.get("linkedin_client_id", "")
    if not client_id:
        return {"error": "LinkedIn client_id not configured"}
    frontend_url = all_s.get("frontend_url", "http://localhost:3040")
    redirect_uri = f"{frontend_url}/settings/linkedin-callback"
    url = linkedin_service.build_authorization_url(client_id, redirect_uri)
    return {"url": url, "redirect_uri": redirect_uri}


class LinkedInCallbackBody(BaseModel):
    code: str
    redirect_uri: str


@router.post("/linkedin/callback")
async def linkedin_callback(
    body: LinkedInCallbackBody, db: AsyncSession = Depends(get_db)
):
    result = await linkedin_service.exchange_code_for_token(
        body.code, body.redirect_uri, db
    )
    return {"status": "connected", **result}
