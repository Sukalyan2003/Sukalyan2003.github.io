"""Shared content model for the blog: front matter, posts, sections, validation.

Used by the importer, the generator and the management CLI so all three agree
on what a valid post is.

Posts are plain Markdown with a YAML front matter block. Values are written as
JSON scalars (valid YAML), which keeps quoting unambiguous and lets the CLI
change one key with a line edit instead of re-serialising the whole block.
"""

from __future__ import annotations

import io
import json
import re
from collections import Counter
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

import blog_config as cfg

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "blog"
DRAFTS = ROOT / "content" / "drafts"
PAGES = CONTENT / "pages"
SECTIONS_FILE = CONTENT / "sections.yml"
OUT = ROOT / "blog"
MIGRATION = ROOT / "migration"

# Paths under /blog/ that the generator owns; a post or section may not use them.
RESERVED_SLUGS = {"tags", "page", "assets", "img", "rss.xml", "search.json"}

FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.S)

# Order keys are written in, so every file reads the same way.
KEY_ORDER = [
    "title", "slug", "section", "seriesOrder", "draft", "datePublished",
    "dateUpdated", "description", "descriptionSource", "seoTitle", "tags",
    "cover", "coverAlt", "ogImage", "canonical", "hashnode",
]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Hashnode tag slugs whose natural spelling is not just "slug with spaces".
TAG_LABELS = {
    "ai": "AI", "llm": "LLM", "rag": "RAG", "mcp": "MCP", "cs50": "CS50",
    "cs50-ai": "CS50 AI", "bm25": "BM25", "ast": "AST", "cli": "CLI", "c": "C",
    "nand2tetris": "Nand2Tetris", "reactjs": "React", "typescript": "TypeScript",
    "promptengineering": "prompt engineering", "compilerdesign": "compiler design",
    "devtools": "dev tools", "agentic-rag": "agentic RAG", "agentic-ai": "agentic AI",
    "ai-agents": "AI agents", "ai-development": "AI development",
    "google-ai-studio": "Google AI Studio",
}


class ContentError(Exception):
    """A post, page or section definition is invalid."""


# --------------------------------------------------------------------- text
def split_front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER.match(text)
    if not match:
        raise ContentError("missing front matter block")
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ContentError("front matter is not a mapping")
    return meta, text[match.end():]


def _scalar(value) -> str:
    if isinstance(value, datetime):
        value = iso(value)
    return json.dumps(value, ensure_ascii=False)


