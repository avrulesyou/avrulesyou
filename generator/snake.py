"""The Gomu Gomu snake: an animated "snake devours the contribution graph" SVG.

A home-grown, stdlib-only replacement for the Platane/snk action (which only
produces output inside CI). The output is a GitHub-style 53x7 calendar on an
editorial paper card. Colour means intensity only: one shared POWER ramp
indexed by GitHub's contribution level 0-4.

The snake is a short gold rubber-band body of beads led by a straw hat (a
prop, no face). It rests in an S down the left gutter (frame 0, and the whole
reduced-motion picture), slithers out, sweeps the year week by week eating
every active day (never reversing on itself), and leaves off the right edge of
the card. Eaten days pop and shrink to faint crumbs, a
fading dotted wake follows the head, then the grid regrows in a left-to-right
wave and the snake fades back into its resting pose, which is exactly frame 0,
so the loop seam is invisible.

Motion plumbing:
- The route is one path: straight grid runs joined by quarter-circle corners
  of radius P/2, so its length is known exactly. Every bead rides it with CSS
  motion-path (offset-path / offset-distance keyframes); bead k simply sits a
  fixed distance behind the head, so the body is rigid along the curve and every
  bead moves at the same speed. Everything animates on the one CSS clock: SMIL
  and CSS timelines start and pause independently inside an <img>, which let
  the head drift away from the cells it was eating.
- Cells, crumbs and the regrow wave: one @keyframes per eaten day, with
  percentages taken from the head's arrival time. Only transform and opacity
  are animated.
- Sparks and wake dots: one shared @keyframes each, offset by animation-delay.
"""
from __future__ import annotations

import datetime as dt
import math

from theme import FONT_BODY, FONT_DISPLAY, FONT_SERIF, MODES, POWER, STRAW_HAT, WIDTH

W, H = WIDTH, 214
PAD = 22                    # card inner margin
X0, Y0 = 78.0, 78.0         # top-left of the grid
P = 14.0                    # cell pitch
S = 11.0                    # cell size
RX = 2.5
ROWS, COLS = 7, 53
R = P / 2                   # corner radius of the route

BEADS = 14                  # body beads behind the head
GAP = 5.0                   # px between bead centres along the route
BEAD_R0, BEAD_R1 = 6.0, 3.0  # first and last bead radius
HEAD_R = 6.6

HOLD = 1.0                  # s resting in the gutter at the start of a lap
TRAVEL = 20.0               # target s for the whole tour
STEP_MIN, STEP_MAX = 0.055, 0.18
JUMP = 0.25                 # s to (invisibly) rewind the snake to the gutter
REGROW = 1.4                # s for the regrow wave to sweep the grid
REGROW_POP = 0.5            # s for one cell to spring back
FADE_IN = 0.7               # s for the snake to fade back into its resting pose
TAIL = 2.4                  # s from leaving the card to the end of the lap
SPARK = 0.5                 # s a spark burst lives
WAKE = 2.2                  # s a wake dot lives

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]

# Editorial surfaces: cream paper, ink, gold (light); ink-blue night paper (dark).
SURFACE = {
    "light": {
        "paper_a": "#FFF6E2", "paper_b": "#FFFDF7", "edge": "#E6DCC6", "rule": "#EADFC7",
        "ink": "#1B1B1F", "muted": "#5C5C66", "accent": "#A87400", "glow": "#FFD95A",
        "glow_op": ".35", "shadow": "#5A3F00", "hat_line": "#8A6414",
        "wake": "#C99400", "crumb_op": ".42",
    },
    "dark": {
        "paper_a": "#171A21", "paper_b": "#11141B", "edge": "#2A2F3A", "rule": "#262B35",
        "ink": "#F5F1E8", "muted": "#A3A3B2", "accent": "#FFD95A", "glow": "#F6B800",
        "glow_op": ".13", "shadow": "#000000", "hat_line": "#6B4C0C",
        "wake": "#FFD95A", "crumb_op": ".5",
    },
}


# --------------------------------------------------------------------------- helpers

