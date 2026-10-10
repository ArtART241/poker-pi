from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..services import Hub

bearer = HTTPBearer(
    auto_error=False,
    description="Your bot token. Send it as the header `Authorization: Bearer <token>`.",
)

_requests: dict[str, deque[float]] = defaultdict(deque)


async def get_hub(request: Request) -> Hub:
    return request.app.state.hub


async def current_bot(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, Any]:
    hub: Hub = request.app.state.hub
    if creds is None or not creds.credentials:
        raise HTTPException(
            401,
            "Missing bearer token. Send the header 'Authorization: Bearer <your token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    bot = hub.store.bot_for_token(creds.credentials.strip())
    if bot is None:
        raise HTTPException(401, "Invalid or revoked token.", headers={"WWW-Authenticate": "Bearer"})

    window = _requests[bot["id"]]
    now = time.monotonic()
    while window and now - window[0] > 1.0:
        window.popleft()
    if len(window) >= hub.settings.rate_limit:
        raise HTTPException(
            429,
            f"Too many requests (max {hub.settings.rate_limit} unproductive requests per second). "
            "Use GET /turn with wait=25 instead of asking in a tight loop.",
        )
    window.append(now)
    hub.registry.seen(bot["id"])
    return bot


def refund(bot_id: str) -> None:
    """Productive requests (a turn delivered, an action accepted) don't count against the limit:
    it exists to stop runaway loops, not fast bots."""
    window = _requests.get(bot_id)
    if window:
        window.pop()
