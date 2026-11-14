"""Content-bearing output evidence for model AutoResearch benchmarks.

This module stores configured-gateway model responses as digest-bound evidence
records in an injected outside-repository store. The benchmark harness can keep
digest-only receipts while an independent verifier can later rehydrate the raw
answer text from a governed artifact.

It does not call providers, run benchmarks, verify answers, promote models,
write PatternMemory, mutate HoloIndex, execute commands, mutate the repository,
or bind RedDog runtime defaults.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Protocol


MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SCHEMA_VERSION = (
    "model_autoresearch_output_evidence_record.v1"
)
MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_RECORD_TYPE = "model_autoresearch_output_evidence"

SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key",
    "apikey",
    "private_key",
    "begin private key",
    "secret=",
    "token=",
    "password=",
)


class ModelAutoResearchOutputEvidenceStore(Protocol):
    """Injected store for content-bearing benchmark output evidence."""

    def append(self, record: "ModelAutoResearchOutputEvidenceRecord") -> str:
        ...


@dataclass(frozen=True)
class ModelAutoResearchOutputEvidenceRecord:
    """One digest-bound raw model response for a benchmark role call."""

    record_id: str
    task_id: str
    prompt_digest: str
    candidate_id: str
    candidate_topology_digest: str
    role: str
    provider: str
    model: str
    policy_digest: str
    response_text: str
    response_digest: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_estimate_usd: float
    schema_version: str = MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SCHEMA_VERSION
    record_type: str = MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_RECORD_TYPE

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class InMemoryModelAutoResearchOutputEvidenceStore:
    """Test/local store for output evidence records."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def append(self, record: ModelAutoResearchOutputEvidenceRecord) -> str:
        rehydrated = rehydrate_model_autoresearch_output_evidence_record(record.to_dict())
        self.records.append(rehydrated.to_dict())
        return rehydrated.record_id


class JsonlModelAutoResearchOutputEvidenceStore:
    """Append-only JSONL store for output evidence records.

    The path must resolve outside the source repository because these records
    contain raw model output. The store rehydrates every record before append so
    caller-provided accepted flags or stale digests cannot be trusted.
    """

    def __init__(self, path: Path | str, *, repo_root: Path | str) -> None:
        self.path = Path(path).resolve()
        self.repo_root = Path(repo_root).resolve()
        if _is_inside(self.path, self.repo_root):
            raise ValueError("model_autoresearch_output_evidence_path_inside_repo")

    def append(self, record: ModelAutoResearchOutputEvidenceRecord) -> str:
        rehydrated = rehydrate_model_autoresearch_output_evidence_record(record.to_dict())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            rehydrated.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return rehydrated.record_id


def build_model_autoresearch_output_evidence_record(
    *,
    task_id: str,
    prompt_digest: str,
    candidate_id: str,
    candidate_topology_digest: str,
    role: str,
    provider: str,
    model: str,
    policy_digest: str,
    response_text: str,
    latency_ms: int,
    input_tokens: int,
    output_tokens: int,
    cost_estimate_usd: float,
) -> ModelAutoResearchOutputEvidenceRecord:
    """Build one output evidence record and reject secret-bearing responses."""

    response = str(response_text or "")
    if _contains_secret(response):
        raise ValueError("model_autoresearch_output_evidence_secret_detected")
    response_digest = _content_digest(response)
    fields = {
        "schema_version": MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SCHEMA_VERSION,
        "record_type": MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_RECORD_TYPE,
        "task_id": _required("task_id", task_id),
        "prompt_digest": _required("prompt_digest", prompt_digest),
        "candidate_id": _required("candidate_id", candidate_id),
        "candidate_topology_digest": _required(
            "candidate_topology_digest",
            candidate_topology_digest,
        ),
        "role": _clean_token(_required("role", role)),
        "provider": _clean_token(_required("provider", provider)),
        "model": _required("model", model),
        "policy_digest": _required("policy_digest", policy_digest),
        "response_text": response,
        "response_digest": response_digest,
        "latency_ms": _non_negative_int(latency_ms),
        "input_tokens": _non_negative_int(input_tokens),
        "output_tokens": _non_negative_int(output_tokens),
        "cost_estimate_usd": _non_negative_float(cost_estimate_usd),
    }
    record_id = _record_id(fields)
    record = ModelAutoResearchOutputEvidenceRecord(record_id=record_id, **fields)
    if _contains_secret(record.to_dict()):
        raise ValueError("model_autoresearch_output_evidence_secret_detected")
    return record


