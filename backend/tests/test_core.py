"""Cekirdek helper testleri. DB gerektirmez -- saf fonksiyonlar."""
from app.modules.bookmark.service import normalize_url, url_hash


def test_normalize_strips_tracking_params():
    assert normalize_url("https://WWW.Example.com/post/?utm_source=x&id=5") == \
        "https://example.com/post?id=5"


def test_normalize_drops_fragment_and_trailing_slash():
    assert normalize_url("https://example.com/a/#section") == "https://example.com/a"


def test_same_url_same_hash():
    """www, takip parametresi ve sondaki / dedup'i bozmamali."""
    assert url_hash("https://example.com/a/") == \
        url_hash("https://www.example.com/a?utm_medium=y")


def test_different_url_different_hash():
    assert url_hash("https://example.com/a") != url_hash("https://example.com/b")


def test_meaningful_query_is_kept():
    """?v=... YouTube'da sayfanin kimligi -- atilirsa tum videolar ayni olur."""
    a = url_hash("https://youtube.com/watch?v=abc")
    b = url_hash("https://youtube.com/watch?v=def")
    assert a != b
