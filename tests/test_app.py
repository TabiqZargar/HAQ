import re
import urllib.error

import pytest

from app import (
    CSS,
    FOOTER_HTML,
    SITE_HEADER_HTML,
    _handle_guide,
    _handle_notice,
    _handle_notice_upload,
    demo,
    render_ai_status,
    render_guide,
    render_legal_aid,
    render_notice,
    render_privacy,
)
from haq.ai import AISettings
from haq.guide import build_guide
from haq.notice import extract_notice_facts

AI_SETTINGS = AISettings(
    base_url="http://localhost:11434",
    model="test-model",
    timeout=10.0,
)


def _ai_transport(content: str, calls: list | None = None):
    def send(url, payload, headers, timeout):
        if calls is not None:
            calls.append(url)
        return {"model": "test-model", "message": {"role": "assistant", "content": content}}

    return send


def _textbox_config(label: str) -> dict:
    for component in demo.config["components"]:
        props = component["props"]
        if component["type"] == "textbox" and props.get("label") == label:
            return props
    raise AssertionError(f"Textbox with label {label!r} not found")


def _checkbox_config(label: str) -> dict:
    for component in demo.config["components"]:
        props = component["props"]
        if component["type"] == "checkbox" and props.get("label") == label:
            return props
    raise AssertionError(f"Checkbox with label {label!r} not found")


def _file_config(label: str) -> dict:
    for component in demo.config["components"]:
        props = component["props"]
        if component["type"] == "file" and props.get("label") == label:
            return props
    raise AssertionError(f"File component with label {label!r} not found")


def _rendered_html() -> str:
    return "\n".join(
        str(component["props"].get("value", ""))
        for component in demo.config["components"]
        if component["type"] == "html"
    )


def test_question_and_notice_textboxes_are_explicitly_interactive() -> None:
    assert _textbox_config("Your question")["interactive"] is True
    assert _textbox_config("Notice text")["interactive"] is True


def test_notice_file_upload_accepts_supported_local_formats() -> None:
    props = _file_config("Or upload a notice (.pdf, .docx, or .txt)")
    assert props["file_types"] == [".pdf", ".docx", ".txt"]
    assert props["file_count"] == "single"
    assert props["interactive"] is True
    assert any(
        dependency.get("api_name") == "_handle_notice_upload"
        for dependency in demo.config["dependencies"]
    )


def test_notice_upload_handler_previews_text_and_mentions_local_reading(tmp_path) -> None:
    path = tmp_path / "notice.txt"
    path.write_text(
        "You must vacate on or before 30/11/2026. Payment of Rs. 10,000 is due within 15 days.",
        encoding="utf-8",
    )

    preview, status = _handle_notice_upload(str(path))

    assert "30/11/2026" in preview
    assert "Loaded plain text" in status
    assert "external service" in status


def test_notice_upload_handler_reports_unsupported_files_gracefully(tmp_path) -> None:
    path = tmp_path / "notice.rtf"
    path.write_text("{\\rtf1 notice}", encoding="utf-8")

    _, status = _handle_notice_upload(str(path))

    assert "Unsupported file type" in status
    assert "haq-warning" in status


def test_navigation_targets_real_sections() -> None:
    component_ids = {
        component["props"].get("elem_id") for component in demo.config["components"]
    }
    rendered_html = _rendered_html()
    hrefs = set(re.findall(r'href="(#[^"]+)"', SITE_HEADER_HTML + FOOTER_HTML))
    assert hrefs
    for href in hrefs:
        target = href[1:]
        assert target in component_ids or f'id="{target}"' in rendered_html


def test_redesign_uses_local_css_only() -> None:
    assert "fonts.googleapis.com" not in CSS
    assert "cdn.tailwindcss.com" not in CSS
    assert "https://" not in CSS


def test_ui_does_not_advertise_unimplemented_tools() -> None:
    rendered_html = _rendered_html()
    for label in (
        "Clause Flagger",
        "Limitation Clock",
        "Scan Notice (OCR)",
        "Download 1-Page",
        "हिन्दी",
    ):
        assert label not in rendered_html


def test_privacy_and_legal_aid_information_remain_visible() -> None:
    privacy = " ".join(render_privacy().split())
    legal_aid = " ".join(render_legal_aid().split())
    assert "does not use analytics" in privacy
    assert "External AI" in privacy
    assert "15100" in legal_aid
    assert "does not decide eligibility" in legal_aid
    assert "https://nalsa.gov.in/faqs" in legal_aid


def test_guide_output_renders_the_verified_passage_that_ranked_first() -> None:
    rendered = render_guide(build_guide("landlord gave me 15 days notice to leave"))
    assert "Verified source response" in rendered
    assert "Section 106" in rendered
    assert "No verified match" not in rendered


