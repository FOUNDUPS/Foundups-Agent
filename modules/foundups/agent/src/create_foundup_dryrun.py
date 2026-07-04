#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_foundup dry-run scaffold planner (FOUNDUP_CREATE_ACTION_DRYRUN_PHASE1).

Maps a GATE_PASSED FoundUpGenesisEnvelope to a FoundUpScaffoldContract and returns
a DRY-RUN scaffold PLAN. It writes NOTHING. This is the create_foundup action's
dry-run precursor to a future valve-gated writer (FOUNDUP_SCAFFOLD_WRITER_*).

Contract: docs/audits/architecture/FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md

Boundary (fail closed):
    - NO file write, NO registry write, NO Hermes real-write path, NO worktree.
    - `create_foundup` is DISTINCT from build_foundup/extract_foundup (no alias;
      this planner produces a NEW-scaffold plan, never an extraction).
    - fail-closed: the envelope MUST re-validate (GATE_PASSED-equivalent) and the
      foundup_id MUST NOT already exist in the registry.

NAVIGATION:
    -> Uses (lazy): ai_overseer.foundup_genesis.envelope + validator (re-validate)
    -> Reads (read-only): modules/foundups/foundup_registry.json for the existence check
    -> Does NOT import Hermes/FAM/launch/consumer (AST-guarded by tests).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

CREATE_ACTION = "create_foundup"
REQUIRED_VALVE_STATE = "VALVE_OPEN_WORKTREE_CREATE"
WRITE_OWNER = "hermes"

# Mirrors foundup_manifest_validator.REQUIRED_GATES (declarative parity).
_REQUIRED_GATES: List[str] = [
    "genesis_gate",
    "manifest_gate",
    "dry_run_gate",
    "test_gate",
    "destructive_action_guard_d0_d6",
    "typed_exec_boundary",
    "no_live_launch",
    "policy_required_sovereign_valve_for_non_dry_run",
]
_FORBIDDEN_PATHS: List[str] = [".env", "main.py", "**/*_dae.py", "vendor"]


@dataclass
class CreateFoundUpPlanResult:
    """Return-value-only dry-run plan. No side effect produced it."""

    action: str
    ok: bool
    rejection_code: Optional[str]
    rejection_reason: Optional[str]
    scaffold_contract: Optional[Dict[str, Any]]
    planned_artifacts: List[str]
    planned_manifest: Optional[Dict[str, Any]]
    planned_registry_seed: Optional[Dict[str, Any]]
    dry_run: bool = True
    files_written: List[str] = field(default_factory=list)
    fam_called: bool = False
    hermes_called: bool = False
    registry_mutated: bool = False
    worktree_created: bool = False
    valve_state_required: str = REQUIRED_VALVE_STATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "ok": self.ok,
            "rejection_code": self.rejection_code,
            "rejection_reason": self.rejection_reason,
            "scaffold_contract": self.scaffold_contract,
            "planned_artifacts": self.planned_artifacts,
            "planned_manifest": self.planned_manifest,
            "planned_registry_seed": self.planned_registry_seed,
            "dry_run": self.dry_run,
            "files_written": self.files_written,
            "fam_called": self.fam_called,
            "hermes_called": self.hermes_called,
            "registry_mutated": self.registry_mutated,
            "worktree_created": self.worktree_created,
            "valve_state_required": self.valve_state_required,
        }


def is_create_action(action: str) -> bool:
    """True iff action is the create_foundup action string."""
    return action == CREATE_ACTION


def create_action_is_not_aliased() -> bool:
    """Invariant: create_foundup is NOT an existing-module (build/extract) action.

    This is the contract's no-alias guarantee expressed as a checkable invariant
    against the job contract's own taxonomy.
    """
    from modules.communication.moltbot_bridge.src.foundup_job_contract import (
        CANONICAL_ACTIONS,
        EXISTING_MODULE_ACTIONS,
    )

    return CREATE_ACTION in CANONICAL_ACTIONS and CREATE_ACTION not in EXISTING_MODULE_ACTIONS


