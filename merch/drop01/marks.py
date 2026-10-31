"""ShadowCypher vector marks, drawn on a 1000x1000 grid (centre x = 500)."""
from sclib import CYAN, ICE, VIOLET, VIOLET_DARK, VIOLET_DEEP

# Outer hood silhouette: pointed crown, sides of the head, draped neck,
# shoulders, and a V where the cloak opens over the chest.
HOOD_OUTER = (
    "M500 56 "
    "C584 84 664 148 704 248 "
    "C738 334 744 432 746 520 "
    "C748 598 764 652 806 694 "
    "C862 742 932 790 952 884 "
    "L952 904 L566 904 L500 808 L434 904 L48 904 L48 884 "
    "C68 790 138 742 194 694 "
    "C236 652 252 598 254 520 "
    "C256 432 262 334 296 248 "
    "C336 148 416 84 500 56 Z"
)
# Face opening (the void).
HOOD_FACE = (
    "M500 252 "
    "C584 266 646 340 654 448 "
    "C662 556 616 652 500 728 "
    "C384 652 338 556 346 448 "
    "C354 340 416 266 500 252 Z"
)
# Lit rim around the opening.
HOOD_RIM = (
    "M500 236 "
    "C594 252 662 334 671 450 "
    "C680 566 630 670 500 752 "
    "C370 670 320 566 329 450 "
    "C338 334 406 252 500 236 Z"
)
# Fold lines in the cloth.
FOLD_L = "M292 268 C268 350 262 440 262 528 C262 610 240 670 196 712"
FOLD_R = "M708 268 C732 350 738 440 738 528 C738 610 760 670 804 712"
DRAPE_L = "M330 760 C280 790 230 830 200 900"
DRAPE_R = "M670 760 C720 790 770 830 800 900"
CREST = "M500 56 C498 110 500 170 500 236"
# Eye slits, angled down toward the centre.
EYE_L = "M380 488 L478 514 C486 517 485 530 477 531 L396 524 C378 522 370 494 380 488 Z"
EYE_R = "M620 488 L522 514 C514 517 515 530 523 531 L604 524 C622 522 630 494 620 488 Z"


def hood_defs(uid: str = "h") -> str:
    return f"""
<linearGradient id="{uid}-cloth" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{VIOLET}"/>
  <stop offset="0.55" stop-color="{VIOLET_DEEP}"/>
  <stop offset="1" stop-color="{VIOLET_DARK}"/>
</linearGradient>
<linearGradient id="{uid}-side" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#000" stop-opacity="0.55"/>
  <stop offset="0.22" stop-color="#000" stop-opacity="0"/>
  <stop offset="0.78" stop-color="#000" stop-opacity="0"/>
  <stop offset="1" stop-color="#000" stop-opacity="0.55"/>
</linearGradient>
<linearGradient id="{uid}-rim" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#c4b5fd"/>
  <stop offset="0.45" stop-color="#9f7aea"/>
  <stop offset="1" stop-color="{VIOLET_DEEP}"/>
</linearGradient>
<linearGradient id="{uid}-light" x1="0" y1="0" x2="1" y2="0.3">
  <stop offset="0" stop-color="#fff" stop-opacity="0.16"/>
  <stop offset="0.42" stop-color="#fff" stop-opacity="0"/>
  <stop offset="0.6" stop-color="#000" stop-opacity="0"/>
  <stop offset="1" stop-color="#000" stop-opacity="0.38"/>
</linearGradient>
<radialGradient id="{uid}-void" cx="0.5" cy="0.45" r="0.6">
  <stop offset="0" stop-color="#05060a"/>
  <stop offset="1" stop-color="#000"/>
</radialGradient>
<filter id="{uid}-glow" x="-60%" y="-200%" width="220%" height="500%">
  <feGaussianBlur stdDeviation="14" result="b1"/>
  <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="b2"/>
  <feMerge><feMergeNode in="b1"/><feMergeNode in="b2"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<linearGradient id="{uid}-fadeg" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0.72" stop-color="#fff"/>
  <stop offset="1" stop-color="#fff" stop-opacity="0"/>
</linearGradient>
<mask id="{uid}-fade" maskUnits="userSpaceOnUse" x="0" y="0" width="1000" height="1000">
  <rect width="1000" height="1000" fill="url(#{uid}-fadeg)"/>
</mask>
<filter id="{uid}-soft" x="-20%" y="-20%" width="140%" height="140%">
  <feGaussianBlur stdDeviation="22"/>
</filter>
"""


def hood(uid: str = "h", glow: bool = True, eye: str = CYAN, fade: bool = True) -> str:
    """Full-colour hood mark as an SVG group in 1000x1000 units."""
    eyes = f'<path d="{EYE_L}" fill="{eye}"/><path d="{EYE_R}" fill="{eye}"/>'
    if glow:
        eyes = f'<g filter="url(#{uid}-glow)">{eyes}</g>'
    mask = f' mask="url(#{uid}-fade)"' if fade else ""
    return f"""
<g{mask}>
  <path d="{HOOD_OUTER}" fill="url(#{uid}-cloth)"/>
  <path d="{HOOD_OUTER}" fill="url(#{uid}-side)"/>
  <path d="{FOLD_L}" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="10" stroke-linecap="round"/>
  <path d="{FOLD_R}" fill="none" stroke="#000" stroke-opacity="0.35" stroke-width="10" stroke-linecap="round"/>
  <path d="{DRAPE_L}" fill="none" stroke="#000" stroke-opacity="0.3" stroke-width="8" stroke-linecap="round"/>
  <path d="{DRAPE_R}" fill="none" stroke="#000" stroke-opacity="0.3" stroke-width="8" stroke-linecap="round"/>
  <path d="{HOOD_OUTER}" fill="url(#{uid}-light)"/>
  <path d="{CREST}" fill="none" stroke="#ddd6fe" stroke-opacity="0.5" stroke-width="4" stroke-linecap="round"/>
  <path d="{HOOD_RIM}" fill="url(#{uid}-rim)"/>
  <path d="{HOOD_FACE}" fill="url(#{uid}-void)"/>
  {eyes}
</g>"""


def hood_flat(fill: str, face: str, eye: str) -> str:
    """Flat, limited-colour version for embroidery and one-colour prints."""
    return f"""
<g>
  <path d="{HOOD_OUTER}" fill="{fill}"/>
  <path d="{HOOD_FACE}" fill="{face}"/>
  <path d="{EYE_L}" fill="{eye}"/><path d="{EYE_R}" fill="{eye}"/>
</g>"""


def brackets(x: float, y: float, w: float, h: float, arm: float, stroke: float,
             color: str = CYAN) -> str:
    """The ShadowCypher corner-bracket frame (viewfinder motif)."""
    sw = stroke
    d = (f"M{x} {y+arm} L{x} {y} L{x+arm} {y} "
         f"M{x+w-arm} {y} L{x+w} {y} L{x+w} {y+arm} "
         f"M{x+w} {y+h-arm} L{x+w} {y+h} L{x+w-arm} {y+h} "
         f"M{x+arm} {y+h} L{x} {y+h} L{x} {y+h-arm}")
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="square" stroke-linejoin="miter"/>')
