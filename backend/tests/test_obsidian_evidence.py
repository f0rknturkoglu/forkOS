"""H3 kasa kanıt primitifleri — salt-okunurluk, determinizm ve konum dürüstlüğü.

Bu testler ajan katmanına dokunmaz: `obsidian/evidence.py` Vault tarafının
yetkili yeridir ve kendi sınırlarını kendi kanıtlar.
"""

from __future__ import annotations

import os
from pathlib import Path

from app.integrations.obsidian.evidence import (
    MAX_VAULT_SCAN_FILES,
    Excerpt,
    build_sections,
    extract_excerpt,
    extract_wikilinks,
    find_backlinks,
    is_evidence_path,
    normalize_text,
    read_note_lines,
    resolve_wikilink,
    scan_evidence_notes,
    tokenize_query,
)
from tests.agent_test_utils import (
    forbid_outbound_network,  # noqa: F401  (autouse: H3 dış ağ çağrısı yapmaz)
)


def _write(vault: Path, rel_path: str, content: str) -> Path:
    target = vault / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _fingerprint(vault: Path) -> dict[str, tuple[bytes, int]]:
    """Kasa içeriği + mtime; salt-okunurluk kanıtı için."""
    result: dict[str, tuple[bytes, int]] = {}
    for root, dirs, files in os.walk(vault):
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            path = Path(root) / name
            stat = path.stat()
            result[str(path.relative_to(vault))] = (path.read_bytes(), stat.st_mtime_ns)
    return result


# ---------------------------------------------------------------------------
# Yol politikası
# ---------------------------------------------------------------------------


def test_evidence_path_excludes_hot_memory_and_hidden(tmp_path: Path) -> None:
    assert is_evidence_path("30 Knowledge/Rust.md") is True
    assert is_evidence_path("90 Agent/Memory/abc.md") is False
    assert is_evidence_path("90 Agent/Memory-x/abc.md") is True
    assert is_evidence_path("90 agent/memory/abc.md") is False
    assert is_evidence_path(".obsidian/workspace.md") is False
    assert is_evidence_path("20 Projects/attachments/a.md") is False


# ---------------------------------------------------------------------------
# Sorgu kelimeleri
# ---------------------------------------------------------------------------


def test_tokenize_query_normalizes_dedupes_and_bounds() -> None:
    terms = tokenize_query("  Why  RUST rust  C# —   ve  ")
    assert terms.tokens == ("rust", "c#")
    assert terms.used_fallback is False
    assert terms.phrase == "why rust rust c# — ve"

    long_query = " ".join(f"kelime{i}" for i in range(20))
    assert len(tokenize_query(long_query).tokens) == 12


def test_tokenize_query_keeps_short_meaningful_tokens() -> None:
    assert "go" in tokenize_query("go or rust").tokens
    assert "ai" in tokenize_query("ai strategy").tokens


def test_tokenize_query_falls_back_when_only_stopwords() -> None:
    terms = tokenize_query("ve ile için the and")
    assert terms.used_fallback is True
    assert set(terms.tokens) == {"ve", "ile", "icin", "the", "and"}


def test_normalize_text_is_accent_and_case_insensitive() -> None:
    assert normalize_text("İSTANBUL") == "istanbul"
    assert normalize_text("ş") == "s"
    assert normalize_text("ﬁle") == "file"
    assert normalize_text("  Rust  ") == "  rust  "


# ---------------------------------------------------------------------------
# Wikilink çıkarımı
# ---------------------------------------------------------------------------


def test_extract_wikilinks_forms_and_exclusions() -> None:
    lines = [
        "Bağlantı [[Rust]] ve [[Rust|alias]] ve [[30 Knowledge/Rust#Karar|K]].",
        "Gömülü ![[image.png]] sayılmaz.",
        "```",
        "[[Kod içinde|kod]]",
        "```",
        "Satır içi `[[kod satiri]]` sayılmaz.",
        "",
    ]
    assert extract_wikilinks(lines) == ("Rust", "30 Knowledge/Rust")


