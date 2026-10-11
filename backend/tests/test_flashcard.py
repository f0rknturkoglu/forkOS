"""Flashcard modulu testleri: SM-2 zamanlama, deck/kart CRUD, ic aktarim.

Modül registry'de aktiftir. Bu testler kart sözleşmelerini ayrı mini FastAPI
uygulamasında /api prefix'iyle doğrudan doğrular.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.time import local_datetime, local_today
from app.db import SessionLocal
from app.modules.flashcard.router import router as flashcard_router

# "test" ile baslamamali yoksa pytest bunu bir test olarak toplamaya calisir.
flashcard_test_app = FastAPI()
flashcard_test_app.include_router(flashcard_router, prefix="/api")


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=flashcard_test_app), base_url="http://test"
    ) as http:
        yield http


def day_due(days: int) -> datetime:
    """Bugun + `days` gun (yerel gun basi), UTC'ye cevrilmis."""
    return local_datetime(local_today() + timedelta(days=days)).astimezone(UTC)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


async def grade(client: AsyncClient, card_id: str, value: int) -> dict:
    """Karti tekrar eder; basarisizsa testi patlatir."""
    response = await client.post(f"/api/flashcard/cards/{card_id}/review", json={"grade": value})
    assert response.status_code == 200
    return response.json()


async def make_deck(client: AsyncClient, title: str = "Test Destek") -> dict:
    response = await client.post("/api/flashcard/decks", json={"title": title})
    assert response.status_code == 201
    return response.json()


async def make_card(client: AsyncClient, deck_id: str, front: str, back: str) -> dict:
    response = await client.post(
        f"/api/flashcard/decks/{deck_id}/cards", json={"front": front, "back": back}
    )
    assert response.status_code == 201
    return response.json()


def build_apkg(cards: list[tuple[str, str]], deck_name: str = "Almanca") -> bytes:
    """Test icin minimal Anki paketi (zip + collection.anki2, Basic tip)."""
    with tempfile.TemporaryDirectory() as directory:
        db_path = os.path.join(directory, "collection.anki2")
        con = sqlite3.connect(db_path)
        con.executescript(
            "create table decks (id integer primary key, name text);"
            "create table notes (id integer primary key, flds text);"
            "create table cards (id integer primary key, nid integer, did integer);"
        )
        con.execute("insert into decks values (1, ?)", (deck_name,))
        for index, (front, back) in enumerate(cards):
            con.execute("insert into notes values (?, ?)", (100 + index, json.dumps([front, back])))
            con.execute("insert into cards values (?, ?, 1)", (1000 + index, 100 + index))
        con.commit()
        con.close()
        with open(db_path, "rb") as handle:
            raw = handle.read()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("collection.anki2", raw)
    return buffer.getvalue()


def build_real_anki_apkg(
    cards: list[tuple[str, str]],
    deck_name: str = "Oxford 5000",
    *,
    qfmt: str = "<b>{{Front}}</b>",
    afmt: str = "{{FrontSide}}<hr id=answer><i>{{Back}}</i>",
) -> bytes:
    """Gercek Anki 2.0/2.1 semasina sahip paket (col tablosu, JSON decks/models, \x1f ayracli flds)."""
    with tempfile.TemporaryDirectory() as directory:
        db_path = os.path.join(directory, "collection.anki2")
        con = sqlite3.connect(db_path)
        con.executescript(
            "create table col (id integer primary key, crt integer, mod integer, scm integer, ver integer, dty integer, usn integer, ls integer, conf text, models text, decks text, dconf text, tags text);"
            "create table notes (id integer primary key, guid text, mid integer, mod integer, usn integer, tags text, flds text, sfld text, csum integer, flags integer, data text);"
            "create table cards (id integer primary key, nid integer, did integer, ord integer, mod integer, usn integer, type integer, queue integer, due integer, ivl integer, factor integer, reps integer, lapses integer, left integer, odue integer, odid integer, flags integer, data text);"
        )
        decks = {
            "1": {"id": 1, "name": "Default"},
            "1636867553462": {"id": 1636867553462, "name": deck_name},
        }
        models = {
            "100": {
                "id": 100,
                "name": "TestModel",
                "flds": [{"name": "Front", "ord": 0}, {"name": "Back", "ord": 1}],
                "tmpls": [{"name": "Card 1", "ord": 0, "qfmt": qfmt, "afmt": afmt}],
            }
        }
        con.execute(
            "insert into col (id, decks, models) values (1, ?, ?)",
            (json.dumps(decks), json.dumps(models)),
        )
        for index, (front, back) in enumerate(cards):
            con.execute(
                "insert into notes (id, mid, flds) values (?, 100, ?)",
                (100 + index, f"{front}\x1f{back}"),
            )
            con.execute(
                "insert into cards (id, nid, did, ord) values (?, ?, 1636867553462, 0)",
                (1000 + index, 100 + index),
            )
        con.commit()
        con.close()
        with open(db_path, "rb") as handle:
            raw = handle.read()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("collection.anki2", raw)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Deck / kart CRUD
