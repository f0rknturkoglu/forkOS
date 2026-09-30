"""Source-attributed facts alongside prose, without a storage schema change."""

import re
from collections.abc import Mapping

_BLOCK = re.compile(r"(?:^|\n\n)Source facts \(([^\n)]+)\):\n(.*?)(?=\n\n|\Z)", re.S)


def enrich(description: str | None, source: str, facts: Mapping[str, object]) -> str | None:
    lines = [f"{key}: {value}" for key, value in facts.items() if value is not None and value != ""]
    block = f"Source facts ({source}):\n" + "\n".join(lines) if lines else ""
    return "\n\n".join(part for part in (description, block) if part) or None


def merge_descriptions(
    existing: str | None,
    incoming: str | None,
    *,
    prefer_existing: bool = False,
    prefer_incoming: bool = False,
) -> str | None:
    """Keep fuller prose and both sources' facts; refresh same-source facts."""
    blocks = {}
    for value in (existing or "", incoming or ""):
        for match in _BLOCK.finditer(value):
            facts = blocks.setdefault(match.group(1), {})
            for line in match.group(2).splitlines():
                if ": " in line:
                    key, fact = line.split(": ", 1)
                    facts[key] = fact
    prose = [_BLOCK.sub("", value or "").strip() for value in (existing, incoming)]
    body = (
        prose[1]
        if prefer_incoming and prose[1]
        else prose[0]
        if prefer_existing and prose[0]
        else max(prose, key=len)
    )
    sections = [
        f"Source facts ({source}):\n" + "\n".join(f"{key}: {facts[key]}" for key in sorted(facts))
        for source, facts in sorted(blocks.items())
    ]
    return "\n\n".join(part for part in [body, *sections] if part) or None


def source_fact(description: str | None, label: str) -> str | None:
    for block in _BLOCK.finditer(description or ""):
        for line in block.group(2).splitlines():
            if line.startswith(label + ": "):
                return line[len(label) + 2 :].strip() or None
    return None


def scoring_tags(description: str) -> str:
    """Discrete stack/experience evidence remains readable beyond the prose head."""
    prefixes = ("Technologies: ", "Technologies/topics: ", "Experience level: ")
    return "\n".join(
        line
        for block in _BLOCK.finditer(description)
        for line in block.group(2).splitlines()
        if line.startswith(prefixes)
    )


def scoring_evidence(description: str) -> str:
    """Preserve inferred board labels, but never score them as employer promises."""
    prefixes = (
        "Board sponsorship",
        "Board requirements:",
        "Board benefits:",
        "Board discovery tags:",
        "Board language tag:",
        "Board region:",
    )
    return "\n".join(
        line
        for line in description.splitlines()
        if "(board inference)" not in line
        and "(Workcamino text inference)" not in line
        and not line.startswith(prefixes)
    )


def authoritative_evidence(description: str) -> str:
    """Native/employer evidence wins over conflicting aggregator labels."""
    return _BLOCK.sub(
        lambda match: "" if "source authority: meta" in match.group(2).lower() else match.group(0),
        description,
    )
