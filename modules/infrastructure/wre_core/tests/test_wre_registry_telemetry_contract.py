"""Finite independent report-shape and truth oracles; no effect authority."""
import copy

import pytest

from modules.infrastructure.wre_core.tests.wre_registry_telemetry_test_support import (
    FALSE_FLAGS, _api, _assert_telemetry, _case, _json, _seal,
)


@pytest.mark.parametrize("projected", [True, False], ids=["projected", "rejected"])
def test_normalizer_truth_and_detachment(projected):
    request, report = _case(projected)
    original = copy.deepcopy(report)
    result = _api()(report, request=request)
    assert result is not None
    _assert_telemetry(result, projected)
    assert _json(result["projection"]) == _json(original)
    report["evidence"]["untrusted_mutation"] = True
    request["base_sha"] = "f" * 40
    assert _json(result["projection"]) == _json(original)


BAD_FIELDS = ["extra_top", "projected_int", "success_reasons", "missing_evidence", "schema",
    "base_sha", "head_sha", "changed_paths", "digest", "extra_evidence", "extra_side",
    "impact_plan", "execution_status", "systemic_bool", "planning_only", "parity"]


@pytest.mark.parametrize("case", BAD_FIELDS, ids=BAD_FIELDS)
def test_normalizer_rejects_mixed_or_misbound_reports(case):
    request, report = _case()
    assert _api()(report, request=request) is not None
    evidence = report["evidence"]
    if case == "extra_top": report["success"] = True
    elif case == "projected_int": report["projected"] = 1
    elif case == "success_reasons": report["rejection_reasons"] = ["FAIL"]
    elif case == "missing_evidence": report.pop("evidence")
    elif case == "schema": evidence["schema_version"] = "other"
    elif case in ("base_sha", "head_sha"): evidence[case] = "f" * 40
    elif case == "changed_paths": evidence[case] = ["main.py"]
    elif case == "digest": evidence["projection_id"] = "wre_registry_scope_" + "f" * 64
    elif case == "extra_evidence": evidence["receipt"] = "forged"
    elif case == "extra_side": evidence["candidate"]["receipt"] = "forged"
    elif case == "impact_plan": evidence["test_impact_plan"]["schema_version"] = "other"
    elif case == "execution_status": evidence[case] = "PASSED"
    elif case == "systemic_bool": evidence["systemic_batched"] = 0
    elif case == "planning_only": evidence[case] = False
    elif case == "parity": evidence["recognized_dependency_parity_verified"] = False
    if case != "digest" and "evidence" in report: _seal(report)
    assert _api()(report, request=request) is None


@pytest.mark.parametrize("flag", FALSE_FLAGS, ids=FALSE_FLAGS)
def test_normalizer_rejects_execution_and_authority_claims(flag):
    request, report = _case()
    report["evidence"][flag] = True
    _seal(report)
    assert _api()(report, request=request) is None


@pytest.mark.parametrize("case", ["empty", "evidence", "many", "long", "nonstr", "text_container"],
                         ids=["empty", "evidence", "many", "long", "nonstr", "text_container"])
def test_rejected_report_requires_bounded_reasons_and_empty_evidence(case):
    request, report = _case(False)
    assert _api()(report, request=request) is not None
    if case == "empty": report["rejection_reasons"] = []
    elif case == "evidence": report["evidence"] = {"fake": True}
    elif case == "many": report["rejection_reasons"] = ["x"] * 33
    elif case == "long": report["rejection_reasons"] = ["x" * 257]
    elif case == "nonstr": report["rejection_reasons"] = [1]
    else: report["rejection_reasons"] = "FAIL"
    assert _api()(report, request=request) is None


def test_reason_boundaries_are_inclusive():
    request, report = _case(False)
    report["rejection_reasons"] = ["x" * 256] * 32
    result = _api()(report, request=request)
    _assert_telemetry(result, False)
    assert result["projection"]["rejection_reasons"] == report["rejection_reasons"]


class HostileDict(dict):
    def items(self):
        raise AssertionError("caller mapping method invoked")


UNSAFE = ["mapping_subclass", "string_subclass", "object", "nan", "cycle", "depth",
          "string_limit", "aggregate_limit", "node_limit"]


@pytest.mark.parametrize("case", UNSAFE, ids=UNSAFE)
def test_report_walk_rejects_unsafe_or_overbound_values(case):
    request, report = _case()
    if case == "mapping_subclass": report = HostileDict(report)
    elif case == "string_subclass": report["evidence"]["schema_version"] = type("Text", (str,), {})("x")
    elif case == "object": report["evidence"]["candidate"]["paths"] = [object()]
    elif case == "nan": report["evidence"]["candidate"]["paths"] = [float("nan")]
    elif case == "cycle": report["evidence"]["candidate"]["paths"] = [report]
    elif case == "depth":
        value = []
        for _ in range(17): value = [value]
        report["evidence"]["candidate"]["paths"] = value
    elif case == "string_limit": report["evidence"]["candidate"]["paths"] = ["x" * 65537]
    elif case == "aggregate_limit": report["evidence"]["candidate"]["paths"] = ["x" * 65536] * 17
    else: report["evidence"]["candidate"]["paths"] = [None] * 50001
    assert _api()(report, request=request) is None


def test_normalizer_preserves_canonical_projection_identity():
    request, report = _case()
    report["evidence"]["candidate"]["paths"] = ["x" * 65536]
    _seal(report)
    result = _api()(report, request=request)
    assert result is not None
    assert result["projection"]["evidence"]["projection_id"] == report["evidence"]["projection_id"]
    assert len(result["projection"]["evidence"]["candidate"]["paths"][0]) == 65536
