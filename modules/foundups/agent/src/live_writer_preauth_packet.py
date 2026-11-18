#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live-writer preauthorization packet (FOUNDUP_LIVE_WRITER_PREAUTH_PACKET_PHASE1).

GENERIC layer (NOT pAccess-specific, NOT the live writer). Given a FoundUp idea /
foundup_id / foundup_name / module_path, it chains the already-landed dry-run
stack and emits a reusable LiveWriterPreauthPacket proving that every prerequisite
for REQUESTING VALVE_OPEN_WORKTREE_CREATE is satisfied -- without opening the
valve, writing the real repo, mutating the registry, or creating a branch/PR.

Generic flow (all dry-run / read-only):
    1. Build the WSP 109 intake packet + FoundUpGenesisEnvelope (P1 builder).
    2. Verify the OpenClaw genesis gate reaches GATE_PASSED.
    3. Verify foundup_id does NOT already exist in foundup_registry.json.
    4. Generate the create_foundup dry-run scaffold plan.
    5. Verify the scaffold writer dry-run materializes the EXACT planned artifacts
       in a sandbox.
    6. Emit the LiveWriterPreauthPacket (digests + fail-closed capability flags).

Boundary (fail closed):
    - NEVER opens the valve, writes a real-repo scaffold, mutates the registry,
      creates a branch/PR/worktree, or claims merge/secret/route/payment authority.
    - NO subprocess / git / gh / worktree / PR / merge calls (AST-guarded).
    - Any forbidden capability flag set True -> refused packet.

Contract: docs/audits/architecture/FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REQUESTED_OPERATION = "create_foundup"
REQUIRED_VALVE_STATE = "VALVE_OPEN_WORKTREE_CREATE"
_FOUNDUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,49}$")  # WSP 104


@dataclass
class LiveWriterPreauthPacket:
    """Return-value-only preauthorization proof. Producing it performs no live write."""

    packet_id: str
    foundup_id: str
    foundup_name: str
    module_path: str
    base_branch: str
    target_branch: str
    requested_operation: str
    requested_valve_state: str

    intake_packet_digest: Optional[str] = None
    genesis_envelope_digest: Optional[str] = None
    gate_receipt_digest: Optional[str] = None
    registry_nonexistence_receipt_digest: Optional[str] = None
    scaffold_plan_digest: Optional[str] = None
    dryrun_writer_receipt_digest: Optional[str] = None

    planned_artifacts_count: int = 0
    planned_artifacts: List[str] = field(default_factory=list)
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)

    # Fail-closed capability flags -- a preauth packet may NEVER claim these.
    registry_write: bool = False
    merge_authority: bool = False
    draft_pr_only: bool = True
    secrets_access: bool = False
    public_route_mutation: bool = False
    api_route_mutation: bool = False
    cloudflare_access: bool = False
    payment_rail_access: bool = False

    receipts: List[Dict[str, Any]] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)

    # Derived readiness (True iff no rejection_reasons). Not a grant -- it only
    # attests the prerequisites for REQUESTING the valve are present.
    preauth_ready: bool = False

    no_live_write_performed: bool = True
    no_registry_mutation_performed: bool = True
    no_branch_created: bool = True
    no_pr_created: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "foundup_id": self.foundup_id,
            "foundup_name": self.foundup_name,
            "module_path": self.module_path,
            "base_branch": self.base_branch,
            "target_branch": self.target_branch,
            "requested_operation": self.requested_operation,
            "requested_valve_state": self.requested_valve_state,
            "intake_packet_digest": self.intake_packet_digest,
            "genesis_envelope_digest": self.genesis_envelope_digest,
            "gate_receipt_digest": self.gate_receipt_digest,
            "registry_nonexistence_receipt_digest": self.registry_nonexistence_receipt_digest,
            "scaffold_plan_digest": self.scaffold_plan_digest,
            "dryrun_writer_receipt_digest": self.dryrun_writer_receipt_digest,
            "planned_artifacts_count": self.planned_artifacts_count,
            "planned_artifacts": self.planned_artifacts,
            "allowed_paths": self.allowed_paths,
            "denied_paths": self.denied_paths,
            "registry_write": self.registry_write,
            "merge_authority": self.merge_authority,
            "draft_pr_only": self.draft_pr_only,
            "secrets_access": self.secrets_access,
            "public_route_mutation": self.public_route_mutation,
            "api_route_mutation": self.api_route_mutation,
            "cloudflare_access": self.cloudflare_access,
            "payment_rail_access": self.payment_rail_access,
            "receipts": self.receipts,
            "rejection_reasons": self.rejection_reasons,
            "preauth_ready": self.preauth_ready,
            "no_live_write_performed": self.no_live_write_performed,
            "no_registry_mutation_performed": self.no_registry_mutation_performed,
            "no_branch_created": self.no_branch_created,
            "no_pr_created": self.no_pr_created,
        }


