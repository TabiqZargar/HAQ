# AGENTS.md

## Repository state
- Python 3.14 project using Gradio and scikit-learn.
- Main app: `app.py`. Core logic: `haq/retrieve.py`, `haq/guide.py`, `haq/notice.py`.
- Verified law-library entries live under `law_library/{tenancy,consumer,labour}/`; provenance is in `law_library/sources.md`.
- There is no CI, lint config, database, or `opencode.json`.

## Commands
- Install: `.venv/bin/pip install -r requirements.txt`
- Run: `.venv/bin/python app.py` (then open `http://127.0.0.1:7860`)
- Test: `.venv/bin/pytest`

## Conventions
- Default branch is `master`; remote is `origin` (github.com/TabiqZargar/HAQ).
- Add contributor names to `contributors.md`.
- Only `verified_official` law-library entries may be indexed.
- Do not invent statutes, sections, citations, deadlines, or legal conclusions.
- Keep the app local-first: no external AI APIs, analytics, or inference-time network calls.
- The Model Tenancy Act, 2021 is a model law, not automatically applicable in every State/UT.
