"""Tests for REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_HANDLER_PHASE1."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_resident_queue_chain_results_store import (
    CHAIN_RESULTS_SCHEMA_VERSION,
    InMemoryResidentQueueChainResultsStore,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_next_stage_dispatch import (
    FAIL_RECORD_REJECTED,
    RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT,
    ResidentQueueStageDispatchRequest,
    invoke_reddog_resident_queue_next_stage_dispatch,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_orchestration_plan import (
    NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
    NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_slice_verifier_handler import (
    BOUNDED_WORKER_PILOT_STAGE_KEY,
    FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING,
    FAIL_DISPATCH_NEXT_ACTION_MISMATCH,
    FAIL_DISPATCH_STAGE_MISMATCH,
    FAIL_EVIDENCE_COMMAND_RUNNER_MISSING,
    FAIL_EVIDENCE_PRODUCER_REJECTED,
    FAIL_SLICE_VERIFIER_REQUEST_BINDING_REJECTED,
    FAIL_VERIFIER_REQUEST_MISSING,
    SLICE_VERIFIER_STAGE_KEY,
    build_reddog_resident_queue_slice_verifier_stage_handler,
)
from modules.communication.moltbot_bridge.src.reddog_resident_queue_slice_verifier_request_binding import (
    FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH,
    FAIL_SLICE_VERIFIER_PLAN_MISSING,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_request_dryrun import (
    QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_runtime_invoke import (
    QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authority_verification_invoke import (
    QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_execution_valve_invoke import (
    QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_executor_plan_dryrun import (
    QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_slice_verifier_invoke import (
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT,
    QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT,
    QueueAuthorizedSliceVerifierInvokeReason,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_authorized_worktree_create_invoke import (
    QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_wre_queue_verified_authority_work_order_invoke import (
    QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_binding import (
    canonical_full_work_order_digest,
)
from modules.communication.moltbot_bridge.src.reddog_work_authority_digest import (
    canonical_work_authority_digest,
)
from modules.communication.moltbot_bridge.tests.test_reddog_resident_queue_slice_verifier_request_binding import (
    _exact_sha_commit_receipt,
)
from modules.communication.moltbot_bridge.tests.test_reddog_wre_queue_authorized_slice_verifier_invoke import (
    ARTIFACT,
    WORK_ORDER_ID,
    _queue_pilot_result,
    _verifier_request,
)
from modules.communication.moltbot_bridge.tests.reddog_resident_queue_test_helpers import (
    WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
    WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
    with_queue_wsp15_allocation,
)
from modules.infrastructure.wre_core.src.wre_autonomous_slice_verifier_runtime import (
    AUTONOMOUS_SLICE_VERIFIER_ACCEPT,
)
from modules.infrastructure.wre_core.src.wre_independent_evidence_producer_runtime import (
    CommandResult,
    EVIDENCE_PRODUCER_ACCEPT,
    FAIL_HOLOINDEX_EVIDENCE,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_resident_queue_slice_verifier_handler.py"
)
NOW_ISO = "2026-07-14T00:00:00+00:00"
EXPIRES = "2026-07-14T01:00:00+00:00"


def _snapshot() -> dict[str, object]:
    queue_item = with_queue_wsp15_allocation(
        {
            "queue_item_id": "queue-1",
            "slice_id": "REDDOG_TEST_SLICE_PHASE1",
            "claim_id": "claim-1",
            "worker_id": "reddog-0102",
            "status": "QUEUED",
            "evidence_refs": ["claim:claim-1", "freshness:fresh-1"],
            "no_execution_performed": True,
        },
        prompt_text="Update one bounded FoundUp test fixture",
    )
    return {
        "schema_version": "reddog_authoritative_work_state.v1",
        "freshness_receipts": [{"receipt_id": "fresh-1", "fresh": True}],
        "worker_claims": [
            {
                "claim_id": "claim-1",
                "slice_id": "REDDOG_TEST_SLICE_PHASE1",
                "worker_id": "reddog-0102",
                "status": "ACTIVE",
                "expires_at": EXPIRES,
                "freshness_receipt_id": "fresh-1",
            }
        ],
        "wre_queue_items": [queue_item],
    }


def _reservation() -> dict[str, object]:
    return {
        "reservation_id": "assurance-reservation-" + "1" * 20,
        "reservation_digest": "sha256:" + "0" * 64,
        "admission_reservation_digest": "sha256:" + "0" * 64,
        "status": "reserved",
        "work_order_id": WORK_ORDER_ID,
        "author_task_id": "reddog-worker-dispatch-" + "1" * 16,
        "author_principal_id": "worker:author",
        "verifier_task_id": "reddog-worker-dispatch-" + "2" * 16,
        "verifier_principal_id": "worker:verifier",
    }


class _ReservationStore:
    def get_independent_assurance_reservation(self, reservation_id: str):
        assert reservation_id == _reservation()["reservation_id"]
        return _reservation()

    def stage_independent_assurance_completion(self, request):
        assert request["reservation_id"] == _reservation()["reservation_id"]
        assert request["terminal_receipt_id"]
        assert str(request["terminal_receipt_digest"]).startswith("sha256:")
        return {"accepted": True, "status": "STAGED"}


class _RenewedReservationStore(_ReservationStore):
    def get_independent_assurance_reservation(self, reservation_id: str):
        assert reservation_id == _reservation()["reservation_id"]
        return {
            **_reservation(),
            "reservation_digest": "sha256:" + "1" * 64,
            "renewal_count": 1,
        }


def _exact_sha_commit_stage(worktree_path: str) -> dict[str, object]:
    work_order_digest = canonical_full_work_order_digest(_work_order())
    return {
        "decision": "RESIDENT_QUEUE_EXACT_SHA_COMMIT_ACCEPT",
        "accepted": True,
        "effect_commit_state": "COMMITTED",
        "reconciliation_required": False,
        "commit_receipt": _exact_sha_commit_receipt(
            worktree_path,
            work_order_digest=work_order_digest,
        ),
    }


def _seeded_store(**stage_overrides: object) -> InMemoryResidentQueueChainResultsStore:
    work_authority = {
        "authority_id": "authority-1",
        "work_order_id": WORK_ORDER_ID,
    }
    authority_digest = canonical_work_authority_digest(work_authority)
    stage_results: dict[str, object] = {
        "authority_request": {"status": QUEUE_AUTHORITY_REQUEST_DRYRUN_ACCEPT},
        "authority_runtime": {
            "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
            "authority_result": {
                "accepted": True,
                "work_authority": work_authority,
                "receipt": {
                    "receipt_id": _digest("8"),
                    "status": "DELEGATED_AUTHORITY_ISSUED",
                    "work_authority_digest": authority_digest,
                },
            },
        },
        "authority_verification": {
            "decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
            "verified_work_authority_digest": authority_digest,
            "verification_result": {"accepted": True},
        },
        "worker_dispatch_dryrun": WORKER_DISPATCH_DRYRUN_STAGE_RESULT,
        "worker_dispatch_runtime": WORKER_DISPATCH_RUNTIME_STAGE_RESULT,
        "work_order_invocation": {"decision": QUEUE_VERIFIED_AUTHORITY_WORK_ORDER_INVOKE_ACCEPT},
        "executor_plan": {
            "decision": QUEUE_AUTHORIZED_EXECUTOR_PLAN_DRYRUN_ACCEPT,
            "executor_plan_result": {
                "plan": {
                    "work_order_digest": canonical_full_work_order_digest(
                        _work_order()
                    )
                },
            },
        },
        "execution_valve": {"decision": QUEUE_AUTHORIZED_EXECUTION_VALVE_INVOKE_ACCEPT},
        "worktree_create": {"decision": QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT},
        "assurance_capacity_admission": {
            "decision": "ASSURANCE_CAPACITY_ADMISSION_ACCEPT",
            "reservation": _reservation(),
        },
        BOUNDED_WORKER_PILOT_STAGE_KEY: _queue_pilot_result(),
        "exact_sha_commit": _exact_sha_commit_stage("O:/tmp/reddog-worker"),
    }
    stage_results.update(stage_overrides)
    return InMemoryResidentQueueChainResultsStore(
        {
            "schema_version": CHAIN_RESULTS_SCHEMA_VERSION,
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
            "stage_results": stage_results,
            "receipts": [],
        }
    )


def _handler(
    *,
    chain_store: InMemoryResidentQueueChainResultsStore,
    verifier_request: dict[str, object] | None = None,
    evidence_producer_request: dict[str, object] | None = None,
    evidence_command_runner: object | None = None,
    work_order_resolver: object | None = None,
    repo_root: Path | None = None,
    slice_verifier_request_binding_enabled: bool = False,
    holoindex_evidence: dict[str, object] | None = None,
    assurance_reservation_store: object | None = None,
    trusted_now: datetime | None = None,
):
    return build_reddog_resident_queue_slice_verifier_stage_handler(
        chain_results_store=chain_store,
        verifier_request=verifier_request if verifier_request is not None else _verifier_request(),
        evidence_producer_request=evidence_producer_request,
        evidence_command_runner=evidence_command_runner,
        work_order_resolver=work_order_resolver,
        repo_root=repo_root,
        slice_verifier_request_binding_enabled=slice_verifier_request_binding_enabled,
        holoindex_evidence=holoindex_evidence,
        assurance_reservation_store=(
            assurance_reservation_store or _ReservationStore()
        ),
        trusted_now=trusted_now,
    )


class _FakeEvidenceRunner:
    def __init__(self, *, head: str = "a" * 40) -> None:
        self.head = head
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd: Path, timeout_s: int) -> CommandResult:
        _ = (cwd, timeout_s)
        argv_tuple = tuple(argv)
        self.calls.append(argv_tuple)
        if argv_tuple == ("git", "rev-parse", "HEAD"):
            return CommandResult(returncode=0, stdout=self.head + "\n")
        if argv_tuple[:3] == ("git", "diff", "--name-only"):
            return CommandResult(returncode=0, stdout=ARTIFACT + "\n")
        if argv_tuple[:3] == ("git", "diff", "--unified=0"):
            return CommandResult(
                returncode=0,
                stdout=(
                    f"diff --git a/{ARTIFACT} b/{ARTIFACT}\n"
                    f"+++ b/{ARTIFACT}\n"
                    "+resident queue produced evidence\n"
                ),
            )
        return CommandResult(returncode=0, stdout="ok\n")


class _Resolver:
    def __init__(self, work_order: dict[str, object]) -> None:
        self.work_order = work_order
        self.calls: list[dict[str, object | None]] = []

    def resolve(
        self,
        *,
        work_order_id: str,
        queue_item_id: str | None,
        selected_slice: str | None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "work_order_id": work_order_id,
                "queue_item_id": queue_item_id,
                "selected_slice": selected_slice,
            }
        )
        if work_order_id != self.work_order.get("work_order_id"):
            return {}
        return self.work_order


def _digest(ch: str) -> str:
    return "sha256:" + ch * 64


def _signed_receipt_chain() -> dict[str, object]:
    return {
        "accepted": True,
        "terminal_receipt_hash": _digest("a"),
    }


def _slice_verifier_plan(**overrides: object) -> dict[str, object]:
    payload = {
        "slice_name": "REDDOG_RESIDENT_QUEUE_SLICE_VERIFIER_HANDLER_PHASE1",
        "worker_id": "worker:author",
        "verifier_id": "worker:verifier",
        "base_sha": "b" * 40,
        "head_sha": "a" * 40,
        "allowed_path_patterns": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/**"
        ],
        "expected_changed_paths": [ARTIFACT],
        "forbidden_path_patterns": ["**/.env", "**/secrets/**"],
        "required_checks": [
            {
                "name": "pytest",
                "argv": ["python", "-m", "pytest", "modules/communication/moltbot_bridge/tests", "-q"],
                "timeout_s": 30,
            }
        ],
        "signed_receipt_chain": _signed_receipt_chain(),
    }
    payload.update(overrides)
    return payload


def _work_order(**overrides: object) -> dict[str, object]:
    payload = {
        "work_order_id": WORK_ORDER_ID,
        "allowed_paths": [
            "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/**"
        ],
        "denied_paths": ["**/.env", "**/secrets/**"],
        "slice_verifier_plan": _slice_verifier_plan(),
        "holoindex_evidence": {
            "index_gap_detected": False,
            "holoindex_freshness_receipt_digest": _digest("b"),
        },
    }
    payload.update(overrides)
    return payload


def _binding_store(tmp_path: Path, **stage_overrides: object) -> InMemoryResidentQueueChainResultsStore:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir(exist_ok=True)
    worktree.mkdir(exist_ok=True)
    work_authority = {
        "authority_id": "authority-1",
        "work_order_id": WORK_ORDER_ID,
    }
    authority_digest = canonical_work_authority_digest(work_authority)
    return _seeded_store(
        authority_runtime={
            "decision": QUEUE_AUTHORITY_RUNTIME_INVOKE_ACCEPT,
            "authority_result": {
                "accepted": True,
                "work_authority": work_authority,
                "receipt": {
                    "receipt_id": _digest("8"),
                    "status": "DELEGATED_AUTHORITY_ISSUED",
                    "work_authority_digest": authority_digest,
                },
            }
        },
        authority_verification={
            "decision": QUEUE_AUTHORITY_VERIFICATION_INVOKE_ACCEPT,
            "verified_work_authority_digest": authority_digest,
            "verification_result": {
                "accepted": True,
                "receipt_id": _digest("c"),
            }
        },
        worktree_create={
            "decision": QUEUE_AUTHORIZED_WORKTREE_CREATE_INVOKE_ACCEPT,
            "worktree_create_result": {
                "worktree_path": str(worktree),
            }
        },
        exact_sha_commit=_exact_sha_commit_stage(str(worktree.resolve())),
        **stage_overrides,
    )


def _evidence_producer_request(tmp_path: Path, **overrides: object) -> dict[str, object]:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir(exist_ok=True)
    worktree.mkdir(exist_ok=True)
    payload = {
        **_verifier_request(),
        "explicit_evidence_production_requested": True,
        "repo_root": str(repo),
        "worktree_path": str(worktree),
        "operation_cwd": str(worktree),
        "required_checks": [
            {
                "name": "pytest",
                "argv": ["python", "-m", "pytest", "modules/communication/moltbot_bridge/tests", "-q"],
                "timeout_s": 30,
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_dispatcher_records_slice_verifier_and_advances_to_draft_pr_publish() -> None:
    chain_store = _seeded_store()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={SLICE_VERIFIER_STAGE_KEY: _handler(chain_store=chain_store)},
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.decision == RESIDENT_QUEUE_NEXT_STAGE_DISPATCH_ACCEPT
    assert result.dispatched_stage == SLICE_VERIFIER_STAGE_KEY
    assert result.next_action == NEXT_QUEUE_VERIFIED_DRAFT_PR_PUBLISH_INVOKE
    stage = chain_store.load()["stage_results"][SLICE_VERIFIER_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["verifier_result"]["receipt"]["changed_paths"] == [ARTIFACT]
    assert stage["no_command_execution_performed"] is True
    assert stage["no_github_call_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True


def test_renewed_verifier_binds_terminal_receipt_to_admission_digest() -> None:
    chain_store = _seeded_store()
    precise_now = datetime(
        2026, 7, 14, 0, 0, 0, 900000, tzinfo=timezone.utc
    )

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            SLICE_VERIFIER_STAGE_KEY: _handler(
                chain_store=chain_store,
                assurance_reservation_store=_RenewedReservationStore(),
                trusted_now=precise_now,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    stage = chain_store.load()["stage_results"][SLICE_VERIFIER_STAGE_KEY]
    receipt = stage["verifier_result"]["receipt"]
    assert receipt["assurance_reservation_digest"] == _digest("0")
    completion = stage["assurance_completion_request"]
    assert completion["reservation_id"] == _reservation()["reservation_id"]
    assert completion["admission_reservation_digest"] == _digest("0")
    assert completion["verifier_task_id"] == _reservation()["verifier_task_id"]
    assert completion["terminal_receipt_id"] == receipt["receipt_id"]
    assert completion["terminal_status"] == "ACCEPT"
    assert completion["completed_at"] == precise_now.isoformat()


def test_missing_bounded_worker_stage_rejects_direct_handler_call() -> None:
    handler = _handler(
        chain_store=_seeded_store(**{BOUNDED_WORKER_PILOT_STAGE_KEY: {}}),
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_BOUNDED_WORKER_PILOT_STAGE_MISSING in result["rejection_reasons"]


def test_missing_verifier_request_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store(), verifier_request={})
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_VERIFIER_REQUEST_MISSING in result["rejection_reasons"]


def test_dispatcher_produces_independent_evidence_before_slice_verifier(tmp_path: Path) -> None:
    chain_store = _seeded_store()
    runner = _FakeEvidenceRunner()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            SLICE_VERIFIER_STAGE_KEY: _handler(
                chain_store=chain_store,
                verifier_request={},
                evidence_producer_request=_evidence_producer_request(tmp_path),
                evidence_command_runner=runner,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    assert result.dispatched_stage == SLICE_VERIFIER_STAGE_KEY
    stage = chain_store.load()["stage_results"][SLICE_VERIFIER_STAGE_KEY]
    assert stage["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT
    assert stage["evidence_producer_result"]["decision"] == EVIDENCE_PRODUCER_ACCEPT
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["verifier_result"]["receipt"]["changed_paths"] == [ARTIFACT]
    assert stage["bounded_evidence_command_execution_performed"] is True
    assert stage["no_command_execution_performed"] is False
    assert stage["no_shell_command_executed"] is True
    assert stage["no_github_call_performed"] is True
    assert stage["no_pr_publish_performed"] is True
    assert stage["no_merge_performed"] is True
    assert stage["no_pattern_memory_write_performed"] is True
    assert stage["no_reward_settlement_performed"] is True
    assert stage["no_holoindex_reindex_performed"] is True
    assert ("git", "rev-parse", "HEAD") in runner.calls


def test_handler_derives_evidence_request_from_resident_queue_chain(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    chain_store = _binding_store(tmp_path)
    resolver = _Resolver(_work_order())
    runner = _FakeEvidenceRunner()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            SLICE_VERIFIER_STAGE_KEY: _handler(
                chain_store=chain_store,
                verifier_request={},
                evidence_producer_request={},
                evidence_command_runner=runner,
                work_order_resolver=resolver,
                repo_root=repo,
                slice_verifier_request_binding_enabled=True,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is True
    stage = chain_store.load()["stage_results"][SLICE_VERIFIER_STAGE_KEY]
    binding = stage["slice_verifier_request_binding_result"]
    assert binding["accepted"] is True
    request = binding["evidence_producer_request"]
    assert request["explicit_evidence_production_requested"] is True
    assert request["expected_changed_paths"] == [ARTIFACT]
    assert request["worktree_receipt"]["receipt_id"] == "bounded_wt_pilot_1234"
    assert request["bounded_worker_pilot_receipt"]["written_artifacts"] == [ARTIFACT]
    assert stage["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_ACCEPT
    assert stage["evidence_producer_result"]["decision"] == EVIDENCE_PRODUCER_ACCEPT
    assert stage["verifier_result"]["decision"] == AUTONOMOUS_SLICE_VERIFIER_ACCEPT
    assert stage["bounded_evidence_command_execution_performed"] is True
    assert stage["no_shell_command_executed"] is True
    assert resolver.calls == [
        {
            "work_order_id": WORK_ORDER_ID,
            "queue_item_id": "queue-1",
            "selected_slice": "REDDOG_TEST_SLICE_PHASE1",
        }
    ]


def test_handler_rejects_binding_failure_before_evidence_runner(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    chain_store = _binding_store(tmp_path)
    resolver = _Resolver(_work_order(slice_verifier_plan={}))
    runner = _FakeEvidenceRunner()
    handler = _handler(
        chain_store=chain_store,
        verifier_request={},
        evidence_producer_request={},
        evidence_command_runner=runner,
        work_order_resolver=resolver,
        repo_root=repo,
        slice_verifier_request_binding_enabled=True,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_SLICE_VERIFIER_REQUEST_BINDING_REJECTED in result["rejection_reasons"]
    assert FAIL_SLICE_VERIFIER_PLAN_MISSING in result["rejection_reasons"]
    assert result["slice_verifier_request_binding_result"]["accepted"] is False
    assert runner.calls == []


def test_rehashed_authority_stage_rejects_before_evidence_runner(
    tmp_path: Path,
) -> None:
    chain_store = _seeded_store()
    state = chain_store.load()
    authority_result = state["stage_results"]["authority_runtime"][
        "authority_result"
    ]
    work_authority = authority_result["work_authority"]
    work_authority["memex_supply_receipt_id"] = "memex-supply-attacker"
    work_authority["memex_supply_digest"] = _digest("7")
    authority_result["receipt"][
        "work_authority_digest"
    ] = canonical_work_authority_digest(work_authority)
    chain_store = InMemoryResidentQueueChainResultsStore(state)
    runner = _FakeEvidenceRunner()
    handler = _handler(
        chain_store=chain_store,
        verifier_request={},
        evidence_producer_request=_evidence_producer_request(tmp_path),
        evidence_command_runner=runner,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_SIGNED_AUTHORITY_BINDING_MISMATCH in result["rejection_reasons"]
    assert runner.calls == []


def test_rejected_evidence_producer_blocks_verifier(tmp_path: Path) -> None:
    handler = _handler(
        chain_store=_seeded_store(),
        verifier_request={},
        evidence_producer_request=_evidence_producer_request(
            tmp_path,
            holoindex_evidence={
                "index_gap_detected": True,
                "holoindex_freshness_receipt_digest": "sha256:" + "b" * 64,
            },
        ),
        evidence_command_runner=_FakeEvidenceRunner(),
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_EVIDENCE_PRODUCER_REJECTED in result["rejection_reasons"]
    assert FAIL_HOLOINDEX_EVIDENCE in result["rejection_reasons"]
    assert result["verifier_result"] is None
    assert result["evidence_producer_result"]["accepted"] is False


def test_evidence_producer_request_requires_explicit_runner(tmp_path: Path) -> None:
    handler = _handler(
        chain_store=_seeded_store(),
        verifier_request={},
        evidence_producer_request=_evidence_producer_request(tmp_path),
        evidence_command_runner=None,
    )
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_EVIDENCE_COMMAND_RUNNER_MISSING in result["rejection_reasons"]
    assert result["verifier_result"] is None


def test_wrong_stage_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=BOUNDED_WORKER_PILOT_STAGE_KEY,
        next_action=NEXT_QUEUE_SLICE_VERIFIER_INVOKE,
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_DISPATCH_STAGE_MISMATCH in result["rejection_reasons"]


def test_wrong_next_action_rejects_direct_handler_call() -> None:
    handler = _handler(chain_store=_seeded_store())
    request = ResidentQueueStageDispatchRequest(
        stage_key=SLICE_VERIFIER_STAGE_KEY,
        next_action="RUN_QUEUE_AUTHORIZED_BOUNDED_WORKER_PILOT_INVOKE",
        queue_item_id="queue-1",
        selected_slice="REDDOG_TEST_SLICE_PHASE1",
        plan_id="plan-1",
        accepted_stages=(),
    )

    result = dict(handler(request))

    assert result["decision"] == QUEUE_AUTHORIZED_SLICE_VERIFIER_INVOKE_REJECT
    assert FAIL_DISPATCH_NEXT_ACTION_MISMATCH in result["rejection_reasons"]


def test_verifier_rejection_is_not_recorded_by_dispatcher() -> None:
    request = _verifier_request()
    request["diff_evidence"]["changed_paths"] = [
        "modules/communication/moltbot_bridge/tests/fixtures/reddog_queue_pilot/OTHER.md"
    ]
    chain_store = _seeded_store()

    result = invoke_reddog_resident_queue_next_stage_dispatch(
        explicit_resident_queue_stage_dispatch_requested=True,
        work_state_snapshot=_snapshot(),
        store=chain_store,
        handlers={
            SLICE_VERIFIER_STAGE_KEY: _handler(
                chain_store=chain_store,
                verifier_request=request,
            )
        },
        now_iso=NOW_ISO,
    )

    assert result.accepted is False
    assert FAIL_RECORD_REJECTED in result.rejection_reasons
    assert QueueAuthorizedSliceVerifierInvokeReason.DIFF_PATHS_MISMATCH in result.rejection_reasons
    assert SLICE_VERIFIER_STAGE_KEY not in chain_store.load()["stage_results"]


def test_module_has_no_shell_git_openclaw_hermes_pr_reward_or_holoindex_authority() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_import_roots = {
        "subprocess",
        "os",
        "shutil",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "holo_index",
        "git",
    }
    banned_import_fragments = {
        "reddog_wre_queue_authorized_verified_draft_pr_publish_invoke",
        "reddog_wre_queue_authorized_verified_outcome_ratchet_invoke",
        "reddog_wre_queue_authorized_held_out_regression_gate_invoke",
        "reddog_wre_queue_authorized_pattern_memory_admission_invoke",
    }
    banned_calls = {"eval", "exec", "compile", "__import__", "open"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
                assert all(fragment not in alias.name for fragment in banned_import_fragments)
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
            assert all(fragment not in node.module for fragment in banned_import_fragments)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls

    forbidden_tokens = (
        "subprocess",
        "git ",
        "\ngh ",
        "openclaw_supervisor",
        "hermes_job_executor",
        "publish_verified_draft_pr(",
        "PatternMemory(",
        "store_outcome",
        "settle_reward",
        "holo_index.py --index",
    )
    for token in forbidden_tokens:
        assert token not in source
