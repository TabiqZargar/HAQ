from app import demo


def _textbox_config(label: str) -> dict:
    for component in demo.config["components"]:
        props = component["props"]
        if component["type"] == "textbox" and props.get("label") == label:
            return props
    raise AssertionError(f"Textbox with label {label!r} not found")


def test_question_and_notice_textboxes_are_explicitly_interactive() -> None:
    assert _textbox_config("Your question")["interactive"] is True
    assert _textbox_config("Notice text")["interactive"] is True
