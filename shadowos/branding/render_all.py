#!/usr/bin/env python3
"""
Render the full ShadowOS wallpaper set:
  20 desktop wallpapers (4 themes × 5 palette variants)
  3 SDDM login-screen variants (darker, more diffuse)

Each rendered at 1920x1080 and 3840x2160.

Outputs to ../profile/airootfs/usr/share/backgrounds/shadowos/
plus thumbs/ for the visual index.

Run: python3 render_all.py
Requires: Pillow, optionally numpy (much faster).
"""
from __future__ import annotations
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "profile" / "airootfs" / "usr" / "share" / "backgrounds" / "shadowos"
LOGIN_DIR = OUT_DIR / "login"
THUMB_DIR = SCRIPT_DIR / "thumbs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOGIN_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)

SIZES = [(1920, 1080), (3840, 2160)]
LOGIN_SIZES = [(1920, 1080), (2560, 1440)]  # 4K login is overkill

# Resolve fonts — try multiple OS paths
def _find_font(candidates: list[str]) -> str:
    for p in candidates:
        if os.path.exists(p):
            return p
    return ImageFont.load_default()  # type: ignore[return-value]

FONT_BOLD = _find_font([
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
])
FONT_REG = _find_font([
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
])
FONT_MONO = _find_font([
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
])

# ── Palettes ──────────────────────────────────────────────────────────────────
@dataclass
class Palette:
    name: str
    bg_inner: tuple
    bg_outer: tuple
    accent: tuple       # primary accent
    accent2: tuple      # secondary accent (for gradients)
    grid: tuple
    text_bright: tuple
    text_dim: tuple

PALETTES = [
    Palette("teal",     (20, 27, 36),  (5, 8, 12),    (0, 224, 164),   (0, 185, 136),  (25, 34, 44),  (230, 237, 243), (107, 119, 133)),
    Palette("crimson",  (28, 14, 18),  (8, 4, 6),     (255, 70, 95),   (210, 50, 75),   (44, 24, 30),  (245, 232, 235), (140, 100, 110)),
    Palette("indigo",   (16, 18, 36),  (4, 5, 12),    (138, 124, 255), (110, 96, 215),  (28, 30, 50),  (230, 232, 248), (110, 110, 145)),
    Palette("amber",    (32, 22, 8),   (10, 8, 4),    (255, 170, 56),  (210, 135, 30),  (44, 34, 18),  (245, 238, 222), (140, 125, 95)),
    Palette("forest",   (12, 24, 18),  (4, 8, 6),     (88, 220, 138),  (60, 180, 110),  (22, 38, 30),  (228, 240, 232), (105, 130, 115)),
]

# Login: 3 darker variants drawn from the 5 palettes (most distinctive)
LOGIN_PALETTES = [PALETTES[0], PALETTES[2], PALETTES[1]]  # teal, indigo, crimson

# ── Common primitives (vectorized) ────────────────────────────────────────────
def radial_gradient(w: int, h: int, inner, outer, cx_pct=0.5, cy_pct=0.5, radius_pct=0.85) -> Image.Image:
    if HAS_NUMPY:
        yy, xx = np.mgrid[0:h, 0:w]
        cx, cy = w * cx_pct, h * cy_pct
        rmax = max(w, h) * radius_pct
        d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
        inner_arr = np.array(inner, dtype=np.float32)
        outer_arr = np.array(outer, dtype=np.float32)
        rgb = (inner_arr[None, None, :] + (outer_arr - inner_arr)[None, None, :] * d[..., None]).astype("uint8")
        return Image.fromarray(rgb, mode="RGB")
    # Fallback (slow)
    img = Image.new("RGB", (w, h), outer)
    px = img.load()
    cx, cy = w * cx_pct, h * cy_pct
    rmax = max(w, h) * radius_pct
    for y in range(h):
        for x in range(w):
            t = min(1.0, math.hypot(x - cx, y - cy) / rmax)
            px[x, y] = tuple(int(inner[i] + (outer[i] - inner[i]) * t) for i in range(3))
    return img


