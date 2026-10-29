"""Haq Guide - a local-first, source-backed legal information app."""

from __future__ import annotations

import html
import os
from collections import OrderedDict

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("GRADIO_SERVER_NAME", "127.0.0.1")

import gradio as gr

from haq.ai import (
    AIAnswer,
    AIConfigError,
    AIError,
    AISettings,
    ENV_MODEL,
    answer_question,
    settings_from_env,
)
from haq.documents import DocumentError, SUPPORTED_EXTENSIONS, read_notice_document
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

NOTICE_UPLOAD_HELP = (
    "Upload a PDF, DOCX, or TXT file to load its text into the box below. "
    "Files are read on this computer and are not sent to an external service. "
    "Scanned PDFs are not OCR'd; if no text can be extracted, paste the text instead."
)

CSS = """
:root {
  --haq-surface: #fff8f3;
  --haq-surface-low: #faf2eb;
  --haq-surface-container: #f4ede6;
  --haq-surface-high: #eee7e0;
  --haq-surface-highest: #e9e1db;
  --haq-paper: #fffdf9;
  --haq-primary: #333b2a;
  --haq-primary-container: #4a5240;
  --haq-ink: #23281d;
  --haq-tertiary: #582e0e;
  --haq-ochre: #a6532b;
  --haq-ochre-light: #fbece3;
  --haq-outline: #767870;
  --haq-line: #c6c7be;
  --haq-line-soft: #ddd6cc;
  --haq-on-surface: #1e1b17;
  --haq-muted: #5d6057;
  --haq-green: #2f6b4f;
  --haq-red: #9d3d2f;
  --haq-serif: "Iowan Old Style", "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  --haq-sans: "Public Sans", Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  overflow-x: hidden;
}

body, .gradio-container {
  background: var(--haq-surface) !important;
  color: var(--haq-on-surface) !important;
}

.gradio-container {
  font-family: var(--haq-sans) !important;
  margin: 0 auto !important;
  max-width: 1280px !important;
  padding: 0 24px !important;
}

.gradio-container .prose {
  max-width: none !important;
}

.gradio-container main {
  background: transparent !important;
}

.gradio-container .main {
  max-width: 1280px !important;
  padding: 80px 0 0 !important;
}

#haq-site-header-html {
  margin: 0 !important;
  min-height: 0 !important;
  padding: 0 !important;
}

#haq-site-header-html .html-container,
#haq-site-header-html .block {
  height: 0 !important;
  margin: 0 !important;
  min-height: 0 !important;
  overflow: visible !important;
  padding: 0 !important;
}

#haq-site-header-html .prose {
  height: 0 !important;
  overflow: visible !important;
}

.haq-site-header {
  backdrop-filter: blur(14px);
  background: rgba(255, 248, 243, 0.97);
  border-bottom: 1px solid var(--haq-line);
  left: 0;
  position: fixed;
  right: 0;
  top: 0;
  width: 100%;
  z-index: 60;
}

.haq-header-inner {
  align-items: center;
  box-sizing: border-box;
  display: flex;
  gap: 24px;
  height: 78px;
  justify-content: space-between;
  margin: 0 auto;
  max-width: 1280px;
  padding: 0 24px;
}

.haq-brand {
  color: inherit !important;
  display: inline-flex;
  flex-direction: column;
  text-decoration: none !important;
}

.haq-brand-lockup {
  align-items: baseline;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  line-height: 1;
}

.haq-brand-en {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: 1.7rem;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.haq-brand-rule {
  color: var(--haq-line);
  font-size: 1.2rem;
  font-weight: 300;
}

.haq-brand-script {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: 1.18rem;
  font-weight: 600;
}

.haq-brand-mark {
  background: var(--haq-ochre-light);
  border: 1px solid rgba(166, 83, 43, 0.24);
  border-radius: 3px;
  color: var(--haq-ochre);
  font-size: 0.6rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  padding: 3px 6px;
  text-transform: uppercase;
}

.haq-brand-sub {
  color: var(--haq-muted);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  margin-top: 5px;
  text-transform: uppercase;
}

.haq-top-nav {
  align-items: stretch;
  display: flex;
  gap: 2px;
  height: 78px;
}

.haq-top-nav a {
  align-items: center;
  border-bottom: 2px solid transparent;
  color: var(--haq-muted) !important;
  display: flex;
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.12em;
  padding: 0 10px;
  text-decoration: none !important;
  text-transform: uppercase;
  transition: color 160ms ease, border-color 160ms ease;
}

.haq-top-nav a:first-child {
  border-bottom-color: var(--haq-primary);
  color: var(--haq-primary) !important;
}

.haq-top-nav a:hover {
  border-bottom-color: var(--haq-ochre);
  color: var(--haq-primary) !important;
}

.haq-header-help {
  align-items: baseline;
  background: var(--haq-ochre-light);
  border: 1px solid rgba(166, 83, 43, 0.38);
  border-radius: 6px;
  color: var(--haq-ochre) !important;
  display: inline-flex;
  flex-shrink: 0;
  gap: 5px;
  padding: 7px 11px;
  text-decoration: none !important;
  transition: background 160ms ease, color 160ms ease;
}

.haq-header-help:hover {
  background: var(--haq-ochre);
  color: #ffffff !important;
}

.haq-header-help-label,
.haq-header-help-note {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.haq-header-help strong {
  font-size: 0.95rem;
  letter-spacing: 0.03em;
}

.haq-hero-section {
  border-bottom: 1px solid var(--haq-line);
  gap: 0 !important;
  padding: 30px 0 48px !important;
  scroll-margin-top: 96px;
}

.haq-registry {
  align-items: center;
  border-bottom: 1px dashed var(--haq-line);
  color: var(--haq-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.71rem;
  gap: 10px 18px;
  justify-content: space-between;
  padding-bottom: 13px;
}

.haq-registry-left,
.haq-registry-right {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.haq-registry-left strong {
  color: var(--haq-primary);
  letter-spacing: 0.09em;
  text-transform: uppercase;
}

.haq-registry-dot {
  background: var(--haq-primary);
  border-radius: 999px;
  display: inline-block;
  height: 8px;
  width: 8px;
}

.haq-registry-sep {
  color: var(--haq-line);
}

.haq-registry-right {
  color: var(--haq-primary);
  font-weight: 650;
}

.haq-hero-copy {
  align-items: center;
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin: 30px auto 24px;
  max-width: 980px;
  text-align: center;
}

.haq-seal {
  align-items: center;
  background: var(--haq-surface-high);
  border: 1px solid var(--haq-outline);
  border-radius: 999px;
  box-shadow: 0 1px 2px rgba(35, 40, 29, 0.08);
  color: var(--haq-primary);
  display: inline-flex;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.13em;
  padding: 6px 12px;
  text-transform: uppercase;
}

.haq-hero-copy h1 {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: clamp(2.15rem, 4.8vw, 3.55rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.08;
  margin: 0;
  text-wrap: balance;
}

.haq-hero-copy h1 span {
  color: var(--haq-tertiary);
  display: block;
  font-style: italic;
  font-weight: 400;
  margin-top: 7px;
}

.haq-hero-copy > p {
  color: var(--haq-muted);
  font-size: 1.01rem;
  line-height: 1.65;
  margin: 0;
  max-width: 760px;
  text-wrap: balance;
}

.haq-disclaimer {
  background: var(--haq-ochre-light);
  border: 1px solid rgba(166, 83, 43, 0.26);
  border-left: 4px solid var(--haq-ochre);
  border-radius: 8px;
  color: #503727;
  font-size: 0.82rem;
  line-height: 1.55;
  margin-top: 6px;
  max-width: 820px;
  padding: 12px 15px;
  text-align: left;
}

.haq-intake-card {
  align-items: stretch !important;
  background: var(--haq-paper) !important;
  border: 2px solid var(--haq-primary) !important;
  border-radius: 14px !important;
  box-shadow: 0 18px 42px rgba(35, 40, 29, 0.11);
  flex-wrap: nowrap !important;
  gap: 0 !important;
  margin: 0 auto !important;
  max-width: 980px !important;
  padding: 10px !important;
  transition: box-shadow 160ms ease, border-color 160ms ease;
}

.haq-intake-card:focus-within {
  border-color: var(--haq-primary) !important;
  box-shadow: 0 0 0 4px rgba(51, 59, 42, 0.14), 0 18px 42px rgba(35, 40, 29, 0.13);
}

.haq-intake-main {
  border: 0 !important;
  min-width: 0 !important;
  padding: 6px 12px 6px 10px !important;
}

.haq-intake-side {
  border-left: 1px solid var(--haq-line-soft);
  gap: 9px !important;
  min-width: 230px !important;
  padding: 8px 8px 8px 18px !important;
}

.haq-intake-card .block,
.haq-intake-card .form {
  border: 0 !important;
  box-shadow: none !important;
}

#haq-question,
#haq-question .block,
#haq-question .form {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}

#haq-question label,
#haq-notice-input label {
  color: var(--haq-muted) !important;
  font-size: 0.68rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
}

#haq-question textarea,
#haq-notice-input textarea {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  color: var(--haq-on-surface) !important;
  font-family: var(--haq-sans) !important;
  font-size: 1rem !important;
  line-height: 1.55 !important;
  padding: 8px 2px !important;
}

#haq-question textarea {
  min-height: 82px;
}

#haq-question textarea:focus,
#haq-notice-input textarea:focus {
  box-shadow: none !important;
  outline: none !important;
}

#haq-question textarea::placeholder,
#haq-notice-input textarea::placeholder {
  color: #8c887f !important;
}

#haq-topic,
#haq-topic .block,
#haq-topic .form {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}

#haq-topic fieldset {
  border: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

#haq-topic .wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

#haq-topic label {
  background: var(--haq-surface-container-low) !important;
  border: 1px solid var(--haq-line) !important;
  border-radius: 999px !important;
  color: var(--haq-primary) !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  line-height: 1.2 !important;
  padding: 5px 9px !important;
}

#haq-topic label:has(input:checked) {
  background: var(--haq-primary) !important;
  border-color: var(--haq-primary) !important;
  color: #ffffff !important;
}

#haq-topic input {
  accent-color: var(--haq-primary);
  margin-right: 4px;
}

#haq-ask-button,
#haq-notice-button {
  background: var(--haq-primary) !important;
  border: 1px solid var(--haq-primary) !important;
  border-radius: 8px !important;
  color: #ffffff !important;
  font-family: var(--haq-sans) !important;
  font-size: 0.75rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.08em !important;
  min-height: 43px !important;
  text-transform: uppercase !important;
  transition: background 160ms ease, transform 120ms ease;
}

#haq-ask-button:hover,
#haq-notice-button:hover {
  background: var(--haq-ink) !important;
  border-color: var(--haq-ink) !important;
}

#haq-ask-button:active,
#haq-notice-button:active {
  transform: scale(0.99);
}

#haq-ask-button:focus-visible,
#haq-notice-button:focus-visible {
  box-shadow: 0 0 0 4px rgba(51, 59, 42, 0.2) !important;
  outline: 2px solid var(--haq-primary) !important;
  outline-offset: 2px !important;
}

.haq-process {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 18px auto 0;
  max-width: 980px;
}

.haq-process-item {
  align-items: flex-start;
  background: rgba(250, 242, 235, 0.7);
  border: 1px solid var(--haq-line-soft);
  border-radius: 9px;
  display: flex;
  gap: 8px;
  padding: 9px 10px;
}

.haq-process-num {
  align-items: center;
  background: var(--haq-surface-highest);
  border-radius: 999px;
  color: var(--haq-primary);
  display: inline-flex;
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 800;
  height: 20px;
  justify-content: center;
  width: 20px;
}

.haq-process-item p {
  margin: 0;
}

.haq-process-item strong {
  color: var(--haq-primary);
  display: block;
  font-size: 0.72rem;
  letter-spacing: 0.03em;
  line-height: 1.3;
}

.haq-process-item span {
  color: var(--haq-muted);
  display: block;
  font-size: 0.7rem;
  line-height: 1.45;
  margin-top: 2px;
}

#haq-guide-output {
  margin: 18px auto 0;
  max-width: 980px;
}

#haq-notice-output {
  margin-top: 14px;
}

.haq-result-card {
  background: var(--haq-paper);
  border: 1px solid var(--haq-line);
  border-radius: 12px;
  box-shadow: 0 8px 22px rgba(35, 40, 29, 0.05);
  overflow: hidden;
}

.haq-result-head {
  align-items: center;
  background: var(--haq-surface-container);
  border-bottom: 1px solid var(--haq-line);
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
  justify-content: space-between;
  padding: 9px 13px;
}

.haq-result-head strong {
  color: var(--haq-primary);
  font-size: 0.68rem;
  font-weight: 850;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.haq-result-head span {
  color: var(--haq-muted);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 0.66rem;
}

.haq-result-body {
  padding: 14px;
}

.haq-output {
  margin: 0;
}

.haq-response-note {
  background: #eef3ed;
  border: 1px solid #c9ddcb;
  border-radius: 8px;
  color: #315443;
  font-size: 0.84rem;
  line-height: 1.55;
  margin: 0 0 13px;
  padding: 10px 12px;
}

.haq-source-card {
  background: #ffffff;
  border: 1px solid var(--haq-line-soft);
  border-left: 4px solid var(--haq-ochre);
  border-radius: 9px;
  margin: 12px 0;
  overflow: hidden;
  padding: 17px 18px;
}

.haq-source-card:last-child {
  margin-bottom: 0;
}

.haq-source-top {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-bottom: 9px;
}

.haq-badge {
  background: #edf3ec;
  border: 1px solid #c9ddcb;
  border-radius: 4px;
  color: #28513c;
  font-size: 0.63rem;
  font-weight: 850;
  letter-spacing: 0.06em;
  padding: 3px 7px;
  text-transform: uppercase;
}

.haq-badge.model {
  background: var(--haq-ochre-light);
  border-color: rgba(166, 83, 43, 0.3);
  color: #7c4b08;
}

.haq-badge.release {
  background: #eef2f8;
  border-color: #cfd9e6;
  color: #29476b;
}

.haq-cat {
  color: var(--haq-muted);
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.haq-source-card h3 {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: 1.08rem;
  line-height: 1.35;
  margin: 0 0 3px;
}

.haq-section-name {
  color: var(--haq-ochre);
  font-size: 0.75rem;
  font-weight: 750;
  margin: 0 0 12px;
}

.haq-quote {
  background: var(--haq-surface-low);
  border-left: 3px solid var(--haq-ochre);
  border-radius: 0 6px 6px 0;
  color: #2d3c50;
  font-family: var(--haq-serif);
  font-size: 0.95rem;
  line-height: 1.62;
  margin: 0 0 12px;
  padding: 11px 14px;
}

.haq-plain {
  background: #f4f7f2;
  border-radius: 7px;
  padding: 11px 12px;
}

.haq-plain strong {
  color: #315443;
  display: block;
  font-size: 0.66rem;
  font-weight: 850;
  letter-spacing: 0.07em;
  margin-bottom: 4px;
  text-transform: uppercase;
}

.haq-plain p {
  color: #34443a;
  font-size: 0.86rem;
  line-height: 1.55;
  margin: 0;
}

.haq-note {
  color: var(--haq-muted);
  font-size: 0.76rem;
  line-height: 1.5;
  margin: 10px 0 0;
}

.haq-source-meta {
  border-top: 1px solid var(--haq-line-soft);
  color: var(--haq-muted);
  font-size: 0.71rem;
  line-height: 1.55;
  margin-top: 12px;
  padding-top: 9px;
}

.haq-source-meta a,
.haq-legal a,
.haq-sources a,
.haq-legal-links a {
  color: var(--haq-ochre) !important;
  font-weight: 750;
}

.haq-empty {
  background: var(--haq-surface-low);
  border: 1px dashed var(--haq-line);
  border-radius: 9px;
  color: var(--haq-muted);
  font-size: 0.88rem;
  line-height: 1.6;
  padding: 15px;
}

.haq-warning {
  background: #fff0eb;
  border: 1px solid #efc9bf;
  border-radius: 7px;
  color: #7a3024;
  font-size: 0.84rem;
  line-height: 1.55;
  margin: 0 0 12px;
  padding: 10px 12px;
}

.haq-warning:last-child {
  margin-bottom: 0;
}

.haq-facts {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
}

.haq-fact {
  background: #ffffff;
  border: 1px solid var(--haq-line-soft);
  border-radius: 8px;
  padding: 12px 13px;
}

.haq-fact h3 {
  color: var(--haq-primary);
  font-size: 0.72rem;
  font-weight: 850;
  letter-spacing: 0.06em;
  margin: 0 0 7px;
  text-transform: uppercase;
}

.haq-fact ul {
  color: #33445a;
  font-size: 0.86rem;
  line-height: 1.5;
  margin: 0;
  padding-left: 18px;
}

.haq-fact li + li {
  margin-top: 4px;
}

.haq-band {
  border-bottom: 1px solid var(--haq-line);
  padding: 44px 0;
}

.haq-band-head {
  align-items: flex-end;
  display: flex;
  flex-wrap: wrap;
  gap: 14px 28px;
  justify-content: space-between;
  margin-bottom: 22px;
}

.haq-band-head h2,
.haq-section-head h2 {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: clamp(1.55rem, 2.8vw, 2.1rem);
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 3px 0 0;
}

.haq-band-head > p {
  color: var(--haq-muted);
  font-size: 0.84rem;
  line-height: 1.55;
  margin: 0;
  max-width: 440px;
}

.haq-eyebrow,
.haq-kicker {
  color: var(--haq-ochre);
  font-size: 0.67rem;
  font-weight: 850;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.haq-tool-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.haq-tool-card {
  background: var(--haq-paper);
  border: 2px solid var(--haq-line);
  border-radius: 10px;
  color: inherit !important;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 230px;
  padding: 18px;
  text-decoration: none !important;
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.haq-tool-card:hover {
  border-color: var(--haq-primary);
  box-shadow: 0 12px 26px rgba(35, 40, 29, 0.08);
  transform: translateY(-2px);
}

.haq-tool-index {
  color: var(--haq-ochre);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.06em;
}

.haq-tool-card h3 {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: 1.18rem;
  line-height: 1.2;
  margin: 10px 0 2px;
}

.haq-tool-deco {
  color: var(--haq-tertiary);
  font-family: var(--haq-serif);
  font-size: 0.78rem;
  margin: 0 0 10px;
}

.haq-tool-card > p {
  color: var(--haq-muted);
  font-size: 0.79rem;
  line-height: 1.55;
  margin: 0;
}

.haq-tool-link {
  border-top: 1px solid var(--haq-line-soft);
  color: var(--haq-primary);
  display: flex;
  font-size: 0.68rem;
  font-weight: 850;
  justify-content: space-between;
  letter-spacing: 0.08em;
  margin-top: 16px;
  padding-top: 11px;
  text-transform: uppercase;
}

.haq-honesty {
  background: var(--haq-surface-low);
  border: 1px solid var(--haq-line);
  border-radius: 12px;
  padding: 24px;
}

.haq-honesty-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.haq-honesty-card {
  background: var(--haq-paper);
  border: 1px solid var(--haq-line);
  border-radius: 9px;
  padding: 16px;
}

.haq-honesty-card span {
  color: var(--haq-ochre);
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 0.68rem;
  font-weight: 750;
}

.haq-honesty-card h3 {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: 1.02rem;
  margin: 7px 0 6px;
}

.haq-honesty-card p {
  color: var(--haq-muted);
  font-size: 0.8rem;
  line-height: 1.55;
  margin: 0;
}

.haq-honesty-note {
  border-top: 1px dashed var(--haq-line);
  color: var(--haq-muted);
  font-size: 0.76rem;
  line-height: 1.55;
  margin: 18px 0 0;
  padding-top: 13px;
}

.haq-privacy {
  align-items: center;
  background: var(--haq-surface-high);
  border: 1px solid var(--haq-line);
  border-radius: 12px;
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.8fr);
  margin: 44px 0;
  padding: 24px;
}

.haq-privacy h2 {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: clamp(1.35rem, 2.4vw, 1.75rem);
  margin: 5px 0 8px;
}

.haq-privacy p {
  color: var(--haq-muted);
  font-size: 0.84rem;
  line-height: 1.6;
  margin: 0;
  max-width: 680px;
}

.haq-privacy-stats {
  display: grid;
  gap: 8px;
}

.haq-privacy-stats div {
  align-items: center;
  background: var(--haq-paper);
  border: 1px solid var(--haq-line);
  border-radius: 7px;
  display: flex;
  gap: 12px;
  justify-content: space-between;
  padding: 9px 11px;
}

.haq-privacy-stats span {
  color: var(--haq-muted);
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.haq-privacy-stats strong {
  color: var(--haq-primary);
  font-size: 0.78rem;
}

.haq-section {
  border-bottom: 1px solid var(--haq-line);
  gap: 0 !important;
  padding: 44px 0 !important;
  scroll-margin-top: 96px;
}

.haq-section-head {
  border-bottom: 1px solid var(--haq-line-soft);
  margin-bottom: 18px;
  padding-bottom: 13px;
}

.haq-section-head p {
  color: var(--haq-muted);
  font-size: 0.86rem;
  line-height: 1.55;
  margin: 5px 0 0;
  max-width: 760px;
}

#haq-notice-input {
  background: var(--haq-surface-low) !important;
  border: 1px solid var(--haq-line) !important;
  border-radius: 9px !important;
  padding: 10px 12px !important;
}

#haq-notice-input:focus-within {
  border-color: var(--haq-primary) !important;
  box-shadow: 0 0 0 3px rgba(51, 59, 42, 0.12);
}

#haq-notice-button {
  margin-top: 10px;
  max-width: 280px;
}

.haq-legal-section {
  border-bottom: 1px solid var(--haq-line);
}

.haq-legal {
  background: var(--haq-primary-container);
  border-radius: 14px;
  box-shadow: 0 20px 44px rgba(35, 40, 29, 0.16);
  color: #ffffff;
  display: grid;
  gap: 26px;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
  overflow: hidden;
  padding: 30px;
  position: relative;
}

.haq-legal::after {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  bottom: -120px;
  box-shadow: 0 0 0 34px rgba(255, 255, 255, 0.035), 0 0 0 68px rgba(255, 255, 255, 0.02);
  content: "";
  height: 280px;
  pointer-events: none;
  position: absolute;
  right: -90px;
  width: 280px;
}

.haq-legal-copy,
.haq-legal-card {
  position: relative;
  z-index: 1;
}

.haq-legal-kicker {
  color: #ffd9c0;
  font-size: 0.67rem;
  font-weight: 850;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.haq-legal h2 {
  color: #ffffff;
  font-family: var(--haq-serif);
  font-size: clamp(1.6rem, 3vw, 2.15rem);
  letter-spacing: -0.02em;
  line-height: 1.15;
  margin: 9px 0 11px;
}

.haq-legal p {
  color: #e4eadf;
  font-size: 0.84rem;
  line-height: 1.65;
  margin: 0 0 9px;
  max-width: 680px;
}

.haq-legal-points {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-top: 15px;
}

.haq-legal-points span {
  color: #f5c9aa;
  font-size: 0.72rem;
  font-weight: 700;
}

.haq-legal-points span::before {
  content: "✓ ";
}

.haq-legal-card {
  align-self: center;
  background: var(--haq-paper);
  border: 1px solid var(--haq-line);
  border-radius: 10px;
  color: var(--haq-on-surface);
  padding: 18px;
}

.haq-legal-card-head {
  align-items: center;
  border-bottom: 1px solid var(--haq-line-soft);
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 9px;
}

.haq-legal-card-head span:first-child {
  color: var(--haq-tertiary);
  font-size: 0.67rem;
  font-weight: 850;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.haq-legal-card-head span:last-child {
  background: #e8f1e8;
  border-radius: 3px;
  color: var(--haq-green);
  font-size: 0.61rem;
  font-weight: 850;
  padding: 3px 6px;
  text-transform: uppercase;
}

.haq-helpline {
  color: var(--haq-primary) !important;
  display: inline-block;
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
  font-size: 2.35rem;
  font-weight: 850;
  letter-spacing: -0.04em;
  line-height: 1;
  margin: 2px 0 8px;
  text-decoration: none !important;
}

.haq-helpline:hover {
  text-decoration: underline !important;
}

.haq-legal-card p {
  color: var(--haq-muted);
  font-size: 0.72rem;
  line-height: 1.5;
  margin: 0 0 12px;
}

.haq-legal-links {
  display: grid;
  gap: 7px;
}

.haq-legal-links a {
  background: var(--haq-surface-low);
  border: 1px solid var(--haq-line);
  border-radius: 6px;
  color: var(--haq-primary) !important;
  font-size: 0.73rem;
  font-weight: 800;
  padding: 8px 10px;
  text-align: center;
  text-decoration: none !important;
}

.haq-legal-links a:hover {
  background: var(--haq-ochre-light);
  border-color: rgba(166, 83, 43, 0.34);
  color: var(--haq-ochre) !important;
}

.haq-sources {
  color: var(--haq-muted);
  font-size: 0.86rem;
  line-height: 1.65;
}

.haq-source-summary {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 16px;
}

.haq-source-stat {
  background: var(--haq-surface-low);
  border: 1px solid var(--haq-line);
  border-radius: 8px;
  padding: 11px 13px;
}

.haq-source-stat strong {
  color: var(--haq-primary);
  display: block;
  font-family: var(--haq-serif);
  font-size: 1.35rem;
  line-height: 1;
}

.haq-source-stat span {
  color: var(--haq-muted);
  display: block;
  font-size: 0.64rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin-top: 5px;
  text-transform: uppercase;
}

.haq-sources > p {
  margin: 0 0 10px;
}

.haq-sources ul {
  margin: 10px 0 14px;
  padding-left: 20px;
}

.haq-sources li {
  margin-bottom: 6px;
}

.haq-sources code {
  background: var(--haq-surface-container);
  border-radius: 3px;
  color: var(--haq-primary);
  padding: 1px 4px;
}

.haq-source-note {
  border-top: 1px dashed var(--haq-line);
  color: var(--haq-muted);
  font-size: 0.78rem;
  margin-top: 14px !important;
  padding-top: 12px;
}

.haq-site-footer {
  background: var(--haq-surface-low);
  border-top: 1px solid var(--haq-line);
  margin-left: calc(50% - 50vw);
  margin-right: calc(50% - 50vw);
  padding: 30px 0 34px;
  width: 100vw;
}

.haq-footer-inner {
  box-sizing: border-box;
  margin: 0 auto;
  max-width: 1280px;
  padding: 0 24px;
}

.haq-footer-main {
  align-items: flex-start;
  border-bottom: 1px solid var(--haq-line);
  display: flex;
  flex-wrap: wrap;
  gap: 18px 28px;
  justify-content: space-between;
  padding-bottom: 18px;
}

.haq-footer-mark {
  color: var(--haq-primary);
  font-family: var(--haq-serif);
  font-size: 1.05rem;
  font-weight: 700;
}

.haq-footer-main p {
  color: var(--haq-muted);
  font-size: 0.76rem;
  line-height: 1.6;
  margin: 5px 0 0;
  max-width: 720px;
}

.haq-footer-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.haq-footer-badges span {
  background: var(--haq-paper);
  border: 1px solid var(--haq-line);
  border-radius: 5px;
  color: var(--haq-primary);
  font-size: 0.66rem;
  font-weight: 750;
  padding: 6px 9px;
}

.haq-footer-bottom {
  align-items: center;
  color: var(--haq-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.68rem;
  gap: 12px 24px;
  justify-content: space-between;
  padding-top: 16px;
}

.haq-footer-bottom nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 15px;
}

.haq-footer-bottom a {
  color: var(--haq-muted) !important;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-decoration: none !important;
  text-transform: uppercase;
}

.haq-footer-bottom a:hover {
  color: var(--haq-primary) !important;
}

.haq-footer-bottom > span {
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
}

@media (max-width: 1050px) {
  .haq-top-nav {
    display: none;
  }
}

@media (max-width: 900px) {
  .gradio-container .main {
    padding-top: 72px !important;
  }

  .haq-header-inner {
    height: 70px;
  }

  .haq-brand-sub {
    display: none;
  }

  .haq-hero-section {
    scroll-margin-top: 84px;
  }

  .haq-section {
    scroll-margin-top: 84px;
  }

  .haq-tool-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .haq-honesty-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .gradio-container {
    padding: 0 16px !important;
  }

  .haq-header-inner {
    gap: 12px;
    padding: 0 16px;
  }

  .haq-brand-mark,
  .haq-header-help-label,
  .haq-header-help-note {
    display: none;
  }

  .haq-hero-section {
    padding-top: 22px !important;
  }

  .haq-registry {
    align-items: flex-start;
    flex-direction: column;
  }

  .haq-hero-copy {
    margin-top: 24px;
  }

  .haq-hero-copy h1 {
    font-size: clamp(1.95rem, 8vw, 2.65rem);
  }

  .haq-hero-copy > p {
    font-size: 0.94rem;
  }

  .haq-intake-card {
    flex-direction: column !important;
  }

  .haq-intake-main {
    padding: 6px 6px 2px !important;
  }

  .haq-intake-side {
    border-left: 0;
    border-top: 1px solid var(--haq-line-soft);
    min-width: 0 !important;
    padding: 12px 6px 6px !important;
  }

  .haq-process {
    grid-template-columns: 1fr;
  }

  .haq-band {
    padding: 34px 0;
  }

  .haq-band-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .haq-tool-card {
    min-height: 210px;
  }

  .haq-honesty {
    padding: 18px;
  }

  .haq-honesty-grid,
  .haq-source-summary {
    grid-template-columns: 1fr;
  }

  .haq-privacy {
    grid-template-columns: 1fr;
    margin: 34px 0;
    padding: 18px;
  }

  .haq-section {
    padding: 34px 0 !important;
  }

  .haq-legal {
    grid-template-columns: 1fr;
    padding: 22px;
  }

  .haq-footer-inner {
    padding: 0 16px;
  }
}

@media (max-width: 560px) {
  .haq-brand-en {
    font-size: 1.48rem;
  }

  .haq-brand-script {
    font-size: 1rem;
  }

  .haq-top-nav {
    display: none;
  }

  .haq-header-help {
    padding: 6px 8px;
  }

  .haq-tool-grid {
    grid-template-columns: 1fr;
  }

  .haq-tool-card {
    min-height: 0;
  }

  .haq-footer-bottom {
    align-items: flex-start;
    flex-direction: column;
  }
}
"""

