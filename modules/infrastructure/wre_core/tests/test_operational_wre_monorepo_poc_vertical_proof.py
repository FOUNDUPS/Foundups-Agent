# -*- coding: utf-8 -*-
"""
Operational WRE monorepo-PoC vertical dry-run PROOF (W6).

Slice: OPERATIONAL_WRE_MONOREPO_POC_VERTICAL_PROOF_PHASE1

This is a VERTICAL PROOF, not new wiring. It drives ONE full dry-run
invocation end-to-end through the EXISTING OpenClaw/WRE create+drain seam
for a safe monorepo_poc FoundUp (default ``gotjunk_001``) and asserts the
entire closed-loop evidence chain in a single invocation.

The proof drives the REAL create and REAL drain entry points -- it does NOT
mock the seam and does NOT call the #786 consumer in isolation:

  REAL CREATE (OpenClaw orchestrator enqueue):
    openclaw_foundup_orchestrator.dispatch_foundup(dae=None, intent)
      -> _is_explicit_build_intent("validate foundup ...")  (True)
      -> _handle_build_intent(intent)
      -> create_job(requested_action="validate_foundup", foundup_id=...)
      -> _FOUNDUP_JOB_QUEUE.append(job)         # the real in-memory queue

  REAL DRAIN (WRE consumer over the OpenClaw queue):
    FoundUpJobConsumer.drain_openclaw_queue_with_retention(clear=False)
      -> get_job_queue()                        # the same real queue
      -> drain_jobs -> consume_one
      -> _dispatch_to_hermes
      -> execute_foundup_job(job)               # Hermes executor -> SIMULATED
      -> _attach_context_bundle_dry_run(...)    # #786/#787 dry-run wiring
      -> ConsumerResult.context_bundle_dry_run  # #775 build -> #786 DryRunResult

Action selection: ``validate_foundup`` is the ONLY canonical action that
reaches the PRE-EXISTING dry-run (SIMULATED) branch -- ``build_foundup`` /
``extract_foundup`` are blocked earlier by the destructive-action guard
(asserted in TestActionReachesSimulated). So the validate action is what
exercises the #786/#787 dry-run wiring.

Boundary discipline (no overclaim, no real execution):
  - HERMES_DELEGATE_ENABLED unset/0 for the whole module: the seam stays on
    its PRE-EXISTING dry-run branch and real Hermes delegation stays BLOCKED.
  - The ONLY mocks are the real-execution SINKS (subprocess Popen/run/call
    and the executor's real-delegate loader) asserted ``assert_not_called``
    THROUGH the full create+drain seam. The seam itself is NEVER mocked.
  - Evidence writes (the executor's PRE-EXISTING .hermes_evidence JSONs) are
    redirected to a tmp workspace via FOUNDUPS_WORKSPACE_ROOT so the proof
    leaves no repo artifact; this is the existing seam behaviour, not a new
    side effect.
  - The default FoundUp id is a PARAMETERIZED fixture (``proof_foundup``),
    not a permanent hard-code: swap the param to run for any safe
    monorepo_poc FoundUp.

NO new production code, NO new wiring, NO broadening of actions. The proof
consumes the existing path AS-IS.

WSP Compliance:
  WSP 11 : Interface contract (typed ConsumerResult + DryRunResult).
  WSP 50 : Pre-action validation (shared resolver gate before any build).
  WSP 77 : Agent coordination (WRE consumer owns dispatch; no new loop).
  WSP 97 : Truth boundaries (dry-run only, no overclaim, no real exec).
"""

from __future__ import annotations

import json
import os
import tempfile
import types
from pathlib import Path
from unittest import mock

import pytest

from modules.communication.moltbot_bridge.src import (
    openclaw_foundup_orchestrator as orchestrator,
)
from modules.communication.moltbot_bridge.src.foundup_job_contract import (
    create_job,
)
from modules.infrastructure.wre_core.src import hermes_job_executor as hje
from modules.infrastructure.wre_core.src.foundup_job_consumer import (
    ConsumerResult,
    FoundUpJobConsumer,
)

# Repo root: tests/ -> wre_core/ -> infrastructure/ -> modules/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]

