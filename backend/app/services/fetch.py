"""SSRF-hardened URL fetching plus article / RSS extraction.

Rules
-----
* http(s) only, no credentials in the URL, no non-standard ports.
* Hostname is resolved first and every address must be public (no loopback, private,
  link-local, multicast, reserved, or cloud-metadata ranges).
* Redirects are followed manually (max 3) and each hop is re-validated.
* Response bodies are streamed and capped.

Known limitation: the final TCP connection re-resolves DNS, so a hostile DNS server
could in theory swap the answer between our check and the connect (DNS rebinding).
Mitigate by running the backend without access to private networks (as Render/Fly do).
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.config import Settings

_UA = "AI-Newsletter-Studio/2.0 (+https://github.com/hardikgoel25/AI-newsletter)"


class FetchError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


@dataclass
class FetchedPage:
    url: str
    status: int
    content_type: str
    body: bytes


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    if len(url) > 2048:
        raise FetchError("URL is too long.")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError("Only http and https URLs are allowed.")
    if not parts.hostname:
        raise FetchError("URL has no host.")
    if parts.username or parts.password:
        raise FetchError("Credentials in URLs are not allowed.")
    if parts.port not in (None, 80, 443):
        raise FetchError("Only ports 80 and 443 are allowed.")
    host = parts.hostname.lower()
    if host in ("localhost",) or host.endswith((".local", ".internal", ".localhost")):
        raise FetchError("Local hosts are not allowed.")
    return url


async def _assert_public(host: str) -> None:
    try:
        ip = ipaddress.ip_address(host)
        addrs = [ip]
    except ValueError:
        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise FetchError(f"Could not resolve host '{host}'.") from exc
        addrs = []
        for info in infos:
            try:
                addrs.append(ipaddress.ip_address(info[4][0]))
            except ValueError:
                continue
    if not addrs:
        raise FetchError("Host did not resolve to any address.")
    for ip in addrs:
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or (ip.version == 6 and ip.ipv4_mapped is not None and not ipaddress.ip_address(ip.ipv4_mapped).is_global)
            or str(ip).startswith("169.254.")
        ):
            raise FetchError("The URL points to a non-public address.")


async def fetch_url(url: str, settings: Settings, *, accept: str = "text/html,application/xhtml+xml,application/xml,text/plain;q=0.9,*/*;q=0.5") -> FetchedPage:
    url = _validate_url(url)
    timeout = httpx.Timeout(settings.fetch_timeout_seconds, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers={"User-Agent": _UA, "Accept": accept}) as client:
        for _hop in range(4):
            parts = urlsplit(url)
            await _assert_public(parts.hostname or "")
            try:
                async with client.stream("GET", url) as resp:
                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get("location")
                        if not location:
                            raise FetchError("Redirect without location.", 502)
                        url = _validate_url(urljoin(url, location))
                        continue
                    if resp.status_code >= 400:
                        raise FetchError(f"The site responded with HTTP {resp.status_code}.", 502)
                    ctype = resp.headers.get("content-type", "")
                    chunks = []
                    size = 0
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        if size > settings.fetch_max_bytes:
                            raise FetchError("The page is too large to import.", 413)
                        chunks.append(chunk)
                    return FetchedPage(url=str(resp.url), status=resp.status_code, content_type=ctype, body=b"".join(chunks))
            except httpx.TimeoutException as exc:
                raise FetchError("The site took too long to respond.", 504) from exc
            except httpx.HTTPError as exc:
                raise FetchError(f"Could not fetch the URL: {exc.__class__.__name__}.", 502) from exc
    raise FetchError("Too many redirects.", 502)


# ---------------------------------------------------------------------------
# Article extraction
# ---------------------------------------------------------------------------

_NOISE_TAGS = ("script", "style", "noscript", "nav", "footer", "header", "aside", "form", "iframe", "svg", "button", "template")
_NOISE_CLASS_RE = re.compile(r"(cookie|banner|sidebar|share|social|comment|related|promo|advert|subscribe|newsletter-signup|breadcrumb)", re.IGNORECASE)


@dataclass
class Article:
    url: str
    title: str
    site: str
    text: str


def extract_article(page: FetchedPage, *, max_chars: int) -> Article:
    if "text/plain" in page.content_type:
        text = page.body.decode("utf-8", errors="replace")
        return Article(url=page.url, title="", site=urlsplit(page.url).hostname or "", text=text[:max_chars].strip())

    soup = BeautifulSoup(page.body, "lxml")
    title = ""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    site = ""
    og_site = soup.find("meta", property="og:site_name")
    if og_site and og_site.get("content"):
        site = og_site["content"].strip()
    site = site or (urlsplit(page.url).hostname or "")

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()
    for tag in soup.find_all(attrs={"class": _NOISE_CLASS_RE}):
        tag.decompose()
    for tag in soup.find_all(attrs={"id": _NOISE_CLASS_RE}):
        tag.decompose()

    root = soup.find("article") or soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    blocks: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "p", "li", "blockquote"]):
        t = " ".join(el.get_text(" ", strip=True).split())
        if len(t) < 3:
            continue
        if el.name in ("h1", "h2", "h3"):
            blocks.append(f"\n## {t}")
        elif el.name == "li":
            blocks.append(f"- {t}")
        else:
            blocks.append(t)
    text = "\n".join(blocks)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 200:
        # Fall back to all visible text.
        text = " ".join(root.get_text(" ", strip=True).split())
    return Article(url=page.url, title=title[:200], site=site[:120], text=text[:max_chars])


# ---------------------------------------------------------------------------
# Feeds
# ---------------------------------------------------------------------------


@dataclass
class FeedEntry:
    title: str
    summary: str
    link: str
    published: str


@dataclass
class Feed:
    title: str
    entries: list[FeedEntry]


def parse_feed(page: FetchedPage, *, limit: int) -> Feed:
    parsed = feedparser.parse(page.body)
    if parsed.bozo and not parsed.entries:
        raise FetchError("The URL is not a valid RSS/Atom feed.", 422)
    entries: list[FeedEntry] = []
    for e in parsed.entries[:limit]:
        raw_summary = e.get("summary") or (e.get("content", [{}])[0].get("value") if e.get("content") else "") or ""
        summary = " ".join(BeautifulSoup(raw_summary, "lxml").get_text(" ", strip=True).split())[:1200]
        entries.append(
            FeedEntry(
                title=(e.get("title") or "").strip()[:200],
                summary=summary,
                link=(e.get("link") or "")[:2048],
                published=(e.get("published") or e.get("updated") or "")[:60],
            )
        )
    return Feed(title=(parsed.feed.get("title") or "").strip()[:200], entries=entries)


def feed_to_text(feed: Feed) -> str:
    lines = [f"# {feed.title}"] if feed.title else []
    for e in feed.entries:
        lines.append(f"\n## {e.title}")
        if e.published:
            lines.append(f"({e.published})")
        if e.summary:
            lines.append(e.summary)
        if e.link:
            lines.append(f"Source: {e.link}")
    return "\n".join(lines).strip()
