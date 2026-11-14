"""A whole effect-review set under one inert lease, with actual test signatures."""

from contextlib import contextmanager
from dataclasses import asdict
import importlib
import inspect
import pytest

from modules.communication.moltbot_bridge.tests.reddog_reviewer_quorum_test_support import (
    ROOT, after_reviews, closed, during_owner_reread, during_finish_clock, expire_at_finish, lookup, mutate_input,
    positive, quorum_setup, refresh, reset, setup, sign,
)
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import assert_closed


def test_current_quorum_public_api_exposes_only_bound_inputs():
    api = importlib.import_module(ROOT + "reddog_elevated_authority_consensus_verification")
    verify = getattr(api, "verify_current_effect_reviewer_decisions", None)
    assert callable(verify), "verify_current_effect_reviewer_decisions_api_missing"
    expected = {"owner_config_path", "repo_root", "decisions", "context", "authority_request", "target",
                "expected_target", "policy", "runtime_evidence_resolver", "revoked_key_epochs"}
    params = inspect.signature(verify).parameters
    assert set(params) == expected and all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())
    assert params["revoked_key_epochs"].default == frozenset()


@pytest.mark.parametrize("case", ["list", "tuple", "last_current"])
def test_current_quorum_one_lease_exact_crypto_and_runtime_samples(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    if case == "tuple":
        state.call["decisions"] = tuple(state.call["decisions"])
    elif case == "last_current":
        state.now = 1019
    positive(verify, state)


@pytest.mark.parametrize("case", ["key_0", "key_1", "runtime_0", "runtime_1", "manifest", "selection",
                                  "owner", "designation", "context", "rollback"])
def test_current_quorum_rechecks_all_lifetimes_at_finish(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    positive(verify, state)
    reset(state)
    expire_at_finish(state, case)
    assert verify(**state.call) is False
    assert len(state.crypto) == 3 and all(c[3] is True for c in state.crypto)
    assert state.records.calls == [lookup(d) for d in state.call["decisions"]]
    closed(state)


@pytest.mark.parametrize("case", ["first", "second", "aliased"])
def test_current_quorum_retains_every_evidence_reference_and_snapshot(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    positive(verify, state)
    reset(state)
    if case == "aliased":
        actual = state.records.resolve

        def resolve(*args):
            result = actual(*args)
            if len(state.records.calls) == 2:
                for name, value in asdict(result).items():
                    object.__setattr__(state.evidence[0], name, value)
                return state.evidence[0]
            return result

        monkeypatch.setattr(state.records, "resolve", resolve)
    else:
        index = 0 if case == "first" else 1
        after_reviews(state, lambda s: object.__setattr__(s.evidence[index], "expires_at", 1021))
    assert verify(**state.call) is False
    assert len(state.records.calls) == 2 and len(state.crypto) == 3
    closed(state)


@pytest.mark.parametrize("case", ["decision", "append", "reorder", "policy", "target", "finish_clock"])
def test_current_quorum_rechecks_inputs_after_owner_reread(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    positive(verify, state)
    reset(state)

    seam = during_finish_clock if case == "finish_clock" else during_owner_reread
    seam(monkeypatch, state, lambda s: mutate_input(s, case))
    assert verify(**state.call) is False
    assert state.reads == 2 and len(state.crypto) == 3
    closed(state)


@pytest.mark.parametrize("case", ["owner_changed", "owner_removed", "owner_read_error", "wrong_owner",
                                  "lease_enter", "lease_exit", "key_close"])
def test_current_quorum_owner_lease_and_cleanup_fail_closed(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    positive(verify, state)
    reset(state)
    if case == "owner_changed":
        after_reviews(state, lambda s: s.owner.update(config_id="sha256:" + "e" * 64))
    elif case == "owner_removed":
        after_reviews(state, lambda s: s.owner.pop("reviewer_designation_authority"))
    elif case == "owner_read_error":
        after_reviews(state, lambda s: setattr(s, "owner_error", True))
    elif case == "wrong_owner":
        state.selection["owner_config_id"] = "sha256:" + "e" * 64
    elif case == "lease_enter":
        state.lease_error = True
    elif case == "key_close":
        state.close_error = True
    else:
        actual = state.lease._lease_current

        @contextmanager
        def lease(token):
            with actual(token) as selection:
                yield selection
            raise RuntimeError("inert lease-exit rejection")

        monkeypatch.setattr(state.lease, "_lease_current", lease)
    assert verify(**state.call) is False
    closed(state)


@pytest.mark.parametrize("case", ["signature", "domain", "role", "principal_key", "revoked", "missing", "resolver_error"])
def test_current_quorum_invalid_second_review_rejects_whole_set(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    positive(verify, state)
    reset(state)
    second = state.call["decisions"][1]
    if case == "signature":
        second["decision_id"] = "changed-after-signing"
    elif case == "domain":
        sign(second, state.second_key, "reddog-elevated-consensus-review.v1.")
    elif case == "role":
        state.designation["reviewers"][1]["authorized_roles"] = ["critic"]
        refresh(state)
    elif case == "principal_key":
        state.artifact["principals"]["test|reviewer:second"]["principal_public_key"] = "different-key"
        refresh(state)
    elif case == "revoked":
        state.call["revoked_key_epochs"] = frozenset({second["reviewer_key_epoch"]})
    elif case == "missing":
        state.records.records.pop(lookup(second))
    else:
        state.records.error_at = 2
    assert verify(**state.call) is False
    closed(state)


def test_current_quorum_interrupt_still_closes_projection_and_lease(monkeypatch, tmp_path):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    positive(verify, state)
    reset(state)
    failure = KeyboardInterrupt("inert interrupt")

    def interrupt(s):
        raise failure

    after_reviews(state, interrupt)
    with pytest.raises(KeyboardInterrupt) as caught:
        verify(**state.call)
    assert caught.value is failure
    closed(state)


@pytest.mark.parametrize("case", ["unchanged", "final_owner_mutation"])
def test_current_single_api_preserved_and_final_input_gap_closed(monkeypatch, tmp_path, case):
    verify, state = setup(monkeypatch, tmp_path)
    if case == "final_owner_mutation":
        during_owner_reread(monkeypatch, state,
            lambda s: s.call["decision"].update(decision_id="changed-after-verification"))
    assert verify(**state.call) is (case == "unchanged")
    assert state.reads == 2 and len(state.crypto) == 2
    assert_closed(state)


@pytest.mark.parametrize("case", ["empty", "nine", "mapping", "list_subclass", "tuple_subclass", "both", "neither"])
def test_current_quorum_shape_and_mode_rejected_before_owner(monkeypatch, tmp_path, case):
    verify, state = quorum_setup(monkeypatch, tmp_path)
    values = state.call["decisions"]
    changes = {"empty": [], "nine": [values[0]] * 9, "mapping": {},
        "list_subclass": type("ListSubclass", (list,), {})(values),
        "tuple_subclass": type("TupleSubclass", (tuple,), {})(values)}
    if case in changes:
        state.call["decisions"] = changes[case]
    else:
        verify = state.runtime.verify_current_effect_review
        if case == "both":
            state.call["decision"] = values[0]
        else:
            state.call.pop("decisions")
    assert verify(**state.call) is False
    assert state.reads == state.lease.selected == state.artifact_reads == 0


def test_current_runtime_snapshot_ninth_call_rejected_before_resolver(monkeypatch, tmp_path):
    _, state = setup(monkeypatch, tmp_path)
    resolver = state.kw["runtime_evidence_resolver"]
    snapshot = state.runtime._RuntimeSnapshot(resolver)
    for index in range(8):
        snapshot.resolve("reviewer:" + str(index), "selection", "runtime")
    with pytest.raises((ValueError, RuntimeError)):
        snapshot.resolve("reviewer:8", "selection", "runtime")
    assert len(resolver.calls) == 8
