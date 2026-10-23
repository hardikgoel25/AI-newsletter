"""Sanitisation of everything that can carry executable or hostile content.

* Markdown from the model  -> `markdown_to_html` (CommonMark + allow-list HTML cleaner)
* Uploaded SVG logos       -> `sanitize_svg`   (allow-list XML filter)
* Uploaded raster images   -> `process_raster` (decode + re-encode through Pillow)
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass
from xml.etree import ElementTree as ET  # noqa: S405 - only used for serialisation, parsing goes through defusedxml

import nh3
from defusedxml import ElementTree as SafeET
from markdown_it import MarkdownIt
from PIL import Image, ImageOps, UnidentifiedImageError

# Decompression-bomb guard (Pillow raises above this).
Image.MAX_IMAGE_PIXELS = 40_000_000

# ---------------------------------------------------------------------------
# Markdown -> HTML
# ---------------------------------------------------------------------------

_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable(
    ["table", "strikethrough"]
)

_ALLOWED_TAGS = {
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "a",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "pre",
    "h3",
    "h4",
    "hr",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "span",
}
_ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "th": {"align"},
    "td": {"align"},
}


def markdown_to_html(text: str) -> str:
    """Render untrusted Markdown to a strict subset of HTML."""
    if not text:
        return ""
    # Demote any headings the model emitted so they never compete with template headings.
    text = re.sub(r"^#{1,6}\s+(.+?)\s*#*\s*$", r"**\1**", text, flags=re.MULTILINE)
    html = _md.render(text)
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer",
        strip_comments=True,
    )


def plain_text(text: str) -> str:
    """Strip Markdown markers for text/markdown-free outputs."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"[_*`]+", "", text)
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
    return text.strip()


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_FORBIDDEN_TAGS = {"script", "foreignobject", "iframe", "embed", "object", "audio", "video", "animate", "set", "handler"}
_UNWRAP_TAGS = {"a"}
_URL_ATTRS = {"href", f"{{{_XLINK_NS}}}href"}
_STYLE_DANGER_RE = re.compile(r"(url\s*\(|@import|expression\s*\(|javascript:)", re.IGNORECASE)


class SVGError(ValueError):
    pass


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def sanitize_svg(data: bytes, *, max_bytes: int = 1_000_000) -> bytes:
    """Return a sanitised SVG document or raise SVGError."""
    if len(data) > max_bytes:
        raise SVGError("SVG is too large.")
    try:
        root = SafeET.fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except Exception as exc:  # defusedxml raises several types
        raise SVGError(f"Invalid SVG: {exc}") from exc

    if _local(root.tag) != "svg":
        raise SVGError("Root element is not <svg>.")

    def clean(el) -> None:
        changed = True
        while changed:
            changed = False
            for idx, child in enumerate(list(el)):
                name = _local(child.tag)
                if name in _FORBIDDEN_TAGS:
                    el.remove(child)
                    changed = True
                    break
                if name in _UNWRAP_TAGS:
                    el.remove(child)
                    for offset, grandchild in enumerate(list(child)):
                        el.insert(idx + offset, grandchild)
                    changed = True
                    break
        for child in list(el):
            clean(child)

        for attr in list(el.attrib):
            lname = _local(attr)
            value = el.attrib[attr]
            if lname.startswith("on"):
                del el.attrib[attr]
            elif attr in _URL_ATTRS or lname == "href":
                v = value.strip()
                if not (v.startswith("#") or v.startswith("data:image/")):
                    del el.attrib[attr]
            elif lname == "style" and _STYLE_DANGER_RE.search(value):
                del el.attrib[attr]

        if _local(el.tag) == "style" and el.text and _STYLE_DANGER_RE.search(el.text):
            el.text = ""

    clean(root)

    ET.register_namespace("", _SVG_NS)
    ET.register_namespace("xlink", _XLINK_NS)
    out = ET.tostring(root, encoding="utf-8")
    if b"xmlns=" not in out[:300]:
        out = out.replace(b"<svg", b'<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return out


# ---------------------------------------------------------------------------
# Raster images
# ---------------------------------------------------------------------------


@dataclass
class ProcessedImage:
    data: bytes
    mime: str
    width: int
    height: int

    @property
    def data_uri(self) -> str:
        return f"data:{self.mime};base64," + base64.b64encode(self.data).decode("ascii")


class ImageError(ValueError):
    pass


def process_raster(data: bytes, *, max_dimension: int = 1600, max_bytes: int = 5 * 1024 * 1024) -> ProcessedImage:
    """Decode, strip metadata, resize and re-encode an uploaded raster image."""
    if len(data) > max_bytes:
        raise ImageError("Image is too large.")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))  # verify() invalidates the object
        img.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ImageError("File is not a supported image.") from exc

    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")
    img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buf = io.BytesIO()
    if has_alpha:
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    else:
        img.save(buf, format="JPEG", quality=86, optimize=True, progressive=True)
        mime = "image/jpeg"
    return ProcessedImage(data=buf.getvalue(), mime=mime, width=img.width, height=img.height)


def svg_data_uri(svg: bytes) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


def sniff_is_svg(data: bytes) -> bool:
    head = data[:2048].lstrip().lower()
    return head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head)
