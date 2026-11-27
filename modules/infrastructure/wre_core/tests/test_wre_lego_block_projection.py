"""Offline tests for WRE Lego block compiler, catalog reconciler, and conservative triage."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from modules.infrastructure.wre_core.scripts.generate_test_registry import (
    build_registry,
    canonical_bytes,
)
from modules.infrastructure.wre_core.src.wre_lego_block_projection import (
    AGI_SCAFFOLDING_HYPOTHESIS,
    BlockTriageRecord,
    ExactByteProvenance,
    RenameAliasRecord,
    VerifiedCapabilityReceipt,
    admit_verified_capability_receipt,
    compute_exact_byte_provenance,
    compute_git_blob_oid_sha1,
    project_lego_blocks,
    sha256_bytes,
    to_canonical_json,
    to_m2m_compact,
)
from modules.infrastructure.wre_core.src.wre_test_registry import REGISTRY_PATH


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _digest_label(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def test_exact_byte_provenance_git_oid_sha256_and_crlf_drift(tmp_path: Path) -> None:
    lf_bytes = b"def compute_value() -> int:\n    return 42\n"
    crlf_bytes = b"def compute_value() -> int:\r\n    return 42\r\n"
    edited_bytes = b"def compute_value() -> int:\n    return 43\n"

    clean = compute_exact_byte_provenance(lf_bytes, lf_bytes)
    assert clean.byte_status == "CLEAN_EXACT_MATCH"
    assert clean.git_blob_oid_sha1 == compute_git_blob_oid_sha1(lf_bytes)
    assert clean.git_blob_sha256 == sha256_bytes(lf_bytes)
    assert clean.checkout_bytes_sha256 == sha256_bytes(lf_bytes)
    assert clean.git_blob_oid_sha1 != clean.git_blob_sha256
    assert len(clean.git_blob_oid_sha1 or "") == 40
    assert len(clean.git_blob_sha256 or "") == 64

    drift = compute_exact_byte_provenance(crlf_bytes, lf_bytes)
    assert drift.byte_status == "EOL_CRLF_DRIFT"
    assert drift.git_blob_oid_sha1 == clean.git_blob_oid_sha1
    assert drift.git_blob_sha256 == clean.git_blob_sha256
    assert drift.checkout_bytes_sha256 == sha256_bytes(crlf_bytes)
    assert drift.checkout_bytes_sha256 != drift.git_blob_sha256

    modified = compute_exact_byte_provenance(edited_bytes, lf_bytes)
    assert modified.byte_status == "MODIFIED_CONTENT"

    untracked = compute_exact_byte_provenance(lf_bytes, None)
    assert untracked.byte_status == "UNTRACKED"
    assert untracked.git_blob_oid_sha1 is None
    assert untracked.git_blob_sha256 is None

    with pytest.raises(ValueError, match="clean_exact_match_iff_identical_sha256"):
        ExactByteProvenance(
            git_blob_oid_sha1=clean.git_blob_oid_sha1,
            git_blob_sha256=clean.git_blob_sha256,
            checkout_bytes_sha256=sha256_bytes(crlf_bytes),
            byte_status="CLEAN_EXACT_MATCH",
        )

    # Also verify real Git object-store read without normalizing CRLF on disk
    repo = tmp_path / "git_repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "core.autocrlf", "false"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@foundups.local"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "LegoTest"], check=True)
    mod_rel = "modules/infrastructure/sample/src/worker.py"
    _write_bytes(repo / mod_rel, lf_bytes)
    subprocess.run(["git", "-C", str(repo), "add", mod_rel], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "seed lf blob"], check=True)
    # Overwrite working tree copy with CRLF bytes
    _write_bytes(repo / mod_rel, crlf_bytes)
    _write_bytes(repo / "modules/infrastructure/sample/src/untracked.py", lf_bytes)

    report = project_lego_blocks(repo)
    by_path = {b.identity.current_posix_path: b for b in report.blocks}
    worker_prov = by_path[mod_rel].provenance
    assert worker_prov is not None
    assert worker_prov.byte_status == "EOL_CRLF_DRIFT"
    assert worker_prov.git_blob_oid_sha1 == compute_git_blob_oid_sha1(lf_bytes)
    assert worker_prov.git_blob_sha256 == sha256_bytes(lf_bytes)
    assert worker_prov.checkout_bytes_sha256 == sha256_bytes(crlf_bytes)
    untracked_prov = by_path["modules/infrastructure/sample/src/untracked.py"].provenance
    assert untracked_prov is not None and untracked_prov.byte_status == "UNTRACKED"


def test_stable_identity_preserved_across_directory_rename_and_hierarchy(tmp_path: Path) -> None:
    repo_before = tmp_path / "before"
    old_py = "modules/foundups/legacy_alpha/src/engine.py"
    old_skill = "modules/foundups/legacy_alpha/sub_worker/SKILL.md"
    _write_bytes(repo_before / old_py, b"def run_engine() -> str:\n    return 'ok'\n")
    _write_bytes(repo_before / old_skill, b"---\nname: alpha-sub-worker\n---\n# Skill\n")

    rep_before = project_lego_blocks(
        repo_before,
        alias_map={old_py: "lego::alpha_engine_v1"},
    )
    before_by_path = {b.identity.current_posix_path: b for b in rep_before.blocks}
    engine_before = before_by_path[old_py]
    skill_before = before_by_path[old_skill]
    sub_before = before_by_path["modules/foundups/legacy_alpha/sub_worker"]
    mod_before = before_by_path["modules/foundups/legacy_alpha"]
    dom_before = before_by_path["modules/foundups"]

    assert dom_before.identity.parent_block_id is None
    assert mod_before.identity.parent_block_id == dom_before.identity.canonical_id
    assert sub_before.identity.parent_block_id == mod_before.identity.canonical_id
    assert skill_before.identity.parent_block_id == sub_before.identity.canonical_id
    assert skill_before.identity.canonical_id == "skill::alpha-sub-worker"

    repo_after = tmp_path / "after"
    new_py = "modules/foundups/modern_alpha/src/engine.py"
    new_skill = "modules/foundups/modern_alpha/sub_worker/SKILL.md"
    _write_bytes(repo_after / new_py, b"def run_engine() -> str:\n    return 'ok'\n")
    _write_bytes(repo_after / new_skill, b"---\nname: alpha-sub-worker\n---\n# Skill\n")

    rep_after = project_lego_blocks(
        repo_after,
        alias_map={old_py: "lego::alpha_engine_v1"},
        git_rename_pairs=[("modules/foundups/legacy_alpha", "modules/foundups/modern_alpha")],
    )
    after_by_path = {b.identity.current_posix_path: b for b in rep_after.blocks}
    engine_after = after_by_path[new_py]
    mod_after = after_by_path["modules/foundups/modern_alpha"]

    assert engine_after.identity.canonical_id == engine_before.identity.canonical_id == "lego::alpha_engine_v1"
    assert mod_after.identity.canonical_id == mod_before.identity.canonical_id
    assert RenameAliasRecord(old_py, "git_rename") in engine_after.identity.aliases
    assert after_by_path[new_skill].identity.canonical_id == "skill::alpha-sub-worker"


def test_typed_catalog_reconciliation_many_to_many_and_orphan_diagnostics(tmp_path: Path) -> None:
    registry_doc = {
        "schema_version": "1.0.0",
        "entities": [
            {
                "foundup_id": "holoindex_prod_01",
                "entity_type": "infra_service",
                "module_path": "modules/foundups/holoindex_prod_01",
            },
            {
                "foundup_id": "autopost",
                "entity_type": "external_foundup",
                "module_path": None,
            },
        ],
    }
    _write_bytes(
        tmp_path / "modules/foundups/foundup_registry.json",
        json.dumps(registry_doc).encode("utf-8"),
    )
    # 1 FoundUp -> 2 manifests (dual holoindex_prod_01 pattern)
    _write_bytes(
        tmp_path / "holo_index/foundup_manifest.json",
        json.dumps({"foundup_id": "holoindex_prod_01", "capabilities": ["semantic_search"]}).encode("utf-8"),
    )
    _write_bytes(
        tmp_path / "modules/foundups/holoindex_prod_01/foundup_manifest.json",
        json.dumps({"foundup_id": "holoindex_prod_01", "capabilities": ["mall_discovery"]}).encode("utf-8"),
    )
    _write_bytes(
        tmp_path / "modules/foundups/holoindex_prod_01/src/bridge.py",
        b"from modules.infrastructure.unmapped_orphan.src import helper\n\ndef query() -> str:\n    return helper.ping()\n",
    )
    _write_bytes(
        tmp_path / "modules/infrastructure/unmapped_orphan/src/helper.py",
        b"def ping() -> str:\n    return 'pong'\n",
    )
    # 1 module -> 2 shards (unit + integration) + 1 quarantined test
    t_unit = "modules/foundups/holoindex_prod_01/tests/test_bridge_unit.py"
    t_integ = "modules/foundups/holoindex_prod_01/tests/integration/test_bridge_integration.py"
    t_quar = "modules/foundups/holoindex_prod_01/tests/test_live_quarantined.py"
    _write_bytes(tmp_path / t_unit, b"def test_u() -> None:\n    assert True\n")
    _write_bytes(tmp_path / t_integ, b"def test_i() -> None:\n    assert True\n")
    _write_bytes(tmp_path / t_quar, b"import sys\nsys.exit(1)\n")
    payload = build_registry(tmp_path, test_paths=sorted([t_unit, t_integ, t_quar]))
    _write_bytes(tmp_path / REGISTRY_PATH, canonical_bytes(payload))

    report = project_lego_blocks(tmp_path)
    rels_by_type: dict[str, set[tuple[str, str]]] = {}
    for rel in report.catalog_relations:
        rels_by_type.setdefault(rel.relation_type, set()).add((rel.source_id, rel.target_id))

    assert rels_by_type["FOUNDUP_TO_MANIFEST"] == {
        ("foundup::holoindex_prod_01", "holo_index/foundup_manifest.json"),
        ("foundup::holoindex_prod_01", "modules/foundups/holoindex_prod_01/foundup_manifest.json"),
    }
    holo_shards = {dst for src, dst in rels_by_type["MODULE_TO_TEST_SHARD"] if src == "foundup::holoindex_prod_01"}
    assert len(holo_shards) == 2
    assert (
        "block::modules/foundups/holoindex_prod_01/src/bridge.py",
        "block::modules/infrastructure/unmapped_orphan/src/helper.py",
    ) in rels_by_type["BLOCK_IMPORTS_BLOCK"]

    diag_map = {(d.code, d.subject_id): d for d in report.catalog_diagnostics}
    assert ("DUPLICATE_MANIFEST_FOUNDUP_ID", "foundup::holoindex_prod_01") in diag_map
    assert ("EXTERNAL_FOUNDUP_NO_LOCAL_MODULE", "foundup::autopost") in diag_map
    assert ("MODULE_WITHOUT_FOUNDUP", "module::modules/infrastructure/unmapped_orphan") in diag_map
    assert ("MODULE_WITHOUT_TEST_SHARD", "module::modules/infrastructure/unmapped_orphan") in diag_map
    assert any(d.code == "QUARANTINED_TEST_ENTRY" and t_quar in d.related_paths for d in report.catalog_diagnostics)


def test_toxic_scanned_module_is_projected_safely_without_code_execution(tmp_path: Path) -> None:
    sentinel = tmp_path / "MUST_NEVER_BE_CREATED.txt"
    toxic_source = (
        f"from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed')\n"
        f"raise SystemExit('MUST_NOT_EXECUTE')\n"
    ).encode("utf-8")
    toxic_rel = "modules/infrastructure/toxic_zone/src/poison_bomb.py"
    _write_bytes(tmp_path / toxic_rel, toxic_source)

    report = project_lego_blocks(tmp_path)
    assert not sentinel.exists()
    by_path = {b.identity.current_posix_path: b for b in report.blocks}
    poison = by_path[toxic_rel]
    assert poison.static_tier == "STATICALLY_ANALYZED"
    assert poison.ast_summary is not None
    assert "module_raise" in poison.ast_summary.module_effects_flags
    assert "file_write" in poison.ast_summary.module_effects_flags

    # Verify our compiler module itself contains zero dynamic code-execution calls
    compiler_src = Path(__file__).resolve().parents[1] / "src" / "wre_lego_block_projection.py"
    tree = ast.parse(compiler_src.read_text(encoding="utf-8"))
    banned = {"eval", "exec", "__import__", "import_module"}
    called_names = {
        node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else ""
        )
        for node in ast.walk(tree) if isinstance(node, ast.Call)
    }
    assert not (called_names & banned)


def test_conservative_triage_candidates_unknown_consumers_and_no_deletion(tmp_path: Path) -> None:
    _write_bytes(tmp_path / "NAVIGATION.py", b"NAV = {'skill_target': 'modules/infrastructure/demo/src/nav_referenced.py'}\n")
    _write_bytes(tmp_path / "modules/infrastructure/demo/src/isolated_candidate.py", b"def unused() -> int:\n    return 0\n")
    _write_bytes(tmp_path / "modules/infrastructure/demo/src/nav_referenced.py", b"def routed() -> int:\n    return 1\n")
    _write_bytes(tmp_path / "modules/infrastructure/demo/src/plugin_target.py", b"def handle() -> int:\n    return 2\n")
    _write_bytes(
        tmp_path / "modules/infrastructure/demo/src/dynamic_loader.py",
        b"import importlib\n\ndef load() -> object:\n    mod = importlib.import_module('modules.infrastructure.demo.src.plugin_target')\n    return getattr(mod, 'handle')\n",
    )
    _write_bytes(tmp_path / "modules/infrastructure/demo/src/cli.py", b"def main() -> None:\n    pass\n")

    rep = project_lego_blocks(tmp_path, consumer_scope_complete=True)
    by_path = {b.identity.current_posix_path: b for b in rep.blocks}

    iso = by_path["modules/infrastructure/demo/src/isolated_candidate.py"].triage
    assert iso.classification == "CANDIDATE_ZERO_STATIC_CALLERS"
    assert iso.is_dead_code_proven is False
    assert iso.deletion_authorized is False

    nav = by_path["modules/infrastructure/demo/src/nav_referenced.py"].triage
    assert nav.classification == "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER"
    assert any("NAVIGATION.py" in ev for ev in nav.contrary_evidence)

    plug = by_path["modules/infrastructure/demo/src/plugin_target.py"].triage
    assert plug.classification == "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER"
    assert any("dynamic_dispatch_reference:" in ev for ev in plug.contrary_evidence)

    cli = by_path["modules/infrastructure/demo/src/cli.py"].triage
    assert cli.classification == "INTENTIONAL_ENTRYPOINT_OR_STUB"

    rep_partial = project_lego_blocks(tmp_path, consumer_scope_complete=False)
    iso_partial = {b.identity.current_posix_path: b for b in rep_partial.blocks}[
        "modules/infrastructure/demo/src/isolated_candidate.py"
    ].triage
    assert iso_partial.classification == "UNKNOWN_DYNAMIC_OR_EXTERNAL_CONSUMER"
    assert "consumer_scope_incomplete" in iso_partial.contrary_evidence

    with pytest.raises(ValueError, match="deletion_authorized_must_be_false"):
        project_lego_blocks(tmp_path, deletion_authorized=True)
    with pytest.raises(ValueError, match="deletion_authorized_must_be_false"):
        BlockTriageRecord("block::x", "CANDIDATE_ZERO_STATIC_CALLERS", deletion_authorized=True)


def test_capability_scoped_receipt_rejects_simulated_and_downgrades_on_1byte_edit(tmp_path: Path) -> None:
    rel = "modules/infrastructure/verif_demo/src/ DualCap.py".replace(" ", "")
    src_v1 = b"def cap_alpha() -> int:\n    return 1\n\ndef cap_beta() -> int:\n    return 2\n"
    _write_bytes(tmp_path / rel, src_v1)
    oid = compute_git_blob_oid_sha1(src_v1)
    blob_sha = sha256_bytes(src_v1)
    dep_sha = _digest_label("requirements-lock-v1")
    env_sha = _digest_label("win32-py312-env")
    inp_sha = _digest_label("bounded-inputs-v1")

    with pytest.raises(ValueError, match="simulated_evidence_cannot_verify_runtime"):
        VerifiedCapabilityReceipt(
            block_id=f"block::{rel}", capability_id="symbol::cap_alpha",
            source_git_blob_oid_sha1=oid, source_git_blob_sha256=blob_sha,
            executed_checkout_sha256=blob_sha, dependency_lock_sha256=dep_sha,
            environment_fingerprint_sha256=env_sha, inputs_sha256=inp_sha,
            verifier_receipt_id="rcpt-sim-01", evidence_origin="SIMULATED_TRANSITION_ONLY",
        )

    base_rep = project_lego_blocks(tmp_path, committed_git_blobs={rel: src_v1})
    base_blk = {b.identity.current_posix_path: b for b in base_rep.blocks}[rel]
    assert base_blk.runtime_claims_enabled is False
    with pytest.raises(ValueError, match="simulated_evidence_cannot_verify_runtime"):
        admit_verified_capability_receipt(
            base_blk,
            {"block_id": base_blk.identity.canonical_id, "evidence_origin": "SIMULATED_TRANSITION_ONLY", "runtime_verification_eligible": False},
        )

    valid_rcpt = VerifiedCapabilityReceipt(
        block_id=base_blk.identity.canonical_id, capability_id="symbol::cap_alpha",
        source_git_blob_oid_sha1=oid, source_git_blob_sha256=blob_sha,
        executed_checkout_sha256=blob_sha, dependency_lock_sha256=dep_sha,
        environment_fingerprint_sha256=env_sha, inputs_sha256=inp_sha,
        verifier_receipt_id="rcpt-real-01", evidence_origin="INDEPENDENT_PYTEST_RECEIPT",
    )
    ver_rep = project_lego_blocks(
        tmp_path, committed_git_blobs={rel: src_v1}, capability_receipts=[valid_rcpt], current_dependency_lock_sha256=dep_sha,
    )
    ver_blk = {b.identity.current_posix_path: b for b in ver_rep.blocks}[rel]
    statuses = {cs.capability_id: cs.status for cs in ver_blk.capability_statuses}
    assert statuses == {"symbol::cap_alpha": "VERIFIED_CAPABILITY", "symbol::cap_beta": "UNVERIFIED_STATIC_ONLY"}

    # 1-byte checkout edit immediately downgrades cap_alpha to STALE_PROVENANCE_MISMATCH
    src_v2 = src_v1 + b"\n"
    _write_bytes(tmp_path / rel, src_v2)
    stale_rep = project_lego_blocks(
        tmp_path, committed_git_blobs={rel: src_v1}, capability_receipts=[valid_rcpt], current_dependency_lock_sha256=dep_sha,
    )
    stale_blk = {b.identity.current_posix_path: b for b in stale_rep.blocks}[rel]
    stale_statuses = {cs.capability_id: cs.status for cs in stale_blk.capability_statuses}
    assert stale_statuses["symbol::cap_alpha"] == "STALE_PROVENANCE_MISMATCH"
    assert stale_blk.runtime_claims_enabled is False


def test_deterministic_canonical_json_and_m2m_output_across_runs(tmp_path: Path) -> None:
    for copy_name in ("copy_one", "copy_two"):
        root = tmp_path / copy_name
        _write_bytes(root / "modules/infrastructure/det/src/a.py", b"from . import b\n\ndef run() -> int:\n    return b.val()\n")
        _write_bytes(root / "modules/infrastructure/det/src/b.py", b"def val() -> int:\n    return 7\n")

    r1 = project_lego_blocks(tmp_path / "copy_one")
    r2 = project_lego_blocks(tmp_path / "copy_one")
    r3 = project_lego_blocks(tmp_path / "copy_two")

    assert r1.agi_scaffolding_hypothesis == AGI_SCAFFOLDING_HYPOTHESIS == "HYPOTHESIS_UNDER_TEST"
    assert r1.projection_sha256 == r2.projection_sha256 == r3.projection_sha256
    assert to_canonical_json(r1) == to_canonical_json(r2) == to_canonical_json(r3)
    assert to_m2m_compact(r1) == to_m2m_compact(r2) == to_m2m_compact(r3)
    assert "HYPOTHESIS: HYPOTHESIS_UNDER_TEST" in to_m2m_compact(r1)
