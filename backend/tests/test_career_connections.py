"""Career Ops yerel LinkedIn baglanti ayrıştırma testleri."""

import pytest

from app.modules.opportunity.career import normalize_company, parse_connections_csv

pytestmark = pytest.mark.no_database


def test_company_normalization_uses_stable_tokens():
    assert normalize_company("Siemens Energy GmbH") == "energy siemens"
    assert normalize_company("ACME, Inc.") == "acme"
    assert normalize_company("Acme Ltd") == "acme"


def test_linkedin_connections_csv_accepts_preamble_and_bom():
    content = (
        "\ufeffNotes:\n"
        "When exporting your connection data, some columns may be empty.\n\n"
        "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
        "Ada,Lovelace,https://www.linkedin.com/in/ada,ada@example.com,Acme Energy GmbH,"
        "Staff Engineer,04 Sep 2026\n"
    ).encode()

    rows = parse_connections_csv(content)

    assert rows == [
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "profile_url": "https://www.linkedin.com/in/ada",
            "email": "ada@example.com",
            "company": "Acme Energy GmbH",
            "position": "Staff Engineer",
            "connected_on": "04 Sep 2026",
        }
    ]


def test_invalid_connections_csv_is_rejected():
    with pytest.raises(ValueError, match="basliklari bulunamadi"):
        parse_connections_csv(b"name,organization\nAda,Acme\n")
