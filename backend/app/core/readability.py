"""Mozilla Pocket tarzi yerel icerik ve makale govdesi cikarici.

selectolax (Lexbor) parser'i ile HTML temizligi, gurultu ayiklama, hero gorsel,
yazar, tahmini okuma suresi ve guvenli HTML/metin cikarimi yapar.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlsplit

from selectolax.parser import HTMLParser, Node

_NOISE_SELECTORS = (
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "form",
    "nav",
    "footer",
    "header",
    "aside",
    "noscript",
    "svg",
    "button",
    "input",
    "select",
    "textarea",
    ".ad",
    ".ads",
    ".advertisement",
    ".social-share",
    ".share-buttons",
)

_ARTICLE_SELECTORS = (
    "article",
    "[role='main']",
    "[itemprop='articleBody']",
    "main",
    ".post-content",
    ".entry-content",
    ".article-content",
    ".article-body",
    "#article-body",
    "#content",
)

_OPEN_TAG = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)([^<>]*)>")


@dataclass
class ArticleContent:
    title: str | None = None
    content_html: str | None = None
    content_text: str | None = None
    hero_image_url: str | None = None
    favicon_url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    word_count: int = 0
    reading_time_min: int = 1


def _sanitize_attributes(html: str, base_url: str = "") -> str:
    def fix(match: re.Match) -> str:
        tag = match.group(1).lower()
        attrs = match.group(2)

        if tag == "img":
            src = re.search(r'\bsrc\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', attrs, re.I)
            alt = re.search(r'\balt\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', attrs, re.I)
            if not src:
                return "<img>"
            src_val = src.group(1).strip("\"'")
            if base_url and not src_val.startswith(("http://", "https://", "data:")):
                src_val = urljoin(base_url, src_val)
            if not src_val.startswith(("http://", "https://", "data:")):
                return "<img>"
            alt_val = f' alt="{alt.group(1).strip(chr(34) + chr(39))}"' if alt else ""
            return f'<img src="{src_val}"{alt_val}>'
        elif tag == "a":
            href = re.search(r'\bhref\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', attrs, re.I)
            if not href:
                return "<a>"
            href_val = href.group(1).strip("\"'")
            if base_url and not href_val.startswith(("http://", "https://", "mailto:")):
                href_val = urljoin(base_url, href_val)
            if not href_val.startswith(("http://", "https://", "mailto:")):
                return "<a>"
            return f'<a href="{href_val}" target="_blank" rel="noreferrer noopener">'

        return f"<{tag}>"

    return _OPEN_TAG.sub(fix, html)


def _find_candidate(root: Node) -> Node:
    for selector in _ARTICLE_SELECTORS:
        candidate = root.css_first(selector)
        if candidate is not None:
            return candidate

    # En cok <p> iceren govde blogu
    best, best_count = None, 0
    for node in root.css("div, section"):
        count = len(node.css("p"))
        if count > best_count:
            best_count, best = count, node
    body = root.css_first("body")
    return best or body or root


def extract_article(html: str | bytes, base_url: str = "") -> ArticleContent:
    if not html:
        return ArticleContent()

    parser = HTMLParser(html)
    root = parser.root
    if root is None:
        return ArticleContent()

    # Metadata cikarimi (Title, Hero image, Author, Date, Favicon)
    title = None
    og_title = root.css_first("meta[property='og:title'], meta[name='twitter:title']")
    if og_title and og_title.attributes.get("content"):
        title = og_title.attributes["content"].strip()
    elif root.css_first("title"):
        title = root.css_first("title").text().strip()

    hero_image_url = None
    og_image = root.css_first("meta[property='og:image'], meta[name='twitter:image']")
    if og_image and og_image.attributes.get("content"):
        raw_img = og_image.attributes["content"].strip()
        hero_image_url = urljoin(base_url, raw_img) if base_url else raw_img

    author = None
    author_el = root.css_first("meta[name='author'], meta[property='article:author']")
    if author_el and author_el.attributes.get("content"):
        author = author_el.attributes["content"].strip()

    published_at = None
    time_el = root.css_first("meta[property='article:published_time'], time[datetime]")
    if time_el:
        raw_date = time_el.attributes.get("content") or time_el.attributes.get("datetime")
        if raw_date:
            try:
                published_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            except Exception:
                pass

    favicon_url = None
    fav_el = root.css_first("link[rel~='icon']")
    if fav_el and fav_el.attributes.get("href"):
        fav_raw = fav_el.attributes["href"].strip()
        favicon_url = urljoin(base_url, fav_raw) if base_url else fav_raw
    elif base_url:
        parts = urlsplit(base_url)
        if parts.scheme and parts.netloc:
            favicon_url = f"{parts.scheme}://{parts.netloc}/favicon.ico"

    # Gurultu temizligi
    for selector in _NOISE_SELECTORS:
        for node in root.css(selector):
            node.decompose()

    candidate = _find_candidate(root)
    raw_html = candidate.html.strip() if candidate.html else ""
    content_html = _sanitize_attributes(raw_html, base_url)

    content_text = candidate.text(separator=" ").strip() if candidate else ""
    content_text = re.sub(r"\s+", " ", content_text).strip()

    words = len(content_text.split()) if content_text else 0
    reading_time = max(1, math.ceil(words / 200)) if words > 0 else 1

    return ArticleContent(
        title=title,
        content_html=content_html,
        content_text=content_text,
        hero_image_url=hero_image_url,
        favicon_url=favicon_url,
        author=author,
        published_at=published_at,
        word_count=words,
        reading_time_min=reading_time,
    )


async def fetch_and_extract(url: str) -> ArticleContent | None:
    """Verilen URL'den makale HTML'ini ceker ve ayiklar."""
    if not url.startswith(("http://", "https://")):
        return None

    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                return extract_article(resp.content, base_url=str(resp.url))
    except Exception:
        pass
    return None
