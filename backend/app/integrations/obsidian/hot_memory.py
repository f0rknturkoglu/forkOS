"""Sıcak hafıza (Hot Memory) depolama katmanı — `90 Agent/Memory/`.

H2'nin kalıcılık sınırı burasıdır. Vault dosya sistemi davranışının ikinci bir
zayıf kopyası ÜRETİLMEZ: kök çözümleme, yol güvenliği, frontmatter ayrıştırma
ve atomik yazma mevcut Obsidian primitiflerinden gelir.

Tasarım kararları:

  - **Öğe başına tek dosya.** Tek bir büyük `Profile.md` yoktur: çakışma
    yüzeyi küçük kalır, her öğe kendi revizyonuna sahip olur, emeklilik
    güvenlidir ve Git geçmişi okunabilir.
  - **Kimlik `memory_id`'dir, yol değil.** Dosya adı `<memory_id>.md`; başlık
    yalnızca frontmatter'da yaşar. Bu, yol temizleme karmaşıklığını ortadan
    kaldırır ve kullanıcı dosyayı taşısa bile kimliği korur.
  - **Revizyon içerikten TÜRETİLİR.** `sha256(dosya baytları)`; dosyanın içine
    yazılmaz. Böylece dosya sistemi zaman damgası çözünürlüğü önemsizleşir.
  - **Silme yoktur.** Emeklilik (`status=retired`) dosyayı olduğu yerde
    bırakır; tarih Git'te kalır.
  - **Okuma onarıcı değildir.** Bozuk/insan-düzenlemesi dosyalar okuma
    sırasında "düzeltilmez"; raporlanır.
  - **Yazma yetkisi DİSKTEN gelir.** Revizyon karşılaştırması `os.replace`'ten
    hemen önce GÜNCEL baytlar üzerinden yapılır (compare-and-swap). Tarama
    anındaki kopya yalnızca kolaylıktır, tek başına yetki vermez; böylece
    Obsidian'daki kullanıcı düzenlemesi bayat bir yazmayla ezilmez.
  - **Oluşturma atomiktir ve üzerine yazmaz.** Tam içerik geçici dosyaya
    yazılır, hedefe `os.link` ile bağlanır; kısmi bir Markdown dosyası hiçbir
    an görünmez.
  - **Politika okuma anında da geçerlidir.** Elle düzenlenmiş bir dosya apaçık
    kimlik bilgisi taşıyorsa sıcak hafızaya yüklenmez — ve DEĞİŞTİRİLMEZ.
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import os
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.integrations.obsidian.frontmatter import (
    parse_frontmatter,
    render_markdown_with_frontmatter,
)
from app.integrations.obsidian.security import resolve_safe_vault_path
from app.integrations.obsidian.vault import require_writable_vault

#: Kanonik kök. `TYPE_DEFAULT_FOLDERS["memory"]` ile aynı ağaçtadır.
MEMORY_ROOT = "90 Agent/Memory"

#: Frontmatter sözleşme sürümü. Uyumsuz sürüm = geçersiz dosya.
MEMORY_SCHEMA_VERSION = 1

MemoryKind = Literal["profile", "preference", "goal", "constraint", "decision"]
MemoryStatus = Literal["active", "retired"]
EffectiveStatus = Literal["active", "expired", "retired"]
SourceMode = Literal["explicit_user", "approved_candidate"]

KINDS: tuple[MemoryKind, ...] = ("profile", "preference", "goal", "constraint", "decision")
STATUSES: tuple[MemoryStatus, ...] = ("active", "retired")
SOURCE_MODES: tuple[SourceMode, ...] = ("explicit_user", "approved_candidate")

#: §41 sınırları. Aşan bilgi sıcak hafızaya değil, normal Vault bilgisine aittir.
MAX_TITLE = 120
MAX_TEXT = 1200
MAX_TAGS = 8
MAX_RELATED = 5
MAX_RETIRED_REASON = 240

#: Tanılamada dönen geçersiz dosya yolu sayısı sınırı.
MAX_INVALID_REPORTED = 20

#: Sert bağ (`os.link`) desteklemeyen dosya sistemleri: yayın `O_CREAT|O_EXCL`
#: yoluna düşer. Üzerine yazma yine engellenir; kısmi görünürlük garantisi
#: o ortamda geçersizdir (§24).
_NO_HARDLINK_ERRNOS = frozenset(
    {errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV, errno.EMLINK}
)

#: H2'nin sahip olduğu anahtarlar. Güncellemede bunlar yönetilir; BİLİNMEYEN
#: kullanıcı anahtarları korunur (§31).
OWNED_KEYS: tuple[str, ...] = (
    "agent_memory_version",
    "memory_id",
    "memory_kind",
    "title",
    "status",
    "importance",
    "source_mode",
    "created_at",
    "updated_at",
    "expires_at",
    "related_forkos_ids",
    "tags",
    "retired_at",
    "retired_reason",
)

#: Deterministik, YÜKSEK GÜVENLİ sır desenleri (§20). Bu bir sınıflandırıcı
#: DEĞİLDİR; yalnızca apaçık kimlik bilgisi biçimlerini reddeder. Asıl savunma
#: küçük şema + açık onay + otomatik yazma yasağıdır.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----\s*BEGIN[^-]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]{20,}", re.IGNORECASE),
    re.compile(
        r"\b(?:password|passwd|pwd|api[_-]?key|secret[_-]?key|client[_-]?secret"
        r"|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*\S{6,}",
        re.IGNORECASE,
    ),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
)

_UUID_RE = re.compile(r"\A[0-9a-fA-F-]{36}\Z")


class HotMemoryError(Exception):
    """Model-okunur sıcak hafıza hatası (`KOD: açıklama`)."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass
class MemoryRecord:
    """Tek bir sıcak hafıza öğesinin doğrulanmış hâli."""

    memory_id: str
    kind: str
    title: str
    text: str
    status: str
    importance: int
    source_mode: str
    created_at: str
    updated_at: str
    expires_at: str | None
    related_forkos_ids: list[str]
    tags: list[str]
    retired_at: str | None
    retired_reason: str | None
    relative_path: str
    revision: str
    #: Kullanıcıya ait, H2'nin sahip olmadığı frontmatter anahtarları.
    extra_frontmatter: dict[str, Any] = field(default_factory=dict)

    def effective_status(self, *, now: datetime | None = None) -> str:
        """Etkin durum: `retired` > `expired` > `active` (§27)."""
        if self.status == "retired":
            return "retired"
        if self.expires_at:
            try:
                expiry = parse_iso(self.expires_at)
            except ValueError:
                return "active"
            if expiry is not None and expiry <= (now or datetime.now(UTC)):
                return "expired"
        return "active"


@dataclass
class MemorySnapshot:
    """`90 Agent/Memory` dizininin tek geçişlik, salt-okunur görünümü."""

    items: list[MemoryRecord] = field(default_factory=list)
    conflicts: dict[str, list[str]] = field(default_factory=dict)
    #: Göreli yollar SINIRLIDIR (`MAX_INVALID_REPORTED`); sayaç değildir (§32).
    invalid_relative_paths: list[str] = field(default_factory=list)
    #: Şema dışı + politika dışı dosyaların GERÇEK sayısı.
    invalid_count: int = 0
    #: Yalnızca politika nedeniyle dışlananlar (`HOT_MEMORY_POLICY_REJECTED`).
    policy_rejected_relative_paths: list[str] = field(default_factory=list)
    policy_rejected_count: int = 0
    available: bool = True
    diagnostic: str | None = None

    @property
    def conflict_ids(self) -> list[str]:
        return sorted(self.conflicts)


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------


def _resolved_root(root: Path) -> Path:
    """Kökü çözerek normalize et.

    macOS'ta `/var` gerçekte `/private/var`'dır; `resolve_safe_vault_path` çözülmüş
    yol döndürdüğü için göreli yol hesabı ancak kök de çözülmüşse tutarlı olur.
    """
    return root.expanduser().resolve()


def revision_of(content: bytes) -> str:
    """İçerik revizyonu: dosya baytlarının sha256'sı (§29)."""
    return hashlib.sha256(content).hexdigest()