def rehydrate_model_autoresearch_output_evidence_record(
    payload: Mapping[str, Any],
) -> ModelAutoResearchOutputEvidenceRecord:
    """Rehydrate a serialized output evidence record and verify every digest."""

    if not isinstance(payload, Mapping):
        raise ValueError("invalid_model_autoresearch_output_evidence_record")
    if payload.get("schema_version") != MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("invalid_model_autoresearch_output_evidence_schema")
    if payload.get("record_type") != MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_RECORD_TYPE:
        raise ValueError("invalid_model_autoresearch_output_evidence_type")
    record_id = _required("record_id", payload.get("record_id"))
    response_text = str(payload.get("response_text") or "")
    response_digest = _required("response_digest", payload.get("response_digest"))
    if not hmac.compare_digest(response_digest, _content_digest(response_text)):
        raise ValueError("model_autoresearch_output_evidence_response_digest_mismatch")
    record = build_model_autoresearch_output_evidence_record(
        task_id=_required("task_id", payload.get("task_id")),
        prompt_digest=_required("prompt_digest", payload.get("prompt_digest")),
        candidate_id=_required("candidate_id", payload.get("candidate_id")),
        candidate_topology_digest=_required(
            "candidate_topology_digest",
            payload.get("candidate_topology_digest"),
        ),
        role=_required("role", payload.get("role")),
        provider=_required("provider", payload.get("provider")),
        model=_required("model", payload.get("model")),
        policy_digest=_required("policy_digest", payload.get("policy_digest")),
        response_text=response_text,
        latency_ms=_non_negative_int(payload.get("latency_ms")),
        input_tokens=_non_negative_int(payload.get("input_tokens")),
        output_tokens=_non_negative_int(payload.get("output_tokens")),
        cost_estimate_usd=_non_negative_float(payload.get("cost_estimate_usd")),
    )
    if not hmac.compare_digest(record_id, record.record_id):
        raise ValueError("model_autoresearch_output_evidence_record_id_mismatch")
    return record


def read_model_autoresearch_output_evidence_jsonl(
    path: Path | str,
    *,
    repo_root: Path | str,
) -> tuple[ModelAutoResearchOutputEvidenceRecord, ...]:
    """Read an outside-repo JSONL evidence store and verify all records."""

    resolved = Path(path).resolve()
    root = Path(repo_root).resolve()
    if _is_inside(resolved, root):
        raise ValueError("model_autoresearch_output_evidence_path_inside_repo")
    records: list[ModelAutoResearchOutputEvidenceRecord] = []
    with resolved.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            records.append(
                rehydrate_model_autoresearch_output_evidence_record(json.loads(text))
            )
    return tuple(records)


def _record_id(fields: Mapping[str, Any]) -> str:
    return _digest_prefixed("model_autoresearch_output_evidence", fields)


def _content_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _digest_prefixed(prefix: str, value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(encoded).hexdigest()}"


def _contains_secret(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, default=str).lower()
    return any(marker in text for marker in SECRET_MARKERS)


def _required(name: str, value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing_{name}")
    return text


def _clean_token(value: object) -> str:
    text = _required("token", value)
    return "".join(ch if ch.isalnum() or ch in {"_", "-", ".", "/"} else "_" for ch in text)


def _non_negative_int(value: object) -> int:
    try:
        result = int(value)
    except Exception as exc:
        raise ValueError("invalid_non_negative_int") from exc
    if result < 0:
        raise ValueError("invalid_non_negative_int")
    return result


def _non_negative_float(value: object) -> float:
    try:
        result = float(value)
    except Exception as exc:
        raise ValueError("invalid_non_negative_float") from exc
    if result < 0.0:
        raise ValueError("invalid_non_negative_float")
    return result


def _is_inside(child: Path, parent: Path) -> bool:
    child_r = child.resolve()
    parent_r = parent.resolve()
    return child_r == parent_r or parent_r in child_r.parents


__all__ = [
    "InMemoryModelAutoResearchOutputEvidenceStore",
    "JsonlModelAutoResearchOutputEvidenceStore",
    "MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_RECORD_TYPE",
    "MODEL_AUTORESEARCH_OUTPUT_EVIDENCE_SCHEMA_VERSION",
    "ModelAutoResearchOutputEvidenceRecord",
    "ModelAutoResearchOutputEvidenceStore",
    "build_model_autoresearch_output_evidence_record",
    "read_model_autoresearch_output_evidence_jsonl",
    "rehydrate_model_autoresearch_output_evidence_record",
]
