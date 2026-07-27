"""Authentication, replay, and migration tests for resident control receipts."""

from __future__ import annotations

import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_resident_control_loop_receipt_store as receipt_store,
)

from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_store import (
    CONTROL_LOOP_AUTHENTICATED,
    CONTROL_LOOP_DISPLAY_ONLY,
    ControlLoopReceiptSigningContext,
    LEGACY_CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
    _receipt_id,
    append_resident_control_loop_receipt,
    build_resident_control_loop_receipt,
    verify_resident_control_loop_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_resident_control_loop_receipt_chain import (
    verify_resident_control_loop_receipt_chain,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_live_canary_test_support import (
    _AuditMacBuilder,
    _LocalSignerClient,
    _PUBLIC_KEY,
    _SIGNING_CONTEXT,
    _test_private_key,
    _test_public_key,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    Ed25519SignatureVerifier,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signer_backend import (
    ControlLoopAuthorityPolicy,
    Ed25519SignerBackend,
)
from modules.communication.moltbot_bridge.src.reddog_signer_control_loop_anchor import (
    InMemorySignerControlLoopAnchorStore,
)
from modules.communication.moltbot_bridge.src import openclaw_supervisor


def _claim_evidence(
    *, task_id: str, status: str = "completed", receipt_id: str = "child-receipt-1"
) -> dict[str, object]:
    claim_status = {
        "completed": openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_ACCEPT,
        "requeued": openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_REQUEUED,
        "failed": openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
    }[status]
    return openclaw_supervisor._signed_worker_claim_result(
        accepted=status != "failed",
        status=claim_status,
        task_id=task_id,
        receipt_id=None if status == "failed" else receipt_id,
    )


def _result(**overrides: object) -> dict[str, object]:
    evidence = _claim_evidence(task_id="task-1")
    evidence_digest = str(evidence["execution_result_digest"])
    result: dict[str, object] = {
        "accepted": True,
        "status": "PASS",
        "rounds": 1,
        "serial_progress": 2,
        "claim_progress": 1,
        "worker_claim_count": 1,
        "worker_completion_count": 1,
        "worker_requeue_count": 0,
        "worker_failure_count": 0,
        "receipt_ids": ("child-receipt-1",),
        "child_execution_receipt_ids": ("child-receipt-1",),
        "child_execution_evidence_digests": (evidence_digest,),
        "child_execution_outcomes": (
            {
                "task_id": "task-1",
                "status": "completed",
                "receipt_id": "child-receipt-1",
                "evidence_digest": evidence_digest,
                "worker_execution_performed": False,
                "effect_evidence_complete": True,
                "worker_process_spawn_count": 0,
                "shell_command_count": 0,
            },
        ),
        "child_execution_evidence": (evidence,),
        "rejection_reasons": (),
        "control_lock_acquired": True,
        "dispatched_stages": ("authority_runtime",),
    }
    result.update(overrides)
    if "receipt_ids" in overrides and "child_execution_receipt_ids" not in overrides:
        result["child_execution_receipt_ids"] = overrides["receipt_ids"]
    if (
        "child_execution_outcomes" not in overrides
        and "child_execution_receipt_ids" not in overrides
        and "child_execution_evidence_digests" not in overrides
        and "receipt_ids" in overrides
    ):
        receipts = tuple(result["child_execution_receipt_ids"])
        digests = tuple(
            "sha256:" + hashlib.sha256(receipt_id.encode("utf-8")).hexdigest()
            for receipt_id in receipts
        )
        result["child_execution_evidence_digests"] = digests
        result["child_execution_outcomes"] = tuple(
            {
                "task_id": f"task-{index}",
                "status": "completed",
                "receipt_id": receipt_id,
                "evidence_digest": digest,
                "worker_execution_performed": False,
                "effect_evidence_complete": True,
                "worker_process_spawn_count": 0,
                "shell_command_count": 0,
            }
            for index, (receipt_id, digest) in enumerate(
                zip(receipts, digests), start=1
            )
        )
    if (
        "child_execution_outcomes" not in overrides
        and "child_execution_evidence_digests" in overrides
        and "child_execution_receipt_ids" not in overrides
    ):
        receipts = tuple(result["child_execution_receipt_ids"])
        digests = tuple(result["child_execution_evidence_digests"])
        result["child_execution_outcomes"] = tuple(
            {
                "task_id": f"task-{index}",
                "status": "completed",
                "receipt_id": receipt_id,
                "evidence_digest": digest,
                "worker_execution_performed": False,
                "effect_evidence_complete": True,
                "worker_process_spawn_count": 0,
                "shell_command_count": 0,
            }
            for index, (receipt_id, digest) in enumerate(
                zip(receipts, digests), start=1
            )
        )
    outcomes = tuple(dict(item) for item in result["child_execution_outcomes"])
    for outcome in outcomes:
        outcome.setdefault("worker_execution_performed", False)
        outcome.setdefault("effect_evidence_complete", True)
        outcome.setdefault("worker_process_spawn_count", 0)
        outcome.setdefault("shell_command_count", 0)
    result["child_execution_outcomes"] = outcomes
    if not any(
        key in overrides
        for key in (
            "child_execution_outcomes",
            "child_execution_evidence_digests",
            "child_execution_evidence",
        )
    ):
        generated = tuple(
            _claim_evidence(
                task_id=str(outcome["task_id"]),
                status=str(outcome["status"]),
                receipt_id=str(outcome["receipt_id"]),
            )
            for outcome in outcomes
        )
        result["child_execution_evidence"] = generated
        result["child_execution_evidence_digests"] = tuple(
            str(item["execution_result_digest"]) for item in generated
        )
        for outcome, item in zip(outcomes, generated):
            outcome["evidence_digest"] = item["execution_result_digest"]
    return result


def test_signed_receipt_requires_valid_signature_and_expected_key(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    receipt = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-1",
        nonce="nonce-1",
        signing_context=_SIGNING_CONTEXT,
    )

    verified = verify_resident_control_loop_receipt(
        receipt.to_dict(),
        expected_repo_root=repo,
        expected_signer_public_key=_PUBLIC_KEY,
        expected_key_epoch="epoch-canary-1",
        require_authenticated=True,
    )

    assert verified.authentication_status == CONTROL_LOOP_AUTHENTICATED
    assert verified.signature
    assert verified.worker_claim_count == 1
    assert verified.worker_completion_count == 1
    assert verified.worker_requeue_count == 0
    assert verified.shell_command_execution_observed is False
    assert verified.shell_command_count == 0
    with pytest.raises(ValueError, match="signer_invalid"):
        verify_resident_control_loop_receipt(
            receipt.to_dict(),
            expected_signer_public_key="wrong-key",
            require_authenticated=True,
        )


def test_signature_tamper_and_display_only_receipt_fail_live_auth(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    signed = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-1",
        nonce="nonce-1",
        signing_context=_SIGNING_CONTEXT,
    ).to_dict()
    signed["signature"] = "ed25519-sig-v1:" + "A" * 86
    with pytest.raises(ValueError, match="signature_invalid"):
        verify_resident_control_loop_receipt(signed, require_authenticated=True)

    display = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-display",
        nonce="nonce-display",
    )
    assert display.authentication_status == CONTROL_LOOP_DISPLAY_ONLY
    with pytest.raises(ValueError, match="authentication_required"):
        verify_resident_control_loop_receipt(display.to_dict(), require_authenticated=True)


def test_signer_audit_mac_tamper_fails_public_attestation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    receipt = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-audit",
        nonce="nonce-audit",
        signing_context=_SIGNING_CONTEXT,
    ).to_dict()
    receipt["signer_audit_mac"] = "audit:tampered"

    with pytest.raises(ValueError, match="audit_attestation_invalid"):
        verify_resident_control_loop_receipt(receipt, require_authenticated=True)


def test_authority_profile_source_receipt_is_signature_bound(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    receipt = build_resident_control_loop_receipt(
        result=_result(), repo_root=repo,
        created_at="2026-07-18T00:00:00Z", cycle_id="cycle-source",
        nonce="nonce-source", signing_context=_SIGNING_CONTEXT,
    ).to_dict()
    receipt["authority_profile_source_receipt_id"] = "sha256:" + "9" * 64

    with pytest.raises(ValueError):
        verify_resident_control_loop_receipt(receipt, require_authenticated=True)


def test_authenticated_receipt_io_preserves_exact_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime / "nested" / "control.jsonl"
    target.parent.mkdir()
    target.write_text("", encoding="utf-8")
    observed: list[tuple[str, Path | None]] = []

    def read_bytes(path, *, allowed_root, max_bytes):
        observed.append(("read", allowed_root))
        return b"", 0

    def append_text(
        path,
        text,
        *,
        repo_root,
        allowed_root,
        validate_existing,
        max_existing_bytes,
    ):
        observed.append(("append", allowed_root))
        validate_existing("")

    monkeypatch.setattr(receipt_store, "secure_read_confined_bytes", read_bytes)
    monkeypatch.setattr(receipt_store, "secure_append_runtime_text", append_text)

    assert receipt_store._read_existing_chain(target, runtime) == ""
    receipt = build_resident_control_loop_receipt(
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-root",
        nonce="nonce-root",
        signing_context=_SIGNING_CONTEXT,
    )
    receipt_store._append_receipt_once(
        target,
        receipt,
        repo,
        signing_context=_SIGNING_CONTEXT,
        require_authentication=True,
        runtime_root=runtime,
    )

    assert observed == [("read", runtime), ("append", runtime)]


def test_chain_links_receipts_and_rejects_cycle_or_nonce_replay(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    first = append_resident_control_loop_receipt(
        path=path,
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-1",
        nonce="nonce-1",
        signing_context=_SIGNING_CONTEXT,
        require_authentication=True, runtime_root=path.parent,
    )
    second = append_resident_control_loop_receipt(
        path=path,
        result=_result(receipt_ids=("child-receipt-2",)),
        repo_root=repo,
        created_at="2026-07-18T00:00:01Z",
        cycle_id="cycle-2",
        nonce="nonce-2",
        signing_context=_SIGNING_CONTEXT,
        require_authentication=True, runtime_root=path.parent,
    )

    assert second.previous_receipt_id == first.receipt_id
    with pytest.raises(ValueError, match="cycle_replay"):
        append_resident_control_loop_receipt(
            path=path,
            result=_result(),
            repo_root=repo,
            created_at="2026-07-18T00:00:02Z",
            cycle_id="cycle-1",
            nonce="nonce-3",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )


def test_child_receipt_and_evidence_reuse_is_rejected_across_cycles(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    append_resident_control_loop_receipt(
        path=path, result=_result(), repo_root=repo,
        created_at="2026-07-18T00:00:00Z", cycle_id="cycle-1",
        nonce="nonce-1", signing_context=_SIGNING_CONTEXT,
        require_authentication=True, runtime_root=path.parent,
    )

    with pytest.raises(ValueError, match="child_(receipt|evidence)_replay"):
        append_resident_control_loop_receipt(
            path=path, result=_result(), repo_root=repo,
            created_at="2026-07-18T00:00:01Z", cycle_id="cycle-2",
            nonce="nonce-2", signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )


def test_head_recovers_exact_signed_receipt_after_append_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    original_append = receipt_store._append_receipt_once
    calls = 0

    def fail_once(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated_append_interruption")
        original_append(*args, **kwargs)

    monkeypatch.setattr(receipt_store, "_append_receipt_once", fail_once)
    with pytest.raises(RuntimeError, match="simulated_append_interruption"):
        append_resident_control_loop_receipt(
            path=path, result=_result(), repo_root=repo,
            created_at="2026-07-18T00:00:00Z", cycle_id="cycle-1",
            nonce="nonce-1", signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )

    second = append_resident_control_loop_receipt(
        path=path, result=_result(receipt_ids=("child-receipt-2",)),
        repo_root=repo, created_at="2026-07-18T00:00:01Z",
        cycle_id="cycle-2", nonce="nonce-2", signing_context=_SIGNING_CONTEXT,
        require_authentication=True, runtime_root=path.parent,
    )
    payloads = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(payloads) == 2
    assert payloads[0]["sequence_number"] == 1
    assert payloads[1]["sequence_number"] == 2
    assert second.previous_receipt_id == payloads[0]["receipt_id"]


def test_retention_limit_rejects_before_advancing_high_water_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    state_path = tmp_path / "runtime" / "authority.json"
    first = append_resident_control_loop_receipt(
        path=path,
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-capacity-1",
        nonce="nonce-capacity-1",
        signing_context=_SIGNING_CONTEXT,
        require_authentication=True, runtime_root=path.parent,
        head_state_path=state_path,
    )
    before = json.loads(state_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        receipt_store,
        "MAX_CONTROL_RECEIPT_CHAIN_BYTES",
        path.stat().st_size + 1,
    )

    with pytest.raises(ValueError, match="retention_limit"):
        append_resident_control_loop_receipt(
            path=path,
            result=_result(receipt_ids=("child-receipt-capacity-2",)),
            repo_root=repo,
            created_at="2026-07-18T00:00:01Z",
            cycle_id="cycle-capacity-2",
            nonce="nonce-capacity-2",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
            head_state_path=state_path,
        )

    after = json.loads(state_path.read_text(encoding="utf-8"))
    assert after["control_receipt_head"]["receipt_id"] == first.receipt_id
    assert after["revision"] == before["revision"]
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_concurrent_same_cycle_allows_exactly_one_signed_append(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"

    def append() -> str:
        receipt = append_resident_control_loop_receipt(
            path=path,
            result=_result(),
            repo_root=repo,
            created_at="2026-07-18T00:00:00Z",
            cycle_id="same-cycle",
            nonce="same-nonce",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )
        return receipt.receipt_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(append) for _ in range(2)]
    successes = [future.result() for future in futures if future.exception() is None]
    failures = [future.exception() for future in futures if future.exception() is not None]

    assert len(successes) == 1
    assert len(failures) == 1
    assert "replay" in str(failures[0]) or "revision_conflict" in str(failures[0])
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_concurrent_distinct_signed_appends_are_serialized_without_loss(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"

    def append(index: int) -> str:
            return append_resident_control_loop_receipt(
                path=path,
                result=_result(receipt_ids=(f"child-receipt-{index}",)),
            repo_root=repo,
            created_at=f"2026-07-18T00:00:0{index}Z",
            cycle_id=f"distinct-cycle-{index}",
            nonce=f"distinct-nonce-{index}",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        ).receipt_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        receipt_ids = list(executor.map(append, (0, 1)))

    payloads = tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    )
    assert len(set(receipt_ids)) == 2
    assert len(payloads) == 2
    assert payloads[1]["previous_receipt_id"] == payloads[0]["receipt_id"]


def test_string_false_never_becomes_accepted_true(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    receipt = build_resident_control_loop_receipt(
        result=_result(accepted="false"),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-false",
        nonce="nonce-false",
        signing_context=_SIGNING_CONTEXT,
    )

    assert receipt.accepted is False


def test_receipt_records_observed_stage_effects_without_inventing_shell_or_process_use(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    receipt = build_resident_control_loop_receipt(
        result=_result(
            dispatched_stages=(
                "authority_runtime",
                "worktree_create",
                "bounded_worker_pilot",
                "slice_verifier",
                "verified_draft_pr_publish",
                "pattern_memory_admission",
            ),
        ),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-effects",
        nonce="nonce-effects",
        signing_context=_SIGNING_CONTEXT,
    )

    assert receipt.worktree_creation_count == 1
    assert receipt.bounded_file_edit_count == 1
    assert receipt.slice_verification_count == 1
    assert receipt.draft_pr_publish_count == 1
    assert receipt.pattern_memory_admission_count == 1
    assert receipt.worktree_creation_observed is True
    assert receipt.bounded_file_edit_observed is True
    assert receipt.shell_command_count == 0
    assert receipt.shell_command_execution_observed is False
    assert receipt.worker_process_spawn_count == 0
    assert receipt.worker_process_spawn_observed is False
    assert "no_merge_performed" not in receipt.to_dict()


@pytest.mark.parametrize(
    ("field", "value"),
    (("worker_process_spawn_count", 7), ("shell_command_count", 9)),
)
def test_parent_effect_counts_must_equal_digest_bound_child_counts(
    tmp_path: Path, field: str, value: int
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(ValueError, match=f"effect_claim_conflict:{field}"):
        build_resident_control_loop_receipt(
            result=_result(**{field: value}),
            repo_root=repo,
            created_at="2026-07-18T00:00:00Z",
        )


def test_unknown_runner_effects_are_signed_as_unverified_not_no_effect(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    unknown_effects = {
        "worker_execution_performed": True,
        "effect_evidence_complete": False,
        "worker_process_spawn_count": 0,
        "shell_command_count": 0,
        **{
            field: False
            for field in openclaw_supervisor._SIGNED_WORKER_NO_EFFECT_FIELDS
        },
    }
    evidence = openclaw_supervisor._signed_worker_claim_result(
        accepted=False,
        status=openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
        task_id="task-runner-exception",
        rejection_reasons=("runner_exception",),
        effect_source=unknown_effects,
    )
    digest = str(evidence["execution_result_digest"])

    receipt = build_resident_control_loop_receipt(
        result=_result(
            accepted=False,
            status="REJECT",
            claim_progress=1,
            worker_claim_count=1,
            worker_completion_count=0,
            worker_failure_count=1,
            worker_execution_count=1,
            receipt_ids=(),
            child_execution_receipt_ids=(),
            child_execution_evidence_digests=(digest,),
            child_execution_outcomes=(
                {
                    "task_id": "task-runner-exception",
                    "status": "failed",
                    "receipt_id": "",
                    "evidence_digest": digest,
                    "worker_execution_performed": True,
                    "effect_evidence_complete": False,
                    "worker_process_spawn_count": 0,
                    "shell_command_count": 0,
                },
            ),
            child_execution_evidence=(evidence,),
        ),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        signing_context=_SIGNING_CONTEXT,
    )

    assert receipt.worker_effects_unverified_count == 1
    assert receipt.worker_execution_count == 1
    assert receipt.shell_command_count == 0


def test_failed_claim_counts_execution_only_when_runner_was_invoked(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    effect_source = {
        "worker_execution_performed": True,
        "effect_evidence_complete": True,
        "worker_process_spawn_count": 0,
        "shell_command_count": 1,
        "no_shell_command_executed": False,
        "no_source_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_hermes_dispatch_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_live_foundup_enqueue_performed": True,
        "no_pattern_memory_write_performed": True,
        "no_reward_settlement_performed": True,
    }
    evidence = openclaw_supervisor._signed_worker_claim_result(
        accepted=False,
        status=openclaw_supervisor.SIGNED_WORKER_OPENCLAW_CLAIM_REJECT,
        task_id="task-failed-after-runner",
        rejection_reasons=("runner_rejected",),
        effect_source=effect_source,
    )
    digest = str(evidence["execution_result_digest"])
    receipt = build_resident_control_loop_receipt(
        result=_result(
            claim_progress=1,
            worker_claim_count=1,
            worker_completion_count=0,
            worker_failure_count=1,
            worker_execution_count=1,
            shell_command_count=1,
            receipt_ids=(),
            child_execution_receipt_ids=(),
            child_execution_evidence_digests=(digest,),
            child_execution_outcomes=(
                {
                    "task_id": "task-failed-after-runner",
                    "status": "failed",
                    "receipt_id": "",
                    "evidence_digest": digest,
                    "worker_execution_performed": True,
                    "effect_evidence_complete": True,
                    "worker_process_spawn_count": 0,
                    "shell_command_count": 1,
                },
            ),
            child_execution_evidence=(evidence,),
        ),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-failed-after-runner",
        nonce="nonce-failed-after-runner",
        signing_context=_SIGNING_CONTEXT,
    )
    assert receipt.worker_failure_count == 1
    assert receipt.worker_execution_count == 1
    assert receipt.worker_execution_performed is True
    assert receipt.shell_command_count == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"child_execution_receipt_ids": ()},
        {"child_execution_evidence_digests": ()},
    ],
)
def test_completed_worker_requires_exact_child_receipt_and_execution_evidence(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(
        ValueError,
        match="(child_.*(cardinality|projection)_.*|worker_outcome_count_invalid)",
    ):
        build_resident_control_loop_receipt(
            result=_result(**overrides),
            repo_root=repo,
            created_at="2026-07-18T00:00:00Z",
            cycle_id="cycle-missing-child",
            nonce="nonce-missing-child",
            signing_context=_SIGNING_CONTEXT,
        )


def test_child_outcome_order_must_match_receipt_and_evidence_projections(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    evidence_two = _claim_evidence(task_id="task-2", receipt_id="child-receipt-2")
    evidence_one = _claim_evidence(task_id="task-1", receipt_id="child-receipt-1")
    digest_one = str(evidence_one["execution_result_digest"])
    digest_two = str(evidence_two["execution_result_digest"])
    result = _result(
        claim_progress=2,
        worker_claim_count=2,
        worker_completion_count=2,
        receipt_ids=("child-receipt-1", "child-receipt-2"),
        child_execution_receipt_ids=("child-receipt-1", "child-receipt-2"),
        child_execution_evidence_digests=(digest_one, digest_two),
        child_execution_outcomes=(
            {
                "task_id": "task-2", "status": "completed",
                "receipt_id": "child-receipt-2", "evidence_digest": digest_two,
                "worker_execution_performed": False,
            },
            {
                "task_id": "task-1", "status": "completed",
                "receipt_id": "child-receipt-1", "evidence_digest": digest_one,
                "worker_execution_performed": False,
            },
        ),
        child_execution_evidence=(evidence_two, evidence_one),
    )
    with pytest.raises(ValueError, match="child_projection_conflict"):
        build_resident_control_loop_receipt(
            result=result, repo_root=repo, created_at="2026-07-18T00:00:00Z",
            cycle_id="cycle-order", nonce="nonce-order",
            signing_context=_SIGNING_CONTEXT,
        )


@pytest.mark.parametrize("field", ["detail", "worker_execution_performed", "execution_result_digest"])
def test_complete_child_evidence_rejects_body_or_digest_tamper(
    tmp_path: Path, field: str
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = _result()
    evidence = dict(result["child_execution_evidence"][0])
    if field == "worker_execution_performed":
        evidence[field] = True
    elif field == "execution_result_digest":
        evidence[field] = "sha256:" + "f" * 64
    else:
        evidence[field] = "tampered after child execution"
    result["child_execution_evidence"] = (evidence,)

    with pytest.raises(ValueError, match="child_evidence"):
        build_resident_control_loop_receipt(
            result=result, repo_root=repo, created_at="2026-07-18T00:00:00Z",
            cycle_id="cycle-child-tamper", nonce="nonce-child-tamper",
            signing_context=_SIGNING_CONTEXT,
        )


def test_authenticated_append_rejects_unsigned_v2_predecessor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    append_resident_control_loop_receipt(
        path=path,
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="display-cycle",
        nonce="display-nonce",
    )

    with pytest.raises(ValueError, match="authentication_required"):
        append_resident_control_loop_receipt(
            path=path,
            result=_result(receipt_ids=("child-receipt-2",)),
            repo_root=repo,
            created_at="2026-07-18T00:00:01Z",
            cycle_id="signed-cycle",
            nonce="signed-nonce",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )


def test_authenticated_append_rejects_foreign_signed_v2_predecessor(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    private_key = _test_private_key()
    public_key = _test_public_key(private_key)
    foreign_context = ControlLoopReceiptSigningContext(
        signer=_LocalSignerClient(
            Ed25519SignerBackend(
                private_key=private_key,
                    public_key=public_key,
                    key_epoch="foreign-epoch",
                    audit_mac_builder=_AuditMacBuilder(),
                    control_loop_anchor_store=InMemorySignerControlLoopAnchorStore(),
                    control_loop_authority_policy=ControlLoopAuthorityPolicy(
                        issuer_principal_id="github:foreign",
                        signer_public_key=public_key,
                        key_epoch="foreign-epoch",
                        consensus_receipt_digest="sha256:" + "d" * 64,
                        authority_profile_digest="sha256:" + "f" * 64,
                        authority_profile_source_receipt_id="sha256:" + "e" * 64,
                    ),
                )
        ),
        signature_verifier=Ed25519SignatureVerifier(),
        issuer_principal_id="github:foreign",
        signer_public_key=public_key,
        key_epoch="foreign-epoch",
        authority_tier="HIGH",
        consensus_receipt_digest="sha256:" + "d" * 64,
        authority_profile_digest="sha256:" + "f" * 64,
        authority_profile_source_receipt_id="sha256:" + "e" * 64,
    )
    append_resident_control_loop_receipt(
        path=path,
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="foreign-cycle",
        nonce="foreign-nonce",
        signing_context=foreign_context,
        require_authentication=True, runtime_root=path.parent,
    )

    with pytest.raises(ValueError, match="signer_invalid"):
        append_resident_control_loop_receipt(
            path=path,
            result=_result(receipt_ids=("child-receipt-2",)),
            repo_root=repo,
            created_at="2026-07-18T00:00:01Z",
            cycle_id="local-cycle",
            nonce="local-nonce",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )


def test_complete_chain_verifier_rejects_tamper_and_reorder(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    for index in range(2):
        append_resident_control_loop_receipt(
            path=path,
            result=_result(
                receipt_ids=(f"child-receipt-{index + 1}",),
            ),
            repo_root=repo,
            created_at=f"2026-07-18T00:00:0{index}Z",
            cycle_id=f"chain-cycle-{index}",
            nonce=f"chain-nonce-{index}",
            signing_context=_SIGNING_CONTEXT,
            require_authentication=True, runtime_root=path.parent,
        )
    payloads = tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
    )
    expected = {
        "expected_signer_public_key": _SIGNING_CONTEXT.signer_public_key,
        "expected_key_epoch": _SIGNING_CONTEXT.key_epoch,
        "expected_consensus_receipt_digest": (
            _SIGNING_CONTEXT.consensus_receipt_digest
        ),
        "expected_authority_profile_digest": (
            _SIGNING_CONTEXT.authority_profile_digest
        ),
        "expected_authority_profile_source_receipt_id": (
            _SIGNING_CONTEXT.authority_profile_source_receipt_id
        ),
        "expected_issuer_principal_id": _SIGNING_CONTEXT.issuer_principal_id,
    }
    verify_resident_control_loop_receipt_chain(payloads, **expected)
    tampered = [dict(item) for item in payloads]
    tampered[0]["status"] = "TAMPERED"
    with pytest.raises(ValueError):
        verify_resident_control_loop_receipt_chain(tampered, **expected)
    with pytest.raises(ValueError, match="(previous_link|sequence)_invalid"):
        verify_resident_control_loop_receipt_chain(tuple(reversed(payloads)), **expected)


def test_first_v2_receipt_binds_validated_legacy_prefix(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    path = tmp_path / "runtime" / "control.jsonl"
    path.parent.mkdir()
    legacy = {
        "schema_version": LEGACY_CONTROL_LOOP_RECEIPT_SCHEMA_VERSION,
        "accepted": True,
        "status": "PASS",
        "rounds": 1,
        "serial_progress": 1,
        "claim_progress": 0,
        "receipt_ids": [],
        "rejection_reasons": [],
        "created_at": "2026-07-17T00:00:00Z",
        "repo_root_digest": "legacy-repo",
        "control_lock_acquired": True,
        "no_authority_issued": True,
        "no_worker_spawn_performed": True,
        "no_shell_command_executed": True,
        "no_holoindex_reindex_performed": True,
        "no_merge_performed": True,
        "no_reward_settlement_performed": True,
    }
    legacy["receipt_id"] = _receipt_id(legacy)
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    current = append_resident_control_loop_receipt(
        path=path,
        result=_result(),
        repo_root=repo,
        created_at="2026-07-18T00:00:00Z",
        cycle_id="cycle-current",
        nonce="nonce-current",
        signing_context=_SIGNING_CONTEXT,
        require_authentication=True, runtime_root=path.parent,
    )

    assert current.previous_receipt_id == legacy["receipt_id"]
    assert current.legacy_prefix_digest.startswith("sha256:")
