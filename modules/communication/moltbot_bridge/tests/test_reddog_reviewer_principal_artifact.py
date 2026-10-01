"""Principal v2 preserves identities and keeps strict legacy parsing separate."""

from copy import deepcopy
import importlib
import pytest

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, artifact, canonical, fixture,
)


@pytest.mark.parametrize("case", ["v1", "v2", "v1_rejects_v2", "unknown", "missing", "extra",
    "duplicate_json", "none", "empty", "two", "bad_inner"])
def test_principal_artifact_version_and_shape(case):
    api = importlib.import_module(ROOT + "reddog_signer_owner_e0_principal_records")
    parse = getattr(api, "parse_principal_artifact", None)
    assert callable(parse), "reviewer_principal_artifact_missing"
    authority, designation, _, _ = fixture()
    value = artifact(authority, designation)
    legacy = {k: v for k, v in value.items() if k != "reviewer_authorizations"}
    legacy["schema_version"] = "reddog_authority_runtime_resolver_supply.v1"
    expected = api.parse_principal_records(canonical(legacy).encode("ascii"))
    if case == "v1":
        records, grants = parse(canonical(legacy).encode("ascii"))
        assert records == expected and grants == ()
        return
    if case == "v2":
        records, grants = parse(canonical(value).encode("ascii"))
        assert records == expected and grants == (designation,)
        assert not hasattr(next(iter(records.values())), "authorized_roles")
        return
    if case == "v1_rejects_v2":
        with pytest.raises(ValueError):
            api.parse_principal_records(canonical(value).encode("ascii"))
        return
    if case == "unknown":
        value["schema_version"] = "reddog_authority_runtime_resolver_supply.v3"
    elif case == "missing":
        value.pop("reviewer_authorizations")
    elif case == "extra":
        value["reviewer_count"] = 1
    elif case in {"none", "empty", "two"}:
        value["reviewer_authorizations"] = {"none": None, "empty": [], "two": [designation, deepcopy(designation)]}[case]
    elif case == "bad_inner":
        value["reviewer_authorizations"][0]["verified"] = True
    raw = canonical(value)
    if case == "duplicate_json":
        raw = raw[:-1] + ',"principal_count":1}'
    with pytest.raises(ValueError):
        parse(raw.encode("ascii"))
