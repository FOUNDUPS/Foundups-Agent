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


def _bootstrap_projection_policy(schema):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    # Hash-dependency fixture only, never a signed/admissible owner policy.
    policy = {name: "fixture-" + name for name in pc.POLICY_FIELDS_V8}
    policy.update(schema_version=schema, allowed_operations=["signer_socket_peer_handshake"],
                  allowed_authority_tiers=["LOW"], consensus_required_tiers=[],
                  rate_limit_window_seconds=60, rate_limit_max_requests=1)
    return policy


def _bootstrap_permission_receipt(manifest):
    from modules.communication.moltbot_bridge.src import reddog_grant_authority_wsp71_permission_contract as rc
    receipt = {name: "fixture-" + name for name in rc.FIELDS}
    digest = "sha256:" + "1" * 64
    receipt.update(schema_version=rc.SCHEMA_VERSION, e0_manifest_id=manifest,
                   e0_artifact_generation_digest=digest, e0_generation=1,
                   signing_key_ref_hash=digest, audit_mac_key_ref_hash=digest,
                   permission=rc.SECRETS_READ, allowed_operations=[rc.GET_SECRET],
                   issued_at=1000, expires_at=1600, revoked=False)
    receipt["receipt_id"] = rc.permission_receipt_id(receipt)
    return rc.validate_permission_receipt(receipt)


@pytest.mark.parametrize("schema,acyclic", [
    ("reddog-signer-owner-e0-policy.v8", False),
    ("reddog-signer-owner-e0-policy.v9", True),
])
def test_bootstrap_permission_can_bind_resulting_target_manifest(tmp_path, schema, acyclic):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import canonical_json, manifest_id_for, raw_digest
    from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_config_supply_contract import canonical_config_digest
    from modules.communication.moltbot_bridge.tests.test_reddog_signer_socket_service_config_supply import _initial_config
    policy = _bootstrap_projection_policy(schema)
    _, config = _initial_config(tmp_path)
    before = pc.signer_owner_e0_authority_binding_digest(policy)
    config["owner_e0_authority_binding_digest"] = before
    # Reduced manifest demonstrates the real hash edge, not runtime admission.
    manifest = manifest_id_for({"signer_service_config_digest": canonical_config_digest(config)})
    receipt = _bootstrap_permission_receipt(manifest)
    policy.update(grant_authority_permission_snapshot_digest=raw_digest(canonical_json(receipt).encode("ascii")),
                  grant_authority_permission_snapshot_receipt_id=receipt["receipt_id"])
    after = pc.signer_owner_e0_authority_binding_digest(policy)
    config["owner_e0_authority_binding_digest"] = after
    resulting = manifest_id_for({"signer_service_config_digest": canonical_config_digest(config)})
    assert (before == after) is acyclic
    assert (receipt["e0_manifest_id"] == resulting) is acyclic


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


# Recorded before v9 against 385de3a06; synthetic hash fixtures, not authority.
_LEGACY_PROJECTION_VECTORS = [('reddog-signer-owner-e0-policy.v5',
  'sha256:33f31523036a07f87edf3b89757bab3c365054abcad84aab37dd45358460abe2',
  'sha256:a054db0cf502d9261dc7667cb2e8672a48f48f59768cad3c421f0b4a516e825b',
  '1188c7c06500aa7cf7fb184e6b70c8cfe75467ba386c77767a08c2e1f6635a0b'),
 ('reddog-signer-owner-e0-policy.v6',
  'sha256:9bc64091ff8fa4211dcd0b2b48cae091fb3d28f5b8a1a2b91131b7ec4d470177',
  'sha256:4a6177d3c2b7538b114b699237ba6bc7571d0352a821a2d452b5e69e5db36123',
  '5f38a69fe5a07a138270149950a6f28c71cdab0e10bea6075c15674457d42c66'),
 ('reddog-signer-owner-e0-policy.v7',
  'sha256:975a7febc3ed55e868bc9a0c63aefceba1ef34a6d4d0cf81f9e3083f253fe409',
  'sha256:77343b6112a4886f445d2e5de6184e658514a84a257a2ef6e6e08e7832e0da2c',
  '7b8f4c88b967c1a89d78a989e7096f3773646b62142bfd6b98456d9a26e3e70f'),
 ('reddog-signer-owner-e0-policy.v8',
  'sha256:706348da87f7f27f50641d11075465f28cb891ef0f8de8a1219330538cb36112',
  'sha256:9875e7ee69615c59e70e0b8ae05f970c69236b04dad045da596cc901539c4d24',
  'e94f017991d2cdd1609f162b2cabac9acdcb5594b9e65bff987ab9aa5d622827')]
