# Haq Guide (हक़ गाइड)

A small, local-first legal-information app for India. It currently covers three topics:

- situation guide
- notice decoder
- tenancy
- consumer complaints
- unpaid wages

The app searches a hand-checked library of official law excerpts with TF-IDF. If it cannot find a relevant verified passage, it abstains instead of guessing. It does not use an external AI API, analytics, a database, or a vector database.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Open <http://127.0.0.1:7860>. The server binds to `127.0.0.1` by default. Set `HAQ_PORT` to use a different port.

## Tests

```bash
.venv/bin/pytest
```

The tests cover verified-source loading, retrieval by topic, citation metadata, abstention on unrelated questions, and conservative notice extraction.

## How it works

```text
app.py                 Gradio interface and result rendering
haq/retrieve.py        TF-IDF index, category filter, abstention threshold
haq/guide.py           Source-grounded guide result assembly
haq/notice.py          Explicit-fact extraction only
haq/documents.py       Local PDF, DOCX, and TXT text extraction
law_library/           Verified source metadata and quoted passages
law_library/sources.md Source list and verification notes
tests/                 Pytest suite
```

Each law-library entry records its title, section, jurisdiction, official URL, collection date, verification status, excerpt, plain-language summary, and applicability note. Only entries marked `verified_official` are indexed.

## Source policy

- Source text was checked against official PDFs or official government pages on **29 October 2026**.
- The Model Tenancy Act, 2021 is a **model law**. It applies only if a State or Union Territory has adopted it or enacted similar provisions.
- The Code on Wages, 2019 has been in force from **21 November 2025**, according to an official Press Information Bureau release.
- NALSA's official FAQ states that its toll-free helpline is **15100**.
- The app does not calculate deadlines, infer missing dates, or state legal conclusions.
- If no verified passage is relevant, the app says so and points to legal aid.

## Current limitations

- The library is intentionally small: 16 passages from 5 official documents.
- It is English-only in this slice.
- It does not provide State-specific rent-control rules, consumer fee/pecuniary-jurisdiction calculations, or minimum-wage rates.
- Notice decoding extracts explicit text only. It does not validate whether a notice is legally effective.
- The Notice Decoder accepts pasted text plus PDF, DOCX, and TXT uploads. PDFs and DOCX files are read locally with `pypdf` and `python-docx`; text files must be UTF-8 or UTF-16. There is no OCR, so scanned PDFs report that no text could be extracted. The interface does not include clause analysis, deadline calculation, language switching, or generated draft documents.
- The interface uses local system fonts and inline CSS. It does not load a font CDN, analytics script, or frontend framework from an external service.
- No Ollama or other generative model is required or included in this slice.
- The app makes no application-level external requests at inference time and Gradio analytics is disabled. Full offline operation should still be verified in the target environment, because browser and Gradio behaviour can vary.

## Disclaimer

Haq Guide provides general legal information, not legal advice or a legal opinion. Laws and rules change, and a quoted passage may not fit a particular situation. For advice, contact a qualified lawyer or the relevant District Legal Services Authority. In an emergency, contact local emergency services.
