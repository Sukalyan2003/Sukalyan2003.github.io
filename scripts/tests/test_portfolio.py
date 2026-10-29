"""Regressions for the public evidence and generated portfolio routes."""
import json
import copy
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_blog
import build_portfolio as portfolio
import portfolio_explore as explore


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.hrefs = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs += [value for key, value in attrs if key == 'href']


class PortfolioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(portfolio.SOURCE.read_text())
        cls.pages = portfolio.build(cls.data)

    def test_case_studies_retain_every_public_evidence_and_ownership_facet(self):
        for project in self.data['projects']:
            if not project.get('facets'):
                continue
            page = self.pages[f'work/{project["slug"]}/index.html']
            for label, original in project['facets'].items():
                with self.subTest(project=project['slug'], facet=label):
                    self.assertIn(portfolio.relative(original, '../../'), page)

    def test_work_index_links_only_to_existing_detailed_cases(self):
        links = Links(self.pages['work/index.html']).hrefs
        for project in self.data['projects']:
            route = f'work/{project["slug"]}/index.html'
            if project.get('facets'):
                self.assertIn(route, self.pages)
                self.assertIn(f'../work/{project["slug"]}/', links)
            else:
                self.assertNotIn(route, self.pages)
        self.assertEqual(self.pages['work/index.html'].count('data-category='), len(self.data['projects']))

    def test_classic_keeps_current_evidence_and_every_project(self):
        page = self.pages['classic/index.html']
        self.assertIn('../css/styles.css', page)
        self.assertNotIn('assets/record/css', page)
        self.assertIn(portfolio.relative(self.data['bio_html'], '../'), page)
        self.assertIn(portfolio.relative(self.data['record_html'], '../'), page)
        self.assertIn(portfolio.relative(self.data['credentials_html'], '../'), page)
        for project in self.data['projects']:
            with self.subTest(project=project['slug']):
                self.assertIn(f'id="project-{project["slug"]}"', page)
                for text in project.get('facets', {}).values():
                    self.assertIn(portfolio.relative(text, '../'), page)
                if project.get('facets'):
                    self.assertIn(f'../work/{project["slug"]}/', Links(page).hrefs)
                else:
                    self.assertNotIn(f'../work/{project["slug"]}/', Links(page).hrefs)

    def test_classic_lists_all_published_writing_and_library_entries(self):
        links = Links(self.pages['classic/index.html']).hrefs
        posts = json.loads((portfolio.ROOT / 'blog/search.json').read_text())
        for post in posts:
            self.assertIn('..' + post['url'], links)
        for item in self.data['books'] + self.data['films'] + self.data['essays']:
            self.assertIn(item['url'], links)
        self.assertIn('../', links)
        self.assertIn('../blog/', links)

    def test_classic_updates_when_content_records_change(self):
        data = copy.deepcopy(self.data)
        data['projects'][0]['facets']['Evidence'] = 'A new measured result, under stated conditions.'
        data['books'].append(dict(data['books'][0], url='https://example.com/new-book'))
        page = portfolio.build(data)['classic/index.html']
        self.assertIn('A new measured result, under stated conditions.', page)
        self.assertIn('https://example.com/new-book', Links(page).hrefs)

    def test_writing_updates_preserve_surrounding_portfolio(self):
        home = self.pages['index.html']
        replacement = '<!-- WRITING:START -->\n<p>A later dispatch</p>\n<!-- WRITING:END -->'
        updated = portfolio.update_writing.splice(home, replacement)
        self.assertIn('A later dispatch', updated)
        self.assertIn('Selected work', updated)
        self.assertIn('about/', Links(updated).hrefs)
        self.assertEqual(updated.count('WRITING:START'), 1)
        self.assertEqual(updated.count('WRITING:END'), 1)

    def test_personal_links_use_the_provided_accounts_without_embedded_playback(self):
        about = self.pages['about/index.html']
        self.assertIn('yearly film lists', about)
        library = self.pages['library/index.html']
        links = Links(library).hrefs
        self.assertIn('../library/', Links(about).hrefs)
        for url in ('https://casuallyoverthinking.substack.com/',
                    'https://www.goodreads.com/user/show/122426384-suka',
                    'https://www.imdb.com/list/ls591727943/'):
            self.assertIn(url, links)
            self.assertNotIn(url, Links(self.pages['index.html']).hrefs)
        self.assertNotIn('ls4115507913', library)  # annual watching log stays out
        self.assertNotRegex(library, r'https://(?:www\.)?(?:spotify|instagram)\.com')
        self.assertNotRegex(''.join(self.pages.values()), r'<(?:audio|iframe)\b|\bautoplay\b')

    def test_search_routes_include_private_summaries_and_real_writing(self):
        home = self.pages['index.html']
        payload = re.search(r'<script type="application/json" id="find-index">(.*?)</script>', home, re.S)
        entries = json.loads(payload[1])
        for entry in entries:
            if entry['kind'] == 'Project':
                path, _, fragment = entry['url'].partition('#')
                target = self.pages[path + 'index.html']
                if fragment:
                    self.assertIn(f'id="{fragment}"', target)
            elif entry['kind'] == 'Writing':
                self.assertTrue((portfolio.ROOT / entry['url'] / 'index.html').is_file())

    def test_map_connections_are_named_and_reference_existing_projects(self):
        slugs = {p['slug'] for p in self.data['projects']}
        for a, b, label in explore.CONNECTIONS:
            self.assertIn(a, slugs)
            self.assertIn(b, slugs)
            self.assertTrue(label.strip())
        markup = explore.project_map(self.data)
        self.assertEqual(set(re.findall(r'data-project="([^"]+)"', markup)), slugs)

    def test_selected_work_precedes_the_optional_map(self):
        page = self.pages['index.html']
        self.assertLess(page.index('id="work"'), page.index('class="map-disclosure"'))
        self.assertIn('<details class="map-disclosure" data-enhance hidden>', page)

    def test_project_counts_and_map_follow_the_content_record(self):
        data = copy.deepcopy(self.data)
        extra = dict(data['projects'][-1], slug='another-tool', title='Another tool')
        data['projects'].append(extra)
        pages = portfolio.build(data)
        self.assertIn('10 projects', pages['work/index.html'])
        self.assertIn('All 10 projects', pages['index.html'])
        self.assertIn('data-project="another-tool"', pages['index.html'])
        self.assertIn('viewBox="0 0 600 544"', pages['index.html'])
        data['projects'] = [p for p in data['projects'] if p['slug'] != 'nand2tetris']
        pages = portfolio.build(data)
        self.assertNotIn('work/nand2tetris/index.html', pages)
        self.assertNotIn('data-project="nand2tetris"', pages['index.html'])

    def test_invalid_and_duplicate_slugs_are_rejected_before_rendering(self):
        for slug in ('../outside', '/absolute', 'with space', 'eeg-platform'):
            with self.subTest(slug=slug):
                data = copy.deepcopy(self.data)
                data['projects'][-1]['slug'] = slug
                with self.assertRaises(ValueError):
                    portfolio.build(data)

    def test_jsonld_escapes_html_without_changing_the_data(self):
        value = '</script><unexpected>'
        page = portfolio.head('', 'Title', 'Description', '', {'@graph': [], 'probe': value})
        block = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)[1]
        self.assertNotIn('<', block)
        self.assertEqual(json.loads(block)['probe'], value)

    def test_sync_checks_then_removes_only_obsolete_owned_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / 'work/retired/index.html'
            custom = root / 'work/custom/index.html'
            old.parent.mkdir(parents=True)
            custom.parent.mkdir(parents=True)
            old.write_text('<!DOCTYPE html>\n' + portfolio.GENERATED_MARKER)
            custom.write_text('<!DOCTYPE html><p>A hand-written page.</p>')
            with mock.patch.object(portfolio, 'ROOT', root):
                pages = {'index.html': 'Current homepage'}
                changes = portfolio.sync(pages, check=True)
                self.assertIn('(obsolete) work/retired/index.html', changes)
                self.assertTrue(old.exists())
                self.assertFalse((root / 'index.html').exists())
                portfolio.sync(pages)
                self.assertFalse(old.exists())
                self.assertTrue(custom.exists())
                self.assertEqual(portfolio.sync(pages, check=True), [])

    def test_sync_rejects_paths_outside_the_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(portfolio, 'ROOT', Path(tmp) / 'repo'):
                with self.assertRaises(ValueError):
                    portfolio.sync({'../outside.html': 'Unexpected'})
            self.assertFalse((Path(tmp) / 'outside.html').exists())

    def test_fusion_example_contains_independently_calculated_default_scores(self):
        page = self.pages['work/local-retrieval/index.html']
        rows = re.findall(r'<li data-result="([^"]+)">.*?<output>([^<]+)</output>', page, re.S)
        # Hand calculation: window is 1/62 + 1/61; cancellation is 1/61 + 1/63.
        self.assertEqual(rows, [('window', '0.032522'), ('cancel', '0.032266'),
                                ('header', '0.031754'), ('queue', '0.031498')])

    def test_film_import_keeps_only_the_public_catalogue_fields(self):
        films = self.data['films']
        self.assertEqual(len(films), 84)
        self.assertEqual(len({film['url'] for film in films}), 84)
        catalogue = {'position', 'title', 'year', 'url', 'type', 'genres', 'director', 'runtime'}
        poster = {'poster', 'poster_width', 'poster_height'}
        self.assertEqual([film['position'] for film in films], list(range(1, 85)))
        for film in films:
            self.assertIn(set(film), (catalogue, catalogue | poster))
            self.assertRegex(film['url'], r'^https://www\.imdb\.com/title/tt\d+/$')
        self.assertEqual(sum(film['type'] == 'Movie' for film in films), 74)

    def test_library_images_are_remote_urls_allowed_only_on_the_library_page(self):
        hosts = {'upload.wikimedia.org', 'thumb.wikimedia.org', 'i.gr-assets.com'}
        urls = [f['poster'] for f in self.data['films'] if 'poster' in f] + [b['image'] for b in self.data['books']]
        self.assertTrue(urls)
        for url in urls:
            self.assertIn(urlparse(url).netloc, hosts)
            self.assertEqual(urlparse(url).scheme, 'https')
            self.assertFalse(urlparse(url).query)
        library = self.pages['library/index.html']
        self.assertEqual(library.count('data-remote-img'), len(urls))
        for host in hosts:
            self.assertIn(f'https://{host}', library)
        for rel, page in self.pages.items():
            if rel == 'classic/index.html':
                # The retained Bootstrap page has no CSP; it still uses only local images.
                self.assertNotRegex(page, r'<img\b[^>]+src="https?://')
            elif rel != 'library/index.html':
                self.assertIn("img-src 'self';", page, rel)

    def test_blog_sitemap_keeps_public_portfolio_routes_and_excludes_private_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'content').mkdir()
            (root / 'content/portfolio.json').write_text(json.dumps(self.data))
            site = build_blog.Site([], [], preview=False, images=build_blog.Images(root, False))
            with mock.patch.object(build_blog, 'ROOT', root):
                site.build_sitemap('2026-10-26')
            xml = ET.fromstring(site.files['sitemap.xml'])
            urls = [el.text for el in xml.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
            # The alternate classic presentation stays out of the main sitemap.
            expected = {portfolio.SITE + '/' + rel.removesuffix('index.html')
                        for rel in self.pages if rel != 'classic/index.html'}
            self.assertEqual(set(urls), expected)
            self.assertEqual(len(urls), len(set(urls)))

    def test_blog_preview_keeps_portfolio_navigation_working_without_copying_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source', Path(tmp) / 'preview'
            output.mkdir()
            for folder in ('assets', 'blog/assets'):
                (source / folder).mkdir(parents=True)
                (source / folder / 'example.css').write_text('body {}')
            for rel in ('index.html', 'manifest.json', '404.html',
                        'work/index.html', 'work/example/index.html',
                        'about/index.html', 'library/index.html',
                        'content/drafts/private.md'):
                path = source / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(rel)
            with mock.patch.object(build_blog, 'ROOT', source):
                build_blog.copy_preview_assets(output)
            self.assertTrue((output / 'library/index.html').is_file())
            self.assertTrue((output / 'work/example/index.html').is_file())
            self.assertFalse((output / 'content').exists())


if __name__ == '__main__':
    unittest.main()