def _n(v: float, nd: int = 1) -> str:
    """Round and strip trailing zeros to keep the file small."""
    s = f"{v:.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _cx(c: float) -> float:
    return X0 + c * P + S / 2


def _cy(r: float) -> float:
    return Y0 + r * P + S / 2


def _tooltip(day: dict) -> str:
    d = dt.date.fromisoformat(day["date"])
    when = f"{DAY_NAMES[(d.weekday() + 1) % 7]}, {MONTHS_LONG[d.month - 1]} {d.day}, {d.year}"
    c = day["count"]
    if c <= 0:
        return f"No contributions on {when}"
    return f"{c} contribution{'s' if c != 1 else ''} on {when}"


def _md(s: str, year: bool = False) -> str:
    d = dt.date.fromisoformat(s)
    return f"{MONTHS[d.month - 1]} {d.day}" + (f", {d.year}" if year else "")


def _span(a: str, b: str) -> str:
    """'Aug 17-21' or 'Aug 30 - Sep 2' for a date range."""
    da, db = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    if da == db:
        return _md(a)
    if da.month == db.month:
        return f"{MONTHS[da.month - 1]} {da.day}&#8211;{db.day}"
    return f"{_md(a)} &#8211; {_md(b)}"


# --------------------------------------------------------------------------- planning

def _plan(active: set, rows: int = ROWS, exit_col: int = COLS + 8):
    """Left-to-right sweep tour with grid-adjacent steps and no U-turns.

    The head always finishes the leftmost week that still has food, taking the
    nearest day in it first, so the year is eaten roughly in date order.

    Returns (path, eaten): path is a list of (col, row) grid points; eaten maps
    (col, row) to the path index at which the head arrives there. The first
    points are the resting pose in the gutter (tail at the bottom, head at row
    0), so the tour starts at index `rows - 1`.
    """
    path = [(-1, r) for r in range(rows - 1, -1, -1)]
    left = set(active)
    eaten = {}
    state = {"c": -1, "r": 0, "d": (0, -1)}

    def step(dc: int, dr: int) -> None:
        state["c"] += dc
        state["r"] += dr
        state["d"] = (dc, dr)
        p = (state["c"], state["r"])
        path.append(p)
        if p in left:
            left.discard(p)
            eaten[p] = len(path) - 1

    def run(dc: int, dr: int, n: int) -> None:
        for _ in range(n):
            step(dc, dr)

    def sign(v: int) -> int:
        return (v > 0) - (v < 0)

    def go(tc: int, tr: int) -> None:
        dx, dy = tc - state["c"], tr - state["r"]
        hd, vd = (sign(dx), 0), (0, sign(dy))
        back = (-state["d"][0], -state["d"][1])
        if dx and hd != back:
            run(*hd, abs(dx))
            run(*vd, abs(dy))
        elif dy and vd != back:
            run(*vd, abs(dy))
            run(*hd, abs(dx))
        elif dx:   # straight back along the row: side-step a row, run, step back
            side = 1 if state["r"] < rows - 1 else -1
            run(0, side, 1)
            run(*hd, abs(dx))
            run(0, -side, 1)
        else:      # straight back along the column: side-step a column
            side = 1 if state["c"] < tc + 1 and state["c"] < COLS - 1 else -1
            run(side, 0, 1)
            run(*vd, abs(dy))
            run(-side, 0, 1)

    while left:
        c, r = state["c"], state["r"]
        lo = min(p[0] for p in left)          # sweep: finish the leftmost week first
        target = min((p for p in left if p[0] == lo),
                     key=lambda p: (abs(p[0] - c) + abs(p[1] - r), p[1]))
        go(*target)
    if eaten:
        if state["d"] == (-1, 0):
            run(0, 1 if state["r"] < rows - 1 else -1, 1)
        run(1, 0, max(0, exit_col - state["c"]))
    return path, eaten


# The resting body hangs from the head in a gentle S down the left gutter.
# Built backwards from the head as circular arcs (signed turn in radians, radius
# in px) so every length is exact; positive turns are clockwise on screen.
WAVE = [(0.62, 10.0), (-1.24, 10.0), (1.24, 10.0), (-1.24, 10.0), (0.62, 10.0)]


