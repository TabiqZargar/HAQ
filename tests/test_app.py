import re

from app import (
    CSS,
    FOOTER_HTML,
    SITE_HEADER_HTML,
    demo,
    render_legal_aid,
    render_privacy,
)


def _textbox_config(label: str) -> dict:
    for component in demo.config["components"]:
        props = component["props"]
        if component["type"] == "textbox" and props.get("label") == label:
            return props
    raise AssertionError(f"Textbox with label {label!r} not found")


def _rendered_html() -> str:
    return "\n".join(
        str(component["props"].get("value", ""))
        for component in demo.config["components"]
        if component["type"] == "html"
    )


def test_question_and_notice_textboxes_are_explicitly_interactive() -> None:
    assert _textbox_config("Your question")["interactive"] is True
    assert _textbox_config("Notice text")["interactive"] is True


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
