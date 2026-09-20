import uuid

import pytest
from pydantic import ValidationError

from app.integrations.agent.models import KnowledgePointer
from app.integrations.agent.write_models import (
    ActionReceipt,
    ApplicationTransitionIn,
    BookmarkCaptureIn,
    BookmarkUpdateIn,
    BrainCaptureIn,
    BrainSaveToEntityIn,
    OpportunityTransitionIn,
    ProjectUpdateIn,
    TodoCreateIn,
    TodoPlanIn,
    TodoUpdateIn,
)

pytestmark = pytest.mark.no_database


def test_action_receipt():
    uid = str(uuid.uuid4())
    r = ActionReceipt(
        request_id="req-123",
        tool="forkos_todo_create",
        status="executed",
        target_type="todo",
        target_id=uid,
        summary="Created todo: Buy milk",
        changed_fields=["status", "priority"],
        before={},
        after={"title": "Buy milk", "priority": 1},
        warnings=[],
    )
    assert r.status == "executed"
    assert r.request_id == "req-123"
    assert r.changed_fields == ["status", "priority"]

    # Test defaults
    r_defaults = ActionReceipt(
        tool="forkos_todo_complete",
        status="noop",
        target_type="todo",
        target_id=uid,
        summary="Already done",
    )
    assert r_defaults.request_id is None
    assert r_defaults.changed_fields == []
    assert r_defaults.before == {}
    assert r_defaults.after == {}
    assert r_defaults.warnings == []

    # Invalid status
    with pytest.raises(ValidationError):
        ActionReceipt(
            tool="forkos_todo_create",
            status="failed",  # type: ignore[arg-type]
            target_type="todo",
            target_id=uid,
            summary="Failed",
        )


def test_todo_create_bounds():
    # Valid minimal
    m = TodoCreateIn(title="  Buy milk  ")
    assert m.title == "Buy milk"
    assert m.priority == 2
    assert m.description is None
    assert m.recur is None

    # Title empty / whitespace
    with pytest.raises(ValidationError):
        TodoCreateIn(title="   ")

    # Title too long
    with pytest.raises(ValidationError):
        TodoCreateIn(title="x" * 301)

    # Description max 5000
    m_desc = TodoCreateIn(title="Test", description="d" * 5000)
    assert len(m_desc.description) == 5000
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", description="d" * 5001)

    # Priority 0..3
    assert TodoCreateIn(title="Test", priority=0).priority == 0
    assert TodoCreateIn(title="Test", priority=3).priority == 3
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", priority=-1)
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", priority=4)

    # Datetimes and date validation
    valid_iso = "2026-09-25T14:30:00Z"
    m_dates = TodoCreateIn(
        title="Test",
        due_at=valid_iso,
        reminder_at=valid_iso,
        plan_day="2026-09-25",
    )
    assert m_dates.due_at == valid_iso
    assert m_dates.plan_day == "2026-09-25"

    # Whitespace stripping on datetimes
    m_ws_date = TodoCreateIn(title="Test", due_at=" 2026-09-25T14:30:00Z ")
    assert m_ws_date.due_at == "2026-09-25T14:30:00Z"

    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", due_at="invalid-date")
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", plan_day="2026/09/25")
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", plan_day="2026-02-30")

    # UUID fields
    valid_uuid = str(uuid.uuid4())
    m_uuids = TodoCreateIn(
        title="Test",
        project_id=valid_uuid,
        milestone_id=valid_uuid,
        parent_id=valid_uuid,
    )
    assert m_uuids.project_id == valid_uuid

    # Whitespace stripping on UUID
    m_ws_uuid = TodoCreateIn(title="Test", project_id=" 11111111-1111-1111-1111-111111111111 ")
    assert m_ws_uuid.project_id == "11111111-1111-1111-1111-111111111111"

    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", project_id="not-a-uuid")

    # Tags: max 20, max 50 chars each
    valid_tags = [f"tag-{i}" for i in range(20)]
    m_tags = TodoCreateIn(title="Test", tags=valid_tags)
    assert len(m_tags.tags) == 20

    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", tags=[f"tag-{i}" for i in range(21)])
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", tags=["x" * 51])

    # Recur
    assert TodoCreateIn(title="Test", recur="daily").recur == "daily"
    assert TodoCreateIn(title="Test", recur="weekdays").recur == "weekdays"
    with pytest.raises(ValidationError):
        TodoCreateIn(title="Test", recur="yearly")  # type: ignore[arg-type]


