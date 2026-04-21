"""Target surface IO for AutoAgent Lab experiments.

Read production skill configs, create isolated workspace copies,
and write candidate mutations. Production files are NEVER modified.

Mutable fields (from experiment_config.py):
- agents, wsp_chain, domains, tokens_budget, prompt

Immutable fields (preserved exactly):
- name, version, description, author, dependencies, skill_id, category, etc.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from .experiment_config import VALID_MUTABLE_FIELDS
from .safety_gates import SafetyViolation, validate_workspace_path

logger = logging.getLogger("autoagent_lab.target_surface")

# Default workspace root relative to module
DEFAULT_WORKSPACE_ROOT = Path(__file__).parent.parent / "workspace"


class TargetSurfaceError(Exception):
    """Raised when target surface operations fail."""


@dataclass
class SkillSurface:
    """Represents a skill config surface for experimentation.

    Separates mutable fields (can be changed by experiments) from
    immutable fields (preserved exactly).
    """

    source_path: Path  # Original production file (read-only)
    workspace_path: Optional[Path]  # Workspace copy (if created)
    skill_id: str  # Derived from 'name' field or filename
    immutable_fields: dict[str, Any]  # Fields that cannot change
    mutable_fields: dict[str, Any]  # Fields that can be mutated
    body_content: str  # Markdown body after frontmatter

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "source_path": str(self.source_path),
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "skill_id": self.skill_id,
            "immutable_fields": dict(self.immutable_fields),
            "mutable_fields": dict(self.mutable_fields),
            "body_content_length": len(self.body_content),
        }


def load_skill_surface(skill_path: Path | str) -> SkillSurface:
    """Load a skill config from a production file.

    Args:
        skill_path: Path to the SKILL.md file.

    Returns:
        SkillSurface with parsed mutable/immutable fields.

    Raises:
        TargetSurfaceError: If the file cannot be read or parsed.
    """
    skill_path = Path(skill_path)

    if not skill_path.exists():
        raise TargetSurfaceError(f"Skill file not found: {skill_path}")

    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        raise TargetSurfaceError(f"Failed to read skill file: {e}")

    # Parse frontmatter and body
    frontmatter_str, body_content = _split_frontmatter(content)
    if frontmatter_str is None:
        raise TargetSurfaceError(f"No YAML frontmatter found in: {skill_path}")

    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as e:
        raise TargetSurfaceError(f"Invalid YAML frontmatter: {e}")

    if not isinstance(frontmatter, dict):
        raise TargetSurfaceError(f"Frontmatter must be a mapping, got {type(frontmatter).__name__}")

    # Separate mutable and immutable fields
    mutable_fields = {}
    immutable_fields = {}

    for key, value in frontmatter.items():
        if key in VALID_MUTABLE_FIELDS:
            mutable_fields[key] = value
        else:
            immutable_fields[key] = value

    # Derive skill_id from 'name' field or filename
    skill_id = immutable_fields.get("name") or skill_path.stem

    logger.debug(
        f"Loaded skill surface: {skill_id} "
        f"(mutable: {list(mutable_fields.keys())}, "
        f"immutable: {list(immutable_fields.keys())})"
    )

    return SkillSurface(
        source_path=skill_path.resolve(),
        workspace_path=None,
        skill_id=skill_id,
        immutable_fields=immutable_fields,
        mutable_fields=mutable_fields,
        body_content=body_content,
    )


def create_workspace_copy(
    surface: SkillSurface,
    workspace_root: Optional[Path] = None,
    experiment_id: Optional[str] = None,
) -> SkillSurface:
    """Create an isolated workspace copy of a skill surface.

    Args:
        surface: The skill surface to copy.
        workspace_root: Root directory for workspace copies.
            Defaults to module workspace/ directory.
        experiment_id: Optional experiment identifier for the subdirectory.
            If not provided, uses a hash of the source path.

    Returns:
        New SkillSurface with workspace_path set.

    Raises:
        SafetyViolation: If the workspace path escapes isolation.
        TargetSurfaceError: If the copy fails.
    """
    workspace_root = workspace_root or DEFAULT_WORKSPACE_ROOT
    workspace_root = Path(workspace_root).resolve()

    # Generate experiment subdirectory
    if experiment_id is None:
        # Deterministic: hash of source path
        path_hash = hashlib.sha256(str(surface.source_path).encode()).hexdigest()[:12]
        experiment_id = f"exp_{path_hash}"

    experiment_dir = workspace_root / experiment_id
    workspace_path = experiment_dir / "SKILL.md"

    # Validate workspace isolation (fail-closed)
    validate_workspace_path(workspace_root, workspace_path)

    # Create directory
    try:
        experiment_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise TargetSurfaceError(f"Failed to create workspace directory: {e}")

    # Write the skill content to workspace
    content = _render_skill_content(surface)
    try:
        workspace_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise TargetSurfaceError(f"Failed to write workspace copy: {e}")

    logger.info(f"Created workspace copy: {workspace_path}")

    # Return new surface with workspace_path set
    return SkillSurface(
        source_path=surface.source_path,
        workspace_path=workspace_path,
        skill_id=surface.skill_id,
        immutable_fields=dict(surface.immutable_fields),
        mutable_fields=dict(surface.mutable_fields),
        body_content=surface.body_content,
    )


def write_candidate_surface(
    surface: SkillSurface,
    updated_mutable_fields: dict[str, Any],
    candidate_suffix: str = "_candidate",
) -> Path:
    """Write a candidate skill config with updated mutable fields.

    Immutable fields are preserved exactly. Only mutable fields
    from updated_mutable_fields are applied.

    Args:
        surface: The skill surface (must have workspace_path set).
        updated_mutable_fields: New values for mutable fields.
            Keys not in VALID_MUTABLE_FIELDS are ignored with a warning.
        candidate_suffix: Suffix for the candidate filename.

    Returns:
        Path to the written candidate file.

    Raises:
        TargetSurfaceError: If no workspace_path or write fails.
        SafetyViolation: If candidate path escapes workspace.
    """
    if surface.workspace_path is None:
        raise TargetSurfaceError(
            "Cannot write candidate: no workspace_path set. "
            "Call create_workspace_copy() first."
        )

    workspace_dir = surface.workspace_path.parent
    candidate_path = workspace_dir / f"SKILL{candidate_suffix}.md"

    # Validate workspace isolation
    validate_workspace_path(workspace_dir.parent, candidate_path)

    # Merge mutable fields (only valid mutable keys)
    new_mutable = dict(surface.mutable_fields)
    for key, value in updated_mutable_fields.items():
        if key in VALID_MUTABLE_FIELDS:
            new_mutable[key] = value
        else:
            logger.warning(f"Ignoring non-mutable field in update: {key}")

    # Create temporary surface with updated mutable fields
    candidate_surface = SkillSurface(
        source_path=surface.source_path,
        workspace_path=candidate_path,
        skill_id=surface.skill_id,
        immutable_fields=surface.immutable_fields,
        mutable_fields=new_mutable,
        body_content=surface.body_content,
    )

    # Render and write
    content = _render_skill_content(candidate_surface)
    try:
        candidate_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise TargetSurfaceError(f"Failed to write candidate: {e}")

    logger.info(f"Wrote candidate: {candidate_path}")
    return candidate_path


def get_candidate_path(surface: SkillSurface, candidate_suffix: str = "_candidate") -> Path:
    """Get the deterministic path for a candidate file.

    Args:
        surface: The skill surface (must have workspace_path set).
        candidate_suffix: Suffix for the candidate filename.

    Returns:
        Path where candidate would be written.

    Raises:
        TargetSurfaceError: If no workspace_path set.
    """
    if surface.workspace_path is None:
        raise TargetSurfaceError("No workspace_path set")

    return surface.workspace_path.parent / f"SKILL{candidate_suffix}.md"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_frontmatter(content: str) -> tuple[Optional[str], str]:
    """Split content into frontmatter and body.

    Returns:
        (frontmatter_str, body_content)
        frontmatter_str is None if no frontmatter found.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, content

    # Find closing ---
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :])
            return frontmatter, body

    return None, content


def _render_skill_content(surface: SkillSurface) -> str:
    """Render a SkillSurface back to SKILL.md format.

    Combines immutable and mutable fields into frontmatter,
    preserving field order (immutable first, then mutable).
    """
    # Combine fields: immutable first, then mutable
    combined = {}
    combined.update(surface.immutable_fields)
    combined.update(surface.mutable_fields)

    # Render frontmatter
    frontmatter = yaml.dump(combined, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Combine with body
    return f"---\n{frontmatter}---{surface.body_content}"
