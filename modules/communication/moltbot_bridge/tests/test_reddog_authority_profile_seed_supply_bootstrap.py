"""Tests for REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_MAIN_PREFLIGHT_PHASE1."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from prompt.swarm.m2m_compiler import encode_m2m_envelope
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_seed_supply import (
    _invalid_seed_plan,
    _seed_plan,
    _plan_bound_determination,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply_bootstrap import (
    AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED,
    AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY,
    run_reddog_authority_profile_seed_supply_bootstrap,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _REDDOG_PUBLIC_KEY,
    _determination,
    _memex_supply,
    _model_selection,
)
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_source_artifact_supply import (
    _principal,
    _snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_authority_profile_seed_supply_bootstrap.py"
)
NOW = 1_784_160_000


def _write_json(root: Path, name: str, payload: object) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, Path]:
    runtime = tmp_path / "runtime"
    return {
        "determination": _write_json(runtime, "architect_determination.json", _determination()),
        "model": _write_json(runtime, "model_selection_receipt.json", _model_selection()),
        "memex": _write_json(runtime, "memex_supply_receipt.json", _memex_supply()),
        "principal": _write_json(runtime, "principal_authority_record.json", _principal().to_dict()),
        "snapshot": _write_json(runtime, "permission_snapshot.json", asdict(_snapshot())),
        "output": runtime / "authority_profile_seed.json",
    }


def _bootstrap(files, **overrides):
    params = {
        "repo_root": REPO_ROOT,
        "architect_determination_path": files["determination"],
        "model_selection_receipt_path": files["model"],
        "memex_supply_receipt_path": files["memex"],
        "principal_authority_record_path": files["principal"],
        "permission_snapshot_path": files["snapshot"],
        "output_path": files["output"], "reddog_id": "reddog:architect",
        "reddog_public_key": _REDDOG_PUBLIC_KEY,
        "consensus_receipt_digest": "sha256:" + "c" * 64,
        "sovereign_authorization_digest": "sha256:" + "d" * 64, "now_epoch": NOW,
    }
    params.update(overrides)
    return run_reddog_authority_profile_seed_supply_bootstrap(**params)


@pytest.mark.parametrize("kind", ("matching", "omitted", "none", "empty", "conflicting"))
@pytest.mark.parametrize("receipt_plan", ("full", "empty"))
def test_bootstrap_enforces_receipt_plan_consistency(tmp_path, kind, receipt_plan):
    files = _inputs(tmp_path)
    determination = _plan_bound_determination({} if receipt_plan == "empty" else None)
    files["determination"].write_text(json.dumps(determination), encoding="utf-8")
    expected = deepcopy(determination["proposal_admission"]["bounded_worker_plan"])
    plan = None if kind == "none" else {} if kind == "empty" else deepcopy(expected)
    if kind == "conflicting":
        plan = _seed_plan()
        plan["m2m_envelope"]["A"] = "Different work"
    files["output"].write_bytes(b"previous seed")
    result = _bootstrap(
        files, requested_operation=determination["proposal_admission"]["requested_operation"],
        **({} if kind == "omitted" else {"bounded_worker_plan": plan}),
    )
    accepted = kind in {"matching", "omitted"} or (kind == "empty" and receipt_plan == "empty")
    assert result.accepted is accepted, result.rejection_reasons
    if accepted:
        assert json.loads(files["output"].read_text())["bounded_worker_plan"] == expected
    else:
        assert files["output"].read_bytes() == b"previous seed"


@pytest.mark.parametrize("kind", ("absent", "empty", "full"))
def test_bootstrap_selects_plan_from_actual_producer(tmp_path, monkeypatch, kind):
    from modules.communication.moltbot_bridge.tests import test_reddog_architect_fix_promotion_exact_schema as producer
    # Supply valid FoundUp-local deny scope to the model fixture BEFORE admission.
    model_output = producer._model_output

    def scoped_output(*args, **kwargs):
        output = model_output(*args, **kwargs)
        output["denied_paths"] = ["modules/foundups/demo/secrets/**"]
        return output

    monkeypatch.setattr(producer, "_model_output", scoped_output)
    produced, store, runner = producer._produced_determination(kind)
    assert produced.accepted is True and produced.persist_result.stored is True
    assert len(runner.calls) == 1
    determination = produced.receipt.to_dict()
    assert store.records[0].determination == determination
    admission = determination["proposal_admission"]
    files = _inputs(tmp_path)
    _write_json(files["determination"].parent, files["determination"].name, determination)
    _write_json(files["principal"].parent, files["principal"].name,
                replace(_principal(), foundup_scope=("demo",)).to_dict())
    _write_json(files["memex"].parent, files["memex"].name, _memex_supply(
        foundup_id="demo", snapshot_receipt_id=determination["snapshot_receipt_id"],
        snapshot_content_digest=determination["snapshot_content_digest"],
        holoindex_generation_id=admission["holoindex_generation_id"],
        source_revision=admission["work_state_revision"],
    ))
    result = _bootstrap(files, **{key: admission[key] for key in (
        "requested_operation", "allowed_paths", "denied_paths", "required_tests", "required_policy_gates",
    )})
    assert result.accepted is True, result.rejection_reasons
    seed = json.loads(files["output"].read_text(encoding="utf-8"))
    assert ("bounded_worker_plan" in seed) is (kind != "absent")
    if kind != "absent":
        assert seed["bounded_worker_plan"] == admission["bounded_worker_plan"]
    assert seed["source_determination_receipt_id"] == determination["determination_receipt_id"]
    assert seed["queue_candidate_id"] == determination["queue_candidate"]["queue_candidate_id"]


@pytest.mark.parametrize("part", ("null", "malformed", "receipt", "candidate", "wrapper", "scope"))
def test_bootstrap_omission_does_not_launder_invalid_receipts(tmp_path, part):
    files = _inputs(tmp_path)
    determination = _plan_bound_determination()
    admission = determination["proposal_admission"]
    if part in {"null", "malformed"}:
        admission["bounded_worker_plan"] = None if part == "null" else []
    elif part == "receipt":
        admission["receipt_id"] = "sha256:" + "0" * 64
    elif part == "candidate":
        determination["queue_candidate"]["source_determination_receipt_id"] = "sha256:" + "0" * 64
    elif part == "wrapper":
        determination = {"receipt": determination}
    _write_json(files["determination"].parent, files["determination"].name, determination)
    files["output"].write_bytes(b"previous seed")
    result = _bootstrap(files, requested_operation=(
        "feature_slice" if part == "scope" else admission["requested_operation"]
    ))
    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY
    assert files["output"].read_bytes() == b"previous seed"


@pytest.mark.parametrize("kind", ("absent", "empty", "full"))
def test_bootstrap_freezes_single_raw_read_before_later_callbacks(tmp_path, monkeypatch, kind):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply_bootstrap as bootstrap
    files = _inputs(tmp_path)
    determination = _determination() if kind == "absent" else _plan_bound_determination(
        {} if kind == "empty" else None,
    )
    expected = deepcopy(determination)
    _write_json(files["determination"].parent, files["determination"].name, determination)
    read = bootstrap._read_json_outside_repo
    reads, aliases = [], []

    def mutate_after_read(*args, **kwargs):
        reads.append(args[1])
        if aliases:
            aliases[0]["proposal_admission"]["bounded_worker_plan"] = {"unexpected": True}
            aliases[0]["determination_receipt_id"] = "changed by later callback"
            files["determination"].write_text("{}", encoding="utf-8")
        value, reasons = read(*args, **kwargs)
        if args[1] == files["determination"]:
            aliases.append(value)
        return value, reasons

    monkeypatch.setattr(bootstrap, "_read_json_outside_repo", mutate_after_read)
    result = _bootstrap(files, requested_operation=expected["proposal_admission"]["requested_operation"])
    assert result.accepted is True, result.rejection_reasons
    assert reads.count(files["determination"]) == 1 and len(reads) == 5
    seed = json.loads(files["output"].read_text(encoding="utf-8"))
    assert seed["source_determination_receipt_id"] == expected["determination_receipt_id"]
    assert ("bounded_worker_plan" in seed) is (kind != "absent")
    if kind != "absent":
        assert seed["bounded_worker_plan"] == expected["proposal_admission"]["bounded_worker_plan"]


@pytest.mark.parametrize("explicit_none", (False, True))
def test_bootstrap_absence_preserves_prechange_seed_bytes(tmp_path, explicit_none):
    files = _inputs(tmp_path)
    result = _bootstrap(files, **({"bounded_worker_plan": None} if explicit_none else {}))
    assert result.accepted is True
    assert hashlib.sha256(files["output"].read_bytes()).hexdigest() == (
        "7ae1ec5659c07e6490c38cfb13dae1455b6c285414b5a689ee28a32ad3b3e3b7"
    )


@pytest.mark.parametrize("ancestor", ("determination", "admission"))
def test_bootstrap_omission_rejects_ancestor_before_copy_coercion(tmp_path, monkeypatch, ancestor):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply_bootstrap as bootstrap
    files = _inputs(tmp_path)
    calls = []

    class LaunderedMapping(dict):
        def __deepcopy__(self, memo):
            calls.append("coerced")
            return dict(self)

    determination = _determination()
    if ancestor == "determination":
        determination = LaunderedMapping(determination)
    else:
        determination["proposal_admission"] = LaunderedMapping(determination["proposal_admission"])
    read = bootstrap._read_json_outside_repo

    def supplied_mapping(*args, **kwargs):
        return (determination, ()) if args[1] == files["determination"] else read(*args, **kwargs)

    monkeypatch.setattr(bootstrap, "_read_json_outside_repo", supplied_mapping)
    files["output"].write_bytes(b"previous seed")
    result = _bootstrap(files)
    assert result.accepted is False
    assert result.rejection_reasons == ("authority_seed_proposal_plan_invalid",)
    assert calls == []
    assert files["output"].read_bytes() == b"previous seed"


def test_bootstrap_detaches_explicit_packet_before_reading_receipts(tmp_path, monkeypatch):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply_bootstrap as bootstrap
    files = _inputs(tmp_path)
    plan = _seed_plan()
    expected = deepcopy(plan)
    read = bootstrap._read_json_outside_repo
    calls = []

    def mutate_then_read(*args, **kwargs):
        calls.append("read")
        plan["m2m_envelope"]["I"]["fixture"].append("late receipt callback")
        plan["unknown_field"] = True
        return read(*args, **kwargs)

    monkeypatch.setattr(bootstrap, "_read_json_outside_repo", mutate_then_read)
    result = _bootstrap(files, bounded_worker_plan=plan)
    assert result.accepted is True, result.rejection_reasons
    assert len(calls) == 5
    seed = json.loads(files["output"].read_text(encoding="utf-8"))
    assert seed["bounded_worker_plan"] == expected
    assert encode_m2m_envelope(seed["bounded_worker_plan"]["m2m_envelope"]) == (
        encode_m2m_envelope(expected["m2m_envelope"])
    )


@pytest.mark.parametrize("case", (
    "plan_list", "plan_text", "plan_unknown", "plan_type", "partial",
    "null", "cycle", "depth", "bytes", "secret", "digest", "non_ascii",
))
def test_bootstrap_invalid_plan_rejects_before_receipt_reads(tmp_path, monkeypatch, case):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply_bootstrap as bootstrap
    files = _inputs(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("invalid explicit plan crossed bootstrap preflight")

    monkeypatch.setattr(bootstrap, "_read_json_outside_repo", forbidden)
    monkeypatch.setattr(bootstrap, "run_reddog_authority_profile_seed_supply", forbidden)
    result = _bootstrap(files, bounded_worker_plan=_invalid_seed_plan(case))
    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY
    assert result.rejection_reasons
    assert result.seed_supply_receipt_id is None
    assert not files["output"].exists()


def test_bootstrap_materializes_authority_profile_seed(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_seed_supply_bootstrap(
        repo_root=REPO_ROOT,
        architect_determination_path=files["determination"],
        model_selection_receipt_path=files["model"],
        memex_supply_receipt_path=files["memex"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        reddog_id="reddog:architect",
        reddog_public_key=_REDDOG_PUBLIC_KEY,
        consensus_receipt_digest="sha256:" + ("c" * 64),
        sovereign_authorization_digest="sha256:" + ("d" * 64),
        now_epoch=NOW,
    )

    assert result.accepted is True
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_APPLIED
    assert result.seed_supply_receipt_id and result.seed_supply_receipt_id.startswith("sha256:")
    seed = json.loads(files["output"].read_text(encoding="utf-8"))
    assert seed["principal_id"] == "github:mjtrout"
    assert seed["reddog_public_key"] == _REDDOG_PUBLIC_KEY
    assert seed["no_signing_performed"] is True
    assert seed["no_holoindex_reindex_performed"] is True


def test_bootstrap_rejects_missing_model_selection(tmp_path: Path) -> None:
    files = _inputs(tmp_path)

    result = run_reddog_authority_profile_seed_supply_bootstrap(
        repo_root=REPO_ROOT,
        architect_determination_path=files["determination"],
        model_selection_receipt_path=None,
        memex_supply_receipt_path=files["memex"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        reddog_id="reddog:architect",
        reddog_public_key="pub:reddog",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_BOOTSTRAP_NOT_READY
    assert "missing_model_selection_receipt_path" in result.rejection_reasons
    assert not files["output"].exists()


def test_bootstrap_rejects_input_inside_repo(tmp_path: Path) -> None:
    files = _inputs(tmp_path)
    result = run_reddog_authority_profile_seed_supply_bootstrap(
        repo_root=REPO_ROOT,
        architect_determination_path=REPO_ROOT / "modules",
        model_selection_receipt_path=files["model"],
        memex_supply_receipt_path=files["memex"],
        principal_authority_record_path=files["principal"],
        permission_snapshot_path=files["snapshot"],
        output_path=files["output"],
        reddog_id="reddog:architect",
        reddog_public_key="pub:reddog",
        now_epoch=NOW,
    )

    assert result.accepted is False
    assert "architect_determination_path_inside_repo" in result.rejection_reasons


def test_bootstrap_module_has_no_execution_network_signing_or_reindex_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_import_roots = {
        "subprocess",
        "requests",
        "urllib",
        "http",
        "socket",
        "sqlite3",
        "git",
        "holo_index",
        "hmac",
        "secrets",
    }
    banned_calls = {"eval", "exec", "compile", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_import_roots
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned_calls