def parse_iso(value: str) -> datetime | None:
    """ISO-8601 damgasını UTC-farkındalı `datetime`a çevirir (§38).

    Sıralama ve zaman aşımı kararı bu fonksiyondan geçer; ham metin
    karşılaştırması farklı ofsetleri yanlış sıralar.
    """
    text = value.strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_text(value: str) -> str:
    """Tekilleştirme için metin normalizasyonu (§58) — sezgisel değil, kesin."""
    return " ".join(value.split()).casefold().strip()


def looks_like_secret(*parts: str | None) -> bool:
    """Apaçık kimlik bilgisi biçimi var mı (deterministik, muhafazakâr)."""
    blob = "\n".join(part for part in parts if part)
    return any(pattern.search(blob) for pattern in _SECRET_PATTERNS)


def is_memory_relative_path(relative_path: str | Path) -> bool:
    """Göreli yol sıcak hafıza ağacının içinde mi? (kasa köküne göre)"""
    parts = tuple(
        part.casefold() for part in Path(str(relative_path).replace("\\", "/")).parts
    )
    root = tuple(part.casefold() for part in Path(MEMORY_ROOT).parts)
    return parts[: len(root)] == root


def is_policy_excluded(relative_path: str | Path, *parts: str | None) -> bool:
    """H0/H2 ORTAK politika kapısı (§64).

    Sıcak hafıza tekrar tekrar model bağlamına girmek için tasarlandı; bu yüzden
    apaçık kimlik bilgisi taşıyan `90 Agent/Memory` dosyası YALNIZCA H2
    bağlamından değil, H0 bilgi yüzeyinden (`brain_search`/`brain_read`) de
    dışlanır. Normal Vault bilgisi bu politikaya TABİ DEĞİLDİR.
    """
    return is_memory_relative_path(relative_path) and looks_like_secret(*parts)


def _memory_dir(root: Path) -> Path:
    return resolve_safe_vault_path(root, MEMORY_ROOT)


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _is_regular_no_symlink(path: Path, root: Path) -> bool:
    """Sembolik link / düzenli olmayan dosya / kasa dışına kaçış reddi (§72)."""
    if path.is_symlink():
        return False
    try:
        real = path.resolve(strict=True)
    except OSError:
        return False
    try:
        real.relative_to(root)
    except ValueError:
        return False
    return real.is_file()


# ---------------------------------------------------------------------------
# Tarama ve ayrıştırma
# ---------------------------------------------------------------------------


