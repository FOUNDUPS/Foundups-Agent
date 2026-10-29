"""Security regressions for backend registered-FoundUp target verification."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess

import pytest
from copy import deepcopy
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_registered_foundup_target_verifier import (
    verify_registered_foundup_target,
)

ROOT = Path(__file__).resolve().parents[4]
REGISTRY = ROOT / "modules/foundups/foundup_registry.json"
SCHEMA = ROOT / "modules/foundups/foundup_registry.schema.json"


def _digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _receipt() -> dict:
    registry_bytes, schema_bytes = REGISTRY.read_bytes(), SCHEMA.read_bytes()
    registry = json.loads(registry_bytes)
    entity = next(item for item in registry["entities"] if item["foundup_id"] == "trade")
    manifest = ROOT / entity["manifest_path"]
    manifest_data = json.loads(manifest.read_bytes())
    evidence = [
        {"path": "modules/foundups/foundup_registry.json", "content_digest": _digest(registry_bytes)},
        {"path": "modules/foundups/foundup_registry.schema.json", "content_digest": _digest(schema_bytes)},
        {"path": entity["manifest_path"], "content_digest": _digest(manifest.read_bytes())},
    ]
    payload = {
        "schema_version": "registered_foundup_target_receipt.v1",
        "applied": True,
        "passed": True,
        "rejection_reasons": [],
        "foundup_id": "trade",
        "registry_digest": _digest(registry_bytes),
        "registry_schema_digest": _digest(schema_bytes),
        "registry_entity_digest": _digest(entity),
        "manifest_path": entity["manifest_path"],
        "evidence_digests": evidence,
        "safe_mutation_surfaces": manifest_data["build_contract"]["safe_mutation_surface"],
        "repo_root_digest": _digest(str(ROOT.resolve())),
        "repo_head_sha": __import__("subprocess").check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "grants_authority": False,
    }
    return {**payload, "receipt_id": _digest(payload)}


def _selection(receipt: dict) -> dict:
    return {
        "foundup_id": receipt["foundup_id"],
        "registered_foundup_target_receipt_id": receipt["receipt_id"],
    }


def _work_order(receipt: dict) -> dict:
    safe = receipt["safe_mutation_surfaces"]
    return {
        "foundup_id": receipt["foundup_id"],
        "registered_foundup_target_receipt_id": receipt["receipt_id"],
        "registered_foundup_target_receipt": receipt,
        "safe_mutation_surface_digest": _digest({"safe_mutation_surfaces": safe}),
        "allowed_paths": safe,
    }


def _rehash(receipt: dict) -> dict:
    value = deepcopy(receipt)
    value.pop("receipt_id", None)
    value["receipt_id"] = _digest(value)
    return value


def test_valid_current_checkout_binding_passes() -> None:
    receipt = _receipt()
    assert verify_registered_foundup_target(
        ROOT, receipt, selection_receipt=_selection(receipt), work_order=_work_order(receipt)
    ) == ()


def test_recomputed_scope_forgery_fails_against_manifest() -> None:
    receipt = _receipt()
    receipt["safe_mutation_surfaces"] = ["modules/foundups/**"]
    forged = _rehash(receipt)
    reasons = verify_registered_foundup_target(ROOT, forged, selection_receipt=_selection(forged))
    assert "registered_foundup_target_manifest_changed" in reasons


def test_recomputed_entity_forgery_fails_against_registry() -> None:
    receipt = _receipt()
    receipt["registry_entity_digest"] = "sha256:" + "0" * 64
    forged = _rehash(receipt)
    assert "registered_foundup_target_entity_changed" in verify_registered_foundup_target(ROOT, forged)


def test_recomputed_head_forgery_fails_against_checkout() -> None:
    receipt = _receipt()
    receipt["repo_head_sha"] = "0" * 40
    forged = _rehash(receipt)
    assert "registered_foundup_target_repo_head_mismatch" in verify_registered_foundup_target(ROOT, forged)


def test_selection_and_work_order_mismatch_fail() -> None:
    receipt = _receipt()
    assert "registered_foundup_target_selection_mismatch" in verify_registered_foundup_target(
        ROOT, receipt, selection_receipt={"foundup_id": "other", "registered_foundup_target_receipt_id": receipt["receipt_id"]}
    )
    order = _work_order(receipt)
    order["foundup_id"] = "other"
    assert "registered_foundup_target_work_order_mismatch" in verify_registered_foundup_target(
        ROOT, receipt, work_order=order
    )


def test_claim_without_receipt_fails() -> None:
    assert verify_registered_foundup_target(
        ROOT, None, selection_receipt={"foundup_id": "trade"}
    ) == ("registered_foundup_target_receipt_missing",)


@pytest.fixture
def branded_repo(tmp_path):
    """Synthetic public checkout; the receipt itself is produced by real Node code."""
    root = tmp_path / "公開"
    module = "modules/foundups/alpha"
    entity = {"foundup_id": "alpha", "display_name": "Alpha", "entity_type": "foundup",
              "module_path": module, "stage": "proto", "tier": "F0_DAE",
              "implementation_status": "IMPLEMENTED", "token_status": "EXISTS", "token_symbol": "ALPHA",
              "manifest_status": "exists", "manifest_path": module + "/foundup_manifest.json",
              "brand_context_path": module + "/brand_context.json", "evidence_docs": []}
    context = {"schema_version": "1.0.0", "foundup_id": "alpha", "canonical_brand": "Alpha.example",
               "aliases": ["Alpha"], "public_urls": [], "default_locale": "ja", "rules": [],
               "authority_boundary": "BRANDING_ONLY_NO_EXECUTION_AUTHORITY",
               "child_foundups": [{"foundup_id": "snow", "canonical_brand": "雪.me", "relationship": "child",
                                   "aliases": ["雪", "Snow"], "public_urls": [], "rules": []},
                                  {"foundup_id": "harbor", "canonical_brand": "Harbor.me", "relationship": "child",
                                   "aliases": ["Harbor"], "public_urls": [], "rules": []}]}
    files = {"modules/foundups/foundup_registry.json": {"schema_version": "1.0.0", "last_updated": "2026-08-02T00:00:00Z", "entities": [entity]},
             entity["manifest_path"]: {"foundup_id": "alpha", "build_contract": {"safe_mutation_surface": [module + "/**"]}},
             entity["brand_context_path"]: context}
    for relative, value in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf8")
    for name in ("foundup_registry.schema.json", "brand_context.schema.json"):
        shutil.copyfile(ROOT / "modules/foundups" / name, root / "modules/foundups" / name)
    (root / ".git").mkdir()
    (root / ".git/HEAD").write_text("a" * 40, encoding="utf8")
    return root, entity, context


def _node_receipt(root, reference="雪"):
    node = os.environ.get("REDDOG_TEST_NODE") or shutil.which("node")
    assert node, "real Node is required for producer/consumer qualification"
    program = r"""const fs=require('fs'),path=require('path');
