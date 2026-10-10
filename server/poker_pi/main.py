"""FastAPI application. Run with:  uvicorn poker_pi.main:create_app --factory"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import yaml
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .api import bot, public
from .config import Settings
from .services import Hub

DESCRIPTION = """
**poker-pi** is a No-Limit Texas Hold'em tournament played by bots.

Your bot talks to this API over plain HTTP + JSON, in any language:

1. `GET /api/v1/bot/turn?wait=25` waits until it is your turn and returns the game state
   (it answers `204` if nothing happened within 25 seconds, then just ask again).
2. `POST /api/v1/bot/action` with `{"turn_id": "...", "action": "call"}` sends your decision.

Every bot request needs the header `Authorization: Bearer <your token>`.
Click **Authorize** above, paste your token, and you can try every endpoint right here.

The full guide (English + Deutsch) is on the website under **Docs**.
"""


class WebFiles(StaticFiles):
    """Static UI files. index.html is always revalidated; hashed assets are cached for a year."""

    def file_response(self, full_path, stat_result, scope, status_code=200):  # type: ignore[no-untyped-def]
        response = super().file_response(full_path, stat_result, scope, status_code)
        if "/assets/" in str(full_path):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-cache"
        return response


TAGS = [
    {"name": "Bot API", "description": "For your bot. Needs your bearer token."},
    {"name": "Public (spectators)", "description": "Read-only, no token. Used by the website."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    hub = Hub(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await hub.start()
        yield
        await hub.stop()

    app = FastAPI(
        title="poker-pi",
        version="1.0.0",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True, "tryItOutEnabled": True},
    )
    app.state.hub = hub
    app.add_middleware(GZipMiddleware, minimum_size=1000)  # SSE streams are excluded automatically
    app.include_router(bot.router)
    app.include_router(public.router)

    @app.get("/api/v1/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/openapi.yaml", include_in_schema=False)
    async def openapi_yaml() -> PlainTextResponse:
        return PlainTextResponse(yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True),
                                 media_type="application/yaml")

    static = Path(settings.static_dir)
    audio_types = {".mp3", ".ogg", ".wav", ".m4a", ".webm", ".aac", ".flac"}

    @app.get("/api/v1/public/config", include_in_schema=False)
    async def web_config() -> dict[str, object]:
        """Settings for the website: default card style and the recorded sound files that exist."""
        sounds_dir = static / "sounds"
        sounds = sorted(f.name for f in sounds_dir.iterdir()
                        if f.is_file() and f.suffix.lower() in audio_types) if sounds_dir.is_dir() else []
        return {"card_deck": settings.card_deck, "sounds": sounds}

    if (static / "index.html").exists():
        app.mount("/", WebFiles(directory=static, html=True), name="web")
    else:
        @app.get("/", include_in_schema=False)
        async def no_ui() -> JSONResponse:
            return JSONResponse({"message": "poker-pi API is running. The web UI is not built; see /docs."})

    return app


def run() -> None:
    import os

    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uvicorn.run(
        "poker_pi.main:create_app",
        factory=True,
        host=os.environ.get("POKER_HOST", "0.0.0.0"),
        port=int(os.environ.get("POKER_PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips="*",
        # bots keep long-polls open for up to 30 s; don't let them block a restart
        timeout_graceful_shutdown=3,
    )
