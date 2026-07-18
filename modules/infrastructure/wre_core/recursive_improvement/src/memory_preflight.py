#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WRE Memory Preflight Guard
===========================

Enforces WSP_CORE "WSP Memory System (0102)" by requiring tiered memory retrieval
and auto-stubbing Tier-0 artifacts (README.md, INTERFACE.md) before code changes.

WSP Compliance:
    - WSP_CORE: Memory System, Tiered Holo Retrieval Targets, Start-of-Work Loop
    - WSP 50: Pre-Action Verification
    - WSP 87: Code Navigation Protocol (HoloIndex)
    - WSP_00 Section 3.4: Post-Awakening Operational Protocol

Architecture:
    HoloIndex = Retrieval Memory (canonical)
    WRE = Enforcement & orchestration gate (hard stop)
    AI_Overseer = Safe patch/write executor (allowlisted)

Environment Variables:
    WRE_MEMORY_PREFLIGHT_ENABLED: Enable preflight checks (default: true)
    WRE_MEMORY_AUTOSTUB_TIER0: Auto-create missing Tier-0 stubs (default: false)
    WRE_MEMORY_ALLOW_DEGRADED: Allow proceed with missing artifacts (default: false)
    WRE_HOLO_RETRIEVAL_MODE: semantic (default) or explicit lexical opt-down
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# =============================================================================
# TIER DEFINITIONS (Mirror WSP_CORE)
# =============================================================================

@dataclass
class TierDefinition:
    """Defines a retrieval tier with required and optional artifacts."""
    tier: int
    name: str
    required: List[str]
    optional: List[str]
    purpose: str


# Canonical tier definitions per WSP_CORE "Tiered Holo Retrieval Targets"
TIER_DEFINITIONS = {
    0: TierDefinition(
        tier=0,
        name="Contract/Guardrails",
        required=["README.md", "INTERFACE.md"],
        optional=["SPEC.md", "PRD.md", "PROMPTS.md", "prompts/", "RUNBOOK.md"],
        purpose="What the module is + contract + constraints"
    ),
    1: TierDefinition(
        tier=1,
        name="Evolution/Verification",
        required=[],
        optional=["ROADMAP.md", "ModLog.md", "tests/TestModLog.md", "tests/README.md", "GOLDENS/"],
        purpose="What changed + what's verified + how to reproduce"
    ),
    2: TierDefinition(
        tier=2,
        name="Retrieval/Decisions/Failures",
        required=[],
        optional=[
            "HOLOINDEX.md", "ADR.md", "adr/", "INCIDENTS.md",
            "SEV.md", "EXPERIMENTS.md", "TRACES/"
        ],
        purpose="Why decisions exist + known failures + retrieval config"
    ),
}


# =============================================================================
# MEMORY BUNDLE
# =============================================================================

@dataclass
class ArtifactInfo:
    """Information about a single memory artifact."""
    path: str
    relative_path: str
    tier: int
    required: bool
    exists: bool
    last_updated: Optional[str] = None
    key_snippets: List[str] = field(default_factory=list)
    why_retrieved: str = ""


@dataclass
class MemoryBundle:
    """
    Structured memory bundle for orchestration.
    Machine-first format per WSP_CORE Memory-First Retrieval Contract.
    """
    module_path: str
    artifacts: List[ArtifactInfo]
    missing_required: List[str]
    missing_optional: List[str]
    duplication_rate_proxy: float
    ordering_confidence: Optional[float]
    staleness_risk: Optional[str]
    tier0_complete: bool
    preflight_passed: bool
    stubs_created: List[str] = field(default_factory=list)
    requested_retrieval_mode: str = "unknown"
    retrieval_mode: str = "unknown"
    embedding_backend: str = "unknown"
    routing_active: bool = False
    semantic_requirement_met: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "module_path": self.module_path,
            "artifacts": [
                {
                    "path": a.path,
                    "relative_path": a.relative_path,
                    "tier": a.tier,
                    "required": a.required,
                    "exists": a.exists,
                    "last_updated": a.last_updated,
                    "why_retrieved": a.why_retrieved,
                }
                for a in self.artifacts
            ],
            "missing_required": self.missing_required,
            "missing_optional": self.missing_optional,
            "duplication_rate_proxy": self.duplication_rate_proxy,
            "ordering_confidence": self.ordering_confidence,
            "staleness_risk": self.staleness_risk,
            "tier0_complete": self.tier0_complete,
            "preflight_passed": self.preflight_passed,
            "stubs_created": self.stubs_created,
            "requested_retrieval_mode": self.requested_retrieval_mode,
            "retrieval_mode": self.retrieval_mode,
            "embedding_backend": self.embedding_backend,
            "routing_active": self.routing_active,
            "semantic_requirement_met": self.semantic_requirement_met,
        }


