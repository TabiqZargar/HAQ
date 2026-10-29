from haq.notice import extract_notice_facts


SAMPLE_NOTICE = """NOTICE NO. LD/2026/045
From: Rakesh Sharma
To: Meera Khan
Date: 15 November 2026

You are hereby notified to vacate the premises on or before 30 November 2026.
Payment of Rs. 45,000/- is due within 15 days from receipt of this notice.
Reference: ABC/123.
"""


def test_extracts_explicit_notice_facts() -> None:
    facts = extract_notice_facts(SAMPLE_NOTICE)
    assert "15 November 2026" in facts.dates
    assert "30 November 2026" in facts.dates
    assert "Rs. 45,000" in facts.amounts
    assert "Rakesh Sharma" in facts.parties
    assert "Meera Khan" in facts.parties
    assert "LD/2026/045" in facts.reference_numbers
    assert "ABC/123" in facts.reference_numbers
    assert any("within 15 days" in phrase for phrase in facts.deadline_language)
    assert any("on or before 30 November 2026" in phrase for phrase in facts.deadline_language)
    assert facts.has_facts is True


def test_does_not_infer_a_deadline_from_relative_language_alone() -> None:
    facts = extract_notice_facts("Please vacate the premises soon. This is urgent.")
    assert facts.dates == ()
    assert facts.deadline_language == ()


def test_does_not_turn_within_fifteen_days_into_a_calendar_date() -> None:
    facts = extract_notice_facts("You must pay within 15 days of this notice.")
    assert facts.dates == ()
    assert facts.deadline_language == ("within 15 days of this notice",)


def test_empty_notice_has_no_facts() -> None:
    facts = extract_notice_facts("   ")
    assert facts.has_facts is False
    assert facts.dates == ()
    assert facts.amounts == ()
    assert facts.parties == ()
    assert facts.reference_numbers == ()
    assert facts.deadline_language == ()


def test_extracts_numeric_and_month_first_dates() -> None:
    facts = extract_notice_facts("Hearing is on 05/12/2026. Reply by December 5, 2026.")
    assert "05/12/2026" in facts.dates
    assert "December 5, 2026" in facts.dates
    assert "by December 5, 2026" in facts.deadline_language
