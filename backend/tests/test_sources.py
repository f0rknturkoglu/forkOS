"""RSS parse ve OPML testleri. Ag'a cikmaz."""
from app.sources.opml import parse_opml
from app.sources.rss_source import item_guid, parse_entries

RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Ornek Blog</title>
  <item>
    <title>Ilk yazi</title>
    <link>https://ornek.dev/1</link>
    <guid>https://ornek.dev/1</guid>
    <description>Merhaba dunya</description>
    <pubDate>Tue, 03 Jun 2025 09:00:00 GMT</pubDate>
    <author>yazar@ornek.dev</author>
  </item>
  <item>
    <title>Guid'siz yazi</title>
    <link>https://ornek.dev/2</link>
  </item>
</channel></rss>"""

OPML = b"""<?xml version="1.0"?>
<opml version="1.0"><body>
  <outline text="AI/LLM">
    <outline text="Anthropic" xmlUrl="https://anthropic.com/rss" htmlUrl="https://anthropic.com"/>
    <outline text="Yinelenen" xmlUrl="https://anthropic.com/rss"/>
  </outline>
  <outline text="Development">
    <outline text="Bir Blog" xmlUrl="https://blog.dev/feed"/>
  </outline>
  <outline text="Kategorisiz" xmlUrl="https://tek.dev/feed"/>
</body></opml>"""


def test_parse_entries_reads_fields():
    items = parse_entries(RSS)
    assert len(items) == 2
    first = items[0]
    assert first.title == "Ilk yazi"
    assert first.url == "https://ornek.dev/1"
    assert first.external_id == "https://ornek.dev/1"
    assert first.published_at is not None
    assert "Merhaba" in (first.summary or "")


def test_guid_falls_back_to_hash():
    """GUID'i olmayan feed'ler dedup'i bozmasin."""
    items = parse_entries(RSS)
    assert items[1].external_id == item_guid(None, "https://ornek.dev/2", "Guid'siz yazi")
    assert len(items[1].external_id) == 64


def test_opml_categories_come_from_folders():
    feeds = parse_opml(OPML)
    by_url = {f.url: f for f in feeds}
    assert by_url["https://anthropic.com/rss"].category == "AI/LLM"
    assert by_url["https://blog.dev/feed"].category == "Development"
    # Klasor icinde olmayan feed'in kategorisi yoktur
    assert by_url["https://tek.dev/feed"].category is None


def test_opml_deduplicates_urls():
    assert len(parse_opml(OPML)) == 3


def test_opml_keeps_site_url():
    feeds = {f.url: f for f in parse_opml(OPML)}
    assert feeds["https://anthropic.com/rss"].site_url == "https://anthropic.com"
