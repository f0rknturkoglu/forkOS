"""Prompt'a giden güvenilmeyen metin için ortak güvenlik yardımcıları.

Bu yardımcılar domain bilgisi taşımaz: verilen metni HTML/XML kaçışından
geçirir, mutlak sistem yollarını redakte eder ve alan sınırı uygular. A2
bağlam render'ı ve A3 epizodik devir render'ı AYNI kuralları kullanır; ikinci
bir kaçış çerçevesi yazmak, birinin düzeltilip diğerinin unutulmasına yol açar.
"""

from __future__ import annotations

import html
import re

#: Mutlak yol: sürücü harfli (C:\\ / C:/) ya da kökle başlayan (/...) diziler.
#: Tırnak, parantez, virgül ve noktalı virgülde durur; böylece cümle içindeki
#: bir yol tek başına eşleşir ve ardındaki metni yutmaz.
_ABSOLUTE_PATH_RE = re.compile(
    r"(^|[\s'\"(\[,;])((?:[A-Za-z]:[\\/]|/)[^'\"()\[\],;\n]+)",
    re.MULTILINE,
)


def redact_absolute_paths(text: str) -> str:
    """Tanılama ve bağlam metninden mutlak sistem yollarını temizler."""
    return _ABSOLUTE_PATH_RE.sub(lambda match: f"{match.group(1)}<vault>", text or "")


def escape_context_data(text: str, max_chars: int = 1000) -> str:
    """Evrensel HTML/XML kaçışı, mutlak yol redaksiyonu ve alan sınırı uygular.

    Sıra önemlidir: önce sınır uygulanır, sonra yol redaksiyonu, en son kaçış.
    Kaçıştan sonra kırpmak `&amp;` gibi dizileri ortadan bölerdi.
    """
    if not text:
        return ""
    bounded = text[:max_chars]
    clean = redact_absolute_paths(bounded)
    return html.escape(clean, quote=True)


__all__ = ["escape_context_data", "redact_absolute_paths"]
