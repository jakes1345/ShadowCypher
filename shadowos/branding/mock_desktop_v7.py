#!/usr/bin/env python3
"""ShadowOS desktop — v7: the actual designed bare-desktop.

Visual language ties to: wallpaper hex monogram, Plymouth orbit dots,
GRUB selection accent, SDDM login input, top-bar purple glow. Same hex
shape, same purple-gradient strip, same diamond mark across all chrome.

Layout:
  • Wallpaper with hex monogram visible
  • Top bar with hex-pattern texture
  • Left half: greeting + clock framing the wallpaper's S monogram
  • Right half: widget column — mode card, today's stats, threat feed,
    quick action hex grid, system pulse
  • Bottom dock with subtle hex tile pattern
  • Bottom-left mode chip, bottom-right pulse
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-01-hex-teal-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-v7.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_LIGHT= "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf"

W, H = 1920, 1080

PURPLE    = (180, 74, 255)
PURPLE_DK = (130, 50, 200)
PURPLE_LO = (90, 35, 145)
INDIGO    = (110, 96, 235)
BLUE      = (88, 124, 255)
TEAL      = (0, 224, 164)         # reserved for OK / online indicators only
WHITE     = (236, 234, 244)
GRAY      = (148, 142, 168)
DIM       = (108, 102, 130)
DARK      = (72, 66, 92)
BG_DEEP   = (8, 8, 14)
BG_PANEL  = (16, 14, 26)
BG_PANEL2 = (12, 10, 22)
BG_HIGH   = (28, 22, 44)
BORDER    = (40, 34, 58)
BORDER_HI = (60, 50, 90)
WARN      = (255, 170, 56)
CRIT      = (255, 80, 100)
OK        = (98, 220, 154)

# ── Compose wallpaper, tinted toward our palette ────────────────────────────
wp = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
# Tint the wallpaper's teal toward purple slightly to unify the look
try:
    import numpy as np
    arr = np.array(wp, dtype=np.int16)
    # Add slight purple bias
    arr[..., 0] = np.clip(arr[..., 0] + 8, 0, 255)
    arr[..., 2] = np.clip(arr[..., 2] + 14, 0, 255)
    arr[..., 1] = np.clip(arr[..., 1] - 6, 0, 255)
    canvas = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
except ImportError:
    canvas = wp.copy()

# Darken slightly
canvas.alpha_composite(Image.new("RGBA", (W, H), (5, 4, 10, 60)))
d = ImageDraw.Draw(canvas)

# ── Helper: hex points ──────────────────────────────────────────────────────
def hex_pts(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]

# ════════════════════════════════════════════════════════════════════════════
# TOP BAR — with subtle hex texture (visual tie to wallpaper)
# ════════════════════════════════════════════════════════════════════════════
TOPH = 36
top = Image.new("RGBA", (W, TOPH), (10, 8, 18, 248))
canvas.alpha_composite(top, (0, 0))

# Hex texture on the bar
tex = Image.new("RGBA", (W, TOPH), (0, 0, 0, 0))
td = ImageDraw.Draw(tex)
r = 18
dx = r * math.sqrt(3)
dy = r * 1.5
y_ = -r
row = 0
while y_ < TOPH + r:
    x_off = 0 if row % 2 == 0 else dx / 2
    x_ = -dx + x_off
    while x_ < W + dx:
        pts = hex_pts(x_, y_, r)
        td.line(pts + [pts[0]], fill=PURPLE + (28,), width=1)
        x_ += dx
    y_ += dy
    row += 1
canvas.alpha_composite(tex)

# Bottom divider + purple gradient strip
d.rectangle([0, TOPH, W, TOPH + 1], fill=BORDER + (255,))
grad = Image.new("RGBA", (W, 3), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
for x_ in range(W):
    t = x_ / W
    # blue → purple → blue
    if t < 0.5:
        mix = t * 2
        r_, g_, b_ = (int(BLUE[i] + (PURPLE[i] - BLUE[i]) * mix) for i in range(3))
    else:
        mix = (t - 0.5) * 2
        r_, g_, b_ = (int(PURPLE[i] + (BLUE[i] - PURPLE[i]) * mix) for i in range(3))
    gd.line([(x_, 0), (x_, 2)], fill=(r_, g_, b_, 130))
grad = grad.filter(ImageFilter.GaussianBlur(radius=1.2))
canvas.alpha_composite(grad, (0, TOPH))

# Diamond + Activities pill
diamond_pts = [(22, 12), (32, 18), (22, 24), (12, 18)]
d.polygon(diamond_pts, fill=PURPLE + (255,))
d.text((40, 11), "ShadowOS",
       font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))
# subtle "activities" hint
d.text((128, 12), "press Super to open",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))

# Right cluster
# Workspaces (5)
wx = W - 380
for i in range(5):
    cx = wx + i * 16
    if i == 0:
        d.rounded_rectangle([cx - 7, 12, cx + 9, 24], radius=4,
                            fill=PURPLE + (255,))
        d.text((cx - 3, 12), "1",
               font=ImageFont.truetype(FONT_BOLD, 9), fill=WHITE + (255,))
    else:
        d.ellipse([cx - 2, 16, cx + 2, 20], fill=DARK + (255,))

# Mode pip
mx = W - 270
d.ellipse([mx, 14, mx + 8, 22], fill=WARN + (255,))
d.text((mx + 13, 11), "pentest",
       font=ImageFont.truetype(FONT_REG, 11), fill=GRAY + (255,))

# Tray
tx = W - 180
for ic in ["", "", "", "", ""]:
    d.text((tx, 11), ic, font=ImageFont.truetype(FONT_REG, 13),
           fill=DIM + (255,))
    tx += 19

# Clock
d.text((W - 80, 11), "21:34",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))

# ════════════════════════════════════════════════════════════════════════════
# LEFT HALF: greeting + clock framed around the wallpaper's S monogram
# Layout: greeting top-left of monogram, clock right of monogram,
# date below monogram, status strip below that
# ════════════════════════════════════════════════════════════════════════════

# Greeting (above the wallpaper logo area)
greet_y = 200
d.text((90, greet_y),
       "Good evening, jack",
       font=ImageFont.truetype(FONT_LIGHT, 38), fill=WHITE + (240,))
d.text((90, greet_y + 50),
       "you are operating in",
       font=ImageFont.truetype(FONT_REG, 14), fill=GRAY + (255,))
# pentest mode big chip
chip_x = 90
chip_y = greet_y + 76
d.rounded_rectangle([chip_x, chip_y, chip_x + 168, chip_y + 38],
                    radius=18, fill=(255, 170, 56, 32),
                    outline=WARN + (220,), width=1)
d.ellipse([chip_x + 14, chip_y + 12, chip_x + 26, chip_y + 24],
          fill=WARN + (255,))
d.text((chip_x + 36, chip_y + 8), "PENTEST",
       font=ImageFont.truetype(FONT_BOLD, 16), fill=WHITE + (255,))
d.text((chip_x + 36, chip_y + 27), "mode",
       font=ImageFont.truetype(FONT_MONO, 9), fill=WARN + (255,))

# Clock (huge, light, anchored bottom-left of the screen but artistic)
clock_font = ImageFont.truetype(FONT_LIGHT, 220)
clock_str = "21:34"
bb = d.textbbox((0, 0), clock_str, font=clock_font)
clock_w = bb[2] - bb[0]
clock_x = 90
clock_y = 410
# Shadow
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(shadow).text((clock_x + 4, clock_y + 4),
                              clock_str, font=clock_font, fill=(0, 0, 0, 200))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))
canvas.alpha_composite(shadow)
d.text((clock_x, clock_y),
       clock_str, font=clock_font, fill=WHITE + (245,))

# Date
date_font = ImageFont.truetype(FONT_REG, 22)
d.text((clock_x + 8, clock_y + 222),
       "Monday  ·  May 18, 2026",
       font=date_font, fill=GRAY + (220,))

# Greeting separator + status row (under clock)
sep_y = clock_y + 268
d.line([clock_x + 4, sep_y, clock_x + 720, sep_y], fill=BORDER + (220,), width=1)
# A few status pills below the clock
pill_y = sep_y + 18
def status_pill(x, dot_col, label, value):
    d.ellipse([x, pill_y + 4, x + 8, pill_y + 12], fill=dot_col + (255,))
    d.text((x + 16, pill_y), label,
           font=ImageFont.truetype(FONT_MONO, 11), fill=DIM + (255,))
    d.text((x + 16, pill_y + 16), value,
           font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))

status_pill(clock_x + 4,   OK,     "guardian",  "idle · ok")
status_pill(clock_x + 158, INDIGO, "vpn",        "wireguard · DE")
status_pill(clock_x + 314, PURPLE, "ai quota",   "8 / 500 today")
status_pill(clock_x + 478, WARN,   "updates",    "3 available")
status_pill(clock_x + 638, OK,     "scope",      "open · 1 target")

# ════════════════════════════════════════════════════════════════════════════
# RIGHT HALF: stacked widget column
# ════════════════════════════════════════════════════════════════════════════
RW_x0 = 1180
RW_x1 = W - 30
RW_y0 = 80
RW_w  = RW_x1 - RW_x0

# Widget helper
def widget(y0, h, title, content_fn, accent=PURPLE):
    box = Image.new("RGBA", (RW_w, h), BG_PANEL + (235,))
    canvas.alpha_composite(box, (RW_x0, y0))
    d.rounded_rectangle([RW_x0, y0, RW_x1, y0 + h], radius=12,
                        outline=BORDER + (255,), width=1)
    # Accent strip top-left corner (hex-tile-like)
    accent_tab = Image.new("RGBA", (60, 4), accent + (200,))
    canvas.alpha_composite(accent_tab.filter(ImageFilter.GaussianBlur(radius=1)),
                            (RW_x0 + 14, y0))
    # Header
    d.text((RW_x0 + 22, y0 + 14), title,
           font=ImageFont.truetype(FONT_BOLD, 10), fill=DARK + (255,))
    content_fn(RW_x0, y0, RW_x1, y0 + h)

# ── Widget 1: Today's activity (sparkline + 3 metrics) ──────────────────────
w_y = RW_y0
w_h = 168
def w_today(x0, y0, x1, y1):
    d.text((x0 + 22, y0 + 32),
           "TODAY",
           font=ImageFont.truetype(FONT_BOLD, 26), fill=WHITE + (255,))
    d.text((x0 + 22, y0 + 64),
           "since 00:00",
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    # Metrics row
    metrics = [
        ("Scans",    "12",  PURPLE),
        ("AI calls", "8",   INDIGO),
        ("CVEs",     "2",   WARN),
    ]
    mx = x0 + 22
    my = y0 + 100
    for label, val, col in metrics:
        d.text((mx, my), val,
               font=ImageFont.truetype(FONT_BOLD, 32), fill=col + (255,))
        d.text((mx, my + 38), label,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
        mx += 110
    # Sparkline on right
    sp_x = x1 - 220
    sp_y = y0 + 50
    sp_w = 198
    sp_h = 80
    rnd = random.Random(42)
    spark = [rnd.randint(8, 70) for _ in range(48)]
    pts = []
    for i, v in enumerate(spark):
        px = sp_x + i * sp_w / (len(spark) - 1)
        py = sp_y + sp_h - v
        pts.append((px, py))
    # Fill under
    poly = pts + [(sp_x + sp_w, sp_y + sp_h), (sp_x, sp_y + sp_h)]
    sp_fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sp_fill).polygon(poly, fill=PURPLE + (40,))
    canvas.alpha_composite(sp_fill)
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i+1]], fill=PURPLE + (230,), width=2)
    d.ellipse([pts[-1][0]-3, pts[-1][1]-3, pts[-1][0]+3, pts[-1][1]+3],
              fill=PURPLE + (255,))

widget(w_y, w_h, "TODAY", w_today, accent=PURPLE)

# ── Widget 2: Threat Feed ───────────────────────────────────────────────────
w_y += w_h + 14
w_h = 232
def w_feed(x0, y0, x1, y1):
    feed = [
        ("4m ago",  "CVE-2024-10443", "Synology DSM RCE on nas.local",        CRIT),
        ("32m ago", "CVE-2024-49113", "LDAP DoS exposure on ws-02",          WARN),
        ("2h ago",  "CVE-2024-43491", "Windows update server reachable",      WARN),
        ("4h ago",  "MISC",            "1 new device joined: iot-cam-01",      INDIGO),
        ("yest.",   "CVE-2024-38063", "TCP/IP IPv6 RCE — patched",           OK),
    ]
    fy = y0 + 38
    for ts, cve, body, col in feed:
        d.ellipse([x0 + 22, fy + 6, x0 + 30, fy + 14], fill=col + (255,))
        d.text((x0 + 40, fy), cve,
               font=ImageFont.truetype(FONT_MONO, 10), fill=col + (255,))
        d.text((x1 - 70, fy), ts,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
        d.text((x0 + 40, fy + 14), body,
               font=ImageFont.truetype(FONT_REG, 12), fill=WHITE + (255,))
        fy += 38
widget(w_y, w_h, "THREAT FEED", w_feed, accent=CRIT)

# ── Widget 3: Quick actions (hex grid 3x2) ──────────────────────────────────
w_y += w_h + 14
w_h = 178
def w_actions(x0, y0, x1, y1):
    actions = [
        ("◆", "ShadowCypher", PURPLE),
        ("⌖", "scan target",  INDIGO),
        ("☄", "exploit",       CRIT),
        ("",  "lock screen",  GRAY),
        ("⚙", "settings",      GRAY),
        ("🜂",  "switch mode",  WARN),
    ]
    hx0 = x0 + 30
    hy0 = y0 + 50
    hr = 28
    gap_x = hr * math.sqrt(3) + 18
    gap_y = hr * 1.5 + 28
    for i, (g, label, col) in enumerate(actions):
        cx = hx0 + (i % 3) * gap_x + hr
        cy = hy0 + (i // 3) * gap_y + hr
        pts = hex_pts(cx, cy, hr)
        # Filled if first one
        if i == 0:
            fill_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(fill_img).polygon(pts, fill=PURPLE + (40,))
            canvas.alpha_composite(fill_img)
            d.line(pts + [pts[0]], fill=PURPLE + (255,), width=2)
        else:
            d.line(pts + [pts[0]], fill=BORDER + (200,), width=1)
        bb = d.textbbox((0, 0), g, font=ImageFont.truetype(FONT_BOLD, 20))
        d.text((cx - (bb[2]-bb[0])/2, cy - (bb[3]-bb[1])/2 - 2 - bb[1]),
               g, font=ImageFont.truetype(FONT_BOLD, 20),
               fill=col + (255,))
        # Label below
        nb = d.textbbox((0, 0), label, font=ImageFont.truetype(FONT_MONO, 9))
        d.text((cx - (nb[2]-nb[0])/2, cy + hr + 4),
               label, font=ImageFont.truetype(FONT_MONO, 9),
               fill=GRAY + (255,))

widget(w_y, w_h, "QUICK ACTIONS", w_actions, accent=INDIGO)

# ── Widget 4: System pulse (CPU bar + RAM bar + Net) ────────────────────────
w_y += w_h + 14
w_h = 130
def w_pulse(x0, y0, x1, y1):
    # CPU bar
    d.text((x0 + 22, y0 + 36), "CPU",
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    d.text((x0 + 60, y0 + 32), "4%",
           font=ImageFont.truetype(FONT_BOLD, 14), fill=WHITE + (255,))
    bar_x = x0 + 110
    bar_w = x1 - x0 - 130
    d.rounded_rectangle([bar_x, y0 + 38, bar_x + bar_w, y0 + 44],
                        radius=3, fill=BG_HIGH + (255,))
    d.rounded_rectangle([bar_x, y0 + 38, bar_x + bar_w * 0.04, y0 + 44],
                        radius=3, fill=PURPLE + (255,))
    # RAM
    d.text((x0 + 22, y0 + 60), "RAM",
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    d.text((x0 + 60, y0 + 56), "1.1G",
           font=ImageFont.truetype(FONT_BOLD, 14), fill=WHITE + (255,))
    d.rounded_rectangle([bar_x, y0 + 62, bar_x + bar_w, y0 + 68],
                        radius=3, fill=BG_HIGH + (255,))
    d.rounded_rectangle([bar_x, y0 + 62, bar_x + bar_w * 0.07, y0 + 68],
                        radius=3, fill=INDIGO + (255,))
    # Net
    d.text((x0 + 22, y0 + 84), "NET",
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    d.text((x0 + 60, y0 + 80), "↑12 ↓8",
           font=ImageFont.truetype(FONT_MONO, 12), fill=WHITE + (255,))
    d.rounded_rectangle([bar_x, y0 + 86, bar_x + bar_w, y0 + 92],
                        radius=3, fill=BG_HIGH + (255,))
    d.rounded_rectangle([bar_x, y0 + 86, bar_x + bar_w * 0.02, y0 + 92],
                        radius=3, fill=BLUE + (255,))

widget(w_y, w_h, "SYSTEM PULSE", w_pulse, accent=INDIGO)

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM DOCK — with hex tile pattern hint behind icons
# ════════════════════════════════════════════════════════════════════════════
DOCK_H = 60
dock_y = H - DOCK_H
dock = Image.new("RGBA", (W, DOCK_H), (10, 8, 18, 248))
canvas.alpha_composite(dock, (0, dock_y))

# subtle hex pattern in dock
tex2 = Image.new("RGBA", (W, DOCK_H), (0, 0, 0, 0))
td2 = ImageDraw.Draw(tex2)
r2 = 14
dx = r2 * math.sqrt(3)
dy = r2 * 1.5
y_ = -r2
row = 0
while y_ < DOCK_H + r2:
    x_off = 0 if row % 2 == 0 else dx / 2
    x_ = -dx + x_off
    while x_ < W + dx:
        pts = hex_pts(x_, y_, r2)
        td2.line(pts + [pts[0]], fill=PURPLE + (24,), width=1)
        x_ += dx
    y_ += dy
    row += 1
canvas.alpha_composite(tex2, (0, dock_y))

# Top gradient strip on dock (matches top-bar)
grad2 = Image.new("RGBA", (W, 3), (0, 0, 0, 0))
gd2 = ImageDraw.Draw(grad2)
for x_ in range(W):
    t = x_ / W
    if t < 0.5:
        mix = t * 2
        r_, g_, b_ = (int(BLUE[i] + (PURPLE[i] - BLUE[i]) * mix) for i in range(3))
    else:
        mix = (t - 0.5) * 2
        r_, g_, b_ = (int(PURPLE[i] + (BLUE[i] - PURPLE[i]) * mix) for i in range(3))
    gd2.line([(x_, 0), (x_, 2)], fill=(r_, g_, b_, 130))
grad2 = grad2.filter(ImageFilter.GaussianBlur(radius=1.2))
canvas.alpha_composite(grad2, (0, dock_y - 2))

DOCK_ICONS = [
    ("◆",   PURPLE),
    ("",   GRAY),
    ("",   GRAY),
    ("",   GRAY),
    ("",   GRAY),
    ("",   GRAY),
    ("",   GRAY),
    ("",   GRAY),
    ("",   GRAY),
]
icon_size = 44
total_w = len(DOCK_ICONS) * (icon_size + 10) - 10
start_x = (W - total_w) // 2
for i, (g, c) in enumerate(DOCK_ICONS):
    ix = start_x + i * (icon_size + 10)
    iy = dock_y + (DOCK_H - icon_size) // 2 - 2
    d.rounded_rectangle([ix, iy, ix + icon_size, iy + icon_size],
                        radius=11, fill=BG_HIGH + (220,),
                        outline=BORDER + (200,), width=1)
    if g == "◆":
        cxd, cyd = ix + icon_size / 2, iy + icon_size / 2
        # subtle glow under the diamond
        gl = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
        ImageDraw.Draw(gl).polygon(
            [(icon_size/2, icon_size/2 - 14), (icon_size/2 + 12, icon_size/2),
             (icon_size/2, icon_size/2 + 14), (icon_size/2 - 12, icon_size/2)],
            fill=PURPLE + (90,))
        gl = gl.filter(ImageFilter.GaussianBlur(radius=4))
        canvas.alpha_composite(gl, (ix, iy))
        d.polygon([(cxd, cyd - 14), (cxd + 12, cyd), (cxd, cyd + 14), (cxd - 12, cyd)],
                   fill=PURPLE + (255,))
    else:
        d.text((ix + icon_size / 2 - 10, iy + 11), g,
               font=ImageFont.truetype(FONT_REG, 22), fill=c + (255,))

# Bottom-left: a properly designed mode chip (bigger + glow)
mp_x = 22
mp_y = dock_y + 16
# subtle glow
gl_m = Image.new("RGBA", (140, 32), (255, 170, 56, 70))
gl_m = gl_m.filter(ImageFilter.GaussianBlur(radius=8))
canvas.alpha_composite(gl_m, (mp_x - 6, mp_y - 4))
d.rounded_rectangle([mp_x, mp_y, mp_x + 128, mp_y + 28],
                    radius=14, fill=(255, 170, 56, 30),
                    outline=WARN + (220,), width=1)
d.ellipse([mp_x + 10, mp_y + 10, mp_x + 20, mp_y + 20], fill=WARN + (255,))
d.text((mp_x + 28, mp_y + 7), "pentest mode",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))

# Bottom-right: system info with little icons
sx = W - 220
sf = ImageFont.truetype(FONT_MONO, 10)
d.text((sx, dock_y + 14),
       "  4%       1.1/16G",
       font=sf, fill=GRAY + (255,))
d.text((sx, dock_y + 32),
       "  ↑12 KB/s  ↓8 KB/s",
       font=sf, fill=GRAY + (255,))

# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