def _rest_head():
    """Where the resting head sits: the gutter column, where it bends into row 0."""
    return _cx(-1), _cy(0) + R


def _gutter(need: float):
    """The S-shaped resting route, traced backwards from the resting head.

    Returns (prims, length): prims are ('arc', x0, y0, hx, hy, turn, rad) or
    ('line', x0, y0, hx, hy, len) steps walking away from the head (heading
    down first), long enough to hold `need` px of body.
    """
    x, y = _rest_head()
    hx, hy = 0.0, 1.0
    prims, total = [], 0.0
    for turn, rad in WAVE:
        prims.append(("arc", x, y, hx, hy, turn, rad))
        x, y, hx, hy = _arc_end(x, y, hx, hy, turn, rad)
        total += abs(turn) * rad
    if total < need:
        prims.append(("line", x, y, hx, hy, need - total))
        total = need
    return prims, total


def _rot(vx: float, vy: float, a: float):
    """Rotate a vector clockwise on screen (y down) by a radians."""
    c, s = math.cos(a), math.sin(a)
    return vx * c - vy * s, vx * s + vy * c


def _arc_end(x, y, hx, hy, turn, rad, part: float = 1.0):
    nx, ny = (-hy, hx) if turn > 0 else (hy, -hx)
    cx, cy = x + nx * rad, y + ny * rad
    vx, vy = _rot(x - cx, y - cy, turn * part)
    hx2, hy2 = _rot(hx, hy, turn * part)
    return cx + vx, cy + vy, hx2, hy2


def _walk(prims: list, s: float):
    """Point at distance s along the backwards gutter route."""
    for p in prims:
        if p[0] == "arc":
            _, x, y, hx, hy, turn, rad = p
            ln = abs(turn) * rad
            if s <= ln + 1e-9:
                px, py, _, _ = _arc_end(x, y, hx, hy, turn, rad, s / ln)
                return px, py
        else:
            _, x, y, hx, hy, ln = p
            if s <= ln + 1e-9:
                return x + hx * s, y + hy * s
        s -= ln
    return x, y


def _gutter_d(prims: list) -> str:
    """Forward path data (tail end first) for the backwards gutter route."""
    pts = []
    for p in prims:
        if p[0] == "arc":
            _, x, y, hx, hy, turn, rad = p
            ex, ey, _, _ = _arc_end(x, y, hx, hy, turn, rad)
            pts.append(("A", x, y, ex, ey, turn, rad))
        else:
            _, x, y, hx, hy, ln = p
            pts.append(("L", x, y, x + hx * ln, y + hy * ln))
    out = []
    last = pts[-1]
    out.append(f"M{_n(last[3], 2)} {_n(last[4], 2)}")
    for q in reversed(pts):
        if q[0] == "L":
            out.append(f"L{_n(q[1], 2)} {_n(q[2], 2)}")
        else:
            _, x, y, ex, ey, turn, rad = q
            sweep = 0 if turn > 0 else 1        # walked forwards, the turn flips
            out.append(f"A{_n(rad)} {_n(rad)} 0 0 {sweep} {_n(x, 2)} {_n(y, 2)}")
    return "".join(out)


def _route(path: list, start: int, gutter: list, gutter_len: float):
    """Rounded SVG route: the S-shaped gutter, then grid runs with round corners.

    path[start] is the resting head's grid point (always a corner into row 0).
    Returns (d, dist, total, d0): the path data, the route distance at which
    the head is closest to each grid point, the total length and the distance
    of the resting head.
    """
    n = len(path)
    dirs = [None] + [(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]) for i in range(1, n)]
    corner = [False] * n
    for i in range(1, n - 1):
        corner[i] = dirs[i] != dirs[i + 1]
    quarter = math.pi * R / 2

    def pt(i: int):
        return _cx(path[i][0]), _cy(path[i][1])

    out = [_gutter_d(gutter)]
    dist = [0.0] * n
    s = d0 = gutter_len
    for i in range(start, n):
        seg = 0.0 if i == start else P - (R if corner[i - 1] else 0) - (R if corner[i] else 0)
        s += seg
        px, py = pt(i)
        dx, dy = dirs[i]
        if corner[i]:
            ex, ey = px - dx * R, py - dy * R
            if seg > 1e-6:
                out.append(f"H{_n(ex)}" if dy == 0 else f"V{_n(ey)}")
            nx, ny = dirs[i + 1]
            sweep = 1 if dx * ny - dy * nx > 0 else 0
            out.append(f"A{_n(R)} {_n(R)} 0 0 {sweep} {_n(px + nx * R)} {_n(py + ny * R)}")
            dist[i] = s + quarter / 2
            s += quarter
        else:
            dist[i] = s
            if i + 1 >= n:
                out.append(f"H{_n(px)}" if dy == 0 else f"V{_n(py)}")
    return "".join(out), dist, s, d0


