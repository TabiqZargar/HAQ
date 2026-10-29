"""Haq Guide - a local-first, source-backed legal information app."""

from __future__ import annotations

import html
import os
from collections import OrderedDict

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("GRADIO_SERVER_NAME", "127.0.0.1")

import gradio as gr

from haq.guide import CATEGORY_LABELS, GuideResult, build_guide, get_retriever
from haq.notice import NoticeFacts, extract_notice_facts

APP_TITLE = "Haq Guide"
TOPIC_LABELS = ("All topics", "Tenancy", "Consumer", "Unpaid wages")
TOPIC_TO_CATEGORY = {
    "All topics": "All",
    "Tenancy": "tenancy",
    "Consumer": "consumer",
    "Unpaid wages": "labour",
}

CSS = """
:root {
  --haq-ink: #10233f;
  --haq-ink-soft: #42536b;
  --haq-paper: #f7f2e8;
  --haq-card: #fffaf0;
  --haq-line: #ddcfb7;
  --haq-saffron: #c8781a;
  --haq-saffron-soft: #f3dfbf;
  --haq-green: #2f6b4f;
  --haq-red: #9d3d2f;
}

body, .gradio-container {
  background:
    radial-gradient(circle at 12% 0%, rgba(200, 120, 26, 0.09), transparent 32rem),
    var(--haq-paper) !important;
  color: var(--haq-ink) !important;
}

.gradio-container {
  max-width: 1180px !important;
  margin: 0 auto !important;
  font-family: Inter, "Segoe UI", system-ui, -apple-system, sans-serif !important;
}

.haq-hero {
  padding: 30px 4px 14px;
}

.haq-eyebrow {
  color: var(--haq-saffron);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.haq-hero h1 {
  color: var(--haq-ink);
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: clamp(2rem, 4.5vw, 3.35rem);
  line-height: 1.06;
  margin: 10px 0 12px;
  max-width: 970px;
}

.haq-lede {
  color: var(--haq-ink-soft);
  font-size: 1.04rem;
  line-height: 1.6;
  margin: 0;
  max-width: 760px;
}

.haq-privacy {
  align-items: center;
  background: #edf3ec;
  border: 1px solid #c9ddcb;
  border-radius: 999px;
  color: #28513c;
  display: inline-flex;
  font-size: 0.82rem;
  font-weight: 700;
  gap: 8px;
  margin-top: 16px;
  padding: 7px 12px;
}

.haq-dot {
  background: var(--haq-green);
  border-radius: 999px;
  display: inline-block;
  height: 8px;
  width: 8px;
}

.haq-disclaimer {
  background: #fff8e8;
  border: 1px solid var(--haq-saffron-soft);
  border-left: 5px solid var(--haq-saffron);
  border-radius: 12px;
  color: #4a3a26;
  font-size: 0.92rem;
  line-height: 1.55;
  margin: 10px 0 22px;
  padding: 14px 18px;
}

.haq-shell {
  align-items: flex-start;
  gap: 24px;
}

.haq-nav {
  background: rgba(255, 250, 240, 0.72);
  border: 1px solid var(--haq-line);
  border-radius: 16px;
  padding: 16px 12px;
  position: sticky;
  top: 16px;
}

.haq-nav-title {
  color: var(--haq-ink-soft);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  margin: 2px 8px 10px;
  text-transform: uppercase;
}

.haq-nav a {
  border-radius: 9px;
  color: var(--haq-ink) !important;
  display: block;
  font-size: 0.92rem;
  font-weight: 650;
  padding: 9px 10px;
  text-decoration: none !important;
}

.haq-nav a:hover {
  background: var(--haq-saffron-soft);
  color: #6b3d08 !important;
}

.haq-section-card {
  background: var(--haq-card);
  border: 1px solid var(--haq-line);
  border-radius: 18px;
  box-shadow: 0 12px 30px rgba(16, 35, 63, 0.045);
  margin-bottom: 22px;
  padding: 24px !important;
  scroll-margin-top: 18px;
}

.haq-section-head {
  border-bottom: 1px solid #eadfca;
  margin-bottom: 16px;
  padding-bottom: 13px;
}

.haq-kicker {
  color: var(--haq-saffron);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.haq-section-head h2 {
  color: var(--haq-ink);
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: 1.55rem;
  margin: 4px 0 5px;
}

.haq-section-head p {
  color: var(--haq-ink-soft);
  font-size: 0.92rem;
  line-height: 1.55;
  margin: 0;
}

.haq-output {
  margin-top: 12px;
}

.haq-response-note {
  background: #f2f6f2;
  border: 1px solid #cfe0d2;
  border-radius: 10px;
  color: #315443;
  font-size: 0.9rem;
  line-height: 1.5;
  margin: 8px 0 14px;
  padding: 10px 13px;
}

.haq-source-card {
  background: #ffffff;
  border: 1px solid #e5dac7;
  border-radius: 14px;
  margin: 12px 0;
  overflow: hidden;
  padding: 17px 18px;
}

.haq-source-top {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 8px;
}

.haq-badge {
  background: #edf3ec;
  border: 1px solid #c9ddcb;
  border-radius: 999px;
  color: #28513c;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  padding: 4px 8px;
  text-transform: uppercase;
}

.haq-badge.model {
  background: #fff2d9;
  border-color: #efd5a6;
  color: #7c4b08;
}

.haq-badge.release {
  background: #eef2f8;
  border-color: #cfd9e6;
  color: #29476b;
}

.haq-cat {
  color: var(--haq-ink-soft);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.haq-source-card h3 {
  color: var(--haq-ink);
  font-size: 1.02rem;
  line-height: 1.35;
  margin: 0 0 3px;
}

.haq-section-name {
  color: var(--haq-saffron);
  font-size: 0.8rem;
  font-weight: 700;
  margin: 0 0 11px;
}

.haq-quote {
  background: #fbf7ef;
  border-left: 4px solid #d7b27b;
  border-radius: 0 8px 8px 0;
  color: #2d3c50;
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: 0.94rem;
  line-height: 1.62;
  margin: 0 0 12px;
  padding: 11px 14px;
}

.haq-plain {
  background: #f8faf7;
  border-radius: 9px;
  padding: 11px 13px;
}

.haq-plain strong {
  color: #315443;
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  margin-bottom: 4px;
  text-transform: uppercase;
}

.haq-plain p {
  color: #34443a;
  font-size: 0.89rem;
  line-height: 1.55;
  margin: 0;
}

.haq-note {
  color: #5f6b7a;
  font-size: 0.8rem;
  line-height: 1.5;
  margin: 10px 0 0;
}

.haq-source-meta {
  border-top: 1px solid #efe6d7;
  color: #687385;
  font-size: 0.75rem;
  line-height: 1.5;
  margin-top: 12px;
  padding-top: 9px;
}

.haq-source-meta a, .haq-legal a, .haq-sources a {
  color: #8a4c08 !important;
  font-weight: 700;
}

.haq-empty {
  background: #fbf7ef;
  border: 1px dashed #d8c8aa;
  border-radius: 12px;
  color: #5b6572;
  line-height: 1.55;
  padding: 16px;
}

.haq-warning {
  background: #fff1ed;
  border: 1px solid #efc9bf;
  border-radius: 10px;
  color: #7a3024;
  font-size: 0.88rem;
  line-height: 1.5;
  margin: 8px 0 14px;
  padding: 10px 13px;
}

.haq-facts {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.haq-fact {
  background: #fff;
  border: 1px solid #e5dac7;
  border-radius: 12px;
  padding: 13px 14px;
}

.haq-fact h3 {
  color: var(--haq-ink);
  font-size: 0.82rem;
  letter-spacing: 0.05em;
  margin: 0 0 7px;
  text-transform: uppercase;
}

.haq-fact ul {
  color: #33445a;
  font-size: 0.88rem;
  line-height: 1.5;
  margin: 0;
  padding-left: 18px;
}

.haq-fact li + li {
  margin-top: 4px;
}

.haq-legal {
  background: linear-gradient(135deg, #10233f, #18385c);
  border-radius: 16px;
  color: #f9f4e9;
  padding: 22px 24px;
}

.haq-legal h2 {
  color: #ffffff;
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: 1.5rem;
  margin: 0 0 8px;
}

.haq-legal p, .haq-legal li {
  color: #dfe7f1;
  font-size: 0.91rem;
  line-height: 1.6;
}

.haq-legal a {
  color: #ffd18c !important;
}

.haq-helpline {
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 209, 140, 0.38);
  border-radius: 12px;
  display: inline-block;
  font-size: 1.05rem;
  font-weight: 800;
  margin: 8px 0 12px;
  padding: 10px 14px;
}

.haq-sources {
  color: #4a5667;
  font-size: 0.87rem;
  line-height: 1.6;
}

.haq-sources ul {
  margin: 8px 0 0;
  padding-left: 20px;
}

.haq-sources li {
  margin-bottom: 6px;
}

.haq-footer {
  color: #687385;
  font-size: 0.78rem;
  line-height: 1.55;
  padding: 14px 4px 32px;
  text-align: center;
}

.haq-section-card .block, .haq-section-card .form {
  border: none !important;
  box-shadow: none !important;
}

.haq-section-card input, .haq-section-card textarea {
  background: #fffdf8 !important;
}

#haq-ask-button, #haq-notice-button {
  background: var(--haq-ink) !important;
  border: 1px solid var(--haq-ink) !important;
  color: #fffaf0 !important;
  font-weight: 750 !important;
}

#haq-ask-button:hover, #haq-notice-button:hover {
  background: #1d3b63 !important;
}

@media (max-width: 760px) {
  .haq-shell {
    flex-direction: column;
  }
  .haq-nav {
    position: static;
    width: 100%;
  }
  .haq-nav a {
    display: inline-block;
  }
  .haq-hero {
    padding-top: 20px;
  }
  .haq-section-card {
    padding: 18px !important;
  }
}
"""


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _section_head(kicker: str, title: str, description: str) -> str:
    return (
        '<div class="haq-section-head">'
        f'<div class="haq-kicker">{_escape(kicker)}</div>'
        f"<h2>{_escape(title)}</h2>"
        f"<p>{_escape(description)}</p>"
        "</div>"
    )


