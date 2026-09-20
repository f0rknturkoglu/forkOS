from __future__ import annotations

import urllib.parse


def open_file_uri(vault_name: str, relative_path: str) -> str:
    """Belirtilen dosyayı Obsidian uygulamasında açacak resmi URI'yi oluşturur.

    Örnek:
    obsidian://open?vault=Vault&file=20%20Projects%2FforkOS
    """
    clean_vault = urllib.parse.quote(vault_name or "Vault", safe="")
    clean_path = str(relative_path).replace("\\", "/").removesuffix(".md").strip("/")
    encoded_file = urllib.parse.quote(clean_path, safe="/")
    return f"obsidian://open?vault={clean_vault}&file={encoded_file}"


def create_note_uri(vault_name: str, relative_path: str, content: str | None = None) -> str:
    """Yeni not oluşturan ya da açan resmi Obsidian URI'si."""
    clean_vault = urllib.parse.quote(vault_name or "Vault", safe="")
    clean_path = str(relative_path).replace("\\", "/").removesuffix(".md").strip("/")
    encoded_file = urllib.parse.quote(clean_path, safe="/")
    uri = f"obsidian://new?vault={clean_vault}&file={encoded_file}"
    if content:
        encoded_content = urllib.parse.quote(content, safe="")
        uri += f"&content={encoded_content}"
    return uri


def search_uri(vault_name: str, query: str) -> str:
    """Obsidian içi arama başlatan resmi URI."""
    clean_vault = urllib.parse.quote(vault_name or "Vault", safe="")
    encoded_query = urllib.parse.quote(query.strip(), safe="")
    return f"obsidian://search?vault={clean_vault}&query={encoded_query}"