_V9_STABLE_FIELDS = ['allowed_authority_tiers',
 'allowed_operations',
 'audit_mac_key_ref_hash',
 'consensus_required_tiers',
 'grant_authority_archive_source_descriptor_digest',
 'grant_authority_audit_mac_key_ref_hash',
 'grant_authority_key_epoch',
 'grant_authority_key_fingerprint',
 'grant_authority_principal_id',
 'grant_authority_principal_provider',
 'grant_authority_public_key',
 'grant_authority_signer_agent_id',
 'grant_authority_signer_profile_id',
 'grant_authority_signing_key_ref_hash',
 'grant_authority_source_commit_sha',
 'grant_authority_source_object_format',
 'grant_authority_source_policy_digest',
 'grant_authority_source_repo_root_digest',
 'grant_requester_principal_id',
 'permission_snapshot_digest',
 'permission_snapshot_receipt_id',
 'rate_limit_max_requests',
 'rate_limit_window_seconds',
 'replay_path',
 'replay_root',
 'replay_store_durability_receipt_id',
 'replay_store_id',
 'revocation_anchor_state_binding_digest',
 'revocation_anchor_store_durability_receipt_id',
 'revocation_anchor_store_id',
 'revocation_authority_principal_id',
 'revocation_authority_principal_provider',
 'revocation_authority_public_key',
 'revocation_lock_path',
 'revocation_path',
 'revocation_root',
 'revocation_snapshot_schema',
 'revocation_store_durability_receipt_id',
 'revocation_store_id',
 'revocation_store_schema',
 'revocation_witness_path',
 'revocation_witness_root',
 'revocation_witness_store_durability_receipt_id',
 'revocation_witness_store_id',
 'signing_key_ref_hash',
 'target_signer_agent_id',
 'target_signer_key_epoch',
 'target_signer_key_fingerprint',
 'target_signer_profile_id',
 'target_signer_public_key']


@pytest.mark.parametrize("schema,binding,identity,signing_hash", _LEGACY_PROJECTION_VECTORS)
def test_legacy_projection_golden_vectors(schema, binding, identity, signing_hash):
    import hashlib
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    sample = {field: "fixture-" + field for field in pc._policy_fields(schema)}
    sample.update(schema_version=schema, allowed_operations=["signer_peer_handshake"],
                  allowed_authority_tiers=["LOW"], consensus_required_tiers=[], generation=1,
                  issued_at=1000, expires_at=1600, rate_limit_window_seconds=60, rate_limit_max_requests=1)
    assert pc.signer_owner_e0_authority_binding_digest(sample) == binding
    assert pc.signer_owner_e0_policy_id(sample) == identity
    assert hashlib.sha256(pc.canonical_signer_owner_e0_policy_input(sample).encode("ascii")).hexdigest() == signing_hash


