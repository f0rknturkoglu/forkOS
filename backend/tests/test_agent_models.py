from datetime import UTC, datetime

import pytest

from app.integrations.agent.models import (
    ActivityEventData,
    AgentEnvelope,
    BrainReadData,
    BrainSearchResult,
    BrainStatusData,
    BriefingData,
    EntityContextData,
    EntitySearchResult,
    ProjectContextData,
    sanitize_and_bound_payload,
    sanitize_payload,
)

pytestmark = pytest.mark.no_database


def test_agent_envelope_structure():
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC)
    envelope = AgentEnvelope[dict[str, str]](
        as_of=now,
        source="forkos",
        data={"message": "hello"},
        truncated=False,
    )
    dumped = envelope.model_dump(mode="json")
    assert dumped["source"] == "forkos"
    assert dumped["truncated"] is False
    assert "2026-09-20T12:00:00" in dumped["as_of"]
    assert dumped["data"] == {"message": "hello"}


def test_briefing_data_defaults():
    briefing = BriefingData(
        day="2026-09-20",
        agenda=[],
        open_todos=[],
        deadlines=[],
        active_projects=[],
        learning_due=[],
        opportunity_attention=[],
        notifications=[],
        recent_activity_summary=[],
        vault_status={"available": True},
    )
    assert briefing.day == "2026-09-20"
    assert briefing.agenda == []
    assert briefing.vault_status["available"] is True


def test_sanitize_payload_masks_sensitive_keys():
    raw = {
        "user": "furkan",
        "github_token": "ghp_1234567890abcdef",
        "nested": {
            "password": "secret_password",
            "api_key": "xyz987",
            "public_metric": 42,
        },
        "safe_list": [{"secret_token": "val", "count": 10}],
    }
    sanitized = sanitize_payload(raw)
    assert sanitized["user"] == "furkan"
    assert sanitized["github_token"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["public_metric"] == 42
    assert sanitized["safe_list"][0]["secret_token"] == "[REDACTED]"
    assert sanitized["safe_list"][0]["count"] == 10


def test_brain_status_version():
    status = BrainStatusData(
        configured=True,
        available=True,
        readable=True,
        writable=True,
        vault_name="f0rknbrain",
        total_markdown_files=27,
        managed_files_count=12,
        conflicts_count=0,
        invalid_metadata_count=0,
    )
    assert status.brain_interface_version == 1
    assert status.vault_name == "f0rknbrain"


def test_brain_search_result_locator():
    res1 = BrainSearchResult(
        locator="3f6f99e0-1234-5678-9abc-def012345678",
        title="Test Managed",
        relative_path="20 Projects/Test/Test.md",
        forkos_id="3f6f99e0-1234-5678-9abc-def012345678",
        forkos_type="project",
        matched_heading="Architecture",
        snippet="This is a test snippet...",
        score=100,
    )
    assert res1.locator == "3f6f99e0-1234-5678-9abc-def012345678"

    res2 = BrainSearchResult(
        locator="30 Knowledge/Rust.md",
        title="Rust",
        relative_path="30 Knowledge/Rust.md",
        forkos_id=None,
        forkos_type=None,
        matched_heading=None,
        snippet="Rust memory ownership...",
        score=80,
    )
    assert res2.locator == "30 Knowledge/Rust.md"


def test_other_models_instantiation():
    search_hit = EntitySearchResult(
        id="3f6f99e0-1234-5678-9abc-def012345678",
        type="project",
        title="forkOS",
        route="/projects/3f6f99e0",
        summary="A personal OS",
    )
    assert search_hit.type == "project"

    entity_ctx = EntityContextData(
        id="3f6f99e0-1234-5678-9abc-def012345678",
        type="project",
        title="forkOS",
        route="/projects/3f6f99e0",
    )
    assert entity_ctx.title == "forkOS"

    proj_ctx = ProjectContextData(
        project={"id": "1", "title": "Test"},
    )
    assert proj_ctx.project["title"] == "Test"

    act = ActivityEventData(
        id=1,
        timestamp="2026-09-20T12:00:00Z",
        verb="created",
        title="Created task",
    )
    assert act.verb == "created"

    read_data = BrainReadData(
        title="Sample Note",
        relative_path="10 Daily/2026-09-20.md",
        content="# Sample Note\nContent",
    )
    assert read_data.title == "Sample Note"


def test_sanitize_and_bound_payload_bounds():
    # 1. Depth bounding (max_depth=4)
    deep = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": "too deep"}}}}}}
    bounded_deep = sanitize_and_bound_payload(deep, max_depth=4)
    assert bounded_deep["l1"]["l2"]["l3"]["l4"] == "[TRUNCATED_DEPTH]"

    # 2. Key count bounding (max_keys=25)
    wide_dict = {f"key_{i}": i for i in range(35)}
    bounded_dict = sanitize_and_bound_payload(wide_dict, max_keys=25)
    assert len([k for k in bounded_dict if not k.startswith("_")]) == 25
    assert bounded_dict["_truncated_keys"] == 10

    # 3. Item count bounding (max_items=25)
    long_list = list(range(35))
    bounded_list = sanitize_and_bound_payload(long_list, max_items=25)
    assert len(bounded_list) == 26  # 25 items + 1 truncation marker
    assert bounded_list[-1] == "[TRUNCATED_ITEMS]"

    # 4. String length bounding (max_str_len=500)
    long_str = "x" * 1000
    bounded_str = sanitize_and_bound_payload(long_str, max_str_len=500)
    assert len(bounded_str) == 500 + len("...[truncated]")
    assert bounded_str.endswith("...[truncated]")

    # 5. Total payload byte bounding (max_bytes=4096)
    large_payload = {f"k{i}": "y" * 300 for i in range(25)}
    bounded_large = sanitize_and_bound_payload(large_payload, max_bytes=1024)
    assert bounded_large.get("_payload_truncated") is True
    assert bounded_large.get("_byte_length") > 1024

