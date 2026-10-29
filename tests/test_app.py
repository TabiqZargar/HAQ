import re

from app import (
    CSS,
    FOOTER_HTML,
    SITE_HEADER_HTML,
    _handle_notice_upload,
    demo,
    render_guide,
    render_legal_aid,
    render_notice,
    render_privacy,
)
from haq.guide import build_guide
from haq.notice import extract_notice_facts


def _textbox_config(label: str) -> dict:
    for component in demo.config["components"]:
        props = component["props"]
        if component["type"] == "textbox" and props.get("label") == label:
            return props
    raise AssertionError(f"Textbox with label {label!r} not found")


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
