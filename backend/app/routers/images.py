"""Stock photo search and selection (Unsplash) plus generated banners."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import get_settings
from app.deps import get_unsplash, limiter, require_access_key
from app.schemas import BrandKit, HeroImage, ImageSearchRequest, ImageSearchResult, ImageSelectRequest, RenderOptions
from app.services.images import UnsplashClient, generated_banner
from app.services.sanitize import ImageError

router = APIRouter(prefix="/api/images", tags=["images"], dependencies=[Depends(require_access_key)])


@router.post("/search", response_model=list[ImageSearchResult])
@limiter.limit(lambda: get_settings().rate_limit_default)
async def search(
    request: Request,
    body: ImageSearchRequest,
    unsplash: UnsplashClient = Depends(get_unsplash),
) -> list[ImageSearchResult]:
    if not unsplash.enabled:
        raise HTTPException(status_code=503, detail="Stock photo search is not configured on this server.")
    try:
        return await unsplash.search(body.query, body.per_page)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Stock photo search failed.") from exc


@router.post("/select", response_model=HeroImage)
@limiter.limit(lambda: get_settings().rate_limit_default)
async def select(
    request: Request,
    body: ImageSelectRequest,
    unsplash: UnsplashClient = Depends(get_unsplash),
) -> HeroImage:
    try:
        return await unsplash.download(body)
    except (httpx.HTTPError, ImageError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not download the photo: {exc}") from exc


class _GeneratedRequest(RenderOptions):
    brand: BrandKit = BrandKit()
    company_name: str = ""


@router.post("/generated", response_model=HeroImage)
async def generated(body: _GeneratedRequest) -> HeroImage:
    brand = body.brand
    if body.company_name and not brand.company_name:
        brand = brand.model_copy(update={"company_name": body.company_name})
    return generated_banner(brand, None, theme=body.theme)
