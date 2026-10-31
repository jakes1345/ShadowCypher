"""Shared helpers for the ShadowCypher Drop 01 merch build.

Text is shaped with HarfBuzz and converted to outlines, so every SVG source
renders identically anywhere (no font dependency at print time).
"""
from __future__ import annotations

import io
import os
from functools import lru_cache

import resvg_py
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")

# ── Brand palette (matches shadowcypher.site styles.css + existing merch) ────
VOID = "#07080a"        # site --bg-base
GARMENT = "#0c0c0c"     # Printful Bella+Canvas / Gildan "Black" color_code
VIOLET = "#8b5cf6"      # site --accent-primary
VIOLET_DEEP = "#6d28d9"  # site --accent-secondary
VIOLET_DARK = "#2e1065"
CYAN = "#22e3ff"        # merch signal cyan (eyes, brackets)
ICE = "#f1f5f9"         # site --text-primary
SLATE = "#94a3b8"       # site --text-secondary
MUTED = "#64748b"       # site --text-muted


class Font:
    def __init__(self, file: str, wght: float | None = None):
        path = os.path.join(FONTS, file)
        tt = TTFont(path)
        if wght is not None and "fvar" in tt:
            tt = instantiateVariableFont(tt, {"wght": wght})
        buf = io.BytesIO()
        tt.save(buf)
        data = buf.getvalue()
        self.tt = TTFont(io.BytesIO(data))
        self.glyphset = self.tt.getGlyphSet()
        self.upm = self.tt["head"].unitsPerEm
        face = hb.Face(data)
        self.hbfont = hb.Font(face)
        self.order = self.tt.getGlyphOrder()

    def _shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf, {"kern": True, "liga": False})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        _, pos = self._shape(text)
        s = size / self.upm
        adv = sum(p.x_advance for p in pos) * s
        return adv + tracking * size * max(len(pos) - 1, 0)

    def path(self, text: str, size: float, x: float, y: float,
             tracking: float = 0.0, anchor: str = "start") -> str:
        """Return SVG path data for `text` with baseline at y.

        tracking is in em (0.1 = 10% of size added between glyphs).
        """
        infos, pos = self._shape(text)
        s = size / self.upm
        w = self.width(text, size, tracking)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        pen = SVGPathPen(self.glyphset)
        cx = x
        for info, p in zip(infos, pos):
            name = self.order[info.codepoint]
            t = TransformPen(pen, (s, 0, 0, -s, cx + p.x_offset * s, y - p.y_offset * s))
            self.glyphset[name].draw(t)
            cx += p.x_advance * s + tracking * size
        return pen.getCommands()


@lru_cache(maxsize=None)
def font(file: str, wght: float | None = None) -> Font:
    return Font(file, wght)


def display(w=700):   # big headline face
    return font("Unbounded[wght].ttf", w)


def grotesk(w=500):
    return font("SpaceGrotesk[wght].ttf", w)


def mono(w=500):
    return font("JetBrainsMono[wght].ttf", w)


def svg_doc(w: int, h: int, body: str, defs: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">\n<defs>{defs}</defs>\n{body}\n</svg>\n')


def render(svg: str, width: int, background: str | None = None) -> Image.Image:
    png = resvg_py.svg_to_bytes(svg_string=svg, width=width, background=background)
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def knockout(img: Image.Image, garment=(12, 12, 12), soft: int = 10) -> Image.Image:
    """Turn an artwork rendered ON the garment colour into a print file.

    DTG prints semi-transparent pixels badly on dark shirts (the white
    underbase shows through as a haze). So glows are baked against the real
    garment colour first, then only pixels that are effectively the garment
    colour become transparent. Everything that remains is opaque ink.
    """
    import numpy as np
    a = np.asarray(img.convert("RGB")).astype("int16")
    g = np.array(garment, dtype="int16")
    dist = np.abs(a - g).max(axis=2)
    alpha = np.clip((dist - 2) * (255 / max(soft, 1)), 0, 255).astype("uint8")
    out = np.dstack([a.astype("uint8"), alpha])
    return Image.fromarray(out, "RGBA")


def save_png(img: Image.Image, path: str, dpi=300):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, dpi=(dpi, dpi), optimize=True)
