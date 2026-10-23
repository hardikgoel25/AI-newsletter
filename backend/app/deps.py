"""FastAPI dependencies and shared singletons."""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.images import UnsplashClient
from app.services.llm import LLMService

limiter = Limiter(key_func=get_remote_address, headers_enabled=False)


def get_llm(request: Request) -> LLMService:
    return request.app.state.llm


def get_unsplash(request: Request) -> UnsplashClient:
    return request.app.state.unsplash
