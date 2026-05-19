#!/usr/bin/env python3
"""ShadowOS desktop — v5: 'real desktop in use', no launcher overlay.

Clean Hyprland tile of 3 apps doing actual work, wallpaper visible in
gaps, dense real content (not just chrome). Browser + terminal +
notes/editor. ShadowCypher exists in the dock but isn't even open right now
because not every session needs it.
"""
from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
WALL = ROOT.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos" / \
       "shadowos-18-minimal-indigo-1920x1080.png"
OUT = ROOT / "previews" / "mock-desktop-v5.png"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

W, H = 1920, 1080

PURPLE    = (180, 74, 255)
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
BG_HOVER  = (36, 28, 56)
BORDER    = (40, 34, 58)
BORDER_LO = (28, 24, 42)
WARN      = (255, 170, 56)
CRIT      = (255, 80, 100)
OK        = (98, 220, 154)

canvas = Image.open(WALL).convert("RGBA").resize((W, H), Image.LANCZOS)
d = ImageDraw.Draw(canvas)

# ── TOP BAR ────────────────────────────────────────────────────────────────
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

# Focused window
d.text((114, 9), "Firefox",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))
d.text((164, 10), "—  CVE-2024-10443 · Synology Security Advisory",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))

# Workspaces
wx = W - 380
for i in range(5):
    cx = wx + i * 16
    if i == 0:
        d.rounded_rectangle([cx - 6, 11, cx + 8, 21], radius=4,
                            fill=PURPLE + (255,))
        d.text((cx - 3, 10), "1",
               font=ImageFont.truetype(FONT_BOLD, 9), fill=WHITE + (255,))
    elif i == 1:
        # workspace 2 has stuff (faint dot)
        d.ellipse([cx - 3, 13, cx + 3, 19], outline=DIM + (255,), width=1)
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

# ── Helper: focused vs unfocused window ──────────────────────────────────
def window(box, title_left, title_right="", focus=False):
    x0, y0, x1, y1 = box
    # Shadow
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 - 6, y0 - 4, x1 + 6, y1 + 8],
                                          radius=14, fill=(0, 0, 0, 160))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=16))
    canvas.alpha_composite(sh)
    # Body
    body = Image.new("RGBA", (x1 - x0, y1 - y0), BG_PANEL + (250,))
    canvas.alpha_composite(body, (x0, y0))
    # Border
    edge = (70, 50, 100) if focus else BORDER
    d.rounded_rectangle([x0, y0, x1, y1], radius=10,
                        outline=edge + (255,), width=1)
    # Title bar
    tb_h = 32
    tb = Image.new("RGBA", (x1 - x0 - 2, tb_h), BG_HIGH + (252,))
    canvas.alpha_composite(tb, (x0 + 1, y0 + 1))
    d.line([x0 + 1, y0 + tb_h, x1 - 1, y0 + tb_h],
           fill=BORDER + (200,), width=1)
    if focus:
        accent = Image.new("RGBA", (x1 - x0 - 30, 2), PURPLE + (200,))
        canvas.alpha_composite(accent.filter(ImageFilter.GaussianBlur(radius=1)),
                                (x0 + 15, y0))
    # Title
    d.text((x0 + 18, y0 + 10), title_left,
           font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))
    if title_right:
        bb = d.textbbox((0, 0), title_left, font=ImageFont.truetype(FONT_BOLD, 11))
        d.text((x0 + 18 + bb[2] + 14, y0 + 11), title_right,
               font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))
    # Controls
    cx_ = x1 - 18
    for ch, col in [("×", GRAY), ("▢", DARK), ("—", DARK)]:
        d.text((cx_, y0 + 9), ch,
               font=ImageFont.truetype(FONT_REG, 13), fill=col + (255,))
        cx_ -= 18

# ════════════════════════════════════════════════════════════════════════════
# LEFT HALF: Firefox showing a security advisory page (focused)
# ════════════════════════════════════════════════════════════════════════════
FX_x0, FX_y0 = 14, TOPH + 14
FX_x1, FX_y1 = 1050, H - 78
window((FX_x0, FX_y0, FX_x1, FX_y1),
       "Firefox", "CVE-2024-10443 · Synology Security Advisory",
       focus=True)