def _badge_for(passage) -> str:
    if passage.source_type == "model_law":
        return '<span class="haq-badge model">Model law</span>'
    if passage.source_type == "government_release":
        return '<span class="haq-badge release">Government release</span>'
    return '<span class="haq-badge">Verified official</span>'


def _render_source_card(passage) -> str:
    category = CATEGORY_LABELS.get(passage.category, passage.category.title())
    return f"""
    <article class="haq-source-card">
      <div class="haq-source-top">
        {_badge_for(passage)}
        <span class="haq-cat">{_escape(category)}</span>
      </div>
      <h3>{_escape(passage.title)}</h3>
      <p class="haq-section-name">{_escape(passage.section)}</p>
      <blockquote class="haq-quote">{_escape(passage.text)}</blockquote>
      <div class="haq-plain">
        <strong>Plain-language summary of this passage</strong>
        <p>{_escape(passage.plain_summary)}</p>
      </div>
      <p class="haq-note"><strong>Applicability:</strong> {_escape(passage.applicability_note)}</p>
      <div class="haq-source-meta">
        Jurisdiction: {_escape(passage.jurisdiction)}<br>
        Collected: {_escape(passage.collection_date)} ·
        <a href="{_escape(passage.source_url)}" target="_blank" rel="noopener noreferrer">Open official source</a>
      </div>
    </article>
    """


