## Purpose

Describe the prospecting problem this change addresses.

## Boundaries checked

- [ ] No person fields (roles, e-mail, phone) are read, stored or exported.
- [ ] ENK stays excluded by default and keeps its warning.
- [ ] Registry data is still described as "not marketing consent" on the shortlist and export screens.
- [ ] No scraping, telemetry, accounts or external AI calls were added.
- [ ] Nothing under src/ imports streamlit; all SQL stays in storage.py.
- [ ] New legal or API facts cite an official source, or are marked TODO(verify).

## Verification

- [ ] Tests pass.
- [ ] Ruff passes.
- [ ] Documentation is updated.
