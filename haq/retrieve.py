"""Small, local TF-IDF retriever for verified law-library excerpts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REQUIRED_FIELDS = (
    "id",
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
)

DEFAULT_LIBRARY_DIR = Path(__file__).resolve().parent.parent / "law_library"
DEFAULT_MIN_SCORE = 0.10
DEFAULT_RELATIVE_SCORE = 0.65
GENERIC_QUERY_WORDS = {
    "right",
    "rights",
    "law",
    "legal",
    "help",
    "option",
    "options",
    "know",
    "question",
}


@dataclass(frozen=True)
class RetrievedPassage:
    id: str
    title: str
    section: str
    jurisdiction: str
    source_url: str
    collection_date: str
    verification_status: str
    category: str
    source_type: str
    topic_tags: tuple[str, ...]
    text: str
    plain_summary: str
    applicability_note: str
    score: float

    @property
    def citation(self) -> str:
        return f"{self.title}, {self.section}"


def _entry_from_mapping(entry: dict) -> RetrievedPassage:
    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        raise ValueError(f"Law-library entry is missing fields: {', '.join(missing)}")

    tags = entry["topic_tags"]
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError(f"{entry['id']}: topic_tags must be a list of strings")
    if entry["verification_status"] != "verified_official":
        raise ValueError(f"{entry['id']}: only verified_official entries may be indexed")
    if not isinstance(entry["text"], str) or len(entry["text"].strip()) < 40:
        raise ValueError(f"{entry['id']}: text is too short to use as a source")
    if not str(entry["source_url"]).startswith(("https://", "http://")):
        raise ValueError(f"{entry['id']}: source_url must be an official HTTP(S) URL")
    if not str(entry["collection_date"]).strip():
        raise ValueError(f"{entry['id']}: collection_date is required")

    return RetrievedPassage(
        id=entry["id"],
        title=entry["title"],
        section=entry["section"],
        jurisdiction=entry["jurisdiction"],
        source_url=entry["source_url"],
        collection_date=entry["collection_date"],
        verification_status=entry["verification_status"],
        category=entry["category"],
        source_type=entry["source_type"],
        topic_tags=tuple(tags),
        text=entry["text"],
        plain_summary=entry["plain_summary"],
        applicability_note=entry["applicability_note"],
        score=0.0,
    )


def load_entries(library_dir: Path | str = DEFAULT_LIBRARY_DIR) -> tuple[RetrievedPassage, ...]:
    """Load and validate every JSON source list under the law library."""

    root = Path(library_dir)
    if not root.exists():
        raise FileNotFoundError(f"Law library not found: {root}")

    entries: list[RetrievedPassage] = []
    seen_ids: set[str] = set()
    for path in sorted(root.glob("*/*.json")):
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected a JSON list")
        for raw in data:
            if not isinstance(raw, dict):
                raise ValueError(f"{path}: every entry must be an object")
            entry = _entry_from_mapping(raw)
            if entry.id in seen_ids:
                raise ValueError(f"Duplicate law-library id: {entry.id}")
            seen_ids.add(entry.id)
            entries.append(entry)

    if not entries:
        raise ValueError(f"No verified law-library entries found under {root}")
    return tuple(entries)


class Retriever:
    """TF-IDF cosine-similarity search over verified excerpts."""

    def __init__(
        self,
        entries: Sequence[RetrievedPassage] | None = None,
        *,
        library_dir: Path | str = DEFAULT_LIBRARY_DIR,
        min_score: float = DEFAULT_MIN_SCORE,
        relative_score: float = DEFAULT_RELATIVE_SCORE,
    ) -> None:
        self.entries = tuple(entries) if entries is not None else load_entries(library_dir)
        if not self.entries:
            raise ValueError("Retriever requires at least one entry")
        self.min_score = min_score
        self.relative_score = relative_score
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=list(ENGLISH_STOP_WORDS | GENERIC_QUERY_WORDS),
            ngram_range=(1, 2),
            sublinear_tf=True,
            token_pattern=r"(?u)\b[a-zA-Z0-9]+(?:'[a-zA-Z]+)?\b",
        )
        self._matrix = self._vectorizer.fit_transform(
            self._document(entry) for entry in self.entries
        )

    @staticmethod
    def _document(entry: RetrievedPassage) -> str:
        tags = " ".join(entry.topic_tags)
        return " ".join((entry.title, entry.section, tags, entry.text))

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({entry.category for entry in self.entries}))

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        top_k: int = 3,
    ) -> tuple[RetrievedPassage, ...]:
        """Return relevant passages above the abstention threshold."""

        cleaned = " ".join((query or "").split())
        if not cleaned or top_k < 1:
            return ()

        query_vector = self._vectorizer.transform([cleaned])
        scores = cosine_similarity(query_vector, self._matrix).ravel()
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        candidates = [
            (index, float(score))
            for index, score in ranked
            if not category or category == "All" or self.entries[index].category == category
        ]
        if not candidates or candidates[0][1] < self.min_score:
            return ()

        relative_floor = max(self.min_score, candidates[0][1] * self.relative_score)
        results: list[RetrievedPassage] = []
        for index, score in candidates:
            if score < relative_floor:
                break
            entry = self.entries[index]
            results.append(
                RetrievedPassage(
                    id=entry.id,
                    title=entry.title,
                    section=entry.section,
                    jurisdiction=entry.jurisdiction,
                    source_url=entry.source_url,
                    collection_date=entry.collection_date,
                    verification_status=entry.verification_status,
                    category=entry.category,
                    source_type=entry.source_type,
                    topic_tags=entry.topic_tags,
                    text=entry.text,
                    plain_summary=entry.plain_summary,
                    applicability_note=entry.applicability_note,
                    score=float(score),
                )
            )
            if len(results) >= top_k:
                break
        return tuple(results)

    def source_ids(self) -> Iterable[str]:
        return (entry.id for entry in self.entries)
