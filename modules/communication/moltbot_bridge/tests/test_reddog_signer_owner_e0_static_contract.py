"""Static and capability-state tests for signer owner E0 admission."""

from __future__ import annotations

import ast
import copy
import pickle
import time
from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import (
    SLICE_MODULES,
    _CURRENT_SELECTION,
    _SelectionBoundary,
    _fixture,
    _resign,
)
from modules.communication.moltbot_bridge.src import (
    reddog_signer_owner_e0_current_selection as current_selection_module,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_admission_validation import (
    require_policy_authorities,
)
from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import (
    signer_owner_e0_policy_id,
    validated_signer_owner_e0_policy,
)


class _AuthorityResolver:
    def __init__(self, values: dict[tuple[str, str], str]) -> None:
        self._values = values

    def resolve(self, principal_id: str, principal_provider: str) -> str | None:
        return self._values.get((principal_id, principal_provider))


@pytest.mark.parametrize("operations,tiers,consensus,accepted", [
    (["signer_socket_peer_handshake"], ["LOW"], [], True),
    (["write_repo"], ["LOW"], [], False),
    (["signer_socket_peer_handshake", "write_repo"], ["LOW"], [], False),
    (["signer_socket_peer_handshake"], ["HIGH"], [], False),
    (["signer_socket_peer_handshake"], [], [], False),
    ([], ["LOW"], [], False),
    (["write_repo"], ["HIGH"], ["HIGH"], True),
])
def test_empty_e0_consensus_is_only_low_handshake(operations, tiers, consensus, accepted):
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import _require_lists
    scope = {"allowed_operations": operations, "allowed_authority_tiers": tiers,
             "consensus_required_tiers": consensus}
    if accepted:
        _require_lists(scope)
    else:
        with pytest.raises(ValueError, match="scope_invalid"):
            _require_lists(scope)


@pytest.mark.parametrize("mutation", ["valid", "generation", "boolean-generation", "work", "tier", "consensus"])
def test_initial_e0_config_requires_independent_exact_scope(tmp_path, mutation):
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_admission_validation import require_policy_config_binding
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_policy_contract import signer_key_reference_digest
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_rehydration import rehydrate_signer_socket_service_runtime_config
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply_contract import canonical_config_digest
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_config_supply import _initial_config
    repo, payload = _initial_config(tmp_path)
    config = rehydrate_signer_socket_service_runtime_config(
        repo, Path(payload["runtime_root"]), payload, expected_config_digest=canonical_config_digest(payload))
    profile = payload["key_provider_profiles"][0]
    policy = {
        "generation": 1, "allowed_operations": ["signer_socket_peer_handshake"],
        "allowed_authority_tiers": ["LOW"], "consensus_required_tiers": [],
        "target_signer_agent_id": profile["signer_agent_id"],
        "target_signer_profile_id": profile["signer_profile_id"],
        "target_signer_public_key": profile["expected_public_key"],
        "target_signer_key_fingerprint": profile["expected_key_fingerprint"],
        "target_signer_key_epoch": profile["expected_key_epoch"],
        "target_signer_generation_id": "sha256:" + "3" * 64,
        "artifact_generation_digest": "sha256:" + "3" * 64,
        "permission_snapshot_digest": profile["permission_snapshot_digest"],
        "signing_key_ref_hash": signer_key_reference_digest(profile["signing_key_ref"]),
        "audit_mac_key_ref_hash": signer_key_reference_digest(profile["audit_mac_key_ref"]),
    }
    policy.update({
        "generation": {"generation": 2}, "boolean-generation": {"generation": True},
        "work": {"allowed_operations": ["write_repo"]},
        "tier": {"allowed_authority_tiers": ["HIGH"]},
        "consensus": {"consensus_required_tiers": ["LOW"]},
    }.get(mutation, {}))
    if mutation == "valid":
        assert require_policy_config_binding(policy, config).signer_agent_id == "signer:reddog"
    else:
        with pytest.raises(ValueError, match="initial_handshake_scope_invalid"):
            require_policy_config_binding(policy, config)


class _AcceptingSignatureVerifier:
    @staticmethod
    def verify(_public_key: str, _message: str, _signature: str) -> bool:
        return True


def _authority_resolver(policy: dict[str, object]) -> _AuthorityResolver:
    return _AuthorityResolver(
        {
            (
                str(policy[f"{prefix}_principal_id"]),
                str(policy[f"{prefix}_principal_provider"]),
            ): str(policy[f"{prefix}_public_key"])
            for prefix in ("grant_authority", "revocation_authority")
        }
    )


@pytest.fixture(autouse=True)
def _root_owned_selection_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    def load(**_kwargs: object) -> tuple[object, _SelectionBoundary]:
        capability = object()
        return capability, _SelectionBoundary(capability, _CURRENT_SELECTION)

    monkeypatch.setattr(
        current_selection_module,
        "load_system_service_manifest_selection",
        load,
    )


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("valid", None),
        ("same_principal", "e0_policy_authorities_not_independent"),
        ("same_key", "e0_policy_authorities_not_independent"),
        ("grant_target", "e0_policy_self_authority_rejected"),
        ("revocation_target", "e0_policy_self_authority_rejected"),
        ("requester_grant", "e0_policy_requester_not_independent"),
        ("requester_target", "e0_policy_requester_not_independent"),
    ],
)
def test_authority_independence_matrix(
    tmp_path: Path, mutation: str, reason: str | None
) -> None:
    fixture = _fixture(tmp_path)
    policy = fixture["policy"]
    if mutation == "same_principal":
        policy["revocation_authority_principal_id"] = policy[
            "grant_authority_principal_id"
        ]
        policy["revocation_authority_principal_provider"] = "gitlab"
    elif mutation == "same_key":
        policy["revocation_authority_public_key"] = policy["grant_authority_public_key"]
    elif mutation == "requester_grant":
        policy["grant_requester_principal_id"] = policy[
            "grant_authority_principal_id"
        ]
    elif mutation == "requester_target":
        policy["grant_requester_principal_id"] = policy["target_signer_agent_id"]
    elif mutation.endswith("_target"):
        prefix = mutation.removesuffix("_target") + "_authority_public_key"
        policy[prefix] = fixture["target_public"]
    kwargs = {
        "principal_key_resolver": _authority_resolver(policy),
        "signature_verifier": _AcceptingSignatureVerifier(),
    }
    if reason is None:
        require_policy_authorities(policy, **kwargs)
    else:
        with pytest.raises(ValueError, match=f"^{reason}$"):
            require_policy_authorities(policy, **kwargs)


