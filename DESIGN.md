# Profile design spec: "The Engineering Atlas"

The GitHub profile for `avrulesyou` (Abhishek Vishwakarma, AI Engineer at REI Systems).
The theme is **One Piece meets Naruto**. Early on it was Gear 5 Luffy and Zoro against
Itachi and Pain, but after several rounds of feedback it is now carried by **scenery and
props only**. Treat this file as the source of truth. When it disagrees with older notes,
this file wins.

All design tokens live in [`generator/theme.py`](generator/theme.py). Use those exact hex values.

## Approved redesign direction

The October 26 redesign replaces the collection of equally prominent widgets with one
cinematic engineering atlas. The README is a complete, readable introduction and an
invitation into the interactive War Room. The site is the immersive destination, not a
prerequisite for understanding the creator.

Use one original harbor-to-storm skyline, warm paper and ink, restrained gold/crimson,
cartographic detail, clear typography, generous negative space, and deliberate motion.
The existing identity, privacy, original-art and scenery-only rules below remain binding.
The former section inventory below documents the retained asset vocabulary, not the new
mandatory order.

The new README order is hero, native introduction and exploration link, complete
contribution-world preview, prominent capabilities, compact toolkit, career journey,
achievements, optional collectibles, and footer. Dense side-by-side posters and repeating
decorative chapter ribbons are not primary content. Essential explanations use native
text that remains readable on mobile.

The site defaults to a complete straight-on scene, with explicit exploration, highlights,
camera presets, filters and user-triggered replay. Date selection synchronizes the scene,
heatmap and inspector. Touch exploration is opt-in so the canvas does not trap page
scrolling. Reduced-motion and static fallback views are finished compositions. Light is
the default and dark receives equal art direction.

`site/model.js` is the single source for interactive metric definitions. Calendar dates,
not the collection query's enclosing range, define the displayed period. Consistency uses
observed calendar days on or after this account's join date. Competition ranks preserve
ties. Monthly momentum compares matching elapsed dates, explicitly labels its periods,
and does not invent a percentage for a zero or missing comparison baseline. Contribution
counts are activity, not an engineering-quality score. No project outcomes are invented.

## Sections of the README, top to bottom (October 26 integration)

| # | Section | Asset(s) | Generator |
|---|---------|----------|-----------|
| 0 | **Hero banner.** Scenery only, name in the centre, "Engineering Atlas" eyebrow | `assets/banner-{mode}.svg`, 840×370 | `generator/art_banner.py` |
| 0b | **Field-note caption.** Editorial paper strip with a compass mark and a typewriter cycling four lines (gold caret for the sunlit lines, crimson for the storm lines) | `assets/caption-{mode}.svg`, 840×70 | `generator/art_caption.py` |
| — | **Intro** (native Markdown): "AI Expert · developing solutions since 2016 · AI Engineer at REI Systems", location and tagline, current focus, links row | README | README |
| 1 | **Contribution world.** Straight-on 3D harbor: open water before the join date (sun path, ship, lighthouse), then one tower per day; HUD with total, active days, peak, busiest weekday, streak and labelled momentum. Links to the War Room | `dist/battlefield-{mode}.svg`, 840×690 | `generator/battlefield.py` |
| 1b | **Gomu Gomu snake** eating the calendar, straw-hat head, no face | `dist/snake-{mode}.svg`, 840×214 | `generator/snake.py` |
| — | **"The numbers, with context"** privacy paragraph, then **What I build** (three native sub-sections) | README | README |
| 2 | **Collectibles.** Most Valued poster and Field Dossier side by side in a 2-cell table, with a one-line native caption | `dist/wanted-{mode}.svg` and `dist/bingo-{mode}.svg` | `generator/cards.py` |
| 3 | **Toolkit.** Three-sword table (skillicons.dev and shields.io) plus a native text list | README HTML | README |
| 4 | **Achievements.** Achievement rings plus the native line | `dist/seals-{mode}.svg`, 840×230 | `generator/cards.py` |
| 5 | **The route so far.** Career line and the "About this atlas" details | README Markdown | README |
| 6 | **Footer:** "To be continued…" | `assets/footer-{mode}.svg` | `generator/art_footer.py` |
| — | **War Room**, the interactive 3D page on GitHub Pages | `site/` (Three.js 0.170.0 from jsDelivr) | hand-written JS |

The section ribbons (`assets/arc-*.svg`) are no longer used; Markdown headings divide the
page. `assets/` holds static art, committed to `main`. `dist/` holds data-driven art: CI
rebuilds it daily and publishes it to the `output` branch, which the README loads from
`raw.githubusercontent.com/avrulesyou/avrulesyou/output/…`. CI also stages
`dist/battlefield-*.svg` and `data/stats.json` inside `site/` before uploading Pages.

## Rules the user has set (all confirmed in conversation)

- **Light and dark:** every image has a light and a dark variant with the same composition,
  and the README swaps them with `<picture>`. The local preview and the War Room default to
  **light**.