def _digest(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _sanitize_line(value: str) -> str:
    """Collapse ALL whitespace (incl. newlines/tabs) to single spaces so a free-text
    value cannot inject additional 'key: value' intake lines (anti line-injection)."""
    return " ".join(str(value).split())


def _intake_text(idea: str, foundup_id: str, foundup_name: str, category: str) -> str:
    """Deterministic structured WSP-109 intake text from the generic inputs.

    Every free-text value is sanitized to a SINGLE line so it cannot inject extra
    structured fields (e.g. a second ``foundup_id:`` line that last-write-wins would
    resolve to an attacker-chosen id). ``foundup_id`` itself is already regex-validated
    to contain no whitespace.
    """
    idea_s = _sanitize_line(idea)
    name_s = _sanitize_line(foundup_name)
    cat_s = _sanitize_line(category)
    return "\n".join([
        f"name: {name_s}",
        f"foundup_id: {foundup_id}",
        f"tagline: {idea_s[:80]}",
        f"description: {idea_s}",
        f"category: {cat_s}",
        "lifecycle_stage: idea",
        "binding_state: unbound",
        (
            f"acceptance: {name_s} scaffold materializes | pytest | "
            "14 WSP-49 artifacts in sandbox | dry_run writer ok"
        ),
    ])


def build_live_writer_preauth_packet(
    *,
    idea: str,
    foundup_id: str,
    foundup_name: str,
    module_path: str,
    target_branch: str,
    base_branch: str = "main",
    requested_operation: str = REQUESTED_OPERATION,
    requested_valve_state: str = REQUIRED_VALVE_STATE,
    category: str = "tools",
    registry_write: bool = False,
    merge_authority: bool = False,
    secrets_access: bool = False,
    public_route_mutation: bool = False,
    api_route_mutation: bool = False,
    cloudflare_access: bool = False,
    payment_rail_access: bool = False,
    registry_path: Optional[Path] = None,
    sandbox_root: Optional[Path] = None,
) -> LiveWriterPreauthPacket:
    """Build a LiveWriterPreauthPacket for a FoundUp. Dry-run / read-only only.

    Returns a packet with ``preauth_ready=True`` and every digest populated when all
    prerequisites pass, or a refused packet (``preauth_ready=False`` +
    ``rejection_reasons``) otherwise. It NEVER opens the valve or writes the repo.
    """
    module_path_norm = str(module_path).replace("\\", "/").rstrip("/")
    packet = LiveWriterPreauthPacket(
        packet_id="",
        foundup_id=foundup_id,
        foundup_name=foundup_name,
        module_path=module_path_norm,
        base_branch=base_branch,
        target_branch=target_branch,
        requested_operation=requested_operation,
        requested_valve_state=requested_valve_state,
        registry_write=bool(registry_write),
        merge_authority=bool(merge_authority),
        secrets_access=bool(secrets_access),
        public_route_mutation=bool(public_route_mutation),
        api_route_mutation=bool(api_route_mutation),
        cloudflare_access=bool(cloudflare_access),
        payment_rail_access=bool(payment_rail_access),
    )

    def _finish(reason: Optional[str] = None) -> LiveWriterPreauthPacket:
        if reason:
            packet.rejection_reasons.append(reason)
        packet.preauth_ready = not packet.rejection_reasons
        packet.packet_id = "preauth_" + hashlib.sha256(
            _digest({
                "foundup_id": packet.foundup_id,
                "module_path": packet.module_path,
                "scaffold_plan_digest": packet.scaffold_plan_digest,
                "ready": packet.preauth_ready,
            }).encode("utf-8")
        ).hexdigest()[:16]
        return packet

    # Guard A: no forbidden capability may be claimed by a preauth packet.
    for name, val in (
        ("registry_write", registry_write),
        ("merge_authority", merge_authority),
        ("secrets_access", secrets_access),
        ("public_route_mutation", public_route_mutation),
        ("api_route_mutation", api_route_mutation),
        ("cloudflare_access", cloudflare_access),
        ("payment_rail_access", payment_rail_access),
    ):
        if val:
            return _finish(f"FAIL_FORBIDDEN_CAPABILITY:{name}")

    # Guard B: operation + valve state must be exactly the sanctioned request.
    if requested_operation != REQUESTED_OPERATION:
        return _finish("FAIL_INVALID_OPERATION")
    if requested_valve_state != REQUIRED_VALVE_STATE:
        return _finish("FAIL_INVALID_VALVE_STATE")

    # Guard C: foundup_id + module_path pinned (no traversal / injection).
    if not _FOUNDUP_ID_RE.match(foundup_id):
        return _finish("FAIL_INVALID_FOUNDUP_ID")
    if module_path_norm != f"modules/foundups/{foundup_id}":
        return _finish("FAIL_INVALID_MODULE_PATH")

    # Step 1-2: build WSP-109 intake packet + envelope and run the OpenClaw gate.
    from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_packet_builder import (
        build_intake_packet_dry_run,
    )

    intake = build_intake_packet_dry_run(
        _intake_text(idea, foundup_id, foundup_name, category), actor_id="0102"
    )
    if intake.envelope is not None:
        packet.intake_packet_digest = _digest(intake.envelope)
        packet.genesis_envelope_digest = _digest(intake.envelope)
    packet.gate_receipt_digest = _digest(intake.gate_result)
    packet.receipts.append({
        "step": "genesis_gate", "digest": packet.gate_receipt_digest,
        "gate_reason": intake.gate_reason,
    })

    # Step 3: gate must be GATE_PASSED.
    if not intake.gate_passed or intake.gate_reason != "GATE_PASSED":
        return _finish(f"FAIL_GATE_NOT_PASSED:{intake.gate_reason}")

    # Anti-injection binding: the envelope's derived foundup_id MUST equal the
    # Guard-C-validated, registry-checked argument id. This defeats a free-text
    # `idea`/`foundup_name` that smuggles a second foundup_id into the intake.
    if (intake.envelope or {}).get("foundup_id") != foundup_id:
        return _finish("FAIL_ENVELOPE_ID_MISMATCH")

    # Step 4: registry non-existence (read-only).
    from modules.foundups.agent.src.create_foundup_dryrun import _foundup_id_exists

    exists = _foundup_id_exists(foundup_id, registry_path)
    registry_receipt = {
        "registry_checked": True,
        "foundup_id": foundup_id,
        "present": bool(exists),
    }
    packet.registry_nonexistence_receipt_digest = _digest(registry_receipt)
    packet.receipts.append({
        "step": "registry_nonexistence",
        "digest": packet.registry_nonexistence_receipt_digest,
        "present": bool(exists),
    })
    if exists:
        return _finish("FAIL_FOUNDUP_ID_EXISTS")

    # Step 5: create_foundup dry-run scaffold plan.
    from modules.foundups.agent.src.create_foundup_dryrun import plan_create_foundup_dry_run

    plan = plan_create_foundup_dry_run(intake.envelope, registry_path=registry_path)
    if not plan.ok or not plan.scaffold_contract:
        return _finish(f"FAIL_PLAN_REJECTED:{plan.rejection_code}")
    contract = plan.scaffold_contract
    # Anti-injection binding: the plan's module_path MUST equal the validated argument
    # module_path (the actual authorized write surface can never diverge from the header).
    if str(contract.get("module_path")) != module_path_norm:
        return _finish("FAIL_PLAN_MODULE_PATH_MISMATCH")
    packet.scaffold_plan_digest = _digest(contract)
    packet.planned_artifacts = list(contract.get("scaffold_artifacts", []))
    packet.planned_artifacts_count = len(packet.planned_artifacts)
    packet.allowed_paths = list(contract.get("allowed_paths", []))
    packet.denied_paths = list(contract.get("denied_paths", []))
    packet.receipts.append({
        "step": "create_foundup_plan", "digest": packet.scaffold_plan_digest,
        "artifacts": packet.planned_artifacts_count,
    })

    # Step 6: scaffold writer dry-run materializes the EXACT planned artifacts in a
    # sandbox (isolated temp dir; cleaned up). Proves the plan is materializable.
    from modules.foundups.agent.src.scaffold_writer_dryrun import materialize_scaffold_dry_run

    owns_sandbox = sandbox_root is None
    sandbox = Path(sandbox_root) if sandbox_root is not None else Path(tempfile.mkdtemp(prefix="preauth_sandbox_"))
    try:
        writer = materialize_scaffold_dry_run(contract, output_root=sandbox)
        writer_receipt = {
            "ok": writer.ok,
            "matches_plan": writer.matches_plan,
            "files_written": len(writer.files_written),
            "rejection_code": writer.rejection_code,
            "registry_mutated": writer.registry_mutated,
            "wrote_to_main_repo": writer.wrote_to_main_repo,
            "worktree_created": writer.worktree_created,
        }
        packet.dryrun_writer_receipt_digest = _digest(writer_receipt)
        packet.receipts.append({
            "step": "scaffold_writer_dryrun",
            "digest": packet.dryrun_writer_receipt_digest,
            "files_written": len(writer.files_written),
        })
        if not writer.ok:
            return _finish(f"FAIL_DRYRUN_WRITER_REJECTED:{writer.rejection_code}")
        # The gate ENFORCES (not just records) the writer's no-side-effect attestation:
        # a writer that reports any real-repo/registry/worktree side effect is refused.
        if writer.registry_mutated or writer.wrote_to_main_repo or writer.worktree_created:
            return _finish("FAIL_DRYRUN_WRITER_SIDE_EFFECT")
        if not writer.matches_plan or len(writer.files_written) != packet.planned_artifacts_count:
            return _finish("FAIL_PLAN_ARTIFACT_MISMATCH")
        # Bind the no-* attestations to the writer's own enforced receipt (not static
        # claims). branch/PR are never touched by this module -> remain True.
        packet.no_live_write_performed = not writer.wrote_to_main_repo
        packet.no_registry_mutation_performed = not writer.registry_mutated
    finally:
        if owns_sandbox:
            shutil.rmtree(sandbox, ignore_errors=True)

    # All prerequisites satisfied -> ready packet.
    return _finish(None)
