import urllib.error

import pytest

from haq.ai import (
    SYSTEM_PROMPT,
    AIConfigError,
    AIError,
    AISettings,
    answer_question,
    build_messages,
    settings_from_env,
)
from haq.retrieve import Retriever

SETTINGS = AISettings(
    base_url="http://localhost:11434",
    model="gemma-test:latest",
    timeout=10.0,
)


@pytest.fixture(scope="module")
def passages():
    result = Retriever().search("security deposit")
    assert result
    return result[:1]


def _transport_returning(content: str):
    calls: list[dict] = []

    def send(url, payload, headers, timeout):
        calls.append({"url": url, "payload": payload, "headers": headers, "timeout": timeout})
        return {"model": "gemma-test:latest", "message": {"role": "assistant", "content": content}}

    return send, calls


def _http_error(code: int, body: bytes = b"{}") -> urllib.error.HTTPError:
    import io

    return urllib.error.HTTPError(
        "http://localhost:11434/api/chat", code, "error", hdrs=None, fp=io.BytesIO(body)
    )


def test_disabled_mode_raises_config_error_without_a_request() -> None:
    def send(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("transport must not be called when AI is disabled")

    with pytest.raises(AIConfigError) as excinfo:
        answer_question("security deposit", (), settings=AISettings(), transport=send)
    assert "HAQ_OLLAMA_MODEL" in str(excinfo.value)


def test_missing_model_tag_is_reported() -> None:
    settings = AISettings(base_url="http://localhost:11434", model="")
    assert settings.enabled is False
    assert settings.missing == ("HAQ_OLLAMA_MODEL",)
    assert "ollama list" in settings.problem


def test_non_loopback_endpoint_is_refused() -> None:
    settings = AISettings(base_url="https://api.example.com/v1", model="gemma-test:latest")
    assert settings.enabled is False
    assert "loopback" in settings.problem


def test_loopback_endpoint_without_scheme_is_accepted() -> None:
    settings = AISettings(base_url="localhost:11434", model="gemma-test:latest")
    assert settings.enabled is True
    assert settings.local_endpoint is True


def test_successful_answer_uses_the_local_ollama_chat_api(passages) -> None:
    send, calls = _transport_returning("The security deposit is discussed in [S1].")
    answer = answer_question(
        "is my deposit refundable", passages, settings=SETTINGS, transport=send
    )

    assert answer.text == "The security deposit is discussed in [S1]."
    assert answer.model == "gemma-test:latest"
    assert answer.passage_ids == (passages[0].id,)

    call = calls[0]
    assert call["url"] == "http://localhost:11434/api/chat"
    assert call["payload"]["model"] == "gemma-test:latest"
    assert call["payload"]["stream"] is False
    assert call["payload"]["options"]["temperature"] == 0
    assert "Authorization" not in call["headers"]
    user_message = call["payload"]["messages"][1]["content"]
    assert "is my deposit refundable" in user_message
    assert passages[0].text in user_message
    assert passages[0].source_url in user_message
    assert passages[0].title in user_message


def test_prompt_instructs_conservative_answering_and_safe_abstention(passages) -> None:
    messages = build_messages("a question", passages)
    assert messages[0]["role"] == "system"
    prompt = messages[0]["content"]
    assert "Use ONLY the numbered passages" in prompt
    assert "Do not add any statute, section number, case, deadline, amount" in prompt
    assert "verified library does not cover it" in prompt
    assert "official source or qualified legal professional" in prompt
    assert "[S1]" in messages[1]["content"]


def test_safe_abstention_response_is_accepted_as_grounded(passages) -> None:
    abstention_text = (
        "The verified library does not cover this question. Please verify with an "
        "appropriate official source or qualified legal professional. This is general "
        "information, not legal advice."
    )
    send, _ = _transport_returning(abstention_text)
    answer = answer_question(
        "how do I file an injunction", passages, settings=SETTINGS, transport=send
    )
    assert answer.text == abstention_text
    assert answer.passage_ids == (passages[0].id,)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_http_error(404, b'{"error":"model \\"gemma-test:latest\\" not found"}'), "does not have"),
        (_http_error(500), "HTTP 500"),
        (_http_error(400), "rejected the request"),
    ],
)
def test_ollama_http_errors_are_reported_safely(passages, error, expected) -> None:
    def send(*args, **kwargs):
        raise error

    with pytest.raises(AIError) as excinfo:
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)
    assert expected in str(excinfo.value)


def test_unreachable_ollama_is_reported_safely(passages) -> None:
    def send(*args, **kwargs):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    with pytest.raises(AIError, match="could not be reached"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)


def test_timeout_is_reported_safely(passages) -> None:
    def send(*args, **kwargs):
        raise TimeoutError

    with pytest.raises(AIError, match="did not respond in time"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)


def test_urlerror_timeout_is_reported_safely(passages) -> None:
    def send(*args, **kwargs):
        raise urllib.error.URLError(TimeoutError("timed out"))

    with pytest.raises(AIError, match="did not respond in time"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)


def test_invalid_responses_are_rejected(passages) -> None:
    send, _ = _transport_returning("")
    with pytest.raises(AIError, match="empty answer"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)

    def malformed(*args, **kwargs):
        return {"done": True}

    with pytest.raises(AIError, match="unexpected response"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=malformed)

    def unreadable(*args, **kwargs):
        raise ValueError("not json")

    with pytest.raises(AIError, match="could not be read"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=unreadable)


def test_answer_citing_an_unretrieved_source_is_rejected(passages) -> None:
    send, _ = _transport_returning("This is stated in [S4].")
    with pytest.raises(AIError, match="source that was not retrieved"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)


def test_answer_inventing_a_section_is_rejected(passages) -> None:
    send, _ = _transport_returning("Under Section 999 of the Act, you must pay.")
    with pytest.raises(AIError, match="section that is not in the retrieved passages"):
        answer_question("security deposit", passages, settings=SETTINGS, transport=send)


def test_no_passages_means_no_request() -> None:
    def send(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("transport must not be called without passages")

    with pytest.raises(AIError, match="No verified passage"):
        answer_question("security deposit", [], settings=SETTINGS, transport=send)


def test_empty_question_means_no_request(passages) -> None:
    def send(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("transport must not be called with an empty question")

    with pytest.raises(AIError, match="Enter a question"):
        answer_question("   ", passages, settings=SETTINGS, transport=send)


def test_settings_from_env_uses_local_defaults_and_clamps_timeout() -> None:
    configured = settings_from_env(
        {"HAQ_OLLAMA_MODEL": "gemma-test:latest", "HAQ_OLLAMA_TIMEOUT": "9999"}
    )
    assert configured.base_url == "http://localhost:11434"
    assert configured.enabled is True
    assert configured.timeout == 300.0

    defaults = settings_from_env({"HAQ_OLLAMA_TIMEOUT": "not-a-number"})
    assert defaults.enabled is False
    assert defaults.base_url == "http://localhost:11434"
    assert defaults.timeout == 120.0
