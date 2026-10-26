"""Render README.md through GitHub's markdown API into .preview/index.html.

Remote output-branch URLs and absolute asset URLs are rewritten to local files
so the page shows what the profile will look like before anything is pushed.
Usage: python3 scripts/preview.py && python3 -m http.server -d . 8765
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".preview" / "index.html"
RAW_OUTPUT = "https://raw.githubusercontent.com/avrulesyou/avrulesyou/output/"
PAGES = "https://avrulesyou.github.io/avrulesyou/"

HTML_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "dd", "del",
    "details", "div", "dl", "dt", "em", "figcaption", "figure", "h1", "h2",
    "h3", "h4", "h5", "h6", "hr", "i", "img", "kbd", "li", "mark", "ol",
    "p", "picture", "pre", "s", "samp", "small", "source", "span", "strong",
    "sub", "summary", "sup", "table", "tbody", "td", "th", "thead", "tr",
    "tt", "ul", "var", "wbr",
}
HTML_TOKEN = re.compile(r"<!--[\s\S]*?-->|</?([A-Za-z][\w-]*)\b(?:[^>\"']|\"[^\"]*\"|'[^']*')*>")
LINK = re.compile(r'(!?)\[([^\]\n]*)\]\(\s*(<[^>\n]+>|[^\s)]+)(?:\s+["\']([^"\']*)["\'])?\s*\)')
ACTIVE_HTML = re.compile(r"<(script|style)\b[^>]*>[\s\S]*?</\1\s*>", re.I)


def safe_url(value: str) -> str:
    scheme = urlsplit(html.unescape(value).strip()).scheme.lower()
    return value if scheme in {"", "http", "https", "mailto"} else "#"


def safe_tag(match: re.Match[str]) -> str:
    raw = match[0]
    if raw.startswith("<!--"):
        return raw
    if match[1].lower() not in HTML_TAGS:
        return html.escape(raw)
    raw = re.sub(r"\s+on[\w-]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", raw, flags=re.I)
    raw = re.sub(
        r"(\b(?:href|src|srcset)\s*=\s*)(?:([\"'])(.*?)\2|([^\s>]+))",
        lambda attr: attr[0] if safe_url(attr[3] if attr[2] else attr[4]) != "#" else attr[1] + '"#"',
        raw, flags=re.I | re.S,
    )
    raw = re.sub(r"\s+style\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", "", raw, flags=re.I)
    return raw


class NativeHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.output: list[str] = []
        self.ignored: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        if tag in {"script", "style"}:
            self.ignored.append(tag)
        if not self.ignored:
            raw = self.get_starttag_text()
            match = HTML_TOKEN.fullmatch(raw)
            self.output.append(safe_tag(match) if match else html.escape(raw))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        if not self.ignored and tag not in {"script", "style"}:
            raw = self.get_starttag_text()
            match = HTML_TOKEN.fullmatch(raw)
            self.output.append(safe_tag(match) if match else html.escape(raw))

    def handle_endtag(self, tag: str) -> None:
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
        else:
            self.output.append(f"</{tag}>" if tag in HTML_TAGS else html.escape(f"</{tag}>"))

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.output.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.ignored:
            self.output.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.ignored:
            self.output.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        if not self.ignored:
            self.output.append(f"<!--{data}-->")


def native_html(text: str) -> str:
    parser = NativeHTML()
    parser.feed(text)
    parser.close()
    return "".join(parser.output)


def inline_markdown(text: str) -> str:
    tokens: list[str] = []

    def formatting(value: str) -> str:
        value = html.escape(value)
        value = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda match: "<strong>" + (match[1] or match[2]) + "</strong>", value)
        value = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!\w)_([^_\n]+)_(?!\w)", lambda match: "<em>" + (match[1] or match[2]) + "</em>", value)
        value = re.sub(r"~~(.+?)~~", r"<del>\1</del>", value)
        return re.sub(r"&amp;((?:#[xX][0-9a-fA-F]+|#\d+|[A-Za-z][A-Za-z0-9]+);)", r"&\1", value)

    def store(value: str) -> str:
        tokens.append(value)
        return f"\x00{len(tokens) - 1}\x00"

    text = re.sub(r"(`+)(.+?)\1", lambda match: store("<code>" + html.escape(match[2]) + "</code>"), text)
    text = re.sub(r"<!--[\s\S]*?-->", lambda match: store(match[0]), text)
    text = ACTIVE_HTML.sub("", text)
    text = HTML_TOKEN.sub(lambda match: store(safe_tag(match)), text)

    def link(match: re.Match[str]) -> str:
        url = html.escape(safe_url(html.unescape(match[3].strip("<>"))), quote=True)
        title = f' title="{html.escape(html.unescape(match[4]), quote=True)}"' if match[4] else ""
        if match[1]:
            return store(f'<img src="{url}" alt="{html.escape(html.unescape(match[2]), quote=True)}"{title}>')
        return store(f'<a href="{url}"{title}>{formatting(match[2])}</a>')

    text = LINK.sub(link, text)
    text = formatting(text)
    for _ in tokens:
        text = re.sub(r"\x00(\d+)\x00", lambda match: tokens[int(match[1])], text)
    return text


def heading_slug(rendered: str, seen: dict[str, int]) -> str:
    """GitHub-style anchor: lowercase, punctuation dropped, spaces to hyphens, repeats get -1, -2."""
    text = html.unescape(re.sub(r"<[^>]*>", "", rendered)).strip().lower()
    slug = re.sub(r"[^\w\- ]", "", text).replace(" ", "-")
    count = seen.get(slug, 0)
    seen[slug] = count + 1
    return slug if not count else f"{slug}-{count}"


def offline_markdown(markdown: str, seen: dict[str, int] | None = None) -> str:
    seen = {} if seen is None else seen
    lines = markdown.replace("\r\n", "\n").splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    index = 0

    def flush() -> None:
        if paragraph:
            output.append("<p>" + inline_markdown("\n".join(paragraph)) + "</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            flush()
            index += 1
            continue
        fence = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence:
            flush()
            code = []
            index += 1
            while index < len(lines) and not re.match(r"^\s*" + re.escape(fence[1][0]) + "{" + str(len(fence[1])) + r",}\s*$", lines[index]):
                code.append(lines[index])
                index += 1
            output.append("<pre><code>" + html.escape("\n".join(code) + "\n") + "</code></pre>")
        elif re.match(r"^\s*<(script|style)\b", line, re.I):
            flush()
            tag = re.match(r"^\s*<(script|style)\b", line, re.I)[1]
            while not re.search(r"</" + tag + r"\s*>", lines[index], re.I) and index + 1 < len(lines):
                index += 1
        elif re.match(r"^\s*<!--", line):
            flush()
            comment = [line]
            while "-->" not in comment[-1] and index + 1 < len(lines):
                index += 1
                comment.append(lines[index])
            output.append(native_html("\n".join(comment)))
        elif re.match(r"^\s*</?(?:p|div|picture|table|thead|tbody|tr|td|th|details|summary|br|hr|figure|figcaption|ul|ol|li|h[1-6])\b", line, re.I):
            flush()
            raw = [line]
            while index + 1 < len(lines) and lines[index + 1].strip():
                index += 1
                raw.append(lines[index])
            output.append(native_html("\n".join(raw)))
        elif re.match(r"^\s{0,3}>", line):
            flush()
            quote = []
            while index < len(lines) and re.match(r"^\s{0,3}>", lines[index]):
                quote.append(re.sub(r"^\s{0,3}> ?", "", lines[index]))
                index += 1
            output.append("<blockquote>" + offline_markdown("\n".join(quote), seen) + "</blockquote>")
            continue
        elif re.match(r"^\s{0,3}(?:[-+*]|\d+[.)])\s+", line):
            flush()
            ordered = bool(re.match(r"^\s*\d+", line))
            tag = "ol" if ordered else "ul"
            items = []
            while index < len(lines):
                item = re.match(r"^\s{0,3}([-+*]|\d+[.)])\s+(.*)$", lines[index])
                if not item or bool(item[1][0].isdigit()) != ordered:
                    break
                items.append("<li>" + inline_markdown(item[2]) + "</li>")
                index += 1
            output.append(f"<{tag}>" + "\n".join(items) + f"</{tag}>")
            continue
        elif re.match(r"^\s{0,3}#{1,6}\s", line):
            flush()
            heading = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
            body = inline_markdown(heading[2])
            output.append(f'<h{len(heading[1])} id="{heading_slug(body, seen)}">' + body + f"</h{len(heading[1])}>")
        elif re.match(r"^\s{0,3}(?:---+|\*\*\*+|___+)\s*$", line):
            flush()
            output.append("<hr>")
        elif index + 1 < len(lines) and "|" in line and re.match(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]):
            flush()
            rows = ["<tr>" + "".join("<th>" + inline_markdown(cell.strip()) + "</th>" for cell in line.strip().strip("|").split("|")) + "</tr>"]
            index += 2
            body = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                body.append("<tr>" + "".join("<td>" + inline_markdown(cell.strip()) + "</td>" for cell in lines[index].strip().strip("|").split("|")) + "</tr>")
                index += 1
            output.append("<table><thead>" + "".join(rows) + "</thead><tbody>" + "".join(body) + "</tbody></table>")
            continue
        else:
            paragraph.append(line)
        index += 1
    flush()
    return "\n".join(output)


def rewrite_urls(rendered: str) -> str:
    rendered = rendered.replace(RAW_OUTPUT, "../dist/").replace(PAGES, "../site/")
    # GitHub's API prefixes heading ids; the page's own #fragment links omit the prefix.
    rendered = re.sub(r'(\bid\s*=\s*["\'])user-content-', r"\1", rendered, flags=re.I)
    # The Markdown API's "markdown" mode emits bare headings; GitHub adds the ids on the page.
    seen: dict[str, int] = {}
    rendered = re.sub(
        r"<h([1-6])>(.*?)</h\1>",
        lambda match: f'<h{match[1]} id="{heading_slug(match[2], seen)}">{match[2]}</h{match[1]}>',
        rendered, flags=re.S,
    )
    return re.sub(
        r"(\b(?:src|href|srcset|poster)\s*=\s*)([\"'])(.*?)\2",
        lambda match: match[1] + match[2] + re.sub(r"(^|,\s*)(?:\./|/)?assets/", r"\1../assets/", match[3]) + match[2],
        rendered, flags=re.I | re.S,
    )


def preview_document(rendered: str) -> str:
    return f"""<!doctype html>
