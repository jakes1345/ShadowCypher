#!/usr/bin/env python3
"""ShadowOS desktop — bare, nothing running.

Just: wallpaper + top bar + bottom dock + minimal time/date widget.
This is what you see when you log in or close everything.
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-18-minimal-indigo-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-bare.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_LIGHT= "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf"

W, H = 1920, 1080

PURPLE    = (180, 74, 255)
INDIGO    = (110, 96, 235)
WHITE     = (236, 234, 244)
GRAY      = (148, 142, 168)
DIM       = (108, 102, 130)
DARK      = (72, 66, 92)
BG_HIGH   = (28, 22, 44)
BORDER    = (40, 34, 58)
WARN      = (255, 170, 56)
OK        = (98, 220, 154)

canvas = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
d = ImageDraw.Draw(canvas)

# ── TOP BAR ─────────────────────────────────────────────────────────────────
TOPH = 32
top = Image.new("RGBA", (W, TOPH), (10, 8, 18, 245))
canvas.alpha_composite(top, (0, 0))
d.rectangle([0, TOPH, W, TOPH + 1], fill=BORDER + (220,))
glow = Image.new("RGBA", (W, 4), PURPLE + (60,))
glow = glow.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow, (0, TOPH))

# Activities pill
d.rounded_rectangle([12, 6, 96, 26], radius=6, fill=(180, 74, 255, 32),
                    outline=PURPLE + (180,), width=1)
d.polygon([(22, 16), (28, 12), (34, 16), (28, 20)], fill=PURPLE + (255,))
d.text((42, 9), "Activities",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))

# No focused window (desktop is empty)
d.text((114, 10), "Desktop",
       font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))

# Right: workspaces, mode, tray, clock
wx = W - 380
for i in range(5):
    cx = wx + i * 16
    if i == 0:
        d.rounded_rectangle([cx - 6, 11, cx + 8, 21], radius=4,
                            fill=PURPLE + (255,))
        d.text((cx - 3, 10), "1",
               font=ImageFont.truetype(FONT_BOLD, 9), fill=WHITE + (255,))
    else:
        d.ellipse([cx - 2, 14, cx + 2, 18], fill=DARK + (255,))

mx = W - 270
d.ellipse([mx, 13, mx + 8, 21], fill=WARN + (255,))
d.text((mx + 13, 10), "pentest",
       font=ImageFont.truetype(FONT_REG, 11), fill=GRAY + (255,))

tx = W - 180
for ic in ["", "", "", "", ""]:
    d.text((tx, 10), ic, font=ImageFont.truetype(FONT_REG, 13),
           fill=DIM + (255,))
    tx += 19

d.text((W - 80, 10), "21:34",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))

# ── CENTER WIDGET — minimal clock + date + greeting ─────────────────────────
# Drawn directly on wallpaper, no panel. Just text with subtle shadow.
center_y = H // 2 - 60

# Time (huge, light weight)
try:
    time_font = ImageFont.truetype(FONT_LIGHT, 180)
except Exception:
    time_font = ImageFont.truetype(FONT_REG, 180)
time_str = "21:34"
bb = d.textbbox((0, 0), time_str, font=time_font)
tw = bb[2] - bb[0]

# Soft shadow under the time
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(shadow).text(((W - tw) // 2 + 3, center_y - bb[1] + 3),
                              time_str, font=time_font, fill=(0, 0, 0, 180))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
canvas.alpha_composite(shadow)

d.text(((W - tw) // 2 - bb[0], center_y - bb[1]),
       time_str, font=time_font, fill=WHITE + (235,))

# Date below time
date_font = ImageFont.truetype(FONT_REG, 22)
date_str = "Monday  ·  May 18"
bb2 = d.textbbox((0, 0), date_str, font=date_font)
dw = bb2[2] - bb2[0]
d.text(((W - dw) // 2 - bb2[0], center_y + 175),
       date_str, font=date_font, fill=GRAY + (220,))

# Tiny status line — very subtle, only when something deserves attention
status_font = ImageFont.truetype(FONT_MONO, 12)
status = "system nominal  ·  3 updates available  ·  guardian idle"
bb3 = d.textbbox((0, 0), status, font=status_font)
sw = bb3[2] - bb3[0]
d.text(((W - sw) // 2 - bb3[0], center_y + 215),
       status, font=status_font, fill=DIM + (200,))

# ── BOTTOM DOCK ─────────────────────────────────────────────────────────────
DOCK_H = 56
dock_y = H - DOCK_H
dock = Image.new("RGBA", (W, DOCK_H), (10, 8, 18, 245))
canvas.alpha_composite(dock, (0, dock_y))
glow_top = Image.new("RGBA", (W, 4), PURPLE + (100,))
glow_top = glow_top.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow_top, (0, dock_y - 2))

# Dock icons — pinned apps, none running
DOCK_ICONS = [
    ("◆",   PURPLE),  # ShadowCypher
    ("",   GRAY),    # files
    ("",   GRAY),    # firefox
    ("",   GRAY),    # vscode
    ("",   GRAY),    # terminal
    ("",   GRAY),    # helix/notes
    ("",   GRAY),    # discord
    ("",   GRAY),    # steam
    ("",   GRAY),    # tools
]
icon_size = 40
total_w = len(DOCK_ICONS) * (icon_size + 10) - 10
start_x = (W - total_w) // 2
for i, (g, c) in enumerate(DOCK_ICONS):
    ix = start_x + i * (icon_size + 10)
    iy = dock_y + (DOCK_H - icon_size) // 2 - 2
    d.rounded_rectangle([ix, iy, ix + icon_size, iy + icon_size],
                        radius=10, fill=BG_HIGH + (220,),
                        outline=BORDER + (200,), width=1)
    if g == "◆":
        cxd, cyd = ix + icon_size / 2, iy + icon_size / 2
        d.polygon([(cxd, cyd - 12), (cxd + 10, cyd), (cxd, cyd + 12), (cxd - 10, cyd)],
                   fill=PURPLE + (255,))
    else:
        d.text((ix + icon_size / 2 - 9, iy + 10), g,
               font=ImageFont.truetype(FONT_REG, 20), fill=c + (255,))

# Bottom-left mode pill
mp_x = 14
mp_y = dock_y + 16
d.rounded_rectangle([mp_x, mp_y, mp_x + 116, mp_y + 24],
                    radius=12, fill=(255, 170, 56, 18),
                    outline=WARN + (200,), width=1)
d.ellipse([mp_x + 10, mp_y + 8, mp_x + 18, mp_y + 16], fill=WARN + (255,))
d.text((mp_x + 24, mp_y + 5), "pentest",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))

# Bottom-right system info
sx = W - 200
sf = ImageFont.truetype(FONT_MONO, 10)
d.text((sx, dock_y + 12),
       "CPU 4%   RAM 1.1/16 GB",
       font=sf, fill=GRAY + (255,))
d.text((sx, dock_y + 28),
       "↑ 12 KB/s   ↓ 8 KB/s",
       font=sf, fill=GRAY + (255,))

# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