# Firefox URL bar
url_y = FX_y0 + 40
d.rounded_rectangle([FX_x0 + 14, url_y, FX_x1 - 14, url_y + 30],
                    radius=15, fill=BG_PANEL2 + (255,),
                    outline=BORDER + (200,), width=1)
# Lock icon (HTTPS)
d.text((FX_x0 + 28, url_y + 8), "",
       font=ImageFont.truetype(FONT_REG, 11), fill=OK + (255,))
d.text((FX_x0 + 46, url_y + 8),
       "synology.com/en-global/security/advisory/Synology_SA_24_18",
       font=ImageFont.truetype(FONT_MONO, 11), fill=WHITE + (255,))
# right side icons
d.text((FX_x1 - 78, url_y + 8), "", font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))
d.text((FX_x1 - 56, url_y + 8), "", font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))
d.text((FX_x1 - 34, url_y + 8), "", font=ImageFont.truetype(FONT_REG, 11), fill=DIM + (255,))

# Tab bar above URL would be next, but skip for space. Render page content.

# Severity badge
sev_y = url_y + 50
d.rounded_rectangle([FX_x0 + 30, sev_y, FX_x0 + 110, sev_y + 26],
                    radius=4, fill=CRIT + (255,))
d.text((FX_x0 + 42, sev_y + 5), "CRITICAL",
       font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))
d.text((FX_x0 + 122, sev_y + 6),
       "CVSS 9.8 · published 2 days ago",
       font=ImageFont.truetype(FONT_MONO, 11), fill=DIM + (255,))

# Title
d.text((FX_x0 + 30, sev_y + 40),
       "Synology DSM Photos Vulnerability",
       font=ImageFont.truetype(FONT_BOLD, 26), fill=WHITE + (255,))
d.text((FX_x0 + 30, sev_y + 76),
       "CVE-2024-10443",
       font=ImageFont.truetype(FONT_MONO, 14), fill=PURPLE + (255,))

# Body content
body_y = sev_y + 110
para = [
    "A heap buffer overflow vulnerability in the Synology Photos package",
    "before 7.0.1-0026 allows remote attackers to execute arbitrary",
    "code on affected installations of Synology DiskStation Manager.",
    "",
    "Authentication is NOT required to exploit this vulnerability.",
    "",
    "Affected products:",
    "    • DSM 7.2.2 — fixed in 7.2.2-72806-3",
    "    • DSM 7.2.1 — fixed in 7.2.1-69057-6",
    "    • DSM 7.2   — fixed in 7.2-64570-4",
    "    • BeeStation OS 1.1 — fixed in 1.1-65374-2",
    "",
    "Recommended actions:",
    "    1. Update Synology Photos to the latest version immediately.",
    "    2. If exposed to the internet, take device offline until patched.",
    "    3. Audit DSM logs for suspicious authentication attempts since Oct 2024.",
    "",
    "Discovered by Ryota Shiga (@Ga_ryo_) — Flatt Security",
]
para_font = ImageFont.truetype(FONT_REG, 13)
for i, line in enumerate(para):
    color = WHITE if line and not line.startswith(" ") and not "Affected" in line and \
                     not "Recommended" in line else GRAY
    if line.startswith("    "):
        color = GRAY
    if "Affected" in line or "Recommended" in line:
        color = WHITE
    d.text((FX_x0 + 30, body_y + i * 22), line, font=para_font, fill=color + (255,))

# References sidebar (right within firefox)
ref_x = FX_x1 - 280
ref_y = sev_y + 110
d.rounded_rectangle([ref_x, ref_y, FX_x1 - 30, ref_y + 280],
                    radius=8, fill=BG_PANEL2 + (255,),
                    outline=BORDER + (180,), width=1)
d.text((ref_x + 16, ref_y + 14),
       "REFERENCES",
       font=ImageFont.truetype(FONT_BOLD, 10), fill=DARK + (255,))
