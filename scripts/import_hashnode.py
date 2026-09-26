#!/usr/bin/env python3
"""Import the Hashnode GitHub backup into content/blog/ (and drafts locally).

Repeatable and idempotent: run it again after the backup changes and it only
writes what is new. A post that already exists locally and differs from the
backup is left alone unless --overwrite is given, so edits made here are never
silently replaced. An existing `section:` / `seriesOrder:` is always kept.

What it changes in a post body, and nothing else:
  - CRLF line endings become LF
  - Hashnode's ` align="center"` inside image syntax is removed
  - `class` attributes on <mark> are removed (Tailwind classes from the editor)
  - links to this blog's Hashnode posts become /blog/<slug>/ when the slug exists
  - remote images are downloaded (and optimised, see blog_lib.optimize_image)
    and referenced by a relative path

Outputs:
  content/blog/<slug>.md, content/blog/img/<slug>/*        published posts
  content/drafts/<slug>.md, content/drafts/img/<slug>/*    drafts (gitignored)
  migration/report.md, migration/hashnode-url-map.csv      committed
  content/drafts/_REPORT.md                                 draft details (gitignored)

Usage:
    python3 scripts/import_hashnode.py [BACKUP_DIR] [--overwrite] [--no-download]
With no BACKUP_DIR the backup repository is cloned into a temporary directory.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import io
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blog_config as cfg  # noqa: E402
from blog_lib import (  # noqa: E402
    CONTENT, DRAFTS, MIGRATION, compose, iso, load_file, optimize_image, parse_date, slugify,
)
from update_writing import _summarize  # noqa: E402

BACKUP_URL = "https://github.com/Sukalyan2003/hashnode-backup.git"
USER_AGENT = "Mozilla/5.0 (compatible; engineering-tales-import)"
FORMATS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}

IMAGE_MD = re.compile(r"!\[([^\]]*)\]\(\s*<?([^\s)>]+)>?((?:\s+\"[^\"]*\")?)\s*\)")
ALIGN_ATTR = re.compile(r"(!\[[^\]]*\]\([^)\s]+)\s+align=\"[^\"]*\"(\))")
MARK_CLASS = re.compile(r"<mark\s+class=\"[^\"]*\"\s*>")
OWN_LINK = re.compile(rf"https?://{re.escape(cfg.HASHNODE_HOST)}/([a-z0-9-]+)/?(?![\w/.-])")
# Hashnode's editor also links posts by id: https://hashnode.com/post/<cuid>
CUID_LINK = re.compile(r"https?://(?:www\.)?hashnode\.com/post/([a-z0-9]+)/?(?![\w/.-])")
TYPOGRAPHIC = re.compile(r"[ -⁯€™ -ÿ]")


# ------------------------------------------------------------------- source
SOURCE_FM = re.compile(r"\A---\n(.*?)\n---[ \t]*\n?", re.S)
SOURCE_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_]*):[ \t]*(.*)$")


def parse_source_front_matter(block: str) -> dict:
    """Hashnode's export is YAML-like but not YAML: quoted values can contain
    unescaped quotes (`"… "vibecoding" …"`) and line breaks. Read it by line:
    a `key:` starts a field, anything else continues the previous one, and one
    pair of surrounding quotes is removed."""
    fields: dict[str, list[str]] = {}
    key = None
    for line in block.split("\n"):
        match = SOURCE_KEY.match(line)
        if match:
            key = match.group(1)
            fields[key] = [match.group(2)]
        elif key is not None:
            fields[key].append(line)
    meta = {}
    for key, parts in fields.items():
        value = "\n".join(parts).strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        meta[key] = re.sub(r"\s+", " ", value).strip()
    return meta


def read_source(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = SOURCE_FM.match(text)
    if not match:
        raise ValueError(f"{path.name}: no front matter")
    return parse_source_front_matter(match.group(1)), text[match.end():]


def git_dates_updated(repo: Path, name: str, published) -> str | None:
    """Latest backup 'update post' commit that changed the body text.

    The backup has no dateUpdated field. Its git history records each sync,
    so a sync that actually changed the prose is the best available evidence
    of an edit. Whitespace-only and metadata-only changes do not count.
    """
    try:
        log = subprocess.run(
            ["git", "-C", str(repo), "log", "--format=%H%x09%aI%x09%s", "--", name],
            check=True, capture_output=True, text=True,
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    def body_at(ref: str) -> str | None:
        out = subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{name}"],
                             capture_output=True, text=True)
        if out.returncode != 0:
            return None
        text = out.stdout.replace("\r\n", "\n")
        match = SOURCE_FM.match(text)
        return re.sub(r"\s+", "", text[match.end():] if match else text)

    for line in log:  # newest first
        sha, when, subject = line.split("\t", 2)
        if not subject.startswith("update post"):
            continue
        after, before = body_at(sha), body_at(f"{sha}^")
        if after is not None and before is not None and after != before:
            date = parse_date(when)
            return iso(date) if date > published else None
    return None


# ------------------------------------------------------------------- images
def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for _ in range(2):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
    raise RuntimeError(str(last))


def sniff_extension(data: bytes) -> str:
    head = data[:512].lstrip()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2048]):
        return "svg"
    with Image.open(io.BytesIO(data)) as img:
        fmt = img.format
    if fmt not in FORMATS:
        raise RuntimeError(f"unsupported image format {fmt}")
    return FORMATS[fmt]


class Localizer:
    """Downloads remote images next to the post and remembers the result."""

    def __init__(self, base: Path, enabled: bool):
        self.base = base
        self.enabled = enabled
        self.failures: list[tuple[str, str, str]] = []

    def __call__(self, slug: str, url: str) -> str:
        if not re.match(r"https?://", url):
            return url
        if not self.enabled:
            return url
        folder = self.base / "img" / slug
        stem = hashlib.sha1(url.encode()).hexdigest()[:12]
        existing = sorted(folder.glob(f"{stem}.*")) if folder.exists() else []
        if existing:
            return f"img/{slug}/{existing[0].name}"
        try:
            data = download(url)
            data, ext = optimize_image(data, sniff_extension(data))
        except Exception as exc:  # noqa: BLE001 - reported, remote URL kept
            self.failures.append((slug, url, str(exc)))
            return url
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{stem}.{ext}").write_bytes(data)
        return f"img/{slug}/{stem}.{ext}"


# --------------------------------------------------------------- conversion
def convert_body(body: str, slug: str, known: set[str], localize, cuids: dict | None = None) -> tuple[str, dict]:
    notes = {"unresolved_links": [], "images": 0, "images_no_alt": 0, "remote_hosts": set()}
    body = ALIGN_ATTR.sub(r"\1\2", body)
    body = MARK_CLASS.sub("<mark>", body)

    def link(match: re.Match) -> str:
        target = match.group(1)
        if target in known:
            return f"/blog/{target}/"
        notes["unresolved_links"].append(target)
        return match.group(0)

    body = OWN_LINK.sub(link, body)

    def cuid_link(match: re.Match) -> str:
        target = (cuids or {}).get(match.group(1))
        if target:
            return f"/blog/{target}/"
        notes["unresolved_links"].append(f"hashnode.com/post/{match.group(1)}")
        return match.group(0)

    body = CUID_LINK.sub(cuid_link, body)

    def image(match: re.Match) -> str:
        alt, url, title = match.groups()
        notes["images"] += 1
        if not alt.strip():
            notes["images_no_alt"] += 1
        host = re.match(r"https?://([^/]+)", url)
        if host:
            notes["remote_hosts"].add(host.group(1))
        return f"![{alt}]({localize(slug, url)}{title})"

    body = IMAGE_MD.sub(image, body)
    return body, notes


def plain_text(body: str) -> str:
    text = re.sub(r"^```.*?^```", " ", body, flags=re.S | re.M)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s{0,3}(#{1,6}|>|[*+-]|\d+\.)\s+", "", text, flags=re.M)
    text = re.sub(r"[*_`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def excerpt(body: str) -> str:
    return _summarize(plain_text(body))


def build_meta(src: dict, slug: str, body: str, localize, *, draft: bool, cuid: str) -> dict:
    meta: dict = {"title": str(src.get("title") or "").strip(), "slug": slug}
    if draft:
        meta["draft"] = True
    if src.get("datePublished"):
        meta["datePublished"] = iso(parse_date(src["datePublished"]))
    seo = str(src.get("seoDescription") or "").strip()
    if seo:
        meta["description"] = seo
    elif body.strip():
        meta["description"] = excerpt(body)
        meta["descriptionSource"] = "excerpt"
    if src.get("seoTitle"):
        meta["seoTitle"] = str(src["seoTitle"]).strip()
    tags = src.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    meta["tags"] = [t for t in (tags or []) if t]
    if src.get("cover"):
        meta["cover"] = localize(slug, str(src["cover"]).strip())
        meta["coverAlt"] = ""
    if src.get("ogImage"):
        meta["ogImage"] = localize(slug, str(src["ogImage"]).strip())
    meta["hashnode"] = {"cuid": cuid}
    if not draft:
        meta["hashnode"]["url"] = f"https://{cfg.HASHNODE_HOST}/{slug}"
    return meta


def write_if_changed(path: Path, text: str, overwrite: bool) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return "written"
    if path.read_text(encoding="utf-8") == text:
        return "unchanged"
    if not overwrite:
        return "skipped (local copy differs; --overwrite replaces it)"
    path.write_text(text, encoding="utf-8")
    return "overwritten"


def keep_local_placement(path: Path, meta: dict, mapped: dict) -> None:
    """An existing post's section wins over the migration map."""
    placement = dict(mapped)
    if path.exists():
        try:
            local = load_file(path)["meta"]
            for key in ("section", "seriesOrder"):
                if key in local:
                    placement[key] = local[key]
        except Exception:  # noqa: BLE001 - unreadable local file: fall back to the map
            pass
    for key in ("section", "seriesOrder"):
        if key in placement:
            meta[key] = placement[key]


