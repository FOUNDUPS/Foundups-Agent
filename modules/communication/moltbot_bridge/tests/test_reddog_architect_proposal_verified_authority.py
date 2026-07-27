"""Security tests for architect-proposal promotion authority verification."""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from modules.communication.moltbot_bridge.src import (
    reddog_architect_fix_signed_wsp15_work_order_promotion as promotion,
)
from modules.communication.moltbot_bridge.src.reddog_authoritative_work_state_refresh_runtime import (
    AtomicJsonAuthoritativeWorkStateStore,
    InMemoryAuthoritativeWorkStateStore,
)
from modules.communication.moltbot_bridge.src.reddog_architect_proposal_verified_authority import (
    verify_architect_proposal_promotion_authority,
)
from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
    run_reddog_main_architect_fix_promotion_bootstrap,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_promotion_test_helpers import (
    StaticPrincipalKeyResolver,
    build_proposal_runtime_inputs,
    seal_authority_profile,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_fix_signed_wsp15_work_order_promotion import (
    NOW_EPOCH,
    _authority_profile,
    _determination,
    _promote,
    _work_state,
)
from modules.communication.moltbot_bridge.tests.test_reddog_main_architect_fix_promotion_bootstrap import (
    NOW,
    _repo,
    _runtime_files,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    ready_proposal_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_architect_proposal_verified_authority.py"
)


def _inputs():
    determination = _determination()
    profile = _authority_profile()
    attestation, runtime_config, resolver = build_proposal_runtime_inputs(
        determination,
        profile,
        now_epoch=NOW_EPOCH,
    )
    return determination, profile, attestation, runtime_config, resolver


def _verify(**overrides: Any):
    determination, profile, attestation, runtime_config, resolver = _inputs()
    values = {
        "attestation": attestation,
        "proposal_admission": determination["proposal_admission"],
        "determination": determination,
        "queue_candidate": determination["queue_candidate"],
        "authority_profile": profile,
        "signer_runtime_config": runtime_config,
        "principal_key_resolver": resolver,
        "now_epoch": NOW_EPOCH,
    }
    values.update(overrides)
    return verify_architect_proposal_promotion_authority(**values)


def test_untrusted_principal_cannot_self_mint_authority() -> None:
    with pytest.raises(ValueError):
        _verify(
            principal_key_resolver=StaticPrincipalKeyResolver(
                "ed25519-public:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
            )
        )


def test_tampered_attestation_and_runtime_authorization_fail() -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    changed_attestation = dict(attestation)
    signature = str(changed_attestation["signature"])
    midpoint = len(signature) // 2
    replacement = "A" if signature[midpoint] != "A" else "B"
    changed_attestation["signature"] = (
        signature[:midpoint] + replacement + signature[midpoint + 1 :]
    )
    with pytest.raises(ValueError):
        _verify(
            attestation=changed_attestation,
            proposal_admission=determination["proposal_admission"],
            determination=determination,
            queue_candidate=determination["queue_candidate"],
            authority_profile=profile,
            signer_runtime_config=runtime_config,
            principal_key_resolver=resolver,
        )
    authorization = runtime_config.proposal_policy_authorization.to_dict()
    authorization["security_context_digest"] = "sha256:" + ("0" * 64)
    changed_config = dataclasses.replace(
        runtime_config,
        proposal_policy_authorization=authorization,
    )
    with pytest.raises(ValueError):
        _verify(signer_runtime_config=changed_config)


def test_tautological_signer_context_is_rejected() -> None:
    _, _, _, runtime_config, _ = _inputs()
    authorization = runtime_config.proposal_policy_authorization.to_dict()
    authorization["signer_instance_id"] = "attacker-selected-instance"
    changed = dataclasses.replace(
        runtime_config,
        proposal_policy_authorization=authorization,
    )
    with pytest.raises(ValueError):
        _verify(signer_runtime_config=changed)


def test_current_determination_profile_and_revocation_are_rechecked() -> None:
    determination, _, attestation, runtime_config, resolver = _inputs()
    changed_determination = json.loads(json.dumps(determination))
    changed_determination["next_slice_name"] = "REDDOG_CHANGED_PHASE1"
    changed_determination["queue_candidate"]["slice_id"] = (
        "REDDOG_CHANGED_PHASE1"
    )
    changed_profile = _authority_profile(
        consensus_receipt_digest="sha256:" + ("0" * 64)
    )
    for overrides in (
        {"determination": changed_determination},
        {"authority_profile": changed_profile},
        {"revoked_key_epochs": frozenset({"epoch-1"})},
    ):
        with pytest.raises(ValueError):
            _verify(
                attestation=attestation,
                signer_runtime_config=runtime_config,
                principal_key_resolver=resolver,
                **overrides,
            )


_PROFILE_MUTATIONS = (
    ("principal_id", "github:attacker"),
    ("principal_provider", "attacker-provider"),
    (
        "principal_public_key",
        "ed25519-public:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    ),
    ("reddog_id", "reddog:attacker"),
    (
        "reddog_public_key",
        "ed25519-public:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",
    ),
    ("key_epoch", "epoch-attacker"),
    ("repo_full_name", "attacker/repository"),
    ("foundup_id", "attacker_foundup"),
    ("allowed_paths", ["modules/**"]),
    ("denied_paths", ["docs/**"]),
    ("requested_operation", "merge"),
    ("permission_snapshot_digest", "sha256:attacker-permission"),
    ("required_tests", ["true"]),
    ("required_policy_gates", ["attacker_gate"]),
)


@pytest.mark.parametrize(("field", "changed"), _PROFILE_MUTATIONS)
@pytest.mark.parametrize("receipt_mode", ("stale", "recomputed"))
def test_caller_profile_cannot_substitute_signed_authority_fields(
    field: str,
    changed: Any,
    receipt_mode: str,
) -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    changed_profile = {**profile, field: changed}
    if receipt_mode == "recomputed":
        changed_profile = seal_authority_profile(changed_profile)
    result, store = _promote(
        architect_determination=determination,
        authority_profile=changed_profile,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert result.accepted is False
    assert not store.load().get("wre_queue_items")


def test_caller_cannot_substitute_authority_profile_source_receipt() -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    result, store = _promote(
        architect_determination=determination,
        authority_profile={
            **profile,
            "authority_profile_source_receipt_id": "sha256:attacker-receipt",
        },
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert result.accepted is False
    assert not store.load().get("wre_queue_items")


def test_missing_runtime_trust_cannot_enter_promotion() -> None:
    result, store = _promote(
        proposal_authenticity_attestation={},
        signer_runtime_config=None,
        principal_key_resolver=None,
    )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        in result.rejection_reasons
    )
    assert not store.load().get("wre_queue_items")


def test_failed_profile_write_allows_verified_retry() -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    common = {
        "architect_determination": determination,
        "authority_profile": profile,
        "proposal_authenticity_attestation": attestation,
        "signer_runtime_config": runtime_config,
        "principal_key_resolver": resolver,
    }
    rejected, _ = _promote(
        **common,
        authority_profile_publication_publisher=lambda _request: (_ for _ in ()).throw(
            OSError("profile-write-failed")
        ),
    )
    assert rejected.accepted is False
    retried, _ = _promote(**common)
    assert retried.accepted is True


def test_failed_store_write_allows_verified_retry() -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    store = InMemoryAuthoritativeWorkStateStore(
        _work_state(), fail_commit=True
    )
    common = {
        "store": store,
        "architect_determination": determination,
        "authority_profile": profile,
        "proposal_authenticity_attestation": attestation,
        "signer_runtime_config": runtime_config,
        "principal_key_resolver": resolver,
    }
    rejected, _ = _promote(**common)
    store.fail_commit = False
    retried, _ = _promote(**common)

    assert rejected.accepted is False
    assert retried.accepted is True
    assert len(store.load()["wre_queue_items"]) == 1
    assert len(store.load()["architect_fix_promotions"]) == 1


def test_success_persists_replay_guard_in_authoritative_store() -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    first, store = _promote(
        architect_determination=determination,
        authority_profile=profile,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )
    second, _ = _promote(
        store=store,
        architect_determination=determination,
        authority_profile=profile,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert first.accepted is True
    assert second.accepted is False
    assert len(store.load()["wre_queue_items"]) == 1


def test_replay_guard_survives_authoritative_store_restart(
    tmp_path: Path,
) -> None:
    determination, profile, attestation, runtime_config, resolver = _inputs()
    store_path = tmp_path / "runtime" / "work-state.json"
    store_path.parent.mkdir()
    store_path.write_text(
        json.dumps(_work_state(), sort_keys=True),
        encoding="utf-8",
    )
    first, _ = _promote(
        store=AtomicJsonAuthoritativeWorkStateStore(store_path),
        architect_determination=determination,
        authority_profile=profile,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )
    restarted, restarted_store = _promote(
        store=AtomicJsonAuthoritativeWorkStateStore(store_path),
        architect_determination=determination,
        authority_profile=profile,
        proposal_authenticity_attestation=attestation,
        signer_runtime_config=runtime_config,
        principal_key_resolver=resolver,
    )

    assert first.accepted is True
    assert restarted.accepted is False
    assert len(restarted_store.load()["wre_queue_items"]) == 1


def test_production_bootstrap_without_authority_fails_before_side_effects(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    files = _runtime_files(tmp_path)
    with (
        patch(
            "modules.communication.moltbot_bridge.src."
            "reddog_main_architect_fix_promotion_bootstrap.read_git_head_sha",
            return_value="sha256:repo-head",
        ),
        patch(
            "modules.communication.moltbot_bridge.src."
            "reddog_main_architect_fix_promotion_bootstrap."
            "verify_reddog_holoindex_owner_binding",
            return_value=True,
        ),
        patch(
            "modules.communication.moltbot_bridge.src."
            "reddog_architect_proposal_admission_contract."
            "current_architect_proposal_admission_policy",
            return_value=ready_proposal_policy(),
        ),
    ):
        result = run_reddog_main_architect_fix_promotion_bootstrap(
            repo_root=repo,
            runtime_root=tmp_path / "runtime",
            work_state_path=files["work_state"],
            architect_determination_path=files["determination"],
            model_selection_receipt_path=files["model_selection"],
            memex_supply_receipt_path=files["memex_supply"],
            authority_profile_source_path=files["authority_profile_source"],
            authority_profile_output_path=files["authority_profile_output"],
            holoindex_receipt_path=files["holoindex_receipt"],
            worker_id="reddog-main-production-boundary-test",
            now_iso=NOW,
        )

    assert result.accepted is False
    assert (
        promotion.ArchitectFixPromotionReason.PROPOSAL_AUTHENTICITY_INVALID
        in result.rejection_reasons
    )
    assert not files["authority_profile_output"].exists()
    persisted = json.loads(files["work_state"].read_text(encoding="utf-8"))
    assert not persisted.get("wre_queue_items")


def test_promotion_binds_signed_runtime_context_across_outputs() -> None:
    result, store = _promote()
    assert result.accepted is True
    assert result.receipt is not None
    expected = result.receipt.proposal_signer_runtime_context_digest
    assert expected.startswith("sha256:")
    snapshot = store.load()
    assert snapshot["worker_claims"][0][
        "proposal_signer_runtime_context_digest"
    ] == expected
    assert snapshot["wre_queue_items"][0][
        "proposal_signer_runtime_context_digest"
    ] == expected
    assert snapshot["architect_fix_promotions"][0][
        "proposal_signer_runtime_context_digest"
    ] == expected
    assert result.authority_profile is not None
    assert result.authority_profile[
        "proposal_signer_runtime_context_digest"
    ] == expected


def test_authority_module_has_no_registry_or_execution_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "_AUTHORITY_REGISTRY" not in source
    assert "_USE_STATES" not in source
    tree = ast.parse(source)
    banned_roots = {
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "git",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".", 1)[0] not in banned_roots
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".", 1)[0] not in banned_roots