def render_guide(result: GuideResult) -> str:
    if result.abstained:
        return f"""
        <div class="haq-output">
          <div class="haq-warning">{_escape(result.message)}</div>
          <div class="haq-empty">
            The guide only answers when it can quote a passage from its small verified library.
            It does not use an external AI model, invent a section, or calculate a deadline.
          </div>
        </div>
        """

    cards = "".join(_render_source_card(passage) for passage in result.passages)
    return f"""
    <div class="haq-output">
      <div class="haq-response-note">{_escape(result.message)}</div>
      {cards}
    </div>
    """


def render_notice(facts: NoticeFacts, original: str) -> str:
    if not (original or "").strip():
        return (
            '<div class="haq-empty">Paste the notice text above. '
            "The decoder will show only explicit dates, amounts, parties, reference numbers, "
            "and deadline language it can see in the text.</div>"
        )

    if not facts.has_facts:
        return """
        <div class="haq-warning">
          No explicit dates, amounts, labelled parties, reference numbers, or deadline phrases
          were found. This tool does not infer a date or deadline.
        </div>
        """

    def fact_block(title: str, values: tuple[str, ...]) -> str:
        if not values:
            return ""
        items = "".join(f"<li>{_escape(value)}</li>" for value in values)
        return f'<div class="haq-fact"><h3>{_escape(title)}</h3><ul>{items}</ul></div>'

    blocks = "".join(
        (
            fact_block("Dates written", facts.dates),
            fact_block("Amounts written", facts.amounts),
            fact_block("Labelled parties", facts.parties),
            fact_block("Reference numbers", facts.reference_numbers),
            fact_block("Explicit deadline language", facts.deadline_language),
        )
    )
    return f"""
    <div class="haq-warning">
      These are exact text matches only. No deadline has been calculated, converted, or inferred.
      Check the original notice and confirm any date with a qualified person.
    </div>
    <div class="haq-facts">{blocks}</div>
    """


