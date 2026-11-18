"""Resident RedDog queue binding profile helpers.

Slice: REDDOG_RESIDENT_QUEUE_BINDING_PROFILE_PHASE1

The base profile defaults derivation/request-binding controls and safe
control-plane loop flags. The fusion profile additionally selects the existing
`foundups_fusion` artifact generator mode. The worktree profile additionally
selects the existing isolated worktree runner. The draft-PR profile
additionally selects the existing independent evidence runner and verified
draft-PR runner. The PatternMemory profile additionally selects the existing
verified PatternMemory admission sink. No profile enables shell execution,
reward settlement, merge authority, or HoloIndex re-indexing.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


ENV_REDDOG_RESIDENT_QUEUE_BINDING_PROFILE = "REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"
PROFILE_SIGNED_0102_BOUNDED_CODE = "signed_0102_bounded_code"
PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION = "signed_0102_bounded_code_fusion"
PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE = "signed_0102_bounded_code_fusion_worktree"
PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR = (
    "signed_0102_bounded_code_fusion_worktree_draft_pr"
)
PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY = (
    "signed_0102_bounded_code_fusion_worktree_draft_pr_pattern_memory"
)
RESIDENT_QUEUE_PROFILES = frozenset(
    {
        PROFILE_SIGNED_0102_BOUNDED_CODE,
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION,
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR,
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    }
)

_DRAFT_PR_OR_HIGHER_PROFILES = frozenset(
    {
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR,
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
    }
)
_WORKTREE_OR_HIGHER_PROFILES = frozenset(
    {
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE,
        *_DRAFT_PR_OR_HIGHER_PROFILES,
    }
)
_FUSION_OR_HIGHER_PROFILES = frozenset(
    {
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION,
        *_WORKTREE_OR_HIGHER_PROFILES,
    }
)

PROFILE_BINDING_FLAGS = frozenset(
    {
        "REDDOG_PILOT_DRYRUN_BINDING",
        "REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING",
        "REDDOG_SLICE_VERIFIER_REQUEST_BINDING",
        "REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING",
        "REDDOG_OUTCOME_RATCHET_REQUEST_BINDING",
        "REDDOG_HELD_OUT_GATE_REQUEST_BINDING",
        "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING",
    }
)

PROFILE_RUNTIME_FLAGS = frozenset(
    {
        "REDDOG_WORK_STATE_SOURCE_RECORD_SUPPLY",
        "REDDOG_WORK_LEDGER_SOURCE_PROJECTION_SUPPLY",
        "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM",
        "REDDOG_MODEL_SELECTION_ARTIFACT_SUPPLY",
        "REDDOG_GITHUB_PRINCIPAL_PERMISSION_SNAPSHOT_SUPPLY",
        "REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY",
        "REDDOG_AUTHORITY_PROFILE_SOURCE_ARTIFACT_SUPPLY",
        "REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY",
        "REDDOG_SIGNER_SOCKET_PROFILE_BINDING",
        "REDDOG_WORKER_DISPATCH_AGENTDB_WRITER",
        "OPENCLAW_SIGNED_WORKER_TASKS_ENABLED",
        "OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED",
        "OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED",
        "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP",
        "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER",
        "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP",
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP",
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE",
    }
)

PROFILE_RUNTIME_PATH_FILENAMES = {
    "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "authoritative_work_state.json",
    "REDDOG_ACTIVE_SLICE_LEDGER_PATH": "ACTIVE_SLICE_LEDGER.runtime.md",
    "REDDOG_WORK_LEDGER_JSON_PATH": "work_ledger.runtime.json",
    "REDDOG_GITHUB_PR_RECORDS_PATH": "github_pr_records.json",
    "REDDOG_W10_REPORT_RECORDS_PATH": "w10_report_records.json",
    "REDDOG_ARCHITECT_FIX_DETERMINATION_PATH": "architect_determination.json",
    "REDDOG_MODEL_SELECTION_RECEIPT_PATH": "model_selection_receipt.json",
    "REDDOG_MODEL_RUNTIME_BINDING_RECEIPT_PATH": "model_runtime_binding_receipt.json",
    "REDDOG_MODEL_CATALOG_SNAPSHOT_PATH": "model_catalog_snapshot.json",
    "REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH": (
        "model_benchmark_evidence_receipts.json"
    ),
    "REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH": (
        "model_promotion_evidence_receipts.json"
    ),
    "REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH": (
        "model_production_evidence_bundle.json"
    ),
    "REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH": (
        "model_runtime_binding_policy.json"
    ),
    "REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH": (
        "model_evidence_trusted_keys.json"
    ),
    "REDDOG_MODEL_AUTORESEARCH_PROMOTION_GATE_RECEIPTS_PATH": (
        "model_autoresearch_promotion_gate_receipts.json"
    ),
    "REDDOG_MODEL_AUTORESEARCH_PLAN_RECEIPT_PATH": "model_autoresearch_plan_receipt.json",
    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_EXECUTION_RECEIPT_PATH": (
        "model_autoresearch_campaign_execution_receipt.json"
    ),
    "REDDOG_MODEL_AUTORESEARCH_CAMPAIGN_PROMOTION_POLICIES_PATH": (
        "model_autoresearch_campaign_promotion_policies.json"
    ),
    "REDDOG_MODEL_AUTORESEARCH_CYCLE_RECEIPT_PATH": "model_autoresearch_cycle_receipt.json",
    "REDDOG_MODEL_AUTORESEARCH_CYCLE_FEEDBACK_LEDGER_PATH": (
        "model_autoresearch_cycle_feedback.jsonl"
    ),
    "REDDOG_MEMEX_SUPPLY_RECEIPT_PATH": "memex_supply_receipt.json",
    "REDDOG_PRINCIPAL_AUTHORITY_RECORD_PATH": "principal_authority_record.json",
    "REDDOG_PERMISSION_SNAPSHOT_PATH": "permission_snapshot.json",
    "REDDOG_AUTHORITY_PROFILE_SEED_PATH": "authority_profile_seed.json",
    "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": "authority_profile_source.json",
    "REDDOG_EXECUTION_VALVE_ENV_PATH": "execution_valve_env.json",
    "REDDOG_AUTHORITY_RUNTIME_STATE_PATH": "authority_runtime_state.json",
    "REDDOG_PERMISSION_SNAPSHOTS_PATH": "permission_snapshots.json",
    "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH": "principal_authority_records.json",
    "REDDOG_SIGNER_SERVICE_CONFIG_PATH": "signer_service_config.json",
    "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH": "signer_service_run_packet.json",
    "REDDOG_SIGNER_SOCKET_PATH": "reddog_signer.sock",
    "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": "resident_queue_chain_results.json",
    "REDDOG_ARCHITECT_FIX_INERT_PROFILE_PATH": (
        "architect_fix_inert_profile.json"
    ),
    "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": "authority_profile.json",
    "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH": (
        "resident_queue_control_loop_receipts.jsonl"
    ),
}


def resident_queue_binding_profile(env: Mapping[str, str]) -> str:
    """Return the normalized resident queue binding profile."""

    value = str(env.get(ENV_REDDOG_RESIDENT_QUEUE_BINDING_PROFILE) or "").strip().lower()
    return value if value in RESIDENT_QUEUE_PROFILES else ""


def resident_queue_binding_enabled(env: Mapping[str, str], env_name: str) -> bool:
    """Return whether a derivation binding flag is enabled.

    Explicit environment values win. The profile only enables the known binding
    flags and only when the flag is absent.
    """

    raw = str(env.get(env_name) or "").strip()
    if raw:
        return raw == "1"
    return (
        env_name in PROFILE_BINDING_FLAGS
        and resident_queue_binding_profile(env) in RESIDENT_QUEUE_PROFILES
    )


def resident_queue_runtime_flag_enabled(env: Mapping[str, str], env_name: str) -> bool:
    """Return whether a safe resident runtime control-plane flag is enabled.

    Explicit environment values win. The profile only enables known
    control-plane flags that start existing gated loops or materialize
    outside-repo receipts needed by those loops; this helper never selects
    effect modes such as model generation, worktree, draft PR, PatternMemory,
    HoloIndex, merge, or reward settlement.
    """

    raw = str(env.get(env_name) or "").strip()
    if raw:
        return raw == "1"
    if (
        env_name == "REDDOG_AGENTDB_FIX_PROMOTION_CLAIM"
        and "REDDOG_RESIDENT_FIX_PROMOTION_HANDOFF" in env
    ):
        return False
    return (
        env_name in PROFILE_RUNTIME_FLAGS
        and resident_queue_binding_profile(env) in RESIDENT_QUEUE_PROFILES
    )


def resident_queue_runtime_root_path(env: Mapping[str, str], repo_root: Path | str) -> str:
    """Return explicit/default outside-repo resident runtime root for profiles."""

    root = Path(repo_root).resolve()
    raw = str(env.get("REDDOG_RESIDENT_RUNTIME_ROOT") or "").strip()
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = root.parent / path
        return str(validate_runtime_root_path(path, repo_root=root))
    if resident_queue_binding_profile(env) not in RESIDENT_QUEUE_PROFILES:
        return ""
    runtime_root = root.parent / ".reddog" / "resident" / _repo_slug(root)
    return str(validate_runtime_root_path(runtime_root, repo_root=root))


def resident_queue_signer_runtime_root_path(
    env: Mapping[str, str],
    repo_root: Path | str,
) -> str:
    """Return the signer-owned root kept separate from resident runtime state."""

    root = Path(repo_root).resolve()
    raw = str(env.get("REDDOG_SIGNER_RUNTIME_ROOT") or "").strip()
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = root.parent / path
        return str(validate_runtime_root_path(path, repo_root=root))
    resident = resident_queue_runtime_root_path(env, root)
    if not resident:
        return ""
    resident_path = Path(resident)
    signer_root = resident_path.parent / f"{resident_path.name}-signer-state"
    return str(validate_runtime_root_path(signer_root, repo_root=root))


def resident_queue_runtime_file_path(
    env: Mapping[str, str],
    repo_root: Path | str,
    env_name: str,
) -> str:
    """Return a confined explicit or profile-derived runtime file path."""

    filename = PROFILE_RUNTIME_PATH_FILENAMES.get(env_name)
    if not filename:
        return ""
    raw = str(env.get(env_name) or "").strip()
    runtime_root = resident_queue_runtime_root_path(env, repo_root)
    if raw:
        return str(
            validate_runtime_artifact_path(
                raw,
                repo_root=repo_root,
                allowed_root=runtime_root or None,
            )
        )
    if not runtime_root:
        return ""
    return str(
        validate_runtime_artifact_path(
            Path(runtime_root) / filename,
            repo_root=repo_root,
            allowed_root=runtime_root,
        )
    )


def resident_queue_artifact_generator_mode(env: Mapping[str, str]) -> str:
    """Return explicit/default artifact generator mode for the profile."""

    raw = str(env.get("REDDOG_ARTIFACT_GENERATOR_MODE") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) in _FUSION_OR_HIGHER_PROFILES:
        return "foundups_fusion"
    return ""


def resident_queue_worktree_runner_mode(env: Mapping[str, str]) -> str:
    """Return explicit/default worktree runner mode for the profile."""

    raw = str(env.get("REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) in _WORKTREE_OR_HIGHER_PROFILES:
        return "real"
    return ""


def resident_queue_draft_pr_runner_mode(env: Mapping[str, str]) -> str:
    """Return explicit/default verified draft-PR runner mode for the profile."""

    raw = str(env.get("REDDOG_DRAFT_PR_RUNNER_MODE") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) in _DRAFT_PR_OR_HIGHER_PROFILES:
        return "real"
    return ""


def resident_queue_evidence_command_runner_mode(env: Mapping[str, str]) -> str:
    """Return explicit/default independent evidence command runner mode."""

    raw = str(env.get("REDDOG_EVIDENCE_COMMAND_RUNNER_MODE") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) in _DRAFT_PR_OR_HIGHER_PROFILES:
        return "real"
    return ""


def resident_queue_outcome_ratchet_store_path(
    env: Mapping[str, str],
    repo_root: Path | str,
) -> str:
    """Return explicit/default verified outcome ratchet store path."""

    raw = str(env.get("REDDOG_OUTCOME_RATCHET_STORE_PATH") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) not in _DRAFT_PR_OR_HIGHER_PROFILES:
        return ""
    runtime_root = resident_queue_runtime_root_path(env, repo_root)
    return str(Path(runtime_root) / "outcome_ratchet" / "verified_outcomes.jsonl")


def resident_queue_model_feedback_ledger_store_path(
    env: Mapping[str, str],
    repo_root: Path | str,
) -> str:
    """Return explicit/default model-feedback ledger store path."""

    raw = str(env.get("REDDOG_MODEL_FEEDBACK_LEDGER_STORE_PATH") or "").strip()
    if raw:
        return raw
    if resident_queue_binding_profile(env) not in _DRAFT_PR_OR_HIGHER_PROFILES:
        return ""
    runtime_root = resident_queue_runtime_root_path(env, repo_root)
    return str(Path(runtime_root) / "model_feedback" / "model_feedback.jsonl")


def resident_queue_pattern_memory_admission_db_path(
    env: Mapping[str, str],
    repo_root: Path | str,
) -> str:
    """Return explicit/default verified PatternMemory admission DB path."""

    raw = str(env.get("REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH") or "").strip()
    if raw:
        return raw
    if (
        resident_queue_binding_profile(env)
        != PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY
    ):
        return ""
    runtime_root = resident_queue_runtime_root_path(env, repo_root)
    return str(Path(runtime_root) / "pattern_memory" / "pattern_memory.db")


def resident_queue_materializer_mode(env: Mapping[str, str]) -> str:
    """Return explicit/default work-order materializer mode for the profile."""

    has_explicit_mode = "REDDOG_WORK_ORDER_MATERIALIZER_MODE" in env
    raw = str(env.get("REDDOG_WORK_ORDER_MATERIALIZER_MODE") or "").strip()
    if raw:
        return raw
    if not has_explicit_mode and str(env.get("REDDOG_WORK_ORDERS_PATH") or "").strip():
        return ""
    if resident_queue_binding_profile(env) in RESIDENT_QUEUE_PROFILES:
        return "authority_profile"
    return ""


def resident_queue_now_epoch(env: Mapping[str, str]) -> tuple[int | None, bool]:
    """Return an optional nonnegative trusted test/runtime epoch."""

    raw = str(env.get("REDDOG_RESIDENT_QUEUE_NOW_EPOCH") or "").strip()
    if not raw:
        return None, True
    try:
        value = int(raw)
    except ValueError:
        return None, False
    return value, value >= 0


def resident_queue_integer_epoch() -> int:
    return int(time.time())


def _repo_slug(root: Path) -> str:
    raw = root.name or "repo"
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip(".-_")
    return slug or "repo"


__all__ = [
    "ENV_REDDOG_RESIDENT_QUEUE_BINDING_PROFILE",
    "PROFILE_BINDING_FLAGS",
    "PROFILE_RUNTIME_FLAGS",
    "PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION",
    "PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY",
    "PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR",
    "PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE",
    "PROFILE_SIGNED_0102_BOUNDED_CODE",
    "PROFILE_RUNTIME_PATH_FILENAMES",
    "RESIDENT_QUEUE_PROFILES",
    "resident_queue_artifact_generator_mode",
    "resident_queue_binding_enabled",
    "resident_queue_binding_profile",
    "resident_queue_draft_pr_runner_mode",
    "resident_queue_evidence_command_runner_mode",
    "resident_queue_materializer_mode",
    "resident_queue_integer_epoch",
    "resident_queue_model_feedback_ledger_store_path",
    "resident_queue_now_epoch",
    "resident_queue_outcome_ratchet_store_path",
    "resident_queue_pattern_memory_admission_db_path",
    "resident_queue_runtime_file_path",
    "resident_queue_runtime_flag_enabled",
    "resident_queue_runtime_root_path",
    "resident_queue_signer_runtime_root_path",
    "resident_queue_worktree_runner_mode",
]
