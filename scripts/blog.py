#!/usr/bin/env python3
"""Manage the blog: sections, drafts, publishing, building.

    python3 scripts/blog.py sections                     list sections and post counts
    python3 scripts/blog.py drafts                       list local drafts
    python3 scripts/blog.py new <section> "Title"        start a draft in content/drafts/
    python3 scripts/blog.py publish <slug> [--section S] [--order N] [--date ISO]
                                                          move a draft into content/blog/
    python3 scripts/blog.py unpublish <slug>             move a post back to drafts
    python3 scripts/blog.py move <slug> <section> [--order N]
                                                          change a post's section
    python3 scripts/blog.py optimize [--dry-run]         shrink original images in content/
    python3 scripts/blog.py import [BACKUP_DIR] [--overwrite]
                                                          re-run the Hashnode importer
    python3 scripts/blog.py build | check | preview      generate / verify / preview with drafts

Edits touch only the front-matter keys they are about; the body is never
rewritten. Run `build` afterwards (or let CI do it) to regenerate /blog.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blog_lib import (  # noqa: E402
    CONTENT, DRAFTS, ROOT, ContentError, compose, iso, load_file, load_posts,
    load_sections, optimize_folder, set_key, slugify, validate,
)


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def post_sections(sections) -> dict:
    return {s["slug"]: s for s in sections if not s["page"]}


def find(directory: Path, slug: str) -> Path | None:
    path = directory / f"{slug}.md"
    if path.exists():
        return path
    for candidate in directory.glob("*.md"):
        if load_file(candidate)["slug"] == slug:
            return candidate
    return None


def move_images(slug: str, src_root: Path, dst_root: Path) -> None:
    src = src_root / "img" / slug
    if not src.exists():
        return
    dst = dst_root / "img" / slug
    if dst.exists():
        raise ContentError(f"{dst.relative_to(ROOT)} already exists")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


MERMAID_FENCE = re.compile(r"^(`{3,}|~{3,})[ \t]*mermaid\b[^\n]*\n(.*?)^\1[ \t]*$", re.M | re.S)


def move_diagrams(body: str, src_root: Path, dst_root: Path) -> None:
    """Carry a post's cached Mermaid renders along, so publishing needs no Node."""
    from build_blog import Diagrams  # heavier imports, only when needed
    for match in MERMAID_FENCE.finditer(body):
        for theme in ("paper", "press"):
            name = f"{Diagrams.key(match.group(2), theme)}-{theme}.svg"
            src = src_root / "diagrams" / name
            if src.exists():
                (dst_root / "diagrams").mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst_root / "diagrams" / name))


def check_placement(sections, section: str, order, posts, exclude: str = "") -> str | None:
    available = post_sections(sections)
    if section not in available:
        return f"unknown section '{section}' (choose from: {', '.join(available)})"
    if available[section]["series"]:
        if order is None:
            return f"'{section}' is a series; pass --order N"
        taken = [p["slug"] for p in posts if p["section"] == section
                 and p["meta"].get("seriesOrder") == order and p["slug"] != exclude]
        if taken:
            return f"seriesOrder {order} is already used by {taken[0]}"
    return None


# ------------------------------------------------------------------ commands
def cmd_sections(args) -> int:
    sections = load_sections(CONTENT / "sections.yml")
    posts = load_posts(CONTENT)
    for s in sections:
        members = [p for p in posts if p["section"] == s["slug"]]
        kind = "page" if s["page"] else ("series" if s["series"] else "section")
        print(f"{s['slug']:<22} {s['label']:<22} {s['nav']:<8} {kind:<8} {'' if s['page'] else len(members)}")
        if s["series"]:
            for p in sorted(members, key=lambda p: p["meta"].get("seriesOrder", 0)):
                print(f"{'':<24}{p['meta'].get('seriesOrder', '?'):>3}  {p['slug']}")
    known = {s["slug"] for s in sections}
    orphans = [p["slug"] for p in posts if p["section"] not in known]
    if orphans:
        print("\nposts without a valid section:\n  " + "\n  ".join(orphans))
    errors = validate(sections, posts)
    if errors:
        print("\nproblems:\n  " + "\n  ".join(errors))
        return 1
    return 0