def linear_gradient(w: int, h: int, top, bot) -> Image.Image:
    if HAS_NUMPY:
        t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        top_arr = np.array(top, dtype=np.float32)
        bot_arr = np.array(bot, dtype=np.float32)
        rgb = (top_arr[None, None, :] + (bot_arr - top_arr)[None, None, :] * t).astype("uint8")
        rgb = np.broadcast_to(rgb, (h, w, 3)).copy()
        return Image.fromarray(rgb, mode="RGB")
    img = Image.new("RGB", (w, h), top)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def teal_spotlight(img: Image.Image, color, cx_pct=0.5, cy_pct=0.5, radius_pct=0.32, strength=0.10):
    if not HAS_NUMPY:
        return
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w * cx_pct, h * cy_pct
    rmax = max(w, h) * radius_pct
    d = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1)
    alpha = ((1 - d) ** 2 * 255 * strength).astype("uint8")
    overlay = np.zeros((h, w, 4), dtype="uint8")
    overlay[..., 0] = color[0]
    overlay[..., 1] = color[1]
    overlay[..., 2] = color[2]
    overlay[..., 3] = alpha
    img.alpha_composite(Image.fromarray(overlay, mode="RGBA"))


def hex_path(cx: float, cy: float, r: float):
    return [(cx + r * math.cos(math.radians(60 * i - 30)),
             cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]


def draw_hex_grid(img: Image.Image, radius: int, color, opacity: float):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = img.size
    dx = radius * math.sqrt(3)
    dy = radius * 1.5
    a = int(255 * opacity)
    stroke = (color[0], color[1], color[2], a)
    row = 0
    y = -radius
    while y < h + radius:
        x_off = 0 if row % 2 == 0 else dx / 2
        x = -dx + x_off
        while x < w + dx:
            pts = hex_path(x, y, radius)
            d.line(pts + [pts[0]], fill=stroke, width=1)
            x += dx
        y += dy
        row += 1
    img.alpha_composite(layer)


def draw_monogram(img: Image.Image, cx: int, cy: int, r: int, palette: Palette, letter: str = "S"):
    """Hex S monogram with gradient fill + accent border."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Gradient fill
    if HAS_NUMPY:
        size = r * 2 + 8
        strip = np.zeros((size, size, 4), dtype="uint8")
        top = (palette.bg_inner[0] + 6, palette.bg_inner[1] + 8, palette.bg_inner[2] + 12)
        bot = (palette.bg_outer[0] + 6, palette.bg_outer[1] + 8, palette.bg_outer[2] + 16)
        for yy in range(size):
            t = yy / max(1, size - 1)
            for i in range(3):
                strip[yy, :, i] = int(top[i] + (bot[i] - top[i]) * t)
            strip[yy, :, 3] = 255
        fill_img = Image.fromarray(strip, mode="RGBA")
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).polygon(hex_path(size / 2, size / 2, r), fill=255)
        fill_img.putalpha(mask)
        layer.paste(fill_img, (cx - size // 2, cy - size // 2), fill_img)
    else:
        d.polygon(hex_path(cx, cy, r), fill=palette.bg_inner)

    # Accent border
    d.line(hex_path(cx, cy, r) + [hex_path(cx, cy, r)[0]], fill=palette.accent + (255,), width=3)
    outer = hex_path(cx, cy, r * 1.06)
    d.line(outer + [outer[0]], fill=palette.accent + (90,), width=1)

    # Letter
    font = ImageFont.truetype(FONT_BOLD, int(r * 1.4))
    bb = d.textbbox((0, 0), letter, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1] - int(r * 0.05)), letter, font=font, fill=palette.text_bright + (255,))

    img.alpha_composite(layer)


def draw_centered_text(img: Image.Image, y: int, text: str, font_path: str, size: int, color, tracking: int = 0):
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size)
    widths = []
    for ch in text:
        bb = d.textbbox((0, 0), ch, font=font)
        widths.append(bb[2] - bb[0])
    total = sum(widths) + tracking * (len(text) - 1)
    x = (img.size[0] - total) / 2
    for ch, w in zip(text, widths):
        bb = d.textbbox((0, 0), ch, font=font)
        d.text((x - bb[0], y), ch, font=font, fill=color + (255,))
        x += w + tracking


def draw_corner_brackets(img: Image.Image, inset: int, size: int, width: int, color):
    d = ImageDraw.Draw(img)
    w, h = img.size
    c = color + (255,)
    for (x, y, dx_a, dy_a, dx_b, dy_b) in [
        (inset, inset, size, 0, 0, size),                                 # TL
        (w - inset, inset, -size, 0, 0, size),                             # TR
        (inset, h - inset, size, 0, 0, -size),                             # BL
        (w - inset, h - inset, -size, 0, 0, -size),                        # BR
    ]:
        d.line([(x, y), (x + dx_a, y + dy_a)], fill=c, width=width)
        d.line([(x, y), (x + dx_b, y + dy_b)], fill=c, width=width)


# ── Composition: Theme A — Hex Predator ────────────────────────────────────────
def theme_a_hex(w: int, h: int, palette: Palette, seed: int) -> Image.Image:
    base = radial_gradient(w, h, palette.bg_inner, palette.bg_outer, radius_pct=0.78).convert("RGBA")
    hex_r = max(28, int(h * 0.034))
    draw_hex_grid(base, hex_r, palette.grid, opacity=0.55)
    teal_spotlight(base, palette.accent, cx_pct=0.5, cy_pct=0.44, radius_pct=0.34, strength=0.14)

    cx, cy = w // 2, int(h * 0.44)
    r = int(h * 0.16)
    draw_monogram(base, cx, cy, r, palette)

    scale = h / 1080
    draw_centered_text(base, int(h * 0.66), "SHADOWOS", FONT_BOLD, int(60 * scale), palette.text_bright, tracking=int(10 * scale))
    draw_centered_text(base, int(h * 0.72), "ENTERPRISE  ·  PREDATOR  ·  SOVEREIGN",
                       FONT_REG, int(15 * scale), palette.text_dim, tracking=int(4 * scale))

    inset = int(40 * scale)
    draw_corner_brackets(base, inset, int(40 * scale), max(1, int(1.2 * scale)), palette.grid)
    return base.convert("RGB")


# ── Composition: Theme B — Code Matrix ────────────────────────────────────────
def theme_b_code(w: int, h: int, palette: Palette, seed: int) -> Image.Image:
    base = linear_gradient(w, h, palette.bg_inner, palette.bg_outer).convert("RGBA")

    # Scattered "code" lines — abstract mono text drift
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    scale = h / 1080
    font_size = max(10, int(13 * scale))
    font = ImageFont.truetype(FONT_MONO, font_size)
    snippets = [
        "0x" + "".join(rnd.choice("0123456789abcdef") for _ in range(8))
        for _ in range(140)
    ] + [
        f"#{rnd.randint(1000,9999)}:{rnd.choice(['SCAN','MAP','POLL','SYNC','TRACE','EXFIL','PROBE'])}"
        for _ in range(60)
    ]
    rnd.shuffle(snippets)
    line_h = int(font_size * 1.6)
    y = 20
    while y < h:
        x = rnd.randint(-40, 80)
        while x < w:
            s = snippets[(y * 7 + x) % len(snippets)]
            alpha = rnd.randint(20, 90)
            d.text((x, y), s, font=font, fill=palette.grid + (alpha,))
            x += rnd.randint(220, 360)
        y += line_h

    base.alpha_composite(layer)

    # Diagonal accent bar (subtle)
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    bd.polygon([(0, h * 0.78), (w, h * 0.86), (w, h * 0.88), (0, h * 0.80)],
               fill=palette.accent + (35,))
    base.alpha_composite(bar)

    teal_spotlight(base, palette.accent, cx_pct=0.5, cy_pct=0.42, radius_pct=0.40, strength=0.18)

    cx, cy = w // 2, int(h * 0.44)
    r = int(h * 0.15)
    draw_monogram(base, cx, cy, r, palette)

    draw_centered_text(base, int(h * 0.66), "SHADOWOS", FONT_BOLD, int(64 * scale), palette.text_bright, tracking=int(12 * scale))
    draw_centered_text(base, int(h * 0.72), "// SECURE  SHELL  //  ZERO  TRACE",
                       FONT_MONO, int(13 * scale), palette.text_dim, tracking=int(3 * scale))
    return base.convert("RGB")


# ── Composition: Theme C — Network Constellation ──────────────────────────────
def theme_c_constellation(w: int, h: int, palette: Palette, seed: int) -> Image.Image:
    base = radial_gradient(w, h, palette.bg_inner, palette.bg_outer, cy_pct=0.55, radius_pct=0.9).convert("RGBA")

    rnd = random.Random(seed)
    nodes = []
    # Cluster nodes loosely around center
    cx, cy = w / 2, h * 0.44
    for _ in range(60):
        # Polar offset
        angle = rnd.uniform(0, 2 * math.pi)
        radius = rnd.uniform(h * 0.12, h * 0.55)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle) * 0.75
        if 40 < x < w - 40 and 40 < y < h - 40:
            nodes.append((x, y))

    # Draw connections (each node connects to 2 nearest others)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, (x1, y1) in enumerate(nodes):
        dists = sorted(((math.hypot(x1 - x2, y1 - y2), j) for j, (x2, y2) in enumerate(nodes) if j != i))[:2]
        for _, j in dists:
            x2, y2 = nodes[j]
            dist = math.hypot(x1 - x2, y1 - y2)
            if dist > h * 0.5:
                continue
            alpha = int(80 * (1 - dist / (h * 0.5)))
            d.line([(x1, y1), (x2, y2)], fill=palette.accent + (alpha,), width=1)

    # Draw nodes
    for x, y in nodes:
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=palette.accent + (180,))
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=palette.text_bright + (255,))

    base.alpha_composite(layer)
    teal_spotlight(base, palette.accent, cx_pct=0.5, cy_pct=0.44, radius_pct=0.30, strength=0.20)

    # Central hub
    r = int(h * 0.13)
    draw_monogram(base, int(cx), int(cy), r, palette)

    scale = h / 1080
    draw_centered_text(base, int(h * 0.66), "SHADOWOS", FONT_BOLD, int(60 * scale), palette.text_bright, tracking=int(10 * scale))
    draw_centered_text(base, int(h * 0.72), "DISTRIBUTED  ·  ENCRYPTED  ·  RESILIENT",
                       FONT_REG, int(14 * scale), palette.text_dim, tracking=int(4 * scale))
    return base.convert("RGB")


# ── Composition: Theme D — Minimal Logo ───────────────────────────────────────
def theme_d_minimal(w: int, h: int, palette: Palette, seed: int) -> Image.Image:
    base = linear_gradient(w, h, palette.bg_inner, palette.bg_outer).convert("RGBA")

    # Very faint hex grid for texture
    hex_r = max(40, int(h * 0.048))
    draw_hex_grid(base, hex_r, palette.grid, opacity=0.18)

    # Vary monogram position by seed
    positions = [
        (0.5, 0.5),    # center
        (0.28, 0.5),   # left
        (0.72, 0.5),   # right
        (0.5, 0.35),   # upper
        (0.5, 0.62),   # lower
    ]
    px, py = positions[seed % len(positions)]
    cx, cy = int(w * px), int(h * py)
    r = int(h * 0.14)

    teal_spotlight(base, palette.accent, cx_pct=px, cy_pct=py, radius_pct=0.28, strength=0.18)
    draw_monogram(base, cx, cy, r, palette)

    # Single thin accent line beneath
    d = ImageDraw.Draw(base)
    line_y = cy + int(r * 1.5)
    d.line([(cx - r * 1.2, line_y), (cx + r * 1.2, line_y)], fill=palette.accent + (140,), width=1)

    # Bottom-left small wordmark
    scale = h / 1080
    font_small = ImageFont.truetype(FONT_BOLD, int(20 * scale))
    d.text((int(80 * scale), h - int(80 * scale)), "SHADOWOS", font=font_small, fill=palette.text_bright + (200,))
    font_micro = ImageFont.truetype(FONT_REG, int(12 * scale))
    d.text((int(80 * scale), h - int(50 * scale)), f"v0.3  ·  {palette.name.upper()}", font=font_micro, fill=palette.text_dim + (180,))
    return base.convert("RGB")


THEMES = [
    ("01-hex",     theme_a_hex),
    ("02-code",    theme_b_code),
    ("03-graph",   theme_c_constellation),
    ("04-minimal", theme_d_minimal),
]


# ── Login screen variants ─────────────────────────────────────────────────────
def render_login(w: int, h: int, palette: Palette, seed: int) -> Image.Image:
    """Darker, more diffuse — meant to be blurred by hyprlock."""
    base = radial_gradient(w, h, palette.bg_inner, palette.bg_outer, cy_pct=0.5, radius_pct=0.7).convert("RGBA")

    # Subtle hex grid
    hex_r = max(28, int(h * 0.04))
    draw_hex_grid(base, hex_r, palette.grid, opacity=0.30)

    # Larger, dimmer accent spotlight (so blur looks atmospheric, not bland)
    teal_spotlight(base, palette.accent, cx_pct=0.5, cy_pct=0.5, radius_pct=0.55, strength=0.10)

    # Faint monogram, larger, centered
    cx, cy = w // 2, h // 2
    r = int(h * 0.21)
    # Custom dimmer monogram
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.line(hex_path(cx, cy, r) + [hex_path(cx, cy, r)[0]], fill=palette.accent + (80,), width=2)
    font = ImageFont.truetype(FONT_BOLD, int(r * 1.3))
    bb = d.textbbox((0, 0), "S", font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1] - int(r * 0.05)), "S", font=font,
           fill=palette.text_bright + (60,))
    base.alpha_composite(layer)

    # Apply a slight global darken for "locked" feel
    if HAS_NUMPY:
        arr = np.array(base, dtype=np.int16)
        arr[..., :3] = np.clip(arr[..., :3] - 15, 0, 255)
        base = Image.fromarray(arr.astype("uint8"), mode="RGBA")

    return base.convert("RGB")


# ── Main loop ─────────────────────────────────────────────────────────────────
def make_thumb(img: Image.Image, max_w: int = 480) -> Image.Image:
    w, h = img.size
    ratio = max_w / w
    return img.resize((max_w, int(h * ratio)), Image.LANCZOS)


def main():
    print(f"Output dir: {OUT_DIR}")
    print(f"Login dir:  {LOGIN_DIR}")
    print(f"Thumb dir:  {THUMB_DIR}")
    print(f"NumPy: {'yes' if HAS_NUMPY else 'no (slow)'}")
    print()

    idx = 1
    # 4 themes × 5 palettes = 20 desktop wallpapers
    for theme_slug, render_fn in THEMES:
        for pal_i, palette in enumerate(PALETTES):
            seed = idx * 131
            for w, h in SIZES:
                img = render_fn(w, h, palette, seed)
                fname = f"shadowos-{idx:02d}-{theme_slug.split('-',1)[1]}-{palette.name}-{w}x{h}.png"
                path = OUT_DIR / fname
                img.save(path, "PNG", optimize=True)
                size_kb = path.stat().st_size // 1024
                print(f"  {fname}  ({size_kb} KB)")
                # Thumbnail from the 1080p version
                if w == 1920:
                    thumb = make_thumb(img)
                    thumb.save(THUMB_DIR / fname.replace(f"-{w}x{h}", "-thumb"), "PNG", optimize=True)
            idx += 1

    # 3 login variants
    print()
    print("Login variants:")
    for li, palette in enumerate(LOGIN_PALETTES, start=1):
        for w, h in LOGIN_SIZES:
            img = render_login(w, h, palette, li * 211)
            fname = f"shadowos-login-{li:02d}-{palette.name}-{w}x{h}.png"
            path = LOGIN_DIR / fname
            img.save(path, "PNG", optimize=True)
            size_kb = path.stat().st_size // 1024
            print(f"  {fname}  ({size_kb} KB)")

    # Default symlinks: wallpaper.png → first desktop, login.png → first login
    default_wp = OUT_DIR / "wallpaper.png"
    default_login = LOGIN_DIR / "default.png"
    # Pick: 01-hex-teal-1920x1080.png as desktop default
    src = OUT_DIR / "shadowos-01-hex-teal-1920x1080.png"
    if src.exists():
        if default_wp.exists() or default_wp.is_symlink():
            default_wp.unlink()
        default_wp.symlink_to(src.name)
        print(f"\ndefault wallpaper → {src.name}")
    src_login = LOGIN_DIR / "shadowos-login-01-teal-1920x1080.png"
    if src_login.exists():
        if default_login.exists() or default_login.is_symlink():
            default_login.unlink()
        default_login.symlink_to(src_login.name)
        print(f"default login     → {src_login.name}")

    print(f"\nDone. {20 * 2 + 3 * 2} files written.")


if __name__ == "__main__":
    main()