# --------------------------------------------------------------------------- snake art

def _hat(sf: dict) -> str:
    """A straw hat seen slightly from above: brim, crown, red band, weave, shading."""
    line = sf["hat_line"]
    return (
        f'<ellipse cx=".6" cy="1.6" rx="10.2" ry="3.2" fill="{sf["shadow"]}" opacity=".22"/>'
        f'<ellipse rx="10.6" ry="3.9" fill="url(#brim)" stroke="{line}" stroke-width=".7"/>'
        f'<path d="M-7.6.9Q0 3.3 7.6.9" fill="none" stroke="{line}" stroke-width=".5" opacity=".45"/>'
        f'<path d="M-5.7-.2C-6.1-6.4-3.4-9.4 0-9.4S6.1-6.4 5.7-.2Q0 1.5-5.7-.2Z" '
        f'fill="url(#crown)" stroke="{line}" stroke-width=".7"/>'
        f'<path d="M-5.8-1.1Q0 .6 5.8-1.1L5.6-3.6Q0-2.1-5.6-3.6Z" fill="{STRAW_HAT["straw_band"]}"/>'
        f'<path d="M-5.6-3.6Q0-2.1 5.6-3.6" fill="none" stroke="#FFFFFF" stroke-width=".45" opacity=".35"/>'
        f'<path d="M-3.1-6.9Q-1.6-8.4.4-8.5" fill="none" stroke="#FFFFFF" stroke-width="1.1" '
        f'stroke-linecap="round" opacity=".55"/>'
        f'<path d="M-9.1-.3Q-8-1.5-6.3-1.8M6.4-1.8Q8-1.5 9.1-.3" fill="none" stroke="#FFFFFF" '
        f'stroke-width=".6" stroke-linecap="round" opacity=".4"/>'
    )


def _bead_r(k: int) -> float:
    """Radius of body bead k (1 = right behind the head)."""
    t = (k - 1) / max(1, BEADS - 1)
    return BEAD_R0 + (BEAD_R1 - BEAD_R0) * t ** 1.3


def _snake_art(sf: dict, motion=None, rest_xy=None) -> str:
    """The body beads, the head bead and the straw hat.

    With motion=None every bead is placed by rest_xy(k) (the resting pose).
    Otherwise motion(k) returns the CSS classes that move bead k (0 = head).
    """
    out = []

    def g(k: int, inner: str, cls: str = "") -> str:
        c = f' class="{cls}"' if cls else ""
        if motion is None:
            x, y = rest_xy(k)
            return f'<g transform="translate({_n(x, 2)},{_n(y, 2)})"><g{c}>{inner}</g></g>'
        return f'<g class="{motion(k)}"><g{c}>{inner}</g></g>'

    # soft sun glow riding under the head
    out.append(g(0, '<circle r="15" fill="url(#halo)"/>'))
    for k in range(BEADS, 0, -1):          # tail first, so the head lands on top
        r = _bead_r(k)
        out.append(g(
            k,
            f'<circle cx=".9" cy="1.3" r="{_n(r, 2)}" fill="{sf["shadow"]}" opacity=".16"/>'
            f'<circle r="{_n(r, 2)}" fill="url(#bead)" class="bs"/>',
            f"pb p{k % 6}" if motion is not None else "",
        ))
    out.append(g(
        0,
        f'<circle cx=".9" cy="1.4" r="{HEAD_R}" fill="{sf["shadow"]}" opacity=".18"/>'
        f'<circle r="{HEAD_R}" fill="url(#bead)" class="bs"/>'
        f'<g transform="translate(0,-3.2) scale(1.2)"><g class="wob">{_hat(sf)}</g></g>',
    ))
    return "".join(out)


