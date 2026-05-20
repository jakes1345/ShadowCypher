#!/usr/bin/env python3
"""Render the v9 wallpaper set via headless Chromium.

Output: ../profile/airootfs/usr/share/backgrounds/shadowos/v9/*.png

Variants:
  v1  teal/purple/indigo (canonical)
  v2  crimson/pink/violet
  v3  ocean teal/indigo
  v4  amber/pink/violet
  v5  forest/teal/violet
  v6  monochrome subtle
Each rendered:
  - 1920x1080 + 3840x2160
  - Full (with diamond + wordmark + tagline)
  - Minimal (just wordmark watermark, no logo)
  - Login (darker, larger diamond ghost behind)
"""
from playwright.sync_api import sync_playwright
from pathlib import Path

HTML = Path(__file__).resolve().parent / "html_wallpapers" / "wallpaper.html"
OUT  = Path(__file__).resolve().parent.parent / "profile" / "airootfs" / \
        "usr" / "share" / "backgrounds" / "shadowos" / "v9"
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "login").mkdir(parents=True, exist_ok=True)

PALETTES = ["v1", "v2", "v3", "v4", "v5", "v6"]
MODES    = ["full", "minimal", "minimal2"]
SIZES    = [(1920, 1080), (3840, 2160)]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for size in SIZES:
            ctx = browser.new_context(viewport={"width": size[0], "height": size[1]},
                                       device_scale_factor=1)
            for pal in PALETTES:
                for mode in MODES:
                    page = ctx.new_page()
                    page.goto(f"file://{HTML}", wait_until="domcontentloaded",
                                timeout=20000)
                    classes = pal if mode == "full" else f"{pal} {mode}"
                    page.evaluate(f"document.body.className = '{classes}'")
                    # Let fonts settle
                    page.wait_for_timeout(800)
                    name = f"shadowos-{pal}-{mode}-{size[0]}x{size[1]}.png"
                    page.screenshot(path=str(OUT / name), full_page=False)
                    print(f"  {name} ({(OUT / name).stat().st_size//1024} KB)")
                    page.close()
            ctx.close()

        # Login variants: same but darker, larger diamond
        ctx = browser.new_context(viewport={"width": 1920, "height": 1080})
        for i, pal in enumerate(["v1", "v3", "v2"], 1):
            page = ctx.new_page()
            page.goto(f"file://{HTML}", wait_until="domcontentloaded", timeout=20000)
            page.evaluate(f"document.body.className = '{pal} minimal2'")
            # Dim the body slightly to make it lockscreen-feel
            page.evaluate("""
                const o = document.createElement('div');
                o.style.cssText = 'position:absolute;inset:0;background:rgba(0,0,0,0.35);z-index:99;';
                document.body.appendChild(o);
            """)
            page.wait_for_timeout(600)
            name = f"shadowos-login-{i:02d}-{pal}-1920x1080.png"
            page.screenshot(path=str(OUT / "login" / name), full_page=False)
            print(f"  login/{name}")
            page.close()
        ctx.close()
        browser.close()

    print(f"\nDone. Output: {OUT}")

if __name__ == "__main__":
    main()