def render_empty_guide() -> str:
    return """
    <div class="haq-empty">
      Try a specific question, such as: “My landlord has not returned my security deposit.”
      Choose a topic to narrow the search, or leave it on “All topics”.
    </div>
    """


def render_legal_aid() -> str:
    return """
    <div class="haq-legal">
      <div class="haq-kicker">Free legal help</div>
      <h2>If the problem is urgent or you cannot afford a lawyer</h2>
      <p>NALSA's official FAQ states that people can contact its toll-free helpline for urgent legal assistance.</p>
      <div class="haq-helpline">NALSA helpline: 15100</div>
      <p>
        <a href="https://nalsa.gov.in/faqs" target="_blank" rel="noopener noreferrer">Read the NALSA FAQ</a>
        ·
        <a href="https://nalsa.gov.in/services/legal-aid/eligibility" target="_blank" rel="noopener noreferrer">Check legal-aid eligibility</a>
      </p>
      <p>
        Eligibility can depend on the category of applicant and, for income-based eligibility,
        on the limits prescribed for the relevant State or Union Territory. This app does not
        decide eligibility.
      </p>
    </div>
    """


def render_sources() -> str:
    retriever = get_retriever()
    unique: OrderedDict[tuple[str, str], list[str]] = OrderedDict()
    for entry in retriever.entries:
        unique.setdefault((entry.title, entry.source_url), []).append(entry.section)

    items = []
    for (title, url), sections in unique.items():
        items.append(
            f'<li><a href="{_escape(url)}" target="_blank" rel="noopener noreferrer">'
            f"{_escape(title)}</a> — {len(sections)} passage(s)</li>"
        )
    return f"""
    <div class="haq-sources">
      <p>
        The starter library contains <strong>{len(retriever.entries)}</strong> checked passages
        from <strong>{len(unique)}</strong> official documents. Only passages marked
        <code>verified_official</code> are searchable.
      </p>
      <ul>{''.join(items)}</ul>
      <p>
        The Model Tenancy Act, 2021 is a model law; it is not automatically applicable in every
        State or Union Territory. The Code on Wages, 2019 has been in force since 21 November 2025.
      </p>
    </div>
    """


def _handle_guide(query: str, topic_label: str) -> str:
    category = TOPIC_TO_CATEGORY.get(topic_label, "All")
    return render_guide(build_guide(query, category=category))


def _handle_notice(text: str) -> str:
    return render_notice(extract_notice_facts(text), text)


