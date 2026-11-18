"""Strict provider-neutral role Skillz loader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from modules.infrastructure.wre_core.skillz.wre_skills_loader import WRESkillsLoader

ROLE_SKILL_REGISTRY_FIELDS = frozenset({
        "description", "domain", "intent_type", "location", "logical_roles",
        "promotion_state", "version", "wsp_chain",
})
ROLE_SKILL_FRONTMATTER_FIELDS = frozenset({
        "category", "description", "evals", "intent_type", "logical_roles",
        "name", "promotion_state", "retirement_date", "version", "wsp_chain",
})

@dataclass(frozen=True)
class RoleSkillArtifact:
    name: str
    version: str
    logical_roles: tuple[str, ...]
    wsp_chain: tuple[str, ...]
    promotion_state: str
    location: Path
    content: str
    content_digest: str
    registry_entry_digest: str

class WRERoleSkillLoader:
    """Rehydrate one exact role Skillz without selecting a model."""

    def __init__(self, loader: WRESkillsLoader) -> None:
        self._loader = loader

    def load(
        self,
        skill_name: str,
        *,
        required_roles: Sequence[str],
        promotion_state: str = "production",
    ) -> RoleSkillArtifact:
        skill_info = _skill_info(
            self._loader.registry, skill_name, promotion_state
        )
        roles = _required_roles(skill_info, required_roles)
        skill_path = self._loader.resolve_skill_file(skill_name)
        metadata = self._loader.get_skill_metadata(skill_name)
        if not isinstance(metadata, Mapping):
            raise ValueError(f"Role skill '{skill_name}' metadata is invalid")
        hygiene = self._loader.check_skill_hygiene(skill_name)
        if (
            not hygiene.is_healthy
            or hygiene.missing_evals
            or not _metadata_matches(
                skill_name, promotion_state, roles, skill_info, metadata
            )
        ):
            raise ValueError(f"Role skill '{skill_name}' failed integrity checks")
        content = skill_path.read_text(encoding="utf-8")
        return _artifact(
            skill_name, promotion_state, roles, skill_info, skill_path, content
        )

def load_verified_role_skill(
    *,
    registry: Mapping[str, Any],
    skill_name: str,
    skill_path: Path,
    content: str,
    required_roles: Sequence[str],
    promotion_state: str = "production",
) -> RoleSkillArtifact:
    """Build a role Skillz only from already authenticated bytes."""
    skill_info = _skill_info(registry, skill_name, promotion_state)
    roles = _required_roles(skill_info, required_roles)
    metadata = _frontmatter(content)
    if (
        not _metadata_healthy(metadata)
        or not _metadata_matches(
            skill_name, promotion_state, roles, skill_info, metadata
        )
    ):
        raise ValueError(f"Role skill '{skill_name}' failed integrity checks")
    return _artifact(
        skill_name, promotion_state, roles, skill_info, skill_path, content
    )

def _skill_info(
    registry: Mapping[str, Any], skill_name: str, promotion_state: str
) -> Mapping[str, Any]:
    skills = registry.get("skills")
    value = skills.get(skill_name) if isinstance(skills, Mapping) else None
    if not isinstance(value, Mapping):
        raise ValueError(f"Skill not found in registry: {skill_name}")
    if (
        not str(value.get("version") or "").strip()
        or set(value) != ROLE_SKILL_REGISTRY_FIELDS
        or value.get("promotion_state") != promotion_state
    ):
        raise ValueError(f"Role skill '{skill_name}' registry schema is invalid")
    return value

def _required_roles(
    skill_info: Mapping[str, Any], required_roles: Sequence[str]
) -> tuple[str, ...]:
    roles = _logical_roles(skill_info)
    required = tuple(str(role).strip() for role in required_roles)
    if not roles or any(not role for role in required):
        raise ValueError("Role skill logical roles are invalid")
    if not set(required).issubset(roles):
        raise ValueError("Role skill is missing required logical roles")
    return roles

def _metadata_matches(
    skill_name: str,
    promotion_state: str,
    roles: tuple[str, ...],
    skill_info: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> bool:
    return bool(
        metadata.get("name") == skill_name
        and str(metadata.get("version") or "") == str(skill_info.get("version") or "")
        and metadata.get("promotion_state") == promotion_state
        and _logical_roles(metadata) == roles
        and metadata.get("description") == skill_info.get("description")
        and metadata.get("intent_type") == skill_info.get("intent_type")
        and tuple(metadata.get("wsp_chain") or ())
        == tuple(skill_info.get("wsp_chain") or ())
        and set(metadata) == ROLE_SKILL_FRONTMATTER_FIELDS
    )

def _frontmatter(content: str) -> Mapping[str, Any]:
    normalized = content.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return {}
    end = normalized.find("\n---\n", 4)
    value = yaml.safe_load(normalized[4:end]) if end >= 0 else None
    return value if isinstance(value, Mapping) else {}

def _metadata_healthy(metadata: Mapping[str, Any]) -> bool:
    if metadata.get("category") not in {"workflow", "capability-uplift"}:
        return False
    if not metadata.get("evals"):
        return False
    retirement = metadata.get("retirement_date")
    if retirement in (None, "", "null"):
        return True
    try:
        return date.fromisoformat(str(retirement)) > date.today()
    except ValueError:
        return False

def _artifact(
    skill_name: str,
    promotion_state: str,
    roles: tuple[str, ...],
    skill_info: Mapping[str, Any],
    skill_path: Path,
    content: str,
) -> RoleSkillArtifact:
    return RoleSkillArtifact(
        name=skill_name,
        version=str(skill_info.get("version") or ""),
        logical_roles=roles,
        wsp_chain=tuple(skill_info.get("wsp_chain") or ()),
        promotion_state=promotion_state,
        location=skill_path,
        content=content,
        content_digest=_sha256(content),
        registry_entry_digest=_sha256(json.dumps(
            skill_info, sort_keys=True, separators=(",", ":")
        )),
    )

def _logical_roles(value: Mapping[str, Any]) -> tuple[str, ...]:
    raw = value.get("logical_roles") or ()
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return ()
    roles = tuple(str(role).strip() for role in raw)
    return roles if all(roles) and len(set(roles)) == len(roles) else ()

def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

__all__ = [
    "ROLE_SKILL_FRONTMATTER_FIELDS",
    "ROLE_SKILL_REGISTRY_FIELDS",
    "RoleSkillArtifact",
    "WRERoleSkillLoader",
    "load_verified_role_skill",
]
