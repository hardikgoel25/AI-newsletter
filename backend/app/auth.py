"""Request authentication.

Two ways in:

* **Access key** — `X-App-Key` matches `APP_ACCESS_KEY`. The request may use the server's
  provider keys.
* **Bring your own key (BYOK)** — `X-LLM-Key` (+ optional `X-LLM-Provider`, default groq).
  The request is served with *that* key only; the server's keys are never used, so the
  access-key gate does not apply. The key lives only in the request; it is never stored
  or logged.

When `APP_ACCESS_KEY` is unset the server is open and every request may use server keys.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Header, HTTPException

from app.config import Settings, get_settings

Provider = Literal["groq", "openai", "gemini", "ollama"]
_PROVIDERS: tuple[str, ...] = ("groq", "openai", "gemini")


@dataclass(frozen=True)
class AuthContext:
    mode: Literal["open", "access-key", "byok"]
    llm_key: str | None = None
    llm_provider: str | None = None

    def provider_for(self, requested: str | None) -> str | None:
        """BYOK requests are pinned to the provider the key belongs to."""
        return self.llm_provider if self.mode == "byok" else requested


async def get_auth(
    settings: Settings = Depends(get_settings),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
    x_llm_key: str | None = Header(default=None, alias="X-LLM-Key"),
    x_llm_provider: str | None = Header(default=None, alias="X-LLM-Provider"),
) -> AuthContext:
    app_key = (x_app_key or "").strip()
    llm_key = (x_llm_key or "").strip()
    provider = (x_llm_provider or "groq").strip().lower()

    if app_key and settings.app_access_key and secrets.compare_digest(app_key, settings.app_access_key):
        return AuthContext(mode="access-key")

    if llm_key:
        if not settings.allow_byok:
            raise HTTPException(status_code=403, detail="This server does not accept personal API keys.")
        if provider not in _PROVIDERS:
            raise HTTPException(status_code=400, detail="X-LLM-Provider must be groq, openai or gemini.")
        if len(llm_key) > 256 or any(ch.isspace() for ch in llm_key):
            raise HTTPException(status_code=400, detail="The API key looks malformed.")
        return AuthContext(mode="byok", llm_key=llm_key, llm_provider=provider)

    if not settings.app_access_key:
        return AuthContext(mode="open")

    raise HTTPException(
        status_code=401,
        detail="This server requires an access key. Enter it under the key icon, or paste your own provider API key there instead.",
    )