def _validate_frontmatter(frontmatter: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Frontmatter'ı doğrular; hata varsa (None, sebep) döner."""
    version = frontmatter.get("agent_memory_version")
    if version != MEMORY_SCHEMA_VERSION:
        return None, f"desteklenmeyen agent_memory_version: {version!r}"

    raw_id = str(frontmatter.get("memory_id") or "").strip()
    if not _UUID_RE.match(raw_id):
        return None, f"geçersiz memory_id: {raw_id!r}"
    try:
        memory_id = str(uuid.UUID(raw_id))
    except ValueError:
        return None, f"geçersiz memory_id: {raw_id!r}"

    kind = str(frontmatter.get("memory_kind") or "").strip().lower()
    if kind not in KINDS:
        return None, f"geçersiz memory_kind: {kind!r}"

    status = str(frontmatter.get("status") or "").strip().lower()
    if status not in STATUSES:
        return None, f"geçersiz status: {status!r}"

    source_mode = str(frontmatter.get("source_mode") or "").strip().lower()
    if source_mode not in SOURCE_MODES:
        return None, f"geçersiz source_mode: {source_mode!r}"

    importance = frontmatter.get("importance")
    if not isinstance(importance, int) or isinstance(importance, bool) or importance not in (1, 2, 3):
        return None, f"geçersiz importance: {importance!r}"

    title = str(frontmatter.get("title") or "").strip()
    if not title or len(title) > MAX_TITLE:
        return None, "title boş ya da çok uzun"

    for key in ("created_at", "updated_at"):
        raw = frontmatter.get(key)
        if not isinstance(raw, str) or not raw.strip():
            return None, f"{key} eksik"
        try:
            parse_iso(raw)
        except ValueError:
            return None, f"{key} ISO değil"

    expires_at = frontmatter.get("expires_at")
    if expires_at is not None:
        if not isinstance(expires_at, str) or not expires_at.strip():
            return None, "expires_at boş"
        try:
            parse_iso(expires_at)
        except ValueError:
            return None, "expires_at ISO değil"
        expires_at = expires_at.strip()

    tags = frontmatter.get("tags") or []
    if not isinstance(tags, list) or len(tags) > MAX_TAGS:
        return None, "tags listesi geçersiz"
    if any(not isinstance(tag, str) for tag in tags):
        return None, "tags yalnızca metin içerebilir"

    related = frontmatter.get("related_forkos_ids") or []
    if not isinstance(related, list) or len(related) > MAX_RELATED:
        return None, "related_forkos_ids listesi geçersiz"
    for entry in related:
        if not _UUID_RE.match(str(entry)):
            return None, f"related_forkos_ids UUID değil: {entry!r}"

    retired_reason = frontmatter.get("retired_reason")
    if retired_reason is not None and (
        not isinstance(retired_reason, str) or len(retired_reason) > MAX_RETIRED_REASON
    ):
        return None, "retired_reason geçersiz"

    return {
        "memory_id": memory_id,
        "memory_kind": kind,
        "status": status,
        "source_mode": source_mode,
        "importance": importance,
        "title": title,
        "created_at": str(frontmatter["created_at"]).strip(),
        "updated_at": str(frontmatter["updated_at"]).strip(),
        "expires_at": expires_at,
        "tags": [str(tag) for tag in tags],
        "related_forkos_ids": [str(entry) for entry in related],
        "retired_at": frontmatter.get("retired_at"),
        "retired_reason": retired_reason,
    }, None


def parse_memory_file(path: Path, root: Path) -> MemoryRecord:
    """Tek dosyayı okuyup doğrular. Hata durumunda `HotMemoryError` yükseltir."""
    raw = path.read_bytes()
    content = raw.decode("utf-8", errors="replace")
    frontmatter, body = parse_frontmatter(content)
    if not isinstance(frontmatter, dict):
        raise HotMemoryError("HOT_MEMORY_INVALID", "frontmatter bulunamadı")

    validated, reason = _validate_frontmatter(frontmatter)
    if validated is None:
        raise HotMemoryError("HOT_MEMORY_INVALID", reason or "geçersiz frontmatter")

    text = body.strip()
    if not text or len(text) > MAX_TEXT:
        raise HotMemoryError("HOT_MEMORY_INVALID", "gövde boş ya da çok uzun")

    # §13/§14: politika OKUMA anında da uygulanır. Gövde Obsidian'da elle
    # düzenlenebildiği için yazma anındaki kontrol tek başına yetmez. Eşleşen
    # dosya DEĞİŞTİRİLMEZ — yalnızca sıcak hafızaya yüklenmez.
    if looks_like_secret(validated["title"], text):
        raise HotMemoryError(
            "HOT_MEMORY_POLICY_REJECTED",
            "dosya apaçık kimlik bilgisi biçimi içeriyor; sıcak hafızaya yüklenmedi",
        )

    extra = {key: value for key, value in frontmatter.items() if key not in OWNED_KEYS}
    return MemoryRecord(
        memory_id=validated["memory_id"],
        kind=validated["memory_kind"],
        title=validated["title"],
        text=text,
        status=validated["status"],
        importance=validated["importance"],
        source_mode=validated["source_mode"],
        created_at=validated["created_at"],
        updated_at=validated["updated_at"],
        expires_at=validated["expires_at"],
        related_forkos_ids=validated["related_forkos_ids"],
        tags=validated["tags"],
        retired_at=validated["retired_at"],
        retired_reason=validated["retired_reason"],
        relative_path=_relative(root, path),
        revision=revision_of(raw),
        extra_frontmatter=extra,
    )


def scan_memories(root: Path) -> MemorySnapshot:
    """`90 Agent/Memory` altını tarar; doğrulanmış öğe, çakışma ve geçersizleri döner.

    Salt-okunur: hiçbir dosya yazılmaz, taşınmaz veya "onarılmaz".

    Okunamayan dizin ham `OSError` olarak SIZMAZ; `HOT_MEMORY_UNAVAILABLE`a
    çevrilir (§28). Tek tek dosyaların okunamaması ise tüm taramayı düşürmez:
    o dosya "geçersiz" sayılır ve raporlanır.
    """
    root = _resolved_root(root)
    try:
        memory_dir = _memory_dir(root)
        if not memory_dir.is_dir():
            # Dizin yoksa boş hafıza — bu bir hata değil, H2 boş başlar (§29).
            return MemorySnapshot(items=[], available=True)
        entries = sorted(memory_dir.iterdir())
    except OSError as exc:
        raise HotMemoryError("HOT_MEMORY_UNAVAILABLE", "hafıza dizini okunamıyor") from exc

    items: list[MemoryRecord] = []
    conflicts: dict[str, list[str]] = {}
    invalid: list[str] = []
    policy_rejected: list[str] = []
    invalid_count = 0
    policy_rejected_count = 0

    for entry in entries:
        if entry.name.startswith(".") or not entry.name.endswith(".md"):
            continue
        if not _is_regular_no_symlink(entry, root):
            # Sembolik link / düzenli olmayan dosya: sessizce atlanır (§72).
            continue
        try:
            record = parse_memory_file(entry, root)
        except (HotMemoryError, OSError) as exc:
            # §32: SAYAÇ gerçeği söyler, yol listesi sınırlı kalır.
            invalid_count += 1
            relative = _relative(root, entry)
            if len(invalid) < MAX_INVALID_REPORTED:
                invalid.append(relative)
            if isinstance(exc, HotMemoryError) and exc.code == "HOT_MEMORY_POLICY_REJECTED":
                policy_rejected_count += 1
                if len(policy_rejected) < MAX_INVALID_REPORTED:
                    policy_rejected.append(relative)
            continue

        if record.memory_id in conflicts:
            conflicts[record.memory_id].append(record.relative_path)
        elif any(existing.memory_id == record.memory_id for existing in items):
            first = next(item for item in items if item.memory_id == record.memory_id)
            conflicts[record.memory_id] = [first.relative_path, record.relative_path]
        else:
            items.append(record)

    return MemorySnapshot(
        items=items,
        conflicts=conflicts,
        invalid_relative_paths=invalid,
        invalid_count=invalid_count,
        policy_rejected_relative_paths=policy_rejected,
        policy_rejected_count=policy_rejected_count,
        available=True,
    )


def assert_no_conflict(snapshot: MemorySnapshot, memory_id: str) -> None:
    """Aynı kimlik iki dosyada ise fail-closed (§33)."""
    paths = snapshot.conflicts.get(str(memory_id))
    if paths:
        raise HotMemoryError(
            "HOT_MEMORY_CONFLICT",
            f"aynı memory_id birden fazla dosyada: {', '.join(sorted(paths))}",
        )


def find_memory(snapshot: MemorySnapshot, memory_id: str) -> MemoryRecord | None:
    target = str(memory_id)
    return next((item for item in snapshot.items if item.memory_id == target), None)


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------


def _render_frontmatter(
    *,
    memory_id: str,
    kind: str,
    title: str,
    status: str,
    importance: int,
    source_mode: str,
    created_at: str,
    updated_at: str,
    expires_at: str | None,
    related_forkos_ids: list[str],
    tags: list[str],
    retired_at: str | None = None,
    retired_reason: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "agent_memory_version": MEMORY_SCHEMA_VERSION,
        "memory_id": memory_id,
        "memory_kind": kind,
        "title": title,
        "status": status,
        "importance": importance,
        "source_mode": source_mode,
        "created_at": created_at,
        "updated_at": updated_at,
        "expires_at": expires_at,
        "related_forkos_ids": related_forkos_ids,
        "tags": tags,
    }
    if retired_at is not None:
        metadata["retired_at"] = retired_at
    if retired_reason is not None:
        metadata["retired_reason"] = retired_reason
    if extra:
        # Kullanıcıya ait bilinmeyen anahtarlar KORUNUR (§31).
        for key, value in extra.items():
            metadata.setdefault(key, value)
    return metadata


def _temp_path(target: Path) -> Path:
    """Hedefin YANINDA, gizli geçici dosya adı (§71)."""
    return target.with_name(f".{target.name}.hm-{uuid.uuid4().hex}.tmp")


def _write_temp(target: Path, content: str) -> Path:
    """Tam içeriği geçici dosyaya yazar; GÖRÜNÜR hedefe dokunmaz."""
    temp = _temp_path(target)
    with open(temp, "x", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return temp


def _replace_guarded(target: Path, content: str, guard: Callable[[], None]) -> None:
    """Geçici dosyayı yazar, `guard`ı REPLACE'TEN HEMEN ÖNCE çalıştırır, sonra
    hedefi atomik olarak değiştirir (§3).

    Sıra kasıtlıdır: pahalı iş (yazma + fsync) doğrulamadan ÖNCE yapılır, böylece
    "doğrulandı" ile "değiştirildi" arasındaki pencere tek bir `os.replace`
    çağrısına iner. Ters sırada (önce doğrula, sonra yaz) pencere yazma süresi
    kadar açık kalırdı.

    Süreç içi eşzamanlılık (§52): `guard()` ile `os.replace` arasında `await`
    YOKTUR. Tek iş parçacıklı olay döngüsü bu bölümü başka bir göreve bölemez;
    bu yüzden iki eşzamanlı forkOS isteği yarışırsa ikincisi GÜNCEL baytlarda
    eski revizyonu görüp `HOT_MEMORY_STALE` alır. Süreç içi kilit yoktur.

    Kalan pencere yalnızca DIŞ süreçlere (Obsidian) karşıdır: `os.replace`
    çağrısından önceki mikrosaniyelerde yapılan bir düzenleme yakalanmaz. Bu,
    tek kullanıcılı yerel mimaride kabul edilir ve hiçbir kilit onu kapatamaz.
    """
    temp = _write_temp(target, content)
    try:
        guard()
        os.replace(temp, target)
    except Exception:
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)
        raise


def _create_exclusive_fallback(target: Path, content: str) -> None:
    """Sert bağ desteklemeyen dosya sistemleri için `O_CREAT|O_EXCL` yolu."""
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as exc:
        raise HotMemoryError("HOT_MEMORY_CONFLICT", "aynı kimlikle dosya zaten var") from exc
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
    except Exception:
        with contextlib.suppress(OSError):
            target.unlink(missing_ok=True)
        raise


def _create_exclusive(target: Path, content: str) -> None:
    """Yeni hedefi atomik VE üzerine yazmadan yayınlar (§24).

    Sıra: tam içerik geçici dosyaya yazılır → `os.link` ile hedefe bağlanır →
    geçici dosya silinir. `os.link` hedef varsa `FileExistsError` verir; yani
    "varsa üzerine yaz" DEĞİLDİR. Hedef ancak içeriği TAM olan dosyaya işaret
    ettiği için kısmi bir Markdown dosyası hiçbir an görünmez.

    Sert bağ desteklemeyen dosya sistemlerinde `O_CREAT|O_EXCL` yoluna düşülür:
    üzerine yazma yine engellenir, ancak kısmi görünürlük garantisi o ortamda
    GEÇERSİZDİR.
    """
    temp = _write_temp(target, content)
    try:
        try:
            os.link(temp, target)
        except FileExistsError as exc:
            raise HotMemoryError(
                "HOT_MEMORY_CONFLICT", "aynı kimlikle dosya zaten var"
            ) from exc
        except OSError as exc:
            if exc.errno not in _NO_HARDLINK_ERRNOS:
                raise
            _create_exclusive_fallback(target, content)
    finally:
        # §25/§84: başarı da başarısızlık da geçici dosya BIRAKMAZ.
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)


