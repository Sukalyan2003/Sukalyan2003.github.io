"""Tests for the blog importer, content model, management CLI and generator.

Run from the repository root with the build requirements installed:
    python3 -m unittest discover -s scripts/tests -v
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import blog  # noqa: E402
import blog_lib  # noqa: E402
import build_blog  # noqa: E402
import import_hashnode as imp  # noqa: E402
import update_writing  # noqa: E402
from blog_lib import compose, set_key, split_front_matter, validate  # noqa: E402

SECTIONS_YML = """
- {slug: linux, label: Linux, nav: primary, description: Terminal notes.}
- {slug: aiml, label: AIML, nav: primary}
- {slug: bits, label: Bits, nav: more, series: true}
"""


def post_text(slug, *, section="linux", date="2026-01-01T00:00:00.000Z", tags=("c",), body="Body text.\n", **extra):
    meta = {"title": slug.replace("-", " ").title(), "slug": slug, "section": section,
            "datePublished": date, "description": f"About {slug}.", "tags": list(tags)}
    meta.update(extra)
    return compose(meta, body)


class TempContent:
    """A throwaway content/ tree for tests that write files."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp())
        self.content = self.dir / "content" / "blog"
        self.drafts = self.dir / "content" / "drafts"
        self.content.mkdir(parents=True)
        (self.content / "sections.yml").write_text(SECTIONS_YML, encoding="utf-8")

    def add(self, slug, where=None, **kw):
        folder = where or self.content
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{slug}.md"
        path.write_text(post_text(slug, **kw), encoding="utf-8")
        return path

    def cleanup(self):
        shutil.rmtree(self.dir, ignore_errors=True)


