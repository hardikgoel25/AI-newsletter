"""Hero image resolution: upload > Unsplash search > generated SVG banner."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from dataclasses import dataclass

import httpx

from app.config import Settings
from app.schemas import BrandKit, HeroImage, ImageCredit, ImageSearchResult, ImageSelectRequest, Newsletter
from app.services import colors
from app.services.sanitize import ImageError, process_raster

log = logging.getLogger("newsletter.images")

UNSPLASH_API = "https://api.unsplash.com"
_APP_NAME = "ai_newsletter_studio"


# ---------------------------------------------------------------------------
# Generated banner (always works, zero network)
# ---------------------------------------------------------------------------


def generated_banner(brand: BrandKit, newsletter: Newsletter | None = None, *, theme: str = "dark") -> HeroImage:
    primary, secondary, accent = brand.primary, brand.secondary, brand.accent
    company = (newsletter.company_name if newsletter else brand.company_name) or ""
    initials = "".join(w[0] for w in company.split()[:2]).upper() if company else ""
    dark = theme == "dark"
    base = colors.mix(primary, "#070a0f" if dark else "#ffffff", 0.82 if dark else 0.9)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 720" width="1600" height="720" role="img" aria-label="Banner">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{primary}"/>
<stop offset="0.55" stop-color="{secondary}"/>
<stop offset="1" stop-color="{accent}"/>
</linearGradient>
<radialGradient id="r1" cx="0.2" cy="0.25" r="0.6">
<stop offset="0" stop-color="#ffffff" stop-opacity="0.35"/>
<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
</radialGradient>
<radialGradient id="r2" cx="0.85" cy="0.9" r="0.7">
<stop offset="0" stop-color="{base}" stop-opacity="0.75"/>
<stop offset="1" stop-color="{base}" stop-opacity="0"/>
</radialGradient>
<pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
<path d="M80 0H0V80" fill="none" stroke="#ffffff" stroke-opacity="0.08" stroke-width="1"/>
</pattern>
</defs>
<rect width="1600" height="720" fill="url(#g)"/>
<rect width="1600" height="720" fill="url(#grid)"/>
<rect width="1600" height="720" fill="url(#r1)"/>
<rect width="1600" height="720" fill="url(#r2)"/>
<circle cx="1280" cy="140" r="260" fill="#ffffff" fill-opacity="0.08"/>
<circle cx="1420" cy="560" r="180" fill="#ffffff" fill-opacity="0.06"/>
<circle cx="260" cy="620" r="320" fill="{base}" fill-opacity="0.22"/>
<path d="M0 560 C 400 420, 700 700, 1100 520 S 1500 420, 1600 480 V720 H0Z" fill="#ffffff" fill-opacity="0.07"/>
<text x="96" y="600" font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif" font-weight="800" font-size="300" fill="#ffffff" fill-opacity="0.16" letter-spacing="-12">{_xml_escape(initials)}</text>
</svg>"""
    return HeroImage(
        kind="generated",
        src="data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii"),
        alt=f"{company} banner".strip(),
        credit=None,
    )


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------------------
# Unsplash
# ---------------------------------------------------------------------------


@dataclass
class _CacheEntry:
    expires: float
    results: list[ImageSearchResult]


class UnsplashClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: dict[str, _CacheEntry] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.settings.unsplash_access_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Client-ID {self.settings.unsplash_access_key}",
            "Accept-Version": "v1",
        }

    async def search(self, query: str, per_page: int = 9) -> list[ImageSearchResult]:
        if not self.enabled:
            return []
        key = f"{query.lower().strip()}|{per_page}"
        now = time.time()
        hit = self._cache.get(key)
        if hit and hit.expires > now:
            return hit.results

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{UNSPLASH_API}/search/photos",
                headers=self._headers(),
                params={
                    "query": query,
                    "per_page": per_page,
                    "orientation": "landscape",
                    "content_filter": "high",
                },
            )
        if resp.status_code != 200:
            log.warning("Unsplash search %r -> %s", query, resp.status_code)
            return []
        results: list[ImageSearchResult] = []
        for item in resp.json().get("results", []):
            try:
                user = item.get("user", {})
                results.append(
                    ImageSearchResult(
                        id=str(item["id"]),
                        thumb=item["urls"]["small"],
                        regular=item["urls"]["regular"],
                        alt=(item.get("alt_description") or item.get("description") or "")[:200],
                        author=user.get("name", ""),
                        author_url=(user.get("links", {}) or {}).get("html", ""),
                        download_location=item["links"]["download_location"],
                        width=int(item.get("width", 0)),
                        height=int(item.get("height", 0)),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        self._cache[key] = _CacheEntry(expires=now + 3600, results=results)
        if len(self._cache) > 500:
            # Drop expired / oldest entries.
            for k in sorted(self._cache, key=lambda k: self._cache[k].expires)[:100]:
                self._cache.pop(k, None)
        return results

    async def download(self, selection: ImageSelectRequest) -> HeroImage:
        """Download the chosen photo, trigger Unsplash's download hook, return a data URI."""
        if not selection.regular.startswith("https://images.unsplash.com/"):
            raise ImageError("Unexpected image host.")
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            if self.enabled and selection.download_location.startswith(f"{UNSPLASH_API}/"):
                try:
                    await client.get(selection.download_location, headers=self._headers())
                except httpx.HTTPError:
                    pass  # attribution hook is best-effort
            url = selection.regular
            sep = "&" if "?" in url else "?"
            resp = await client.get(f"{url}{sep}w=1600&q=80&fm=jpg&fit=max")
            resp.raise_for_status()
            if len(resp.content) > self.settings.max_upload_bytes * 2:
                raise ImageError("Downloaded image is too large.")
        processed = process_raster(resp.content, max_dimension=self.settings.max_image_dimension, max_bytes=self.settings.max_upload_bytes * 2)
        credit = ImageCredit(
            name=selection.author,
            url=_utm(selection.author_url),
            source="Unsplash",
            source_url=_utm("https://unsplash.com"),
        )
        return HeroImage(kind="unsplash", src=processed.data_uri, alt=selection.alt, credit=credit)

    async def auto_pick(self, keywords: list[str], budget_seconds: float) -> HeroImage | None:
        """Try up to three queries within a time budget; return the first good photo."""
        if not self.enabled or not keywords:
            return None
        queries = _query_plan(keywords)
        deadline = time.time() + budget_seconds
        for q in queries[:3]:
            remaining = deadline - time.time()
            if remaining <= 1:
                break
            try:
                results = await asyncio.wait_for(self.search(q, per_page=5), timeout=remaining)
            except (TimeoutError, httpx.HTTPError) as exc:
                log.info("Unsplash query %r failed: %s", q, exc)
                continue
            for r in results:
                if r.width < 1000:
                    continue
                remaining = deadline - time.time()
                if remaining <= 1:
                    return None
                try:
                    return await asyncio.wait_for(
                        self.download(
                            ImageSelectRequest(
                                id=r.id,
                                regular=r.regular,
                                download_location=r.download_location,
                                author=r.author,
                                author_url=r.author_url,
                                alt=r.alt,
                            )
                        ),
                        timeout=remaining,
                    )
                except (TimeoutError, httpx.HTTPError, ImageError) as exc:
                    log.info("Unsplash download failed: %s", exc)
                    continue
        return None


def _query_plan(keywords: list[str]) -> list[str]:
    kws = [k.strip() for k in keywords if k and k.strip()]
    plan: list[str] = []
    if len(kws) >= 2:
        plan.append(f"{kws[0]} {kws[1]}")
    plan.extend(kws)
    seen: set[str] = set()
    out = []
    for q in plan:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def _utm(url: str) -> str:
    if not url:
        return ""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source={_APP_NAME}&utm_medium=referral"


async def resolve_hero(
    *,
    requested: HeroImage | None,
    auto_mode: str,
    newsletter: Newsletter,
    brand: BrandKit,
    theme: str,
    unsplash: UnsplashClient,
    settings: Settings,
) -> tuple[HeroImage, list[str]]:
    warnings: list[str] = []
    if requested and requested.src and requested.kind != "none":
        return requested, warnings
    if requested and requested.kind == "none":
        return HeroImage(kind="none", src=""), warnings
    if auto_mode == "none":
        return HeroImage(kind="none", src=""), warnings
    if auto_mode == "unsplash":
        if not unsplash.enabled:
            warnings.append("Unsplash is not configured on the server; a generated banner was used.")
        else:
            picked = await unsplash.auto_pick(newsletter.image_keywords, settings.unsplash_budget_seconds)
            if picked:
                return picked, warnings
            warnings.append("No suitable stock photo was found in time; a generated banner was used.")
    return generated_banner(brand, newsletter, theme=theme), warnings