def verify_current_revision(
    root: Path, record: MemoryRecord, expected_revision: str
) -> bytes:
    """Hedefin GÜNCEL baytlarını okuyup revizyonu doğrular (§3/§4/§20).

    YETKİLİ kontrol budur. `record.revision` tarama anına aittir; tarama ile
    yazma arasında kullanıcı Obsidian'da dosyayı düzenlemiş olabilir. Bu yüzden
    karar, dosyanın ŞU ANKİ baytlarının hash'i ile verilir.

    Uyuşmazlıkta hiçbir yazma yapılmaz ve `HOT_MEMORY_STALE` yükseltilir;
    çağıranlar dosyayı tazeleyip yeniden denemelidir. Dönen baytlar çağırana
    "doğrulanmış güncel içerik" olarak verilir.
    """
    root = _resolved_root(root)
    try:
        target = resolve_safe_vault_path(root, record.relative_path)
    except (OSError, ValueError, PermissionError) as exc:
        raise HotMemoryError("HOT_MEMORY_UNAVAILABLE", "hedef dosya çözümlenemedi") from exc
    if not _is_regular_no_symlink(target, root):
        raise HotMemoryError("HOT_MEMORY_UNAVAILABLE", "hedef dosya okunamıyor")
    try:
        current = target.read_bytes()
    except OSError as exc:
        raise HotMemoryError("HOT_MEMORY_UNAVAILABLE", "hedef dosya okunamıyor") from exc
    if revision_of(current) != expected_revision:
        raise HotMemoryError(
            "HOT_MEMORY_STALE",
            "hafıza dosyası okunduktan sonra değişmiş; güncelleme yapılmadı",
        )
    return current