def test_todo_update_extra_forbid():
    valid_uuid = str(uuid.uuid4())
    m = TodoUpdateIn(todo_id=valid_uuid, title="Updated Title", priority=3)
    assert m.title == "Updated Title"
    assert m.priority == 3

    # Empty string recur allows clearing recurrence
    m_clear_recur = TodoUpdateIn(todo_id=valid_uuid, recur="")
    assert m_clear_recur.recur == ""

    # Extra forbid: status, delete, parent_id
    with pytest.raises(ValidationError):
        TodoUpdateIn(todo_id=valid_uuid, status="done")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        TodoUpdateIn(todo_id=valid_uuid, delete=True)  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        TodoUpdateIn(todo_id=valid_uuid, parent_id=valid_uuid)  # type: ignore[call-arg]

    # Bounds
    with pytest.raises(ValidationError):
        TodoUpdateIn(todo_id="bad-uuid")
    with pytest.raises(ValidationError):
        TodoUpdateIn(todo_id=valid_uuid, title="   ")
    with pytest.raises(ValidationError):
        TodoUpdateIn(todo_id=valid_uuid, priority=4)


def test_todo_plan_bounds():
    valid_uuid = str(uuid.uuid4())
    m = TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", start_min=540, duration_min=60)
    assert m.day == "2026-09-25"
    assert m.start_min == 540
    assert m.duration_min == 60

    # Bounds on start_min (0..1439)
    assert TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", start_min=0).start_min == 0
    assert TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", start_min=1439).start_min == 1439
    with pytest.raises(ValidationError):
        TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", start_min=-1)
    with pytest.raises(ValidationError):
        TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", start_min=1440)

    # Bounds on duration_min (5..1440)
    assert TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", duration_min=5).duration_min == 5
    assert TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", duration_min=1440).duration_min == 1440
    with pytest.raises(ValidationError):
        TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", duration_min=4)
    with pytest.raises(ValidationError):
        TodoPlanIn(todo_id=valid_uuid, day="2026-09-25", duration_min=1441)


def test_project_update_disallows_rename():
    valid_uuid = str(uuid.uuid4())
    m = ProjectUpdateIn(project_id=valid_uuid, next_action="Ship H1")
    assert m.next_action == "Ship H1"

    # Next action stripped
    m_ws = ProjectUpdateIn(project_id=valid_uuid, next_action="  Ship H1  ")
    assert m_ws.next_action == "Ship H1"

    # Next action max 500 chars
    with pytest.raises(ValidationError):
        ProjectUpdateIn(project_id=valid_uuid, next_action="x" * 501)

    # Extra forbid: rename / title / status / delete
    with pytest.raises(ValidationError):
        ProjectUpdateIn(project_id=valid_uuid, title="Renamed Project")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        ProjectUpdateIn(title="Renamed Project")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        ProjectUpdateIn(project_id=valid_uuid, status="completed")  # type: ignore[call-arg]


def test_opportunity_transition_bounds():
    valid_uuid = str(uuid.uuid4())
    m = OpportunityTransitionIn(
        opportunity_id=valid_uuid,
        expected_status="lead",
        to_status="evaluating",
        note="Good lead",
    )
    assert m.expected_status == "lead"
    assert m.to_status == "evaluating"

    # expected_status is mandatory
    with pytest.raises(ValidationError):
        OpportunityTransitionIn(
            opportunity_id=valid_uuid,
            to_status="evaluating",  # type: ignore[call-arg]
        )

    # Note max 1000 chars
    with pytest.raises(ValidationError):
        OpportunityTransitionIn(
            opportunity_id=valid_uuid,
            expected_status="lead",
            to_status="evaluating",
            note="x" * 1001,
        )


def test_application_transition_bounds():
    valid_uuid = str(uuid.uuid4())
    # expected_status is optional for first apply
    m_first = ApplicationTransitionIn(
        opportunity_id=valid_uuid,
        to_status="applied",
    )
    assert m_first.expected_status is None
    assert m_first.to_status == "applied"

    # rejection_reason max 200 chars
    m_rej = ApplicationTransitionIn(
        opportunity_id=valid_uuid,
        expected_status="interviewing",
        to_status="rejected",
        rejection_reason="Position cancelled",
    )
    assert m_rej.rejection_reason == "Position cancelled"

    with pytest.raises(ValidationError):
        ApplicationTransitionIn(
            opportunity_id=valid_uuid,
            to_status="rejected",
            rejection_reason="r" * 201,
        )

    with pytest.raises(ValidationError):
        ApplicationTransitionIn(
            opportunity_id=valid_uuid,
            to_status="applied",
            note="n" * 1001,
        )


