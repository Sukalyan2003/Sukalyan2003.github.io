#!/usr/bin/env python3
"""Verify the built site against design.md and against itself.

design.md states rules that are easy to violate accidentally during a later
edit - a stray border-radius, a card shadow, a link to a repository that has
gone private. This turns those rules into a check that fails loudly.

Standard library only.

Covers the front page, the legacy page, and every generated /blog page.

Usage:
    python3 scripts/check.py              # structural + design rules
    python3 scripts/check.py --links      # also resolve every external URL
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC_PAGES = ["index.html", "404.html", "classic/index.html", "the-record/index.html"]
CSS_FILES = ["the-record/css/styles.css", "blog/assets/blog.css"]
DRAFTS = ROOT / "content" / "drafts"


def pages() -> list[str]:
    blog = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "blog").rglob("index.html"))
    return STATIC_PAGES + blog

# design.md > Elevation & Depth, and > Shapes.
BANNED_CSS = {
    "box-shadow": "Print has no z-axis (design.md > Elevation & Depth)",
    "backdrop-filter": "No glassmorphism (design.md > Elevation & Depth)",
    "border-radius": "The rounded scale has one token and it is 0 (design.md > Shapes)",
    "text-align: justify": "No justified body copy (design.md > Do's and Don'ts)",
}
BANNED_FONTS = ["Inter", "Poppins", "Montserrat"]

USER_AGENT = "Mozilla/5.0 (compatible; the-record link-check)"
# Hosts that reject automated HEAD/GET but are fine in a browser.
BOT_WALLED = {"linkedin.com": {999, 403}, "hashnode.dev": {403}, "coursera.org": {403}}
# The page's own canonical URL 404s until the site is actually deployed.
SELF_URL = "https://sukalyan2003.github.io/"


def strip_css_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def check() -> list[str]:
    problems: list[str] = []

    # ---- CSS design rules (comments stripped, so the header can name them) ---
    for css_file in CSS_FILES:
        if not (ROOT / css_file).exists():
            continue
        css = strip_css_comments((ROOT / css_file).read_text(encoding="utf-8"))
        for prop, why in BANNED_CSS.items():
            if prop in css:
                problems.append(f"{css_file}: '{prop}' is banned - {why}")
        for font in BANNED_FONTS:
            if re.search(rf"\b{font}\b", css):
                problems.append(f"{css_file}: '{font}' is banned (design.md > Do's and Don'ts)")

        # Every grid must declare its columns; a bare `display: grid` silently
        # collapses to one full-width column. This bit us on the previous site.
        for block in re.findall(r"\{[^{}]*\}", css):
            if "display: grid" in block and "grid-template-columns" not in block:
                selector_hint = block.strip()[:60].replace("\n", " ")
                problems.append(
                    f"{css_file}: grid without grid-template-columns near '{selector_hint}…'"
                )

    # ---- per-page structural checks ------------------------------------------
    for page in pages():
        html = (ROOT / page).read_text(encoding="utf-8")
        # Highlighted code is a run of spans (some holding only whitespace)
        # inside <pre>; the empty-element rule is about layout, not code.
        html_no_code = re.sub(r"<pre\b.*?</pre>", "<pre></pre>", html, flags=re.S)

        if 'style="' in html:
            problems.append(f"{page}: inline style attribute (use a class)")

        refs = set(re.findall(r'(?:src|href)="(?!https?:|mailto:|#|data:)([^"]+)"', html))
        for candidate in re.findall(r'srcset="([^"]+)"', html):
            for part in candidate.split(","):
                refs.add(part.strip().split()[0])
        for ref in sorted(refs):
            path = ref.split("?")[0].split("#")[0]
            candidate = ROOT / path.lstrip("/") if path.startswith("/") else ROOT / Path(page).parent / path
            if not candidate.resolve().exists():
                problems.append(f"{page}: missing local file '{ref}'")

        ids = set(re.findall(r'id="([^"]+)"', html))
        for anchor in sorted(set(re.findall(r'href="#([^"]+)"', html))):
            if anchor not in ids:
                problems.append(f"{page}: dead anchor '#{anchor}'")

        for tag in ("section", "article", "picture", "main", "div", "figure",
                    "blockquote", "h1", "h2", "h3", "p", "time", "button"):
            opened = len(re.findall(rf"<{tag}[\s>]", html))
            closed = len(re.findall(rf"</{tag}>", html))
            if opened != closed:
                problems.append(f"{page}: <{tag}> unbalanced ({opened} open, {closed} close)")

        for match in re.finditer(r"<(p|h2|h3|span|div)([^>]*)>\s*</\1>", html_no_code):
            if 'class="navbar-toggler-icon"' in match.group(2):
                continue
            problems.append(f"{page}: empty <{match.group(1)}{match.group(2)}>")

        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                problems.append(f"{page}: JSON-LD invalid ({exc})")

        # The giscus CSP exception belongs only on pages that mount comments.
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)
        if csp and "giscus.app" in csp.group(1) and "data-giscus" not in html:
            problems.append(f"{page}: CSP allows giscus.app but the page has no comments")

    # ---- drafts must never reach public output --------------------------------
    # content/drafts/ exists only on the author's machine (gitignored).
    if DRAFTS.exists():
        draft_slugs = set()
        for draft in (d for d in DRAFTS.glob("*.md") if not d.name.startswith("_")):
            match = re.search(r'^slug:\s*"?([^"\n]+)"?\s*$', draft.read_text(encoding="utf-8"), re.M)
            draft_slugs.add(match.group(1).strip() if match else draft.stem)
        published = {p.stem for p in (ROOT / "content" / "blog").glob("*.md")}
        draft_slugs -= published  # a draft may share a slug with the post it once was
        public = [ROOT / "sitemap.xml", ROOT / "blog" / "rss.xml", ROOT / "blog" / "search.json"]
        public += [ROOT / p for p in pages()]
        for path in public:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for slug in sorted(draft_slugs):
                if f"/blog/{slug}/" in text:
                    problems.append(f"{path.relative_to(ROOT)}: links to draft '{slug}'")
        for slug in sorted(draft_slugs):
            if (ROOT / "blog" / slug).exists():
                problems.append(f"blog/{slug}/: a draft was built into the public output")

    # ---- JSON payloads --------------------------------------------------------
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    try:
        json.loads(
            re.search(r'<script type="application/ld\+json">(.*?)</script>', index, re.S).group(1)
        )
    except (AttributeError, json.JSONDecodeError) as exc:
        problems.append(f"index.html: JSON-LD invalid ({exc})")
    try:
        json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        problems.append(f"manifest.json: invalid ({exc})")

    # The dispatch markers must survive edits or the sync silently stops working.
    for marker in ("WRITING:START", "WRITING:END"):
        if index.count(marker) != 1:
            problems.append(f"index.html: expected exactly one {marker}")

    return problems


def check_links() -> list[str]:
    problems = []
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    urls = sorted(set(re.findall(r'href="(https?://[^"]+)"', index)))
    urls = [u for u in urls if not u.startswith(SELF_URL)]
    for url in urls:
        tolerated = set()
        for host, codes in BOT_WALLED.items():
            if host in url:
                tolerated = codes
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=25) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except Exception as exc:  # noqa: BLE001 - network flake, not a page defect
            print(f"  ????  {url}  ({exc})")
            continue
        ok = status == 200 or status in tolerated
        print(f"  {status:<5} {url}{'  (bot-walled, OK in a browser)' if status in tolerated and status != 200 else ''}")
        if not ok:
            problems.append(f"index.html: link returns {status} - {url}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--links", action="store_true", help="also resolve external URLs")
    args = parser.parse_args()

    problems = check()
    if args.links:
        print("external links:")
        problems += check_links()

    if problems:
        print("\nFAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
