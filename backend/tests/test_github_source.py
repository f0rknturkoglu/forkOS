from __future__ import annotations

import pytest

from app.sources.github import parse_github_payload

pytestmark = pytest.mark.no_database


def test_github_payload_skips_null_repository_nodes():
    payload = {
        "data": {
            "user": {
                "contributionsCollection": {
                    "contributionCalendar": {
                        "weeks": [
                            {
                                "contributionDays": [
                                    {"date": "2026-08-29", "contributionCount": 3}
                                ]
                            }
                        ]
                    }
                },
                "repositoriesContributedTo": {"nodes": [None]},
            }
        }
    }
    items = parse_github_payload(payload, "forkan")
    assert len(items) == 1
    assert items[0].external_id == "day:2026-08-29"
