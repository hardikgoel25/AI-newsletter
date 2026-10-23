"""Health, templates, brand presets, models and fonts."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.deps import get_llm, get_unsplash
from app.schemas import BrandKit, HealthResponse, ModelInfo, TemplateInfo
from app.services.brands import presets
from app.services.images import UnsplashClient
from app.services.llm import LLMService
from app.services.renderer import list_fonts, list_templates

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(
    settings: Settings = Depends(get_settings),
    llm: LLMService = Depends(get_llm),
    unsplash: UnsplashClient = Depends(get_unsplash),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.version,
        environment=settings.environment,
        providers=llm.available_providers(),
        unsplash=unsplash.enabled,
        access_key_required=bool(settings.app_access_key),
    )


@router.get("/templates", response_model=list[TemplateInfo])
async def templates() -> list[TemplateInfo]:
    return list_templates()


@router.get("/fonts", response_model=list[str])
async def fonts() -> list[str]:
    return list_fonts()


@router.get("/brands/presets", response_model=list[BrandKit])
async def brand_presets() -> list[BrandKit]:
    return presets()


@router.get("/models", response_model=list[ModelInfo])
async def models(llm: LLMService = Depends(get_llm)) -> list[ModelInfo]:
    return await llm.list_models()