def test_bookmark_capture_bounds():
    m = BookmarkCaptureIn(
        url="https://example.com/article",
        title="Sample",
        collection="inbox",
    )
    assert m.url == "https://example.com/article"
    assert m.collection == "inbox"

    # Default collection is inbox
    m_default = BookmarkCaptureIn(url="http://example.com")
    assert m_default.collection == "inbox"

    # URL must start with http:// or https:// and have non-empty host
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="https://")
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="ftp://example.com")
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="javascript:alert(1)")
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="example.com")

    # URL max 2048 chars
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="https://example.com/" + ("a" * 2040))

    # Title max 300 chars
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="https://example.com", title="t" * 301)

    # Note max 5000 chars
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="https://example.com", note="n" * 5001)

    # Tags max 20
    with pytest.raises(ValidationError):
        BookmarkCaptureIn(url="https://example.com", tags=[f"t{i}" for i in range(21)])

    # Tags stripping and ignoring empty
    m_clean_tags = BookmarkCaptureIn(url="https://example.com", tags=["  tag1 ", "   ", "tag2  "])
    assert m_clean_tags.tags == ["tag1", "tag2"]


def test_bookmark_update_bounds():
    valid_uuid = str(uuid.uuid4())
    m = BookmarkUpdateIn(
        bookmark_id=valid_uuid,
        collection="archive",
        favorite=True,
        read_status="read",
        expected_updated_at="2026-09-25T10:00:00Z",
    )
    assert m.collection == "archive"
    assert m.favorite is True
    assert m.read_status == "read"

    # Extra forbid
    with pytest.raises(ValidationError):
        BookmarkUpdateIn(bookmark_id=valid_uuid, title="Extra Field")  # type: ignore[call-arg]

    with pytest.raises(ValidationError):
        BookmarkUpdateIn(bookmark_id="not-a-uuid")
    with pytest.raises(ValidationError):
        BookmarkUpdateIn(bookmark_id=valid_uuid, read_status="finished")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        BookmarkUpdateIn(bookmark_id=valid_uuid, collection="deleted")  # type: ignore[arg-type]


def test_brain_capture_bounds():
    m = BrainCaptureIn(
        body="Captured note content",
        title="My Note",
    )
    assert m.body == "Captured note content"

    # Body stripped and non-empty
    with pytest.raises(ValidationError):
        BrainCaptureIn(body="   ")

    # Body max 40000 chars
    m_max = BrainCaptureIn(body="c" * 40000)
    assert len(m_max.body) == 40000

    with pytest.raises(ValidationError):
        BrainCaptureIn(body="c" * 40001)

    # Title max 300 chars
    with pytest.raises(ValidationError):
        BrainCaptureIn(body="Valid", title="t" * 301)

    # Relate to UUID
    valid_uuid = str(uuid.uuid4())
    m_rel = BrainCaptureIn(body="Valid", relate_to=valid_uuid)
    assert m_rel.relate_to == valid_uuid
    with pytest.raises(ValidationError):
        BrainCaptureIn(body="Valid", relate_to="not-uuid")


def test_brain_save_to_entity_extra_forbid():
    valid_uuid = str(uuid.uuid4())
    m = BrainSaveToEntityIn(
        forkos_id=valid_uuid,
        text="Appended log line",
        heading="## Log",
    )
    assert m.forkos_id == valid_uuid
    assert m.text == "Appended log line"
    assert m.heading == "## Log"

    # Text stripped and non-empty
    with pytest.raises(ValidationError):
        BrainSaveToEntityIn(forkos_id=valid_uuid, text="   ")

    # Text max 20000 chars
    m_max = BrainSaveToEntityIn(forkos_id=valid_uuid, text="x" * 20000)
    assert len(m_max.text) == 20000

    with pytest.raises(ValidationError):
        BrainSaveToEntityIn(forkos_id=valid_uuid, text="x" * 20001)

    # Heading max 200 chars
    with pytest.raises(ValidationError):
        BrainSaveToEntityIn(forkos_id=valid_uuid, text="Valid", heading="h" * 201)

    # Strictly disallow relative_path!
    with pytest.raises(ValidationError):
        BrainSaveToEntityIn(  # type: ignore[call-arg]
            forkos_id=valid_uuid,
            text="Valid",
            relative_path="projects/my-note.md",
        )


def test_knowledge_pointer_contains():
    kp = KnowledgePointer(
        state="available",
        available=True,
        forkos_id=str(uuid.uuid4()),
        relative_path="projects/p.md",
        title="Project Note",
    )
    # Model fields must be recognized by 'in'
    assert "state" in kp
    assert "available" in kp
    assert "forkos_id" in kp
    assert "relative_path" in kp
    assert "title" in kp
    assert "diagnostic" in kp

    # Non-fields must NOT be in kp
    assert "nonexistent" not in kp
    # Built-ins must NOT be in kp (unlike hasattr)
    assert "__class__" not in kp
    assert "model_dump" not in kp