def dump_front_matter(meta: dict) -> str:
    keys = [k for k in KEY_ORDER if k in meta] + sorted(k for k in meta if k not in KEY_ORDER)
    lines = ["---"]
    for key in keys:
        value = meta[key]
        if value is None:
            continue
        lines.append(f"{key}: {_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def compose(meta: dict, body: str) -> str:
    return dump_front_matter(meta) + "\n" + body.lstrip("\n")


def set_key(text: str, key: str, value) -> str:
    """Set (or with value=None, remove) one top-level key, touching nothing else."""
    match = FRONT_MATTER.match(text)
    if not match:
        raise ContentError("missing front matter block")
    block = match.group(1)
    line = re.compile(rf"^{re.escape(key)}:.*(?:\r?\n|$)", re.M)
    if value is None:
        new_block = line.sub("", block).rstrip("\n")
    elif line.search(block):
        new_block = line.sub(lambda m: f"{key}: {_scalar(value)}" + ("\n" if m.group(0).endswith("\n") else ""), block, count=1)
    else:
        new_block = block.rstrip("\n") + f"\n{key}: {_scalar(value)}"
    start, end = match.span(1)
    return text[:start] + new_block + text[end:]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", text) or "post"


def tag_slug(tag: str) -> str:
    return slugify(tag)


def tag_label(tag: str) -> str:
    return TAG_LABELS.get(tag, tag.replace("-", " "))


# -------------------------------------------------------------------- dates
def parse_date(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    text = dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return text


def date_label(dt: datetime) -> str:
    local = dt.astimezone(cfg.DISPLAY_TZ)
    return f"{local.day} {MONTHS[local.month - 1]} {local.year}"


def date_ymd(dt: datetime) -> str:
    return dt.astimezone(cfg.DISPLAY_TZ).strftime("%Y-%m-%d")


# ------------------------------------------------------------------ loading
def load_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        meta, body = split_front_matter(text)
    except (ContentError, yaml.YAMLError) as exc:
        raise ContentError(f"{path.name}: {exc}") from exc
    post = {"path": path, "meta": meta, "body": body}
    post["slug"] = str(meta.get("slug") or path.stem)
    post["title"] = str(meta.get("title") or "").strip()
    post["section"] = meta.get("section") or ""
    post["tags"] = [str(t).strip() for t in (meta.get("tags") or []) if str(t).strip()]
    post["draft"] = bool(meta.get("draft"))
    post["description"] = str(meta.get("description") or "").strip()
    if meta.get("datePublished"):
        post["date"] = parse_date(meta["datePublished"])
    else:
        post["date"] = None
    post["updated"] = parse_date(meta["dateUpdated"]) if meta.get("dateUpdated") else None
    return post


def load_posts(directory: Path = CONTENT) -> list[dict]:
    if not directory.exists():
        return []
    # Files starting with "_" (e.g. content/drafts/_REPORT.md) are notes, not posts.
    posts = [load_file(p) for p in sorted(directory.glob("*.md")) if not p.name.startswith("_")]
    return sorted(posts, key=lambda p: (p["date"] or datetime.max.replace(tzinfo=timezone.utc)), reverse=True)


def load_sections(path: Path = SECTIONS_FILE) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ContentError(f"{path.name}: expected a list of sections")
    sections = []
    for raw in data:
        if not isinstance(raw, dict) or not raw.get("slug") or not raw.get("label"):
            raise ContentError(f"{path.name}: every section needs slug and label: {raw!r}")
        section = {
            "slug": str(raw["slug"]),
            "label": str(raw["label"]),
            "nav": raw.get("nav", "primary"),
            "description": str(raw.get("description") or "").strip(),
            "series": bool(raw.get("series")),
            "page": raw.get("page"),
        }
        sections.append(section)
    return sections


def load_page(relpath: str) -> dict:
    path = CONTENT / relpath
    if not path.exists():
        raise ContentError(f"sections.yml: page file {relpath} does not exist")
    return load_file(path)


# ------------------------------------------------------------------- images
def is_photo_like(im) -> bool:
    """Photos and illustrations spread across many colours; screenshots and
    diagrams are dominated by a few flat ones. Measured on a small
    nearest-neighbour thumbnail so anti-aliasing does not blur the answer."""
    rgb = (im.convert("RGBA") if im.mode in ("P", "PA", "LA") else im).convert("RGB")
    w, h = rgb.size
    thumb = rgb.resize((256, max(1, round(h * 256 / w))), 0)  # 0 = NEAREST
    pixels = getattr(thumb, "get_flattened_data", None) or thumb.getdata  # getdata: Pillow < 12.1
    counts = Counter(pixels())
    top = sum(n for _, n in counts.most_common(16))
    return top / (thumb.width * thumb.height) < 0.5


def optimize_image(data: bytes, ext: str) -> tuple[bytes, str]:
    """Return (bytes, extension) for an original image, re-encoded when that
    makes it meaningfully smaller or it is wider than MAX_ORIGINAL_WIDTH."""
    from PIL import Image, ImageOps

    ext = ext.lower().lstrip(".")
    if ext in ("svg", "gif"):
        return data, ext  # vector, or possibly animated: leave alone
    with Image.open(io.BytesIO(data)) as im:
        photo = im.format == "JPEG" or is_photo_like(im)
        im = ImageOps.exif_transpose(im)
        resized = im.width > cfg.MAX_ORIGINAL_WIDTH
        if resized:
            im = im.resize((cfg.MAX_ORIGINAL_WIDTH, round(im.height * cfg.MAX_ORIGINAL_WIDTH / im.width)),
                           Image.LANCZOS)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA" if "transparency" in im.info or im.mode in ("LA", "PA", "P") else "RGB")
        out = io.BytesIO()
        if photo:
            im.save(out, "WEBP", quality=cfg.PHOTO_QUALITY, method=6)
        else:
            im.save(out, "WEBP", lossless=True, quality=80, method=4)
    encoded = out.getvalue()
    if resized or len(encoded) < 0.9 * len(data):
        return encoded, "webp"
    return data, ext


def optimize_folder(root: Path, slugs: list[str] | None = None, dry_run: bool = False) -> list[tuple[str, int, int]]:
    """Optimise root/img/<slug>/* and point root/*.md at any renamed files.

    Returns (relative path, bytes before, bytes after) for every file changed.
    """
    changed = []
    img_root = root / "img"
    if not img_root.exists():
        return changed
    folders = [img_root / s for s in slugs] if slugs else sorted(p for p in img_root.iterdir() if p.is_dir())
    renames: dict[str, str] = {}
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(p for p in folder.iterdir() if p.is_file()):
            data = path.read_bytes()
            try:
                new_data, ext = optimize_image(data, path.suffix)
            except (OSError, ValueError, SyntaxError):
                continue  # not an image Pillow can read (or corrupt): leave it as it is
            if new_data is data:
                continue
            target = path.with_suffix("." + ext)
            if target != path and target.exists():
                continue  # a file with the target name already exists; leave both
            rel_old = f"img/{folder.name}/{path.name}"
            rel_new = f"img/{folder.name}/{target.name}"
            changed.append((rel_old, len(data), len(new_data)))
            if dry_run:
                continue
            target.write_bytes(new_data)
            if target != path:
                path.unlink()
                renames[rel_old] = rel_new
    if renames and not dry_run:
        for md in root.glob("*.md"):
            text = md.read_text(encoding="utf-8")
            new = text
            for old, rel in renames.items():
                new = new.replace(old, rel)
            if new != text:
                md.write_text(new, encoding="utf-8")
    return changed


# --------------------------------------------------------------- validation
def validate(sections: list[dict], posts: list[dict]) -> list[str]:
    """Every rule the build depends on. Returns human-readable errors."""
    errors: list[str] = []
    by_slug = {}
    for s in sections:
        if s["slug"] in by_slug:
            errors.append(f"sections.yml: duplicate section slug '{s['slug']}'")
        by_slug[s["slug"]] = s
        if s["nav"] not in ("primary", "more"):
            errors.append(f"sections.yml: section '{s['slug']}' nav must be 'primary' or 'more'")
        if s["slug"] in RESERVED_SLUGS or slugify(s["slug"]) != s["slug"]:
            errors.append(f"sections.yml: section slug '{s['slug']}' is reserved or not URL-safe")

    seen_posts: dict[str, Path] = {}
    series_orders: dict[str, dict[int, str]] = {}
    for post in posts:
        name = post["path"].name
        slug = post["slug"]
        if post["draft"]:
            errors.append(f"{name}: has draft: true but lives in content/blog/ (use `blog.py unpublish`)")
        if not post["title"]:
            errors.append(f"{name}: missing title")
        if post["date"] is None:
            errors.append(f"{name}: missing datePublished")
        if slugify(slug) != slug or slug in RESERVED_SLUGS:
            errors.append(f"{name}: slug '{slug}' is reserved or not URL-safe")
        if slug in seen_posts:
            errors.append(f"{name}: slug '{slug}' also used by {seen_posts[slug].name}")
        seen_posts[slug] = post["path"]
        if slug in by_slug:
            errors.append(f"{name}: slug '{slug}' collides with a section URL")
        section = by_slug.get(post["section"])
        if not post["section"]:
            errors.append(f"{name}: missing section (one of: {', '.join(s['slug'] for s in sections if not s['page'])})")
        elif section is None:
            errors.append(f"{name}: unknown section '{post['section']}'")
        elif section["page"]:
            errors.append(f"{name}: section '{post['section']}' is a page, not a post section")
        elif section["series"]:
            order = post["meta"].get("seriesOrder")
            if not isinstance(order, int):
                errors.append(f"{name}: section '{post['section']}' is a series; set seriesOrder (integer)")
            else:
                taken = series_orders.setdefault(post["section"], {})
                if order in taken:
                    errors.append(f"{name}: seriesOrder {order} already used by {taken[order]}")
                taken[order] = name
    return errors


def load_all() -> tuple[list[dict], list[dict]]:
    """Load and validate; raise ContentError listing every problem at once."""
    sections = load_sections()
    posts = load_posts()
    errors = validate(sections, posts)
    if errors:
        raise ContentError("\n".join(errors))
    return sections, posts
