#!/usr/bin/env python3
"""Generate 5 additional SC hoodie print designs."""

import random
from PIL import Image, ImageDraw, ImageFont

OUT   = "/home/jack/ShadowCypher/merch/designs"
LATO  = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"
MONO  = "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf"
SZ    = 4096

# SC brand palette
BLACK   = (0, 0, 0)
NAVY    = (5, 0, 30)
WHITE   = (255, 255, 255)
CYAN    = (0, 212, 255)
PURPLE  = (168, 85, 247)
PINK    = (255, 0, 110)
LPURPLE = (113, 75, 235)
DGRAY   = (18, 18, 24)


def F(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()


def cx(draw, text, y, font, color, w=SZ):
    bb = draw.textbbox((0, 0), text, font=font)
    x = (w - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bb[3] - bb[1]


def sc_brackets(draw, sz=SZ, color=CYAN, thick=16, arm=240):
    """Draw SC corner frame brackets."""
    m = int(sz * 0.08)
    coords = [
        # TL
        [(m, m), (m + arm, m), (m, m), (m, m + arm)],
        # TR
        [(sz-m-arm, m), (sz-m, m), (sz-m, m), (sz-m, m+arm)],
        # BL
        [(m, sz-m-arm), (m, sz-m), (m, sz-m), (m+arm, sz-m)],
        # BR
        [(sz-m-arm, sz-m), (sz-m, sz-m), (sz-m, sz-m-arm), (sz-m, sz-m)],
    ]
    for (x1,y1),(x2,y2),(x3,y3),(x4,y4) in coords:
        draw.line([(x1,y1),(x2,y2)], fill=color, width=thick)
        draw.line([(x3,y3),(x4,y4)], fill=color, width=thick)


# ── D4: SC WING BACK ─────────────────────────────────────────────────────────
# Front for SC WING uses sc-svg1-wing.png directly. Back panel:
def design4_back():
    img  = Image.new("RGB", (SZ, SZ), BLACK)
    draw = ImageDraw.Draw(img)

    # Corner brackets in cyan
    sc_brackets(draw, color=CYAN, thick=20, arm=300)

    # Faint vertical grid lines for depth
    for x in range(0, SZ, 120):
        draw.line([(x, 0), (x, SZ)], fill=(10, 10, 18), width=1)

    f_huge = F(LATO, 620)
    f_sub  = F(LATO, 80)
    f_code = F(MONO, 52)

    cx(draw, "SHADOW", int(SZ*0.25), f_huge, WHITE)
    cx(draw, "CYPHER", int(SZ*0.52), f_huge, WHITE)

    # Cyan line
    lw = int(SZ * 0.55)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.80), lx+lw, int(SZ*0.80)+8], fill=CYAN)

    cx(draw, "SHADOWCYPHER.SITE", int(SZ*0.82), f_sub, CYAN)
    cx(draw, "// DIGITAL SOVEREIGNTY", int(SZ*0.89), f_code, PURPLE)

    img.save(f"{OUT}/d4-wing-back.jpg", "JPEG", quality=95)
    print("d4-wing-back.jpg saved")


# ── D5: SC PHANTOM BACK ───────────────────────────────────────────────────────
def design5_back():
    img  = Image.new("RGB", (SZ, SZ), NAVY)
    draw = ImageDraw.Draw(img)

    sc_brackets(draw, color=LPURPLE, thick=18, arm=260)

    f_huge = F(LATO, 520)
    f_sub  = F(LATO, 90)
    f_code = F(MONO, 48)

    # "SC" in huge white, centered high
    cx(draw, "SC", int(SZ*0.15), f_huge, WHITE)

    # Purple thick line
    lw = int(SZ * 0.6)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.47), lx+lw, int(SZ*0.47)+10], fill=LPURPLE)

    cx(draw, "SHADOWCYPHER", int(SZ*0.52), f_sub, WHITE)
    cx(draw, "DIGITAL SECURITY PLATFORM", int(SZ*0.62), f_code, CYAN)
    cx(draw, "v3.0  //  2024", int(SZ*0.69), f_code, PURPLE)

    img.save(f"{OUT}/d5-phantom-back.jpg", "JPEG", quality=95)
    print("d5-phantom-back.jpg saved")


