"""Restart-safe orchestration for one authenticated production binding."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from .model_autoresearch_production_binding_freshness import (
    refresh_production_authority,
)
from .model_autoresearch_production_binding_execution import execute_production_binding
from .model_autoresearch_production_binding_outputs import (
    claim_output_transaction,
    cleanup_output_transaction,
    output_transaction_for,
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
    store = inputs["authority_use"].publication_store
    transaction = output_transaction_for(
        inputs["selection_output"], inputs["runtime_output"], identity
    )
    status = publication_status(store, identity)
    recovered = _recover_before_callback(inputs, transaction, status)
    if recovered is not None:
        return publish_recovered_binding(recovered, transaction)
    transaction = claim_output_transaction(
        inputs["selection_output"], inputs["runtime_output"], identity
    )
    inputs["output_transaction"] = transaction
    try:
        bundle = provider(inputs["preview"])
        refresh_production_authority(inputs)
        return execute_production_binding(inputs=inputs, bundle=bundle)
    except BaseException:
        recovered = _recover_after_failure(inputs, transaction)
        if recovered is not None:
            return publish_recovered_binding(recovered, transaction)
        cleanup_output_transaction(transaction)
        raise


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


__all__ = ["run_production_binding_transaction"]