const request=JSON.parse(fs.readFileSync(0,'utf8'));
const producer=require(request.module);
console.log(JSON.stringify(producer.resolveFoundupWorkGrounding(request.root,request.prompt,{
repo_head_sha:'a'.repeat(40),registry_status_clean:true,tracked_paths:request.tracked,dirty_paths:[]})));"""
    request = {"module": str(ROOT / "extensions/reddog/foundup_work_grounding.js"), "root": str(root),
               "prompt": "work on " + reference + " FoundUp",
               "tracked": [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]}
    result = subprocess.run([node, "-e", program], input=json.dumps(request), text=True, encoding="utf8",
                            capture_output=True, timeout=30, check=True)
    receipt = json.loads(result.stdout)
    assert receipt["passed"] is True, receipt
    return receipt


def test_actual_node_unicode_brand_receipt_and_authority_binding(branded_repo):
    root, entity, _ = branded_repo
    receipt = _node_receipt(root)
    assert receipt["brand_foundup_id"] == "snow"
    assert receipt["canonical_brand"] == "雪.me"
    assert receipt["safe_mutation_surfaces"] == [entity["module_path"] + "/**"]
    assert receipt["grants_authority"] is False
    assert verify_registered_foundup_target(root, receipt, selection_receipt=_selection(receipt), work_order=_work_order(receipt)) == ()
    payload = {k: v for k, v in receipt.items() if k != "receipt_id"}
    old_hash = "sha256:" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    assert old_hash != receipt["receipt_id"], "non-ASCII producer must exercise the original cross-language defect"


@pytest.mark.parametrize("identity,canonical", [("invented", "Invented"), ("harbor", "Harbor.me")])
def test_child_relabeling_cannot_change_node_reference(branded_repo, identity, canonical):
    root, _, _ = branded_repo
    receipt = _node_receipt(root)
    forged = _rehash({**receipt, "brand_foundup_id": identity, "canonical_brand": canonical})
    assert "registered_foundup_target_brand_selection_mismatch" in verify_registered_foundup_target(root, forged)


def test_brand_bytes_changed_after_node_receipt_rejected(branded_repo):
    root, entity, context = branded_repo
    receipt = _node_receipt(root)
    context["rules"].append("Changed.")
    (root / entity["brand_context_path"]).write_text(json.dumps(context), encoding="utf8")
    assert "registered_foundup_target_evidence_changed" in verify_registered_foundup_target(root, receipt)


@pytest.mark.parametrize("mode", ["duplicate", "alias"])
def test_rehashed_duplicate_or_ambiguous_context_rejected(branded_repo, mode):
    root, entity, context = branded_repo
    receipt = _node_receipt(root)
    child = deepcopy(context["child_foundups"][0])
    if mode == "alias":
        child["foundup_id"] = "other"
    context["child_foundups"].append(child)
    context_file = root / entity["brand_context_path"]
    context_file.write_text(json.dumps(context), encoding="utf8")
    for record in receipt["evidence_digests"]:
        if record["path"] == entity["brand_context_path"]:
            record["content_digest"] = _digest(context_file.read_bytes())
    assert "registered_foundup_target_brand_identity_ambiguous" in verify_registered_foundup_target(root, _rehash(receipt))


@pytest.mark.parametrize("field,value", [("brand_foundup_id", "child"), ("canonical_brand", "Forged"), ("brand_context_path", "modules/foundups/context.json")])
def test_legacy_absent_context_rejects_forged_brand_fields(field, value):
    receipt = _receipt()
    forged = _rehash({**receipt, field: value})
    assert verify_registered_foundup_target(ROOT, forged)


def test_absent_context_node_fallback_still_passes(branded_repo):
    root, entity, _ = branded_repo
    entity.pop("brand_context_path")
    registry_file = root / "modules/foundups/foundup_registry.json"
    registry = json.loads(registry_file.read_bytes())
    registry["entities"] = [entity]
    registry_file.write_text(json.dumps(registry), encoding="utf8")
    receipt = _node_receipt(root, "Alpha")
    assert receipt["brand_context_path"] is None
    assert verify_registered_foundup_target(root, receipt) == ()


@pytest.mark.parametrize("relative", ["secrets/context.json", ".netrc", "modules/private_key.json", "../escape.json",
                                      "modules/id_rsa", "modules/id_ed25519", "modules/auth.json", "modules/.dockerconfigjson"])
def test_private_evidence_rejected_before_read(branded_repo, monkeypatch, relative):
    root, _, _ = branded_repo
    receipt = _node_receipt(root)
    private_fixture = (root / relative).resolve()
    private_fixture.parent.mkdir(parents=True, exist_ok=True)
    private_fixture.write_bytes(b"synthetic fixture, not private data")
    receipt["evidence_digests"].insert(0, {"path": relative, "content_digest": "sha256:" + "0" * 64})
    original = Path.read_bytes
    def guarded_read(path):
        assert path != (root / relative).resolve(), "private fixture was read"
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    assert "registered_foundup_target_evidence_changed" in verify_registered_foundup_target(root, _rehash(receipt))


def test_link_components_rejected_before_evidence_read(branded_repo, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_registered_foundup_target_verifier as verifier
    root, entity, _ = branded_repo
    target = root / entity["brand_context_path"]
    hardlink = root / "hardlink.json"
    os.link(target, hardlink)
    assert verifier._path(root, "hardlink.json") is None
    # lstat reparse metadata is also checked on Windows; Linux exercises real symlinks.
    if os.name != "nt":
        (root / "public-link").symlink_to(target.parent, target_is_directory=True)
        assert verifier._path(root, "public-link/brand_context.json") is None
    else:
        original = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda p: p == target.parent or original(p))
        assert verifier._path(root, entity["brand_context_path"]) is None


def test_node_unpaired_surrogate_receipt_rejects_without_exception(branded_repo):
    root, entity, context = branded_repo
    context["child_foundups"][0]["canonical_brand"] = "Snow\ud800"
    (root / entity["brand_context_path"]).write_text(json.dumps(context), encoding="utf8")
    receipt = _node_receipt(root, "Snow")
    assert receipt["canonical_brand"] == "Snow\ud800"
    assert verify_registered_foundup_target(root, receipt) == ("registered_foundup_target_receipt_invalid",)
