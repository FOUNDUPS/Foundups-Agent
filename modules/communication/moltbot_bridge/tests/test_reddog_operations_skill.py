"""Provider-neutral RedDog Operations Skillz contract tests."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_operations_skill import (
    LOGICAL_ROLES,
    SKILL_NAME,
    SKILL_RELATIVE_PATH,
    load_reddog_operations_skill,
    operations_skill_receipt_matches,
    skill_receipt_dict,
)
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader


REPO_ROOT = Path(__file__).resolve().parents[4]
REGISTRY_PATH = (
    REPO_ROOT / "modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
)
MODEL_MARKERS = ("glm", "deepseek", "kimi", "qwen", "gemma", "gpt-")


def test_canonical_operations_skill_is_role_bound_and_model_independent() -> None:
    skill = load_reddog_operations_skill(REPO_ROOT)
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = registry["skills"][SKILL_NAME]

    assert skill.receipt["logical_roles"] == LOGICAL_ROLES
    assert skill.receipt["wsp_chain"] == (
        "WSP 00", "WSP 15", "WSP 50", "WSP 77", "WSP 95", "WSP 97"
    )
    assert skill.receipt["relative_path"] == SKILL_RELATIVE_PATH
    assert skill.receipt["grants_authority"] is False
    assert skill.receipt["receipt_id"].startswith("sha256:")
    assert entry["logical_roles"] == list(LOGICAL_ROLES)
    assert "only when its source receipt is" in skill.content
    assert "Otherwise record that source as unavailable" in skill.content
    assert "cannot prove" in skill.content
    assert "Current repository/direct-read evidence" in skill.content
    assert "approved Memex, Breadcrumb continuity, Brain history" in skill.content
    assert "historical artifact metadata" in skill.content
    assert "label unavailable content NEEDS_VERIFICATION" in skill.content
    assert "Registered FoundUp Work" in skill.content
    assert "foundup_registry.json" in skill.content
    assert "requires_wsp109_resolution" in skill.content
    assert "grant no mutation scope until resolved" in skill.content
    assert "exactly one bounded REUSE or EXTEND slice" in skill.content
    assert not {
        "agents",
        "primary_agent",
        "fallback_agent",
        "model",
        "models",
        "provider",
        "principal_model",
        "panel_models",
    }.intersection(entry)
    assert all(marker not in skill.content.lower() for marker in MODEL_MARKERS)


def test_role_discovery_is_separate_from_legacy_agent_discovery() -> None:
    loader = WRESkillsLoader(repo_root=REPO_ROOT)

    assert SKILL_NAME in loader.list_healthy_skills(
        logical_role="verifier", promotion_state="production"
    )
    assert SKILL_NAME not in loader.list_skills(agent_type="qwen")


def test_prompt_binds_skill_receipt_without_granting_authority() -> None:
    skill = load_reddog_operations_skill(REPO_ROOT)

    prompt = skill.prompt_for("Inspect current work.")

    assert skill.receipt["receipt_id"] in prompt
    assert skill.receipt["content_digest"] in prompt
    assert "Inspect current work." in prompt
    assert "grants no source mutation" in prompt


def test_persisted_intent_must_match_complete_use_time_receipt() -> None:
    skill = load_reddog_operations_skill(REPO_ROOT)
    receipt = skill_receipt_dict(skill)
    intent = {
        "operations_skill_receipt": receipt,
        "operations_skill_receipt_id": receipt["receipt_id"],
        "operations_skill_content_digest": receipt["content_digest"],
        "operations_skill_registry_entry_digest": receipt["registry_entry_digest"],
    }

    assert operations_skill_receipt_matches(intent, receipt)
    tampered = {
        **intent,
        "operations_skill_content_digest": "sha256:" + "0" * 64,
    }
    assert not operations_skill_receipt_matches(tampered, receipt)


@pytest.mark.parametrize(
    "relative_path",
    (REGISTRY_PATH.relative_to(REPO_ROOT), Path(SKILL_RELATIVE_PATH)),
)
def test_manifest_verified_policy_rejects_post_copy_tampering(
    tmp_path: Path,
    relative_path: Path,
) -> None:
    tracked = (REGISTRY_PATH.relative_to(REPO_ROOT), Path(SKILL_RELATIVE_PATH))
    expected: dict[Path, str] = {}
    reads: list[Path] = []
    for relative in tracked:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (REPO_ROOT / relative).read_bytes()
        target.write_bytes(raw)
        expected[relative] = hashlib.sha256(
            raw.replace(b"\r\n", b"\n")
        ).hexdigest()

    def verified_reader(path: Path) -> str:
        relative = Path(path).resolve().relative_to(tmp_path.resolve())
        reads.append(relative)
        raw = Path(path).read_bytes()
        observed = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        if observed != expected.get(relative):
            raise ImportError("runtime_source_digest_mismatch")
        return raw.decode("utf-8")

    assert load_reddog_operations_skill(
        tmp_path, verified_text_reader=verified_reader
    ).receipt["receipt_id"].startswith("sha256:")
    assert reads == list(tracked)
    target = tmp_path / relative_path
    target.write_text(target.read_text(encoding="utf-8") + "\nattacker", encoding="utf-8")
    with pytest.raises(ImportError, match="runtime_source_digest_mismatch"):
        load_reddog_operations_skill(
            tmp_path, verified_text_reader=verified_reader
        )


def test_role_skill_runtime_has_no_execution_surface_and_meets_wsp62() -> None:
    paths = (
        REPO_ROOT
        / "modules/infrastructure/wre_core/skillz/wre_role_skill_loader.py",
        REPO_ROOT
        / "modules/communication/moltbot_bridge/src/reddog_operations_skill.py",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert len(source.splitlines()) <= 200
        assert all(
            (node.end_lineno or node.lineno) - node.lineno + 1 <= 50
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        assert not any(
            isinstance(node, (ast.Import, ast.ImportFrom))
            and any(
                alias.name.split(".")[0] in {"subprocess", "requests", "openai"}
                for alias in node.names
            )
            for node in ast.walk(tree)
        )
