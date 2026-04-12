"""
Compliance: FoundUp README must document route, AI hook, DAEmon, and namespace
surfaces per FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md (WSP 91 + WSP 104).

Discovery: any immediate child of modules/foundups/ with module.json or
foundup_manifest.json.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CONTRACT_FILENAME = "FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md"
CONTRACT_REL_PATH = f"modules/foundups/docs/{CONTRACT_FILENAME}"

HEADING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Route Namespace", re.compile(r"^##\s+Route Namespace\s*$", re.MULTILINE)),
    ("App Mount", re.compile(r"^##\s+App Mount\s*$", re.MULTILINE)),
    ("AI Capability Hooks", re.compile(r"^##\s+AI Capability Hooks\s*$", re.MULTILINE)),
    ("DAEmon Outputs", re.compile(r"^##\s+DAEmon Outputs\s*$", re.MULTILINE)),
    ("Data / Telemetry Namespace", re.compile(r"^##\s+Data / Telemetry Namespace\s*$", re.MULTILINE)),
    ("WSP References", re.compile(r"^##\s+WSP References\s*$", re.MULTILINE)),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _foundups_root() -> Path:
    return _repo_root() / "modules" / "foundups"


def discover_manifest_foundups() -> list[Path]:
    root = _foundups_root()
    out: list[Path] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        if (d / "module.json").exists() or (d / "foundup_manifest.json").exists():
            out.append(d)
    return out


def validate_foundup_readme(text: str) -> list[str]:
    errors: list[str] = []
    for label, pat in HEADING_PATTERNS:
        if not pat.search(text):
            errors.append(f"missing ## {label} heading")
    if "WSP 91" not in text:
        errors.append("missing literal 'WSP 91'")
    if "WSP 104" not in text:
        errors.append("missing literal 'WSP 104'")
    if CONTRACT_FILENAME not in text:
        errors.append(f"missing reference to {CONTRACT_FILENAME}")
    return errors


def test_canonical_contract_doc_exists_and_references_wsps() -> None:
    path = _repo_root() / CONTRACT_REL_PATH
    assert path.is_file(), f"expected {CONTRACT_REL_PATH}"
    body = path.read_text(encoding="utf-8")
    assert "WSP 91" in body
    assert "WSP 104" in body


def test_foundup_template_requires_contract_sections() -> None:
    tmpl = _foundups_root() / "docs" / "FOUNDUP_TEMPLATE.md"
    text = tmpl.read_text(encoding="utf-8")
    for label, pat in HEADING_PATTERNS:
        assert pat.search(text), f"FOUNDUP_TEMPLATE.md must document ## {label}"
    assert CONTRACT_FILENAME in text
    assert "WSP 91" in text
    assert "WSP 104" in text


@pytest.mark.parametrize("foundup_dir", discover_manifest_foundups(), ids=lambda p: p.name)
def test_foundup_readme_surface_contract(foundup_dir: Path) -> None:
    readme = foundup_dir / "README.md"
    assert readme.is_file(), f"{foundup_dir.name}: README.md required for contract compliance"
    errors = validate_foundup_readme(readme.read_text(encoding="utf-8"))
    assert not errors, f"{foundup_dir.name}: " + "; ".join(errors)


def test_validator_detects_gaps_in_minimal_readme(tmp_path: Path) -> None:
    p = tmp_path / "README.md"
    p.write_text("# X\n\nNo sections.\n", encoding="utf-8")
    errs = validate_foundup_readme(p.read_text(encoding="utf-8"))
    assert len(errs) >= 6
