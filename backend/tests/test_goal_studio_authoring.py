"""Authoring content never skips the canonical proposal and approval boundary."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.goal.studio import public_reply
from app.modules.goal.studio_authoring import canonical_proposal

pytestmark = pytest.mark.no_database


def exam():
    return {
        "kind": "goal",
        "title": "YDS 60+",
        "description": "45 gün, günde 4 saat: kelime, gramer, okuma ve deneme.",
        "target_date": "2026-11-26",
        "metric": {"title": "YDS puanı", "target_value": 60, "unit": "puan"},
        "milestones": [{"title": "Seviyeni bir denemeyle belirle", "due_date": "2026-10-13"}],
        "missing_information": ["Mevcut İngilizce seviyesi"],
    }


def test_exam_preserves_authored_constraints_with_unknown_measurement():
    draft = canonical_proposal(exam())
    goal, metric, milestone = draft.operations
    assert goal.data.target_at.date().isoformat() == "2026-11-26"
    assert goal.data.target_at.utcoffset().total_seconds() == 10800
    assert metric.data.target_value == 60
    assert metric.data.manual_value is None
    assert metric.goal_ref == milestone.goal_ref == goal.key
    assert "4 saat" in goal.data.description


def test_five_year_plan_binds_goals_without_model_supplied_ids():
    value = {
        "kind": "plan",
        "title": "Beş yıllık yol haritası",
        "description": "Uzmanlık geliştir.",
        "start_date": "2026-10-12",
        "end_date": "2031-10-12",
        "goals": [{"title": "Uzmanlık", "description": "Projeler ve öğrenme."}],
    }
    plan, goal = canonical_proposal(value).operations
    assert goal.plan_ref == plan.key and goal.data.horizon == "long_term"
    assert plan.data.end_at.year - plan.data.start_at.year == 5
    value["end_date"] = value["start_date"]
    with pytest.raises(ValidationError):
        canonical_proposal(value)


def test_edit_binds_only_the_user_selected_goal():
    selected = str(uuid4())
    goal, metric, milestone = canonical_proposal(exam(), goal_id=selected).operations
    assert goal.type == "goal.update" and str(goal.target_id) == selected
    assert metric.goal_ref == milestone.goal_ref == selected


@pytest.mark.parametrize(
    "key,value",
    [
        ("approved", True),
        ("target_id", str(uuid4())),
        ("status", "completed"),
        ("manual_value", 60),
    ],
)
def test_authoring_rejects_permission_state_and_measurements(key, value):
    invalid = {**exam(), key: value}
    with pytest.raises(ValidationError):
        canonical_proposal(invalid)


def test_one_public_envelope_with_preface_is_parsed_without_leaking_json_into_chat():
    envelope = {"discussion": "Taslağını düzenleyebilirsin.", "proposal": exam()}
    assert public_reply("İşte taslağın.\n```json\n" + json.dumps(envelope) + "\n```") == envelope
    with pytest.raises(ValueError):
        public_reply("<think>private</think>" + json.dumps(envelope))
    with pytest.raises(ValueError):
        public_reply(json.dumps(envelope) + " another payload")


def test_only_one_omitted_final_object_delimiter_can_be_repaired():
    envelope = {"discussion": "Taslak", "proposal": exam()}
    encoded = json.dumps(envelope)
    assert public_reply(encoded[:-1]) == envelope
    with pytest.raises(ValueError):
        public_reply(encoded[:-2])
    with pytest.raises(ValueError):
        public_reply('{"discussion":"truncated text')


def test_relative_user_deadline_is_anchored_to_original_local_message_day():
    from app.modules.goal.studio_authoring import user_deadline

    data = {
        "turns": {
            "turn": {
                "message": "İlk kez giriyorum, 45 gün kaldı. Günde 4 saat.",
                "at": "2026-10-12T20:00:00+00:00",
            }
        }
    }
    deadline = user_deadline(data)
    assert deadline.isoformat() == "2026-11-26"
    draft = canonical_proposal({**exam(), "target_date": "2026-11-25"}, target_date=deadline)
    assert draft.operations[0].data.target_at.date() == deadline
    data["turns"]["later"] = {
        "message": "Süre değişti, 30 gün kaldı",
        "at": "2026-10-12T21:01:00+00:00",
    }
    assert user_deadline(data).isoformat() == "2026-11-12"
    assert (
        user_deadline(
            {
                "messages": [{"role": "assistant", "text": "10 gün kaldı"}],
                "context": {"text": "5 gün kaldı"},
            }
        )
        is None
    )


def test_nested_plan_notes_are_visible_without_authorizing_state_changes():
    value = {
        "kind": "plan",
        "title": "Kariyer",
        "description": "Beş yıl.",
        "start_date": "2026-10-12",
        "end_date": "2031-10-12",
        "goals": [
            {
                "title": "Uzmanlık",
                "description": "Projeler.",
                "assumptions": ["Haftada 5 saat"],
                "warnings": "",
            }
        ],
    }
    assert canonical_proposal(value).assumptions == ["Haftada 5 saat"]
