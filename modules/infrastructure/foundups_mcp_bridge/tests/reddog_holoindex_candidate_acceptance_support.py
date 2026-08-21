"""Ordered orchestration contracts for isolated HoloIndex acceptance."""

from __future__ import annotations

import os

import socket

import threading

from pathlib import Path

from types import SimpleNamespace

import pytest

from holo_index.query_receipt import build_query_receipt

SHA = "a" * 40

GENERATION = "sha256:" + "b" * 64

RECEIPT_DIGEST = "sha256:" + "c" * 64

REPLICA_BINDING = ("descriptor", "generation", "replica", "path")

def _config(tmp_path: Path, *, real_mode: bool = True):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        CandidateAcceptanceConfig,
    )

    return CandidateAcceptanceConfig(
        candidate_root=tmp_path / "candidate",
        authority_root=tmp_path / "authority",
        owner_runtime_root=tmp_path / "runtime",
        canonical_store=tmp_path / "canonical",
        isolated_store=tmp_path / "isolated",
        receipt_path=tmp_path / "receipts" / "acceptance.json",
        expected_sha=SHA,
        real_mode=real_mode,
    )

def _query_result() -> dict[str, object]:
    return {
        "ok": True,
        "freshness": "CURRENT",
        "index_gap_detected": False,
        "repo_head_sha": SHA,
        "freshness_generation_id": GENERATION,
        "freshness_receipt_digest": RECEIPT_DIGEST,
        "no_holoindex_reindex_performed": True,
    }

def _activation_result(tmp_path: Path) -> dict[str, object]:
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        K1_ACCEPTANCE_QUERY,
    )

    result: dict[str, object] = {
        **_query_result(),
        "source": "holoindex_owner_service",
        "query": K1_ACCEPTANCE_QUERY,
        "raw_result": {},
        "repo_root_digest": "sha256:" + "e" * 64,
        "workspace_repo_head_sha": SHA,
        "authority_repo_head_sha": SHA,
        "authority_repo_root_digest": "sha256:" + "e" * 64,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "clean_workspace_head",
        "no_authority_worktree_mutation_performed": True,
        "owner_attempts": 1,
        "owner_retry_performed": False,
        "owner_retry_reason": "",
    }
    result["query_receipt"] = dict(
        build_query_receipt(
            source="holoindex_owner_service",
            source_class="holoindex",
            query=K1_ACCEPTANCE_QUERY,
            result=result,
            require_generation=True,
        )
    )
    return result

def _worktree_proof():
    return SimpleNamespace(
        candidate_root_digest="sha256:" + "e" * 64,
        authority_root_digest="sha256:" + "f" * 64,
    )

def _model_copy_proof():
    return SimpleNamespace(
        source_digest="sha256:" + "1" * 64,
        destination_digest="sha256:" + "1" * 64,
        file_count=4,
        total_bytes=200,
    )

def _runtime_proof(tmp_path: Path):
    executable_proof = SimpleNamespace(path=tmp_path / "python.exe")
    return SimpleNamespace(
        runtime_root_digest="sha256:" + "0" * 64,
        site_packages=(str(tmp_path / "runtime" / ".venv" / "Lib" / "site-packages"),),
        base_executable_proof=executable_proof,
    )

def _operational_proof():
    return SimpleNamespace(
        ready=True,
        status="REFRESHED",
        refreshed=True,
        error="",
        repo_head_sha=SHA,
        generation_id=GENERATION,
        freshness_receipt_digest=RECEIPT_DIGEST,
    )

def _rehydration_proof():
    return SimpleNamespace(
        allowed=True,
        freshness="CURRENT",
        binding={
            "repo_head_sha": SHA,
            "freshness_generation_id": GENERATION,
            "freshness_receipt_digest": RECEIPT_DIGEST,
        },
    )

class _ReceiptProof:
    def __init__(self, calls: list[object]) -> None:
        self.calls = calls
        self.receipt = SimpleNamespace(generation_id=GENERATION)

    def __enter__(self):
        self.calls.append("receipt_open")
        return self

    def __exit__(self, *_exc):
        self.calls.append("receipt_close")

    def revalidate(self) -> None:
        self.calls.append("receipt_revalidate")


