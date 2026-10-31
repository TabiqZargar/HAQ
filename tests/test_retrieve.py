import pytest

from haq.retrieve import Retriever, load_entries


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever()


def test_every_indexed_entry_is_verified(retriever: Retriever) -> None:
    assert retriever.entries
    assert all(entry.verification_status == "verified_official" for entry in retriever.entries)


def test_security_deposit_query_finds_model_law(retriever: Retriever) -> None:
    results = retriever.search("my landlord is not returning my security deposit")
    assert results
    assert results[0].id == "mta-2021-s11-security-deposit"
    assert "two months rent" in results[0].text


def test_notice_query_finds_transfer_of_property_act(retriever: Retriever) -> None:
    results = retriever.search(
        "how much notice does my landlord need to give to end a month to month lease"
    )
    assert results
    assert results[0].id == "tpa-1882-s106-notice"
    assert "fifteen days' notice" in results[0].text


def test_unpaid_salary_query_finds_wage_payment_rules(retriever: Retriever) -> None:
    results = retriever.search("my employer has not paid my salary")
    ids = {result.id for result in results}
    assert "code-on-wages-2019-s17-payment" in ids
    assert all(result.category == "labour" for result in results)


def test_consumer_time_limit_query_finds_consumer_limitation(retriever: Retriever) -> None:
    results = retriever.search("consumer complaint time limit", category="consumer")
    assert results
    assert results[0].id == "cp-2019-s69-1-limitation"
    assert "two years" in results[0].text


def test_category_filter_excludes_other_topics(retriever: Retriever) -> None:
    results = retriever.search("complaint time limit", category="consumer")
    assert results
    assert all(result.category == "consumer" for result in results)


def test_irrelevant_query_abstains(retriever: Retriever) -> None:
    assert retriever.search("how do I renew my passport") == ()


def test_generic_rights_question_abstains(retriever: Retriever) -> None:
    assert retriever.search("what are my rights") == ()


def test_single_shared_word_does_not_answer_an_unrelated_question(retriever: Retriever) -> None:
    assert retriever.search("how do I register a company") == ()


def test_one_word_query_still_finds_a_matching_passage(retriever: Retriever) -> None:
    results = retriever.search("eviction")
    assert results
    assert results[0].id == "mta-2021-s21-eviction"


def test_two_word_query_with_a_phrase_match_is_still_answered(retriever: Retriever) -> None:
    results = retriever.search("deposit refund")
    assert results
    assert results[0].id == "mta-2021-s11-security-deposit"


def test_number_in_question_does_not_match_unrelated_section_number(retriever: Retriever) -> None:
    results = retriever.search("landlord gave me 15 days notice to leave")
    assert results
    assert results[0].id == "tpa-1882-s106-notice"


def test_number_in_question_does_not_trigger_abstention(retriever: Retriever) -> None:
    results = retriever.search("I have not received my salary for 45 days")
    assert results
    assert results[0].id == "code-on-wages-2019-s17-payment"


def test_scores_are_descending_and_bounded(retriever: Retriever) -> None:
    results = retriever.search("landlord refusing repairs", top_k=3)
    assert results
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)


def test_legal_aid_eligibility_query_finds_nalsa_guidance(retriever: Retriever) -> None:
    results = retriever.search("who is eligible for free legal aid")
    assert results
    assert results[0].id == "nalsa-legal-aid-eligibility"
    assert "Section 12" in results[0].text


def test_legal_aid_application_query_finds_nalsa_procedure(retriever: Retriever) -> None:
    results = retriever.search("how do I apply for free legal aid")
    assert results
    assert results[0].id == "nalsa-legal-aid-apply"
    assert "front office" in results[0].text


def test_unrelated_question_does_not_return_legal_aid(retriever: Retriever) -> None:
    assert retriever.search("how do I renew my passport") == ()


def test_legal_aid_entries_have_valid_source_metadata(retriever: Retriever) -> None:
    legal_aid = [entry for entry in retriever.entries if entry.category == "legal_aid"]
    assert len(legal_aid) >= 3
    for entry in legal_aid:
        assert entry.verification_status == "verified_official"
        assert entry.source_url.startswith("https://nalsa.gov.in/")
        assert entry.collection_date == "2026-10-29"
        assert entry.jurisdiction == "India"
        assert entry.text.strip() and entry.plain_summary.strip()
        assert entry.applicability_note.strip()


def test_loaded_entries_have_official_http_urls() -> None:
    for entry in load_entries():
        assert entry.source_url.startswith("https://")
        assert entry.collection_date
        assert entry.text.strip()
        assert entry.plain_summary.strip()


def test_citation_contains_title_and_section(retriever: Retriever) -> None:
    result = retriever.search("security deposit")[0]
    assert result.title in result.citation
    assert result.section in result.citation


def test_query_cache_reuses_results() -> None:
    retriever = Retriever()
    first = retriever.search("security deposit")
    second = retriever.search("security deposit")
    assert first == second
    assert first is second


def test_query_cache_is_bounded_and_clearable() -> None:
    retriever = Retriever(query_cache_size=2)
    retriever.search("security deposit")
    retriever.search("consumer complaint time limit")
    retriever.search("unpaid wages")
    assert len(retriever._query_cache) == 2
    retriever.clear_query_cache()
    assert len(retriever._query_cache) == 0


def test_concurrent_searches_return_consistent_results() -> None:
    from concurrent.futures import ThreadPoolExecutor

    retriever = Retriever()
    queries = [
        "my landlord is not returning my security deposit",
        "consumer complaint time limit",
        "my employer has not paid my salary",
        "how do I renew my passport",
    ]
    expected = {query: retriever.search(query) for query in queries}
    tasks = queries * 50
    with ThreadPoolExecutor(max_workers=8) as executor:
        actual = list(executor.map(retriever.search, tasks))
    assert actual == [expected[query] for query in tasks]


def test_source_metadata_is_preserved_in_search_results(retriever: Retriever) -> None:
    source_by_id = {entry.id: entry for entry in retriever.entries}
    result = retriever.search("consumer complaint time limit")[0]
    source = source_by_id[result.id]
    for field in (
        "title",
        "section",
        "jurisdiction",
        "source_url",
        "collection_date",
        "verification_status",
        "category",
        "source_type",
        "topic_tags",
        "text",
        "plain_summary",
        "applicability_note",
    ):
        assert getattr(result, field) == getattr(source, field)
    assert 0.0 <= result.score <= 1.0


def test_load_entries_cache_invalidates_when_source_changes(tmp_path) -> None:
    import json
    from pathlib import Path

    source_path = Path("law_library/tenancy/sources.json")
    entry = json.loads(source_path.read_text(encoding="utf-8"))[0]
    target = tmp_path / "tenancy" / "sources.json"
    target.parent.mkdir()
    target.write_text(json.dumps([entry]), encoding="utf-8")

    first = load_entries(tmp_path)
    entry["title"] = f"{entry['title']} Updated"
    target.write_text(json.dumps([entry]), encoding="utf-8")
    second = load_entries(tmp_path)

    assert first is not second
    assert second[0].title.endswith("Updated")
