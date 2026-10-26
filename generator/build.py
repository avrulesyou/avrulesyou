"""Render every data-driven SVG into dist/ for both GitHub themes.

Run generator/fetch.py first; this only reads data/stats.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import battlefield  # noqa: E402
import cards  # noqa: E402
import snake  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

RENDERERS = {
    "wanted": cards.render_wanted,
    "bingo": cards.render_bingo,
    "seals": cards.render_seals,
    "battlefield": battlefield.render_battlefield,
    "snake": snake.render_snake,
}


def main() -> None:
    stats = json.loads((ROOT / "data" / "stats.json").read_text())
    DIST.mkdir(exist_ok=True)
    for name, render in RENDERERS.items():
        for mode in ("light", "dark"):
            out = DIST / f"{name}-{mode}.svg"
            out.write_text(render(stats, mode))
            print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
