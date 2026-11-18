"""Bounded environment projection for the signed-worker queue loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_resident_queue_binding_profile import (
    resident_queue_artifact_generator_mode,
    resident_queue_binding_enabled,
    resident_queue_evidence_command_runner_mode,
    resident_queue_materializer_mode,
    resident_queue_model_feedback_ledger_store_path,
    resident_queue_outcome_ratchet_store_path,
    resident_queue_runtime_file_path,
    resident_queue_runtime_flag_enabled,
    resident_queue_runtime_root_path,
    resident_queue_worktree_runner_mode,
)


_PATH_PAIRS = {
    "work_orders_path": "REDDOG_WORK_ORDERS_PATH",
    "valve_environment_path": "REDDOG_EXECUTION_VALVE_ENV_PATH",
    "generic_writer_dryrun_result_path": "REDDOG_GENERIC_WRITER_DRYRUN_RESULT_PATH",
    "governed_shell_dryrun_result_path": "REDDOG_GOVERNED_SHELL_DRYRUN_RESULT_PATH",
    "artifact_contents_path": "REDDOG_ARTIFACT_CONTENTS_PATH",
    "artifact_generation_request_path": "REDDOG_ARTIFACT_GENERATION_REQUEST_PATH",
    "model_verifier.catalog_path": "REDDOG_MODEL_CATALOG_SNAPSHOT_PATH",
    "model_verifier.benchmarks_path": "REDDOG_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH",
    "model_verifier.promotions_path": "REDDOG_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH",
    "model_verifier.evidence_path": "REDDOG_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH",
    "model_verifier.policy_path": "REDDOG_MODEL_RUNTIME_BINDING_POLICY_PATH",
    "model_verifier.trusted_keys_path": "REDDOG_MODEL_EVIDENCE_TRUSTED_KEYS_PATH",
    "holoindex_evidence_path": "REDDOG_HOLOINDEX_EVIDENCE_PATH",
    "verifier_request_path": "REDDOG_SLICE_VERIFIER_REQUEST_PATH",
    "evidence_producer_request_path": "REDDOG_EVIDENCE_PRODUCER_REQUEST_PATH",
    "publish_request_path": "REDDOG_DRAFT_PR_PUBLISH_REQUEST_PATH",
    "ratchet_request_path": "REDDOG_OUTCOME_RATCHET_REQUEST_PATH",
    "outcome_ratchet_store_path": "REDDOG_OUTCOME_RATCHET_STORE_PATH",
    "held_out_gate_request_path": "REDDOG_HELD_OUT_GATE_REQUEST_PATH",
    "admission_request_path": "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_PATH",
    "authority_state_path": "REDDOG_AUTHORITY_RUNTIME_STATE_PATH",
    "permission_snapshots_path": "REDDOG_PERMISSION_SNAPSHOTS_PATH",
    "principal_authority_records_path": "REDDOG_PRINCIPAL_AUTHORITY_RECORDS_PATH",
    "signer_socket_path": "REDDOG_SIGNER_SOCKET_PATH",
    "signature_verifier_backend": "REDDOG_SIGNATURE_VERIFIER_BACKEND",
}

_FLAG_PAIRS = (
    ("pilot_dryrun_binding_enabled", "REDDOG_PILOT_DRYRUN_BINDING"),
    (
        "artifact_generation_request_binding_enabled",
        "REDDOG_ARTIFACT_GENERATION_REQUEST_BINDING",
    ),
    ("slice_verifier_request_binding_enabled", "REDDOG_SLICE_VERIFIER_REQUEST_BINDING"),
    (
        "draft_pr_publish_request_binding_enabled",
        "REDDOG_DRAFT_PR_PUBLISH_REQUEST_BINDING",
    ),
    (
        "outcome_ratchet_request_binding_enabled",
        "REDDOG_OUTCOME_RATCHET_REQUEST_BINDING",
    ),
    ("held_out_gate_request_binding_enabled", "REDDOG_HELD_OUT_GATE_REQUEST_BINDING"),
    (
        "pattern_memory_admission_request_binding_enabled",
        "REDDOG_PATTERN_MEMORY_ADMISSION_REQUEST_BINDING",
    ),
)


@dataclass(frozen=True)
class SignedWorkerQueueLoopEnvironment:
    """Validated, effect-free queue-loop environment projection."""

    requested: bool
    work_state_path: str
    chain_results_path: str
    authority_profile_path: str
    max_steps: int
    now_epoch: int | None
    now_epoch_valid: bool
    runtime_allowed_root: Path
    now_iso: str | None
    bootstrap_kwargs: dict[str, Any]


def project_signed_worker_queue_loop_environment(
    env: Mapping[str, str], repo_root: Path | str, *, now_epoch_resolver
) -> SignedWorkerQueueLoopEnvironment:
    """Project environment values without constructing effectful dependencies."""

    max_steps = _max_steps(env)
    now_epoch, now_epoch_valid = now_epoch_resolver(env)
    return SignedWorkerQueueLoopEnvironment(
        requested=resident_queue_runtime_flag_enabled(
            env, "REDDOG_SIGNED_WORKER_QUEUE_LOOP_RUNNER"
        ),
        work_state_path=_runtime_path(
            env, repo_root, "REDDOG_AUTHORITATIVE_WORK_STATE_PATH"
        ),
        chain_results_path=_runtime_path(
            env, repo_root, "REDDOG_RESIDENT_QUEUE_CHAIN_RESULTS_PATH"
        ),
        authority_profile_path=_runtime_path(
            env, repo_root, "REDDOG_RESIDENT_QUEUE_AUTHORITY_PROFILE_PATH"
        ),
        max_steps=max_steps,
        now_epoch=now_epoch,
        now_epoch_valid=now_epoch_valid,
        runtime_allowed_root=resident_queue_runtime_root_path(env, repo_root),
        now_iso=_stripped(env.get("REDDOG_RESIDENT_QUEUE_NOW_ISO")) or None,
        bootstrap_kwargs=build_signed_worker_bootstrap_kwargs(env, repo_root=repo_root),
    )


def build_signed_worker_bootstrap_kwargs(
    env: Mapping[str, str], *, repo_root: Path | str
) -> dict[str, Any]:
    """Build bounded bootstrap kwargs from the resident binding profile."""

    payload = _path_payload(env, repo_root)
    _add_modes_and_stores(payload, env, repo_root)
    _add_model_config(payload, env)
    for key, env_name in _FLAG_PAIRS:
        if resident_queue_binding_enabled(env, env_name):
            payload[key] = True
    return payload


def _path_payload(env: Mapping[str, str], repo_root: Path | str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, env_name in _PATH_PAIRS.items():
        value = _optional_runtime_file_path(env, repo_root=repo_root, env_name=env_name)
        if value:
            payload[key] = value
    if payload.get("signer_socket_path"):
        payload.setdefault("signature_verifier_backend", "ed25519")
    return payload


def _add_modes_and_stores(
    payload: dict[str, Any], env: Mapping[str, str], repo_root: Path | str
) -> None:
    values = {
        "work_order_materializer_mode": resident_queue_materializer_mode(env),
        "artifact_generator_mode": resident_queue_artifact_generator_mode(env),
        "worktree_runner_mode": resident_queue_worktree_runner_mode(env),
        "evidence_command_runner_mode": resident_queue_evidence_command_runner_mode(
            env
        ),
        "outcome_ratchet_store_path": resident_queue_outcome_ratchet_store_path(
            env, repo_root
        ),
        "model_feedback_ledger_store_path": resident_queue_model_feedback_ledger_store_path(
            env, repo_root
        ),
    }
    payload.update({key: value for key, value in values.items() if value})


def _add_model_config(payload: dict[str, Any], env: Mapping[str, str]) -> None:
    providers = tuple(
        sorted(
            {
                item.strip().lower()
                for item in str(
                    env.get("REDDOG_MODEL_RUNTIME_AVAILABLE_PROVIDERS") or ""
                ).split(",")
                if item.strip()
            }
        )
    )
    if providers:
        payload["artifact_model_available_providers"] = providers
    config = {
        key.split(".", 1)[1]: payload.pop(key)
        for key in tuple(payload)
        if key.startswith("model_verifier.")
    }
    config["verifier_backend"] = (
        _stripped(env.get("REDDOG_MODEL_EVIDENCE_SIGNATURE_VERIFIER_BACKEND"))
        or "ed25519"
    )
    payload["model_runtime_verifier_config"] = config


def _max_steps(env: Mapping[str, str]) -> int:
    raw = _stripped(env.get("REDDOG_SIGNED_WORKER_QUEUE_LOOP_MAX_STEPS")) or _stripped(
        env.get("REDDOG_RESIDENT_QUEUE_SERIAL_LOOP_MAX_STEPS")
    )
    try:
        return int(raw) if raw else 2
    except ValueError:
        return 0


def _runtime_path(env: Mapping[str, str], repo_root: Path | str, name: str) -> str:
    return _stripped(resident_queue_runtime_file_path(env, repo_root, name))


def _optional_runtime_file_path(
    env: Mapping[str, str], *, repo_root: Path | str, env_name: str
) -> str:
    explicit = _stripped(env.get(env_name))
    if explicit:
        return explicit
    value = _runtime_path(env, repo_root, env_name)
    return value if value and Path(value).exists() else ""


def _stripped(value: Any) -> str:
    return str(value or "").strip()


__all__ = [
    "SignedWorkerQueueLoopEnvironment",
    "build_signed_worker_bootstrap_kwargs",
    "project_signed_worker_queue_loop_environment",
]