SITE_HEADER_HTML = """
<header class="haq-site-header">
  <div class="haq-header-inner">
    <a class="haq-brand" href="#ask" aria-label="Haq Guide home">
      <span class="haq-brand-lockup">
        <span class="haq-brand-en">Haq</span>
        <span class="haq-brand-rule" aria-hidden="true">|</span>
        <span class="haq-brand-script" lang="ur" dir="rtl">حق</span>
        <span class="haq-brand-rule" aria-hidden="true">|</span>
        <span class="haq-brand-script" lang="hi">हक़</span>
        <span class="haq-brand-mark">सार्वजनिक</span>
      </span>
      <span class="haq-brand-sub">Civic legal information · Made simple</span>
    </a>
    <nav class="haq-top-nav" aria-label="Primary">
      <a href="#ask">Ask</a>
      <a href="#notice">Notice decoder</a>
      <a href="#legal-aid">Free legal help</a>
      <a href="#sources">Sources</a>
    </nav>
    <a class="haq-header-help" href="tel:15100" aria-label="Call the NALSA legal-aid helpline on 15100">
      <span class="haq-header-help-label">NALSA</span>
      <strong>15100</strong>
      <span class="haq-header-help-note">free</span>
    </a>
  </div>
</header>
"""

HERO_INTRO_HTML = """
<div class="haq-registry">
  <div class="haq-registry-left">
    <span class="haq-registry-dot" aria-hidden="true"></span>
    <span><strong>Haq Guide</strong></span>
    <span class="haq-registry-sep" aria-hidden="true">·</span>
    <span>Public-interest legal information</span>
    <span class="haq-registry-sep" aria-hidden="true">·</span>
    <span>No login needed</span>
  </div>
  <div class="haq-registry-right">Local-first · No analytics · AI runs locally</div>
</div>
<div class="haq-hero-copy">
  <div class="haq-seal">Verified-source library · India</div>
  <h1>
    Tell us what happened in one sentence.
    <span>We show you the verified law that may apply.</span>
  </h1>
  <p>
    No lawyer jargon. Search a small, hand-checked library for tenancy, consumer,
    and unpaid-wage questions. If no verified passage fits, the guide says so.
  </p>
  <div class="haq-disclaimer">
    <strong>Important:</strong> Haq Guide provides general legal information, not legal advice
    or a legal opinion. Laws, rules, and State amendments change. A quoted passage may not fit
    your facts. For advice about your situation, contact a qualified lawyer or your District
    Legal Services Authority.
  </div>
</div>
"""