refs = [
    ("NVD entry",       "nvd.nist.gov/...10443"),
    ("Vendor advisory", "synology.com/sa-24-18"),
    ("PoC (Github)",    "@Ga_ryo_/cve-2024-10443"),
    ("Patch diff",      "Synology/DSM-7.2.2-3"),
    ("Mitre",           "cve.mitre.org/...10443"),
    ("ExploitDB",       "exploit-db.com/49281"),
]
ry = ref_y + 38
for label, url in refs:
    d.text((ref_x + 16, ry), label,
           font=ImageFont.truetype(FONT_BOLD, 11), fill=WHITE + (255,))
    d.text((ref_x + 16, ry + 16), url,
           font=ImageFont.truetype(FONT_MONO, 9), fill=PURPLE + (255,))
    ry += 40

# ════════════════════════════════════════════════════════════════════════════
# TOP RIGHT: Terminal running active scan
# ════════════════════════════════════════════════════════════════════════════
TX_x0, TX_y0 = 1064, TOPH + 14
TX_x1, TX_y1 = W - 14, 550
window((TX_x0, TX_y0, TX_x1, TX_y1),
       "Terminal", "shadow@nexus  /  ~/work/synology")

term = [
    ("$ shadow-mode status",                                            PURPLE),
    ("  mode: pentest    firewall: scan-open",                          DIM),
    ("",                                                                 DIM),
    ("$ rustscan -a 192.168.1.42 -- -sC -sV",                          PURPLE),
    ("Starting rustscan...",                                            DIM),
    ("Open 192.168.1.42:445   smb   Samba 4.21.1",                      WHITE),
    ("Open 192.168.1.42:5000  http  Synology DSM 7.2.2",                WARN),
    ("                                ┗ CVE-2024-10443  CRITICAL",    CRIT),
    ("Open 192.168.1.42:5001  https Synology DSM 7.2.2",                WARN),
    ("",                                                                 DIM),
    ("$ searchsploit synology dsm",                                     PURPLE),
    ("Path Title",                                                       DIM),
    ("───────────────────────────────────────────────────────",        DIM),
    ("49281  Synology DSM 7.2 - RCE (Authenticated)",                   WHITE),
    ("50312  Synology DSM Photos - RCE (Pre-auth)  ★ matches CVE",     OK),
    ("51827  Synology DSM - Path traversal",                            WHITE),
    ("",                                                                 DIM),
    ("$ msfconsole -q -x \"use exploit/multi/synology/...",             PURPLE),
    ("[*] Started reverse TCP handler on 10.0.0.5:4444",               DIM),
    ("[*] Sending stage (199944 bytes) to 192.168.1.42",                WHITE),
    ("[+] Meterpreter session 1 opened",                                OK),
    ("",                                                                 DIM),
    ("meterpreter > ▮",                                                  PURPLE),
]
tf = ImageFont.truetype(FONT_MONO, 11)
ty = TX_y0 + 44
for line, col in term:
    d.text((TX_x0 + 18, ty), line, font=tf, fill=col + (255,))
    ty += 17

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM RIGHT: Notes editor (helix/nvim) — engagement notebook
# ════════════════════════════════════════════════════════════════════════════
NT_x0, NT_y0 = 1064, 566
NT_x1, NT_y1 = W - 14, H - 78
window((NT_x0, NT_y0, NT_x1, NT_y1),
       "Helix", "~/work/synology/engagement.md  [modified]")

# Status line at top of editor
d.rectangle([NT_x0 + 1, NT_y0 + 33, NT_x1 - 1, NT_y0 + 52], fill=BG_PANEL2 + (255,))
d.text((NT_x0 + 18, NT_y0 + 36),
       "NOR",
       font=ImageFont.truetype(FONT_BOLD, 10), fill=PURPLE + (255,))
d.text((NT_x0 + 56, NT_y0 + 36),
       "markdown · 152 lines · utf-8",
       font=ImageFont.truetype(FONT_MONO, 10), fill=GRAY + (255,))
