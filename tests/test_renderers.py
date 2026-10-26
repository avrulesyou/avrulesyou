from __future__ import annotations

import copy
import sys
import unittest
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "generator"))

import build

sys.path.insert(0, str(ROOT / "scripts"))
import check

# Renderers whose output is not yet held to the check.py policy (the README does not reference them).
POLICY_EXEMPT = set()


def fixture_days(start: date, counts: list[int], level: int) -> list[list[dict]]:
    weeks: list[list[dict]] = []
    for index, count in enumerate(counts):
        day = start + timedelta(days=index)
        weekday = (day.weekday() + 1) % 7
        if not weeks or weekday == 0:
            weeks.append([])
        weeks[-1].append({"date": day.isoformat(), "count": count, "level": level if count else 0, "weekday": weekday})
    return weeks


def full_year(count: int = 1) -> dict:
    weeks = fixture_days(date(2026, 1, 1), [count] * 365, 1)
    monthly: dict[str, int] = defaultdict(int)
    weekdays = [0] * 7
    for week in weeks:
        for day in week:
            monthly[day["date"][:7]] += day["count"]
            weekdays[day["weekday"]] += day["count"]
    return {
        "name": "Example",
        "login": "example",
        "joined": "2026-01-01",
        "totals": {"contributions": 365 * count, "private": 365 * count, "public": 0},
        "weeks": weeks,
        "streak": {"current": 0, "longest": 365, "longest_start": "2026-01-01", "longest_end": "2026-12-31"},
        "monthly": dict(monthly),
        "weekday_totals": weekdays,
        "active_days": 365,
        "days_since_join": 365,
        "best_day": {"date": "2026-01-01", "count": count},
    }


def renderer_fixtures() -> dict[str, dict]:
    zero = {
        "name": "Zero activity",
        "login": "example",
        "joined": "2026-01-04",
        "totals": {"contributions": 0, "private": 0, "public": 0},
        "weeks": fixture_days(date(2026, 1, 4), [0] * 7, 0),
        "streak": {"current": 0, "longest": 0},
        "monthly": {"2026-01": 0},
        "weekday_totals": [0] * 7,
        "active_days": 0,
        "days_since_join": 7,
        "best_day": {"date": "2026-01-04", "count": 0},
    }
    one = copy.deepcopy(zero)
    one.update({
        "totals": {"contributions": 47, "private": 47, "public": 0},
        "weeks": fixture_days(date(2026, 1, 4), [0, 47, 0, 0, 0, 0, 0], 4),
        "monthly": {"2026-01": 47},
        "weekday_totals": [0, 47, 0, 0, 0, 0, 0],
        "active_days": 1,
        "streak": {"current": 0, "longest": 1, "longest_start": "2026-01-05", "longest_end": "2026-01-05"},
        "best_day": {"date": "2026-01-05", "count": 47},
    })
    huge = full_year(1000000)
    huge["name"] = "Abhishek Vishwakarma " * 8
    return {"empty": {}, "zero": zero, "one_day": one, "full_year": full_year(), "huge_long_name": huge}


class RendererStructureTests(unittest.TestCase):
    def test_all_renderers_all_modes_all_fixtures(self) -> None:
        for fixture_name, stats in renderer_fixtures().items():
            for name, render in build.RENDERERS.items():
                for mode in ("light", "dark"):
                    with self.subTest(fixture=fixture_name, renderer=name, mode=mode):
                        rendered = render(copy.deepcopy(stats), mode)
                        payload = rendered.encode("utf-8")
                        self.assertLessEqual(len(payload), 250000)
                        root = ET.fromstring(payload)
                        self.assertEqual(root.tag.rsplit("}", 1)[-1], "svg")
                        self.assertEqual(root.get("role"), "img")
                        children = list(root)
                        self.assertTrue(children, "SVG must start with a title")
                        self.assertEqual(children[0].tag.rsplit("}", 1)[-1], "title")
                        self.assertTrue("".join(children[0].itertext()).strip())
                        self.assertTrue(any(
                            node.tag.rsplit("}", 1)[-1] == "desc" and "".join(node.itertext()).strip()
                            for node in root.iter()
                        ), "SVG must include a nonempty desc")

    def test_renderer_output_meets_the_svg_policy(self) -> None:
        for fixture_name, stats in renderer_fixtures().items():
            for name, render in build.RENDERERS.items():
                if name in POLICY_EXEMPT:
                    continue
                for mode in ("light", "dark"):
                    with self.subTest(fixture=fixture_name, renderer=name, mode=mode):
                        self.assertEqual(check.check_svg_bytes(render(copy.deepcopy(stats), mode).encode("utf-8")), [])


if __name__ == "__main__":
    unittest.main()
