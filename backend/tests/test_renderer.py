from __future__ import annotations

import pytest

from app.schemas import BrandKit, RenderOptions
from app.services.renderer import TEMPLATES, render_email_html, render_html, render_markdown, render_text


@pytest.mark.parametrize("template_id", list(TEMPLATES))
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_every_template_renders(sample_newsletter, sample_brand, template_id, theme):
    html = render_html(sample_newsletter, sample_brand, RenderOptions(template=template_id, theme=theme))
    assert html.startswith("<!DOCTYPE html>")
    assert sample_newsletter.hero_title in html
    assert "<strong>AI Assistant 2.0</strong>" in html  # markdown rendered
    assert "100k" in html
    assert "LinkedIn" in html
    assert "--primary: #6366f1" in html
    assert "<script" not in html.lower()


def test_user_content_is_escaped(sample_newsletter, sample_brand):
    sample_newsletter.hero_title = '<img src=x onerror=alert(1)> "quoted"'
    sample_newsletter.sections[0].content = "<script>alert(1)</script> **ok**"
    html = render_html(sample_newsletter, sample_brand, RenderOptions())
    assert "<img src=x" not in html
    assert "&lt;img src=x onerror" in html  # escaped, inert
    assert "<script>" not in html


def test_logo_invert_and_fallback(sample_newsletter):
    brand = BrandKit(company_name="TechNova", logo="https://example.com/logo.png", logo_invert="on-dark")
    html = render_html(sample_newsletter, brand, RenderOptions(theme="dark"))
    assert "brightness(0) invert(1)" in html
    html_light = render_html(sample_newsletter, brand, RenderOptions(theme="light"))
    assert "brightness(0) invert(1)" not in html_light
    html_nologo = render_html(sample_newsletter, BrandKit(company_name="TechNova"), RenderOptions())
    assert 'class="logo-fallback"' in html_nologo and ">T<" in html_nologo


def test_email_html_resolves_css_variables(sample_newsletter, sample_brand):
    html = render_email_html(sample_newsletter, sample_brand, RenderOptions(template="minimal"))
    assert "var(--" not in html
    assert "fonts.googleapis" not in html


def test_markdown_and_text(sample_newsletter):
    md = render_markdown(sample_newsletter)
    assert md.startswith("# AI Assistant 2.0")
    assert "## 🚀 Product" in md
    text = render_text(sample_newsletter)
    assert "**" not in text
    assert "AI Assistant 2.0" in text
