"""A quiet closing horizon for assets/footer-{light,dark}.svg.

Historical scene annotations are retained; the closing composition now uses a
single editorial line, chart marks and the same harbor as the opening panorama.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "generator"))
from theme import AKATSUKI as AK, STRAW_HAT as SH, MODES, FONT_SERIF, FONT_BODY  # noqa: E402

W, H = 840, 120


def footer(mode: str) -> str:
    m = MODES[mode]
    dark = mode == "dark"
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    a('<title id="t">To be continued</title>')
    a('<desc id="d">A quiet closing horizon, with gold chart lines and a distant ink skyline. To be continued.</desc>')
    a('<defs><style>@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>')
    a(f'<linearGradient id="paper"><stop stop-color="{m["sky_left"]}"/><stop offset="1" stop-color="{m["panel"]}"/></linearGradient>')
    a('</defs>')
    a('<rect width="840" height="120" fill="url(#paper)"/>')
    # light sources: sun-glow left, red moon right
    a(f'<path d="M0,1H840" stroke="{m["panel_edge"]}" stroke-width="1"/>')
    a(f'<path d="M32,1H132" stroke="{SH["sun_gold"]}" stroke-width="2"/>')
    # far crows
    # sea: back wave (slow, right) then front wave (left)
    a(f'<path d="M477,104Q575,82 679,100T852,90M459,111Q575,90 679,107T852,98" fill="none" stroke="{m["text_muted"]}" stroke-width=".6" opacity=".3"/>')
    # cloud + straw hat, floating over the water
    for k in range(12):
        x, h = 592 + k * 18, 8 + k * 13 % 28
        a(f'<path d="M{x},96V{96-h}h{9 + k % 5}V96Z" fill="{m["text_muted"]}" opacity="{".3" if dark else ".2"}"/>')
    # sparkles
    a(f'<path d="M794,39V57M785,48H803" stroke="{SH["straw_band"]}" stroke-width=".8" opacity=".65"/>')
    # spray and embers lifting off the sea
    a(f'<path d="M510,79Q592,49 741,68" fill="none" stroke="{SH["sun_gold"]}" stroke-width=".8" stroke-dasharray="3 6" opacity=".6"/>')
    # "TO BE CONTINUED" arrow plate
    a(f'<text x="32" y="58" font-family="{FONT_SERIF}" font-size="31" fill="{m["text"]}">To be continued<tspan fill="{SH["straw_band"]}">…</tspan></text>')
    a(f'<text x="34" y="86" font-family="{FONT_BODY}" font-size="14" fill="{m["text_muted"]}">The next chapter is useful software.</text>')
    # manga panel frame
    a(f'<path d="M808,17H824V33" fill="none" stroke="{m["panel_edge"]}" stroke-width="1"/>')
    a('</svg>')
    return "\n".join(o)


if __name__ == "__main__":
    for mode in ("light", "dark"):
        p = REPO / "assets" / f"footer-{mode}.svg"
        p.write_text(footer(mode))
        print(p, p.stat().st_size)