# A safe monorepo_poc FoundUp whose manifest passes the #773 validator and
# whose canonical module_path is the validated source of truth.
DEFAULT_PROOF_FOUNDUP_ID = "gotjunk_001"
DEFAULT_PROOF_MODULE_PATH = "modules/foundups/gotjunk"

# A second real FoundUp used ONLY to prove cross-FoundUp payload substitution
# is rejected by the shared resolver end-to-end.
FORGED_OTHER_MODULE_PATH = "modules/foundups/kosei"

# Authority / gate-pass keys that must NEVER appear in the serialized
# context_bundle_dry_run evidence (they would imply pass-state / promotion).
_FORBIDDEN_SERIALIZED_KEYS = frozenset({
    "gate_passed", "gates_passed", "passed", "all_gates_passed",
    "security_passed", "permission_passed", "dry_run_passed", "build_passed",
    "verification_complete", "cabr_ready", "cabr_passed", "payout_ready",
    "payout_approved", "dao_ready", "dao_approved", "dao_passed",
})

# Body / content keys that must NEVER appear (no file bodies in the receipt).
_FORBIDDEN_BODY_KEYS = ('"body"', '"content"', '"source_text"', '"file_body"')


# ---------------------------------------------------------------------------
# Parameterized fixture: the proof FoundUp (default gotjunk_001, swappable).
# ---------------------------------------------------------------------------


@pytest.fixture(
    params=[(DEFAULT_PROOF_FOUNDUP_ID, DEFAULT_PROOF_MODULE_PATH)],
    ids=["gotjunk_001"],
)
def proof_foundup(request):
    """The safe monorepo_poc FoundUp under proof.

    Default param is ``gotjunk_001`` but the proof is NOT hard-coded to it:
    add a ``(foundup_id, module_path)`` tuple to ``params`` to run the whole
    vertical proof for any other safe monorepo_poc FoundUp.
    """
    foundup_id, module_path = request.param
    return types.SimpleNamespace(
        foundup_id=foundup_id,
        module_path=module_path,
    )


@pytest.fixture(autouse=True)
def _dry_run_branch_and_isolated_workspace(monkeypatch):
    """Pin the dry-run branch and isolate the seam's evidence writes.

    - HERMES_DELEGATE_ENABLED unset: the seam stays on its PRE-EXISTING
      dry-run branch (SIMULATED) and real Hermes delegation stays BLOCKED.
    - FOUNDUPS_WORKSPACE_ROOT -> a fresh tmp dir so the executor's
      PRE-EXISTING .hermes_evidence/*.json writes never touch the repo.
    - Reset the Hermes executor singleton and the in-memory job queue so each
      param runs cleanly through the real create+drain entries.
    """
    monkeypatch.delenv("HERMES_DELEGATE_ENABLED", raising=False)
    tmp_ws = tempfile.mkdtemp(prefix="w6_vertical_proof_")
    monkeypatch.setenv("FOUNDUPS_WORKSPACE_ROOT", tmp_ws)
    # Force the executor singleton to re-detect the tmp workspace root.
    monkeypatch.setattr(hje, "_executor_singleton", None, raising=False)
    orchestrator.clear_job_queue()
    yield
    orchestrator.clear_job_queue()
    monkeypatch.setattr(hje, "_executor_singleton", None, raising=False)


def _build_intent(foundup_id, *, forged_module_path=None):
    """Construct a minimal OpenClaw build intent for the REAL create path.

    ``dispatch_foundup`` reads only ``raw_message``, ``sender``,
    ``session_key`` and ``channel`` on the explicit-build branch, so a
    SimpleNamespace is a faithful stand-in for an inbound intent. The message
    is natural language ("validate foundup <id> --dry-run") -- the same intake
    a real OpenClaw chat prompt would carry -- so action/foundup_id/dry-run
    are extracted by the REAL orchestrator, not injected by the test.
    """
    return types.SimpleNamespace(
        raw_message=f"validate foundup {foundup_id} --dry-run",
        sender="tenant_w6",
        session_key="w6_proof_session",
        channel="w6_proof_channel",
    )


