"""Shared cryptographic fixtures for architect proposal promotion tests."""

from __future__ import annotations

import itertools
import json
import tempfile
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.reddog_architect_proposal_authenticity import (
    ArchitectProposalSignerPolicy,
    build_architect_proposal_authenticity_payload,
    canonical_architect_proposal_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_authority_profile_source_artifact_supply import (
    canonical_authority_profile_source_digest,
)
from modules.communication.moltbot_bridge.src.reddog_ed25519_signature_verifier_backend import (
    encode_ed25519_public_key,
    encode_ed25519_signature,
)
from modules.communication.moltbot_bridge.src.reddog_signer_key_provider_dryrun import (
    PROVIDER_MODE_WSP71_PERMISSIONED,
)
from modules.communication.moltbot_bridge.src.reddog_signer_socket_service_runtime_wiring import (
    architect_proposal_security_context_digest,
)
from modules.communication.moltbot_bridge.src.reddog_main_architect_fix_promotion_bootstrap import (
    run_reddog_main_architect_fix_promotion_bootstrap as _run_bootstrap,
)
from modules.communication.moltbot_bridge.src.reddog_operational_memex_supply_receipt import (
    rehydrate_operational_memex_supply_receipt,
)
from modules.communication.moltbot_bridge.tests.test_reddog_architect_proposal_signer_policy_runtime import (
    _policy_authorization,
    _runtime_proposal_config,
)
from modules.communication.moltbot_bridge.tests.architect_proposal_test_helpers import (
    ready_proposal_policy,
)


def _private_key(seed: int):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    return Ed25519PrivateKey.from_private_bytes(bytes([seed]) * 32)


def _public_key(private_key: Any) -> str:
    from cryptography.hazmat.primitives import serialization

    return encode_ed25519_public_key(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


PRINCIPAL_PRIVATE_KEY = _private_key(17)
REDDOG_PRIVATE_KEY = _private_key(29)
PRINCIPAL_PUBLIC_KEY = _public_key(PRINCIPAL_PRIVATE_KEY)
REDDOG_PUBLIC_KEY = _public_key(REDDOG_PRIVATE_KEY)
_NONCE_COUNTER = itertools.count(1)


class StaticPrincipalKeyResolver:
    def __init__(self, public_key: str = PRINCIPAL_PUBLIC_KEY) -> None:
        self._public_key = public_key

    def resolve(
        self,
        principal_id: str,
        principal_provider: str,
    ) -> str | None:
        if (
            principal_id == "github:mjtrout"
            and principal_provider == "github"
        ):
            return self._public_key
        return None


def seal_authority_profile(
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a test authority profile to its canonical source receipt."""

    sealed = dict(profile)
    sealed.pop("authority_profile_source_receipt_id", None)
    sealed["authority_profile_source_receipt_id"] = (
        canonical_authority_profile_source_digest(sealed)
    )
    return sealed


def build_proposal_runtime_inputs(
    determination: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    memex_supply_receipt: Mapping[str, Any],
    *,
    now_epoch: int,
    nonce: str | None = None,
) -> tuple[dict[str, Any], Any, StaticPrincipalKeyResolver]:
    nonce = nonce or (
        "proposal-promotion-nonce-"
        f"{next(_NONCE_COUNTER)}-{uuid.uuid4().hex}"
    )
    proposal = dict(determination["proposal_admission"])
    verified_memex = verified_memex_supply_for_test(
        determination,
        authority_profile,
        memex_supply_receipt,
        now_epoch=now_epoch,
    )
    payload = build_architect_proposal_authenticity_payload(
        proposal_admission=proposal,
        determination=determination,
        queue_candidate=dict(determination["queue_candidate"]),
        memex_supply_receipt=verified_memex,
        requester_principal_id=str(authority_profile["principal_id"]),
        reddog_id=str(authority_profile["reddog_id"]),
        signer_public_key=str(authority_profile["reddog_public_key"]),
        key_epoch=str(authority_profile["key_epoch"]),
        consensus_receipt_digest=str(
            authority_profile["consensus_receipt_digest"]
        ),
        authority_profile_source_receipt_id=str(
            authority_profile["authority_profile_source_receipt_id"]
        ),
        nonce=nonce,
        issued_at=int(now_epoch) - 5,
        expires_at=int(now_epoch) + 120,
    )
    return (
        _signed_attestation(payload),
        _production_runtime_config(
            payload,
            authority_profile=authority_profile,
            now_epoch=now_epoch,
        ),
        StaticPrincipalKeyResolver(),
    )


def verified_memex_supply_for_test(
    determination: Mapping[str, Any],
    authority_profile: Mapping[str, Any],
    memex_supply_receipt: Mapping[str, Any],
    *,
    now_epoch: int,
):
    proposal = dict(determination["proposal_admission"])
    return rehydrate_operational_memex_supply_receipt(
        memex_supply_receipt,
        expected_foundup_id=str(authority_profile["foundup_id"]),
        expected_principal_id=str(authority_profile["principal_id"]),
        expected_snapshot_receipt_id=str(determination["snapshot_receipt_id"]),
        expected_snapshot_content_digest=str(
            determination["snapshot_content_digest"]
        ),
        expected_holoindex_generation_id=str(
            proposal["holoindex_generation_id"]
        ),
        expected_source_revision=str(proposal["work_state_revision"]),
        now_iso=datetime.fromtimestamp(now_epoch, timezone.utc).isoformat(),
    )


def _signed_attestation(payload: Any) -> dict[str, Any]:
    return {
        **payload.to_dict(),
        "signature": encode_ed25519_signature(
            REDDOG_PRIVATE_KEY.sign(
                canonical_architect_proposal_signing_input(payload).encode(
                    "utf-8"
                )
            )
        ),
    }


def _production_runtime_config(
    payload: Any,
    *,
    authority_profile: Mapping[str, Any],
    now_epoch: int,
) -> Any:
    root = Path(tempfile.gettempdir()).resolve() / (
        "reddog-proposal-runtime-" + uuid.uuid4().hex
    )
    config = _runtime_proposal_config(
        repo=root / "repo",
        runtime=root / "runtime",
        signer_runtime=root / "signer",
        policy=ArchitectProposalSignerPolicy(expected_payload=payload),
        principal_private=PRINCIPAL_PRIVATE_KEY,
        reddog_private=REDDOG_PRIVATE_KEY,
    )
    config = replace(
        config,
        provider_mode=PROVIDER_MODE_WSP71_PERMISSIONED,
        allow_test_only_key_material=False,
        proposal_policy_authorization=None,
        proposal_security_context_digest=None,
    )
    security_context_digest = architect_proposal_security_context_digest(
        config
    )
    authorization = _policy_authorization(
        config.proposal_authority_policy,
        principal_private=PRINCIPAL_PRIVATE_KEY,
        public_key=REDDOG_PUBLIC_KEY,
        signer_runtime_root=Path(config.signer_runtime_root),
        security_context_digest=security_context_digest,
        profile=dict(authority_profile),
        issued_at=int(now_epoch) - 10,
        expires_at=int(now_epoch) + 120,
    )
    config = replace(
        config,
        proposal_policy_authorization=authorization,
        proposal_security_context_digest=security_context_digest,
    )
    return config


def run_bootstrap_with_test_authority(runner: Any, **kwargs: Any) -> Any:
    """Supply valid test authority without changing the production bootstrap."""

    if "proposal_authenticity_attestation" not in kwargs:
        try:
            determination = json.loads(
                Path(kwargs["architect_determination_path"]).read_text(
                    encoding="utf-8"
                )
            )
            authority_profile = json.loads(
                Path(kwargs["authority_profile_source_path"]).read_text(
                    encoding="utf-8"
                )
            )
            memex_supply = json.loads(
                Path(kwargs["memex_supply_receipt_path"]).read_text(
                    encoding="utf-8"
                )
            )
            now_epoch = int(
                datetime.fromisoformat(str(kwargs["now_iso"])).timestamp()
            )
            attestation, config, resolver = build_proposal_runtime_inputs(
                determination,
                authority_profile,
                memex_supply,
                now_epoch=now_epoch,
            )
            kwargs["proposal_authenticity_attestation"] = attestation
            kwargs["signer_runtime_config"] = config
            kwargs["principal_key_resolver"] = resolver
        except Exception:
            pass
    return runner(**kwargs)


def run_main_bootstrap_with_test_authority(**kwargs: Any) -> Any:
    """Invoke the production main bootstrap with valid test authority."""

    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_main_architect_fix_promotion_bootstrap."
        "resolve_query_replica_owner_route",
        return_value=object(),
    ):
        return run_bootstrap_with_test_authority(_run_bootstrap, **kwargs)


def invoke_promotion_with_test_authority(
    promote: Callable[..., Any],
    *,
    args: Mapping[str, Any],
    overrides: Mapping[str, Any],
    now_epoch: int,
) -> Any:
    """Invoke promotion with valid authority unless a test overrides it."""

    values = dict(args)
    default_determination = values["architect_determination"]
    default_authority_profile = values["authority_profile"]
    default_memex_supply = values["memex_supply_receipt"]
    values.update(overrides)
    if "proposal_authenticity_attestation" not in values:
        determination = values["architect_determination"]
        profile = values["authority_profile"]
        if not (
            isinstance(determination.get("proposal_admission"), Mapping)
            and isinstance(determination.get("queue_candidate"), Mapping)
        ):
            determination = default_determination
        required = (
            "principal_id",
            "principal_provider",
            "principal_public_key",
            "reddog_id",
            "reddog_public_key",
            "key_epoch",
            "consensus_receipt_digest",
            "authority_profile_source_receipt_id",
        )
        if not all(profile.get(field) for field in required):
            profile = default_authority_profile
        memex_supply = values["memex_supply_receipt"]
        try:
            verified_memex_supply_for_test(
                determination,
                profile,
                memex_supply,
                now_epoch=now_epoch,
            )
        except (TypeError, ValueError):
            memex_supply = default_memex_supply
        attestation, runtime_config, resolver = build_proposal_runtime_inputs(
            determination,
            profile,
            memex_supply,
            now_epoch=now_epoch,
        )
        values.update(
            proposal_authenticity_attestation=attestation,
            signer_runtime_config=runtime_config,
            principal_key_resolver=resolver,
        )
    with patch(
        "modules.communication.moltbot_bridge.src."
        "reddog_architect_proposal_admission_contract."
        "current_architect_proposal_admission_policy",
        return_value=ready_proposal_policy(),
    ):
        return promote(**values)


__all__ = [
    "PRINCIPAL_PRIVATE_KEY",
    "PRINCIPAL_PUBLIC_KEY",
    "REDDOG_PRIVATE_KEY",
    "REDDOG_PUBLIC_KEY",
    "StaticPrincipalKeyResolver",
    "build_proposal_runtime_inputs",
    "invoke_promotion_with_test_authority",
    "run_main_bootstrap_with_test_authority",
    "run_bootstrap_with_test_authority",
    "seal_authority_profile",
    "verified_memex_supply_for_test",
]
