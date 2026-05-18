#!/usr/bin/env python3
"""Render GRUB theme assets for ShadowOS.

Outputs to ../profile/airootfs/usr/share/grub/themes/shadowos/:
  background.png         1920x1080 dark hex backdrop
  select_c.png, select_e.png, select_w.png, select_n.png, select_s.png,
  select_nw.png, select_ne.png, select_sw.png, select_se.png
       9-slice pixmap pieces for the selected menu item highlight
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "profile" / "airootfs" / "usr" / "share" / "grub" / "themes" / "shadowos"
OUT.mkdir(parents=True, exist_ok=True)

BG_OUTER = (5, 8, 12)
BG_INNER = (20, 27, 36)
GRID = (25, 34, 44)
TEAL = (0, 224, 164)


def hex_points(cx, cy, r):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]


def make_background(w=1920, h=1080):
    try:
        import numpy as np
        yy, xx = np.mgrid[0:h, 0:w]
        cx, cy = w / 2, h * 0.5
        rmax = max(w, h) * 0.85
        d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
        inner = np.array(BG_INNER, dtype=np.float32)
        outer = np.array(BG_OUTER, dtype=np.float32)
        rgb = (inner[None, None, :] + (outer - inner)[None, None, :] * d[..., None]).astype("uint8")
        base = Image.fromarray(rgb, mode="RGB").convert("RGBA")
    except ImportError:
        base = Image.new("RGBA", (w, h), BG_OUTER + (255,))

    # Hex grid
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    r = 40
    dx = r * math.sqrt(3)
    dy = r * 1.5
    row = 0
    y = -r
    while y < h + r:
        x_off = 0 if row % 2 == 0 else dx / 2
        x = -dx + x_off
        while x < w + dx:
            pts = hex_points(x, y, r)
            ld.line(pts + [pts[0]], fill=GRID + (130,), width=1)
            x += dx
        y += dy
        row += 1
    base.alpha_composite(layer)

    # Subtle teal spotlight at top
    try:
        import numpy as np
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.clip(np.hypot(xx - w / 2, yy - h * 0.15) / (h * 0.6), 0, 1)
        alpha = ((1 - d) ** 2 * 255 * 0.06).astype("uint8")
        overlay = np.zeros((h, w, 4), dtype="uint8")
        overlay[..., 0] = TEAL[0]
        overlay[..., 1] = TEAL[1]
        overlay[..., 2] = TEAL[2]
        overlay[..., 3] = alpha
        base.alpha_composite(Image.fromarray(overlay, mode="RGBA"))
    except Exception:
        pass

    return base.convert("RGB")


def make_select_pixmaps():
    """9-slice pixmap pieces for selected menu highlight.

    GRUB uses select_c (center), select_n/s/e/w (sides), select_nw/ne/sw/se (corners).
    For a simple highlight bar we just need transparent corners/edges and a teal center.
    """
    # Center: transparent with teal left-edge accent bar
    c = Image.new("RGBA", (1, 1), (0, 224, 164, 30))
    c.save(OUT / "select_c.png", "PNG")

    # Side strips — all 1px wide/tall, kept minimal
    n = Image.new("RGBA", (1, 1), (0, 224, 164, 0))
    n.save(OUT / "select_n.png", "PNG")
    Image.new("RGBA", (1, 1), (0, 224, 164, 0)).save(OUT / "select_s.png", "PNG")
    Image.new("RGBA", (1, 1), (0, 224, 164, 0)).save(OUT / "select_e.png", "PNG")
    # West: bright teal accent line on left edge
    Image.new("RGBA", (3, 1), (0, 224, 164, 255)).save(OUT / "select_w.png", "PNG")

    # Corners (transparent)
    for name in ["nw", "ne", "sw", "se"]:
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(OUT / f"select_{name}.png", "PNG")


def main():
    print(f"Output: {OUT}")
    make_background(1920, 1080).save(OUT / "background.png", "PNG", optimize=True)
    print("  background.png")
    make_select_pixmaps()
    print("  select_*.png (9 pieces)")
    print("Done.")


if __name__ == "__main__":
    main()
