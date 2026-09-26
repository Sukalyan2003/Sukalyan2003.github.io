"""Settings for the /blog section. Edit here, then rebuild.

Everything the generator needs to know that is not content lives in this one
file, so changing the site URL, the comment backend or the page size never
means editing template code.
"""

from __future__ import annotations

from datetime import timedelta, timezone

SITE_URL = "https://sukalyan2003.github.io"
BLOG_NAME = "Engineering Tales"
# The author's own one-line description of the blog (from the Start here page).
BLOG_DESCRIPTION = (
    "A technical lab notebook: RAG systems, interpreters, Nand2Tetris, Linux, "
    "ML experiments, and project breakdowns."
)

AUTHOR_NAME = "Sukalyan Roy"
AUTHOR_ROLE = "Backend Engineer · Python, Data & ML Systems"
AUTHOR_LOCATION = "Kolkata, India"
AUTHOR_LINKS = {
    "GitHub": "https://github.com/Sukalyan2003",
    "LinkedIn": "https://www.linkedin.com/in/sukalyan-roy-457040362/",
}
# The Person node already declared in the front page's JSON-LD.
PERSON_ID = f"{SITE_URL}/#person"
WEBSITE_ID = f"{SITE_URL}/#website"

# Where the posts came from. Used only for the migration map and for rewriting
# old internal links; nothing at runtime depends on it.
HASHNODE_HOST = "sukalyanroy.hashnode.dev"

# Dates are shown in the author's timezone. India has no DST, so a fixed
# offset is exact and keeps the build independent of the host's tz database.
DISPLAY_TZ = timezone(timedelta(hours=5, minutes=30))

FRONT_PAGE_COUNT = 5      # lead story + two per side column on /blog/
POSTS_PER_PAGE = 10       # archive rows per page after the front-page block
WORDS_PER_MINUTE = 230
TOC_MIN_HEADINGS = 4      # a table of contents appears at this many h2/h3
RELATED_COUNT = 3
IMAGE_WIDTHS = (480, 960, 1440)
RSS_ITEMS = 20            # newest posts in rss.xml (full text); keeps the feed a steady size

# Original images in content/ are optimised when added (import, publish,
# `blog.py optimize`): capped in width, photo-like images stored as
# high-quality lossy WebP, screenshots and diagrams as lossless WebP (only
# when that is actually smaller). Metadata such as EXIF/GPS is dropped.
MAX_ORIGINAL_WIDTH = 2400
PHOTO_QUALITY = 90
OG_SIZE = (1200, 630)

# Mermaid diagrams (```mermaid fences) are rendered to SVG at build time by
# mermaid-cli via npx, once per theme, and cached in content/<kind>/diagrams/.
# Readers get static images; Node is needed only when a diagram changes.
MERMAID_CLI = "@mermaid-js/mermaid-cli@12.0.0"
_MERMAID_COMMON = {
    "theme": "base",
    "look": "classic",
    "htmlLabels": False,  # plain SVG text: renders the same inside an <img>
    "flowchart": {"htmlLabels": False},
}
_MONO = "ui-monospace, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
MERMAID_THEMES = {
    "paper": {**_MERMAID_COMMON, "themeVariables": {
        "fontFamily": _MONO, "fontSize": "14px", "background": "#f4f1ea",
        "primaryColor": "#f4f1ea", "primaryTextColor": "#17140f", "primaryBorderColor": "#17140f",
        "secondaryColor": "#eae5da", "tertiaryColor": "#eae5da", "lineColor": "#5a5348",
        "textColor": "#17140f", "edgeLabelBackground": "#f4f1ea", "noteBkgColor": "#eae5da",
        "noteTextColor": "#17140f", "noteBorderColor": "#8a8274",
    }},
    "press": {**_MERMAID_COMMON, "themeVariables": {
        "fontFamily": _MONO, "fontSize": "14px", "background": "#14120e",
        "primaryColor": "#14120e", "primaryTextColor": "#e9e3d6", "primaryBorderColor": "#e9e3d6",
        "secondaryColor": "#1c1915", "tertiaryColor": "#1c1915", "lineColor": "#a39b8b",
        "textColor": "#e9e3d6", "edgeLabelBackground": "#14120e", "noteBkgColor": "#1c1915",
        "noteTextColor": "#e9e3d6", "noteBorderColor": "#786f60",
    }},
}

# Comments via giscus (GitHub Discussions). Leave repo_id/category_id empty
# and the comments block is simply omitted. To enable: turn on Discussions for
# the repo, install https://github.com/apps/giscus, then copy the IDs that
# https://giscus.app shows for this repo and category.
GISCUS = {
    "repo": "Sukalyan2003/Sukalyan2003.github.io",
    "repo_id": "",
    "category": "Comments",
    "category_id": "",
}

# Likes / view counts are deferred until a backend exists. Set this to the
# endpoint base URL to enable them; the templates render nothing while None.
REACTIONS_ENDPOINT: str | None = None
