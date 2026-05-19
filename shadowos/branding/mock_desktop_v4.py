#!/usr/bin/env python3
"""ShadowOS desktop mock — v4.

Real OS feel:
  • ShadowCypher is just ONE of several open apps, not the platform itself
  • Wallpaper dominates background
  • Top bar + bottom dock = OS chrome (custom but recognisable)
  • Super-key launcher overlay open in center → shows app grid + search +
    workspace thumbnails + quick actions

Palette stays v3: black + royal purple + electric indigo.
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-18-minimal-indigo-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-v4.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1920, 1080

# Palette
PURPLE    = (180, 74, 255)
PURPLE_DK = (130, 50, 200)
INDIGO    = (110, 96, 235)
WHITE     = (236, 234, 244)
GRAY      = (148, 142, 168)
DIM       = (108, 102, 130)
DARK      = (72, 66, 92)
BG_DEEP   = (8, 8, 14)
BG_PANEL  = (16, 14, 26)
BG_HIGH   = (28, 22, 44)
BORDER    = (40, 34, 58)
BORDER_LO = (28, 24, 42)
WARN      = (255, 170, 56)
CRIT      = (255, 80, 100)
OK        = (98, 220, 154)

# ── Load wallpaper + slight global dim because launcher is up ───────────────
canvas = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
d = ImageDraw.Draw(canvas)

# ════════════════════════════════════════════════════════════════════════════
# TOP BAR — slim OS-chrome (always visible)
# ════════════════════════════════════════════════════════════════════════════
TOPH = 32
top = Image.new("RGBA", (W, TOPH), (10, 8, 18, 240))
canvas.alpha_composite(top, (0, 0))
d.rectangle([0, TOPH, W, TOPH + 1], fill=BORDER + (220,))
# subtle purple glow under bar
glow = Image.new("RGBA", (W, 4), PURPLE + (60,))
glow = glow.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow, (0, TOPH))

# Activities button (left) — clicking this also opens launcher
d.rounded_rectangle([12, 6, 96, 26], radius=6, fill=(180, 74, 255, 32),
                    outline=PURPLE + (180,), width=1)
d.polygon([(22, 16), (28, 12), (34, 16), (28, 20)], fill=PURPLE + (255,))
d.text((42, 9), "Activities",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))

# Focused app indicator — what window the user is in right now
d.text((114, 9), "Firefox",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=GRAY + (255,))
d.text((164, 10), "—  shadowcypher.site",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DARK + (255,))

# Right side: workspace dots, mode, tray, clock
# Workspaces (5)
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

# Mode pip
mx = W - 270
d.ellipse([mx, 13, mx + 8, 21], fill=WARN + (255,))
d.text((mx + 13, 10), "pentest",
       font=ImageFont.truetype(FONT_REG, 11), fill=GRAY + (255,))

# Tray
tx = W - 180
for ic in ["", "", "", "", ""]:
    d.text((tx, 10), ic, font=ImageFont.truetype(FONT_REG, 13),
           fill=DIM + (255,))
    tx += 19

# Clock
d.text((W - 80, 10), "21:34",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))

# ════════════════════════════════════════════════════════════════════════════
# Background apps (visible behind launcher, slightly dimmed) — gives
# context that this is a real desktop with running windows
# ════════════════════════════════════════════════════════════════════════════
def thumb_window(box, title, content_render, dim_alpha=170):
    """Draw a window thumbnail (slightly dimmed since launcher is on top)."""
    x0, y0, x1, y1 = box
    body = Image.new("RGBA", (x1 - x0, y1 - y0), BG_PANEL + (252,))
    canvas.alpha_composite(body, (x0, y0))
    d.rounded_rectangle([x0, y0, x1, y1], radius=8,
                        outline=BORDER + (255,), width=1)
    # title bar
    tb = Image.new("RGBA", (x1 - x0 - 2, 26), BG_HIGH + (252,))
    canvas.alpha_composite(tb, (x0 + 1, y0 + 1))
    d.text((x0 + 12, y0 + 7), title,
           font=ImageFont.truetype(FONT_REG, 10), fill=DIM + (255,))
    # window controls (right)
    d.text((x1 - 16, y0 + 6), "×",
           font=ImageFont.truetype(FONT_REG, 12), fill=DARK + (255,))
    content_render(x0, y0 + 28, x1, y1)

# Firefox (top-left, focused)
def render_firefox(x0, y0, x1, y1):
    # URL bar
    d.rounded_rectangle([x0 + 12, y0 + 8, x1 - 12, y0 + 32], radius=12,
                        fill=(20, 16, 32, 255), outline=BORDER + (200,), width=1)
    d.text((x0 + 28, y0 + 14),
           "  shadowcypher.site/dashboard",
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    # mock content
    d.text((x0 + 14, y0 + 50),
           "Operations · Last 30 days",
           font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))
    # simple bars chart
    rnd = random.Random(11)
    bars_x = x0 + 14
    bars_y = y0 + 80
    bw = (x1 - x0 - 30) / 30
    for i in range(30):
        h = rnd.randint(8, 60)
        col = PURPLE if i in (4, 18, 27) else INDIGO
        d.rectangle([bars_x + i * bw, bars_y + 60 - h,
                     bars_x + (i + 1) * bw - 1, bars_y + 60],
                    fill=col + (200,))

thumb_window((14, TOPH + 14, 720, 510), "Firefox  —  ShadowCypher Dashboard",
             render_firefox)

# ShadowCypher app (top-right) — much smaller than v3, just one of many
def render_shadowcypher(x0, y0, x1, y1):
    d.text((x0 + 14, y0 + 8), "Spectral Intel",
           font=ImageFont.truetype(FONT_BOLD, 11), fill=PURPLE + (255,))
    d.text((x0 + 14, y0 + 24),
           "192.168.1.0/24 · 8 hosts · 1 critical",
           font=ImageFont.truetype(FONT_MONO, 9), fill=DIM + (255,))
    # KPI mini cards
    kpis = [("8", "devices", WHITE),
            ("1", "critical", CRIT),
            ("3", "CVEs", WARN)]
    cx_ = x0 + 14
    for v, l, c in kpis:
        d.rounded_rectangle([cx_, y0 + 48, cx_ + 90, y0 + 100],
                            radius=6, fill=(20, 16, 32, 255),
                            outline=BORDER + (200,), width=1)
        d.text((cx_ + 10, y0 + 54),
               v, font=ImageFont.truetype(FONT_BOLD, 24), fill=c + (255,))
        d.text((cx_ + 10, y0 + 80),
               l, font=ImageFont.truetype(FONT_MONO, 9), fill=DIM + (255,))
        cx_ += 96

thumb_window((735, TOPH + 14, 1190, 510),
             "ShadowCypher  —  Spectral Intel",
             render_shadowcypher)

# Terminal (bottom-left)
def render_term(x0, y0, x1, y1):
    lines = [
        ("$ shadow-mode status",                              PURPLE),
        ("  mode: pentest",                                    GRAY),
        ("",                                                    GRAY),
        ("$ rustscan -a 192.168.1.0/24",                       PURPLE),
        ("Open 192.168.1.1:22    ssh",                         WHITE),
        ("Open 192.168.1.42:445  smb",                         WHITE),
        ("Open 192.168.1.42:5000 http  DSM 7.2.2",             WARN),
        ("scan complete: 8 hosts",                             OK),
        ("$ ▮",                                                 PURPLE),
    ]
    ty = y0 + 12
    for ln, c in lines:
        d.text((x0 + 14, ty), ln,
               font=ImageFont.truetype(FONT_MONO, 10), fill=c + (255,))
        ty += 17

thumb_window((14, 520, 720, 1010), "Terminal  —  shadow@nexus",
             render_term)

# Thunar file manager (bottom-right)
def render_thunar(x0, y0, x1, y1):
    # Sidebar
    sidebar = Image.new("RGBA", (140, y1 - y0), (12, 10, 22, 255))
    canvas.alpha_composite(sidebar, (x0, y0))
    d.rectangle([x0 + 140, y0, x0 + 141, y1], fill=BORDER + (220,))
    side = ["Home", "Documents", "Downloads", "Findings", "Reports", "Scripts"]
    sy = y0 + 14
    for i, s in enumerate(side):
        col = WHITE if i == 3 else GRAY
        if i == 3:
            d.rectangle([x0, sy - 3, x0 + 140, sy + 18],
                        fill=(180, 74, 255, 26))
            d.rectangle([x0, sy - 3, x0 + 3, sy + 18], fill=PURPLE + (255,))
        d.text((x0 + 14, sy), s,
               font=ImageFont.truetype(FONT_REG, 11), fill=col + (255,))
        sy += 24
    # File grid (right side)
    grid_x = x0 + 154
    grid_y = y0 + 14
    files = [
        ("nmap-1.7.txt", WARN), ("scan-08.json", INDIGO),
        ("nas-cve.md",   CRIT), ("creds.txt",    WARN),
        ("targets.csv",  INDIGO), ("notes.org",  GRAY),
    ]
    for i, (name, col) in enumerate(files):
        col_i = i % 3
        row_i = i // 3
        gx = grid_x + col_i * 110
        gy = grid_y + row_i * 80
        d.rounded_rectangle([gx, gy, gx + 60, gy + 60],
                            radius=4, fill=BG_HIGH + (220,),
                            outline=BORDER + (200,), width=1)
        d.text((gx + 16, gy + 18), "",
               font=ImageFont.truetype(FONT_REG, 28), fill=col + (255,))
        d.text((gx - 10, gy + 64), name[:14],
               font=ImageFont.truetype(FONT_MONO, 9), fill=GRAY + (255,))

thumb_window((735, 520, 1906, 1010), "Files  —  ~/Findings",
             render_thunar)

# ── Global dim because launcher is on top ───────────────────────────────────
dimmer = Image.new("RGBA", (W, H), (0, 0, 0, 130))
canvas.alpha_composite(dimmer)
# Blur the underlying content slightly (faux Gaussian effect on whole image)
canvas_blur = canvas.filter(ImageFilter.GaussianBlur(radius=3))
canvas = canvas_blur
d = ImageDraw.Draw(canvas)

# ════════════════════════════════════════════════════════════════════════════
# LAUNCHER OVERLAY — opens when user presses Super
# Layout: search bar (top) + pinned hex apps grid (middle) + workspace
# thumbnails (bottom) + quick-action chips (right)
# ════════════════════════════════════════════════════════════════════════════
LX = W // 2
LY = H // 2

# Big translucent panel
PAL_W = 1280
PAL_H = 760
px = LX - PAL_W // 2
py = LY - PAL_H // 2

# Panel shadow
sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(sh).rounded_rectangle([px - 16, py - 16, px + PAL_W + 16, py + PAL_H + 16],
                                      radius=24, fill=(0, 0, 0, 180))
sh = sh.filter(ImageFilter.GaussianBlur(radius=24))
canvas.alpha_composite(sh)

# Glass panel
panel = Image.new("RGBA", (PAL_W, PAL_H), (16, 14, 26, 245))
canvas.alpha_composite(panel, (px, py))
# Subtle purple top edge
glow_top = Image.new("RGBA", (PAL_W, 3), PURPLE + (200,))
canvas.alpha_composite(glow_top.filter(ImageFilter.GaussianBlur(radius=2)), (px, py))
d.rounded_rectangle([px, py, px + PAL_W, py + PAL_H],
                    radius=20, outline=BORDER + (255,), width=1)

# ── Search bar at top of launcher ───────────────────────────────────────────
sb_y = py + 36
d.rounded_rectangle([px + 40, sb_y, px + PAL_W - 280, sb_y + 56],
                    radius=28, fill=(8, 6, 14, 255),
                    outline=BORDER + (220,), width=1)
d.text((px + 60, sb_y + 18),
       "", font=ImageFont.truetype(FONT_REG, 18), fill=PURPLE + (255,))
d.text((px + 92, sb_y + 14),
       "search apps · commands · files…",
       font=ImageFont.truetype(FONT_REG, 16), fill=DARK + (255,))
# Cmd-K hint on right
hint_x = px + PAL_W - 410
d.rounded_rectangle([hint_x, sb_y + 18, hint_x + 60, sb_y + 38],
                    radius=4, fill=BG_HIGH + (220,))
d.text((hint_x + 8, sb_y + 19),
       "Super+/",
       font=ImageFont.truetype(FONT_MONO, 11), fill=GRAY + (255,))

# Power / lock / settings (right of search)
quick_x = px + PAL_W - 250
quick_y = sb_y
quick_actions = [
    ("⏻", "power",    CRIT),
    ("🔒", "lock",    WARN),
    ("⚙",  "settings", PURPLE),
]
for i, (g, label, col) in enumerate(quick_actions):
    ax = quick_x + i * 76
    d.rounded_rectangle([ax, quick_y, ax + 60, quick_y + 56],
                        radius=10, fill=BG_HIGH + (220,),
                        outline=BORDER + (220,), width=1)
    d.text((ax + 20, quick_y + 8), g,
           font=ImageFont.truetype(FONT_BOLD, 22), fill=col + (255,))
    d.text((ax + 14, quick_y + 38), label,
           font=ImageFont.truetype(FONT_MONO, 9), fill=DIM + (255,))

# ── Section: All applications ───────────────────────────────────────────────
hdr_y = sb_y + 86
d.text((px + 50, hdr_y),
       "APPLICATIONS",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=DARK + (255,))
d.text((px + PAL_W - 200, hdr_y), "showing 24 · 87 installed",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))

# Hex grid of pinned apps
grid_y0 = hdr_y + 28
hex_r   = 52
cell_w  = hex_r * math.sqrt(3) + 30   # spacing
cell_h  = hex_r * 1.5 + 36
cols    = 7
rows    = 3
grid_w  = cols * cell_w
grid_x0 = px + (PAL_W - grid_w) // 2 + cell_w / 2

apps = [
    ("ShadowCypher", "◆",         PURPLE),
    ("Firefox",      "",         WARN),
    ("Foot",         "",         OK),
    ("VSCode",       "",         INDIGO),
    ("Files",        "",         GRAY),
    ("Discord",      "",         INDIGO),
    ("Signal",       "",         INDIGO),

    ("Steam",        "",         WARN),
    ("Heroic",       "♛",          PURPLE),
    ("Lutris",       "",         WARN),
    ("OBS",          "",         CRIT),
    ("GIMP",         "",         INDIGO),
    ("Blender",      "",         WARN),
    ("Krita",        "",         INDIGO),

    ("nmap",         "⌖",          PURPLE),
    ("Metasploit",   "☄",          CRIT),
    ("Wireshark",    "",         INDIGO),
    ("KeePassXC",    "",         WARN),
    ("Distrobox",    "",         GRAY),
    ("Docker",       "",         INDIGO),
    ("Settings",     "⚙",          GRAY),
]
font_app = ImageFont.truetype(FONT_BOLD, 11)
font_ico = ImageFont.truetype(FONT_BOLD, 28)
for i, (name, glyph, col) in enumerate(apps):
    row = i // cols
    col_i = i % cols
    cx = grid_x0 + col_i * cell_w
    cy = grid_y0 + row * cell_h + hex_r
    # Hex cell
    pts = [(cx + hex_r * math.cos(math.radians(60 * k - 30)),
            cy + hex_r * math.sin(math.radians(60 * k - 30))) for k in range(6)]
    # First app shown as "hovered" — purple ring
    if i == 0:
        # filled background
        f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(f).polygon(pts, fill=(180, 74, 255, 40))
        canvas.alpha_composite(f)
        d.line(pts + [pts[0]], fill=PURPLE + (255,), width=3)
    else:
        d.line(pts + [pts[0]], fill=BORDER + (180,), width=1)
    # Glyph
    bb = d.textbbox((0, 0), glyph, font=font_ico)
    iw = bb[2] - bb[0]
    ih = bb[3] - bb[1]
    d.text((cx - iw / 2 - bb[0], cy - ih / 2 - bb[1] - 4),
           glyph, font=font_ico, fill=col + (255,))
    # Name below hex
    nb = d.textbbox((0, 0), name, font=font_app)
    nw = nb[2] - nb[0]
    d.text((cx - nw / 2, cy + hex_r + 8),
           name, font=font_app, fill=(WHITE if i == 0 else GRAY) + (255,))

# ── Workspace thumbnails at bottom ──────────────────────────────────────────
ws_y = py + PAL_H - 130
d.text((px + 50, ws_y - 24),
       "WORKSPACES",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=DARK + (255,))

ws_thumb_w = 180
ws_thumb_h = 100
ws_spacing = 16
ws_total_w = 5 * ws_thumb_w + 4 * ws_spacing
ws_x0 = px + (PAL_W - ws_total_w) // 2
for i in range(5):
    tx = ws_x0 + i * (ws_thumb_w + ws_spacing)
    ty = ws_y
    if i == 0:
        # Active workspace — purple border, shows current desktop scaled down
        d.rounded_rectangle([tx, ty, tx + ws_thumb_w, ty + ws_thumb_h],
                            radius=6, fill=BG_PANEL + (255,),
                            outline=PURPLE + (255,), width=2)
        # Mini representations of windows on this workspace
        d.rounded_rectangle([tx + 8, ty + 8, tx + 84, ty + 56],
                            radius=2, fill=BG_HIGH + (255,))
        d.rounded_rectangle([tx + 92, ty + 8, tx + 168, ty + 56],
                            radius=2, fill=BG_HIGH + (255,))
        d.rounded_rectangle([tx + 8, ty + 60, tx + 84, ty + 92],
                            radius=2, fill=BG_HIGH + (255,))
        d.rounded_rectangle([tx + 92, ty + 60, tx + 168, ty + 92],
                            radius=2, fill=BG_HIGH + (255,))
        # Tiny purple bars showing focus
        d.rectangle([tx + 8, ty + 8, tx + 84, ty + 11], fill=PURPLE + (255,))
        d.text((tx + 8, ty + ws_thumb_h + 4),
               "1   Recon",
               font=ImageFont.truetype(FONT_BOLD, 10), fill=WHITE + (255,))
    else:
        d.rounded_rectangle([tx, ty, tx + ws_thumb_w, ty + ws_thumb_h],
                            radius=6, fill=BG_PANEL + (200,),
                            outline=BORDER + (200,), width=1)
        d.text((tx + 8, ty + 40),
               "empty",
               font=ImageFont.truetype(FONT_MONO, 11), fill=DARK + (255,))
        labels = ["2   Tools", "3   Web", "4   Comm", "5   Game"]
        d.text((tx + 8, ty + ws_thumb_h + 4),
               labels[i - 1],
               font=ImageFont.truetype(FONT_BOLD, 10), fill=GRAY + (255,))

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM DOCK (visible behind launcher, slightly dim)
# ════════════════════════════════════════════════════════════════════════════
DOCK_H = 56
dock_y = H - DOCK_H
dock = Image.new("RGBA", (W, DOCK_H), (10, 8, 18, 245))
canvas.alpha_composite(dock, (0, dock_y))
glow_top = Image.new("RGBA", (W, 4), PURPLE + (100,))
glow_top = glow_top.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow_top, (0, dock_y - 2))

DOCK_ICONS = [
    ("◆",   PURPLE, True),    # ShadowCypher running
    ("",   GRAY,   False),
    ("",   GRAY,   True),    # firefox running (focused)
    ("",   GRAY,   False),
    ("",   GRAY,   True),    # terminal running
    ("",   GRAY,   True),    # files running
    ("",   GRAY,   False),
    ("",   GRAY,   False),
    ("",   GRAY,   False),
]
icon_size = 40
total_w = len(DOCK_ICONS) * (icon_size + 10) - 10
start_x = (W - total_w) // 2
for i, (g, c, running) in enumerate(DOCK_ICONS):
    ix = start_x + i * (icon_size + 10)
    iy = dock_y + (DOCK_H - icon_size) // 2 - 2
    d.rounded_rectangle([ix, iy, ix + icon_size, iy + icon_size],
                        radius=10, fill=BG_HIGH + (200,),
                        outline=BORDER + (200,), width=1)
    if g == "◆":
        cxd, cyd = ix + icon_size/2, iy + icon_size/2
        d.polygon([(cxd, cyd - 12), (cxd + 10, cyd), (cxd, cyd + 12), (cxd - 10, cyd)],
                   fill=PURPLE + (255,))
    else:
        d.text((ix + icon_size/2 - 9, iy + 10), g,
               font=ImageFont.truetype(FONT_REG, 20), fill=c + (255,))
    if running:
        d.ellipse([ix + icon_size/2 - 2, iy + icon_size + 4,
                   ix + icon_size/2 + 2, iy + icon_size + 8],
                  fill=PURPLE + (255,))

# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
