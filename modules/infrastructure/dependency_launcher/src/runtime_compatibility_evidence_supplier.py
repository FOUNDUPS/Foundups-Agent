"""Compose cached runtime compatibility evidence from bounded source receipts.

This WRE-side producer is intentionally separate from the startup consumer. It
may publish an off-repo cache, but it never installs software, loads a model, or
changes a runtime route. Source receipt hashes provide integrity, not signer
authentication; production update authority remains a separate gate.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    secure_read_confined_text,
    secure_replace_runtime_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

from .runtime_compatibility_receipt import (
    CompatibilityState,
    EVIDENCE_SCHEMA,
    INTEGRITY_ONLY,
    MAX_EVIDENCE_TTL_SECONDS,
    MAX_FUTURE_SKEW_SECONDS,
    REQUIRED_COMPONENTS,
    build_runtime_compatibility_receipt,
    canonical_digest,
)


SOURCE_SCHEMA = "reddog_runtime_component_source_receipt.v1"
SUPPLY_SCHEMA = "reddog_runtime_compatibility_supply.v1"
SOURCE_ROLES = frozenset({"INSTALLED_OBSERVATION", "EXPECTED_BINDING"})
OFFICIAL_RELEASE_APIS = {
    "openclaw": "https://api.github.com/repos/openclaw/openclaw/releases/latest",
    "hermes": "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest",
}
PROMOTED_COMPONENTS = frozenset({"qwen_general", "qwen_code", "inference_backend"})
MAX_SUPPLY_BYTES = 512 * 1024
SOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "component_id",
        "source_role",
        "source_kind",
        "component_ref",
        "source_locator",
        "source_payload_digest",
        "observed_at_utc",
        "expires_at_utc",
        "verification",
        "receipt_id",
    }
)
SUPPLY_FIELDS = frozenset(
    {
        "schema_version",
        "verification",
        "installed_observations",
        "promoted_expectations",
        "supply_receipt_id",
    }
)


@dataclass(frozen=True)
class RuntimeComponentSourceReceipt:
    schema_version: str
    component_id: str
    source_role: str
    source_kind: str
    component_ref: str
    source_locator: str
    source_payload_digest: str
    observed_at_utc: str
    expires_at_utc: str
    verification: str
    receipt_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_component_source_receipt(
    *,
    component_id: str,
    source_role: str,
    source_kind: str,
    component_ref: str,
    source_locator: str,
    source_payload_digest: str,
    observed_at_utc: str,
    expires_at_utc: str,
) -> RuntimeComponentSourceReceipt:
    """Build one deterministic source receipt after strict field validation."""
    body = {
        "schema_version": SOURCE_SCHEMA,
        "component_id": _component(component_id),
        "source_role": _role(source_role),
        "source_kind": _source_kind(source_kind),
        "component_ref": _bounded(component_ref, "component_ref"),
        "source_locator": _bounded(source_locator, "source_locator"),
        "source_payload_digest": _digest(source_payload_digest, "source_payload_digest"),
        "observed_at_utc": _timestamp(observed_at_utc, "observed_at_utc").isoformat(),
        "expires_at_utc": _timestamp(expires_at_utc, "expires_at_utc").isoformat(),
        "verification": INTEGRITY_ONLY,
    }
    _validate_source_semantics(body)
    return RuntimeComponentSourceReceipt(**body, receipt_id=canonical_digest(body))


def rehydrate_component_source_receipt(
    value: Mapping[str, Any],
    *,
    now: datetime,
) -> RuntimeComponentSourceReceipt:
    """Recompute one serialized source receipt and enforce use-time freshness."""
    if set(value) != SOURCE_FIELDS:
        raise ValueError("source_receipt_fields_invalid")
    receipt = build_component_source_receipt(
        component_id=str(value.get("component_id") or ""),
        source_role=str(value.get("source_role") or ""),
        source_kind=str(value.get("source_kind") or ""),
        component_ref=str(value.get("component_ref") or ""),
        source_locator=str(value.get("source_locator") or ""),
        source_payload_digest=str(value.get("source_payload_digest") or ""),
        observed_at_utc=str(value.get("observed_at_utc") or ""),
        expires_at_utc=str(value.get("expires_at_utc") or ""),
    )
    if receipt.receipt_id != value.get("receipt_id"):
        raise ValueError("source_receipt_id_mismatch")
    _validate_freshness(receipt, _utc(now))
    return receipt


def compose_runtime_compatibility_evidence(
    supply: Mapping[str, Any],
    *,
    upstream_releases: Mapping[str, Mapping[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compose the exact evidence envelope consumed by the startup advisory."""
    instant = _utc(now or datetime.now(timezone.utc))
    _validate_supply_envelope(supply)
    observations = _receipt_map(supply.get("installed_observations"), instant)
    expected = _receipt_map(supply.get("promoted_expectations"), instant)
    _require_exact_set(observations, set(REQUIRED_COMPONENTS), "observation")
    _require_exact_set(expected, set(PROMOTED_COMPONENTS), "promoted_expectation")
    expected.update(_upstream_expectations(upstream_releases, instant))
    components = [
        _component_evidence(observations[component_id], expected[component_id])
        for component_id in REQUIRED_COMPONENTS
    ]
    expires = min(
        _timestamp(receipt.expires_at_utc, "expires_at_utc")
        for receipt in (*observations.values(), *expected.values())
    )
    payload: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA,
        "generated_at_utc": instant.isoformat(),
        "expires_at_utc": expires.isoformat(),
        "verification": INTEGRITY_ONLY,
        "source_receipt_ids": sorted(
            receipt.receipt_id for receipt in (*observations.values(), *expected.values())
        ),
        "components": components,
    }
    payload["evidence_receipt_id"] = canonical_digest(payload)
    return payload


