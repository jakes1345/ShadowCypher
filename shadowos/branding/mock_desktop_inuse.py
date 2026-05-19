#!/usr/bin/env python3
"""Realistic 'desktop in use' mock — like a screenshot of an actual session.

Shows:
  • Real ShadowOS wallpaper (one of our 20) visible through Hyprland gaps
  • 3 tiled windows: ShadowCypher app, browser, terminal
  • Top bar with threat-aware telemetry
  • Hex workspace switcher as overlay top-left
  • Bottom mode footer
  • A mako notification slide in from top-right
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-01-hex-teal-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-inuse.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1920, 1080
TEAL    = (0, 224, 164)
WHITE   = (230, 237, 243)
DIM     = (107, 119, 133)
DARK    = (61, 70, 81)
BG_DARK = (15, 20, 28)
BG_TBAR = (8, 11, 16)
BORDER  = (31, 42, 54)
WARN    = (255, 170, 56)
CRIT    = (255, 95, 110)

# Load real wallpaper
canvas = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
d = ImageDraw.Draw(canvas)

# ── TOP BAR — full width, threat-aware ───────────────────────────────────────
BAR_H = 38
top = Image.new("RGBA", (W, BAR_H), BG_TBAR + (220,))
canvas.alpha_composite(top, (0, 0))
d.rectangle([0, BAR_H, W, BAR_H + 1], fill=BORDER + (255,))

# Logo
def hex_pts(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]

d.polygon(hex_pts(28, BAR_H/2, 12), outline=TEAL + (255,), width=2)
d.text((22, BAR_H/2 - 9),
       "S", font=ImageFont.truetype(FONT_BOLD, 18), fill=WHITE + (255,))

# Telemetry items in bar
ft_lbl = ImageFont.truetype(FONT_MONO, 10)
ft_val = ImageFont.truetype(FONT_BOLD, 12)

def tele(x, lbl, val, col=TEAL):
    d.text((x, 6),  lbl, font=ft_lbl, fill=DIM + (255,))
    d.text((x, 19), val, font=ft_val, fill=col + (255,))

tele( 60, "PORTS",  "3",                TEAL)
tele(130, "CONNS",  "12 → 6",            WHITE)
tele(220, "TOR",    "● ● ●  US→DE→NL",   TEAL)
tele(400, "DNS",    "9.9.9.9  enc",      WHITE)
tele(540, "FP",     "0",                 TEAL)
tele(610, "THREAT", "LOW",               TEAL)

# Right side: clock, network, mode tag, tray
right_tray = [
    ("", DIM),     # bluetooth
    ("", DIM),     # wifi
    ("", DIM),     # battery
    ("", DIM),     # volume
]
tray_font = ImageFont.truetype(FONT_MONO, 14)
xr = W - 280
for ic, col in right_tray:
    d.text((xr, 12), ic, font=tray_font, fill=col + (255,))
    xr += 28

# Clock
d.text((W - 110, 6),
       "21:34", font=ImageFont.truetype(FONT_BOLD, 14), fill=WHITE + (255,))
d.text((W - 110, 22),
       "Mon · May 18", font=ImageFont.truetype(FONT_REG, 10), fill=DIM + (255,))

# Mode chip in bar (replaces "PENTEST" badge from before)
chip_x = W - 220
d.rounded_rectangle([chip_x, 7, chip_x + 80, 31],
                    radius=4, fill=(255, 170, 56, 35), outline=WARN + (220,), width=1)
d.text((chip_x + 13, 13),
       "PENTEST", font=ImageFont.truetype(FONT_BOLD, 10), fill=WARN + (255,))


# ── WAYBAR LEFT — narrow vertical strip with hex workspaces ─────────────────
LEFT_W = 56
strip = Image.new("RGBA", (LEFT_W, H - BAR_H), BG_TBAR + (200,))
canvas.alpha_composite(strip, (0, BAR_H))
d.rectangle([LEFT_W, BAR_H, LEFT_W + 1, H], fill=BORDER + (200,))

# 7 hex workspaces stacked vertically
ws_data = [
    ("RECON",   True,  TEAL),
    ("EXPLOIT", False, DIM),
    ("LOOT",    False, DIM),
    ("REPORT",  False, DIM),
    ("LAB",     False, DIM),
    ("CHAT",    False, DIM),
    ("BREAK",   False, DIM),
]
hex_r = 18
y0 = BAR_H + 50
spacing = 56
for i, (name, active, col) in enumerate(ws_data):
    cy = y0 + i * spacing
    cx = LEFT_W / 2
    pts = hex_pts(cx, cy, hex_r)
    if active:
        d.polygon(pts, fill=(0, 224, 164, 50), outline=TEAL + (255,), width=2)
        # Accent bar on the side indicating active workspace
        d.rectangle([0, cy - hex_r, 3, cy + hex_r], fill=TEAL + (255,))
        text_col = WHITE
        label_font = ImageFont.truetype(FONT_BOLD, 8)
    else:
        d.polygon(pts, outline=col + (180,), width=1)
        text_col = DIM
        label_font = ImageFont.truetype(FONT_BOLD, 8)
    # Workspace number 1-7
    d.text((cx - 4, cy - 6), str(i+1),
           font=ImageFont.truetype(FONT_BOLD, 13), fill=text_col + (255,))
    # Tiny label below the hex
    bb = d.textbbox((0, 0), name, font=label_font)
    tw = bb[2] - bb[0]
    d.text((cx - tw/2, cy + hex_r + 4), name,
           font=label_font, fill=DIM + (255,))


# ── window-shadow helper ─────────────────────────────────────────────────────
def window(box, title, color=BG_DARK, accent=TEAL):
    x0, y0, x1, y1 = box
    # Drop shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8],
                         radius=14, fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=14))
    canvas.alpha_composite(shadow)
    # Subtle teal border around active window
    d.rounded_rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1],
                        radius=11, outline=accent + (180,), width=2)
    # Window body — slightly transparent so wallpaper bleeds
    body = Image.new("RGBA", (x1 - x0, y1 - y0), color + (240,))
    canvas.alpha_composite(body, (x0, y0))
    # Title bar
    tb = Image.new("RGBA", (x1 - x0, 28), (24, 32, 44, 245))
    canvas.alpha_composite(tb, (x0, y0))
    # Traffic-light buttons
    d.ellipse([x0 + 12, y0 + 9, x0 + 22, y0 + 19], fill=CRIT)
    d.ellipse([x0 + 28, y0 + 9, x0 + 38, y0 + 19], fill=WARN)
    d.ellipse([x0 + 44, y0 + 9, x0 + 54, y0 + 19], fill=TEAL)
    # Title text
    d.text((x0 + 70, y0 + 9), title,
           font=ImageFont.truetype(FONT_MONO, 11), fill=DIM + (255,))


# ── Window 1: ShadowCypher GTK app (left half, full height-ish) ─────────────
SC_x0, SC_y0 = LEFT_W + 14, BAR_H + 12
SC_x1, SC_y1 = 850, H - 50
window((SC_x0, SC_y0, SC_x1, SC_y1), "ShadowCypher  ·  Spectral Intelligence")

# Mock the ShadowCypher app interior
# Left navigation
nav_x = SC_x0 + 8
nav_w = 180
d.rectangle([nav_x, SC_y0 + 32, nav_x + nav_w, SC_y1 - 4],
            fill=(11, 15, 22, 230))

nav_items = [
    ("⌂", "Central HUD",         False),
    ("⌖", "Spectral Intel",       True),
    ("☄", "Vulnerability Sweep", False),
    ("⊕", "Network Scanner",     False),
    ("◉", "OSINT Probe",          False),
    ("✺", "Combat Deck",          False),
    ("◈", "Payload Factory",     False),
    ("▣", "C2 Command",           False),
    ("💬", "Community Chat",      False),
    ("▤", "Forensic Audit",      False),
    ("⚙", "Hub Settings",         False),
]
nav_font = ImageFont.truetype(FONT_BOLD, 11)
icon_font = ImageFont.truetype(FONT_REG, 14)
yy = SC_y0 + 50
for icon, label, active in nav_items:
    if active:
        d.rectangle([nav_x, yy - 4, nav_x + nav_w, yy + 22],
                    fill=(0, 224, 164, 30))
        d.rectangle([nav_x, yy - 4, nav_x + 3, yy + 22], fill=TEAL)
        text_c = WHITE
    else:
        text_c = DIM
    d.text((nav_x + 14, yy - 1), icon, font=icon_font, fill=text_c + (255,))
    d.text((nav_x + 38, yy + 1), label, font=nav_font, fill=text_c + (255,))
    yy += 30

# Main content area (Spectral Intel)
main_x = nav_x + nav_w + 16
main_y = SC_y0 + 50
d.text((main_x, main_y),
       "SPECTRAL INTELLIGENCE",
       font=ImageFont.truetype(FONT_BOLD, 12), fill=TEAL + (255,))
d.text((main_x, main_y + 22),
       "OSINT aggregator  ·  192.168.1.0/24",
       font=ImageFont.truetype(FONT_BOLD, 18), fill=WHITE + (255,))

# Stat cards
stats = [
    ("DEVICES",   "8",   WHITE),
    ("INCIDENTS", "1",   CRIT),
    ("CVE ALERTS","3",   WARN),
    ("AI QUERIES","42",  TEAL),
]
sx = main_x
sy = main_y + 70
sw, sh = 130, 80
for label, val, col in stats:
    d.rounded_rectangle([sx, sy, sx + sw, sy + sh],
                        radius=8, fill=(15, 20, 28, 255), outline=BORDER + (200,), width=1)
    d.text((sx + 14, sy + 12), label,
           font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    d.text((sx + 14, sy + 30), val,
           font=ImageFont.truetype(FONT_BOLD, 28), fill=col + (255,))
    sx += sw + 8

# Recent incident card
inc_y = sy + sh + 24
d.rounded_rectangle([main_x, inc_y, main_x + 4*sw + 24, inc_y + 110],
                    radius=8, fill=(35, 12, 18, 220),
                    outline=CRIT + (180,), width=1)
d.rectangle([main_x, inc_y, main_x + 4, inc_y + 110], fill=CRIT)
d.text((main_x + 18, inc_y + 14),
       "ACTIVE INCIDENT  ·  CRITICAL",
       font=ImageFont.truetype(FONT_BOLD, 10), fill=CRIT + (255,))
d.text((main_x + 18, inc_y + 34),
       "CVE-2024-10443  ·  Synology DSM RCE",
       font=ImageFont.truetype(FONT_BOLD, 16), fill=WHITE + (255,))
d.text((main_x + 18, inc_y + 60),
       "Heap overflow in photo handler allows unauthenticated RCE.",
       font=ImageFont.truetype(FONT_REG, 12), fill=DIM + (255,))
d.text((main_x + 18, inc_y + 82),
       "Affected: 192.168.1.42 (nas.local)  ·  detected 4 min ago",
       font=ImageFont.truetype(FONT_MONO, 11), fill=DIM + (255,))


# ── Window 2: Firefox-ish browser (top right) ───────────────────────────────
B_x0 = 870
B_y0 = BAR_H + 12
B_x1 = W - 14
B_y1 = 580
window((B_x0, B_y0, B_x1, B_y1), "shadowcypher.site  —  Mozilla Firefox", accent=BORDER)

# URL bar
urlbar_y = B_y0 + 38
d.rounded_rectangle([B_x0 + 14, urlbar_y, B_x1 - 14, urlbar_y + 28],
                    radius=14, fill=(11, 15, 22, 255), outline=BORDER + (200,), width=1)
d.text((B_x0 + 30, urlbar_y + 7),
       "  shadowcypher.site/dashboard",
       font=ImageFont.truetype(FONT_MONO, 11), fill=DIM + (255,))

# Tab strip
d.text((B_x0 + 22, B_y0 + 76),
       "ShadowCypher Dashboard",
       font=ImageFont.truetype(FONT_BOLD, 14), fill=WHITE + (255,))

# Mock page content — a small dashboard chart
import random as _r
rnd = _r.Random(11)
chart_x0 = B_x0 + 22
chart_y0 = B_y0 + 110
chart_w  = B_x1 - B_x0 - 44
chart_h  = 220
d.rectangle([chart_x0, chart_y0, chart_x0 + chart_w, chart_y0 + chart_h],
            fill=(11, 15, 22, 240), outline=BORDER + (200,), width=1)
# fake line chart
pts = []
for i in range(40):
    x = chart_x0 + 20 + i * (chart_w - 40) / 39
    y = chart_y0 + chart_h - 30 - rnd.randint(20, chart_h - 60)
    pts.append((x, y))
for i in range(len(pts) - 1):
    d.line([pts[i], pts[i+1]], fill=TEAL + (220,), width=2)
# axis label
d.text((chart_x0 + 14, chart_y0 + 12),
       "INCIDENTS  ·  LAST  30  DAYS",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))

# bottom stat rows
ry = chart_y0 + chart_h + 18
for i, (k, v) in enumerate([("agents online", "3 / 4"),
                              ("scans today",   "27"),
                              ("AI calls",      "118 / 500")]):
    d.text((chart_x0 + i * 200, ry),
           k, font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    d.text((chart_x0 + i * 200, ry + 14),
           v, font=ImageFont.truetype(FONT_BOLD, 16), fill=WHITE + (255,))


# ── Window 3: Terminal (bottom right) ───────────────────────────────────────
T_x0 = 870
T_y0 = 595
T_x1 = W - 14
T_y1 = H - 50
window((T_x0, T_y0, T_x1, T_y1), "foot  —  shadow@nexus  ~/work", accent=BORDER)

term_lines = [
    ("$ shadow-mode status",                                              TEAL),
    ("  MODE: pentest",                                                   WARN),
    ("  Firewall: scan-open  ·  Tor: off  ·  MAC: original",              DIM),
    ("",                                                                   DIM),
    ("$ rustscan -a 192.168.1.0/24 -- -sC -sV",                           TEAL),
    ("Open 192.168.1.1:22    ssh",                                        WHITE),
    ("Open 192.168.1.1:443   nginx",                                      WHITE),
    ("Open 192.168.1.42:445  smb  (Samba 4.21.1)",                        WHITE),
    ("Open 192.168.1.42:5000 http (Synology DSM 7.2.2)  CVE-2024-10443",  CRIT),
    ("",                                                                   DIM),
    ("$ ▮",                                                                TEAL),
]
tf = ImageFont.truetype(FONT_MONO, 11)
ty = T_y0 + 40
for line, col in term_lines:
    d.text((T_x0 + 18, ty), line, font=tf, fill=col + (255,))
    ty += 17


# ── mako notification (slide-in top-right) ──────────────────────────────────
NOTIF_W = 320
NOTIF_H = 80
NX = W - NOTIF_W - 16
NY = BAR_H + 16
shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle(
    [NX - 6, NY - 6, NX + NOTIF_W + 6, NY + NOTIF_H + 6],
    radius=12, fill=(0, 0, 0, 130))
shadow = shadow.filter(ImageFilter.GaussianBlur(radius=12))
canvas.alpha_composite(shadow)

notif = Image.new("RGBA", (NOTIF_W, NOTIF_H), (15, 20, 28, 248))
ImageDraw.Draw(notif).rounded_rectangle([0, 0, NOTIF_W, NOTIF_H],
                                          radius=10, fill=(15, 20, 28, 245),
                                          outline=CRIT + (255,), width=2)
canvas.alpha_composite(notif, (NX, NY))
# Accent strip
d.rectangle([NX, NY, NX + 4, NY + NOTIF_H], fill=CRIT + (255,))
d.text((NX + 16, NY + 12),
       "Guardian", font=ImageFont.truetype(FONT_BOLD, 11), fill=CRIT + (255,))
d.text((NX + 16, NY + 28),
       "Critical incident detected",
       font=ImageFont.truetype(FONT_BOLD, 13), fill=WHITE + (255,))
d.text((NX + 16, NY + 48),
       "CVE-2024-10443 on nas.local  ·  4m ago",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))


# ── BOTTOM MODE FOOTER ───────────────────────────────────────────────────────
FOOT_H = 28
foot_y = H - FOOT_H
foot = Image.new("RGBA", (W, FOOT_H), BG_TBAR + (235,))
canvas.alpha_composite(foot, (0, foot_y))
d.rectangle([0, foot_y, W, foot_y + 1], fill=BORDER + (200,))

# Mode chip
d.rectangle([0, foot_y, 180, H], fill=(255, 170, 56, 30))
d.rectangle([0, foot_y, 3, H], fill=WARN)
d.text((16, foot_y + 7),
       "MODE", font=ImageFont.truetype(FONT_BOLD, 11), fill=WARN + (255,))
d.text((58, foot_y + 7),
       "PENTEST", font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))

# Status chips
sf = ImageFont.truetype(FONT_MONO, 10)
status_items = [
    ("nmap",  "running",   WARN),
    ("burp",  "listening", TEAL),
    ("tor",   "disabled",  DIM),
    ("vpn",   "disabled",  DIM),
    ("CPU",   "23%",       TEAL),
    ("MEM",   "4.2G",      TEAL),
]
x = 200
for name, val, col in status_items:
    d.text((x,      foot_y + 8), name, font=sf, fill=DIM + (255,))
    d.text((x + 32, foot_y + 8), val,  font=sf, fill=col + (255,))
    x += 130

# Right: hints
d.text((W - 280, foot_y + 8),
       "⌘K palette    ⌘M modes    ⌘? help",
       font=sf, fill=DIM + (255,))


# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