def _create_via_real_openclaw_entry(foundup_id):
    """Drive the REAL OpenClaw create/enqueue entry and return the queued job.

    Asserts the real orchestrator -- not the test -- produced a QUEUED
    validate_foundup job for ``foundup_id`` and appended it to the real queue.
    """
    response = orchestrator.dispatch_foundup(None, _build_intent(foundup_id))
    assert "FoundUpJob created" in response
    queue = orchestrator.get_job_queue()
    assert len(queue) == 1, "real OpenClaw entry must enqueue exactly one job"
    job = queue[0]
    assert job.requested_action == "validate_foundup"
    assert job.foundup_id == foundup_id
    assert job.status.value == "queued"
    return job


def _drain_via_real_wre_entry():
    """Drive the REAL WRE drain entry over the OpenClaw queue, return result.

    Uses ``drain_openclaw_queue_with_retention`` (the real queue drain) which
    pulls ``get_job_queue()`` and runs each job through ``consume_one`` ->
    ``_dispatch_to_hermes``. ``clear=False`` keeps the queue inspectable.
    """
    consumer = FoundUpJobConsumer(dry_run=True)
    drain_result = consumer.drain_openclaw_queue_with_retention(clear=False)
    assert len(drain_result.results) == 1, "drain must consume the one job"
    return drain_result.results[0]


# ===========================================================================
# Action-reaches-SIMULATED control: validate_foundup is the dry-run action.
# ===========================================================================


class TestActionReachesSimulated:
    def test_validate_reaches_simulated_build_extract_blocked(self, proof_foundup):
        """validate_foundup reaches SIMULATED; build/extract are guard-blocked.

        Proves WHICH action exercises the #786/#787 dry-run wiring: only the
        validate action reaches the PRE-EXISTING SIMULATED branch.
        """
        statuses = {}
        for action in ("validate_foundup", "build_foundup", "extract_foundup"):
            job = create_job(
                tenant_id="tenant_w6",
                requested_action=action,
                foundup_id=proof_foundup.foundup_id,
                payload={},
            )
            statuses[action] = hje.execute_foundup_job(job).status.value
            # Reset singleton between calls (workspace stays isolated).
            hje._executor_singleton = None

        assert statuses["validate_foundup"] == "SIMULATED"
        assert statuses["build_foundup"] == "BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD"
        assert statuses["extract_foundup"] == "BLOCKED_BY_DESTRUCTIVE_ACTION_GUARD"


# ===========================================================================
# THE vertical proof: every acceptance item asserted in ONE invocation.
# ===========================================================================


