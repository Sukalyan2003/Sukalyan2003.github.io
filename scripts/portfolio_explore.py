"""Static markup for the portfolio's browser-local interactions."""
from __future__ import annotations

import html
import json


def esc(value):
    return html.escape(str(value), quote=True)


# Connections name shared tools or mechanisms already described in the cases.
CONNECTIONS = [
    ('eeg-platform', 'eeg-benchmark', 'EEG processing'),
    ('eeg-platform', 'medipredict', 'FastAPI'),
    ('eeg-platform', 'newstrellis', 'FastAPI'),
    ('local-retrieval', 'internal-rag', 'Local document retrieval'),
    ('local-retrieval', 'tempo', 'Local inference'),
    ('tempo', 'premiere-assist', 'Limits on model actions'),
    ('premiere-assist', 'nand2tetris', 'Python'),
    ('newstrellis', 'internal-rag', 'Python ingestion'),
]


def map_card(project):
    slug = project['slug']
    href = f'work/{slug}/' if project.get('facets') else f'work/#project-{slug}'
    return f'''<span class="eyebrow">{esc(project['status'])}</span>
<h3>{esc(project.get('headline', project['title']))}</h3><p>{esc(project['summary'])}</p>
<p class="map-metric">{esc(project.get('metric', project['note'] if 'note' in project else ''))}{f"<span>{esc(project['metric_label'])}</span>" if project.get("metric_label") else ""}</p>
<a class="text-link" href="{href}">{'Read the case study' if project.get('facets') else 'Read the project summary'} →</a>'''


