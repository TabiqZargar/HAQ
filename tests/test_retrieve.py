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


def test_scores_are_descending_and_bounded(retriever: Retriever) -> None:
    results = retriever.search("landlord refusing repairs", top_k=3)
    assert results
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= score <= 1.0 for score in scores)


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
