#!/usr/bin/env python3
"""ShadowOS desktop mock — v3.

Same enterprise-platform structure as v2, but:
  • Color palette: deep black + royal purple + electric indigo (matches
    ShadowCypher Android app's #b44aff brand)
  • More polish: gradient title bars, subtle dividers, better typography
    hierarchy, sparkline + ring chart, hover state shown on one row
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "previews" / "mock-desktop-v3.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1920, 1080

# ── Palette: black + royal purple + electric indigo ─────────────────────────
BG_DEEP   = (8, 8, 14)        # almost-black with hint of indigo
BG_PANEL  = (16, 14, 26)      # raised panel
BG_HIGH   = (28, 22, 44)      # slightly higher panel
BG_HOVER  = (36, 28, 56)      # hover state
BORDER    = (40, 34, 58)
BORDER_LO = (28, 24, 42)
PURPLE    = (180, 74, 255)    # primary accent — ShadowCypher brand
PURPLE_LO = (130, 50, 200)
INDIGO    = (110, 96, 235)    # secondary accent
BLUE      = (88, 124, 255)
WHITE     = (236, 234, 244)
GRAY      = (148, 142, 168)
DIM       = (108, 102, 130)
DARK      = (72, 66, 92)
WARN      = (255, 170, 56)
CRIT      = (255, 80, 100)
OK        = (98, 220, 154)

# ── Background: solid deep with very subtle radial purple glow ──────────────
def make_bg():
    try:
        import numpy as np
        yy, xx = np.mgrid[0:H, 0:W]
        cx, cy = W * 0.6, H * 0.45
        rmax = max(W, H) * 0.9
        d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
        # base
        base = np.zeros((H, W, 3), dtype=np.float32)
        base[..., 0] = BG_DEEP[0]
        base[..., 1] = BG_DEEP[1]
        base[..., 2] = BG_DEEP[2]
        # purple glow fading outward
        glow_r = (1 - d) ** 2.4 * 32
        base[..., 0] += glow_r * 0.95   # R
        base[..., 1] += glow_r * 0.35   # G
        base[..., 2] += glow_r * 1.2    # B
        base = np.clip(base, 0, 255).astype(np.uint8)
        img = Image.fromarray(base, mode="RGB").convert("RGBA")
    except ImportError:
        img = Image.new("RGBA", (W, H), BG_DEEP + (255,))
    # Subtle hex grid overlay, very low opacity
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    r = 44
    dx = r * math.sqrt(3)
    dy = r * 1.5
    row = 0
    y = -r
    while y < H + r:
        x_off = 0 if row % 2 == 0 else dx / 2
        x = -dx + x_off
        while x < W + dx:
            pts = [(x + r * math.cos(math.radians(60 * i - 30)),
                    y + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
            od.line(pts + [pts[0]], fill=BORDER + (45,), width=1)
            x += dx
        y += dy
        row += 1
    img.alpha_composite(overlay)
    return img

canvas = make_bg()
d = ImageDraw.Draw(canvas)

# ════════════════════════════════════════════════════════════════════════════
# TOP MENU BAR
# ════════════════════════════════════════════════════════════════════════════
TOPH = 30
top = Image.new("RGBA", (W, TOPH), (10, 8, 18, 250))
canvas.alpha_composite(top, (0, 0))
# Bottom divider with subtle purple glow
d.rectangle([0, TOPH, W, TOPH + 1], fill=BORDER + (255,))
glow_line = Image.new("RGBA", (W, 4), (0, 0, 0, 0))
ImageDraw.Draw(glow_line).rectangle([0, 0, W, 1], fill=PURPLE + (90,))
glow_line = glow_line.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow_line, (0, TOPH))

# Logo + app menu — left side
def hex_pts(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]

# Diamond logo (matches ShadowCypher Android app's ◆ idea)
d.polygon([(16, 15), (22, 9), (28, 15), (22, 21)], fill=PURPLE + (255,))
d.text((36, 8), "ShadowCypher",
       font=ImageFont.truetype(FONT_BOLD, 12), fill=WHITE + (255,))

items = ["File", "Edit", "View", "Scan", "Tools", "Window", "Help"]
mx = 154
mf = ImageFont.truetype(FONT_REG, 11)
for it in items:
    d.text((mx, 9), it, font=mf, fill=GRAY + (255,))
    mx += d.textbbox((0, 0), it, font=mf)[2] + 16

# Right — workspaces, mode dot, tray, clock
# Workspace dots
wx = W - 380
for i in range(5):
    cx = wx + i * 16
    if i == 0:
        # Active — purple pill instead of dot
        d.rounded_rectangle([cx - 6, 11, cx + 8, 19], radius=4,
                            fill=PURPLE + (255,))
        d.text((cx - 3, 9), "1",
               font=ImageFont.truetype(FONT_BOLD, 9), fill=WHITE + (255,))
    else:
        d.ellipse([cx - 2, 13, cx + 2, 17], fill=DARK + (255,))

# Mode pip
mode_x = W - 270
d.ellipse([mode_x, 12, mode_x + 8, 20], fill=WARN + (255,))
d.text((mode_x + 13, 9), "pentest",
       font=ImageFont.truetype(FONT_REG, 11), fill=GRAY + (255,))

# Tray
tray_x = W - 175
tray_font = ImageFont.truetype(FONT_REG, 13)
for ic, col in [("", DIM), ("", DIM), ("", DIM), ("", DIM), ("", DIM)]:
    d.text((tray_x, 9), ic, font=tray_font, fill=col + (255,))
    tray_x += 19

# Clock
d.text((W - 78, 8), "21:34",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))

# ════════════════════════════════════════════════════════════════════════════
# Helper: window with gradient title bar
# ════════════════════════════════════════════════════════════════════════════
def window(box, title, focus=False, subtitle=""):
    x0, y0, x1, y1 = box
    # Shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 - 4, y0 - 2, x1 + 4, y1 + 6],
                                          radius=12, fill=(0, 0, 0, 130))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=14))
    canvas.alpha_composite(sh)
    # Body
    body = Image.new("RGBA", (x1 - x0, y1 - y0), BG_PANEL + (252,))
    canvas.alpha_composite(body, (x0, y0))
    # Outline — focused windows get a faint purple edge
    edge = (60, 40, 90) if focus else BORDER
    d.rounded_rectangle([x0, y0, x1, y1], radius=10,
                        outline=edge + (255,), width=1)
    # Title bar with subtle gradient
    tb_h = 34
    try:
        import numpy as np
        grad = np.zeros((tb_h, x1 - x0 - 2, 4), dtype=np.float32)
        for yi in range(tb_h):
            t = yi / max(1, tb_h - 1)
            grad[yi, :, 0] = BG_HIGH[0] + (BG_PANEL[0] - BG_HIGH[0]) * t
            grad[yi, :, 1] = BG_HIGH[1] + (BG_PANEL[1] - BG_HIGH[1]) * t
            grad[yi, :, 2] = BG_HIGH[2] + (BG_PANEL[2] - BG_HIGH[2]) * t
            grad[yi, :, 3] = 252
        tb_img = Image.fromarray(grad.astype(np.uint8), mode="RGBA")
        canvas.alpha_composite(tb_img, (x0 + 1, y0 + 1))
    except ImportError:
        tb = Image.new("RGBA", (x1 - x0 - 2, tb_h), BG_HIGH + (252,))
        canvas.alpha_composite(tb, (x0 + 1, y0 + 1))
    # Divider under title bar
    d.line([x0 + 1, y0 + tb_h, x1 - 1, y0 + tb_h], fill=BORDER + (180,), width=1)
    # If focus, faint purple accent on top edge
    if focus:
        accent_strip = Image.new("RGBA", (x1 - x0 - 30, 2), PURPLE + (180,))
        canvas.alpha_composite(accent_strip.filter(ImageFilter.GaussianBlur(radius=1)),
                               (x0 + 15, y0))
    # Title
    d.text((x0 + 18, y0 + 11), title,
           font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))
    if subtitle:
        bb = d.textbbox((0, 0), title, font=ImageFont.truetype(FONT_BOLD, 11))
        d.text((x0 + 18 + bb[2] + 14, y0 + 12), subtitle,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    # Right side: window controls
    cx = x1 - 18
    d.text((cx, y0 + 10), "×",
           font=ImageFont.truetype(FONT_REG, 14), fill=DIM + (255,))
    d.text((cx - 18, y0 + 10), "▢",
           font=ImageFont.truetype(FONT_REG, 12), fill=DARK + (255,))
    d.text((cx - 34, y0 + 10), "—",
           font=ImageFont.truetype(FONT_REG, 12), fill=DARK + (255,))


# ════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW: ShadowCypher Spectral Intelligence
# ════════════════════════════════════════════════════════════════════════════
SC_x0, SC_y0 = 14, TOPH + 14
SC_x1, SC_y1 = 1200, H - 78
window((SC_x0, SC_y0, SC_x1, SC_y1),
       "ShadowCypher", focus=True,
       subtitle="Spectral Intelligence  /  192.168.1.0/24")

# Left nav
NAV_W = 210
nav_x0 = SC_x0 + 1
nav_y0 = SC_y0 + 36
nav_h  = SC_y1 - nav_y0 - 1
nav_bg = Image.new("RGBA", (NAV_W, nav_h), (12, 10, 22, 255))
canvas.alpha_composite(nav_bg, (nav_x0, nav_y0))
d.rectangle([nav_x0 + NAV_W, nav_y0, nav_x0 + NAV_W + 1, SC_y1 - 1],
            fill=BORDER + (220,))

# Nav header
d.text((nav_x0 + 18, nav_y0 + 16), "OPERATIONS",
       font=ImageFont.truetype(FONT_BOLD, 10), fill=DARK + (255,))

# Nav items with little dots / pulse for "running"
nav = [
    ("Dashboard",       False, None,    False),
    ("Spectral Intel",  True,  None,    True),
    ("Vulnerabilities", False, "3",     False),
    ("Devices",         False, "8",     False),
    ("Network Scanner", False, None,    True),   # running
    ("Combat Deck",     False, None,    False),
    ("Payloads",        False, None,    False),
    ("C2 Operations",   False, None,    False),
    ("Community",       False, "12",    False),
    ("Audit Log",       False, None,    False),
    ("Settings",        False, None,    False),
]
ny = nav_y0 + 50
for label, active, badge, running in nav:
    if active:
        # Gradient highlight bar
        hl = Image.new("RGBA", (NAV_W, 30), (0, 0, 0, 0))
        try:
            import numpy as np
            arr = np.zeros((30, NAV_W, 4), dtype=np.float32)
            for xi in range(NAV_W):
                t = xi / NAV_W
                arr[:, xi, 0] = PURPLE[0] * (1 - t) * 0.18
                arr[:, xi, 1] = PURPLE[1] * (1 - t) * 0.18
                arr[:, xi, 2] = PURPLE[2] * (1 - t) * 0.18
                arr[:, xi, 3] = (1 - t) * 80
            hl = Image.fromarray(arr.astype(np.uint8), mode="RGBA")
            canvas.alpha_composite(hl, (nav_x0, ny - 4))
        except ImportError:
            d.rectangle([nav_x0, ny - 4, nav_x0 + NAV_W, ny + 24],
                        fill=(180, 74, 255, 30))
        d.rectangle([nav_x0, ny - 4, nav_x0 + 3, ny + 26], fill=PURPLE + (255,))
        color = WHITE
    else:
        color = GRAY if not running else WHITE
    # running pulse dot
    if running:
        d.ellipse([nav_x0 + 14, ny + 6, nav_x0 + 20, ny + 12],
                  fill=PURPLE + (255,))
        text_off = 28
    else:
        text_off = 22
    d.text((nav_x0 + text_off, ny + 1), label,
           font=ImageFont.truetype(FONT_REG, 12), fill=color + (255,))
    if badge:
        bf = ImageFont.truetype(FONT_BOLD, 10)
        bw = d.textbbox((0, 0), badge, font=bf)[2] + 14
        d.rounded_rectangle([nav_x0 + NAV_W - bw - 14, ny + 4,
                              nav_x0 + NAV_W - 14,    ny + 19],
                             radius=8, fill=(58, 30, 50, 255),
                             outline=CRIT + (180,), width=1)
        d.text((nav_x0 + NAV_W - bw - 7, ny + 4),
               badge, font=bf, fill=CRIT + (255,))
    ny += 30

# Footer of nav (storage info — fun detail)
foot_y = SC_y1 - 70
d.text((nav_x0 + 18, foot_y), "STORAGE",
       font=ImageFont.truetype(FONT_BOLD, 9), fill=DARK + (255,))
# tiny capacity bar
d.rectangle([nav_x0 + 18, foot_y + 18, nav_x0 + NAV_W - 18, foot_y + 22],
            fill=BG_HIGH + (255,))
d.rectangle([nav_x0 + 18, foot_y + 18, nav_x0 + 18 + (NAV_W - 36) * 0.43,
             foot_y + 22], fill=PURPLE + (255,))
d.text((nav_x0 + 18, foot_y + 28),
       "204 GB free of 480 GB",
       font=ImageFont.truetype(FONT_MONO, 9), fill=DIM + (255,))

# ── Content area ────────────────────────────────────────────────────────────
CT_x0 = nav_x0 + NAV_W + 1
CT_y0 = nav_y0
CT_x1 = SC_x1 - 1
CT_y1 = SC_y1 - 1

# Toolbar
d.text((CT_x0 + 28, CT_y0 + 22),
       "Network Intelligence",
       font=ImageFont.truetype(FONT_BOLD, 20), fill=WHITE + (255,))
d.text((CT_x0 + 28, CT_y0 + 52),
       "Subnet 192.168.1.0/24  ·  scan in progress  ·  3/8 hosts profiled",
       font=ImageFont.truetype(FONT_REG, 12), fill=GRAY + (255,))

# Right side of toolbar: action buttons
btn_x = CT_x1 - 18
for btn_label, btn_color in [("⏸ Pause", BG_HIGH), ("⤵ Export", BG_HIGH),
                               ("▶ Rescan", PURPLE)]:
    bf = ImageFont.truetype(FONT_BOLD, 10)
    bw = d.textbbox((0, 0), btn_label, font=bf)[2] + 22
    bx0 = btn_x - bw
    by0 = CT_y0 + 24
    by1 = by0 + 28
    if btn_color == PURPLE:
        d.rounded_rectangle([bx0, by0, btn_x, by1], radius=6, fill=PURPLE + (255,))
        text_c = WHITE
    else:
        d.rounded_rectangle([bx0, by0, btn_x, by1], radius=6,
                            fill=btn_color + (255,), outline=BORDER + (220,), width=1)
        text_c = GRAY
    d.text((bx0 + 11, by0 + 8), btn_label, font=bf, fill=text_c + (255,))
    btn_x = bx0 - 8

# Stat ribbon — 4 KPI cards with sparklines
ribbon_y = CT_y0 + 90
cards = [
    ("TOTAL DEVICES",  "8",   "+2 this week", WHITE,  PURPLE,  [4, 5, 5, 6, 6, 7, 8]),
    ("INCIDENTS",      "1",   "1 critical",   CRIT,   CRIT,    [0, 0, 1, 0, 0, 1, 1]),
    ("CVE ALERTS",     "3",   "2 high · 1 med", WARN, WARN,    [1, 2, 2, 3, 2, 3, 3]),
    ("AI QUERIES",     "42",  "8 / 500 today", WHITE, INDIGO,  [3, 8, 15, 22, 30, 38, 42]),
]
cw = (CT_x1 - CT_x0 - 80) / 4 - 6
cx = CT_x0 + 28
for label, val, sub, val_col, accent, spark in cards:
    cy0 = ribbon_y
    cy1 = ribbon_y + 100
    d.rounded_rectangle([cx, cy0, cx + cw, cy1], radius=8,
                        fill=(20, 16, 32, 255), outline=BORDER + (200,), width=1)
    # accent bar on top
    d.rectangle([cx, cy0, cx + cw, cy0 + 3], fill=accent + (255,))
    d.text((cx + 16, cy0 + 14), label,
           font=ImageFont.truetype(FONT_MONO, 9), fill=DARK + (255,))
    d.text((cx + 16, cy0 + 30),
           val, font=ImageFont.truetype(FONT_BOLD, 32), fill=val_col + (255,))
    d.text((cx + 16, cy0 + 72), sub,
           font=ImageFont.truetype(FONT_MONO, 10), fill=GRAY + (255,))
    # sparkline at right
    sp_w = 100
    sp_h = 36
    sp_x = cx + cw - sp_w - 14
    sp_y = cy0 + 28
    mx_v = max(spark)
    mn_v = min(spark)
    rng  = max(1, mx_v - mn_v)
    pts = []
    for i, v in enumerate(spark):
        px = sp_x + i * sp_w / (len(spark) - 1)
        py = sp_y + sp_h - (v - mn_v) / rng * sp_h
        pts.append((px, py))
    # Fill under line (faded)
    poly = pts + [(sp_x + sp_w, sp_y + sp_h), (sp_x, sp_y + sp_h)]
    sp_fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sp_fill).polygon(poly, fill=accent + (40,))
    canvas.alpha_composite(sp_fill)
    for i in range(len(pts) - 1):
        d.line([pts[i], pts[i+1]], fill=accent + (230,), width=2)
    # Last point dot
    lp = pts[-1]
    d.ellipse([lp[0]-3, lp[1]-3, lp[0]+3, lp[1]+3], fill=accent + (255,))
    cx += cw + 8

# Section header for table
sec_y = ribbon_y + 120
d.text((CT_x0 + 28, sec_y), "DISCOVERED HOSTS",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=DARK + (255,))
d.text((CT_x0 + 28 + 160, sec_y), "showing 8 of 8",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
# Search input on right
sx0 = CT_x1 - 220
d.rounded_rectangle([sx0, sec_y - 4, CT_x1 - 18, sec_y + 18],
                    radius=11, fill=(20, 16, 32, 255),
                    outline=BORDER + (200,), width=1)
d.text((sx0 + 10, sec_y), "",
       font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))
d.text((sx0 + 28, sec_y),
       "filter hosts…", font=ImageFont.truetype(FONT_REG, 10),
       fill=DARK + (255,))

# Table header
headers = ["IP", "HOSTNAME", "OS", "PORTS", "RISK", "STATUS"]
col_widths = [120, 175, 200, 130, 100, 100]
header_y = sec_y + 28
hx = CT_x0 + 28
for hdr, w in zip(headers, col_widths):
    d.text((hx, header_y), hdr,
           font=ImageFont.truetype(FONT_MONO, 10), fill=DARK + (255,))
    hx += w
d.line([CT_x0 + 28, header_y + 20, CT_x1 - 28, header_y + 20],
       fill=BORDER + (255,), width=1)

# Rows
rows = [
    ("192.168.1.1",  "router.local",  "OpenWRT 23.05",    "22, 443",       "Low",      "Online",      OK,    False),
    ("192.168.1.42", "nas.local",     "Synology DSM 7.2.2","445, 5000",     "Critical", "Vulnerable",  CRIT,  True),   # hover
    ("192.168.1.55", "ws-laptop",     "Arch Linux 6.13",  "22",            "Low",      "Online",      OK,    False),
    ("192.168.1.66", "tv.local",      "WebOS 23",         "8080, 9080",    "Medium",   "Online",      WARN,  False),
    ("192.168.1.71", "iot-cam-01",    "Unknown",          "80, 554, 8554", "Medium",   "Online",      WARN,  False),
    ("192.168.1.99", "voip.local",    "Linphone 5.3",     "5060, 5061",    "Low",      "Online",      OK,    False),
    ("192.168.1.100","pi.local",      "Debian 12",        "22, 80",        "Low",      "Online",      OK,    False),
    ("192.168.1.221","ws-02",         "Windows 11 22H2",  "135, 445, 3389","Medium",   "Online",      WARN,  False),
]
ry = header_y + 30
for ip, hn, osv, ports, risk, status, status_c, hovered in rows:
    if hovered:
        # Hover state — slight purple tint + left accent bar
        d.rectangle([CT_x0 + 14, ry - 4, CT_x1 - 14, ry + 24],
                    fill=(180, 74, 255, 14))
        d.rectangle([CT_x0 + 14, ry - 4, CT_x0 + 17, ry + 24], fill=PURPLE + (255,))
    vx = CT_x0 + 28
    risk_color = {"Low": GRAY, "Medium": WARN, "Critical": CRIT}.get(risk, GRAY)
    cells_text = [(ip, WHITE), (hn, WHITE), (osv, GRAY), (ports, GRAY),
                  (risk, risk_color), (status, status_c)]
    for (t, c), w in zip(cells_text, col_widths):
        d.text((vx, ry), t,
               font=ImageFont.truetype(FONT_MONO, 11), fill=c + (255,))
        vx += w
    ry += 32

# ════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN: terminal + chat panel
# ════════════════════════════════════════════════════════════════════════════
RC_x0 = SC_x1 + 14
RC_x1 = W - 14

T_y0 = TOPH + 14
T_y1 = 540
window((RC_x0, T_y0, RC_x1, T_y1),
       "Terminal", subtitle="shadow@nexus  /  ~/work")

term = [
    ("$ shadow-mode status",                                                  PURPLE),
    ("  mode: pentest    firewall: scan-open",                                GRAY),
    ("",                                                                       GRAY),
    ("$ rustscan -a 192.168.1.0/24 -- -sC -sV",                              PURPLE),
    ("Open 192.168.1.1:22    ssh   OpenSSH 9.6",                              WHITE),
    ("Open 192.168.1.1:443   nginx 1.27.3",                                   WHITE),
    ("Open 192.168.1.42:445  smb   Samba 4.21.1",                             WHITE),
    ("Open 192.168.1.42:5000 http  Synology DSM 7.2.2",                       WARN),
    ("                                  ┗ CVE-2024-10443 critical",          CRIT),
    ("Open 192.168.1.66:8080 http  WebOS 23",                                 WHITE),
    ("Open 192.168.1.100:80  http  nginx 1.27.3",                             WHITE),
    ("",                                                                       GRAY),
    ("scan complete: 8 hosts · 13 ports · 1 critical CVE",                   OK),
    ("",                                                                       GRAY),
    ("$ shadow scan agent --target 192.168.1.42 \\",                         PURPLE),
    ("                    --module cve-2024-10443",                          PURPLE),
    ("queued mission #4421 for guardian 'nexus-gateway'",                    GRAY),
    ("",                                                                       GRAY),
    ("$ ▮",                                                                    PURPLE),
]
tf = ImageFont.truetype(FONT_MONO, 11)
ty = T_y0 + 48
for line, col in term:
    d.text((RC_x0 + 18, ty), line, font=tf, fill=col + (255,))
    ty += 17

# Bottom right: community chat
C_y0 = 555
C_y1 = H - 78
window((RC_x0, C_y0, RC_x1, C_y1),
       "Community Chat", subtitle="#global  /  12 online")

# Messages
msgs = [
    ("alex",   PURPLE,  "anyone else seeing CVE-2024-10443 in the wild?", "21:18"),
    ("ria",    WARN,    "yeah we found one on a synology nas this morning",     "21:21"),
    ("jamie",  INDIGO,  "patch came out 2 days ago — most people aren't on it", "21:23"),
    ("alex",   PURPLE,  "what's the exploit reliability?",                       "21:24"),
    ("ria",    WARN,    "high — guardian fired immediately on a 7.2.2.81 host",  "21:30"),
    ("you",    OK,      "queueing a guardian mission for nas.local right now",   "21:33"),
]
my = C_y0 + 56
for nick, col, body, ts in msgs:
    # Avatar
    d.ellipse([RC_x0 + 18, my, RC_x0 + 40, my + 22], fill=col + (255,))
    d.text((RC_x0 + 26, my + 3), nick[0].upper(),
           font=ImageFont.truetype(FONT_BOLD, 11), fill=BG_PANEL + (255,))
    # Nick + ts
    d.text((RC_x0 + 50, my), nick,
           font=ImageFont.truetype(FONT_BOLD, 11), fill=col + (255,))
    nb = d.textbbox((0, 0), nick, font=ImageFont.truetype(FONT_BOLD, 11))[2]
    d.text((RC_x0 + 50 + nb + 8, my + 2), ts,
           font=ImageFont.truetype(FONT_MONO, 9), fill=DARK + (255,))
    # Body
    d.text((RC_x0 + 50, my + 16), body,
           font=ImageFont.truetype(FONT_REG, 11), fill=GRAY + (255,))
    my += 44

# Input
inp_y = C_y1 - 46
d.rounded_rectangle([RC_x0 + 14, inp_y, RC_x1 - 14, inp_y + 30],
                    radius=15, fill=(20, 16, 32, 255),
                    outline=BORDER + (220,), width=1)
d.text((RC_x0 + 28, inp_y + 8),
       "message #global…", font=ImageFont.truetype(FONT_REG, 11),
       fill=DARK + (255,))
# Send button
sb_x0 = RC_x1 - 60
d.rounded_rectangle([sb_x0, inp_y + 4, RC_x1 - 18, inp_y + 26],
                    radius=11, fill=PURPLE + (255,))
d.text((sb_x0 + 8, inp_y + 8), "Send",
       font=ImageFont.truetype(FONT_BOLD, 10), fill=WHITE + (255,))

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM DOCK
# ════════════════════════════════════════════════════════════════════════════
DOCK_H = 56
dock_y = H - DOCK_H
dock = Image.new("RGBA", (W, DOCK_H), (10, 8, 18, 248))
canvas.alpha_composite(dock, (0, dock_y))
# Top edge: subtle purple glow
glow_top = Image.new("RGBA", (W, 4), PURPLE + (120,))
glow_top = glow_top.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow_top, (0, dock_y - 2))
d.rectangle([0, dock_y, W, dock_y + 1], fill=BORDER + (255,))

DOCK_ICONS = [
    ("◆",   PURPLE, True,  True),    # ShadowCypher
    ("",   GRAY,   False, False),   # files
    ("",   GRAY,   False, False),   # firefox
    ("",   GRAY,   False, False),   # vscode
    ("",   GRAY,   True,  False),   # terminal
    ("",   GRAY,   False, False),   # discord
    ("",   GRAY,   False, False),   # steam
    ("",   GRAY,   False, False),   # github
    ("",   GRAY,   False, False),   # tools
]
icon_size = 40
total_w = len(DOCK_ICONS) * (icon_size + 10) - 10
start_x = (W - total_w) // 2
for i, (glyph, col, running, active) in enumerate(DOCK_ICONS):
    ix = start_x + i * (icon_size + 10)
    iy = dock_y + (DOCK_H - icon_size) // 2 - 2
    if active:
        fill = (180, 74, 255, 50)
        outline = PURPLE + (255,)
    else:
        fill = BG_HIGH + (220,)
        outline = BORDER + (200,)
    d.rounded_rectangle([ix, iy, ix + icon_size, iy + icon_size],
                        radius=10, fill=fill, outline=outline, width=1)
    if glyph == "◆":
        # ShadowCypher diamond logo
        cxd, cyd = ix + icon_size/2, iy + icon_size/2
        d.polygon([(cxd, cyd - 14), (cxd + 12, cyd), (cxd, cyd + 14), (cxd - 12, cyd)],
                   fill=PURPLE + (255,))
    else:
        d.text((ix + icon_size/2 - 9, iy + 10), glyph,
               font=ImageFont.truetype(FONT_REG, 20), fill=col + (255,))
    if running:
        d.ellipse([ix + icon_size/2 - 2, iy + icon_size + 4,
                   ix + icon_size/2 + 2, iy + icon_size + 8],
                  fill=PURPLE + (255,))

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
       "CPU 23%   RAM 4.2/16 GB",
       font=sf, fill=GRAY + (255,))
d.text((sx, dock_y + 28),
       "↑ 1.2 MB/s   ↓ 380 KB/s",
       font=sf, fill=GRAY + (255,))

# Save
canvas.convert("RGB").save(OUT, "PNG", optimize=True)
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
