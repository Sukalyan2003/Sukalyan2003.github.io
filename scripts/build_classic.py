"""Render the original Bootstrap design with the current public content."""
from __future__ import annotations

import html
import re
from pathlib import Path


def render(data: dict, posts: list[dict], root: Path) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value), quote=True)

    def relative(fragment: str) -> str:
        return re.sub(r'(href|src)="(?!https?:|mailto:|#|data:)([^"]+)"',
                      lambda m: f'{m[1]}="../{m[2]}"', fragment)

    def project(p: dict) -> str:
        stack = ''.join(f'<span>{esc(tag)}</span>' for tag in p['tags'])
        detail = ''
        if p.get('facets'):
            detail = '<details class="classic-evidence"><summary>Architecture, tradeoffs &amp; evidence</summary><ul class="case-study-details">'
            detail += ''.join(f'<li><strong>{esc(label)}:</strong> {relative(text)}</li>'
                              for label, text in p['facets'].items())
            detail += '</ul></details>'
            links = f'<a href="../work/{esc(p["slug"])}/">Full case study →</a> ' + relative(p['links_html'])
        else:
            links = f'<span>{esc(p["note"])}</span>'
        metric = f'<span class="case-study-metric">{esc(p["metric"])}</span>' if p.get('metric') else ''
        context = f'<p class="text-muted">{esc(p["metric_label"])}</p>' if p.get('metric_label') else ''
        return f'''<article class="case-study-card" id="project-{esc(p['slug'])}">
<div class="case-study-topline"><span class="case-study-label">{esc(p['status'])}</span>{metric}</div>
<h3>{esc(p['title'])}</h3><p>{esc(p['summary'])}</p>{context}{detail}
<div class="stack-list" aria-label="Technology stack">{stack}</div><div class="case-study-links">{links}</div></article>'''

    def post(p: dict) -> str:
        return f'''<article class="writing-card"><p class="writing-meta"><time datetime="{esc(p['date'])}">{esc(p['dateLabel'])}</time> · {esc(p['sectionLabel'])}</p>
<h3><a href="..{esc(p['url'])}">{esc(p['title'])}</a></h3><p>{esc(p['summary'])}</p></article>'''

    ordered = sorted(posts, key=lambda p: p['date'], reverse=True)
    writing = '<div class="writing-grid">' + ''.join(post(p) for p in ordered[:4]) + '</div>'
    if len(ordered) > 4:
        writing += f'<details class="classic-evidence mt-4"><summary>All {len(ordered)} posts</summary><div class="writing-grid mt-4">' + ''.join(post(p) for p in ordered[4:]) + '</div></details>'
    writing += '<p class="text-center mt-4"><a href="../blog/">Engineering Tales →</a> · <a href="../blog/rss.xml">RSS</a></p>'

    books = ''.join(f'<article class="side-card"><h3><a href="{esc(b["url"])}" target="_blank" rel="noopener">{esc(b["title"])}</a></h3><p>{esc(b["author"])}</p></article>' for b in data['books'])
    films = ''.join(f'<article class="side-card"><h3><a href="{esc(f["url"])}" target="_blank" rel="noopener">{esc(f["title"])} ({esc(f["year"])})</a></h3><p>{esc(f["type"])} · {esc(f["genres"])}</p></article>' for f in data['films'])
    essays = ''.join(f'<article class="side-card"><h3><a href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["title"])}</a></h3><p>{esc(e["description"])}</p></article>' for e in data['essays'])
    library = f'''<p class="section-intro text-muted mx-auto text-center">Away from work I read, keep film lists, make playlists and write at <a href="https://casuallyoverthinking.substack.com/">Casually Overthinking</a>.</p>
<h3>Books I would read again</h3><p><a href="{esc(data['personal_sources']['book_shelf'])}">My Goodreads shelf →</a></p><div class="side-grid">{books}</div>
<details class="classic-evidence mt-4"><summary>Films &amp; series I recommend · {len(data['films'])}</summary><p class="mt-3"><a href="{esc(data['personal_sources']['film_list'])}">My IMDb recommendations →</a></p><div class="side-grid">{films}</div></details>
<h3 class="mt-5">Other writing</h3><div class="side-grid">{essays}</div><p class="mt-4"><a href="../library/">Visit the Library with covers and posters →</a></p>'''
    # Five selected cases; the remaining work retains its full evidence below.
    replacements = {
        'BIO': relative(data['bio_html']),
        'RECORD': relative(data['record_html']),
        'CREDENTIALS': relative(data['credentials_html']),
        'SELECTED': ''.join(project(p) for p in data['projects'][:5]),
        'OTHER': ''.join(project(p) for p in data['projects'][5:]),
        'WRITING': writing,
        'LIBRARY': library,
    }
    template = (root / 'classic/template.html').read_text(encoding='utf-8')
    for key, value in replacements.items():
        template = template.replace(f'@@{key}@@', value)
    if re.search(r'@@[A-Z]+@@', template):
        raise ValueError('Classic template contains an unresolved content slot')
    return template