HEADER_HTML = """
<div class="haq-hero">
  <div class="haq-eyebrow">Local-first legal information · India</div>
  <h1>Haq Guide — Know your rights. Understand your options.</h1>
  <p class="haq-lede">
    A small, source-backed guide for tenancy, consumer, and unpaid-wage questions.
    It quotes verified law-library passages and says when it cannot find an answer.
  </p>
  <div class="haq-privacy"><span class="haq-dot"></span>Runs on this device · No analytics · No external AI</div>
</div>
<div class="haq-disclaimer">
  <strong>Important:</strong> Haq Guide provides general legal information, not legal advice or a
  legal opinion. Laws, rules, and State amendments change. A quoted passage may not fit your facts.
  For advice about your situation, contact a qualified lawyer or your District Legal Services Authority.
</div>
"""

NAV_HTML = """
<nav class="haq-nav" aria-label="Sections">
  <div class="haq-nav-title">On this page</div>
  <a href="#ask">Ask a question</a>
  <a href="#notice">Decode a notice</a>
  <a href="#legal-aid">Free legal help</a>
  <a href="#sources">Sources</a>
</nav>
"""

FOOTER_HTML = """
<div class="haq-footer">
  Haq Guide is a hackathon prototype. It does not call an external AI API, use analytics, or
  send your text to an external server. Source links open only when you click them.
</div>
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title=APP_TITLE,
        analytics_enabled=False,
    ) as demo:
        gr.HTML(HEADER_HTML)

        with gr.Row(elem_classes=["haq-shell"], elem_id="haq-shell"):
            with gr.Column(scale=1, min_width=170, elem_id="haq-nav-col"):
                gr.HTML(NAV_HTML)

            with gr.Column(scale=5, elem_id="haq-content"):
                with gr.Column(elem_id="ask", elem_classes=["haq-section-card"]):
                    gr.HTML(
                        _section_head(
                            "01 · Ask",
                            "Start with the problem",
                            "Describe what happened. The guide searches only the verified starter library.",
                        )
                    )
                    query = gr.Textbox(
                        label="Your question",
                        placeholder="Example: My landlord is keeping my security deposit without giving a reason.",
                        lines=3,
                        interactive=True,
                    )
                    topic = gr.Radio(
                        choices=list(TOPIC_LABELS),
                        value="All topics",
                        label="Topic",
                        info="Choose one topic, or search all three.",
                    )
                    ask_button = gr.Button(
                        "Find verified guidance",
                        variant="primary",
                        elem_id="haq-ask-button",
                    )
                    guide_output = gr.HTML(value=render_empty_guide(), elem_id="haq-guide-output")

                with gr.Column(elem_id="notice", elem_classes=["haq-section-card"]):
                    gr.HTML(
                        _section_head(
                            "02 · Notice",
                            "Decode a notice",
                            "Paste a notice to pull out only what it explicitly says. No dates are calculated.",
                        )
                    )
                    notice_input = gr.Textbox(
                        label="Notice text",
                        placeholder="Paste the full notice here, including dates, amounts, and reference numbers.",
                        lines=8,
                        interactive=True,
                    )
                    notice_button = gr.Button(
                        "Extract explicit facts",
                        variant="primary",
                        elem_id="haq-notice-button",
                    )
                    notice_output = gr.HTML(
                        value="<div class='haq-empty'>Paste a notice above to see explicit facts.</div>",
                        elem_id="haq-notice-output",
                    )

                with gr.Column(elem_id="legal-aid", elem_classes=["haq-section-card"]):
                    gr.HTML(render_legal_aid())

                with gr.Column(elem_id="sources", elem_classes=["haq-section-card"]):
                    gr.HTML(
                        _section_head(
                            "03 · Sources",
                            "What this guide can quote",
                            "A deliberately small library. If a question falls outside it, the guide abstains.",
                        )
                    )
                    gr.HTML(render_sources())

        gr.HTML(FOOTER_HTML)

        ask_button.click(
            _handle_guide,
            inputs=[query, topic],
            outputs=[guide_output],
        )
        query.submit(
            _handle_guide,
            inputs=[query, topic],
            outputs=[guide_output],
        )
        notice_button.click(
            _handle_notice,
            inputs=[notice_input],
            outputs=[notice_output],
        )

    return demo


demo = build_app()


if __name__ == "__main__":
    demo.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.environ.get("HAQ_PORT", "7860")),
        share=False,
        show_error=False,
        footer_links=[],
        theme=gr.themes.Base(),
        css=CSS,
    )
