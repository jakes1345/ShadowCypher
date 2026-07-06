#!/usr/bin/env python3
"""Add SC branding text overlays to Voltic Pro design PNGs."""

from PIL import Image, ImageDraw, ImageFont
import os

DESIGNS_DIR = "/home/jack/ShadowCypher/merch/designs"
FONT_PATH = "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf"

SC_PURPLE = (168, 85, 247, 255)
SC_CYAN   = (0, 212, 255, 255)
SHADOW    = (0, 0, 0, 180)

DESIGNS = [
    {
        "input":  "sc-volticpro-design-1.png",
        "output": "sc-volticpro-design-1-branded.png",
        "lines": [
            # (text, color, size, y_from_bottom)
            ("//SHADOWCYPHER · CHAPTER 02",    SC_PURPLE, 28, 120),
            ("return null;",                   SC_PURPLE, 64, 240),
            ("ERROR 404: IDENTITY NOT FOUND",  SC_CYAN,   28, 310),
        ],
    },
    {
        "input":  "sc-volticpro-design-2-standing-watch.png",
        "output": "sc-volticpro-design-2-branded.png",
        "lines": [
            ("//SHADOWCYPHER · CHAPTER 03",    SC_PURPLE, 28, 120),
            ("DAEMON RUNNING: 24/7/365",       SC_PURPLE, 52, 230),
            ("sudo watch --interval=0",        SC_CYAN,   28, 300),
        ],
    },
    {
        "input":  "sc-volticpro-design-3-3am-grind.png",
        "output": "sc-volticpro-design-3-branded.png",
        "lines": [
            ("//SHADOWCYPHER · CHAPTER 01",    SC_PURPLE, 28, 120),
            ("while(alive) { grind(); }",      SC_PURPLE, 52, 230),
            ("03:17:00 — PROCESS RUNNING",     SC_CYAN,   28, 300),
        ],
    },
]

def load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()

def add_text_shadow(draw, x, y, text, font, color, shadow_offset=3):
    # Drop shadow first
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=SHADOW)
    draw.text((x, y), text, font=font, fill=color)

def process_design(d):
    in_path  = os.path.join(DESIGNS_DIR, d["input"])
    out_path = os.path.join(DESIGNS_DIR, d["output"])

    img = Image.open(in_path).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for text, color, size, y_from_bottom in d["lines"]:
        font = load_font(size)
        # Measure text width
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        x = (w - text_w) // 2
        y = h - y_from_bottom

        # Subtle backing rect for readability
        pad_x, pad_y = 16, 8
        draw.rectangle(
            [x - pad_x, y - pad_y, x + text_w + pad_x, y + (bbox[3] - bbox[1]) + pad_y],
            fill=(8, 8, 26, 160)
        )
        add_text_shadow(draw, x, y, text, font, color)

    # Composite overlay onto original
    result = Image.alpha_composite(img, overlay).convert("RGB")
    result.save(out_path, "PNG", optimize=True)
    print(f"  saved → {d['output']}")

for d in DESIGNS:
    print(f"Processing {d['input']}...")
    process_design(d)

print("\nDone — 3 branded designs saved.")