def _handoff_callbacks(calls: list[object], handoffs):
    values = iter(
        handoffs or [
            None,
            ("http://127.0.0.1:8127", "private-token"),
            ("http://127.0.0.1:8127", "private-token"),
        ]
    )
    state = {"cleaned": False}

    def cleanup_owner(*, expected_handoff, **_kwargs):
        current_handoff = next(values)
        calls.append("cleanup_attempt")
        if current_handoff != expected_handoff:
            return False
        calls.append("cleanup")
        state["cleaned"] = True
        return True

    def resolve_handoff():
        calls.append("handoff")
        if state["cleaned"]:
            return None
        return next(values)

    return cleanup_owner, resolve_handoff

def _dependencies(tmp_path: Path, calls: list[object], *, handoffs=None):
    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_candidate_acceptance import (
        CandidateAcceptanceDependencies,
    )

    model_source = tmp_path / "canonical-model"
    receipt_proof = SimpleNamespace(digest="sha256:" + "d" * 64, size=100)

    def record(name, value=None):
        calls.append((name, value) if value is not None else name)

    cleanup_owner, resolve_handoff = _handoff_callbacks(calls, handoffs)

    return CandidateAcceptanceDependencies(
        validate_worktrees=lambda *args, **kwargs: record("worktrees")
        or _worktree_proof(),
        validate_runtime=lambda *args, **kwargs: record("runtime")
        or _runtime_proof(tmp_path),
        create_store=lambda *args, **kwargs: record("create_store")
        or SimpleNamespace(path=tmp_path / "isolated"),
        verify_store=lambda *args, **kwargs: record("verify_store"),
        resolve_model=lambda *args, **kwargs: record("resolve_model") or model_source,
        copy_model=lambda *args, **kwargs: record("copy_model")
        or _model_copy_proof(),
        read_digest=lambda *args, **kwargs: record("canonical_digest") or receipt_proof,
        port_available=lambda host, port: record("port", (host, port)) or True,
        resolve_handoff=resolve_handoff,
        ensure_operational=lambda **kwargs: record("maintenance")
        or _operational_proof(),
        query_owner=lambda **kwargs: record("query", (kwargs["query"], kwargs["limit"]))
        or _query_result(),
        rehydrate=lambda **kwargs: record("rehydrate") or _rehydration_proof(),
        cleanup_owner=cleanup_owner,
        activate_supported_wrapper=lambda **kwargs: record("activation")
        or _activation_result(tmp_path),
        open_receipt_proof=lambda **kwargs: _ReceiptProof(calls),
        verify_collection_snapshots=lambda *args, **kwargs: record(
            "snapshot", kwargs.copy()
        ) or [],
        publish_receipt=lambda path, payload, **kwargs: record("publish", payload.copy()) or path,
    )

def _port_race_result(supervisor_module, tmp_path: Path, calls: list[object]):
    def lose_port_after_precheck(**_kwargs):
        calls.append("maintenance")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            listener.bind((supervisor_module.OWNER_HOST, 8127))
            listener.listen(1)
            try:
                supervisor_module.HoloQueryServiceSupervisor(
                    repo_root=tmp_path,
                    port=8127,
                    canonical_ssd_path=tmp_path / "canonical",
                    query_replica_root=tmp_path / "replica",
                    replica_capability_verifier=lambda: object(),
                    expected_replica_binding=REPLICA_BINDING,
                ).start()
            except supervisor_module.HoloQueryServiceSupervisorError as exc:
                error = exc.code
            else:  # pragma: no cover - an occupied exclusive port must reject
                raise AssertionError("foreign listener was reused")
        return SimpleNamespace(
            ready=False,
            status="FAILED",
            refreshed=False,
            error=error,
            repo_head_sha=SHA,
            generation_id="",
            freshness_receipt_digest="",
        )

    return lose_port_after_precheck

__all__ = [name for name in globals() if not name.startswith("__")]
