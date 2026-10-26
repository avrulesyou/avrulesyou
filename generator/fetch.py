"""Fetch contribution data and derive the stats every card renders from.

Only aggregate counts are read. The calendar already includes private
contributions when "Private contributions" is enabled on the profile, so no
repo-scoped token is needed and no private repo names are ever requested.

Usage:
  GITHUB_TOKEN=... python generator/fetch.py          # CI
  python generator/fetch.py                           # local, falls back to `gh`
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("PROFILE_LOGIN", "avrulesyou")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "stats.json"

QUERY = """
query($login: String!) {
  user(login: $login) {
    login name bio location createdAt avatarUrl(size: 256)
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
    contributionsCollection {
      startedAt endedAt
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
      totalRepositoryContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

LEVEL_INDEX = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def graphql() -> dict:
    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        out = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={LOGIN}"],
            check=True, capture_output=True, text=True,
        ).stdout
        return json.loads(out)
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-generator"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def download_avatar(url: str) -> bool:
    """Save the avatar so cards can embed it (SVGs in <img> can't load URLs)."""
    target = ROOT / "data" / "avatar.png"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            target.write_bytes(resp.read())
        return True
    except Exception:
        # Local fallback: some corporate proxies break Python TLS but not curl.
        return subprocess.run(["curl", "-sfL", "-o", str(target), url]).returncode == 0


def streaks(days: list[dict], today: str) -> dict:
    days = sorted((d for d in days if d["date"] <= today), key=lambda d: d["date"])
    longest = cur = 0
    longest_range = (None, None)
    start = None
    previous = None
    for d in days:
        if d["count"] > 0:
            if previous is None or (dt.date.fromisoformat(d["date"]) - dt.date.fromisoformat(previous)).days != 1:
                cur, start = 0, None
            start = start or d["date"]
            cur += 1
            if cur > longest:
                longest, longest_range = cur, (start, d["date"])
        else:
            cur, start = 0, None
        previous = d["date"]

    # Current streak: today may still be empty without breaking it.
    past = [d for d in days if d["date"] <= today]
    if past and past[-1]["date"] == today and past[-1]["count"] == 0:
        past = past[:-1]
    current = 0
    current_start = None
    expected = dt.date.fromisoformat(past[-1]["date"]) if past else None
    if expected is not None and (dt.date.fromisoformat(today) - expected).days > 1:
        past = []
    for d in reversed(past):
        if d["count"] == 0 or dt.date.fromisoformat(d["date"]) != expected:
            break
        current += 1
        current_start = d["date"]
        expected -= dt.timedelta(days=1)
    return {
        "current": current,
        "current_start": current_start,
        "longest": longest,
        "longest_start": longest_range[0],
        "longest_end": longest_range[1],
    }


def derive(raw: dict) -> dict:
    user = (raw.get("data") or {}).get("user")
    if not user or not user.get("contributionsCollection"):
        raise ValueError("GitHub did not return a complete contribution profile")
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = [
        [
            {
                "date": d["date"],
                "count": d["contributionCount"],
                "level": LEVEL_INDEX[d["contributionLevel"]],
                "weekday": d["weekday"],
            }
            for d in w["contributionDays"]
        ]
        for w in cal["weeks"]
    ]
    days = [d for w in weeks for d in w]
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    active = [d for d in days if d["count"] > 0]
    best = max(days, key=lambda d: d["count"]) if days else None
    weekday_totals = [0] * 7
    for d in days:
        weekday_totals[d["weekday"]] += d["count"]
    joined = user["createdAt"][:10]
    since_join = [d for d in days if d["date"] >= joined]
    months: dict[str, int] = {}
    for d in days:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["count"]

    return {
        "login": user["login"],
        "name": user["name"],
        "bio": user["bio"],
        "location": user["location"],
        "joined": joined,
        "followers": user["followers"]["totalCount"],
        "public_repos": user["repositories"]["totalCount"],
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "range": {"start": cc["startedAt"][:10], "end": cc["endedAt"][:10]},
        "totals": {
            "contributions": cal["totalContributions"],
            "commits": cc["totalCommitContributions"],
            "pull_requests": cc["totalPullRequestContributions"],
            "reviews": cc["totalPullRequestReviewContributions"],
            "issues": cc["totalIssueContributions"],
            "repos_created": cc["totalRepositoryContributions"],
            "private": cc["restrictedContributionsCount"],
            "public": cal["totalContributions"] - cc["restrictedContributionsCount"],
        },
        "streak": streaks(days, today),
        "active_days": len(active),
        "days_since_join": len(since_join),
        "active_rate_since_join": round(len(active) / max(1, len(since_join)), 3),
        "best_day": {"date": best["date"], "count": best["count"]} if best else None,
        "weekday_totals": weekday_totals,
        "busiest_weekday": WEEKDAYS[weekday_totals.index(max(weekday_totals))],
        "monthly": months,
        "weeks": weeks,
    }


def main() -> None:
    raw = graphql()
    if "errors" in raw:
        sys.exit(f"GraphQL errors: {raw['errors']}")
    stats = derive(raw)
    stats["avatar"] = "data/avatar.png" if download_avatar(raw["data"]["user"]["avatarUrl"]) else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=1))
    t = stats["totals"]
    print(f"{stats['login']}: {t['contributions']} contributions "
          f"({t['private']} private), streak {stats['streak']}")


if __name__ == "__main__":
    main()
