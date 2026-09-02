"""Faz 35: kaynaklar/ilerleme, [[wikilink]] backlink'leri ve satir ici #etiket.

Ayristirici testleri veritabani istemez; akis testleri API uzerinden gider.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.refs import parse_tags, parse_wikilinks
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Ayristirici (DB'siz) ────────────────────────────────────────────────


@pytest.mark.no_database
def test_wikilink_parser_reads_targets_and_aliases() -> None:
    body = "Bugun [[Lineer Cebir]] ve [[Kalkulus|turev]] calistim. Yine [[Lineer Cebir]]."
    # Tekrar eden hedef bir kez doner; alias hedefi degistirmez.
    assert parse_wikilinks(body) == ["Lineer Cebir", "Kalkulus"]


@pytest.mark.no_database
def test_parsers_ignore_code_blocks_and_markdown_headings() -> None:
    body = (
        "# Baslik degil etiket degil\n"
        "## Alt baslik\n"
        "Gercek etiket: #matematik ve #linear-algebra\n"
        "URL icindeki cirpa etiket degil: https://site.com/#bolum\n"
        "```\n#kodicinde [[Baglanti]]\n```\n"
        "Satir ici `#kod` da sayilmaz.\n"
    )
    assert parse_tags(body) == ["matematik", "linear-algebra"]
    assert parse_wikilinks(body) == []


@pytest.mark.no_database
def test_tag_parser_accepts_turkish_letters() -> None:
    assert parse_tags("#çalışma #öğrenme #İstatistik") == ["çalışma", "öğrenme", "İstatistik"]


# ── Kaynaklar ve ilerleme ───────────────────────────────────────────────


async def test_resources_drive_topic_progress_across_subtopics(client: AsyncClient) -> None:
    area = (await client.post("/api/study/areas", json={"title": "Matematik"})).json()
    parent = (
        await client.post("/api/study/topics", json={"title": "Cebir", "area_id": area["id"]})
    ).json()
    child = (
        await client.post(
            "/api/study/topics",
            json={"title": "Matrisler", "area_id": area["id"], "parent_id": parent["id"]},
        )
    ).json()

    async def add(topic_id: str, title: str) -> dict:
        response = await client.post(
            f"/api/study/topics/{topic_id}/resources",
            json={"title": title, "url": f"https://example.com/{title}", "kind": "video"},
        )
        assert response.status_code == 201
        return response.json()

    first = await add(parent["id"], "giris")
    await add(child["id"], "carpim")

    # Hicbiri tamamlanmadi.
    progress = (await client.get(f"/api/study/topics/{parent['id']}/progress")).json()
    assert progress == {"total": 2, "done": 0, "pct": 0}

    # Ust konunun ilerlemesi ALT konunun kaynagini da sayar.
    done = await client.patch(f"/api/learning/resources/{first['id']}", json={"completed": True})
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None
    assert (await client.get(f"/api/study/topics/{parent['id']}/progress")).json() == {
        "total": 2, "done": 1, "pct": 50,
    }
    # Alt konu kendi basina yalnizca kendi kaynagini gorur.
    assert (await client.get(f"/api/study/topics/{child['id']}/progress")).json() == {
        "total": 1, "done": 0, "pct": 0,
    }

    # Geri alinca yuzde de geri doner -- yuzde ayri kolonda tutulmuyor.
    await client.patch(f"/api/learning/resources/{first['id']}", json={"completed": False})
    assert (await client.get(f"/api/study/topics/{parent['id']}/progress")).json()["done"] == 0

    # Kaynak silinince toplam da duser (yuzde kaynaklarla tutarli kalir).
    assert (await client.delete(f"/api/learning/resources/{first['id']}")).status_code == 204
    assert (await client.get(f"/api/study/topics/{parent['id']}/progress")).json()["total"] == 1

    # Konu agaci ilerlemeyi tasir (arayuz her konu icin ayri istek atmaz).
    tree = (await client.get(f"/api/study/topics?area_id={area['id']}")).json()
    assert tree[0]["progress"] == {"total": 1, "done": 0, "pct": 0}


# ── Not: wikilink -> backlink, #etiket -> genel etiket havuzu ───────────


async def test_note_body_creates_backlinks_and_tags(client: AsyncClient) -> None:
    area = (await client.post("/api/study/areas", json={"title": "Alan"})).json()
    topic = (
        await client.post(
            "/api/study/topics", json={"title": "Grafik Teorisi", "area_id": area["id"]}
        )
    ).json()

    note = (
        await client.post(
            "/api/notes",
            json={
                "body": "[[Grafik Teorisi]] uzerine notlar. #matematik\n[[Olmayan Konu]] da var.",
                "tags": ["ders"],
            },
        )
    ).json()

    # Cozulen wikilink baglanir, cozulmeyen "unresolved" olarak doner.
    assert note["unresolved_links"] == ["Olmayan Konu"]
    # Elle verilen etiket ile govdedeki #etiket ayni havuzda birlesir.
    assert sorted(note["tags"]) == ["ders", "matematik"]

    # Konu tarafindan bakinca backlink gorunur.
    backlinks = (await client.get(f"/api/entities/{topic['id']}/backlinks")).json()
    assert [b["id"] for b in backlinks] == [note["id"]]

    # Graf ayni bagi kenar olarak dondurur.
    graph = (await client.get(f"/api/graph?focus={topic['id']}&depth=1")).json()
    assert {n["id"] for n in graph["nodes"]} >= {note["id"], topic["id"]}
    assert {"from": note["id"], "to": topic["id"], "relation": "mentions"} in graph["edges"]


async def test_editing_a_note_body_resyncs_links_and_keeps_manual_tags(
    client: AsyncClient,
) -> None:
    area = (await client.post("/api/study/areas", json={"title": "Alan2"})).json()
    topic = (
        await client.post("/api/study/topics", json={"title": "Diziler", "area_id": area["id"]})
    ).json()
    note = (
        await client.post(
            "/api/notes", json={"body": "[[Diziler]] hakkinda. #eski", "tags": ["elle"]}
        )
    ).json()
    assert sorted(note["tags"]) == ["elle", "eski"]

    # Govdeden wikilink ve #eski cikarildi: bag da etiket de gider,
    # elle eklenen etiket KALIR.
    updated = (
        await client.patch(f"/api/notes/{note['id']}", json={"body": "Artik baglanti yok."})
    ).json()
    assert updated["tags"] == ["elle"]
    assert (await client.get(f"/api/entities/{topic['id']}/backlinks")).json() == []


@pytest.mark.no_database
def test_derived_title_strips_markdown_syntax() -> None:
    from app.modules.note.service import derive_title

    # Markdown basligi listede "# ..." diye gorunmemeli.
    assert derive_title("# Git notlarım\n\ngövde") == "Git notlarım"
    assert derive_title("## Alt başlık") == "Alt başlık"
    assert derive_title("- [ ] yapılacak iş") == "yapılacak iş"
    assert derive_title("> alıntı") == "alıntı"
    assert derive_title("**kalın** giriş") == "kalın giriş"
    # Bos satirlar atlanir, ilk anlamli satir kazanir.
    assert derive_title("\n\n   \nasıl başlık") == "asıl başlık"
    assert derive_title("") == "Not"
    assert derive_title("###   ") == "Not"


async def test_course_listing_survives_double_entity_foreign_key(client: AsyncClient) -> None:
    """Regresyon: course'un entity'ye iki FK'si var (id + certificate_entity_id).

    `select(Course).join(Entity)` bu yuzden belirsizdi ve GET /courses 500
    donuyordu; testler yalnizca POST/PATCH ettigi icin yakalanmamisti.
    """
    created = await client.post("/api/courses", json={"title": "Lineer Cebir kursu"})
    assert created.status_code == 201

    listed = await client.get("/api/courses")
    assert listed.status_code == 200
    assert created.json()["id"] in {row["id"] for row in listed.json()}


# ── JSON ile konu agaci ice aktarma ─────────────────────────────────────

TREE = {
    "area": "Makine Öğrenmesi",
    "topics": [
        {
            "title": "Doğrusal Modeller",
            "status": "in_progress",
            "resources": [
                {"title": "ISLR bölüm 3", "url": "https://example.com/islr3", "kind": "book"},
                {"title": "Ders videosu", "url": "https://example.com/v1", "kind": "video"},
            ],
            "children": [
                {
                    "title": "Regularizasyon",
                    "resources": [
                        {"title": "Ridge & Lasso", "url": "https://example.com/ridge"}
                    ],
                }
            ],
        },
        {"title": "Ağaç Tabanlı Modeller"},
    ],
}


async def test_import_builds_tree_with_resources(client: AsyncClient) -> None:
    result = (await client.post("/api/study/import", json=TREE)).json()
    assert result["topics_created"] == 3
    assert result["resources_created"] == 3
    assert result["area_title"] == "Makine Öğrenmesi"

    tree = (await client.get(f"/api/study/topics?area_id={result['area_id']}")).json()
    titles = [node["title"] for node in tree]
    assert titles == ["Doğrusal Modeller", "Ağaç Tabanlı Modeller"]
    assert [c["title"] for c in tree[0]["children"]] == ["Regularizasyon"]
    # Ilerleme kaynaklardan turedi: ust konu alt agaci da sayar.
    assert tree[0]["progress"] == {"total": 3, "done": 0, "pct": 0}


async def test_reimporting_the_same_tree_creates_no_duplicates(client: AsyncClient) -> None:
    first = (await client.post("/api/study/import", json=TREE)).json()
    second = (
        await client.post("/api/study/import", json={**TREE, "area_id": first["area_id"]})
    ).json()

    # Ikinci yuklemede hicbir sey olusmaz; hepsi eslesir.
    assert second["topics_created"] == 0
    assert second["topics_matched"] == 3
    assert second["resources_created"] == 0
    assert second["resources_skipped"] == 3

    tree = (await client.get(f"/api/study/topics?area_id={first['area_id']}")).json()
    assert len(tree) == 2
    assert len(tree[0]["children"]) == 1


async def test_reimport_adds_only_the_new_branches(client: AsyncClient) -> None:
    first = (await client.post("/api/study/import", json=TREE)).json()
    grown = {
        "area_id": first["area_id"],
        "topics": [
            {
                # Ayni konu, fazla bosluk ve farkli harf buyuklugu -- yine eslesir.
                "title": "  doğrusal   modeller ",
                "resources": [
                    {"title": "ISLR bölüm 3", "url": "https://example.com/islr3"},
                    {"title": "Yeni makale", "url": "https://example.com/yeni"},
                ],
                "children": [{"title": "Lojistik Regresyon"}],
            }
        ],
    }
    result = (await client.post("/api/study/import", json=grown)).json()
    assert result["topics_matched"] == 1
    assert result["topics_created"] == 1  # yalniz Lojistik Regresyon
    assert result["resources_created"] == 1  # yalniz "Yeni makale"
    assert result["resources_skipped"] == 1


async def test_import_rejects_unknown_fields_and_oversized_trees(client: AsyncClient) -> None:
    # Bilinmeyen alan sessizce yutulmaz -- elde yazilmis JSON yanlis yerlesmesin.
    bad = await client.post(
        "/api/study/import",
        json={"area": "X", "topics": [{"title": "A", "renk": "kırmızı"}]},
    )
    assert bad.status_code == 422

    # Derinlik tavani.
    deep: dict = {"title": "d0"}
    node = deep
    for i in range(1, 8):
        node["children"] = [{"title": f"d{i}"}]
        node = node["children"][0]
    too_deep = await client.post("/api/study/import", json={"area": "Y", "topics": [deep]})
    assert too_deep.status_code == 422

    # Alan bilgisi olmadan yukleme reddedilir.
    no_area = await client.post("/api/study/import", json={"topics": [{"title": "A"}]})
    assert no_area.status_code == 422


# ── Pomodoro baglam adaylari ────────────────────────────────────────────


async def test_pomodoro_contexts_include_learning_and_exclude_closed_todos(
    client: AsyncClient,
) -> None:
    """Baglam listesi yalnizca gorevlerden ibaret degil (Faz 36).

    Calisma konusu ve ogrenme kaynagi da odaklanilabilir; kapanmis gorev
    listeye girmez -- bitmis ise odaklanilmaz.
    """
    area = (await client.post("/api/study/areas", json={"title": "Bağlam Alanı"})).json()
    topic = (
        await client.post("/api/study/topics", json={"title": "Odak Konusu", "area_id": area["id"]})
    ).json()
    resource = (
        await client.post(
            f"/api/study/topics/{topic['id']}/resources",
            json={"title": "Odak Kaynağı", "url": "https://example.com/odak"},
        )
    ).json()
    open_todo = (await client.post("/api/todos", json={"title": "Açık görev"})).json()
    done_todo = (await client.post("/api/todos", json={"title": "Biten görev"})).json()
    assert (
        await client.patch(f"/api/todos/{done_todo['id']}", json={"status": "done"})
    ).status_code == 200

    rows = (await client.get("/api/pomodoro/contexts")).json()
    by_id = {row["id"]: row for row in rows}

    assert by_id[topic["id"]]["type"] == "study_topic"
    assert by_id[resource["id"]]["type"] == "learning_resource"
    assert by_id[open_todo["id"]]["type"] == "todo"
    # Kapanmis gorev aday degil.
    assert done_todo["id"] not in by_id
    # Firsat (is ilani) hic aday degil.
    assert all(row["type"] != "opportunity" for row in rows)

    # Arama basliga gore daraltir ve ALAKAYA gore dizer: global aramanin
    # trigram esigi alakasiz kayitlari da yakalayabilir, gercek eslesme
    # listenin dibinde kalmamali.
    filtered = (await client.get("/api/pomodoro/contexts?q=Odak Konusu")).json()
    assert filtered[0]["id"] == topic["id"]
    assert open_todo["id"] not in {row["id"] for row in filtered}

    # Kaynak da aranabilir.
    by_resource = (await client.get("/api/pomodoro/contexts?q=Odak Kaynağı")).json()
    assert by_resource[0]["id"] == resource["id"]


async def test_started_session_reports_its_context_type(client: AsyncClient) -> None:
    """Seans, baglaminin tipini de dondurur -- arayuz rozeti bundan cizer."""
    area = (await client.post("/api/study/areas", json={"title": "Tip Alanı"})).json()
    topic = (
        await client.post("/api/study/topics", json={"title": "Tipli Konu", "area_id": area["id"]})
    ).json()
    started = (
        await client.post(
            "/api/pomodoro/start", json={"planned_min": 1, "context_entity_id": topic["id"]}
        )
    ).json()
    assert started["context_type"] == "study_topic"
    assert started["context_title"] == "Tipli Konu"
    await client.post(f"/api/pomodoro/{started['id']}/stop", json={"interrupted": False})