<html data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Profile preview</title>
<link id="md-css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown-light.min.css">
<style>
  body {{ margin:0; background:#fff; color:#1f2328; font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
  html[data-theme="dark"] body {{ background:#0d1117; }}
  html[data-theme="dark"] .markdown-body {{ color:#e6edf3; }}
  .markdown-body {{ box-sizing:border-box; max-width:896px; margin:0 auto; padding:32px 28px; }}
  .markdown-body img {{ max-width:100%; box-sizing:content-box; }}
  .markdown-body a {{ color:#0969da; text-decoration:none; }}
  html[data-theme="dark"] .markdown-body a {{ color:#4493f8; }}
  .markdown-body p, .markdown-body blockquote, .markdown-body ul, .markdown-body ol, .markdown-body table {{ margin-top:0; margin-bottom:16px; }}
  .markdown-body table {{ border-spacing:0; border-collapse:collapse; display:block; width:max-content; max-width:100%; overflow:auto; }}
  .markdown-body td, .markdown-body th {{ padding:6px 13px; border:1px solid #d1d9e0; }}
  html[data-theme="dark"] .markdown-body td, html[data-theme="dark"] .markdown-body th {{ border-color:#3d444d; }}
  .markdown-body blockquote {{ padding:0 1em; color:#59636e; border-left:.25em solid #d1d9e0; }}
  .markdown-body summary {{ cursor:pointer; }}
  @media (max-width: 767px) {{ .markdown-body {{ padding:56px 16px 16px; }} }}
  .theme-switch {{ position:fixed; top:12px; right:12px; z-index:10; display:flex; gap:2px; padding:3px;
    border-radius:999px; background:#f6f8fa; border:1px solid #d0d7de; font:600 13px -apple-system,Segoe UI,sans-serif; }}
  html[data-theme="dark"] .theme-switch {{ background:#161b22; border-color:#30363d; }}
  .theme-switch button {{ border:0; border-radius:999px; padding:6px 12px; cursor:pointer; background:transparent; color:#57606a; font:inherit; }}
  html[data-theme="dark"] .theme-switch button {{ color:#8b949e; }}
  .theme-switch button[aria-pressed="true"] {{ background:#F6B800; color:#1B1B1F; }}
</style></head>
<body>
<div class="theme-switch" role="group" aria-label="Preview theme">
  <button type="button" data-t="light" aria-pressed="true">Light</button>
  <button type="button" data-t="dark" aria-pressed="false">Dark</button>
</div>
<article class="markdown-body">{rendered}</article>
<script>
  // GitHub picks each <picture> variant from the viewer's theme. Here a switch
  // decides instead, so both themes can be checked on one machine.
  const pics = [...document.querySelectorAll('picture')].map(p => {{
    const src = p.querySelector('source[media*="dark"]');
    const img = p.querySelector('img');
    if (!img) return null;
    const v = {{ img, light: img.getAttribute('src'), dark: src ? src.getAttribute('srcset') : img.getAttribute('src') }};
    p.querySelectorAll('source').forEach(s => s.remove());
    return v;
  }}).filter(Boolean);
  function apply(t) {{
    document.documentElement.dataset.theme = t;
    document.getElementById('md-css').href =
      'https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown-' + t + '.min.css';
    pics.forEach(p => {{ p.img.src = p[t]; }});
    document.querySelectorAll('.theme-switch button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === t)));
    try {{ localStorage.setItem('preview-theme', t); }} catch (e) {{}}
  }}
  document.querySelectorAll('.theme-switch button').forEach(b => b.addEventListener('click', () => apply(b.dataset.t)));
  let saved = null;
  try {{ saved = localStorage.getItem('preview-theme'); }} catch (e) {{}}
  apply(saved === 'dark' ? 'dark' : 'light');
</script>
</body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a local profile preview; --offline uses a limited stdlib Markdown subset, not full GitHub GFM.")
    parser.add_argument("--offline", action="store_true", help="Do not call gh or use the Markdown API")
    parser.add_argument("--readme", type=Path, default=ROOT / "README.md")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    markdown = args.readme.read_text(encoding="utf-8")
    rendered = ""
    source = "offline subset"
    if not args.offline:
        try:
            rendered = subprocess.run(
                ["gh", "api", "markdown", "-f", f"text={markdown}", "-f", "mode=gfm"],
                check=True, capture_output=True, text=True, timeout=45,
            ).stdout
            source = "GitHub Markdown API"
        except (OSError, subprocess.SubprocessError):
            print("GitHub Markdown API unavailable; using the offline subset (no credentials requested).", file=sys.stderr)
    if not rendered:
        rendered = offline_markdown(markdown)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(preview_document(rewrite_urls(rendered)), encoding="utf-8")
    print(f"wrote {args.output} ({source})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
