"""Bounded bootstrap for RedDog model-runtime use-time verification."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_artifact_supply_bootstrap import (
    _key_resolver,
    _signature_verifier,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_use_time_verifier import (
    ModelRuntimeBindingUseTimeVerifier,
)
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import (
    consume_verified_runtime_binding_capability,
    discard_verified_runtime_binding_capability,
    verified_runtime_binding_receipt,
)
from modules.communication.moltbot_bridge.src.reddog_elevated_authority_consensus_policy import (
    ReviewerRuntimeEvidence,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_json_read import (
    read_reddog_runtime_json_outside_repo,
)


@dataclass(frozen=True)
class ModelRuntimeVerifierConfig:
    catalog_path: Path | str | None = None
    benchmarks_path: Path | str | None = None
    promotions_path: Path | str | None = None
    evidence_path: Path | str | None = None
    policy_path: Path | str | None = None
    trusted_keys_path: Path | str | None = None
    verifier_backend: str = "ed25519"
    signature_verifier: Any = None

    def paths(self) -> tuple[Path | str | None, ...]:
        return (
            self.catalog_path,
            self.benchmarks_path,
            self.promotions_path,
            self.evidence_path,
            self.policy_path,
            self.trusted_keys_path,
        )


def build_model_runtime_verifier(
    *,
    repo_root: Path,
    runtime_root: Path,
    config: ModelRuntimeVerifierConfig | Mapping[str, Any] | None,
    trusted_now: Callable[[], int],
    injected: Any = None,
    artifact_generator: Any = None,
) -> tuple[Any, tuple[str, ...]]:
    if injected is not None:
        return injected, ()
    if artifact_generator is None:
        return None, ()
    try:
        values = (
            config
            if isinstance(config, ModelRuntimeVerifierConfig)
            else ModelRuntimeVerifierConfig(**dict(config or {}))
        )
    except (TypeError, ValueError):
        return None, ("malformed_model_runtime_verifier_config",)
    payloads, reasons = _load_payloads(repo_root, runtime_root, values.paths())
    resolver, found = _key_resolver(payloads.get("trusted_keys") or {})
    reasons.extend(found)
    verifier = values.signature_verifier
    if verifier is None:
        verifier, found = _signature_verifier(values.verifier_backend)
        reasons.extend(found)
    benchmarks = _records(payloads.get("benchmarks"), "benchmark_evidence_receipts")
    promotions = _records(payloads.get("promotions"), "promotion_evidence_receipts")
    if benchmarks is None:
        reasons.append("malformed_model_benchmark_evidence_receipts")
    if promotions is None:
        reasons.append("malformed_model_promotion_evidence_receipts")
    if reasons or resolver is None or verifier is None:
        return None, tuple(dict.fromkeys(reasons))
    return _verifier(
        payloads, benchmarks or (), promotions or (), resolver, verifier, trusted_now
    ), ()


def _load_payloads(
    repo_root: Path,
    runtime_root: Path,
    paths: tuple[Path | str | None, ...],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    names = ("catalog", "benchmarks", "promotions", "evidence", "policy", "trusted_keys")
    payloads: dict[str, Mapping[str, Any]] = {}
    reasons: list[str] = []
    for name, path in zip(names, paths):
        payload, found = read_reddog_runtime_json_outside_repo(
            repo_root,
            runtime_root,
            path,
            missing_reason=f"missing_model_runtime_verification_{name}_path",
            inside_reason=f"model_runtime_verification_{name}_path_inside_repo",
            unreadable_reason=f"malformed_model_runtime_verification_{name}",
        )
        reasons.extend(found)
        if payload is not None:
            payloads[name] = payload
    return payloads, reasons


def _records(
    payload: Mapping[str, Any] | None,
    key: str,
) -> tuple[Mapping[str, Any], ...] | None:
    raw = payload.get(key) if isinstance(payload, Mapping) else None
    if not isinstance(raw, list) or not raw:
        return None
    if any(not isinstance(item, Mapping) for item in raw):
        return None
    return tuple(raw)


def _verifier(
    payloads: Mapping[str, Mapping[str, Any]],
    benchmarks: tuple[Mapping[str, Any], ...],
    promotions: tuple[Mapping[str, Any], ...],
    resolver: Any,
    verifier: Any,
    trusted_now: Callable[[], int],
) -> ModelRuntimeBindingUseTimeVerifier:
    return ModelRuntimeBindingUseTimeVerifier(
        catalog_snapshot=payloads["catalog"],
        benchmark_evidence_receipts=benchmarks,
        promotion_evidence_receipts=promotions,
        verified_evidence_bundle=payloads["evidence"],
        runtime_policy=payloads["policy"],
        trusted_keys_payload=payloads["trusted_keys"],
        key_resolver=resolver,
        signature_verifier=verifier,
        trusted_now_epoch=trusted_now,
    )


@dataclass(frozen=True)
class ReviewerRuntimeArtifacts:
    """Caller-owned artifact pair and independently configured trusted verifier."""

    model_id: str
    selection: Mapping[str, Any]
    binding: Mapping[str, Any]
    verifier: ModelRuntimeBindingUseTimeVerifier


class ModelRuntimeReviewerEvidenceResolver:
    """Reverify cited artifacts, not execution provenance or principal authority.

    The composition owner must supply trusted verifier inputs (for example via
    build_model_runtime_verifier). This adapter does not authorize trust roots,
    prove model authorship, grant permissions, or enroll a production runtime.
    Each resolution snapshots the artifact pair and consumes a fresh capability.
    """

    def __init__(self, records: Mapping[str, ReviewerRuntimeArtifacts]):
        if len(records) > 8:
            raise ValueError("reviewer_runtime_artifact_limit_exceeded")
        self._records = dict(records)

    def resolve(self, reviewer_principal_id, model_selection_receipt_id,
                model_runtime_binding_receipt_id) -> ReviewerRuntimeEvidence | None:
        capability = None
        try:
            record = self._records.get(reviewer_principal_id)
            if type(record) is not ReviewerRuntimeArtifacts or type(record.verifier) is not ModelRuntimeBindingUseTimeVerifier:
                return None
            selection, binding = deepcopy((record.selection, record.binding))
            receipt = verified_runtime_binding_receipt(binding)
            if (receipt is None or record.model_id not in receipt.model_ids
                    or receipt.selection_receipt_id != model_selection_receipt_id
                    or receipt.runtime_binding_receipt_id != model_runtime_binding_receipt_id):
                return None
            now = record.verifier.trusted_now_epoch()
            if type(now) is not int or not receipt.verified_at <= now < receipt.valid_until:
                return None
            capability = ModelRuntimeBindingUseTimeVerifier.verify(
                record.verifier, binding=binding, selection=selection,
            )
            verified = consume_verified_runtime_binding_capability(
                capability, binding=binding, selection=selection, receipt=receipt,
            )
            finish = record.verifier.trusted_now_epoch()
            if verified is None or type(finish) is not int or not now <= finish < verified.valid_until:
                return None
            return ReviewerRuntimeEvidence(
                record.model_id, verified.selection_receipt_id,
                verified.selection_receipt_digest, verified.runtime_binding_receipt_id,
                verified.runtime_binding_digest, verified.valid_until,
            )
        except Exception:
            return None
        finally:
            discard_verified_runtime_binding_capability(capability)


__all__ = [
    "ReviewerRuntimeArtifacts",
    "ModelRuntimeReviewerEvidenceResolver",
    "ModelRuntimeVerifierConfig",
    "build_model_runtime_verifier",
]
