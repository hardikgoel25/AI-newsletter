"""LLM access layer.

All providers are reached through the OpenAI-compatible chat-completions API, which Groq,
OpenAI, Gemini and Ollama all expose. This keeps one code path with retries, timeouts,
JSON mode and a model fallback chain.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    RateLimitError,
)

from app.config import Settings
from app.schemas import ModelInfo

log = logging.getLogger("newsletter.llm")


class LLMError(RuntimeError):
    """Raised when every attempt to get a completion failed."""

    def __init__(self, message: str, *, status: int = 502, provider: str = "", model: str = ""):
        super().__init__(message)
        self.status = status
        self.provider = provider
        self.model = model


@dataclass
class LLMResult:
    content: str
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    attempts: int = 1
    elapsed_ms: int = 0


# Models that are not chat models and should never be offered.
_GROQ_EXCLUDE = ("whisper", "guard", "orpheus", "tts", "safeguard", "allam")

CURATED_MODELS: dict[str, list[tuple[str, str]]] = {
    "openai": [
        ("gpt-5-mini", "GPT-5 mini"),
        ("gpt-5", "GPT-5"),
        ("gpt-4.1-mini", "GPT-4.1 mini"),
        ("gpt-4.1", "GPT-4.1"),
    ],
    "gemini": [
        ("gemini-2.5-flash", "Gemini 2.5 Flash"),
        ("gemini-2.5-pro", "Gemini 2.5 Pro"),
    ],
    "ollama": [
        ("llama3.1", "Llama 3.1 (local)"),
        ("qwen2.5", "Qwen 2.5 (local)"),
        ("gemma3", "Gemma 3 (local)"),
    ],
}


class LLMService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._clients: dict[str, AsyncOpenAI] = {}
        self._groq_models_cache: tuple[float, list[str]] | None = None

    # ------------------------------------------------------------------ providers
    def provider_config(self, provider: str) -> tuple[str | None, str | None]:
        """Return (base_url, api_key) for a provider or (None, None) if unconfigured."""
        s = self.settings
        if provider == "groq":
            return "https://api.groq.com/openai/v1", s.groq_api_key
        if provider == "openai":
            return None, s.openai_api_key
        if provider == "gemini":
            return "https://generativelanguage.googleapis.com/v1beta/openai/", s.gemini_api_key
        if provider == "ollama":
            return s.ollama_base_url.rstrip("/") + "/v1", "ollama"
        return None, None

    def available_providers(self) -> list[str]:
        out = []
        for p in ("groq", "openai", "gemini"):
            _, key = self.provider_config(p)
            if key:
                out.append(p)
        if not self.settings.is_production:
            out.append("ollama")
        return out

    def _client(self, provider: str) -> AsyncOpenAI:
        if provider in self._clients:
            return self._clients[provider]
        base_url, key = self.provider_config(provider)
        if not key:
            raise LLMError(f"Provider '{provider}' is not configured on the server.", status=503, provider=provider)
        client = AsyncOpenAI(
            api_key=key,
            base_url=base_url,
            timeout=httpx.Timeout(self.settings.llm_timeout_seconds, connect=10.0),
            max_retries=0,  # we handle retries ourselves
        )
        self._clients[provider] = client
        return client

    async def list_models(self) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        s = self.settings
        for provider in self.available_providers():
            if provider == "groq":
                ids = await self._groq_model_ids()
                for mid in ids:
                    models.append(
                        ModelInfo(
                            provider="groq",
                            id=mid,
                            label=mid.split("/")[-1],
                            default=(provider == s.default_provider and mid == s.default_model),
                        )
                    )
            else:
                for mid, label in CURATED_MODELS.get(provider, []):
                    models.append(
                        ModelInfo(
                            provider=provider,
                            id=mid,
                            label=label,
                            default=(provider == s.default_provider and mid == s.default_model),
                        )
                    )
        if not any(m.default for m in models) and models:
            models[0].default = True
        return models

    async def _groq_model_ids(self) -> list[str]:
        now = time.time()
        if self._groq_models_cache and now - self._groq_models_cache[0] < 600:
            return self._groq_models_cache[1]
        ids: list[str] = []
        try:
            client = self._client("groq")
            page = await client.models.list()
            for m in page.data:
                mid = m.id
                if any(x in mid.lower() for x in _GROQ_EXCLUDE):
                    continue
                ids.append(mid)
            ids.sort(key=lambda x: (0 if x == self.settings.default_model else 1, x))
        except Exception as exc:  # pragma: no cover - network
            log.warning("Could not list Groq models: %s", exc)
            ids = [self.settings.default_model, *self.settings.fallback_model_list]
        self._groq_models_cache = (now, ids)
        return ids

    # ------------------------------------------------------------------ completion
    def _candidate_models(self, provider: str, model: str | None) -> list[str]:
        s = self.settings
        if model:
            chain = [model]
            if provider == s.default_provider:
                chain += [m for m in [s.default_model, *s.fallback_model_list] if m != model]
            return chain
        if provider == s.default_provider:
            return [s.default_model, *s.fallback_model_list]
        curated = CURATED_MODELS.get(provider, [])
        return [curated[0][0]] if curated else []

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> LLMResult:
        """Ask for a JSON object. Retries transient errors and walks the fallback chain."""
        provider = provider or self.settings.default_provider
        candidates = self._candidate_models(provider, model)
        if not candidates:
            raise LLMError(f"No model configured for provider '{provider}'.", status=400, provider=provider)

        client = self._client(provider)
        started = time.perf_counter()
        attempts = 0
        last_error: Exception | None = None

        for candidate in candidates:
            use_json_mode = True
            for attempt in range(1, self.settings.llm_max_retries + 1):
                attempts += 1
                try:
                    content, usage = await self._call(
                        client, candidate, system, user, temperature, use_json_mode, max_tokens
                    )
                    if not content.strip():
                        raise ValueError("empty completion")
                    return LLMResult(
                        content=content,
                        provider=provider,
                        model=candidate,
                        usage=usage,
                        attempts=attempts,
                        elapsed_ms=int((time.perf_counter() - started) * 1000),
                    )
                except AuthenticationError as exc:
                    raise LLMError(
                        f"Authentication with {provider} failed. Check the API key.",
                        status=503,
                        provider=provider,
                        model=candidate,
                    ) from exc
                except NotFoundError as exc:
                    log.warning("Model %s not found on %s: %s", candidate, provider, exc)
                    last_error = exc
                    break  # next candidate
                except BadRequestError as exc:
                    msg = str(exc).lower()
                    if use_json_mode and ("response_format" in msg or "json" in msg):
                        log.info("Model %s rejected JSON mode; retrying without it", candidate)
                        use_json_mode = False
                        continue
                    if "model" in msg and ("decommission" in msg or "not exist" in msg or "not found" in msg):
                        log.warning("Model %s unavailable: %s", candidate, exc)
                        last_error = exc
                        break
                    raise LLMError(f"{provider} rejected the request: {exc}", status=400, provider=provider, model=candidate) from exc
                except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                    last_error = exc
                    if attempt < self.settings.llm_max_retries:
                        await asyncio.sleep(_backoff(attempt))
                        continue
                    break  # exhausted -> next candidate
                except APIStatusError as exc:
                    last_error = exc
                    if exc.status_code >= 500 and attempt < self.settings.llm_max_retries:
                        await asyncio.sleep(_backoff(attempt))
                        continue
                    break
                except ValueError as exc:
                    last_error = exc
                    if attempt < self.settings.llm_max_retries:
                        continue
                    break

        raise LLMError(
            f"The language model did not respond after {attempts} attempt(s): {last_error}",
            status=502,
            provider=provider,
            model=candidates[0],
        )

    async def _call(
        self,
        client: AsyncOpenAI,
        model: str,
        system: str,
        user: str,
        temperature: float,
        json_mode: bool,
        max_tokens: int | None,
    ) -> tuple[str, dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens or self.settings.llm_max_output_tokens:
            kwargs["max_tokens"] = max_tokens or self.settings.llm_max_output_tokens

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        content = choice.message.content or ""
        usage: dict[str, Any] = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        return content, usage


def _backoff(attempt: int) -> float:
    return min(8.0, (2 ** (attempt - 1)) * 0.8) + random.uniform(0, 0.4)
