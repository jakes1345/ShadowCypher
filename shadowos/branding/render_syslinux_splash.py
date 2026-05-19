#!/usr/bin/env python3
"""Render SYSLINUX splash.png for ShadowOS BIOS boot.

SYSLINUX requires a 640x480 PNG (indexed or RGB, up to 16-color palette
recommended for old-school compatibility but RGB works on modern hardware).
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "profile" / "syslinux" / "splash.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

W, H = 640, 480

BG_DEEP = (5, 8, 12)
BG_INNER = (20, 27, 36)
TEAL    = (0, 224, 164)
WHITE   = (230, 237, 243)
DIM     = (107, 119, 133)

# Radial gradient bg
try:
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W]
    cx, cy = W / 2, H * 0.45
    rmax = max(W, H) * 0.75
    d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
    inner = np.array(BG_INNER, dtype=np.float32)
    outer = np.array(BG_DEEP, dtype=np.float32)
    rgb = (inner[None, None, :] + (outer - inner)[None, None, :] * d[..., None]).astype("uint8")
    img = Image.fromarray(rgb, mode="RGB").convert("RGBA")
except ImportError:
    img = Image.new("RGBA", (W, H), BG_DEEP + (255,))

d = ImageDraw.Draw(img)

# Hex S monogram center
def hex_pts(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]

CX, CY = W // 2, int(H * 0.40)
R = 64

# Glow
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.polygon(hex_pts(CX, CY, R * 1.4), fill=TEAL + (50,))
glow = glow.filter(ImageFilter.GaussianBlur(radius=18))
img.alpha_composite(glow)

# Hex inner fill
d.polygon(hex_pts(CX, CY, R), fill=BG_INNER)
d.line(hex_pts(CX, CY, R) + [hex_pts(CX, CY, R)[0]], fill=TEAL + (255,), width=3)
d.line(hex_pts(CX, CY, R * 1.06) + [hex_pts(CX, CY, R * 1.06)[0]],
       fill=TEAL + (90,), width=1)

# S letter
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
try:
    f = ImageFont.truetype(FONT_BOLD, 84)
except Exception:
    f = ImageFont.load_default()
bb = d.textbbox((0, 0), "S", font=f)
tw, th = bb[2] - bb[0], bb[3] - bb[1]
d.text((CX - tw / 2 - bb[0], CY - th / 2 - bb[1] - 4),
       "S", font=f, fill=WHITE)

# Wordmark below
try:
    wf = ImageFont.truetype(FONT_BOLD, 38)
except Exception:
    wf = ImageFont.load_default()
wm = "SHADOWOS"
bb = d.textbbox((0, 0), wm, font=wf)
tw = bb[2] - bb[0]
d.text(((W - tw) // 2 - bb[0], int(H * 0.62)),
       wm, font=wf, fill=WHITE)

# Tagline
try:
    sf = ImageFont.truetype(FONT_BOLD, 12)
except Exception:
    sf = ImageFont.load_default()
tag = "PRIVACY  ·  ISOLATED  ·  AMNESIC"
bb = d.textbbox((0, 0), tag, font=sf)
tw = bb[2] - bb[0]
d.text(((W - tw) // 2 - bb[0], int(H * 0.72)),
       tag, font=sf, fill=DIM)

# Footer
try:
    ff = ImageFont.truetype(FONT_BOLD, 10)
except Exception:
    ff = ImageFont.load_default()
foot = "[ select an entry below ]"
bb = d.textbbox((0, 0), foot, font=ff)
tw = bb[2] - bb[0]
d.text(((W - tw) // 2 - bb[0], int(H * 0.85)),
       foot, font=ff, fill=DIM)

# Convert to RGB + save (SYSLINUX likes RGB or P)
img.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
