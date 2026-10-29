from haq.guide import ABSTENTION_MESSAGE, build_guide
from haq.retrieve import Retriever


def test_abstains_when_no_verified_passage_matches() -> None:
    result = build_guide("how do I renew my passport")
    assert result.abstained is True
    assert result.passages == ()
    assert result.message == ABSTENTION_MESSAGE


def test_empty_question_asks_for_input() -> None:
    result = build_guide("   ")
    assert result.abstained is True
    assert "Enter a question" in result.message


def test_guide_returns_source_ids_and_passages() -> None:
    retriever = Retriever()
    result = build_guide("landlord is not returning my security deposit", retriever=retriever)
    assert result.abstained is False
    assert result.passages
    assert result.source_ids == tuple(passage.id for passage in result.passages)
    assert all(passage.id in set(retriever.source_ids()) for passage in result.passages)


def test_guide_respects_category_selection() -> None:
    result = build_guide("complaint time limit", category="consumer")
    assert result.abstained is False
    assert all(passage.category == "consumer" for passage in result.passages)


def test_guide_says_it_is_not_a_legal_opinion() -> None:
    result = build_guide("security deposit")
    assert "not a legal opinion" in result.message
