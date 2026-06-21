"""FastAPI application entry point with WebSocket streaming support."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.routes import niches, blogs, settings as settings_router
from app.services.scheduler_service import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory registry of active WebSocket connections keyed by blog_id
_ws_registry: dict[int, list[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(
    title="LinkedIn Post Master",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(niches.router, prefix="/api")
app.include_router(blogs.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{blog_id}")
async def ws_endpoint(websocket: WebSocket, blog_id: int):
    """Stream generation progress for a specific blog."""
    await websocket.accept()
    _ws_registry.setdefault(blog_id, []).append(websocket)
    try:
        while True:
            await asyncio.sleep(30)  # keep-alive ping
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        if blog_id in _ws_registry:
            _ws_registry[blog_id] = [
                ws for ws in _ws_registry[blog_id] if ws != websocket
            ]
    except Exception:
        pass


async def broadcast(blog_id: int, phase: str, message: str) -> None:
    """Send a generation event to all WebSocket clients watching a blog."""
    sockets = _ws_registry.get(blog_id, [])
    dead = []
    for ws in sockets:
        try:
            await ws.send_json({"type": "log", "phase": phase, "message": message})
        except Exception:
            dead.append(ws)
    for ws in dead:
        sockets.remove(ws)