def test_extract_wikilinks_is_deterministic_and_deduped() -> None:
    lines = ["[[B]] [[a]] [[B]] [[A#Başlık]] [[C|alias]]"]
    assert extract_wikilinks(lines) == ("B", "a", "C")


# ---------------------------------------------------------------------------
# Bölümler ve snippet konumu
# ---------------------------------------------------------------------------


def test_build_sections_maps_headings_to_line_ranges() -> None:
    lines = ["---", "title: X", "---", "# Not", "", "Giriş", "", "## Karar", "", "Rust seçildi.", ""]
    sections = build_sections(lines, 3)
    assert [(s.heading, s.start, s.end) for s in sections] == [
        ("Not", 3, 5),
        ("Karar", 7, 9),
    ]


def test_excerpt_line_numbers_reproduce_source_exactly(tmp_path: Path) -> None:
    """§28/§193: satır numaraları UYDURULMAZ; kesilmemiş snippet birebir çıkar."""
    vault = tmp_path / "Vault"
    vault.mkdir()
    body = "\n".join(
        ["---", "forkos_id: 5b3e5f0e-0000-4000-8000-000000000001", "---", "# Proje", "", "Giriş satırı."]
        + ["## Teknoloji Kararı", "", "Rust seçildi çünkü bellek güvenliği istendi.", ""]
        + [f"ilgisiz satır {i}" for i in range(3)]
    )
    path = _write(vault, "20 Projects/forkjob.md", body)

    lines = path.read_text(encoding="utf-8").split("\n")
    sections = build_sections(lines, 3)
    excerpt = extract_excerpt(lines, sections, tokenize_query("Rust kararı"), max_chars=1200)

    assert excerpt is not None
    assert excerpt.heading == "Teknoloji Kararı"
    assert excerpt.truncated is False
    assert excerpt.text == "\n".join(lines[excerpt.line_start - 1 : excerpt.line_end])
    assert "Rust seçildi" in excerpt.text
    assert excerpt.text not in body[: body.index("Rust seçildi")]


def test_excerpt_keeps_match_line_when_section_is_long() -> None:
    lines = ["# Not"] + [f"dolgu {i}" for i in range(200)] + ["Rust kararı burada.", ""] + [f"sonra {i}" for i in range(50)]
    sections = build_sections(lines, 0)
    excerpt = extract_excerpt(lines, sections, tokenize_query("Rust kararı"), max_chars=200)

    assert excerpt is not None
    assert excerpt.truncated is True
    assert "Rust kararı burada." in excerpt.text
    assert len(excerpt.text) <= 200
    assert excerpt.text == "\n".join(lines[excerpt.line_start - 1 : excerpt.line_end])


def test_excerpt_truncates_a_single_overlong_line() -> None:
    lines = ["# Not", "Rust " + "x" * 4000, ""]
    sections = build_sections(lines, 0)
    excerpt = extract_excerpt(lines, sections, tokenize_query("Rust"), max_chars=100)

    assert excerpt is not None
    assert excerpt.truncated is True
    assert excerpt.line_start == excerpt.line_end == 2
    assert lines[1].startswith(excerpt.text)


def test_excerpt_is_none_without_sections() -> None:
    assert extract_excerpt([], [], tokenize_query("Rust"), max_chars=100) is None


# ---------------------------------------------------------------------------
# Tarama
# ---------------------------------------------------------------------------