FOOTER_HTML = """
<footer class="haq-site-footer">
  <div class="haq-footer-inner">
    <div class="haq-footer-main">
      <div>
        <div class="haq-footer-mark">हक़ सबका अधिकार · Haq Guide</div>
        <p>
          General legal information, not legal advice or a legal opinion. Sourced from the
          verified law-library passages listed on this page. The app does not calculate
          deadlines, infer missing dates, or decide legal-aid eligibility.
        </p>
      </div>
      <div class="haq-footer-badges" aria-label="Application qualities">
        <span>Verified library</span>
        <span>Local-first</span>
        <span>AI runs locally</span>
      </div>
    </div>
    <div class="haq-footer-bottom">
      <nav aria-label="Footer">
        <a href="#ask">Ask</a>
        <a href="#notice">Notice decoder</a>
        <a href="#privacy">Privacy</a>
        <a href="#legal-aid">Free legal help</a>
        <a href="#sources">Sources</a>
      </nav>
      <span>Hackathon prototype · English starter library</span>
    </div>
  </div>
</footer>
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


def _result_shell(title: str, meta: str, body: str, *, empty: bool = False) -> str:
    empty_class = " haq-result-empty" if empty else ""
    return f"""
    <div class="haq-output">
      <div class="haq-result-card{empty_class}">
        <div class="haq-result-head">
          <strong>{_escape(title)}</strong>
          <span>{_escape(meta)}</span>
        </div>
        <div class="haq-result-body">{body}</div>
      </div>
    </div>
    """


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


def render_guide(result: GuideResult, *, ai_answer: AIAnswer | None = None, ai_status: str | None = None) -> str:
    if result.abstained:
        body = f"""
          <div class="haq-warning">{_escape(result.message)}</div>
          <div class="haq-empty">
            The guide only answers when it can quote a passage from its small verified library.
            It never asks an AI model to invent a rule, an authority, or a deadline.
          </div>
        """
        return _result_shell("No verified match", "Local search · no guess", body)

    cards = "".join(_render_source_card(passage) for passage in result.passages)
    count_label = "source passage" if len(result.passages) == 1 else "source passages"
    ai_block = ""
    if ai_answer is not None:
        paragraphs = "".join(
            f"<p>{_escape(chunk)}</p>" for chunk in ai_answer.text.split("\n\n") if chunk.strip()
        )
        ai_block = f"""
      <div class="haq-response-note">
        <strong>AI explanation, grounded in the passages below.</strong>
        Generated by the local Ollama model ({_escape(ai_answer.model)}) from the retrieved passages
        only. It is general information, not legal advice; check the cited sources.
      </div>
      <div class="haq-result-body">{paragraphs}</div>
      """
    status_block = ""
    if ai_status:
        status_block = f'<div class="haq-warning">{_escape(ai_status)}</div>'
    body = f"""
      {status_block}
      <div class="haq-response-note">{_escape(result.message)}</div>
      {ai_block}
      {cards}
    """
    meta = (
        f"{len(result.passages)} {count_label} · AI answer + sources"
        if ai_answer is not None
        else f"{len(result.passages)} {count_label} · local search"
    )
    return _result_shell("Verified source response", meta, body)


def render_ai_status(settings: AISettings | None = None) -> str:
    active = settings if settings is not None else settings_from_env()
    if active.enabled:
        return (
            '<div class="haq-empty">'
            f"Local AI mode is configured ({_escape(active.describe)}) and stays off until you "
            "tick the box. Ticking it sends your question and the retrieved passages to the "
            "Ollama model running on this computer. Notices and uploaded files are never sent."
            "</div>"
        )
    return (
        '<div class="haq-empty">'
        "Local AI mode is not configured, so this app uses local search only. "
        f"{_escape(active.problem)} "
        "To enable it, start Ollama and set "
        f"{_escape(ENV_MODEL)} to a tag shown by <code>ollama list</code>. "
        "Notices and uploaded files are never sent to an AI model."
        "</div>"
    )


def render_notice(facts: NoticeFacts, original: str) -> str:
    if not (original or "").strip():
        body = (
            '<div class="haq-empty">Paste the notice text above. '
            "The decoder will show only explicit dates, amounts, parties, reference numbers, "
            "and deadline language it can see in the text.</div>"
        )
        return _result_shell("Explicit facts only", "No dates inferred", body, empty=True)

    if not facts.has_facts:
        body = """
        <div class="haq-warning">
          No explicit dates, amounts, labelled parties, reference numbers, or deadline phrases
          were found. This tool does not infer a date or deadline.
        </div>
        """
        return _result_shell("No explicit facts found", "Nothing inferred", body)

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
    body = f"""
    <div class="haq-warning">
      These are exact text matches only. No deadline has been calculated, converted, or inferred.
      Check the original notice and confirm any date with a qualified person.
    </div>
    <div class="haq-facts">{blocks}</div>
    """
    return _result_shell("Explicit text matches", "No legal conclusion", body)


def render_notice_file_status(message: str, *, warning: bool = False) -> str:
    css_class = "haq-warning" if warning else "haq-empty"
    return f'<div class="{css_class}">{_escape(message)}</div>'


def render_empty_guide() -> str:
    body = """
    <div class="haq-empty">
      Try a specific question, such as: “My landlord has not returned my security deposit.”
      Choose a topic to narrow the search, or leave it on “All topics”.
    </div>
    """
    return _result_shell("Ready when you are", "AI off by default", body, empty=True)


def render_how_it_works() -> str:
    count = len(get_retriever().entries)
    return f"""
    <div class="haq-process" aria-label="How the guide works">
      <div class="haq-process-item">
        <span class="haq-process-num">1</span>
        <p><strong>Describe the problem</strong><span>Tenancy, consumer, or unpaid-wage question in English.</span></p>
      </div>
      <div class="haq-process-item">
        <span class="haq-process-num">2</span>
        <p><strong>Local search</strong><span>The TF-IDF retriever checks {count} verified passages.</span></p>
      </div>
      <div class="haq-process-item">
        <span class="haq-process-num">3</span>
        <p><strong>Sources or abstention</strong><span>Quoted passages and summaries, or an explicit no-match response.</span></p>
      </div>
    </div>
    """


def render_tools() -> str:
    retriever = get_retriever()
    unique_sources = {(entry.title, entry.source_url) for entry in retriever.entries}
    return f"""
    <section class="haq-band" aria-labelledby="tools-title">
      <div class="haq-band-head">
        <div>
          <div class="haq-eyebrow">In this MVP</div>
          <h2 id="tools-title">Four real routes through the guide</h2>
        </div>
        <p>Each card opens a working section of this local app. No placeholder pages or simulated results.</p>
      </div>
      <div class="haq-tool-grid">
        <a class="haq-tool-card" href="#ask">
          <div>
            <span class="haq-tool-index">01 · Ask</span>
            <h3>Situation guide</h3>
            <p class="haq-tool-deco">मामला गाइड</p>
            <p>Describe a tenancy, consumer, or unpaid-wage problem. The local search returns quoted passages or an explicit abstention.</p>
          </div>
          <span class="haq-tool-link">Go to the question box <span aria-hidden="true">→</span></span>
        </a>
        <a class="haq-tool-card" href="#notice">
          <div>
            <span class="haq-tool-index">02 · Notice</span>
            <h3>Notice decoder</h3>
            <p class="haq-tool-deco">नोटिस अनुवादक</p>
            <p>Paste notice text or upload a PDF, DOCX, or TXT file. The decoder extracts only explicit dates, amounts, parties, reference numbers, and deadline language.</p>
          </div>
          <span class="haq-tool-link">Open notice decoder <span aria-hidden="true">→</span></span>
        </a>
        <a class="haq-tool-card" href="#sources">
          <div>
            <span class="haq-tool-index">03 · Sources</span>
            <h3>Verified library</h3>
            <p class="haq-tool-deco">सत्यापित स्रोत</p>
            <p>{len(retriever.entries)} checked passages from {len(unique_sources)} official documents. Every indexed entry is marked verified_official.</p>
          </div>
          <span class="haq-tool-link">See the sources <span aria-hidden="true">→</span></span>
        </a>
        <a class="haq-tool-card" href="#legal-aid">
          <div>
            <span class="haq-tool-index">04 · Legal aid</span>
            <h3>Free legal help</h3>
            <p class="haq-tool-deco">मुफ़्त कानूनी सहायता</p>
            <p>NALSA helpline 15100, the official FAQ, and legal-aid eligibility information. This app does not decide eligibility.</p>
          </div>
          <span class="haq-tool-link">Go to legal aid <span aria-hidden="true">→</span></span>
        </a>
      </div>
    </section>
    """


def render_honesty() -> str:
    return """
    <section class="haq-band haq-honesty" aria-labelledby="honesty-title">
      <div class="haq-band-head">
        <div>
          <div class="haq-eyebrow">Source policy</div>
          <h2 id="honesty-title">How the guide stays honest</h2>
        </div>
        <p>The visual language is new. The behavior is the same verified-source pipeline underneath.</p>
      </div>
      <div class="haq-honesty-grid">
        <article class="haq-honesty-card">
          <span>01</span>
          <h3>Quoted, not invented</h3>
          <p>Every answer comes from the verified law library. The app does not generate a legal rule from a model.</p>
        </article>
        <article class="haq-honesty-card">
          <span>02</span>
          <h3>Abstains when unsure</h3>
          <p>If no indexed passage clears the relevance threshold, the guide says it could not find a verified match.</p>
        </article>
        <article class="haq-honesty-card">
          <span>03</span>
          <h3>No hidden calculations</h3>
          <p>The notice decoder extracts explicit text only from pasted or uploaded text. It does not OCR scanned pages, calculate, convert, or infer a deadline.</p>
        </article>
      </div>
      <p class="haq-honesty-note">
        The Model Tenancy Act, 2021 is a model law and is not automatically applicable in every
        State or Union Territory. The Code on Wages, 2019 has been in force since 21 November 2025.
      </p>
    </section>
    """


def render_privacy() -> str:
    return """
    <section class="haq-privacy" id="privacy" aria-labelledby="privacy-title">
      <div>
        <div class="haq-eyebrow">Privacy, in plain words</div>
        <h2 id="privacy-title">Your privacy is part of the architecture.</h2>
        <p>
          Haq Guide runs as a local Gradio app. It does not use analytics or an account system,
          and retrieval and notice decoding work without any external service. Local AI mode is off by default. If you configure a local Ollama model and tick the consent box, only your question and the retrieved passages are sent to that local model. Uploaded notice files are read on
          this computer and are never sent to an AI model. Source links open only when you
          click them.
        </p>
      </div>
      <div class="haq-privacy-stats" aria-label="Privacy facts">
        <div><span>Analytics</span><strong>None</strong></div>
        <div><span>External AI</span><strong>None</strong></div>
        <div><span>Account</span><strong>Not needed</strong></div>
      </div>
    </section>
    """


def render_legal_aid() -> str:
    return """
    <div class="haq-legal">
      <div class="haq-legal-copy">
        <div class="haq-legal-kicker">Free legal help · NALSA</div>
        <h2>If the problem is urgent or you cannot afford a lawyer</h2>
        <p>
          NALSA's official FAQ states that people can contact its toll-free helpline for urgent
          legal assistance.
        </p>
        <p>
          Eligibility can depend on the category of applicant and, for income-based eligibility,
          on the limits prescribed for the relevant State or Union Territory. This app does not
          decide eligibility.
        </p>
        <div class="haq-legal-points">
          <span>Official NALSA links</span>
          <span>No eligibility decision in this app</span>
        </div>
      </div>
      <div class="haq-legal-card">
        <div class="haq-legal-card-head">
          <span>National Legal Aid Helpline</span>
          <span>Toll-free</span>
        </div>
        <a class="haq-helpline" href="tel:15100">15100</a>
        <p>The app itself does not place the call. Use the official links below to confirm current information.</p>
        <div class="haq-legal-links">
          <a href="https://nalsa.gov.in/faqs" target="_blank" rel="noopener noreferrer">Read the NALSA FAQ</a>
          <a href="https://nalsa.gov.in/services/legal-aid/eligibility" target="_blank" rel="noopener noreferrer">Check legal-aid eligibility</a>
        </div>
      </div>
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
      <div class="haq-source-summary">
        <div class="haq-source-stat"><strong>{len(retriever.entries)}</strong><span>checked passages</span></div>
        <div class="haq-source-stat"><strong>{len(unique)}</strong><span>official documents</span></div>
        <div class="haq-source-stat"><strong>100%</strong><span>verified_official only</span></div>
      </div>
      <p>
        The starter library contains <strong>{len(retriever.entries)}</strong> checked passages
        from <strong>{len(unique)}</strong> official documents. Only passages marked
        <code>verified_official</code> are searchable.
      </p>
      <ul>{''.join(items)}</ul>
      <p class="haq-source-note">
        The Model Tenancy Act, 2021 is a model law; it is not automatically applicable in every
        State or Union Territory. The Code on Wages, 2019 has been in force since 21 November 2025.
      </p>
    </div>
    """


def _handle_guide(
    query: str,
    topic_label: str,
    use_ai: bool = False,
    *,
    settings: AISettings | None = None,
    transport=None,
) -> str:
    category = TOPIC_TO_CATEGORY.get(topic_label, "All")
    result = build_guide(query, category=category)
    if not use_ai:
        return render_guide(result)
    if result.abstained:
        return render_guide(
            result,
            ai_status="No verified passage matched, so no AI request was made.",
        )
    try:
        answer = answer_question(
            result.query,
            result.passages,
            settings=settings,
            transport=transport,
        )
    except AIConfigError:
        return render_guide(
            result,
            ai_status=(
                "Local AI mode is not configured. Showing local retrieval only; see the "
                "status note above the results."
            ),
        )
    except AIError as exc:
        return render_guide(
            result, ai_status=f"AI answer unavailable: {exc} Showing local retrieval only."
        )
    return render_guide(result, ai_answer=answer)


def _handle_notice(text: str) -> str:
    return render_notice(extract_notice_facts(text), text)


def _handle_notice_upload(file_value):
    if file_value in (None, "", []):
        return gr.skip(), render_notice_file_status(NOTICE_UPLOAD_HELP)
    try:
        document = read_notice_document(file_value)
    except DocumentError as exc:
        return gr.skip(), render_notice_file_status(str(exc), warning=True)
    except Exception:
        return gr.skip(), render_notice_file_status(
            "This file could not be read. Upload a different PDF, DOCX, or TXT file.",
            warning=True,
        )

    details = [f"Loaded {document.kind}"]
    if document.pages is not None:
        details.append(f"{document.pages} page(s)")
    details.append(f"{len(document.text):,} characters")
    message = (
        " · ".join(details)
        + ". Review the text above, then extract explicit facts. "
        "Nothing was sent to an external service."
    )
    if document.warnings:
        message = message + " " + " ".join(document.warnings)
    return document.text, render_notice_file_status(message, warning=bool(document.warnings))


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title=APP_TITLE,
        analytics_enabled=False,
    ) as demo:
        gr.HTML(SITE_HEADER_HTML, elem_id="haq-site-header-html")

        with gr.Column(elem_id="ask", elem_classes=["haq-hero-section"]):
            gr.HTML(HERO_INTRO_HTML)
            with gr.Row(elem_classes=["haq-intake-card"]):
                with gr.Column(scale=4, elem_classes=["haq-intake-main"]):
                    query = gr.Textbox(
                        label="Your question",
                        placeholder="e.g. My landlord is keeping my security deposit without giving a reason.",
                        lines=3,
                        interactive=True,
                        elem_id="haq-question",
                    )
                with gr.Column(scale=2, min_width=230, elem_classes=["haq-intake-side"]):
                    topic = gr.Radio(
                        choices=list(TOPIC_LABELS),
                        value="All topics",
                        label="Topic",
                        info="Choose one topic, or search all three.",
                        elem_id="haq-topic",
                    )
                    ask_button = gr.Button(
                        "Find verified guidance",
                        variant="primary",
                        elem_id="haq-ask-button",
                    )
                    ai_consent = gr.Checkbox(
                        label="Ask the local Ollama model for an explanation",
                        info=(
                            "Off by default. Runs on this computer and sends only your question and the "
                            "retrieved passages to localhost. Notices and uploaded files are never sent."
                        ),
                        value=False,
                        elem_id="haq-ai-consent",
                    )
            gr.HTML(render_ai_status(), elem_id="haq-ai-status")
            gr.HTML(render_how_it_works())
            guide_output = gr.HTML(value=render_empty_guide(), elem_id="haq-guide-output")

        gr.HTML(render_tools())

        with gr.Column(elem_id="notice", elem_classes=["haq-section"]):
            gr.HTML(
                _section_head(
                    "02 · Notice",
                    "Decode a notice",
                    "Paste a notice or upload a PDF, DOCX, or TXT file. Only what the text "
                    "explicitly says is shown. No dates are calculated, and scanned PDFs are not OCR'd.",
                )
            )
            notice_file = gr.File(
                label="Or upload a notice (.pdf, .docx, or .txt)",
                file_types=list(SUPPORTED_EXTENSIONS),
                file_count="single",
                type="filepath",
                interactive=True,
                elem_id="haq-notice-file",
            )
            notice_file_status = gr.HTML(
                value=render_notice_file_status(NOTICE_UPLOAD_HELP),
                elem_id="haq-notice-file-status",
            )
            notice_input = gr.Textbox(
                label="Notice text",
                placeholder="Paste the full notice here, including dates, amounts, and reference numbers.",
                lines=8,
                interactive=True,
                elem_id="haq-notice-input",
            )
            notice_button = gr.Button(
                "Extract explicit facts",
                variant="primary",
                elem_id="haq-notice-button",
            )
            notice_output = gr.HTML(
                value=render_notice(NoticeFacts((), (), (), (), ()), ""),
                elem_id="haq-notice-output",
            )

        gr.HTML(render_honesty())
        gr.HTML(render_privacy())

        with gr.Column(elem_id="legal-aid", elem_classes=["haq-section", "haq-legal-section"]):
            gr.HTML(render_legal_aid())

        with gr.Column(elem_id="sources", elem_classes=["haq-section"]):
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
            inputs=[query, topic, ai_consent],
            outputs=[guide_output],
        )
        query.submit(
            _handle_guide,
            inputs=[query, topic, ai_consent],
            outputs=[guide_output],
        )
        notice_button.click(
            _handle_notice,
            inputs=[notice_input],
            outputs=[notice_output],
        )
        notice_file.change(
            _handle_notice_upload,
            inputs=[notice_file],
            outputs=[notice_input, notice_file_status],
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