def cmd_drafts(args) -> int:
    drafts = load_posts(DRAFTS)
    if not drafts:
        print("no drafts in content/drafts/")
        return 0
    published = {p["slug"] for p in load_posts(CONTENT)}
    for d in sorted(drafts, key=lambda d: d["slug"]):
        flags = []
        if d["slug"] in published:
            flags.append("slug already published")
        if len(d["body"].strip()) < 300:
            flags.append("stub")
        print(f"{d['slug']:<60} {d['section'] or '-':<22} {len(d['body'].strip()):>6} chars  {', '.join(flags)}")
    return 0


def cmd_new(args) -> int:
    sections = load_sections(CONTENT / "sections.yml")
    if args.section not in post_sections(sections):
        return fail(f"unknown section '{args.section}'")
    slug = args.slug or slugify(args.title)
    if find(CONTENT, slug) or find(DRAFTS, slug):
        return fail(f"slug '{slug}' already exists (pass --slug to choose another)")
    meta = {"title": args.title, "slug": slug, "section": args.section, "draft": True,
            "description": "", "tags": [], "cover": None}
    DRAFTS.mkdir(parents=True, exist_ok=True)
    path = DRAFTS / f"{slug}.md"
    path.write_text(compose(meta, "Write here.\n"), encoding="utf-8")
    print(f"created {path.relative_to(ROOT)}")
    print(f"images go in {(DRAFTS / 'img' / slug).relative_to(ROOT)}/ and are referenced as img/{slug}/<file>")
    return 0


def cmd_publish(args) -> int:
    sections = load_sections(CONTENT / "sections.yml")
    posts = load_posts(CONTENT)
    src = find(DRAFTS, args.slug)
    if not src:
        return fail(f"no draft '{args.slug}' in content/drafts/")
    draft = load_file(src)
    slug = draft["slug"]
    if find(CONTENT, slug):
        return fail(f"a published post already uses slug '{slug}'; change the draft's slug first")
    section = args.section or draft["section"]
    if not section:
        return fail("draft has no section; pass --section")
    order = args.order if args.order is not None else draft["meta"].get("seriesOrder")
    problem = check_placement(sections, section, order, posts)
    if problem:
        return fail(problem)
    if not draft["title"]:
        return fail("draft has no title")

    text = src.read_text(encoding="utf-8")
    date = args.date or iso(datetime.now(timezone.utc))
    text = set_key(text, "draft", None)
    text = set_key(text, "section", section)
    if order is not None:
        text = set_key(text, "seriesOrder", order)
    text = set_key(text, "datePublished", date)
    dst = CONTENT / f"{slug}.md"
    move_images(slug, DRAFTS, CONTENT)
    move_diagrams(draft["body"], DRAFTS, CONTENT)
    dst.write_text(text, encoding="utf-8")
    src.unlink()
    report_optimized(optimize_folder(CONTENT, [slug]))
    errors = validate(sections, load_posts(CONTENT))
    print(f"published {dst.relative_to(ROOT)} ({section}, {date})")
    if errors:
        print("warnings:\n  " + "\n  ".join(errors))
    print("next: python3 scripts/blog.py build")
    return 0


def cmd_unpublish(args) -> int:
    src = find(CONTENT, args.slug)
    if not src:
        return fail(f"no published post '{args.slug}'")
    post = load_file(src)
    if find(DRAFTS, post["slug"]):
        return fail(f"a draft named '{post['slug']}' already exists")
    DRAFTS.mkdir(parents=True, exist_ok=True)
    text = set_key(src.read_text(encoding="utf-8"), "draft", True)
    move_images(post["slug"], CONTENT, DRAFTS)
    move_diagrams(post["body"], CONTENT, DRAFTS)
    (DRAFTS / src.name).write_text(text, encoding="utf-8")
    src.unlink()
    print(f"moved to content/drafts/{src.name}")
    print(f"warning: {post['slug']} will 404 at /blog/{post['slug']}/ after the next build; "
          "external links and the Hashnode canonical still point there")
    return 0


