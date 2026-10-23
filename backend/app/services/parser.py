"""Tolerant JSON extraction and newsletter coercion.

Order of defence:
1. Provider JSON mode (see llm.py) — usually enough.
2. `extract_json` — strips fences/prose, finds the first balanced object, repairs
   trailing commas and smart quotes.
3. `coerce_newsletter` — fills defaults, enforces counts and merges brand data, then
   validates with the Pydantic model. Validation errors are returned so the caller can
   ask the model to repair its own output.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.schemas import BrandKit, GenerateOptions, Newsletter


class JSONExtractError(ValueError):
    pass


_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_SMART_QUOTES = {"“": '"', "”": '"', "‘": "'", "’": "'"}


def _balanced_object(text: str) -> str | None:
    """Return the first balanced {...} block, honouring string literals."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        start = text.find("{", start + 1)
    return None


def _try_load(candidate: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def extract_json(raw: str) -> dict[str, Any]:
    """Extract a JSON object from an LLM response, tolerating common defects."""
    if not raw or not raw.strip():
        raise JSONExtractError("The model returned an empty response.")

    text = raw.strip()

    # 1. Straight parse.
    obj = _try_load(text)
    if obj is not None:
        return obj

    # 2. Fenced block.
    m = _FENCE_RE.search(text)
    if m:
        obj = _try_load(m.group(1).strip())
        if obj is not None:
            return obj
        text = m.group(1).strip()

    # 3. First balanced object.
    block = _balanced_object(text)
    if block is None:
        raise JSONExtractError("No JSON object found in the model response.")

    obj = _try_load(block)
    if obj is not None:
        return obj

    # 4. Light repairs: trailing commas, smart quotes, literal newlines in strings.
    repaired = _TRAILING_COMMA_RE.sub(r"\1", block)
    for bad, good in _SMART_QUOTES.items():
        repaired = repaired.replace(bad, good)
    obj = _try_load(repaired)
    if obj is not None:
        return obj

    # Escape raw newlines inside string literals.
    out = []
    in_str = False
    esc = False
    for ch in repaired:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            elif ch == "\n":
                out.append("\\n")
                continue
            elif ch == "\t":
                out.append("\\t")
                continue
        elif ch == '"':
            in_str = True
        out.append(ch)
    obj = _try_load("".join(out))
    if obj is not None:
        return obj

    raise JSONExtractError("The model response contained invalid JSON that could not be repaired.")


def format_validation_errors(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors()[:20]:
        loc = ".".join(str(p) for p in err.get("loc", ()))
        lines.append(f"- {loc or '<root>'}: {err.get('msg')}")
    return "\n".join(lines)


def coerce_newsletter(
    data: dict[str, Any],
    options: GenerateOptions,
    brand: BrandKit,
) -> tuple[Newsletter, list[str]]:
    """Normalise raw model JSON into a validated Newsletter, applying brand data and overrides.

    Raises `pydantic.ValidationError` if the structure is unusable.
    """
    warnings: list[str] = []
    data = dict(data or {})

    # ---- Company / meta -------------------------------------------------
    if brand.company_name:
        data["company_name"] = brand.company_name
    if not data.get("newsletter_type"):
        data["newsletter_type"] = (
            options.custom_type_instruction.strip()[:40] if options.newsletter_type == "Custom" else options.newsletter_type
        )
    if options.publication_date.strip():
        data["date"] = options.publication_date.strip()
    elif not data.get("date"):
        data["date"] = date.today().strftime("%B %Y")

    if options.hero_title_override.strip():
        data["hero_title"] = options.hero_title_override.strip()
    if options.summary_override.strip():
        data["summary"] = options.summary_override.strip()

    rt = str(data.get("estimated_read_time") or "").strip()
    if options.reading_time.strip().lower() not in ("", "auto"):
        data["estimated_read_time"] = options.reading_time.strip()
    elif not rt or rt.lower() == "auto":
        data["estimated_read_time"] = _estimate_read_time(data)

    # ---- Optional blocks respect the toggles ----------------------------
    if not options.include_stats:
        data["stats"] = []
    if not options.include_quote:
        data["quote"] = None
    if not options.include_cta:
        data["cta"] = None
    elif options.cta_override and options.cta_override.label:
        data["cta"] = options.cta_override.model_dump()

    # ---- Footer: brand data always wins over model guesses ---------------
    footer = data.get("footer") if isinstance(data.get("footer"), dict) else {}
    footer = dict(footer)
    footer.setdefault("socials", {})
    brand_footer = {
        "tagline": brand.tagline,
        "website": brand.website,
        "contact_email": brand.contact_email,
        "phone": brand.phone,
        "address": brand.address,
        "privacy_url": brand.privacy_url,
        "terms_url": brand.terms_url,
        "unsubscribe_url": brand.unsubscribe_url,
    }
    for key, value in brand_footer.items():
        if value:
            footer[key] = value
        elif key in ("website", "contact_email", "phone", "address"):
            # Never let the model invent contact details.
            footer[key] = ""
    if brand.subscription_note:
        footer["subscription_note"] = brand.subscription_note
    footer["socials"] = brand.socials.model_dump()
    company = data.get("company_name") or brand.company_name or "Your Company"
    footer["copyright"] = f"© {date.today().year} {company}. All rights reserved."
    data["footer"] = footer

    # ---- Validate ---------------------------------------------------------
    newsletter = Newsletter.model_validate(data)

    # ---- Post-validation checks -------------------------------------------
    if len(newsletter.highlights) != options.highlight_count:
        warnings.append(
            f"Model returned {len(newsletter.highlights)} highlights instead of {options.highlight_count}."
        )
    if len(newsletter.sections) != options.section_count:
        warnings.append(f"Model returned {len(newsletter.sections)} sections instead of {options.section_count}.")
    newsletter.highlights = [h for h in newsletter.highlights if h.title][: max(options.highlight_count, 1)]
    newsletter.sections = [s for s in newsletter.sections if s.title or s.content][: max(options.section_count, 1)]
    newsletter.stats = [s for s in newsletter.stats if s.value and s.label][:4]

    if not newsletter.hero_title:
        newsletter.hero_title = f"{newsletter.company_name} {newsletter.newsletter_type}".strip()
        warnings.append("Model did not return a headline; a default was used.")
    if not newsletter.sections:
        raise ValueError("The model returned no usable sections.")
    return newsletter, warnings


def _estimate_read_time(data: dict[str, Any]) -> str:
    words = 0
    for key in ("summary", "hero_title", "subtitle"):
        words += len(str(data.get(key) or "").split())
    for s in data.get("sections") or []:
        if isinstance(s, dict):
            words += len(str(s.get("content") or "").split()) + len(str(s.get("title") or "").split())
    for h in data.get("highlights") or []:
        if isinstance(h, dict):
            words += len(str(h.get("title") or "").split()) + len(str(h.get("subtitle") or "").split())
    minutes = max(1, round(words / 200))
    return f"{minutes} min read"