def create_memory(
    root: Path,
    *,
    kind: str,
    title: str,
    text: str,
    importance: int,
    source_mode: str,
    expires_at: str | None = None,
    related_forkos_ids: list[str] | None = None,
    tags: list[str] | None = None,
) -> MemoryRecord:
    """Tek bir sıcak hafıza dosyası oluşturur (atomik, çakışmada üzerine yazmaz).

    §24: hedef, içeriği TAM olan bir dosyaya atomik olarak bağlanır; kısmi bir
    Markdown dosyası hiçbir an görünmez ve var olan hedef ASLA değiştirilmez.
    """
    root = _resolved_root(root)
    memory_id = str(uuid.uuid4())
    now = _now_iso()
    metadata = _render_frontmatter(
        memory_id=memory_id,
        kind=kind,
        title=title,
        status="active",
        importance=importance,
        source_mode=source_mode,
        created_at=now,
        updated_at=now,
        expires_at=expires_at,
        related_forkos_ids=list(related_forkos_ids or []),
        tags=list(tags or []),
    )
    content = render_markdown_with_frontmatter(metadata, text)

    memory_dir = _memory_dir(root)
    memory_dir.mkdir(parents=True, exist_ok=True)
    target = resolve_safe_vault_path(root, f"{MEMORY_ROOT}/{memory_id}.md")

    # `memory_id` sunucu üretimi olduğu için çakışma pratikte imkânsızdır; yine de
    # sessiz üzerine yazma yerine deterministik hata tercih edilir.
    _create_exclusive(target, content)

    return parse_memory_file(target, root)


