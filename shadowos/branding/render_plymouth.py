#!/usr/bin/env python3
"""Render Plymouth boot theme assets for ShadowOS.

Outputs to ../profile/airootfs/usr/share/plymouth/themes/shadowos/:
  - logo.png            (320x320 hex S monogram, transparent PNG)
  - logo-glow.png       (with outer glow halo for pulse animation)
  - dot.png             (16x16 accent dot for orbit spinner)
  - background.png      (1920x1080 dark hex backdrop)
  - progress-bar-bg.png, progress-bar.png (fallback indeterminate bar parts)
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "profile" / "airootfs" / "usr" / "share" / "plymouth" / "themes" / "shadowos"
OUT.mkdir(parents=True, exist_ok=True)

# Palette (matches default teal wallpaper)
BG_OUTER = (5, 8, 12)
BG_INNER = (20, 27, 36)
GRID = (25, 34, 44)
TEAL = (0, 224, 164)
WHITE = (230, 237, 243)

FONT_PATHS = [
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def find_font(size: int) -> ImageFont.ImageFont:
    for p in FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()  # type: ignore[return-value]


def hex_points(cx: float, cy: float, r: float):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]


def make_logo(size: int = 320, glow: bool = False) -> Image.Image:
    """Hex S monogram on transparent background. Optional outer glow."""
    pad = 40 if glow else 16
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    if glow:
        # Outer halo: large blurred teal hex
        glow_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        cx, cy = size / 2, size / 2
        r_outer = (size - pad) / 2
        gd.polygon(hex_points(cx, cy, r_outer), fill=TEAL + (140,))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=22))
        canvas.alpha_composite(glow_layer)

    # Main hex frame
    d = ImageDraw.Draw(canvas)
    cx, cy = size / 2, size / 2
    r = (size - pad) / 2

    # Inner fill (subtle gradient via two passes)
    inner = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    id_ = ImageDraw.Draw(inner)
    id_.polygon(hex_points(cx, cy, r), fill=(15, 22, 31, 255))
    canvas.alpha_composite(inner)

    # Outer ring (faint)
    d.line(hex_points(cx, cy, r * 1.04) + [hex_points(cx, cy, r * 1.04)[0]],
           fill=TEAL + (60,), width=1)
    # Inner border (bold)
    d.line(hex_points(cx, cy, r) + [hex_points(cx, cy, r)[0]],
           fill=TEAL + (255,), width=4)

    # 'S' letter
    font = find_font(int(r * 1.4))
    bb = d.textbbox((0, 0), "S", font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1] - int(r * 0.04)),
           "S", font=font, fill=WHITE + (255,))

    return canvas


def make_dot(size: int = 18) -> Image.Image:
    """Solid teal dot used by orbit spinner."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    # Soft outer glow
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([1, 1, size - 1, size - 1], fill=TEAL + (180,))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=2))
    canvas.alpha_composite(glow)
    # Bright core
    d.ellipse([4, 4, size - 4, size - 4], fill=TEAL + (255,))
    return canvas


def make_background(w: int = 1920, h: int = 1080) -> Image.Image:
    """Dark hex backdrop matching the default wallpaper."""
    # Radial gradient
    try:
        import numpy as np
        yy, xx = np.mgrid[0:h, 0:w]
        cx, cy = w / 2, h * 0.48
        rmax = max(w, h) * 0.78
        d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
        inner = np.array(BG_INNER, dtype=np.float32)
        outer = np.array(BG_OUTER, dtype=np.float32)
        rgb = (inner[None, None, :] + (outer - inner)[None, None, :] * d[..., None]).astype("uint8")
        base = Image.fromarray(rgb, mode="RGB").convert("RGBA")
    except ImportError:
        base = Image.new("RGBA", (w, h), BG_OUTER + (255,))

    # Hex grid overlay
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    r = 38
    dx = r * math.sqrt(3)
    dy = r * 1.5
    row = 0
    y = -r
    while y < h + r:
        x_off = 0 if row % 2 == 0 else dx / 2
        x = -dx + x_off
        while x < w + dx:
            pts = hex_points(x, y, r)
            ld.line(pts + [pts[0]], fill=GRID + (140,), width=1)
            x += dx
        y += dy
        row += 1
    base.alpha_composite(layer)
    return base.convert("RGB")


def make_progress_bar_bg(w: int = 600, h: int = 6) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h], fill=GRID + (200,))
    return img


def make_progress_bar(w: int = 200, h: int = 6) -> Image.Image:
    """A teal pill — Plymouth animates X position."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Gradient along width
    for x in range(w):
        t = abs((x / w) - 0.5) * 2  # 0 in middle → 1 at edges
        alpha = int(255 * (1 - t * t))
        d.rectangle([x, 0, x + 1, h], fill=TEAL + (alpha,))
    return img


def main():
    print(f"Output: {OUT}")
    (OUT / "logo.png").write_bytes(b"")  # placeholder for `with` clarity
    make_logo(320, glow=False).save(OUT / "logo.png", "PNG", optimize=True)
    print(f"  logo.png")
    make_logo(380, glow=True).save(OUT / "logo-glow.png", "PNG", optimize=True)
    print(f"  logo-glow.png")
    make_dot(18).save(OUT / "dot.png", "PNG", optimize=True)
    print(f"  dot.png")
    make_background(1920, 1080).save(OUT / "background.png", "PNG", optimize=True)
    print(f"  background.png")
    make_progress_bar_bg(600, 6).save(OUT / "progress-bar-bg.png", "PNG", optimize=True)
    print(f"  progress-bar-bg.png")
    make_progress_bar(200, 6).save(OUT / "progress-bar.png", "PNG", optimize=True)
    print(f"  progress-bar.png")
    print("\nDone.")


if __name__ == "__main__":
    main()
