"""Connected real signatures with explicit inert owner/lease provenance seams."""

from dataclasses import replace
import importlib
import pytest

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import ROOT, digest, sign
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import (
    assert_closed, refresh, setup,
)
from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import _sync


SCOPE_CASES = ["valid", "last_current", "designation_tamper", "review_tamper", "designation_domain",
    "review_domain", "issuer_id", "issuer_provider", "issuer_epoch", "owner_digest", "repo", "foundup",
    "policy", "decision_domain", "principal_key", "principal_repo", "principal_foundup", "role_subset", "revoked_epoch"]


def _scope_change(state, case):
    grant, kw = state.designation, state.kw
    record = state.artifact["principals"]["test|reviewer:test"]
    changes = {"issuer_id": ("issuer_principal_id", "issuer:other"),
        "issuer_provider": ("issuer_principal_provider", "other"), "issuer_epoch": ("issuer_key_epoch", "other"),
        "owner_digest": ("owner_authority_digest", "sha256:" + "0" * 64),
        "repo": ("repo_full_name", "other/repo"), "foundup": ("foundup_id", "other-foundup"),
        "policy": ("policy_digest", "sha256:" + "0" * 64),
        "decision_domain": ("decision_schema_version", "reddog_elevated_authority_reviewer_decision.v1")}
    if case in changes:
        key, value = changes[case]
        grant[key] = value
    elif case.startswith("principal_"):
        field = {"principal_key": "principal_public_key", "principal_repo": "repo_scope", "principal_foundup": "foundup_scope"}[case]
        record[field] = "different-public-key" if case == "principal_key" else ["other"]
    elif case == "role_subset":
        kw["policy"] = replace(kw["policy"], reviewer_membership=(("reviewer:test", "test", "critic"),
            ("reviewer:test", "test", "verifier")))
        _sync(kw)
        state.call.update(policy=kw["policy"], context=kw["context"])
        state.authority["policy_digest"] = grant["policy_digest"] = kw["policy"].policy_digest
        grant["owner_authority_digest"] = digest(state.authority)
    elif case == "revoked_epoch":
        state.call["revoked_key_epochs"] = frozenset({"reviewer-epoch"})
    elif case == "last_current":
        state.now = 1019
    refresh(state)
    if case == "designation_domain":
        sign(grant, state.issuer, "reddog-effect-consensus-review.v1.")
    elif case == "designation_tamper":
        grant["expires_at"] -= 1
    elif case == "review_domain":
        sign(kw["decision"], state.reviewer, "reddog-elevated-consensus-review.v1.")
    elif case == "review_tamper":
        kw["decision"]["decision_id"] = "decision:changed-after-signing"
    refresh(state, sign_designation=False, sign_review=False)


@pytest.mark.parametrize("case", SCOPE_CASES)
def test_connected_real_signatures_and_scope(monkeypatch, tmp_path, case):
    verify, state = setup(monkeypatch, tmp_path)
    _scope_change(state, case)
    expected = case in {"valid", "last_current"}
    assert verify(**state.call) is expected
    assert_closed(state)
    if expected:
        assert len(state.crypto) == 2 and all(c[3] is True for c in state.crypto)
        assert state.crypto[0][1].startswith("reddog-reviewer-designation.v1.")
        assert state.crypto[1][1].startswith("reddog-effect-consensus-review.v1.")
        assert state.reads == 2 and state.lease.selected == state.lease.entered == state.lease.exited == 1


LIFETIME_CASES = ["owner_future", "owner_expired", "designation_future", "designation_expired",
    "entry_future", "entry_expired", "manifest_expired", "selection_expired", "expires_during_review",
    "owner_changed", "owner_removed", "loader_throws", "lease_throws", "runtime_throws", "mutated_inputs", "escaped_resolver"]


def _lifetime_change(state, case):
    if case.startswith(("owner_", "designation_", "entry_")) and case.endswith(("future", "expired")):
        part, action = case.split("_")
        value = {"owner": state.authority, "designation": state.designation, "entry": state.designation["reviewers"][0]}[part]
        value["issued_at" if action == "future" else "expires_at"] = 1001 if action == "future" else 1000
        state.designation["owner_authority_digest"] = digest(state.authority)
    elif case in {"manifest_expired", "selection_expired"}:
        state.selection[case.replace("_expired", "_expires_at")] = 1000
    elif case == "loader_throws":
        state.owner_error = True
    elif case == "lease_throws":
        state.lease_error = True
    elif case == "runtime_throws":
        state.kw["runtime_evidence_resolver"].error = True
    refresh(state)


def _callback(case):
    def change(state, message):
        if not message.startswith("reddog-effect-consensus-review.v1."):
            return
        if case == "expires_during_review":
            state.now = 1020
        elif case == "owner_changed":
            state.owner["config_id"] = "sha256:" + "e" * 64
        elif case == "owner_removed":
            state.owner.pop("reviewer_designation_authority")
            state.owner["config_id"] = "sha256:" + "e" * 64
        elif case == "mutated_inputs":
            state.call["expected_target"]["unexpected_mutation"] = True
    return change


@pytest.mark.parametrize("case", LIFETIME_CASES)
def test_connected_lifetime_and_cleanup(monkeypatch, tmp_path, case):
    verify, state = setup(monkeypatch, tmp_path)
    _lifetime_change(state, case)
    state.callback = _callback(case)
    if case == "escaped_resolver":
        api = importlib.import_module(ROOT + "reddog_elevated_authority_consensus_verification")
        actual = api.verify_effect_reviewer_decision

        def observe(**kwargs):
            state.captured_resolver = kwargs["reviewer_key_resolver"]
            return actual(**kwargs)

        monkeypatch.setattr(api, "verify_effect_reviewer_decision", observe)
    assert verify(**state.call) is (case == "escaped_resolver")
    assert_closed(state)
    if case == "escaped_resolver":
        assert state.captured_resolver is not None
        try:
            result = state.captured_resolver.resolve("reviewer:test", "test")
        except (ValueError, RuntimeError):
            result = None
        assert result is None
    if case in {"expires_during_review", "owner_changed", "owner_removed", "mutated_inputs"}:
        assert len(state.crypto) == 2 and all(c[3] is True for c in state.crypto)
