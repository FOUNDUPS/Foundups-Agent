"""Protected signer owner input/layout checks; APIs re-exported by owner loader.

Input supply is not a current-generation proof or execution permission.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Callable, Mapping
from .reddog_runtime_artifact_manifest_contract import RuntimeArtifactManifestError, digest, is_sha256, raw_digest
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path, validate_runtime_root_path, secure_read_confined_bytes,
)

MODEL_VERIFIER_INPUTS = ("catalog", "benchmarks", "promotions", "evidence", "policy", "trusted_keys")


def _validate_outcome_authority_root_separation(
    value: Mapping[str, Any],
    *,
    owner_root: Path,
    state_root: Path,
    witness_root: Path,
    installation_root: Path,
) -> None:
    anchor = Path(value["anchor_path"])
    if not anchor.is_absolute():
        anchor = Path(value["runtime_root"]) / anchor
    existing_roots = tuple(
        Path(value[name]).resolve()
        for name in ("runtime_root", "high_water_root", "witness_root")
    ) + (owner_root, anchor.parent.resolve())
    if any(
        first == second or first in second.parents or second in first.parents
        for first, second in (
            (state_root, witness_root),
            (state_root, installation_root),
            (witness_root, installation_root),
            *(
                (root, other)
                for root in (state_root, witness_root, installation_root)
                for other in existing_roots
            ),
        )
    ):
        raise RuntimeArtifactManifestError("verified_outcome_owner_root_overlap")



def _require_grant_disjoint_root(
    value: Mapping[str, Any], *, owner_root: Path, grant_root: Path,
    policy: Mapping[str, Any] | None = None,
) -> None:
    outcome = value["verified_outcome_authority"]
    existing = [
        owner_root,
        *(Path(value[name]).resolve()
          for name in ("runtime_root", "high_water_root", "witness_root")),
        *(Path(outcome[name]).resolve()
          for name in ("state_root", "state_witness_root", "installation_root")),
    ]
    if policy is not None:
        existing.extend(
            Path(policy[name]).resolve()
            for name in ("replay_root", "revocation_root", "revocation_witness_root")
        )
    _reject_grant_root_overlap(grant_root, existing)


def _reject_grant_root_overlap(root: Path, existing) -> None:
    if any(root == other or root in other.parents or other in root.parents
           for other in existing):
        raise RuntimeArtifactManifestError("grant_authority_owner_root_overlap")


def _grant_socket_root(value, *, repo, owner_root, grant_root, policy=None):
    """V10 separates issuer-writable transport from protected artifact ancestry."""
    from .reddog_signer_system_service_manifest_selection_loader import SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12
    raw = value["independent_grant_authority"]["authority_socket_path"]
    if value.get("schema_version") not in {SCHEMA_VERSION_V10, SCHEMA_VERSION_V11, SCHEMA_VERSION_V12}:
        path = validate_runtime_artifact_path(raw, allowed_root=grant_root, repo_root=repo)
        if path != grant_root / "grant-authority.sock":
            raise RuntimeArtifactManifestError("grant_authority_socket_path_invalid")
        return grant_root
    path = validate_runtime_artifact_path(raw, repo_root=repo)
    root = validate_runtime_root_path(path.parent, repo_root=repo)
    if (not Path(raw).is_absolute() or Path(raw) != path
            or path.name != "grant-authority.sock" or not root.is_dir()):
        raise RuntimeArtifactManifestError("grant_authority_socket_path_invalid")
    _require_grant_disjoint_root(value, owner_root=owner_root, grant_root=root, policy=policy)
    _reject_grant_root_overlap(root, [
        grant_root, _owner_anchor_root(value, repo=repo),
        Path(value["verified_outcome_authority"]["authority_socket_path"]).resolve().parent,
        *(Path(value["grant_rate_store"][name]).resolve()
          for name in ("nonce_root", "high_water_root")),
        Path(value["startup_custody"]["replay_store"]["high_water_root"]).resolve(),
    ])
    return root


def _validate_owner_paths(
    value: Mapping[str, Any], *, repo: Path, owner_root: Path
) -> None:
    runtime = validate_runtime_root_path(value["runtime_root"], repo_root=repo)
    high_root = validate_runtime_root_path(value["high_water_root"], repo_root=repo)
    witness_root = validate_runtime_root_path(value["witness_root"], repo_root=repo)
    anchor_root = _owner_anchor_root(value, repo=repo)
    roots = (runtime, high_root, witness_root)
    if anchor_root != runtime:
        roots += (anchor_root,)
    if any(
        first == second or first in second.parents or second in first.parents
        for first, second in (
            *((first, second) for index, first in enumerate(roots)
              for second in roots[index + 1:]),
            *((owner_root, item) for item in roots),
        )
    ):
        raise RuntimeArtifactManifestError("signer_owner_root_overlap")
    expected = (
        (value["anchor_path"], anchor_root, "generation-anchor.json"),
        (value["high_water_path"], high_root, "high-water.json"),
        (value["witness_path"], witness_root, "generation.sqlite3"),
    )
    for raw_path, root, filename in expected:
        path = validate_runtime_artifact_path(
            raw_path, allowed_root=root, repo_root=repo
        )
        if path != root / filename:
            raise RuntimeArtifactManifestError("signer_owner_path_invalid")


def _owner_anchor_root(value: Mapping[str, Any], *, repo: Path) -> Path:
    """Reuse the approved anchor path; relative legacy paths stay colocated."""
    runtime = validate_runtime_root_path(value["runtime_root"], repo_root=repo)
    raw = value["anchor_path"]
    if not isinstance(raw, str):
        raise RuntimeArtifactManifestError("signer_owner_path_invalid")
    absolute = Path(raw).is_absolute()
    anchor = validate_runtime_artifact_path(
        raw, repo_root=repo, allowed_root=None if absolute else runtime,
    )
    root = validate_runtime_root_path(anchor.parent, repo_root=repo)
    if anchor.name != "generation-anchor.json" or (not absolute and root != runtime):
        raise RuntimeArtifactManifestError("signer_owner_path_invalid")
    return root


def load_system_service_signer_identity(
    *, owner_config_path: Path | str, repo_root: Path,
    expected_owner_config_id: str | None = None,
) -> tuple[int, int]:
    """Load process identity, optionally bound to the caller's selected owner."""

    from . import reddog_signer_system_service_manifest_selection_loader as owner_loader
    owner = owner_loader._load_owner_config(owner_config_path, repo=Path(repo_root).resolve())
    if expected_owner_config_id is not None and expected_owner_config_id != owner["config_id"]:
        raise RuntimeArtifactManifestError("signer_owner_selection_mismatch")
    return owner_loader._signer_identity_from_owner(owner)


