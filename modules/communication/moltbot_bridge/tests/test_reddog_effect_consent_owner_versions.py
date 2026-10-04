"""Real v6 validation and explicit inert seams at OS/service boundaries."""

from contextlib import contextmanager
from copy import deepcopy
import importlib
from types import SimpleNamespace
import pytest

from modules.communication.moltbot_bridge.tests.reddog_effect_consent_test_support import (
    ROOT, api, canonical, digest, materials,
)
from modules.communication.moltbot_bridge.tests.test_reddog_reviewer_owner_versions import owner_data
from modules.communication.moltbot_bridge.tests.reddog_reviewer_composition_test_support import (
    assert_closed, setup as reviewer_setup,
)


def owner_fixture(monkeypatch, tmp_path):
    api()
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    assert getattr(loader, "SCHEMA_VERSION_V6", None) == "reddog_signer_system_service_owner_config.v6", "effect_owner_v6_api_missing"
    repo, root, owner, additions, _ = owner_data(tmp_path)
    keys = ("verified_outcome_authority", "independent_grant_authority", "grant_authority_source_policy", "reviewer_designation_authority")
    owner.update(dict(zip(keys, additions)))
    owner.update(schema_version=loader.SCHEMA_VERSION_V6, effect_consent_authority=materials(monkeypatch).authority)
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw = [canonical(owner).encode("ascii")]
    monkeypatch.setattr(loader, "_read_root_owned_bytes", lambda *args: raw[0])
    return loader, repo, root / "owner.json", owner, raw


OWNER_CASES = ["valid", "missing", "extra", "duplicate", "config_digest", "outcome", "grant", "source_policy", "reviewer", "consent"]


@pytest.mark.parametrize("case", OWNER_CASES)
def test_effect_consent_owner_v6_inherits_every_validator(monkeypatch, tmp_path, case):
    loader, repo, path, owner, raw = owner_fixture(monkeypatch, tmp_path)
    assert loader._load_owner_config(path, repo=repo) == owner
    assert loader.V6_FIELDS == loader.V5_FIELDS | {"effect_consent_authority"}
    if case == "missing":
        owner.pop("effect_consent_authority")
    elif case == "extra":
        owner["effect_granted"] = True
    elif case == "outcome":
        owner["verified_outcome_authority"]["authority_service_uid"] = 1
    elif case == "grant":
        owner["independent_grant_authority"]["authority_service_uid"] = 0
    elif case == "source_policy":
        owner["grant_authority_source_policy"]["source_policy_digest"] = "sha256:" + "0" * 64
    elif case == "reviewer":
        owner["reviewer_designation_authority"]["privilege"] = "authorize_exact_high_worktree_effect"
    elif case == "consent":
        owner["effect_consent_authority"]["privilege"] = "designate_effect_reviewers"
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    if case == "config_digest":
        owner["config_id"] = "sha256:" + "0" * 64
    text = canonical(owner)
    if case == "duplicate":
        text = text[:-1] + ',"config_id":' + canonical(owner["config_id"]) + '}'
    raw[0] = text.encode("ascii")
    if case == "valid":
        assert loader._load_owner_config(path, repo=repo) == owner
    else:
        with pytest.raises(loader.RuntimeArtifactManifestError):
            loader._load_owner_config(path, repo=repo)


def test_effect_consent_v6_startup_policy_and_grant_owner_edges(monkeypatch, tmp_path):
    loader, repo, path, owner, raw = owner_fixture(monkeypatch, tmp_path)
    selected, boundary = object(), object()
    monkeypatch.setattr(loader, "_manifest_selection_from_owner", lambda *args, **kwargs: (selected, boundary))
    def forbidden(*args, **kwargs):
        raise AssertionError("startup selection must not resolve signing authority")
    monkeypatch.setattr(loader, "_verified_outcome_authority_from_owner", forbidden)
    result = loader.load_system_service_startup_selection(owner_config_path=path, repo_root=repo)
    assert result.owner_config_id == owner["config_id"] and result.manifest_selection is selected
    assert result.manifest_selection_boundary is boundary
    binding = importlib.import_module(ROOT + "reddog_grant_authority_service_owner_binding")
    policy_api = importlib.import_module(ROOT + "reddog_grant_authority_source_policy_authority")
    assert binding.grant_authority_owner_runtime_root(path, repo, owner["config_id"]) == (tmp_path / "grant").resolve()
    token, current = policy_api.load_grant_authority_source_policy_authority(owner_config_path=path, repo_root=repo)
    assert current.revalidate(token)["owner_config_id"] == owner["config_id"]
    with pytest.raises(loader.RuntimeArtifactManifestError):
        binding.grant_authority_owner_runtime_root(path, repo, "sha256:" + "0" * 64)
    owner["anchor_id"] = "changed"
    owner["config_id"] = digest({k: v for k, v in owner.items() if k != "config_id"})
    raw[0] = canonical(owner).encode("ascii")
    with pytest.raises(loader.RuntimeArtifactManifestError):
        current.revalidate(token)


def test_effect_consent_v6_grant_supply_schema_edge_only(monkeypatch, tmp_path):
    _, repo, path, owner, _ = owner_fixture(monkeypatch, tmp_path)
    supply = importlib.import_module(ROOT + "reddog_signer_independent_grant_authority_client_supply")
    calls, sentinel = [], object()
    policy = {"owner_config_id": owner["config_id"]}
    @contextmanager
    def admission(**kwargs):
        calls.append("enter")
        try:
            yield SimpleNamespace(policy=policy)
        finally:
            calls.append("exit")
    def build(**kwargs):
        assert kwargs["owner"] == owner and kwargs["policy"] is policy
        assert owner["schema_version"] in kwargs["required_schemas"]
        assert {"reddog_signer_system_service_owner_config.v3", "reddog_signer_system_service_owner_config.v4",
                "reddog_signer_system_service_owner_config.v5"}.issubset(kwargs["required_schemas"])
        calls.append("build")
        return sentinel
    monkeypatch.setattr(supply, "lease_validated_owner_e0_current_admission", admission)
    monkeypatch.setattr(supply, "_build_authenticated_supply", build)
    assert supply.load_system_service_independent_grant_authority_client(
        owner_config_path=path, repo_root=repo, owner_policy=policy) is sentinel
    assert calls == ["enter", "build", "exit"]


def test_effect_consent_v6_retains_reviewer_verification(monkeypatch, tmp_path):
    api()
    verify, state = reviewer_setup(monkeypatch, tmp_path)
    assert verify(**state.call) is True
    assert_closed(state)
    state.reads = 0
    state.crypto.clear()
    state.lease.selected = state.lease.entered = state.lease.exited = 0
    state.owner["schema_version"] = "reddog_signer_system_service_owner_config.v6"
    state.owner["effect_consent_authority"] = materials(monkeypatch).authority
    assert verify(**state.call) is True
    assert len(state.crypto) == 2 and all(c[3] is True for c in state.crypto)
    assert state.reads == 2
    assert_closed(state)


def test_effect_consent_windows_does_not_bypass_linux_owner_guard(monkeypatch, tmp_path):
    api()
    loader = importlib.import_module(ROOT + "reddog_signer_system_service_manifest_selection_loader")
    monkeypatch.setattr(loader.sys, "platform", "win32")
    with pytest.raises(loader.RuntimeArtifactManifestError, match="signer_owner_linux_service_required"):
        loader._read_root_owned_bytes(tmp_path / "not-created.json", tmp_path)
