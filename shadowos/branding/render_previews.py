#!/usr/bin/env python3
"""Generate visual QA previews for ShadowOS:

  preview-wallpapers-grid.png    4x5 grid of all 20 desktop wallpapers
  preview-login-mock.png         mock of SDDM login (wallpaper + blur + input)
  preview-plymouth-frame.png     single frame of Plymouth boot animation
  preview-grub-mock.png          mock of the GRUB menu screen

These let us QA the design visually without booting the ISO.
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT.parent / "profile" / "airootfs"
WALL_DIR = PROFILE / "usr" / "share" / "backgrounds" / "shadowos"
LOGIN_DIR = WALL_DIR / "login"
OUT = ROOT / "previews"
OUT.mkdir(parents=True, exist_ok=True)

def _find(candidates):
    for p in candidates:
        if Path(p).exists():
            return p
    raise SystemExit(f"No font found: {candidates}")

FONT_BOLD = _find([
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
])
FONT_REG = _find([
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
])
FONT_MONO = _find([
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
])

TEAL = (0, 224, 164)
WHITE = (230, 237, 243)
DIM = (107, 119, 133)


# ── 1. Wallpaper grid ─────────────────────────────────────────────────────────
def make_grid():
    files = sorted([p for p in WALL_DIR.glob("shadowos-*-1920x1080.png")])
    assert len(files) == 20, f"expected 20 wallpapers, got {len(files)}"

    cols = 5
    rows = 4
    cell_w, cell_h = 480, 270  # 16:9 thumbs
    pad = 12
    label_h = 28
    W = cols * cell_w + (cols + 1) * pad
    H = rows * (cell_h + label_h + 4) + (rows + 1) * pad + 80

    canvas = Image.new("RGB", (W, H), (5, 8, 12))
    d = ImageDraw.Draw(canvas)

    title_font = ImageFont.truetype(FONT_BOLD, 28)
    d.text((pad + 8, 16), "SHADOWOS  ·  WALLPAPER SET  ·  20 VARIANTS", font=title_font, fill=WHITE)
    sub_font = ImageFont.truetype(FONT_REG, 14)
    d.text((pad + 8, 50), "4 themes (hex · code · graph · minimal) × 5 palettes (teal · crimson · indigo · amber · forest)",
           font=sub_font, fill=DIM)

    label_font = ImageFont.truetype(FONT_MONO, 11)

    for i, f in enumerate(files):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = 80 + pad + r * (cell_h + label_h + 4 + pad)
        img = Image.open(f).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        canvas.paste(img, (x, y))
        # Subtle border
        d.rectangle([x - 1, y - 1, x + cell_w, y + cell_h], outline=(35, 45, 60), width=1)
        # Filename label
        label = f.stem.replace("shadowos-", "").replace("-1920x1080", "")
        d.text((x + 2, y + cell_h + 4), label, font=label_font, fill=DIM)

    out = OUT / "preview-wallpapers-grid.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"  {out.name}  ({out.stat().st_size // 1024} KB)")


# ── 2. SDDM login mock ────────────────────────────────────────────────────────
def make_login_mock():
    src = LOGIN_DIR / "shadowos-login-01-teal-1920x1080.png"
    if not src.exists():
        print(f"  ! skip login mock — {src} missing")
        return

    base = Image.open(src).convert("RGBA")
    # SDDM blurs the background — simulate it
    base = base.filter(ImageFilter.GaussianBlur(radius=14))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    w, h = base.size

    # Logo wordmark at center-upper
    title = ImageFont.truetype(FONT_BOLD, 72)
    bb = d.textbbox((0, 0), "ShadowOS", font=title)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.32),
           "ShadowOS", font=title, fill=WHITE + (240,))

    # Time
    time_font = ImageFont.truetype(FONT_MONO, 110)
    bb = d.textbbox((0, 0), "21:34", font=time_font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.16),
           "21:34", font=time_font, fill=WHITE + (220,))

    # Input field pill
    inp_w, inp_h = 360, 56
    inp_x = (w - inp_w) // 2
    inp_y = int(h * 0.52)
    # Inner fill
    d.rounded_rectangle([inp_x, inp_y, inp_x + inp_w, inp_y + inp_h],
                        radius=28, fill=(17, 22, 29, 200), outline=TEAL + (255,), width=2)
    # Placeholder text
    pf = ImageFont.truetype(FONT_REG, 16)
    d.text((inp_x + 28, inp_y + 18), "password", font=pf, fill=(107, 119, 133, 220))
    # User chip
    user_font = ImageFont.truetype(FONT_BOLD, 18)
    user_text = "shadow"
    bb = d.textbbox((0, 0), user_text, font=user_font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], inp_y - 38),
           user_text, font=user_font, fill=WHITE + (240,))

    # Tagline (bottom)
    tag_font = ImageFont.truetype(FONT_MONO, 14)
    tag = "privacy is a posture"
    bb = d.textbbox((0, 0), tag, font=tag_font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.68),
           tag, font=tag_font, fill=(107, 119, 133, 180))

    # Power buttons row (top-right)
    pw_font = ImageFont.truetype(FONT_REG, 18)
    d.text((w - 200, 30), "⏻  ⟳  ⌖  ⓘ", font=pw_font, fill=DIM + (200,))

    base.alpha_composite(overlay)
    out = OUT / "preview-login-mock.png"
    base.convert("RGB").save(out, "PNG", optimize=True)
    print(f"  {out.name}  ({out.stat().st_size // 1024} KB)")


# ── 3. Plymouth frame ─────────────────────────────────────────────────────────
def make_plymouth_mock():
    """Single frame of the Plymouth animation at mid-rotation."""
    plym_dir = PROFILE / "usr" / "share" / "plymouth" / "themes" / "shadowos"
    if not (plym_dir / "background.png").exists():
        print(f"  ! skip plymouth mock — assets missing")
        return

    bg = Image.open(plym_dir / "background.png").convert("RGBA")
    # Scale to 1920x1080
    bg = bg.resize((1920, 1080), Image.LANCZOS)
    w, h = bg.size

    # Glow halo
    glow = Image.open(plym_dir / "logo-glow.png").convert("RGBA")
    glow_pos = ((w - glow.width) // 2, (h - glow.height) // 2 - 40)
    # ~0.45 alpha for the glow at this frame
    glow_dim = Image.new("RGBA", glow.size, (0, 0, 0, 0))
    glow_dim = Image.alpha_composite(glow_dim, glow)
    alpha = glow_dim.split()[3].point(lambda a: int(a * 0.45))
    glow_dim.putalpha(alpha)
    bg.alpha_composite(glow_dim, glow_pos)

    # Logo at full brightness
    logo = Image.open(plym_dir / "logo.png").convert("RGBA")
    bg.alpha_composite(logo, ((w - logo.width) // 2, (h - logo.height) // 2 - 40))

    # 12-dot orbit at ~mid-rotation
    dot = Image.open(plym_dir / "dot.png").convert("RGBA")
    cx, cy = w // 2, h // 2 - 40
    orbit_r = logo.width // 2 + 50
    phase = 1.7  # mid-frame
    for i in range(12):
        angle = phase * 2.0 + (i * 2 * math.pi / 12)
        dx = orbit_r * math.cos(angle)
        dy = orbit_r * math.sin(angle)
        rel = i / 12
        alpha = 0.15 + 0.85 * (1.0 - rel)
        dot_dim = dot.copy()
        a = dot_dim.split()[3].point(lambda v: int(v * alpha))
        dot_dim.putalpha(a)
        bg.alpha_composite(dot_dim,
                           (int(cx + dx - dot.width // 2),
                            int(cy + dy - dot.height // 2)))

    # Bottom status text mimicking Plymouth message
    d = ImageDraw.Draw(bg)
    mf = ImageFont.truetype(FONT_REG, 14)
    d.text((40, h - 60), "Initializing secure boot environment...", font=mf, fill=(107, 119, 133, 255))

    out = OUT / "preview-plymouth-frame.png"
    bg.convert("RGB").save(out, "PNG", optimize=True)
    print(f"  {out.name}  ({out.stat().st_size // 1024} KB)")


# ── 4. GRUB mock ──────────────────────────────────────────────────────────────
def make_grub_mock():
    grub_dir = PROFILE / "usr" / "share" / "grub" / "themes" / "shadowos"
    if not (grub_dir / "background.png").exists():
        print(f"  ! skip grub mock — assets missing")
        return

    bg = Image.open(grub_dir / "background.png").convert("RGBA")
    bg = bg.resize((1920, 1080), Image.LANCZOS)
    w, h = bg.size

    d = ImageDraw.Draw(bg)
    # Title
    title = ImageFont.truetype(FONT_BOLD, 56)
    bb = d.textbbox((0, 0), "SHADOWOS", font=title)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.14),
           "SHADOWOS", font=title, fill=WHITE + (255,))

    sub = ImageFont.truetype(FONT_REG, 16)
    sub_txt = "ENTERPRISE  ·  PREDATOR  ·  SOVEREIGN"
    bb = d.textbbox((0, 0), sub_txt, font=sub)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.19),
           sub_txt, font=sub, fill=DIM + (220,))

    # Menu items
    menu_font = ImageFont.truetype(FONT_REG, 22)
    items = [
        ("ShadowOS  (x86_64, uefi)", True),
        ("ShadowOS  (x86_64, uefi) — verbose + diag", False),
        ("ShadowOS  (x86_64, uefi) with speech", False),
        ("UEFI Shell", False),
        ("System reboot", False),
        ("System shutdown", False),
    ]
    y = int(h * 0.32)
    left_x = int(w * 0.18)
    width = int(w * 0.64)
    for label, sel in items:
        # Selected: subtle teal box + bright accent on left
        if sel:
            d.rectangle([left_x, y - 2, left_x + width, y + 38], fill=(0, 224, 164, 30))
            d.rectangle([left_x, y - 2, left_x + 3, y + 38], fill=TEAL + (255,))
            color = TEAL
        else:
            color = (156, 165, 179)
        d.text((left_x + 18, y + 4), label, font=menu_font, fill=color + (255,))
        y += 42

    # Bottom progress bar
    bar_y = int(h * 0.86)
    bar_x = int(w * 0.18)
    bar_w = int(w * 0.64)
    d.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 14], fill=(17, 22, 29, 255),
                outline=(31, 42, 54, 255), width=1)
    # 60% filled
    d.rectangle([bar_x + 2, bar_y + 2, bar_x + int(bar_w * 0.6), bar_y + 12],
                fill=TEAL + (255,))

    # Footer hint
    hint_font = ImageFont.truetype(FONT_REG, 13)
    hint = "[↑↓] navigate     [Enter] boot     [e] edit     [c] grub shell"
    bb = d.textbbox((0, 0), hint, font=hint_font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], h * 0.92),
           hint, font=hint_font, fill=(61, 70, 81, 255))

    out = OUT / "preview-grub-mock.png"
    bg.convert("RGB").save(out, "PNG", optimize=True)
    print(f"  {out.name}  ({out.stat().st_size // 1024} KB)")


# ── 5. Login wallpaper trio ───────────────────────────────────────────────────
def make_login_trio():
    files = sorted([p for p in LOGIN_DIR.glob("shadowos-login-*-1920x1080.png")])
    if not files:
        return
    cell_w, cell_h = 640, 360
    pad = 20
    label_h = 28
    W = len(files) * cell_w + (len(files) + 1) * pad
    H = cell_h + label_h + 80

    canvas = Image.new("RGB", (W, H), (5, 8, 12))
    d = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(FONT_BOLD, 24)
    d.text((pad + 8, 16), "SHADOWOS  ·  LOGIN SCREEN VARIANTS", font=title_font, fill=WHITE)
    sub = ImageFont.truetype(FONT_REG, 14)
    d.text((pad + 8, 46), "Designed to be blurred by hyprlock — darker, atmospheric.",
           font=sub, fill=DIM)

    label_font = ImageFont.truetype(FONT_MONO, 12)
    for i, f in enumerate(files):
        x = pad + i * (cell_w + pad)
        y = 76
        img = Image.open(f).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        canvas.paste(img, (x, y))
        d.rectangle([x - 1, y - 1, x + cell_w, y + cell_h], outline=(35, 45, 60), width=1)
        # Label
        label = f.stem.replace("shadowos-login-", "").replace("-1920x1080", "")
        d.text((x + 4, y + cell_h + 6), label, font=label_font, fill=DIM)

    out = OUT / "preview-login-trio.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"  {out.name}  ({out.stat().st_size // 1024} KB)")


def main():
    print(f"Output: {OUT}")
    make_grid()
    make_login_mock()
    make_login_trio()
    make_plymouth_mock()
    make_grub_mock()
    print("\nQA previews ready. Open them in any image viewer.")


if __name__ == "__main__":
    main()
