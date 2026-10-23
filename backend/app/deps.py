"""FastAPI dependencies and shared singletons."""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import Settings, get_settings
from app.services.images import UnsplashClient
from app.services.llm import LLMService

limiter = Limiter(key_func=get_remote_address, headers_enabled=False)


def get_llm(request: Request) -> LLMService:
    return request.app.state.llm


def get_unsplash(request: Request) -> UnsplashClient:
    return request.app.state.unsplash


async def require_access_key(
    settings: Settings = Depends(get_settings),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
) -> None:
    """Optional shared-secret gate for private deployments."""
    if not settings.app_access_key:
        return
    if not x_app_key or not secrets.compare_digest(x_app_key, settings.app_access_key):
        raise HTTPException(status_code=401, detail="Missing or invalid access key.")