d.text((NT_x1 - 90, NT_y0 + 36),
       "1.0  ALL",
       font=ImageFont.truetype(FONT_MONO, 10), fill=DIM + (255,))

# Editor content — markdown notes for the engagement
ed = [
    ("# Engagement — synology nas",          PURPLE,  "h1"),
    ("",                                        DIM,    ""),
    ("## Scope",                                INDIGO, "h2"),
    ("- 192.168.1.42 (nas.local)",              GRAY,   "li"),
    ("- in-scope per contract sec-007",         GRAY,   "li"),
    ("",                                        DIM,    ""),
    ("## Findings",                             INDIGO, "h2"),
    ("",                                        DIM,    ""),
    ("### [CRIT] CVE-2024-10443  ·  Synology Photos RCE", CRIT, "h3"),
    ("Heap overflow in photo handler.",         GRAY,   "p"),
    ("Auth required: **no**",                    GRAY,   "p"),
    ("Verified working w/ MSF module on host.",  GRAY,   "p"),
    ("",                                        DIM,    ""),
    ("### [HIGH] SMB shares world-readable",    WARN,   "h3"),
    ("",                                        DIM,    ""),
    ("## Next steps",                           INDIGO, "h2"),
    ("- [x] Initial recon",                     GRAY,   "li"),
    ("- [x] Vuln scan via guardian agent",      GRAY,   "li"),
    ("- [x] Exploit verification (MSF)",        GRAY,   "li"),
    ("- [ ] Persistence test",                  WHITE,  "li"),
    ("- [ ] Lateral movement attempt",          WHITE,  "li"),
    ("- [ ] Write up the report",               WHITE,  "li"),
    ("",                                        DIM,    ""),
    ("## Evidence",                             INDIGO, "h2"),
    ("Screenshots in ./evidence/",              GRAY,   "p"),
]
ef = ImageFont.truetype(FONT_MONO, 12)
ey = NT_y0 + 60
for line, col, kind in ed:
    font = ef
    if kind == "h1":
        font = ImageFont.truetype(FONT_BOLD, 14)
    elif kind in ("h2", "h3"):
        font = ImageFont.truetype(FONT_BOLD, 12)
    d.text((NT_x0 + 18, ey), line, font=font, fill=col + (255,))
    ey += 16

# ════════════════════════════════════════════════════════════════════════════
# BOTTOM DOCK
# ════════════════════════════════════════════════════════════════════════════
DOCK_H = 56
dock_y = H - DOCK_H
dock = Image.new("RGBA", (W, DOCK_H), (10, 8, 18, 245))
canvas.alpha_composite(dock, (0, dock_y))
glow_top = Image.new("RGBA", (W, 4), PURPLE + (100,))
glow_top = glow_top.filter(ImageFilter.GaussianBlur(radius=2))
canvas.alpha_composite(glow_top, (0, dock_y - 2))

DOCK_ICONS = [
    ("◆",   PURPLE, False, False),  # ShadowCypher (not running this session)
    ("",   GRAY,   False, False),  # files
    ("",   GRAY,   True,  True),   # firefox (running + focused)
    ("",   GRAY,   False, False),  # vscode
    ("",   GRAY,   True,  False),  # terminal running
    ("",   GRAY,   True,  False),  # helix/notes running
    ("",   GRAY,   False, False),  # discord
    ("",   GRAY,   False, False),  # steam
    ("",   GRAY,   False, False),  # tools
]
icon_size = 40
total_w = len(DOCK_ICONS) * (icon_size + 10) - 10
start_x = (W - total_w) // 2
for i, (g, c, running, focused) in enumerate(DOCK_ICONS):
    ix = start_x + i * (icon_size + 10)
    iy = dock_y + (DOCK_H - icon_size) // 2 - 2
    if focused:
        fill = (180, 74, 255, 50)
        outline = PURPLE + (255,)
    else:
        fill = BG_HIGH + (220,)
        outline = BORDER + (200,)
    d.rounded_rectangle([ix, iy, ix + icon_size, iy + icon_size],
                        radius=10, fill=fill, outline=outline, width=1)
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
