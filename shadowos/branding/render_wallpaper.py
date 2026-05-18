#!/usr/bin/env python3
"""Render ShadowOS wallpaper with Pillow (no SVG renderer required)."""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path(__file__).resolve().parent
SIZES = [(1920, 1080), (3840, 2160)]

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_LIGHT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf"

# Palette
BG_OUTER = (5, 8, 12)
BG_INNER = (20, 27, 36)
HEX_STROKE = (25, 34, 44)
TEAL = (0, 224, 164)
WHITE = (230, 237, 243)
DIM = (107, 119, 133)
DARK_TEXT = (90, 100, 112)
MICRO = (61, 70, 81)
S_FILL_TOP = (26, 35, 48)
S_FILL_BOT = (11, 16, 24)
BRACKET = (31, 42, 54)


def radial_gradient(w: int, h: int, inner: tuple, outer: tuple, cx_pct=0.5, cy_pct=0.46, radius_pct=0.75) -> Image.Image:
    img = Image.new("RGB", (w, h), outer)
    px = img.load()
    cx, cy = w * cx_pct, h * cy_pct
    rmax = max(w, h) * radius_pct
    for y in range(h):
        for x in range(w):
            d = math.hypot(x - cx, y - cy) / rmax
            d = min(1.0, d)
            t = d
            r = int(inner[0] + (outer[0] - inner[0]) * t)
            g = int(inner[1] + (outer[1] - inner[1]) * t)
            b = int(inner[2] + (outer[2] - inner[2]) * t)
            px[x, y] = (r, g, b)
    return img


def radial_gradient_fast(w: int, h: int, inner, outer, cx_pct=0.5, cy_pct=0.46, radius_pct=0.75) -> Image.Image:
    """Vectorized via numpy if available, else fall back."""
    try:
        import numpy as np
    except Exception:
        return radial_gradient(w, h, inner, outer, cx_pct, cy_pct, radius_pct)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * cx_pct, h * cy_pct
    rmax = max(w, h) * radius_pct
    d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
    inner = np.array(inner, dtype=np.float32)
    outer = np.array(outer, dtype=np.float32)
    rgb = (inner[None, None, :] + (outer - inner)[None, None, :] * d[..., None]).astype("uint8")
    return Image.fromarray(rgb, mode="RGB")


def draw_hex_grid(img: Image.Image, radius: int, color, opacity: float):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = img.size
    dx = radius * math.sqrt(3)
    dy = radius * 1.5
    a = int(255 * opacity)
    stroke = (color[0], color[1], color[2], a)
    row = 0
    y = -radius
    while y < h + radius:
        x_off = 0 if row % 2 == 0 else dx / 2
        x = -dx + x_off
        while x < w + dx:
            pts = []
            for i in range(6):
                ang = math.radians(60 * i - 30)
                pts.append((x + radius * math.cos(ang), y + radius * math.sin(ang)))
            d.line(pts + [pts[0]], fill=stroke, width=1)
            x += dx
        y += dy
        row += 1
    img.alpha_composite(layer)


def teal_spotlight(img: Image.Image, cx_pct=0.5, cy_pct=0.44, radius_pct=0.32, strength=0.10):
    try:
        import numpy as np
    except Exception:
        return
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * cx_pct, h * cy_pct
    rmax = max(w, h) * radius_pct
    d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
    alpha = ((1 - d) ** 2 * 255 * strength).astype("uint8")
    overlay = np.zeros((h, w, 4), dtype="uint8")
    overlay[..., 0] = TEAL[0]
    overlay[..., 1] = TEAL[1]
    overlay[..., 2] = TEAL[2]
    overlay[..., 3] = alpha
    img.alpha_composite(Image.fromarray(overlay, mode="RGBA"))


def hex_path(cx: float, cy: float, r: float):
    pts = []
    for i in range(6):
        ang = math.radians(60 * i - 30)
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def draw_monogram(img: Image.Image, cx: int, cy: int, scale: float = 1.0):
    R = int(170 * scale)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # vertical fill gradient inside hex (approximate by horizontal strips)
    try:
        import numpy as np
        size = R * 2 + 8
        # build a square fill, then mask to hex
        strip = np.zeros((size, size, 4), dtype="uint8")
        for yy in range(size):
            t = yy / max(1, size - 1)
            r = int(S_FILL_TOP[0] + (S_FILL_BOT[0] - S_FILL_TOP[0]) * t)
            g = int(S_FILL_TOP[1] + (S_FILL_BOT[1] - S_FILL_TOP[1]) * t)
            b = int(S_FILL_TOP[2] + (S_FILL_BOT[2] - S_FILL_TOP[2]) * t)
            strip[yy, :, 0] = r
            strip[yy, :, 1] = g
            strip[yy, :, 2] = b
            strip[yy, :, 3] = 255
        fill_img = Image.fromarray(strip, mode="RGBA")
        # hex mask
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).polygon(hex_path(size / 2, size / 2, R), fill=255)
        fill_img.putalpha(mask)
        layer.paste(fill_img, (cx - size // 2, cy - size // 2), fill_img)
    except Exception:
        d.polygon(hex_path(cx, cy, R), fill=S_FILL_TOP)

    # outer hex stroke (teal)
    d.line(hex_path(cx, cy, R) + [hex_path(cx, cy, R)[0]], fill=TEAL + (255,), width=3)

    # faint outer ring
    outer = hex_path(cx, cy, R * 1.06)
    d.line(outer + [outer[0]], fill=TEAL + (90,), width=1)

    # 'S' letter
    try:
        font = ImageFont.truetype(FONT_BOLD, int(240 * scale))
    except Exception:
        font = ImageFont.load_default()
    text = "S"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1] - int(8 * scale)), text, font=font, fill=WHITE + (255,))

    img.alpha_composite(layer)


