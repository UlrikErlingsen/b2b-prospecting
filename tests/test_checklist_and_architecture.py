import ast
from pathlib import Path

import pytest

import prospectsignal
from prospectsignal import checklist
from prospectsignal.errors import DataProblem

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_HOSTS = (
    "https://lovdata.no/",
    "https://www.forbrukertilsynet.no/",
    "https://www.datatilsynet.no/",
    "https://www.brreg.no/",
    "https://data.norge.no/",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_nothing_under_src_imports_streamlit_except_ui():
    ui = ROOT / "src" / "prospectsignal" / "ui"
    offenders = [
        str(path)
        for path in (ROOT / "src").rglob("*.py")
        if ui not in path.parents and "streamlit" in _imports(path)
    ]
    assert offenders == []


def test_core_package_does_not_import_the_ui_layer():
    # The Streamlit-free core must not reach Streamlit indirectly through prospectsignal.ui either.
    offenders = []
    for path in (ROOT / "src" / "prospectsignal").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = ("." * node.level) + (node.module or "")
                names = {alias.name for alias in node.names}
                if module in {"prospectsignal.ui", ".ui"} or module.startswith(("prospectsignal.ui.", ".ui.")):
                    offenders.append(path.name)
                elif module in {"prospectsignal", "."} and "ui" in names:
                    offenders.append(path.name)
            elif isinstance(node, ast.Import) and any(a.name.startswith("prospectsignal.ui") for a in node.names):
                offenders.append(path.name)
    assert offenders == []


def test_only_storage_talks_to_the_database():
    offenders = [
        path.name
        for path in (ROOT / "src" / "prospectsignal").glob("*.py")
        if "duckdb" in _imports(path) and path.name != "storage.py"
    ]
    assert offenders == []


def test_pages_do_not_import_duckdb_directly():
    ui = ROOT / "src" / "prospectsignal" / "ui"
    for path in [ROOT / "app.py", *(ROOT / "pages").glob("*.py"), *ui.rglob("*.py")]:
        assert "duckdb" not in _imports(path), path


def test_public_api_is_exported():
    for name in prospectsignal.__all__:
        assert hasattr(prospectsignal, name), name


def test_bundled_checklist_is_sourced_and_marks_open_questions():
    loaded = checklist.load()
    assert "not legal advice" in loaded.disclaimer.lower()
    ids = {item.id for item in loaded.items}
    assert {
        "company-versus-named-person",
        "email-sms-prior-consent",
        "phone-reservation",
        "gdpr-legitimate-interest",
    } <= ids
    for item in loaded.items:
        assert item.sources, item.id
        for source in item.sources:
            assert source.url.startswith(OFFICIAL_HOSTS), (item.id, source.url)
            assert source.retrieved == "2026-10-01"
    assert any(item.needs_verification for item in loaded.items)


def test_checklist_rejects_unsourced_or_malformed_items(tmp_path):
    with pytest.raises(DataProblem, match="official source"):
        checklist.parse("items:\n  - {id: a, title: A, applies_to: email, status: verified, rule: r, action: x}\n")
    with pytest.raises(DataProblem, match="status"):
        checklist.parse(
            "items:\n  - {id: a, title: A, applies_to: email, status: maybe, rule: r, action: x, "
            "sources: [{url: 'https://lovdata.no/'}]}\n"
        )


def test_checklist_override_via_environment(tmp_path, monkeypatch):
    custom = tmp_path / "mine.yaml"
    custom.write_text(
        "version: x\ndisclaimer: Not legal advice.\nitems:\n  - {id: own, title: Own rule, applies_to: any, "
        "status: TODO(verify), rule: r, action: a, sources: [{publisher: P, title: T, url: 'https://lovdata.no/', "
        "reference: ref, retrieved: '2026-10-01'}]}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(checklist.ENV_OVERRIDE, str(custom))
    assert [item.id for item in checklist.load().items] == ["own"]
