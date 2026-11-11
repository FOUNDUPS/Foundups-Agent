"""Real disposable signatures; inert current-owner/lease and runtime evidence."""

from dataclasses import replace
import importlib

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, Ed25519PrivateKey, canonical, digest, public, sign,
)
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import (
    assert_closed, refresh, setup,
)
from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import _preimage


class RuntimeRecords:
    def __init__(self, state, records):
        self.state, self.records, self.calls, self.error_at = state, records, [], None

    def resolve(self, *args):
        assert self.state.lease.active
        assert args not in self.calls, "runtime evidence must not be reread"
        self.calls.append(args)
        if len(self.calls) == self.error_at:
            raise RuntimeError("inert runtime rejection")
        return self.records.get(args)


def quorum_setup(monkeypatch, tmp_path):
    _, state = setup(monkeypatch, tmp_path)
    second_key = Ed25519PrivateKey.generate()
    first = state.kw["decision"]
    second = dict(first, decision_id="decision:second", reviewer_principal_id="reviewer:second",
        reviewer_public_key=public(second_key), reviewer_key_epoch="reviewer-second-epoch",
        reviewer_role="verifier", reviewer_model_id="model:second", model_selection_receipt_id="selection:second",
        model_selection_digest="sha256:" + "6" * 64, model_runtime_binding_receipt_id="runtime:second",
        model_runtime_binding_digest="sha256:" + "7" * 64)
    state.designation["reviewers"].append(dict(state.designation["reviewers"][0],
        principal_id=second["reviewer_principal_id"], public_key=second["reviewer_public_key"],
        key_epoch=second["reviewer_key_epoch"], authorized_roles=["verifier"]))
    record = dict(state.artifact["principals"]["test|reviewer:test"], principal_id="reviewer:second",
        principal_public_key=second["reviewer_public_key"])
    state.artifact["principals"]["test|reviewer:second"] = record
    state.artifact["principal_count"] = 2
    state.call.pop("decision")
    state.call["decisions"] = [first, second]
    state.call["revoked_key_epochs"] = frozenset()
    first_evidence = state.kw["runtime_evidence_resolver"].value
    state.evidence = [first_evidence, replace(first_evidence, reviewer_model_id=second["reviewer_model_id"],
        model_selection_receipt_id=second["model_selection_receipt_id"], model_selection_digest=second["model_selection_digest"],
        model_runtime_binding_receipt_id=second["model_runtime_binding_receipt_id"],
        model_runtime_binding_digest=second["model_runtime_binding_digest"])]
    state.records = RuntimeRecords(state, {lookup(d): e for d, e in zip(state.call["decisions"], state.evidence)})
    state.call["runtime_evidence_resolver"] = state.records
    state.second_key = second_key
    state.projected, state.close_calls, state.artifact_reads, state.close_error = [], 0, 0, False
    _observe_resources(monkeypatch, state)
    refresh(state)
    sign(second, second_key, "reddog-effect-consensus-review.v1.")
    api = importlib.import_module(ROOT + "reddog_elevated_authority_consensus_verification")
    verify = getattr(api, "verify_current_effect_reviewer_decisions", None)
    assert callable(verify), "verify_current_effect_reviewer_decisions_api_missing"
    return verify, state


def lookup(decision):
    return (decision["reviewer_principal_id"], decision["model_selection_receipt_id"],
            decision["model_runtime_binding_receipt_id"])


def _observe_resources(monkeypatch, state):
    original = state.runtime._project_reviewer_keys
    load = state.runtime.principals.load_current_generation_principal_artifact

    def project(**kwargs):
        assert state.lease.active
        keys = original(**kwargs)
        close = keys.close

        def close_once():
            assert state.lease.active
            state.close_calls += 1
            close()
            if state.close_error:
                raise RuntimeError("inert key-close failure after clearing")

        keys.close = close_once
        state.projected.append(keys)
        return keys

    def read(**kwargs):
        assert state.lease.active
        state.artifact_reads += 1
        return load(**kwargs)

    monkeypatch.setattr(state.runtime, "_project_reviewer_keys", project)
    monkeypatch.setattr(state.runtime.principals, "load_current_generation_principal_artifact", read)


def closed(state):
    assert_closed(state)
    assert state.artifact_reads <= 1
    assert state.close_calls == len(state.projected)
    for keys in state.projected:
        for decision in state.call["decisions"]:
            assert keys.resolve(decision["reviewer_principal_id"], decision["reviewer_principal_provider"]) is None


def positive(verify, state):
    assert verify(**state.call) is True
    closed(state)
    assert state.reads == 2 and state.artifact_reads == 1 and state.close_calls == 1
    assert state.lease.selected == state.lease.entered == state.lease.exited == 1
    assert state.records.calls == [lookup(d) for d in state.call["decisions"]]
    grant = state.designation
    expected = [(state.authority["issuer_public_key"], "reddog-reviewer-designation.v1." +
        canonical({k: v for k, v in grant.items() if k != "signature"}), grant["signature"], True)]
    expected += [(d["reviewer_public_key"], _preimage(d), d["signature"], True) for d in state.call["decisions"]]
    assert state.crypto == expected


def reset(state):
    closed(state)
    state.reads = state.artifact_reads = state.close_calls = 0
    state.lease.selected = state.lease.entered = state.lease.exited = 0
    state.crypto.clear()
    state.projected.clear()
    state.records.calls.clear()


def after_reviews(state, action):
    def callback(current, message):
        if message.startswith("reddog-effect-consensus-review.v1.") and len(current.crypto) == 3:
            action(current)
    state.callback = callback


def during_owner_reread(monkeypatch, state, action):
    original = state.loader._load_owner_config

    def load(*args, **kwargs):
        value = original(*args, **kwargs)
        if state.reads == 2:
            action(state)
        return value

    monkeypatch.setattr(state.loader, "_load_owner_config", load)


def expire_at_finish(state, case):
    if case.startswith("key_"):
        state.designation["reviewers"][int(case[-1])]["expires_at"] = 1001
    elif case.startswith("runtime_"):
        object.__setattr__(state.evidence[int(case[-1])], "expires_at", 1001)
    elif case in {"manifest", "selection"}:
        state.selection[case + "_expires_at"] = 1001
    elif case == "owner":
        state.authority["expires_at"] = 1001
        state.designation["owner_authority_digest"] = digest(state.authority)
    elif case == "designation":
        state.designation["expires_at"] = 1001
    refresh(state)
    after_reviews(state, lambda s: setattr(s, "now", {"context": 1020, "rollback": 999}.get(case, 1001)))


def mutate_input(state, case):
    if case in {"decision", "finish_clock"}:
        state.call["decisions"][0]["decision_id"] = "changed-after-verification"
    elif case == "append":
        state.call["decisions"].append(dict(state.call["decisions"][0]))
    elif case == "reorder":
        state.call["decisions"].reverse()
    elif case == "policy":
        object.__setattr__(state.call["policy"], "maximum_ttl_seconds", 19)
    else:
        state.call["expected_target"]["unexpected_mutation"] = True


def during_finish_clock(monkeypatch, state, action):
    calls = []

    def clock():
        calls.append(True)
        if len(calls) == 2:
            action(state)
        return state.now

    monkeypatch.setattr(state.runtime, "_now_epoch", clock)
