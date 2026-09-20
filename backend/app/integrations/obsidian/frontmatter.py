from __future__ import annotations

import re
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n(?:---|\.\.\.)\r?\n?(.*)", re.DOTALL)
_H1_RE = re.compile(r"^\s*#\s+(.+)$", re.MULTILINE)


def parse_frontmatter(content: str) -> tuple[dict[str, Any] | None, str]:
    """Markdown metninden YAML frontmatter bloğunu ve gövdeyi ayrıştırır.

    Dönüş: (frontmatter_dict, body_text)
    Frontmatter yoksa veya bozuksa: (None, content)
    Bozuk YAML scan akışını patlatmaz.
    """
    match = _FRONTMATTER_RE.match(content or "")
    if not match:
        return None, content

    yaml_raw, body = match.group(1), match.group(2)
    try:
        parsed = yaml.safe_load(yaml_raw)
        if isinstance(parsed, dict):
            return parsed, body
        return None, content
    except Exception:
        # Bozuk YAML scan'i durdurmaz
        return None, content


def extract_title(frontmatter: dict[str, Any] | None, body: str, fallback: str = "Untitled") -> str:
    """Belge başlığını sırayla frontmatter, ilk H1 başlığı veya fallback'ten belirler."""
    if frontmatter and isinstance(frontmatter.get("title"), str) and frontmatter["title"].strip():
        return frontmatter["title"].strip()

    h1_match = _H1_RE.search(body or "")
    if h1_match:
        return h1_match.group(1).strip()

    return fallback


def render_markdown_with_frontmatter(metadata: dict[str, Any], body: str) -> str:
    """Frontmatter metadata sözlüğünü ve gövdeyi standart Markdown belgesi olarak birleştirir."""
    yaml_text = yaml.dump(metadata, sort_keys=False, allow_unicode=True).strip()
    clean_body = (body or "").strip()
    if clean_body:
        return f"---\n{yaml_text}\n---\n\n{clean_body}\n"
    return f"---\n{yaml_text}\n---\n"
