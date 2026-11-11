"""Real disposable root-owned config/generation fixture; never operational service data."""

from dataclasses import replace
import hashlib
import importlib
import json

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, artifact, canonical, digest, fixture, public, sign,
)
from modules.communication.moltbot_bridge.tests.test_reddog_elevated_authority_consensus_effect_reviewer import _case, _sync


def review_at(monkeypatch, now):
    _, kw = _case(monkeypatch)
    parent = kw["authority_request"]
    kw["authority_request"] = replace(parent, issued_at=now, identity_expires_at=now + 100, work_authority_expires_at=now + 100)
    target = kw["target"]
    prefix = "reddog-authoritative-use-lease.v1."
    payload = json.loads(target.signing_input[len(prefix):])
    payload.update(issued_at=now, expires_at=now + 20)
    kw["target"] = replace(target, signing_input=prefix + canonical(payload), payload_digest=digest(payload))
    kw["expected_target"] = kw["target"].to_dict()
    kw["context"] = replace(kw["context"], issued_at=now, expires_at=now + 20,
        target_signing_request_digest=digest(kw["expected_target"]))
    resolver = kw["runtime_evidence_resolver"]
    resolver.value = replace(resolver.value, expires_at=now + 20)
    _sync(kw)
    authority, grant, issuer, reviewer = fixture()
    for value in (authority, grant, grant["reviewers"][0]):
        value.update(issued_at=now - 10, expires_at=now + 100)
    authority["policy_digest"] = grant["policy_digest"] = kw["policy"].policy_digest
    grant["owner_authority_digest"] = digest(authority)
    kw["decision"]["reviewer_public_key"] = public(reviewer)
    sign(grant, issuer)
    sign(kw["decision"], reviewer, "reddog-effect-consensus-review.v1.")
    return kw, authority, grant


def complete_owner(base, prepared, authority):
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_system_service_entrypoint import _upgrade_prepared_owner_to_v2
    owner = _upgrade_prepared_owner_to_v2(prepared, base)
    repo = prepared["harness"].repo_root
    grant_root = base / "grant-service"
    grant_root.mkdir(mode=0o700)
    sources = {"reddog_grant_authority_service.py": "modules/communication/moltbot_bridge/src/reddog_isolated_signer_socket_resident_service.py"}
    schema = "reddog_grant_authority_service_git_source_policy.v1"
    owner.update(schema_version="reddog_signer_system_service_owner_config.v5",
        independent_grant_authority=dict(authority_root=str(grant_root), authority_socket_path=str(grant_root / "grant-authority.sock"),
            authority_service_uid=1202, authority_service_gid=1202),
        grant_authority_source_policy=dict(schema_version=schema, repo_root_digest="sha256:" + hashlib.sha256(str(repo.resolve()).encode()).hexdigest(),
            sources=sources, source_policy_digest=digest(dict(schema_version=schema, sources=sources))),
        reviewer_designation_authority=authority)
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    return owner


def linux_fixture(monkeypatch, base):
    from modules.communication.moltbot_bridge.tests import test_reddog_signer_system_service_manifest_selection_loader as old
    from modules.communication.moltbot_bridge.tests.test_reddog_signed_runtime_artifact_manifest import NOW
    api = importlib.import_module(ROOT + "reddog_elevated_authority_consensus_verification")
    verify = getattr(api, "verify_current_effect_reviewer_decision", None)
    assert callable(verify), "current_effect_reviewer_api_missing"
    runtime = importlib.import_module(ROOT + "reddog_current_effect_reviewer_verification")
    monkeypatch.setattr(old.selection_module, "_now_epoch", lambda: NOW)
    monkeypatch.setattr(old.loader_module.time, "time", lambda: NOW)
    monkeypatch.setattr(runtime, "_now_epoch", lambda: NOW)
    kw, authority, grant = review_at(monkeypatch, NOW)
    original_build = old._build_harness

    def with_reviewers(root):
        harness = original_build(root)
        old._write_json(harness.runtime_root / "principal_authority_records.json", artifact(authority, grant))
        return harness

    monkeypatch.setattr(old, "_build_harness", with_reviewers)
    prepared = old._prepare_real_cli_owner(base, None)
    harness = prepared["harness"]
    owner = complete_owner(base, prepared, authority)
    path = prepared["owner_path"]
    path.write_text(canonical(owner), encoding="ascii")
    path.chmod(0o400)
    call = dict(owner_config_path=path, repo_root=harness.repo_root,
        **{k: v for k, v in kw.items() if k not in ("signature_verifier", "reviewer_key_resolver", "now")})
    return verify, call, owner