def rewrite_memory(
    root: Path,
    record: MemoryRecord,
    *,
    expected_revision: str,
    kind: str | None = None,
    title: str | None = None,
    text: str | None = None,
    importance: int | None = None,
    expires_at: str | None = None,
    clear_expires_at: bool = False,
    related_forkos_ids: list[str] | None = None,
    tags: list[str] | None = None,
    status: str | None = None,
    retired_reason: str | None = None,
) -> MemoryRecord:
    """Var olan öğeyi atomik olarak günceller; revizyon uyuşmazsa YAZMAZ.

    İki katmanlı revizyon denetimi (§5):

      erken karşılaştırma (`record.revision`) = kolaylık, hızlı hata yolu
      `verify_current_revision` (disk)        = YETKİ

    İkincisi olmadan, tarama ile yazma arasında Obsidian'da yapılan bir
    kullanıcı düzenlemesi bayat bir ajan yazmasıyla ezilebilirdi.

    `None` = "alanı değiştirme". Temizleme niyeti `clear_expires_at` gibi açık
    bir bayrakla ifade edilir; böylece H1.1'deki omitted-vs-null ayrımı burada
    da korunur.
    """
    root = _resolved_root(root)
    if record.revision != expected_revision:
        # Kolaylık: en yaygın bayatlık hâlini disk okumadan yakalar.
        raise HotMemoryError(
            "HOT_MEMORY_STALE",
            "hafıza dosyası okunduktan sonra değişmiş; güncelleme yapılmadı",
        )

    target = resolve_safe_vault_path(root, record.relative_path)
    if not _is_regular_no_symlink(target, root):
        raise HotMemoryError("HOT_MEMORY_UNAVAILABLE", "hedef dosya okunamıyor")

    now = _now_iso()
    next_expires = None if clear_expires_at else (expires_at if expires_at is not None else record.expires_at)
    next_status = status or record.status
    retired_at = record.retired_at
    next_retired_reason = record.retired_reason
    if next_status == "retired":
        retired_at = retired_at or now
        if retired_reason is not None:
            next_retired_reason = retired_reason

    metadata = _render_frontmatter(
        memory_id=record.memory_id,
        kind=kind or record.kind,
        title=title or record.title,
        status=next_status,
        importance=importance if importance is not None else record.importance,
        source_mode=record.source_mode,
        created_at=record.created_at,
        updated_at=now,
        expires_at=next_expires,
        related_forkos_ids=related_forkos_ids
        if related_forkos_ids is not None
        else record.related_forkos_ids,
        tags=tags if tags is not None else record.tags,
        retired_at=retired_at,
        retired_reason=next_retired_reason,
        extra=record.extra_frontmatter,
    )
    content = render_markdown_with_frontmatter(metadata, text if text is not None else record.text)

    # §3/§5: YETKİLİ kontrol replace'ten hemen önce çalışır. Yukarıdaki
    # `record.revision` karşılaştırması hızlı hata yoludur; tek başına YETKİ
    # VERMEZ, çünkü tarama ile bu an arasında kullanıcı dosyayı Obsidian'da
    # düzenlemiş olabilir. Yetki, dosyanın ŞU ANKİ baytlarının hash'inden gelir.
    _replace_guarded(
        target,
        content,
        lambda: verify_current_revision(root, record, expected_revision),
    )
    return parse_memory_file(target, root)


