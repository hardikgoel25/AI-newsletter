"""Re-render edited newsletters and export in several formats (no LLM calls)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.deps import require_access_key
from app.schemas import ExportRequest, RenderRequest, RenderResponse
from app.services import renderer

router = APIRouter(prefix="/api", tags=["render"], dependencies=[Depends(require_access_key)])


@router.post("/render", response_model=RenderResponse)
async def render(body: RenderRequest) -> RenderResponse:
    return RenderResponse(html=renderer.render_html(body.newsletter, body.brand, body.render))


@router.post("/export")
async def export(body: ExportRequest) -> Response:
    n = body.newsletter
    if body.format == "html":
        content = renderer.render_html(n, body.brand, body.render)
        media, ext = "text/html; charset=utf-8", "html"
    elif body.format == "email":
        content = renderer.render_email_html(n, body.brand, body.render)
        media, ext = "text/html; charset=utf-8", "email.html"
    elif body.format == "markdown":
        content = renderer.render_markdown(n)
        media, ext = "text/markdown; charset=utf-8", "md"
    elif body.format == "text":
        content = renderer.render_text(n)
        media, ext = "text/plain; charset=utf-8", "txt"
    else:
        content = renderer.render_json(n)
        media, ext = "application/json; charset=utf-8", "json"
    filename = renderer.safe_filename(n, ext)
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": renderer.content_disposition(filename), "X-Filename": filename},
    )