def non_latin(text: str) -> list[str]:
    chars = {c for c in text if ord(c) > 0x7F and not TYPOGRAPHIC.match(c)}
    return sorted(chars)


def likely_same_post(a: str, b: str) -> bool:
    """Titles that differ only in a part number are different posts."""
    return re.findall(r"\d+", a) == re.findall(r"\d+", b)


def suggest(old: str, known: set[str]) -> str | None:
    hits = [k for k in known if k in old or old in k]
    return hits[0] if len(hits) == 1 else None


# -------------------------------------------------------------------- main
def run(backup: Path, overwrite: bool, fetch: bool) -> int:
    files = sorted(backup.glob("*.md"))
    published = [f for f in files if not f.name.startswith("draft-")]
    drafts = [f for f in files if f.name.startswith("draft-")]
    section_map = yaml.safe_load((MIGRATION / "section-map.yml").read_text(encoding="utf-8")) or {}

    sources = []
    for path in published:
        meta, body = read_source(path)
        sources.append((path, meta, body))
    known = {str(m["slug"]) for _, m, _ in sources}
    cuids = {str(m["cuid"]): str(m["slug"]) for _, m, _ in sources if m.get("cuid")}

    post_localizer = Localizer(CONTENT, fetch)
    rows, report = [], []
    for path, src, body in sources:
        slug = str(src["slug"])
        new_body, notes = convert_body(body, slug, known, post_localizer, cuids)
        meta = build_meta(src, slug, new_body, post_localizer, draft=False, cuid=str(src.get("cuid", "")))
        updated = git_dates_updated(backup, path.name, parse_date(src["datePublished"]))
        if updated:
            meta["dateUpdated"] = updated
        target = CONTENT / f"{slug}.md"
        keep_local_placement(target, meta, section_map.get(slug, {}))
        status = write_if_changed(target, compose(meta, new_body), overwrite)
        rows.append((slug, meta, notes, status, path, body))

    draft_localizer = Localizer(DRAFTS, fetch)
    published_titles = {slug: m["title"] for slug, m, *_ in rows}
    draft_rows = []
    used: set[str] = set()
    for path in drafts:
        src, body = read_source(path)
        title = str(src.get("title") or "").strip()
        slug = str(src.get("slug") or slugify(title))
        base, n = slug, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        new_body, notes = convert_body(body, slug, known, draft_localizer, cuids)
        cuid = path.stem.removeprefix("draft-")
        meta = build_meta(src, slug, new_body, draft_localizer, draft=True, cuid=cuid)
        status = write_if_changed(DRAFTS / f"{slug}.md", compose(meta, new_body), overwrite)
        flags = []
        if slug in known:
            flags.append(f"slug collides with published post `{slug}`")
        for pslug, ptitle in published_titles.items():
            if not likely_same_post(title, ptitle):
                continue
            ratio = difflib.SequenceMatcher(None, title.lower(), ptitle.lower()).ratio()
            if ratio >= 0.75:
                flags.append(f"likely stale duplicate of published `{pslug}` (title similarity {ratio:.2f})")
                break
        if len(body.strip()) < 300:
            flags.append("stub (under 300 characters)")
        draft_rows.append((slug, title, status, flags, len(body.strip())))

    write_reports(rows, draft_rows, known, post_localizer.failures, draft_localizer.failures)
    written = sum(1 for r in rows if r[3] in ("written", "overwritten"))
    skipped = [r[0] for r in rows if r[3].startswith("skipped")]
    print(f"posts: {len(rows)} ({written} written, {len(skipped)} skipped as locally modified)")
    print(f"drafts: {len(draft_rows)} -> {DRAFTS.relative_to(CONTENT.parent.parent)}/ (gitignored)")
    failures = post_localizer.failures + draft_localizer.failures
    if failures:
        print(f"image downloads failed: {len(failures)} (see migration/report.md)")
    for slug in skipped:
        print(f"  skipped: {slug}")
    return 0