# ── D6: GHOST PROTOCOL – CAMO AOP BACK ───────────────────────────────────────
def _camo_layer(img_size):
    """Generate a cyberpunk pixel-camo pattern."""
    random.seed(42)
    img  = Image.new("RGB", (img_size, img_size), (3, 3, 8))
    draw = ImageDraw.Draw(img)

    palette = [
        (5, 3, 14),    # near-black purple
        (10, 8, 22),   # dark navy
        (14, 5, 8),    # dark maroon
        (3, 10, 18),   # dark steel
        (8, 4, 18),    # deep violet
        (3, 3, 8),     # base black
    ]

    for _ in range(22000):
        x = random.randint(0, img_size - 1)
        y = random.randint(0, img_size - 1)
        w = random.randint(20, 180)
        h = random.randint(8, 60)
        c = random.choice(palette)
        draw.rectangle([x, y, x+w, y+h], fill=c)

    return img


def design6_camo():
    base = _camo_layer(SZ)
    draw = ImageDraw.Draw(base)

    sc_brackets(draw, color=CYAN, thick=22, arm=280)

    # Horizontal scan lines overlay
    for y in range(0, SZ, 6):
        draw.line([(0, y), (SZ, y)], fill=(0, 0, 0, 30), width=1)

    f_huge = F(LATO, 460)
    f_sub  = F(LATO, 100)
    f_code = F(MONO, 56)

    # Semi-transparent backing for text legibility
    overlay = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
    od      = ImageDraw.Draw(overlay)
    od.rectangle([int(SZ*0.05), int(SZ*0.28), int(SZ*0.95), int(SZ*0.78)],
                 fill=(0, 0, 0, 140))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)

    cx(draw, "GHOST", int(SZ*0.30), f_huge, WHITE)
    cx(draw, "PROTOCOL", int(SZ*0.50), f_huge, CYAN)

    lw = int(SZ * 0.7)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.69), lx+lw, int(SZ*0.69)+8], fill=PURPLE)

    cx(draw, "SHADOWCYPHER  ·  COVERT SERIES", int(SZ*0.72), f_sub, PURPLE)
    cx(draw, "ACCESS LEVEL: ROOT", int(SZ*0.81), f_code, CYAN)

    base.save(f"{OUT}/d6-ghost-camo-back.jpg", "JPEG", quality=95)
    print("d6-ghost-camo-back.jpg saved")


def design6_camo_front():
    base = _camo_layer(SZ)
    draw = ImageDraw.Draw(base)

    sc_brackets(draw, color=CYAN, thick=20, arm=220)

    overlay = Image.new("RGBA", (SZ, SZ), (0, 0, 0, 0))
    od      = ImageDraw.Draw(overlay)
    od.rectangle([int(SZ*0.1), int(SZ*0.35), int(SZ*0.9), int(SZ*0.65)],
                 fill=(0, 0, 0, 130))
    base = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(base)

    f_big  = F(LATO, 340)
    f_code = F(MONO, 60)

    cx(draw, "SHDW CYPH", int(SZ*0.37), f_big, WHITE)
    cx(draw, "GHOST PROTOCOL  //  COVERT SERIES", int(SZ*0.55), f_code, CYAN)

    base.save(f"{OUT}/d6-ghost-camo-front.jpg", "JPEG", quality=95)
    print("d6-ghost-camo-front.jpg saved")


# ── D7: SC PINK / PHANTOM EDITION ─────────────────────────────────────────────
def design7_pink_front():
    img  = Image.new("RGB", (SZ, SZ), BLACK)
    draw = ImageDraw.Draw(img)

    sc_brackets(draw, color=PINK, thick=20, arm=280)

    f_big  = F(LATO, 560)
    f_sub  = F(LATO, 80)
    f_code = F(MONO, 60)

    cx(draw, "SHDW CYPH", int(SZ*0.28), f_big, WHITE)

    # Pink accent line
    lw = int(SZ * 0.55)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.54), lx+lw, int(SZ*0.54)+8], fill=PINK)

    cx(draw, "PHANTOM  ·  COLLECTION 01", int(SZ*0.57), f_sub, PINK)
    cx(draw, "trace.complete();", int(SZ*0.66), f_code, PINK)

    img.save(f"{OUT}/d7-pink-front.jpg", "JPEG", quality=95)
    print("d7-pink-front.jpg saved")