def test_caller_cannot_mutate_policy_after_admission(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is True
    fixture["policy"]["allowed_operations"].append("issue_principal_identity")
    receipt = fixture["boundary"].consume(result.capability)
    assert receipt.policy_id == result.policy_id


def test_owner_policy_rejects_noncanonical_authority_tier(tmp_path: Path) -> None:
    policy = _fixture(tmp_path)["policy"]
    policy["allowed_authority_tiers"] = ["HIGH", "SOVEREIGN"]
    policy["consensus_required_tiers"] = ["HIGH", "SOVEREIGN"]
    policy["policy_id"] = signer_owner_e0_policy_id(policy)
    with pytest.raises(ValueError, match="scope_invalid"):
        validated_signer_owner_e0_policy(policy, now_epoch=int(time.time()))


@pytest.mark.parametrize("mutation", ["missing", "extra"])
def test_owner_policy_requires_exact_grant_authority_epoch_schema(
    tmp_path: Path, mutation: str
) -> None:
    policy = _fixture(tmp_path)["policy"]
    if mutation == "missing":
        policy.pop("grant_authority_key_epoch")
    else:
        policy["grant_authority_epoch"] = policy["grant_authority_key_epoch"]
    with pytest.raises(ValueError, match="policy_malformed"):
        validated_signer_owner_e0_policy(policy, now_epoch=int(time.time()))


def test_admission_capability_is_one_use(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is True
    fixture["boundary"].consume(result.capability)
    with pytest.raises(ValueError):
        fixture["boundary"].consume(result.capability)


def test_runtime_roots_must_be_disjoint(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["policy"]["revocation_root"] = fixture["policy"]["replay_root"]
    fixture["policy"]["revocation_path"] = str(
        Path(str(fixture["policy"]["replay_root"])) / "revocations.db"
    )
    _resign(fixture)
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


@pytest.mark.parametrize("root_name", ["separate", "replay_root", "revocation_root", "revocation_witness_root"])
def test_initial_socket_root_is_disjoint_from_e0_stores(tmp_path, root_name):
    from types import SimpleNamespace
    from modules.communication.moltbot_bridge.src.reddog_signer_owner_e0_admission_validation import require_policy_runtime_paths
    fixture = _fixture(tmp_path)
    policy = fixture["policy"]
    root = tmp_path / "socket-state" if root_name == "separate" else Path(policy[root_name])
    config = SimpleNamespace(initial_handshake_only=True, socket_path=root / "signer.sock")
    kwargs = dict(repo_root=tmp_path / "repo", signer_runtime_root=tmp_path / "signer",
                  initial_config=config)
    if root_name == "separate":
        require_policy_runtime_paths(policy, **kwargs)
    else:
        with pytest.raises(ValueError, match="socket_root_not_disjoint"):
            require_policy_runtime_paths(policy, **kwargs)


@pytest.mark.parametrize(
    "field",
    [
        "revocation_snapshot_schema", "revocation_store_schema",
        "revocation_witness_root", "revocation_witness_path",
        "revocation_witness_store_id",
        "revocation_witness_store_durability_receipt_id",
        "revocation_lock_path",
    ],
)
def test_revocation_topology_is_inside_signed_policy(
    tmp_path: Path, field: str,
) -> None:
    fixture = _fixture(tmp_path)
    fixture["policy"][field] = str(fixture["policy"][field]) + "-attacker"
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_witness_root_cannot_overlap_replay_domain(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    replay_root = Path(str(fixture["policy"]["replay_root"]))
    fixture["policy"]["revocation_witness_root"] = str(replay_root)
    fixture["policy"]["revocation_witness_path"] = str(
        replay_root / "revocation-witness.sqlite3"
    )
    _resign(fixture)
    assert fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    ).accepted is False


def test_capability_cannot_be_copied_or_pickled(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is True
    with pytest.raises(TypeError):
        copy.copy(result.capability)
    with pytest.raises(TypeError):
        copy.deepcopy(result.capability)
    with pytest.raises(TypeError):
        pickle.dumps(result.capability)


def test_slice_has_no_effect_runtime_imports_or_calls() -> None:
    source_root = Path(__file__).parents[1] / "src"
    banned_imports = {
        "subprocess",
        "socket",
        "secrets_mcp.src.op_cli_secret_resolver",
    }
    banned_calls = {
        "bind",
        "connect",
        "listen",
        "popen",
        "run",
        "start",
        "resolve_signer_key",
        "build_signer_backend_from_provider",
    }
    for filename in SLICE_MODULES:
        tree = ast.parse((source_root / filename).read_text(encoding="ascii"))
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            str(node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        calls = {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Attribute, ast.Name))
        }
        assert not any(
            item == banned or item.endswith("." + banned)
            for item in imports
            for banned in banned_imports
        )
        assert calls.isdisjoint(banned_calls)


def test_slice_obeys_wsp62_module_and_function_limits() -> None:
    source_root = Path(__file__).parents[1] / "src"
    for filename in SLICE_MODULES:
        text = (source_root / filename).read_text(encoding="ascii")
        assert len(text.splitlines()) <= 200
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 50


def test_slice_test_helpers_obey_wsp62_function_limit() -> None:
    test_root = Path(__file__).parent
    for filename in (
        "test_reddog_signer_owner_controlled_e0_admission.py",
        "test_reddog_signer_owner_e0_static_contract.py",
    ):
        text = (test_root / filename).read_text(encoding="ascii")
        assert len(text.splitlines()) <= 675
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert (node.end_lineno or node.lineno) - node.lineno + 1 <= 60