def _resolve_holo_retrieval_mode(env: Optional[Dict[str, str]] = None) -> str:
    """Return the governed WRE retrieval mode (semantic unless explicitly lexical)."""
    source = env if env is not None else os.environ
    requested = str(source.get("WRE_HOLO_RETRIEVAL_MODE", "semantic")).strip().lower()
    return "lexical" if requested == "lexical" else "semantic"


def _build_holo_query_env(
    source_env: Optional[Dict[str, str]] = None,
    retrieval_mode: str = "semantic",
) -> Dict[str, str]:
    """Build a read-only HoloIndex environment without silent mode inheritance."""
    env = dict(source_env if source_env is not None else os.environ)
    env["HOLO_SILENT"] = "1"
    env["HOLOINDEX_QUERY_READONLY"] = "1"
    if retrieval_mode == "lexical":
        env["HOLO_SKIP_MODEL"] = "1"
    else:
        env.pop("HOLO_SKIP_MODEL", None)
    return env


# =============================================================================
# STUB TEMPLATES (Machine-First, ASCII-Safe)
# =============================================================================

README_STUB_TEMPLATE = '''# {module_name}

## Purpose

[TODO: Describe module purpose in 1-2 sentences]

## WSP Compliance

- WSP_CORE: Memory System compliant (Tier-0 stub created)
- WSP 49: Module structure pending completion

## Usage

```bash
# [TODO: Add usage example]
python -m {module_import_path}
```

## Integration Points

- [TODO: List integration points]

## Dependencies

- [TODO: List dependencies]

---

*Tier-0 stub created per WSP_CORE Memory System. See: WSP_framework/src/WSP_CORE.md*
'''

INTERFACE_STUB_TEMPLATE = '''# {module_name} Interface

## Public API

[TODO: Document public API]

```python
# Example:
# def main_function(arg1: str) -> bool:
#     """Brief description."""
#     pass
```

## Error Handling

- [TODO: Document error types and handling]

## Examples

```python
# [TODO: Add usage examples]
```

---

*Tier-0 stub created per WSP_CORE Memory System. See: WSP_framework/src/WSP_CORE.md*
'''


# =============================================================================
# PREFLIGHT GUARD EXCEPTIONS
# =============================================================================

class MemoryPreflightError(Exception):
    """Raised when memory preflight check fails."""
    def __init__(self, message: str, missing_files: List[str], module_path: str):
        super().__init__(message)
        self.missing_files = missing_files
        self.module_path = module_path
        if any(str(item).startswith("Semantic retrieval:") for item in missing_files):
            self.required_action = (
                "Restore the cached embedding model/dependencies, or explicitly set "
                "WRE_MEMORY_ALLOW_DEGRADED=true for a truth-labelled degraded run"
            )
        else:
            self.required_action = (
                "Create Tier-0 stubs or enable WRE_MEMORY_AUTOSTUB_TIER0=true"
            )


# =============================================================================
# MEMORY PREFLIGHT GUARD
# =============================================================================

