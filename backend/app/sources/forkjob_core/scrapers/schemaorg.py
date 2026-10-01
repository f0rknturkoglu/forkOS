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


def field_text(value):
    """Declared structured values, never arbitrary JSON or inferred prose."""
    if isinstance(value, list):
        values = [field_text(v) for v in value]
        return ", ".join(dict.fromkeys(v for v in values if v)) or None
    if isinstance(value, dict):
        return field_text(value.get("name") or value.get("label") or value.get("value") or value.get("description"))
    return text(value)


def schema_job(posting, **kwargs):
    """Shared JobPosting facts; never promote the organization ID to job ID."""
    from ..geo import region_for
    from ..models import Job
    from ..normalize import format_salary, parse_single_country
    from ..rich_text import enrich

    requirements = posting.get("applicantLocationRequirements")
    if isinstance(requirements, dict):
        requirements = [requirements]
    scope = ", ".join(str(r["name"]) for r in requirements or [] if isinstance(r, dict) and r.get("name")) or None
    if not kwargs.get("country"):
        kwargs["country"] = parse_single_country(kwargs.get("location") or scope)
        if kwargs["country"]:
            kwargs["region"] = region_for(kwargs["country"])
    salary = posting.get("baseSalary")
    if isinstance(salary, dict) and isinstance(salary.get("value"), dict):
        values = salary["value"]
        period = values.get("unitText")
        low, high = values.get("minValue", values.get("value")), values.get("maxValue")
        low = low if isinstance(low, (int, float)) and low > 0 else None
        high = high if isinstance(high, (int, float)) and high > 0 else None
        formatted = format_salary(low, high, salary.get("currency"), suffix="/" + period if isinstance(period, str) else "")
        if formatted:
            kwargs["salary"] = formatted
    kwargs["description"] = enrich(kwargs.get("description"), kwargs["source"], {
        "Employment type": field_text(posting.get("employmentType")),
        "Remote scope": scope,
        "Technologies": field_text(posting.get("skills")),
        "Experience requirements": field_text(posting.get("experienceRequirements")),
        "Qualifications": field_text(posting.get("qualifications")),
        "Industry": field_text(posting.get("industry")),
        "Job function": field_text(posting.get("occupationalCategory")),
        "Experience requirement (months)": (posting.get("experienceRequirements") or {}).get("monthsOfExperience") if isinstance(posting.get("experienceRequirements"), dict) else None,
        "Responsibilities": field_text(posting.get("responsibilities")),
        "Benefits": field_text(posting.get("jobBenefits")),
        "Application deadline": text(posting.get("validThrough")),
        "Posting language": text(posting.get("inLanguage")),
        "Company URL": (posting.get("hiringOrganization") or {}).get("sameAs") if isinstance(posting.get("hiringOrganization"), dict) else None,
    })
    return Job.build(**kwargs)