def _digest(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _wsp49_artifacts(module_path: str, foundup_id: str) -> List[str]:
    """The WSP-49 (+WSP 11/12/22/60 + Hermes REQUIRED_CONTRACTS) artifact set."""
    return [
        f"{module_path}/__init__.py",
        f"{module_path}/README.md",
        f"{module_path}/INTERFACE.md",
        f"{module_path}/ROADMAP.md",
        f"{module_path}/ModLog.md",
        f"{module_path}/requirements.txt",
        f"{module_path}/src/__init__.py",
        f"{module_path}/src/{foundup_id}.py",
        f"{module_path}/tests/__init__.py",
        f"{module_path}/tests/README.md",
        f"{module_path}/tests/TestModLog.md",
        f"{module_path}/tests/test_{foundup_id}.py",
        f"{module_path}/memory/README.md",
        f"{module_path}/foundup_manifest.json",
    ]


def _planned_manifest(foundup_id: str, module_path: str) -> Dict[str, Any]:
    """A foundup_manifest.json that satisfies foundup_manifest_validator (no promo)."""
    return {
        "foundup_id": foundup_id,
        "build_contract": {
            "foundup_id": foundup_id,
            "module_path": module_path,
            "status": "BASELINE_DECLARATIVE_ONLY",
            "build": {"command": None},
            "test": {"command": ["python", "-m", "pytest", f"{module_path}/tests"]},
            "dry_run": {"command": None, "default": True, "required": True},
            "forbidden_paths": list(_FORBIDDEN_PATHS),
            "required_gates": list(_REQUIRED_GATES),
            "readiness": {
                "build_ready": False,
                "autonomous_execution_ready": False,
                "manifest_ready": False,
            },
            "safe_mutation_surface": [f"{module_path}/**"],
            "evidence_output": f"{module_path}/tests",
        },
        "execution_routing": {
            "orchestrator": "openclaw",
            "executor": "hermes",
            "auditor": "ai_overseer",
            "external_agent_allowed": False,
            "declarative_only": True,
            "can_self_authorize": False,
            "wre_coordinator": "wre",
            "external_agent_contract_required": True,
            "build_plan_source": "build_plan_generator",
            "job_contract_source": "foundup_job_contract",
        },
    }


def _registry_seed(foundup_id: str, display_name: str, module_path: str) -> Dict[str, Any]:
    """The entities[] seed entry for a NEW FoundUp at genesis (specified, NOT written)."""
    return {
        "foundup_id": foundup_id,
        "display_name": display_name,
        "entity_type": "foundup",
        "module_path": module_path,
        "stage": "incubating",
        "tier": "F0_DAE",
        "implementation_status": "SPECIFIED",
        "poc_status": "idea",
        "manifest_status": "exists",
        "manifest_path": f"{module_path}/foundup_manifest.json",
        "hermes_openclaw_build_status": "scaffold",
        "token_status": "TOKEN_DEFERRED",
        "next_slice": f"{foundup_id.upper()}_POC_PHASE1",
    }


def _revalidate_envelope(envelope: Dict[str, Any]):
    """Re-validate the envelope via the ai_overseer genesis validator (fail-closed).

    Returns (is_valid, errors, parsed_envelope). Never trusts a caller-supplied
    'gate passed' claim -- it re-runs the real strict validator.
    """
    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.envelope import (
        FoundUpGenesisEnvelope,
    )
    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.validator import (
        validate_genesis_envelope,
    )

    parsed = FoundUpGenesisEnvelope.from_dict(envelope)
    result = validate_genesis_envelope(parsed, strict_mode=True)
    return result.is_valid, list(result.errors), parsed


def _foundup_id_exists(foundup_id: str, registry_path: Optional[Path]) -> bool:
    """Read-only registry existence check. Missing registry -> treated as 'no ids'.

    Reads ``foundup_registry.json`` directly (same ``entities[].foundup_id`` shape
    the read-only ``foundup_registry_loader`` validates). We do NOT import the
    loader here because ``modules/foundups/src/__init__`` eagerly imports a missing
    ``platform_manager`` and would break this import; a direct read is dependency-free
    and equally read-only. (Residual: the loader-import blocker is out of scope.)
    """
    path = registry_path
    if path is None:
        # Default production registry: modules/foundups/foundup_registry.json
        path = Path(__file__).resolve().parents[2] / "foundup_registry.json"
    path = Path(path)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    entities = data.get("entities", []) if isinstance(data, dict) else []
    return any(
        isinstance(e, dict) and e.get("foundup_id") == foundup_id for e in entities
    )


def plan_create_foundup_dry_run(
    envelope: Dict[str, Any],
    *,
    actor_id: str = "0102",
    registry_path: Optional[Path] = None,
) -> CreateFoundUpPlanResult:
    """Plan (dry-run) the scaffold for a NEW FoundUp from a genesis envelope.

    Writes nothing. Returns a CreateFoundUpPlanResult with the FoundUpScaffoldContract,
    the planned WSP-49 artifacts, planned manifest, and planned registry seed -- or a
    fail-closed rejection.

    Args:
        envelope: a FoundUpGenesisEnvelope dict (e.g. from the WSP 109 intake builder).
        actor_id: who is requesting creation (telemetry only).
        registry_path: optional registry path (defaults to production, read-only).
    """
    def _reject(code: str, reason: str) -> CreateFoundUpPlanResult:
        return CreateFoundUpPlanResult(
            action=CREATE_ACTION,
            ok=False,
            rejection_code=code,
            rejection_reason=reason[:300],
            scaffold_contract=None,
            planned_artifacts=[],
            planned_manifest=None,
            planned_registry_seed=None,
        )

    is_valid, errors, parsed = _revalidate_envelope(envelope or {})
    if not is_valid:
        return _reject(
            "FAIL_ENVELOPE_NOT_GATE_PASSED",
            "envelope did not pass genesis validation: " + "; ".join(errors),
        )

    foundup_id = parsed.foundup_id
    if _foundup_id_exists(foundup_id, registry_path):
        return _reject(
            "FAIL_FOUNDUP_ID_EXISTS",
            "foundup_id already exists in registry; create_foundup authors a NEW "
            "scaffold and must not update/extract an existing FoundUp",
        )

    module_path = f"modules/foundups/{foundup_id}"
    artifacts = _wsp49_artifacts(module_path, foundup_id)
    manifest = _planned_manifest(foundup_id, module_path)
    seed = _registry_seed(foundup_id, parsed.name, module_path)

    contract = {
        "foundup_id": foundup_id,
        "display_name": parsed.name,
        "entity_type": "foundup",
        "module_path": module_path,
        "source_intake_packet_digest": _digest(envelope),
        "genesis_envelope_digest": _digest(parsed.to_dict()),
        "scaffold_artifacts": artifacts,
        "manifest_fields": manifest,
        "registry_seed": seed,
        "allowed_paths": [f"{module_path}/**"],
        "denied_paths": list(_FORBIDDEN_PATHS),
        "write_owner": WRITE_OWNER,
        "required_valve_state": REQUIRED_VALVE_STATE,
        "rollback_plan": (
            f"remove worktree + delete {module_path}; no registry write occurred "
            "(seed is planned only)"
        ),
        "validation_commands": [["python", "-m", "pytest", f"{module_path}/tests"]],
        "receipt_chain": [],
    }

    return CreateFoundUpPlanResult(
        action=CREATE_ACTION,
        ok=True,
        rejection_code=None,
        rejection_reason=None,
        scaffold_contract=contract,
        planned_artifacts=artifacts,
        planned_manifest=manifest,
        planned_registry_seed=seed,
    )