def quiet(func, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = func(*args, **kwargs)
    return code, out.getvalue() + err.getvalue()


# =============================================================== importer
class ImporterTests(unittest.TestCase):
    def test_source_front_matter_tolerates_hashnode_quirks(self):
        block = ('title: "What is Agentic RAG? \n"\n'
                 'seoDescription: "Learn to use AI-driven "vibecoding" safely"\n'
                 "tags: ai, rag,  mcp\ndatePublished: 2026-05-30T04:42:39.018Z")
        meta = imp.parse_source_front_matter(block)
        self.assertEqual(meta["title"], "What is Agentic RAG?")
        self.assertEqual(meta["seoDescription"], 'Learn to use AI-driven "vibecoding" safely')
        self.assertEqual(meta["tags"], "ai, rag, mcp")  # whitespace runs collapse

    def test_convert_body_minimal_changes(self):
        body = ('Intro <mark class="bg-yellow-200 dark:bg-yellow-500/30">hi</mark>\n\n'
                '![](https://cdn.hashnode.com/x/a.png align="center")\n\n'
                '![A cat](https://cdn.hashnode.com/x/b.png)\n\n'
                "[old](https://sukalyanroy.hashnode.dev/known-post) and "
                "[gone](https://sukalyanroy.hashnode.dev/renamed-post) and "
                "[other](https://someone.hashnode.dev/known-post) and "
                "[by id](https://hashnode.com/post/abc123)\n")
        localize = lambda slug, url: f"img/{slug}/{url.rsplit('/', 1)[-1]}"
        out, notes = imp.convert_body(body, "me", {"known-post"}, localize, {"abc123": "known-post"})
        self.assertIn("<mark>hi</mark>", out)
        self.assertIn("![](img/me/a.png)", out)
        self.assertIn("![A cat](img/me/b.png)", out)
        self.assertIn("[old](/blog/known-post/)", out)
        self.assertIn("https://sukalyanroy.hashnode.dev/renamed-post", out)
        self.assertIn("https://someone.hashnode.dev/known-post", out)
        self.assertIn("[by id](/blog/known-post/)", out)
        self.assertEqual(notes["unresolved_links"], ["renamed-post"])
        self.assertEqual((notes["images"], notes["images_no_alt"]), (2, 1))

    def test_build_meta_excerpt_and_tags(self):
        src = {"title": " T ", "datePublished": "2026-01-02T03:04:05.000Z", "tags": "a, b ,c"}
        body = "## TL;DR\n\n* First point here.\n"
        meta = imp.build_meta(src, "t", body, lambda s, u: u, draft=False, cuid="x")
        self.assertEqual(meta["title"], "T")
        self.assertEqual(meta["tags"], ["a", "b", "c"])
        self.assertEqual(meta["descriptionSource"], "excerpt")
        self.assertEqual(meta["description"], "First point here.")
        self.assertEqual(meta["hashnode"]["url"], "https://sukalyanroy.hashnode.dev/t")
        draft = imp.build_meta({"title": "D"}, "d", "", lambda s, u: u, draft=True, cuid="y")
        self.assertTrue(draft["draft"])
        self.assertNotIn("url", draft["hashnode"])
        self.assertNotIn("datePublished", draft)

    def test_seo_description_wins(self):
        src = {"title": "T", "datePublished": "2026-01-02T00:00:00Z", "seoDescription": "Real one."}
        meta = imp.build_meta(src, "t", "Other text.", lambda s, u: u, draft=False, cuid="x")
        self.assertEqual(meta["description"], "Real one.")
        self.assertNotIn("descriptionSource", meta)

    def test_part_numbers_are_not_duplicates(self):
        self.assertFalse(imp.likely_same_post("Nand2Tetris Part 2: Software", "Nand2Tetris Part 1: Hardware"))
        self.assertFalse(imp.likely_same_post("From Tokens to Trees Part 2", "From Tokens to Trees"))
        self.assertTrue(imp.likely_same_post("History Part 2", "History Part 2"))

    def test_date_updated_counts_only_prose_changes(self):
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo, True)
        git = lambda *a, date="2026-01-01T00:00:00+00:00": subprocess.run(
            ["git", "-C", str(repo), *a], check=True, capture_output=True,
            env={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date, "HOME": str(repo),
                 "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                 "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"})
        git("init", "-q")
        f = repo / "p.md"
        f.write_text("---\ntitle: T\n---\nHello world\n")
        git("add", "."); git("commit", "-qm", "create post: T")
        f.write_text("---\ntitle: T2\n---\nHello   world\n")  # metadata + whitespace only
        git("commit", "-qam", "update post: T", date="2026-02-01T00:00:00+00:00")
        published = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertIsNone(imp.git_dates_updated(repo, "p.md", published))
        f.write_text("---\ntitle: T2\n---\nHello brave world\n")
        git("commit", "-qam", "update post: T", date="2026-03-01T00:00:00+00:00")
        self.assertEqual(imp.git_dates_updated(repo, "p.md", published), "2026-03-01T00:00:00.000Z")

    def test_write_if_changed_protects_local_edits(self):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        path = tmp.content / "x.md"
        self.assertEqual(imp.write_if_changed(path, "a", False), "written")
        self.assertEqual(imp.write_if_changed(path, "a", False), "unchanged")
        self.assertTrue(imp.write_if_changed(path, "b", False).startswith("skipped"))
        self.assertEqual(path.read_text(), "a")
        self.assertEqual(imp.write_if_changed(path, "b", True), "overwritten")

    def test_local_section_survives_reimport(self):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        path = tmp.add("x", section="aiml")
        meta = {}
        imp.keep_local_placement(path, meta, {"section": "linux"})
        self.assertEqual(meta["section"], "aiml")
        fresh = {}
        imp.keep_local_placement(tmp.content / "new.md", fresh, {"section": "bits", "seriesOrder": 2})
        self.assertEqual(fresh, {"section": "bits", "seriesOrder": 2})

    def test_reports_and_url_map(self):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        meta = {"title": "T", "datePublished": "2026-01-01T00:00:00.000Z", "tags": [],
                "hashnode": {"cuid": "c1", "url": "https://sukalyanroy.hashnode.dev/t"}}
        notes = {"unresolved_links": ["old", "old"], "images": 1, "images_no_alt": 1, "remote_hosts": set()}
        rows = [("t", meta, notes, "written", Path("x"), "Body $$x$$")]
        drafts = [("d", "Secret title", "written", ["stub (under 300 characters)"], 10)]
        with mock.patch.object(imp, "MIGRATION", tmp.dir / "migration"), mock.patch.object(imp, "DRAFTS", tmp.drafts):
            imp.write_reports(rows, drafts, {"t"}, [], [])
        report = (tmp.dir / "migration" / "report.md").read_text()
        self.assertIn("1 of 1 inline images have no alt text", report)
        self.assertEqual(report.count("links to `old` on Hashnode"), 1)
        self.assertIn("math", report)
        self.assertNotIn("Secret title", report)  # draft titles stay out of committed files
        rows_csv = list(csv.reader((tmp.dir / "migration" / "hashnode-url-map.csv").read_text().splitlines()))
        self.assertEqual(rows_csv[1][:2], ["https://sukalyanroy.hashnode.dev/t", "https://sukalyan2003.github.io/blog/t/"])
        self.assertIn("Secret title", (tmp.drafts / "_REPORT.md").read_text())


# ========================================================== content model
class ContentModelTests(unittest.TestCase):
    def test_set_key_touches_only_that_key(self):
        body = "\nBody with ---\nand: colons\n"
        text = compose({"title": "T", "slug": "t", "section": "linux"}, body)
        changed = set_key(text, "section", "aiml")
        self.assertIn('section: "aiml"', changed)
        self.assertTrue(changed.endswith(body.lstrip("\n")))
        self.assertEqual(changed.replace('"aiml"', '"linux"'), text)
        added = set_key(text, "seriesOrder", 3)
        self.assertIn("seriesOrder: 3", added)
        removed = set_key(added, "seriesOrder", None)
        self.assertEqual(removed, text)

    def test_front_matter_round_trip(self):
        meta = {"title": 'Quote "me": yes', "slug": "q", "tags": ["a"], "hashnode": {"cuid": "c"}}
        parsed, body = split_front_matter(compose(meta, "Hi\n"))
        self.assertEqual(parsed, meta)
        self.assertEqual(body, "\nHi\n")

    def _validate(self, *posts):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        for slug, kw in posts:
            tmp.add(slug, **kw)
        return validate(blog_lib.load_sections(tmp.content / "sections.yml"), blog_lib.load_posts(tmp.content))

    def test_validation_rules(self):
        self.assertEqual(self._validate(("ok", {})), [])
        self.assertTrue(any("unknown section" in e for e in self._validate(("a", {"section": "nope"}))))
        self.assertTrue(any("missing section" in e for e in self._validate(("a", {"section": ""}))))
        self.assertTrue(any("draft: true" in e for e in self._validate(("a", {"draft": True}))))
        self.assertTrue(any("collides with a section" in e for e in self._validate(("linux", {}))))
        self.assertTrue(any("set seriesOrder" in e for e in self._validate(("a", {"section": "bits"}))))
        errors = self._validate(("a", {"section": "bits", "seriesOrder": 1}), ("b", {"section": "bits", "seriesOrder": 1}))
        self.assertTrue(any("seriesOrder 1 already used" in e for e in errors))

    def test_start_here_links_resolve(self):
        page = (blog_lib.PAGES / "start-here.md").read_text(encoding="utf-8")
        slugs = {p.stem for p in blog_lib.CONTENT.glob("*.md")}
        links = re.findall(r"\]\(/blog/([^/)]+)/\)", page)
        self.assertEqual(len(links), 6)
        for slug in links:
            self.assertIn(slug, slugs)


# ===================================================================== CLI
class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TempContent()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (("CONTENT", self.tmp.content), ("DRAFTS", self.tmp.drafts), ("ROOT", self.tmp.dir)):
            patcher = mock.patch.object(blog, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_new_then_publish_then_unpublish(self):
        code, _ = quiet(blog.main, ["new", "linux", "My Shell Notes"])
        self.assertEqual(code, 0)
        draft = self.tmp.drafts / "my-shell-notes.md"
        self.assertTrue(split_front_matter(draft.read_text())[0]["draft"])
        code, out = quiet(blog.main, ["new", "linux", "My Shell Notes"])
        self.assertEqual(code, 1)
        self.assertIn("already exists", out)

        (self.tmp.drafts / "img" / "my-shell-notes").mkdir(parents=True)
        (self.tmp.drafts / "img" / "my-shell-notes" / "a.png").write_bytes(b"x")
        code, _ = quiet(blog.main, ["publish", "my-shell-notes", "--date", "2026-09-01T10:00:00.000Z"])
        self.assertEqual(code, 0)
        published = self.tmp.content / "my-shell-notes.md"
        meta = split_front_matter(published.read_text())[0]
        self.assertNotIn("draft", meta)
        self.assertEqual(meta["datePublished"], "2026-09-01T10:00:00.000Z")
        self.assertFalse(draft.exists())
        self.assertTrue((self.tmp.content / "img" / "my-shell-notes" / "a.png").exists())

        code, _ = quiet(blog.main, ["unpublish", "my-shell-notes"])
        self.assertEqual(code, 0)
        self.assertTrue(split_front_matter(draft.read_text())[0]["draft"])
        self.assertTrue((self.tmp.drafts / "img" / "my-shell-notes" / "a.png").exists())
        self.assertFalse(published.exists())

    def test_publish_carries_diagram_renders(self):
        body = "Text\n\n```mermaid\nflowchart LR\n  A --> B\n```\n"
        self.tmp.add("diag", where=self.tmp.drafts, draft=True, body=body)
        source = "flowchart LR\n  A --> B\n"
        names = [f"{build_blog.Diagrams.key(source, t)}-{t}.svg" for t in ("paper", "press")]
        (self.tmp.drafts / "diagrams").mkdir(parents=True)
        for name in names:
            (self.tmp.drafts / "diagrams" / name).write_text("<svg/>")
        code, _ = quiet(blog.main, ["publish", "diag"])
        self.assertEqual(code, 0)
        for name in names:
            self.assertTrue((self.tmp.content / "diagrams" / name).exists())
            self.assertFalse((self.tmp.drafts / "diagrams" / name).exists())

    def test_publish_guards(self):
        self.tmp.add("d", where=self.tmp.drafts, section="", draft=True)
        code, out = quiet(blog.main, ["publish", "d"])
        self.assertEqual(code, 1)
        self.assertIn("no section", out)
        code, out = quiet(blog.main, ["publish", "d", "--section", "bits"])
        self.assertEqual(code, 1)
        self.assertIn("--order", out)
        self.tmp.add("taken")
        self.tmp.add("taken", where=self.tmp.drafts, draft=True)
        code, out = quiet(blog.main, ["publish", "taken"])
        self.assertEqual(code, 1)
        self.assertIn("already uses slug", out)

    def test_move_changes_only_section(self):
        path = self.tmp.add("p", body="Keep\n  exactly\n")
        before = path.read_text()
        code, _ = quiet(blog.main, ["move", "p", "aiml"])
        self.assertEqual(code, 0)
        after = path.read_text()
        self.assertEqual(after.replace('section: "aiml"', 'section: "linux"'), before)
        code, out = quiet(blog.main, ["move", "p", "bits"])
        self.assertEqual(code, 1)
        code, _ = quiet(blog.main, ["move", "p", "bits", "--order", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(split_front_matter(path.read_text())[0]["seriesOrder"], 2)
        code, _ = quiet(blog.main, ["move", "p", "linux"])
        self.assertNotIn("seriesOrder", split_front_matter(path.read_text())[0])


# =============================================================== generator
class MarkdownTests(unittest.TestCase):
    def render(self, body):
        return build_blog.render_markdown(body, lambda src: None)

    def test_headings_toc_and_shift(self):
        out = self.render("# One\n\n## Two\n\ntext words here\n")
        self.assertIn("<h2", out["html"])
        self.assertIn("<h3", out["html"])
        self.assertNotIn("<h1", out["html"])
        self.assertEqual([h["text"] for h in out["toc"]], ["One", "Two"])
        self.assertIn('class="heading-anchor" href="#one"', out["html"])

    def test_reserved_heading_ids_are_renamed(self):
        out = self.render("## Main\n")
        self.assertIn('id="main-section"', out["html"])

    def test_code_tables_images_links(self):
        out = self.render("```python\ndef f():\n    return 1\n```\n\n```\nplain <b>\n```\n\n"
                          "| a | b |\n|---|---|\n| 1 | 2 |\n\n![alt](img/x.png \"Cap\")\n\nSee https://example.com now.\n")
        html = out["html"]
        self.assertIn('<span class="code-block__lang">python</span>', html)
        self.assertIn('<span class="k">def</span>', html)
        self.assertIn("plain &lt;b&gt;", html)
        self.assertIn('<div class="table-scroll"', html)
        self.assertIn('<figure class="figure">', html)
        self.assertIn("<figcaption>Cap</figcaption>", html)
        self.assertNotIn("<p><figure", html)
        self.assertIn('<a href="https://example.com">https://example.com</a>', html)
        self.assertEqual(len(out["problems"]), 1)  # the unresolved image is reported

    def test_math_becomes_mathml_and_prices_stay_text(self):
        html = self.render("Area $a^2$ costs $250, not $ 5 $.\n\n$$\\frac{1}{2}$$\n")["html"]
        self.assertEqual(html.count("<math"), 2)
        self.assertIn('display="inline"', html)
        self.assertIn('<div class="math-block"><math', html)
        self.assertIn("costs $250", html)
        self.assertIn("$ 5 $", html)

    def test_word_count_excludes_code(self):
        out = self.render("one two three\n\n```\nfour five six seven\n```\n")
        self.assertEqual(out["words"], 3)


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TempContent()
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(17):
            section = ["linux", "aiml"][i % 2]
            tags = ["shared", f"t{i % 3}"]
            cls.tmp.add(f"post-{i:02d}", section=section, tags=tags,
                        date=blog_lib.iso(base + timedelta(days=i)), body="## A\n\nwords " * 3)
        cls.tmp.add("bits-2", section="bits", seriesOrder=2, date=blog_lib.iso(base + timedelta(days=30)))
        cls.tmp.add("bits-1", section="bits", seriesOrder=1, date=blog_lib.iso(base + timedelta(days=31)))
        sections = blog_lib.load_sections(cls.tmp.content / "sections.yml")
        posts = blog_lib.load_posts(cls.tmp.content)
        assert validate(sections, posts) == []
        cls.site = build_blog.Site(sections, posts, preview=False, images=build_blog.Images(cls.tmp.dir, True))
        cls.site.build("2026-01-01")
        cls.posts = {p["slug"]: p for p in posts}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pages_generated(self):
        files = self.site.files
        for rel in ("blog/index.html", "blog/page/2/index.html", "blog/linux/index.html",
                    "blog/bits/index.html", "blog/tags/index.html", "blog/tags/shared/index.html",
                    "blog/post-00/index.html", "blog/rss.xml", "blog/search.json", "sitemap.xml", "robots.txt"):
            self.assertIn(rel, files)
        self.assertNotIn("blog/page/3/index.html", files)  # 19 posts: 5 front + 10 + 4
        self.assertEqual(self.site.problems, [])

    def test_canonical_and_jsonld(self):
        page = self.site.files["blog/post-03/index.html"]
        self.assertIn('<link rel="canonical" href="https://sukalyan2003.github.io/blog/post-03/">', page)
        self.assertIn('href="../../the-record/css/styles.css?v=1"', page)
        self.assertNotRegex(page, r'(?:href|src|srcset)="/(?!/)')
        self.assertIn('<meta property="og:type" content="article">', page)
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1))
        types = [node["@type"] for node in ld["@graph"]]
        self.assertEqual(types, ["BlogPosting", "BreadcrumbList"])
        self.assertEqual(ld["@graph"][0]["datePublished"], "2026-01-04T00:00:00.000Z")
        index = self.site.files["blog/page/2/index.html"]
        self.assertIn('<link rel="canonical" href="https://sukalyan2003.github.io/blog/page/2/">', index)

    def test_prev_next_edges(self):
        self.assertIsNone(self.posts["post-00"]["older"])
        self.assertEqual(self.posts["post-00"]["newer"]["slug"], "post-01")
        self.assertIsNone(self.posts["bits-1"]["newer"])

    def test_related_prefers_shared_tags_and_section(self):
        related = [p["slug"] for p in self.posts["post-00"]["related"]]
        self.assertEqual(len(related), 3)
        # Only post-06 and post-12 share both the section (even) and tag t0
        # (i % 3 == 0); they rank first, newest first.
        self.assertEqual(related[:2], ["post-12", "post-06"])

    def test_series_order_and_label(self):
        self.assertEqual([p["slug"] for p in self.posts["bits-2"]["series"]], ["bits-1", "bits-2"])
        self.assertIn("Part 2 of 2", self.site.files["blog/bits-2/index.html"])

    def test_feeds_parse(self):
        rss = ET.fromstring(self.site.files["blog/rss.xml"])
        self.assertEqual(len(rss.findall("./channel/item")), 19)
        link = rss.find("./channel/item/link").text
        self.assertTrue(link.startswith("https://sukalyan2003.github.io/blog/"))
        sitemap = ET.fromstring(self.site.files["sitemap.xml"])
        locs = [e.text for e in sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertIn("https://sukalyan2003.github.io/blog/post-05/", locs)
        self.assertEqual(len(locs), len(set(locs)))
        self.assertIn("Disallow: /content/", self.site.files["robots.txt"])

    def test_rss_is_capped(self):
        with mock.patch.object(build_blog.cfg, "RSS_ITEMS", 5):
            self.site.build_rss()
        rss = ET.fromstring(self.site.files["blog/rss.xml"])
        titles = [i.find("title").text for i in rss.findall("./channel/item")]
        self.assertEqual(len(titles), 5)
        self.assertEqual(titles[0], self.site.posts[0]["title"])  # newest first
        self.site.build_rss()

    def test_no_comments_without_giscus_ids(self):
        page = self.site.files["blog/post-01/index.html"]
        self.assertNotIn("giscus", page)


def png_bytes(image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def noise_image(w, h):
    import random
    from PIL import Image
    rnd = random.Random(1)
    return Image.frombytes("RGB", (w, h), bytes(rnd.getrandbits(8) for _ in range(w * h * 3)))


def flat_image(w, h):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    for i in range(0, w, 40):
        draw.rectangle([i, 10, i + 20, h - 10], outline=(0, 0, 0), width=2)
    return im


class ImageOptimizeTests(unittest.TestCase):
    def test_photo_becomes_lossy_webp_capped_in_width(self):
        from PIL import Image
        data, ext = blog_lib.optimize_image(png_bytes(noise_image(3000, 300)), "png")
        self.assertEqual(ext, "webp")
        with Image.open(io.BytesIO(data)) as im:
            self.assertEqual(im.size, (2400, 240))

    def test_classification(self):
        self.assertTrue(blog_lib.is_photo_like(noise_image(300, 200)))
        self.assertFalse(blog_lib.is_photo_like(flat_image(300, 200)))

    def test_kept_when_not_meaningfully_smaller(self):
        buf = io.BytesIO()
        flat_image(300, 200).save(buf, "WEBP", lossless=True, quality=80, method=4)
        already = buf.getvalue()  # re-encoding cannot shave 10% off this
        data, ext = blog_lib.optimize_image(already, "webp")
        self.assertIs(data, already)
        self.assertEqual(ext, "webp")

    def test_unreadable_files_are_skipped(self):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        (tmp.content / "img" / "p").mkdir(parents=True)
        (tmp.content / "img" / "p" / "broken.png").write_bytes(b"not an image")
        self.assertEqual(blog_lib.optimize_folder(tmp.content), [])

    def test_gif_and_svg_untouched(self):
        self.assertEqual(blog_lib.optimize_image(b"GIF89a...", "gif"), (b"GIF89a...", "gif"))
        self.assertEqual(blog_lib.optimize_image(b"<svg/>", ".svg"), (b"<svg/>", "svg"))

    def test_folder_pass_renames_and_rewrites_references(self):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        folder = tmp.content / "img" / "p"
        folder.mkdir(parents=True)
        (folder / "cover.png").write_bytes(png_bytes(noise_image(600, 300)))
        post = tmp.add("p", body="![A](img/p/cover.png)\n", cover="img/p/cover.png")
        dry = blog_lib.optimize_folder(tmp.content, dry_run=True)
        self.assertEqual(len(dry), 1)
        self.assertTrue((folder / "cover.png").exists())
        changed = blog_lib.optimize_folder(tmp.content)
        self.assertEqual(changed[0][0], "img/p/cover.png")
        self.assertFalse((folder / "cover.png").exists())
        self.assertTrue((folder / "cover.webp").exists())
        text = post.read_text()
        self.assertNotIn("cover.png", text)
        self.assertEqual(text.count("img/p/cover.webp"), 2)
        self.assertEqual(blog_lib.optimize_folder(tmp.content), [])  # idempotent

    def test_variant_names_follow_content(self):
        tmp = TempContent()
        self.addCleanup(tmp.cleanup)
        src = tmp.dir / "a.png"
        src.write_bytes(png_bytes(flat_image(600, 300)))
        images = build_blog.Images(tmp.dir / "out", True)
        first = images.variants(src, "blog/x/img")["src"]
        src.write_bytes(png_bytes(noise_image(600, 300)))
        second = images.variants(src, "blog/x/img")["src"]
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("/blog/x/img/a-"))


SAMPLE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {w} 120"><text>x</text></svg>'


class FingerprintTests(unittest.TestCase):
    def test_text_fingerprint_ignores_line_endings(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "a.css").write_bytes(b"a {\n  color: red;\n}\n")
        (d / "b.css").write_bytes(b"a {\r\n  color: red;\r\n}\r\n")
        self.assertEqual(build_blog.fingerprint(d / "a.css"), build_blog.fingerprint(d / "b.css"))


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.images = build_blog.Images(self.dir / "out", True)
        self.source = "flowchart LR\n  accTitle: Pipeline\n  accDescr: A goes to B.\n  A --> B\n"

    def fake_render(self, width):
        def render(diagrams, source, theme, target):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(SAMPLE_SVG.format(w=width))
            return None
        return render

    def test_figure_has_two_plates_alt_and_caption(self):
        diagrams = build_blog.Diagrams(self.images, check=False)
        with mock.patch.object(build_blog.Diagrams, "_render", self.fake_render(400)):
            html = diagrams.figure(self.source, self.dir / "cache", "blog/p/img")
        self.assertIn("diagram-plate--paper", html)
        self.assertIn("diagram-plate--press", html)
        self.assertIn('alt="A goes to B. (opens full size)"', html)
        self.assertIn("<figcaption>Pipeline</figcaption>", html)
        self.assertIn('width="400" height="120"', html)
        self.assertEqual(len(list((self.dir / "cache").glob("*.svg"))), 2)
        self.assertEqual(len(self.images.expected), 2)

    def test_wide_diagram_scrolls_at_legible_scale(self):
        diagrams = build_blog.Diagrams(self.images, check=False)
        with mock.patch.object(build_blog.Diagrams, "_render", self.fake_render(1200)):
            html = diagrams.figure(self.source, self.dir / "cache", "blog/p/img")
        self.assertIn("diagram-figure--scroll", html)
        self.assertIn('width="900" height="90"', html)
        self.assertIn("Scroll sideways", html)

    def test_cache_is_reused_and_check_mode_reports_missing(self):
        with mock.patch.object(build_blog.Diagrams, "_render", self.fake_render(300)):
            build_blog.Diagrams(self.images, check=False).figure(self.source, self.dir / "cache", "blog/p/img")
        with mock.patch.object(build_blog.Diagrams, "_render", side_effect=AssertionError("re-rendered")):
            self.assertIsNotNone(build_blog.Diagrams(self.images, check=False).figure(
                self.source, self.dir / "cache", "blog/p/img"))
        checker = build_blog.Diagrams(build_blog.Images(self.dir / "out2", False), check=True)
        self.assertIsNone(checker.figure("flowchart LR\n  X --> Y\n", self.dir / "cache", "blog/p/img"))
        self.assertTrue(any("diagram not rendered" in m for m in checker.images.missing))

    def test_prune_removes_unused_renders(self):
        diagrams = build_blog.Diagrams(self.images, check=False)
        (self.dir / "cache").mkdir()
        (self.dir / "cache" / "stale-paper.svg").write_text("x")
        with mock.patch.object(build_blog.Diagrams, "_render", self.fake_render(300)):
            diagrams.figure(self.source, self.dir / "cache", "blog/p/img")
        diagrams.prune(self.dir / "cache")
        self.assertEqual(len(list((self.dir / "cache").glob("*.svg"))), 2)

    def test_render_failure_is_a_build_problem(self):
        diagrams = build_blog.Diagrams(self.images, check=False)
        with mock.patch.object(build_blog.Diagrams, "_render", return_value="mermaid-cli failed: syntax"):
            self.assertIsNone(diagrams.figure(self.source, self.dir / "cache", "blog/p/img"))
        self.assertEqual(diagrams.problems, ["mermaid-cli failed: syntax"])
        html = build_blog.render_markdown("```mermaid\nA-->B\n```\n", lambda s: None, lambda src: None)["html"]
        self.assertIn('<span class="code-block__lang">mermaid</span>', html)  # falls back to the source


class RelativeUrlTests(unittest.TestCase):
    def test_relative_url(self):
        r = build_blog.relative_url
        self.assertEqual(r("/the-record/css/a.css?v=1", "blog/x/index.html"), "../../the-record/css/a.css?v=1")
        self.assertEqual(r("/blog/", "blog/index.html"), "./")
        self.assertEqual(r("/blog/#search", "blog/x/index.html"), "../#search")
        self.assertEqual(r("/", "blog/tags/y/index.html"), "../../../")
        self.assertEqual(r("/blog/y/", "blog/x/index.html"), "../y/")

    def test_relativize_leaves_full_urls(self):
        doc = ('<a href="https://x.dev/a">x</a><img src="/blog/a/img/p-480.webp" '
               'srcset="/blog/a/img/p-480.webp 480w, /blog/a/img/p-960.webp 960w">')
        out = build_blog.relativize(doc, "blog/a/index.html")
        self.assertIn('href="https://x.dev/a"', out)
        self.assertIn('src="img/p-480.webp"', out)
        self.assertIn('srcset="img/p-480.webp 480w, img/p-960.webp 960w"', out)


class WritingSectionTests(unittest.TestCase):
    def test_render_links_locally(self):
        records = [{"title": "A's post", "url": "/blog/a/", "summary": "TL;DR Short.", "dateLabel": "1 Jan 2026",
                    "date": "2026-01-01T00:00:00.000Z", "tags": [{"slug": "x", "label": "X"}]}]
        block = update_writing.render(update_writing.posts_from_records(records))
        self.assertIn('<a href="blog/a/">A&#x27;s post</a>', block)
        self.assertNotIn("target=", block)
        self.assertIn("<p>Short.</p>", block)


if __name__ == "__main__":
    unittest.main()