def test_scan_is_deterministic_bounded_and_excludes_memory(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/Rust.md", "# Rust\n\nRust bellek güvenliği.\n")
    _write(vault, "20 Projects/forkjob.md", "# forkjob\n\nRust projesi.\n")
    _write(vault, "90 Agent/Memory/secret-ish.md", "# Not\n\nRust burada gizli.\n")
    _write(vault, ".obsidian/workspace.md", "# Rust\n")
    _write(vault, "attachments/Rust.md", "# Rust\n")
    _write(vault, "notes.txt", "Rust\n")

    first = scan_evidence_notes(vault, tokenize_query("Rust"))
    second = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert [note.rel_path for note in first.notes] == [
        "20 Projects/forkjob.md",
        "30 Knowledge/Rust.md",
    ]
    assert [note.rel_path for note in second.notes] == [note.rel_path for note in first.notes]
    assert first.files_read == 2
    assert first.truncated is False
    assert all(note.score > 0 for note in first.notes)


def test_scan_reports_file_cap_honestly(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    for index in range(6):
        _write(vault, f"30 Knowledge/note-{index}.md", f"# Not {index}\n\nRust {index}\n")
    monkeypatch.setattr("app.integrations.obsidian.evidence.MAX_VAULT_SCAN_FILES", 3)

    index = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert index.truncated is True
    assert index.files_read == 3
    assert any("cap" in warning for warning in index.warnings)
    assert MAX_VAULT_SCAN_FILES == 500


def test_scan_reports_oversized_and_unreadable_files(tmp_path: Path, monkeypatch) -> None:
    """Sınırlar ve okunamayan dosyalar sessizce yutulmaz (§80).

    Okunamazlık izin bitleriyle DEĞİL, kırık bir sembolik bağla kurulur: root
    olarak çalışan ortamlarda `chmod 000` dosyayı yine okunur kılar ve test
    ortama bağlı hâle gelirdi.
    """
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/big.md", "# Büyük\n\nRust\n" + "x" * 500)
    monkeypatch.setattr("app.integrations.obsidian.evidence.MAX_VAULT_FILE_BYTES", 64)

    index = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert index.oversized_files == 1
    assert any("KiB" in warning for warning in index.warnings)

    # Kasa İÇİNE işaret eden ama var olmayan hedef: çözümleme geçer, dosya yok.
    (vault / "30 Knowledge" / "broken.md").symlink_to(vault / "30 Knowledge" / "missing.md")
    blocked = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert blocked.unreadable_files == 1
    assert any("could not be read" in warning for warning in blocked.warnings)
    assert all(note.rel_path != "30 Knowledge/broken.md" for note in blocked.notes)


def test_scan_survives_path_resolution_oserror(tmp_path: Path, monkeypatch) -> None:
    """Yol çözümlemesi OSError (ör. ELOOP) atsa bile tarama çökmez."""
    from app.integrations.obsidian import evidence as vault_evidence

    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/Rust.md", "# Rust\n")

    def _boom(*args, **kwargs):
        raise OSError("too many levels of symbolic links")

    monkeypatch.setattr(vault_evidence, "resolve_safe_vault_path", _boom)
    index = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert index.unreadable_files == 1
    assert index.notes == ()
    assert any("could not be read" in warning for warning in index.warnings)


def test_scan_skips_symlinks_escaping_the_vault(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Dışarı\n\nRust\n", encoding="utf-8")
    (vault / "30 Knowledge").mkdir()
    (vault / "30 Knowledge" / "escape.md").symlink_to(outside)
    _write(vault, "30 Knowledge/inside.md", "# İçeride\n\nRust\n")

    index = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert [note.rel_path for note in index.notes] == ["30 Knowledge/inside.md"]
    assert index.unreadable_files == 1


def test_scan_never_writes(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/Rust.md", "# Rust\n\n[[forkjob]]\n\nRust notu.\n")
    before = _fingerprint(vault)

    index = scan_evidence_notes(vault, tokenize_query("Rust"))
    find_backlinks(index, "30 Knowledge/Rust.md")
    read_note_lines(vault, "30 Knowledge/Rust.md")

    assert _fingerprint(vault) == before


# ---------------------------------------------------------------------------
# Puanlama sırası (sabit değerler değil, göreli sıra kilitlenir)
# ---------------------------------------------------------------------------


def test_score_order_title_beats_heading_beats_path_beats_body(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/title.md", "# Rust\n\ngövde\n")
    _write(vault, "30 Knowledge/heading.md", "# Başka\n\n## Rust\n\ngövde\n")
    _write(vault, "30 Knowledge/rust-path.md", "# Başka\n\ngövde\n")
    _write(vault, "30 Knowledge/body.md", "# Başka\n\ngövdede rust geçer\n")

    notes = {note.rel_path: note.score for note in scan_evidence_notes(vault, tokenize_query("Rust")).notes}

    assert notes["30 Knowledge/title.md"] > notes["30 Knowledge/heading.md"]
    assert notes["30 Knowledge/heading.md"] > notes["30 Knowledge/rust-path.md"]
    assert notes["30 Knowledge/rust-path.md"] > notes["30 Knowledge/body.md"]


def test_score_rewards_more_body_matches() -> None:
    vault_query = tokenize_query("rust postgres")
    from app.integrations.obsidian.evidence import score_note

    one_score, _ = score_note(
        rel_path="a.md", title="A", headings=(), body_words=frozenset({"rust"}), terms=vault_query
    )
    two_score, _ = score_note(
        rel_path="b.md",
        title="B",
        headings=(),
        body_words=frozenset({"rust", "postgres"}),
        terms=vault_query,
    )
    assert two_score > one_score


# ---------------------------------------------------------------------------
# Wikilink çözümü ve backlink
# ---------------------------------------------------------------------------


def test_resolve_wikilink_unique_ambiguous_and_path() -> None:
    stems = {"rust": ("30 Knowledge/Rust.md",), "note": ("a/note.md", "b/note.md")}
    paths = {"30 knowledge/rust": ("30 Knowledge/Rust.md",), "30 knowledge/rust.md": ("30 Knowledge/Rust.md",)}

    unique = resolve_wikilink("Rust", stems=stems, paths=paths)
    assert unique.status == "resolved"
    assert unique.rel_path == "30 Knowledge/Rust.md"

    qualified = resolve_wikilink("30 Knowledge/Rust.md", stems=stems, paths=paths)
    assert qualified.status == "resolved"
    assert qualified.rel_path == "30 Knowledge/Rust.md"

    ambiguous = resolve_wikilink("note", stems=stems, paths=paths)
    assert ambiguous.status == "ambiguous"
    assert ambiguous.candidates == ("a/note.md", "b/note.md")

    assert resolve_wikilink("yok", stems=stems, paths=paths).status == "unresolved"
    assert resolve_wikilink("a/b/c", stems=stems, paths=paths).status == "unresolved"


def test_find_backlinks_counts_only_resolved_links(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/Rust.md", "# Rust\n")
    _write(vault, "20 Projects/forkjob.md", "# forkjob\n\n[[Rust]] notu.\n")
    _write(vault, "50 Career/decision.md", "# Karar\n\n[[30 Knowledge/Rust]] gerekçesi.\n")
    _write(vault, "50 Career/unrelated.md", "# İlgisiz\n\n[[Yok]] bağlantısı.\n")

    index = scan_evidence_notes(vault, tokenize_query("Rust"))

    assert find_backlinks(index, "30 Knowledge/Rust.md") == (
        "20 Projects/forkjob.md",
        "50 Career/decision.md",
    )


def test_backlinks_of_missing_anchor_are_empty(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/Rust.md", "# Rust\n")
    index = scan_evidence_notes(vault, tokenize_query("Rust"))
    assert find_backlinks(index, "30 Knowledge/Yok.md") == ()


def test_read_note_lines_is_safe_and_bounded(tmp_path: Path) -> None:
    vault = tmp_path / "Vault"
    vault.mkdir()
    _write(vault, "30 Knowledge/Rust.md", "# Rust\n\nsatır\n")

    assert read_note_lines(vault, "30 Knowledge/Rust.md") == ["# Rust", "", "satır", ""]
    assert read_note_lines(vault, "../outside.md") is None
    assert read_note_lines(vault, "30 Knowledge/yok.md") is None
    assert read_note_lines(vault, "90 Agent/Memory/x.md") is None


def test_excerpt_heading_is_none_before_first_heading() -> None:
    lines = ["Girişte rust geçer.", "", "## Sonra", "", "başka"]
    sections = build_sections(lines, 0)
    excerpt = extract_excerpt(lines, sections, tokenize_query("Rust"), max_chars=1200)
    assert isinstance(excerpt, Excerpt)
    assert excerpt.heading is None
    assert excerpt.text == "Girişte rust geçer."
