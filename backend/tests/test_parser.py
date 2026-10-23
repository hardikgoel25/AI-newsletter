from __future__ import annotations

import json

import pytest

from app.schemas import BrandKit, GenerateOptions
from app.services.parser import JSONExtractError, coerce_newsletter, extract_json

GOOD = {
    "company_name": "X",
    "newsletter_type": "Monthly Update",
    "hero_title": "Big news",
    "subtitle": "sub",
    "summary": "summary",
    "date": "October 2026",
    "estimated_read_time": "3 min read",
    "highlights": [{"icon": "🚀", "title": "A", "subtitle": "a"}, {"icon": "📈", "title": "B", "subtitle": "b"}],
    "sections": [{"icon": "🚀", "title": "S1", "content": "c1"}, {"icon": "📈", "title": "S2", "content": "c2"}],
    "stats": [],
    "quote": None,
    "cta": None,
    "image_keywords": ["modern office"],
    "footer": {"tagline": "t"},
}


def test_extract_plain():
    assert extract_json(json.dumps(GOOD))["hero_title"] == "Big news"


def test_extract_fenced_with_prose():
    raw = "Sure! Here is the JSON:\n```json\n" + json.dumps(GOOD) + "\n```\nHope this helps."
    assert extract_json(raw)["company_name"] == "X"


def test_extract_trailing_commas_and_smart_quotes():
    raw = '{"a": 1, "b": [1,2,],}'
    assert extract_json(raw) == {"a": 1, "b": [1, 2]}
    raw2 = '{“a”: “b”}'
    assert extract_json(raw2) == {"a": "b"}


def test_extract_raw_newlines_in_strings():
    raw = '{"content": "line one\nline two"}'
    assert extract_json(raw)["content"] == "line one\nline two"


def test_extract_fails_cleanly():
    with pytest.raises(JSONExtractError):
        extract_json("no json here")
    with pytest.raises(JSONExtractError):
        extract_json("")


def test_coerce_applies_brand_and_overrides():
    opts = GenerateOptions(highlight_count=2, section_count=2, hero_title_override="Override!", include_cta=False)
    brand = BrandKit(company_name="Brand Co", website="brandco.com", contact_email="hi@brandco.com")
    data = dict(GOOD)
    data["footer"] = {"website": "https://invented.example", "phone": "+1 555 0100"}
    n, warnings = coerce_newsletter(data, opts, brand)
    assert n.company_name == "Brand Co"
    assert n.hero_title == "Override!"
    assert n.footer.website == "https://brandco.com"  # brand wins; bare domain normalised
    assert n.footer.contact_email == "hi@brandco.com"
    assert n.footer.phone == ""  # invented contact details are dropped
    assert n.cta is None
    assert n.footer.copyright.startswith("©")
    assert warnings == []


def test_coerce_legacy_shapes_and_counts():
    opts = GenerateOptions(highlight_count=4, section_count=2)
    data = dict(GOOD)
    data["highlights"] = ["AI launch", "Hiring engineers"]  # legacy string highlights
    data["sections"] = [
        {"title": "Second", "content": "x", "priority": 2},
        {"title": "First", "content": "y", "priority": 1},
    ]
    data["estimated_read_time"] = "Auto"
    n, warnings = coerce_newsletter(data, opts, BrandKit())
    assert [s.title for s in n.sections] == ["First", "Second"]
    assert n.highlights[0].icon == "⭐"
    assert n.estimated_read_time.endswith("min read")
    assert any("highlights" in w for w in warnings)


def test_coerce_rejects_no_sections():
    data = dict(GOOD)
    data["sections"] = []
    with pytest.raises(ValueError):
        coerce_newsletter(data, GenerateOptions(), BrandKit())


def test_icons_never_words():
    data = dict(GOOD)
    data["sections"][0] = {"icon": "rocket", "title": "S", "content": "c"}
    n, _ = coerce_newsletter(data, GenerateOptions(section_count=2, highlight_count=2), BrandKit())
    assert n.sections[0].icon == "📰"
