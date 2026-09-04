#!/usr/bin/env python3
"""Generate text-only hoodie print previews."""

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf"
OUT_DIR   = "/home/jack/ShadowCypher/merch/designs"
SIZE      = 1200  # preview canvas

BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
CYAN   = (0, 212, 255)
PURPLE = (168, 85, 247)
GRAY   = (100, 100, 120)


def font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()


def centered_text(draw, text, y, f, color, img_w):
    bb = draw.textbbox((0, 0), text, font=f)
    x = (img_w - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=f, fill=color)
    return bb[3] - bb[1]  # height


# ── VARIANT A: Box Logo ───────────────────────────────────────────────────
def variant_a(chapter, code_line, chapter_name):
    img  = Image.new("RGB", (SIZE, SIZE), BLACK)
    draw = ImageDraw.Draw(img)

    # Main box
    bx1, by1, bx2, by2 = 120, 380, 1080, 580
    draw.rectangle([bx1, by1, bx2, by2], outline=WHITE, width=5)

    # "SHDW CYPH" inside box
    f_main = font(130)
    centered_text(draw, "SHDW CYPH", by1 + 30, f_main, WHITE, SIZE)

    # Chapter line below box
    f_ch = font(36)
    centered_text(draw, f"CHAPTER {chapter}  ·  {chapter_name}", by2 + 40, f_ch, CYAN, SIZE)

    # Code line
    f_code = font(32)
    centered_text(draw, code_line, by2 + 100, f_code, PURPLE, SIZE)

    return img


# ── VARIANT B: Stacked oversized ─────────────────────────────────────────
def variant_b(chapter, code_line, chapter_name):
    img  = Image.new("RGB", (SIZE, SIZE), BLACK)
    draw = ImageDraw.Draw(img)

    f_big  = font(220)
    f_ch   = font(38)
    f_code = font(34)

    # SHDW on one line, CYPH on next — tight stacked
    centered_text(draw, "SHDW", 240, f_big, WHITE, SIZE)
    centered_text(draw, "CYPH", 440, f_big, WHITE, SIZE)

    # Thin rule
    draw.rectangle([200, 690, 1000, 693], fill=CYAN)

    centered_text(draw, f"CHAPTER {chapter}  ·  {chapter_name}", 715, f_ch, CYAN, SIZE)
    centered_text(draw, code_line, 770, f_code, PURPLE, SIZE)

    return img


# ── VARIANT C: Minimal wordmark + chapter ────────────────────────────────
def variant_c(chapter, code_line, chapter_name):
    img  = Image.new("RGB", (SIZE, SIZE), BLACK)
    draw = ImageDraw.Draw(img)

    f_sc   = font(56)
    f_big  = font(90)
    f_ch   = font(32)
    f_code = font(28)

    # SC wordmark small top
    centered_text(draw, "SHADOWCYPHER", 300, f_sc, GRAY, SIZE)

    # Big chapter name
    centered_text(draw, chapter_name, 390, f_big, WHITE, SIZE)

    # Chapter number accent
    centered_text(draw, f"CH.{chapter}", 510, f_big, CYAN, SIZE)

    # Rule
    draw.rectangle([300, 640, 900, 642], fill=PURPLE)

    centered_text(draw, code_line, 665, f_code, PURPLE, SIZE)

    return img


CHAPTERS = [
    ("01", "while(alive) { grind(); }", "RUNTIME"),
    ("02", "return null;",              "NULL"),
    ("03", "sudo watch --interval=0",   "ROOT"),
]

for ch, code, name in CHAPTERS:
    variant_a(ch, code, name).save(f"{OUT_DIR}/preview-A-ch{ch}.png")
    variant_b(ch, code, name).save(f"{OUT_DIR}/preview-B-ch{ch}.png")
    variant_c(ch, code, name).save(f"{OUT_DIR}/preview-C-ch{ch}.png")
    print(f"CH{ch} done")

print("All previews saved.")