def _validate_model_verifier_authority(owner, *, repo):
    value = owner.get("model_verifier_authority")
    if owner['schema_version'] == 'reddog_signer_system_service_owner_config.v12':
        from .reddog_model_verifier_selection_inputs import validate_selection_authority
        validate_selection_authority(value, validate_bundle=lambda bundle:
            _validate_model_verifier_bundle(bundle, owner=owner, repo=repo))
        return
    _validate_model_verifier_bundle(value, owner=owner, repo=repo)


def _validate_model_verifier_bundle(value, *, owner, repo):
    if (type(value) is not dict or set(value) != {"issued_at", "expires_at", "inputs"}
            or any(type(value[key]) is not int for key in ("issued_at", "expires_at"))
            or not 0 < value["issued_at"] < value["expires_at"]
            or value["expires_at"] - value["issued_at"] > 3600
            or type(value["inputs"]) is not dict or set(value["inputs"]) != set(MODEL_VERIFIER_INPUTS)):
        raise RuntimeArtifactManifestError("model_verifier_authority_invalid")
    paths = set()
    for descriptor in value["inputs"].values():
        if (type(descriptor) is not dict or set(descriptor) != {"path", "raw_digest"}
                or type(descriptor["path"]) is not str or not Path(descriptor["path"]).is_absolute()
                or not is_sha256(descriptor["raw_digest"])):
            raise RuntimeArtifactManifestError("model_verifier_descriptor_invalid")
        path = validate_runtime_artifact_path(descriptor["path"], repo_root=repo,
                                              allowed_root=owner["runtime_root"])
        if path in paths:
            raise RuntimeArtifactManifestError("model_verifier_duplicate_path")
        paths.add(path)