# --------------------------------------------------------------------------- render

def render_snake(stats: dict, mode: str) -> str:
    m = MODES[mode]
    sf = SURFACE[mode]
    ramp = POWER[mode]
    weeks = (stats.get("weeks") or [])[:COLS]
    days = [d for w in weeks for d in w]

    computed_total = sum(max(0, d.get("count", 0)) for d in days)
    total = (stats.get("totals") or {}).get("contributions", computed_total)
    active_days = sum(1 for d in days if d.get("count", 0) > 0)
    best = max(days, key=lambda d: d.get("count", 0)) if days else None
    streak = stats.get("streak") or {}

    # ---- plan + timing
    cells = {}
    for c, w in enumerate(weeks):
        for d in w:
            cells[(c, d["weekday"])] = d
    active = {p for p, d in cells.items() if d.get("count", 0) > 0}
    exit_col = COLS + 2 + math.ceil((BEADS * GAP + 30) / P)
    path, eaten = _plan(active, exit_col=exit_col)
    start = ROWS - 1                       # path index of the resting head
    animated = bool(eaten)

    gutter, gutter_len = _gutter(BEADS * GAP + 2)
    if animated:
        route, dist, length, d0 = _route(path, start, gutter, gutter_len)
    else:
        route, dist, length, d0 = "", [], 0.0, 0.0
    if animated:
        moves = len(path) - 1 - start
        step = min(STEP_MAX, max(STEP_MIN, TRAVEL / moves))
        speed = P / step                   # px per second
        # the head runs until the last bead is past the card edge
        travel = (length - d0) / speed
        t_out = HOLD + travel
        dur = round(t_out + TAIL, 2)
    else:
        speed = travel = t_out = 0.0
        dur = 1.0
    ds = f"{_n(dur, 2)}s"

    def at(i: int) -> float:
        """Seconds into the lap when the head is closest to path point i."""
        return HOLD + (dist[i] - d0) / speed

    def pct(t: float) -> str:
        return _n(min(100.0, max(0.0, t / dur * 100)), 2) + "%"

    # ---- CSS
    css = [
        f"text{{font-family:{FONT_BODY};fill:{sf['muted']};font-size:13px}}",
        f".t{{font-family:{FONT_DISPLAY};fill:{sf['ink']};font-size:22px;letter-spacing:.045em}}",
        f".s{{font-family:{FONT_SERIF};font-style:italic;fill:{sf['muted']};font-size:15px;letter-spacing:0}}",
        f".n{{font-family:{FONT_BODY};font-style:normal;font-weight:700;fill:{sf['accent']}}}",
        f".k{{fill:{sf['ink']};font-weight:600}}",
        ".bs{stroke:#9A6A00;stroke-opacity:.4;stroke-width:.6}",
    ]
    for i in range(5):
        css.append(f".v{i}{{fill:{ramp[i]}}}")
    css.append(".rest{display:none}")
    if animated:
        lap = f"{ds} infinite"
        css.append(f".e{{transform-box:fill-box;transform-origin:center;animation:{lap} linear}}")
        # sparks
        sp = _n(SPARK / dur * 100, 3)
        css.append(
            f".sp{{opacity:0;animation:sp {lap} cubic-bezier(.2,.7,.3,1)}}"
            f"@keyframes sp{{0%{{opacity:1;transform:scale(.45)}}{sp}%,100%{{opacity:0;transform:scale(1.9)}}}}"
        )
        # wake dots
        wk = _n(WAKE / dur * 100, 3)
        css.append(
            f".wk{{fill:{sf['wake']};opacity:0;transform-box:fill-box;transform-origin:center;"
            f"animation:wk {lap} cubic-bezier(.4,0,.6,1)}}"
            f"@keyframes wk{{0%{{opacity:0;transform:scale(.4)}}{_n(0.12 / dur * 100, 3)}%{{opacity:.7;"
            f"transform:scale(1)}}{wk}%,100%{{opacity:0;transform:scale(.5)}}}}"
        )
        # the live snake: visible, hidden while it rewinds, fades back into its resting pose
        # hide a beat before the rewind starts (the tail is already past the edge)
        f0, f1 = t_out - 0.15, dur - FADE_IN
        css.append(
            f".live{{animation:lv {lap} linear}}"
            f"@keyframes lv{{0%,{pct(f0)}{{opacity:1}}{pct(f0 + 0.02)},{pct(f1)}{{opacity:0;"
            f"animation-timing-function:cubic-bezier(.3,0,.2,1)}}100%{{opacity:1}}}}"
            f".rise{{animation:rs {lap} linear}}"
            f"@keyframes rs{{0%,{pct(f0)}{{transform:translate(0,0)}}{pct(f0 + 0.02)},{pct(f1)}{{transform:translate(0,-6px);"
            f"animation-timing-function:cubic-bezier(.34,1.5,.64,1)}}100%{{transform:translate(0,0)}}}}"
        )
        # rubber body: a peristaltic swell travelling down the beads, a wobbling hat
        css.append(
            ".pb{animation:pb .9s ease-in-out infinite alternate}"
            "@keyframes pb{from{transform:scale(.94)}to{transform:scale(1.08)}}"
            + "".join(f".p{i}{{animation-delay:-{_n(i * .15, 2)}s}}" for i in range(6))
            + ".wob{animation:wb 1.1s ease-in-out infinite alternate}"
            "@keyframes wb{from{transform:rotate(-7deg)}to{transform:rotate(6deg)}}"
        )
    else:
        css.append(".idle{animation:bob 2.6s ease-in-out infinite}"
                   "@keyframes bob{50%{transform:translate(0,-2px)}}")

    # ---- grid, crumbs, sparks, wake
    grid, overlays, sparks, wake, kf = [], [], [], [], []
    tips = len(eaten) <= 200
    for (c, r), d in sorted(cells.items()):
        x, y = _n(X0 + c * P), _n(Y0 + r * P)
        geo = f'x="{x}" y="{y}" width="{_n(S)}" height="{_n(S)}" rx="{RX}"'
        # hover text only shows when the SVG is opened directly, so active days get
        # it while the file is small; a fully active year skips it to stay lean
        tip = f"<title>{_tooltip(d)}</title>" if d.get("count", 0) > 0 and tips else ""
        lvl = max(0, min(4, int(d.get("level", 0))))
        if d.get("count", 0) > 0 and lvl == 0:
            lvl = 1
        if (c, r) in eaten and animated:
            k = len(kf)
            ta = at(eaten[(c, r)])
            rg = t_out + 0.1 + REGROW * (c / max(1, COLS - 1)) + 0.04 * r
            # base style is scale 1 / opacity 1, so 0% is implied; 2-decimal stops keep it lean
            kf.append(
                f"@keyframes e{k}{{{pct(ta - 0.06)}{{transform:none;opacity:1;animation-timing-function:ease-out}}"
                f"{pct(ta + 0.05)}{{transform:scale(1.32);animation-timing-function:cubic-bezier(.6,0,.3,1)}}"
                f"{pct(ta + 0.42)},{pct(rg)}{{transform:scale(.3);opacity:{sf['crumb_op']};"
                f"animation-timing-function:cubic-bezier(.34,1.56,.64,1)}}"
                f"{pct(rg + REGROW_POP)},100%{{transform:none;opacity:1}}}}"
            )
            grid.append(f'<rect class="v0" {geo}/>')
            overlays.append(f'<rect class="e v{lvl}" style="animation-name:e{k}" {geo}>{tip}</rect>')
            sparks.append(
                f'<g transform="translate({_n(_cx(c))},{_n(_cy(r))})">'
                f'<use href="#k{max(2, lvl)}" class="sp" style="animation-delay:{_n(ta, 2)}s"/></g>'
            )
        else:
            grid.append(f'<rect class="v{lvl}" {geo}>{tip}</rect>')
    if animated:
        for i in range(start + 1, len(path)):
            c, r = path[i]
            if 0 <= c < COLS and (c, r) not in eaten:
                wake.append(
                    f'<circle class="wk" style="animation-delay:{_n(at(i), 2)}s" '
                    f'cx="{_n(_cx(c))}" cy="{_n(_cy(r))}" r="1.7"/>'
                )

    # ---- month + weekday labels (months sit on the first week that starts in them)
    labels = []
    marks = []
    prev_month = None
    for c, w in enumerate(weeks):
        if not w:
            continue
        mo = dt.date.fromisoformat(w[0]["date"]).month
        if mo != prev_month:
            marks.append((c, mo))
        prev_month = mo
    for i, (c, mo) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else None
        if (nxt is not None and nxt - c < 3) or c > len(weeks) - 2:
            continue
        labels.append(f'<text x="{_n(X0 + c * P)}" y="{_n(Y0 - 8)}">{MONTHS[mo - 1]}</text>')
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        labels.append(f'<text x="{_n(X0 - 26)}" y="{_n(_cy(r) + 4.5)}" text-anchor="end">{name}</text>')

    # ---- header
    grid_right = X0 + (COLS - 1) * P + S
    noun = "contribution" if total == 1 else "contributions"
    if total > 0:
        stat = f'devouring <tspan class="n">{total:,}</tspan> {noun}'
    else:
        stat = "waiting for the first contribution"
    header = (
        f'<text x="{PAD}" y="38" class="t">THE GOMU GOMU SNAKE'
        f'<tspan class="s" dx="12">{stat}</tspan></text>'
        f'<path d="M{PAD} 52.5H{_n(grid_right)}" stroke="{sf["rule"]}"/>'
        f'<path d="M{PAD} 52.5h44" stroke="{STRAW_HAT["sun_gold"]}" stroke-width="2"/>'
    )

    legend = [f'<text x="{_n(grid_right)}" y="37" text-anchor="end">More</text>']
    lx = grid_right - 37 - 5 * 14 + 3
    for i in range(5):
        legend.append(f'<rect class="v{i}" x="{_n(lx + i * 14)}" y="26.5" width="11" height="11" rx="{RX}"/>')
    legend.append(f'<text x="{_n(lx - 7)}" y="37" text-anchor="end">Less</text>')

    # ---- footer
    fy = H - 17
    bits = []
    if active_days and best is not None:
        bits.append(f'<tspan class="k">{active_days}</tspan> active day{"s" if active_days != 1 else ""}')
        bits.append(f'best day <tspan class="k">{best["count"]}</tspan> on {_md(best["date"])}')
        longest = int(streak.get("longest") or 0)
        if longest > 1 and streak.get("longest_start") and streak.get("longest_end"):
            bits.append(f'longest streak <tspan class="k">{longest}</tspan> days, '
                        f'{_span(streak["longest_start"], streak["longest_end"])}')
        foot = [f'<text x="{PAD}" y="{fy}">{" &#183; ".join(bits)}</text>']
    else:
        foot = [f'<text x="{PAD}" y="{fy}">The grid is quiet. The snake is resting.</text>']
    if days:
        foot.append(
            f'<text x="{_n(grid_right)}" y="{fy}" text-anchor="end">'
            f'{_md(days[0]["date"], True)} &#8211; {_md(days[-1]["date"], True)}</text>'
        )

    # ---- snake
    def rest_xy(k: int):
        """Resting pose: the body hangs in an S down the gutter from the head."""
        return _walk(gutter, k * GAP)

    rest = f'<g class="rest">{_snake_art(sf, rest_xy=rest_xy)}</g>'
    if animated:
        t1, t2, t3 = HOLD / dur, t_out / dur, (t_out + JUMP) / dur

        p1, p2, p3 = (_n(t * 100, 3) + "%" for t in (t1, t2, t3))
        css.append(f'.mv{{offset-path:path("{route}");offset-rotate:0deg;animation:{lap} linear}}')

        def motion(k: int) -> str:
            a = _n((d0 - k * GAP) / length * 100, 3)
            b = _n((length - k * GAP) / length * 100, 3)
            css.append(f".m{k}{{animation-name:m{k}}}@keyframes m{k}{{0%,{p1}{{offset-distance:{a}%}}"
                       f"{p2}{{offset-distance:{b}%}}{p3},100%{{offset-distance:{a}%}}}}")
            return f"mv m{k}"

        live = (f'<g clip-path="url(#card)"><g class="live"><g class="rise">'
                f'{_snake_art(sf, motion)}</g></g></g>')
        route_def = "".join(
            f'<path id="k{i}" d="M0-7h0M6.1-3.5h0M6.1 3.5h0M0 7h0M-6.1 3.5h0M-6.1-3.5h0" fill="none" '
            f'stroke="{ramp[i]}" stroke-width="2.4" stroke-linecap="round"/>' for i in (2, 3, 4))
    else:
        live = f'<g class="live idle">{_snake_art(sf, rest_xy=rest_xy)}</g>'
        route_def = ""

    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}"
               ".live,.fx{display:none}.rest{display:inline}}")

    lap_txt = f" One lap takes about {round(dur)} seconds." if animated else ""
    title = "The Gomu Gomu snake devours the contribution graph"
    desc = (f"A GitHub-style contribution calendar for the last year with {total:,} {noun} "
            f"over {active_days} active day{'s' if active_days != 1 else ''}. Colour shows intensity, "
            f"from pale for quiet days through gold to crimson for the busiest. A short gold snake "
            f"wearing a straw hat slithers out of the left margin, eats every active day week by "
            f"week, and leaves on the right while the grid regrows.{lap_txt}")

    return "".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="sn-title sn-desc">',
        f'<title id="sn-title">{title}</title>',
        f'<desc id="sn-desc">{desc}</desc>',
        "<defs>",
        f'<linearGradient id="paper" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{sf["paper_a"]}"/><stop offset=".6" stop-color="{sf["paper_b"]}"/>'
        f'</linearGradient>',
        f'<radialGradient id="sun" cx=".06" cy="0" r=".5" gradientTransform="matrix(1 0 0 2.2 0 0)">'
        f'<stop offset="0" stop-color="{sf["glow"]}" stop-opacity="{sf["glow_op"]}"/>'
        f'<stop offset="1" stop-color="{sf["glow"]}" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="bead" cx=".36" cy=".32" r=".75">'
        '<stop offset="0" stop-color="#FFF1B8"/><stop offset=".35" stop-color="#FFD24A"/>'
        f'<stop offset=".75" stop-color="{STRAW_HAT["sun_gold"]}"/><stop offset="1" stop-color="#D99A00"/>'
        '</radialGradient>',
        '<radialGradient id="halo"><stop offset="0" stop-color="#FFD95A" stop-opacity=".55"/>'
        '<stop offset=".6" stop-color="#F6B800" stop-opacity=".16"/>'
        '<stop offset="1" stop-color="#F6B800" stop-opacity="0"/></radialGradient>',
        '<linearGradient id="crown" x1="0" y1="0" x2="1" y2=".35">'
        '<stop offset="0" stop-color="#F7DF98"/><stop offset=".55" stop-color="#E9C46A"/>'
        '<stop offset="1" stop-color="#C99A3E"/></linearGradient>',
        '<linearGradient id="brim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#F4D78A"/><stop offset=".6" stop-color="#E9C46A"/>'
        '<stop offset="1" stop-color="#CFA24A"/></linearGradient>',
        f'<clipPath id="card"><rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="13"/></clipPath>',
        route_def,
        "</defs>",
        f"<style>{''.join(css)}{''.join(kf)}</style>",
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="url(#paper)" stroke="{sf["edge"]}"/>',
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="url(#sun)"/>',
        header,
        "".join(legend),
        "".join(labels),
        "<g>", "".join(grid), "</g>",
        f'<g class="fx">{"".join(wake)}</g>',
        "<g>", "".join(overlays), "</g>",
        f'<g class="fx">{"".join(sparks)}</g>',
        rest,
        live,
        "".join(foot),
        "</svg>",
    ])
