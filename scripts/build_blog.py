#!/usr/bin/env python3
"""Build /blog from content/blog/*.md into static HTML.

content/blog/*.md -> blog/ (committed), plus sitemap.xml, robots.txt and the
Writing section of index.html. Nothing at runtime depends on Hashnode or on
this script: the output is plain files served by GitHub Pages.

Usage:
    python3 scripts/build_blog.py            # build and write
    python3 scripts/build_blog.py --check    # exit 1 if the committed output is stale
    python3 scripts/build_blog.py --drafts --out .preview
                                             # local preview including drafts (never committed)
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import posixpath
import re
import shutil
import subprocess
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from markdown_it import MarkdownIt
from latex2mathml.converter import convert as latex_to_mathml
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.footnote import footnote_plugin
from PIL import Image, ImageOps
from pygments import highlight as pyg_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog_config as cfg  # noqa: E402
import update_writing  # noqa: E402
from blog_lib import (  # noqa: E402
    CONTENT, DRAFTS, ROOT, ContentError, date_label, iso, load_page, load_posts,
    load_sections, tag_label, tag_slug, validate,
)

BLOG_URL = f"{cfg.SITE_URL}/blog/"
BLOG_ID = f"{BLOG_URL}#blog"
ASSETS = ROOT / "blog" / "assets"
THEME_GUARD = ("<script>try{var t=localStorage.getItem('the-record-theme');"
               "if(t)document.documentElement.dataset.theme=t}catch(e){}</script>")
THEME_GUARD_HASH = "sha256-pP5MwfJZWvCxkSS0iO9M4STcOUeW0jl58hfmJEgF9/Y="
OG_FALLBACK = {"url": f"{cfg.SITE_URL}/the-record/img/og-card.jpg", "width": 1200, "height": 630}
PLAIN_LANGS = {"", "plaintext", "text", "plain", "txt", "none"}
# Page element ids a heading slug must not take.
RESERVED_IDS = {"main", "comments", "toc", "search", "share", "related", "contents",
                "theme-toggle", "series", "finder-q", "finder-section", "finder-tag"}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


TEXT_SUFFIXES = {".css", ".js", ".svg", ".json", ".xml", ".html", ".md"}


def fingerprint(path: Path) -> str:
    """Short content hash. Text files are hashed with LF line endings, so a
    Windows checkout (core.autocrlf) and CI produce identical output."""
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(data).hexdigest()[:8]


# ===================================================================== images
class Images:
    """Responsive WebP variants, generated once per source (named by source)."""

    def __init__(self, out_root: Path, write: bool):
        self.out_root = out_root
        self.write = write
        self.expected: set[str] = set()
        self.missing: list[str] = []

    def _emit(self, rel: str, make) -> None:
        self.expected.add(rel)
        target = self.out_root / rel
        if target.exists():
            return
        if not self.write:
            self.missing.append(rel)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        make(target)

    def variants(self, src: Path, url_dir: str) -> dict:
        # Output names carry a hash of the source bytes, so replacing an image
        # under the same file name can never leave stale variants behind.
        stem = f"{src.stem}-{fingerprint(src)}"
        if src.suffix.lower() == ".svg":
            text = src.read_text(encoding="utf-8", errors="replace")
            w, h = svg_size(text)
            rel = f"{url_dir}/{stem}.svg"
            self._emit(rel, lambda t: shutil.copyfile(src, t))
            return {"src": "/" + rel, "srcset": "", "width": w, "height": h}

        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            w, h = im.size
            animated = getattr(im, "is_animated", False)
        if animated:
            rel = f"{url_dir}/{stem}{src.suffix.lower()}"
            self._emit(rel, lambda t: shutil.copyfile(src, t))
            return {"src": "/" + rel, "srcset": "", "width": w, "height": h}

        widths = [x for x in cfg.IMAGE_WIDTHS if x < w] + ([w] if w <= cfg.IMAGE_WIDTHS[-1] else [])
        entries = []
        for width in widths:
            height = round(h * width / w)
            rel = f"{url_dir}/{stem}-{width}.webp"

            def make(target, width=width, height=height):
                with Image.open(src) as im:
                    im = ImageOps.exif_transpose(im)
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGBA")
                    im.resize((width, height), Image.LANCZOS).save(target, "WEBP", quality=80, method=6)

            self._emit(rel, make)
            entries.append((width, height, "/" + rel))
        first = entries[0]
        return {
            "src": first[2],
            "srcset": ", ".join(f"{url} {width}w" for width, _, url in entries),
            "width": first[0],
            "height": first[1],
        }

    def og(self, src: Path, rel: str) -> dict:
        def make(target):
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)
                if im.mode in ("RGBA", "LA", "P"):
                    im = im.convert("RGBA")
                    ground = Image.new("RGB", im.size, (244, 241, 234))
                    ground.paste(im, mask=im.split()[-1])
                    im = ground
                ImageOps.fit(im.convert("RGB"), cfg.OG_SIZE, Image.LANCZOS).save(target, "JPEG", quality=82, optimize=True)

        if src.suffix.lower() == ".svg":
            return OG_FALLBACK
        self._emit(rel, make)
        return {"url": f"{cfg.SITE_URL}/{rel}", "width": cfg.OG_SIZE[0], "height": cfg.OG_SIZE[1]}


DIAGRAM_SCROLL_AT = 970  # px; 680px column / 0.7 minimum comfortable scale


class Diagrams:
    """```mermaid fences -> one SVG per theme, rendered by mermaid-cli.

    Renders are cached next to the content (content/blog/diagrams/, and the
    gitignored content/drafts/diagrams/ for drafts), keyed by a hash of the
    source, the CLI version and the theme, so a build only needs Node when a
    diagram is new or changed. The SVGs are shown as <img>: an SVG inside an
    image carries its own styles, which the page's CSP would block inline.
    """

    def __init__(self, images: Images, check: bool):
        self.images = images
        self.check = check
        self.problems: list[str] = []
        self.used: set[Path] = set()

    @staticmethod
    def key(source: str, theme: str) -> str:
        payload = json.dumps([source.strip(), cfg.MERMAID_CLI, cfg.MERMAID_THEMES[theme]], sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _render(self, source: str, theme: str, target: Path) -> str | None:
        cli = shutil.which("mmdc")
        command = [cli] if cli else ([shutil.which("npx"), "-y", cfg.MERMAID_CLI] if shutil.which("npx") else None)
        if not command:
            return "Node.js is needed to render new Mermaid diagrams (install it, then rebuild)"
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "in.mmd").write_text(source, encoding="utf-8")
            (tmp / "config.json").write_text(json.dumps(cfg.MERMAID_THEMES[theme]), encoding="utf-8")
            # CI runners disallow Chrome's sandbox; the input is our own diagram source.
            (tmp / "puppeteer.json").write_text('{"args": ["--no-sandbox"]}', encoding="utf-8")
            result = subprocess.run(command + ["-i", str(tmp / "in.mmd"), "-o", str(tmp / "out.svg"),
                                               "-c", str(tmp / "config.json"), "-p", str(tmp / "puppeteer.json"),
                                               "-b", "transparent", "-q"],
                                    capture_output=True, text=True, timeout=600)
            if result.returncode != 0 or not (tmp / "out.svg").exists():
                detail = (result.stderr or result.stdout).strip().splitlines()
                return "mermaid-cli failed: " + (detail[-1] if detail else f"exit {result.returncode}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(tmp / "out.svg", target)
        return None

    def figure(self, source: str, cache_dir: Path, url_dir: str) -> str | None:
        plates = []
        for theme in ("paper", "press"):
            cached = cache_dir / f"{self.key(source, theme)}-{theme}.svg"
            self.used.add(cached)
            if not cached.exists():
                if self.check:
                    self.images.missing.append(f"diagram not rendered: {cached.name}")
                    return None
                error = self._render(source, theme, cached)
                if error:
                    self.problems.append(error)
                    return None
            rel = f"{url_dir}/{cached.name}"
            self.images._emit(rel, lambda t, src=cached: shutil.copyfile(src, t))
            w, h = svg_size(cached.read_text(encoding="utf-8", errors="replace"))
            plates.append((theme, "/" + rel, w, h))

        title = re.search(r"^\s*accTitle\s*:\s*(.+)$", source, re.M)
        desc = re.search(r"^\s*accDescr\s*:\s*(.+)$", source, re.M)
        alt = (desc or title).group(1).strip() if (desc or title) else "Diagram"
        # Diagrams shrink to the column, but not so far that 14px labels become
        # unreadable: past ~70% they are drawn at 75% and scroll sideways
        # instead. Each plate links to its SVG for a full-size view.
        natural = plates[0][2]
        scale, kind = (0.75, " diagram-figure--scroll") if natural > DIAGRAM_SCROLL_AT else (1, "")
        if natural > 560:
            kind += " diagram-figure--wide"
        imgs = "".join(
            f'<a class="diagram-plate diagram-plate--{theme}" href="{esc(url)}" target="_blank" rel="noopener"'
            + ('' if theme == "paper" else ' tabindex="-1" aria-hidden="true"') + '>'
            + f'<img src="{esc(url)}" width="{round(w * scale)}" height="{round(h * scale)}" '
            + (f'alt="{esc(alt)} (opens full size)"' if theme == "paper" else 'alt=""')
            + ' loading="lazy" decoding="async"></a>'
            for theme, url, w, h in plates)
        parts = [esc(title.group(1).strip())] if title else []
        if natural > 560:
            narrow = "" if "--scroll" in kind else " diagram__hint--narrow"
            parts.append(f'<span class="diagram__hint{narrow}">Scroll sideways, or open it full size.</span>')
        caption = f"<figcaption>{' '.join(parts)}</figcaption>" if parts else ""
        return f'<figure class="figure diagram-figure{kind}"><div class="diagram__scroll">{imgs}</div>{caption}</figure>\n'

    def prune(self, cache_dir: Path) -> None:
        if cache_dir.exists():
            for path in cache_dir.glob("*.svg"):
                if path not in self.used:
                    path.unlink()


def svg_size(text: str) -> tuple[int, int]:
    root = re.search(r"<svg\b[^>]*>", text)
    box = re.search(r'viewBox="[\d.\s-]*?([\d.]+)\s+([\d.]+)"', root.group(0)) if root else None
    if box:
        return round(float(box.group(1))), round(float(box.group(2)))
    w = re.search(r'<svg[^>]*\swidth="([\d.]+)', text)
    h = re.search(r'<svg[^>]*\sheight="([\d.]+)', text)
    if w and h:
        return round(float(w.group(1))), round(float(h.group(1)))
    box = re.search(r'viewBox="[\d.\s-]*?([\d.]+)\s+([\d.]+)"', text)
    if box:
        return round(float(box.group(1))), round(float(box.group(2)))
    return 800, 450


def img_tag(info: dict, alt: str, sizes: str, *, eager: bool = False, cls: str = "") -> str:
    attrs = [f'src="{esc(info["src"])}"']
    if info.get("srcset"):
        attrs.append(f'srcset="{esc(info["srcset"])}" sizes="{esc(sizes)}"')
    attrs.append(f'width="{info["width"]}" height="{info["height"]}" alt="{esc(alt)}"')
    attrs.append('fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"')
    if cls:
        attrs.append(f'class="{cls}"')
    return f"<img {' '.join(attrs)}>"


# =================================================================== markdown
def heading_slug(title: str) -> str:
    from blog_lib import slugify
    slug = slugify(title) if title.strip() else "section"
    return f"{slug}-section" if slug in RESERVED_IDS else slug


def shift_headings(state) -> None:
    """Article titles are the page's <h1>; a body that uses '#' is shifted down."""
    levels = [int(t.tag[1]) for t in state.tokens if t.type == "heading_open"]
    if levels and min(levels) == 1:
        for token in state.tokens:
            if token.type in ("heading_open", "heading_close"):
                token.tag = f"h{min(int(token.tag[1]) + 1, 6)}"


def mark_figures(state) -> None:
    """A paragraph holding only images renders as figures, not <p><img>."""
    tokens = state.tokens
    for i, token in enumerate(tokens):
        if token.type != "paragraph_open" or i + 2 >= len(tokens):
            continue
        children = tokens[i + 1].children or []
        real = [c for c in children if not (c.type in ("softbreak", "hardbreak")
                                            or (c.type == "text" and not c.content.strip()))]
        if real and all(c.type == "image" for c in real):
            token.hidden = True
            tokens[i + 2].hidden = True
            for child in real:
                child.meta["block"] = True


def highlight_code(code: str, lang: str) -> tuple[str, str]:
    lang = (lang or "").lower()
    if lang in PLAIN_LANGS:
        return esc(code.rstrip("\n")), "text"
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return esc(code.rstrip("\n")), lang
    return pyg_highlight(code, lexer, HtmlFormatter(nowrap=True)).rstrip("\n"), lang


def render_fence(self, tokens, idx, options, env) -> str:
    token = tokens[idx]
    info = token.info.strip() if token.type == "fence" else ""
    lang = info.split()[0] if info else ""
    if lang.lower() == "mermaid" and env.get("render_mermaid"):
        figure = env["render_mermaid"](token.content)
        if figure:
            return figure
    body, label = highlight_code(token.content, lang)
    return (f'<div class="code-block"><div class="code-block__bar">'
            f'<span class="code-block__lang">{esc(label)}</span></div>'
            f'<pre class="code" tabindex="0"><code>{body}</code></pre></div>\n')


def render_image(self, tokens, idx, options, env) -> str:
    token = tokens[idx]
    src = token.attrGet("src") or ""
    alt = self.renderInlineAsText(token.children or [], options, env)
    title = token.attrGet("title") or ""
    info = env["resolve_image"](src)
    if info:
        img = img_tag(info, alt, "(max-width: 900px) 100vw, 680px")
    else:
        env["problems"].append(f"image not local, rendered without dimensions: {src}")
        img = f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" decoding="async">'
    if token.meta.get("block"):
        caption = f"<figcaption>{esc(title)}</figcaption>" if title else ""
        return f'<figure class="figure">{img}{caption}</figure>\n'
    return img


def render_heading_close(self, tokens, idx, options, env) -> str:
    opening = tokens[idx - 2]
    slug = opening.attrGet("id")
    tag = tokens[idx].tag
    if slug and opening.type == "heading_open":
        return f' <a class="heading-anchor" href="#{esc(slug)}" aria-label="Link to this section">#</a></{tag}>\n'
    return f"</{tag}>\n"


def render_math(self, tokens, idx, options, env) -> str:
    """$...$ and $$...$$ become MathML at build time: no script, no fonts."""
    token = tokens[idx]
    display = token.type.startswith("math_block") or token.type == "math_inline_double"
    tex = token.content.strip()
    try:
        mathml = latex_to_mathml(tex, display="block" if display else "inline")
    except Exception as exc:  # noqa: BLE001 - latex2mathml raises several types
        env["problems"].append(f"math could not be converted ({exc}): {tex[:60]}")
        return f"<code>{esc(tex)}</code>"
    return f'<div class="math-block">{mathml}</div>\n' if token.type.startswith("math_block") else mathml


def render_table_open(self, tokens, idx, options, env) -> str:
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="Table"><table>\n'


def render_table_close(self, tokens, idx, options, env) -> str:
    return "</table></div>\n"


def make_markdown() -> MarkdownIt:
    # linkify: Hashnode rendered bare URLs as links, so the migration keeps that.
    md = MarkdownIt("commonmark", {"html": True, "linkify": True}).enable(["table", "strikethrough", "linkify"])
    md.use(footnote_plugin)
    # Strict delimiters so prices and shell variables stay text: no space
    # inside the $, and no digit touching it ("$250", "$foo" alone are prose).
    md.use(dollarmath_plugin, allow_labels=False, allow_space=False, allow_digits=False,
           allow_blank_lines=False, double_inline=True)
    for kind in ("math_inline", "math_inline_double", "math_block"):
        md.add_render_rule(kind, render_math)
    md.use(anchors_plugin, min_level=2, max_level=4, slug_func=heading_slug)
    md.core.ruler.before("anchor", "shift_headings", shift_headings)
    md.core.ruler.push("figures", mark_figures)
    md.add_render_rule("fence", render_fence)
    md.add_render_rule("code_block", render_fence)
    md.add_render_rule("image", render_image)
    md.add_render_rule("heading_close", render_heading_close)
    md.add_render_rule("table_open", render_table_open)
    md.add_render_rule("table_close", render_table_close)
    return md


MD = make_markdown()


def render_markdown(body: str, resolve_image, render_mermaid=None) -> dict:
    env = {"resolve_image": resolve_image, "render_mermaid": render_mermaid, "problems": []}
    tokens = MD.parse(body, env)
    toc, words = [], 0
    for i, token in enumerate(tokens):
        if token.type == "inline":
            words += len(re.findall(r"\w+", token.content))
        if token.type == "heading_open" and token.tag in ("h2", "h3") and token.attrGet("id"):
            text = "".join(c.content for c in tokens[i + 1].children or [] if c.type in ("text", "code_inline"))
            toc.append({"id": token.attrGet("id"), "text": text.strip(), "level": int(token.tag[1])})
    rendered = MD.renderer.render(tokens, MD.options, env)
    return {"html": rendered, "toc": toc, "words": words, "problems": env["problems"]}


# ================================================================ the model
class Site:
    def __init__(self, sections, posts, *, preview: bool, images: Images):
        self.sections = sections
        self.by_section = {s["slug"]: s for s in sections}
        self.posts = posts
        self.preview = preview
        self.images = images
        self.diagrams = Diagrams(images, check=not images.write)
        self.files: dict[str, str] = {}
        self.problems: list[str] = []
        self.css_v = fingerprint(ASSETS / "blog.css")
        self.js_v = fingerprint(ASSETS / "blog.js")
        self.giscus = cfg.GISCUS if cfg.GISCUS.get("repo_id") and cfg.GISCUS.get("category_id") else None
        self.tags: dict[str, dict] = {}
        for post in posts:
            for tag in post["tags"]:
                entry = self.tags.setdefault(tag_slug(tag), {"slug": tag_slug(tag), "label": tag_label(tag), "posts": []})
                entry["posts"].append(post)

    # ------------------------------------------------------------ preparation
    def prepare(self) -> None:
        for post in self.posts:
            base = post["path"].parent
            url_dir = f"blog/{post['slug']}/img"

            def resolve(src, base=base, url_dir=url_dir, post=post):
                if re.match(r"[a-z]+:|/", src):
                    return None
                path = (base / src).resolve()
                if not path.exists():
                    self.problems.append(f"{post['path'].name}: image file missing: {src}")
                    return None
                return self.images.variants(path, url_dir)

            def mermaid(source, base=base, url_dir=url_dir):
                return self.diagrams.figure(source, base / "diagrams", url_dir)

            post["url"] = f"/blog/{post['slug']}/"
            post["abs_url"] = cfg.SITE_URL + post["url"]
            rendered = render_markdown(post["body"], resolve, mermaid)
            self.problems += [f"{post['path'].name}: {p}" for p in rendered["problems"]]
            post["html"] = rendered["html"]
            post["toc"] = rendered["toc"] if len(rendered["toc"]) >= cfg.TOC_MIN_HEADINGS else []
            post["words"] = rendered["words"]
            post["minutes"] = max(1, round(rendered["words"] / cfg.WORDS_PER_MINUTE))
            post["summary"] = update_writing._summarize(post["description"]) if post["description"] else ""
            cover = post["meta"].get("cover")
            post["cover"] = resolve(cover) if cover else None
            og_src = post["meta"].get("ogImage") or cover
            og_path = (base / og_src).resolve() if og_src and not re.match(r"[a-z]+:|/", og_src) else None
            post["og"] = (self.images.og(og_path, f"blog/{post['slug']}/og-{fingerprint(og_path)}.jpg")
                          if og_path and og_path.exists() else OG_FALLBACK)
            section = self.by_section.get(post["section"])
            post["section_label"] = section["label"] if section else post["section"]
            post["tag_objs"] = [{"slug": tag_slug(t), "label": tag_label(t)} for t in post["tags"]]
            post["modified"] = post["updated"] or post["date"]

        chronological = sorted(self.posts, key=lambda p: p["date"])
        for i, post in enumerate(chronological):
            post["older"] = chronological[i - 1] if i > 0 else None
            post["newer"] = chronological[i + 1] if i + 1 < len(chronological) else None
            post["related"] = self.related(post)
            section = self.by_section.get(post["section"])
            if section and section["series"]:
                post["series"] = self.series_posts(section)
            else:
                post["series"] = None

    def related(self, post) -> list[dict]:
        def features(p):
            return {f"tag:{tag_slug(t)}" for t in p["tags"]} | {f"section:{p['section']}"}

        mine = features(post)
        scored = []
        for other in self.posts:
            if other is post:
                continue
            theirs = features(other)
            score = len(mine & theirs) / len(mine | theirs)
            if score > 0:
                scored.append((score, other["date"], other))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [p for _, _, p in scored[: cfg.RELATED_COUNT]]

    def series_posts(self, section) -> list[dict]:
        members = [p for p in self.posts if p["section"] == section["slug"]]
        return sorted(members, key=lambda p: (p["meta"].get("seriesOrder", 0), p["date"]))

    # --------------------------------------------------------------- layout
    def csp(self, *, comments: bool) -> str:
        script = f"'self' '{THEME_GUARD_HASH}'"
        style, frame = "'self'", ""
        if comments:
            script += " https://giscus.app"
            style += " https://giscus.app"
            frame = "; frame-src https://giscus.app"
        return (f"default-src 'none'; img-src 'self'; style-src {style}; font-src 'self'; "
                f"script-src {script}; connect-src 'self'; manifest-src 'self'{frame}; "
                "base-uri 'none'; form-action 'none'")

    def page(self, *, rel: str, title: str, description: str, content: str, current: str = "",
             og_type: str = "website", og: dict | None = None, jsonld: dict | None = None,
             head_extra: str = "", comments: bool = False, nameplate_h1: bool = False,
             prev_url: str = "", next_url: str = "", robots: str = "index, follow") -> None:
        canonical = f"{BLOG_URL}{rel.removesuffix('index.html')}"
        og = og or OG_FALLBACK
        if self.preview:
            robots = "noindex, nofollow"
        links = ""
        if prev_url:
            links += f'\n<link rel="prev" href="{esc(cfg.SITE_URL + prev_url)}">'
        if next_url:
            links += f'\n<link rel="next" href="{esc(cfg.SITE_URL + next_url)}">'
        ld = ""
        if jsonld:
            payload = json.dumps(jsonld, ensure_ascii=False, indent=2).replace("</", "<\\/")
            ld = f'\n<script type="application/ld+json">\n{payload}\n</script>'
        banner = ('<p class="draft-banner">Preview build - includes drafts, not for publishing</p>\n'
                  if self.preview else "")
        doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(cfg.AUTHOR_NAME)}">
<meta name="robots" content="{robots}">
<meta http-equiv="Content-Security-Policy" content="{self.csp(comments=comments)}">
<meta name="color-scheme" content="light dark">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="theme-color" content="#f4f1ea" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#14120e" media="(prefers-color-scheme: dark)">
<link rel="canonical" href="{esc(canonical)}">{links}

<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="en_GB">
<meta property="og:site_name" content="{esc(cfg.BLOG_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(og['url'])}">
<meta property="og:image:width" content="{og['width']}">
<meta property="og:image:height" content="{og['height']}">{head_extra}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(og['url'])}">

<link rel="preload" href="/the-record/fonts/newsreader.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/the-record/fonts/fraunces.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/the-record/fonts/fonts.css">
<link rel="stylesheet" href="/the-record/css/styles.css?v=1">
<link rel="stylesheet" href="/blog/assets/blog.css?v={self.css_v}">
{THEME_GUARD}

<link rel="icon" href="/the-record/img/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/the-record/img/favicon-32.png">
<link rel="apple-touch-icon" href="/the-record/img/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
<link rel="alternate" type="application/rss+xml" title="{esc(cfg.BLOG_NAME)} - {esc(cfg.AUTHOR_NAME)}" href="/blog/rss.xml">{ld}
</head>

<body class="blog">
<a class="skip-link" href="#main">Skip to content</a>
{banner}{self.masthead(nameplate_h1)}
{self.nav(current)}

<main id="main">
  <div class="sheet">
{content}
  </div>
</main>

{self.footer()}

<script src="/the-record/js/main.js" defer></script>
<script src="/blog/assets/blog.js?v={self.js_v}" defer></script>
</body>
</html>
"""
        self.files[f"blog/{rel}" if not rel.startswith("blog/") else rel] = doc

    def masthead(self, h1: bool) -> str:
        tag = "h1" if h1 else "p"
        compact = "" if h1 else " masthead--compact"
        count = len(self.posts)
        return f"""<header class="masthead masthead--blog{compact}">
  <div class="sheet">
    <{tag} class="masthead__name blog-nameplate"><a href="/blog/">{esc(cfg.BLOG_NAME)}</a></{tag}>
    <hr class="masthead__rule">
    <div class="masthead__strap">
      <p class="dateline">
        <span><a href="/">{esc(cfg.AUTHOR_NAME)}</a></span><span>Technical lab notebook</span><span>{count} posts</span>
      </p>
      <button class="theme-toggle" type="button" id="theme-toggle" aria-pressed="false">
        <span class="theme-toggle__on" data-theme-label>Paper</span>
      </button>
    </div>
  </div>
</header>"""

    def nav(self, current: str) -> str:
        def item(section):
            here = section["slug"] == current
            attrs = ' class="is-current" aria-current="page"' if here else ""
            return f'<li><a href="/blog/{section["slug"]}/"{attrs}>{esc(section["label"])}</a></li>'

        primary = [item(s) for s in self.sections if s["nav"] == "primary"]
        more = [s for s in self.sections if s["nav"] == "more"]
        more_html = ""
        if more:
            in_more = any(s["slug"] == current for s in more)
            summary_cls = ' class="is-current"' if in_more else ""
            more_html = (f'\n      <li class="more-menu"><details><summary{summary_cls}>More</summary>'
                         f'<ul class="more-menu__list">{"".join(item(s) for s in more)}</ul></details></li>')
        return f"""<nav class="contents blog-nav" aria-label="Blog sections">
  <div class="sheet">
    <ul class="contents__list blog-nav__list">
      {''.join(primary)}{more_html}
      <li class="blog-nav__search-item"><a class="blog-nav__search" href="/blog/#search">Search</a></li>
    </ul>
  </div>
</nav>"""

    def footer(self) -> str:
        return f"""<footer class="blog-footer">
  <div class="sheet">
    <div class="folio">
      <span><a href="/blog/">{esc(cfg.BLOG_NAME)}</a></span>
      <span><a href="/">{esc(cfg.AUTHOR_NAME)}</a> · {esc(cfg.AUTHOR_LOCATION)}</span>
      <span><a href="/blog/rss.xml">RSS</a> · <a href="/blog/tags/">Tags</a> · <a href="https://github.com/Sukalyan2003" target="_blank" rel="me noopener">Source</a></span>
    </div>
  </div>
</footer>"""

    # ------------------------------------------------------------ fragments
    def tags_html(self, post, limit: int | None = None) -> str:
        tags = post["tag_objs"][:limit] if limit else post["tag_objs"]
        if not tags:
            return ""
        links = "".join(f'<a class="tag" href="/blog/tags/{t["slug"]}/">{esc(t["label"])}</a>' for t in tags)
        return f'<div class="tags">{links}</div>'

    def meta_line(self, post) -> str:
        return (f'<p class="story__meta"><time datetime="{iso(post["date"])}">{date_label(post["date"])}</time>'
                f'<span>{post["minutes"]} min read</span></p>')

    def story(self, post, *, lead: bool = False) -> str:
        media = ""
        if post["cover"]:
            sizes = "(max-width: 900px) 100vw, 640px" if lead else "(max-width: 560px) 100vw, (max-width: 900px) 50vw, 300px"
            media = (f'<a class="story__media" href="{post["url"]}" tabindex="-1" aria-hidden="true">'
                     f'{img_tag(post["cover"], "", sizes, eager=lead)}</a>')
        excerpt = f'<p class="story__excerpt">{esc(post["summary"])}</p>' if lead and post["summary"] else ""
        heading = "h3"
        cls = "story story--lead" if lead else "story"
        return f"""<article class="{cls}">
        {media}
        <p class="story__kicker"><a href="/blog/{post['section']}/">{esc(post['section_label'])}</a></p>
        <{heading} class="story__title"><a href="{post['url']}">{esc(post['title'])}</a></{heading}>
        {excerpt}
        {self.meta_line(post)}
      </article>"""

    def row(self, post, *, numeral: str = "", thumb: bool = True) -> str:
        num = f'<span class="section__numeral">{esc(numeral)}</span>' if numeral else ""
        thumb_html = ""
        if thumb and post["cover"]:
            thumb_html = (f'\n        <a class="dispatch__thumb" href="{post["url"]}" tabindex="-1" aria-hidden="true">'
                          f'{img_tag(post["cover"], "", "(max-width: 900px) min(100vw, 420px), 180px")}</a>')
        summary = f'<p>{esc(post["summary"])}</p>' if post["summary"] else ""
        tags = self.tags_html(post, 4)
        meta = f'<div class="dispatch__meta">{tags}</div>' if tags else ""
        cls = "dispatch dispatch--thumb" if thumb_html else "dispatch"
        return f"""<article class="{cls}">
        <div class="dispatch__date">{num}
          <time datetime="{iso(post['date'])}">{date_label(post['date'])}</time>
          <span class="dispatch__read">{post['minutes']} min read</span>
        </div>
        <div class="dispatch__body">
          <p class="dispatch__kicker"><a href="/blog/{post['section']}/">{esc(post['section_label'])}</a></p>
          <h3><a href="{post['url']}">{esc(post['title'])}</a></h3>
          {summary}
          {meta}
        </div>{thumb_html}
      </article>"""

    def rows(self, posts, **kw) -> str:
        if not posts:
            return '<p class="empty-state">Nothing here yet.</p>'
        return '<div class="dispatches">\n      ' + "\n      ".join(self.row(p, **kw) for p in posts) + "\n    </div>"

    def section_head(self, title: str, *, numeral: str = "", note: str = "", hid: str = "", level: str = "h2") -> str:
        num = f'<span class="section__numeral">{esc(numeral)}</span>' if numeral else ""
        note_html = f'<span class="section__note">{esc(note)}</span>' if note else ""
        id_attr = f' id="{hid}"' if hid else ""
        return f'<div class="section__head">{num}<{level} class="section__title"{id_attr}>{esc(title)}</{level}>{note_html}</div>'

    def breadcrumb_ld(self, trail: list[tuple[str, str]]) -> dict:
        return {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
                for i, (name, url) in enumerate(trail)
            ],
        }

    def author_ld(self) -> dict:
        return {"@type": "Person", "@id": cfg.PERSON_ID, "name": cfg.AUTHOR_NAME, "url": cfg.SITE_URL + "/"}

    # ----------------------------------------------------------------- pages
    def build_index(self) -> None:
        front, rest = self.posts[: cfg.FRONT_PAGE_COUNT], self.posts[cfg.FRONT_PAGE_COUNT:]
        pages = max(1, math.ceil(len(rest) / cfg.POSTS_PER_PAGE))
        for n in range(1, pages + 1):
            chunk = rest[(n - 1) * cfg.POSTS_PER_PAGE: n * cfg.POSTS_PER_PAGE]
            url = "/blog/" if n == 1 else f"/blog/page/{n}/"
            prev_url = "" if n == 1 else ("/blog/" if n == 2 else f"/blog/page/{n - 1}/")
            next_url = f"/blog/page/{n + 1}/" if n < pages else ""
            parts = []
            if n == 1:
                parts.append(self.front_block(front))
                parts.append(self.colophon())
            parts.append(self.archive_block(chunk, n, pages, finder=(n == 1)))
            jsonld = {"@context": "https://schema.org", "@graph": [
                {"@type": "Blog", "@id": BLOG_ID, "url": BLOG_URL, "name": cfg.BLOG_NAME,
                 "description": cfg.BLOG_DESCRIPTION, "inLanguage": "en", "author": self.author_ld(),
                 "isPartOf": {"@id": cfg.WEBSITE_ID}},
                self.breadcrumb_ld([("Home", cfg.SITE_URL + "/"), ("Blog", BLOG_URL)]),
            ]}
            title = f"{cfg.BLOG_NAME} - {cfg.AUTHOR_NAME}" if n == 1 else f"{cfg.BLOG_NAME} - page {n}"
            self.page(rel=url.removeprefix("/blog/") + "index.html", title=title,
                      description=cfg.BLOG_DESCRIPTION, content="\n".join(parts), jsonld=jsonld,
                      nameplate_h1=(n == 1), prev_url=prev_url, next_url=next_url)

    def front_block(self, front) -> str:
        if not front:
            return '<section class="section"><p class="empty-state">No posts yet.</p></section>'
        lead, sides = front[0], front[1:]
        left, right = sides[:2], sides[2:4]
        col = lambda posts, side: (f'<div class="front__col front__col--{side}">' +
                                   "".join(self.story(p) for p in posts) + "</div>") if posts else ""
        return f"""    <section class="section front" aria-labelledby="latest-title">
      {self.section_head("Latest", numeral="01", note="Newest first", hid="latest-title")}
      <div class="front__grid">
      <div class="front__lead">{self.story(lead, lead=True)}</div>
      {col(left, "left")}
      {col(right, "right")}
      </div>
    </section>"""

    def colophon(self) -> str:
        start = next((s for s in self.sections if s["page"]), None)
        start_link = f'<span><a href="/blog/{start["slug"]}/">{esc(start["label"])}</a></span>' if start else ""
        return f"""    <section class="colophon" aria-label="About this blog">
      <div class="portrait colophon__portrait">
        <picture class="portrait__plate portrait__plate--paper"><img src="/the-record/img/portrait-halftone-240.webp" width="240" height="240" alt="" loading="lazy" decoding="async"></picture>
        <picture class="portrait__plate portrait__plate--press"><img src="/the-record/img/portrait-halftone-press-240.webp" width="240" height="240" alt="" loading="lazy" decoding="async"></picture>
      </div>
      <div class="colophon__body">
        <p class="colophon__name">{esc(cfg.BLOG_NAME)}</p>
        <p class="colophon__desc">A technical lab notebook by <a href="/">{esc(cfg.AUTHOR_NAME)}</a>: RAG systems, interpreters, Nand2Tetris, Linux, ML experiments, and project breakdowns.</p>
        <p class="colophon__meta"><span>{len(self.posts)} posts</span>{start_link}<span><a href="/blog/rss.xml">RSS</a></span></p>
      </div>
    </section>"""

    def archive_block(self, chunk, n, pages, *, finder: bool) -> str:
        head = self.section_head("Archive", numeral="02", note=f"Page {n} of {pages}", hid="archive-title")
        finder_html = self.finder() if finder else ""
        return f"""    <section class="section archive" id="search" aria-labelledby="archive-title">
      {head}
      {finder_html}
      <div class="archive__list" data-archive>
      {self.rows(chunk)}
      {self.pagination(n, pages)}
      </div>
      {self.browse()}
    </section>"""

    def finder(self) -> str:
        sections = "".join(f'<option value="{s["slug"]}">{esc(s["label"])}</option>'
                           for s in self.sections if not s["page"])
        tags = "".join(f'<option value="{t["slug"]}">{esc(t["label"])} ({len(t["posts"])})</option>'
                       for t in sorted(self.tags.values(), key=lambda t: t["label"]))
        return f"""<form class="finder" role="search" aria-label="Search posts" data-finder hidden>
        <div class="finder__field finder__field--q">
          <label class="label" for="finder-q">Search</label>
          <input id="finder-q" type="search" name="q" autocomplete="off" spellcheck="false" placeholder="Title, summary or tag">
        </div>
        <div class="finder__field">
          <label class="label" for="finder-section">Section</label>
          <select id="finder-section" name="section"><option value="">All sections</option>{sections}</select>
        </div>
        <div class="finder__field">
          <label class="label" for="finder-tag">Tag</label>
          <select id="finder-tag" name="tag"><option value="">All tags</option>{tags}</select>
        </div>
      </form>
      <output class="finder__status" for="finder-q finder-section finder-tag" aria-live="polite" data-finder-status></output>
      <ul class="finder__results" data-finder-results hidden></ul>"""

    def browse(self) -> str:
        links = "".join(f'<li><a href="/blog/{s["slug"]}/">{esc(s["label"])}</a></li>' for s in self.sections)
        return (f'<nav class="browse" aria-label="Browse the archive"><p class="label">Browse</p>'
                f'<ul class="browse__list">{links}<li><a href="/blog/tags/">All tags</a></li></ul></nav>')

    def pagination(self, n, pages) -> str:
        if pages <= 1:
            return ""
        url = lambda k: "/blog/" if k == 1 else f"/blog/page/{k}/"
        items = []
        for k in range(1, pages + 1):
            if k == n:
                items.append(f'<li><a href="{url(k)}" aria-current="page">{k}</a></li>')
            else:
                items.append(f'<li><a href="{url(k)}">{k}</a></li>')
        newer = f'<a class="pagination__step" href="{url(n - 1)}" rel="prev">Newer posts</a>' if n > 1 else ""
        older = f'<a class="pagination__step" href="{url(n + 1)}" rel="next">Older posts</a>' if n < pages else ""
        return (f'<nav class="pagination" aria-label="Archive pages">{newer}'
                f'<ol class="pagination__pages">{"".join(items)}</ol>{older}</nav>')

    def build_sections(self) -> None:
        for section in self.sections:
            if section["page"]:
                self.build_content_page(section)
                continue
            members = [p for p in self.posts if p["section"] == section["slug"]]
            if section["series"]:
                members = self.series_posts(section)
                listing = self.rows_numbered(members)
                note = f"{len(members)} parts, in reading order"
            else:
                listing = self.rows(members)
                note = f"{len(members)} posts, newest first"
            intro = f'<p class="standfirst">{esc(section["description"])}</p>' if section["description"] else ""
            content = f"""    <section class="section page-intro">
      <p class="entry__kicker">{'Series' if section['series'] else 'Section'}</p>
      <h1 class="page-title">{esc(section['label'])}</h1>
      {intro}
    </section>
    <section class="section" aria-labelledby="list-title">
      {self.section_head("Posts", note=note, hid="list-title")}
      {listing}
      {self.browse()}
    </section>"""
            url = f"{BLOG_URL}{section['slug']}/"
            jsonld = {"@context": "https://schema.org", "@graph": [
                {"@type": "CollectionPage", "@id": url, "url": url, "name": section["label"],
                 "description": section["description"], "isPartOf": {"@id": BLOG_ID}, "inLanguage": "en"},
                self.breadcrumb_ld([("Home", cfg.SITE_URL + "/"), ("Blog", BLOG_URL), (section["label"], url)]),
            ]}
            self.page(rel=f"{section['slug']}/index.html", title=f"{section['label']} - {cfg.BLOG_NAME}",
                      description=section["description"] or f"{section['label']} posts on {cfg.BLOG_NAME}.",
                      content=content, current=section["slug"], jsonld=jsonld)

    def rows_numbered(self, posts) -> str:
        if not posts:
            return '<p class="empty-state">Nothing here yet.</p>'
        return ('<div class="dispatches">\n      ' +
                "\n      ".join(self.row(p, numeral=f"{i:02d}") for i, p in enumerate(posts, 1)) +
                "\n    </div>")

    def build_content_page(self, section) -> None:
        page = load_page(section["page"])
        rendered = render_markdown(page["body"], lambda src: None, lambda source: self.diagrams.figure(
            source, CONTENT / "diagrams", f"blog/{section['slug']}/img"))
        self.problems += [f"{section['page']}: {p}" for p in rendered["problems"]]
        title = page["title"] or section["label"]
        content = f"""    <article class="section article article--page">
      <header class="article__head">
        <h1 class="article__title">{esc(title)}</h1>
      </header>
      <div class="prose">
{rendered['html']}
      </div>
      <p><a class="more-link" href="/blog/">All posts</a></p>
    </article>"""
        url = f"{BLOG_URL}{section['slug']}/"
        jsonld = {"@context": "https://schema.org", "@graph": [
            {"@type": "WebPage", "@id": url, "url": url, "name": title, "isPartOf": {"@id": BLOG_ID}, "inLanguage": "en"},
            self.breadcrumb_ld([("Home", cfg.SITE_URL + "/"), ("Blog", BLOG_URL), (title, url)]),
        ]}
        self.page(rel=f"{section['slug']}/index.html", title=f"{title} - {cfg.BLOG_NAME}",
                  description=page["description"] or cfg.BLOG_DESCRIPTION, content=content,
                  current=section["slug"], jsonld=jsonld)

    def build_tags(self) -> None:
        ordered = sorted(self.tags.values(), key=lambda t: (-len(t["posts"]), t["label"]))
        items = "".join(f'<li><a class="tag" href="/blog/tags/{t["slug"]}/">{esc(t["label"])}'
                        f'<span class="tag__count">{len(t["posts"])}</span></a></li>' for t in ordered)
        body = f'<ul class="tag-index">{items}</ul>' if ordered else '<p class="empty-state">No tags yet.</p>'
        content = f"""    <section class="section page-intro">
      <p class="entry__kicker">Index</p>
      <h1 class="page-title">Tags</h1>
      <p class="standfirst">Every topic tag used on {esc(cfg.BLOG_NAME)}, most used first.</p>
    </section>
    <section class="section" aria-labelledby="tags-title">
      {self.section_head("All tags", note=f"{len(ordered)} tags", hid="tags-title")}
      {body}
    </section>"""
        self.page(rel="tags/index.html", title=f"Tags - {cfg.BLOG_NAME}",
                  description=f"All topic tags on {cfg.BLOG_NAME}.", content=content)
        for tag in ordered:
            content = f"""    <section class="section page-intro">
      <p class="entry__kicker"><a href="/blog/tags/">Tag</a></p>
      <h1 class="page-title">{esc(tag['label'])}</h1>
    </section>
    <section class="section" aria-labelledby="list-title">
      {self.section_head("Posts", note=f"{len(tag['posts'])} tagged", hid="list-title")}
      {self.rows(tag['posts'])}
      {self.browse()}
    </section>"""
            self.page(rel=f"tags/{tag['slug']}/index.html", title=f"Posts tagged {tag['label']} - {cfg.BLOG_NAME}",
                      description=f"Posts on {cfg.BLOG_NAME} tagged {tag['label']}.", content=content)

    def build_posts(self) -> None:
        for post in self.posts:
            self.build_post(post)

    def build_post(self, post) -> None:
        section = self.by_section.get(post["section"])
        crumbs = (f'<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="/blog/">Blog</a></li>'
                  f'<li><a href="/blog/{post["section"]}/">{esc(post["section_label"])}</a></li></ol></nav>')
        series_label = ""
        if post["series"]:
            pos = post["series"].index(post) + 1
            series_label = f'<p class="article__series label">Part {pos} of {len(post["series"])}</p>'
        standfirst = ""
        if post["description"] and post["meta"].get("descriptionSource") != "excerpt":
            standfirst = f'<p class="standfirst article__standfirst">{esc(post["description"])}</p>'
        updated = ""
        if post["updated"]:
            updated = f'<span>Updated <time datetime="{iso(post["updated"])}">{date_label(post["updated"])}</time></span>'
        draft_note = '<p class="draft-banner">Draft - not published</p>' if post["draft"] else ""
        cover = ""
        if post["cover"]:
            cover = (f'<figure class="article__cover">'
                     f'{img_tag(post["cover"], post["meta"].get("coverAlt", ""), "(max-width: 900px) 100vw, 680px", eager=True)}</figure>')
        toc = ""
        if post["toc"]:
            items = "".join(f'<li class="toc__l{h["level"]}"><a href="#{esc(h["id"])}">{esc(h["text"])}</a></li>'
                            for h in post["toc"])
            toc = (f'<nav class="toc" aria-label="On this page"><details class="toc__box" data-toc>'
                   f'<summary class="label">On this page</summary><ol class="toc__list">{items}</ol></details></nav>')
        rail = f"""<aside class="article__rail" aria-label="Article details">
          <dl class="article__facts">
            <div><dt>Published</dt><dd><time datetime="{iso(post['date'])}">{date_label(post['date'])}</time></dd></div>
            {f'<div><dt>Updated</dt><dd><time datetime="{iso(post["updated"])}">{date_label(post["updated"])}</time></dd></div>' if post['updated'] else ''}
            <div><dt>Reading time</dt><dd>{post['minutes']} min</dd></div>
            <div><dt>Section</dt><dd><a href="/blog/{post['section']}/">{esc(post['section_label'])}</a></dd></div>
          </dl>
          {toc}
        </aside>"""
        content = f"""    <article class="article" aria-labelledby="article-title">
      <header class="article__head">
        {draft_note}{crumbs}
        {series_label}
        <h1 class="article__title" id="article-title">{esc(post['title'])}</h1>
        {standfirst}
        <p class="dateline article__dateline"><span>By <a href="/">{esc(cfg.AUTHOR_NAME)}</a></span><span>Published <time datetime="{iso(post['date'])}">{date_label(post['date'])}</time></span>{updated}<span>{post['minutes']} min read</span></p>
      </header>
      <div class="article__layout">
        {rail}
        <div class="article__main">
          {cover}
          <div class="prose">
{post['html']}
          </div>
          <footer class="article__foot">
            {self.tags_html(post)}
            {self.share(post)}
            {self.author_box()}
          </footer>
        </div>
      </div>
      {self.series_nav(post)}
      {self.pager(post)}
      {self.related_block(post)}
      {self.comments(post)}
      <p><a class="more-link" href="/blog/">Back to all posts</a></p>
    </article>"""
        head_extra = (f'\n<meta property="article:published_time" content="{iso(post["date"])}">'
                      f'\n<meta property="article:modified_time" content="{iso(post["modified"])}">'
                      f'\n<meta property="article:author" content="{esc(cfg.SITE_URL)}/">'
                      f'\n<meta property="article:section" content="{esc(post["section_label"])}">'
                      + "".join(f'\n<meta property="article:tag" content="{esc(t["label"])}">' for t in post["tag_objs"]))
        canonical = post["meta"].get("canonical") or post["abs_url"]
        jsonld = {"@context": "https://schema.org", "@graph": [
            {"@type": "BlogPosting", "@id": f"{canonical}#article", "mainEntityOfPage": canonical,
             "url": canonical, "headline": post["title"][:110], "description": post["description"],
             "datePublished": iso(post["date"]), "dateModified": iso(post["modified"]),
             "author": self.author_ld(), "publisher": self.author_ld(),
             "image": [post["og"]["url"]], "keywords": [t["label"] for t in post["tag_objs"]],
             "articleSection": post["section_label"], "wordCount": post["words"], "inLanguage": "en",
             "isPartOf": {"@type": "Blog", "@id": BLOG_ID, "name": cfg.BLOG_NAME, "url": BLOG_URL}},
            self.breadcrumb_ld([("Home", cfg.SITE_URL + "/"), ("Blog", BLOG_URL),
                                (post["section_label"], f"{BLOG_URL}{post['section']}/"), (post["title"], canonical)]),
        ]}
        title = post["meta"].get("seoTitle") or post["title"]
        self.page(rel=f"{post['slug']}/index.html", title=f"{title} - {cfg.BLOG_NAME}",
                  description=post["description"] or cfg.BLOG_DESCRIPTION, content=content,
                  current=section["slug"] if section else "", og_type="article", og=post["og"],
                  jsonld=jsonld, head_extra=head_extra, comments=bool(self.giscus))

    def share(self, post) -> str:
        url = quote(post["abs_url"], safe="")
        text = quote(post["title"], safe="")
        return f"""<div class="share">
              <p class="label">Share</p>
              <ul class="share__list">
                <li><button class="action" type="button" data-share hidden>Share</button></li>
                <li><button class="action" type="button" data-copy-link="{esc(post['abs_url'])}" hidden>Copy link</button></li>
                <li><a class="action" href="https://www.linkedin.com/sharing/share-offsite/?url={url}" target="_blank" rel="noopener">LinkedIn</a></li>
                <li><a class="action" href="https://x.com/intent/post?url={url}&amp;text={text}" target="_blank" rel="noopener">X</a></li>
                <li><a class="action" href="https://www.reddit.com/submit?url={url}&amp;title={text}" target="_blank" rel="noopener">Reddit</a></li>
                <li><a class="action" href="mailto:?subject={text}&amp;body={url}">Email</a></li>
              </ul>
              <output class="share__status" aria-live="polite" data-share-status></output>
            </div>"""

    def author_box(self) -> str:
        links = " · ".join(f'<a href="{esc(u)}" target="_blank" rel="me noopener">{esc(n)}</a>'
                           for n, u in cfg.AUTHOR_LINKS.items())
        return f"""<aside class="author" aria-label="About the author">
              <div class="portrait author__portrait">
                <picture class="portrait__plate portrait__plate--paper"><img src="/the-record/img/portrait-halftone-240.webp" width="240" height="240" alt="" loading="lazy" decoding="async"></picture>
                <picture class="portrait__plate portrait__plate--press"><img src="/the-record/img/portrait-halftone-press-240.webp" width="240" height="240" alt="" loading="lazy" decoding="async"></picture>
              </div>
              <div class="author__body">
                <p class="author__name"><a href="/">{esc(cfg.AUTHOR_NAME)}</a></p>
                <p class="author__role">{esc(cfg.AUTHOR_ROLE)}. {esc(cfg.AUTHOR_LOCATION)}.</p>
                <p class="author__links"><a href="/">Portfolio</a> · {links} · <a href="/blog/rss.xml">RSS</a></p>
              </div>
            </aside>"""

    def series_nav(self, post) -> str:
        if not post["series"]:
            return ""
        section = self.by_section[post["section"]]
        items = []
        for i, member in enumerate(post["series"], 1):
            if member is post:
                items.append(f'<li><span class="section__numeral">{i:02d}</span><span aria-current="page">{esc(member["title"])}</span></li>')
            else:
                items.append(f'<li><span class="section__numeral">{i:02d}</span><a href="{member["url"]}">{esc(member["title"])}</a></li>')
        return f"""<nav class="section series" id="series" aria-labelledby="series-title">
        {self.section_head(section['label'], note="The series, in reading order", hid="series-title")}
        <ol class="series__list">{''.join(items)}</ol>
      </nav>"""

    def pager(self, post) -> str:
        older, newer = post["older"], post["newer"]
        if not older and not newer:
            return ""
        parts = []
        if older:
            parts.append(f'<a class="pager__link pager__link--older" href="{older["url"]}" rel="prev">'
                         f'<span class="label">Older</span><span class="pager__title">{esc(older["title"])}</span></a>')
        if newer:
            parts.append(f'<a class="pager__link pager__link--newer" href="{newer["url"]}" rel="next">'
                         f'<span class="label">Newer</span><span class="pager__title">{esc(newer["title"])}</span></a>')
        return f'<nav class="pager" aria-label="Older and newer posts">{"".join(parts)}</nav>'

    def related_block(self, post) -> str:
        if not post["related"]:
            return ""
        return f"""<section class="section related" id="related" aria-labelledby="related-title">
        {self.section_head("Related", note="By shared topics", hid="related-title")}
        {self.rows(post['related'], thumb=False)}
      </section>"""

    def comments(self, post) -> str:
        if not self.giscus:
            return ""
        g = self.giscus
        return f"""<section class="section comments" id="comments" aria-labelledby="comments-title">
        {self.section_head("Comments", note="Via GitHub Discussions", hid="comments-title")}
        <div class="giscus-mount" data-giscus data-repo="{esc(g['repo'])}" data-repo-id="{esc(g['repo_id'])}"
             data-category="{esc(g['category'])}" data-category-id="{esc(g['category_id'])}" data-term="{esc(post['slug'])}"
             data-theme-paper="{cfg.SITE_URL}/blog/assets/giscus-paper.css" data-theme-press="{cfg.SITE_URL}/blog/assets/giscus-press.css">
          <p class="comments__fallback">Comments are GitHub Discussions threads and load with JavaScript.
            <a href="https://github.com/{esc(g['repo'])}/discussions" target="_blank" rel="noopener">Open the discussions on GitHub</a>.</p>
        </div>
      </section>"""

    # --------------------------------------------------------- feeds & maps
    def build_search(self) -> None:
        records = [{
            "slug": p["slug"], "url": p["url"], "title": p["title"], "date": iso(p["date"]),
            "dateLabel": date_label(p["date"]), "section": p["section"], "sectionLabel": p["section_label"],
            "tags": p["tag_objs"], "summary": p["summary"], "minutes": p["minutes"],
        } for p in self.posts]
        self.files["blog/search.json"] = json.dumps(records, ensure_ascii=False, indent=1) + "\n"

    def build_rss(self) -> None:
        def absolute(fragment: str) -> str:
            fragment = re.sub(r'(href|src)="/(?!/)', rf'\1="{cfg.SITE_URL}/', fragment)
            return re.sub(r'srcset="([^"]+)"', lambda m: 'srcset="' + re.sub(
                r"(^|,\s*)/(?!/)", rf"\g<1>{cfg.SITE_URL}/", m.group(1)) + '"', fragment)

        def cdata(text: str) -> str:
            return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"

        latest = max((p["modified"] for p in self.posts), default=datetime(2024, 1, 1, tzinfo=timezone.utc))
        items = []
        for p in self.posts[: cfg.RSS_ITEMS]:  # newest first; the full archive lives in the sitemap
            cats = "".join(f"\n      <category>{esc(t['label'])}</category>" for t in p["tag_objs"])
            items.append(f"""    <item>
      <title>{esc(p['title'])}</title>
      <link>{p['abs_url']}</link>
      <guid isPermaLink="true">{p['abs_url']}</guid>
      <pubDate>{rfc822(p['date'])}</pubDate>
      <dc:creator>{esc(cfg.AUTHOR_NAME)}</dc:creator>
      <description>{esc(p['summary'])}</description>{cats}
      <content:encoded>{cdata(absolute(p['html']))}</content:encoded>
    </item>""")
        self.files["blog/rss.xml"] = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>{esc(cfg.BLOG_NAME)}</title>
    <link>{BLOG_URL}</link>
    <description>{esc(cfg.BLOG_DESCRIPTION)}</description>
    <language>en</language>
    <lastBuildDate>{rfc822(latest)}</lastBuildDate>
    <atom:link href="{BLOG_URL}rss.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""

    def build_sitemap(self, home_lastmod: str) -> None:
        latest = max((p["modified"] for p in self.posts), default=None)
        latest_day = latest.strftime("%Y-%m-%d") if latest else home_lastmod
        entries = [(f"{cfg.SITE_URL}/", max(home_lastmod, latest_day), "1.0")]
        for rel in sorted(k for k in self.files if k.endswith("index.html")):
            url = cfg.SITE_URL + "/" + rel.removesuffix("index.html")
            post = next((p for p in self.posts if f"blog/{p['slug']}/index.html" == rel), None)
            day = post["modified"].strftime("%Y-%m-%d") if post else latest_day
            priority = "0.8" if post else ("0.9" if rel == "blog/index.html" else "0.5")
            entries.append((url, day, priority))
        body = "".join(f"""  <url>
    <loc>{esc(url)}</loc>
    <lastmod>{day}</lastmod>
    <priority>{priority}</priority>
  </url>
""" for url, day, priority in entries)
        self.files["sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                     f"{body}</urlset>\n")
        self.files["robots.txt"] = (f"User-agent: *\nAllow: /\nDisallow: /content/\nDisallow: /migration/\n\n"
                                    f"Sitemap: {cfg.SITE_URL}/sitemap.xml\n")

    # ------------------------------------------------------------ integrity
    def check_links(self) -> None:
        pages = {k.removesuffix("index.html") for k in self.files if k.endswith("index.html")}
        for rel, text in self.files.items():
            if not rel.endswith(".html"):
                continue
            for href in re.findall(r'href="(/blog/[^"#?]*)', text):
                target = href.lstrip("/")
                if target.startswith("blog/assets/") or "." in target.rsplit("/", 1)[-1]:
                    continue  # files (feeds, images, SVGs) are checked by check.py
                if not target.endswith("/"):
                    target += "/"
                if target not in pages:
                    self.problems.append(f"{rel}: link to missing page {href}")

    def build(self, home_lastmod: str) -> None:
        self.prepare()
        self.build_index()
        self.build_sections()
        self.build_tags()
        self.build_posts()
        self.build_search()
        self.build_rss()
        self.problems += self.diagrams.problems
        self.check_links()
        self.build_sitemap(home_lastmod)
        for rel in self.files:
            if rel.endswith(".html"):
                self.files[rel] = relativize(self.files[rel], rel)


ROOT_URL = re.compile(r'(\s(?:href|src))="(/(?!/)[^"]*)"')
SRCSET = re.compile(r'(\ssrcset)="([^"]*)"')


def relative_url(url: str, page: str) -> str:
    """'/the-record/css/x.css' as seen from 'blog/slug/index.html' -> '../../the-record/css/x.css'.

    Templates write root-absolute URLs; every page is rewritten to relative
    ones at the end of the build, so the site works wherever it is served
    from: GitHub Pages, VS Code Live Server rooted at a parent folder, any
    local static server.
    """
    path, sep, rest = url.partition("#")
    path, qsep, query = path.partition("?")
    suffix = (qsep + query) + (sep + rest)
    target = path.lstrip("/")
    rel = posixpath.relpath(target or ".", posixpath.dirname(page) or ".")
    if path.endswith("/") or not target:
        rel = "./" if rel == "." else rel + "/"
    return rel + suffix


def relativize(doc: str, page: str) -> str:
    doc = ROOT_URL.sub(lambda m: f'{m.group(1)}="{relative_url(m.group(2), page)}"', doc)

    def srcset(match):
        parts = []
        for candidate in match.group(2).split(","):
            bits = candidate.strip().split()
            if bits and bits[0].startswith("/") and not bits[0].startswith("//"):
                bits[0] = relative_url(bits[0], page)
            parts.append(" ".join(bits))
        return f'{match.group(1)}="{", ".join(parts)}"'

    return SRCSET.sub(srcset, doc)


def rfc822(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


def current_home_lastmod() -> str:
    try:
        text = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        match = re.search(rf"<loc>{re.escape(cfg.SITE_URL)}/</loc>\s*<lastmod>([\d-]+)</lastmod>", text)
        if match:
            return match.group(1)
    except OSError:
        pass
    return "2026-01-01"


# ======================================================================= main
def load_preview_drafts(sections: list[dict], published: set[str]) -> list[dict]:
    drafts = []
    for draft in load_posts(DRAFTS):
        if draft["slug"] in published:
            print(f"preview: skipping draft '{draft['slug']}' (a published post has that slug)")
        else:
            drafts.append(draft)
    if not drafts:
        return []
    if not any(s["slug"] == "drafts" for s in sections):
        sections.append({"slug": "drafts", "label": "Drafts", "nav": "more", "description":
                         "Local drafts. This section exists only in preview builds.", "series": False, "page": None})
    now = datetime.now(timezone.utc)
    for draft in drafts:
        draft["date"] = draft["date"] or now
        if not draft["section"] or draft["section"] not in {s["slug"] for s in sections}:
            draft["section"] = "drafts"
        if any(s["slug"] == draft["section"] and s["series"] for s in sections):
            draft["meta"].setdefault("seriesOrder", 999)
    return drafts


def sync(files: dict[str, str], images: Images, out_root: Path, write: bool) -> list[str]:
    """Write changed files and delete stale generated ones. Returns what differs."""
    changed = []
    for rel, text in sorted(files.items()):
        target = out_root / rel
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current != text:
            changed.append(rel)
            if write:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
    changed += images.missing
    blog_dir = out_root / "blog"
    keep = set(files) | images.expected
    if blog_dir.exists():
        for path in sorted(blog_dir.rglob("*"), reverse=True):
            rel = path.relative_to(out_root).as_posix()
            if rel.startswith("blog/assets"):
                continue
            if path.is_file() and rel not in keep:
                changed.append(f"(stale) {rel}")
                if write:
                    path.unlink()
            elif path.is_dir() and write and not any(path.iterdir()):
                path.rmdir()
    return changed


def copy_preview_assets(out_root: Path) -> None:
    for rel in ("the-record/css", "the-record/js", "the-record/fonts", "the-record/img", "blog/assets"):
        src = ROOT / rel
        dst = out_root / rel
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    for rel in ("index.html", "manifest.json", "404.html"):
        shutil.copyfile(ROOT / rel, out_root / rel)


def run(check: bool = False, drafts: bool = False, out: Path | None = None) -> int:
    sections = load_sections()
    posts = load_posts()
    errors = validate(sections, posts)
    if errors:
        print("content errors:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    out_root = (out or ROOT).resolve()
    preview = drafts
    if preview and out_root == ROOT.resolve():
        print("--drafts needs --out (drafts must never be written into the committed blog/)", file=sys.stderr)
        return 2
    if preview:
        drafts = load_preview_drafts(sections, {p["slug"] for p in posts})
        posts = sorted(posts + drafts, key=lambda p: p["date"], reverse=True)

    images = Images(out_root, write=not check)
    site = Site(sections, posts, preview=preview, images=images)
    try:
        site.build(current_home_lastmod())
    except ContentError as exc:
        print(f"content error: {exc}", file=sys.stderr)
        return 1
    if site.problems:
        print("build problems:\n  " + "\n  ".join(site.problems), file=sys.stderr)
        return 1

    if preview:
        out_root.mkdir(parents=True, exist_ok=True)
        copy_preview_assets(out_root)
    elif not check:
        site.diagrams.prune(CONTENT / "diagrams")  # drop renders no post uses any more
    changed = sync(site.files, images, out_root, write=not check)

    if not preview:
        index = update_writing.TARGET.read_text(encoding="utf-8")
        updated = update_writing.splice(index, update_writing.render(update_writing.posts_from_records(
            json.loads(site.files["blog/search.json"]))))
        if updated != index:
            changed.append("index.html (Writing section)")
            if not check:
                update_writing.TARGET.write_text(updated, encoding="utf-8")

    pages = sum(1 for k in site.files if k.endswith(".html"))
    if check:
        if changed:
            print("blog output is STALE:\n  " + "\n  ".join(changed[:40]), file=sys.stderr)
            return 1
        print(f"blog output up to date ({len(posts)} posts, {pages} pages)")
        return 0
    print(f"built {len(posts)} posts, {pages} pages into {out_root.relative_to(ROOT.resolve()) if out_root != ROOT.resolve() else '.'}"
          f" ({len(changed)} files changed)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="fail if the committed output is stale")
    parser.add_argument("--drafts", action="store_true", help="include content/drafts (requires --out)")
    parser.add_argument("--out", type=Path, help="output root (default: the repository)")
    args = parser.parse_args(argv)
    return run(check=args.check, drafts=args.drafts, out=args.out)


if __name__ == "__main__":
    raise SystemExit(main())
