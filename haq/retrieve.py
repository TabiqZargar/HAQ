"""Small, local TF-IDF retriever for verified law-library excerpts."""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Iterable, Sequence

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

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


def library_signature(
    library_dir: Path | str = DEFAULT_LIBRARY_DIR,
) -> tuple[tuple[str, int, int], ...]:
    """Return a cheap fingerprint that changes when source files change."""

    root = Path(library_dir)
    if not root.exists():
        raise FileNotFoundError(f"Law library not found: {root}")

    signature: list[tuple[str, int, int]] = []
    with os.scandir(root) as categories:
        for category in categories:
            if not category.is_dir():
                continue
            with os.scandir(category.path) as files:
                for file in files:
                    if not file.name.endswith(".json"):
                        continue
                    stat = file.stat()
                    signature.append(
                        (
                            f"{category.name}/{file.name}",
                            stat.st_mtime_ns,
                            stat.st_size,
                        )
                    )
    signature.sort()
    return tuple(signature)


@lru_cache(maxsize=8)
def _load_entries_cached(
    root: str, _signature: tuple[tuple[str, int, int], ...]
) -> tuple[RetrievedPassage, ...]:
    entries: list[RetrievedPassage] = []
    seen_ids: set[str] = set()
    for path in sorted(Path(root).glob("*/*.json")):
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


def load_entries(library_dir: Path | str = DEFAULT_LIBRARY_DIR) -> tuple[RetrievedPassage, ...]:
    """Load and validate every JSON source list under the law library."""

    root = Path(library_dir)
    signature = library_signature(root)
    return _load_entries_cached(str(root.resolve()), signature)


class Retriever:
    """TF-IDF cosine-similarity search over verified excerpts."""

    def __init__(
        self,
        entries: Sequence[RetrievedPassage] | None = None,
        *,
        library_dir: Path | str = DEFAULT_LIBRARY_DIR,
        min_score: float = DEFAULT_MIN_SCORE,
        relative_score: float = DEFAULT_RELATIVE_SCORE,
        query_cache_size: int = 128,
    ) -> None:
        self.entries = tuple(entries) if entries is not None else load_entries(library_dir)
        if not self.entries:
            raise ValueError("Retriever requires at least one entry")
        self.min_score = min_score
        self.relative_score = relative_score
        self._query_cache_size = max(0, query_cache_size)
        self._query_cache: OrderedDict[
            tuple[str, str, int], tuple[RetrievedPassage, ...]
        ] = OrderedDict()
        self._query_cache_lock = RLock()
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words=list(ENGLISH_STOP_WORDS | GENERIC_QUERY_WORDS),
            ngram_range=(1, 2),
            sublinear_tf=True,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9']+\b",
        )
        self._matrix = self._vectorizer.fit_transform(
            self._document(entry) for entry in self.entries
        )
<<<<<<< HEAD
        indices_by_category: dict[str, list[int]] = {}
        for index, entry in enumerate(self.entries):
            indices_by_category.setdefault(entry.category, []).append(index)
        self._all_indices = tuple(range(len(self.entries)))
        self._indices_by_category = {
            category: tuple(indices) for category, indices in indices_by_category.items()
        }
=======
        self._feature_names = self._vectorizer.get_feature_names_out()
        self._doc_terms = tuple(frozenset(row.indices) for row in self._matrix)
>>>>>>> 410afaecea8376bf598ca8a3d28db59a81de8dfe

    @staticmethod
    def _document(entry: RetrievedPassage) -> str:
        tags = " ".join(entry.topic_tags)
        return " ".join((entry.title, entry.section, tags, entry.text))

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({entry.category for entry in self.entries}))

<<<<<<< HEAD
    def clear_query_cache(self) -> None:
        """Drop cached results for this immutable index."""

        with self._query_cache_lock:
            self._query_cache.clear()
=======
    def _shares_enough_terms(
        self,
        index: int,
        query_unigrams: set[int],
        query_phrases: set[int],
    ) -> bool:
        """Reject passages that share only one incidental word with the query.

        On a small corpus a single rare token can clear the score threshold while
        the rest of the question matches nothing (for example "register a company"
        against a wage-liability passage). A passage must therefore share at least
        two distinct query words, or one multi-word phrase, with the question. A
        one-word question is still allowed to match that single word.
        """

        doc_terms = self._doc_terms[index]
        unigram_hits = len(query_unigrams & doc_terms)
        if unigram_hits >= 2:
            return True
        if query_phrases & doc_terms:
            return True
        return len(query_unigrams) == 1 and unigram_hits == 1
>>>>>>> 410afaecea8376bf598ca8a3d28db59a81de8dfe

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

<<<<<<< HEAD
        cache_key = (cleaned, category or "", top_k)
        if self._query_cache_size:
            with self._query_cache_lock:
                cached = self._query_cache.get(cache_key)
                if cached is not None:
                    self._query_cache.move_to_end(cache_key)
                    return cached
=======
        query_vector = self._vectorizer.transform([cleaned])
        query_features = set(query_vector.nonzero()[1].tolist())
        query_unigrams = {
            index for index in query_features if " " not in self._feature_names[index]
        }
        query_phrases = query_features - query_unigrams
        scores = cosine_similarity(query_vector, self._matrix).ravel()
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        candidates = [
            (index, float(score))
            for index, score in ranked
            if (not category or category == "All" or self.entries[index].category == category)
            and self._shares_enough_terms(index, query_unigrams, query_phrases)
        ]
        if not candidates or candidates[0][1] < self.min_score:
            return ()
>>>>>>> 410afaecea8376bf598ca8a3d28db59a81de8dfe

        if not category or category == "All":
            candidate_indices = self._all_indices
        else:
            candidate_indices = self._indices_by_category.get(category, ())

        query_vector = self._vectorizer.transform([cleaned])
        if not candidate_indices:
            results: tuple[RetrievedPassage, ...] = ()
        else:
            scores = (self._matrix @ query_vector.T).toarray().ravel()
            ranked = sorted(candidate_indices, key=scores.__getitem__, reverse=True)
            top_score = float(scores[ranked[0]])
            if top_score < self.min_score:
                results = ()
            else:
                relative_floor = max(self.min_score, top_score * self.relative_score)
                selected: list[RetrievedPassage] = []
                for index in ranked:
                    score = float(scores[index])
                    if score < relative_floor:
                        break
                    entry = self.entries[index]
                    selected.append(
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
                            score=score,
                        )
                    )
                    if len(selected) >= top_k:
                        break
                results = tuple(selected)

        if self._query_cache_size:
            with self._query_cache_lock:
                self._query_cache[cache_key] = results
                self._query_cache.move_to_end(cache_key)
                while len(self._query_cache) > self._query_cache_size:
                    self._query_cache.popitem(last=False)
        return results

    def source_ids(self) -> Iterable[str]:
        return (entry.id for entry in self.entries)
