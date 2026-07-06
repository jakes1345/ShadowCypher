#!/usr/bin/env python3
"""
Extract flat artwork from Voltic Pro AOP mockup renders.
Removes white background + white sleeve areas, autocrop, upscale, add SC branding.
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np

DESIGNS_DIR = "/home/jack/ShadowCypher/merch/designs"
FONT_PATH = "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf"

SC_PURPLE = (168, 85, 247)
SC_CYAN   = (0, 212, 255)
SHADOW    = (0, 0, 0, 180)
TARGET_SIZE = 4096

# White threshold: pixels with R,G,B all above this become transparent
WHITE_THRESHOLD = 230

DESIGNS = [
    {
        "input":  "sc-volticpro-design-3-3am-grind.png",
        "output": "sc-ch01-runtime-print.png",
        "chapter": "01",
        "lines": [
            ("//SHADOWCYPHER · CHAPTER 01", SC_PURPLE),
            ("while(alive) { grind(); }",   SC_PURPLE),
            ("03:17:00 — PROCESS RUNNING",  SC_CYAN),
        ],
    },
    {
        "input":  "sc-volticpro-design-1.png",
        "output": "sc-ch02-null-print.png",
        "chapter": "02",
        "lines": [
            ("//SHADOWCYPHER · CHAPTER 02",   SC_PURPLE),
            ("return null;",                  SC_PURPLE),
            ("ERROR 404: IDENTITY NOT FOUND", SC_CYAN),
        ],
    },
    {
        "input":  "sc-volticpro-design-2-standing-watch.png",
        "output": "sc-ch03-root-print.png",
        "chapter": "03",
        "lines": [
            ("//SHADOWCYPHER · CHAPTER 03", SC_PURPLE),
            ("DAEMON RUNNING: 24/7/365",    SC_PURPLE),
            ("sudo watch --interval=0",     SC_CYAN),
        ],
    },
]


def crop_body_only(img: Image.Image) -> Image.Image:
    """
    Hard-crop to the center body illustration, removing white sleeve columns.
    The sleeves occupy ~18% on each side. Crop to center ~64% width.
    Also remove the top ~8% (plain background above hood).
    """
    w, h = img.size
    left  = int(w * 0.17)
    right = int(w * 0.83)
    top   = int(h * 0.05)
    return img.crop((left, top, right, h))


def autocrop_transparent(img: Image.Image, padding=40) -> Image.Image:
    """Crop to bounding box of non-transparent pixels, with padding."""
    bbox = img.getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    w, h = img.size
    l = max(0, l - padding)
    t = max(0, t - padding)
    r = min(w, r + padding)
    b = min(h, b + padding)
    return img.crop((l, t, r, b))


def upscale_on_dark(img: Image.Image, size=TARGET_SIZE) -> Image.Image:
    """Place artwork (RGBA) centered on a dark navy background, scaled to fit."""
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 255))  # pure black — blends with black hoodie

    # Scale artwork to fit within size x size maintaining aspect ratio
    aw, ah = img.size
    scale = min(size / aw, size / ah) * 0.95  # 5% margin
    nw, nh = int(aw * scale), int(ah * scale)
    artwork = img.resize((nw, nh), Image.LANCZOS)

    x = (size - nw) // 2
    y = (size - nh) // 2
    bg.paste(artwork, (x, y), artwork)
    return bg


def load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def add_branding(img: Image.Image, lines) -> Image.Image:
    """Add SC branding text at bottom of image."""
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # 3 lines stacked at bottom
    font_sizes = [int(w * 0.022), int(w * 0.045), int(w * 0.022)]
    y_offsets  = [int(h * 0.80),  int(h * 0.84),  int(h * 0.90)]

    for i, (text, color) in enumerate(lines):
        font = load_font(font_sizes[i])
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (w - tw) // 2
        y = y_offsets[i]

        pad_x, pad_y = 20, 8
        draw.rectangle(
            [x - pad_x, y - pad_y, x + tw + pad_x, y + th + pad_y],
            fill=(8, 8, 26, 200)
        )
        # Shadow
        shadow_color = (0, 0, 0, 200)
        draw.text((x+3, y+3), text, font=font,
                  fill=shadow_color)
        draw.text((x, y), text, font=font,
                  fill=color + (255,) if len(color) == 3 else color)

    return img


def process(d):
    import os
    in_path  = os.path.join(DESIGNS_DIR, d["input"])
    out_path = os.path.join(DESIGNS_DIR, d["output"])

    print(f"  Loading {d['input']}...")
    img = Image.open(in_path)

    print(f"  Cropping to body only (removing sleeves)...")
    img = crop_body_only(img)

    print(f"  Placing on dark background + upscaling to {TARGET_SIZE}px...")
    img = upscale_on_dark(img)

    print(f"  Adding branding...")
    img = add_branding(img, d["lines"])

    print(f"  Saving → {d['output']}")
    img.convert("RGB").save(out_path, "PNG", optimize=False)
    print(f"  Done.")


for d in DESIGNS:
    print(f"\nProcessing Chapter {d['chapter']}...")
    process(d)

print("\nAll 3 print files ready.")
