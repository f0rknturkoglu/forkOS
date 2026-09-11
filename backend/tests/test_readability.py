from __future__ import annotations

import pytest
from app.core.readability import extract_article

pytestmark = pytest.mark.no_database

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Gelecegin Yazilim Mimarileri</title>
    <meta property="og:title" content="Gelecegin Yazilim Mimarileri ve Kisisel Sistemler">
    <meta property="og:image" content="https://example.com/hero.jpg">
    <meta name="author" content="Ahmet Yilmaz">
    <meta property="article:published_time" content="2026-09-10T14:30:00Z">
    <link rel="icon" href="/favicon.ico">
    <style>.ad { display: none; }</style>
    <script>alert('noise');</script>
</head>
<body>
    <header><nav><a href="/">Ana Sayfa</a></nav></header>
    <article>
        <h1>Gelecegin Yazilim Mimarileri ve Kisisel Sistemler</h1>
        <p class="lead">Yerel oncelikli mimariler gunumuzde buyuk onem kazandi.</p>
        <p>Verilerin kullanicinin kendi cihazinda kalmasi hem gizlilik hem de hiz saglar. Bu yazida yerel veri tabanlarinin avantajlarini detaylica ele alacagiz.</p>
        <div class="ad"><a href="http://spam.com">Reklam Linki</a></div>
        <blockquote>Basitlik, karmasikligin onune gecmelidir.</blockquote>
        <img src="https://example.com/diagram.png" alt="Mimari Diyagram" onclick="evil()">
    </article>
    <footer><p>Telif Hakki 2026</p></footer>
</body>
</html>
"""


def test_extract_article_metadata():
    article = extract_article(SAMPLE_HTML, base_url="https://example.com/blog/article-1")
    assert article is not None
    assert article.title == "Gelecegin Yazilim Mimarileri ve Kisisel Sistemler"
    assert article.author == "Ahmet Yilmaz"
    assert article.hero_image_url == "https://example.com/hero.jpg"
    assert article.favicon_url == "https://example.com/favicon.ico"
    assert article.published_at is not None
    assert article.word_count > 20
    assert article.reading_time_min >= 1


def test_extract_article_content_cleanliness():
    article = extract_article(SAMPLE_HTML, base_url="https://example.com/blog/article-1")
    assert article.content_html is not None
    assert article.content_text is not None
    # Script, style, nav, footer temizlenmis olmali
    assert "<script" not in article.content_html.lower()
    assert "<style" not in article.content_html.lower()
    assert "<nav" not in article.content_html.lower()
    assert "onclick" not in article.content_html.lower()
    # Govde metinleri yer almali
    assert "Yerel oncelikli mimariler" in article.content_text
    assert "Basitlik, karmasikligin onune gecmelidir" in article.content_text
    # Reklamlar ve noise ayiklanmis olmali
    assert "Reklam Linki" not in article.content_text


def test_extract_article_handles_empty_and_short_html():
    article = extract_article("<html><body><p>Kisa</p></body></html>")
    assert article.title is None or article.title == ""
    assert article.word_count == 1
    assert article.reading_time_min == 1
