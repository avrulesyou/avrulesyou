from __future__ import annotations

import argparse
import ast
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from preview import RAW_OUTPUT, offline_markdown

ROOT = Path(__file__).resolve().parent.parent
MAX_SVG_BYTES = 250000
# The crew name is banned; the singular "straw hat" is an allowed prop (DESIGN.md).
BANNED = re.compile(r"(?<!\w)(?:Straw\s+Hats|Straw\s+Hat\s+(?:Pirates|crew)|Akatsuki|versus|vs\.?|threats?|dead\s+or\s+alive|Agentic)(?!\w)", re.I)
BANNED_POSTER = re.compile(r"(?<!\w)WANTED(?!\w)")
JAPANESE = re.compile(r"[\u1100-\u11ff\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff\uff66-\uff9f]")
ACTIVE_CONTENT = re.compile(r"<\s*(?:script|foreignobject)\b|<!entity\b|javascript\s*:", re.I)
REDUCED_MOTION = re.compile(r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)", re.I)
STATS_KEYS = {
    "login", "name", "bio", "location", "joined", "followers", "public_repos",
    "generated_at", "range", "totals", "streak", "active_days", "days_since_join",
    "active_rate_since_join", "best_day", "weekday_totals", "busiest_weekday",
    "monthly", "weeks", "avatar",
}
TOTAL_KEYS = {"contributions", "commits", "pull_requests", "reviews", "issues", "repos_created", "private", "public"}
DAY_KEYS = {"date", "count", "level", "weekday"}
PRIVATE_KEYS = {"repository", "repositories", "repo_name", "organization", "org_name", "code"}
CSS_URL = re.compile(r"url\s*\(\s*(['\"]?)(.*?)\1\s*\)", re.I | re.S)
BLOCK_TAGS = {"p", "div", "br", "li", "tr", "td", "th", "section", "article", "main", "header", "footer", "aside", "nav", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "ul", "ol", "dl", "dt", "dd", "summary", "details", "table", "title"}