- **No characters:** the user rejected hand-drawn faces and then silhouettes, so there are no
  drawn people anywhere. Use props and scenery: sun, ship, straw hat, katanas, red clouds,
  red moon, Sharingan, rods, crows, rain and skyline.
- **No faction names:** never write "Straw Hats", "Akatsuki" or "vs"/"versus" in visible
  text, alt text or SVG `<title>`/`<desc>`. The singular "straw hat" is an allowed prop.
  `scripts/check.py` enforces this.
- **English only:** no Japanese text or kanji.
- **Colour means intensity:** contribution colour comes from `POWER` in `theme.py`, indexed
  by GitHub's contribution level 0–4 (gold for light days, crimson for the busiest). Never split
  the data into two sides.
- **Tone:** fun but professional, because this is a work account.
  - No "WANTED", "threat", "dead or alive" or violence words.
  - The poster title is **MOST VALUED · ENGINEER**, with the tagline "for shipping perfect
    software in record time".
  - The Bingo Book uses productive words: "Focus by weekday", "Monthly momentum" and
    "Archive · Achievements on record".
- **Positioning copy:** "AI Expert · developing solutions since 2016", "AI Engineer at REI
  Systems", and the career line "2016–2025 banking, fintech and blockchain → 2025–now AI
  engineering". Keep AI mentions light.
- **Privacy:** show aggregate counts only. Never print org names, private repo names or
  project codenames.
- **Art:** original only. Don't copy official artwork or screenshots. A reference image the
  user shared was anime frames, which can't be used.

## Hard constraints (GitHub renders README SVGs inside `<img>`, through the camo proxy)

- **No external resources:** no `href`/`src` URLs, no `@import`, no web fonts and no JS.
  Embed raster images as base64 (the avatar only).
- **Fonts:** use only the system font stacks in `theme.py`.
- **Animation:** CSS `@keyframes` or SMIL only.
  - Use cubic-bezier easing, staggered prime-ish durations, and animate only transform and
    opacity.
  - Always include `@media (prefers-reduced-motion: reduce)`.
  - Frame 0 must be complete, including the contribution world and all towers.
- **Size:** each file must stay at or below 250 KB.
- **Accessibility:** set `role="img"`, and give the root a `<title>` as its first child and
  a `<desc>`.
- **Validity:** each file must parse as valid XML, and `&` must be escaped.
- **Layout:** 840 px is the full README width. Body text must be at least 13 px at that width.
  Essential numbers are repeated in native Markdown so phones never depend on text inside a
  scaled-down SVG.
- **Momentum:** always the matched elapsed-period comparison from `battlefield.matched_momentum`
  / `site/model.js` (for example "Oct 1–25 over Sep 1–25"), never a partial month against a
  whole month, and no percentage when the baseline is zero or incomplete.

## Data (`data/stats.json`, written by `generator/fetch.py`)

The data is aggregate only, and it is already public on the profile: the contribution
calendar includes private counts.

- **Totals:** 313 contributions in the last year, 309 of them private. 42 active days since
  joining on 2026-05-06.
- **Highlights:** the peak day was 47 on 2026-09-28. The longest streak is 5 days, Aug 17–21.
  Monday is the busiest weekday.
- **Monthly totals:** May 2, Jun 28, Jul 22, Aug 82, Sep 59, Oct 120.

Every number must come from `stats.json`. Nothing is hard-coded, because CI re-renders daily.
Lead with total contributions, classified missions, active days, peak day, momentum and the
busiest weekday. Don't lead with the near-zero public PR or commit counts.

## Code conventions

- **Python:** 3.9-compatible and stdlib only (`from __future__ import annotations`). CI uses 3.12.
- **Renderers:** `render_x(stats: dict, mode: str) -> str`, called by `generator/build.py`.
- **Static art:** regenerate it with `python3 generator/art_{banner,caption,ribbons,footer}.py`.
- **Preview:**
  1. Run `python3 scripts/preview.py` (GitHub Markdown API through `gh`; `--offline` otherwise).
  2. Copy `dist/battlefield-*.svg` and `data/stats.json` into `site/` (CI does the same).
  3. Serve the repo root (on this Mac, serve a copy outside `~/Documents`; see HANDOVER.md).
  4. Open `/.preview/index.html`, which has a Light/Dark switch. The War Room is at `/site/`.
- **War Room UI:** Front is the default preset; touch exploration is opt-in ("Explore in 3D");
  on phones no text is below 12 px and every primary control is at least 44 px tall;
  reduced motion disables continuous animation and replaces Play with "Step one week".
- **Local-only guardrail:** do not create a repository, commit, push, enable Pages, or
  publish without separate approval. Existing deployment configuration is not permission
  to deploy.
- **Verification:** run `python3 -m unittest discover -s tests -p 'test_*.py'` and
  `python3 scripts/check.py` after building. Browser model assertions are exported by
  `tests/model.test.js`. Browser checks use optional isolated Playwright tooling, not a
  Node application dependency.
