#!/usr/bin/env python3
"""ShadowCypher Drop 01 — build every merch print file from source.

    python3 merch/drop01/build.py

Outputs (all regenerated, safe to delete):
    src/      vector SVG sources, text converted to outlines
    print/    print-ready PNGs at 300 DPI for Printful
    preview/  flat previews on the product colour, for the shop page

Requirements: pip install resvg-py uharfbuzz fonttools pillow numpy cryptography
"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: E402
from PIL import Image  # noqa: E402

import marks  # noqa: E402
from sclib import (CYAN, GARMENT, ICE, MUTED, SLATE, VIOLET, VIOLET_DEEP,  # noqa: E402
                   display, grotesk, knockout, mono, render, save_png, svg_doc)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src")
PRINT = os.path.join(HERE, "print")
PREVIEW = os.path.join(HERE, "preview")
# Web copies served by the site (www/ is what deploys to shadowcypher.site).
WEB = os.path.join(HERE, "..", "..", "www", "shop", "drop01")

GARMENT_RGB = (12, 12, 12)  # Printful "Black" #0c0c0c
MANIFEST: list[dict] = []


def emit(name: str, svg: str, w: int, h: int, *, product: str, placement: str,
         inches: str, ground: str = GARMENT, knock: bool = True, note: str = ""):
    """Write the SVG source, the print PNG and a preview."""
    os.makedirs(SRC, exist_ok=True)
    with open(os.path.join(SRC, f"{name}.svg"), "w") as f:
        f.write(svg)

    if knock:
        # Bake glows against the real garment colour, then cut the garment out.
        img = render(svg, w, background=ground)
        img = knockout(img, GARMENT_RGB)
    else:
        img = render(svg, w)
    save_png(img, os.path.join(PRINT, f"{name}.png"))

    prev = Image.new("RGBA", img.size, ground)
    prev.alpha_composite(img)
    prev.thumbnail((1200, 1200), Image.LANCZOS)
    save_png(prev.convert("RGB"), os.path.join(PREVIEW, f"{name}.png"), dpi=72)
    web_copy(prev, name)

    MANIFEST.append({"file": f"print/{name}.png", "source": f"src/{name}.svg",
                     "product": product, "placement": placement,
                     "size_px": [w, h], "size_in": inches, "note": note})


def web_copy(img: Image.Image, name: str):
    os.makedirs(WEB, exist_ok=True)
    w = img.convert("RGB").copy()
    w.thumbnail((900, 900), Image.LANCZOS)
    w.save(os.path.join(WEB, f"{name}.webp"), "WEBP", quality=86, method=6)


def P(font, text, size, x, y, fill, tracking=0.0, anchor="start", extra=""):
    d = font.path(text, size, x, y, tracking=tracking, anchor=anchor)
    return f'<path d="{d}" fill="{fill}" {extra}/>'


def mark_at(cx: float, top: float, size: float, uid: str, **kw) -> str:
    s = size / 1000
    return (f'<g transform="translate({cx - size / 2} {top}) scale({s})">'
            f'{marks.hood(uid, **kw)}</g>')


def wordmark(cx, baseline, size, fill=ICE, accent=VIOLET, tracking=0.08):
    """SHADOW in ice, CYPHER in violet, set in Unbounded."""
    f = display(700)
    w1 = f.width("SHADOW", size, tracking)
    w2 = f.width("CYPHER", size, tracking)
    gap = size * tracking
    x0 = cx - (w1 + gap + w2) / 2
    return (P(f, "SHADOW", size, x0, baseline, fill, tracking) +
            P(f, "CYPHER", size, x0 + w1 + gap, baseline, accent, tracking))


# ════════════════════════════════════════════════════════════════════════════
# 1. GHOST MODE TEE  (Bella+Canvas 3001, Black) — left chest + full back
# ════════════════════════════════════════════════════════════════════════════
def ghost_mode_tee():
    # Left chest: 3.5in mark with a small wordmark under it.
    W = H = 1050
    body = mark_at(W / 2, 30, 840, "lc")
    body += wordmark(W / 2, 995, 74, tracking=0.06)
    svg = svg_doc(W, H, body, marks.hood_defs("lc"))
    emit("ghost-mode-tee_left-chest", svg, W, H, product="ghost-mode-tee",
         placement="front (left chest)", inches="3.5 x 3.5",
         note="Place on the wearer's left chest, about 3 in below the collar.")

    # Back: 12 x 16 in.
    W, H = 3600, 4800
    d = display(800)
    g = grotesk(500)
    m = mono(500)
    body = marks.brackets(240, 200, 3120, 2880, 380, 46)
    body += mark_at(W / 2, 360, 2560, "bk")
    # Scan line across the eyes.
    body += f'<rect x="420" y="{360 + 2560 * 0.517}" width="2760" height="6" fill="{CYAN}" opacity="0.35"/>'
    body += P(d, "GHOST", 560, W / 2, 3700, ICE, tracking=0.06, anchor="middle")
    body += P(d, "MODE", 560, W / 2, 4260, VIOLET, tracking=0.32, anchor="middle")
    body += P(g, "END-TO-END ENCRYPTED  ·  ZERO KNOWLEDGE  ·  NO TRACE", 86,
              W / 2, 4500, SLATE, tracking=0.16, anchor="middle")
    body += P(m, "aes-256-gcm // your keys never leave your device", 92,
              W / 2, 4690, CYAN, tracking=0.02, anchor="middle")
    svg = svg_doc(W, H, body, marks.hood_defs("bk"))
    emit("ghost-mode-tee_back", svg, W, H, product="ghost-mode-tee",
         placement="back", inches="12 x 16")


# ════════════════════════════════════════════════════════════════════════════
# 2. PLAINTEXT TEE  (Bella+Canvas 3001, Black) — full front
#    The grid is a REAL AES-256-GCM ciphertext of the message printed below it.
# ════════════════════════════════════════════════════════════════════════════
MESSAGE = "say it in the dark."


def plaintext_tee():
    W, H = 3600, 4800
    key = bytes.fromhex("5c" * 32)          # fixed key so the build is reproducible
    nonce = bytes.fromhex("0b" * 12)
    filler = (b"shadowcypher // end-to-end // " * 40)[:400]
    ct = AESGCM(key).encrypt(nonce, filler + MESSAGE.encode(), b"sc-drop-01")
    hexes = [f"{b:02x}" for b in ct]

    m = mono(500)
    mb = mono(800)
    d = display(800)
    g = grotesk(500)
    cols, rows = 12, 17
    size = 132
    cell = m.width("00 ", size)
    grid_w = cell * cols - m.width(" ", size)
    x0 = (W - grid_w) / 2
    y0 = 520
    lh = 178
    reveal_row = 11
    body = ""
    # Header line.
    body += P(m, "$ sc decrypt --key ~/.sc/identity drop01.bin", 92, x0, 330, VIOLET)
    i = 0
    for r in range(rows):
        y = y0 + r * lh
        if r == reveal_row:
            # Plaintext line, highlighted, with a block cursor.
            body += f'<rect x="{x0 - 60}" y="{y - size * 0.92}" width="{grid_w + 120}" height="{lh * 1.02}" fill="{VIOLET_DEEP}" opacity="0.28"/>'
            body += P(mb, MESSAGE, 168, W / 2, y + 10, ICE, anchor="middle")
            cw = mb.width(MESSAGE, 168)
            body += f'<rect x="{W / 2 + cw / 2 + 24}" y="{y - 130}" width="84" height="150" fill="{CYAN}"/>'
            continue
        # Fade the cipher text out toward the edges of the print.
        t = abs(r - reveal_row) / max(reveal_row, rows - reveal_row)
        op = 0.95 - 0.7 * t
        line = " ".join(hexes[i:i + cols])
        i += cols
        col = SLATE if abs(r - reveal_row) > 1 else ICE
        body += P(m, line, size, x0, y, col, extra=f'opacity="{op:.2f}"')

    yb = y0 + rows * lh + 160
    body += f'<rect x="{x0}" y="{yb - 40}" width="{grid_w}" height="8" fill="{VIOLET}"/>'
    body += P(d, "PLAINTEXT IS A CHOICE.", 196, W / 2, yb + 250, ICE, tracking=0.02, anchor="middle")
    body += wordmark(W / 2, yb + 480, 120, tracking=0.12)
    body += P(g, "AES-256-GCM  ·  THE CIPHERTEXT ABOVE IS REAL", 74, W / 2, yb + 620,
              MUTED, tracking=0.2, anchor="middle")
    svg = svg_doc(W, H, body)
    emit("plaintext-tee_front", svg, W, H, product="plaintext-tee",
         placement="front", inches="12 x 16",
         note=f"Ciphertext = AES-256-GCM(key=0x5c*32, nonce=0x0b*12, aad='sc-drop-01') of filler + '{MESSAGE}'.")


# ════════════════════════════════════════════════════════════════════════════
# 3. SAY IT IN THE DARK HOODIE  (Gildan 18500, Black) — chest + full back
# ════════════════════════════════════════════════════════════════════════════
def dark_hoodie():
    # Chest: 10 x 3 in, mark + wordmark lockup.
    W, H = 3000, 900
    body = mark_at(420, 40, 820, "hc")
    body += f'<rect x="900" y="170" width="8" height="560" fill="{VIOLET}" opacity="0.8"/>'
    f = display(700)
    body += P(f, "SHADOW", 300, 1000, 440, ICE, tracking=0.06)
    body += P(f, "CYPHER", 300, 1000, 780, VIOLET, tracking=0.06)
    svg = svg_doc(W, H, body, marks.hood_defs("hc"))
    emit("dark-hoodie_chest", svg, W, H, product="dark-hoodie",
         placement="front (chest)", inches="10 x 3",
         note="Centre on the chest, top edge about 3.5 in below the collar seam, above the pocket.")

    # Back: 12 x 16 in, stacked headline.
    W, H = 3600, 4800
    d = display(800)
    g = grotesk(500)
    m = mono(500)
    body = mark_at(W / 2, 110, 1360, "hb")
    body += marks.brackets(1060, 80, 1480, 1320, 200, 32)
    lines = [("SAY", ICE), ("IT IN", ICE), ("THE", ICE), ("DARK.", VIOLET)]
    y = 2110
    for text, col in lines:
        body += P(d, text, 600, W / 2, y, col, tracking=0.04, anchor="middle")
        y += 600
    body += P(g, "PRIVATE MESSAGING  ·  ENCRYPTED BY DEFAULT", 104, W / 2, 4430,
              SLATE, tracking=0.2, anchor="middle")
    body += P(m, "shadowcypher.site", 108, W / 2, 4640, CYAN, anchor="middle")
    svg = svg_doc(W, H, body, marks.hood_defs("hb"))
    emit("dark-hoodie_back", svg, W, H, product="dark-hoodie",
         placement="back", inches="12 x 16")


# ════════════════════════════════════════════════════════════════════════════
# 4. HOOD DAD HAT  (Yupoong 6245CM, Black) — flat embroidery, 3 thread colours
#    Thread colours are Printful's own: 1832 Purple #6B5294, 1695 Aqua/Teal
#    #3399FF, 1801 White #FFFFFF. No gradients, no anti-aliasing.
# ════════════════════════════════════════════════════════════════════════════
THREAD_PURPLE = "#6B5294"
THREAD_AQUA = "#3399FF"
THREAD_WHITE = "#FFFFFF"

# Embroidery needs thicker eyes than the print mark (min ~1.5 mm stitches).
EYE_L_EMB = "M360 476 L486 508 L480 552 L382 540 Z"
EYE_R_EMB = "M640 476 L514 508 L520 552 L618 540 Z"


def dad_hat():
    W, H = 1200, 525        # 4 x 1.75 in at 300 dpi
    s = 470 / 1000
    hood = (f'<g transform="translate({W / 2 - 500 * s} 20) scale({s})" shape-rendering="crispEdges">'
            f'<path d="{marks.HOOD_OUTER}" fill="{THREAD_PURPLE}"/>'
            f'<path d="{marks.HOOD_RIM}" fill="{THREAD_WHITE}"/>'
            f'<path d="{marks.HOOD_FACE}" fill="#000000"/>'
            f'<path d="{EYE_L_EMB}" fill="{THREAD_AQUA}"/><path d="{EYE_R_EMB}" fill="{THREAD_AQUA}"/>'
            f'</g>')
    svg = svg_doc(W, H, hood)
    # Embroidery: transparent background, exact thread colours, black face is
    # stitched in 1800 Black so the face reads as a void on any hat colour.
    img = render(svg, W)
    save_png(img, os.path.join(PRINT, "hood-dad-hat_embroidery-front.png"))
    os.makedirs(SRC, exist_ok=True)
    with open(os.path.join(SRC, "hood-dad-hat_embroidery-front.svg"), "w") as f:
        f.write(svg)
    prev = Image.new("RGBA", img.size, (20, 20, 20, 255))
    prev.alpha_composite(img)
    save_png(prev.convert("RGB"), os.path.join(PREVIEW, "hood-dad-hat_embroidery-front.png"), dpi=72)
    web_copy(prev, "hood-dad-hat_embroidery-front")
    MANIFEST.append({"file": "print/hood-dad-hat_embroidery-front.png",
                     "source": "src/hood-dad-hat_embroidery-front.svg",
                     "product": "hood-dad-hat", "placement": "embroidery_front",
                     "size_px": [W, H], "size_in": "4 x 1.75",
                     "note": "Flat embroidery. Threads: 1832 Purple #6B5294, 1801 White #FFFFFF, "
                             "1695 Aqua/Teal #3399FF, 1800 Black #000000."})


# ════════════════════════════════════════════════════════════════════════════
# 5. STICKERS  (Printful Kiss-Cut, 4 x 4 in, white vinyl)
# ════════════════════════════════════════════════════════════════════════════
def sticker_hood():
    W = H = 1200
    body = (f'<rect x="40" y="40" width="1120" height="1120" rx="150" fill="#0b0b10"/>'
            f'<rect x="40" y="40" width="1120" height="1120" rx="150" fill="none" stroke="{VIOLET_DEEP}" stroke-width="10"/>')
    body += marks.brackets(140, 120, 920, 860, 140, 24)
    body += mark_at(W / 2, 130, 820, "s1", fade=False)
    body += wordmark(W / 2, 1080, 68, tracking=0.12)
    svg = svg_doc(W, H, body, marks.hood_defs("s1"))
    emit("sticker_ghost-mode", svg, W, H, product="sticker-ghost-mode",
         placement="default", inches="4 x 4", knock=False)


def text_on_circle(font, text, size, cx, cy, r, centre_deg, fill, tracking=0.0, bottom=False):
    """Set text along a circle, centred on centre_deg (0 = top, clockwise).

    Top text sits outside radius r and reads clockwise. Bottom text has its
    baseline on radius r, grows toward the centre and reads left to right.
    """
    out = ""
    widths = [font.width(ch, size) for ch in text]
    total = sum(widths) + tracking * size * (len(text) - 1)
    arc = total / r
    direction = -1 if bottom else 1
    a = math.radians(centre_deg) - direction * arc / 2
    for ch, w in zip(text, widths):
        a_mid = a + direction * (w / 2) / r
        x = cx + r * math.sin(a_mid)
        y = cy - r * math.cos(a_mid)
        rot = math.degrees(a_mid) + (180 if bottom else 0)
        if ch != " ":
            d = font.path(ch, size, 0, 0, anchor="middle")
            out += (f'<path d="{d}" fill="{fill}" transform="translate({x:.2f} {y:.2f}) '
                    f'rotate({rot:.3f})"/>')
        a += direction * (w + tracking * size) / r
    return out


def sticker_seal():
    W = H = 1200
    c = W / 2
    d = display(800)
    m = mono(600)
    body = (f'<circle cx="{c}" cy="{c}" r="575" fill="#0b0b10"/>'
            f'<circle cx="{c}" cy="{c}" r="548" fill="none" stroke="{VIOLET}" stroke-width="14"/>'
            f'<circle cx="{c}" cy="{c}" r="402" fill="none" stroke="{VIOLET}" stroke-width="6"/>')
    body += text_on_circle(d, "ENCRYPTED BY DEFAULT", 80, c, c, 440, 0, ICE, tracking=0.12)
    body += text_on_circle(m, "AES-256-GCM · ZERO KNOWLEDGE", 50, c, c, 520, 180,
                           CYAN, tracking=0.06, bottom=True)
    for side in (-1, 1):   # dots where the two arcs meet
        ang = math.radians(180 + side * 69)
        body += (f'<circle cx="{c + 474 * math.sin(ang):.1f}" cy="{c - 474 * math.cos(ang):.1f}" '
                 f'r="14" fill="{VIOLET}"/>')
    body += mark_at(c, 250, 640, "s2", fade=False)
    body += f'<circle cx="{c}" cy="{c}" r="402" fill="none" stroke="{VIOLET}" stroke-width="6"/>'
    svg = svg_doc(W, H, body, marks.hood_defs("s2"))
    emit("sticker_encrypted-seal", svg, W, H, product="sticker-encrypted-seal",
         placement="default", inches="4 x 4", knock=False)


def sticker_terminal():
    W = H = 1200
    m = mono(500)
    mb = mono(700)
    x, y, w, h = 60, 230, 1080, 740
    body = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="46" fill="#0b0b10"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="46" fill="none" stroke="#2a2a38" stroke-width="8"/>'
            f'<path d="M{x} {y + 46} a46 46 0 0 1 46 -46 H{x + w - 46} a46 46 0 0 1 46 46 V{y + 110} H{x} Z" fill="#16161f"/>')
    for i, col in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        body += f'<circle cx="{x + 70 + i * 62}" cy="{y + 56}" r="20" fill="{col}"/>'
    body += P(m, "sc — ~/inbox", 44, x + w / 2, y + 72, MUTED, anchor="middle")
    ty = y + 210
    body += P(mb, "$", 64, x + 60, ty, VIOLET) + P(m, "sc send @you --e2e", 64, x + 110, ty, ICE)
    body += P(m, "  encrypting", 52, x + 60, ty + 110, SLATE)
    body += f'<rect x="{x + 470}" y="{ty + 72}" width="380" height="44" rx="6" fill="{VIOLET}"/>'
    body += P(m, "100%", 52, x + 880, ty + 110, SLATE)
    body += P(m, "> delivered.", 64, x + 60, ty + 230, CYAN)
    body += P(m, "> nobody else can read it.", 64, x + 60, ty + 330, CYAN)
    body += P(mb, "$", 64, x + 60, ty + 450, VIOLET)
    body += f'<rect x="{x + 110}" y="{ty + 398}" width="38" height="64" fill="{ICE}"/>'
    svg = svg_doc(W, H, body)
    emit("sticker_terminal", svg, W, H, product="sticker-terminal",
         placement="default", inches="4 x 4", knock=False)


# ════════════════════════════════════════════════════════════════════════════
# 6. MUG  (Printful Black Glossy Mug 11 oz) — wrap, handle on the right
# ════════════════════════════════════════════════════════════════════════════
def mug():
    W, H = 2700, 1050
    m = mono(500)
    mb = mono(700)
    g = grotesk(500)
    # Left face (seen by a right-handed drinker's guests): the mark.
    body = marks.brackets(170, 110, 820, 830, 120, 22)
    body += mark_at(580, 150, 760, "mg")
    body += wordmark(580, 1010, 64, tracking=0.12)
    # Right face (seen by the drinker): the ritual.
    lines = [("while", VIOLET), ("(", SLATE), ("awake", ICE), (") {", SLATE)]
    x0, y0 = 1420, 250
    xx = x0
    for t, c in lines:
        body += P(mb if c == VIOLET else m, t, 104, xx, y0, c)
        xx += m.width(t, 104)
    body += P(m, "brew();", 104, x0 + 125, y0 + 150, CYAN)
    body += P(m, "encrypt();", 104, x0 + 125, y0 + 300, CYAN)
    body += P(m, "ship();", 104, x0 + 125, y0 + 450, CYAN)
    body += P(m, "}", 104, x0, y0 + 600, SLATE)
    body += P(g, "// nobody's listening.", 60, x0, y0 + 700, MUTED, tracking=0.04)
    svg = svg_doc(W, H, body, marks.hood_defs("mg"))
    emit("mug_wrap", svg, W, H, product="mug", placement="default", inches="9 x 3.5",
         ground="#0c0c0c")


def contact_sheet():
    files = [x["file"].replace("print/", "") for x in MANIFEST]
    thumbs = []
    for f in files:
        im = Image.open(os.path.join(PREVIEW, f)).convert("RGB")
        im.thumbnail((560, 560), Image.LANCZOS)
        tile = Image.new("RGB", (600, 600), (24, 24, 30))
        tile.paste(im, ((600 - im.width) // 2, (600 - im.height) // 2))
        thumbs.append(tile)
    cols = 4
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * 600, rows * 600), (10, 10, 14))
    for i, t in enumerate(thumbs):
        sheet.paste(t, ((i % cols) * 600, (i // cols) * 600))
    sheet.save(os.path.join(PREVIEW, "_contact-sheet.jpg"), quality=88)


def main():
    ghost_mode_tee()
    plaintext_tee()
    dark_hoodie()
    dad_hat()
    sticker_hood()
    sticker_seal()
    sticker_terminal()
    mug()
    with open(os.path.join(HERE, "print-files.json"), "w") as f:
        json.dump(MANIFEST, f, indent=2)
        f.write("\n")
    contact_sheet()
    print(f"built {len(MANIFEST)} print files")


if __name__ == "__main__":
    main()
