"""The contribution calendar as a static-first engineering atlas skyline.

The weeks run left to right across the full width, the same way as GitHub's
graph. The seven weekday rows recede straight back, with Sunday at the back,
under a true 1-point perspective centred on the image. Each day is a tower:
its front face and top are always visible, and the inner side face (the one
facing the centre) shows where the perspective reveals it. Height follows a
sqrt scale of the day's count.

Colour means intensity: every tower uses the shared POWER ramp from theme.py
(GitHub level 0-4, from gold on light days to crimson on the hottest). The theme
lives in the scenery instead: a rising sun, its glitter path, a lighthouse and
the ship on the left, and the red moon, red clouds, crows, rain and a distant
skyline on the right. Days before the account joined are open water ("the sea
before setting sail"), and the land begins on the day the account joined.

The HUD leads with the total and five context numbers (active days, peak day,
busiest weekday, longest streak and matched-period momentum). A quiet row of
month totals sits above the city, the streak is drawn as a bridge over its
tower tops and the peak tower carries a pennant.

Painter's algorithm: rows from back to front. Inside a row, columns are drawn
from the outer edges toward the centre column, since the camera sits on the
centre line and nearer prisms are always the ones closer to it.

Interactivity (when the SVG is opened directly): every day is a <g> with a
GitHub-style <title> tooltip and a subtle optional hover lift.

The complete scene is visible at frame zero. Ambient motion only touches
transform and opacity: a boat bob, drifting wave crests, twinkling glitter,
a breathing sun and lighthouse beam, drifting clouds, crows and rain.
Reduced motion disables all animation.
"""
from __future__ import annotations

import datetime as dt
import math

from theme import AKATSUKI, FONT_BODY, FONT_MONO, FONT_SERIF, MODES, POWER, STRAW_HAT

W, H = 840, 460

# Perspective: world x is in weeks and z is depth in rows (z=0 is the front edge,
# z=7 the back edge). s(z) = F / (F + z) scales width and height with depth.
COL_W = 15.2          # px per week at the front edge
FOCAL = 31.9          # s(7) = 0.82 -> gentle 1-point perspective
Y_FRONT = 392.0       # screen y of the front ground edge
DEPTH_PX = 85.0       # screen height of the ground from the front edge to the back edge
H_MAX = 150.0         # tallest tower in px at the front row
H_MIN = 2.0           # sliver for an active-era day with no contributions
INSET = 0.12          # gap between prisms, as a fraction of a cell
SLAB = 8.0            # thickness of the map board
MONTH_Y = 152         # baseline of the month-total row
HUD_Y = 128           # the rule under the HUD

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]

EASE_SINE = "cubic-bezier(.37,0,.63,1)"
EASE_OUT = "cubic-bezier(.22,.9,.32,1)"


# --------------------------------------------------------------------------- helpers

def _f(v: float) -> str:
    """Round to one decimal and drop a trailing .0 to keep the file small."""
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return "0" if s == "-0" else s


def _pts(points) -> str:
    return " ".join(f"{_f(x)},{_f(y)}" for x, y in points)


def _rgb(c: str):
    h = c.lstrip("#")
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))


def _mix(a: str, b: str, t: float) -> str:
    """Blend colour a toward colour b by t (0 = a, 1 = b)."""
    return "#" + "".join(
        f"{max(0, min(255, round(x + (y - x) * t))):02X}" for x, y in zip(_rgb(a), _rgb(b))
    )


def _shade(c: str, k: float) -> str:
    return _mix(c, "#000000", k)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md(s: str) -> str:
    d = dt.date.fromisoformat(s)
    return f"{MONTHS[d.month - 1]} {d.day}"


def _mdy(s: str) -> str:
    d = dt.date.fromisoformat(s)
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def _span(a: str, b: str) -> str:
    """'Oct 1–25', 'Oct 28 – Nov 3' or 'Oct 1' for a single day."""
    da, db = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    if da == db:
        return _md(a)
    if (da.year, da.month) == (db.year, db.month):
        return f"{MONTHS[da.month - 1]} {da.day}–{db.day}"
    return f"{_md(a)} – {_md(b)}"


def _tooltip(day: dict) -> str:
    """GitHub's wording: '47 contributions on Monday, September 28, 2026'."""
    d = dt.date.fromisoformat(day["date"])
    when = f"{DAY_NAMES[(d.weekday() + 1) % 7]}, {MONTHS_LONG[d.month - 1]} {d.day}, {d.year}"
    c = day["count"]
    if c == 0:
        return f"No contributions on {when}"
    return f"{c} contribution{'s' if c != 1 else ''} on {when}"


def _est(text: str, fs: float, k: float = .56) -> float:
    """Rough advance width of proportional text, good enough to lay out the HUD."""
    narrow = sum(1 for ch in text if ch in " .,:;!'|il1·")
    return fs * (k * (len(text) - narrow) + .3 * narrow)


# --------------------------------------------------------------------------- data

def matched_momentum(stats: dict):
    """Matched elapsed-period momentum, the same rule as site/model.js.

    The latest calendar month so far (from the 1st, or the join date, to the
    last calendar day) is compared with the same dates of the previous month.
    Returns None without data; pct is None when the baseline is zero or the
    previous period is not fully observed, so no percentage is ever invented.
    """
    days = [d for w in (stats.get("weeks") or []) for d in w]
    if not days:
        return None
    joined = str(stats.get("joined") or "")
    first, end_s = days[0]["date"], days[-1]["date"]
    end = dt.date.fromisoformat(end_s)
    month_start = end.replace(day=1).isoformat()
    cur_start = max(x for x in (month_start, first, joined) if x)
    if cur_start > end_s:
        return None
    first_day = dt.date.fromisoformat(cur_start).day
    prev_last_date = end.replace(day=1) - dt.timedelta(days=1)
    prev_last = prev_last_date.day
    completed = (end + dt.timedelta(days=1)).day == 1
    prev_start = prev_last_date.replace(day=min(first_day, prev_last)).isoformat()
    prev_end = prev_last_date.replace(day=prev_last if completed else min(end.day, prev_last)).isoformat()

    def window(a: str, b: str) -> list:
        return [d for d in days if a <= d["date"] <= b and not (joined and d["date"] < joined)]

    cur, prev = window(cur_start, end_s), window(prev_start, prev_end)
    expected = (dt.date.fromisoformat(prev_end) - dt.date.fromisoformat(prev_start)).days + 1
    comparable = len(prev) == expected and expected > 0
    current = sum(d["count"] for d in cur)
    previous = sum(d["count"] for d in prev)
    pct = None
    if comparable and previous > 0:
        pct = int(math.floor((current / previous - 1) * 100 + .5))
    return {
        "current": current, "previous": previous, "pct": pct, "comparable": comparable,
        "current_start": cur_start, "current_end": end_s,
        "previous_start": prev_start, "previous_end": prev_end,
        "label": f"{_span(cur_start, end_s)} over {_span(prev_start, prev_end)}",
    }


def momentum_value(mo) -> str:
    """'+900%', '−12%' or the current count when there is no baseline to compare with."""
    if not mo:
        return "–"
    if mo["pct"] is None:
        return f"{mo['current']:,}"
    sign = "+" if mo["pct"] >= 0 else "−"
    return f"{sign}{abs(mo['pct']):,}%"


