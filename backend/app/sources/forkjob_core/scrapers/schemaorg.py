"""schema.org helpers shared by the ld+json scrapers.

Three sources now publish `JobPosting` as ld+json (beBee, Ticjob) or as
microdata (JobFluent). The parsing quirks are the same everywhere, so they live
here rather than being rediscovered per site.
"""

import html as html_lib
import json
import re
from typing import Any

from ..geo import country_code

_LD_JSON_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)


def ld_blocks(html: str) -> list[dict[str, Any]]:
    """Every ld+json object on a page, flattening list-valued scripts.

    `strict=False` is deliberate: Ticjob emits raw newlines inside its JSON
    strings, which is invalid JSON but universally accepted by browsers. A
    strict parse drops the entire posting over a line break.

    One malformed block never costs the others.
    """
    blocks: list[dict[str, Any]] = []
    for match in _LD_JSON_RE.finditer(html or ""):
        try:
            data = json.loads(match.group(1), strict=False)
        except (json.JSONDecodeError, ValueError):
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict):
                blocks.append(item)
    return blocks


def find_type(blocks: list[dict[str, Any]], type_name: str) -> dict[str, Any] | None:
    """First block whose @type matches (also matches inside a @type list)."""
    for block in blocks:
        declared = block.get("@type")
        if declared == type_name or (isinstance(declared, list) and type_name in declared):
            return block
    return None


def job_posting_nodes(html: str) -> list[dict[str, Any]]:
    """Every JobPosting on a page, however it was nested.

    `find_type` returns the first match at the top level, which is enough for a
    detail page. A listing page is different: publishers wrap the postings in
    `@graph`, or in an `ItemList` whose `itemListElement` entries each hold one
    posting. All three shapes appear in the wild, so all three are unwrapped.
    """
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                walk(child)
            return
        if not isinstance(node, dict):
            return

        declared = node.get("@type")
        names = declared if isinstance(declared, list) else [declared]
        if any(str(n).lower() == "jobposting" for n in names if n):
            found.append(node)
            return

        for key in ("@graph", "itemListElement", "item", "mainEntity"):
            if key in node:
                walk(node[key])

    for block in ld_blocks(html):
        walk(block)
    return found


def organisation_name(node: Any) -> str | None:
    """`hiringOrganization` -> name.

    Unescaped, because sites embed HTML entities inside the JSON: Ticjob ships
    "S&amp;M Services", which would otherwise be stored — and matched against
    other sources — with the entity intact.
    """
    if isinstance(node, dict):
        name = node.get("name")
        if isinstance(name, str) and name.strip():
            return html_lib.unescape(name).strip()
    return None


def place(node: Any) -> tuple[str | None, str | None]:
    """`jobLocation` -> (city, ISO country), either possibly None."""
    if isinstance(node, list):
        node = node[0] if node else None
    if not isinstance(node, dict):
        return None, None

    address = node.get("address")
    if not isinstance(address, dict):
        return None, None

    city = address.get("addressLocality")
    if isinstance(city, str):
        city = html_lib.unescape(city)
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    country = country_code(country) if isinstance(country, str) else None

    return (city.strip() if isinstance(city, str) and city.strip() else None), country


def text(value: Any) -> str | None:
    """A schema.org string field, unescaped and stripped."""
    if isinstance(value, str) and value.strip():
        return html_lib.unescape(value).strip()
    return None