# ---------------------------------------------------------------------------


async def test_deck_crud(client: AsyncClient) -> None:
    created = await client.post("/api/flashcard/decks", json={"title": "Almanca"})
    assert created.status_code == 201
    deck = created.json()
    assert deck["title"] == "Almanca"
    assert (deck["card_count"], deck["due_count"], deck["new_count"]) == (0, 0, 0)

    listed = (await client.get("/api/flashcard/decks")).json()
    assert [item["id"] for item in listed] == [deck["id"]]

    patched = await client.patch(
        f"/api/flashcard/decks/{deck['id']}", json={"title": "Almanca II"}
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Almanca II"

    missing = await client.patch(
        "/api/flashcard/decks/00000000-0000-0000-0000-000000000000", json={"title": "yok"}
    )
    assert missing.status_code == 404

    assert (await client.delete(f"/api/flashcard/decks/{deck['id']}")).status_code == 204
    assert (await client.get("/api/flashcard/decks")).json() == []


async def test_card_crud_and_deck_counts(client: AsyncClient) -> None:
    deck = await make_deck(client, "Tarih")
    card = await client.post(
        f"/api/flashcard/decks/{deck['id']}/cards",
        json={"front": "1453", "back": "İstanbul fethedildi"},
    )
    assert card.status_code == 201
    data = card.json()
    assert data["front"] == "1453"
    assert data["interval_days"] == 0
    assert data["ease"] == 2.5
    assert data["due_at"] is None
    assert data["reps"] == 0
    assert data["suspended"] is False

    listed = (await client.get("/api/flashcard/decks")).json()
    assert listed[0]["card_count"] == 1
    assert listed[0]["new_count"] == 1
    assert listed[0]["due_count"] == 0

    cards = (await client.get(f"/api/flashcard/decks/{deck['id']}/cards")).json()
    assert len(cards) == 1

    patched = await client.patch(
        f"/api/flashcard/cards/{data['id']}",
        json={"back": "Konstantinopolis düştü", "suspended": True},
    )
    assert patched.status_code == 200
    assert patched.json()["back"] == "Konstantinopolis düştü"
    assert patched.json()["suspended"] is True

    assert (
        await client.delete(f"/api/flashcard/cards/{data['id']}")
    ).status_code == 204
    assert (await client.get(f"/api/flashcard/decks/{deck['id']}/cards")).json() == []

    # Destek silinince kartlari da cascade silinir; kayip destege kart 404.
    assert (await client.delete(f"/api/flashcard/decks/{deck['id']}")).status_code == 204
    missing = await client.post(
        f"/api/flashcard/decks/{deck['id']}/cards",
        json={"front": "x", "back": "y"},
    )
    assert missing.status_code == 404


# ---------------------------------------------------------------------------
# SM-2 zamanlama (deterministik: gun bazli hesaplar local_today uzerinden)
# ---------------------------------------------------------------------------


async def test_review_sm2_new_card_grades(client: AsyncClient) -> None:
    deck = await make_deck(client, "SM2 Yeni")

    easy = await make_card(client, deck["id"], "kolay", "k")
    result = await grade(client, easy["id"], 3)
    assert result["interval_days"] == 4
    assert parse_dt(result["due_at"]) == day_due(4)

    good = await make_card(client, deck["id"], "iyi", "k")
    result = await grade(client, good["id"], 2)
    assert result["interval_days"] == 1
    assert parse_dt(result["due_at"]) == day_due(1)

    hard = await make_card(client, deck["id"], "zor", "k")
    result = await grade(client, hard["id"], 1)
    assert result["interval_days"] == 1
    assert parse_dt(result["due_at"]) == day_due(1)

    again = await make_card(client, deck["id"], "tekrar", "k")
    result = await grade(client, again["id"], 0)
    assert result["interval_days"] == 0
    delta = (parse_dt(result["due_at"]) - datetime.now(UTC)).total_seconds()
    assert 9 * 60 <= delta <= 11 * 60


async def test_review_sm2_sequence(client: AsyncClient) -> None:
    deck = await make_deck(client, "SM2 Dizi")
    card = await make_card(client, deck["id"], "soru", "cevap")

    # Yeni kart, Good: 1 gun, ease degismez.
    result = await grade(client, card["id"], 2)
    assert result["interval_days"] == 1
    assert parse_dt(result["due_at"]) == day_due(1)

    # Good: interval x ease (2.5) -> 2.5 -> 3.
    result = await grade(client, card["id"], 2)
    assert result["interval_days"] == 3

    # Again: x0.5 -> 1.5 -> 2, ease -0.20.
    result = await grade(client, card["id"], 0)
    assert result["interval_days"] == 2
    assert parse_dt(result["due_at"]) == day_due(2)

    # Hard: x1.2 -> 2.4 -> 2, ease -0.15.
    result = await grade(client, card["id"], 1)
    assert result["interval_days"] == 2

    # Easy: x ease (2.15) x 1.3 -> 5.59 -> 6, ease +0.15.
    result = await grade(client, card["id"], 3)
    assert result["interval_days"] == 6

    state = (await client.get(f"/api/flashcard/decks/{deck['id']}/cards")).json()[0]
    assert state["reps"] == 5
    assert state["lapses"] == 1
    assert state["ease"] == 2.3


async def test_review_unknown_card_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/flashcard/cards/00000000-0000-0000-0000-000000000000/review", json={"grade": 2}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tekrar sirasi ve sayaclar
# ---------------------------------------------------------------------------


async def test_due_queue_orders_due_before_new(client: AsyncClient) -> None:
    deck = await make_deck(client, "Kuyruk")
    due = await make_card(client, deck["id"], "vadesi gecmis", "k")
    new_one = await make_card(client, deck["id"], "yeni 1", "k")
    new_suspended = await make_card(client, deck["id"], "askida", "k")
    future = await make_card(client, deck["id"], "gelecek", "k")

    # future karti tekrar et -> vadesi gelecege (bugun + 1 gun) gitsin.
    await client.post(f"/api/flashcard/cards/{future['id']}/review", json={"grade": 2})
    # due karti vadesi gecmis yap + new_suspended'i askiya al (dogrudan DB).
    await client.patch(f"/api/flashcard/cards/{new_suspended['id']}", json={"suspended": True})
    async with SessionLocal() as session:
        await session.execute(
            text("update flashcard_card set due_at = now() - interval '1 day' where id = :id"),
            {"id": due["id"]},
        )
        await session.commit()

    queue = (
        await client.get(f"/api/flashcard/decks/{deck['id']}/cards", params={"due": "1"})
    ).json()
    ids = [card["id"] for card in queue]
    assert ids[0] == due["id"]  # vadesi gecen once
    assert ids[1:] == [new_one["id"]]  # sonra yeni; askiya alinan ve gelecek vade yok

    summary = (await client.get("/api/flashcard/decks")).json()[0]
    assert summary["card_count"] == 4
    assert summary["due_count"] == 1
    assert summary["new_count"] == 1  # askıdaki yeni kart çalışma kuyruğunda değildir


async def test_cards_of_missing_deck_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/flashcard/decks/00000000-0000-0000-0000-000000000000/cards"
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Ic aktarim: CSV / TXT / APKG
# ---------------------------------------------------------------------------


async def test_import_csv_creates_and_reuses_deck(client: AsyncClient) -> None:
    content = "front,back\nMerhaba,Hello\nDünya,World\n".encode()
    response = await client.post(
        "/api/flashcard/import",
        files={"file": ("kartlar.csv", content, "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["added"] == 2
    assert data["skipped"] == 0
    assert data["deck_title"] == "İçe Aktarılan Kartlar"

    # Ayni isimli destek MEVCUTSA yenisini kurma, mevcuda ekle.
    again = await client.post(
        "/api/flashcard/import",
        files={"file": ("kartlar.csv", content, "text/csv")},
    )
    assert again.json()["deck_id"] == data["deck_id"]
    deck = (await client.get("/api/flashcard/decks")).json()[0]
    assert deck["card_count"] == 4


async def test_import_csv_with_deck_name_and_txt_tabs(client: AsyncClient) -> None:
    content = "Merhaba,Hello\nDünya,World\n".encode()
    response = await client.post(
        "/api/flashcard/import",
        params={"deck": "Dil"},
        files={"file": ("kartlar.csv", content, "text/csv")},
    )
    assert response.json()["deck_title"] == "Dil"
    assert response.json()["added"] == 2

    tabbed = "Merhaba\tHello\nDünya\tWorld\n".encode()
    response = await client.post(
        "/api/flashcard/import",
        files={"file": ("kartlar.txt", tabbed, "text/plain")},
    )
    data = response.json()
    assert data["added"] == 2
    cards = (await client.get(f"/api/flashcard/decks/{data['deck_id']}/cards")).json()
    assert {card["front"] for card in cards} == {"Merhaba", "Dünya"}


async def test_import_apkg(client: AsyncClient) -> None:
    payload = build_apkg([("Haus", "Ev"), ("Apfel", "Elma")])
    response = await client.post(
        "/api/flashcard/import",
        files={"file": ("kartlar.apkg", payload, "application/octet-stream")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["added"] == 2
    assert data["deck_title"] == "Almanca"  # apkg icindeki destek adi kullanilir

    cards = (await client.get(f"/api/flashcard/decks/{data['deck_id']}/cards")).json()
    assert {card["front"] for card in cards} == {"Haus", "Apfel"}

    # Deck parametresi apkg destek adini ezer.
    overridden = await client.post(
        "/api/flashcard/import",
        params={"deck": "Dil"},
        files={"file": ("kartlar.apkg", payload, "application/octet-stream")},
    )
    assert overridden.json()["deck_title"] == "Dil"
    assert overridden.json()["deck_id"] != data["deck_id"]


async def test_import_real_anki_apkg(client: AsyncClient) -> None:
    """Gercek Anki paketleri (col.decks JSON, notes \x1f ayraci, HTML sablonlar) basariyla aktarilir."""
    payload = build_real_anki_apkg(
        [("abandon", "terk etmek"), ("ability", "yetenek")],
        deck_name="Oxford 5000",
    )
    response = await client.post(
        "/api/flashcard/import",
        files={"file": ("Oxford.apkg", payload, "application/octet-stream")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["added"] == 2
    assert data["skipped"] == 0
    assert data["deck_title"] == "Oxford 5000"

    cards = (await client.get(f"/api/flashcard/decks/{data['deck_id']}/cards")).json()
    # HTML etiketleri Markdown'a cevrilmis olmali
    assert {card["front"] for card in cards} == {"**abandon**", "**ability**"}
    assert {card["back"] for card in cards} == {"*terk etmek*", "*yetenek*"}


async def test_import_apkg_template_rendering_and_html_cleaning(client: AsyncClient) -> None:
    """HTML etiketleri temizlenir, kosullu sablonlar ve cloze dogru render edilir."""
    payload = build_real_anki_apkg(
        [
            (
                "<div><b>Hello</b> <script>alert(1)</script>world</div>",
                "<p>Merhaba <i>dunya</i></p><br><hr id=answer>Ekstra",
            )
        ],
        deck_name="HTML Deste",
        qfmt="<div style='color: red;'>{{Front}}</div>",
        afmt="{{FrontSide}}<hr id=answer><div style='font-size: 16px;'>{{Back}}</div>",
    )
    response = await client.post(
        "/api/flashcard/import",
        files={"file": ("html.apkg", payload, "application/octet-stream")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["added"] == 1
    cards = (await client.get(f"/api/flashcard/decks/{data['deck_id']}/cards")).json()
    card = cards[0]
    assert "<script>" not in card["front"]
    assert "<div" not in card["front"]
    assert "**Hello** world" in card["front"]
    assert "Merhaba *dunya*" in card["back"]
    assert "{{FrontSide}}" not in card["back"]


async def test_import_invalid_apkg_400(client: AsyncClient) -> None:
    response = await client.post(
        "/api/flashcard/import",
        files={"file": ("bozuk.apkg", b"not a zip", "application/octet-stream")},
    )
    assert response.status_code == 400


async def test_reversible_card_creates_both_directions(client: AsyncClient) -> None:
    """Cift yonlu kart: on->arka ve arka->on ayni desteye girer."""
    deck = await make_deck(client, "Ters Kartlar")

    created = await client.post(
        f"/api/flashcard/decks/{deck['id']}/cards",
        json={"front": "Haus", "back": "Ev", "reversible": True},
    )
    assert created.status_code == 201
    assert created.json()["front"] == "Haus"

    cards = (await client.get(f"/api/flashcard/decks/{deck['id']}/cards")).json()
    assert {(card["front"], card["back"]) for card in cards} == {("Haus", "Ev"), ("Ev", "Haus")}


async def test_reversible_same_text_does_not_duplicate(client: AsyncClient) -> None:
    """On ve arka ayniysa ters kart uretilmez (kopya kuyruk olmasin)."""
    deck = await make_deck(client, "Ayni Yuz")

    await client.post(
        f"/api/flashcard/decks/{deck['id']}/cards",
        json={"front": "Ankara", "back": "Ankara", "reversible": True},
    )

    cards = (await client.get(f"/api/flashcard/decks/{deck['id']}/cards")).json()
    assert len(cards) == 1


async def test_only_lapses_filter_and_search(client: AsyncClient) -> None:
    """`only_lapses` yalnizca unutulan kartlari, `q` metin eslesmesini suzer."""
    deck = await make_deck(client, "Zayif Noktalar")
    hard = (
        await client.post(f"/api/flashcard/decks/{deck['id']}/cards", json={"front": "Zor", "back": "Hard"})
    ).json()
    await client.post(f"/api/flashcard/decks/{deck['id']}/cards", json={"front": "Kolay", "back": "Easy"})
    await grade(client, hard["id"], 0)  # "Yine" -> lapses 1

    lapses = (await client.get(
        f"/api/flashcard/decks/{deck['id']}/cards", params={"only_lapses": True}
    )).json()
    assert [card["front"] for card in lapses] == ["Zor"]
    assert lapses[0]["lapses"] == 1

    searched = (await client.get(
        f"/api/flashcard/decks/{deck['id']}/cards", params={"q": "kolay"}
    )).json()
    assert [card["front"] for card in searched] == ["Kolay"]


async def test_cram_missed_orders_by_lapses_across_decks(client: AsyncClient) -> None:
    """Cram kuyrugu desteler genelinde en cok unutulani basa alir."""
    first = await make_deck(client, "Deste Bir")
    second = await make_deck(client, "Deste Iki")
    once = (
        await client.post(f"/api/flashcard/decks/{first['id']}/cards", json={"front": "Bir", "back": "One"})
    ).json()
    twice = (
        await client.post(f"/api/flashcard/decks/{second['id']}/cards", json={"front": "Iki", "back": "Two"})
    ).json()
    await grade(client, once["id"], 0)
    await grade(client, twice["id"], 0)
    await grade(client, twice["id"], 0)

    queue = (await client.get("/api/flashcard/cram/missed")).json()

    assert [card["front"] for card in queue] == ["Iki", "Bir"]
    assert {card["deck_title"] for card in queue} == {"Deste Bir", "Deste Iki"}


async def test_decks_linked_to_note(client: AsyncClient) -> None:
    """`linked_to` yalnizca o kayda bagli desteyi doner (not -> deste bagi)."""
    linked = await make_deck(client, "Notun Kartlari")
    await make_deck(client, "Bagimsiz")

    async with SessionLocal() as session:
        note_id = (
            await session.execute(
                text(
                    "insert into entity (type, title, search_text) values ('note', 'Kaynak not', '') "
                    "returning id"
                )
            )
        ).scalar_one()
        await session.execute(
            text(
                "insert into link (from_id, to_id, relation) values (:deck, :note, 'studies')"
            ),
            {"deck": linked["id"], "note": note_id},
        )
        await session.commit()

    filtered = (await client.get("/api/flashcard/decks", params={"linked_to": str(note_id)})).json()
    assert [deck["title"] for deck in filtered] == ["Notun Kartlari"]

    # Bag yoksa bos doner (panel cizilmez).
    async with SessionLocal() as session:
        other_id = (
            await session.execute(
                text("insert into entity (type, title, search_text) values ('note', 'Baska not', '') returning id")
            )
        ).scalar_one()
        await session.commit()
    assert (await client.get("/api/flashcard/decks", params={"linked_to": str(other_id)})).json() == []


async def test_deck_out_reports_mature_count(client: AsyncClient) -> None:
    """SRS dagilim cubugu icin olgun kart sayisi (interval > 21 gun) doner."""
    deck = await make_deck(client, "Olgun Destek")
    card = (
        await client.post(f"/api/flashcard/decks/{deck['id']}/cards", json={"front": "Yasli", "back": "Old"})
    ).json()
    # Uzun araliga cikar: 4 -> 10 -> 25 gun (Kolay kolay).
    await grade(client, card["id"], 3)
    await grade(client, card["id"], 3)
    await grade(client, card["id"], 3)

    listed = (await client.get("/api/flashcard/decks")).json()
    assert listed[0]["mature_count"] == 1
