from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.sanitize import ImageError, SVGError, markdown_to_html, process_raster, sanitize_svg


def test_markdown_allows_safe_subset():
    html = markdown_to_html("**Bold** and a [link](https://example.com)\n\n- one\n- two")
    assert "<strong>Bold</strong>" in html
    assert 'href="https://example.com"' in html
    assert 'rel="noopener noreferrer"' in html
    assert "<li>one</li>" in html


def test_markdown_strips_scripts_and_bad_schemes():
    html = markdown_to_html('<script>alert(1)</script> [x](javascript:alert(1)) <img src=x onerror=alert(1)>')
    assert "<script" not in html
    assert 'href="javascript' not in html
    assert "<img" not in html
    assert "onerror=" not in html.replace("&lt;img src=x onerror=alert(1)&gt;", "")


def test_markdown_demotes_headings():
    html = markdown_to_html("# Heading\ntext")
    assert "<h1" not in html
    assert "<strong>Heading</strong>" in html


MALICIOUS_SVG = b"""<?xml version="1.0"?>
<!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" onload="alert(1)">
  <script>alert(1)</script>
  <a xlink:href="javascript:alert(1)"><rect width="10" height="10" onclick="evil()"/></a>
  <image xlink:href="https://evil.example/track.png"/>
  <foreignObject><body xmlns="http://www.w3.org/1999/xhtml"><script>1</script></body></foreignObject>
  <style>@import url(https://evil.example/x.css);</style>
  <circle r="5" style="fill:url(https://evil.example)"/>
</svg>"""


def test_svg_with_dtd_is_rejected():
    with pytest.raises(SVGError):
        sanitize_svg(MALICIOUS_SVG)


def test_svg_sanitizer_strips_dangerous_content():
    svg = MALICIOUS_SVG.split(b"\n", 2)[2]  # drop the xml decl + doctype
    svg = b'<?xml version="1.0"?>\n' + svg
    clean = sanitize_svg(svg).decode()
    assert "<script" not in clean
    assert "onload" not in clean
    assert "onclick" not in clean
    assert "javascript:" not in clean
    assert "evil.example" not in clean
    assert "foreignObject" not in clean
    assert "<rect" in clean  # content survives


def test_svg_rejects_non_svg():
    with pytest.raises(SVGError):
        sanitize_svg(b"<html><body>hi</body></html>")


def _png(w=2000, h=1000):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_raster_is_reencoded_and_resized():
    out = process_raster(_png(), max_dimension=800)
    assert out.mime == "image/jpeg"
    assert out.width == 800 and out.height == 400
    assert out.data_uri.startswith("data:image/jpeg;base64,")


def test_raster_rejects_garbage():
    with pytest.raises(ImageError):
        process_raster(b"GIF89a-not-really-an-image" * 10)
