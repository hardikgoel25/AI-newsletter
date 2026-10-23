"""Built-in brand presets. Users can create their own in the UI; these ship as examples."""

from __future__ import annotations

import base64
from functools import lru_cache

from app.config import ASSETS_DIR
from app.schemas import BrandKit, Socials


def _asset_data_uri(relative: str, mime: str) -> str:
    path = ASSETS_DIR / relative
    if not path.exists():
        return ""
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


@lru_cache
def presets() -> list[BrandKit]:
    return [
        BrandKit(
            id="generic",
            name="Generic",
            company_name="",
            tagline="",
            primary="#6366f1",
            secondary="#8b5cf6",
            accent="#06b6d4",
        ),
        BrandKit(
            id="avl",
            name="AVL",
            company_name="AVL",
            tagline="Reimagining Motion",
            logo=_asset_data_uri("brands/avl/logo.svg", "image/svg+xml"),
            logo_invert="on-dark",
            primary="#23a638",
            secondary="#009770",
            accent="#00a5c8",
            website="https://www.avl.com",
            socials=Socials(
                linkedin="https://www.linkedin.com/company/avl",
                youtube="https://www.youtube.com/@AVLListens",
                facebook="https://www.facebook.com/AVL.Listens",
                instagram="https://www.instagram.com/avllistens",
            ),
            subscription_note="You are receiving this newsletter because you subscribed to AVL updates.",
        ),
        BrandKit(
            id="midnight",
            name="Midnight",
            primary="#0ea5e9",
            secondary="#2563eb",
            accent="#a855f7",
            font_heading="Space Grotesk",
            font_body="DM Sans",
        ),
        BrandKit(
            id="ember",
            name="Ember",
            primary="#f97316",
            secondary="#ef4444",
            accent="#fbbf24",
            font_heading="Manrope",
            font_body="Manrope",
        ),
        BrandKit(
            id="forest",
            name="Forest",
            primary="#059669",
            secondary="#0d9488",
            accent="#84cc16",
            font_heading="Fraunces",
            font_body="Inter",
        ),
    ]