class TestOperationalWREMonorepoPoCVerticalProof:
    def test_full_dry_run_invocation_end_to_end(self, proof_foundup):
        """One full dry-run invocation through the REAL create+drain seam.

        Every acceptance item is asserted in this single run. The real-exec
        sinks are mocked ONLY to prove they are never called; the seam itself
        (create entry, drain entry, dispatch, executor, #786 consumer) runs
        for real.
        """
        foundup_id = proof_foundup.foundup_id
        expected_module_path = proof_foundup.module_path

        # --- ACCEPTANCE: real-exec sinks must never fire THROUGH the seam. ---
        # subprocess.* and the executor's real-delegate loader are patched and
        # asserted not-called across the ENTIRE create+drain path. These are
        # the only mocks; the seam is real.
        with mock.patch("subprocess.Popen") as m_popen, \
                mock.patch("subprocess.run") as m_run, \
                mock.patch("subprocess.call") as m_call, \
                mock.patch(
                    "modules.infrastructure.wre_core.src.hermes_job_executor."
                    "HermesJobExecutor._lazy_import_delegate_task",
                    side_effect=AssertionError(
                        "real delegate loader must not run in dry-run"
                    ),
                ) as m_delegate:

            # --- ACCEPTANCE: the OpenClaw/WRE path CREATES a FoundUp job
            #     (real entry, not mocked). ---
            job = _create_via_real_openclaw_entry(foundup_id)
            assert job.policy_flags.dry_run_mode is True
            # The real create entry built the payload itself; it carries NO
            # module_path -- so the resolver MUST derive it from the manifest.
            assert "module_path" not in job.payload
            assert "source_module" not in job.payload

            # --- ACCEPTANCE: the OpenClaw/WRE path DRAINS the job
            #     (real entry, not mocked). ---
            result = _drain_via_real_wre_entry()

            # The real-exec sinks were never reached on the dry-run path.
            m_popen.assert_not_called()
            m_run.assert_not_called()
            m_call.assert_not_called()
            m_delegate.assert_not_called()

        # The drained result is the EXISTING typed receipt.
        assert isinstance(result, ConsumerResult)
        assert result.job_id == job.job_id
        assert result.dispatched is True

        # --- ACCEPTANCE: the existing dispatch seam took the DRY-RUN branch
        #     (SIMULATED, real_execution_performed False). ---
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False

        cb = result.context_bundle_dry_run
        assert cb is not None, "dry-run evidence must attach on the dry-run branch"

        # --- ACCEPTANCE: a ContextBundle is BUILT (#775) and the #786 consumer
        #     RAN -> DryRunResult attached to the receipt. ---
        # A populated DryRunResult (bundle_id + refs) proves both the #775
        # build_context_bundle producer and the #786
        # consume_context_bundle_dry_run consumer executed; an error
        # projection would carry context_bundle_error instead.
        assert "context_bundle_error" not in cb
        assert cb["dry_run"] is True
        assert cb["real_execution_performed"] is False
        assert isinstance(cb.get("bundle_id"), str) and cb["bundle_id"]
        assert isinstance(cb.get("consumer_version"), str) and cb["consumer_version"]

        # --- ACCEPTANCE: DryRunResult is ATTACHED to ConsumerResult / receipt
        #     and survives serialization (context_bundle_dry_run present). ---
        receipt = result.to_dict()
        assert receipt.get("context_bundle_dry_run") is not None
        assert receipt["context_bundle_dry_run"]["source_authority"] == "monorepo_poc"

        # --- ACCEPTANCE: source_authority == "monorepo_poc". ---
        assert cb["source_authority"] == "monorepo_poc"

        # --- ACCEPTANCE: module_path comes from the shared validated resolver
        #     (== validated canonical, NOT the payload). ---
        assert cb["resolved_module_path"] == expected_module_path
        # The create entry put no module_path in the payload; observable-ignore
        # confirms the resolver ran and trusted no payload candidate.
        assert cb["rejected_input"]["resolver_run"] is True
        assert cb["rejected_input"]["payload_module_path_ignored"] is None
        assert cb["rejected_input"]["resolver_failed"] is False

        # --- ACCEPTANCE: evidence_refs are refs + sha256 (+ size) ONLY. ---
        refs = cb["evidence_refs"]
        assert len(refs) >= 1
        allowed_ref_keys = {"path", "sha256", "size_bytes", "role"}
        for ref in refs:
            assert set(ref.keys()) <= allowed_ref_keys, (
                "evidence ref carries an unexpected key (possible body leak): "
                + repr(set(ref.keys()) - allowed_ref_keys)
            )
            assert isinstance(ref["sha256"], str) and len(ref["sha256"]) == 64
            assert isinstance(ref["size_bytes"], int)

        # --- ACCEPTANCE: NO file bodies anywhere in the receipt. ---
        # The body check covers the WHOLE receipt; no file body may appear
        # anywhere in the serialized ConsumerResult.
        receipt_blob = json.dumps(receipt)
        for body_key in _FORBIDDEN_BODY_KEYS:
            assert body_key not in receipt_blob, (
                "file body leaked into receipt: " + body_key
            )

        # --- ACCEPTANCE: no gate-pass / pass-state key leaked into the
        #     dry-run EVIDENCE. ---
        # The pass-state scan targets the context_bundle_dry_run evidence blob
        # (cb), NOT the whole ConsumerResult: the receipt legitimately carries
        # the EXISTING WSP 97 truth fields (verification_complete / cabr_ready
        # / payout_ready) -- all False -- which are truth boundaries, not
        # pass-state. The dry-run evidence must never imply pass-state.
        cb_blob = json.dumps(cb)
        for forbidden in _FORBIDDEN_SERIALIZED_KEYS:
            assert ('"' + forbidden + '"') not in cb_blob, (
                "forbidden pass-state key leaked into dry-run evidence: "
                + forbidden
            )
        # gates are NAMES to re-check, never pass-state booleans.
        gates = cb["gates_to_recheck"]
        assert isinstance(gates, list) and len(gates) >= 1
        for gate in gates:
            assert isinstance(gate, str) and not isinstance(gate, bool)

        # --- ACCEPTANCE: readiness flags remain False. ---
        readiness = cb["readiness_flags"]
        assert len(readiness) >= 1
        for name, value in readiness.items():
            assert value is False, "readiness flag promoted: " + name

        # --- ACCEPTANCE: the EXISTING WSP 97 truth fields stay False. ---
        assert receipt["verification_complete"] is False
        assert receipt["cabr_ready"] is False
        assert receipt["payout_ready"] is False

        # --- planned actions are declared-only, never executed. ---
        for action in cb["planned_actions"]:
            assert action["executed"] is False


