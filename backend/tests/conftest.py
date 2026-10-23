from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.pop("APP_ACCESS_KEY", None)

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas import BrandKit, Footer, Highlight, Newsletter, Section, Socials, Stat  # noqa: E402


@pytest.fixture(scope="session")
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def client(settings):
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_newsletter() -> Newsletter:
    return Newsletter(
        company_name="TechNova",
        newsletter_type="Monthly Update",
        hero_title="AI Assistant 2.0 Lands as TechNova Passes 100k Users",
        subtitle="A record quarter of launches, partnerships and growth.",
        summary="TechNova shipped AI Assistant 2.0, crossed one hundred thousand active users and opened its Bangalore office. " * 2,
        date="October 2026",
        estimated_read_time="4 min read",
        highlights=[
            Highlight(icon="🚀", title="AI Assistant 2.0", subtitle="Faster, smarter, multilingual."),
            Highlight(icon="📈", title="100,000 users", subtitle="Doubling in six months."),
        ],
        sections=[
            Section(icon="🚀", title="Product", content="**AI Assistant 2.0** is here.\n\n- Faster\n- Smarter"),
            Section(icon="🏢", title="Offices", content="We opened in Bangalore."),
        ],
        stats=[Stat(value="100k", label="Active users"), Stat(value="2", label="New offices")],
        footer=Footer(website="https://technova.example", socials=Socials(linkedin="https://linkedin.com/company/technova")),
    )


@pytest.fixture
def sample_brand() -> BrandKit:
    return BrandKit(company_name="TechNova", primary="#6366f1", secondary="#8b5cf6", accent="#06b6d4")
