"""Real crypto with explicitly substituted protected owner and generation leases."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
import inspect

import pytest

from modules.communication.moltbot_bridge.tests.reddog_parent_consent_test_support import (
    setup, positive, closed, replace_parent, resign, contract, runtime,
)


def test_parent_consent_actual_crypto_current_generation(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    positive(resolve, state)
    assert set(inspect.signature(resolve).parameters) == {"owner_config_path", "repo_root", "assertion", "parent", "policy"}


@pytest.mark.parametrize("field,value", [
    ("work_order_id", "other"), ("work_order_digest", "sha256:" + "9" * 64),
    ("base_ref", "other"), ("allowed_paths", ("other",)), ("requested_operation", "write_repo"),
    ("principal_id", "other"), ("principal_provider", "other"), ("reddog_id", "other"),
    ("key_epoch", "other"), ("repo_full_name", "other/repo"), ("foundup_id", "other"),
    ("model_selection_digest", "sha256:" + "9" * 64),
    ("model_runtime_binding_digest", "sha256:" + "9" * 64),
    ("model_runtime_binding_verification_digest", "sha256:" + "9" * 64),
    ("work_authority_expires_at", 999), ("identity_expires_at", True), ("issued_at", 1001),
])
def test_parent_consent_rejects_request_rebinding(monkeypatch, tmp_path, field, value):
    resolve, state = setup(monkeypatch, tmp_path)
    replace_parent(state, **{field: value})
    assert resolve(**state.call) is None
    closed(state)


@pytest.mark.parametrize("field", sorted(contract.CURRENT_FIELDS))
def test_parent_consent_cannot_cross_current_generation(monkeypatch, tmp_path, field):
    resolve, state = setup(monkeypatch, tmp_path)
    old = state.selection[field]
    state.selection[field] = old + 1 if type(old) is int else "sha256:" + "8" * 64
    assert resolve(**state.call) is None
    closed(state)


@pytest.mark.parametrize("case", ["missing", "legacy", "rotation", "epoch", "withdrawal", "privilege", "policy"])
def test_parent_consent_registration_is_explicit_and_revocable(monkeypatch, tmp_path, case):
    resolve, state = setup(monkeypatch, tmp_path)
    if case == "missing":
        state.owner.pop("parent_consent_authority")
    elif case == "legacy":
        state.owner["schema_version"] = state.loader.SCHEMA_VERSION_V10
    elif case == "withdrawal":
        state.owner["parent_consent_authority"] = None
    else:
        field, value = {"rotation": ("issuer_public_key", state.parent.reddog_public_key),
            "epoch": ("issuer_key_epoch", "rotated"), "privilege": ("privilege", "authorize_exact_high_worktree_effect"),
            "policy": ("policy_digest", "sha256:" + "8" * 64)}[case]
        state.authority[field] = value
    assert resolve(**state.call) is None
    closed(state)


@pytest.mark.parametrize("case", ["input", "owner", "selection", "records", "expiry", "rollback", "artifact"])
def test_parent_consent_final_drift_rejected(monkeypatch, tmp_path, case):
    resolve, state = setup(monkeypatch, tmp_path)
    def drift(s):
        if case == "input": s.assertion["policy_digest"] = "sha256:" + "7" * 64
        elif case == "owner": s.owner["parent_consent_authority"]["issuer_key_epoch"] = "rotated"
        elif case == "selection": s.selection["generation"] += 1
        elif case == "records": s.loaded_records.clear()
        elif case == "expiry": s.now = 1020
        elif case == "rollback": s.now = 999
        elif case == "artifact": (s.store / "principal_authority_records.json").write_bytes(b"{}")
    state.callback = drift
    assert resolve(**state.call) is None
    closed(state)


def test_parent_consent_lease_exit_rejection_withholds_evidence(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    original = state.lease._lease_current
    @contextmanager
    def rejecting_exit(token):
        with original(token) as selected:
            yield selected
            raise ValueError("synthetic lease exit revocation")
    monkeypatch.setattr(state.lease, "_lease_current", rejecting_exit)
    assert resolve(**state.call) is None
    closed(state)


def test_parent_consent_proof_backreferences_stay_excluded(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    replace_parent(state, sovereign_authorization_digest=None, consensus_receipt_digest=None)
    positive(resolve, state)


def _other_policy(policy):
    from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import elevated_consensus_policy_digest
    other = replace(policy, policy_receipt_id="elevated-consensus-policy:other")
    return replace(other, policy_digest=elevated_consensus_policy_digest(other))


def test_parent_consent_rejects_actual_other_policy(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    state.call["policy"] = _other_policy(state.call["policy"])
    assert resolve(**state.call) is None
    closed(state)


def test_parent_consent_policy_restriction_survives_existing_consensus_boundary(monkeypatch, tmp_path):
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_contract as wire
    from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import SovereignAuthorizationEvidence
    from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_evidence import consensus_receipt_matches
    from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import _case
    resolve, state = setup(monkeypatch, tmp_path)
    evidence = positive(resolve, state)
    policy = _other_policy(state.call["policy"])
    _, sample = _case(monkeypatch)
    decision = wire.ElevatedAuthorityReviewerDecision(**sample["decision"])
    context = wire.ElevatedAuthorityConsensusContext(wire.CONSENSUS_SCHEMA_VERSION,
        evidence.authority_request_digest, evidence.authorization_digest, policy.policy_digest,
        (), policy.minimum_approvals, policy.required_roles, "test-only", 1000, 1020)
    receipt = wire.ElevatedAuthorityConsensusReceipt(wire.CONSENSUS_SCHEMA_VERSION, "pending", context,
                                                    (decision,) * policy.minimum_approvals)
    receipt = replace(receipt, receipt_id=wire.canonical_consensus_receipt_digest(receipt))
    parent = replace(state.parent, sovereign_authorization_digest=evidence.authorization_digest,
                     consensus_receipt_digest=receipt.receipt_id)
    args = (receipt, parent, evidence.authority_request_digest, policy)
    # The legacy shape would erase the policy-A restriction; demonstrate this exact seam.
    legacy = SovereignAuthorizationEvidence(**{k: v for k, v in asdict(evidence).items()
                                               if k != "consensus_policy_digest"})
    assert consensus_receipt_matches(*args, legacy, 1000) is True
    assert consensus_receipt_matches(*args, evidence, 1000) is False
    assert evidence.consensus_policy_digest != policy.policy_digest


@pytest.mark.parametrize("role,field,value", [
    ("issuer", "principal_id", "other"), ("beneficiary", "principal_provider", "other"),
    ("issuer", "principal_public_key", "other"), ("beneficiary", "repo_scope", []),
    ("issuer", "foundup_scope", []),
])
def test_parent_consent_current_principal_tuple_and_key_required(monkeypatch, tmp_path, role, field, value):
    from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import refresh
    resolve, state = setup(monkeypatch, tmp_path)
    key = state.authority[role + "_principal_provider"] + "|" + state.authority[role + "_principal_id"]
    state.artifact["principals"][key][field] = value
    refresh(state)
    assert resolve(**state.call) is None
    closed(state)


@pytest.mark.parametrize("value", [999, 1020, True, -1])
def test_parent_consent_clock_boundaries(monkeypatch, tmp_path, value):
    resolve, state = setup(monkeypatch, tmp_path)
    state.now = value
    assert resolve(**state.call) is None
    closed(state)


def test_parent_consent_initial_snapshot_precedes_clock_callback(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    def mutate(s):
        s.assertion['issued_at'] = 999
        s.clock_callback = None
    state.clock_callback = mutate
    assert resolve(**state.call) is None
    closed(state)


def test_parent_consent_final_policy_snapshot_cannot_drift(monkeypatch, tmp_path):
    resolve, state = setup(monkeypatch, tmp_path)
    def mutate(s):
        object.__setattr__(s.call['policy'], 'policy_receipt_id', 'elevated-consensus-policy:changed')
    state.callback = mutate
    assert resolve(**state.call) is None
    closed(state)
