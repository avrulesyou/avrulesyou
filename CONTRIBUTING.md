# Contributing

This repository is the public profile and contribution explorer for
[avrulesyou](https://github.com/avrulesyou). Contributions are welcome when they
improve accessibility, reliability, documentation, or the visual experience without
exposing private repository data.

## Local development

The contribution explorer is a static site in `site/`. Its data-driven SVGs are
generated from `data/stats.json`:

```bash
python generator/fetch.py
python generator/build.py
cp data/stats.json site/stats.json
cp dist/battlefield-light.svg dist/battlefield-dark.svg site/
python -m http.server 8000 --directory site
```

Open `http://localhost:8000` to inspect the page. The fetcher uses `gh` locally when
`GITHUB_TOKEN` is not set; it only requests aggregate contribution information for
the configured `PROFILE_LOGIN` (default: `avrulesyou`).

## Checks

Run the Python tests and artifact checks before opening a pull request:

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/check.py
```

Keep generated snapshots and SVG output out of commits unless a change explicitly
requires checked-in artifacts. GitHub Actions regenerates the profile images and
deploys the Pages site on pushes to `master` and on its scheduled run.

## Pull requests

Please describe the user-facing change, include screenshots for visual changes, and
call out any accessibility or reduced-motion implications. Avoid adding repository
names, private project details, credentials, or telemetry that does not belong in a
public profile.
