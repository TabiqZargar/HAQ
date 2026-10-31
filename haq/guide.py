"""Source-grounded guidance assembly with explicit abstention."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import RLock

from haq.retrieve import (
    DEFAULT_LIBRARY_DIR,
    Retriever,
    RetrievedPassage,
    library_signature,
)

CATEGORY_LABELS = {
    "All": "All topics",
    "tenancy": "Tenancy",
    "consumer": "Consumer",
    "labour": "Unpaid wages",
}

ABSTENTION_MESSAGE = (
    "I could not find a verified law-library passage that is relevant to this question. "
    "I will not guess or invent a legal rule. Please use the legal-aid contacts below, "
    "or rephrase the question with the type of problem and the document or notice involved."
)


@dataclass(frozen=True)
class GuideResult:
    query: str
    category: str
    passages: tuple[RetrievedPassage, ...]
    abstained: bool
    message: str

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(passage.id for passage in self.passages)


_RETRIEVER_LOCK = RLock()


@lru_cache(maxsize=4)
def _cached_retriever(
    library_dir: str, _signature: tuple[tuple[str, int, int], ...]
) -> Retriever:
    return Retriever(library_dir=library_dir)


def get_retriever(library_dir: Path | str = DEFAULT_LIBRARY_DIR) -> Retriever:
    """Return a cached immutable index, rebuilding it when source files change."""

    root = Path(library_dir)
    signature = library_signature(root)
    with _RETRIEVER_LOCK:
        return _cached_retriever(str(root.resolve()), signature)


def clear_retriever_cache() -> None:
    """Drop cached retrievers; primarily useful for tests and development."""

    with _RETRIEVER_LOCK:
        _cached_retriever.cache_clear()


def build_guide(
    query: str,
    category: str = "All",
    *,
    retriever: Retriever | None = None,
) -> GuideResult:
    """Find verified passages and prepare a non-conclusory summary."""

    cleaned = " ".join((query or "").split())
    if not cleaned:
        return GuideResult(
            query="",
            category=category,
            passages=(),
            abstained=True,
            message="Enter a question about a tenancy, consumer, or unpaid-wage problem.",
        )

    active_retriever = retriever or get_retriever()
    passages = active_retriever.search(cleaned, category=category, top_k=3)

    if not passages:
        return GuideResult(
            query=cleaned,
            category=category,
            passages=(),
            abstained=True,
            message=ABSTENTION_MESSAGE,
        )

    if len(passages) == 1:
        message = (
            "I found one verified source passage. The quoted text and the plain-language "
            "summary below are limited to that passage and are not a legal opinion."
        )
    else:
        message = (
            f"I found {len(passages)} verified source passages. Read the quoted text and "
            "the plain-language summaries together; they are not a legal opinion."
        )

    return GuideResult(
        query=cleaned,
        category=category,
        passages=passages,
        abstained=False,
        message=message,
    )
