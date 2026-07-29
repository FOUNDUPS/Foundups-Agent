"""Strict provider-neutral WRE role Skillz tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.infrastructure.wre_core.skillz.wre_role_skill_loader import (
    WRERoleSkillLoader,
)
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader


ROLES = ("principal", "researcher", "critic", "implementer", "verifier")
SKILL_NAME = "role_skill"
SKILL_TEXT = """---
name: role_skill
description: Test provider-neutral role workflow.
version: 1.0.0
intent_type: DECISION
promotion_state: production
category: workflow
logical_roles: [principal, researcher, critic, implementer, verifier]
wsp_chain: [WSP 00, WSP 15, WSP 50, WSP 77, WSP 95, WSP 97]
evals:
  - name: bounded
    expected: pass
retirement_date: null
---
# Role Skill
"""


def _loader(
    tmp_path: Path,
    *,
    registry_change: dict | None = None,
    text_change: tuple[str, str] | None = None,
) -> WRERoleSkillLoader:
    relative = Path("skillz/role_skill")
    target = tmp_path / relative / "SKILLz.md"
    target.parent.mkdir(parents=True)
    content = SKILL_TEXT
    if text_change:
        content = content.replace(*text_change, 1)
    target.write_text(content, encoding="utf-8")
    entry = {
        "location": relative.as_posix(),
        "logical_roles": list(ROLES),
        "intent_type": "DECISION",
        "version": "1.0.0",
        "promotion_state": "production",
        "domain": "operations",
        "wsp_chain": ["WSP 00", "WSP 15", "WSP 50", "WSP 77", "WSP 95", "WSP 97"],
        "description": "Test provider-neutral role workflow.",
    }
    if registry_change:
        entry.update(registry_change)
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps({"version": "2.0", "skills": {SKILL_NAME: entry}}),
        encoding="utf-8",
    )
    return WRERoleSkillLoader(
        WRESkillsLoader(registry_path=registry_path, repo_root=tmp_path)
    )


def test_role_skill_loads_with_deterministic_digests(tmp_path: Path) -> None:
    artifact = _loader(tmp_path).load(SKILL_NAME, required_roles=ROLES)

    assert artifact.logical_roles == ROLES
    assert artifact.content_digest.startswith("sha256:")
    assert artifact.registry_entry_digest.startswith("sha256:")


@pytest.mark.parametrize(
    ("registry_change", "text_change"),
    (
        ({"agents": ["legacy-model"]}, None),
        ({"model_id": "attacker/model"}, None),
        (None, ("evals:", "model_id: attacker/model\nevals:")),
        ({"logical_roles": ["principal"]}, None),
        ({"wsp_chain": ["WSP 00"]}, None),
        (None, ("evals:", "model: fixed/model\nevals:")),
        (None, ("evals:", "evals: []\nignored_evals:")),
        (None, ("verifier]", "attacker]")),
        ({"version": ""}, None),
    ),
)
def test_role_skill_rejects_model_selectors_and_integrity_drift(
    tmp_path: Path,
    registry_change: dict | None,
    text_change: tuple[str, str] | None,
) -> None:
    loader = _loader(
        tmp_path,
        registry_change=registry_change,
        text_change=text_change,
    )

    with pytest.raises(ValueError):
        loader.load(SKILL_NAME, required_roles=ROLES)