def draw_centered_spaced(img: Image.Image, y: int, text: str, font_path: str, size: int,
                          color, tracking: int):
    """Draw a horizontally-centered string with a given pixel tracking between chars."""
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size)
    # measure each char
    widths = []
    for ch in text:
        bb = d.textbbox((0, 0), ch, font=font)
        widths.append(bb[2] - bb[0])
    total = sum(widths) + tracking * (len(text) - 1)
    x = (img.size[0] - total) / 2
    for ch, w in zip(text, widths):
        bb = d.textbbox((0, 0), ch, font=font)
        d.text((x - bb[0], y), ch, font=font, fill=color + (255,))
        x += w + tracking


def draw_corner_brackets(img: Image.Image, inset: int, size: int, width: int, color):
    d = ImageDraw.Draw(img)
    w, h = img.size
    c = color + (255,)
    # top-left
    d.line([(inset, inset), (inset + size, inset)], fill=c, width=width)
    d.line([(inset, inset), (inset, inset + size)], fill=c, width=width)
    # top-right
    d.line([(w - inset, inset), (w - inset - size, inset)], fill=c, width=width)
    d.line([(w - inset, inset), (w - inset, inset + size)], fill=c, width=width)
    # bottom-left
    d.line([(inset, h - inset), (inset + size, h - inset)], fill=c, width=width)
    d.line([(inset, h - inset), (inset, h - inset - size)], fill=c, width=width)
    # bottom-right
    d.line([(w - inset, h - inset), (w - inset - size, h - inset)], fill=c, width=width)
    d.line([(w - inset, h - inset), (w - inset, h - inset - size)], fill=c, width=width)


def render(w: int, h: int) -> Image.Image:
    base = radial_gradient_fast(w, h, BG_INNER, BG_OUTER).convert("RGBA")
    # hex grid (radius scales with resolution)
    hex_r = max(28, int(h * 0.034))
    draw_hex_grid(base, hex_r, HEX_STROKE, opacity=0.55)
    # teal spotlight behind monogram
    teal_spotlight(base, cy_pct=0.44, radius_pct=0.34, strength=0.12)

    # monogram center
    cx, cy = w // 2, int(h * 0.44)
    monogram_scale = h / 1080
    draw_monogram(base, cx, cy, scale=monogram_scale)

    # wordmark
    word_y = int(h * 0.66)
    draw_centered_spaced(base, word_y, "SHADOWOS",
                         FONT_BOLD, int(60 * monogram_scale), WHITE, tracking=int(10 * monogram_scale))
    # tagline
    tag_y = int(h * 0.72)
    draw_centered_spaced(base, tag_y, "PRIVACY · ISOLATED · AMNESIC",
                         FONT_REG, int(15 * monogram_scale), DIM, tracking=int(4 * monogram_scale))

    # corner brackets
    inset = int(40 * monogram_scale)
    bsize = int(40 * monogram_scale)
    draw_corner_brackets(base, inset, bsize, max(1, int(1.2 * monogram_scale)), BRACKET)

    # bottom-left mark
    d = ImageDraw.Draw(base)
    bar_x = int(80 * monogram_scale)
    bar_y = int(h - 90 * monogram_scale)
    d.rectangle([bar_x, bar_y, bar_x + int(50 * monogram_scale), bar_y + max(2, int(2 * monogram_scale))],
                fill=TEAL + (255,))
    font_small = ImageFont.truetype(FONT_REG, int(13 * monogram_scale))
    d.text((bar_x + int(64 * monogram_scale), bar_y - int(6 * monogram_scale)),
           "SHADOWCYPHER  /  v0.1", font=font_small, fill=DARK_TEXT + (255,))

    # top-right meta
    font_micro = ImageFont.truetype(FONT_REG, int(12 * monogram_scale))
    meta = "SECURE  SHELL  ·  ZERO  TRACE"
    bb = d.textbbox((0, 0), meta, font=font_micro)
    tw = bb[2] - bb[0]
    d.text((w - int(80 * monogram_scale) - tw, int(60 * monogram_scale)),
           meta, font=font_micro, fill=MICRO + (255,))

    return base.convert("RGB")


def main():
    for w, h in SIZES:
        img = render(w, h)
        path = OUT_DIR / f"wallpaper-{w}x{h}.png"
        img.save(path, "PNG", optimize=True)
        print(f"wrote {path}  ({path.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
