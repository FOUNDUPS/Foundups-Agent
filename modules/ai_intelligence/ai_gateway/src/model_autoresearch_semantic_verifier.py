"""Deterministic output-evidence verifier for model AutoResearch benchmarks.

The verifier consumes content-bearing output evidence records produced by the
configured gateway runner. It verifies that evidence records match the
candidate/task/output digest and then applies explicit task metadata
requirements. It does not call a model, infer unstated semantics, promote
models, write PatternMemory, mutate HoloIndex, execute commands, or bind RedDog
runtime defaults.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .model_autoresearch_configured_gateway_runner import CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION
from .model_autoresearch_output_evidence_bundle import (
    ModelAutoResearchOutputEvidenceRecord,
    rehydrate_model_autoresearch_output_evidence_record,
)
from .model_combination_benchmark_harness import (
    ModelBenchmarkCandidate,
    ModelBenchmarkTask,
    ModelBenchmarkTaskOutput,
    ModelBenchmarkVerifierResult,
)
from .model_intelligence_outcomes import VerifierDecision


MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER_SCHEMA = (
    "model_autoresearch_output_evidence_semantic_verifier.v1"
)
REQUIRED_TERMS_METADATA_KEY = "expected_answer_contains"
FORBIDDEN_TERMS_METADATA_KEY = "expected_answer_excludes"

OutputEvidenceRecords = (
    Sequence[ModelAutoResearchOutputEvidenceRecord | Mapping[str, object]]
    | Callable[[], Sequence[ModelAutoResearchOutputEvidenceRecord | Mapping[str, object]]]
)


@dataclass(frozen=True)
class ModelAutoResearchSemanticVerifierPolicy:
    """Task-metadata keys that define deterministic semantic expectations."""

    required_terms_metadata_key: str = REQUIRED_TERMS_METADATA_KEY
    forbidden_terms_metadata_key: str = FORBIDDEN_TERMS_METADATA_KEY
    schema_version: str = MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER_SCHEMA

    def normalized(self) -> "ModelAutoResearchSemanticVerifierPolicy":
        return ModelAutoResearchSemanticVerifierPolicy(
            required_terms_metadata_key=_clean_token(self.required_terms_metadata_key),
            forbidden_terms_metadata_key=_clean_token(self.forbidden_terms_metadata_key),
        )

    def to_dict(self) -> dict[str, str]:
        policy = self.normalized()
        return {
            "schema_version": policy.schema_version,
            "required_terms_metadata_key": policy.required_terms_metadata_key,
            "forbidden_terms_metadata_key": policy.forbidden_terms_metadata_key,
        }


def build_model_autoresearch_output_evidence_semantic_verifier(
    *,
    evidence_records: OutputEvidenceRecords,
    policy: ModelAutoResearchSemanticVerifierPolicy | None = None,
):
    """Return a benchmark verifier over configured-gateway output evidence."""

    normalized_policy = (policy or ModelAutoResearchSemanticVerifierPolicy()).normalized()
    policy_digest = _digest_prefixed("model_autoresearch_semantic_verifier_policy", normalized_policy.to_dict())

    def _verifier(
        task: ModelBenchmarkTask,
        candidate: ModelBenchmarkCandidate,
        output: ModelBenchmarkTaskOutput,
    ) -> ModelBenchmarkVerifierResult:
        try:
            normalized_task = task.normalized()
            normalized_output = output.normalized()
            records = _records(evidence_records)
            relevant_records = _records_for_sample(
                records=records,
                task=normalized_task,
                candidate=candidate,
            )
            required_terms = _terms(
                normalized_task.metadata.get(normalized_policy.required_terms_metadata_key, "")
            )
            forbidden_terms = _terms(
                normalized_task.metadata.get(normalized_policy.forbidden_terms_metadata_key, "")
            )
            reasons: list[str] = []
            if not required_terms:
                reasons.append("semantic_verifier_required_terms_missing")
            if len(relevant_records) != len(candidate.role_assignments):
                reasons.append("semantic_verifier_evidence_record_count_mismatch")
            role_reasons = _role_binding_rejections(candidate, relevant_records)
            reasons.extend(role_reasons)
            if relevant_records and not role_reasons:
                reasons.extend(
                    _runner_digest_rejections(
                        task=normalized_task,
                        candidate=candidate,
                        output=normalized_output,
                        records=relevant_records,
                    )
                )
            text = "\n".join(record.response_text for record in relevant_records).lower()
            for term in required_terms:
                if term.lower() not in text:
                    reasons.append(f"semantic_verifier_required_term_missing:{_clean_reason(term)}")
            for term in forbidden_terms:
                if term.lower() in text:
                    reasons.append(f"semantic_verifier_forbidden_term_present:{_clean_reason(term)}")
            reasons = _dedupe(reasons)
            accepted = not reasons
            return ModelBenchmarkVerifierResult(
                decision=VerifierDecision.ACCEPT if accepted else VerifierDecision.REJECT,
                verifier_receipt_id=_verifier_receipt_id(
                    task=normalized_task,
                    candidate=candidate,
                    output=normalized_output,
                    records=relevant_records,
                    required_terms=required_terms,
                    forbidden_terms=forbidden_terms,
                    policy_digest=policy_digest,
                    accepted=accepted,
                    rejection_reasons=reasons,
                ),
                evidence_correct=accepted,
                rejection_reasons=tuple(reasons),
            )
        except Exception as exc:
            reason = f"semantic_verifier_error:{type(exc).__name__}"
            return ModelBenchmarkVerifierResult(
                decision=VerifierDecision.ERROR,
                verifier_receipt_id=_digest_prefixed(
                    "model_autoresearch_semantic_verifier_error",
                    {
                        "task_id": getattr(task, "task_id", ""),
                        "candidate_id": getattr(candidate, "candidate_id", ""),
                        "output_digest": getattr(output, "output_digest", ""),
                        "reason": reason,
                        "policy_digest": policy_digest,
                    },
                ),
                evidence_correct=False,
                rejection_reasons=(reason,),
            )

    return _verifier


def _records(source: OutputEvidenceRecords) -> tuple[ModelAutoResearchOutputEvidenceRecord, ...]:
    raw = source() if callable(source) else source
    records = tuple(
        item
        if isinstance(item, ModelAutoResearchOutputEvidenceRecord)
        else rehydrate_model_autoresearch_output_evidence_record(item)
        for item in raw
    )
    record_ids = [record.record_id for record in records]
    if len(set(record_ids)) != len(record_ids):
        raise ValueError("duplicate_output_evidence_records")
    return records


def _records_for_sample(
    *,
    records: Sequence[ModelAutoResearchOutputEvidenceRecord],
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
) -> tuple[ModelAutoResearchOutputEvidenceRecord, ...]:
    matching = [
        record
        for record in records
        if record.task_id == task.task_id
        and record.prompt_digest == task.prompt_digest
        and record.candidate_id == candidate.candidate_id
        and record.candidate_topology_digest == candidate.topology_digest
    ]
    by_role = {record.role: record for record in matching}
    ordered: list[ModelAutoResearchOutputEvidenceRecord] = []
    for assignment in candidate.role_assignments:
        record = by_role.get(assignment.role)
        if record is not None:
            ordered.append(record)
    return tuple(ordered)


def _role_binding_rejections(
    candidate: ModelBenchmarkCandidate,
    records: Sequence[ModelAutoResearchOutputEvidenceRecord],
) -> list[str]:
    reasons: list[str] = []
    by_role = {record.role: record for record in records}
    if len(by_role) != len(records):
        reasons.append("semantic_verifier_duplicate_role_evidence")
    for assignment in candidate.role_assignments:
        record = by_role.get(assignment.role)
        if record is None:
            reasons.append(f"semantic_verifier_role_evidence_missing:{_clean_reason(assignment.role)}")
            continue
        if record.provider != assignment.provider:
            reasons.append(f"semantic_verifier_provider_mismatch:{_clean_reason(assignment.role)}")
        expected_model = _model_name_for_provider(assignment.model_id, assignment.provider)
        if record.model != expected_model:
            reasons.append(f"semantic_verifier_model_mismatch:{_clean_reason(assignment.role)}")
    return reasons


def _runner_digest_rejections(
    *,
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
    output: ModelBenchmarkTaskOutput,
    records: Sequence[ModelAutoResearchOutputEvidenceRecord],
) -> list[str]:
    policy_digests = {record.policy_digest for record in records}
    if len(policy_digests) != 1:
        return ["semantic_verifier_policy_digest_mismatch"]
    runner_body = {
        "schema_version": CONFIGURED_GATEWAY_RUNNER_SCHEMA_VERSION,
        "task_id": task.task_id,
        "prompt_digest": task.prompt_digest,
        "candidate_id": candidate.candidate_id,
        "candidate_topology_digest": candidate.topology_digest,
        "policy_digest": next(iter(policy_digests)),
        "calls": [
            {
                "role": record.role,
                "provider": record.provider,
                "model": record.model,
                "response_digest": record.response_digest,
                "latency_ms": record.latency_ms,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "cost_estimate_usd": record.cost_estimate_usd,
                "output_evidence_record_id": record.record_id,
            }
            for record in records
        ],
    }
    expected_output = _digest_prefixed("configured_gateway_benchmark_output", runner_body)
    expected_runner = _digest_prefixed("configured_gateway_benchmark_runner", runner_body)
    reasons: list[str] = []
    if not hmac.compare_digest(output.output_digest, expected_output):
        reasons.append("semantic_verifier_output_digest_mismatch")
    if not hmac.compare_digest(output.runner_receipt_id, expected_runner):
        reasons.append("semantic_verifier_runner_receipt_mismatch")
    return reasons


def _verifier_receipt_id(
    *,
    task: ModelBenchmarkTask,
    candidate: ModelBenchmarkCandidate,
    output: ModelBenchmarkTaskOutput,
    records: Sequence[ModelAutoResearchOutputEvidenceRecord],
    required_terms: Sequence[str],
    forbidden_terms: Sequence[str],
    policy_digest: str,
    accepted: bool,
    rejection_reasons: Sequence[str],
) -> str:
    return _digest_prefixed(
        "model_autoresearch_semantic_verifier",
        {
            "schema_version": MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER_SCHEMA,
            "task_id": task.task_id,
            "candidate_id": candidate.candidate_id,
            "output_digest": output.output_digest,
            "runner_receipt_id": output.runner_receipt_id,
            "evidence_record_ids": [record.record_id for record in records],
            "required_terms": list(required_terms),
            "forbidden_terms": list(forbidden_terms),
            "policy_digest": policy_digest,
            "accepted": accepted,
            "rejection_reasons": list(rejection_reasons),
        },
    )


def _terms(value: object) -> tuple[str, ...]:
    raw = str(value or "").strip()
    if not raw:
        return ()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            raise ValueError("invalid_semantic_verifier_terms") from exc
        if not isinstance(parsed, list):
            raise ValueError("invalid_semantic_verifier_terms")
        values = [str(item).strip() for item in parsed]
    else:
        values = [item.strip() for item in raw.replace("\n", ";").replace(",", ";").split(";")]
    return tuple(dict.fromkeys(item for item in values if item))


def _model_name_for_provider(model_id: str, provider: str) -> str:
    raw = _required("model_id", model_id)
    prefix = f"{provider}/"
    if raw.startswith(prefix):
        raw = raw[len(prefix) :]
    return _required("model", raw)


def _digest_prefixed(prefix: str, value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _required(name: str, value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing_{name}")
    return text


def _clean_token(value: object) -> str:
    text = _required("token", value)
    return "".join(ch if ch.isalnum() or ch in {"_", "-", ".", "/"} else "_" for ch in text)


def _clean_reason(value: object) -> str:
    text = str(value or "").strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-", ".", "/"} else "_" for ch in text)
    return cleaned[:64] or "unknown"


def _dedupe(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


__all__ = [
    "FORBIDDEN_TERMS_METADATA_KEY",
    "MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SEMANTIC_VERIFIER_SCHEMA",
    "ModelAutoResearchSemanticVerifierPolicy",
    "REQUIRED_TERMS_METADATA_KEY",
    "build_model_autoresearch_output_evidence_semantic_verifier",
]
