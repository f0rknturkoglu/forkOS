from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from app.config import settings
from app.integrations.agent.models import BrainReadData, BrainSearchResult, BrainStatusData
from app.integrations.obsidian.hot_memory import is_policy_excluded
from app.integrations.obsidian.security import (
    EXCLUDED_DIRS,
    is_safe_knowledge_path,
    resolve_safe_vault_path,
)
from app.integrations.obsidian.service import vault_index

WHITELISTED_FRONTMATTER_KEYS = {
    "forkos_id",
    "forkos_type",
    "forkos_note_kind",
    "forkos_entity_type",
    "forkos_project_id",
    "forkos_journal_day",
    "forkos_source_bookmark_id",
    "tags",
    "source",
    "source_title",
    "title",
}

SCOPE_FOLDER_MAP: dict[str, list[str]] = {
    "all": [],
    "inbox": ["00 inbox", "00-inbox"],
    "daily": ["10 daily", "10-günlük", "10-gunluk"],
    "projects": ["20 projects", "20-projeler"],
    "knowledge": ["30 knowledge", "30-alanlar"],
    "learning": ["40 learning", "40-kaynaklar"],
    "career": ["50 career", "50-moc"],
    "sources": ["60 sources", "40-kaynaklar"],
    "agent": ["90 agent"],
}


def _get_vault_root() -> Path:
    v_root = settings.resolved_obsidian_vault_path
    if not v_root or not v_root.exists() or not v_root.is_dir():
        raise ValueError("VAULT_UNAVAILABLE: Obsidian Vault is not configured or does not exist.")
    return v_root