# ===========================================================================
# NEGATIVE through the FULL seam: forged module_path fails end-to-end.
# ===========================================================================


class TestForgedModulePathFailsEndToEnd:
    def test_forged_cross_foundup_module_path_rejected_via_seam(self, proof_foundup):
        """A forged module_path on the queued job FAILS through the full seam.

        A forged job arrives in the real OpenClaw queue carrying a
        cross-FoundUp ``module_path``. Draining it through the REAL WRE entry
        still reaches SIMULATED, but the shared resolver REJECTS the forged
        path end-to-end: no preview is produced, the rejected value is
        observable, and it is NEVER used as the resolved module_path.

        Real-exec sinks are asserted not-called here too: rejection happens
        on the dry-run path, never via real execution.
        """
        foundup_id = proof_foundup.foundup_id

        with mock.patch("subprocess.Popen") as m_popen, \
                mock.patch("subprocess.run") as m_run, \
                mock.patch("subprocess.call") as m_call, \
                mock.patch(
                    "modules.infrastructure.wre_core.src.hermes_job_executor."
                    "HermesJobExecutor._lazy_import_delegate_task",
                    side_effect=AssertionError(
                        "real delegate loader must not run in dry-run"
                    ),
                ) as m_delegate:

            # Real create entry -> queued job for foundup_id.
            job = _create_via_real_openclaw_entry(foundup_id)
            # Forge a cross-FoundUp module_path on the queued job (a forged job
            # landing in the queue). The shared resolver must reject it.
            assert FORGED_OTHER_MODULE_PATH != proof_foundup.module_path
            job.payload["module_path"] = FORGED_OTHER_MODULE_PATH

            # Real drain entry over the queue.
            result = _drain_via_real_wre_entry()

            m_popen.assert_not_called()
            m_run.assert_not_called()
            m_call.assert_not_called()
            m_delegate.assert_not_called()

        # Seam still took the dry-run branch...
        assert result.checkpoint_state == "SIMULATED"
        assert result.real_execution_performed is False

        cb = result.context_bundle_dry_run
        assert cb is not None
        # ...but the forged path was REJECTED by the shared resolver.
        assert cb.get("context_bundle_error") == "module_path_resolution_failed"
        assert cb.get("fail_token") == "cross_foundup_mismatch"
        # The forged value is observable (never used as the resolved path).
        assert cb.get("payload_module_path_ignored") == FORGED_OTHER_MODULE_PATH
        assert cb.get("resolved_module_path") is None

        # No file bodies anywhere in the receipt on the negative path.
        receipt_blob = json.dumps(result.to_dict())
        for body_key in _FORBIDDEN_BODY_KEYS:
            assert body_key not in receipt_blob
        # No pass-state key in the dry-run evidence blob (cb); the receipt's
        # EXISTING WSP 97 truth fields are out of scope for this scan.
        cb_blob = json.dumps(cb)
        for forbidden in _FORBIDDEN_SERIALIZED_KEYS:
            assert ('"' + forbidden + '"') not in cb_blob
