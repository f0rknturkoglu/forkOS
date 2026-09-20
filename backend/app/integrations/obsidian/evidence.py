"""H3 kasa kanıt primitifleri — TAMAMEN salt-okunur.

Bu modül H3'ün Vault tarafındaki TEK yetkili yeridir: yol güvenliği, dosya
tarama sınırları, leksikal puanlama, başlık dilimi çıkarma ve `[[wikilink]]`
grafiği burada yaşar. Ajan orkestrasyon katmanı (`agent/evidence.py`) dosya
sistemi davranışını KOPYALAMAZ; yalnızca buradaki primitifleri çağırır (H2
dersi: orkestrasyon kolaylıktır, depolama güvenliği otoritedir).

Değişmezler:

  - **Sıfır yazma.** Hiçbir dosya oluşturulmaz, taşınmaz, yeniden yazılmaz,
    mtime'a dokunulmaz. İndeks kalıcı DEĞİLDİR: her istek kendi geçici
    görünümünü kurar ve atar.
  - **Sıcak hafıza hariç.** `90 Agent/Memory` kanıt ağacının DIŞINDADIR:
    kişiselleştirme bağlamı kanıt değildir.
  - **Determinizm.** Dizinler ve dosyalar sıralı taranır; her yol/koleksiyon
    açıkça sıralanır. Aynı girdi aynı çıktıyı üretir.
  - **Dürüst satır numaraları.** `line_start`/`line_end` gerçek Markdown
    dosyasının 1 tabanlı fiziksel satırlarıdır. Türetilemiyorsa `None` döner;
    yaklaşık değer UYDURULMAZ.

Satır modeli: dosya `\n` ile bölünür. `\r\n` → `\n` normalizasyonu satır
SAYISINI değiştirmez, dolayısıyla numaralar dosyayla birebir hizalı kalır.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.integrations.obsidian.frontmatter import extract_title, parse_frontmatter
from app.integrations.obsidian.security import is_evidence_path, resolve_safe_vault_path

# ---------------------------------------------------------------------------
# Tarama sınırları (§78/§80)
# ---------------------------------------------------------------------------

#: Tek bir istekte bakılabilecek en fazla Markdown dosyası. Gerçek kasa 28
#: dosyadır; 500 kişisel ölçekte konservatif bir tavandır. Tavana çıkılırsa
#: tarama DURUR ve `truncated` + uyarı ile dürüstçe raporlanır: sessiz kısmi
#: arama yoktur.
MAX_VAULT_SCAN_FILES = 500

#: Tek bir dosyadan okunacak en fazla bayt. Daha büyük dosya kısmen taranır,
#: sayılır ve uyarı üretir; çökme yok, sessiz tam-kapsam iddiası yok.
MAX_VAULT_FILE_BYTES = 256 * 1024

#: Sorgudan çıkarılacak en fazla anlamlı kelime.
MAX_QUERY_TOKENS = 12

#: Bu uzunluğun altındaki kelimeler gürültüdür. İki karakterlik anlamlı
#: kelimeler (AI, Go, C#) KORUNUR (§72).
MIN_TOKEN_LENGTH = 2

#: Sorgu "glue word" kümesi. Kasıtlı olarak DAR tutulur; stemmer/NLP
#: bağımlılığı yoktur (§73). Kaynak listesi okunabilir Türkçe/İngilizce
#: yazılır ve ÇALIŞMA ZAMANINDA normalize edilir -- böylece `için`/`icin`
#: gibi bir yazım farkı duraklama kelimesinin sessizce işlevsiz kalmasına
#: yol açamaz (tokenler normalize edilmiş gelir).
_STOPWORD_SOURCE: tuple[str, ...] = (
    # Türkçe
    "ve", "ile", "bu", "şu", "ne", "mi", "mı", "mu", "mü", "neden", "niye",
    "nasıl", "hangi", "için", "bir", "da", "de", "ki", "ama", "çok", "daha",
    # İngilizce
    "the", "and", "or", "of", "to", "is", "was", "were", "why", "how", "what",
    "which", "did", "do", "does", "a", "an", "in", "on", "for", "we", "our",
)

#: Sıralamada kullanılan göreli ağırlıklar (§75/§76). Testler bu sayıları
#: değil, aralarındaki SIRAYI kilitler: birebir başlık > başlık kelimesi >
#: heading > yol > gövde.
SCORE_EXACT_TITLE = 100
SCORE_TITLE_PHRASE = 85
SCORE_TITLE_ALL_TOKENS = 70
SCORE_TITLE_TOKEN = 55
SCORE_HEADING_TOKEN = 40
SCORE_PATH_TOKEN = 30
SCORE_BODY_BASE = 10


# ---------------------------------------------------------------------------
# Sorgu kelimeleri
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"\w+(?:[#+]\w*)*", re.UNICODE)

_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]]+)\]\]")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def normalize_text(value: str) -> str:
    """NFKD + birleşen işaret temizliği + casefold (aksan duyarsız).

    Projenin Postgres arama konvansiyonu `immutable_unaccent` ile aynı
    hizadadır ve Türkçe için kritiktir: `İstanbul` → `istanbul`, `ş` → `s`.
    Böylece kullanıcının büyük/küçük harf, aksan ya da birleşik harf tercihi
    eşleşmeyi bozmaz. Aynı normalizasyon hem sorguya hem kaynağa uygulanır.
    """
    decomposed = unicodedata.normalize("NFKD", value or "")
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return stripped.casefold()


def words_of(value: str) -> frozenset[str]:
    """Normalize edilmiş metnin kelime kümesi.

    Türkçe ekler kesme işaretiyle ayrıldığı için doğal olarak ayrışır
    ("rust'a" → "rust" + "a"); bu yüzden kök bulma (stemming) gerekmez.
    """
    return frozenset(_TOKEN_RE.findall(normalize_text(value)))


#: Normalize edilmiş duraklama kelimeleri. `_STOPWORD_SOURCE`'tan TÜRETİLİR:
#: tokenler normalize geldiği için küme de aynı biçimde olmak zorundadır.
STOPWORDS: frozenset[str] = frozenset(normalize_text(word) for word in _STOPWORD_SOURCE)


@dataclass(frozen=True)
class QueryTerms:
    """Sorgudan türetilen deterministik arama terimleri."""

    phrase: str
    tokens: tuple[str, ...]
    used_fallback: bool


def tokenize_query(query: str) -> QueryTerms:
    """Sorguyu deterministik terimlere indirger (§72-§74).

    Sıra korunur, tekrarlar atılır, ilk MAX_QUERY_TOKENS kelime kullanılır.
    Duraklama kelimeleri (stopword) çıkarıldıktan sonra hiçbir şey kalmazsa
    HAM kelimelere dönülür: yalnızca yaygın kelimelerden oluşan bir soru boş
    aramaya dönüşmez.
    """
    normalized = normalize_text(query)
    phrase = " ".join(normalized.split())
    ordered: list[str] = []
    for token in _TOKEN_RE.findall(normalized):
        if len(token) < MIN_TOKEN_LENGTH or token in ordered:
            continue
        ordered.append(token)

    useful = [token for token in ordered if token not in STOPWORDS][:MAX_QUERY_TOKENS]
    if useful:
        return QueryTerms(phrase=phrase, tokens=tuple(useful), used_fallback=False)
    return QueryTerms(phrase=phrase, tokens=tuple(ordered[:MAX_QUERY_TOKENS]), used_fallback=True)


# ---------------------------------------------------------------------------
# Markdown dilimleri
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Section:
    """Bir Markdown bölümü: başlığı ve dosya satır aralığı (0 tabanlı, dahil)."""

    heading: str | None
    level: int
    start: int
    end: int


@dataclass(frozen=True)
class Excerpt:
    """Çıkarılan snippet ve kaynaktaki TAM yeri.

    `truncated=False` ise `text`, `lines[line_start-1:line_end]` ile BİREBİR
    aynıdır. `truncated=True` ise `text` aynı satırların bir ÖNEKİdir.

    `section_start`/`section_end` snippet'in TÜRETİLDİĞİ bölümün sınırlarıdır
    (0 tabanlı, dahil). Sonraki global bütçe kırpması bu aralığın DIŞINA
    çıkamaz; aksi hâlde `heading` yalan söylerdi (H3.1 §44-§47).

    `focus_line` snippet'in DAYANAĞI olan satırdır (0 tabanlı): sorgu
    kelimelerinin en çok eşleştiği satır. Sonraki bir kırpma daima bu satırı
    korur; aksi hâlde kanıt, kanıtladığı şeyi kaybederdi (H3.2 §10).
    """

    text: str
    heading: str | None
    line_start: int
    line_end: int
    truncated: bool
    section_start: int
    section_end: int
    focus_line: int


def body_start_line(lines: list[str]) -> int:
    """Frontmatter bloğundan sonraki ilk gövde satırının 0 tabanlı indeksi."""
    if not lines or lines[0].strip() != "---":
        return 0
    for idx in range(1, min(len(lines), 400)):
        if lines[idx].strip() in {"---", "..."}:
            return idx + 1
    return 0


def _trim(lines: list[str], start: int, end: int) -> tuple[int, int] | None:
    """Aralığın başındaki/sonundaki boş satırları kırpar; boşsa None."""
    while start <= end and not lines[start].strip():
        start += 1
    while end >= start and not lines[end].strip():
        end -= 1
    if end < start:
        return None
    return start, end


def build_sections(lines: list[str], body_start: int) -> list[Section]:
    """Gövdeyi başlık bölümlerine ayırır (dosya satır indeksleriyle)."""
    if body_start >= len(lines):
        return []

    sections: list[Section] = []
    heading: str | None = None
    level = 0
    start = body_start
    for idx in range(body_start, len(lines)):
        match = _HEADING_RE.match(lines[idx].strip())
        if match is None:
            continue
        trimmed = _trim(lines, start, idx - 1)
        if trimmed is not None:
            sections.append(Section(heading, level, trimmed[0], trimmed[1]))
        heading = match.group(2).strip()
        level = len(match.group(1))
        start = idx

    trimmed = _trim(lines, start, len(lines) - 1)
    if trimmed is not None:
        sections.append(Section(heading, level, trimmed[0], trimmed[1]))
    return sections


def _line_hits(line: str, tokens: frozenset[str]) -> int:
    return len(tokens & words_of(line))


def _section_hits(lines: list[str], section: Section, tokens: frozenset[str]) -> int:
    """Bölümün tamamında geçen AYRI sorgu kelimesi sayısı."""
    found: set[str] = set()
    for idx in range(section.start, section.end + 1):
        found |= tokens & words_of(lines[idx])
        if len(found) == len(tokens):
            break
    return len(found)


def extract_excerpt(
    lines: list[str],
    sections: list[Section],
    terms: QueryTerms,
    *,
    max_chars: int,
) -> Excerpt | None:
    """Sorguya en iyi uyan bölümden sınırlı bir snippet çıkarır (§81-§84).

    Kural: snippet DAİMA en iyi eşleşen satırı içerir; bölüm bütçeye sığmıyorsa
    o satırdan dışa doğru simetrik büyütülür. Satır aralığı bitişiktir.
    """
    if not sections or not lines:
        return None

    tokens = frozenset(terms.tokens)
    if tokens:
        ranked = [
            (_section_hits(lines, section, tokens), -section.start, section)
            for section in sections
        ]
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        section = ranked[0][2]
    else:
        section = sections[0]

    # Odak satırı: bölümdeki en çok kelime eşleşen İLK satır.
    focus = section.start
    best_hits = -1
    for idx in range(section.start, section.end + 1):
        hits = _line_hits(lines[idx], tokens) if tokens else 0
        if hits > best_hits:
            best_hits = hits
            focus = idx
            if tokens and hits == len(tokens):
                break

    section_text = "\n".join(lines[section.start : section.end + 1])
    if len(section_text) <= max_chars:
        text = section_text
        start, end = section.start, section.end
        truncated = False
    else:
        # Odaktan dışa doğru büyüt: önce alt, sonra üst satır (deterministik).
        start = end = focus
        used = len(lines[focus])
        if used > max_chars:
            return Excerpt(
                text=lines[focus][:max_chars],
                heading=section.heading,
                line_start=focus + 1,
                line_end=focus + 1,
                truncated=True,
                section_start=section.start,
                section_end=section.end,
                focus_line=focus,
            )
        below, above = focus + 1, focus - 1
        while True:
            grew = False
            if below <= section.end:
                cost = len(lines[below]) + 1
                if used + cost <= max_chars:
                    used += cost
                    end = below
                    below += 1
                    grew = True
            if above >= section.start:
                cost = len(lines[above]) + 1
                if used + cost <= max_chars:
                    used += cost
                    start = above
                    above -= 1
                    grew = True
            if not grew:
                break
        text = "\n".join(lines[start : end + 1])
        truncated = True

    return Excerpt(
        text=text,
        heading=section.heading,
        line_start=start + 1,
        line_end=end + 1,
        truncated=truncated,
        section_start=section.start,
        section_end=section.end,
        focus_line=focus,
    )


# ---------------------------------------------------------------------------
# Wikilink grafiği (§89-§95)
# ---------------------------------------------------------------------------


def extract_wikilinks(lines: list[str]) -> tuple[str, ...]:
    """Gövdedeki `[[hedef]]` bağlarını çıkarır (sıra korunur, tekilleştirilir).

    - `![[...]]` gömülü ek/görsel: kanıt kenarı DEĞİLDİR, atlanır (§89).
    - ``` kod blokları ``` ve `satır içi kod` içindeki bağlar bağ sayılmaz (§90).
    - `[[Hedef|Takma ad]]` ve `[[Hedef#Başlık...]]` biçimlerinde yalnızca HEDEF
      döner; takma ad ve başlık çapa değildir.
    """
    targets: list[str] = []
    seen: set[str] = set()
    fence_marker: str | None = None

    for line in lines:
        fence = _FENCE_RE.match(line)
        if fence is not None:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif marker == fence_marker:
                fence_marker = None
            continue
        if fence_marker is not None or "[[" not in line:
            continue

        for embed, inner in _WIKILINK_RE.findall(_INLINE_CODE_RE.sub(" ", line)):
            if embed:
                continue
            target = inner.split("|", 1)[0].split("#", 1)[0].strip().replace("\\", "/")
            if not target:
                continue
            key = target.casefold()
            if key in seen:
                continue
            seen.add(key)
            targets.append(target)

    return tuple(targets)


@dataclass(frozen=True)
class LinkResolution:
    """Bir wikilink hedefinin çözümü. Belirsizlik TAHMİN EDİLMEZ (§92/§93)."""

    status: Literal["resolved", "ambiguous", "unresolved"]
    rel_path: str | None = None
    candidates: tuple[str, ...] = ()


def resolve_wikilink(
    target: str,
    *,
    stems: dict[str, tuple[str, ...]],
    paths: dict[str, tuple[str, ...]],
) -> LinkResolution:
    """Wikilink hedefini deterministik olarak çözer.

    - Yol nitelikli hedef (`30 Knowledge/Rust`) yol indeksinden çözülür;
      `.md` uzantısı opsiyoneldir.
    - Çıplak hedef (`Rust`) güvenli Markdown dosya SAPLARINDAN çözülür.
    - Tek aday → çözüldü; birden fazla aday → belirsiz; hiç aday yok → çözülmedi.
    """
    cleaned = target.strip().removesuffix(".md").replace("\\", "/")
    key = cleaned.casefold()
    if not key:
        return LinkResolution("unresolved")

    if "/" in key:
        found = paths.get(key, ())
        if not found:
            return LinkResolution("unresolved")
        if len(found) == 1:
            return LinkResolution("resolved", rel_path=found[0])
        return LinkResolution("ambiguous", candidates=found)

    found = stems.get(key, ())
    if not found:
        return LinkResolution("unresolved")
    if len(found) == 1:
        return LinkResolution("resolved", rel_path=found[0])
    return LinkResolution("ambiguous", candidates=found)


# ---------------------------------------------------------------------------
# Geçici kasa görünümü (istek başına; kalıcı indeks YOK)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoteRef:
    """Taranan tek bir notun hafif metadata kaydı (gövde taşımaz)."""

    rel_path: str
    stem: str
    title: str
    forkos_id: str | None
    forkos_type: str | None
    updated_at: str | None
    score: int
    matched: tuple[str, ...]
    wikilinks: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceNoteIndex:
    """İstek ömrü boyunca yaşayan, yeniden üretilebilir kasa görünümü (§122/§123).

    İkinci bir doğruluk kaynağı DEĞİLDİR: diskten türetilir, istek bitince
    atılır, hiçbir yere yazılmaz.
    """

    root: Path
    notes: tuple[NoteRef, ...]
    notes_by_path: dict[str, NoteRef]
    stems: dict[str, tuple[str, ...]]
    paths: dict[str, tuple[str, ...]]
    conflicted_forkos_ids: frozenset[str]
    files_read: int
    oversized_files: int
    unreadable_files: int
    truncated: bool
    warnings: tuple[str, ...]

    def by_path(self, rel_path: str) -> NoteRef | None:
        return self.notes_by_path.get(rel_path)

    def resolve(self, target: str) -> LinkResolution:
        return resolve_wikilink(target, stems=self.stems, paths=self.paths)


def read_note_lines(root: Path, rel_path: str) -> list[str] | None:
    """Tek bir notun satırlarını güvenli ve sınırlı biçimde okur (salt-okunur)."""
    try:
        safe_path = resolve_safe_vault_path(root, rel_path)
    except (ValueError, OSError):
        return None
    if not safe_path.is_file() or safe_path.suffix.lower() != ".md":
        return None
    try:
        with open(safe_path, encoding="utf-8", errors="replace") as handle:
            raw = handle.read(MAX_VAULT_FILE_BYTES + 1)
    except OSError:
        return None
    return raw[:MAX_VAULT_FILE_BYTES].replace("\r\n", "\n").split("\n")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def score_note(
    *,
    rel_path: str,
    title: str,
    headings: tuple[str, ...],
    body_words: frozenset[str],
    terms: QueryTerms,
) -> tuple[int, tuple[str, ...]]:
    """Deterministik leksikal puan ve eşleşen alanların listesi (§75/§76).

    Puan bir GÜVEN/DOĞRULUK puanı değildir: yalnızca sıralamayı sabitler ve
    kanıt çıktısına YAZILMAZ (§32/§77). Dönen alan listesi ise kanıtın
    `retrieval_reason` metnine girer -- böylece "neden seçildi" sorusu
    gerçekten gözlemlenebilir bir olguya dayanır (§106/§107).
    """
    tokens = frozenset(terms.tokens)
    if not tokens:
        return 0, ()

    matched: list[str] = []
    title_norm = normalize_text(title)
    title_words = words_of(title)
    score = 0

    if terms.phrase and title_norm == terms.phrase:
        score = SCORE_EXACT_TITLE
        matched.append("exact title")
    elif terms.phrase and terms.phrase in title_norm:
        score = SCORE_TITLE_PHRASE
        matched.append("title phrase")
    elif tokens <= title_words:
        score = SCORE_TITLE_ALL_TOKENS
        matched.append("title")
    elif tokens & title_words:
        score = SCORE_TITLE_TOKEN
        matched.append("title token")

    if score < SCORE_HEADING_TOKEN:
        for heading in headings:
            if tokens & words_of(heading):
                score = SCORE_HEADING_TOKEN
                matched.append("heading")
                break

    if score < SCORE_PATH_TOKEN and tokens & words_of(rel_path):
        score = SCORE_PATH_TOKEN
        matched.append("path")

    hits = len(tokens & body_words)
    if hits:
        score = max(score, SCORE_BODY_BASE + min(hits, 5))
        matched.append("body")

    return score, tuple(matched)


def scan_evidence_notes(root: Path, terms: QueryTerms) -> EvidenceNoteIndex:
    """Kasa ağacını TEK geçişte, sınırlı ve sıralı biçimde tarar (§79).

    Sıcak hafıza ağacı, gizli dizinler, ekler ve Vault dışına çıkan sembolik
    bağlar taranmaz. Hiçbir dosya yazılmaz.
    """
    notes: list[NoteRef] = []
    stems: dict[str, list[str]] = {}
    paths: dict[str, list[str]] = {}
    forkos_id_paths: dict[str, list[str]] = {}
    warnings: list[str] = []
    files_read = 0
    oversized = 0
    unreadable = 0
    truncated = False

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        rel_dir = current.relative_to(root)

        dirnames[:] = sorted(
            name
            for name in dirnames
            if is_evidence_path(rel_dir / name)
            and not os.path.islink(os.path.join(dirpath, name))
        )

        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            rel_path = str(rel_dir / filename).replace("\\", "/")
            if not is_evidence_path(rel_path):
                continue

            if files_read >= MAX_VAULT_SCAN_FILES:
                truncated = True
                warnings.append(
                    f"Vault scan stopped at the {MAX_VAULT_SCAN_FILES}-file cap; "
                    "results may be incomplete."
                )
                break

            try:
                safe_path = resolve_safe_vault_path(root, rel_path)
            except (ValueError, OSError):
                # ValueError: sözleşme dışı yol ('..', mutlak, kaçış).
                # OSError: PermissionError, ELOOP, ENAMETOOLONG vb.
                # Tarama HİÇBİR koşulda çökmez; dosya atlanır ve sayılır (§80).
                unreadable += 1
                continue
            if not safe_path.is_file():
                unreadable += 1
                continue

            try:
                with open(safe_path, encoding="utf-8", errors="replace") as handle:
                    raw = handle.read(MAX_VAULT_FILE_BYTES + 1)
            except OSError:
                unreadable += 1
                continue

            files_read += 1
            if len(raw) > MAX_VAULT_FILE_BYTES:
                oversized += 1
            text = raw[:MAX_VAULT_FILE_BYTES].replace("\r\n", "\n")
            lines = text.split("\n")

            frontmatter, body = parse_frontmatter(text)
            metadata = frontmatter if isinstance(frontmatter, dict) else {}
            title = extract_title(metadata, body, fallback=Path(filename).stem)
            headings = tuple(
                match.group(2).strip()
                for match in (_HEADING_RE.match(line.strip()) for line in lines)
                if match is not None
            )
            wikilinks = extract_wikilinks(lines) if "[[" in text else ()
            score, matched = score_note(
                rel_path=rel_path,
                title=title,
                headings=headings,
                body_words=words_of(body),
                terms=terms,
            )

            note = NoteRef(
                rel_path=rel_path,
                stem=Path(filename).stem,
                title=title,
                forkos_id=_optional_str(metadata.get("forkos_id")),
                forkos_type=_optional_str(metadata.get("forkos_type")),
                updated_at=_optional_str(metadata.get("forkos_updated_at")),
                score=score,
                matched=matched,
                wikilinks=wikilinks,
            )
            notes.append(note)

            if note.forkos_id:
                forkos_id_paths.setdefault(note.forkos_id, []).append(rel_path)
            stems.setdefault(note.stem.casefold(), []).append(rel_path)
            paths.setdefault(rel_path.removesuffix(".md").casefold(), []).append(rel_path)
            paths.setdefault(rel_path.casefold(), []).append(rel_path)

        if truncated:
            break

    if oversized:
        warnings.append(
            f"{oversized} note(s) exceeded {MAX_VAULT_FILE_BYTES // 1024} KiB and were only "
            "partially scanned."
        )
    if unreadable:
        warnings.append(f"{unreadable} note(s) could not be read and were skipped.")

    notes.sort(key=lambda note: note.rel_path)
    return EvidenceNoteIndex(
        root=root,
        notes=tuple(notes),
        notes_by_path={note.rel_path: note for note in notes},
        stems={key: tuple(sorted(value)) for key, value in stems.items()},
        paths={key: tuple(sorted(value)) for key, value in paths.items()},
        #: Birden fazla dosyanın sahiplendiği kimlikler: H3 hiçbirine "bu not"
        #: demez (§86). Kanonik yönetilen indeksin çakışma sinyaliyle aynı
        #: olgudur; H3 bunu kendi taramasında zaten gördüğü için ikinci bir
        #: tarama yapmaz.
        conflicted_forkos_ids=frozenset(
            forkos_id for forkos_id, found in forkos_id_paths.items() if len(found) > 1
        ),
        files_read=files_read,
        oversized_files=oversized,
        unreadable_files=unreadable,
        truncated=truncated,
        warnings=tuple(warnings),
    )


def find_backlinks(index: EvidenceNoteIndex, anchor_rel_path: str) -> tuple[str, ...]:
    """Çapalı nota işaret eden notları bulur (§97).

    Yalnızca ÇÖZÜLEBİLEN bağlar sayılır; belirsiz hedefler tahmin edilmez.
    Sonuç yola göre sıralıdır (deterministik).
    """
    anchor = anchor_rel_path.removesuffix(".md").casefold()
    found: list[str] = []
    for note in index.notes:
        if note.rel_path == anchor_rel_path:
            continue
        for target in note.wikilinks:
            resolution = index.resolve(target)
            if resolution.status != "resolved" or resolution.rel_path is None:
                continue
            if resolution.rel_path.removesuffix(".md").casefold() == anchor:
                found.append(note.rel_path)
                break
    return tuple(sorted(found))
