#!/usr/bin/env python3
"""ShadowOS desktop — v8.

No-XFCE redesign:
  • Hex-tile dock (icons in hexagons, not rounded squares)
  • Asymmetric widget layout (varying sizes, intentional placement,
    not a stack-of-cards grid)
  • Diagonal accent line crossing the wallpaper
  • Mode chip stays as-is (user liked it)
  • Greeting + clock + chip framed around the wallpaper's S monogram
  • Vertical SHADOWOS wordmark on left edge as a layered element
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-01-hex-teal-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-v8.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_LIGHT= "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf"

W, H = 1920, 1080

PURPLE    = (180, 74, 255)
PURPLE_DK = (130, 50, 200)
INDIGO    = (110, 96, 235)
BLUE      = (88, 124, 255)
WHITE     = (236, 234, 244)
GRAY      = (148, 142, 168)
DIM       = (108, 102, 130)
DARK      = (72, 66, 92)
BG_DEEP   = (8, 8, 14)
BG_PANEL  = (16, 14, 26)
BG_PANEL2 = (12, 10, 22)
BG_HIGH   = (28, 22, 44)
BORDER    = (40, 34, 58)
WARN      = (255, 170, 56)
CRIT      = (255, 80, 100)
OK        = (98, 220, 154)

# ── Wallpaper tinted toward purple ──────────────────────────────────────────
wp = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
try:
    import numpy as np
    arr = np.array(wp, dtype=np.int16)
    arr[..., 0] = np.clip(arr[..., 0] + 8,  0, 255)
    arr[..., 2] = np.clip(arr[..., 2] + 14, 0, 255)
    arr[..., 1] = np.clip(arr[..., 1] - 6,  0, 255)
    canvas = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
except ImportError:
    canvas = wp.copy()

# Darken slightly
canvas.alpha_composite(Image.new("RGBA", (W, H), (5, 4, 10, 60)))

def hex_pts(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]

# ── Diagonal accent stripe across wallpaper ─────────────────────────────────
stripe = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(stripe)
# Two diagonal lines forming a thin band
sd.polygon([(0, 200), (W, -250), (W, -240), (0, 210)], fill=PURPLE + (60,))
sd.polygon([(0, 870), (W, 1220), (W, 1230), (0, 880)], fill=BLUE + (50,))
stripe = stripe.filter(ImageFilter.GaussianBlur(radius=1))
canvas.alpha_composite(stripe)

d = ImageDraw.Draw(canvas)

# ════════════════════════════════════════════════════════════════════════════
# TOP BAR — hex texture + gradient strip
# ════════════════════════════════════════════════════════════════════════════
TOPH = 36
top = Image.new("RGBA", (W, TOPH), (10, 8, 18, 248))
canvas.alpha_composite(top, (0, 0))

# Hex texture
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

d.rectangle([0, TOPH, W, TOPH + 1], fill=BORDER + (255,))
grad = Image.new("RGBA", (W, 3), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
for x_ in range(W):
    t = x_ / W
    if t < 0.5:
        mix = t * 2
        col = tuple(int(BLUE[i] + (PURPLE[i] - BLUE[i]) * mix) for i in range(3))
    else:
        mix = (t - 0.5) * 2
        col = tuple(int(PURPLE[i] + (BLUE[i] - PURPLE[i]) * mix) for i in range(3))
    gd.line([(x_, 0), (x_, 2)], fill=col + (130,))
grad = grad.filter(ImageFilter.GaussianBlur(radius=1.2))
canvas.alpha_composite(grad, (0, TOPH))

# Diamond + name
d.polygon([(22, 12), (32, 18), (22, 24), (12, 18)], fill=PURPLE + (255,))
d.text((40, 11), "ShadowOS",
       font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))
d.text((128, 12), "press Super to open",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))

# Right cluster
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

mx = W - 270
d.ellipse([mx, 14, mx + 8, 22], fill=WARN + (255,))
d.text((mx + 13, 11), "pentest",
       font=ImageFont.truetype(FONT_REG, 11), fill=GRAY + (255,))

tx = W - 180
for ic in ["", "", "", "", ""]:
    d.text((tx, 11), ic, font=ImageFont.truetype(FONT_REG, 13),
           fill=DIM + (255,))
    tx += 19

d.text((W - 80, 11), "21:34",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))

# ════════════════════════════════════════════════════════════════════════════
# VERTICAL "SHADOWOS" WORDMARK — left edge, big and layered (decorative)
# ════════════════════════════════════════════════════════════════════════════
vt_font = ImageFont.truetype(FONT_BOLD, 120)
vt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
vd = ImageDraw.Draw(vt_layer)
# Render text horizontally, then rotate -90
text_img = Image.new("RGBA", (1200, 200), (0, 0, 0, 0))
td_ = ImageDraw.Draw(text_img)
td_.text((0, 0), "SHADOWOS",
         font=vt_font, fill=WHITE + (38,))
text_img = text_img.rotate(90, expand=True, resample=Image.BICUBIC)
canvas.alpha_composite(text_img, (-15, 100))

# ════════════════════════════════════════════════════════════════════════════
# CENTER-LEFT: greeting + clock anchored to wallpaper's S monogram
# ════════════════════════════════════════════════════════════════════════════
# Greeting line
greet_y = 200
d.text((220, greet_y),
       "Good evening, jack",
       font=ImageFont.truetype(FONT_LIGHT, 40), fill=WHITE + (240,))
d.text((220, greet_y + 54),
       "you are operating in",
       font=ImageFont.truetype(FONT_REG, 14), fill=GRAY + (255,))

# Chip (user liked this — kept identical)
chip_x = 220
chip_y = greet_y + 80
# glow halo
gl_m = Image.new("RGBA", (200, 50), (255, 170, 56, 85))
gl_m = gl_m.filter(ImageFilter.GaussianBlur(radius=12))
canvas.alpha_composite(gl_m, (chip_x - 8, chip_y - 6))
d.rounded_rectangle([chip_x, chip_y, chip_x + 188, chip_y + 42],
                    radius=20, fill=(255, 170, 56, 38),
                    outline=WARN + (255,), width=2)
d.ellipse([chip_x + 14, chip_y + 12, chip_x + 30, chip_y + 28],
          fill=WARN + (255,))
d.text((chip_x + 40, chip_y + 8), "PENTEST",
       font=ImageFont.truetype(FONT_BOLD, 18), fill=WHITE + (255,))
d.text((chip_x + 40, chip_y + 28), "mode",
       font=ImageFont.truetype(FONT_MONO, 9), fill=WARN + (255,))

# Big clock — offset slightly to NOT obscure the wallpaper S, framed instead
clock_font = ImageFont.truetype(FONT_LIGHT, 220)
clock_str = "21:34"
bb = d.textbbox((0, 0), clock_str, font=clock_font)
clock_w = bb[2] - bb[0]
clock_x = 220
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
d.text((clock_x + 8, clock_y + 222),
       "Monday  ·  May 18, 2026",
       font=ImageFont.truetype(FONT_REG, 22), fill=GRAY + (220,))

# Small horizontal accent under date
acc = Image.new("RGBA", (180, 2), PURPLE + (220,))
acc = acc.filter(ImageFilter.GaussianBlur(radius=0.6))
canvas.alpha_composite(acc, (clock_x + 8, clock_y + 260))

# Status pills under date (more inline)
pill_y = clock_y + 280
def status_pill(x, dot_col, label, value):
    d.ellipse([x, pill_y + 4, x + 8, pill_y + 12], fill=dot_col + (255,))
    d.text((x + 16, pill_y - 2), label,
           font=ImageFont.truetype(FONT_MONO, 11), fill=DIM + (255,))
    d.text((x + 16, pill_y + 14), value,
           font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))
status_pill(clock_x + 8,   OK,     "guardian",  "idle · ok")
status_pill(clock_x + 158, INDIGO, "vpn",        "wireguard · DE")
status_pill(clock_x + 314, PURPLE, "ai",         "8 / 500 today")
status_pill(clock_x + 468, WARN,   "updates",    "3 available")

# ════════════════════════════════════════════════════════════════════════════
# ASYMMETRIC WIDGET LAYOUT — right side
# Big TODAY top (wider), Threat Feed mid (narrower), Quick actions hex grid
# bottom-right (small), Pulse strip on right edge (tall thin)
# ════════════════════════════════════════════════════════════════════════════

def hex_widget(x0, y0, x1, y1, title, content_fn, accent=PURPLE):
    """Widget with hex-cut top-right corner — angular, non-XFCE feel."""
    # Construct polygon body that has a cut corner
    cut = 28
    pts = [(x0, y0),
           (x1 - cut, y0),
           (x1, y0 + cut),
           (x1, y1),
           (x0, y1)]
    # Shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh_pts = [(p[0]+4, p[1]+4) for p in pts]
    ImageDraw.Draw(sh).polygon(sh_pts, fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=14))
    canvas.alpha_composite(sh)
    # Body
    body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(body).polygon(pts, fill=BG_PANEL + (244,))
    canvas.alpha_composite(body)
    # Outline
    d.line(pts + [pts[0]], fill=BORDER + (255,), width=1)
    # Accent diagonal piece on the cut corner
    d.line([(x1 - cut, y0), (x1, y0 + cut)], fill=accent + (220,), width=2)
    # Title
    d.text((x0 + 20, y0 + 12), title,
           font=ImageFont.truetype(FONT_BOLD, 10), fill=DARK + (255,))
    content_fn(x0, y0, x1, y1)

# ── Widget 1: TODAY (top right, wide) ──────────────────────────────────────
TX0 = 1180
TX1 = W - 28
TY0 = 86
TY1 = 290
def w_today(x0, y0, x1, y1):
    d.text((x0 + 20, y0 + 36),
           "TODAY",
           font=ImageFont.truetype(FONT_BOLD, 32), fill=WHITE + (255,))
    d.text((x0 + 20, y0 + 76),
           "since 00:00",
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    # 3 KPI
    metrics = [
        ("12", "Scans",    PURPLE),
        ("8",  "AI calls", INDIGO),
        ("2",  "CVEs",     WARN),
    ]
    mx_ = x0 + 20
    my_ = y0 + 116
    for v, l, c in metrics:
        d.text((mx_, my_), v,
               font=ImageFont.truetype(FONT_BOLD, 36), fill=c + (255,))
        d.text((mx_, my_ + 44), l,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
        mx_ += 100
    # Sparkline right
    sp_x = x1 - 280
    sp_y = y0 + 60
    sp_w = 250
    sp_h = 100
    rnd = random.Random(42)
    spark = [rnd.randint(8, 90) for _ in range(56)]
    pts_ = []
    for i, v in enumerate(spark):
        px = sp_x + i * sp_w / (len(spark) - 1)
        py = sp_y + sp_h - v
        pts_.append((px, py))
    poly = pts_ + [(sp_x + sp_w, sp_y + sp_h), (sp_x, sp_y + sp_h)]
    sp_fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sp_fill).polygon(poly, fill=PURPLE + (50,))
    canvas.alpha_composite(sp_fill)
    for i in range(len(pts_) - 1):
        d.line([pts_[i], pts_[i+1]], fill=PURPLE + (240,), width=2)
    d.ellipse([pts_[-1][0]-4, pts_[-1][1]-4, pts_[-1][0]+4, pts_[-1][1]+4],
              fill=PURPLE + (255,))

hex_widget(TX0, TY0, TX1, TY1, "TODAY", w_today, accent=PURPLE)

# ── Widget 2: Threat Feed (mid right, slightly narrower) ────────────────────
FX0 = 1240
FX1 = W - 28
FY0 = 312
FY1 = 612
def w_feed(x0, y0, x1, y1):
    feed = [
        ("4m ago",  "CVE-2024-10443", "Synology DSM RCE on nas.local",  CRIT),
        ("32m ago", "CVE-2024-49113", "LDAP DoS on ws-02",              WARN),
        ("2h ago",  "CVE-2024-43491", "Win-update server reachable",    WARN),
        ("4h ago",  "MISC",           "new device: iot-cam-01",         INDIGO),
        ("yest.",   "CVE-2024-38063", "TCP/IP IPv6 RCE — patched",      OK),
        ("yest.",   "GH-EVT",         "shadowcypher push to main",      PURPLE),
    ]
    fy = y0 + 40
    for ts, cve, body, col in feed:
        d.ellipse([x0 + 20, fy + 6, x0 + 28, fy + 14], fill=col + (255,))
        d.text((x0 + 38, fy), cve,
               font=ImageFont.truetype(FONT_MONO, 10), fill=col + (255,))
        d.text((x1 - 80, fy), ts,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
        d.text((x0 + 38, fy + 14), body,
               font=ImageFont.truetype(FONT_REG, 12), fill=WHITE + (255,))
        fy += 38
hex_widget(FX0, FY0, FX1, FY1, "THREAT FEED", w_feed, accent=CRIT)

# ── Widget 3: Quick actions HEX GRID (bottom right, square-ish) ─────────────
QX0 = 1400
QX1 = W - 28
QY0 = 634
QY1 = 916
def w_actions(x0, y0, x1, y1):
    actions = [
        ("◆", "ShadowCypher", PURPLE),
        ("⌖", "scan target",  INDIGO),
        ("☄", "exploit",       CRIT),
        ("",  "lock",         GRAY),
        ("⚙", "settings",      GRAY),
        ("🜂",  "switch mode",  WARN),
    ]
    hx0 = x0 + 32
    hy0 = y0 + 50
    hr = 32
    gap_x = hr * math.sqrt(3) + 14
    gap_y = hr * 1.5 + 32
    for i, (g, label, col) in enumerate(actions):
        cx = hx0 + (i % 3) * gap_x + hr
        cy = hy0 + (i // 3) * gap_y + hr
        pts = hex_pts(cx, cy, hr)
        if i == 0:
            f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(f).polygon(pts, fill=PURPLE + (50,))
            canvas.alpha_composite(f)
            d.line(pts + [pts[0]], fill=PURPLE + (255,), width=2)
        else:
            d.line(pts + [pts[0]], fill=BORDER + (220,), width=1)
        bb_ = d.textbbox((0, 0), g, font=ImageFont.truetype(FONT_BOLD, 22))
        d.text((cx - (bb_[2]-bb_[0])/2 - bb_[0],
                cy - (bb_[3]-bb_[1])/2 - bb_[1] - 4),
               g, font=ImageFont.truetype(FONT_BOLD, 22), fill=col + (255,))
        nb = d.textbbox((0, 0), label, font=ImageFont.truetype(FONT_MONO, 9))
        d.text((cx - (nb[2]-nb[0])/2, cy + hr + 6),
               label, font=ImageFont.truetype(FONT_MONO, 9), fill=GRAY + (255,))
hex_widget(QX0, QY0, QX1, QY1, "QUICK ACTIONS", w_actions, accent=INDIGO)

# ── Widget 4: PULSE — narrow vertical strip on the right edge of widgets ────
PX0 = 1180
PX1 = 1380
PY0 = 634
PY1 = 916
def w_pulse(x0, y0, x1, y1):
    items = [
        ("CPU",    "4%",     0.04, PURPLE),
        ("RAM",    "1.1G",   0.07, INDIGO),
        ("DISK",   "204G",   0.43, INDIGO),
        ("NET ↑",  "12K",    0.02, BLUE),
        ("NET ↓",  "8K",     0.01, BLUE),
        ("TEMP",   "47°",    0.39, OK),
    ]
    py_ = y0 + 36
    for label, val, frac, col in items:
        d.text((x0 + 20, py_), label,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
        d.text((x1 - 60, py_ - 1), val,
               font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))
        # bar
        bar_x = x0 + 20
        bar_w = x1 - x0 - 40
        d.rounded_rectangle([bar_x, py_ + 16, bar_x + bar_w, py_ + 20],
                            radius=2, fill=BG_HIGH + (255,))
        d.rounded_rectangle([bar_x, py_ + 16, bar_x + bar_w * frac, py_ + 20],
                            radius=2, fill=col + (255,))
        py_ += 40

hex_widget(PX0, PY0, PX1, PY1, "PULSE", w_pulse, accent=BLUE)

# ════════════════════════════════════════════════════════════════════════════
# HEX DOCK — bottom, icons in hexagonal tiles, NOT rounded squares
# ════════════════════════════════════════════════════════════════════════════
DOCK_H = 100
dock_y0 = H - DOCK_H
# Dock background: faint hex-textured band with sloped sides

# Compute dock width — only as wide as needed for icons
HEX_ICONS = [
    ("◆",   PURPLE,  True),   # ShadowCypher (running)
    ("",   GRAY,    False),  # files
    ("",   GRAY,    False),  # firefox
    ("",   GRAY,    False),  # vscode
    ("",   GRAY,    False),  # terminal
    ("",   GRAY,    False),  # helix
    ("",   GRAY,    False),  # discord
    ("",   GRAY,    False),  # steam
    ("",   GRAY,    False),  # tools
]
hr = 32
hspacing = hr * math.sqrt(3) + 10
dock_inner_w = int(len(HEX_ICONS) * hspacing)
dock_total_w = dock_inner_w + 100
dock_x0 = (W - dock_total_w) // 2
dock_x1 = dock_x0 + dock_total_w

# Sloped dock background (hex-band shape)
dock_pts = [
    (dock_x0,        dock_y0 + 30),
    (dock_x0 + 30,   dock_y0),
    (dock_x1 - 30,   dock_y0),
    (dock_x1,        dock_y0 + 30),
    (dock_x1,        H),
    (dock_x0,        H),
]
# Shadow
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(sh).polygon([(p[0], p[1] + 4) for p in dock_pts],
                             fill=(0, 0, 0, 160))
sh = sh.filter(ImageFilter.GaussianBlur(radius=16))
canvas.alpha_composite(sh)
# Body
body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(body).polygon(dock_pts, fill=(10, 8, 18, 250))
canvas.alpha_composite(body)
# Outline (top edge with gradient stroke)
d.line([(dock_x0, dock_y0 + 30), (dock_x0 + 30, dock_y0)],
       fill=PURPLE + (220,), width=2)
d.line([(dock_x0 + 30, dock_y0), (dock_x1 - 30, dock_y0)],
       fill=PURPLE + (200,), width=2)
d.line([(dock_x1 - 30, dock_y0), (dock_x1, dock_y0 + 30)],
       fill=BLUE + (220,), width=2)

# Hex texture inside dock
texd = Image.new("RGBA", (dock_total_w, DOCK_H), (0, 0, 0, 0))
td_ = ImageDraw.Draw(texd)
r2 = 16
dx2 = r2 * math.sqrt(3)
dy2 = r2 * 1.5
y2_ = -r2
row2 = 0
while y2_ < DOCK_H + r2:
    x_off2 = 0 if row2 % 2 == 0 else dx2 / 2
    x2_ = -dx2 + x_off2
    while x2_ < dock_total_w + dx2:
        pts2 = hex_pts(x2_, y2_, r2)
        td_.line(pts2 + [pts2[0]], fill=PURPLE + (28,), width=1)
        x2_ += dx2
    y2_ += dy2
    row2 += 1
# Mask texture to dock shape
mask = Image.new("L", (W, H), 0)
ImageDraw.Draw(mask).polygon(dock_pts, fill=255)
tex_full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
tex_full.paste(texd, (dock_x0, dock_y0), texd)
tex_full.putalpha(mask)
canvas.alpha_composite(tex_full)

# Icons inside dock — HEXAGONS not rounded squares
icon_y = dock_y0 + 50
start_x = dock_x0 + 50 + hr
for i, (g, c, running) in enumerate(HEX_ICONS):
    cx = start_x + i * hspacing
    cy = icon_y
    pts = hex_pts(cx, cy, hr)
    if i == 0:
        # ShadowCypher — filled purple background hex
        f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(f).polygon(pts, fill=PURPLE + (60,))
        canvas.alpha_composite(f)
        # Glow halo
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(gl).polygon(pts, fill=PURPLE + (140,))
        gl = gl.filter(ImageFilter.GaussianBlur(radius=10))
        canvas.alpha_composite(gl)
        d.line(pts + [pts[0]], fill=PURPLE + (255,), width=2)
    else:
        d.line(pts + [pts[0]], fill=BORDER + (220,), width=1)

    if g == "◆":
        d.polygon([(cx, cy - 14), (cx + 12, cy), (cx, cy + 14), (cx - 12, cy)],
                   fill=PURPLE + (255,))
    else:
        bb = d.textbbox((0, 0), g, font=ImageFont.truetype(FONT_REG, 22))
        d.text((cx - (bb[2]-bb[0])/2 - bb[0],
                cy - (bb[3]-bb[1])/2 - bb[1]),
               g, font=ImageFont.truetype(FONT_REG, 22), fill=c + (255,))
    if running:
        d.ellipse([cx - 2, cy + hr + 10, cx + 2, cy + hr + 14],
                  fill=PURPLE + (255,))

# Bottom-left mode chip (same designed style — user liked it)
mp_x = 22
mp_y = dock_y0 + 36
gl_m = Image.new("RGBA", (140, 32), (255, 170, 56, 70))
gl_m = gl_m.filter(ImageFilter.GaussianBlur(radius=8))
canvas.alpha_composite(gl_m, (mp_x - 6, mp_y - 4))
d.rounded_rectangle([mp_x, mp_y, mp_x + 128, mp_y + 28],
                    radius=14, fill=(255, 170, 56, 30),
                    outline=WARN + (220,), width=1)
d.ellipse([mp_x + 10, mp_y + 10, mp_x + 20, mp_y + 20], fill=WARN + (255,))
d.text((mp_x + 28, mp_y + 7), "pentest mode",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))

# Bottom-right system info
sx = W - 220
sf = ImageFont.truetype(FONT_MONO, 10)
d.text((sx, dock_y0 + 34),
       "  4%       1.1/16G",
       font=sf, fill=GRAY + (255,))
d.text((sx, dock_y0 + 52),
       "  ↑12 KB/s  ↓8 KB/s",
       font=sf, fill=GRAY + (255,))

# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
