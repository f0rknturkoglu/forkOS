"""Medya metadata aramasi: iTunes/RAWG yanit normalizasyonu (saf fonksiyon testleri).

Live API cagrisi yok; yalnizca yanit -> MetadataResult eslemesi test edilir.
"""
import pytest

from app.modules.media.service import (
    _bigger_artwork,
    _itunes_results,
    _kitsu_results,
    _rawg_results,
)


def test_bigger_artwork_scales_thumb_to_200px():
    url = "https://is1-ssl.mzstatic.com/image/thumb/abc/100x100bb.jpg"
    assert _bigger_artwork(url) == "https://is1-ssl.mzstatic.com/image/thumb/abc/200x200bb.jpg"


def test_itunes_results_maps_podcast_row():
    payload = {"results": [
        {
            "collectionName": "Syntax",
            "artistName": "Wes Bos",
            "collectionId": 502174510,
            "artworkUrl100": "https://is5-ssl.mzstatic.com/image/thumb/x/100x100bb.jpg",
        },
        {"trackName": "Yalniz track", "trackId": 7},
    ]}
    rows = _itunes_results(payload, "podcast")
    assert len(rows) == 2
    first = rows[0]
    assert first.title == "Syntax"
    assert first.subtitle == "Wes Bos"
    assert first.cover_url.endswith("200x200bb.jpg")
    assert first.metadata == {
        "source": "itunes", "itunes_id": 502174510, "itunes_kind": "podcast",
    }
    assert rows[1].metadata["itunes_id"] == 7


def test_itunes_results_falls_back_on_empty_rows():
    assert _itunes_results({"results": []}, "music") == []


def test_rawg_results_maps_game_row():
    payload = {"results": [
        {
            "id": 3498,
            "slug": "grand-theft-auto-v",
            "name": "Grand Theft Auto V",
            "released": "2013-09-17",
            "background_image": "https://media.rawg.io/media/games/x.jpg",
        },
    ]}
    rows = _rawg_results(payload)
    assert len(rows) == 1
    row = rows[0]
    assert row.title == "Grand Theft Auto V"
    assert row.subtitle == "2013-09-17"
    assert row.cover_url == "https://media.rawg.io/media/games/x.jpg"
    assert row.metadata == {
        "source": "rawg", "rawg_id": 3498, "rawg_slug": "grand-theft-auto-v",
    }


def test_rawg_results_drops_missing_cover():
    rows = _rawg_results({"results": [{"id": 1, "slug": "s", "name": "N"}]})
    assert rows[0].cover_url is None


@pytest.mark.parametrize("kind", ["music", "podcast", "audiobook"])
def test_itunes_results_keeps_kind_in_metadata(kind):
    rows = _itunes_results({"results": [{"collectionName": "X"}]}, kind)
    assert rows[0].metadata["itunes_kind"] == kind
    assert rows[0].metadata["source"] == "itunes"


def test_kitsu_results_maps_manga_row():
    payload = {"data": [
        {
            "id": "58159",
            "attributes": {
                "canonicalTitle": "Sakamoto Days",
                "chapterCount": 180,
                "startDate": "2020-11-21",
                "posterImage": {"medium": "https://media.kitsu.io/manga/poster_images/58159/medium.jpg"},
            },
        },
    ]}
    rows = _kitsu_results(payload, "manga")
    assert len(rows) == 1
    row = rows[0]
    assert row.title == "Sakamoto Days"
    assert row.subtitle == "180 bolum"
    assert row.cover_url == "https://media.kitsu.io/manga/poster_images/58159/medium.jpg"
    assert row.metadata == {"source": "kitsu", "kitsu_id": "58159", "kitsu_kind": "manga"}


def test_kitsu_results_falls_back_to_start_date_without_episode_count():
    rows = _kitsu_results({"data": [
        {"id": "1", "attributes": {"canonicalTitle": "A", "startDate": "2015-10-04"}},
    ]}, "anime")
    assert rows[0].subtitle == "2015-10-04"


def test_kitsu_results_drops_missing_poster():
    rows = _kitsu_results({"data": [
        {"id": "1", "attributes": {"canonicalTitle": "A"}},
    ]}, "anime")
    assert rows[0].cover_url is None
