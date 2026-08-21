"""Restart-safe orchestration for one authenticated production binding."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    runtime_operation_lock,
)

from .model_autoresearch_production_binding_claims import (
    load_or_create_claim,
    load_provider_bundle,
    persist_provider_bundle,
)
from .model_autoresearch_production_binding_execution import execute_production_binding
from .model_autoresearch_production_binding_freshness import (
    refresh_production_authority,
)
from .model_autoresearch_production_binding_outputs import (
    claim_output_transaction,
    cleanup_output_transaction,
    close_sealed_artifacts,
    transaction_for_claim,
)
from .model_autoresearch_production_binding_recovery import (
    publish_recovered_binding,
    recover_terminal_binding,
)
from .model_autoresearch_production_binding_transaction import (
    advance_publication,
    publication_status,
)


def run_production_binding_transaction(
    inputs: dict[str, Any],
    provider: Callable[[Any], Mapping[str, Any]],
) -> tuple[Any, Any]:
    identity = inputs["publication_identity"]
    with runtime_operation_lock(identity.nonce):
        return _run_locked(inputs, provider)


def _run_locked(
    inputs: dict[str, Any], provider: Callable[[Any], Mapping[str, Any]]
) -> tuple[Any, Any]:
    identity = inputs["publication_identity"]
    store = inputs["authority_use"].publication_store
    status = publication_status(store, identity)
    _reserve_before_callback(inputs)
    claim = load_or_create_claim(inputs)
    recovery_transaction = transaction_for_claim(inputs, claim)
    recovered = _recover_before_callback(inputs, recovery_transaction, status)
    if recovered is not None:
        return _publish_and_close(recovered, recovery_transaction)
    bundle = load_provider_bundle(inputs)
    if bundle is not None:
        refresh_production_authority(inputs)
    transaction = claim_output_transaction(inputs)
    inputs["output_transaction"] = transaction
    try:
        if bundle is None:
            supplied = provider(inputs["preview"])
            bundle = persist_provider_bundle(inputs, supplied)
        refresh_production_authority(inputs)
        result = execute_production_binding(inputs=inputs, bundle=bundle)
        close_sealed_artifacts(tuple(inputs.get("sealed_artifacts", ())))
        return result
    except BaseException:
        return _handle_failure(inputs, transaction)


def _handle_failure(inputs, transaction):
    error = __import__("sys").exc_info()[1]
    recovered = _recover_after_failure(inputs, transaction)
    if recovered is not None:
        close_sealed_artifacts(tuple(inputs.get("sealed_artifacts", ())))
        return _publish_and_close(recovered, transaction)
    cleanup_error = None
    try:
        cleanup_output_transaction(
            transaction, tuple(inputs.get("sealed_artifacts", ()))
        )
    except ValueError as value:
        cleanup_error = value
    finally:
        close_sealed_artifacts(tuple(inputs.get("sealed_artifacts", ())))
    assert error is not None
    if cleanup_error is not None and "stage_durability_failed" not in str(error):
        raise cleanup_error
    raise error.with_traceback(error.__traceback__)


def _publish_and_close(recovered, transaction):
    held = (recovered[2], recovered[3])
    try:
        return publish_recovered_binding(recovered, transaction)
    finally:
        close_sealed_artifacts(held)


def _recover_before_callback(inputs, transaction, status: str | None):
    if status == "APPLIED":
        return recover_terminal_binding(inputs, transaction, required=True)
    if status == "AUTHORIZED":
        recovered = recover_terminal_binding(inputs, transaction, required=False)
        if recovered is not None:
            _complete_recovered(inputs)
        return recovered
    return None


def _recover_after_failure(inputs, transaction):
    identity = inputs["publication_identity"]
    status = publication_status(inputs["authority_use"].publication_store, identity)
    if status not in {"AUTHORIZED", "APPLIED"}:
        return None
    recovered = recover_terminal_binding(
        inputs, transaction, required=status == "APPLIED"
    )
    if recovered is not None and status == "AUTHORIZED":
        _complete_recovered(inputs)
    return recovered


def _complete_recovered(inputs) -> None:
    identity = inputs["publication_identity"]
    store = inputs["authority_use"].publication_store
    try:
        advance_publication(
            store,
            nonce=identity.nonce,
            binding_digest=identity.binding_digest,
            target_status="APPLIED",
        )
    except ValueError:
        if publication_status(store, identity) != "APPLIED":
            raise


def _reserve_before_callback(inputs) -> None:
    identity = inputs["publication_identity"]
    try:
        advance_publication(
            inputs["authority_use"].publication_store,
            nonce=identity.nonce,
            binding_digest=identity.binding_digest,
            target_status="RESERVED",
        )
    except ValueError:
        raise ValueError("single_model_production_authority_binding_conflict") from None


__all__ = ["run_production_binding_transaction"]
