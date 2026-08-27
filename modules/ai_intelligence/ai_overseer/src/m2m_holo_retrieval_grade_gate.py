"""Independent A-grade evidence gate for HoloIndex retrieval candidates.

The public regression Skillz is necessary integrity evidence, but its checked-in
queries are not independent promotion evidence. This module composes that
public result with a separately signed, sealed-corpus evaluation. It emits an
eligibility receipt only; it never changes a ranker, index, route, or artifact.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol, Sequence

from holo_index.query_receipt import digest_json
from holo_index.retrieval_autoresearch import (
    RUN_SCHEMA,
    VERIFICATION_SCHEMA,
    retrieval_candidate_id,
)


GRADE_SCHEMA = "holoindex_retrieval_a_grade_gate.v1"
INDEPENDENT_SCHEMA = "holoindex_independent_retrieval_evaluation.v1"
GRADE_ACCEPT = "HOLO_RETRIEVAL_A_GRADE_EVIDENCE_ACCEPT"
GRADE_REJECT = "HOLO_RETRIEVAL_A_GRADE_EVIDENCE_REJECT"
PUBLIC_REGRESSION_THRESHOLD = 0.95
A_GRADE_MIN_CASE_COUNT = 30
A_GRADE_MIN_METRIC = 0.95
A_GRADE_MAX_P95_LATENCY_MS = 5000.0


class IndependentRetrievalSignatureVerifier(Protocol):
    """Verify a separately administered evaluation signature."""

    def verify(
        self,
        receipt: Mapping[str, Any],
        signature_envelope: Mapping[str, Any],
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class HoloRetrievalGradePolicy:
    min_case_count: int = A_GRADE_MIN_CASE_COUNT
    min_recall_at_k: float = A_GRADE_MIN_METRIC
    min_mrr: float = A_GRADE_MIN_METRIC
    min_ndcg_at_k: float = A_GRADE_MIN_METRIC
    max_p95_latency_ms: float = A_GRADE_MAX_P95_LATENCY_MS

    def validate(self) -> None:
        metrics = (self.min_recall_at_k, self.min_mrr, self.min_ndcg_at_k)
        if type(self.min_case_count) is not int or (
            self.min_case_count < A_GRADE_MIN_CASE_COUNT
        ) or any(
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not A_GRADE_MIN_METRIC <= value <= 1.0
            for value in metrics
        ):
            raise ValueError("invalid_holo_retrieval_grade_policy")
        if (
            type(self.max_p95_latency_ms) not in (int, float)
            or not math.isfinite(self.max_p95_latency_ms)
            or not 0 < self.max_p95_latency_ms <= A_GRADE_MAX_P95_LATENCY_MS
        ):
            raise ValueError("invalid_holo_retrieval_grade_policy")


@dataclass(frozen=True, slots=True)
class HoloRetrievalGradeGateReceipt:
    receipt_id: str
    decision: str
    accepted: bool
    candidate_id: str
    generation_id: str
    public_run_receipt_id: str
    public_verification_receipt_id: str
    independent_evaluation_receipt_id: str
    independent_signature_envelope_digest: str
    policy: HoloRetrievalGradePolicy
    rejection_reasons: tuple[str, ...]
    a_grade_evidence_accepted: bool
    signature_verifier_invoked: bool
    promotion_authorized: bool = False
    promotion_to_holoindex_performed: bool = False
    no_gate_holoindex_reindex_performed: bool = True
    no_gate_ranker_change_performed: bool = True
    no_gate_repository_artifact_written: bool = True
    external_verifier_effects_attested: bool = False
    external_promotion_authority_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema_version"] = GRADE_SCHEMA
        value["rejection_reasons"] = list(self.rejection_reasons)
        return value


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _receipt_integrity_ok(receipt: Mapping[str, Any]) -> bool:
    payload = {key: value for key, value in receipt.items() if key != "receipt_id"}
    return bool(receipt.get("receipt_id")) and receipt.get("receipt_id") == digest_json(payload)


def _digest_ok(value: Any) -> bool:
    text = str(value or "")
    return (
        len(text) == 71
        and text.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in text[7:])
    )


def _public_reasons(public_result: Mapping[str, Any]) -> list[str]:
    run = _mapping(public_result.get("benchmark_run"))
    verification = _mapping(public_result.get("verification"))
    reasons: list[str] = []
    if public_result.get("success") is not True:
        reasons.append("public_regression_not_accepted")
    if verification.get("accepted") is not True:
        reasons.append("public_verification_not_accepted")
    if not _receipt_integrity_ok(run):
        reasons.append("public_run_integrity_invalid")
    if not _receipt_integrity_ok(verification):
        reasons.append("public_verification_integrity_invalid")
    if public_result.get("public_regression_corpus_not_independent_heldout") is not True:
        reasons.append("public_corpus_truth_boundary_missing")
    if run.get("no_holoindex_reindex_performed") is not True:
        reasons.append("public_reindex_boundary_unproven")
    if run.get("no_generation_promotion_performed") is not True:
        reasons.append("public_promotion_boundary_unproven")
    reasons.extend(_public_binding_reasons(run, verification))
    reasons.extend(_public_quality_reasons(public_result, run))
    return reasons


def _public_binding_reasons(
    run: Mapping[str, Any], verification: Mapping[str, Any],
) -> list[str]:
    binding = _mapping(run.get("candidate_binding"))
    fields = (
        "generation_id", "freshness_receipt_digest", "repo_root_digest",
        "config_digest", "ranker_digest",
    )
    reasons: list[str] = []
    if run.get("schema_version") != RUN_SCHEMA or run.get("split") != "heldout":
        reasons.append("public_run_contract_invalid")
    if any(not _digest_ok(binding.get(name)) for name in fields):
        reasons.append("public_candidate_binding_invalid")
    try:
        expected_id = retrieval_candidate_id(**{
            name: str(binding.get(name) or "")
            for name in (
                "generation_id", "freshness_receipt_digest", "repo_head_sha",
                "repo_root_digest", "config_digest", "ranker_digest",
            )
        })
    except TypeError:
        expected_id = ""
    if binding.get("candidate_id") != expected_id:
        reasons.append("public_candidate_id_invalid")
    if verification.get("schema_version") != VERIFICATION_SCHEMA:
        reasons.append("public_verification_contract_invalid")
    if verification.get("benchmark_run_receipt_id") != run.get("receipt_id"):
        reasons.append("public_verification_binding_invalid")
    if verification.get("candidate_binding_digest") != digest_json(dict(binding)):
        reasons.append("public_verification_candidate_invalid")
    return reasons


def _public_quality_reasons(
    public_result: Mapping[str, Any], run: Mapping[str, Any],
) -> list[str]:
    metrics = _mapping(run.get("metrics"))
    names = ("recall_at_k", "mrr", "ndcg_at_k")
    valid = all(
        type(metrics.get(name)) in (int, float)
        and math.isfinite(metrics[name])
        and 0.0 <= metrics[name] <= 1.0
        for name in names
    )
    if public_result.get("quality_threshold") != PUBLIC_REGRESSION_THRESHOLD:
        return ["public_quality_threshold_invalid"]
    passed = valid and all(
        metrics[name] >= PUBLIC_REGRESSION_THRESHOLD for name in names
    )
    reasons = [] if passed else ["public_quality_policy_not_met"]
    if public_result.get("quality_gate_passed") is not passed:
        reasons.append("public_quality_status_mismatch")
    return reasons


def _metric_reasons(
    independent: Mapping[str, Any], policy: HoloRetrievalGradePolicy,
) -> list[str]:
    metrics = _mapping(independent.get("metrics"))
    thresholds = (
        ("recall_at_k", policy.min_recall_at_k),
        ("mrr", policy.min_mrr),
        ("ndcg_at_k", policy.min_ndcg_at_k),
    )
    reasons: list[str] = []
    for name, minimum in thresholds:
        value = metrics.get(name)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            reasons.append(f"independent_{name}_invalid")
        elif value < minimum:
            reasons.append(f"independent_{name}_below_policy")
    latency = metrics.get("p95_latency_ms")
    if type(latency) not in (int, float) or not math.isfinite(latency) or latency <= 0:
        reasons.append("independent_latency_invalid")
    elif latency > policy.max_p95_latency_ms:
        reasons.append("independent_latency_above_policy")
    return reasons


def _independent_reasons(
    independent: Mapping[str, Any], policy: HoloRetrievalGradePolicy,
) -> list[str]:
    reasons: list[str] = []
    if independent.get("schema_version") != INDEPENDENT_SCHEMA:
        reasons.append("independent_schema_invalid")
    if not _receipt_integrity_ok(independent):
        reasons.append("independent_receipt_integrity_invalid")
    if independent.get("accepted") is not True:
        reasons.append("independent_evaluation_not_accepted")
    if independent.get("corpus_disjoint_from_public_regression") is not True:
        reasons.append("independent_corpus_separation_unproven")
    if not str(independent.get("sealed_corpus_id") or "").strip():
        reasons.append("sealed_corpus_id_missing")
    if type(independent.get("sealed_corpus_case_count")) is not int or (
        independent.get("sealed_corpus_case_count", 0) < policy.min_case_count
    ):
        reasons.append("independent_corpus_too_small")
    if independent.get("no_holoindex_reindex_performed") is not True:
        reasons.append("independent_reindex_boundary_unproven")
    if independent.get("no_generation_promotion_performed") is not True:
        reasons.append("independent_promotion_boundary_unproven")
    reasons.extend(_metric_reasons(independent, policy))
    return reasons


def _binding_reasons(
    public_result: Mapping[str, Any], independent: Mapping[str, Any],
) -> list[str]:
    run = _mapping(public_result.get("benchmark_run"))
    binding = _mapping(run.get("candidate_binding"))
    reasons: list[str] = []
    fields = (
        "candidate_id", "generation_id", "freshness_receipt_digest",
        "repo_head_sha", "repo_root_digest", "config_digest", "ranker_digest",
    )
    if any(independent.get(name) != binding.get(name) for name in fields):
        reasons.append("independent_candidate_binding_mismatch")
    proposer = str(independent.get("proposer_principal_id") or "")
    evaluator = str(independent.get("evaluator_principal_id") or "")
    if not proposer or not evaluator or proposer == evaluator:
        reasons.append("independent_evaluator_separation_invalid")
    if not _digest_ok(independent.get("sealed_corpus_digest")):
        reasons.append("sealed_corpus_digest_invalid")
    return reasons


def _signature_binding_reasons(
    independent: Mapping[str, Any], envelope: Mapping[str, Any],
) -> list[str]:
    if envelope.get("signed_receipt_id") != independent.get("receipt_id"):
        return ["independent_signature_binding_invalid"]
    if envelope.get("signer_principal_id") != independent.get("evaluator_principal_id"):
        return ["independent_signature_principal_mismatch"]
    return []


def _signature_accepted(
    independent: Mapping[str, Any], envelope: Mapping[str, Any],
    verifier: IndependentRetrievalSignatureVerifier,
) -> bool:
    try:
        return verifier.verify(independent, envelope) is True
    except Exception:
        return False


def _gate_payload(
    *, public: Mapping[str, Any], independent: Mapping[str, Any],
    envelope: Mapping[str, Any], policy: HoloRetrievalGradePolicy,
    reasons: Sequence[str], verifier_invoked: bool,
) -> dict[str, Any]:
    run = _mapping(public.get("benchmark_run"))
    verification = _mapping(public.get("verification"))
    binding = _mapping(run.get("candidate_binding"))
    accepted = not reasons
    return {
        "schema_version": GRADE_SCHEMA,
        "decision": GRADE_ACCEPT if accepted else GRADE_REJECT,
        "accepted": accepted,
        "candidate_id": str(binding.get("candidate_id") or ""),
        "generation_id": str(binding.get("generation_id") or ""),
        "public_run_receipt_id": str(run.get("receipt_id") or ""),
        "public_verification_receipt_id": str(verification.get("receipt_id") or ""),
        "independent_evaluation_receipt_id": str(independent.get("receipt_id") or ""),
        "independent_signature_envelope_digest": digest_json(dict(envelope)),
        "policy": asdict(policy),
        "rejection_reasons": list(reasons),
        "a_grade_evidence_accepted": accepted,
        "signature_verifier_invoked": verifier_invoked,
        "promotion_authorized": False,
        "promotion_to_holoindex_performed": False,
        "no_gate_holoindex_reindex_performed": True,
        "no_gate_ranker_change_performed": True,
        "no_gate_repository_artifact_written": True,
        "external_verifier_effects_attested": False,
        "external_promotion_authority_required": True,
    }


def _evaluate_holo_retrieval_a_grade(
    *, public_result: Mapping[str, Any],
    independent_evaluation: Mapping[str, Any],
    signature_envelope: Mapping[str, Any],
    signature_verifier: IndependentRetrievalSignatureVerifier,
    policy: HoloRetrievalGradePolicy = HoloRetrievalGradePolicy(),
) -> HoloRetrievalGradeGateReceipt:
    """Admit independently signed A-grade evidence without promoting it."""

    policy.validate()
    reasons = _public_reasons(public_result)
    reasons.extend(_independent_reasons(independent_evaluation, policy))
    reasons.extend(_binding_reasons(public_result, independent_evaluation))
    reasons.extend(_signature_binding_reasons(
        independent_evaluation, signature_envelope,
    ))
    verifier_invoked = not reasons
    if verifier_invoked and not _signature_accepted(
        independent_evaluation, signature_envelope, signature_verifier,
    ):
        reasons.append("independent_signature_invalid")
    reasons = list(dict.fromkeys(reasons))
    payload = _gate_payload(
        public=public_result, independent=independent_evaluation,
        envelope=signature_envelope, policy=policy, reasons=reasons,
        verifier_invoked=verifier_invoked,
    )
    receipt_id = digest_json(payload)
    value = dict(payload)
    value.pop("schema_version")
    value["policy"] = policy
    value["rejection_reasons"] = tuple(reasons)
    return HoloRetrievalGradeGateReceipt(receipt_id=receipt_id, **value)


__all__ = [
    "A_GRADE_MAX_P95_LATENCY_MS", "A_GRADE_MIN_CASE_COUNT",
    "A_GRADE_MIN_METRIC",
    "GRADE_ACCEPT", "GRADE_REJECT", "GRADE_SCHEMA", "INDEPENDENT_SCHEMA",
    "PUBLIC_REGRESSION_THRESHOLD",
    "HoloRetrievalGradeGateReceipt", "HoloRetrievalGradePolicy",
    "IndependentRetrievalSignatureVerifier",
]