class MemoryPreflightGuard:
    """
    Enforces WSP_CORE Memory System by requiring tiered retrieval
    and Tier-0 artifact presence before code-changing operations.

    Usage:
        guard = MemoryPreflightGuard(project_root)
        bundle = guard.run_preflight("modules/communication/livechat")
        if not bundle.preflight_passed:
            # Handle missing artifacts or use stubs_created
            pass
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize Memory Preflight Guard.

        Args:
            project_root: Root of the project. Defaults to auto-detect.
        """
        if project_root is None:
            # Auto-detect from this file's location
            project_root = Path(__file__).resolve().parents[5]
        self.project_root = Path(project_root)

        # Environment configuration
        self.enabled = os.getenv("WRE_MEMORY_PREFLIGHT_ENABLED", "true").lower() in ("true", "1", "yes")
        self.autostub_tier0 = os.getenv("WRE_MEMORY_AUTOSTUB_TIER0", "false").lower() in ("true", "1", "yes")
        self.allow_degraded = os.getenv("WRE_MEMORY_ALLOW_DEGRADED", "false").lower() in ("true", "1", "yes")
        self.use_holo_bundle = os.getenv("WRE_MEMORY_USE_HOLO_BUNDLE", "true").lower() in ("true", "1", "yes")

        logger.info(
            f"[MEMORY-PREFLIGHT] Initialized: enabled={self.enabled}, "
            f"autostub={self.autostub_tier0}, allow_degraded={self.allow_degraded}, "
            f"use_holo_bundle={self.use_holo_bundle}"
        )

    def run_preflight(self, module_path: str, task: Optional[str] = None) -> MemoryBundle:
        """
        Run memory preflight check for a module.

        Executes WSP_CORE Start-of-Work Loop:
        1. Tiered retrieval (Tier 0 -> 1 -> 2)
        2. Evaluate retrieval quality
        3. Auto-stub Tier-0 if enabled and missing
        4. Return structured Memory Bundle

        Args:
            module_path: Relative path to module (e.g., "modules/communication/livechat")
            task: Optional task/objective string for HoloIndex bundle (defaults to module-scoped preflight)

        Returns:
            MemoryBundle with retrieval results and preflight status

        Raises:
            MemoryPreflightError: If Tier-0 missing and autostub disabled
        """
        if not self.enabled:
            logger.info("[MEMORY-PREFLIGHT] Disabled - skipping preflight")
            return self._create_passthrough_bundle(module_path)

        full_module_path = self.project_root / module_path

        # Canonical retrieval: HoloIndex emits machine-readable bundle JSON
        if self.use_holo_bundle:
            holo_task = (task or f"memory preflight for {module_path}").strip()
            bundle = self._retrieve_via_holo_bundle(module_path=module_path, task=holo_task)

            # Tier-0 enforcement (disk is source of truth for existence)
            missing_required, missing_optional, duplication_proxy = self._evaluate_quality(bundle.artifacts)
            tier0_complete = len([m for m in missing_required if "Tier-0" in m]) == 0

            stubs_created: List[str] = []
            if not tier0_complete and self.autostub_tier0:
                stubs_created = self._create_tier0_stubs(full_module_path, module_path, missing_required)
                # Re-run canonical retrieval after stub creation
                bundle = self._retrieve_via_holo_bundle(module_path=module_path, task=holo_task)
                missing_required, missing_optional, duplication_proxy = self._evaluate_quality(bundle.artifacts)
                tier0_complete = len([m for m in missing_required if "Tier-0" in m]) == 0

            preflight_passed = tier0_complete or self.allow_degraded

            out = MemoryBundle(
                module_path=module_path,
                artifacts=bundle.artifacts,
                missing_required=[m for m in missing_required],
                missing_optional=missing_optional,
                duplication_rate_proxy=duplication_proxy,
                ordering_confidence=None,
                staleness_risk=None,
                tier0_complete=tier0_complete,
                preflight_passed=preflight_passed,
                stubs_created=stubs_created,
                requested_retrieval_mode=bundle.requested_retrieval_mode,
                retrieval_mode=bundle.retrieval_mode,
                embedding_backend=bundle.embedding_backend,
                routing_active=bundle.routing_active,
                semantic_requirement_met=bundle.semantic_requirement_met,
            )

            semantic_ok = bundle.semantic_requirement_met or self.allow_degraded
            out.preflight_passed = bool(out.preflight_passed and semantic_ok)

            self._emit_telemetry(out)

            if not out.preflight_passed:
                tier0_missing = [m for m in missing_required if "Tier-0" in m]
                if tier0_complete and not bundle.semantic_requirement_met:
                    raise MemoryPreflightError(
                        "HoloIndex semantic retrieval was required but the bundle "
                        f"reported mode={bundle.retrieval_mode!r}, "
                        f"backend={bundle.embedding_backend!r}",
                        missing_files=["Semantic retrieval: unavailable"],
                        module_path=module_path,
                    )
                raise MemoryPreflightError(
                    f"Tier-0 artifacts missing for {module_path}: {tier0_missing}",
                    missing_files=tier0_missing,
                    module_path=module_path
                )

            return out

        # Step 1: Tiered retrieval
        artifacts = self._retrieve_tiered_artifacts(full_module_path, module_path)

        # Step 2: Evaluate quality
        missing_required, missing_optional, duplication_proxy = self._evaluate_quality(artifacts)
        tier0_complete = len([m for m in missing_required if "Tier-0" in m]) == 0

        # Step 3: Auto-stub if needed
        stubs_created = []
        if not tier0_complete and self.autostub_tier0:
            stubs_created = self._create_tier0_stubs(full_module_path, module_path, missing_required)
            # Re-evaluate after stub creation
            artifacts = self._retrieve_tiered_artifacts(full_module_path, module_path)
            missing_required, missing_optional, duplication_proxy = self._evaluate_quality(artifacts)
            tier0_complete = len([m for m in missing_required if "Tier-0" in m]) == 0

        # Step 4: Build bundle
        preflight_passed = tier0_complete or self.allow_degraded

        bundle = MemoryBundle(
            module_path=module_path,
            artifacts=artifacts,
            missing_required=[m for m in missing_required],
            missing_optional=missing_optional,
            duplication_rate_proxy=duplication_proxy,
            ordering_confidence=None,  # v1: not observable
            staleness_risk=None,       # v1: requires git correlation
            tier0_complete=tier0_complete,
            preflight_passed=preflight_passed,
            stubs_created=stubs_created,
            requested_retrieval_mode="filesystem",
            retrieval_mode="filesystem",
            embedding_backend="none",
            routing_active=False,
            semantic_requirement_met=True,
        )

        # Log telemetry
        self._emit_telemetry(bundle)

        # Raise if blocked
        if not preflight_passed:
            tier0_missing = [m for m in missing_required if "Tier-0" in m]
            raise MemoryPreflightError(
                f"Tier-0 artifacts missing for {module_path}: {tier0_missing}",
                missing_files=tier0_missing,
                module_path=module_path
            )

        return bundle

    def _retrieve_via_holo_bundle(self, module_path: str, task: str) -> "MemoryBundle":
        """
        Call `holo_index.py --bundle-json` and translate output into MemoryBundle-like shape.

        This makes HoloIndex the canonical retrieval emitter (WSP_CORE Memory System).
        """
        cmd = [
            sys.executable,
            str(self.project_root / "holo_index.py"),
            "--bundle-json",
            "--search",
            task,
            "--bundle-module-hint",
            module_path,
            "--limit",
            "5",
            "--quiet-root-alerts",
        ]
        requested_mode = _resolve_holo_retrieval_mode(os.environ)
        env = _build_holo_query_env(os.environ, requested_mode)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
        except Exception as exc:
            raise MemoryPreflightError(
                f"HoloIndex bundle call failed: {exc}",
                missing_files=["Tier-0: (unknown)"],
                module_path=module_path,
            )

        stdout = (proc.stdout or "").strip()
        if proc.returncode != 0 or not stdout:
            raise MemoryPreflightError(
                f"HoloIndex bundle call failed (exit={proc.returncode}): {(proc.stderr or '').strip()[:500]}",
                missing_files=["Tier-0: (unknown)"],
                module_path=module_path,
            )

        try:
            payload = json.loads(stdout)
        except Exception as exc:
            raise MemoryPreflightError(
                f"HoloIndex bundle returned non-JSON output: {exc}",
                missing_files=["Tier-0: (unknown)"],
                module_path=module_path,
            )

        retrieval_meta = (payload.get("task_retrieval") or {}).get("metadata") or {}
        retrieval_mode = str(
            retrieval_meta.get("retrieval_mode")
            or retrieval_meta.get("mode")
            or "unknown"
        )
        embedding_backend = str(retrieval_meta.get("embedding_backend") or "unknown")
        routing_active = retrieval_meta.get("routing_active") is True
        semantic_requirement_met = requested_mode != "semantic" or retrieval_mode == "semantic"

        # Translate structured_memory.artifacts → ArtifactInfo list.
        artifacts: List[ArtifactInfo] = []
        structured = payload.get("structured_memory") or {}
        for a in (structured.get("artifacts") or []):
            try:
                tier = int(a.get("tier", 2))
            except Exception:
                tier = 2
            rel = a.get("relative_path") or ""
            abs_path = a.get("path") or ""
            required = bool(a.get("required", False))
            exists = bool(a.get("exists", False))
            artifacts.append(ArtifactInfo(
                path=abs_path,
                relative_path=f"{module_path}/{rel}".replace("\\", "/").replace("//", "/").strip("/"),
                tier=tier,
                required=required,
                exists=exists,
                last_updated=None,
                key_snippets=[],
                why_retrieved=f"bundle-json tier-{tier} {'required' if required else 'optional'}",
            ))

        # If bundle couldn't resolve module, fall back to filesystem tier scan (still blocks Tier-0).
        if not artifacts:
            full_module_path = self.project_root / module_path
            artifacts = self._retrieve_tiered_artifacts(full_module_path, module_path)

        return MemoryBundle(
            module_path=module_path,
            artifacts=artifacts,
            missing_required=[],
            missing_optional=[],
            duplication_rate_proxy=0.0,
            ordering_confidence=None,
            staleness_risk=None,
            tier0_complete=True,
            preflight_passed=True,
            stubs_created=[],
            requested_retrieval_mode=requested_mode,
            retrieval_mode=retrieval_mode,
            embedding_backend=embedding_backend,
            routing_active=routing_active,
            semantic_requirement_met=semantic_requirement_met,
        )

    def _retrieve_tiered_artifacts(
        self,
        full_path: Path,
        relative_path: str
    ) -> List[ArtifactInfo]:
        """Retrieve artifacts by tier priority."""
        artifacts = []

        for tier_num, tier_def in TIER_DEFINITIONS.items():
            # Required artifacts
            for artifact_name in tier_def.required:
                artifact_path = full_path / artifact_name
                exists = artifact_path.exists() or (full_path / artifact_name.rstrip("/")).is_dir()

                last_updated = None
                if exists and artifact_path.is_file():
                    try:
                        mtime = artifact_path.stat().st_mtime
                        last_updated = datetime.fromtimestamp(mtime).isoformat()
                    except Exception:
                        pass

                artifacts.append(ArtifactInfo(
                    path=str(artifact_path),
                    relative_path=f"{relative_path}/{artifact_name}",
                    tier=tier_num,
                    required=True,
                    exists=exists,
                    last_updated=last_updated,
                    why_retrieved=f"Tier-{tier_num} required: {tier_def.purpose}",
                ))

            # Optional artifacts
            for artifact_name in tier_def.optional:
                artifact_path = full_path / artifact_name
                is_dir = artifact_name.endswith("/")
                exists = (
                    (full_path / artifact_name.rstrip("/")).is_dir() if is_dir
                    else artifact_path.exists()
                )

                last_updated = None
                if exists and not is_dir and artifact_path.is_file():
                    try:
                        mtime = artifact_path.stat().st_mtime
                        last_updated = datetime.fromtimestamp(mtime).isoformat()
                    except Exception:
                        pass

                artifacts.append(ArtifactInfo(
                    path=str(artifact_path),
                    relative_path=f"{relative_path}/{artifact_name}",
                    tier=tier_num,
                    required=False,
                    exists=exists,
                    last_updated=last_updated,
                    why_retrieved=f"Tier-{tier_num} optional: {tier_def.purpose}",
                ))

        return artifacts

    def _evaluate_quality(
        self,
        artifacts: List[ArtifactInfo]
    ) -> Tuple[List[str], List[str], float]:
        """
        Evaluate retrieval quality per WSP_CORE Retrieval Quality Metrics.

        Returns:
            Tuple of (missing_required, missing_optional, duplication_rate_proxy)
        """
        missing_required = []
        missing_optional = []
        paths_seen = set()
        duplicate_count = 0

        for artifact in artifacts:
            if not artifact.exists:
                label = f"Tier-{artifact.tier}: {artifact.relative_path}"
                if artifact.required:
                    missing_required.append(label)
                else:
                    missing_optional.append(label)

            # Track duplication (simple path-based proxy)
            if artifact.path in paths_seen:
                duplicate_count += 1
            paths_seen.add(artifact.path)

        total = len(artifacts)
        duplication_proxy = duplicate_count / total if total > 0 else 0.0

        return missing_required, missing_optional, round(duplication_proxy, 3)

    def _create_tier0_stubs(
        self,
        full_path: Path,
        relative_path: str,
        missing_required: List[str]
    ) -> List[str]:
        """
        Create machine-first stubs for missing Tier-0 artifacts.

        Uses simple file writes (not PatchExecutor) for stub creation
        since these are new files, not patches to existing code.

        Args:
            full_path: Absolute path to module
            relative_path: Relative module path
            missing_required: List of missing required artifacts

        Returns:
            List of created stub file paths
        """
        stubs_created = []
        module_name = relative_path.split("/")[-1] if "/" in relative_path else relative_path
        module_import_path = relative_path.replace("/", ".").replace("\\", ".")

        # Ensure module directory exists
        full_path.mkdir(parents=True, exist_ok=True)

        for missing in missing_required:
            if "README.md" in missing:
                readme_path = full_path / "README.md"
                if not readme_path.exists():
                    content = README_STUB_TEMPLATE.format(
                        module_name=module_name,
                        module_import_path=module_import_path
                    )
                    readme_path.write_text(content, encoding="utf-8")
                    stubs_created.append(str(readme_path))
                    logger.info(f"[MEMORY-PREFLIGHT] Created stub: {readme_path}")

            if "INTERFACE.md" in missing:
                interface_path = full_path / "INTERFACE.md"
                if not interface_path.exists():
                    content = INTERFACE_STUB_TEMPLATE.format(
                        module_name=module_name
                    )
                    interface_path.write_text(content, encoding="utf-8")
                    stubs_created.append(str(interface_path))
                    logger.info(f"[MEMORY-PREFLIGHT] Created stub: {interface_path}")

        return stubs_created

    def _emit_telemetry(self, bundle: MemoryBundle) -> None:
        """Emit structured telemetry for AI_Overseer and monitoring."""
        telemetry = {
            "event": "memory_preflight_complete",
            "timestamp": datetime.now().isoformat(),
            "module_path": bundle.module_path,
            "tier0_complete": bundle.tier0_complete,
            "preflight_passed": bundle.preflight_passed,
            "missing_required_count": len(bundle.missing_required),
            "missing_optional_count": len(bundle.missing_optional),
            "stubs_created": bundle.stubs_created,
            "duplication_rate_proxy": bundle.duplication_rate_proxy,
            "requested_retrieval_mode": bundle.requested_retrieval_mode,
            "retrieval_mode": bundle.retrieval_mode,
            "embedding_backend": bundle.embedding_backend,
            "routing_active": bundle.routing_active,
            "semantic_requirement_met": bundle.semantic_requirement_met,
        }

        # Log as JSON for machine parsing
        logger.info(f"[MEMORY-PREFLIGHT-TELEMETRY] {json.dumps(telemetry)}")

        # If stubs were created, emit special signal
        if bundle.stubs_created:
            stub_signal = {
                "event": "memory_preflight_stub_created",
                "module_path": bundle.module_path,
                "files_created": bundle.stubs_created,
            }
            logger.info(f"[MEMORY-PREFLIGHT-SIGNAL] {json.dumps(stub_signal)}")

    def _create_passthrough_bundle(self, module_path: str) -> MemoryBundle:
        """Create a passthrough bundle when preflight is disabled."""
        return MemoryBundle(
            module_path=module_path,
            artifacts=[],
            missing_required=[],
            missing_optional=[],
            duplication_rate_proxy=0.0,
            ordering_confidence=None,
            staleness_risk=None,
            tier0_complete=True,
            preflight_passed=True,
            stubs_created=[],
            requested_retrieval_mode="disabled",
            retrieval_mode="disabled",
            embedding_backend="none",
            routing_active=False,
            semantic_requirement_met=True,
        )