def test_notice_output_renders_explicit_deadline_language_and_amounts() -> None:
    notice_text = (
        "You must vacate the premises on or before 30/11/2026. "
        "Payment of Rs. 10,000 is due within 15 days."
    )
    rendered = render_notice(extract_notice_facts(notice_text), notice_text)
    assert "Explicit deadline language" in rendered
    assert "on or before 30/11/2026" in rendered
    assert "within 15 days" in rendered
    assert "Rs. 10,000" in rendered


def test_ai_consent_checkbox_is_off_by_default() -> None:
    props = _checkbox_config("Ask the local Ollama model for an explanation")
    assert props["value"] is False
    assert any(
        dependency.get("api_name") == "_handle_guide" and len(dependency["inputs"]) == 3
        for dependency in demo.config["dependencies"]
    )


def test_local_mode_does_not_call_the_ai_model(monkeypatch) -> None:
    def fail(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("AI model must not be called without consent")

    monkeypatch.setattr("app.answer_question", fail)
    rendered = _handle_guide("security deposit", "All topics", False)

    assert "Verified source response" in rendered
    assert "local search" in rendered


def test_unsupported_question_never_calls_the_ai_model() -> None:
    calls: list[str] = []
    rendered = _handle_guide(
        "how do I renew my passport",
        "All topics",
        True,
        settings=AI_SETTINGS,
        transport=_ai_transport("[S1] invented", calls),
    )

    assert "No verified match" in rendered
    assert calls == []


def test_ai_answer_is_rendered_with_its_sources() -> None:
    rendered = _handle_guide(
        "security deposit",
        "All topics",
        True,
        settings=AI_SETTINGS,
        transport=_ai_transport("The deposit is discussed in [S1]."),
    )

    assert "The deposit is discussed in [S1]." in rendered
    assert "AI explanation" in rendered
    assert "AI answer + sources" in rendered
    assert "Verified source response" in rendered


def test_unconfigured_ai_falls_back_to_local_results() -> None:
    rendered = _handle_guide(
        "security deposit",
        "All topics",
        True,
        settings=AISettings(),
        transport=_ai_transport("[S1] unused"),
    )

    assert "AI mode is not configured" in rendered
    assert "Verified source response" in rendered


def test_ai_http_error_falls_back_to_local_results() -> None:
    def send(*args, **kwargs):
        raise urllib.error.HTTPError("http://localhost:11434/api/chat", 500, "error", None, None)

    rendered = _handle_guide(
        "security deposit", "All topics", True, settings=AI_SETTINGS, transport=send
    )

    assert "AI answer unavailable" in rendered
    assert "Showing local retrieval only" in rendered
    assert "Verified source response" in rendered


def test_ai_unreachable_falls_back_to_local_results() -> None:
    def send(*args, **kwargs):
        raise urllib.error.URLError(ConnectionRefusedError("connection refused"))

    rendered = _handle_guide(
        "security deposit", "All topics", True, settings=AI_SETTINGS, transport=send
    )

    assert "AI answer unavailable" in rendered
    assert "could not be reached" in rendered
    assert "Verified source response" in rendered


def test_ai_timeout_falls_back_to_local_results() -> None:
    def send(*args, **kwargs):
        raise TimeoutError("timed out")

    rendered = _handle_guide(
        "security deposit", "All topics", True, settings=AI_SETTINGS, transport=send
    )

    assert "AI answer unavailable" in rendered
    assert "did not respond in time" in rendered
    assert "Verified source response" in rendered


def test_ai_malformed_response_falls_back_to_local_results() -> None:
    def send(*args, **kwargs):
        return {"unexpected": "payload"}

    rendered = _handle_guide(
        "security deposit", "All topics", True, settings=AI_SETTINGS, transport=send
    )

    assert "AI answer unavailable" in rendered
    assert "Showing local retrieval only" in rendered
    assert "Verified source response" in rendered


def test_notice_decoder_does_not_call_the_ai_model(monkeypatch) -> None:
    def fail(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("notice decoding must never call an AI model")

    monkeypatch.setattr("app.answer_question", fail)
    rendered = _handle_notice("You must vacate on or before 30/11/2026.")

    assert "30/11/2026" in rendered


def test_render_ai_status_reflects_configuration() -> None:
    unconfigured = render_ai_status(AISettings())
    assert "Local AI mode is not configured" in unconfigured

    configured = render_ai_status(
        AISettings(base_url="http://localhost:11434", model="gemma4:e2b")
    )
    assert "Local AI mode is configured" in configured
    assert "gemma4:e2b" in configured
