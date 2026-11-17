"""Connected supply writes identities, never reviewer permissions or live authority."""

from copy import deepcopy
from dataclasses import asdict
import importlib
import inspect
import json
import pytest

from modules.communication.moltbot_bridge.tests.reddog_reviewer_authority_test_support import (
    ROOT, artifact, canonical, digest, fixture, sign,
)


def _identity_inputs(public_key):
    from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import PrincipalAuthorityRecord
    from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import PermissionSnapshot
    main = PrincipalAuthorityRecord("github:mjtrout", "github", public_key,
        ("FOUNDUPS/Foundups-Agent",), ("paccess_001",), "sha256:" + "b" * 64,
        reward_account="reward:paccess", owner_dae="dae:paccess")
    snapshot = PermissionSnapshot("sha256:" + "a" * 64, 1800003600, True, False, "FOUNDUPS/Foundups-Agent")
    return json.loads(canonical(main.to_dict())), asdict(snapshot)


@pytest.mark.parametrize("case", ["two_principals", "duplicate", "collision", "missing", "extra",
    "key_mismatch", "repo_mismatch", "foundup_mismatch", "without_designation", "separator_alias"])
def test_reviewer_principal_supply(tmp_path, case):
    api = importlib.import_module(ROOT + "reddog_authority_runtime_resolver_artifact_supply")
    supply = api.run_reddog_authority_runtime_resolver_artifact_supply
    assert "reviewer_principal_records" in inspect.signature(supply).parameters, "reviewer_principal_supply_missing"
    authority, grant, issuer, _ = fixture()
    main, snapshot = _identity_inputs(authority["issuer_public_key"])
    authority.update(repo_full_name=snapshot["repo_full_name"], foundup_id=main["foundup_scope"][0])
    grant.update(repo_full_name=authority["repo_full_name"], foundup_id=authority["foundup_id"], owner_authority_digest=digest(authority))
    sign(grant, issuer)
    record = next(iter(artifact(authority, grant)["principals"].values()))
    records, grants = [record], [grant]
    if case == "duplicate":
        records.append(deepcopy(record))
    elif case == "collision":
        records = [main]
    elif case == "missing":
        records = []
    elif case == "extra":
        records.append(dict(record, principal_id="reviewer:extra"))
    elif case == "key_mismatch":
        record["principal_public_key"] = main["principal_public_key"]
    elif case in {"repo_mismatch", "foundup_mismatch"}:
        record["repo_scope" if case == "repo_mismatch" else "foundup_scope"] = ["other"]
    elif case == "without_designation":
        grants = None
    elif case == "separator_alias":
        grant["reviewers"][0].update(principal_provider="test", principal_id="reviewer|test")
        record.update(principal_provider="test|reviewer", principal_id="test")
        sign(grant, issuer)
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "runtime"
    result = supply(repo_root=repo, principal_authority_record=main, permission_snapshot=snapshot,
        principal_records_output_path=output / "principal.json", permission_snapshots_output_path=output / "permission.json",
        reviewer_authorizations=grants, reviewer_principal_records=records)
    assert result.accepted is (case == "two_principals")
    if case != "two_principals":
        assert not output.exists(), "invalid reviewer supply must reject before output writes"
        return
    principals = json.loads((output / "principal.json").read_text(encoding="utf-8"))
    permissions = json.loads((output / "permission.json").read_text(encoding="utf-8"))
    assert result.principal_records_loaded == principals["principal_count"] == 2
    assert result.permission_snapshots_loaded == permissions["snapshot_count"] == 1
    assert principals["schema_version"] == "reddog_authority_runtime_resolver_supply.v2"
    assert permissions["schema_version"] == "reddog_authority_runtime_resolver_supply.v1"
    assert principals["principals"]["test|reviewer:test"] == record
    assert principals["principals"][main["principal_provider"] + "|" + main["principal_id"]] == main
    assert "reviewer_authorizations" not in permissions
