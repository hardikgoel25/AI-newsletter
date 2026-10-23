"""Image uploads (logo / hero) returned as sanitised data URIs. Nothing is stored."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile

from app.config import Settings, get_settings
from app.deps import limiter, require_access_key
from app.schemas import UploadImageResponse
from app.services.sanitize import ImageError, SVGError, process_raster, sanitize_svg, sniff_is_svg, svg_data_uri

router = APIRouter(prefix="/api", tags=["upload"], dependencies=[Depends(require_access_key)])

_ALLOWED_EXT = (".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif")


@router.post("/upload/image", response_model=UploadImageResponse)
@limiter.limit(lambda: get_settings().rate_limit_default)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    kind: Literal["logo", "hero"] = Query(default="hero"),
    settings: Settings = Depends(get_settings),
) -> UploadImageResponse:
    name = (file.filename or "").lower()
    if not name.endswith(_ALLOWED_EXT):
        raise HTTPException(status_code=415, detail="Upload an SVG, PNG, JPG, WebP or GIF image.")

    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"Image must be under {settings.max_upload_bytes // (1024 * 1024)} MB.")
    if not data:
        raise HTTPException(status_code=422, detail="The file is empty.")

    if sniff_is_svg(data) or name.endswith(".svg"):
        if kind != "logo":
            raise HTTPException(status_code=415, detail="SVG is only supported for logos. Use PNG or JPG for the hero image.")
        try:
            clean = sanitize_svg(data)
        except SVGError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return UploadImageResponse(data_uri=svg_data_uri(clean), mime="image/svg+xml", width=0, height=0, bytes=len(clean))

    max_dim = 600 if kind == "logo" else settings.max_image_dimension
    try:
        processed = process_raster(data, max_dimension=max_dim, max_bytes=settings.max_upload_bytes)
    except ImageError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UploadImageResponse(
        data_uri=processed.data_uri,
        mime=processed.mime,
        width=processed.width,
        height=processed.height,
        bytes=len(processed.data),
    )