def _summary(stats: dict) -> dict:
    """Every HUD number comes from stats, derived from the calendar if a key is missing."""
    days = [d for w in (stats.get("weeks") or []) for d in w]
    totals = stats.get("totals") or {}
    total = totals.get("contributions")
    if total is None:
        total = sum(d["count"] for d in days)
    active = stats.get("active_days")
    if active is None:
        active = sum(1 for d in days if d["count"] > 0)
    best = stats.get("best_day")
    if not best and days:
        b = max(days, key=lambda d: d["count"])
        best = {"date": b["date"], "count": b["count"]}
    wt = stats.get("weekday_totals")
    if not wt:
        wt = [0] * 7
        for d in days:
            wt[d["weekday"]] += d["count"]
    busiest_i = wt.index(max(wt)) if any(wt) else None
    if stats.get("busiest_weekday") in DAY_SHORT and any(wt):
        busiest_i = DAY_SHORT.index(stats["busiest_weekday"])
    streak = stats.get("streak") or {}
    if not streak:
        run = longest = 0
        for d in days:
            run = run + 1 if d["count"] > 0 else 0
            longest = max(longest, run)
        streak = {"current": 0, "longest": longest}
    # Streak to highlight: the current one if it is alive, otherwise the longest.
    st_live = False
    if (streak.get("current") or 0) > 0 and streak.get("current_start"):
        st_len, st_from = streak["current"], streak["current_start"]
        st_to = (dt.date.fromisoformat(st_from) + dt.timedelta(days=st_len - 1)).isoformat()
        st_live = True
    elif streak.get("longest_start") and streak.get("longest_end"):
        st_len, st_from, st_to = streak.get("longest", 0), streak["longest_start"], streak["longest_end"]
    else:  # derive the longest run from the calendar
        st_len, st_from, st_to, run, start = 0, None, None, 0, None
        for d in days:
            if d["count"] > 0:
                start = start or d["date"]
                run += 1
                if run > st_len:
                    st_len, st_from, st_to = run, start, d["date"]
            else:
                run, start = 0, None
    monthly = stats.get("monthly") or {}
    if not monthly:
        for d in days:
            monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]
    return {
        "monthly": monthly,
        "momentum": matched_momentum(stats),
        "streak_len": st_len or 0,
        "streak_from": st_from,
        "streak_to": st_to,
        "streak_live": st_live,
        "total": total,
        "active": active,
        "best": best if best and best.get("count") else None,
        "busiest": DAY_NAMES[busiest_i] if busiest_i is not None else None,
        "busiest_total": wt[busiest_i] if busiest_i is not None else 0,
        "joined": stats.get("joined") or None,
        "first": days[0]["date"] if days else None,
        "last": days[-1]["date"] if days else None,
    }


# --------------------------------------------------------------------------- render

