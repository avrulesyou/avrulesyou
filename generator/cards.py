"""Data-driven cards: Most Valued poster, Bingo Book page and the Rings & Haki strip.

Each renderer is ``render_x(stats: dict, mode: str) -> str`` and returns a complete,
self-contained SVG (no external resources, no JS, system fonts only).
"""
from __future__ import annotations

import base64
import calendar
import json
import math
from pathlib import Path

from theme import AKATSUKI as AK
from theme import FONT_BODY, FONT_DISPLAY, FONT_SERIF, MODES, POWER
from theme import STRAW_HAT as SH

from battlefield import matched_momentum, momentum_value

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Same serif family as FONT_SERIF, but Times first for lining figures in big numbers.
NUM_SERIF = "'Times New Roman','Georgia',serif"

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none !important;}}"


# --------------------------------------------------------------------------- helpers

def esc(s: object) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _int(x: object, default: int = 0) -> int:
    try:
        return int(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _f(x: float) -> str:
    """Compact number formatting for coordinates."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _count_label(value: object) -> str:
    n = _int(value)
    digits = str(abs(n))
    if len(digits) <= 5:
        return f"{n:,}"
    return f"{'-' if n < 0 else ''}{digits[0]}.{digits[1:3]}e{len(digits)-1}"


def est_w(text: str, fs: float, avg: float = 0.55) -> float:
    """Rough text width estimate: narrow punctuation counts less."""
    w = 0.0
    for ch in text:
        if ch in " .,:;'|!·-":
            w += 0.32
        elif ch.isupper() or ch.isdigit():
            w += avg * 1.12
        else:
            w += avg
    return w * fs


def wrap(text: str, maxw: float, fs: float, avg: float = 0.55) -> list:
    words = str(text).split()
    lines: list = []
    cur = ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if cur and est_w(trial, fs, avg) > maxw:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


def _svg(w: int, h: int, title: str, desc: str, body: str, css: str = "") -> str:
    out = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>'
        f"<style>{css}{REDUCED_MOTION}</style>{body}</svg>"
    )
    # Pure ASCII output: safe however the caller writes the file.
    return out.encode("ascii", "xmlcharrefreplace").decode("ascii")


def _mode(mode: str) -> str:
    return "dark" if mode == "dark" else "light"


def _name(stats: dict) -> str:
    return str(stats.get("name") or stats.get("login") or "Unknown Engineer").strip()


def _short_date(iso: object) -> str:
    s = str(iso or "")
    try:
        y, m, d = s[:10].split("-")
        return f"{calendar.month_abbr[int(m)]} {int(d)}"
    except (ValueError, IndexError):
        return ""


def _streak(stats: dict) -> tuple:
    st = stats.get("streak") or {}
    cur = _int(st.get("current"))
    if cur > 0:
        return cur, "Current streak"
    return _int(st.get("longest")), "Longest streak"


def _days(n: int) -> str:
    return f"{n} day" if n == 1 else f"{n} days"


def _avatar_uri(stats: dict) -> str:
    rel = stats.get("avatar")
    if not rel:
        return ""
    p = Path(str(rel))
    if not p.is_absolute():
        p = ROOT / p
    try:
        raw = p.read_bytes()
    except OSError:
        return ""
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif raw[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        mime = "image/webp"
    elif raw[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    else:
        return ""
    if len(raw) > 120_000:  # keep the card under the 200 KB budget
        return ""
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _months_since_join(stats: dict) -> list:
    monthly = stats.get("monthly") or {}
    keys = sorted(k for k in monthly if isinstance(k, str) and len(k) >= 7)
    jm = str(stats.get("joined") or "")[:7]
    seq = [(k, _int(monthly[k])) for k in keys if not jm or k >= jm]
    if not seq:
        seq = [(k, _int(monthly[k])) for k in keys]
    return seq


# ---------------------------------------------------------------- shared motifs

def straw_hat(cx: float, cy: float, s: float = 1.0, band: str = SH["straw_band"]) -> str:
    """Small straw hat icon centred on (cx, cy); s=1 is ~52 px wide."""
    return (
        f'<g transform="translate({_f(cx)} {_f(cy)}) scale({_f(s)})">'
        f'<ellipse cx="0" cy="6" rx="26" ry="7" fill="#B8862F"/>'
        f'<ellipse cx="0" cy="4.5" rx="25" ry="6" fill="{SH["straw"]}"/>'
        f'<path d="M-14,4 C-14,-12 14,-12 14,4 Z" fill="{SH["straw"]}" stroke="#B8862F" stroke-width="1"/>'
        f'<path d="M-14,1.5 C-13,-3 13,-3 14,1.5 L14,4.5 C9,6 -9,6 -14,4.5 Z" fill="{band}"/>'
        f'<path d="M-8,-7 C-5,-10 2,-11 6,-9" stroke="#FFF3C4" stroke-width="1.6" fill="none" '
        f'stroke-linecap="round" opacity="0.8"/>'
        f"</g>"
    )


CLOUD_D = ("M14,46 C3,46 1,31 12,28 C8,13 27,5 37,14 C41,1 63,1 67,14 C77,5 96,12 90,27 "
           "C101,30 99,46 86,46 C85,53 73,53 71,46 L33,46 C31,53 16,53 14,46 Z")


def red_cloud(x: float, y: float, w: float, opacity: float = 1.0, edge: str = AK["cloud_edge"],
              fill: str = AK["cloud_red"], extra: str = "") -> str:
    """Akatsuki red cloud with white outline; (x, y) is the top-left, w the width."""
    s = w / 100.0
    sw = 3.2 / s if s > 0 else 3
    return (
        f'<g transform="translate({_f(x)} {_f(y)}) scale({_f(s)})" opacity="{_f(opacity)}" {extra}>'
        f'<path d="{CLOUD_D}" fill="{fill}" stroke="{edge}" stroke-width="{_f(min(sw, 5))}" '
        f'stroke-linejoin="round"/>'
        f'<path d="M30,30 C34,22 44,24 42,32 M58,22 C64,16 72,22 68,28" fill="none" '
        f'stroke="{edge}" stroke-width="{_f(min(sw, 5) * 0.55)}" stroke-linecap="round" opacity="0.7"/>'
        f"</g>"
    )


def sharingan(cx: float, cy: float, r: float, ring: str = AK["tomoe"]) -> str:
    """Three-tomoe eye, centred at (cx, cy) with radius r. Spins via class 'spin'."""
    t = r * 0.17
    rr = r * 0.55
    tomoe = []
    for k in range(3):
        a = math.radians(-90 + k * 120)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        rot = -90 + k * 120 + 90
        tomoe.append(
            f'<g transform="translate({_f(x)} {_f(y)}) rotate({rot})">'
            f'<circle r="{_f(t)}" fill="{ring}"/>'
            f'<path d="M{_f(-t)},0 Q{_f(-t * 0.9)},{_f(-t * 2.4)} {_f(t * 1.9)},{_f(-t * 2.3)} '
            f'Q{_f(t * 0.6)},{_f(-t * 1.3)} {_f(t)},0 Z" fill="{ring}"/></g>'
        )
    return (
        f'<g class="spin">'
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="url(#shar)" stroke="{ring}" '
        f'stroke-width="{_f(r * 0.1)}"/>'
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(rr)}" fill="none" stroke="{ring}" '
        f'stroke-width="{_f(r * 0.04)}" opacity="0.6"/>'
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r * 0.2)}" fill="{ring}"/>'
        + "".join(tomoe) + "</g>"
    )


# ===================================================== 1. MOST VALUED poster

def _laurel(cx: float, cy: float, flip: bool) -> str:
    """Small gold laurel sprig (original drawing); flip mirrors it for the right side."""
    leaves = []
    for k in range(5):
        t = k / 4.0
        x = -6 + 10 * math.sin(t * 1.4)
        y = 16 - 32 * t
        ang = -35 + 25 * t
        leaves.append(f'<ellipse cx="{_f(x - 4)}" cy="{_f(y)}" rx="6" ry="2.6" '
                      f'transform="rotate({_f(ang)} {_f(x - 4)} {_f(y)})"/>')
        if k < 4:
            leaves.append(f'<ellipse cx="{_f(x + 4)}" cy="{_f(y - 3)}" rx="5.5" ry="2.4" '
                          f'transform="rotate({_f(-ang - 70)} {_f(x + 4)} {_f(y - 3)})"/>')
    sx = -1 if flip else 1
    return (
        f'<g transform="translate({_f(cx)} {_f(cy)}) scale({sx} 1)" fill="url(#foilV)" '
        f'stroke="#5A3A0C" stroke-width="0.5">'
        f'<path d="M-4,20 C-8,6 -6,-6 4,-18" fill="none" stroke="url(#foilV)" stroke-width="1.8"/>'
        + "".join(leaves) + "</g>"
    )


def _icon_calendar(cx: float, cy: float, ink: str, accent: str) -> str:
    x, y = cx - 9, cy - 8
    dots = "".join(f'<rect x="{_f(x + 3 + (k % 3) * 4.5)}" y="{_f(y + 7.5 + (k // 3) * 4)}" '
                   f'width="2.4" height="2.4" fill="{ink}"/>' for k in range(6))
    return (f'<rect x="{_f(x)}" y="{_f(y)}" width="18" height="16" rx="2.5" fill="none" stroke="{ink}" '
            f'stroke-width="1.5"/><rect x="{_f(x)}" y="{_f(y)}" width="18" height="5" rx="2" fill="{accent}"/>'
            f'<path d="M{_f(x + 4.5)},{_f(y - 2.5)} V{_f(y + 2)} M{_f(x + 13.5)},{_f(y - 2.5)} V{_f(y + 2)}" '
            f'stroke="{ink}" stroke-width="1.6" stroke-linecap="round"/>' + dots)


def _icon_flame(cx: float, cy: float) -> str:
    return (f'<g transform="translate({_f(cx)} {_f(cy)})">'
            f'<path d="M0,-10 C3,-5 9,-2 8,4 C7.5,8.5 4,10.5 0,10.5 C-4.5,10.5 -8,8 -8,3.5 '
            f'C-8,-1 -4,-2.5 -3,-6 C-1,-3.5 -0.5,-2 0,-10 Z" fill="url(#flame)" stroke="#7A2A08" '
            f'stroke-width="0.7"/>'
            f'<path d="M0,0 C2,2.5 4,4 3.5,6.5 C3,9 1.5,9.5 0,9.5 C-2,9.5 -3.5,8 -3.5,6 C-3.5,3.5 -1,2.5 0,0 Z" '
            f'fill="#FFE27A"/></g>')


def _icon_chain(cx: float, cy: float, ink: str, accent: str) -> str:
    return (f'<g transform="translate({_f(cx)} {_f(cy)}) rotate(-40)" fill="none" stroke-width="2.2">'
            f'<rect x="-11" y="-4" width="13" height="8" rx="4" stroke="{ink}"/>'
            f'<rect x="-2" y="-4" width="13" height="8" rx="4" stroke="{accent}"/></g>')


def _wax_seal(cx: float, cy: float, r: float) -> str:
    pts = []
    for k in range(28):
        a = math.pi * 2 * k / 28
        rr = r * (1 + 0.07 * math.sin(k * 2.3) + 0.04 * math.cos(k * 5.1))
        pts.append(f"{_f(cx + rr * math.cos(a))},{_f(cy + rr * math.sin(a))}")
    star = []
    for k in range(10):
        a = -math.pi / 2 + math.pi * k / 5
        rr = r * (0.42 if k % 2 == 0 else 0.18)
        star.append(f"{_f(cx + rr * math.cos(a))},{_f(cy + rr * math.sin(a))}")
    return (
        f'<g filter="url(#sealShadow)">'
        f'<polygon points="{" ".join(pts)}" fill="url(#wax)"/>'
        f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r * 0.7)}" fill="none" stroke="#6E0A12" '
        f'stroke-width="1.6" opacity="0.7"/>'
        f'<circle cx="{_f(cx - 0.6)}" cy="{_f(cy - 0.6)}" r="{_f(r * 0.7)}" fill="none" stroke="#FF9A8A" '
        f'stroke-width="0.6" opacity="0.6"/>'
        f'<polygon points="{" ".join(star)}" fill="#8E0F16" stroke="#F28B82" stroke-width="0.6"/>'
        f'<ellipse cx="{_f(cx - r * 0.35)}" cy="{_f(cy - r * 0.45)}" rx="{_f(r * 0.28)}" ry="{_f(r * 0.12)}" '
        f'fill="#FFF" opacity="0.35" transform="rotate(-30 {_f(cx - r * 0.35)} {_f(cy - r * 0.45)})"/>'
        f"</g>"
    )


def render_wanted(stats: dict, mode: str) -> str:
    mode = _mode(mode)
    m = MODES[mode]
    W, H = 410, 520
    PW, PH = 354, 484          # poster size
    PX, PY = 28, 18            # poster origin
    ink = "#2E1C10"
    ink2 = "#5A3A1E"
    red = "#A3161F"

    totals = stats.get("totals") or {}
    contrib = _int(totals.get("contributions"))
    name = _name(stats).upper()
    name = name if len(name) <= 28 else name[:25].rstrip() + "…"
    bounty = f"{contrib * 1_000_000:,}-" if len(str(abs(contrib))) <= 7 else _count_label(contrib * 1_000_000)
    active = _int(stats.get("active_days"))
    best = stats.get("best_day") or {}
    peak_n = _int(best.get("count"))
    peak_date = _short_date(best.get("date"))
    streak_n, streak_label = _streak(stats)
    avatar = _avatar_uri(stats)

    css = (
        ".sway{transform-origin:205px 34px;animation:sway 11s cubic-bezier(.45,.05,.55,.95) infinite;}"
        "@keyframes sway{0%,100%{transform:rotate(0deg);}50%{transform:rotate(0.2deg);}}"
        ".glow{opacity:.15}.shine{display:none}"
    )

    defs = f"""<defs>
<linearGradient id="paper" x1="0" y1="0" x2="0.35" y2="1">
 <stop offset="0" stop-color="#F6E6BE"/><stop offset="0.55" stop-color="#EDD6A2"/>
 <stop offset="1" stop-color="#E0C185"/></linearGradient>
<radialGradient id="burn" cx="0.5" cy="0.45" r="0.72">
 <stop offset="0.62" stop-color="#8A5A2B" stop-opacity="0"/>
 <stop offset="0.9" stop-color="#8A5A2B" stop-opacity="0.26"/>
 <stop offset="1" stop-color="#6B4019" stop-opacity="0.55"/></radialGradient>
<linearGradient id="bend" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#5A3A1E" stop-opacity="0.22"/>
 <stop offset="0.07" stop-color="#5A3A1E" stop-opacity="0"/>
 <stop offset="0.45" stop-color="#FFF8E6" stop-opacity="0.18"/>
 <stop offset="0.9" stop-color="#5A3A1E" stop-opacity="0"/>
 <stop offset="1" stop-color="#5A3A1E" stop-opacity="0.2"/></linearGradient>
<linearGradient id="lamp" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#FFE7A0" stop-opacity="0.10"/>
 <stop offset="1" stop-color="#3A1E05" stop-opacity="0.22"/></linearGradient>
<linearGradient id="flap" x1="1" y1="1" x2="0.55" y2="0.55">
 <stop offset="0" stop-color="#FFF6DD"/><stop offset="0.6" stop-color="#EBD3A0"/>
 <stop offset="1" stop-color="#B98F55"/></linearGradient>
<linearGradient id="foil" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#FFF6C8"/><stop offset="0.38" stop-color="#F6CB4A"/>
 <stop offset="0.58" stop-color="#D49A1A"/><stop offset="0.8" stop-color="#F2C443"/>
 <stop offset="1" stop-color="#A86F0E"/></linearGradient>
<linearGradient id="foilV" x1="0" y1="0" x2="1" y2="1">
 <stop offset="0" stop-color="#FFE58A"/><stop offset="0.5" stop-color="#C8901E"/>
 <stop offset="1" stop-color="#7A4E08"/></linearGradient>
<linearGradient id="shineG" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#FFF" stop-opacity="0"/><stop offset="0.5" stop-color="#FFF" stop-opacity="0.6"/>
 <stop offset="1" stop-color="#FFF" stop-opacity="0"/></linearGradient>
<linearGradient id="plate" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#F3DFAE"/><stop offset="0.5" stop-color="#E6C98C"/>
 <stop offset="1" stop-color="#D6B473"/></linearGradient>
<linearGradient id="tail" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="#B5352B"/><stop offset="1" stop-color="#7A1A14"/></linearGradient>
<linearGradient id="flame" x1="0" y1="1" x2="0" y2="0">
 <stop offset="0" stop-color="#F6B800"/><stop offset="0.6" stop-color="#E8590C"/>
 <stop offset="1" stop-color="#C1121F"/></linearGradient>
<radialGradient id="wax" cx="0.38" cy="0.32" r="0.75">
 <stop offset="0" stop-color="#E5484D"/><stop offset="0.55" stop-color="#B3121C"/>
 <stop offset="1" stop-color="#6E0A12"/></radialGradient>
<radialGradient id="tack" cx="0.35" cy="0.3" r="0.75">
 <stop offset="0" stop-color="#FF9A8A"/><stop offset="0.45" stop-color="{SH['luffy_red']}"/>
 <stop offset="1" stop-color="#7A0E14"/></radialGradient>
<radialGradient id="lantern" cx="0.5" cy="0.34" r="0.7">
 <stop offset="0" stop-color="{SH['sun_glow']}" stop-opacity="0.6"/>
 <stop offset="0.45" stop-color="{SH['sun_gold']}" stop-opacity="0.24"/>
 <stop offset="1" stop-color="{SH['sun_gold']}" stop-opacity="0"/></radialGradient>
<radialGradient id="photoVig" cx="0.5" cy="0.5" r="0.7">
 <stop offset="0.6" stop-color="#2E1C10" stop-opacity="0"/>
 <stop offset="1" stop-color="#2E1C10" stop-opacity="0.35"/></radialGradient>
<filter id="shadow" x="-10%" y="-10%" width="125%" height="125%">
 <feDropShadow dx="3" dy="7" stdDeviation="{6 if mode == 'light' else 8}" flood-color="#000"
  flood-opacity="{0.28 if mode == 'light' else 0.6}"/></filter>
<filter id="sealShadow" x="-30%" y="-30%" width="170%" height="170%">
 <feDropShadow dx="1" dy="2" stdDeviation="1.4" flood-color="#2E1C10" flood-opacity="0.45"/></filter>
<filter id="lift" x="-10%" y="-30%" width="120%" height="170%">
 <feDropShadow dx="0" dy="1.5" stdDeviation="1.2" flood-color="#2E1C10" flood-opacity="0.3"/></filter>
<filter id="grain" x="0" y="0" width="100%" height="100%">
 <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" result="n"/>
 <feColorMatrix in="n" type="matrix"
  values="0 0 0 0 0.33  0 0 0 0 0.2  0 0 0 0 0.08  1.6 0 0 0 -0.62" result="c"/>
 <feComposite in="c" in2="SourceGraphic" operator="in"/></filter>
<filter id="stain" x="0" y="0" width="100%" height="100%">
 <feTurbulence type="fractalNoise" baseFrequency="0.014" numOctaves="3" seed="11" result="n"/>
 <feColorMatrix in="n" type="matrix"
  values="0 0 0 0 0.55  0 0 0 0 0.35  0 0 0 0 0.12  2.4 0 0 0 -1.05" result="c"/>
 <feComposite in="c" in2="SourceGraphic" operator="in"/></filter>
<filter id="sepia" color-interpolation-filters="sRGB">
 <feColorMatrix type="matrix" values="
  0.152 0.512 0.052 0 0.20
  0.159 0.534 0.054 0 0.12
  0.142 0.477 0.048 0 0.06
  0 0 0 1 0"/>
 <feComponentTransfer><feFuncR type="gamma" exponent="1.1"/><feFuncG type="gamma" exponent="1.1"/>
  <feFuncB type="gamma" exponent="1.1"/></feComponentTransfer></filter>
<filter id="soft"><feGaussianBlur stdDeviation="2.2"/></filter>
<clipPath id="photoClip"><rect x="74" y="104" width="206" height="150"/></clipPath>
<clipPath id="titleClip"><text x="0" y="0" transform="translate(177 66) scale(0.74 1)" text-anchor="middle"
 font-family="{FONT_SERIF}" font-weight="bold" font-size="40">MOST VALUED</text></clipPath>
</defs>"""

    shape = f"M0,0 H{PW} V{PH - 34} L{PW - 34},{PH} H0 Z"

    # --- title: gold foil, thin dark outline, slow shine sweep, laurels, kicker
    title = (
        f'<text x="0" y="0" transform="translate(177.5 67.5) scale(0.74 1)" text-anchor="middle" '
        f'font-family="{FONT_SERIF}" font-weight="bold" font-size="40" fill="#3A230C" opacity="0.35">'
        f'MOST VALUED</text>'
        f'<text x="0" y="0" transform="translate(177 66) scale(0.74 1)" text-anchor="middle" '
        f'font-family="{FONT_SERIF}" font-weight="bold" font-size="40" fill="url(#foil)" '
        f'stroke="#3A230C" stroke-width="0.9" paint-order="stroke">MOST VALUED</text>'
        f'<g clip-path="url(#titleClip)"><g class="shine">'
        f'<rect x="0" y="30" width="22" height="44" fill="url(#shineG)" transform="skewX(-20)"/></g></g>'
        + _laurel(38, 52, False) + _laurel(316, 52, True)
        + f'<path d="M88,86 H116 M238,86 H266" stroke="{ink2}" stroke-width="1" opacity="0.7"/>'
        f'<path d="M119,86 l3,-3 3,3 -3,3 Z M229,86 l3,-3 3,3 -3,3 Z" fill="#B9800F"/>'
        f'<text x="177" y="91" text-anchor="middle" font-family="{FONT_SERIF}" font-weight="bold" '
        f'font-size="13" letter-spacing="3.4" fill="{ink2}">ENGINEER</text>'
    )

    # --- photo with a clean frame and corner brackets
    if avatar:
        photo = (
            f'<rect x="74" y="104" width="206" height="150" fill="#C9A877"/>'
            f'<g clip-path="url(#photoClip)" filter="url(#sepia)">'
            f'<image x="74" y="82" width="206" height="206" preserveAspectRatio="xMidYMid slice" '
            f'xlink:href="{avatar}"/></g>'
        )
    else:
        photo = (
            f'<rect x="74" y="104" width="206" height="150" fill="#D9BE8A"/>'
            f'<path d="M74,212Q126,201 177,212T280,212V254H74Z" fill="{SH["straw"]}"/>'
            f'<path d="M85,229h35M139,234h26M193,226h45M221,243h31" stroke="{SH["nika_white"]}" '
            f'stroke-width="1.2" fill="none" opacity=".6"/>'
            + straw_hat(177, 185, 1.65, band=SH["straw_band"])
        )
    bx0, by0, bx1, by1, bl = 66, 96, 288, 262, 16
    brackets = (
        f'M{bx0},{by0 + bl} V{by0} H{bx0 + bl} M{bx1 - bl},{by0} H{bx1} V{by0 + bl} '
        f'M{bx1},{by1 - bl} V{by1} H{bx1 - bl} M{bx0 + bl},{by1} H{bx0} V{by1 - bl}'
    )
    photo_block = (
        f'<rect x="70" y="100" width="214" height="158" fill="#F3E2BA" stroke="{ink}" stroke-width="1.2" '
        f'filter="url(#lift)"/>'
        + photo
        + f'<rect x="74" y="104" width="206" height="150" fill="url(#photoVig)"/>'
        f'<rect x="74" y="104" width="206" height="150" fill="none" stroke="{ink}" stroke-width="0.8" opacity="0.6"/>'
        f'<path d="{brackets}" fill="none" stroke="{ink}" stroke-width="2.4" stroke-linecap="square"/>'
    )

    # --- name (fit to width)
    name_fs = min(22.0, 290.0 / max(1, len(name) * 0.74))
    name_txt = (f'<text x="{PW / 2}" y="290" text-anchor="middle" font-family="{FONT_SERIF}" '
                f'font-weight="bold" font-size="{_f(name_fs)}" letter-spacing="1" fill="{ink}">'
                f"{esc(name)}</text>")

    # --- value on a ribbon plate, drawn Berry sign (B + two strokes)
    fs = 30.0
    def bw(f: float) -> float:
        num = sum(0.25 if c in ",." else 0.333 if c == "-" else 0.5 for c in bounty) * f
        return 0.667 * f + 0.22 * f + num
    while bw(fs) > 236 and fs > 16:
        fs -= 1
    x0 = PW / 2 - bw(fs) / 2
    pc, ph = 318, 38            # plate centre y, height
    by = pc + fs * 0.34
    plate = (
        f'<path d="M34,{pc - 12} H62 V{pc + 14} H34 L44,{pc + 1} Z" fill="url(#tail)"/>'
        f'<path d="M320,{pc - 12} H292 V{pc + 14} H320 L310,{pc + 1} Z" fill="url(#tail)"/>'
        f'<path d="M56,{pc + 14} L62,{pc + 19} V{pc + 14} Z M298,{pc + 14} L292,{pc + 19} V{pc + 14} Z" '
        f'fill="#5A100C"/>'
        f'<g filter="url(#lift)"><rect x="56" y="{pc - ph / 2}" width="242" height="{ph}" rx="3" '
        f'fill="url(#plate)" stroke="{ink2}" stroke-width="0.9"/></g>'
        f'<rect x="60" y="{pc - ph / 2 + 4}" width="234" height="{ph - 8}" rx="2" fill="none" '
        f'stroke="{ink2}" stroke-width="0.5" opacity="0.6"/>'
    )
    berry = (
        f'<text x="{_f(x0)}" y="{_f(by)}" font-family="{NUM_SERIF}" font-weight="bold" font-size="{_f(fs)}" '
        f'fill="{ink}">B</text>'
        f'<path d="M{_f(x0 + 0.24 * fs)},{_f(by - 0.86 * fs)} V{_f(by + 0.14 * fs)} '
        f'M{_f(x0 + 0.44 * fs)},{_f(by - 0.86 * fs)} V{_f(by + 0.14 * fs)}" stroke="{ink}" '
        f'stroke-width="{_f(fs * 0.055)}"/>'
        f'<text x="{_f(x0 + 0.887 * fs)}" y="{_f(by)}" font-family="{NUM_SERIF}" font-weight="bold" '
        f'font-size="{_f(fs)}" fill="{ink}">{esc(bounty)}</text>'
    )
    tagline = (f'<text x="{PW / 2}" y="358" text-anchor="middle" font-family="{FONT_SERIF}" '
               f'font-style="italic" font-size="15" textLength="292" lengthAdjust="spacingAndGlyphs" '
               f'fill="{ink2}">for shipping perfect software in record time</text>')

    # --- stat tiles
    tw_, th_, gap = 98, 66, 9
    tx0 = PW / 2 - (3 * tw_ + 2 * gap) / 2
    ty = 370
    peak_label = f"Peak · {peak_date}" if peak_date else "Peak day"
    tiles_data = [
        (_count_label(active), "", "Active days", _icon_calendar),
        (_count_label(peak_n), "", peak_label, None),
        (_count_label(streak_n), " day" if streak_n == 1 else " days", streak_label, _icon_chain),
    ]
    tiles = []
    for i, (val, unit, lab, _) in enumerate(tiles_data):
        x = tx0 + i * (tw_ + gap)
        cx = x + tw_ / 2
        tiles.append(
            f'<rect x="{_f(x)}" y="{ty}" width="{tw_}" height="{th_}" rx="6" fill="#FFF7E2" '
            f'fill-opacity="0.5" stroke="{ink2}" stroke-width="0.9" stroke-opacity="0.55"/>'
        )
        icy = ty + 14
        if i == 0:
            tiles.append(_icon_calendar(cx, icy, ink2, red))
        elif i == 1:
            tiles.append(_icon_flame(cx, icy))
        else:
            tiles.append(_icon_chain(cx, icy, ink2, red))
        unit_t = (f'<tspan font-family="{FONT_BODY}" font-weight="normal" font-size="14" '
                  f'fill="{ink2}">{esc(unit)}</tspan>' if unit else "")
        tiles.append(f'<text x="{_f(cx)}" y="{ty + 45}" text-anchor="middle" font-family="{NUM_SERIF}" '
                     f'font-weight="bold" font-size="26" fill="{ink}">{esc(val)}{unit_t}</text>')
        tiles.append(f'<text x="{_f(cx)}" y="{ty + 61}" text-anchor="middle" font-family="{FONT_BODY}" '
                     f'font-size="13.5" fill="{ink2}">{esc(lab)}</text>')

    # --- footer with wax seal accent
    foot_txt = "ENGINEERING ATLAS · FIELD EDITION"
    footer = (
        f'<path d="M58,446 H{PW - 40}" stroke="{ink2}" stroke-width="0.6" opacity="0.5"/>'
        f'<text x="{PW / 2 + 12}" y="463" text-anchor="middle" font-family="{FONT_SERIF}" font-weight="bold" '
        f'font-size="13" letter-spacing="1.2" textLength="250" lengthAdjust="spacing" fill="{ink2}">'
        f"{esc(foot_txt)}</text>"
    )
    seal = _wax_seal(36, 450, 17)

    # --- curled corner
    curl = (
        f'<path d="M{PW},{PH - 34} L{PW - 34},{PH} L{PW - 30},{PH - 8} Z" fill="#000" opacity="0.25" '
        f'filter="url(#soft)"/>'
        f'<path d="M{PW},{PH - 34} C{PW - 12},{PH - 30} {PW - 26},{PH - 26} {PW - 31},{PH - 31} '
        f'C{PW - 27},{PH - 25} {PW - 31},{PH - 12} {PW - 34},{PH} Z" fill="url(#flap)" '
        f'stroke="#A07C48" stroke-width="0.6"/>'
    )

    poster = (
        f'<clipPath id="posterClip"><path d="{shape}"/></clipPath>'
        f'<g filter="url(#shadow)"><path d="{shape}" fill="url(#paper)"/></g>'
        f'<g clip-path="url(#posterClip)">'
        f'<path d="{shape}" fill="#000" filter="url(#stain)" opacity="0.5"/>'
        f'<rect x="10" y="10" width="{PW - 20}" height="{PH - 20}" fill="none" stroke="{ink2}" '
        f'stroke-width="1.4" opacity="0.55"/>'
        f'<rect x="14" y="14" width="{PW - 28}" height="{PH - 28}" fill="none" stroke="{ink2}" '
        f'stroke-width="0.6" opacity="0.45"/>'
        + photo_block + name_txt + plate + berry + tagline + "".join(tiles) + footer
        + f'<path d="{shape}" fill="#000" filter="url(#grain)" opacity="0.45"/>'
        + f'<path d="{shape}" fill="url(#burn)"/>'
        + f'<path d="{shape}" fill="url(#bend)"/>'
        + (f'<path d="{shape}" fill="url(#lamp)"/>' if mode == "dark" else "")
        + title + seal
        + "</g>" + curl
    )
    tack = (
        f'<ellipse cx="{PW / 2 + 3}" cy="22" rx="8" ry="4" fill="#000" opacity="0.28" filter="url(#soft)"/>'
        f'<circle cx="{PW / 2}" cy="16" r="8" fill="url(#tack)" stroke="#5A0A10" stroke-width="0.8"/>'
        f'<ellipse cx="{PW / 2 - 2.5}" cy="13" rx="2.6" ry="1.6" fill="#FFF" opacity="0.75"/>'
    )

    bg = f'<rect width="{W}" height="{H}" fill="{m["page"]}"/>'
    if mode == "dark":
        bg += f'<rect class="glow" width="{W}" height="{H}" fill="url(#lantern)"/>'
    body = (
        defs + bg
        + f'<g class="sway"><g transform="rotate(-1 205 34)"><g transform="translate({PX} {PY})">'
        + poster + tack + "</g></g></g>"
    )
    peak_desc = f"peak day {peak_n} contributions on {peak_date}" if peak_date else f"peak day {peak_n}"
    desc = (f"One Piece style Most Valued Engineer poster for {_name(stats)}, for shipping perfect software "
            f"in record time. Valued at {bounty.rstrip('-')} berries: {contrib} contributions in the last "
            f"year times one million. {active} active days, {peak_desc}, {streak_label.lower()} "
            f"{_days(streak_n)}. Engineering Atlas field edition.")
    return _svg(W, H, f"Most Valued Engineer: {_name(stats)}", desc, body, css)


# ============================================================ 2. BINGO BOOK page

RANKS = [  # (upper bound exclusive, rank)
    (100, "First entries"),
    (250, "In progress"),
    (750, "Steady"),
    (1500, "Growing"),
    (3000, "Established"),
    (None, "Extensive"),
]


def _rank(total: int) -> str:
    for bound, name in RANKS:
        if bound is None or total < bound:
            return name
    return RANKS[-1][1]


def render_bingo(stats: dict, mode: str) -> str:
    mode = _mode(mode)
    m = MODES[mode]
    W, H = 410, 520
    PW, PH = 354, 484
    PX, PY = 28, 18
    c = dict(page=m["panel"], page2=m["panel_edge"], edge=m["panel_edge"],
             ink=m["text"], muted=m["text_muted"], crimson=POWER[mode][4],
             purple=SH["sun_gold"], purple_soft=SH["straw"], redact=m["panel_edge"],
             bar=POWER[mode][2], grid=m["panel_edge"], hanko=SH["straw_band"],
             hanko_ink=SH["nika_white"], cloud_op=0.04,
             cloud_edge=SH["straw_band"], box=m["panel"])

    totals = stats.get("totals") or {}
    total = _int(totals.get("contributions"))
    private = _int(totals.get("private"))
    public = _int(totals.get("public"))
    name = _name(stats).upper()
    name = name if len(name) <= 44 else name[:41].rstrip() + "…"
    village = str(stats.get("location") or "Not shared").strip()
    rank_title = _rank(total)

    css = (
        ".pulse{animation:pulse 7.1s cubic-bezier(.45,.05,.55,.95) infinite;}"
        "@keyframes pulse{0%,100%{opacity:.7;}50%{opacity:1;}}"
        ".rip{opacity:.2}.glow{opacity:.08}"
    )

    defs = f"""<defs>
<radialGradient id="shar" cx="0.4" cy="0.35" r="0.7">
 <stop offset="0" stop-color="#FF6B6E"/><stop offset="0.6" stop-color="{AK['sharingan']}"/>
 <stop offset="1" stop-color="#8E0F16"/></radialGradient>
<linearGradient id="gutter" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="#000" stop-opacity="{0.28 if mode == 'light' else 0.6}"/>
 <stop offset="0.07" stop-color="#000" stop-opacity="0.06"/>
 <stop offset="0.12" stop-color="#000" stop-opacity="0"/>
 <stop offset="0.96" stop-color="#000" stop-opacity="0"/>
 <stop offset="1" stop-color="#000" stop-opacity="0.12"/></linearGradient>
<linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0" stop-color="{c['crimson']}" stop-opacity="0.55"/>
 <stop offset="1" stop-color="{c['purple_soft']}" stop-opacity="0.08"/></linearGradient>
<linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
 <stop offset="0" stop-color="{c['purple_soft']}"/><stop offset="1" stop-color="{c['crimson']}"/></linearGradient>
<radialGradient id="aura" cx="0.5" cy="0.5" r="0.5">
 <stop offset="0" stop-color="{SH['sun_gold']}" stop-opacity="0.08"/>
 <stop offset="0.5" stop-color="{AK['cloud_red']}" stop-opacity="0.04"/>
 <stop offset="1" stop-color="{SH['sun_gold']}" stop-opacity="0"/></radialGradient>
<filter id="shadow" x="-10%" y="-10%" width="125%" height="125%">
 <feDropShadow dx="3" dy="7" stdDeviation="{6 if mode == 'light' else 8}" flood-color="#000"
  flood-opacity="{0.28 if mode == 'light' else 0.7}"/></filter>
<filter id="grain" x="0" y="0" width="100%" height="100%">
 <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4" result="n"/>
 <feColorMatrix in="n" type="matrix"
  values="0 0 0 0 {0.35 if mode == 'light' else 0.6}  0 0 0 0 {0.25 if mode == 'light' else 0.55}  0 0 0 0 {0.15 if mode == 'light' else 0.7}  1.5 0 0 0 -0.6" result="c"/>
 <feComposite in="c" in2="SourceGraphic" operator="in"/></filter>
<filter id="stamp" x="-5%" y="-5%" width="110%" height="110%">
 <feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="9" result="n"/>
 <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -8 0 0 0 5.75" result="holes"/>
 <feComposite in="SourceGraphic" in2="holes" operator="in"/></filter>
</defs>"""

    # page stack + gutter
    shape = f'x="0" y="0" width="{PW}" height="{PH}" rx="4"'
    page = (
        f'<rect x="7" y="6" width="{PW}" height="{PH}" rx="4" fill="{c["page2"]}" stroke="{c["edge"]}" stroke-width="0.8"/>'
        f'<rect x="3.5" y="3" width="{PW}" height="{PH}" rx="4" fill="{c["page2"]}" stroke="{c["edge"]}" stroke-width="0.8"/>'
        f'<g filter="url(#shadow)"><rect {shape} fill="{c["page"]}"/></g>'
        f'<rect {shape} fill="#000" filter="url(#grain)" opacity="{0.35 if mode == "light" else 0.25}"/>'
        + red_cloud(70, 236, 250, c["cloud_op"], edge=c["cloud_edge"])
        + f'<rect {shape} fill="url(#gutter)"/>'
        + f'<path d="M9,14 V{PH - 14}" stroke="{c["crimson"]}" stroke-width="1.2" stroke-dasharray="6 5" opacity="0.6"/>'
        + f'<rect x="0.5" y="0.5" width="{PW - 1}" height="{PH - 1}" rx="4" fill="none" stroke="{c["edge"]}"/>'
    )

    L, R = 30, PW - 22  # content box
    T = []
    lab = (f'font-family="{FONT_BODY}" font-size="13" font-weight="bold" letter-spacing="1.4" '
           f'fill="{c["muted"]}"')

    # header
    T.append(f'<text x="{L}" y="40" font-family="{FONT_SERIF}" font-size="24" letter-spacing=".5" '
             f'fill="{c["ink"]}">FIELD DOSSIER</text>')
    T.append(f'<text x="{L}" y="59" {lab}>ENGINEERING ATLAS</text>')
    T.append(f'<g transform="translate({R - 22} 38)" fill="none" stroke="{c["crimson"]}" stroke-width=".8">'
             f'<circle r="16"/><circle r="12"/><path d="M0,-20V20M-20,0H20M0,-13L3,0L0,13L-3,0Z"/></g>')
    T.append(f'<path d="M{L},72 H{R}" stroke="{c["crimson"]}" stroke-width="1.6"/>')
    T.append(f'<path d="M{L},75.5 H{R}" stroke="{c["crimson"]}" stroke-width="0.6" opacity="0.7"/>')

    # name
    name_fs = min(28.0, (R - L) / max(1, len(name) * 0.52))
    T.append(f'<text x="{L}" y="96" {lab}>NAME</text>')
    T.append(f'<text x="{L}" y="{_f(98 + name_fs)}" font-family="{FONT_DISPLAY}" font-size="{_f(name_fs)}" '
             f'letter-spacing="1" fill="{c["ink"]}">{esc(name)}</text>')

    # fields + hanko
    val = f'font-family="{FONT_SERIF}" font-size="18" font-weight="bold" fill="{c["ink"]}"'
    T.append(f'<text x="{L}" y="150" {lab}>LOCATION</text>')
    T.append(f'<text x="{L}" y="171" {val}>{esc(village)}</text>')
    T.append(f'<text x="{L}" y="196" {lab}>CALENDAR</text>')
    T.append(f'<text x="{L}" y="217" {val}>{esc(rank_title)} '
             f'<tspan font-size="15" font-weight="normal" fill="{c["muted"]}">· {_count_label(total)} contributions</tspan></text>')

    hx, hy = R - 46, 172
    ripples = "".join(
        f'<circle cx="{hx}" cy="{hy}" r="{rr}" fill="none" stroke="{c["purple_soft"]}" '
        f'stroke-width="{1.6 if k % 2 == 0 else 0.8}" opacity="{_f(0.75 - k * 0.12)}"/>'
        for k, rr in enumerate((30, 37, 44, 51, 58))
    )
    T.append(f'<circle cx="{hx}" cy="{hy}" r="62" fill="url(#aura)"/>')
    T.append(f'<g class="rip">{ripples}</g>')
    words = rank_title.upper().split()
    st_fs = min(22.0, 56.0 / max(1, max(len(w) for w in words) * 0.5))
    lh = st_fs * 1.02
    y0 = hy + st_fs * 0.36 - (len(words) - 1) * lh / 2
    stamp_txt = "".join(
        f'<text x="{hx}" y="{_f(y0 + k * lh)}" text-anchor="middle" font-family="{FONT_DISPLAY}" '
        f'font-size="{_f(st_fs)}" letter-spacing="0.6" fill="{c["hanko_ink"]}">{esc(w)}</text>'
        for k, w in enumerate(words)
    )
    T.append(
        f'<g transform="rotate(-8 {hx} {hy})" filter="url(#stamp)">'
        f'<rect x="{hx - 38}" y="{hy - 38}" width="76" height="76" rx="6" fill="{c["hanko"]}"/>'
        f'<rect x="{hx - 33}" y="{hy - 33}" width="66" height="66" rx="3" fill="none" '
        f'stroke="{c["hanko_ink"]}" stroke-width="1.6"/>'
        + stamp_txt + "</g>"
    )

    T.append(f'<text x="{L}" y="242" {lab}>SPECIALTY</text>')
    T.append(f'<text x="{L}" y="262" font-family="{FONT_BODY}" font-size="15.5" font-weight="600" '
             f'fill="{c["ink"]}">Software engineering since 2016</text>')

    # classified block
    by0, bh = 272, 60
    T.append(f'<rect x="{L}" y="{by0}" width="{R - L}" height="{bh}" rx="3" fill="{c["box"]}" '
             f'stroke="{c["crimson"]}" stroke-width="1.4"/>')
    T.append(f'<text x="{L + 12}" y="{by0 + 20}" font-family="{FONT_BODY}" font-size="13" font-weight="bold" '
             f'letter-spacing="1.4" fill="{c["crimson"]}">PRIVATE ACTIVITY</text>')
    T.append(f'<text x="{L + 12}" y="{by0 + 52}" font-family="{FONT_DISPLAY}" font-size="32" '
             f'letter-spacing="1" fill="{c["ink"]}">{_count_label(private)}</text>')
    rx0 = L + 106
    bars_w = [(0, 150), (0, 96), (60, 110)]
    redact = []
    for k, (off, w) in enumerate(bars_w):
        y = by0 + 28 + k * 10
        w = min(w, R - 12 - (rx0 + off))
        redact.append(f'<rect x="{rx0 + off}" y="{y}" width="{w}" height="7" rx="1" fill="{c["redact"]}"/>')
    T.append("".join(redact))
    T.append(f'<text x="{R - 10}" y="{by0 + 20}" text-anchor="end" font-family="{FONT_BODY}" font-size="13" '
             f'fill="{c["muted"]}">public: {_count_label(public)}</text>')

    # charts
    cy0, cy1 = 368, 404           # bar/area vertical extent
    T.append(f'<text x="{L}" y="350" font-family="{FONT_BODY}" font-size="13" font-weight="bold" '
             f'fill="{c["ink"]}">Focus by weekday</text>')
    wk = list(stats.get("weekday_totals") or [0] * 7)
    wk = ([_int(v) for v in wk] + [0] * 7)[:7]
    order = [1, 2, 3, 4, 5, 6, 0]
    letters = ["M", "T", "W", "T", "F", "S", "S"]
    vals = [wk[i] for i in order]
    vmax = max(vals) if vals else 0
    lw = 150
    step = lw / 7
    bw = 12
    for k, v in enumerate(vals):
        bx = L + k * step + (step - bw) / 2
        h = (cy1 - cy0) * (v / vmax) if vmax else 0
        h = max(h, 1.5)
        top = v == vmax and vmax > 0
        fill = c["crimson"] if top else c["bar"]
        T.append(f'<rect x="{_f(bx)}" y="{_f(cy1 - h)}" width="{bw}" height="{_f(h)}" rx="2" fill="{fill}"/>')
        T.append(f'<text x="{_f(bx + bw / 2)}" y="{cy1 + 17}" text-anchor="middle" font-family="{FONT_BODY}" '
                 f'font-size="13" fill="{c["crimson"] if top else c["muted"]}" '
                 f'font-weight="{"bold" if top else "normal"}">{letters[k]}</text>')
    T.append(f'<path d="M{L},{cy1 + 0.5} H{L + lw}" stroke="{c["grid"]}" stroke-width="1"/>')
    busiest = ""
    if vmax > 0:
        bi = vals.index(vmax)
        busiest = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][bi]
        bxm = L + bi * step + step / 2
        T.append(f'<text x="{_f(bxm)}" y="{cy0 - 5}" text-anchor="middle" font-family="{FONT_BODY}" '
                 f'font-size="13" font-weight="bold" fill="{c["crimson"]}">{vmax}</text>')
        T.append(f'<text x="{L}" y="440" font-family="{FONT_BODY}" font-size="13" fill="{c["muted"]}">'
                 f'Busiest: <tspan font-weight="bold" fill="{c["ink"]}">{busiest}</tspan></text>')

    # monthly momentum sparkline
    sx0, sx1 = L + 168, R
    T.append(f'<text x="{sx0}" y="350" font-family="{FONT_BODY}" font-size="13" font-weight="bold" '
             f'fill="{c["ink"]}">Monthly momentum</text>')
    seq = _months_since_join(stats)
    mm = matched_momentum(stats)
    mo = momentum_value(mm) if mm and mm["pct"] is not None else ""
    mo_label = mm["label"] if mo else ""
    if seq:
        mvals = [v for _, v in seq]
        mmax = max(mvals) or 1
        n = len(seq)
        pad = 6
        xs = ([sx0 + pad + (sx1 - sx0 - 2 * pad) * i / (n - 1) for i in range(n)] if n > 1
              else [(sx0 + sx1) / 2])
        ys = [cy1 - (cy1 - cy0 + 4) * v / mmax for v in mvals]
        pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in zip(xs, ys))
        if n > 1:
            T.append(f'<path d="M{_f(xs[0])},{cy1} L{pts.replace(" ", " L")} L{_f(xs[-1])},{cy1} Z" '
                     f'fill="url(#area)"/>')
            T.append(f'<polyline points="{pts}" fill="none" stroke="url(#line)" stroke-width="2.4" '
                     f'stroke-linejoin="round" stroke-linecap="round"/>')
        T.append(f'<path d="M{sx0},{cy1 + 0.5} H{sx1}" stroke="{c["grid"]}" stroke-width="1"/>')
        for i, (x, y) in enumerate(zip(xs, ys)):
            last = i == n - 1
            T.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{3.6 if last else 2}" '
                     f'fill="{c["crimson"] if last else c["purple_soft"]}"/>')
        T.append(f'<circle class="pulse" cx="{_f(xs[-1])}" cy="{_f(ys[-1])}" r="7" fill="none" '
                 f'stroke="{c["crimson"]}" stroke-width="1.2"/>')
        T.append(f'<text x="{_f(xs[-1] - 13)}" y="{_f(max(ys[-1] + 4, cy0 + 2))}" text-anchor="end" '
                 f'font-family="{FONT_BODY}" font-size="13" font-weight="bold" fill="{c["crimson"]}">'
                 f'{mvals[-1]}</text>' if mvals[-1] and ys[-1] < cy0 + 12 and n > 1 else "")
        every = 1 if n <= 7 else 2
        for i, (k, _) in enumerate(seq):
            if (n - 1 - i) % every:
                continue
            mi = _int(k[5:7], 1)
            T.append(f'<text x="{_f(xs[i])}" y="{cy1 + 17}" text-anchor="middle" font-family="{FONT_BODY}" '
                     f'font-size="13" fill="{c["muted"]}">{calendar.month_abbr[mi][0]}</text>')
    if mo:
        T.append(f'<text x="{sx0}" y="440" font-family="{FONT_BODY}" font-size="15" font-weight="bold" '
                 f'fill="{c["crimson"]}">{esc(mo)}<tspan font-size="13" font-weight="normal" '
                 f'fill="{c["muted"]}"> {esc(mo_label.split(" over ")[0])}</tspan></text>')
        T.append(f'<text x="{sx0}" y="455" font-family="{FONT_BODY}" font-size="13" '
                 f'fill="{c["muted"]}">over {esc(mo_label.split(" over ")[-1])}</text>')

    # footer
    T.append(f'<path d="M{L},463 H{R}" stroke="{c["edge"]}" stroke-width="0.8"/>')
    T.append(f'<text x="{L}" y="{PH - 6}" font-family="{FONT_BODY}" font-size="13" letter-spacing="0.5" '
             f'fill="{c["muted"]}">ARCHIVE · ACHIEVEMENTS ON RECORD</text>')
    T.append(red_cloud(R - 32, PH - 23, 32, 1, edge=c["cloud_edge"]))

    bg = f'<rect width="{W}" height="{H}" fill="{m["page"]}"/>'
    if mode == "dark":
        bg += (f'<ellipse class="glow" cx="205" cy="230" rx="230" ry="260" fill="url(#aura)" '
               f'opacity="1"/>')
    body = (defs + bg + f'<g transform="translate({PX} {PY})">' + page + "".join(T) + "</g>")

    desc = (f"Engineering Atlas field dossier for {_name(stats)}. Calendar: {rank_title} "
            f"({total} contributions in the last year), location {village}, full-stack development across AI, data, and product systems. "
            f"{private} private contributions and {public} public. "
            f"Busiest weekday {busiest or 'none yet'}. Monthly momentum: "
            + ", ".join(f"{calendar.month_abbr[_int(k[5:7], 1)]} {v}" for k, v in seq)
            + (f". {mo.replace(chr(0x2212), 'minus ')} from {mo_label}." if mo else "."))
    return _svg(W, H, f"Field dossier: {_name(stats)}", desc, body, css)


# ======================================================== 3. RINGS & HAKI strip

RING_WORDS = {
    "pull shark": "MERGE",
    "pair extraordinaire": "DUO",
    "quickdraw": "SWIFT",
    "yolo": "BOLD",
    "developer program": "CREW",
    "starstruck": "STARS",
    "galaxy brain": "SAGE",
    "public sponsor": "ALLY",
    "arctic code vault contributor": "VAULT",
}


def _load_achievements() -> list:
    try:
        data = json.loads((HERE / "achievements.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("achievements") if isinstance(data, dict) else data
    return [a for a in (items or []) if isinstance(a, dict) and a.get("name")]


def _ring_word(name: str) -> str:
    key = name.strip().lower()
    for k, v in RING_WORDS.items():
        if key == k or key.startswith(k):
            return v
    word = (name.strip().split() or ["?"])[0].upper()
    return word[:6]


def _spikes(cx: float, cy: float, r0: float, r1: float, n: int, seed: int) -> str:
    pts = []
    for k in range(n * 2):
        a = math.pi * 2 * k / (n * 2) + seed * 0.37
        if k % 2:
            r = r0
        else:
            r = r0 + (r1 - r0) * (0.55 + 0.45 * abs(math.sin(k * 1.7 + seed)))
        pts.append(f"{_f(cx + r * math.cos(a))},{_f(cy + r * math.sin(a))}")
    return " ".join(pts)


def _arc(cx: float, cy: float, r: float, a0: float, a1: float) -> str:
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{_f(x0)},{_f(y0)} A{_f(r)},{_f(r)} 0 {large} 1 {_f(x1)},{_f(y1)}"


def render_seals(stats: dict, mode: str) -> str:
    mode = _mode(mode)
    m = MODES[mode]
    W, H = 840, 230
    items = _load_achievements()
    n = len(items)

    css = (
        ".sheen{transform-box:fill-box;transform-origin:50% 50%;animation:spin 10s linear infinite;}"
        "@keyframes spin{to{transform:rotate(360deg);}}"
        ".haki{transform-box:fill-box;transform-origin:50% 50%;animation:haki 4.5s ease-in-out infinite;}"
        "@keyframes haki{0%,100%{transform:scale(1) rotate(0deg);opacity:0.9;}"
        "50%{transform:scale(1.07) rotate(6deg);opacity:0.6;}}"
        ".bob{animation:bob 6s ease-in-out infinite;}"
        "@keyframes bob{0%,100%{transform:translateY(0);}50%{transform:translateY(-2px);}}"
    )
    metals = {
        "gold": ("#5E3E06", "#D49A1A", "#FFE27A", "#7A560E"),
        "steel": ("#24242C", "#C9CAD6", "#F4F4FA", "#4A4A58"),
    }
    auras = {
        "gold": (SH["sun_gold"], SH["sun_glow"]),
        "crimson": (AK["cloud_red"], AK["sharingan"]),
        "purple": ("#6C5BA8", AK["rinnegan"]),
    }

    defs = [
        '<defs>',
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{m["sky_left"]}"/><stop offset="0.5" stop-color="{m["panel"]}"/>'
        f'<stop offset="1" stop-color="{m["sky_right"]}"/></linearGradient>',
        f'<linearGradient id="chain" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{SH["sun_gold"]}"/><stop offset="0.5" stop-color="{AK["rinnegan"]}"/>'
        f'<stop offset="1" stop-color="{AK["cloud_red"]}"/></linearGradient>',
        '<linearGradient id="dir" x1="0.15" y1="0.1" x2="0.85" y2="0.95">'
        '<stop offset="0" stop-color="#FFF" stop-opacity="0.45"/><stop offset="0.45" stop-color="#FFF" stop-opacity="0"/>'
        '<stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.4"/>'
        '</linearGradient>',
        '<filter id="blur3" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>',
        '<filter id="blur1"><feGaussianBlur stdDeviation="0.8"/></filter>',
        f'<filter id="drop" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="3" '
        f'stdDeviation="2.5" flood-color="#000" flood-opacity="{0.35 if mode == "light" else 0.7}"/></filter>',
    ]

    left, right = 132, 700
    if n > 1:
        xs = [left + (right - left) * i / (n - 1) for i in range(n)]
        slot = (right - left) / (n - 1)
    else:
        xs = [W / 2]
        slot = 300.0
    R = min(44.0, slot * 0.31)
    r_in = R * 0.7
    cy = 94
    maxw = min(slot - 8, 170)

    body = [
        f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="16" fill="url(#bg)" '
        f'stroke="{m["panel_edge"]}"/>',
        f'<text x="{W / 2}" y="25" text-anchor="middle" font-family="{FONT_BODY}" font-size="13" '
        f'font-weight="bold" letter-spacing="3" fill="{m["text_muted"]}">ACHIEVEMENTS UNLOCKED</text>',
    ]
    if n > 1:
        body.append(f'<path d="M{xs[0]},{cy} H{xs[-1]}" stroke="url(#chain)" stroke-width="2" '
                    f'stroke-dasharray="2 7" stroke-linecap="round" opacity="0.7"/>')
    body.append(f'<g class="bob">{straw_hat(48, cy + 2, 1.15)}</g>')
    body.append(f'<g class="bob" style="animation-delay:-3s">'
                f'{red_cloud(W - 84, cy - 17, 64, 1, edge=AK["cloud_edge"])}</g>')

    for i, a in enumerate(items):
        cx = xs[i]
        name = str(a.get("name"))
        tier = _int(a.get("tier"), 1)
        meaning = str(a.get("meaning") or "")
        straw = i % 2 == 0
        aura_key = "gold" if straw else ("crimson" if (i // 2) % 2 == 0 else "purple")
        metal = metals["gold" if straw else "steel"]
        a1, a2 = auras[aura_key]
        if straw:
            face0, face1, glyph_c = "#FFF8E4", "#E9D3A0", SH["luffy_red"]
        else:
            face0, face1 = "#2A2A36", AK["cloak"]
            glyph_c = AK["sharingan"] if aura_key == "crimson" else AK["rinnegan_light"]

        defs.append(
            f'<radialGradient id="tube{i}" gradientUnits="userSpaceOnUse" cx="{_f(cx)}" cy="{cy}" r="{_f(R)}">'
            f'<stop offset="0" stop-color="{metal[0]}"/>'
            f'<stop offset="{_f(r_in / R)}" stop-color="{metal[0]}"/>'
            f'<stop offset="{_f((r_in / R + 1) / 2 - 0.04)}" stop-color="{metal[1]}"/>'
            f'<stop offset="{_f((r_in / R + 1) / 2 + 0.02)}" stop-color="{metal[2]}"/>'
            f'<stop offset="1" stop-color="{metal[3]}"/></radialGradient>'
            f'<radialGradient id="face{i}" cx="0.45" cy="0.4" r="0.65">'
            f'<stop offset="0" stop-color="{face0}"/><stop offset="1" stop-color="{face1}"/></radialGradient>'
            f'<radialGradient id="glow{i}" cx="0.5" cy="0.5" r="0.5">'
            f'<stop offset="0.45" stop-color="{a2}" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="{a1}" stop-opacity="0"/></radialGradient>'
        )
        delay = f"animation-delay:-{_f(i * 0.9)}s"
        annulus = (f"M{_f(cx - R)},{cy} a{_f(R)},{_f(R)} 0 1 0 {_f(2 * R)},0 a{_f(R)},{_f(R)} 0 1 0 {_f(-2 * R)},0 Z "
                   f"M{_f(cx - r_in)},{cy} a{_f(r_in)},{_f(r_in)} 0 1 1 {_f(2 * r_in)},0 "
                   f"a{_f(r_in)},{_f(r_in)} 0 1 1 {_f(-2 * r_in)},0 Z")
        mid = (R + r_in) / 2
        word = _ring_word(name)
        wfs = min(r_in * 0.72, (2 * r_in - 9) / max(1, len(word) * 0.54))
        engrave = "#FFFFFF" if straw else "#000000"
        g = [
            f'<circle cx="{_f(cx)}" cy="{cy}" r="{_f(R * 1.5)}" fill="url(#glow{i})"/>',
            f'<g class="haki" style="{delay}"><polygon points="{_spikes(cx, cy, R * 1.0, R * 1.36, 14, i)}" '
            f'fill="{a1}" opacity="0.55" filter="url(#blur3)"/>'
            f'<polygon points="{_spikes(cx, cy, R * 0.98, R * 1.2, 18, i + 3)}" fill="{a2}" opacity="0.5" '
            f'filter="url(#blur1)"/></g>',
            f'<g filter="url(#drop)">'
            f'<circle cx="{_f(cx)}" cy="{cy}" r="{_f(r_in + 0.5)}" fill="url(#face{i})"/>'
            f'<path d="{annulus}" fill="url(#tube{i})" fill-rule="evenodd"/></g>',
            f'<path d="{annulus}" fill="url(#dir)" fill-rule="evenodd"/>',
            f'<circle cx="{_f(cx)}" cy="{cy}" r="{_f(r_in)}" fill="none" stroke="#000" stroke-width="2" '
            f'opacity="0.35"/>',
            f'<path d="{_arc(cx, cy, mid, 200, 250)}" fill="none" stroke="#FFF" stroke-width="2.4" '
            f'stroke-linecap="round" opacity="0.85"/>',
            f'<path d="{_arc(cx, cy, mid, 20, 40)}" fill="none" stroke="#FFF" stroke-width="1.4" '
            f'stroke-linecap="round" opacity="0.35"/>',
            f'<circle class="sheen" style="{delay}" cx="{_f(cx)}" cy="{cy}" r="{_f(mid)}" fill="none" '
            f'stroke="#FFF" stroke-width="{_f((R - r_in) * 0.55)}" stroke-dasharray="9 400" '
            f'stroke-linecap="round" opacity="0.55"/>',
            f'<text x="{_f(cx)}" y="{_f(cy + wfs * 0.36 + 1)}" text-anchor="middle" font-family="{FONT_DISPLAY}" '
            f'font-size="{_f(wfs)}" letter-spacing="0.5" fill="{engrave}" opacity="0.6">{esc(word)}</text>',
            f'<text x="{_f(cx)}" y="{_f(cy + wfs * 0.36)}" text-anchor="middle" font-family="{FONT_DISPLAY}" '
            f'font-size="{_f(wfs)}" letter-spacing="0.5" fill="{glyph_c}">{esc(word)}</text>',
        ]
        body.append("".join(g))

        # label
        name_fs = 14.0
        badge = f"×{tier}" if tier > 1 else ""
        bw_ = 30 if badge else 0
        nlines = wrap(name, maxw - (bw_ + 6 if badge else 0), name_fs, 0.47)
        y = cy + R + 27
        for j, line in enumerate(nlines):
            lastline = j == len(nlines) - 1
            if lastline and badge:
                tw = est_w(line, name_fs, 0.47)
                x0 = cx - (tw + 6 + bw_) / 2
                body.append(f'<text x="{_f(x0)}" y="{_f(y)}" font-family="{FONT_BODY}" font-size="{name_fs}" '
                            f'font-weight="bold" fill="{m["text"]}">{esc(line)}</text>')
                px = x0 + tw + 6
                pill = a1 if not straw else SH["sun_gold"]
                pill_t = SH["haki_black"] if straw else "#FFFFFF"
                body.append(f'<rect x="{_f(px)}" y="{_f(y - 13.5)}" width="{bw_}" height="18" rx="9" '
                            f'fill="{pill}"/>'
                            f'<text x="{_f(px + bw_ / 2)}" y="{_f(y)}" text-anchor="middle" '
                            f'font-family="{FONT_BODY}" font-size="13" font-weight="bold" fill="{pill_t}">'
                            f'{esc(badge)}</text>')
            else:
                body.append(f'<text x="{_f(cx)}" y="{_f(y)}" text-anchor="middle" font-family="{FONT_BODY}" '
                            f'font-size="{name_fs}" font-weight="bold" fill="{m["text"]}">{esc(line)}</text>')
            y += 17
        y += 1
        for line in wrap(meaning, maxw, 13, 0.52)[:2]:
            body.append(f'<text x="{_f(cx)}" y="{_f(y)}" text-anchor="middle" font-family="{FONT_BODY}" '
                        f'font-size="13" fill="{m["text_muted"]}">{esc(line)}</text>')
            y += 16

    if not items:
        body.append(f'<text x="{W / 2}" y="{cy + 5}" text-anchor="middle" font-family="{FONT_BODY}" '
                    f'font-size="15" fill="{m["text_muted"]}">The first ring is still being forged.</text>')

    defs.append("</defs>")
    desc = ("GitHub achievements shown as metal rings with Haki auras: "
            + "; ".join(f"{a.get('name')}{' x' + str(_int(a.get('tier'), 1)) if _int(a.get('tier'), 1) > 1 else ''}"
                        f" ({a.get('meaning', '')})" for a in items)
            + "." if items else "No achievements yet.")
    return _svg(W, H, "Rings & Haki: GitHub achievements", desc, "".join(defs) + "".join(body), css)
