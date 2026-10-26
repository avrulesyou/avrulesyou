"""Original harbor-to-storm panorama for the Engineering Atlas.

The scene shares one horizon, with the name above the scenery and restrained
cartographic detail below. Historical scene annotations are preserved through
the restyle. Both themes are complete without animation or external resources.

Run: python3 generator/art_banner.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "generator"))
from theme import AKATSUKI as AK, STRAW_HAT as SH, MODES, FONT_SERIF, FONT_BODY  # noqa: E402

W, H = 840, 370
SINE = "cubic-bezier(.45,.05,.55,.95)"


def f(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def ship(dark):
    """An original coastal survey ship, with no character or insignia."""
    ink = SH["haki_black"]
    paper = SH["nika_white"]
    gold = SH["straw"]
    o = ['<g class="boat">']
    # masts first, behind the sails
    o.append(f'<path d="M0,0V-112M46,-2V-77M-37,-2V-57" stroke="{ink}" stroke-width="2.5"/>')
    # main sail (billows), with an original straw-hat emblem
    o.append(f'<path d="M-30,-98Q0,-104 31,-98Q22,-65 30,-28Q0,-24 -30,-28Q-22,-64 -30,-98Z" fill="{paper}" stroke="{ink}" stroke-width="1.2"/>')
    o.append(f'<path d="M-28,-96Q-21,-64 -28,-30L-18,-29Q-12,-62 -17,-100" fill="{gold}" opacity=".4"/>')
    o.append(f'<path d="M-23,-48Q0,-46 25,-48M-22,-88Q0,-91 25,-88" fill="none" stroke="{gold}" stroke-width="1"/>')
    o.append(f'<path d="M49,-72L80,-20H49Z" fill="{paper}" stroke="{ink}" stroke-width="1"/>')
    o.append(f'<path d="M-40,-53L-72,-12H-40Z" fill="{gold}" stroke="{ink}" stroke-width="1"/>')
    # pennant
    o.append(f'<path d="M1,-111L27,-107L1,-101Z" fill="{SH["straw_band"]}"/>')
    # rigging
    o.append(f'<path d="M0,-110L-80,-1M0,-110L88,-5M46,-76L96,-5" stroke="{ink}" stroke-width=".8" fill="none"/>')
    # hull
    o.append(f'<path d="M-82,-8Q-5,1 84,-9L101,-20Q97,9 68,21H-58Q-75,13 -82,-8Z" fill="{ink}" stroke="{gold}" stroke-width="1.2"/>')
    o.append(f'<path d="M-72,2Q-4,12 83,0M-62,11Q-2,18 70,10" fill="none" stroke="{gold}" stroke-width=".7" opacity=".6"/>')
    for x in range(-51, 62, 22):
        o.append(f'<rect x="{x}" y="1" width="5" height="4" rx="1" fill="{gold}"/>')
    # lion-ish figurehead: a round face ringed by a sun-burst mane
    o.append(f'<path d="M88,-14L99,-23L103,-13L96,-8Z" fill="{gold}" stroke="{ink}" stroke-width="1"/>')
    o.append('</g>')
    return "".join(o)


def banner(mode: str) -> str:
    m = MODES[mode]
    dark = mode == "dark"
    paper, ink, muted = m["panel"], m["text"], m["text_muted"]
    tower_ink = muted if dark else ink
    gold, straw, red = SH["sun_gold"], SH["straw"], SH["straw_band"]
    sea = AK["rain"] if dark else m["panel_edge"]
    sky_end = AK["cloak_soft"] if dark else m["panel_edge"]
    o = []
    a = o.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">')
    a('<title id="t">Abhishek Vishwakarma · Personal Engineering Atlas</title>')
    a('<desc id="d">An original panoramic harbor: a survey ship and a hat on the quay, warm sunlight across the water, and a distant skyline beneath crimson clouds, a red moon and fine rain. One continuous world, drawn in paper, ink and gold.</desc>')
    a('<defs><style>')
    # sun: rays turn while intensity breathes
    a(f'@keyframes shimmer{{0%,100%{{opacity:.55}}50%{{opacity:.85}}}}.shimmer{{animation:shimmer 11s {SINE} infinite}}')
    # ship: bob, sails in the wind, pennant flutter
    a(f'@keyframes tide{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-1.5px)}}}}.boat{{animation:tide 7.1s {SINE} infinite}}')
    # moon ripples + three-tomoe eye
    # crows: glide + flap
    # rain in three depth layers
    # embers
    # green slash trail over the planted katanas
    # lightning seam + spark: irregular multi-stop flicker
    # light sweep + lens flare across the name
    a('@media (prefers-reduced-motion:reduce){*{animation:none!important}}')
    a('</style>')
    a(f'<linearGradient id="sky" x1="0" y1="0" x2="1" y2=".7"><stop stop-color="{m["sky_left"]}"/><stop offset=".48" stop-color="{paper}"/><stop offset="1" stop-color="{sky_end}"/></linearGradient>')
    a(f'<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{paper}"/><stop offset="1" stop-color="{sea}"/></linearGradient>')
    a(f'<pattern id="grain" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r=".45" fill="{ink}" opacity=".08"/><circle cx="7" cy="8" r=".35" fill="{ink}" opacity=".06"/></pattern>')
    a(f'<pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M0,5L5,0" stroke="{paper}" stroke-width=".5" opacity=".22"/></pattern>')
    a('<clipPath id="frame"><rect width="840" height="370" rx="4"/></clipPath>')
    a('</defs><g clip-path="url(#frame)">')
    # ================= skies
    a('<rect width="840" height="370" fill="url(#sky)"/>')
    a(f'<path d="M0,218Q156,183 312,214T614,222T840,207V370H0Z" fill="{straw}" opacity=".08"/>')
    # ================= LEFT far: Nika sun with god rays and drum rings
    a(f'<circle cx="236" cy="224" r="47" fill="{gold}" opacity="{".8" if dark else ".65"}"/>')
    a(f'<circle cx="236" cy="224" r="56" fill="none" stroke="{gold}" stroke-width=".7" opacity=".45"/>')
    # LEFT far clouds
    a(f'<path d="M0,222C51,215 72,225 105,218S164,210 189,218M275,220C319,211 345,223 385,216" stroke="{paper}" stroke-width="7" fill="none" opacity=".7"/>')
    # ================= RIGHT far: red moon with ripple rings, speed lines, clouds
    a(f'<circle cx="745" cy="177" r="22" fill="{red}" opacity="{".75" if dark else ".6"}"/>')
    a(f'<circle cx="745" cy="177" r="29" fill="none" stroke="{red}" stroke-width=".7" opacity=".3"/>')
    a(f'<path d="M600,199C612,191 618,197 627,193C638,176 659,181 665,193C681,185 701,193 715,194C735,185 748,195 761,195L789,203C741,211 698,205 658,208C635,209 615,206 600,199Z" fill="{red}" opacity=".75"/>')
    a(f'<path d="M656,195C667,190 677,200 688,197M725,201Q749,193 766,201" fill="none" stroke="{paper}" stroke-width="1" opacity=".5"/>')
    # three-tomoe eye, large and spinning
    a(f'<path d="M461,161C544,143 672,149 804,131M472,166C560,150 674,156 804,139" stroke="{muted}" stroke-width=".6" fill="none" opacity=".16"/>')
    # ================= RIGHT mid: rainy tower skyline
    for layer in range(2):
        baseline = 265 + layer * 11
        for k in range(19):
            x = 412 + k * 25 - layer * 7
            h = 11 + (k * 29 + layer * 17) % 43
            if k in (7, 11, 15):
                h += 24
            w = 13 + (k * 7) % 11
            a(f'<path d="M{x},{baseline}V{baseline-h}h{w}V{baseline}Z" fill="{tower_ink}" opacity="{".13" if layer == 0 else ".48"}"/>')
            if layer:
                a(f'<path d="M{x},{baseline}V{baseline-h}h{w}V{baseline}Z" fill="url(#hatch)"/>')
                a(f'<path d="M{x+4},{baseline-h+5}v{max(2,h-10)}M{x+w-3},{baseline-h+5}v{max(2,h-10)}" stroke="{straw}" stroke-width=".6" opacity=".5"/>')
    # tallest spire with antenna
    a(f'<path d="M685,267V220H690V201H697V190H700V201H707V220H713V267Z" fill="{tower_ink}" opacity=".75"/>')
    a(f'<path d="M698,191V172M689,218H709M692,204H705M688,232H709M688,246H709" fill="none" stroke="{straw}" stroke-width=".8" opacity=".65"/>')
    # ================= LEFT mid: sea + ship
    a('<path d="M0,266Q213,253 420,268T840,264V370H0Z" fill="url(#water)"/>')
    a(f'<path d="M0,269Q213,256 420,271T840,267" fill="none" stroke="{muted}" stroke-width=".8" opacity=".5"/>')
    for k in range(22):
        y = 269 + k * 3.9
        half = 7 + k * 3.1
        x = 236 + math.sin(k * 2.3) * (3 + k)
        a(f'<path class="shimmer" d="M{f(x-half)},{f(y)}h{f(half*2)}" fill="none" stroke="{gold}" stroke-width="{f(1+k*.035)}"/>')
    for k in range(42):
        x = (k * 113) % 840
        y = 277 + (k * 17) % 85
        a(f'<path d="M{x},{y}h{12 + k % 23}" stroke="{muted}" stroke-width=".6" opacity=".25"/>')
    a(f'<g transform="translate(332 294) scale(.64)">{ship(dark)}</g>')
    a(f'<path d="M271,305Q305,310 358,304M257,309Q302,316 367,309" stroke="{paper}" stroke-width="1.2" fill="none" opacity=".8"/>')
    # crows gliding over the red-moon sky
    a(f'<path d="M553,205q6,-6 11,0q5,-7 10,-3M579,189q4,-4 8,0q3,-5 7,-2M533,195q3,-4 7,0q3,-4 6,-2" fill="none" stroke="{ink}" stroke-width="1" opacity=".55"/>')
    # ================= foregrounds
    # left shore: barrel with a straw hat, three planted katanas, green slash trail
    a(f'<path d="M0,315L121,302L238,324L322,370H0Z" fill="{SH["haki_black"]}" opacity=".95"/>')
    a(f'<path d="M0,315L121,302L238,324L322,370M0,331L127,315L281,350M0,347L129,329L273,366M55,309L143,370M100,305L197,370M159,309L257,370" fill="none" stroke="{straw}" stroke-width="1" opacity=".4"/>')
    a(f'<g transform="translate(111 315) rotate(-8)"><ellipse rx="31" ry="6.5" fill="{straw}" stroke="{ink}" stroke-width="1.2"/><path d="M-17,-1Q-18,-22 0,-22Q17,-22 17,-1Z" fill="{straw}" stroke="{ink}" stroke-width="1.2"/><path d="M-17,-8Q0,-4 17,-8V-2Q0,2 -17,-2Z" fill="{red}"/><path d="M-10,-17Q-2,-20 6,-17M-26,1Q0,7 26,1" stroke="{paper}" stroke-width=".8" fill="none" opacity=".65"/></g>')
    a(f'<path d="M28,312V272M22,276H34M191,316V290M186,293H196" stroke="{ink}" stroke-width="3"/>')
    # embers rising on the sunlit side
    # right ground with rods planted in it, near rain and a low drifting red cloud
    a(f'<path d="M723,370L760,343L785,339L804,318L840,312V370Z" fill="{SH["haki_black"]}" opacity=".8"/>')
    for k in range(28):
        x = 616 + (k * 37) % 220
        y = 216 + (k * 19) % 77
        a(f'<path d="M{x},{y}l-4,12" stroke="{muted}" stroke-width=".7" opacity=".3"/>')
    # ================= centre: lightning seam + clash spark
    a(f'<g fill="none" stroke="{muted}" opacity=".28"><path d="M416,355Q530,290 708,310T846,292" stroke-width=".8" stroke-dasharray="4 7"/><path d="M455,365Q586,314 735,326T849,315" stroke-width=".6"/><circle cx="535" cy="315" r="3" stroke-width=".8"/></g>')
    a(f'<g transform="translate(56 219)" stroke="{muted}" fill="none" opacity=".4"><circle r="29" stroke-width=".7"/><circle r="23" stroke-width=".5"/><path d="M0,-36V36M-36,0H36M-20,-20L20,20M-20,20L20,-20" stroke-width=".6"/><path d="M0,-24L5,0L0,24L-5,0Z" fill="{gold}" stroke-width=".7"/></g>')
    a('<rect width="840" height="370" fill="url(#grain)"/>')
    # ================= title block
    a(f'<path d="M38,37H62" stroke="{red}" stroke-width="2"/>')
    a(f'<text x="73" y="41" font-family="{FONT_BODY}" font-size="13" letter-spacing="3" fill="{muted}">ENGINEERING ATLAS</text>')
    a(f'<text x="36" y="111" font-family="{FONT_SERIF}" font-size="60" letter-spacing="-2" fill="{ink}">Abhishek Vishwakarma</text>')
    a(f'<path d="M40,137H800" stroke="{muted}" stroke-width=".6" opacity=".3"/><path d="M40,137H142" stroke="{gold}" stroke-width="1.8"/>')
    a(f'<path d="M14,28V14H28M812,14H826V28M14,342V356H28M812,356H826V342" fill="none" stroke="{muted}" stroke-width=".8" opacity=".4"/>')
    a('</g></svg>')
    return "\n".join(o)


if __name__ == "__main__":
    for mode in ("light", "dark"):
        p = REPO / "assets" / f"banner-{mode}.svg"
        p.write_text(banner(mode))
        print(p, p.stat().st_size)
