"""Template registry and HTML/Markdown/text rendering.

Every template extends `_base.html`, which defines the document structure with named
blocks. Templates mostly contribute CSS; the look of dark/light mode comes from the
token set derived here from the brand colours, so adding a template never requires a
second "dark" file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from app.config import TEMPLATES_DIR
from app.schemas import BrandKit, Newsletter, RenderOptions, TemplateInfo
from app.services import colors
from app.services.sanitize import markdown_to_html, plain_text


@dataclass(frozen=True)
class TemplateSpec:
    id: str
    name: str
    description: str
    file: str
    default_fonts: dict[str, str]
    supports: tuple[str, ...] = ("dark", "light")
    tags: tuple[str, ...] = ()

    def info(self) -> TemplateInfo:
        return TemplateInfo(
            id=self.id,
            name=self.name,
            description=self.description,
            supports=list(self.supports),
            default_fonts=self.default_fonts,
            tags=list(self.tags),
        )


TEMPLATES: dict[str, TemplateSpec] = {
    t.id: t
    for t in (
        TemplateSpec(
            id="modern",
            name="Modern",
            description="Gradient masthead, highlight cards and a stats row. The all-rounder.",
            file="modern.html",
            default_fonts={"heading": "Inter", "body": "Inter"},
            tags=("corporate", "cards", "gradient"),
        ),
        TemplateSpec(
            id="editorial",
            name="Editorial",
            description="Magazine-style serif headlines, hairline rules and a numbered digest.",
            file="editorial.html",
            default_fonts={"heading": "Fraunces", "body": "Inter"},
            tags=("serif", "magazine", "long-form"),
        ),
        TemplateSpec(
            id="minimal",
            name="Minimal",
            description="Single column, generous whitespace, email-friendly. Content first.",
            file="minimal.html",
            default_fonts={"heading": "Inter", "body": "Inter"},
            tags=("email", "simple", "clean"),
        ),
        TemplateSpec(
            id="bold",
            name="Bold",
            description="Full-bleed hero with the headline over the image and big numbers.",
            file="bold.html",
            default_fonts={"heading": "Space Grotesk", "body": "DM Sans"},
            tags=("hero", "launch", "marketing"),
        ),
    )
}

FONT_CATALOG: dict[str, str] = {
    "Inter": "Inter:wght@400;500;600;700;800",
    "Fraunces": "Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700",
    "Playfair Display": "Playfair+Display:wght@500;600;700",
    "Space Grotesk": "Space+Grotesk:wght@500;600;700",
    "DM Sans": "DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700",
    "Manrope": "Manrope:wght@400;500;600;700;800",
    "IBM Plex Sans": "IBM+Plex+Sans:wght@400;500;600;700",
    "Source Serif 4": "Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700",
    "Lora": "Lora:wght@500;600;700",
    "Poppins": "Poppins:wght@400;500;600;700",
}
_SYSTEM_FONTS = {"system", "system-ui", "arial", "helvetica", "georgia", "times new roman", "verdana"}


def list_templates() -> list[TemplateInfo]:
    return [t.info() for t in TEMPLATES.values()]


def list_fonts() -> list[str]:
    return list(FONT_CATALOG.keys())


# ---------------------------------------------------------------------------
# Jinja environment
# ---------------------------------------------------------------------------

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(default=True, default_for_string=True),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _md_filter(text: str) -> Markup:
    return Markup(markdown_to_html(text or ""))  # noqa: S704 - output is nh3-sanitised


def _initials(text: str) -> str:
    return "".join(w[0] for w in (text or "").split()[:2]).upper()


_env.filters["md"] = _md_filter
_env.filters["initials"] = _initials


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


@dataclass
class Tokens:
    values: dict[str, str] = field(default_factory=dict)

    def css(self) -> str:
        body = "\n".join(f"  --{k}: {v};" for k, v in self.values.items())
        return f":root {{\n{body}\n}}"


def build_tokens(brand: BrandKit, theme: str, spec: TemplateSpec) -> Tokens:
    primary, secondary, accent = brand.primary, brand.secondary, brand.accent
    dark = theme == "dark"

    if dark:
        bg = colors.mix(primary, "#0a0d12", 0.93)
        surface = colors.mix(primary, "#121721", 0.92)
        surface2 = colors.mix(primary, "#1a2130", 0.9)
        border = colors.mix(primary, "#273043", 0.85)
        text = "#f3f5f8"
        muted = "#9aa5b4"
        primary_fg = colors.ensure_contrast(primary, surface, 3.0)
        secondary_fg = colors.ensure_contrast(secondary, surface, 3.0)
        accent_fg = colors.ensure_contrast(accent, surface, 3.0)
        shadow = "0 24px 60px rgba(0,0,0,.45)"
    else:
        bg = colors.mix(primary, "#f4f6fa", 0.96)
        surface = "#ffffff"
        surface2 = colors.mix(primary, "#f3f5f9", 0.94)
        border = colors.mix(primary, "#e2e7ee", 0.9)
        text = "#121826"
        muted = "#5b6676"
        primary_fg = colors.ensure_contrast(primary, surface, 4.5)
        secondary_fg = colors.ensure_contrast(secondary, surface, 4.5)
        accent_fg = colors.ensure_contrast(accent, surface, 4.5)
        shadow = "0 18px 50px rgba(17,24,38,.10)"

    heading = brand.font_heading or spec.default_fonts["heading"]
    body = brand.font_body or spec.default_fonts["body"]

    return Tokens(
        {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "primary-fg": primary_fg,
            "secondary-fg": secondary_fg,
            "accent-fg": accent_fg,
            "on-primary": colors.on_color(primary),
            "gradient": f"linear-gradient(120deg, {primary} 0%, {secondary} 55%, {accent} 100%)",
            "primary-soft": colors.rgba(primary, 0.16 if dark else 0.10),
            "accent-soft": colors.rgba(accent, 0.18 if dark else 0.12),
            "bg": bg,
            "surface": surface,
            "surface-2": surface2,
            "border": border,
            "text": text,
            "muted": muted,
            "shadow": shadow,
            "radius": "20px",
            "radius-sm": "12px",
            "font-heading": _font_stack(heading),
            "font-body": _font_stack(body),
        }
    )


def _font_stack(name: str) -> str:
    n = (name or "Inter").strip()
    if n.lower() in _SYSTEM_FONTS:
        return "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    serif = n in ("Fraunces", "Playfair Display", "Source Serif 4", "Lora", "Georgia")
    tail = "Georgia, 'Times New Roman', serif" if serif else "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    return f"'{n}', {tail}"


def _font_link(brand: BrandKit, spec: TemplateSpec) -> str:
    names = {brand.font_heading or spec.default_fonts["heading"], brand.font_body or spec.default_fonts["body"]}
    families = [FONT_CATALOG[n] for n in names if n in FONT_CATALOG]
    if not families:
        return ""
    return "https://fonts.googleapis.com/css2?" + "&".join(f"family={f}" for f in families) + "&display=swap"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def get_spec(template_id: str) -> TemplateSpec:
    return TEMPLATES.get(template_id) or TEMPLATES["modern"]


def render_html(newsletter: Newsletter, brand: BrandKit, options: RenderOptions) -> str:
    spec = get_spec(options.template)
    theme = options.theme if options.theme in spec.supports else spec.supports[0]
    tokens = build_tokens(brand, theme, spec)

    logo = brand.logo
    logo_filter = ""
    if logo and (brand.logo_invert == "always" or (brand.logo_invert == "on-dark" and theme == "dark")):
        logo_filter = "filter: brightness(0) invert(1);"

    template = _env.get_template(spec.file)
    return template.render(
        n=newsletter,
        brand=brand,
        theme=theme,
        template_id=spec.id,
        tokens_css=Markup(tokens.css()),  # noqa: S704 - generated from validated hex colours
        font_link=_font_link(brand, spec),
        logo=logo,
        logo_filter=logo_filter,
        hero=newsletter.hero_image if newsletter.hero_image.src else None,
        socials=newsletter.footer.socials.items_present(),
        year=date.today().year,
    )


_VAR_RE = re.compile(r"var\(--([a-z0-9-]+)\)")


def render_email_html(newsletter: Newsletter, brand: BrandKit, options: RenderOptions) -> str:
    """Email-client friendly HTML: CSS variables resolved and styles inlined."""
    from premailer import Premailer

    html = render_html(newsletter, brand, options)
    spec = get_spec(options.template)
    tokens = build_tokens(brand, options.theme, spec).values
    html = _VAR_RE.sub(lambda m: tokens.get(m.group(1), m.group(0)), html)
    # Email clients ignore external fonts and some clients block <link>.
    html = re.sub(r"<link[^>]+fonts\.googleapis[^>]*>", "", html)
    try:
        return Premailer(
            html,
            remove_classes=False,
            keep_style_tags=True,
            strip_important=False,
            disable_validation=True,
            cssutils_logging_level="CRITICAL",
        ).transform()
    except Exception:
        return html


def render_markdown(newsletter: Newsletter) -> str:
    n = newsletter
    lines: list[str] = []
    lines.append(f"# {n.hero_title}")
    if n.subtitle:
        lines.append(f"_{n.subtitle}_")
    meta = " · ".join(x for x in (n.company_name, n.newsletter_type, n.date, n.estimated_read_time) if x)
    lines.append(f"\n{meta}\n")
    if n.highlights:
        lines.append("## Highlights\n")
        for h in n.highlights:
            sub = f" — {h.subtitle}" if h.subtitle else ""
            lines.append(f"- {h.icon} **{h.title}**{sub}")
        lines.append("")
    if n.summary:
        lines.append("## Executive Summary\n")
        lines.append(n.summary + "\n")
    if n.stats:
        lines.append("| " + " | ".join(s.value for s in n.stats) + " |")
        lines.append("|" + "---|" * len(n.stats))
        lines.append("| " + " | ".join(s.label for s in n.stats) + " |\n")
    for s in n.sections:
        lines.append(f"## {s.icon} {s.title}\n")
        lines.append(s.content.strip() + "\n")
    if n.quote and n.quote.text:
        attr = f"\n> — {n.quote.attribution}" if n.quote.attribution else ""
        lines.append(f"> {n.quote.text}{attr}\n")
    if n.cta and n.cta.label:
        lines.append(f"**[{n.cta.label}]({n.cta.url})**\n" if n.cta.url else f"**{n.cta.label}**\n")
    f = n.footer
    footer_bits = [x for x in (f.tagline, f.website, f.contact_email, f.phone, f.address) if x]
    if footer_bits:
        lines.append("---\n")
        lines.append(" · ".join(footer_bits))
    if f.copyright:
        lines.append(f"\n{f.copyright}")
    return "\n".join(lines).strip() + "\n"


def render_text(newsletter: Newsletter) -> str:
    md = render_markdown(newsletter)
    text = re.sub(r"^#+\s*", "", md, flags=re.MULTILINE)
    text = re.sub(r"^\|.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)
    text = plain_text(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def render_json(newsletter: Newsletter) -> str:
    return json.dumps(newsletter.model_dump(), indent=2, ensure_ascii=False)


def safe_filename(newsletter: Newsletter, ext: str) -> str:
    base = f"{newsletter.company_name}-{newsletter.newsletter_type}-{newsletter.date}".lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:80] or "newsletter"
    return f"{base}.{ext}"


def content_disposition(filename: str) -> str:
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
