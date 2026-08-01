"""Canonical provider-neutral Operations Skillz binding."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)
from modules.infrastructure.wre_core.skillz.wre_role_skill_loader import (
    WRERoleSkillLoader, load_verified_role_skill,
)
from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader


SKILL_NAME = "reddog_operations"
SKILL_VERSION = "1.1.0"
SKILL_RELATIVE_PATH = (
    "modules/communication/moltbot_bridge/skillz/reddog_operations/SKILLz.md"
)
LOGICAL_ROLES = ("principal", "researcher", "critic", "implementer", "verifier")
REQUIRED_WSP_CHAIN = ("WSP 00", "WSP 15", "WSP 50", "WSP 77", "WSP 95", "WSP 97")
RECEIPT_SCHEMA = "reddog_operations_skill_receipt.v1"
REGISTRY_RELATIVE_PATH = (
    "modules/infrastructure/wre_core/skillz/skills_registry_v2.json"
)


@dataclass(frozen=True)
class RedDogOperationsSkill:
    content: str
    receipt: Mapping[str, Any]

    def prompt_for(self, work_focus: str) -> str:
        return "\n".join(
            (
                "# BOUND REDDOG OPERATIONS SKILLZ",
                f"receipt_id: {self.receipt['receipt_id']}",
                f"content_digest: {self.receipt['content_digest']}",
                self.content,
                "# BOUND START OPERATIONS WORK FOCUS",
                work_focus,
            )
        )


def load_reddog_operations_skill(
    repo_root: Path | str,
    *,
    verified_text_reader: Callable[[Path], str] | None = None,
) -> RedDogOperationsSkill:
    root = Path(repo_root).resolve()
    registry_path = (root / REGISTRY_RELATIVE_PATH).resolve()
    if not registry_path.is_relative_to(root) or not registry_path.is_file():
        raise ValueError("reddog_operations_skill_registry_invalid")
    expected_path = (root / SKILL_RELATIVE_PATH).resolve()
    if verified_text_reader is None:
        loader = WRESkillsLoader(registry_path=registry_path, repo_root=root)
        registry = loader.registry
        artifact = WRERoleSkillLoader(loader).load(
            SKILL_NAME, required_roles=LOGICAL_ROLES
        )
    else:
        registry = _verified_registry(verified_text_reader, registry_path)
        artifact = load_verified_role_skill(
            registry=registry,
            skill_name=SKILL_NAME,
            skill_path=expected_path,
            content=verified_text_reader(expected_path),
            required_roles=LOGICAL_ROLES,
        )
    if (
        registry.get("version") != "2.0"
        or artifact.version != SKILL_VERSION
        or artifact.logical_roles != LOGICAL_ROLES
        or artifact.location != expected_path
        or artifact.wsp_chain != REQUIRED_WSP_CHAIN
    ):
        raise ValueError("reddog_operations_skill_binding_invalid")
    values = {
        "schema_version": RECEIPT_SCHEMA,
        "skill_name": artifact.name,
        "skill_version": artifact.version,
        "relative_path": SKILL_RELATIVE_PATH,
        "logical_roles": artifact.logical_roles,
        "wsp_chain": REQUIRED_WSP_CHAIN,
        "content_digest": artifact.content_digest,
        "registry_entry_digest": artifact.registry_entry_digest,
        "grants_authority": False,
    }
    receipt = MappingProxyType({**values, "receipt_id": canonical_digest(values)})
    return RedDogOperationsSkill(content=artifact.content, receipt=receipt)


def _verified_registry(
    reader: Callable[[Path], str], registry_path: Path
) -> Mapping[str, Any]:
    value = json.loads(reader(registry_path))
    if not isinstance(value, Mapping):
        raise ValueError("reddog_operations_skill_registry_invalid")
    return value


def skill_receipt_dict(skill: RedDogOperationsSkill) -> Mapping[str, Any]:
    """Return a detached JSON-compatible receipt mapping."""
    return {
        **dict(skill.receipt),
        "logical_roles": list(skill.receipt["logical_roles"]),
        "wsp_chain": list(skill.receipt["wsp_chain"]),
    }


def operations_skill_receipt_matches(
    intent: Mapping[str, Any],
    expected_receipt: Mapping[str, Any],
) -> bool:
    """Prove one persisted operations intent matches the use-time Skillz."""
    observed = intent.get("operations_skill_receipt")
    if not isinstance(observed, Mapping):
        return False
    expected = dict(expected_receipt)
    return bool(
        dict(observed) == expected
        and intent.get("operations_skill_receipt_id") == expected.get("receipt_id")
        and intent.get("operations_skill_content_digest")
        == expected.get("content_digest")
        and intent.get("operations_skill_registry_entry_digest")
        == expected.get("registry_entry_digest")
        and expected.get("grants_authority") is False
    )


__all__ = [
    "LOGICAL_ROLES",
    "RECEIPT_SCHEMA",
    "REQUIRED_WSP_CHAIN",
    "REGISTRY_RELATIVE_PATH",
    "RedDogOperationsSkill",
    "SKILL_NAME",
    "SKILL_RELATIVE_PATH",
    "SKILL_VERSION",
    "load_reddog_operations_skill",
    "operations_skill_receipt_matches",
    "skill_receipt_dict",
]
