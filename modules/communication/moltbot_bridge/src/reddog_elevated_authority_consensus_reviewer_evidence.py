"""Independent reviewer evidence verification for elevated consensus."""

from __future__ import annotations

from typing import Any, Mapping

from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_contract import (
    APPROVE,
    DECISION_SCHEMA_VERSION,
    ElevatedAuthorityConsensusReceipt,
    canonical_consensus_context_digest,
    canonical_reviewer_decision_signing_input,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    ElevatedConsensusPolicy,
    ReviewerKeyAuthority,
    ReviewerKeyAuthorityResolver,
    ReviewerRuntimeEvidence,
    ReviewerRuntimeEvidenceResolver,
)
from modules.communication.moltbot_bridge.src.reddog_work_order_signature_verifier import (
    SignatureVerifier,
)


def consensus_decisions_verify(
    receipt: ElevatedAuthorityConsensusReceipt,
    request: Any,
    signature_verifier: SignatureVerifier,
    key_resolver: ReviewerKeyAuthorityResolver,
    evidence_resolver: ReviewerRuntimeEvidenceResolver,
    policy: ElevatedConsensusPolicy,
    now: int,
    revoked_key_epochs: frozenset[str],
) -> bool:
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    seen_models: set[str] = set()
    seen_runtime_bindings: set[str] = set()
    roles: set[str] = set()
    context_digest = canonical_consensus_context_digest(receipt.context)
    forbidden_ids = _forbidden_reviewer_ids(request)
    forbidden_keys = {request.principal_public_key, request.reddog_public_key}
    forbidden_runtime = {str(request.model_runtime_binding_digest or "")} - {""}
    membership = set(policy.reviewer_membership)
    for decision in receipt.decisions:
        key, evidence = _verified_decision_evidence(
            decision,
            context_digest,
            signature_verifier,
            key_resolver,
            evidence_resolver,
            now,
            revoked_key_epochs,
        )
        if key is None or evidence is None or any(
            (
                decision.reviewer_principal_id in seen_ids | forbidden_ids,
                key.public_key in seen_keys | forbidden_keys,
                evidence.reviewer_model_id in seen_models,
                evidence.model_runtime_binding_digest
                in seen_runtime_bindings | forbidden_runtime,
                _reviewer_membership(decision) not in membership,
            )
        ):
            return False
        seen_ids.add(decision.reviewer_principal_id)
        seen_keys.add(key.public_key)
        seen_models.add(evidence.reviewer_model_id)
        seen_runtime_bindings.add(evidence.model_runtime_binding_digest)
        roles.add(decision.reviewer_role)
    return set(receipt.context.required_roles).issubset(roles)


def _reviewer_membership(decision: Any) -> tuple[str, str, str]:
    return (
        decision.reviewer_principal_id,
        decision.reviewer_principal_provider,
        decision.reviewer_role,
    )


def _verified_decision_evidence(
    decision: Any,
    context_digest: str,
    signature_verifier: SignatureVerifier,
    key_resolver: ReviewerKeyAuthorityResolver,
    evidence_resolver: ReviewerRuntimeEvidenceResolver,
    now: int,
    revoked_key_epochs: frozenset[str],
) -> tuple[ReviewerKeyAuthority | None, ReviewerRuntimeEvidence | None]:
    if any(
        (
            decision.schema_version != DECISION_SCHEMA_VERSION,
            decision.decision != APPROVE,
            decision.consensus_context_digest != context_digest,
            decision.reviewer_key_epoch in revoked_key_epochs,
        )
    ):
        return None, None
    key = key_resolver.resolve(
        decision.reviewer_principal_id, decision.reviewer_principal_provider
    )
    evidence = evidence_resolver.resolve(
        decision.reviewer_principal_id,
        decision.model_selection_receipt_id,
        decision.model_runtime_binding_receipt_id,
    )
    if type(key) is not ReviewerKeyAuthority or type(evidence) is not ReviewerRuntimeEvidence:
        return None, None
    if key.public_key != decision.reviewer_public_key or any(
        (
            key.key_epoch != decision.reviewer_key_epoch,
            key.expires_at <= now,
            not _runtime_evidence_matches(decision, evidence, now),
        )
    ):
        return None, None
    try:
        verified = signature_verifier.verify(
            key.public_key,
            canonical_reviewer_decision_signing_input(decision),
            decision.signature,
        ) is True
    except Exception:
        verified = False
    return (key, evidence) if verified else (None, None)


def _runtime_evidence_matches(decision: Any, evidence: Any, now: int) -> bool:
    return all(
        (
            evidence.expires_at > now,
            evidence.reviewer_model_id == decision.reviewer_model_id,
            evidence.model_selection_receipt_id == decision.model_selection_receipt_id,
            evidence.model_selection_digest == decision.model_selection_digest,
            evidence.model_runtime_binding_receipt_id
            == decision.model_runtime_binding_receipt_id,
            evidence.model_runtime_binding_digest
            == decision.model_runtime_binding_digest,
        )
    )


def _forbidden_reviewer_ids(request: Any) -> set[str]:
    queue = getattr(request, "queue_consumer_receipt", {})
    worker_id = str(queue.get("worker_id") or "") if isinstance(queue, Mapping) else ""
    return {
        str(getattr(request, "principal_id", "") or ""),
        str(getattr(request, "reddog_id", "") or ""),
        worker_id,
    } - {""}


__all__ = ["consensus_decisions_verify"]
