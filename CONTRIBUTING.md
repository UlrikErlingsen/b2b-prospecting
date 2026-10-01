# Contributing

Contributions should preserve ProspectSignal's boundaries: companies, never people; open register data only (no scraping); no telemetry, accounts or external AI calls; registry data is never presented as marketing consent; the Freddo bridge stays a manual, one-way file.

Architecture rules (enforced by tests):

- All logic, data models and storage live in `src/prospectsignal/` and never import Streamlit.
- Streamlit code lives only in `app.py` and `pages/`; pages call the package's functions.
- All database access goes through `src/prospectsignal/storage.py`.
- The package stays pip-installable with its public API in `src/prospectsignal/__init__.py`.

When you add an API detail or a legal rule, cite an official source with URL and retrieval date in `docs/sources.md` (or the checklist YAML). If you cannot confirm it, mark it `TODO(verify)` instead of guessing.

Before submitting a change:

```bash
python -m pytest
python -m ruff check .
python -m build
```

Tests must not make live network calls; use recorded fixtures. Use fictional data in fixtures and examples, never real people.
