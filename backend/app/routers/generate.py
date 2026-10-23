"""Generation and per-section regeneration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import AuthContext, get_auth
from app.config import Settings, get_settings
from app.deps import get_llm, get_unsplash, limiter
from app.schemas import GenerateRequest, GenerateResponse, RegenerateSectionRequest, RegenerateSectionResponse
from app.services import pipeline
from app.services.images import UnsplashClient
from app.services.llm import LLMError, LLMService

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit(lambda: get_settings().rate_limit_generate)
async def generate(
    request: Request,
    body: GenerateRequest,
    settings: Settings = Depends(get_settings),
    llm: LLMService = Depends(get_llm),
    unsplash: UnsplashClient = Depends(get_unsplash),
    auth: AuthContext = Depends(get_auth),
) -> GenerateResponse:
    if body.total_chars > settings.max_content_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Source content is too long ({body.total_chars:,} characters). The limit is {settings.max_content_chars:,}.",
        )
    if len(body.sources) > settings.max_sources:
        raise HTTPException(status_code=413, detail=f"At most {settings.max_sources} sources are allowed.")
    if not any(s.text.strip() for s in body.sources):
        raise HTTPException(status_code=422, detail="Please provide some content to summarise.")
    try:
        return await pipeline.generate(body, llm, unsplash, settings, auth)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    except pipeline.PipelineError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc


@router.post("/regenerate-section", response_model=RegenerateSectionResponse)
@limiter.limit(lambda: get_settings().rate_limit_generate)
async def regenerate_section(
    request: Request,
    body: RegenerateSectionRequest,
    llm: LLMService = Depends(get_llm),
    auth: AuthContext = Depends(get_auth),
) -> RegenerateSectionResponse:
    try:
        return await pipeline.regenerate_section(body, llm, auth)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    except pipeline.PipelineError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
