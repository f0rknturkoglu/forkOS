from __future__ import annotations

import re
from pathlib import Path

_FORBIDDEN_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
_MULTI_SPACES = re.compile(r"\s+")
_MULTI_DASHES = re.compile(r"-{2,}")


def sanitize_filename(name: str, max_length: int = 120) -> str:
    """Dosya adını dosya sistemine uygun, güvenli ve temiz hale getirir.

    - Yasaklı karakterleri (/ \\ : * ? " < > | ve kontrol karakterleri) temizler.
    - Türkçe ve uluslararası karakterleri korur.
    - Baştaki/sondaki nokta, boşluk ve tireleri eler.
    - Boş kalırsa 'Untitled' döner.
    """
    cleaned = _FORBIDDEN_CHARS.sub("-", name or "").strip()
    cleaned = _MULTI_SPACES.sub(" ", cleaned)
    cleaned = _MULTI_DASHES.sub("-", cleaned)
    cleaned = cleaned.strip(". -")
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(". -")
    return cleaned or "Untitled"


def resolve_safe_vault_path(vault_root: Path, relative_path: str | Path) -> Path:
    """Vault kök dizini altında güvenli bir dosya/klasör yolu çözer.

    GÜVENLİK KURALLARI:
    - Mutlak (absolute) yollar reddedilir.
    - Yol parçalarında '..' üst dizin gezintisi reddedilir.
    - Çözülen mutlak yol strictly vault_root altında olmalıdır (symlink traversal engeli).
    """
    rel_str = str(relative_path).strip()
    if not rel_str:
        return vault_root.resolve()

    rel_p = Path(rel_str)
    if rel_p.is_absolute():
        raise ValueError(f"Geçersiz yol: Mutlak yol kabul edilmez ({rel_str})")

    # Path traversal denemelerini baştan engelle
    if any(part == ".." for part in rel_p.parts):
        raise ValueError(f"Geçersiz yol: Üst dizin referansı ('..') içeremez ({rel_str})")

    root_resolved = vault_root.resolve()
    target = (root_resolved / rel_p).resolve()

    try:
        target.relative_to(root_resolved)
    except ValueError as exc:
        raise PermissionError(f"Geçersiz yol: Vault dizini dışına çıkılamaz ({rel_str})") from exc

    return target
