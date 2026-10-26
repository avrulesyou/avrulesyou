"""Generator for assets/caption-{light,dark}.svg — an editorial field-note strip with a CSS typewriter.

Sits directly under the hero banner, so it borrows the banner's language: warm paper,
a hairline gold rule, a small compass mark, ink text. Lines alternate a gold caret
(the sunlit side) and a crimson caret (the storm side); the strip itself never changes.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "generator"))
from theme import AKATSUKI as AK, STRAW_HAT as SH, MODES, FONT_MONO, FONT_BODY  # noqa: E402

W, H = 840, 70
LINES = [
    ("sh", "I turn ambitious ideas into useful software."),
    ("ak", "AI Expert · Developing solutions since 2016"),
    ("sh", "Most of my battles are fought in private repos."),
    ("ak", "Currently sailing: building solutions for the public sector."),
]
FS = 16
CHAR_W = FS * 0.602  # SF Mono / Menlo / Consolas advance
TX, TY = 92, 41
SLOT = 4.0  # seconds per line
CYCLE = SLOT * len(LINES)
SHIFT = 2.0  # frame 0 lands mid-hold of line 1
TYPE_PCT = 8.5  # % of the cycle spent typing
HOLD_END = 23.0  # % where the line starts fading
OUT = 25.0


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;")


def caption(mode: str) -> str:
    m = MODES[mode]
    dark = mode == "dark"
    paper = "#12151C" if dark else "#FBF7EE"
    paper2 = "#171B23" if dark else "#F4EDDC"
    edge = "#2A2F3A" if dark else "#DDD2B8"
    ink = m["text"]
    muted = m["text_muted"]
    gold = SH["sun_glow"] if dark else "#B07F00"
    crimson = "#FF4D5A" if dark else AK["cloud_red"]
    rule = SH["sun_gold"]

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    a('<title id="t">Field note: I turn ambitious ideas into useful software.</title>')
    a(
        '<desc id="d">An editorial caption strip under the banner. A typewriter cycles four lines: '
        + esc(" / ".join(t for _, t in LINES))
        + "</desc>"
    )
    css = [
        ".cv{transform-box:view-box}",
        "@keyframes caret{0%,40%{opacity:1}55%,85%{opacity:.08}100%{opacity:1}}",
        ".caret{animation:caret 1.1s cubic-bezier(.45,.05,.55,.95) infinite}",
        f"@keyframes show{{0%,{HOLD_END}%{{opacity:1}}{OUT}%,100%{{opacity:0}}}}",
        "@keyframes needle{0%,100%{transform:rotate(-7deg)}50%{transform:rotate(7deg)}}",
        ".needle{transform-box:fill-box;transform-origin:50% 50%;animation:needle 5.3s cubic-bezier(.45,.05,.55,.95) infinite}",
        "@keyframes twk{0%,100%{opacity:.25;transform:scale(.7)}50%{opacity:1;transform:scale(1.05)}}",
        ".fb{transform-box:fill-box;transform-origin:center}",
    ]
    for i, (_, text) in enumerate(LINES):
        n = len(text)
        wpx = n * CHAR_W + 2
        delay = i * SLOT - SHIFT - CYCLE  # always negative, so frame 0 is deterministic
        css.append(f".l{i}{{animation:show {CYCLE:g}s cubic-bezier(.45,.05,.55,.95) {delay:g}s infinite}}")
        css.append(
            f"@keyframes type{i}{{0%{{transform:translateX(0);animation-timing-function:steps({n},end)}}"
            f"{TYPE_PCT}%,100%{{transform:translateX({wpx:.1f}px)}}}}"
        )
        css.append(f".c{i}{{transform:translateX({wpx:.1f}px);animation:type{i} {CYCLE:g}s cubic-bezier(.45,.05,.55,.95) {delay:g}s infinite}}")
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}}")

    a("<defs>")
    a("<style>" + "".join(css) + "</style>")
    a(
        f'<linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{paper}"/>'
        f'<stop offset="1" stop-color="{paper2}"/></linearGradient>'
    )
    a(
        f'<linearGradient id="rg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{rule}" stop-opacity="0"/>'
        f'<stop offset=".12" stop-color="{rule}"/><stop offset=".88" stop-color="{rule}"/><stop offset="1" stop-color="{rule}" stop-opacity="0"/></linearGradient>'
    )
    a('<clipPath id="txt"><rect x="84" y="12" width="612" height="46"/></clipPath>')
    a("</defs>")

    # paper strip with a hairline edge and a gold rule along the top
    a(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="6" fill="url(#pg)" stroke="{edge}"/>')
    a(f'<rect x="24" y="0" width="{W - 48}" height="2" fill="url(#rg)"/>')
    # faint grid, like a survey sheet
    grid = "".join(f"M{x},8V62" for x in range(120, W - 40, 60))
    grid_op = ".05" if dark else ".045"
    a(f'<path d="{grid}" stroke="{ink}" stroke-width="1" opacity="{grid_op}"/>')
    a(f'<path d="M78,14V56" stroke="{edge}" stroke-width="1"/>')

    # compass mark on the left (the Log Pose of the page)
    a(f'<g transform="translate(40 35)">')
    a(f'<circle r="18" fill="none" stroke="{gold}" stroke-width="1.2" opacity=".9"/>')
    a(f'<circle r="13.5" fill="none" stroke="{gold}" stroke-width=".6" opacity=".55"/>')
    ticks = "".join(
        f'M{18 * math.cos(k * math.pi / 4):.2f},{18 * math.sin(k * math.pi / 4):.2f}'
        f'L{14.5 * math.cos(k * math.pi / 4):.2f},{14.5 * math.sin(k * math.pi / 4):.2f}'
        for k in range(8)
    )
    a(f'<path d="{ticks}" stroke="{gold}" stroke-width="1.2"/>')
    a(f'<g class="needle"><path d="M0,-12L3.2,0L0,12L-3.2,0Z" fill="{crimson}"/><path d="M0,-12L3.2,0L-3.2,0Z" fill="{gold}"/></g>')
    a(f'<circle r="1.8" fill="{ink}"/>')
    a("</g>")

    # eyebrow and a small star on the right
    a(f'<text x="{W - 26}" y="23" text-anchor="end" font-family="{FONT_BODY}" font-size="9.5" font-weight="700" letter-spacing="2.2" fill="{muted}">FIELD NOTES</text>')
    a(f'<path class="fb" d="M{W - 26},40l1.6,4.2 4.2,1.6-4.2,1.6-1.6,4.2-1.6-4.2-4.2-1.6 4.2-1.6z" fill="{gold}" style="animation:twk 2.9s cubic-bezier(.45,.05,.55,.95) infinite"/>')

    # --- typewriter lines
    for i, (side, text) in enumerate(LINES):
        acc = gold if side == "sh" else crimson
        op = "1" if i == 0 else "0"
        a(f'<g class="l{i}" opacity="{op}" clip-path="url(#txt)">')
        a(f'<text x="{TX}" y="{TY}" font-family="{FONT_MONO}" font-size="{FS}" font-weight="600" fill="{ink}" '
          f'xml:space="preserve">{esc(text)}</text>')
        # cover slides right in character steps; the caret rides its left edge
        a(f'<g class="cv c{i}">')
        a(f'<rect x="{TX - 1}" y="18" width="{696 - TX}" height="32" fill="url(#pg)"/>')
        a(f'<rect class="caret" x="{TX + 1}" y="24" width="8" height="22" rx="1" fill="{acc}"/>')
        a("</g>")
        a("</g>")

    a("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    for mode in ("light", "dark"):
        p = REPO / "assets" / f"caption-{mode}.svg"
        p.write_text(caption(mode))
        print(p, p.stat().st_size)