def ensure_memory_dir(root: Path) -> Path:
    """Yazma gerektiğinde dizini tembel oluşturur (§122: açılışta yazma yok)."""
    root = _resolved_root(root)
    memory_dir = _memory_dir(root)
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def writable_root() -> Path:
    """Yazma kapısından geçmiş kök (Vault yoksa `HOT_MEMORY_UNAVAILABLE`)."""
    try:
        root, _ = require_writable_vault()
    except (RuntimeError, PermissionError) as exc:
        raise HotMemoryError("HOT_MEMORY_UNAVAILABLE", str(exc)) from exc
    return root


def readable_root() -> Path | None:
    """Okuma için kök; güvenle okunamıyorsa `None` (§28/§29).

    Doğrulama: yapılandırılmış mı, var mı, dizin mi, OKUNABİLİR mi. Hiçbir şey
    OLUŞTURULMAZ (§61). `90 Agent/Memory` yoksa bu bir hata değildir: boş
    hafızadır. Dizin varsa okunabilirliği de burada doğrulanır ki ham bir
    `PermissionError` tarama sırasında sızmasın.
    """
    from app.integrations.obsidian.vault import vault_context

    try:
        root, _ = vault_context()
        if root is None:
            return None
        resolved = root.resolve()
        if not resolved.is_dir() or not os.access(resolved, os.R_OK | os.X_OK):
            return None
        memory_dir = _memory_dir(resolved)
        if memory_dir.is_dir() and not os.access(memory_dir, os.R_OK | os.X_OK):
            return None
    except (OSError, ValueError, PermissionError):
        return None
    return resolved