def cmd_move(args) -> int:
    sections = load_sections(CONTENT / "sections.yml")
    posts = load_posts(CONTENT)
    src = find(CONTENT, args.slug) or find(DRAFTS, args.slug)
    if not src:
        return fail(f"no post or draft '{args.slug}'")
    post = load_file(src)
    order = args.order if args.order is not None else post["meta"].get("seriesOrder")
    target = post_sections(sections).get(args.section)
    if target and not target["series"]:
        order = None
    problem = check_placement(sections, args.section, order, posts, exclude=post["slug"])
    if problem:
        return fail(problem)
    text = set_key(src.read_text(encoding="utf-8"), "section", args.section)
    text = set_key(text, "seriesOrder", order)
    src.write_text(text, encoding="utf-8")
    print(f"{post['slug']}: section -> {args.section}" + (f", seriesOrder {order}" if order is not None else ""))
    return 0


def report_optimized(changed) -> None:
    for rel, before, after in changed:
        print(f"  optimised {rel}: {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB")


def cmd_optimize(args) -> int:
    total_before = total_after = 0
    for root in (CONTENT, DRAFTS):
        changed = optimize_folder(root, dry_run=args.dry_run)
        report_optimized(changed)
        total_before += sum(b for _, b, _ in changed)
        total_after += sum(a for _, _, a in changed)
    verb = "would save" if args.dry_run else "saved"
    print(f"{verb} {(total_before - total_after) / 1e6:.1f} MB" if total_before else "all images already optimised")
    return 0


def run_script(name: str, *extra: str) -> int:
    return subprocess.call([sys.executable, str(ROOT / "scripts" / name), *extra])


def cmd_import(args) -> int:
    extra = [str(args.backup)] if args.backup else []
    if args.overwrite:
        extra.append("--overwrite")
    return run_script("import_hashnode.py", *extra)


def cmd_build(args) -> int:
    return run_script("build_blog.py")


def cmd_check(args) -> int:
    code = run_script("build_blog.py", "--check")
    return code or run_script("check.py")


def cmd_preview(args) -> int:
    out = ROOT / ".preview"
    code = run_script("build_blog.py", "--drafts", "--out", str(out))
    if code:
        return code
    print(f"serving the preview at http://127.0.0.1:{args.port}/blog/ (Ctrl+C to stop)")
    try:
        return subprocess.call([sys.executable, "-m", "http.server", str(args.port),
                                "--bind", "127.0.0.1", "--directory", str(out)])
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("sections", help="list sections and post counts").set_defaults(func=cmd_sections)
    sub.add_parser("drafts", help="list local drafts").set_defaults(func=cmd_drafts)

    p = sub.add_parser("new", help="start a draft")
    p.add_argument("section")
    p.add_argument("title")
    p.add_argument("--slug")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("publish", help="move a draft into content/blog/")
    p.add_argument("slug")
    p.add_argument("--section")
    p.add_argument("--order", type=int, help="position in a series section")
    p.add_argument("--date", help="datePublished (ISO 8601); default now")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("unpublish", help="move a post back to drafts")
    p.add_argument("slug")
    p.set_defaults(func=cmd_unpublish)

    p = sub.add_parser("move", help="change a post's section")
    p.add_argument("slug")
    p.add_argument("section")
    p.add_argument("--order", type=int)
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("optimize", help="shrink original images in content/ (also runs on publish)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_optimize)

    p = sub.add_parser("import", help="re-run the Hashnode importer")
    p.add_argument("backup", nargs="?", type=Path)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_import)

    sub.add_parser("build", help="regenerate /blog").set_defaults(func=cmd_build)
    sub.add_parser("check", help="verify output is current and passes check.py").set_defaults(func=cmd_check)
    p = sub.add_parser("preview", help="build with drafts into .preview/ and serve it")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_preview)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ContentError as exc:
        return fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