def local_name(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def add_once(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def visible_errors(text: str) -> list[str]:
    errors = []
    text = re.sub(r"(?:https?://|//)[^\s<>\"']+", "", text)
    text = re.sub(r"(?<!\w)(?:[\w.-]+/)*[\w-]+\.(?:svg|png|jpe?g|webp|gif|m?js|json|py|md|html|css)(?!\w)", "", text, flags=re.I)
    if BANNED.search(text) or BANNED_POSTER.search(text):
        errors.append("visible text contains a banned whole phrase")
    if JAPANESE.search(text):
        errors.append("visible text contains kana/CJK characters")
    return errors


def allowed_reference(value: str) -> bool:
    value = value.strip()
    return bool(re.fullmatch(r"#[^\s#]+", value) or re.fullmatch(
        r"data:image/(?:png|jpeg);base64,[A-Za-z0-9+/=\s]+", value, re.I
    ))


def css_unescape(value: str) -> str:
    value = re.sub(r"/\*.*?\*/", "", value, flags=re.S)
    return re.sub(
        r"\\([0-9a-fA-F]{1,6})\s?|\\([^\r\n])",
        lambda match: chr(int(match[1], 16)) if match[1] and int(match[1], 16) <= 0x10FFFF else (match[2] or ""),
        value,
    )


def allowed_css_reference(value: str) -> bool:
    return allowed_reference(value)


def check_svg(path: Path) -> list[str]:
    return check_svg_bytes(path.read_bytes())


def check_svg_bytes(payload: bytes) -> list[str]:
    errors = []
    if len(payload) > MAX_SVG_BYTES:
        errors.append(f"size {len(payload)} bytes exceeds {MAX_SVG_BYTES}")
    try:
        root = ET.fromstring(payload)
    except (ET.ParseError, ValueError, LookupError):
        return errors + ["invalid SVG XML"]
    source = html.unescape(payload.decode("utf-8", "replace"))
    if ACTIVE_CONTENT.search(source):
        errors.append("script, foreignObject, entity declarations and javascript: are forbidden")
    if JAPANESE.search(source):
        errors.append("kana/CJK characters are forbidden anywhere in the SVG")
    if local_name(root.tag) != "svg":
        errors.append("root element is not svg")
    if root.get("role") != "img":
        errors.append("root role must be img")
    children = list(root)
    if not children or local_name(children[0].tag) != "title" or not "".join(children[0].itertext()).strip():
        errors.append("first root element must be a nonempty title")
    if not any(local_name(node.tag) == "desc" and "".join(node.itertext()).strip() for node in root.iter()):
        errors.append("nonempty desc is required")
    css = "\n".join("".join(node.itertext()) for node in root.iter() if local_name(node.tag) == "style")
    if not REDUCED_MOTION.search(css_unescape(css)):
        errors.append("reduced-motion media rule is required")
    ids = set()
    external_href = False
    external_css = False
    for node in root.iter():
        if local_name(node.tag).lower() in {"script", "foreignobject"}:
            add_once(errors, f"<{local_name(node.tag)}> element is forbidden")
        for key, value in node.attrib.items():
            if local_name(key).lower().startswith("on"):
                add_once(errors, "event-handler attribute is forbidden")
            if local_name(key) == "id":
                if value in ids:
                    add_once(errors, "duplicate SVG ids")
                ids.add(value)
            if local_name(key) in {"href", "src"} and not allowed_reference(value):
                external_href = True
            normalized = css_unescape(value)
            if any(not allowed_css_reference(match[2]) for match in CSS_URL.finditer(normalized)):
                external_css = True
            if re.search(r"@import\b", normalized, re.I):
                external_css = True
        normalized = css_unescape("".join(node.itertext())) if local_name(node.tag) == "style" else ""
        if re.search(r"@import\b", normalized, re.I) or any(
            not allowed_css_reference(match[2]) for match in CSS_URL.finditer(normalized)
        ):
            external_css = True
    if external_href:
        errors.append("href must be a local fragment or embedded PNG/JPEG")
    if external_css:
        errors.append("CSS import or nonlocal url is forbidden")
    visible = []

    def collect(node: ET.Element, hidden: bool = False) -> None:
        tag = local_name(node.tag)
        hidden = hidden or tag in {"style", "script", "defs", "metadata"}
        if tag in {"title", "desc"} or (not hidden and tag in {"text", "tspan", "textPath"}):
            visible.append("".join(node.itertext()))
            return
        for child in node:
            collect(child, hidden)

    collect(root)
    errors.extend(visible_errors(" ".join(visible)))
    return errors


class VisibleHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.references: list[str] = []
        self.ignored: list[str] = []
        self.ids: set[str] = set()
        self.pictures: list[dict] = []
        self.picture: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        if tag in {"script", "style"}:
            self.ignored.append(tag)
        if self.ignored:
            return
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "picture":
            self.picture = {"sources": [], "img": None}
            self.pictures.append(self.picture)
        elif tag == "source" and self.picture is not None:
            self.picture["sources"].append(values)
        elif tag == "img" and self.picture is not None and self.picture["img"] is None:
            self.picture["img"] = values
        for key, value in attrs:
            if not value:
                continue
            if key in {"alt", "aria-label"}:
                self.text.extend(("\n", value, "\n"))
            if key in {"src", "href", "poster"}:
                self.references.append(value)
            if key == "srcset":
                self.references.extend(srcset_urls(value))
        if tag in BLOCK_TAGS:
            self.text.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "picture":
            self.picture = None
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
        elif tag in BLOCK_TAGS:
            self.text.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.text.append(data)


def srcset_urls(value: str) -> list[str]:
    return re.findall(r"(?:^|,\s*)([^\s,]+)(?:\s+[^,]+)?", value) if not value.startswith("data:") else [value.split()[0]]


def html_content(text: str) -> VisibleHTML:
    parser = VisibleHTML()
    parser.feed(text)
    parser.close()
    return parser


def build_outputs(root: Path) -> set[str]:
    path = root / "generator" / "build.py"
    if not path.exists():
        return set()
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "RENDERERS" for target in node.targets):
            if isinstance(node.value, ast.Dict):
                return {
                    f"{key.value}-{mode}.svg"
                    for key in node.value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    for mode in ("light", "dark")
                }
    return set()


def readme_reference_errors(references: list[str], root: Path) -> list[str]:
    errors = []
    outputs = build_outputs(root)
    for reference in sorted(set(references)):
        if reference.startswith(RAW_OUTPUT):
            relative = unquote(urlsplit(reference[len(RAW_OUTPUT):]).path)
            if relative not in outputs:
                errors.append("remote output reference does not name a known build output")
            elif not (root / "dist" / relative).is_file():
                errors.append(f"missing build output: dist/{relative}")
            continue
        parts = urlsplit(reference)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        path = (root / unquote(parts.path).lstrip("/")).resolve()
        try:
            relative = path.relative_to(root.resolve())
        except ValueError:
            errors.append("local reference escapes repository")
            continue
        if not path.exists():
            errors.append(f"missing local reference: {relative}")
    return errors


def picture_errors(pictures: list[dict]) -> list[str]:
    errors = []
    for number, picture in enumerate(pictures, 1):
        dark = [
            source for source in picture["sources"]
            if re.search(r"prefers-color-scheme\s*:\s*dark", source.get("media", ""), re.I) and source.get("srcset", "").strip()
        ]
        image = picture["img"]
        if not dark:
            errors.append(f"picture {number} lacks a prefers-color-scheme: dark source with srcset")
        if not image or not image.get("src", "").strip():
            errors.append(f"picture {number} lacks a light img with src")
            continue
        if not image.get("alt", "").strip():
            errors.append(f"picture {number} img needs nonempty alt text")
        light_name = urlsplit(image["src"]).path.rsplit("/", 1)[-1]
        if "dark" in light_name.lower():
            errors.append(f"picture {number} light img names a dark file: {light_name}")
        for source in dark:
            dark_name = urlsplit(source["srcset"].split()[0]).path.rsplit("/", 1)[-1]
            if "light" in dark_name.lower() or dark_name == light_name:
                errors.append(f"picture {number} dark source does not name a distinct dark file: {dark_name}")
    return errors


def fragment_errors(references: list[str], known: set[str]) -> list[str]:
    return [
        f"fragment link does not resolve to a heading or id: {reference}"
        for reference in sorted(set(references))
        if reference.startswith("#") and len(reference) > 1 and unquote(reference[1:]) not in known
    ]


SITE_STAGED = re.compile(r"(?:\./)?(?:battlefield-(?:light|dark)\.svg|stats\.json)$")
SITE_ESCAPE = re.compile(r"\.\./(?:dist|assets|data)/")


def site_reference_errors(path: Path, root: Path, references: list[str], text: str) -> list[str]:
    errors = []
    site = (root / "site").resolve()
    if SITE_ESCAPE.search(text):
        errors.append("references ../dist, ../assets or ../data, which Pages does not publish; stage files inside site/")
    for reference in sorted(set(references)):
        parts = urlsplit(reference)
        if parts.scheme or parts.netloc or not parts.path:
            continue
        target = (path.parent / unquote(parts.path)).resolve()
        try:
            target.relative_to(site)
        except ValueError:
            continue
        if not target.exists() and not SITE_STAGED.fullmatch(parts.path):
            errors.append(f"missing local reference: {target.relative_to(root.resolve())}")
    return errors


def check_stats(path: Path) -> list[str]:
    try:
        stats = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return ["invalid stats JSON"]
    if not isinstance(stats, dict):
        return ["stats root must be an object"]
    errors = []
    if set(stats) - STATS_KEYS:
        errors.append("stats has keys outside the root allowlist")
    if "totals" in stats:
        if not isinstance(stats["totals"], dict) or set(stats["totals"]) - TOTAL_KEYS:
            errors.append("totals must be an object with only permitted keys")
    if "weeks" in stats:
        weeks = stats["weeks"]
        if not isinstance(weeks, list) or any(not isinstance(week, list) for week in weeks):
            errors.append("weeks must be an array of day arrays")
        elif any(not isinstance(day, dict) or set(day) - DAY_KEYS for week in weeks for day in week):
            errors.append("each day must be an object with only permitted keys")

    def forbidden(value: object) -> bool:
        if isinstance(value, dict):
            return any(str(key).lower() in PRIVATE_KEYS or forbidden(child) for key, child in value.items())
        if isinstance(value, list):
            return any(forbidden(child) for child in value)
        return False

    if forbidden(stats):
        errors.append("stats contains a forbidden nested key")
    return errors


def run(root: Path) -> int:
    results = []
    svg_paths = sorted(root.glob("assets/*.svg")) + sorted(root.glob("dist/*.svg"))
    if (root / "site" / "social.svg").exists():
        svg_paths.append(root / "site" / "social.svg")
    for path in svg_paths:
        try:
            results.append((path.relative_to(root), check_svg(path)))
        except OSError:
            results.append((path.relative_to(root), ["unable to read SVG"]))
    readme = root / "README.md"
    try:
        markdown = readme.read_text(encoding="utf-8")
        content = html_content(offline_markdown(markdown))
        results.append((Path("README.md"), (
            visible_errors("".join(content.text)) + readme_reference_errors(content.references, root)
            + picture_errors(content.pictures) + fragment_errors(content.references, content.ids)
        )))
    except (OSError, UnicodeError, SyntaxError, ValueError):
        results.append((Path("README.md"), ["unable to inspect README or build output manifest"]))
    html_paths = sorted((root / "site").rglob("*.html"))
    if (root / ".preview" / "index.html").exists():
        html_paths.append(root / ".preview" / "index.html")
    for path in html_paths:
        try:
            text = path.read_text(encoding="utf-8")
            content = html_content(text)
            errors = visible_errors("".join(content.text))
            if (root / "site") in path.parents:
                errors += site_reference_errors(path, root, content.references, text)
            results.append((path.relative_to(root), errors))
        except (OSError, UnicodeError):
            results.append((path.relative_to(root), ["unable to read HTML"]))
    for path in sorted((root / "site").rglob("*.js")) + sorted((root / "site").rglob("*.css")):
        try:
            results.append((path.relative_to(root), site_reference_errors(path, root, [], path.read_text(encoding="utf-8"))))
        except (OSError, UnicodeError):
            results.append((path.relative_to(root), ["unable to read site asset"]))
    stats = root / "data" / "stats.json"
    if stats.exists():
        try:
            results.append((Path("data/stats.json"), check_stats(stats)))
        except OSError:
            results.append((Path("data/stats.json"), ["unable to read stats JSON"]))
    else:
        print("SKIP data/stats.json: optional snapshot absent")
    for path, errors in results:
        print(f"{'FAIL' if errors else 'PASS'} {path}")
        for error in errors:
            print(f"  {error}")
    failures = sum(bool(errors) for _, errors in results)
    print(f"Checked {len(results)} files ({len(svg_paths)} SVG): {len(results) - failures} passed, {failures} failed")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SVG structure, visible wording, local references and aggregate snapshot privacy without network access.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    return run(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
