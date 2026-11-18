"""Additive source-review controls; original 75 acceptance cases unchanged."""
import pytest

from modules.infrastructure.wre_core.tests.wre_registry_telemetry_test_support import (
    _api, _case, _seal,
)


SIDE_CASES = [
    ("registry_digest", None), ("registry_digest", True),
    ("registry_digest", "sha256:" + "g" * 64),
    ("plan_digest", False), ("plan_digest", "sha256:abc"),
    ("shard_ids", "demo-unit"), ("shard_ids", [True]),
    ("paths", None), ("paths", "test_a.py"), ("paths", [True]),
    ("batches", ["demo-unit"]), ("batches", [[True]]),
]
SIDE_IDS = ["registry-none", "registry-bool", "registry-nonhex", "plan-bool",
            "plan-short", "shards-string", "shards-bool-item", "paths-none",
            "paths-string", "paths-bool-item", "batches-flat", "batches-bool-item"]


@pytest.mark.parametrize("side", ["base", "candidate"])
@pytest.mark.parametrize("field,value", SIDE_CASES, ids=SIDE_IDS)
def test_side_plan_rejects_malformed_field_shapes(side, field, value):
    request, report = _case()
    assert _api()(report, request=request) is not None
    report["evidence"][side][field] = value
    _seal(report)  # A valid public body hash does not repair malformed shape.
    assert _api()(report, request=request) is None


@pytest.mark.parametrize("field", ["lineage_digest", "worktree_path_digest",
                                    "repository_common_dir_digest"])
@pytest.mark.parametrize("value", [True, "sha256:" + "g" * 64], ids=["bool", "nonhex"])
def test_top_projection_digest_requires_digest_string(field, value):
    request, report = _case()
    assert _api()(report, request=request) is not None
    report["evidence"][field] = value
    _seal(report)
    assert _api()(report, request=request) is None


@pytest.mark.parametrize("value", [None, True, "test_a.py", [True], [None]],
                         ids=["none", "bool", "string", "bool-item", "none-item"])
def test_matching_malformed_changed_paths_do_not_become_scope(value):
    request, report = _case()
    assert _api()(report, request=request) is not None
    request["expected_changed_paths"] = value
    report["evidence"]["changed_paths"] = value
    _seal(report)
    assert _api()(report, request=request) is None


@pytest.mark.parametrize("side", ["base", "candidate"])
def test_one_empty_side_remains_a_valid_projection_shape(side):
    request, report = _case()
    assert _api()(report, request=request) is not None
    # Owner permits no shards on one side, e.g. first test added / last removed.
    report["evidence"][side].update(shard_ids=[], paths=[], batches=[])
    _seal(report)
    result = _api()(report, request=request)
    assert result is not None and result["telemetry_completed"] is True
    assert result["projection"]["evidence"][side]["paths"] == []


@pytest.mark.parametrize("location", ["report", "request"])
def test_custom_metaclass_comparison_is_never_called(location):
    calls = []

    class HostileType(type):
        def __eq__(cls, other):
            calls.append("equality")
            raise AssertionError("caller metaclass comparison invoked")

    class Hostile(metaclass=HostileType):
        pass

    request, report = _case()
    assert _api()(report, request=request) is not None
    if location == "report":
        report["evidence"]["base"]["paths"] = [Hostile()]
    else:
        request["projection_input"]["omitted_scope_rationale"] = Hostile()
    assert _api()(report, request=request) is None
    assert calls == []
