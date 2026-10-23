"""Test-only consensus admission for inherited downstream queue matrices."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import json
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

from modules.communication.moltbot_bridge.src import (
    reddog_resident_queue_stage_handler_registry as registry_module,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_capability import (
    _mint_elevated_authority_consensus_capability,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    canonical_authority_request_digest,
    canonical_elevated_signing_request_digest,
)
from modules.communication.moltbot_bridge.src.reddog_signer_delegated_authority_runtime import (
    HIGH_AUTHORITY_TIER,
    PrincipalAuthorityRecord,
    build_delegated_authority_signing_requests,
)
from modules.communication.moltbot_bridge.src.reddog_signer_optional_authority_bindings import (
    runtime_binding_request_valid,
)
from modules.communication.moltbot_bridge.tests.reddog_elevated_consensus_test_support import (
    sign_with_test_consensus,
)


class PermitAwareDownstreamTestSigner:
    """Consume the real opaque permit before using an inherited fake signer."""

    def __init__(self, signer: Any, *, now: int) -> None:
        self._signer = signer
        self._now = now

    def sign(self, request: Any) -> Any:
        return self._signer.sign(request)

    def sign_with_elevated_consensus(self, request: Any, permit: Any) -> Any:
        return sign_with_test_consensus(
            self._signer, request, permit, now=self._now
        )


def downstream_test_consensus_capability(
    request: Any, *, now: int, principal: Any = None
) -> Any:
    """Mint only the process-local permit input used by non-consensus tests."""

    principal = principal or PrincipalAuthorityRecord(
        principal_id=request.principal_id, principal_provider=request.principal_provider,
        principal_public_key=request.principal_public_key,
        repo_scope=(request.repo_full_name,), foundup_scope=(request.foundup_id,),
        verified_subject_digest="sha256:" + ("f" * 64),
    )
    if runtime_binding_request_valid(request) is not True:
        return None
    plan = build_delegated_authority_signing_requests(
        request,
        principal,
        authority_tier=HIGH_AUTHORITY_TIER,
        has_runtime_binding=True,
    )
    return _mint_elevated_authority_consensus_capability(
        authority_request_digest=canonical_authority_request_digest(request),
        consensus_receipt_digest=str(request.consensus_receipt_digest or ""),
        expires_at=now + 300,
        authorized_signing_request_digests=frozenset(
            canonical_elevated_signing_request_digest(item) for item in plan[2:]
        ),
        consensus_proof={"schema_version": "test_only_downstream_consensus.v1"},
    )


def with_downstream_test_consensus(function: Any) -> Any:
    """Decorate inherited queue tests without changing production composition."""

    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        with downstream_test_consensus(**_runtime_paths(kwargs)):
            return function(*args, **kwargs)

    return wrapped


@contextmanager
def downstream_test_consensus(
    *, work_state_path: Any = None, authority_profile_path: Any = None
) -> Iterator[None]:
    """Bind fixture evidence and one opaque permit within one test context."""

    _bind_runtime_files(
        {
            "work_state_path": work_state_path,
            "authority_profile_path": authority_profile_path,
        }
    )
    original = registry_module.build_reddog_resident_queue_authority_runtime_stage_handler

    def build_handler(**handler_kwargs: Any) -> Any:
        now = int(handler_kwargs["now"])
        handler_kwargs["signer"] = PermitAwareDownstreamTestSigner(
            handler_kwargs["signer"], now=now
        )
        resolver = handler_kwargs["principal_resolver"]
        handler_kwargs["elevated_consensus_capability_supplier"] = lambda request: (
            downstream_test_consensus_capability(
                request, now=now,
                principal=resolver.resolve(
                    request.principal_id, request.principal_provider
                ),
            )
        )
        return original(**handler_kwargs)

    with patch.object(
        registry_module,
        "build_reddog_resident_queue_authority_runtime_stage_handler",
        side_effect=build_handler,
    ):
        yield


def _runtime_paths(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_state_path": kwargs.get("work_state_path"),
        "authority_profile_path": kwargs.get("authority_profile_path"),
    }


def _bind_runtime_files(kwargs: dict[str, Any]) -> None:
    state_path = kwargs.get("work_state_path")
    profile_path = kwargs.get("authority_profile_path")
    if (
        not state_path
        or not profile_path
        or not Path(state_path).is_file()
        or not Path(profile_path).is_file()
    ):
        return
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
    fields = {
        "model_selection_digest": "sha256:" + ("b" * 64),
        "model_runtime_binding_receipt_id": "reddog_model_runtime_binding:author",
        "model_runtime_binding_digest": "sha256:" + ("c" * 64),
        "model_runtime_binding_verification_receipt_id": "model_runtime_binding_verification:author",
        "model_runtime_binding_verification_digest": "sha256:" + ("e" * 64),
    }
    if profile.get("model_runtime_binding_verification_receipt_id"):
        return
    profile.update(fields)
    queue = state["wre_queue_items"][0]
    claim = state["worker_claims"][0]
    queue.update(fields)
    claim.update({key: value for key, value in fields.items() if key.endswith("receipt_id")})
    queue["evidence_refs"].extend((
        "model_runtime_binding:" + fields["model_runtime_binding_receipt_id"],
        "model_runtime_binding_verification:" + fields[
            "model_runtime_binding_verification_receipt_id"
        ],
    ))
    Path(state_path).write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
    Path(profile_path).write_text(json.dumps(profile, sort_keys=True), encoding="utf-8")


__all__ = [
    "PermitAwareDownstreamTestSigner",
    "downstream_test_consensus",
    "downstream_test_consensus_capability",
    "with_downstream_test_consensus",
]