def write_reports(rows, draft_rows, known, failures, draft_failures) -> None:
    MIGRATION.mkdir(exist_ok=True)
    with (MIGRATION / "hashnode-url-map.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["old_hashnode_url", "new_url", "title", "hashnode_cuid"])
        for slug, meta, *_ in sorted(rows, key=lambda r: r[1]["datePublished"]):
            writer.writerow([meta["hashnode"]["url"], f"{cfg.SITE_URL}/blog/{slug}/",
                             meta["title"], meta["hashnode"]["cuid"]])

    lines = [
        "# Hashnode migration report",
        "",
        "Generated by `scripts/import_hashnode.py`. Re-running the importer rewrites this file.",
        "",
        "## Summary",
        "",
        f"- Published posts imported: **{len(rows)}**",
        f"- Drafts imported locally (gitignored `content/drafts/`): **{len(draft_rows)}**. "
        "Details are in `content/drafts/_REPORT.md`, which is not committed.",
        f"- Image downloads that failed (remote URL kept): **{len(failures)}**",
        f"- Hashnode URL map: `migration/hashnode-url-map.csv` ({len(rows)} rows)",
        "",
        "## Data the backup does not contain (nothing migrated, nothing invented)",
        "",
        "- **Likes / reactions, comments, view counts**: not in the backup. Historical engagement stays on Hashnode.",
        "- **Series**: no series field. Sections and the Unsung Bits order come from `migration/section-map.yml`, "
        "which the author approved.",
        "- **Last-updated dates**: no field. `dateUpdated` is the date of the latest backup sync that changed the "
        "post's prose (whitespace- and metadata-only syncs ignored). It is a sync date, not an edit timestamp "
        "recorded by Hashnode.",
        "- **Cover alt text**: not in the backup. Covers are rendered as decorative (`alt=\"\"`) next to the title.",
        "",
        "## Normalisation applied",
        "",
        "- CRLF line endings converted to LF.",
        "- ` align=\"…\"` removed from Hashnode image syntax (not valid Markdown).",
        "- `class` attributes removed from `<mark>` (Tailwind classes from the Hashnode editor).",
        f"- Links to `{cfg.HASHNODE_HOST}/<slug>` and `hashnode.com/post/<id>` rewritten to `/blog/<slug>/` "
        "when the post is in the backup.",
        "- Remote images downloaded to `content/blog/img/<slug>/` (file named by a hash of the source URL; "
        "extension from the actual file format). Photo-like images are stored as quality-90 WebP, screenshots "
        "and diagrams as lossless WebP when smaller, all capped at 2400px wide, metadata removed.",
        "- Titles trimmed of surrounding whitespace (one title had a trailing line break).",
        "",
        "## Per-post issues",
        "",
    ]
    any_issue = False
    for slug, meta, notes, status, _path, body in sorted(rows, key=lambda r: r[1]["datePublished"]):
        issues = []
        if notes["images_no_alt"]:
            issues.append(f"{notes['images_no_alt']} of {notes['images']} inline images have no alt text "
                          "(left empty; add alt text by hand)")
        for old in dict.fromkeys(notes["unresolved_links"]):
            hint = suggest(old, known)
            guess = f" - possible match `/blog/{hint}/` (unverified)" if hint else " - no confident match"
            issues.append(f"links to `{old}` on Hashnode, which is not a post in the backup; link left pointing at Hashnode{guess}")
        if not meta["tags"]:
            issues.append("no tags")
        if re.search(r"\$\$|\$[^\s$\d][^$\n]*?[^\s$]\$", body):
            issues.append("contains `$…$` math; now rendered as MathML at build time - check it reads correctly")
        if any("duckduckgo" in h for h in notes["remote_hosts"]):
            issues.append("an image was hot-linked through a DuckDuckGo image proxy; it was downloaded, "
                          "but its original source and licence are unknown - verify or replace")
        chars = non_latin(meta["title"] + body)
        if chars:
            sample = "".join(chars[:24])
            issues.append(f"uses characters outside the self-hosted font subsets ({len(chars)} distinct, e.g. "
                          f"`{sample}`); they render in the fallback serif")
        if meta.get("descriptionSource") == "excerpt":
            issues.append("no SEO description in the backup; description is an excerpt of the opening text")
        if slug == "what-comes-after-cs50x-discover-cs50-ai-2":
            issues.append("title looks like a duplicate of `what-comes-after-cs50x-discover-cs50-ai`; "
                          "the body differs (it is part 2) - review the title")
        if status.startswith("skipped"):
            issues.append(f"not updated: {status}")
        if issues:
            any_issue = True
            lines.append(f"### `{slug}`")
            lines.append("")
            lines.extend(f"- {i}" for i in issues)
            lines.append("")
    if not any_issue:
        lines.append("None.")
        lines.append("")

    if failures:
        lines += ["## Failed image downloads", ""]
        lines += [f"- `{slug}`: {url} ({err})" for slug, url, err in failures]
        lines.append("")

    lines += ["## Old Hashnode URL -> new URL", "",
              "Set each Hashnode post's *Original URL* (canonical) to the new URL. Same data as the CSV.", "",
              "| Old | New |", "|---|---|"]
    for slug, meta, *_ in sorted(rows, key=lambda r: r[1]["datePublished"]):
        lines.append(f"| {meta['hashnode']['url']} | {cfg.SITE_URL}/blog/{slug}/ |")
    (MIGRATION / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    DRAFTS.mkdir(parents=True, exist_ok=True)
    dl = ["# Drafts (local only - this folder is gitignored)", "",
          "Publish one with `python3 scripts/blog.py publish <slug> --section <section>`.", "",
          "| Slug | Title | Size | Flags | Import |", "|---|---|---|---|---|"]
    for slug, title, status, flags, size in draft_rows:
        dl.append(f"| `{slug}` | {title} | {size} chars | {'; '.join(flags) or '-'} | {status} |")
    if draft_failures:
        dl += ["", "## Failed image downloads", ""]
        dl += [f"- `{slug}`: {url} ({err})" for slug, url, err in draft_failures]
    (DRAFTS / "_REPORT.md").write_text("\n".join(dl) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("backup", nargs="?", type=Path, help="local clone of the Hashnode backup")
    parser.add_argument("--overwrite", action="store_true", help="replace locally modified posts")
    parser.add_argument("--no-download", action="store_true", help="keep remote image URLs")
    args = parser.parse_args(argv)

    if args.backup:
        return run(args.backup.resolve(), args.overwrite, not args.no_download)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "--quiet", BACKUP_URL, tmp], check=True)
        return run(Path(tmp), args.overwrite, not args.no_download)


if __name__ == "__main__":
    raise SystemExit(main())
