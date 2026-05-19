#!/usr/bin/env python3
"""ShadowOS desktop mock — v2.

Less HUD/AR-glasses, more enterprise security platform (CrowdStrike Falcon /
Splunk vibe). Solid opaque panels, normal taskbar, dense app interiors,
minimal floating chrome.
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
# Use the minimal-teal variant — less busy hex bg
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-16-minimal-teal-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-v2.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1920, 1080
# Palette — keeping ShadowOS teal but everything more grounded
TEAL    = (0, 224, 164)
TEAL_DK = (0, 155, 114)
WHITE   = (235, 240, 245)
DIM     = (130, 140, 152)
DARK    = (85, 92, 102)
PANEL   = (18, 22, 30)
PANEL_LO= (12, 16, 22)
PANEL_HI= (28, 34, 44)
BORDER  = (38, 46, 58)
ACCENT2 = (88, 124, 255)   # secondary blue for charts
WARN    = (255, 170, 56)
CRIT    = (255, 95, 110)
OK      = (88, 220, 138)

canvas = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
# Darken wallpaper slightly so panels stand out cleanly
dimmer = Image.new("RGBA", (W, H), (0, 0, 0, 80))
canvas.alpha_composite(dimmer)
d = ImageDraw.Draw(canvas)

# ════════════════════════════════════════════════════════════════════════════
# TOP MENU BAR — thin, opaque, traditional (like macOS or KDE)
# ════════════════════════════════════════════════════════════════════════════
TOPH = 28
top = Image.new("RGBA", (W, TOPH), PANEL_LO + (252,))
canvas.alpha_composite(top, (0, 0))
d.rectangle([0, TOPH, W, TOPH + 1], fill=BORDER + (255,))

# App menu (left)
appmenu_font = ImageFont.truetype(FONT_BOLD, 11)
sub_font     = ImageFont.truetype(FONT_REG, 11)

# Logo + active app name
d.text((14, 7), "◆",
       font=ImageFont.truetype(FONT_BOLD, 14), fill=TEAL + (255,))
d.text((32, 8), "ShadowCypher",
       font=appmenu_font, fill=WHITE + (255,))
items = ["File", "Edit", "View", "Scan", "Tools", "Window", "Help"]
mx = 142
for it in items:
    d.text((mx, 8), it, font=sub_font, fill=DIM + (255,))
    mx += len(it) * 7 + 16

# Right side: workspace dots, mode pip, system tray, clock
# Workspace dots (5)
wx = W - 360
for i in range(5):
    cx = wx + i * 14
    if i == 0:
        d.ellipse([cx - 3, 11, cx + 3, 17], fill=TEAL + (255,))
    else:
        d.ellipse([cx - 2, 12, cx + 2, 16], fill=DIM + (180,))

# Mode pip (just a colored dot + label)
mode_x = W - 270
d.ellipse([mode_x, 11, mode_x + 7, 18], fill=WARN + (255,))
d.text((mode_x + 12, 8), "pentest",
       font=sub_font, fill=DIM + (255,))

# Tray icons
tray_font = ImageFont.truetype(FONT_REG, 13)
tray_x = W - 170
for ic in ["", "", "", "", ""]:
    d.text((tray_x, 7), ic, font=tray_font, fill=DIM + (255,))
    tray_x += 18

# Clock
d.text((W - 70, 7), "21:34",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))

# ════════════════════════════════════════════════════════════════════════════
# Helper: window with normal title bar
# ════════════════════════════════════════════════════════════════════════════
def window(box, title, focus=False):
    x0, y0, x1, y1 = box
    # subtle shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 - 4, y0 - 2, x1 + 4, y1 + 6],
                                          radius=10, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=10))
    canvas.alpha_composite(sh)
    # body
    body = Image.new("RGBA", (x1 - x0, y1 - y0), PANEL + (255,))
    canvas.alpha_composite(body, (x0, y0))
    # outline (subtle, no glow)
    d.rounded_rectangle([x0, y0, x1, y1], radius=8,
                        outline=(BORDER if not focus else (60, 75, 92)) + (255,), width=1)
    # title bar
    tb = Image.new("RGBA", (x1 - x0 - 2, 30), PANEL_HI + (255,))
    canvas.alpha_composite(tb, (x0 + 1, y0 + 1))
    # decoration: title text only — no traffic-light buttons (they go on the right)
    d.text((x0 + 14, y0 + 9), title,
           font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))
    # window controls right side
    cx = x1 - 14
    for col in [(85, 92, 102), (85, 92, 102), (85, 92, 102)]:
        d.text((cx, y0 + 8), "×" if col == (85, 92, 102) else "·",
               font=ImageFont.truetype(FONT_REG, 13), fill=col + (255,))
        cx -= 16


# ════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW: ShadowCypher Falcon-style dashboard (left 62%)
# ════════════════════════════════════════════════════════════════════════════
SC_x0, SC_y0 = 14, TOPH + 14
SC_x1, SC_y1 = 1200, H - 78
window((SC_x0, SC_y0, SC_x1, SC_y1), "ShadowCypher — Spectral Intelligence", focus=True)

# Inner layout: left nav (180) + content
NAV_W = 200
nav_x0 = SC_x0 + 1
nav_y0 = SC_y0 + 32
nav_box = Image.new("RGBA", (NAV_W, SC_y1 - nav_y0 - 1), PANEL_LO + (255,))
canvas.alpha_composite(nav_box, (nav_x0, nav_y0))
d.rectangle([nav_x0 + NAV_W, nav_y0, nav_x0 + NAV_W + 1, SC_y1 - 1],
            fill=BORDER + (255,))

# Nav header
d.text((nav_x0 + 16, nav_y0 + 14),
       "OPERATIONS",
       font=ImageFont.truetype(FONT_BOLD, 10),
       fill=DARK + (255,))

# Nav items (cleaner, less icon-y)
nav = [
    ("Dashboard",       False, None),
    ("Spectral Intel",   True,  None),
    ("Vulnerabilities",  False, "3"),
    ("Devices",          False, "8"),
    ("Network Scanner",  False, None),
    ("Combat Deck",      False, None),
    ("Payloads",         False, None),
    ("C2 Operations",    False, None),
    ("Community",        False, "12"),
    ("Audit Log",        False, None),
    ("Settings",         False, None),
]
ny = nav_y0 + 46
for label, active, badge in nav:
    if active:
        d.rectangle([nav_x0, ny - 4, nav_x0 + NAV_W, ny + 24],
                    fill=(0, 224, 164, 18))
        d.rectangle([nav_x0, ny - 4, nav_x0 + 3, ny + 24], fill=TEAL + (255,))
        color = WHITE
    else:
        color = DIM
    d.text((nav_x0 + 20, ny),
           label, font=ImageFont.truetype(FONT_REG, 12),
           fill=color + (255,))
    if badge:
        bb = d.textbbox((0, 0), badge, font=ImageFont.truetype(FONT_BOLD, 10))
        bw = bb[2] - bb[0] + 12
        d.rounded_rectangle([nav_x0 + NAV_W - bw - 14, ny + 2,
                              nav_x0 + NAV_W - 14,    ny + 18],
                             radius=8, fill=(60, 35, 40, 255),
                             outline=CRIT + (200,), width=1)
        d.text((nav_x0 + NAV_W - bw - 8, ny + 3),
               badge, font=ImageFont.truetype(FONT_BOLD, 10),
               fill=CRIT + (255,))
    ny += 30

# Content area
CT_x0 = nav_x0 + NAV_W + 1
CT_y0 = nav_y0
CT_x1 = SC_x1 - 1
CT_y1 = SC_y1 - 1

# Toolbar above content
d.text((CT_x0 + 24, CT_y0 + 16),
       "Network Intelligence",
       font=ImageFont.truetype(FONT_BOLD, 18), fill=WHITE + (255,))
d.text((CT_x0 + 24, CT_y0 + 42),
       "Subnet 192.168.1.0/24  ·  last scan 4 min ago  ·  3 hosts found",
       font=ImageFont.truetype(FONT_REG, 12), fill=DIM + (255,))

# Stat ribbon (4 KPI cards)
ribbon_y = CT_y0 + 78
cards = [
    ("Total devices",      "8",       None,      WHITE),
    ("Open incidents",     "1",       "+1 today", CRIT),
    ("CVE alerts",         "3",       "2 high",  WARN),
    ("Last scan",          "4m",      "in progress", TEAL),
]
cw = (CT_x1 - CT_x0 - 64) / 4 - 4
cx = CT_x0 + 24
for label, val, sub, col in cards:
    d.rounded_rectangle([cx, ribbon_y, cx + cw, ribbon_y + 88],
                        radius=6, fill=PANEL_LO + (255,),
                        outline=BORDER + (255,), width=1)
    d.text((cx + 16, ribbon_y + 14),
           label.upper(), font=ImageFont.truetype(FONT_MONO, 10),
           fill=DIM + (255,))
    d.text((cx + 16, ribbon_y + 30),
           val, font=ImageFont.truetype(FONT_BOLD, 32), fill=col + (255,))
    if sub:
        d.text((cx + 16, ribbon_y + 66),
               sub, font=ImageFont.truetype(FONT_MONO, 10),
               fill=DIM + (255,))
    cx += cw + 8

# Hosts table — the meat of the view (Falcon-style)
table_y = ribbon_y + 110
d.text((CT_x0 + 24, table_y),
       "DISCOVERED HOSTS",
       font=ImageFont.truetype(FONT_BOLD, 11),
       fill=DARK + (255,))

# Table header
headers = ["IP", "HOSTNAME", "OS", "PORTS", "RISK", "STATUS"]
col_widths = [120, 180, 200, 130, 100, 100]
header_y = table_y + 24
hx = CT_x0 + 24
for hdr, w in zip(headers, col_widths):
    d.text((hx, header_y),
           hdr, font=ImageFont.truetype(FONT_MONO, 10),
           fill=DARK + (255,))
    hx += w
d.line([CT_x0 + 24, header_y + 18, CT_x1 - 24, header_y + 18],
       fill=BORDER + (255,), width=1)

rows = [
    ("192.168.1.1",  "router.local",  "OpenWRT 23.05",                "22, 443",          "Low",      "Online", WHITE,   OK),
    ("192.168.1.42", "nas.local",     "Synology DSM 7.2.2",           "445, 5000",        "Critical", "Vulnerable", WHITE, CRIT),
    ("192.168.1.55", "ws-laptop",     "Arch Linux 6.13",              "22",               "Low",      "Online", WHITE,   OK),
    ("192.168.1.66", "tv.local",      "WebOS 23",                     "8080, 9080",       "Medium",   "Online", WHITE,   WARN),
    ("192.168.1.71", "iot-cam-01",    "Unknown",                      "80, 554, 8554",    "Medium",   "Online", WHITE,   WARN),
    ("192.168.1.99", "voip.local",    "Linphone 5.3",                 "5060, 5061",       "Low",      "Online", WHITE,   OK),
    ("192.168.1.100","pi.local",      "Debian 12",                    "22, 80",           "Low",      "Online", WHITE,   OK),
    ("192.168.1.221","ws-02",         "Windows 11 22H2",              "135, 445, 3389",   "Medium",   "Online", WHITE,   WARN),
]
ry = header_y + 28
for cells in rows:
    ip, hn, osv, ports, risk, status, text_c, status_c = cells
    # row hover style for the first one
    if ip == "192.168.1.42":
        d.rectangle([CT_x0 + 14, ry - 4, CT_x1 - 14, ry + 22],
                    fill=(255, 95, 110, 16))
    vx = CT_x0 + 24
    cells_text = [(ip, WHITE), (hn, WHITE), (osv, DIM), (ports, DIM)]
    risk_color = {"Low": DIM, "Medium": WARN, "Critical": CRIT}.get(risk, DIM)
    cells_text += [(risk, risk_color), (status, status_c)]
    for (t, c), w in zip(cells_text, col_widths):
        d.text((vx, ry), t,
               font=ImageFont.truetype(FONT_MONO, 11),
               fill=c + (255,))
        vx += w
    ry += 30

# ════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN: terminal + chat panel
# ════════════════════════════════════════════════════════════════════════════
RC_x0 = SC_x1 + 14
RC_x1 = W - 14
RC_w  = RC_x1 - RC_x0

# Top: foot terminal
T_y0 = TOPH + 14
T_y1 = 540
window((RC_x0, T_y0, RC_x1, T_y1), "foot — shadow@nexus")

term = [
    ("$ shadow-mode status",                                                  TEAL),
    ("  mode: pentest    firewall: scan-open",                                DIM),
    ("",                                                                       DIM),
    ("$ rustscan -a 192.168.1.0/24 -- -sC -sV",                              TEAL),
    ("Open 192.168.1.1:22    ssh   OpenSSH 9.6",                              WHITE),
    ("Open 192.168.1.1:443   nginx 1.27.3",                                   WHITE),
    ("Open 192.168.1.42:445  smb   Samba 4.21.1",                             WHITE),
    ("Open 192.168.1.42:5000 http  Synology DSM 7.2.2",                       WARN),
    ("                                  ┗ CVE-2024-10443 critical",          CRIT),
    ("Open 192.168.1.66:8080 http  WebOS 23",                                 WHITE),
    ("Open 192.168.1.100:80  http  nginx 1.27.3",                             WHITE),
    ("",                                                                       DIM),
    ("scan complete: 8 hosts, 13 ports, 1 critical CVE",                     OK),
    ("",                                                                       DIM),
    ("$ shadow scan agent --target 192.168.1.42 --module cve-2024-10443",   TEAL),
    ("queued mission #4421 for guardian agent 'nexus-gateway'",              DIM),
    ("",                                                                       DIM),
    ("$ ▮",                                                                    TEAL),
]
tf = ImageFont.truetype(FONT_MONO, 11)
ty = T_y0 + 42
for line, col in term:
    d.text((RC_x0 + 16, ty), line, font=tf, fill=col + (255,))
    ty += 17

# Bottom right: community chat panel
C_y0 = 555
C_y1 = H - 78
window((RC_x0, C_y0, RC_x1, C_y1), "ShadowCypher — Community Chat")

# Chat room indicator
d.text((RC_x0 + 16, C_y0 + 42), "#global",
       font=ImageFont.truetype(FONT_BOLD, 14), fill=WHITE + (255,))
d.text((RC_x0 + 90, C_y0 + 44),
       "12 online",
       font=ImageFont.truetype(FONT_MONO, 10), fill=OK + (255,))

# Mock messages
msgs = [
    ("alex",   "(00, 200, 140)", "anyone else seeing the CVE-2024-10443 thing in the wild?", "21:18"),
    ("ria",    "(255, 170, 56)", "yeah we found one on a synology nas this morning",         "21:21"),
    ("jamie",  "(88, 124, 255)", "patch came out 2 days ago — most people aren't on it",     "21:23"),
    ("alex",   "(0, 200, 140)",  "what's the exploit reliability?",                          "21:24"),
    ("ria",    "(255, 170, 56)", "high — guardian fired immediately on a 7.2.2.81 host",     "21:30"),
    ("you",    "(0, 224, 164)",  "queueing a guardian mission for nas.local right now",      "21:33"),
]
my = C_y0 + 76
for nick, _, body, ts in msgs:
    colmap = {"alex": (0, 200, 140), "ria": (255, 170, 56),
              "jamie": (88, 124, 255), "you": (0, 224, 164)}
    nick_c = colmap[nick] + (255,)
    # avatar bubble
    d.ellipse([RC_x0 + 16, my, RC_x0 + 38, my + 22], fill=nick_c)
    d.text((RC_x0 + 24, my + 4), nick[0].upper(),
           font=ImageFont.truetype(FONT_BOLD, 11), fill=PANEL + (255,))
    # nick + ts
    d.text((RC_x0 + 50, my + 1), nick,
           font=ImageFont.truetype(FONT_BOLD, 11), fill=nick_c)
    d.text((RC_x0 + 50 + len(nick)*7 + 8, my + 3), ts,
           font=ImageFont.truetype(FONT_MONO, 9), fill=DARK + (255,))
    # message
    d.text((RC_x0 + 50, my + 18), body,
           font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))
    my += 42

# Input pill at bottom
inp_y = C_y1 - 44
d.rounded_rectangle([RC_x0 + 14, inp_y, RC_x1 - 14, inp_y + 28],
                    radius=14, fill=PANEL_LO + (255,),
                    outline=BORDER + (255,), width=1)
d.text((RC_x0 + 28, inp_y + 7),
       "message #global…", font=ImageFont.truetype(FONT_REG, 11),
       fill=DARK + (255,))

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM DOCK — taskbar with pinned apps
# ════════════════════════════════════════════════════════════════════════════
DOCK_H = 56
dock_y = H - DOCK_H
dock = Image.new("RGBA", (W, DOCK_H), PANEL_LO + (242,))
canvas.alpha_composite(dock, (0, dock_y))
d.rectangle([0, dock_y, W, dock_y + 1], fill=BORDER + (255,))

# Dock items — pinned apps, then running apps
DOCK_ICONS = [
    ("S",   TEAL,  True,  True),   # ShadowCypher (running, active)
    ("F",   DARK,  False, False),  # files
    ("",   DARK,  False, False),  # firefox
    ("",   DARK,  False, False),  # vscode
    ("",   DARK,  True,  False),  # foot terminal (running)
    ("",   DARK,  False, False),  # discord
    ("",   DARK,  False, False),  # steam
    ("",   DARK,  False, False),  # github
    ("",   DARK,  False, False),  # bug / pentest
]
icon_size = 36
total_w = len(DOCK_ICONS) * (icon_size + 12) - 12
start_x = (W - total_w) // 2
for i, (glyph, col, running, active) in enumerate(DOCK_ICONS):
    ix = start_x + i * (icon_size + 12)
    iy = dock_y + (DOCK_H - icon_size) // 2 - 2
    # bg tile
    fill = PANEL_HI if not active else (0, 224, 164, 35)
    d.rounded_rectangle([ix, iy, ix + icon_size, iy + icon_size],
                        radius=8, fill=fill,
                        outline=(BORDER if not active else TEAL) + (200,), width=1)
    if glyph == "S":
        # hex S logo
        d.polygon([(ix + icon_size/2 + 11*math.cos(math.radians(60*k - 30)),
                    iy + icon_size/2 + 11*math.sin(math.radians(60*k - 30)))
                   for k in range(6)],
                   outline=TEAL + (255,), width=2)
        d.text((ix + icon_size/2 - 5, iy + 8), "S",
               font=ImageFont.truetype(FONT_BOLD, 16), fill=WHITE + (255,))
    else:
        d.text((ix + icon_size/2 - 8, iy + 8), glyph,
               font=ImageFont.truetype(FONT_REG, 18), fill=col + (255,))
    # running indicator (dot below)
    if running:
        d.ellipse([ix + icon_size/2 - 2, iy + icon_size + 4,
                   ix + icon_size/2 + 2, iy + icon_size + 8],
                  fill=TEAL + (255,))

# Bottom-left: shadow-mode pill (subtle, just a chip)
mode_pill_x = 14
mode_pill_y = dock_y + 16
d.rounded_rectangle([mode_pill_x, mode_pill_y, mode_pill_x + 110, mode_pill_y + 24],
                    radius=12, fill=(255, 170, 56, 25),
                    outline=WARN + (220,), width=1)
d.ellipse([mode_pill_x + 10, mode_pill_y + 8,
           mode_pill_x + 18, mode_pill_y + 16],
          fill=WARN + (255,))
d.text((mode_pill_x + 24, mode_pill_y + 5),
       "pentest", font=ImageFont.truetype(FONT_BOLD, 11),
       fill=WHITE + (255,))

# Bottom-right: subtle system info
sys_x = W - 200
sys_font = ImageFont.truetype(FONT_MONO, 10)
d.text((sys_x, dock_y + 12),
       "23%  4.2/16 GB",
       font=sys_font, fill=DIM + (255,))
d.text((sys_x, dock_y + 28),
       "↑ 1.2 MB/s   ↓ 380 KB/s",
       font=sys_font, fill=DIM + (255,))

# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
