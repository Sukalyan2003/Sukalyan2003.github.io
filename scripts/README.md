# Portfolio and blog tooling

Run from the repository root with the pinned `requirements-blog.txt` dependencies
installed in your Python environment. Node.js is used for JavaScript checks and
for new Mermaid renders.

```sh
python3 scripts/blog.py build     # blog, Record and Classic
python3 scripts/blog.py test      # unit tests and JavaScript syntax
python3 scripts/blog.py check     # freshness, HTML, design and local links
python3 scripts/blog.py preview   # serve a draft-inclusive blog preview
python3 scripts/blog.py posters   # refresh Library poster metadata; makes network requests
python3 scripts/blog.py --help    # authoring and import commands
```

`posters` changes `content/portfolio.json`; rebuild afterwards. `import` is kept
for importing a Hashnode backup and protects local edits unless `--overwrite` is
explicitly supplied. Neither command runs during a normal build or test.

| File | Responsibility |
| --- | --- |
| `blog.py` | Authoring and shared command entry point |
| `build_blog.py` | Blog pages, images, feeds and sitemap |
| `build_portfolio.py` | Complete portfolio pages, including latest writing |
| `build_classic.py` | Classic renderer, called by the portfolio generator |
| `portfolio_explore.py` | Markup for portfolio interactions and Library shelves |
| `blog_lib.py` | Shared content model, excerpts, validation and image optimization |
| `blog_config.py` | Active blog settings |
| `import_hashnode.py` | Optional repeatable Hashnode migration |
| `resolve_posters.py` | Optional Library poster lookup |
| `check.py` | Structural, design and link validation |
| `tests/` | Unit tests and one browser runner |

The portfolio generator owns the entire homepage. There is no separate Writing
updater or partial-page splicing step. Generated pages are ignored by Git; edit
their content or generators and rebuild.

For browser checks, serve the built repository in another terminal:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
CHROME_BIN=/path/to/chromium node scripts/tests/portfolio_browser.cjs
```

The browser runner needs no npm dependencies. It checks all generated blog pages
and portfolio interactions, writes results to `/tmp/portfolio-interaction-review`,
and removes its temporary Chromium profile when it exits. Use
`PORTFOLIO_REVIEW_DIR` for another output directory or `PORTFOLIO_BASE_URL` for
another preview server.
