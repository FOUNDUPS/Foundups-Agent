"""Tests for REDDOG_AUTHORITY_PROFILE_SEED_SUPPLY_PHASE1."""

from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from prompt.swarm.m2m_compiler import encode_m2m_envelope
from modules.communication.moltbot_bridge.tests.test_reddog_authority_profile_exact_schema import (
    _invalid_m2m,
    _m2m_envelope,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_seed_supply import (
    AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT,
    AUTHORITY_PROFILE_SEED_SUPPLY_REJECT,
    AuthorityProfileSeedSupplyReason,
    run_reddog_authority_profile_seed_supply,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    run_reddog_authority_profile_source_artifact_supply,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    _PRINCIPAL_PUBLIC_KEY,
    _REDDOG_PUBLIC_KEY,
    _determination,
    _memex_supply,
    _model_selection,
    _promote,
    _rebind_determination_admission,
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
    / "reddog_authority_profile_seed_supply.py"
)
NOW = 1_784_160_000


def _supply(tmp_path: Path, **overrides):
    params = {
        "repo_root": REPO_ROOT,
        "architect_determination": _determination(),
        "model_selection_receipt": _model_selection(),
        "memex_supply_receipt": _memex_supply(),
        "principal_authority_record": _principal(),
        "permission_snapshot": _snapshot(),
        "output_path": tmp_path / "runtime" / "authority_profile_seed.json",
        "reddog_id": "reddog:architect",
        "reddog_public_key": _REDDOG_PUBLIC_KEY,
        "now_epoch": NOW,
    }
    params.update(overrides)
    return run_reddog_authority_profile_seed_supply(**params)


@pytest.mark.parametrize("with_plan", (False, True))
def test_seed_supply_writes_seed_consumable_by_source_supplier_and_promotion(tmp_path: Path, with_plan: bool) -> None:
    plan = _seed_plan()
    seed_result = _supply(
        tmp_path,
        consensus_receipt_digest="sha256:" + ("c" * 64),
        sovereign_authorization_digest="sha256:" + ("d" * 64),
        **({"bounded_worker_plan": plan} if with_plan else {}),
    )

    assert seed_result.accepted is True
    assert seed_result.status == AUTHORITY_PROFILE_SEED_SUPPLY_ACCEPT
    assert seed_result.seed_supply_receipt_id and seed_result.seed_supply_receipt_id.startswith("sha256:")
    seed = json.loads(Path(seed_result.output_path or "").read_text(encoding="utf-8"))
    assert seed["schema_version"] == "reddog_authority_profile_seed.v1"
    assert seed["principal_id"] == "github:mjtrout"
    assert seed["permission_snapshot_digest"] == "sha256:" + "a" * 64
    assert seed["holoindex_evidence"]["index_gap_detected"] is False
    assert seed["no_holoindex_reindex_performed"] is True

    source_path = tmp_path / "runtime" / "authority_profile_source.json"
    source = run_reddog_authority_profile_source_artifact_supply(
        repo_root=REPO_ROOT,
        authority_seed=seed,
        principal_authority_record=_principal(),
        permission_snapshot=_snapshot(),
        output_path=source_path,
        now_epoch=NOW,
    )
    assert source.accepted is True

    profile = json.loads(source_path.read_text(encoding="utf-8"))
    promoted, _ = _promote(authority_profile=profile)
    assert promoted.accepted is True
    assert promoted.authority_profile is not None
    assert promoted.authority_profile["seed_supply_receipt_id"] == seed["seed_supply_receipt_id"]
    if with_plan:
        expected = encode_m2m_envelope(plan["m2m_envelope"])
        for preserved in (seed, profile, promoted.authority_profile):
            assert preserved["bounded_worker_plan"] == plan
            assert encode_m2m_envelope(preserved["bounded_worker_plan"]["m2m_envelope"]) == expected


def _seed_plan():
    return {"operation": "feature_slice", "m2m_envelope": _m2m_envelope()}


def _supply_with_cosign(tmp_path, **overrides):
    return _supply(
        tmp_path, consensus_receipt_digest="sha256:" + "c" * 64,
        sovereign_authorization_digest="sha256:" + "d" * 64, **overrides,
    )


def _read_seed(result):
    assert result.accepted is True, result.rejection_reasons
    return json.loads(Path(result.output_path).read_text(encoding="utf-8"))


def _plan_bound_determination(plan=None):
    determination = _determination()
    if plan is None:
        plan = _seed_plan()
        plan["operation"] = determination["proposal_admission"]["requested_operation"]
    return _rebind_determination_admission(determination, {"bounded_worker_plan": plan})


def _supply_bound_plan(tmp_path, determination, **overrides):
    params = {
        "architect_determination": determination,
        "requested_operation": determination["proposal_admission"]["requested_operation"],
        "bounded_worker_plan": determination["proposal_admission"]["bounded_worker_plan"],
    }
    params.update(overrides)
    return _supply_with_cosign(tmp_path, **params)


@pytest.mark.parametrize("kind", ("empty", "m2m"))
def test_seed_supply_accepts_matching_receipt_plan(tmp_path, kind):
    determination = _plan_bound_determination({} if kind == "empty" else None)
    seed = _read_seed(_supply_bound_plan(tmp_path, determination))
    assert seed["bounded_worker_plan"] == determination["proposal_admission"]["bounded_worker_plan"]
    assert seed["source_determination_receipt_id"] == determination["determination_receipt_id"]
    assert seed["queue_candidate_id"] == determination["queue_candidate"]["queue_candidate_id"]


@pytest.mark.parametrize("kind", ("omitted", "none", "empty", "action", "bool_int", "int_float"))
def test_seed_supply_rejects_missing_or_conflicting_receipt_plan(tmp_path, kind):
    determination = _plan_bound_determination()
    plan = deepcopy(determination["proposal_admission"]["bounded_worker_plan"])
    if kind in {"omitted", "none"}:
        plan = None
    elif kind == "empty":
        plan = {}
    elif kind == "action":
        plan["m2m_envelope"]["A"] = "Different task"
    elif kind == "bool_int":
        plan["m2m_envelope"]["I"]["fixture"][0] = 1
    else:
        plan["m2m_envelope"]["I"]["fixture"][1] = 1.0
    output = tmp_path / "preserved.json"
    output.write_bytes(b"prior seed")
    kwargs = {} if kind == "omitted" else {"bounded_worker_plan": plan}
    result = _supply_with_cosign(
        tmp_path, architect_determination=determination,
        requested_operation=determination["proposal_admission"]["requested_operation"],
        output_path=output, **kwargs,
    )
    assert result.accepted is False
    assert output.read_bytes() == b"prior seed"


@pytest.mark.parametrize("part", (
    "receipt_plan", "receipt_id", "determination_id", "candidate_id", "candidate_digest",
    "candidate_source", "stage_digest", "stage_body", "candidate_status", "rehashed_proposal",
    "null_plan", "cycle", "non_json",
))
def test_seed_supply_rejects_receipt_plan_lineage_tampering(tmp_path, part):
    determination = _plan_bound_determination()
    explicit = deepcopy(determination["proposal_admission"]["bounded_worker_plan"])
    admission, candidate = determination["proposal_admission"], determination["queue_candidate"]
    if part == "receipt_plan":
        admission["bounded_worker_plan"]["m2m_envelope"]["A"] = "Unhashed change"
    elif part == "receipt_id":
        admission["receipt_id"] = "sha256:" + "0" * 64
    elif part == "determination_id":
        determination["determination_receipt_id"] = "sha256:" + "0" * 64
    elif part == "rehashed_proposal":
        changed = deepcopy(explicit)
        changed["m2m_envelope"]["A"] = "New receipt with stale outer lineage"
        admission.update(_plan_bound_determination(changed)["proposal_admission"])
        explicit = changed
    elif part == "null_plan":
        admission["bounded_worker_plan"] = None
    elif part == "cycle":
        determination["cycle"] = determination
    elif part == "non_json":
        determination["non_json"] = object()
    elif part == "stage_body":
        candidate["progressive_policy_stage_receipt"]["independent_verifier_required"] = False
    else:
        key = {"candidate_id": "queue_candidate_id", "candidate_digest": "proposal_admission_digest",
               "candidate_source": "source_determination_receipt_id", "stage_digest": "progressive_policy_stage_digest",
               "candidate_status": "status"}[part]
        candidate[key] = "BLOCKED_CANDIDATE" if part == "candidate_status" else "sha256:" + "0" * 64
    result = _supply_bound_plan(tmp_path, determination, bounded_worker_plan=explicit)
    assert result.accepted is False
    assert not (tmp_path / "runtime" / "authority_profile_seed.json").exists()


@pytest.mark.parametrize("mirror", (
    "operation", "artifact", "requested_paths", "I.requested_operation", "I.allowed_paths",
    "I.denied_paths", "I.required_tests", "I.required_policy_gates",
))
def test_seed_supply_checks_declared_plan_against_effective_seed_scope(tmp_path, mirror):
    determination = _determination()
    admission = determination["proposal_admission"]
    plan = {"m2m_envelope": _m2m_envelope()}
    overrides = {}
    if mirror == "operation":
        plan["operation"] = admission["requested_operation"]
        overrides["requested_operation"] = "feature_slice"
    elif mirror in {"artifact", "requested_paths"}:
        plan["planned_artifacts" if mirror == "artifact" else "requested_allowed_paths"] = admission["allowed_paths"]
        overrides["allowed_paths"] = ["modules/foundups/paccess_001/docs/**"]
    else:
        key = mirror.removeprefix("I.")
        plan["m2m_envelope"]["I"][key] = admission[key]
        if key == "requested_operation":
            overrides[key] = "feature_slice"
    determination = _plan_bound_determination(plan)
    result = _supply_bound_plan(tmp_path, determination, **overrides)
    assert result.accepted is False
    assert not (tmp_path / "runtime" / "authority_profile_seed.json").exists()


def test_seed_supply_freezes_bound_lineage_before_later_callbacks(tmp_path):
    determination = _plan_bound_determination()
    expected = deepcopy(determination)
    explicit = determination["proposal_admission"]["bounded_worker_plan"]

    class ModelSelection:
        def to_dict(self):
            explicit["m2m_envelope"]["A"] = "Late caller mutation"
            determination["determination_receipt_id"] = "sha256:" + "0" * 64
            determination["queue_candidate"]["queue_candidate_id"] = "sha256:" + "1" * 64
            return _model_selection()

    result = _supply_bound_plan(tmp_path, determination, model_selection_receipt=ModelSelection())
    seed = _read_seed(result)
    assert seed["bounded_worker_plan"] == expected["proposal_admission"]["bounded_worker_plan"]
    assert seed["source_determination_receipt_id"] == expected["determination_receipt_id"]
    assert seed["queue_candidate_id"] == expected["queue_candidate"]["queue_candidate_id"]


@pytest.mark.parametrize("empty", (False, True))
def test_seed_supply_missing_bound_plan_stops_before_other_receipts(tmp_path, empty):
    determination = _plan_bound_determination({} if empty else None)

    class ForbiddenReceipt:
        def to_dict(self):
            pytest.fail("invalid bound plan reached unrelated receipt callback")

    result = _supply_bound_plan(
        tmp_path, determination, bounded_worker_plan=None,
        model_selection_receipt=ForbiddenReceipt(),
    )
    assert result.rejection_reasons == (AuthorityProfileSeedSupplyReason.PROPOSAL_PLAN_INVALID,)


@pytest.mark.parametrize("scope_field", ("required_tests", "required_policy_gates", "allowed_paths"))
def test_seed_supply_matching_explicit_execution_mirrors_pass(tmp_path, scope_field):
    admission = _determination()["proposal_admission"]
    plan = {"m2m_envelope": _m2m_envelope()}
    plan["m2m_envelope"]["I"][scope_field] = admission[scope_field]
    determination = _plan_bound_determination(plan)
    seed = _read_seed(_supply_bound_plan(tmp_path, determination, **{scope_field: admission[scope_field]}))
    assert seed[scope_field] == admission[scope_field]


@pytest.mark.parametrize("ancestor", ("determination", "admission", "plan"))
def test_seed_supply_rejects_nonplain_plan_lineage_ancestors(tmp_path, ancestor):
    class NonPlain(dict):
        pass

    determination = _plan_bound_determination()
    plan = deepcopy(determination["proposal_admission"]["bounded_worker_plan"])
    if ancestor == "determination":
        determination = NonPlain(determination)
    elif ancestor == "admission":
        determination["proposal_admission"] = NonPlain(determination["proposal_admission"])
    else:
        determination["proposal_admission"]["bounded_worker_plan"] = NonPlain(plan)
    result = _supply_bound_plan(tmp_path, determination, bounded_worker_plan=plan)
    assert result.rejection_reasons == (AuthorityProfileSeedSupplyReason.PROPOSAL_PLAN_INVALID,)


@pytest.mark.parametrize("returned", (None, [], [1], True, "receipt"))
def test_seed_supply_malformed_determination_callback_fails_closed(tmp_path, returned):
    class MalformedDetermination:
        def to_dict(self):
            return returned

    result = _supply_with_cosign(tmp_path, architect_determination=MalformedDetermination())
    assert result.accepted is False
    assert result.seed_supply_receipt_id is None
    assert not (tmp_path / "runtime" / "authority_profile_seed.json").exists()


@pytest.mark.parametrize("ancestor", ("determination", "admission"))
def test_seed_supply_cannot_hide_receipt_plan_with_overridden_presence(tmp_path, ancestor):
    class HiddenDetermination(dict):
        def get(self, key, default=None):
            return None if key == "proposal_admission" else super().get(key, default)

    class HiddenAdmission(dict):
        def __contains__(self, key):
            return False if key == "bounded_worker_plan" else super().__contains__(key)

    determination = _plan_bound_determination()
    if ancestor == "determination":
        determination = HiddenDetermination(determination)
    else:
        determination["proposal_admission"] = HiddenAdmission(determination["proposal_admission"])
    result = _supply_bound_plan(tmp_path, determination, bounded_worker_plan={})
    assert result.rejection_reasons == (AuthorityProfileSeedSupplyReason.PROPOSAL_PLAN_INVALID,)
    assert not (tmp_path / "runtime" / "authority_profile_seed.json").exists()


@pytest.mark.parametrize("explicit_none", (False, True))
def test_seed_supply_absence_preserves_prechange_seed_bytes(tmp_path, explicit_none):
    kwargs = {"bounded_worker_plan": None} if explicit_none else {}
    result = _supply_with_cosign(tmp_path, **kwargs)
    seed = _read_seed(result)
    assert "bounded_worker_plan" not in seed
    # Captured twice from fixed existing fixtures at base 8da0551 before this API.
    assert hashlib.sha256(Path(result.output_path).read_bytes()).hexdigest() == (
        "7ae1ec5659c07e6490c38cfb13dae1455b6c285414b5a689ee28a32ad3b3e3b7"
    )


@pytest.mark.parametrize("kind", ("empty", "legacy", "m2m"))
def test_seed_supply_explicit_plan_is_covered_by_receipt(tmp_path, kind):
    plan = {} if kind == "empty" else {"operation": "feature_slice"}
    if kind == "m2m":
        plan = _seed_plan()
    seed = _read_seed(_supply_with_cosign(tmp_path, bounded_worker_plan=plan))
    assert seed["bounded_worker_plan"] == plan
    receipt = seed.pop("seed_supply_receipt_id")
    wire = json.dumps(seed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert receipt == "sha256:" + hashlib.sha256(wire.encode()).hexdigest()
    legacy = _supply_with_cosign(tmp_path / "legacy")
    assert receipt != legacy.seed_supply_receipt_id


@pytest.mark.parametrize("changed", ("action", "nested_type"))
def test_seed_supply_packet_change_changes_seed_receipt(tmp_path, changed):
    plan = _seed_plan()
    first = _supply_with_cosign(tmp_path / "first", bounded_worker_plan=plan)
    first_seed = _read_seed(first)
    if changed == "action":
        plan["m2m_envelope"]["A"] = "Validate the second fixture"
    else:
        plan["m2m_envelope"]["I"]["fixture"][0] = 1
    second = _supply_with_cosign(tmp_path / "second", bounded_worker_plan=plan)
    second_seed = _read_seed(second)
    assert first.seed_supply_receipt_id != second.seed_supply_receipt_id
    assert encode_m2m_envelope(first_seed["bounded_worker_plan"]["m2m_envelope"]) != (
        encode_m2m_envelope(second_seed["bounded_worker_plan"]["m2m_envelope"])
    )


def test_seed_supply_snapshots_plan_before_receipt_callback(tmp_path):
    plan = _seed_plan()
    expected = deepcopy(plan)
    calls = []

    class Determination:
        def to_dict(self):
            calls.append("receipt")
            plan["m2m_envelope"]["I"]["fixture"].append("late caller change")
            plan["operation"] = "inspect_repo"
            plan["unknown_field"] = True
            return _determination()

    result = _supply_with_cosign(
        tmp_path, bounded_worker_plan=plan, architect_determination=Determination(),
    )
    seed = _read_seed(result)
    assert calls == ["receipt"]
    assert seed["bounded_worker_plan"] == expected
    assert encode_m2m_envelope(seed["bounded_worker_plan"]["m2m_envelope"]) == (
        encode_m2m_envelope(expected["m2m_envelope"])
    )


def _invalid_seed_plan(case):
    if case == "plan_list":
        return []
    if case == "plan_bool":
        return False
    if case == "plan_text":
        return "{}"
    if case == "plan_key":
        return {1: "not a field"}
    if case == "plan_subclass":
        class Plan(dict):
            pass
        return Plan(_seed_plan())
    if case == "plan_unknown":
        return {"unknown_field": True}
    if case == "plan_type":
        return {"operation": True}
    plan = {"m2m_envelope": _invalid_m2m(case)}
    if case == "non_ascii":
        plan["m2m_envelope"]["A"] = "validate \u2603"
    elif case == "plan_non_ascii":
        plan["operation"] = "feature_\u2603"
    elif case == "no_effect_type":
        plan["m2m_envelope"]["I"]["no_repo_mutation_performed"] = 1
    return plan


@pytest.mark.parametrize("case", (
    "plan_list", "plan_bool", "plan_text", "plan_key", "plan_subclass",
    "plan_unknown", "plan_type", "null", "wire_string", "partial", "unknown",
    "refs_bool", "tuple", "nan", "cycle", "depth", "nodes", "bytes",
    "secret", "digest", "env_value", "false_no_effect", "no_effect_type",
    "non_ascii", "plan_non_ascii",
))
def test_seed_supply_invalid_plan_rejects_before_callbacks_or_writes(tmp_path, monkeypatch, case):
    from modules.communication.moltbot_bridge.src import reddog_authority_profile_seed_supply as supplier

    class Determination:
        def to_dict(self):
            pytest.fail("invalid plan reached a receipt callback")

    def forbidden_write(*args, **kwargs):
        pytest.fail("invalid plan reached publication")

    monkeypatch.setattr(supplier, "_write_json_atomic", forbidden_write)
    result = _supply_with_cosign(
        tmp_path, bounded_worker_plan=_invalid_seed_plan(case),
        architect_determination=Determination(),
    )
    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_SUPPLY_REJECT
    assert result.rejection_reasons
    assert result.seed_supply_receipt_id is None
    assert result.output_path is None
    assert not (tmp_path / "runtime").exists()


def test_seed_supply_rejects_missing_reddog_public_key(tmp_path: Path) -> None:
    result = _supply(tmp_path, reddog_public_key="")

    assert result.accepted is False
    assert result.status == AUTHORITY_PROFILE_SEED_SUPPLY_REJECT
    assert AuthorityProfileSeedSupplyReason.MISSING_REDDOG_PUBLIC_KEY in result.rejection_reasons


def test_seed_supply_rejects_principal_reddog_key_reuse(tmp_path: Path) -> None:
    result = _supply(tmp_path, reddog_public_key=_PRINCIPAL_PUBLIC_KEY)

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.PRINCIPAL_REDDOG_KEY_REUSE in result.rejection_reasons


def test_seed_supply_rejects_high_authority_without_cosign(tmp_path: Path) -> None:
    result = _supply(tmp_path, requested_operation="create_foundup")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_rejects_worktree_intent_for_low_operation_without_cosign(tmp_path: Path) -> None:
    result = _supply(tmp_path, requested_operation="inspect_repo")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_rejects_live_enqueue_intent_without_cosign(tmp_path: Path) -> None:
    result = _supply(
        tmp_path,
        requested_operation="inspect_repo",
        valve_state_required="VALVE_OPEN_LIVE_ENQUEUE",
    )

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_normalizes_empty_worktree_intent_before_classification(tmp_path: Path) -> None:
    for value in (None, ""):
        result = _supply(
            tmp_path,
            requested_operation="inspect_repo",
            valve_state_required=value,
        )
        assert result.accepted is False
        assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_rejects_consensus_without_sovereign_authorization(tmp_path: Path) -> None:
    result = _supply(tmp_path, consensus_receipt_digest="sha256:consensus")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HIGH_AUTHORITY_COSIGN_MISSING in result.rejection_reasons


def test_seed_supply_accepts_high_authority_with_cosign(tmp_path: Path) -> None:
    result = _supply(
        tmp_path,
        requested_operation="create_foundup",
        consensus_receipt_digest="sha256:consensus",
        sovereign_authorization_digest="sha256:sovereign",
    )

    assert result.accepted is True
    seed = json.loads(Path(result.output_path or "").read_text(encoding="utf-8"))
    assert seed["consensus_receipt_digest"] == "sha256:consensus"
    assert seed["sovereign_authorization_digest"] == "sha256:sovereign"


def test_seed_supply_rejects_memex_foundup_mismatch(tmp_path: Path) -> None:
    result = _supply(tmp_path, memex_supply_receipt=_memex_supply(foundup_id="other_foundup"))

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.FOUNDUP_SCOPE_INVALID in result.rejection_reasons


def test_seed_supply_rejects_fabricated_memex_receipt_without_writes(tmp_path: Path) -> None:
    output = tmp_path / "runtime" / "authority_profile_seed.json"
    result = _supply(
        tmp_path,
        output_path=output,
        memex_supply_receipt=_memex_supply(receipt_id="sha256:" + ("f" * 64)),
    )

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID in result.rejection_reasons
    assert not output.exists()


def test_seed_supply_rejects_rehashed_memex_lineage_without_writes(tmp_path: Path) -> None:
    output = tmp_path / "runtime" / "authority_profile_seed.json"
    result = _supply(
        tmp_path,
        output_path=output,
        memex_supply_receipt=_memex_supply(source_revision="sha256:attacker-revision"),
    )

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.MEMEX_SUPPLY_INVALID in result.rejection_reasons
    assert not output.exists()


def test_seed_supply_rejects_output_inside_repo(tmp_path: Path) -> None:
    result = _supply(tmp_path, output_path=REPO_ROOT / "authority_profile_seed.json")

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.OUTPUT_PATH_INVALID in result.rejection_reasons
    assert not (REPO_ROOT / "authority_profile_seed.json").exists()


def test_seed_supply_rejects_missing_evidence_refs(tmp_path: Path) -> None:
    determination = _determination()
    determination["queue_candidate"]["evidence_refs"] = []
    result = _supply(tmp_path, architect_determination=determination)

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.HOLOINDEX_EVIDENCE_INVALID in result.rejection_reasons


def test_seed_supply_rejects_allocation_mismatch(tmp_path: Path) -> None:
    determination = _determination()
    determination["wsp15_allocation_receipt_id"] = "sha256:wrong"
    result = _supply(tmp_path, architect_determination=determination)

    assert result.accepted is False
    assert AuthorityProfileSeedSupplyReason.WSP15_ALLOCATION_MISMATCH in result.rejection_reasons


def test_module_has_no_execution_network_signing_or_reindex_imports() -> None:
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
