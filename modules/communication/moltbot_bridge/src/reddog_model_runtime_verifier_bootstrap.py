"""Bounded bootstrap for RedDog model-runtime use-time verification."""

from __future__ import annotations

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


__all__ = [
    "ModelRuntimeVerifierConfig",
    "build_model_runtime_verifier",
]
