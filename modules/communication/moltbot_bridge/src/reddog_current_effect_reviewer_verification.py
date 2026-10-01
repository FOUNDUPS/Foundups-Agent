"""One effect-review verification under a current authenticated owner/lease.

Runtime evidence is still supplied by the caller. Success is not quorum,
an execution permit, or proof of a deployed independent reviewer runtime.
"""

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


def verify_current_effect_review(*, owner_config_path, repo_root, **inputs):
    """Fail closed; do not expose the selection or its scoped key projection."""
    try:
        before = _input_snapshot(inputs)
        repo = Path(repo_root).resolve()
        owner = loader._load_owner_config(owner_config_path, repo=repo)
        if owner["schema_version"] != loader.SCHEMA_VERSION_V5:
            return False
        selected, boundary = loader._manifest_selection_from_owner(owner, repo=repo)
        with boundary._lease_current(selected) as selection:
            if selection["owner_config_id"] != owner["config_id"]:
                return False
            return _verify_leased(owner, owner_config_path, repo, selection, inputs, before)
    except Exception:
        return False


def _verify_leased(owner, owner_path, repo, selection, inputs, before):
    from .reddog_elevated_authority_consensus_verification import verify_effect_reviewer_decision

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
        checked = verify_effect_reviewer_decision(
            **{**inputs, "runtime_evidence_resolver": runtime},
            signature_verifier=Ed25519SignatureVerifier(), reviewer_key_resolver=keys, now=now,
        )
        if checked is not True or before != _input_snapshot(inputs):
            return False
        current = loader._load_owner_config(owner_path, repo=repo)
        finish = _now_epoch()
        return (current == owner and finish >= now
                and _still_current(inputs, keys, runtime, finish))
    finally:
        keys.close()


def _still_current(inputs, keys, runtime, now):
    from .reddog_elevated_authority_consensus_effect_context import effect_approval_context_matches

    decision = inputs["decision"]
    key = keys.resolve(decision["reviewer_principal_id"], decision["reviewer_principal_provider"])
    return (key is not None and now < key.expires_at and runtime.current(now)
            and effect_approval_context_matches(
                inputs["context"], parent=inputs["authority_request"], target=inputs["target"],
                expected_target=inputs["expected_target"], now=now,
            ))


def _input_snapshot(inputs):
    payload = {
        "decision": inputs["decision"], "context": inputs["context"].to_dict(),
        "parent": inputs["authority_request"].to_dict(),
        "target": asdict(inputs["target"]), "expected_target": inputs["expected_target"],
        "policy": asdict(inputs["policy"]),
        "revoked_key_epochs": sorted(inputs["revoked_key_epochs"]),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


class _RuntimeSnapshot:
    """Sample supplied runtime evidence once; retain its explicit limitation."""

    def __init__(self, resolver):
        self.resolver, self.evidence, self.before = resolver, None, None

    def resolve(self, *args):
        self.evidence = self.resolver.resolve(*args)
        if self.evidence is not None:
            self.before = asdict(self.evidence)
        return self.evidence

    def current(self, now):
        return (self.evidence is not None and self.before == asdict(self.evidence)
                and type(self.evidence.expires_at) is int and now < self.evidence.expires_at)