def design7_pink_back():
    img  = Image.new("RGB", (SZ, SZ), BLACK)
    draw = ImageDraw.Draw(img)

    sc_brackets(draw, color=PINK, thick=18, arm=260)

    f_huge = F(LATO, 580)
    f_sub  = F(LATO, 88)
    f_code = F(MONO, 52)

    # "PHANTOM" huge in pink
    cx(draw, "PHANTOM", int(SZ*0.22), f_huge, PINK)

    lw = int(SZ * 0.6)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.52), lx+lw, int(SZ*0.52)+8], fill=WHITE)

    cx(draw, "SHADOWCYPHER", int(SZ*0.55), f_sub, WHITE)
    cx(draw, "COLLECTION 01", int(SZ*0.64), f_code, PINK)
    cx(draw, "// UNDEFINED BY DEFAULT", int(SZ*0.71), f_code, (180, 180, 200))

    img.save(f"{OUT}/d7-pink-back.jpg", "JPEG", quality=95)
    print("d7-pink-back.jpg saved")


# ── D8: SC MINIMAL ────────────────────────────────────────────────────────────
def design8_minimal_front():
    img  = Image.new("RGB", (SZ, SZ), BLACK)
    draw = ImageDraw.Draw(img)

    sc_brackets(draw, color=CYAN, thick=24, arm=320)

    f_huge  = F(LATO, 780)
    f_small = F(MONO, 64)

    cy_shadow = (0, 80, 100)
    bb = draw.textbbox((0,0), "SHADOW", font=f_huge)
    tw = bb[2] - bb[0]
    x = (SZ - tw) // 2

    # Subtle shadow offset
    draw.text((x+8, int(SZ*0.12)+8), "SHADOW", font=f_huge, fill=cy_shadow)
    draw.text((x, int(SZ*0.12)), "SHADOW", font=f_huge, fill=WHITE)

    bb2 = draw.textbbox((0,0), "CYPHER", font=f_huge)
    tw2 = bb2[2] - bb2[0]
    x2 = (SZ - tw2) // 2
    draw.text((x2+8, int(SZ*0.46)+8), "CYPHER", font=f_huge, fill=(60, 0, 80))
    draw.text((x2, int(SZ*0.46)), "CYPHER", font=f_huge, fill=CYAN)

    # Thin line separator
    lw = int(SZ * 0.45)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.83), lx+lw, int(SZ*0.83)+4], fill=CYAN)

    cx(draw, "SYS://ONLINE  —  SHADOWCYPHER", int(SZ*0.86), f_small, (160, 160, 190))

    img.save(f"{OUT}/d8-minimal-front.jpg", "JPEG", quality=95)
    print("d8-minimal-front.jpg saved")


def design8_minimal_back():
    img  = Image.new("RGB", (SZ, SZ), BLACK)
    draw = ImageDraw.Draw(img)

    sc_brackets(draw, color=PURPLE, thick=18, arm=280)

    f_med  = F(LATO, 180)
    f_code = F(MONO, 56)

    cx(draw, "SHADOWCYPHER", int(SZ*0.36), f_med, WHITE)

    lw = int(SZ * 0.5)
    lx = (SZ - lw) // 2
    draw.rectangle([lx, int(SZ*0.55), lx+lw, int(SZ*0.55)+6], fill=PURPLE)

    cx(draw, "DIGITAL SECURITY PLATFORM", int(SZ*0.58), f_code, PURPLE)
    cx(draw, "shadowcypher.site", int(SZ*0.65), f_code, CYAN)

    img.save(f"{OUT}/d8-minimal-back.jpg", "JPEG", quality=95)
    print("d8-minimal-back.jpg saved")


if __name__ == "__main__":
    print("Generating 5 design sets...")
    design4_back()
    design5_back()
    design6_camo()
    design6_camo_front()
    design7_pink_front()
    design7_pink_back()
    design8_minimal_front()
    design8_minimal_back()
    print("\nAll design files ready.")
