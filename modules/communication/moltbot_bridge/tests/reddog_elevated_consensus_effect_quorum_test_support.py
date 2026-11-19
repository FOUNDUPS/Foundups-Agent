"""Inert evidence fixtures shared by the bounded effect-review quorum tests."""

from dataclasses import replace
import importlib

from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import (
    _Resolver, _case, _preimage, _sync,
)


class _QuorumResolver(_Resolver):
    """One retained evidence record per lookup; repeated lookup is an error."""

    def resolve(self, *args):
        repeated = args in self.calls
        self.calls.append(args)
        if self.error or repeated:
            raise RuntimeError("inert quorum resolver failure")
        return self.value.get(args)


class _QuorumVerifier(_Resolver):
    override = None

    def verify(self, *args):
        self.calls.append(args)
        if self.error:
            raise RuntimeError("inert quorum verifier failure")
        return self.override if self.override is not None else args in self.value


def _quorum_bind(kw):
    bridge = dict(kw, decision=kw["decisions"][0])
    _sync(bridge)
    kw.update(context=bridge["context"], policy=bridge["policy"])
    for decision in kw["decisions"]:
        decision["consensus_context_digest"] = bridge["decision"]["consensus_context_digest"]


def _quorum_evidence(kw):
    from modules.communication.moltbot_bridge.src import reddog_elevated_authority_consensus_policy as policies
    keys, runtimes, signatures = {}, {}, []
    for d in kw["decisions"]:
        keys[d["reviewer_principal_id"], d["reviewer_principal_provider"]] = policies.ReviewerKeyAuthority(
            d["reviewer_public_key"], d["reviewer_key_epoch"], 1020)
        runtimes[d["reviewer_principal_id"], d["model_selection_receipt_id"],
                 d["model_runtime_binding_receipt_id"]] = policies.ReviewerRuntimeEvidence(
            d["reviewer_model_id"], d["model_selection_receipt_id"], d["model_selection_digest"],
            d["model_runtime_binding_receipt_id"], d["model_runtime_binding_digest"], 1020)
        signatures.append((d["reviewer_public_key"], _preimage(d), d["signature"]))
    kw.update(reviewer_key_resolver=_QuorumResolver(keys), runtime_evidence_resolver=_QuorumResolver(runtimes),
              signature_verifier=_QuorumVerifier(tuple(signatures)))


def _quorum_case(monkeypatch, count=2):
    owner = importlib.import_module("modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_verification")
    verify = getattr(owner, "verify_effect_reviewer_decisions", None)
    assert callable(verify), "verify_effect_reviewer_decisions_api_missing"
    _, kw = _case(monkeypatch)
    first = kw.pop("decision")
    kw["decisions"] = [first]
    for index in range(1, count):
        kw["decisions"].append(dict(first, decision_id=f"decision:{index}",
            reviewer_principal_id=f"reviewer:{index}", reviewer_public_key=f"inert-key:{index}",
            reviewer_key_epoch=f"epoch:{index}", reviewer_role="verifier", reviewer_model_id=f"model:{index}",
            model_selection_receipt_id=f"selection:{index}", model_selection_digest="sha256:" + f"{index:064x}",
            model_runtime_binding_receipt_id=f"runtime:{index}",
            model_runtime_binding_digest="sha256:" + f"{index + 16:064x}", signature=f"opaque:{index}"))
    membership = tuple((d["reviewer_principal_id"], d["reviewer_principal_provider"], d["reviewer_role"])
                       for d in kw["decisions"])
    kw["policy"] = replace(kw["policy"], reviewer_membership=membership)
    _quorum_bind(kw)
    _quorum_evidence(kw)
    return verify, kw