def _parse_frontmatter_and_body(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown text."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    fm_raw = parts[1]
    body = parts[2].lstrip("\r\n")
    try:
        data = yaml.safe_load(fm_raw)
        if isinstance(data, dict):
            return data, body
    except Exception:
        pass
    return {}, text


def _derive_title(frontmatter: dict[str, Any], body: str, filename: str) -> str:
    """Derive display title: frontmatter title > first H1 > filename stem."""
    if frontmatter.get("title") and isinstance(frontmatter["title"], str) and frontmatter["title"].strip():
        return frontmatter["title"].strip()

    for line in body.splitlines():
        line_s = line.strip()
        if line_s.startswith("# "):
            title = line_s[2:].strip()
            if title:
                return title

    stem = Path(filename).stem
    return stem


def _extract_headings(body: str) -> list[str]:
    """Extract all markdown headings (#, ##, ###)."""
    headings: list[str] = []
    for line in body.splitlines():
        line_s = line.strip()
        if line_s.startswith("#"):
            match = re.match(r"^#{1,6}\s+(.+)$", line_s)
            if match:
                headings.append(match.group(1).strip())
    return headings


def _extract_snippet(body: str, query: str, max_chars: int = 500) -> str:
    """Extract a clean text snippet around query occurrence."""
    idx = body.lower().find(query.lower())
    if idx == -1:
        # Fallback to beginning of body
        clean = " ".join(body.split())
        return clean[:max_chars].strip() + ("..." if len(clean) > max_chars else "")

    start = max(0, idx - 150)
    end = min(len(body), idx + len(query) + 350)
    snippet = body[start:end]
    clean = " ".join(snippet.split())
    if start > 0:
        clean = "..." + clean
    if end < len(body):
        clean = clean + "..."
    return clean


def _find_containing_heading(body: str, match_pos: int) -> str | None:
    """Find the heading (# ...) immediately preceding match_pos."""
    lines = body[:match_pos].splitlines()
    for line in reversed(lines):
        line_s = line.strip()
        if line_s.startswith("#"):
            match = re.match(r"^#{1,6}\s+(.+)$", line_s)
            if match:
                return match.group(1).strip()
    return None


def get_brain_status() -> BrainStatusData:
    """Check health, availability and stats of f0rknbrain knowledge interface."""
    v_root = settings.resolved_obsidian_vault_path
    v_name = settings.resolved_obsidian_vault_name

    if not v_root or not v_root.exists() or not v_root.is_dir():
        return BrainStatusData(
            configured=bool(settings.obsidian_vault_path),
            available=False,
            readable=False,
            writable=False,
            vault_name=v_name,
            total_markdown_files=0,
            managed_files_count=0,
            conflicts_count=0,
            invalid_metadata_count=0,
        )

    # Count safe markdown files
    total_md = 0
    for root, dirs, files in os.walk(v_root, followlinks=False):
        dirs[:] = [
            d for d in dirs
            if is_safe_knowledge_path(d)
        ]
        for f in files:
            if f.endswith(".md") and is_safe_knowledge_path(f):
                try:
                    rel_p = (Path(root) / f).relative_to(v_root)
                    if is_safe_knowledge_path(rel_p):
                        total_md += 1
                except Exception:
                    continue

    idx_status = vault_index.current_status(v_root, v_name)

    return BrainStatusData(
        brain_interface_version=1,
        configured=True,
        available=True,
        readable=os.access(v_root, os.R_OK),
        writable=os.access(v_root, os.W_OK),
        vault_name=v_name,
        total_markdown_files=total_md,
        managed_files_count=idx_status.managed_files,
        conflicts_count=idx_status.conflicts,
        invalid_metadata_count=len(idx_status.invalid_files),
    )


def search_vault(
    query: str,
    scope: str = "all",
    limit: int = 8,
) -> list[BrainSearchResult]:
    """Deterministically search all safe Markdown files across the Vault."""
    q = query.strip()
    if len(q) < 2:
        raise ValueError("QUERY_TOO_SHORT: Query must be at least 2 characters.")
    if len(q) > 200:
        raise ValueError("QUERY_TOO_LONG: Query must be at most 200 characters.")

    v_root = _get_vault_root()
    scope_lower = scope.lower().strip()
    if scope_lower not in SCOPE_FOLDER_MAP:
        raise ValueError(f"INVALID_SCOPE: Unknown scope '{scope}'. Allowed scopes: {list(SCOPE_FOLDER_MAP.keys())}")
    allowed_prefixes = SCOPE_FOLDER_MAP[scope_lower]

    limit = max(1, min(limit, 20))
    q_lower = q.lower()
    matches: list[BrainSearchResult] = []

    for root, dirs, files in os.walk(v_root, followlinks=False):
        dirs[:] = [
            d for d in dirs
            if is_safe_knowledge_path(d)
        ]

        for f in files:
            if not f.endswith(".md") or not is_safe_knowledge_path(f):
                continue

            full_path = Path(root) / f
            try:
                safe_target = resolve_safe_vault_path(v_root, full_path.relative_to(v_root))
            except Exception:
                continue

            if not is_safe_knowledge_path(safe_target.relative_to(v_root)):
                continue

            rel_path_str = str(safe_target.relative_to(v_root)).replace("\\", "/")

            # Apply scope filter if specified
            if allowed_prefixes:
                rel_lower = rel_path_str.lower()
                if not any(rel_lower.startswith(prefix) for prefix in allowed_prefixes):
                    continue

            try:
                with open(safe_target, encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
            except Exception:
                continue

            frontmatter, body = _parse_frontmatter_and_body(content)
            title = _derive_title(frontmatter, body, f)
            headings = _extract_headings(body)

            # §16/§64: sıcak hafıza tekrar tekrar model bağlamına girmek için
            # tasarlandı; apaçık sır taşıyan `90 Agent/Memory` dosyası H2
            # bağlamından dışlandığı gibi H0 aramasından da dışlanır. Denetim
            # TAM artifact üzerindedir (göreli yol + ham Markdown) ve snippet/
            # başlık/frontmatter ÜRETİLMEDEN önce yapılır. Bu kural YALNIZCA
            # sıcak hafıza ağacına uygulanır; normal kasa bilgisi etkilenmez.
            if is_policy_excluded(rel_path_str, content):
                continue

            # Score matching
            title_lower = title.lower()
            body_lower = body.lower()
            rel_lower = rel_path_str.lower()

            score = 0
            matched_heading: str | None = None

            if q_lower == title_lower:
                score = 100
            elif q_lower in title_lower:
                score = 80
            else:
                # Check headings
                for h in headings:
                    if q_lower in h.lower():
                        score = 50
                        matched_heading = h
                        break
                if score == 0 and q_lower in rel_lower:
                    score = 30
                elif score == 0 and q_lower in body_lower:
                    score = 10
                    idx = body_lower.find(q_lower)
                    if idx != -1:
                        matched_heading = _find_containing_heading(body, idx)

            if score > 0:
                forkos_id = str(frontmatter["forkos_id"]) if frontmatter.get("forkos_id") else None
                forkos_type = str(frontmatter["forkos_type"]) if frontmatter.get("forkos_type") else None
                locator = forkos_id if forkos_id else rel_path_str

                snippet = _extract_snippet(body, q)

                matches.append(
                    BrainSearchResult(
                        locator=locator,
                        title=title,
                        relative_path=rel_path_str,
                        forkos_id=forkos_id,
                        forkos_type=forkos_type,
                        matched_heading=matched_heading,
                        snippet=snippet,
                        score=score,
                    )
                )

    # Deterministic sort: score DESC, title ASC
    matches.sort(key=lambda item: (-item.score, item.title.lower()))
    return matches[:limit]


def _extract_heading_section(body: str, heading_title: str) -> str:
    """Extract content under a specific heading until the next heading of same or higher level."""
    lines = body.splitlines()
    target_clean = heading_title.lower().strip().lstrip("#").strip()

    start_idx = -1
    target_level = 1

    for i, line in enumerate(lines):
        line_s = line.strip()
        if line_s.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.+)$", line_s)
            if match:
                level = len(match.group(1))
                name = match.group(2).strip().lower()
                if name == target_clean:
                    start_idx = i
                    target_level = level
                    break

    if start_idx == -1:
        return ""

    # Collect until next heading of <= target_level
    section_lines: list[str] = [lines[start_idx]]
    for line in lines[start_idx + 1:]:
        line_s = line.strip()
        if line_s.startswith("#"):
            match = re.match(r"^(#{1,6})\s+", line_s)
            if match and len(match.group(1)) <= target_level:
                break
        section_lines.append(line)

    return "\n".join(section_lines).strip()


def read_vault_note(
    forkos_id: str | None = None,
    relative_path: str | None = None,
    heading: str | None = None,
    char_limit: int = 12000,
) -> BrainReadData:
    """Safely read a Vault markdown note by forkos_id or relative_path."""
    if (forkos_id is None and relative_path is None) or (forkos_id is not None and relative_path is not None):
        raise ValueError("INVALID_LOCATOR: Provide exactly one of 'forkos_id' or 'relative_path'.")

    if forkos_id:
        try:
            uuid.UUID(str(forkos_id).strip())
        except (ValueError, AttributeError) as exc:
            raise ValueError(f"INVALID_UUID: '{forkos_id}' is not a valid UUID.") from exc

    v_root = _get_vault_root()

    target_rel_path: str | None = None

    if forkos_id:
        # Check vault index first
        v_name = settings.resolved_obsidian_vault_name
        idx_status = vault_index.current_status(v_root, v_name)
        if forkos_id in idx_status.conflict_details:
            raise ValueError(f"VAULT_CONFLICT: Managed note ID '{forkos_id}' has conflicting duplicate files.")

        item = vault_index.get_item(forkos_id)
        if item is not None:
            target_rel_path = item.relative_path
        else:
            # Fallback scan for forkos_id in frontmatter
            for root, dirs, files in os.walk(v_root, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in EXCLUDED_DIRS]
                for f in files:
                    if f.endswith(".md") and not f.startswith("."):
                        fp = Path(root) / f
                        try:
                            with open(fp, encoding="utf-8", errors="ignore") as file_handle:
                                text = file_handle.read(1024)
                            fm, _ = _parse_frontmatter_and_body(text)
                            if str(fm.get("forkos_id")) == forkos_id:
                                target_rel_path = str(fp.relative_to(v_root)).replace("\\", "/")
                                break
                        except Exception:
                            continue
                if target_rel_path:
                    break

        if not target_rel_path:
            raise ValueError(f"KNOWLEDGE_NOT_FOUND: Note with forkos_id '{forkos_id}' not found in Vault.")
    else:
        target_rel_path = relative_path

    # Security check: resolve safe path
    try:
        safe_path = resolve_safe_vault_path(v_root, target_rel_path)
    except PermissionError as exc:
        raise ValueError(f"VAULT_PATH_ESCAPES: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"VAULT_PATH_ESCAPES: {exc}") from exc

    rel_from_vault = safe_path.relative_to(v_root)
    if not is_safe_knowledge_path(rel_from_vault):
        raise ValueError(f"ACCESS_DENIED: Path '{target_rel_path}' is in an excluded or hidden directory.")

    if not safe_path.exists() or not safe_path.is_file() or not safe_path.name.endswith(".md"):
        raise ValueError(f"KNOWLEDGE_NOT_FOUND: File '{target_rel_path}' not found in Vault.")

    # Read strictly with mode="r"
    with open(safe_path, encoding="utf-8", errors="ignore") as fp:
        raw_text = fp.read()

    frontmatter, body = _parse_frontmatter_and_body(raw_text)
    title = _derive_title(frontmatter, body, safe_path.name)
    headings = _extract_headings(body)

    # §17/§64: politika dışı sıcak hafıza dosyası H0 okumasından da dışlanır;
    # aksi hâlde H2'nin engellediği içerik `brain_read` ile model bağlamına
    # girebilirdi. Denetim TAM artifact üzerindedir; hata mesajı sırrı, gövdeyi,
    # frontmatter'ı ya da güvenli olmayan dosya adını YANSITMAZ.
    if is_policy_excluded(rel_from_vault, raw_text):
        raise ValueError(
            "ACCESS_DENIED: This path is excluded by the agent-memory policy."
        )

    # Filter whitelisted frontmatter
    whitelisted_fm = {k: v for k, v in frontmatter.items() if k in WHITELISTED_FRONTMATTER_KEYS}

    content_to_return = body
    if heading:
        extracted = _extract_heading_section(body, heading)
        if extracted:
            content_to_return = extracted

    truncated = False
    max_budget = min(char_limit, 40000)
    if len(content_to_return) > max_budget:
        content_to_return = content_to_return[:max_budget]
        truncated = True

    rel_clean = str(safe_path.relative_to(v_root)).replace("\\", "/")
    found_forkos_id = str(frontmatter["forkos_id"]) if frontmatter.get("forkos_id") else None
    found_forkos_type = str(frontmatter["forkos_type"]) if frontmatter.get("forkos_type") else None

    return BrainReadData(
        title=title,
        relative_path=rel_clean,
        forkos_id=found_forkos_id,
        forkos_type=found_forkos_type,
        frontmatter=whitelisted_fm,
        headings=headings,
        content=content_to_return,
        truncated=truncated,
    )