def project_map(data):
    projects = {p['slug']: p for p in data['projects']}
    names = [(p['slug'], p.get('map_label', p['title'])) for p in data['projects']]
    connections = [(a, b, label) for a, b, label in CONNECTIONS if a in projects and b in projects]
    first_slug, first_name = names[0]
    initial_links = dict.fromkeys(label for a, b, label in connections if first_slug in (a, b))
    initial_connections = ' · '.join(initial_links)
    height = ((len(names) + 2) // 3) * 136
    positions = {slug: (100 + i % 3 * 200, 63 + i // 3 * 136) for i, (slug, _) in enumerate(names)}
    lines = []
    for source, target, label in connections:
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        middle_x, middle_y = (x1 + x2) / 2, (y1 + y2) / 2
        if x1 == x2 and abs(y2 - y1) > 136:
            middle_x -= 120  # route around the intermediate node
        if y1 == y2 and abs(x2 - x1) > 200:
            middle_y -= 110
        lines.append(f'<path d="M {x1} {y1} Q {middle_x} {middle_y} {x2} {y2}" fill="none" data-from="{source}" data-to="{target}" data-connection="{esc(label)}"/>')
    buttons = ''.join(f'''<button type="button" class="map-node" data-project="{slug}" aria-pressed="{'true' if i == 0 else 'false'}" aria-controls="map-detail" tabindex="{'0' if i == 0 else '-1'}"><span class="map-node__number">{i + 1:02d}</span><span>{esc(name)}</span></button>''' for i, (slug, name) in enumerate(names))
    templates = ''.join(f'<template data-project-card="{slug}">{map_card(projects[slug])}</template>' for slug, _ in names)
    return f'''<section class="project-atlas" data-enhance hidden aria-labelledby="atlas-title">
<div class="atlas-heading"><div><span class="eyebrow">Explore the projects</span><h2 id="atlas-title">Projects, connected.</h2></div><p>Pick a project to see what connects it to the others. Use the arrow keys to move around the map.</p></div>
<div class="atlas-layout"><div><div class="project-map" role="group" aria-label="Project map">
<svg class="map-lines" viewBox="0 0 600 {height}" preserveAspectRatio="none" aria-hidden="true">{''.join(lines)}</svg>{buttons}</div>
<p class="map-connections" data-map-connections>Connections: {esc(initial_connections)}</p></div>
<aside class="map-detail" id="map-detail" aria-label="Selected project">{map_card(projects[first_slug])}</aside></div>
<p class="sr-only" role="status" data-map-status>{esc(first_name)} selected.</p>{templates}</section>'''


def find_dialog(prefix, data, posts):
    entries = [
        {'title': 'Home', 'kind': 'Page', 'url': prefix or './', 'terms': 'Sukalyan Roy portfolio'},
        {'title': 'All projects', 'kind': 'Page', 'url': prefix + 'work/', 'terms': 'work backend systems data'},
        {'title': 'About & experience', 'kind': 'Page', 'url': prefix + 'about/', 'terms': 'cv resume education reading films music'},
        {'title': 'Library', 'kind': 'Page', 'url': prefix + 'library/', 'terms': 'personal books reading Goodreads films IMDb recommendations Substack essays'},
        {'title': 'Engineering Tales', 'kind': 'Page', 'url': prefix + 'blog/', 'terms': 'writing blog'},
    ]
    for p in data['projects']:
        route = f"work/{p['slug']}/" if p.get('facets') else f"work/#project-{p['slug']}"
        entries.append({'title': p['title'], 'kind': 'Project', 'url': prefix + route,
                        'terms': ' '.join(p['tags']) + ' ' + p['summary']})
    for post in posts:
        tag_names = [t.get('label', t.get('slug', '')) if isinstance(t, dict) else t for t in post.get('tags', [])]
        entries.append({'title': post['title'], 'kind': 'Writing', 'url': prefix + f"blog/{post['slug']}/", 'terms': ' '.join(tag_names)})
    encoded = json.dumps(entries, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<dialog class="find-dialog" id="find-dialog" aria-labelledby="find-title"><div class="dialog-heading"><h2 id="find-title">Find something</h2><button class="quiet-button" data-dialog-close type="button">Close ×</button></div>
<label class="sr-only" for="site-query">Search projects and writing</label><input type="search" id="site-query" placeholder="Projects, tools, writing…" autocomplete="off" aria-describedby="find-help find-count">
<p id="find-help">Type to search. Use ↓ to reach the results, then Enter to open one.</p><p id="find-count" role="status">Projects and writing</p>
<ul id="find-results" aria-label="Search results"><li>Type a project, tool or topic above.</li></ul><p data-find-empty hidden>No matches. Try a tool such as Python, or a topic such as EEG.</p>
</dialog><script type="application/json" id="find-index">{encoded}</script>'''


def print_dialog():
    return '''<dialog class="print-dialog" id="print-dialog" aria-labelledby="print-title"><div class="dialog-heading"><div><span class="eyebrow">The printing press</span><h2 id="print-title">Make a different impression.</h2></div><button class="quiet-button" data-dialog-close type="button">Close ×</button></div>
<div class="print-layout"><div class="print-stage"><p data-print-loading role="status">Loading the photograph…</p><canvas width="440" height="440" data-print-canvas hidden role="img" aria-label="Halftone portrait of Sukalyan Roy">Halftone portrait of Sukalyan Roy.</canvas></div>
<div class="print-settings"><p>A photograph becomes dots of ink. Change their spacing and contrast, or switch back to the photo.</p>
<label for="print-spacing">Dot spacing <output for="print-spacing" id="print-spacing-value">8 px</output></label><input type="range" id="print-spacing" min="4" max="20" value="8" step="1">
<label for="print-contrast">Contrast <output for="print-contrast" id="print-contrast-value">1.0×</output></label><input type="range" id="print-contrast" min="0.5" max="1.8" value="1" step="0.1">
<fieldset><legend>Ink</legend><label><input type="radio" name="print-ink" value="black" checked> Black</label><label><input type="radio" name="print-ink" value="red"> Red</label></fieldset>
<button class="quiet-button" data-print-photo type="button" aria-pressed="false">Show photograph</button>
<div class="print-actions"><button class="quiet-button" data-print-reset type="button">Reset</button><button class="quiet-button" data-print-save type="button">Save PNG ↓</button></div>
<p class="print-note">Made here in your browser.</p></div></div></dialog>'''


DOCUMENTS = {
    'cancel': 'Cancelling a request',
    'window': 'Windowed EEG',
    'queue': 'Background jobs',
    'header': 'Reading a file header',
}
DENSE = ['cancel', 'window', 'queue', 'header']
SPARSE = ['window', 'header', 'cancel', 'queue']


def fusion_demo():
    lists = []
    for key, label, order in [('dense', 'Semantic search', DENSE), ('sparse', 'Exact-term search', SPARSE)]:
        items = ''.join(f'''<li data-doc="{doc}" tabindex="-1"><span class="rank-position">{i + 1:02d}</span><span>{DOCUMENTS[doc]}</span><button type="button" class="rank-up" data-move-up="{doc}" data-enhance hidden aria-label="Move {DOCUMENTS[doc]} up in {label.lower()}"{' disabled' if i == 0 else ''}>↑</button></li>''' for i, doc in enumerate(order))
        lists.append(f'<section class="retriever-list"><h3>{label}</h3><ol data-ranking="{key}">{items}</ol></section>')
    ranked = sorted(DOCUMENTS, key=lambda doc: (-(1 / (61 + DENSE.index(doc)) + 1 / (61 + SPARSE.index(doc))), doc))
    result = []
    for doc in ranked:
        dense, sparse = DENSE.index(doc) + 1, SPARSE.index(doc) + 1
        score = 1 / (60 + dense) + 1 / (60 + sparse)
        result.append(f'''<li data-result="{doc}"><strong>{DOCUMENTS[doc]}</strong><output>{score:.6f}</output><span data-result-ranks>Semantic #{dense} · Exact-term #{sparse}</span><svg viewBox="0 0 200 4" preserveAspectRatio="none" aria-hidden="true"><rect width="{score / .04 * 200:.2f}" height="4"/></svg></li>''')
    return f'''<div class="explainer fusion-lab" data-demo="fusion"><span class="eyebrow">Try rank fusion · example documents</span><h2>Two rankings. Which result comes first?</h2>
<p>Semantic search matches meaning. Exact-term search matches words. They can disagree. Rearrange the four example documents and watch Reciprocal Rank Fusion combine their positions.</p>
<div class="fusion-switches" data-enhance hidden role="group" aria-label="Active retrievers"><label><input type="checkbox" data-retriever="dense" checked> Semantic</label><label><input type="checkbox" data-retriever="sparse" checked> Exact-term</label><button class="quiet-button" data-fusion-reset type="button">Reset rankings</button></div>
<p class="rank-instruction" data-enhance hidden>Drag a row within a list, or use its ↑ button to move it up.</p><div class="retriever-pair">{''.join(lists)}</div>
<section class="fusion-output"><div class="fusion-output__heading"><h3>The combined ranking</h3><span>Higher score first</span></div><ol class="fusion-results">{''.join(result)}</ol><p data-fusion-empty hidden>Enable a retriever to build a combined ranking.</p></section>
<p class="fusion-formula" data-fusion-formula>Top result: 1 / (60 + 2) + 1 / (60 + 1) = 0.032522</p>
<p class="sr-only" role="status" data-fusion-status>Windowed EEG ranks first.</p>
<p class="explainer-note">Each active retriever contributes 1 / (60 + rank). The constant 60 matches the linked implementation. These documents and rankings are illustrative; this does not rerun the project's 18-query regression set.</p></div>'''


def personal_shelves(data, prefix):
    sections = []
    sources = data.get('personal_sources', {})
    books = data.get('books', [])
    if books:
        cards = ''.join(f'''<li data-shelf-item><a class="book-card" href="{esc(book['url'])}" target="_blank" rel="noopener" aria-labelledby="book-{i}"><div class="book-cover"><img src="{prefix}{esc(book['image'])}" width="{book['width']}" height="{book['height']}" loading="lazy" decoding="async" alt="Cover of {esc(book['title'])}"></div><h4 id="book-{i}">{esc(book['title'])}</h4><p>{esc(book['author'])}</p></a></li>''' for i, book in enumerate(books))
        sections.append(shelf('books', 'Books I’d read again', sources['books'], 'All Goodreads shelves', cards))
    films = data.get('films', [])
    if films:
        cards = []
        for film in films:
            kind = 'film' if film['type'] == 'Movie' else 'series'
            runtime = f" · {film['runtime']} min" if kind == 'film' and film.get('runtime') else ''
            cards.append(f'''<li data-shelf-item data-film-type="{kind}"><a class="film-ticket" href="{esc(film['url'])}" target="_blank" rel="noopener"><div class="ticket-stub"><span>{esc(film['year'])}</span><span>{'Film' if kind == 'film' else 'Series'}{esc(runtime)}</span></div><span class="ticket-number" aria-hidden="true">No. {film['position']:02d}</span><h4>{esc(film['title'])}</h4><p class="ticket-director">{esc(film.get('director', '')) or 'Television series'}</p><p class="ticket-genres">{esc(film['genres'])}</p><span class="ticket-link">On IMDb ↗</span></a></li>''')
        film_controls = '<div class="film-options" data-enhance hidden><label for="film-kind">Show</label><select id="film-kind" data-film-filter><option value="all">Films &amp; series</option><option value="film">Films</option><option value="series">Series</option></select><button class="quiet-button" type="button" data-shelf-surprise>Surprise me ↗</button></div>'
        sections.append(shelf('films', 'Films & series I recommend', sources['film_list'], 'Full IMDb list', ''.join(cards), film_controls))
    essays = data.get('essays', [])
    if essays:
        cards = ''.join(f'''<article><span class="eyebrow">Casually Overthinking</span><h4><a href="{esc(post['url'])}" target="_blank" rel="noopener">{esc(post['title'])}</a></h4><p>{esc(post['description'])}</p></article>''' for post in essays)
        sections.append(f'''<section class="personal-essays"><div class="shelf-heading"><h3>Other things I write about</h3><a href="https://casuallyoverthinking.substack.com/" target="_blank" rel="noopener">All of Casually Overthinking ↗</a></div><div class="reading-pair">{cards}</div></section>''')
    return ''.join(sections)


def shelf(key, title, url, link_label, cards, extra=''):
    return f'''<section class="personal-shelf" data-shelf role="region" aria-roledescription="carousel" aria-labelledby="{key}-heading"><div class="shelf-heading"><h3 id="{key}-heading">{esc(title)}</h3><a href="{esc(url)}" target="_blank" rel="noopener">{link_label} ↗</a></div>{extra}
<div class="shelf-controls" data-enhance hidden><button class="quiet-button" type="button" data-shelf-prev aria-label="Previous {key}" aria-controls="{key}-track" disabled>←</button><output data-shelf-position aria-live="polite">Browse the shelf</output><button class="quiet-button" type="button" data-shelf-next aria-label="Next {key}" aria-controls="{key}-track">→</button></div>
<ul class="shelf-track" id="{key}-track" data-shelf-track tabindex="0" aria-label="{esc(title)}. Scroll horizontally to browse.">{cards}</ul></section>'''
