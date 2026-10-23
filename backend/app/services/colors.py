"""Small colour utilities used to derive theme tokens from a brand kit."""

from __future__ import annotations

RGB = tuple[int, int, int]


def hex_to_rgb(value: str) -> RGB:
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def rgb_to_hex(rgb: RGB) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def mix(a: str, b: str, t: float) -> str:
    """Blend colour a towards b by t (0..1)."""
    ra, ga, ba = hex_to_rgb(a)
    rb, gb, bb = hex_to_rgb(b)
    return rgb_to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))


def _channel(c: int) -> float:
    c_ = c / 255
    return c_ / 12.92 if c_ <= 0.03928 else ((c_ + 0.055) / 1.055) ** 2.4


def luminance(value: str) -> float:
    r, g, b = hex_to_rgb(value)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def on_color(bg: str) -> str:
    """Return black or white, whichever reads better on bg."""
    return "#111111" if contrast_ratio(bg, "#111111") >= contrast_ratio(bg, "#ffffff") else "#ffffff"


def ensure_contrast(fg: str, bg: str, minimum: float = 4.5) -> str:
    """Nudge fg towards black/white until it meets the contrast ratio."""
    if contrast_ratio(fg, bg) >= minimum:
        return fg
    target = "#000000" if luminance(bg) > 0.4 else "#ffffff"
    out = fg
    for i in range(1, 21):
        out = mix(fg, target, i / 20)
        if contrast_ratio(out, bg) >= minimum:
            return out
    return target


def rgba(value: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(value)
    return f"rgba({r},{g},{b},{alpha:.2f})"
