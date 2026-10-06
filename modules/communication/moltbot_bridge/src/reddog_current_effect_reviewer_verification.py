"""Effect-review verification under one current authenticated owner/lease.

Runtime evidence is still supplied by the caller. Success does not issue
an execution permit or prove deployed independent reviewer runtimes.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import time

from . import reddog_signer_system_service_manifest_selection_loader as loader
from . import reddog_signer_owner_e0_principal_authority as principals
from .reddog_signer_current_principal_authority_resolver import _project_reviewer_keys
from .reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier


def _now_epoch():
    return int(time.time())


def verify_current_effect_reviewer_decision(
    *, owner_config_path, repo_root, decision, context, authority_request, target,
    expected_target, policy, runtime_evidence_resolver,
    revoked_key_epochs: frozenset[str] = frozenset(),
) -> bool:
    """Verify one review with current scoped keys; runtime evidence is supplied."""
    return verify_current_effect_review(
        owner_config_path=owner_config_path, repo_root=repo_root, decision=decision,
        context=context, authority_request=authority_request, target=target,
        expected_target=expected_target, policy=policy,
        runtime_evidence_resolver=runtime_evidence_resolver,
        revoked_key_epochs=revoked_key_epochs,
    )



def verify_current_effect_reviewer_decisions(
    *, owner_config_path, repo_root, decisions, context, authority_request, target,
    expected_target, policy, runtime_evidence_resolver,
    revoked_key_epochs: frozenset[str] = frozenset(),
) -> bool:
    """Verify a complete quorum under one lease; runtime evidence is supplied."""
    return verify_current_effect_review(
        owner_config_path=owner_config_path, repo_root=repo_root, decisions=decisions,
        context=context, authority_request=authority_request, target=target,
        expected_target=expected_target, policy=policy,
        runtime_evidence_resolver=runtime_evidence_resolver,
        revoked_key_epochs=revoked_key_epochs,
    )



def verify_current_effect_review(*, owner_config_path, repo_root, **inputs):
    """Fail closed; do not expose the selection or its scoped key projection."""
    try:
        before = _input_snapshot(inputs)
        repo = Path(repo_root).resolve()
        owner = loader._load_owner_config(owner_config_path, repo=repo)
        if owner["schema_version"] not in {loader.SCHEMA_VERSION_V5, loader.SCHEMA_VERSION_V6, loader.SCHEMA_VERSION_V7, loader.SCHEMA_VERSION_V8}:
            return False
        selected, boundary = loader._manifest_selection_from_owner(owner, repo=repo)
        with boundary._lease_current(selected) as selection:
            if selection["owner_config_id"] != owner["config_id"]:
                return False
            return _verify_leased(owner, owner_config_path, repo, selection, inputs, before)
    except Exception:
        return False


def _verify_leased(owner, owner_path, repo, selection, inputs, before, *, valid_until=None, completion_checks=None):
    from . import reddog_elevated_authority_consensus_verification as verification

    records, grants = principals.load_current_generation_principal_artifact(
        repo_root=repo, selection=selection,
    )
    if len(grants) != 1:
        return False
    now = _now_epoch()
    keys = _project_reviewer_keys(
        authority=owner["reviewer_designation_authority"], designation=grants[0],
        records=records, policy=inputs["policy"], selection=selection,
        parent=inputs["authority_request"], now=now,
    )
    runtime = _RuntimeSnapshot(inputs["runtime_evidence_resolver"])
    try:
        verify = (verification.verify_effect_reviewer_decisions if "decisions" in inputs
                  else verification.verify_effect_reviewer_decision)
        checked = verify(
            **{**inputs, "runtime_evidence_resolver": runtime},
            signature_verifier=Ed25519SignatureVerifier(), reviewer_key_resolver=keys, now=now,
        )
        if checked is not True:
            return False
        current = loader._load_owner_config(owner_path, repo=repo)
        finish = _now_epoch()
        valid = (current == owner and finish >= now and before == _input_snapshot(inputs)
                 and _still_current(inputs, keys, runtime, finish))
        if valid and valid_until is not None:
            valid_until.extend(evidence.expires_at for evidence, _ in runtime.records)
            key_refs = [keys.resolve(d["reviewer_principal_id"], d["reviewer_principal_provider"])
                        for d in _review_items(inputs)]
            valid_until.extend(key.expires_at for key in key_refs)
            snapshots = [asdict(key) for key in key_refs]
            if completion_checks is not None:
                completion_checks.append(lambda now: runtime.current(now)
                    and snapshots == [asdict(key) for key in key_refs])
        return valid
    finally:
        keys.close()


def _still_current(inputs, keys, runtime, now):
    from .reddog_elevated_authority_consensus_effect_context import effect_approval_context_matches

    for decision in _review_items(inputs):
        key = keys.resolve(decision["reviewer_principal_id"], decision["reviewer_principal_provider"])
        if key is None or type(key.expires_at) is not int or now >= key.expires_at:
            return False
    return (runtime.current(now) and effect_approval_context_matches(
        inputs["context"], parent=inputs["authority_request"], target=inputs["target"],
        expected_target=inputs["expected_target"], now=now,
    ))


def _review_items(inputs):
    if ("decision" in inputs) == ("decisions" in inputs):
        raise ValueError("effect_review_input_mode_invalid")
    if "decision" in inputs:
        return (inputs["decision"],)
    decisions = inputs["decisions"]
    if type(decisions) not in (list, tuple) or not 1 <= len(decisions) <= 8:
        raise ValueError("effect_review_set_count_invalid")
    return tuple(decisions)


def _input_snapshot(inputs):
    payload = {
        "decisions": _review_items(inputs), "plural": "decisions" in inputs,
        "context": inputs["context"].to_dict(),
        "parent": inputs["authority_request"].to_dict(),
        "target": asdict(inputs["target"]), "expected_target": inputs["expected_target"],
        "policy": asdict(inputs["policy"]),
        "revoked_key_epochs": sorted(inputs["revoked_key_epochs"]),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


class _RuntimeSnapshot:
    """Retain each supplied evidence reference and its immediately sampled fields."""

    def __init__(self, resolver):
        self.resolver, self.records = resolver, []

    def resolve(self, *args):
        if len(self.records) >= 8:
            raise ValueError("effect_runtime_snapshot_limit_exceeded")
        evidence = self.resolver.resolve(*args)
        before = asdict(evidence) if evidence is not None else None
        self.records.append((evidence, before))
        return evidence

    def current(self, now):
        return bool(self.records) and all(
            evidence is not None and before == asdict(evidence)
            and type(evidence.expires_at) is int and now < evidence.expires_at
            for evidence, before in self.records
        )
