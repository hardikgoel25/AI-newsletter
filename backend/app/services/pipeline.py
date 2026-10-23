"""The generation pipeline: prompt -> LLM -> extract -> validate/repair -> hero -> render."""

from __future__ import annotations

import logging
import time

from pydantic import ValidationError

from app.auth import AuthContext
from app.config import Settings
from app.schemas import (
    GenerateRequest,
    GenerateResponse,
    RegenerateSectionRequest,
    RegenerateSectionResponse,
    Section,
)
from app.services import prompts
from app.services.images import UnsplashClient, resolve_hero
from app.services.llm import LLMService
from app.services.parser import JSONExtractError, coerce_newsletter, extract_json, format_validation_errors
from app.services.renderer import render_html

log = logging.getLogger("newsletter.pipeline")


class PipelineError(RuntimeError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


async def generate(
    req: GenerateRequest,
    llm: LLMService,
    unsplash: UnsplashClient,
    settings: Settings,
    auth: AuthContext,
) -> GenerateResponse:
    started = time.perf_counter()
    warnings: list[str] = []

    system, user = prompts.build_generation_messages(req.sources, req.options, req.brand)
    result = await llm.complete_json(
        system,
        user,
        provider=auth.provider_for(req.llm.provider),
        model=req.llm.model,
        temperature=req.llm.temperature,
        api_key=auth.llm_key,
    )
    usage = dict(result.usage)
    if result.attempts > 1:
        warnings.append(f"The model needed {result.attempts} attempts.")

    newsletter = None
    try:
        data = extract_json(result.content)
        newsletter, w = coerce_newsletter(data, req.options, req.brand)
        warnings.extend(w)
    except (JSONExtractError, ValidationError, ValueError) as first_error:
        errors = format_validation_errors(first_error) if isinstance(first_error, ValidationError) else str(first_error)
        log.info("First pass failed (%s); asking the model to repair.", errors[:200])
        r_system, r_user = prompts.build_repair_messages(result.content, errors, req.options)
        try:
            repair = await llm.complete_json(
                r_system, r_user, provider=result.provider, model=result.model, temperature=0.0, api_key=auth.llm_key
            )
            for k, v in repair.usage.items():
                usage[k] = usage.get(k, 0) + v
            data = extract_json(repair.content)
            newsletter, w = coerce_newsletter(data, req.options, req.brand)
            warnings.extend(w)
            warnings.append("The model's first answer was malformed and was repaired automatically.")
        except (JSONExtractError, ValidationError, ValueError) as second_error:
            detail = format_validation_errors(second_error) if isinstance(second_error, ValidationError) else str(second_error)
            raise PipelineError(f"The model could not produce a valid newsletter: {detail}", status=502) from second_error

    hero, hero_warnings = await resolve_hero(
        requested=req.hero_image,
        auto_mode=req.auto_hero,
        newsletter=newsletter,
        brand=req.brand,
        theme=req.render.theme,
        unsplash=unsplash,
        settings=settings,
    )
    newsletter.hero_image = hero
    warnings.extend(hero_warnings)

    html = render_html(newsletter, req.brand, req.render)
    return GenerateResponse(
        newsletter=newsletter,
        html=html,
        warnings=warnings,
        usage=usage,
        model=result.model,
        provider=result.provider,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


async def regenerate_section(req: RegenerateSectionRequest, llm: LLMService, auth: AuthContext) -> RegenerateSectionResponse:
    if req.section_index >= len(req.newsletter.sections):
        raise PipelineError("Section index out of range.", status=400)
    section = req.newsletter.sections[req.section_index]
    system, user = prompts.build_section_messages(req.newsletter, section, req.instruction, req.tone, req.language)
    result = await llm.complete_json(
        system,
        user,
        provider=auth.provider_for(req.llm.provider),
        model=req.llm.model,
        temperature=max(0.2, req.llm.temperature),
        api_key=auth.llm_key,
    )
    try:
        data = extract_json(result.content)
        new_section = Section.model_validate({**data, "id": section.id})
    except (JSONExtractError, ValidationError) as exc:
        raise PipelineError("The model returned an invalid section.", status=502) from exc
    if not new_section.content:
        raise PipelineError("The model returned an empty section.", status=502)
    if not new_section.title:
        new_section.title = section.title
    return RegenerateSectionResponse(section=new_section, usage=result.usage, model=result.model)
