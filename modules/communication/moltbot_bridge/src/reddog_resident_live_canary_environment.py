"""Environment overlay for one explicitly confirmed RedDog live canary."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY,
)


def build_live_canary_environment(
    *, runtime_root: Path, environ: Mapping[str, str],
    queue_item_id: str, max_rounds: int,
) -> dict[str, str]:
    env = _runtime_paths(runtime_root)
    env.update(_runtime_modes())
    env.update(_runtime_controls(max_rounds))
    env["REDDOG_WRE_QUEUE_ITEM_ID"] = queue_item_id
    env["REDDOG_AUTHORITY_PROFILE_SOURCE_RECEIPT_ID"] = str(
        environ.get("REDDOG_AUTHORITY_PROFILE_SOURCE_RECEIPT_ID") or ""
    )
    return env


def _runtime_paths(runtime_root: Path) -> dict[str, str]:
    names = {
        "REDDOG_AUTHORITATIVE_WORK_STATE_PATH": "authoritative_work_state.json",
        "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH": "authority_profile.json",
        "REDDOG_AUTHORITY_PROFILE_SOURCE_PATH": "authority_profile_source.json",
        "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH": "resident_queue_chain_results.json",
        "REDDOG_EXECUTION_VALVE_ENV_PATH": "execution_valve_env.json",
        "REDDOG_AUTHORITY_RUNTIME_STATE_PATH": "authority_runtime_state.json",
        "REDDOG_PERMISSION_SNAPSHOTS_PATH": "permission_snapshots.json",
        "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH": "principal_authority_records.json",
        "REDDOG_SIGNER_SERVICE_CONFIG_PATH": "signer_service_config.json",
        "REDDOG_SIGNER_SERVICE_RUN_PACKET_PATH": "signer_service_run_packet.json",
        "REDDOG_SIGNER_SOCKET_PATH": "reddog_signer.sock",
        "REDDOG_OUTCOME_RATCHET_STORE_PATH": "verified_outcomes.jsonl",
        "REDDOG_MODEL_FEEDBACK_LEDGER_STORE_PATH": "model_feedback.jsonl",
        "REDDOG_PATTERN_MEMORY_ADMISSION_DB_PATH": "pattern_memory.db",
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPTS_PATH": (
            "resident_queue_control_loop_receipts.jsonl"
        ),
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_LOCK_PATH": "resident_queue_control_loop.lock",
    }
    paths = {key: str(runtime_root / name) for key, name in names.items()}
    paths["REDDOG_SIGNER_CONTROL_LOOP_ANCHOR_PATH"] = str(
        runtime_root.parent
        / f"{runtime_root.name}-signer-state"
        / "signer_control_loop_anchor.json"
    )
    paths["REDDOG_RESIDENT_RUNTIME_ROOT"] = str(runtime_root)
    paths["REDDOG_RESIDENT_QUEUE_BINDING_PROFILE"] = (
        PROFILE_SIGNED_0102_BOUNDED_CODE_FUSION_WORKTREE_DRAFT_PR_PATTERN_MEMORY
    )
    return paths


def _runtime_modes() -> dict[str, str]:
    return {
        "REDDOG_SIGNATURE_VERIFIER_BACKEND": "ed25519",
        "REDDOG_WORK_ORDER_MATERIALIZER_MODE": "authority_profile",
        "REDDOG_ARTIFACT_GENERATOR_MODE": "foundups_fusion",
        "REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_MODE": "real",
        "REDDOG_EVIDENCE_COMMAND_RUNNER_MODE": "real",
        "REDDOG_DRAFT_PR_RUNNER_MODE": "real",
        "REDDOG_RESIDENT_QUEUE_WORKTREE_RUNNER_TIMEOUT_S": "120",
        "REDDOG_DRAFT_PR_RUNNER_TIMEOUT_S": "120",
        "REDDOG_WORK_ORDERS_PATH": "",
        "REDDOG_ARTIFACT_CONTENTS_PATH": "",
        "REDDOG_ARTIFACT_GENERATION_REQUEST_PATH": "",
        "REDDOG_SIGNER_SERVICE_CONFIG_SUPPLY": "0",
        "REDDOG_SIGNER_SERVICE_RUN_PACKET_SUPPLY": "0",
        "REDDOG_AUTHORITY_RUNTIME_RESOLVER_ARTIFACT_SUPPLY": "0",
        "REDDOG_RESIDENT_QUEUE_NOW_EPOCH": "",
    }


def _runtime_controls(max_rounds: int) -> dict[str, str]:
    enabled = {
        "REDDOG_SIGNER_SERVICE_HEALTHCHECK", "REDDOG_SIGNER_SERVICE_HEALTHCHECK_ENFORCED",
        "REDDOG_PILOT_DRYRUN_BINDING", "REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING",
        "REDDOG_SLICE_VERIFIER_REQUEST_BINDING", "REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING",
        "REDDOG_OUTCOME_RATCHET_REQUEST_BINDING", "REDDOG_HELD_OUT_GATE_REQUEST_BINDING",
        "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING", "REDDOG_WORKER_DISPATCH_AGENTDB_WRITER",
        "OPENCLAW_SIGNED_WORKER_TASKS_ENABLED", "OPENCLAW_SIGNED_0102_BOUNDED_CODE_TASKS_ENABLED",
        "OPENCLAW_SIGNED_QUEUE_STAGE_TASKS_ENABLED", "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER",
        "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP", "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_ENFORCED",
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP", "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_ENFORCED",
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_RECEIPT_PERSISTENCE",
        "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP",
        "REDDOG_OPENCLAW_SIGNED_WORKER_CLAIM_LOOP_ENFORCED",
    }
    controls = {key: "1" for key in enabled}
    controls.update({
        "REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS": "16",
        "REDDOG_RESIDENT_QUEUE_CONTROL_LOOP_MAX_ROUNDS": str(max_rounds),
        "OPENCLAW_SIGNED_WORKER_TASK_MAX_CLAIMS": "1",
    })
    return controls


__all__ = ["build_live_canary_environment"]
