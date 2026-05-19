#!/usr/bin/env python3
"""Mock a proposed ShadowOS custom desktop environment.

Renders a single PNG showing:
  • Top status bar with THREAT-AWARE telemetry (ports, conns, Tor, score)
  • Hex workspace grid (left edge) — workspaces labeled by mission
  • Command palette overlay (Cmd-K style) — primary launcher
  • Right slide-in context panel — current focus driven
  • Mode indicator bottom-left — colour theme adapts to mode
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent / "previews"
OUT.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1920, 1080

# Palette (current ShadowOS dark + teal)
BG_TOP    = (10, 13, 18)
BG_BOT    = (5, 8, 12)
PANEL     = (15, 20, 28)
PANEL_HI  = (24, 32, 44)
BORDER    = (31, 42, 54)
ACCENT    = (0, 224, 164)
ACCENT_DIM = (0, 110, 85)
WARN      = (255, 170, 56)
CRIT      = (255, 95, 110)
TEXT      = (230, 237, 243)
DIM       = (107, 119, 133)
DARK      = (61, 70, 81)

# ── helpers ───────────────────────────────────────────────────────────────────
def linear_gradient(w, h, top, bot):
    img = Image.new("RGB", (w, h), top)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img

def hex_pts(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]

def rounded_rect(d, box, fill=None, outline=None, width=1, radius=8):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

# ── base ──────────────────────────────────────────────────────────────────────
img = linear_gradient(W, H, BG_TOP, BG_BOT).convert("RGBA")
d = ImageDraw.Draw(img)

# Subtle hex grid backdrop
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(overlay)
r = 40
dx = r * math.sqrt(3)
dy = r * 1.5
y = -r
row = 0
while y < H + r:
    x_off = 0 if row % 2 == 0 else dx / 2
    x = -dx + x_off
    while x < W + dx:
        pts = hex_pts(x, y, r)
        od.line(pts + [pts[0]], fill=BORDER + (60,), width=1)
        x += dx
    y += dy
    row += 1
img.alpha_composite(overlay)

# ── TOP BAR: threat-aware ─────────────────────────────────────────────────────
BAR_H = 44
bar_y = 0
d.rectangle([0, 0, W, BAR_H], fill=(8, 11, 16, 230))
d.rectangle([0, BAR_H, W, BAR_H + 1], fill=BORDER)

# Logo
font_logo = ImageFont.truetype(FONT_BOLD, 22)
d.polygon(hex_pts(28, BAR_H/2, 14), outline=ACCENT, width=2)
d.text((22, BAR_H/2 - 11), "S", font=font_logo, fill=TEXT)

# Live telemetry — what's NOVEL
font_tele = ImageFont.truetype(FONT_MONO, 13)
font_tele_b = ImageFont.truetype(FONT_BOLD, 13)

def telemetry(x, label, val, color=ACCENT):
    d.text((x, 9),  label, font=font_tele,   fill=DIM + (255,))
    d.text((x, 24), val,   font=font_tele_b, fill=color + (255,))

telemetry( 70, "OPEN  PORTS",   "3",                 ACCENT)
telemetry(170, "ACTIVE  CONNS", "12 → 6 hosts",      TEXT)
telemetry(330, "TOR  CIRCUIT",  "● ● ● US→DE→NL",    ACCENT)
telemetry(510, "DNS",           "9.9.9.9  encrypted", TEXT)
telemetry(680, "FINGERPRINTS",  "0 detected",        ACCENT)
telemetry(840, "MODE",          "PENTEST",           WARN)
telemetry(970, "THREAT",        "LOW",               ACCENT)

# Right side: clock + workspace context
clock_font = ImageFont.truetype(FONT_BOLD, 18)
mode_font  = ImageFont.truetype(FONT_REG, 12)
d.text((W - 110, 12), "21:34", font=clock_font, fill=TEXT)
d.text((W - 110, 31), "Mon · May 18", font=mode_font, fill=DIM)

# Tray icons (mock)
tray_font = ImageFont.truetype(FONT_MONO, 16)
for i, glyph in enumerate(["", "", "", "", "↑"]):
    d.text((W - 260 + i * 28, 14), glyph, font=tray_font, fill=DIM)

# ── LEFT: HEX WORKSPACE GRID — the signature element ─────────────────────────
hex_panel_x = 0
hex_panel_w = 160
d.rectangle([hex_panel_x, BAR_H + 1, hex_panel_x + hex_panel_w, H], fill=(10, 14, 20, 200))
d.rectangle([hex_panel_w, BAR_H + 1, hex_panel_w + 1, H], fill=BORDER)

font_ws = ImageFont.truetype(FONT_BOLD, 13)
font_ws_s = ImageFont.truetype(FONT_REG, 10)

# Hex workspace layout — 7 hexes in a flower pattern
HEX_R = 36
center_x = hex_panel_x + hex_panel_w / 2
center_y = 280

workspaces = [
    ("RECON",   center_x,                 center_y,              True,  ACCENT),
    ("EXPLOIT", center_x + HEX_R*1.732,    center_y - HEX_R*1.5, False, ACCENT_DIM),
    ("LOOT",    center_x + HEX_R*1.732,    center_y + HEX_R*1.5, False, ACCENT_DIM),
    ("REPORT",  center_x - HEX_R*1.732,    center_y - HEX_R*1.5, False, ACCENT_DIM),
    ("LAB",     center_x - HEX_R*1.732,    center_y + HEX_R*1.5, False, ACCENT_DIM),
    ("CHAT",    center_x,                  center_y - HEX_R*3,    False, ACCENT_DIM),
    ("BREAK",   center_x,                  center_y + HEX_R*3,    False, ACCENT_DIM),
]

# Title
title = ImageFont.truetype(FONT_BOLD, 11)
d.text((hex_panel_x + 14, BAR_H + 24), "WORKSPACES", font=title, fill=DIM)
d.line([hex_panel_x + 14, BAR_H + 44, hex_panel_x + hex_panel_w - 14, BAR_H + 44],
       fill=BORDER, width=1)

for name, cx, cy, active, col in workspaces:
    pts = hex_pts(cx, cy, HEX_R)
    if active:
        # Filled active hex
        d.polygon(pts, fill=(0, 224, 164, 40), outline=col + (255,), width=3)
    else:
        d.polygon(pts, outline=col + (220,), width=1)
    bb = d.textbbox((0, 0), name, font=font_ws)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw/2, cy - th/2 - 2), name,
           font=font_ws if active else font_ws_s, fill=TEXT if active else DIM)

# Active workspace label below
d.text((hex_panel_x + 14, center_y + HEX_R*4 + 20),
       "192.168.1.0/24", font=font_ws_s, fill=DIM)
d.text((hex_panel_x + 14, center_y + HEX_R*4 + 36),
       "3 hosts found", font=font_ws_s, fill=ACCENT)

# ── CENTER STAGE: terminal + map + command palette ──────────────────────────
content_x = hex_panel_w + 16
content_w = 1180
content_y = BAR_H + 16

# Window 1: foot terminal with running nmap
term_h = 380
term_box = [content_x, content_y, content_x + content_w, content_y + term_h]
rounded_rect(d, term_box, fill=PANEL + (255,), outline=BORDER, radius=10)
# Title bar
d.rectangle([content_x, content_y, content_x + content_w, content_y + 30],
            fill=PANEL_HI)
d.ellipse([content_x + 14, content_y + 10, content_x + 24, content_y + 20], fill=CRIT)
d.ellipse([content_x + 30, content_y + 10, content_x + 40, content_y + 20], fill=WARN)
d.ellipse([content_x + 46, content_y + 10, content_x + 56, content_y + 20], fill=ACCENT)
tit = ImageFont.truetype(FONT_MONO, 11)
d.text((content_x + 70, content_y + 10), "shadow@nexus  ─  ~/work/192.168.1.0  ─  nmap -sC -sV",
       font=tit, fill=DIM)

# Terminal contents
ft = ImageFont.truetype(FONT_MONO, 12)
term_lines = [
    ("$ nmap -sC -sV 192.168.1.0/24",                                   ACCENT),
    ("Starting Nmap 7.95 ( https://nmap.org )",                         DIM),
    ("Nmap scan report for router.local (192.168.1.1)",                 TEXT),
    ("Host is up (0.0012s latency).",                                    DIM),
    ("Not shown: 998 closed tcp ports",                                  DIM),
    ("PORT    STATE SERVICE VERSION",                                    DIM),
    ("22/tcp  open  ssh     OpenSSH 9.6 (protocol 2.0)",                ACCENT),
    ("443/tcp open  https   nginx 1.27.3",                              ACCENT),
    ("",                                                                 DIM),
    ("Nmap scan report for nas.local (192.168.1.42)",                   TEXT),
    ("PORT     STATE SERVICE  VERSION",                                  DIM),
    ("445/tcp  open  smb     Samba smbd 4.21.1",                        ACCENT),
    ("5000/tcp open  http    Synology DSM 7.2.2",                       WARN),
    ("│  └─ CVE-2024-10443  CRITICAL  RCE in DSM ≤ 7.2.2.81",          CRIT),
    ("",                                                                 DIM),
    ("$ ▮",                                                              ACCENT),
]
for i, (line, c) in enumerate(term_lines):
    d.text((content_x + 18, content_y + 44 + i * 18), line, font=ft, fill=c + (255,))

# Window 2: live network graph (bottom)
graph_y = content_y + term_h + 16
graph_h = H - graph_y - 70
graph_box = [content_x, graph_y, content_x + 580, graph_y + graph_h]
rounded_rect(d, graph_box, fill=PANEL + (255,), outline=BORDER, radius=10)
d.text((content_x + 18, graph_y + 14), "NETWORK MAP  ·  192.168.1.0/24",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=DIM)

# Draw a simple graph of nodes
import random
rnd = random.Random(7)
gx0 = content_x + 30
gy0 = graph_y + 50
gw  = 540
gh  = graph_h - 70
nodes = []
labels = ["router", "ws-01", "ws-02", "nas", "iot-cam", "tv", "pi", "voip"]
for i, lbl in enumerate(labels):
    nx = gx0 + rnd.randint(20, gw - 20)
    ny = gy0 + rnd.randint(20, gh - 20)
    nodes.append((nx, ny, lbl))

# Edges
for i, (x1, y1, _) in enumerate(nodes[1:], 1):
    rx, ry, _ = nodes[0]
    d.line([(x1, y1), (rx, ry)], fill=BORDER + (200,), width=1)

# Nodes
for nx, ny, lbl in nodes:
    is_router = lbl == "router"
    is_threat = lbl == "nas"
    color = ACCENT if not is_threat else CRIT
    r_ = 9 if is_router else (8 if is_threat else 6)
    d.ellipse([nx - r_, ny - r_, nx + r_, ny + r_], fill=color, outline=TEXT, width=1)
    lf = ImageFont.truetype(FONT_MONO, 10)
    d.text((nx + 12, ny - 6), lbl, font=lf, fill=DIM)

# Window 3: file/git panel (right of graph)
fp_x = content_x + 600
fp_y = graph_y
fp_box = [fp_x, fp_y, content_x + content_w, graph_y + graph_h]
rounded_rect(d, fp_box, fill=PANEL + (255,), outline=BORDER, radius=10)
d.text((fp_x + 18, fp_y + 14), "CONTEXT  ·  cve-2024-10443.md",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=DIM)
notes = [
    "# Synology DSM RCE",
    "",
    "Affected: DSM ≤ 7.2.2.81",
    "Auth required: no",
    "Exploit: heap overflow in",
    "         photo handler",
    "",
    "Mitigation: upgrade to 7.2.2.82",
    "",
    "Targets in scope:",
    "  ☑  192.168.1.42 (nas)",
]
nf = ImageFont.truetype(FONT_MONO, 12)
for i, ln in enumerate(notes):
    color = ACCENT if ln.startswith("#") else (TEXT if not ln.startswith(" ") else DIM)
    d.text((fp_x + 18, fp_y + 46 + i * 18), ln, font=nf, fill=color + (255,))

# ── COMMAND PALETTE (centered, overlay) — the primary launcher ──────────────
PAL_W = 720
PAL_H = 340
px0 = (W - PAL_W) // 2
py0 = 200
# Backdrop dim behind palette
pal_blur = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(pal_blur).rectangle([px0 - 40, py0 - 40, px0 + PAL_W + 40, py0 + PAL_H + 40],
                                    fill=(0, 0, 0, 110))
pal_blur = pal_blur.filter(ImageFilter.GaussianBlur(radius=30))
img.alpha_composite(pal_blur)

# Palette panel
rounded_rect(d, [px0, py0, px0 + PAL_W, py0 + PAL_H],
             fill=(15, 20, 28, 245), outline=ACCENT + (255,), width=2, radius=14)
# Search input
ip_font = ImageFont.truetype(FONT_REG, 22)
d.text((px0 + 28, py0 + 22), "›", font=ImageFont.truetype(FONT_BOLD, 26), fill=ACCENT)
d.text((px0 + 60, py0 + 26), "scan", font=ip_font, fill=TEXT)
# cursor
d.rectangle([px0 + 60 + 64, py0 + 28, px0 + 60 + 66, py0 + 56], fill=ACCENT)
# Hint
hint_f = ImageFont.truetype(FONT_REG, 12)
d.text((px0 + PAL_W - 130, py0 + 32), "press ↵ to run",
       font=hint_f, fill=DIM)
# Divider
d.line([px0 + 16, py0 + 72, px0 + PAL_W - 16, py0 + 72], fill=BORDER, width=1)

# Results
res_font = ImageFont.truetype(FONT_BOLD, 14)
sub_font = ImageFont.truetype(FONT_MONO, 11)
results = [
    ("nmap",           "scan ports of a target — nmap -sC -sV {target}",  True,  ""),
    ("rustscan",       "ultra-fast port discovery — rustscan -a {target}", False, ""),
    ("ffuf",           "fuzz web paths — ffuf -u https://{target}/FUZZ",   False, ""),
    ("scan workspace", "switch to RECON workspace",                       False, "WS"),
    ("scan history",   "show last 12 scans + their findings",             False, ""),
    ("scan agent",     "trigger Guardian-agent scan on all endpoints",    False, "AI"),
]
for i, (cmd, desc, sel, tag) in enumerate(results):
    ry = py0 + 86 + i * 38
    if sel:
        rounded_rect(d, [px0 + 12, ry - 4, px0 + PAL_W - 12, ry + 30],
                     fill=(0, 224, 164, 22), radius=6)
        d.rectangle([px0 + 12, ry - 4, px0 + 15, ry + 30], fill=ACCENT)
    d.text((px0 + 30, ry + 1), cmd, font=res_font, fill=TEXT if sel else DIM)
    d.text((px0 + 30, ry + 18), desc, font=sub_font, fill=DIM)
    if tag:
        tw = d.textbbox((0, 0), tag, font=sub_font)
        ww = tw[2] - tw[0]
        rounded_rect(d, [px0 + PAL_W - 60 - ww, ry + 8, px0 + PAL_W - 30, ry + 26],
                     fill=PANEL_HI + (255,), outline=BORDER, radius=4)
        d.text((px0 + PAL_W - 55 - ww + 5, ry + 9), tag,
               font=sub_font, fill=ACCENT_DIM + (255,))

# ── Bottom: mode-driven status footer ────────────────────────────────────────
FOOT_H = 28
foot_y = H - FOOT_H
d.rectangle([0, foot_y, W, H], fill=(8, 11, 16, 240))
d.rectangle([0, foot_y, W, foot_y + 1], fill=BORDER)

# Mode chip
mode_box_w = 200
d.rectangle([0, foot_y, mode_box_w, H], fill=(255, 170, 56, 30))
d.rectangle([0, foot_y, 4, H], fill=WARN)
mf = ImageFont.truetype(FONT_BOLD, 12)
d.text((16, foot_y + 7), "MODE", font=mf, fill=WARN)
d.text((60, foot_y + 7), "PENTEST", font=mf, fill=TEXT)

# Status chips
sf = ImageFont.truetype(FONT_MONO, 11)
status_items = [
    ("nmap", "running",  WARN),
    ("burp", "listening", ACCENT),
    ("tor",  "disabled",  DIM),
    ("vpn",  "disabled",  DIM),
]
x = mode_box_w + 24
for name, val, col in status_items:
    d.text((x, foot_y + 8), f"{name}", font=sf, fill=DIM)
    d.text((x + 38, foot_y + 8), val, font=sf, fill=col)
    x += 130

# Right: hints
d.text((W - 260, foot_y + 8), "⌘K  palette    ⌘M  modes    ⌘?  help",
       font=sf, fill=DIM)

# ── Save ─────────────────────────────────────────────────────────────────────
out = OUT / "mock-custom-de.png"
img.convert("RGB").save(out, "PNG", optimize=True)
print(f"wrote {out}  ({out.stat().st_size//1024} KB)")