# =============================================================================
# WRE HARD GATE DECORATOR
# =============================================================================

def require_memory_preflight(func):
    """
    Decorator to enforce memory preflight before code-changing operations.

    Usage:
        @require_memory_preflight
        async def route_operation(self, dae_name: str, objective: str, **kwargs):
            ...

    The decorated function must have 'module_path' in kwargs or be determinable
    from the operation context.
    """
    import functools
    import asyncio

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        module_path = kwargs.get("module_path") or kwargs.get("context", {}).get("module_path")

        if module_path:
            guard = MemoryPreflightGuard()
            try:
                bundle = guard.run_preflight(module_path)
                kwargs["_memory_bundle"] = bundle
            except MemoryPreflightError as e:
                logger.error(f"[WRE-GATE] Memory preflight BLOCKED: {e}")
                return {
                    "status": "blocked",
                    "reason": "memory_preflight_failed",
                    "missing_files": e.missing_files,
                    "module": e.module_path,
                    "required_action": e.required_action,
                }

        return await func(*args, **kwargs)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        module_path = kwargs.get("module_path") or kwargs.get("context", {}).get("module_path")

        if module_path:
            guard = MemoryPreflightGuard()
            try:
                bundle = guard.run_preflight(module_path)
                kwargs["_memory_bundle"] = bundle
            except MemoryPreflightError as e:
                logger.error(f"[WRE-GATE] Memory preflight BLOCKED: {e}")
                return {
                    "status": "blocked",
                    "reason": "memory_preflight_failed",
                    "missing_files": e.missing_files,
                    "module": e.module_path,
                    "required_action": e.required_action,
                }

        return func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def check_memory_preflight(module_path: str, project_root: Optional[Path] = None) -> MemoryBundle:
    """
    Convenience function to run memory preflight check.

    Args:
        module_path: Relative path to module
        project_root: Optional project root override

    Returns:
        MemoryBundle with preflight results
    """
    guard = MemoryPreflightGuard(project_root)
    return guard.run_preflight(module_path)


