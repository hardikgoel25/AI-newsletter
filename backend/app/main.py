"""FastAPI application factory."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings, get_settings
from app.deps import limiter
from app.routers import generate, images, meta, render, sources, upload
from app.services.images import UnsplashClient
from app.services.llm import LLMService

log = logging.getLogger("newsletter")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.state.llm = LLMService(settings)
    app.state.unsplash = UnsplashClient(settings)
    log.info(
        "%s v%s starting (%s). Providers: %s. Unsplash: %s",
        settings.app_name,
        settings.version,
        settings.environment,
        ", ".join(app.state.llm.available_providers()) or "none",
        "on" if app.state.unsplash.enabled else "off",
    )
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, json_limit: int, upload_limit: int):
        super().__init__(app)
        self.json_limit = json_limit
        self.upload_limit = upload_limit

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit():
            ctype = request.headers.get("content-type", "")
            limit = self.upload_limit if ctype.startswith("multipart/") else self.json_limit
            if int(length) > limit:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large."})
        return await call_next(request)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = uuid.uuid4().hex[:12]
        request.state.request_id = rid
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("rid=%s %s %s crashed", rid, request.method, request.url.path)
            raise
        elapsed = int((time.perf_counter() - started) * 1000)
        response.headers["X-Request-Id"] = rid
        if request.url.path.startswith("/api"):
            log.info("rid=%s %s %s -> %s %dms", rid, request.method, request.url.path, response.status_code, elapsed)
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Turn raw company updates into polished, brand-accurate newsletters.",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.limiter = limiter

    # Middleware order: outermost first.
    app.add_middleware(RequestLogMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        BodySizeLimitMiddleware,
        json_limit=settings.max_json_body_bytes,
        upload_limit=settings.max_upload_bytes + 64 * 1024,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-App-Key", "X-LLM-Key", "X-LLM-Provider"],
        expose_headers=["X-Request-Id", "X-Filename", "Content-Disposition"],
        max_age=600,
    )

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded):
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = [
            {"loc": ".".join(str(p) for p in e.get("loc", ()) if p != "body"), "msg": e.get("msg")}
            for e in exc.errors()[:10]
        ]
        return JSONResponse(status_code=422, content={"detail": "Invalid request.", "errors": errors})

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        rid = getattr(request.state, "request_id", "")
        log.exception("rid=%s unhandled error", rid)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server.", "request_id": rid})

    app.include_router(meta.router)
    app.include_router(generate.router)
    app.include_router(render.router)
    app.include_router(upload.router)
    app.include_router(sources.router)
    app.include_router(images.router)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"name": settings.app_name, "version": settings.version, "docs": None if settings.is_production else "/docs"}

    return app


app = create_app()