def build_runtime_compatibility_supply(
    *,
    installed_observations: Sequence[RuntimeComponentSourceReceipt | Mapping[str, Any]],
    promoted_expectations: Sequence[RuntimeComponentSourceReceipt | Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the deterministic handoff supplied by WRE inventory/promotion owners."""
    payload: dict[str, Any] = {
        "schema_version": SUPPLY_SCHEMA,
        "verification": INTEGRITY_ONLY,
        "installed_observations": [_mapping(item) for item in installed_observations],
        "promoted_expectations": [_mapping(item) for item in promoted_expectations],
    }
    payload["supply_receipt_id"] = canonical_digest(payload)
    return payload


def load_runtime_compatibility_supply(
    repo_root: Path | str,
    *,
    runtime_root: Path | str,
    supply_path: Path | str,
) -> dict[str, Any]:
    """Load one bounded off-repo supply mapping without following a symlink."""
    root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    path = validate_runtime_artifact_path(supply_path, repo_root=repo_root, allowed_root=root)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_SUPPLY_BYTES:
        raise ValueError("runtime_compatibility_supply_unavailable")
    value = json.loads(
        secure_read_confined_text(path, allowed_root=root, max_bytes=MAX_SUPPLY_BYTES)
    )
    if not isinstance(value, dict):
        raise ValueError("runtime_compatibility_supply_not_mapping")
    return value


def publish_runtime_compatibility_evidence(
    evidence: Mapping[str, Any],
    *,
    repo_root: Path | str,
    runtime_root: Path | str,
    output_path: Path | str,
) -> Path:
    """Atomically publish validated evidence beneath the configured runtime root."""
    root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    path = validate_runtime_artifact_path(output_path, repo_root=repo_root, allowed_root=root)
    if path.exists() and path.is_symlink():
        raise ValueError("runtime_compatibility_output_symlink")
    receipt = build_runtime_compatibility_receipt(evidence)
    if receipt.reasons != ("evidence_authentication_not_verified",) or any(
        item.state == CompatibilityState.NOT_READY.value for item in receipt.components
    ):
        raise ValueError("runtime_compatibility_evidence_invalid")
    return secure_replace_runtime_text(
        path,
        json.dumps(dict(evidence), indent=2, ensure_ascii=True) + "\n",
        repo_root=repo_root,
        allowed_root=root,
    )


def _upstream_expectations(
    releases: Mapping[str, Mapping[str, Any]], now: datetime
) -> dict[str, RuntimeComponentSourceReceipt]:
    _require_exact_set(releases, set(OFFICIAL_RELEASE_APIS), "upstream_release")
    return {
        component_id: _release_receipt(component_id, releases[component_id], now)
        for component_id in OFFICIAL_RELEASE_APIS
    }


def _release_receipt(
    component_id: str, release: Mapping[str, Any], now: datetime
) -> RuntimeComponentSourceReceipt:
    if release.get("draft") is True or release.get("prerelease") is True:
        raise ValueError("upstream_release_not_stable")
    tag = _bounded(str(release.get("tag_name") or ""), "tag_name")
    html_url = _bounded(str(release.get("html_url") or ""), "html_url")
    repository = OFFICIAL_RELEASE_APIS[component_id].split("/repos/", 1)[1].split("/releases/", 1)[0]
    if not html_url.startswith(f"https://github.com/{repository}/releases/tag/"):
        raise ValueError("upstream_release_url_invalid")
    published = _timestamp(str(release.get("published_at") or ""), "published_at")
    if published > now + timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        raise ValueError("upstream_release_published_in_future")
    return build_component_source_receipt(
        component_id=component_id,
        source_role="EXPECTED_BINDING",
        source_kind="UPSTREAM_RELEASE",
        component_ref=tag,
        source_locator=OFFICIAL_RELEASE_APIS[component_id],
        source_payload_digest=canonical_digest(dict(release)),
        observed_at_utc=now.isoformat(),
        expires_at_utc=(now + timedelta(days=7)).isoformat(),
    )


def _receipt_map(raw: Any, now: datetime) -> dict[str, RuntimeComponentSourceReceipt]:
    if not isinstance(raw, list):
        raise ValueError("source_receipts_invalid")
    result: dict[str, RuntimeComponentSourceReceipt] = {}
    for value in raw:
        if not isinstance(value, Mapping):
            raise ValueError("source_receipt_invalid")
        receipt = rehydrate_component_source_receipt(value, now=now)
        if receipt.component_id in result:
            raise ValueError("source_receipt_duplicate")
        result[receipt.component_id] = receipt
    return result


def _component_evidence(
    installed: RuntimeComponentSourceReceipt,
    expected: RuntimeComponentSourceReceipt,
) -> dict[str, Any]:
    if installed.source_role != "INSTALLED_OBSERVATION" or installed.source_kind != "LOCAL_RUNTIME_OBSERVATION":
        raise ValueError("installed_observation_kind_invalid")
    if expected.source_role != "EXPECTED_BINDING":
        raise ValueError("expected_binding_role_invalid")
    if installed.component_id != expected.component_id:
        raise ValueError("component_source_mismatch")
    return {
        "component_id": installed.component_id,
        "installed_ref": installed.component_ref,
        "expected_ref": expected.component_ref,
        "evidence_kind": expected.source_kind,
        "evidence_receipt_id": canonical_digest(
            {"installed": installed.receipt_id, "expected": expected.receipt_id}
        ),
        "verification": INTEGRITY_ONLY,
    }


def _validate_supply_envelope(supply: Mapping[str, Any]) -> None:
    if set(supply) != SUPPLY_FIELDS:
        raise ValueError("runtime_compatibility_supply_fields_invalid")
    if supply.get("schema_version") != SUPPLY_SCHEMA or supply.get("verification") != INTEGRITY_ONLY:
        raise ValueError("runtime_compatibility_supply_invalid")
    receipt_id = str(supply.get("supply_receipt_id") or "")
    unsigned = {key: value for key, value in supply.items() if key != "supply_receipt_id"}
    if receipt_id != canonical_digest(unsigned):
        raise ValueError("runtime_compatibility_supply_receipt_mismatch")


def _validate_source_semantics(body: Mapping[str, Any]) -> None:
    component_id = str(body["component_id"])
    role = str(body["source_role"])
    kind = str(body["source_kind"])
    if role == "INSTALLED_OBSERVATION" and kind != "LOCAL_RUNTIME_OBSERVATION":
        raise ValueError("installed_observation_kind_invalid")
    if role == "EXPECTED_BINDING":
        expected = "UPSTREAM_RELEASE" if component_id in OFFICIAL_RELEASE_APIS else "PROMOTED_RUNTIME_BINDING"
        if kind != expected:
            raise ValueError("expected_binding_kind_invalid")


def _validate_freshness(receipt: RuntimeComponentSourceReceipt, now: datetime) -> None:
    observed = _timestamp(receipt.observed_at_utc, "observed_at_utc")
    expires = _timestamp(receipt.expires_at_utc, "expires_at_utc")
    lifetime = (expires - observed).total_seconds()
    if expires <= observed or now > expires or lifetime > MAX_EVIDENCE_TTL_SECONDS:
        raise ValueError("source_receipt_expired")
    if (observed - now).total_seconds() > MAX_FUTURE_SKEW_SECONDS:
        raise ValueError("source_receipt_observed_in_future")


def _require_exact_set(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label}_component_set_invalid")


def _mapping(value: RuntimeComponentSourceReceipt | Mapping[str, Any]) -> dict[str, Any]:
    return value.to_dict() if isinstance(value, RuntimeComponentSourceReceipt) else dict(value)


def _component(value: str) -> str:
    return value if value in REQUIRED_COMPONENTS else _raise("component_id_invalid")


def _role(value: str) -> str:
    return value if value in SOURCE_ROLES else _raise("source_role_invalid")


def _source_kind(value: str) -> str:
    allowed = {"LOCAL_RUNTIME_OBSERVATION", "UPSTREAM_RELEASE", "PROMOTED_RUNTIME_BINDING"}
    return value if value in allowed else _raise("source_kind_invalid")


def _bounded(value: str, name: str) -> str:
    text = str(value).strip()
    if not text or len(text) > 512 or not text.isascii() or not text.isprintable():
        raise ValueError(f"{name}_invalid")
    return text


def _digest(value: str, name: str) -> str:
    text = str(value)
    if len(text) != 71 or not text.startswith("sha256:") or any(char not in "0123456789abcdef" for char in text[7:]):
        raise ValueError(f"{name}_invalid")
    return text


def _timestamp(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name}_invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name}_timezone_missing")
    return _utc(parsed)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _raise(reason: str) -> Any:
    raise ValueError(reason)


__all__ = [
    "MAX_SUPPLY_BYTES",
    "OFFICIAL_RELEASE_APIS",
    "RuntimeComponentSourceReceipt",
    "SOURCE_SCHEMA",
    "SOURCE_FIELDS",
    "SUPPLY_SCHEMA",
    "SUPPLY_FIELDS",
    "build_component_source_receipt",
    "build_runtime_compatibility_supply",
    "compose_runtime_compatibility_evidence",
    "load_runtime_compatibility_supply",
    "publish_runtime_compatibility_evidence",
    "rehydrate_component_source_receipt",
]