def load_system_service_model_runtime_verifier(
    *, owner_config_path: Path | str, repo_root: Path,
    expected_owner_config_id: str, trusted_now_epoch: Callable[[], int],
    selection_receipt_id=None, selection_receipt_digest=None, _read_budget=None,
):
    """Snapshot protected inputs; caller must bind the owner to a current generation.

    This supplies a verifier, not execution authority or a verified model receipt.
    No caller-injected verifier or second read of a hash-checked input is accepted.
    """
    from . import reddog_signer_system_service_manifest_selection_loader as owner_loader
    from . import reddog_model_runtime_verifier_bootstrap as model
    repo = Path(repo_root).resolve()
    owner = owner_loader._load_owner_config(owner_config_path, repo=repo)
    if owner["schema_version"] not in {owner_loader.SCHEMA_VERSION_V8, owner_loader.SCHEMA_VERSION_V9, owner_loader.SCHEMA_VERSION_V10, owner_loader.SCHEMA_VERSION_V11, owner_loader.SCHEMA_VERSION_V12} or owner["config_id"] != expected_owner_config_id:
        raise RuntimeArtifactManifestError("model_verifier_owner_binding_invalid")
    authority = owner["model_verifier_authority"]
    selected_owner = owner
    if owner['schema_version'] == owner_loader.SCHEMA_VERSION_V12:
        from .reddog_model_verifier_selection_inputs import select_bundle, SelectionReadBudget
        if type(_read_budget) is not SelectionReadBudget:
            raise RuntimeArtifactManifestError('model_selection_read_budget_required')
        authority = select_bundle(authority, selection_receipt_id, selection_receipt_digest)
        selected_owner = dict(owner, model_verifier_authority=authority)
    elif selection_receipt_id is not None or selection_receipt_digest is not None or _read_budget is not None:
        raise RuntimeArtifactManifestError('model_selection_owner_version_invalid')
    payloads, expected_inputs_digest = None, None
    def current_clock():
        started = trusted_now_epoch()
        current = owner_loader._load_owner_config(owner_config_path, repo=repo)
        now = trusted_now_epoch()
        if (type(started) is not int or type(now) is not int or now < started
                or not authority["issued_at"] <= started <= now < authority["expires_at"]
                or current["config_id"] != expected_owner_config_id or current != owner):
            raise RuntimeArtifactManifestError("model_verifier_owner_not_current")
        if payloads is not None and digest(payloads) != expected_inputs_digest:
            raise RuntimeArtifactManifestError("model_verifier_snapshot_changed")
        return now
    current_clock()
    payloads = _read_model_verifier_snapshots(selected_owner, _read_budget=_read_budget)
    expected_inputs_digest = digest(payloads)
    resolver, reasons = model._key_resolver(payloads["trusted_keys"])
    backend, errors = model._signature_verifier("ed25519")
    benchmarks = model._records(payloads["benchmarks"], "benchmark_evidence_receipts")
    promotions = model._records(payloads["promotions"], "promotion_evidence_receipts")
    if reasons or errors or resolver is None or backend is None or benchmarks is None or promotions is None:
        raise RuntimeArtifactManifestError("model_verifier_snapshot_invalid")
    current_clock()
    return model._verifier(payloads, benchmarks, promotions, resolver, backend, current_clock)


def _read_model_verifier_snapshots(owner, *, _read_budget=None):
    payloads = {}
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeArtifactManifestError("model_verifier_json_duplicate")
            result[key] = value
        return result
    for name, descriptor in owner["model_verifier_authority"]["inputs"].items():
        raw, _ = secure_read_confined_bytes(Path(descriptor["path"]),
            allowed_root=Path(owner["runtime_root"]),
            max_bytes=_read_budget.begin() if _read_budget is not None else 1024 * 1024)
        if _read_budget is not None:
            _read_budget.finish(raw)
        if raw_digest(raw) != descriptor["raw_digest"]:
            raise RuntimeArtifactManifestError("model_verifier_input_digest_mismatch")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
        if type(payload) is not dict:
            raise RuntimeArtifactManifestError("model_verifier_snapshot_invalid")
        payloads[name] = payload
    return payloads
