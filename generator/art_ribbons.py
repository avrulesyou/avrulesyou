"""Emit the static section-header ribbons: assets/arc-{1..5}-{light,dark}.svg (840x64).

Each ribbon is a folded banner: a Straw Hat medallion on the left, an Akatsuki
medallion on the right, the arc title in the centre and a slow shimmer sweep.
Edit ARCS below and re-run:  python3 generator/art_ribbons.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from theme import AKATSUKI as AK, FONT_DISPLAY, MODES, STRAW_HAT as SH  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
W, H = 840, 64

ARCS = {
    1: "ARC I — BOUNTY & BINGO BOOK",
    2: "ARC II — THE BATTLEFIELD",
    3: "ARC III — THREE-SWORD STYLE",
    4: "ARC IV — RINGS & HAKI",
    5: "LOG POSE",
}

AKA_CLOUD = (
    "M6,26C-3,26-3,13 7,13C6,3 20,0 25,8C29,-1 44,-1 46,9C53,4 63,10 60,18"
    "C67,20 65,30 57,30C50,30 48,26 44,27C40,31 30,32 25,28C20,31 10,31 6,26Z"
)
AKA_CURL = "M14,22C13,16 22,14 25,19M38,20C39,14 48,14 49,20"


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ribbon(n: int, mode: str) -> str:
    title = ARCS[n]
    m = MODES[mode]
    dark = mode == "dark"
    panel = "#141821" if dark else "#FFFDF7"
    gold_deep = "#8A6400" if not dark else "#6B5214"
    red_deep = "#7A0A14" if not dark else "#5A0810"
    text = m["text"]
    shadow_op = ".55" if dark else ".25"
    # approximate Impact advance (~0.5em) to place the flanking diamonds
    half = len(title) * 13.2 / 2 + 28

    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    a(f'<title id="t">{esc(title)}</title>')
    a(f'<desc id="d">Section ribbon "{esc(title)}" with a straw hat medallion on the left and a red cloud medallion on the right.</desc>')
    a("<defs>")
    a(
        "<style>"
        "@keyframes shim{0%{transform:translateX(-220px)}55%,100%{transform:translateX(1060px)}}"
        ".shim{animation:shim 7s cubic-bezier(.5,0,.3,1) infinite}"
        "@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.5px)}}"
        ".bob{animation:bob 3.7s cubic-bezier(.45,.05,.55,.95) infinite}"
        ".bob2{animation:bob 4.3s cubic-bezier(.45,.05,.55,.95) -1.2s infinite}"
        "@keyframes tw{0%,100%{opacity:.35}50%{opacity:1}}"
        ".tw{animation:tw 2.9s cubic-bezier(.45,.05,.55,.95) infinite}"
        "@keyframes spk{0%,100%{opacity:0;transform:scale(.3) rotate(0)}45%{opacity:1;transform:scale(1) rotate(45deg)}70%{opacity:0;transform:scale(.4) rotate(90deg)}}"
        ".spk{transform-box:fill-box;transform-origin:center}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        "</style>"
    )
    a(
        f'<linearGradient id="band" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SH["sun_gold"]}"/>'
        f'<stop offset=".2" stop-color="{panel}"/><stop offset=".8" stop-color="{panel}"/>'
        f'<stop offset="1" stop-color="{AK["cloud_red"]}"/></linearGradient>'
    )
    a(
        '<linearGradient id="bandShade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".35"/>'
        '<stop offset=".5" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="1" stop-color="#000000" stop-opacity=".14"/></linearGradient>'
    )
    a(
        '<linearGradient id="side" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#B07F00"/>'
        f'<stop offset=".45" stop-color="{SH["sun_gold"]}"/><stop offset=".55" stop-color="{AK["sharingan"]}"/>'
        f'<stop offset="1" stop-color="{AK["cloud_red"]}"/></linearGradient>'
    )
    a(
        '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="#FFFFFF" stop-opacity="{".18" if dark else ".75"}"/>'
        '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
    )
    a(
        '<radialGradient id="medL" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#FFF6D6"/>'
        f'<stop offset=".6" stop-color="{SH["sun_glow"]}"/><stop offset="1" stop-color="{SH["sun_gold"]}"/></radialGradient>'
    )
    a(
        f'<radialGradient id="medR" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#2A2A38"/>'
        f'<stop offset="1" stop-color="{AK["cloak"]}"/></radialGradient>'
    )
    a(
        '<linearGradient id="straw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F7DC93"/>'
        f'<stop offset=".6" stop-color="{SH["straw"]}"/><stop offset="1" stop-color="#B98D2E"/></linearGradient>'
    )
    a('<clipPath id="bandClip"><path d="M70,12 L770,12 L770,52 L70,52Z"/></clipPath>')
    a(
        '<filter id="sh" x="-10%" y="-30%" width="120%" height="160%">'
        f'<feDropShadow dx="0" dy="2" stdDeviation="1.6" flood-color="#000" flood-opacity="{shadow_op}"/></filter>'
    )
    a("</defs>")

    # folded tails behind the band
    a('<g filter="url(#sh)">')
    a(f'<path d="M14,20 L84,20 L84,58 L14,58 L28,39Z" fill="{gold_deep}"/>')
    a(f'<path d="M70,52 L84,58 L84,52Z" fill="#000" opacity=".35"/>')
    a(f'<path d="M826,20 L756,20 L756,58 L826,58 L812,39Z" fill="{red_deep}"/>')
    a(f'<path d="M770,52 L756,58 L756,52Z" fill="#000" opacity=".35"/>')
    # main band
    a('<path d="M70,12 L770,12 L770,52 L70,52Z" fill="url(#band)"/>')
    a("</g>")
    a('<path d="M70,12 L770,12 L770,52 L70,52Z" fill="url(#bandShade)"/>')
    a(f'<path d="M70,16.5 L770,16.5 M70,47.5 L770,47.5" stroke="{m["panel_edge"]}" stroke-width="1" stroke-dasharray="5 3" opacity=".9"/>')
    a(f'<path d="M70,12 L420,12 M70,52 L420,52" stroke="{SH["sun_gold"]}" stroke-width="2"/>')
    a(f'<path d="M420,12 L770,12 M420,52 L770,52" stroke="{AK["cloud_red"]}" stroke-width="2"/>')
    # shimmer sweep
    a('<g clip-path="url(#bandClip)"><rect class="shim" x="0" y="0" width="160" height="64" fill="url(#shine)" transform="translate(-220 0)"/></g>')

    # small sparkles drifting along the band (staggered prime-ish loops)
    for k, (sx_, sy_, d_, col) in enumerate([(120, 18, 5.3, SH["sun_glow"]), (300, 46, 7.1, "#FFFFFF"),
                                            (560, 18, 6.1, "#FFFFFF"), (720, 44, 4.7, AK["sharingan"])]):
        a(f'<path class="spk" d="M{sx_},{sy_ - 4}l1,3 3,1 -3,1 -1,3 -1,-3 -3,-1 3,-1z" fill="{col}" opacity="0" '
          f'style="animation:spk {d_}s cubic-bezier(.45,.05,.55,.95) {-k * 1.7:.1f}s infinite"/>')

    # flanking diamonds
    for sgn, col in ((-1, SH["sun_gold"]), (1, AK["cloud_red"])):
        cx = 420 + sgn * half
        a(f'<path d="M{cx:.1f},26 L{cx + 6:.1f},32 L{cx:.1f},38 L{cx - 6:.1f},32Z" fill="{col}"/>')
        a(f'<path d="M{cx + sgn * 12:.1f},32 L{cx + sgn * 60:.1f},32" stroke="{col}" stroke-width="2" stroke-linecap="round" opacity=".7"/>')
        a(f'<circle class="tw" cx="{cx + sgn * 70:.1f}" cy="32" r="2" fill="{col}"/>')

    # title: faction-coloured extrusion + crisp face
    base = (f'x="420" y="42" text-anchor="middle" font-family="{FONT_DISPLAY}" font-size="27" '
            f'letter-spacing="1.6"')
    a(f'<text {base} transform="translate(1.6 2)" fill="url(#side)">{esc(title)}</text>')
    a(f'<text {base} fill="{text}" stroke="{panel}" stroke-width="1" paint-order="stroke">{esc(title)}</text>')

    # left medallion: straw hat
    a('<g class="bob" filter="url(#sh)"><g transform="translate(44 32)">')
    a(f'<circle r="24" fill="url(#medL)" stroke="{SH["haki_black"]}" stroke-width="2.4"/>')
    a(f'<circle r="19.5" fill="none" stroke="#FFFFFF" stroke-width="1" opacity=".8"/>')
    a('<ellipse cx="0" cy="5" rx="17" ry="4.6" fill="url(#straw)" stroke="#6E4C0C" stroke-width="1.2"/>')
    a('<path d="M-10,5 Q-10,-9 0,-10 Q10,-9 10,5Z" fill="url(#straw)" stroke="#6E4C0C" stroke-width="1.2"/>')
    a(f'<path d="M-10,0 Q0,-2.4 10,0 L10,4 Q0,1.8 -10,4Z" fill="{SH["straw_band"]}"/>')
    a("</g></g>")

    # right medallion: Akatsuki red cloud
    a('<g class="bob2" filter="url(#sh)"><g transform="translate(796 32)">')
    a(f'<circle r="24" fill="url(#medR)" stroke="{AK["cloud_red"]}" stroke-width="2.4"/>')
    a(f'<circle r="19.5" fill="none" stroke="{AK["rinnegan"]}" stroke-width="1" opacity=".8"/>')
    a(f'<g transform="translate(-17.5 -9.5) scale(.56)"><path d="{AKA_CLOUD}" fill="{AK["cloud_red"]}" stroke="#FFFFFF" '
      f'stroke-width="3.4" stroke-linejoin="round"/><path d="{AKA_CURL}" fill="none" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round"/></g>')
    a("</g></g>")
    a("</svg>")
    return "\n".join(o)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for n in ARCS:
        for mode in ("light", "dark"):
            out = ASSETS / f"arc-{n}-{mode}.svg"
            out.write_text(ribbon(n, mode))
            print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size} B)")


if __name__ == "__main__":
    main()
