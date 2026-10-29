"""Optional local AI answers from a local Ollama model.

Everything here stays on the machine: the configured endpoint must be a
loopback address, and only the question plus the already-retrieved passages are
sent to it. Notices and uploaded documents are never sent. When this module is
not configured, unavailable, or returns an unusable answer, the app falls back
to retrieval-only results.

Ollama's chat API is used directly with the standard library:
https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from haq.retrieve import RetrievedPassage

ENV_BASE_URL = "HAQ_OLLAMA_URL"
ENV_MODEL = "HAQ_OLLAMA_MODEL"
ENV_TIMEOUT = "HAQ_OLLAMA_TIMEOUT"

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT = 120.0
MIN_TIMEOUT = 5.0
MAX_TIMEOUT = 300.0
MAX_QUESTION_CHARS = 2000
MAX_ANSWER_CHARS = 4000
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}

_SECTION_RE = re.compile(r"\b(?:section|sec\.?|s\.)\s*(\d+[A-Za-z]?)", re.I)
_LABEL_RE = re.compile(r"\[S(\d+)\]")

SYSTEM_PROMPT = (
    "You explain Indian legal information for Haq Guide, a non-lawyer information tool. "
    "Use ONLY the numbered passages in the user message. Cite the passages you rely on as "
    "[S1], [S2], and so on. Do not add any statute, section number, case, deadline, amount, "
    "eligibility rule, or legal conclusion that is not written in those passages. Do not "
    "predict an outcome and do not say what a person should do. If the passages do not answer "
    "the question or the evidence is insufficient, clearly say that the verified library does "
    "not cover it and direct the user to verify with an appropriate official source or qualified "
    "legal professional. Answer in plain language under 180 words, and end by saying this is "
    "general information, not legal advice."
)


class AIError(RuntimeError):
    """An AI request failed; the message is safe to show to users."""


class AIConfigError(AIError):
    """Local AI mode is not configured."""


@dataclass(frozen=True)
class AISettings:
    base_url: str = DEFAULT_BASE_URL
    model: str = ""
    timeout: float = DEFAULT_TIMEOUT

    @property
    def local_endpoint(self) -> bool:
        url = self.base_url
        if url and "://" not in url:
            url = f"http://{url}"
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        return host in _LOOPBACK_HOSTS or host.endswith(".localhost")

    @property
    def enabled(self) -> bool:
        return bool(self.model) and self.local_endpoint

    @property
    def missing(self) -> tuple[str, ...]:
        return () if self.model else (ENV_MODEL,)

    @property
    def problem(self) -> str:
        if not self.model:
            return (
                f"No local model tag is configured. Set {ENV_MODEL} to a tag from `ollama list`."
            )
        if not self.local_endpoint:
            return (
                "The configured endpoint is not a loopback address. This build only uses a "
                "local Ollama instance."
            )
        return ""

    @property
    def describe(self) -> str:
        if not self.enabled:
            return "not configured"
        return f"{self.model} at {_origin(self.base_url)}"


@dataclass(frozen=True)
class AIAnswer:
    text: str
    model: str
    passage_ids: tuple[str, ...]


def _origin(url: str) -> str:
    clean = url.strip()
    if clean and "://" not in clean:
        clean = f"http://{clean}"
    parts = urllib.parse.urlsplit(clean)
    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"
    return "the configured endpoint"


def _load_dotenv(path: Path | None = None) -> None:
    """Fill missing environment variables from a local .env file, if present."""

    env_path = path or (Path(__file__).resolve().parent.parent / ".env")
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue
        name, _, value = entry.partition("=")
        name = name.strip()
        if name and name not in os.environ:
            os.environ[name] = value.strip().strip("\"'")


def _parse_timeout(raw: str | None) -> float:
    try:
        value = float(raw) if raw else DEFAULT_TIMEOUT
    except ValueError:
        return DEFAULT_TIMEOUT
    return min(max(value, MIN_TIMEOUT), MAX_TIMEOUT)


def settings_from_env(env: dict[str, str] | None = None) -> AISettings:
    if env is None:
        _load_dotenv()
        env = dict(os.environ)
    raw_url = (env.get(ENV_BASE_URL) or DEFAULT_BASE_URL).strip()
    if raw_url and "://" not in raw_url:
        raw_url = f"http://{raw_url}"
    return AISettings(
        base_url=raw_url or DEFAULT_BASE_URL,
        model=(env.get(ENV_MODEL) or "").strip(),
        timeout=_parse_timeout(env.get(ENV_TIMEOUT)),
    )


def build_messages(question: str, passages: Sequence[RetrievedPassage]) -> list[dict[str, str]]:
    blocks = []
    for number, passage in enumerate(passages, start=1):
        blocks.append(
            f"[S{number}] {passage.title} - {passage.section} ({passage.jurisdiction})\n"
            f"Source: {passage.source_url}\n"
            f"Quoted text: {passage.text}\n"
            f"Plain summary: {passage.plain_summary}\n"
            f"Applicability: {passage.applicability_note}"
        )
    user_message = (
        f"Question: {question.strip()[:MAX_QUESTION_CHARS]}\n\n"
        "Verified passages:\n\n" + "\n\n".join(blocks)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


def _post_json(
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout: float,
) -> dict:
    """POST JSON with the standard library. Tests replace this function."""

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    return json.loads(body)


def _check_grounding(answer: str, passages: Sequence[RetrievedPassage]) -> None:
    """Reject answers that cite a source or section not present in the passages."""

    for label in _LABEL_RE.findall(answer):
        if not 1 <= int(label) <= len(passages):
            raise AIError(
                "The AI answer cited a source that was not retrieved, so it was discarded."
            )
    corpus = " ".join(f"{passage.section} {passage.text}" for passage in passages).lower()
    for number in _SECTION_RE.findall(answer):
        if number.lower() not in corpus:
            raise AIError(
                "The AI answer mentioned a legal section that is not in the retrieved "
                "passages, so it was discarded."
            )


def _http_error_message(exc: urllib.error.HTTPError, settings: AISettings) -> str:
    detail = ""
    try:
        detail = exc.read().decode("utf-8", errors="replace").lower()
    except Exception:
        detail = ""
    if exc.code == 404 and "model" in detail:
        return (
            f"Ollama does not have the model tag '{settings.model}'. "
            "Check `ollama list` and update HAQ_OLLAMA_MODEL."
        )
    if exc.code == 404:
        return "Ollama did not recognise the request path. Check the Ollama version."
    if exc.code in (400, 422):
        return "Ollama rejected the request. Check the configured model tag."
    return f"Ollama returned an error (HTTP {exc.code})."


def answer_question(
    question: str,
    passages: Sequence[RetrievedPassage],
    *,
    settings: AISettings | None = None,
    transport: Callable[[str, dict, dict[str, str], float], dict] | None = None,
) -> AIAnswer:
    """Generate an explanation limited to the supplied passages."""

    active_settings = settings if settings is not None else settings_from_env()
    if not active_settings.enabled:
        raise AIConfigError(active_settings.problem or "Local AI mode is not configured.")
    if not passages:
        raise AIError("No verified passage was retrieved, so no AI request was made.")
    if not (question or "").strip():
        raise AIError("Enter a question before requesting an AI answer.")

    url = active_settings.base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": active_settings.model,
        "messages": build_messages(question, passages),
        "stream": False,
        "options": {"temperature": 0, "num_predict": 700},
    }
    headers = {"Content-Type": "application/json"}
    sender = transport or _post_json
    try:
        data = sender(url, payload, headers, active_settings.timeout)
    except urllib.error.HTTPError as exc:
        raise AIError(_http_error_message(exc, active_settings)) from None
    except TimeoutError:
        raise AIError(
            "The local model did not respond in time. Try again or use local search only."
        ) from None
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            raise AIError(
                "The local model did not respond in time. Try again or use local search only."
            ) from None
        raise AIError(
            "Ollama could not be reached at "
            f"{_origin(active_settings.base_url)}. Local search still works."
        ) from None
    except AIError:
        raise
    except Exception:
        raise AIError("The Ollama response could not be read.") from None

    try:
        content = data["message"]["content"]
    except (KeyError, TypeError):
        raise AIError("Ollama returned an unexpected response.") from None
    if not isinstance(content, str) or not content.strip():
        raise AIError("Ollama returned an empty answer.")
    answer = content.strip()
    if len(answer) > MAX_ANSWER_CHARS:
        raise AIError("Ollama returned an answer that was too long to use.")
    _check_grounding(answer, passages)
    return AIAnswer(
        text=answer,
        model=active_settings.model,
        passage_ids=tuple(passage.id for passage in passages),
    )
