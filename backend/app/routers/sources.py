"""Import content: document extraction, URL articles and RSS/Atom feeds."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.auth import get_auth
from app.config import Settings, get_settings
from app.deps import limiter
from app.schemas import (
    ExtractResponse,
    FeedItem,
    FetchFeedRequest,
    FetchFeedResponse,
    FetchUrlRequest,
    FetchUrlResponse,
)
from app.services import fetch
from app.services.extract import ExtractError, extract_text

router = APIRouter(prefix="/api", tags=["sources"], dependencies=[Depends(get_auth)])


@router.post("/extract", response_model=ExtractResponse)
@limiter.limit(lambda: get_settings().rate_limit_default)
async def extract(
    request: Request,
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> ExtractResponse:
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File is too large.")
    try:
        result = extract_text(file.filename or "upload", data, max_chars=settings.max_content_chars)
    except ExtractError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ExtractResponse(
        filename=file.filename or "upload",
        kind=result.kind,
        text=result.text,
        chars=len(result.text),
        pages=result.pages,
    )


@router.post("/fetch-url", response_model=FetchUrlResponse)
@limiter.limit(lambda: get_settings().rate_limit_default)
async def fetch_url(
    request: Request,
    body: FetchUrlRequest,
    settings: Settings = Depends(get_settings),
) -> FetchUrlResponse:
    try:
        page = await fetch.fetch_url(body.url, settings)
        article = fetch.extract_article(page, max_chars=settings.max_content_chars)
    except fetch.FetchError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    if not article.text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found on that page.")
    return FetchUrlResponse(url=article.url, title=article.title, site=article.site, text=article.text, chars=len(article.text))


@router.post("/fetch-feed", response_model=FetchFeedResponse)
@limiter.limit(lambda: get_settings().rate_limit_default)
async def fetch_feed(
    request: Request,
    body: FetchFeedRequest,
    settings: Settings = Depends(get_settings),
) -> FetchFeedResponse:
    try:
        page = await fetch.fetch_url(body.url, settings, accept="application/rss+xml,application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.5")
        feed = fetch.parse_feed(page, limit=body.limit)
    except fetch.FetchError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from exc
    if not feed.entries:
        raise HTTPException(status_code=422, detail="The feed has no entries.")
    text = fetch.feed_to_text(feed)[: settings.max_content_chars]
    return FetchFeedResponse(
        title=feed.title,
        items=[FeedItem(title=e.title, summary=e.summary, link=e.link, published=e.published) for e in feed.entries],
        text=text,
    )