def _v9_signed_fixture():
    import hashlib
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import encode_ed25519_public_key, encode_ed25519_signature
    value = _bootstrap_projection_policy(pc.POLICY_SCHEMA_V9)
    for field in pc._DIGEST_FIELDS_V7:
        value[field] = "sha256:" + "d" * 64
    key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))  # Disposable fixture only.
    public = encode_ed25519_public_key(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))
    value.update(generation=1, issued_at=1000, expires_at=1600,
                 grant_authority_public_key=public, target_signer_public_key=encode_ed25519_public_key(bytes(range(1, 33))),
                 grant_authority_key_fingerprint="sha256:" + hashlib.sha256(public.encode("ascii")).hexdigest(),
                 grant_authority_signer_agent_id="grant:review", target_signer_agent_id="signer:reddog",
                 grant_authority_signer_profile_id="grant-review", target_signer_profile_id="reddog-work-authority",
                 grant_authority_key_epoch="epoch-grant", target_signer_key_epoch="epoch-target",
                 grant_authority_source_object_format="sha1", grant_authority_source_commit_sha="1" * 40)
    for number, field in enumerate(("signing_key_ref_hash", "audit_mac_key_ref_hash",
            "grant_authority_signing_key_ref_hash", "grant_authority_audit_mac_key_ref_hash"), 1):
        value[field] = "sha256:" + str(number) * 64
    value["policy_id"] = pc.signer_owner_e0_policy_id(value)
    value["signature"] = encode_ed25519_signature(key.sign(pc.canonical_signer_owner_e0_policy_input(value).encode("ascii")))
    pc.validated_signer_owner_e0_policy(value, now_epoch=1100)
    return value


@pytest.mark.parametrize("field", _V9_STABLE_FIELDS)
def test_v9_retains_every_known_authority_field(field):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    original = _v9_signed_fixture()
    changed = copy.deepcopy(original)
    item = changed[field]
    changed[field] = item + ["MUTATED"] if isinstance(item, list) else item + 1 if type(item) is int else item + "-changed"
    assert pc.signer_owner_e0_authority_binding_digest(original) != pc.signer_owner_e0_authority_binding_digest(changed)


@pytest.mark.parametrize("field", ["grant_authority_permission_snapshot_digest", "grant_authority_permission_snapshot_receipt_id"])
def test_v9_future_permission_is_still_required_and_signed(field):
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    original = _v9_signed_fixture()
    verifier = Ed25519SignatureVerifier()
    assert verifier.verify(original["grant_authority_public_key"], pc.canonical_signer_owner_e0_policy_input(original), original["signature"])
    changed = dict(original, **{field: "sha256:" + "e" * 64})
    assert pc.signer_owner_e0_authority_binding_digest(original) == pc.signer_owner_e0_authority_binding_digest(changed)
    assert pc.signer_owner_e0_policy_id(changed) != original["policy_id"]
    changed["policy_id"] = pc.signer_owner_e0_policy_id(changed)
    assert not verifier.verify(original["grant_authority_public_key"], pc.canonical_signer_owner_e0_policy_input(changed), original["signature"])
    for bad in (None, True, 7, "", "sha256:invalid"):
        malformed = dict(original, **{field: bad})
        malformed["policy_id"] = pc.signer_owner_e0_policy_id(malformed)
        with pytest.raises(ValueError):
            pc.validated_signer_owner_e0_policy(malformed, now_epoch=1100)
    missing = dict(original)
    missing.pop(field)
    with pytest.raises(ValueError, match="malformed"):
        pc.validated_signer_owner_e0_policy(missing, now_epoch=1100)


def test_v9_partial_projection_is_not_full_authority_and_cannot_downgrade():
    from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_policy_contract as pc
    from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import Ed25519SignatureVerifier
    value = _v9_signed_fixture()
    partial = {field: value[field] for field in _V9_STABLE_FIELDS}
    partial["schema_version"] = pc.POLICY_SCHEMA_V9
    assert pc.signer_owner_e0_authority_binding_digest(partial) == pc.signer_owner_e0_authority_binding_digest(value)
    with pytest.raises(ValueError, match="malformed"):
        pc.validated_signer_owner_e0_policy(partial, now_epoch=1100)
    changed = dict(value, schema_version=pc.POLICY_SCHEMA_V8)
    assert not Ed25519SignatureVerifier().verify(value["grant_authority_public_key"], pc.canonical_signer_owner_e0_policy_input(changed), value["signature"])
    assert pc.POLICY_SCHEMA == pc.POLICY_SCHEMA_V6
    for schema in ("reddog-signer-owner-e0-policy.v10", None, True, 9):
        with pytest.raises(ValueError):
            pc.canonical_signer_owner_e0_policy_input(dict(value, schema_version=schema))
