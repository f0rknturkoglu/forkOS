from __future__ import annotations

import urllib.parse


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def _relative_file(relative_path: str) -> str:
    return str(relative_path).replace("\\", "/").removesuffix(".md").strip("/")


def open_file_uri(vault_name: str, relative_path: str) -> str:
    """Belirtilen dosyayı Obsidian uygulamasında açacak resmi URI'yi oluşturur.

    Örnek:
    obsidian://open?vault=Vault&file=20%20Projects%2FforkOS
    """
    encoded_file = urllib.parse.quote(_relative_file(relative_path), safe="/")
    return f"obsidian://open?vault={_quote(vault_name or 'Vault')}&file={encoded_file}"


def open_vault_uri(vault_name: str) -> str:
    """Obsidian'ı (Vault seçili halde) açar; belirli bir dosyaya gitmez."""
    return f"obsidian://open?vault={_quote(vault_name or 'Vault')}"


def create_note_uri(vault_name: str, relative_path: str, content: str | None = None) -> str:
    """Yeni not oluşturan ya da açan resmi Obsidian URI'si."""
    encoded_file = urllib.parse.quote(_relative_file(relative_path), safe="/")
    uri = f"obsidian://new?vault={_quote(vault_name or 'Vault')}&file={encoded_file}"
    if content:
        uri += f"&content={_quote(content)}"
    return uri


def daily_note_uri(vault_name: str) -> str:
    """Obsidian'ın KENDİ günlük not mekanizmasını tetikler.

    forkOS günlük not içeriğinin sahibi DEĞİLDİR ve günlük dosyayı YAZMAZ
    (mevcut taşınmış günlükleri çiftlememek için). Obsidian çekirdeğinin
    `daily` URI'si bugünün notunu açar/oluşturur; resmi olarak tarih parametresi
    almadığı için parametresiz çağrılır.
    """
    return f"obsidian://daily?vault={_quote(vault_name or 'Vault')}"


def search_uri(vault_name: str, query: str) -> str:
    """Obsidian içi arama başlatan resmi URI."""
    return f"obsidian://search?vault={_quote(vault_name or 'Vault')}&query={_quote(query.strip())}"