# =============================================================================
# CLI / SMOKE TEST
# =============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Memory Preflight Guard Smoke Test")
    parser.add_argument("module_path", help="Module path to check (e.g., modules/communication/livechat)")
    parser.add_argument("--autostub", action="store_true", help="Enable auto-stub creation")
    parser.add_argument("--allow-degraded", action="store_true", help="Allow proceed with missing artifacts")
    args = parser.parse_args()

    # Set env vars from args
    if args.autostub:
        os.environ["WRE_MEMORY_AUTOSTUB_TIER0"] = "true"
    if args.allow_degraded:
        os.environ["WRE_MEMORY_ALLOW_DEGRADED"] = "true"

    print("=" * 60)
    print("MEMORY PREFLIGHT GUARD - SMOKE TEST")
    print("=" * 60)

    try:
        bundle = check_memory_preflight(args.module_path)

        print(f"\nModule: {bundle.module_path}")
        print(f"Tier-0 Complete: {bundle.tier0_complete}")
        print(f"Preflight Passed: {bundle.preflight_passed}")
        print(f"Missing Required: {bundle.missing_required}")
        print(f"Stubs Created: {bundle.stubs_created}")
        print(f"Duplication Proxy: {bundle.duplication_rate_proxy}")

        print("\n--- ARTIFACTS ---")
        for artifact in bundle.artifacts:
            status = "[OK]" if artifact.exists else "[MISSING]"
            req = "(REQ)" if artifact.required else ""
            print(f"  Tier-{artifact.tier} {status} {req} {artifact.relative_path}")

        print("\n--- BUNDLE SUMMARY (JSON) ---")
        print(json.dumps(bundle.to_dict(), indent=2)[:500] + "...")

    except MemoryPreflightError as e:
        print(f"\n[BLOCKED] {e}")
        print(f"  Missing: {e.missing_files}")
        print(f"  Module: {e.module_path}")
        print(f"  Action: {e.required_action}")
        sys.exit(1)
