#!/usr/bin/env python3
"""Record poster URLs for the Library films; the images themselves are never downloaded.

    python3 scripts/resolve_posters.py

Each film's IMDb ID is matched to its English Wikipedia article through Wikidata
(property P345), and the article's lead image becomes the poster. Only the image URL
and its size are written to content/portfolio.json; visitors' browsers load the
picture from upload.wikimedia.org. Films without a match keep the typographic ticket.
Rerun after changing the film list. Uses only the standard library.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / 'content/portfolio.json'
# Wikimedia asks API clients to identify themselves.
USER_AGENT = 'SukalyanRoyPortfolio/1.0 (https://sukalyan2003.github.io/; sukalyanroyofficial@gmail.com)'


def get_json(url: str, params: dict, accept: str = 'application/json') -> dict:
    request = urllib.request.Request(f'{url}?{urllib.parse.urlencode(params)}',
                                     headers={'User-Agent': USER_AGENT, 'Accept': accept})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def imdb_id(url: str) -> str:
    match = re.fullmatch(r'https://www\.imdb\.com/title/(tt\d+)/', url)
    if not match:
        raise ValueError(f'Unexpected IMDb URL: {url}')
    return match.group(1)


def wikipedia_titles(ids: list[str]) -> dict[str, str]:
    values = ' '.join(f'"{i}"' for i in ids)
    query = ('SELECT ?imdb ?article WHERE { VALUES ?imdb { ' + values + ' } ?item wdt:P345 ?imdb . '
             '?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }')
    data = get_json('https://query.wikidata.org/sparql', {'query': query}, 'application/sparql-results+json')
    titles: dict[str, str] = {}
    for row in data['results']['bindings']:
        title = urllib.parse.unquote(row['article']['value'].rsplit('/wiki/', 1)[1]).replace('_', ' ')
        titles.setdefault(row['imdb']['value'], title)
    return titles


def lead_images(titles: list[str]) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for start in range(0, len(titles), 50):
        batch = titles[start:start + 50]
        data = get_json('https://en.wikipedia.org/w/api.php', {
            'action': 'query', 'format': 'json', 'formatversion': 2, 'redirects': 1,
            'prop': 'pageimages', 'piprop': 'thumbnail', 'pithumbsize': 300,
            # Film posters are usually non-free files, which the API omits by default.
            'pilicense': 'any', 'titles': '|'.join(batch)})
        query = data.get('query', {})
        renamed = {item['to']: item['from'] for key in ('normalized', 'redirects') for item in query.get(key, [])}
        for page in query.get('pages', []):
            thumb = page.get('thumbnail')
            if not thumb:
                continue
            title = page['title']
            while title in renamed:
                title = renamed[title]
            found[title] = {'poster': thumb['source'].split('?', 1)[0],
                            'poster_width': thumb['width'], 'poster_height': thumb['height']}
    return found


def main() -> int:
    data = json.loads(CONTENT.read_text(encoding='utf-8'))
    films = data['films']
    titles = wikipedia_titles([imdb_id(film['url']) for film in films])
    images = lead_images(sorted(set(titles.values())))
    matched = 0
    for film in films:
        for key in ('poster', 'poster_width', 'poster_height'):
            film.pop(key, None)
        image = images.get(titles.get(imdb_id(film['url']), ''))
        if image:
            film.update(image)
            matched += 1
        else:
            print(f'no poster: {film["title"]} ({film["url"]})')
    data['personal_sources']['posters'] = (
        f'Poster URLs resolved {date.today().isoformat()} from Wikidata (IMDb ID) and English '
        'Wikipedia lead images; the images load from upload.wikimedia.org.')
    CONTENT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{matched} of {len(films)} films have a poster.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
