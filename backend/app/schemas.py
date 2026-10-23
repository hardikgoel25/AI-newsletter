"""Pydantic models shared by the API, the LLM pipeline and the renderer.

The `Newsletter` model is the single source of truth for a generated newsletter. Every
template renders from it, every export derives from it and the frontend editor edits it.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
SAFE_URL = re.compile(r"^(https?://|mailto:)", re.IGNORECASE)
DATA_IMAGE = re.compile(r"^data:image/(png|jpeg|jpg|webp|gif|svg\+xml);base64,[A-Za-z0-9+/=\s]+$")

DEFAULT_SECTION_ICON = "📰"
DEFAULT_HIGHLIGHT_ICON = "⭐"


def _clean_text(value: str, limit: int) -> str:
    value = (value or "").replace("\x00", "").strip()
    return value[:limit]


def _clean_icon(value: str, default: str) -> str:
    """Keep a short emoji-ish token; drop anything that looks like words."""
    value = (value or "").strip()
    if not value:
        return default
    if any(ch.isascii() and ch.isalnum() for ch in value):
        return default
    return value[:8]


def _safe_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("www."):
        value = "https://" + value
    if not SAFE_URL.match(value):
        # Bare domains like "example.com" are common in user input.
        if re.match(r"^[\w.-]+\.[a-z]{2,}(/.*)?$", value, re.IGNORECASE):
            return "https://" + value
        return ""
    return value[:2048]


def _safe_image_src(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if value.startswith("data:"):
        return value if DATA_IMAGE.match(value) else ""
    if re.match(r"^https?://", value, re.IGNORECASE):
        return value[:2048]
    return ""


class StrictModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")


# ---------------------------------------------------------------------------
# Newsletter content
# ---------------------------------------------------------------------------


class Highlight(StrictModel):
    icon: str = DEFAULT_HIGHLIGHT_ICON
    title: str = ""
    subtitle: str = ""

    @field_validator("icon", mode="before")
    @classmethod
    def _icon(cls, v: Any) -> str:
        return _clean_icon(str(v or ""), DEFAULT_HIGHLIGHT_ICON)

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 120)

    @field_validator("subtitle", mode="before")
    @classmethod
    def _subtitle(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 260)


class Section(StrictModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    icon: str = DEFAULT_SECTION_ICON
    title: str = ""
    content: str = ""  # Markdown (sanitized at render time)

    @field_validator("id", mode="before")
    @classmethod
    def _id(cls, v: Any) -> str:
        v = re.sub(r"[^a-zA-Z0-9_-]", "", str(v or ""))[:32]
        return v or uuid.uuid4().hex[:8]

    @field_validator("icon", mode="before")
    @classmethod
    def _icon(cls, v: Any) -> str:
        return _clean_icon(str(v or ""), DEFAULT_SECTION_ICON)

    @field_validator("title", mode="before")
    @classmethod
    def _title(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 160)

    @field_validator("content", mode="before")
    @classmethod
    def _content(cls, v: Any) -> str:
        if isinstance(v, list):
            v = "\n\n".join(str(x) for x in v)
        return _clean_text(str(v or ""), 6000)


class Stat(StrictModel):
    value: str = ""
    label: str = ""

    @field_validator("value", "label", mode="before")
    @classmethod
    def _short(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 60)


class Quote(StrictModel):
    text: str = ""
    attribution: str = ""

    @field_validator("text", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 500)

    @field_validator("attribution", mode="before")
    @classmethod
    def _attr(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 120)


class CTA(StrictModel):
    label: str = ""
    url: str = ""

    @field_validator("label", mode="before")
    @classmethod
    def _label(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 80)

    @field_validator("url", mode="before")
    @classmethod
    def _url(cls, v: Any) -> str:
        return _safe_url(str(v or ""))


class Socials(StrictModel):
    linkedin: str = ""
    x: str = ""
    instagram: str = ""
    facebook: str = ""
    youtube: str = ""
    github: str = ""

    @field_validator("*", mode="before")
    @classmethod
    def _urls(cls, v: Any) -> str:
        return _safe_url(str(v or ""))

    def items_present(self) -> list[tuple[str, str]]:
        labels = {
            "linkedin": "LinkedIn",
            "x": "X",
            "instagram": "Instagram",
            "facebook": "Facebook",
            "youtube": "YouTube",
            "github": "GitHub",
        }
        return [(labels[k], v) for k, v in self.model_dump().items() if v]


class Footer(StrictModel):
    tagline: str = ""
    website: str = ""
    contact_email: str = ""
    phone: str = ""
    address: str = ""
    socials: Socials = Field(default_factory=Socials)
    copyright: str = ""
    subscription_note: str = "You are receiving this newsletter because you subscribed to company updates."
    privacy_url: str = ""
    terms_url: str = ""
    unsubscribe_url: str = ""

    @field_validator("website", "privacy_url", "terms_url", "unsubscribe_url", mode="before")
    @classmethod
    def _urls(cls, v: Any) -> str:
        return _safe_url(str(v or ""))

    @field_validator("tagline", "contact_email", "phone", "address", "copyright", "subscription_note", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 300)

    @model_validator(mode="before")
    @classmethod
    def _flatten_legacy_socials(cls, data: Any) -> Any:
        """Accept the flat legacy shape (linkedin/twitter/... at top level)."""
        if isinstance(data, dict) and "socials" not in data:
            socials = {}
            for legacy, new in (
                ("linkedin", "linkedin"),
                ("twitter", "x"),
                ("x", "x"),
                ("instagram", "instagram"),
                ("facebook", "facebook"),
                ("youtube", "youtube"),
                ("github", "github"),
            ):
                if data.get(legacy):
                    socials[new] = data[legacy]
            if socials:
                data = {**data, "socials": socials}
        return data


class ImageCredit(StrictModel):
    name: str = ""
    url: str = ""
    source: str = "Unsplash"
    source_url: str = "https://unsplash.com"

    @field_validator("url", "source_url", mode="before")
    @classmethod
    def _url(cls, v: Any) -> str:
        return _safe_url(str(v or ""))


class HeroImage(StrictModel):
    kind: Literal["upload", "unsplash", "generated", "url", "none"] = "generated"
    src: str = ""
    alt: str = ""
    credit: ImageCredit | None = None

    @field_validator("src", mode="before")
    @classmethod
    def _src(cls, v: Any) -> str:
        return _safe_image_src(str(v or ""))

    @field_validator("alt", mode="before")
    @classmethod
    def _alt(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 200)


class Newsletter(StrictModel):
    company_name: str = "Your Company"
    newsletter_type: str = "Newsletter"
    language: str = "en"
    hero_title: str = ""
    subtitle: str = ""
    summary: str = ""
    date: str = ""
    estimated_read_time: str = ""
    highlights: list[Highlight] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    stats: list[Stat] = Field(default_factory=list)
    quote: Quote | None = None
    cta: CTA | None = None
    image_keywords: list[str] = Field(default_factory=list)
    hero_image: HeroImage = Field(default_factory=HeroImage)
    footer: Footer = Field(default_factory=Footer)

    @field_validator("company_name", "newsletter_type", "date", "estimated_read_time", mode="before")
    @classmethod
    def _short(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 120)

    @field_validator("hero_title", mode="before")
    @classmethod
    def _hero(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 160)

    @field_validator("subtitle", mode="before")
    @classmethod
    def _subtitle(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 300)

    @field_validator("summary", mode="before")
    @classmethod
    def _summary(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 2500)

    @field_validator("language", mode="before")
    @classmethod
    def _lang(cls, v: Any) -> str:
        v = re.sub(r"[^a-zA-Z-]", "", str(v or "en"))[:10]
        return v or "en"

    @field_validator("image_keywords", mode="before")
    @classmethod
    def _keywords(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = [k for k in re.split(r"[,\n]", v)]
        if not isinstance(v, list):
            return []
        out = []
        for k in v:
            k = _clean_text(str(k or ""), 60)
            if k:
                out.append(k)
        return out[:8]

    @field_validator("highlights", mode="before")
    @classmethod
    def _highlights(cls, v: Any) -> list[Any]:
        if not isinstance(v, list):
            return []
        out: list[Any] = []
        for item in v:
            if isinstance(item, str):
                out.append({"icon": DEFAULT_HIGHLIGHT_ICON, "title": item, "subtitle": ""})
            elif item is not None:
                out.append(item)
        return out[:12]

    @field_validator("sections", mode="before")
    @classmethod
    def _sections(cls, v: Any) -> list[Any]:
        if not isinstance(v, list):
            return []
        out: list[Any] = []
        for item in v:
            if isinstance(item, str):
                if item.strip():
                    out.append({"title": item.strip()[:80], "content": item})
            elif item is not None:
                out.append(item)

        # Legacy "priority" ordering (only for raw dicts).
        def _prio(item: Any) -> int:
            try:
                return int(item.get("priority", 999)) if isinstance(item, dict) else 999
            except (TypeError, ValueError):
                return 999

        if any(isinstance(s, dict) and "priority" in s for s in out):
            out.sort(key=_prio)
        return out[:12]

    @field_validator("stats", mode="before")
    @classmethod
    def _stats(cls, v: Any) -> list[Any]:
        if not isinstance(v, list):
            return []
        return [s for s in v if s is not None and not isinstance(s, str)][:6]

    @field_validator("quote", "cta", mode="before")
    @classmethod
    def _optional_obj(cls, v: Any) -> Any:
        if not v:
            return None
        if isinstance(v, dict):
            if not any(str(x or "").strip() for x in v.values()):
                return None
        return v

    @property
    def language_code(self) -> str:
        return self.language.split("-")[0].lower() or "en"


# ---------------------------------------------------------------------------
# Brand kit
# ---------------------------------------------------------------------------


class BrandKit(StrictModel):
    id: str = "custom"
    name: str = "Custom"
    company_name: str = ""
    tagline: str = ""
    logo: str = ""  # data URI or https URL
    logo_invert: Literal["never", "on-dark", "always"] = "never"
    primary: str = "#6366f1"
    secondary: str = "#8b5cf6"
    accent: str = "#06b6d4"
    font_heading: str = ""  # empty = template default
    font_body: str = ""
    website: str = ""
    contact_email: str = ""
    phone: str = ""
    address: str = ""
    socials: Socials = Field(default_factory=Socials)
    subscription_note: str = ""
    privacy_url: str = ""
    terms_url: str = ""
    unsubscribe_url: str = ""

    @field_validator("primary", "secondary", "accent", mode="before")
    @classmethod
    def _color(cls, v: Any) -> str:
        v = str(v or "").strip()
        if not HEX_COLOR.match(v):
            raise ValueError("colors must be hex like #1a2b3c")
        if len(v) == 4:
            v = "#" + "".join(ch * 2 for ch in v[1:])
        return v.lower()

    @field_validator("logo", mode="before")
    @classmethod
    def _logo(cls, v: Any) -> str:
        return _safe_image_src(str(v or ""))

    @field_validator("website", "privacy_url", "terms_url", "unsubscribe_url", mode="before")
    @classmethod
    def _urls(cls, v: Any) -> str:
        return _safe_url(str(v or ""))

    @field_validator("id", "name", "company_name", "tagline", "font_heading", "font_body", "contact_email", "phone", "address", "subscription_note", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return _clean_text(str(v or ""), 300)


# ---------------------------------------------------------------------------
# Requests / responses
# ---------------------------------------------------------------------------

NewsletterType = Literal[
    "Corporate",
    "Weekly Update",
    "Monthly Update",
    "Product Launch",
    "Investor Update",
    "Internal Newsletter",
    "HR Newsletter",
    "Marketing",
    "Engineering",
    "Community",
    "Custom",
]

Tone = Literal[
    "Professional",
    "Executive",
    "Friendly",
    "Technical",
    "Marketing",
    "Minimal",
    "Inspirational",
    "Playful",
]


class GenerateOptions(StrictModel):
    newsletter_type: NewsletterType = "Corporate"
    custom_type_instruction: str = Field(default="", max_length=400)
    tone: Tone = "Professional"
    language: str = Field(default="English", max_length=40)
    reading_time: str = Field(default="Auto", max_length=20)
    highlight_count: int = Field(default=4, ge=2, le=8)
    section_count: int = Field(default=4, ge=2, le=8)
    include_stats: bool = True
    include_quote: bool = False
    include_cta: bool = True
    publication_date: str = Field(default="", max_length=60)
    hero_title_override: str = Field(default="", max_length=160)
    summary_override: str = Field(default="", max_length=2500)
    cta_override: CTA | None = None
    extra_instructions: str = Field(default="", max_length=2000)


class LLMOptions(StrictModel):
    provider: Literal["groq", "openai", "gemini", "ollama"] | None = None
    model: str | None = Field(default=None, max_length=120)
    temperature: float = Field(default=0.3, ge=0.0, le=1.5)


class RenderOptions(StrictModel):
    template: str = Field(default="modern", pattern=r"^[a-z0-9_-]{1,40}$")
    theme: Literal["dark", "light"] = "dark"


class Source(StrictModel):
    kind: Literal["text", "file", "url", "feed"] = "text"
    label: str = Field(default="", max_length=200)
    text: str = Field(default="", max_length=60_000)


class GenerateRequest(StrictModel):
    sources: list[Source] = Field(min_length=1, max_length=6)
    options: GenerateOptions = Field(default_factory=GenerateOptions)
    brand: BrandKit = Field(default_factory=BrandKit)
    render: RenderOptions = Field(default_factory=RenderOptions)
    llm: LLMOptions = Field(default_factory=LLMOptions)
    hero_image: HeroImage | None = None
    auto_hero: Literal["unsplash", "generated", "none"] = "unsplash"

    @property
    def total_chars(self) -> int:
        return sum(len(s.text) for s in self.sources)


class GenerateResponse(StrictModel):
    newsletter: Newsletter
    html: str
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    model: str = ""
    provider: str = ""
    elapsed_ms: int = 0


class RenderRequest(StrictModel):
    newsletter: Newsletter
    brand: BrandKit = Field(default_factory=BrandKit)
    render: RenderOptions = Field(default_factory=RenderOptions)


class RenderResponse(StrictModel):
    html: str


class ExportRequest(RenderRequest):
    format: Literal["html", "email", "markdown", "json", "text"] = "html"


class RegenerateSectionRequest(StrictModel):
    newsletter: Newsletter
    section_index: int = Field(ge=0, le=20)
    instruction: str = Field(default="", max_length=1000)
    tone: Tone = "Professional"
    language: str = Field(default="English", max_length=40)
    llm: LLMOptions = Field(default_factory=LLMOptions)


class RegenerateSectionResponse(StrictModel):
    section: Section
    usage: dict[str, Any] = Field(default_factory=dict)
    model: str = ""


class FetchUrlRequest(StrictModel):
    url: str = Field(max_length=2048)


class FetchUrlResponse(StrictModel):
    url: str
    title: str
    site: str
    text: str
    chars: int


class FetchFeedRequest(StrictModel):
    url: str = Field(max_length=2048)
    limit: int = Field(default=8, ge=1, le=25)


class FeedItem(StrictModel):
    title: str
    summary: str
    link: str
    published: str


class FetchFeedResponse(StrictModel):
    title: str
    items: list[FeedItem]
    text: str


class ExtractResponse(StrictModel):
    filename: str
    kind: str
    text: str
    chars: int
    pages: int | None = None


class UploadImageResponse(StrictModel):
    data_uri: str
    mime: str
    width: int
    height: int
    bytes: int


class ImageSearchRequest(StrictModel):
    query: str = Field(min_length=1, max_length=120)
    per_page: int = Field(default=9, ge=1, le=20)


class ImageSearchResult(StrictModel):
    id: str
    thumb: str
    regular: str
    alt: str
    author: str
    author_url: str
    download_location: str
    width: int
    height: int


class ImageSelectRequest(StrictModel):
    id: str = Field(max_length=64)
    regular: str = Field(max_length=2048)
    download_location: str = Field(max_length=2048)
    author: str = Field(default="", max_length=120)
    author_url: str = Field(default="", max_length=2048)
    alt: str = Field(default="", max_length=200)


class ModelInfo(StrictModel):
    provider: str
    id: str
    label: str
    default: bool = False
    available: bool = True


class TemplateInfo(StrictModel):
    id: str
    name: str
    description: str
    supports: list[str]
    default_fonts: dict[str, str]
    tags: list[str] = Field(default_factory=list)


class HealthResponse(StrictModel):
    status: str
    version: str
    environment: str
    providers: list[str]
    unsplash: bool
    access_key_required: bool