def render_battlefield(stats: dict, mode: str) -> str:
    m = MODES[mode]
    dark = mode == "dark"
    weeks = [w for w in (stats.get("weeks") or []) if w] or [[]]
    n = max(1, len(weeks))
    joined = stats.get("joined") or ""
    s = _summary(stats)
    col_w = COL_W * 53 / n
    cx = W / 2
    xc = n / 2

    def sc(z: float) -> float:
        return FOCAL / (FOCAL + z)

    vy = Y_FRONT - DEPTH_PX / (1 - sc(7))  # vanishing point (above the frame)

    def P(x: float, z: float, h: float = 0.0):
        k = sc(z)
        return (cx + (x - xc) * col_w * k, vy + (Y_FRONT - vy) * k - h * k)

    def wx(sx_: float, z: float) -> float:  # screen x back to world x at depth z
        return xc + (sx_ - cx) / (col_w * sc(z))

    days = [(i, d) for i, w in enumerate(weeks) for d in w]
    max_count = max([d["count"] for _, d in days] + [1])

    def height(count: int) -> float:
        return H_MIN + (H_MAX - H_MIN) * math.sqrt(count / max_count)

    def zf(weekday: int) -> float:  # front z of a row; Saturday is the front row
        return 6 - weekday

    def is_sea(d: dict) -> bool:
        return bool(joined) and d["date"] < joined

    coast = 0  # first week index holding any day on or after joining
    for i, w in enumerate(weeks):
        if w and all(is_sea(d) for d in w):
            coast = i + 1
        else:
            break
    # The coast week can start at sea: its land begins on the joining weekday, so the
    # shoreline steps back one week for the rows (nearer the back) that are still water.
    step_z = 7.0
    if coast < n and weeks[coast]:
        land_wd = [d["weekday"] for d in weeks[coast] if not is_sea(d)]
        if land_wd:
            step_z = 7 - min(land_wd)
    land = [P(coast, 0), P(n, 0), P(n, 7)]
    if step_z < 7 and coast + 1 <= n:
        land += [P(coast + 1, 7), P(coast + 1, step_z), P(coast, step_z)]
    else:
        land += [P(coast, 7)]

    # ---- palette
    ramp = POWER[mode]
    stroke = "rgba(255,255,255,.07)" if dark else "rgba(27,27,31,.16)"
    css_levels = []
    for lv, col in enumerate(ramp):
        front = _shade(col, 0.22 if not dark else 0.32)
        lit = _mix(_shade(col, 0.08 if not dark else 0.2), STRAW_HAT["sun_glow"], .12)  # faces the sun
        side = _shade(col, 0.4 if not dark else 0.52)
        css_levels.append(f".p{lv} .t{{fill:{col}}}.p{lv} .f{{fill:{front}}}.p{lv} .d{{fill:{side}}}.p{lv} .l{{fill:{lit}}}")
    land_top = _mix(m["panel_edge"], "#FFFFFF", 0.3) if not dark else "#1B1F29"
    land_front = _shade(land_top, 0.28 if not dark else 0.42)
    shore = _mix(STRAW_HAT["straw"], land_top, .45) if not dark else _mix(STRAW_HAT["straw"], land_top, .7)
    water = (["#E6E3DA", "#C9D2D6", "#A4B4C0", "#8DA0AF"] if not dark
             else ["#33384A", "#22314A", "#172640", "#101C30"])
    water_front = _shade(water[3], .18 if not dark else .3)
    text, muted = m["text"], m["text_muted"]
    floor_line = "rgba(255,255,255,.16)" if dark else "rgba(255,255,255,.4)"
    hy = P(0, 7)[1]  # the horizon: the back edge of the board
    foam = "#FFFFFF"

    out: list[str] = []
    a = out.append
    mo = s["momentum"]
    desc = (
        f"{s['total']} contributions over {s['active']} active days"
        + (f" from {_mdy(s['first'])} to {_mdy(s['last'])}" if s["first"] else "")
        + (f". Peak day: {s['best']['count']} on {_mdy(s['best']['date'])}" if s["best"] else "")
        + (f". Busiest weekday: {s['busiest']}" if s["busiest"] else "")
        + (f". Longest streak: {s['streak_len']} days, {_span(s['streak_from'], s['streak_to'])}"
           if s["streak_len"] > 1 and s["streak_from"] else "")
        + (f". Momentum: {momentum_value(mo).replace(chr(0x2212), 'minus ')} ({mo['label']})"
           if mo and mo["pct"] is not None else "")
        + "."
        + (" Weeks before the account joined are drawn as open water under a rising sun, with a ship"
           " sailing toward the lighthouse where the land begins." if coast else "")
        + " Tower height and colour show each day's contributions, from gold on light days to crimson on the busiest."
        + " A red moon, red clouds and a distant skyline sit on the right."
        + " Open the contribution explorer to inspect the calendar."
    )
    a(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="bf-title bf-desc">'
    )
    a('<title id="bf-title">Contribution world · a year drawn as a skyline</title>')
    a(f'<desc id="bf-desc">{_esc(desc)}</desc>')

    # ---- defs
    sky = (["#FBE9CF", "#F8F1E6", "#EEEAEE", "#E2DDE6"] if not dark
           else ["#2A1C0D", "#161821", "#12131C", "#1C1018"])
    a("<defs>")
    a(
        f'<linearGradient id="sky" x1="0" y1="0" x2="1" y2="0">'
        + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in zip((0, .4, .7, 1), sky))
        + "</linearGradient>"
        f'<linearGradient id="skyv" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{m["page"]}" stop-opacity="{".55" if not dark else ".35"}"/>'
        f'<stop offset=".45" stop-color="{m["page"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="water" x1="0" y1="{_f(hy)}" x2="0" y2="{Y_FRONT}" gradientUnits="userSpaceOnUse">'
        + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in zip((0, .18, .6, 1), water))
        + "</linearGradient>"
        f'<linearGradient id="haze" x1="0" y1="{_f(hy - 120)}" x2="0" y2="{_f(hy)}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{sky[3]}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{sky[3]}" stop-opacity="{".7" if not dark else ".55"}"/></linearGradient>'
        f'<linearGradient id="city" x1="0" y1="{_f(hy - 130)}" x2="0" y2="{_f(hy)}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{"#A9A2B8" if not dark else "#3A3550"}"/>'
        f'<stop offset="1" stop-color="{"#D4CFDA" if not dark else "#221E2E"}"/></linearGradient>'
        f'<radialGradient id="moonG" cx=".4" cy=".38" r=".7">'
        f'<stop offset="0" stop-color="{_mix(AKATSUKI["sharingan"], "#FFFFFF", .18)}"/>'
        f'<stop offset=".7" stop-color="{AKATSUKI["sharingan"]}"/>'
        f'<stop offset="1" stop-color="{AKATSUKI["cloud_red"]}"/></radialGradient>'
        f'<radialGradient id="moonHalo"><stop offset=".3" stop-color="{AKATSUKI["sharingan"]}" '
        f'stop-opacity="{".28" if not dark else ".42"}"/>'
        f'<stop offset="1" stop-color="{AKATSUKI["sharingan"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="boardsh" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#000" stop-opacity="{".16" if not dark else ".5"}"/>'
        f'<stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>'
    )
    a('<filter id="soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>')
    a('<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter>')
    a(f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>')
    a(f'<clipPath id="above"><rect width="{W}" height="{_f(hy)}"/></clipPath>')
    a(f'<clipPath id="sea"><rect y="{_f(hy)}" width="{W}" height="{_f(Y_FRONT - hy)}"/></clipPath>')
    a("</defs>")

    # ---- style
    a("<style>")
    a(
        f"text{{font-family:{FONT_BODY}}}"
        f".mo{{font-family:{FONT_MONO}}}"
        f".sr{{font-family:{FONT_SERIF};font-style:italic}}"
        f".metric{{font-family:{FONT_SERIF}}}"
        f".t,.f,.d,.l{{stroke:{stroke};stroke-width:.5;stroke-linejoin:round}}"
        f".fl{{fill:none;stroke:{floor_line};stroke-dasharray:.6 10.4}}"
        ".sw{fill:#000;fill-opacity:0}"
        # hover: lift (only when the SVG is opened directly)
        f".tw{{transition:transform .18s {EASE_OUT}}}"
        ".tw:hover{transform:translateY(-1px)}"
        # every loop starts from the resting, fully drawn pose so frame 0 is complete
        f".boat{{animation:bf-tide 7.1s {EASE_SINE} infinite}}"
        "@keyframes bf-tide{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.4px)}}"
        f".wk{{animation:bf-wake 3.7s {EASE_SINE} infinite}}"
        "@keyframes bf-wake{0%,100%{opacity:.75}50%{opacity:.3}}"
        f".cr1{{animation:bf-drift 13s {EASE_SINE} infinite}}"
        f".cr2{{animation:bf-drift 17s {EASE_SINE} -6s infinite reverse}}"
        "@keyframes bf-drift{0%,100%{transform:translateX(0)}50%{transform:translateX(5px)}}"
        f".g1{{animation:bf-glint 2.3s {EASE_SINE} infinite}}"
        f".g2{{animation:bf-glint 3.1s {EASE_SINE} -1.2s infinite}}"
        f".g3{{animation:bf-glint 4.3s {EASE_SINE} -2.6s infinite}}"
        "@keyframes bf-glint{0%,100%{opacity:1}50%{opacity:.25}}"
        f".sunb{{animation:bf-breathe 9.7s {EASE_SINE} infinite}}"
        "@keyframes bf-breathe{0%,100%{opacity:1}50%{opacity:.78}}"
        f".beam{{animation:bf-beam 5.3s {EASE_SINE} infinite}}"
        "@keyframes bf-beam{0%,100%{opacity:1}50%{opacity:.45}}"
        f".cl1{{animation:bf-cloud 23s {EASE_SINE} infinite}}"
        f".cl2{{animation:bf-cloud 29s {EASE_SINE} -11s infinite reverse}}"
        "@keyframes bf-cloud{0%,100%{transform:translateX(0)}50%{transform:translateX(-9px)}}"
        ".rn{animation:bf-rain 1.9s linear infinite}"
        ".rn2{animation-duration:2.7s}"
        "@keyframes bf-rain{0%{transform:translate(0,0)}100%{transform:translate(-4px,40px)}}"
        ".wing{transform-box:fill-box;transform-origin:center;animation:bf-flap .9s ease-in-out infinite}"
        "@keyframes bf-flap{0%,100%{transform:scaleY(1)}50%{transform:scaleY(-.55)}}"
        f".flock{{animation:bf-fly 19s {EASE_SINE} infinite}}"
        "@keyframes bf-fly{0%,100%{transform:translate(0,0)}50%{transform:translate(-14px,-4px)}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}"
    )
    a("".join(css_levels))
    a("</style>")

    a('<g clip-path="url(#frame)">')
    a(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    a(f'<rect width="{W}" height="{_f(hy)}" fill="url(#skyv)"/>')

    # ---- far plane: sun on the left, red moon, skyline, clouds, crows and rain on the right
    sun_x = P(min(coast, n / 2) * 0.45 if coast else n * 0.18, 7)[0]
    sun_y = hy - 14
    a(_sun(sun_x, sun_y, hy, dark))
    a(_moon(790, hy - 92, dark))
    a(_skyline(hy, dark))
    a(f'<g class="cl1">{_red_cloud(782, hy - 70, .62)}</g>')
    a(f'<g class="cl2">{_red_cloud(826, hy - 104, .42)}{_red_cloud(604, hy - 96, .4)}</g>')
    a(_crows(dark, hy))
    a(_rain(560, MONTH_Y + 12, hy, dark))

    # ---- water: the whole plane below the horizon, with the sun's path and wave crests
    a(f'<rect y="{_f(hy)}" width="{W}" height="{_f(Y_FRONT - hy)}" fill="url(#water)"/>')
    a(_glitter(P, sc, sun_x, hy, dark))
    a(_crests(P, sc, wx, dark))
    a(f'<path d="M0,{_f(hy + .5)}H{W}" stroke="{foam}" stroke-width=".8" opacity="{".7" if not dark else ".18"}"/>')

    # ---- board: front cross-section of the water and the raised land
    def board_front(x0_: float, x1_: float, fill: str):
        a(f'<rect x="{_f(x0_)}" y="{Y_FRONT}" width="{_f(x1_ - x0_)}" height="{SLAB}" fill="{fill}"/>')

    a(f'<rect y="{_f(Y_FRONT + SLAB)}" width="{W}" height="{_f(H - Y_FRONT - SLAB)}" fill="{m["panel"]}"/>')
    a(f'<rect y="{_f(Y_FRONT + SLAB)}" width="{W}" height="14" fill="url(#boardsh)"/>')
    lx0, lx1 = P(coast, 0)[0], P(n, 0)[0]
    board_front(0, lx0, water_front)
    board_front(lx1, W, water_front)
    a(f'<path d="M0,{Y_FRONT}H{W}" stroke="{foam}" stroke-width=".8" opacity="{".55" if not dark else ".15"}"/>')
    if days:
        # sunlit shoreline: the land's left faces, a sliver of slab under the coast
        drop = SLAB * .9
        faces = [(P(coast, 0), P(coast, step_z))]
        if step_z < 7:
            faces.append((P(coast + 1, step_z), P(coast + 1, 7)))
        for (x0_, y0_), (x1_, y1_) in faces:
            a(f'<polygon points="{_pts([(x0_, y0_), (x1_, y1_), (x1_, y1_ + drop * sc(step_z)), (x0_, y0_ + drop)])}" fill="{shore}"/>')
        a(f'<polygon points="{_pts(land)}" fill="{land_top}"/>')
        board_front(lx0, lx1, land_front)
        a(f'<path d="M{_f(lx0)},{Y_FRONT + .4}H{_f(lx1)}" stroke="{_mix(land_top, "#FFFFFF", .5)}" stroke-width=".8" opacity=".6"/>')
        # foam where the water meets the shore
        fp = [(P(coast, 0)[0] - 2, Y_FRONT), (P(coast, step_z)[0] - 1.5, P(coast, step_z)[1])]
        if step_z < 7:
            fp += [(P(coast + 1, step_z)[0] - 1.5, P(coast + 1, step_z)[1]), (P(coast + 1, 7)[0] - 1, hy)]
        a(f'<polyline points="{_pts(fp)}" fill="none" stroke="{foam}" stroke-width="1.6" stroke-linejoin="round" '
          f'opacity="{".8" if not dark else ".35"}"/>')

    # ---- sea days: invisible hover targets with GitHub tooltips over the water
    if coast:
        tiles = []
        for i, w in enumerate(weeks):
            for d in w:
                if not is_sea(d):
                    continue
                z = zf(d["weekday"])
                quad = [P(i, z), P(i + 1, z), P(i + 1, z + 1), P(i, z + 1)]
                tiles.append(f'<polygon class="sw" points="{_pts(quad)}"><title>{_tooltip(d)}</title></polygon>')
        a("<g>" + "".join(tiles) + "</g>")

    # ---- sea story: the lighthouse at the coast and the ship sailing toward it
    if coast >= 2:
        lhx, lhy = P(coast - .55, 6.35)
        a(_lighthouse(lhx, lhy, sc(6.35) * 1.18, dark))
    if coast >= 4:
        sun_week = wx(sun_x, 7)
        bx, by = P(min(coast - 4.6, sun_week + 7.4), 2.2)
        a(_boat(bx, by, dark))

    # ---- towers: rows back to front, columns from the edges toward the centre
    center = int(xc)
    order = list(range(0, center)) + list(range(n - 1, center - 1, -1))
    tops = {}  # date -> top-centre point, for the streak bridge and the peak pennant
    for wd in range(7):
        z0 = zf(wd)
        z1 = z0 + 1
        row = []
        for i in order:
            d = next((x for x in weeks[i] if x["weekday"] == wd), None)
            if d is None or is_sea(d):
                continue
            h = height(d["count"])
            lv = max(0, min(4, int(d.get("level", 0))))
            if d["count"] > 0 and lv == 0:
                lv = 1
            g = INSET
            xa, xb = i + g, i + 1 - g
            za, zb = z0 + g, z1 - g
            FA, FB = P(xa, za), P(xb, za)
            FAt, FBt = P(xa, za, h), P(xb, za, h)
            BAt, BBt = P(xa, zb, h), P(xb, zb, h)
            tops[d["date"]] = P(i + .5, z0 + .5, h)
            # faces as short paths: vertical and horizontal edges use V/H to keep the worst case small
            faces = []
            if xb < xc:  # left of centre: right side visible (away from the sun)
                Bb = P(xb, zb)
                faces.append(f'<path class="d" d="M{_f(FB[0])},{_f(FB[1])}L{_f(Bb[0])},{_f(Bb[1])}'
                             f'V{_f(BBt[1])}L{_f(FBt[0])},{_f(FBt[1])}Z"/>')
            elif xa > xc:  # right of centre: left side visible (sunlit)
                Ab = P(xa, zb)
                faces.append(f'<path class="l" d="M{_f(FA[0])},{_f(FA[1])}L{_f(Ab[0])},{_f(Ab[1])}'
                             f'V{_f(BAt[1])}L{_f(FAt[0])},{_f(FAt[1])}Z"/>')
            faces.append(f'<path class="f" d="M{_f(FA[0])},{_f(FA[1])}H{_f(FB[0])}V{_f(FBt[1])}H{_f(FAt[0])}Z"/>')
            faces.append(f'<path class="t" d="M{_f(FAt[0])},{_f(FAt[1])}H{_f(FBt[0])}'
                         f'L{_f(BBt[0])},{_f(BBt[1])}H{_f(BAt[0])}Z"/>')
            hp = h * sc(za)
            if hp > 24:
                # floor lines as one dashed vertical stroke as wide as the face: a band every 11 px
                faces.append(f'<path class="fl" stroke-width="{_f(FB[0] - FA[0])}" '
                             f'd="M{_f((FA[0] + FB[0]) / 2)},{_f(FA[1] - 10.7)}V{_f(FA[1] - hp + 5)}"/>')
            row.append(f'<g class="tw p{lv}"><title>{_tooltip(d)}</title>{"".join(faces)}</g>')
        a("<g>" + "".join(row) + "</g>")

    # ---- streak: a glowing bridge over its tower tops, with a bead on each day
    if s["streak_len"] >= 2 and s["streak_from"]:
        pts = [tops[k] for k in sorted(tops) if s["streak_from"] <= k <= s["streak_to"]]
        if len(pts) >= 2:
            lift = 7
            d_ = f"M{_f(pts[0][0])},{_f(pts[0][1] - lift)}"
            for (x0_, y0_), (x1_, y1_) in zip(pts, pts[1:]):
                mx, my = (x0_ + x1_) / 2, min(y0_, y1_) - lift - 9
                d_ += f"Q{_f(mx)},{_f(my)} {_f(x1_)},{_f(y1_ - lift)}"
            gold = STRAW_HAT["sun_gold"]
            beads = "".join(
                f'<path d="M{_f(x)},{_f(y - 1)}V{_f(y - lift)}" stroke="{_shade(gold, .35)}" stroke-width=".9"/>'
                f'<circle cx="{_f(x)}" cy="{_f(y - lift)}" r="2.6" fill="{STRAW_HAT["sun_glow"]}" '
                f'stroke="{_shade(gold, .35)}" stroke-width=".8"/>' for x, y in pts
            )
            lx, ly = min(pts, key=lambda p: p[1])
            a(
                f'<g><path d="{d_}" fill="none" stroke="{STRAW_HAT["sun_glow"]}" stroke-width="6" opacity=".5" filter="url(#glow)"/>'
                f'<path d="{d_}" fill="none" stroke="{text}" stroke-width="3.4" stroke-linecap="round" opacity=".75"/>'
                f'<path d="{d_}" fill="none" stroke="{STRAW_HAT["sun_glow"]}" stroke-width="1.6" stroke-linecap="round"/>'
                f"{beads}"
                f'<path d="M{_f(lx - 3)},{_f(ly - lift - 3)}L{_f(lx - 16)},{_f(ly - lift - 16)}H{_f(lx - 22)}" fill="none" '
                f'stroke="{text}" stroke-width=".9"/>'
                f'<text x="{_f(lx - 25)}" y="{_f(ly - lift - 12)}" font-size="13" font-weight="600" '
                f'text-anchor="end" fill="{text}">{s["streak_len"]}-day streak</text></g>'
            )

    # ---- peak pennant on the tallest tower
    if s["best"] and s["best"]["date"] in tops:
        px, py = tops[s["best"]["date"]]
        red = ramp[4]
        a(
            f'<g><path d="M{_f(px)},{_f(py - 1)}V{_f(py - 24)}" stroke="{text}" stroke-width="1.2"/>'
            f'<path d="M{_f(px)},{_f(py - 24)}l13,4.5l-13,4.5Z" fill="{red}"/>'
            f'<text x="{_f(px - 5)}" y="{_f(py - 13)}" font-size="13" font-weight="600" text-anchor="end" '
            f'fill="{text}">Peak {s["best"]["count"]}</text></g>'
        )

    # ---- month labels under the front edge
    last_i = -10
    labels = []
    for i, w in enumerate(weeks):
        firsts = [d for d in w if d["date"][8:] == "01"]
        if not firsts or i - last_i < 3 or i > n - 2:
            continue
        last_i = i
        x, y = P(i + 0.1, 0)
        labels.append(f'<text x="{_f(x)}" y="{_f(y + SLAB + 19)}">{MONTHS[int(firsts[0]["date"][5:7]) - 1]}</text>')
    a(f'<g font-size="14" fill="{muted}">' + "".join(labels) + "</g>")

    # ---- month totals: a quiet bracket above each month's section of the city
    a(_month_totals(weeks, s["monthly"], coast, joined, P, m, ramp))

    a(_legend(ramp, m))
    a(_hud(s, m, ramp))
    a(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{m["panel_edge"]}"/>')
    a("</g></svg>")
    # Numeric entities for any non-ASCII so the file is encoding-proof.
    return "\n".join(out).encode("ascii", "xmlcharrefreplace").decode("ascii")


# --------------------------------------------------------------------------- pieces

def _sun(sx: float, sy: float, hy: float, dark: bool) -> str:
    """A big low sun: wide bloom, soft blurred rays, a halo and a bright core, clipped at the horizon."""
    glow, gold = STRAW_HAT["sun_glow"], STRAW_HAT["sun_gold"]
    orange = _mix(gold, STRAW_HAT["luffy_red"], .35)
    k = .62 if dark else .9
    defs = (
        f'<radialGradient id="sunBloom" cx="{_f(sx)}" cy="{_f(sy)}" r="330" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{orange}" stop-opacity="{.5 * k:.2f}"/>'
        f'<stop offset=".3" stop-color="{gold}" stop-opacity="{.2 * k:.2f}"/>'
        f'<stop offset="1" stop-color="{gold}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="sunHalo"><stop offset=".25" stop-color="{glow}" stop-opacity=".95"/>'
        f'<stop offset=".5" stop-color="{gold}" stop-opacity=".42"/>'
        f'<stop offset="1" stop-color="{orange}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="sunCore" cx=".46" cy=".42" r=".6"><stop offset="0" stop-color="#FFFFFF"/>'
        f'<stop offset=".55" stop-color="#FFF8DC"/><stop offset=".85" stop-color="{glow}"/>'
        f'<stop offset="1" stop-color="{gold}"/></radialGradient>'
        f'<radialGradient id="rayG" cx="{_f(sx)}" cy="{_f(sy)}" r="300" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{glow}" stop-opacity="{.7 * k:.2f}"/>'
        f'<stop offset=".45" stop-color="{glow}" stop-opacity="{.22 * k:.2f}"/>'
        f'<stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient>'
        f'<filter id="raysoft" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<feGaussianBlur stdDeviation="5"/></filter>'
    )
    rays = []
    for deg, half in ((-168, 2.6), (-150, 1.8), (-132, 3.2), (-113, 1.6), (-97, 2.8), (-80, 1.9),
                      (-62, 3.0), (-44, 1.7), (-27, 2.6), (-12, 1.9)):
        a0, a1 = math.radians(deg - half), math.radians(deg + half)
        rays.append(f"M{_f(sx)},{_f(sy)}L{_f(sx + 300 * math.cos(a0))},{_f(sy + 300 * math.sin(a0))}"
                    f"L{_f(sx + 300 * math.cos(a1))},{_f(sy + 300 * math.sin(a1))}Z")
    return (
        f"<defs>{defs}</defs>"
        f'<g clip-path="url(#above)">'
        f'<rect width="{W}" height="{_f(hy)}" fill="url(#sunBloom)"/>'
        f'<path class="sunb" d="{"".join(rays)}" fill="url(#rayG)" filter="url(#raysoft)"/>'
        f'<circle class="sunb" cx="{_f(sx)}" cy="{_f(sy)}" r="96" fill="url(#sunHalo)"/>'
        f'<circle cx="{_f(sx)}" cy="{_f(sy)}" r="40" fill="url(#sunCore)"/>'
        f"</g>"
    )


def _glitter(P, sc, sx: float, hy: float, dark: bool) -> str:
    """The sun's path on the water: a warm glow under the horizon, a soft column and twinkling dashes."""
    glow = STRAW_HAT["sun_glow"]
    defs = (
        f'<radialGradient id="seaWarm" cx="{_f(sx)}" cy="{_f(hy)}" r="250" gradientUnits="userSpaceOnUse" '
        f'gradientTransform="translate({_f(sx)} {_f(hy)}) scale(1 .42) translate({_f(-sx)} {_f(-hy)})">'
        f'<stop offset="0" stop-color="{glow}" stop-opacity="{".75" if not dark else ".5"}"/>'
        f'<stop offset=".5" stop-color="{STRAW_HAT["sun_gold"]}" stop-opacity="{".18" if not dark else ".14"}"/>'
        f'<stop offset="1" stop-color="{STRAW_HAT["sun_gold"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="glitG" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{glow}" stop-opacity=".95"/>'
        f'<stop offset=".55" stop-color="{glow}" stop-opacity=".4"/>'
        f'<stop offset="1" stop-color="{glow}" stop-opacity=".12"/></linearGradient>'
    )
    trap = [(sx - 22, hy), (sx + 22, hy), (sx + 84, Y_FRONT), (sx - 84, Y_FRONT)]
    dashes = {1: [], 2: [], 3: []}
    for q in range(66):
        t = ((q * 0.618034) % 1) ** 1.35            # bias toward the horizon
        z = 6.95 * (1 - t)
        y = P(0, z)[1]
        k = sc(z)
        half = 16 + 64 * (1 - z / 7)
        jitter = (((q * 0.414214) % 1) * 2 - 1) * half * .9
        ln = (6 + ((q * 7) % 11) * 1.8) * k
        dashes[q % 3 + 1].append(f"M{_f(sx + jitter - ln / 2)},{_f(y)}h{_f(ln)}")
    dash_svg = "".join(
        f'<path class="g{c}" d="{"".join(v)}" stroke="{"#FFFFFF" if c != 2 else glow}" '
        f'stroke-width="{1.7 if c == 1 else 1.3}" stroke-linecap="round"/>'
        for c, v in dashes.items()
    )
    return (
        f"<defs>{defs}</defs>"
        f'<g clip-path="url(#sea)">'
        f'<rect y="{_f(hy)}" width="{W}" height="{_f(Y_FRONT - hy)}" fill="url(#seaWarm)"/>'
        f'<polygon points="{_pts(trap)}" fill="url(#glitG)" opacity="{".6" if dark else ".75"}" filter="url(#soft)"/>'
        f"{dash_svg}</g>"
    )


def _crests(P, sc, wx, dark: bool) -> str:
    """Scattered wave crests in perspective: pale caps over soft troughs, drifting at two speeds."""
    caps, troughs = ([], []), ([], [])
    for q in range(190):
        t = (q * 0.618034) % 1
        z = 7 * (t ** .85)
        k = sc(z)
        x = -10 + ((q * 0.7548777) % 1) * (W + 20)
        y = P(wx(x, z), z)[1] + ((q * 0.5698403) % 1) * 2 - 1
        ln = (14 + ((q * 13) % 9) * 2.6) * k * (1.2 - z / 12)
        amp = .9 * k
        grp = q % 2
        caps[grp].append(f"M{x:.0f},{_f(y)}q{ln / 2:.0f},{_f(-amp * 2)} {ln:.0f},0")
        troughs[grp].append(f"M{x + ln * .2:.0f},{_f(y + 1.6 * k)}h{ln * .7:.0f}")
    cap_col, cap_op = ("#FFFFFF", ".7") if not dark else ("#A9BCD6", ".3")
    tr_col, tr_op = ("#6F8495", ".26") if not dark else ("#05080F", ".4")
    return "".join(
        f'<g class="cr{g + 1}" fill="none" stroke-linecap="round">'
        f'<path d="{"".join(troughs[g])}" stroke="{tr_col}" stroke-width=".9" opacity="{tr_op}"/>'
        f'<path d="{"".join(caps[g])}" stroke="{cap_col}" stroke-width="1.1" opacity="{cap_op}"/></g>'
        for g in (0, 1)
    )


def _moon(mx: float, my: float, dark: bool) -> str:
    """The red moon, low behind the skyline, with a soft halo and faint maria."""
    mar = _shade(AKATSUKI["cloud_red"], .25)
    return (
        f'<g clip-path="url(#above)">'
        f'<circle cx="{_f(mx)}" cy="{_f(my)}" r="78" fill="url(#moonHalo)"/>'
        f'<g opacity="{".86" if not dark else "1"}">'
        f'<circle cx="{_f(mx)}" cy="{_f(my)}" r="27" fill="url(#moonG)"/>'
        f'<g fill="{mar}" opacity=".28"><circle cx="{_f(mx - 8)}" cy="{_f(my - 6)}" r="6"/>'
        f'<circle cx="{_f(mx + 7)}" cy="{_f(my + 5)}" r="4.5"/><circle cx="{_f(mx + 9)}" cy="{_f(my - 10)}" r="2.6"/>'
        f'<circle cx="{_f(mx - 4)}" cy="{_f(my + 12)}" r="3"/></g></g></g>'
    )


def _skyline(hy: float, dark: bool) -> str:
    """A distant city silhouette behind the land, fading into the haze at the horizon."""
    tp = []
    win = []
    spec = ((452, 24, 16), (470, 40, 12), (484, 30, 18), (504, 58, 13), (519, 36, 16), (537, 74, 14),
            (553, 50, 18), (573, 92, 12), (587, 62, 17), (606, 104, 15), (623, 70, 19), (644, 120, 13),
            (659, 84, 18), (679, 98, 14), (695, 66, 20), (717, 112, 13), (732, 78, 17), (751, 90, 15),
            (768, 58, 18), (788, 102, 14), (804, 72, 17), (823, 86, 17))
    for k, (tx, top, tw) in enumerate(spec):
        ty = hy - top
        if k % 3 == 0:  # spire
            tp.append(f"M{tx},{_f(ty + 6)}L{_f(tx + tw / 2)},{_f(ty)}L{tx + tw},{_f(ty + 6)}V{_f(hy)}H{tx}Z"
                      f"M{_f(tx + tw / 2 - .8)},{_f(ty)}V{_f(ty - 11)}h1.6V{_f(ty)}Z")
        elif k % 3 == 1:  # stepped
            tp.append(f"M{tx},{_f(ty + 8)}h3v-8h{tw - 6}v8h3V{_f(hy)}H{tx}Z")
        else:
            tp.append(f"M{tx},{_f(ty)}h{tw}V{_f(hy)}H{tx}Z")
        if dark:
            for r in range(3, int(top // 9)):
                if (k * 7 + r * 3) % 5 == 0:
                    win.append(f"M{_f(tx + 3 + (r % 2) * (tw - 8))},{_f(ty + r * 9)}h2.4")
    lights = (f'<path d="{"".join(win)}" stroke="{STRAW_HAT["sun_glow"]}" stroke-width="1.6" opacity=".55"/>'
              if win else "")
    return f'<g opacity="{".8" if not dark else ".95"}"><path d="{"".join(tp)}" fill="url(#city)"/>{lights}</g>'


def _red_cloud(cx: float, cy: float, k: float) -> str:
    """A red cloud: red puffs with a white outline and two curls."""
    puffs = [(-22, 4, 11), (-8, -4, 14), (10, -2, 13), (24, 5, 10), (2, 8, 11), (-14, 9, 9)]
    circles = "".join(f'<circle cx="{_f(cx + dx * k)}" cy="{_f(cy + dy * k)}" r="{_f(r * k)}"/>' for dx, dy, r in puffs)
    curls = (f'<path d="M{_f(cx - 14 * k)},{_f(cy + 3 * k)}q{_f(4 * k)},{_f(-7 * k)} {_f(9 * k)},{_f(-1 * k)}'
             f'M{_f(cx + 6 * k)},{_f(cy + 4 * k)}q{_f(4 * k)},{_f(-7 * k)} {_f(9 * k)},{_f(-1 * k)}" fill="none" '
             f'stroke="{AKATSUKI["cloud_edge"]}" stroke-width="{_f(2.4 * k)}" stroke-linecap="round"/>')
    return (
        f'<g><g fill="{AKATSUKI["cloud_edge"]}" stroke="{AKATSUKI["cloud_edge"]}" stroke-width="{_f(5 * k)}">{circles}</g>'
        f'<g fill="{AKATSUKI["cloud_red"]}">{circles}</g>{curls}</g>'
    )


def _crows(dark: bool, hy: float) -> str:
    crow = AKATSUKI["crow"] if not dark else "#05050A"
    birds = []
    for k, (x, y, s) in enumerate(((766, hy - 128, .85), (788, hy - 136, .65), (748, hy - 120, .6),
                                   (806, hy - 124, .5))):
        birds.append(
            f'<g transform="translate({x},{_f(y)}) scale({s})">'
            f'<path d="M-2,0Q0,-2.5 2,0Q0,2.5 -2,0Z" fill="{crow}"/>'
            f'<path class="wing" style="animation-delay:-{k * .23:.2f}s" d="M-11,-1Q-5,-7 0,0Q5,-7 11,-1Q5,-4 0,1Q-5,-4 -11,-1Z" fill="{crow}"/></g>'
        )
    return f'<g class="flock" opacity="{".75" if not dark else ".9"}">{"".join(birds)}</g>'


def _rain(x_start: float, y0: float, hy: float, dark: bool) -> str:
    """Fine slanted rain over the skyline; each column repeats every 40 px so the fall loops seamlessly."""
    col = AKATSUKI["rinnegan"] if not dark else "#8592AE"
    near, far = [], []
    q = 0
    x = x_start
    while x < W + 8:
        phase = (q * 17) % 40
        y = y0 - 40 + phase
        seg = near if q % 3 == 0 else far
        while y < hy - 6:
            seg.append(f"M{_f(x)},{_f(y)}l-1.4,{9 if seg is near else 6}")
            y += 40
        q += 1
        x += 9 + (q * 5) % 7
    clip = f'<clipPath id="rainclip"><rect x="{_f(x_start - 20)}" y="{_f(y0)}" width="{_f(W - x_start + 20)}" height="{_f(hy - y0)}"/></clipPath>'
    return (
        f'{clip}<g clip-path="url(#rainclip)" stroke="{col}" stroke-linecap="round">'
        f'<path class="rn" d="{"".join(near)}" stroke-width=".9" opacity="{".32" if not dark else ".4"}"/>'
        f'<path class="rn rn2" d="{"".join(far)}" stroke-width=".7" opacity="{".22" if not dark else ".28"}"/></g>'
    )


def _lighthouse(x: float, y: float, s: float, dark: bool) -> str:
    """A small lighthouse on a rock where the land begins, its beam reaching back over the water."""
    red = AKATSUKI["cloud_red"]
    white = STRAW_HAT["nika_white"] if not dark else "#E9E2D2"
    rock = "#6B6A70" if not dark else "#2A2C36"
    glow = STRAW_HAT["sun_glow"]
    beam = (
        f'<linearGradient id="beamG" x1="1" y1="0" x2="0" y2="0">'
        f'<stop offset="0" stop-color="{glow}" stop-opacity="{".7" if dark else ".6"}"/>'
        f'<stop offset="1" stop-color="{glow}" stop-opacity="0"/></linearGradient>'
    )
    return (
        f"<defs>{beam}</defs>"
        f'<g transform="translate({_f(x)},{_f(y)}) scale({s:.3f})">'
        f'<path class="beam" d="M-2,-44L-118,-58L-118,-28Z" fill="url(#beamG)"/>'
        f'<path d="M-15,2Q-12,-6 -4,-6Q2,-9 8,-5Q15,-4 16,2Z" fill="{rock}"/>'
        f'<path d="M-6,-5L-4,-36H4L6,-5Z" fill="{white}" stroke="{_shade(white, .3)}" stroke-width=".6"/>'
        f'<path d="M-5.6,-12L-5.2,-18H5.2L5.6,-12ZM-4.7,-25L-4.4,-30H4.4L4.7,-25Z" fill="{red}"/>'
        f'<path d="M-6,-36H6V-38H-6Z" fill="{_shade(white, .55)}"/>'
        f'<rect x="-3.6" y="-45" width="7.2" height="7" fill="{glow}"/>'
        f'<circle class="beam" cx="0" cy="-41.5" r="7" fill="{glow}" opacity=".55" filter="url(#glow)"/>'
        f'<path d="M-5,-45L0,-51L5,-45Z" fill="{red}"/>'
        f"</g>"
    )


def _boat(x: float, y: float, dark: bool) -> str:
    """A small sloop: planked hull, straw-hat sail filled by the wind, mast flag and a foaming wake."""
    wood = _mix(_shade(STRAW_HAT["straw"], .5), "#6B3A1E", .4)
    wood_dk = _shade(wood, .4)
    sail = STRAW_HAT["nika_white"]
    sail_sh = _mix(sail, STRAW_HAT["straw"], .45)
    straw = STRAW_HAT["straw"]
    foam = "#FFFFFF"
    wake = (
        f'<g fill="none" stroke="{foam}" stroke-linecap="round">'
        f'<path d="M-38,4Q-84,8 -150,14" stroke-width="1.8" opacity=".7"/>'
        f'<path d="M-34,8Q-76,20 -130,32" stroke-width="1.4" opacity=".5"/>'
        f'<path class="wk" d="M-50,9h9M-74,14h11M-98,19h8M-64,22h10M-92,28h9M-120,16h10" stroke-width="1.4"/>'
        f'<path class="wk" style="animation-delay:-1.8s" d="M-60,8h8M-86,13h10M-110,22h9M-78,25h8M-134,12h8" stroke-width="1.2"/>'
        f"</g>"
    )
    hull = (
        f'<path d="M-44,-14L40,-17Q47,-17 50,-22Q46,0 31,9L-31,9Q-41,3 -44,-14Z" fill="{wood}" stroke="{wood_dk}" stroke-width=".8"/>'
        f'<path d="M-42,-7Q0,-6 45,-11M-39,0Q0,1 41,-3M-35,5Q0,6 36,3" fill="none" stroke="{wood_dk}" stroke-width=".8" opacity=".8"/>'
        f'<path d="M-45,-15L42,-18" stroke="{straw}" stroke-width="2.6" stroke-linecap="round"/>'
        f'<g fill="{STRAW_HAT["sun_glow"]}" stroke="{wood_dk}" stroke-width=".6">'
        f'<circle cx="-16" cy="-6" r="2"/><circle cx="0" cy="-6.5" r="2"/><circle cx="16" cy="-7.5" r="2"/></g>'
        f'<path d="M-44,-15v-11h15v10Z" fill="{wood}" stroke="{wood_dk}" stroke-width=".7"/>'
        f'<rect x="-40" y="-23" width="6" height="4" fill="{STRAW_HAT["sun_glow"]}"/>'
        f'<circle cx="50" cy="-22" r="5.5" fill="{STRAW_HAT["sun_gold"]}" stroke="{_shade(STRAW_HAT["sun_gold"], .3)}" stroke-width=".7"/>'
        f'<circle cx="50" cy="-22" r="3" fill="{straw}"/>'
    )
    rig = (
        f'<path d="M4,-80L46,-16L30,-16Z" fill="{sail}" stroke="{sail_sh}" stroke-width=".7"/>'
        f'<rect x="-2" y="-86" width="4" height="72" fill="{wood_dk}"/>'
        f'<path d="M-7,-76h14l-2,6h-10Z" fill="{wood}" stroke="{wood_dk}" stroke-width=".6"/>'
        f'<path d="M-28,-67H28M-26,-21H26" stroke="{wood_dk}" stroke-width="2.4" stroke-linecap="round"/>'
        f'<path d="M-26,-66Q-20,-44 -25,-22L25,-22Q37,-44 27,-66Z" fill="url(#sailg)" stroke="{sail_sh}" stroke-width=".8"/>'
        f'<path d="M-25,-37Q2,-34 30,-37" stroke="{STRAW_HAT["straw_band"]}" stroke-width="3" fill="none"/>'
        f'<ellipse cx="3" cy="-46" rx="13" ry="3.6" fill="{straw}" stroke="{_shade(straw, .4)}" stroke-width=".7"/>'
        f'<path d="M-5,-46.5Q-5,-58 3,-58Q11,-58 11,-46.5Z" fill="{straw}" stroke="{_shade(straw, .4)}" stroke-width=".7"/>'
        f'<rect x="-5" y="-50" width="16" height="3" fill="{STRAW_HAT["straw_band"]}"/>'
        f'<path d="M2,-86l16,4l-16,5Z" fill="{STRAW_HAT["luffy_red"]}"/>'
    )
    return (
        f'<defs><linearGradient id="sailg" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{sail_sh}"/><stop offset=".45" stop-color="{sail}"/>'
        f'<stop offset="1" stop-color="{_mix(sail, STRAW_HAT["sun_glow"], .35 if dark else .2)}"/></linearGradient></defs>'
        f'<g transform="translate({_f(x)},{_f(y)})">{wake}'
        f'<ellipse cx="2" cy="10" rx="48" ry="4.5" fill="#000" opacity="{".3" if dark else ".14"}"/>'
        f'<g class="boat">{rig}{hull}</g></g>'
    )


def _month_totals(weeks, monthly: dict, coast: int, joined: str, P, m: dict, ramp: list) -> str:
    """Month totals above the city, one bracket per month from the join month on.

    Positions use the mid-depth scale so each bracket sits over the middle of its
    month's towers; neighbouring months meet in the middle of the week they share.
    The weeks before joining get one quiet italic note instead of a row of zeros.
    """
    text, muted, edge = m["text"], m["text_muted"], m["panel_edge"]
    zmid = 3.5
    spans: dict[str, list] = {}
    for i, w in enumerate(weeks):
        for d in w:
            key = d["date"][:7]
            frac = i + (d["weekday"] + .5) / 7
            lo, hi = spans.get(key, [frac, frac])
            spans[key] = [min(lo, frac), max(hi, frac)]
    jm = joined[:7] if joined else ""
    out = []
    y = MONTH_Y
    for key in sorted(spans):
        if jm and key < jm:
            continue
        lo, hi = spans[key]
        x0, x1 = P(lo - .5 / 7, zmid)[0] + 2, P(hi + .5 / 7, zmid)[0] - 2
        if x1 - x0 < 30:
            continue
        mid = (x0 + x1) / 2
        total = int(monthly.get(key) or 0)
        out.append(
            f'<path d="M{_f(x0)},{y + 10}V{y + 6}H{_f(x1)}V{y + 10}" fill="none" stroke="{edge if total == 0 else muted}" '
            f'stroke-width=".8" opacity=".75"/>'
            f'<text x="{_f(mid)}" y="{y}" text-anchor="middle" font-size="13" fill="{muted}">'
            f'{MONTHS[int(key[5:7]) - 1]} <tspan font-weight="700" fill="{text}">{total:,}</tspan></text>'
        )
    if coast >= 6:
        x0, x1 = P(0, zmid)[0] + 8, P(coast, zmid)[0] - 8
        out.append(
            f'<path d="M{_f(x0)},{y + 10}V{y + 6}H{_f(x1)}V{y + 10}" fill="none" stroke="{edge}" stroke-width=".8"/>'
            f'<text x="{_f((x0 + x1) / 2)}" y="{y}" text-anchor="middle" font-size="13.5" class="sr" fill="{muted}">'
            f"Before joining: open water</text>"
        )
    return "<g>" + "".join(out) + "</g>"


def _legend(ramp, m) -> str:
    """A single intensity ramp, the same as GitHub's: Less to More."""
    y = 448
    sw = 12
    muted = m["text_muted"]
    rw = 5 * (sw + 3) - 3
    x = 76
    cells = "".join(
        f'<rect x="{_f(x + q * (sw + 3))}" y="{y - 11}" width="{sw}" height="{sw}" rx="2.5" fill="{c}" '
        f'stroke="{m["panel_edge"]}" stroke-width=".8"/>' for q, c in enumerate(ramp)
    )
    return (
        f'<g font-size="14" fill="{muted}"><text x="{_f(x - 8)}" y="{y}" text-anchor="end">Less</text>{cells}'
        f'<text x="{_f(x + rw + 8)}" y="{y}">More</text>'
        f'<text x="{_f(x + rw + 52)}" y="{y}">· tower height is the day\'s count</text>'
        f'<text x="{W - 30}" y="{y}" font-size="16" font-weight="600" fill="{m["text"]}" text-anchor="end">'
        f"Open the contribution explorer &#8599;</text></g>"
    )


def _hud(s: dict, m: dict, ramp: list) -> str:
    """The total on the left, then five context numbers in columns that end at the right margin."""
    text, muted, edge = m["text"], m["text_muted"], m["panel_edge"]
    total = int(s["total"] or 0)
    digits = str(abs(total))
    value = f"{total:,}" if len(digits) <= 7 else f"{digits[0]}.{digits[1:3]}e{len(digits)-1}"
    vfs = 54 if len(value) <= 5 else 40
    vw = _est(value, vfs, .55)
    parts = [
        f'<path d="M30,{HUD_Y}H810" stroke="{edge}" stroke-width=".8"/>',
        f'<path d="M30,{HUD_Y}H{_f(30 + vw)}" stroke="{ramp[2]}" stroke-width="2"/>',
        f'<text x="30" y="32" font-size="13" letter-spacing="2.6" fill="{muted}">CONTRIBUTION WORLD</text>',
        f'<text x="28" y="101" class="metric" font-size="{vfs}" fill="{text}">{_esc(value)}</text>',
        f'<text x="{_f(38 + vw)}" y="81" font-size="16" font-weight="600" fill="{text}">contributions</text>',
        f'<text x="{_f(38 + vw)}" y="100" font-size="14" fill="{muted}">in the last year</text>',
    ]
    if s["first"] and s["last"]:
        parts.append(
            f'<text x="810" y="32" font-size="13" fill="{muted}" text-anchor="end">'
            f'{_esc(_mdy(s["first"]))} – {_esc(_mdy(s["last"]))}</text>'
        )
    mo = s["momentum"]
    cols = [
        (f"{s['active']:,}", "active days", f"since {_md(s['joined'])}" if s["joined"] else "in the last year"),
        (f"{s['best']['count']:,}" if s["best"] else "–", "peak day",
         _md(s["best"]["date"]) if s["best"] else "no activity yet"),
        (s["busiest"] or "–", "busiest weekday",
         f"{s['busiest_total']:,} contributions" if s["busiest"] else "no activity yet"),
        (f"{s['streak_len']} day{'s' if s['streak_len'] != 1 else ''}",
         "current streak" if s["streak_live"] else "longest streak",
         _span(s["streak_from"], s["streak_to"]) if s["streak_from"] and s["streak_len"] else "no streak yet"),
        (momentum_value(mo), "momentum" if mo and mo["pct"] is not None else "this month",
         mo["label"] if mo and mo["pct"] is not None else (_span(mo["current_start"], mo["current_end"]) if mo else "no data yet")),
    ]
    widths = [max(_est(v, 25, .54), _est(lab, 13, .6), _est(det, 13, .58)) for v, lab, det in cols]
    gap = 22
    x = 810 - sum(widths) - gap * (len(cols) - 1)
    for k, ((v, lab, det), w) in enumerate(zip(cols, widths)):
        if k:
            parts.append(f'<path d="M{_f(x - gap / 2)},58V114" stroke="{edge}" stroke-width=".8"/>')
        accent = ramp[4] if k == 4 and mo and (mo["pct"] or 0) > 0 else text
        parts.append(
            f'<text x="{_f(x)}" y="80" class="metric" font-size="25" fill="{accent}">{_esc(v)}</text>'
            f'<text x="{_f(x)}" y="98" font-size="13" font-weight="600" fill="{text}">{_esc(lab)}</text>'
            f'<text x="{_f(x)}" y="114" font-size="13" fill="{muted}">{_esc(det)}</text>'
        )
        x += w + gap
    return "<g>" + "".join(parts) + "</g>"
