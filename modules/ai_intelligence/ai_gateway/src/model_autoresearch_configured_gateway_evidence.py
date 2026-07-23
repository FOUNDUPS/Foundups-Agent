"""Strict evidence records for configured-gateway AutoResearch calls."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Protocol, Sequence


BUDGET_SCHEMA_VERSION = "configured_gateway_model_budget_evidence.v1"
RUNNER_RECEIPT_SCHEMA_VERSION = "configured_gateway_runner_receipt.v2"
ATTEMPT_RECEIPT_SCHEMA_VERSION = "configured_gateway_call_attempt_receipt.v1"
MAX_RATE_PER_MILLION = Decimal("1000000000")
MAX_TOKEN_BOUND = 1_000_000
MAX_RESULT_VALUE = 1_000_000
MAX_RESPONSE_BYTES = 1_000_000
_DECIMAL_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z")
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")
_PROVIDER_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
_SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")


def digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"invalid_{name}")
    return value


def canonical_decimal(name: str, value: object) -> str:
    if not isinstance(value, str) or not _DECIMAL_PATTERN.fullmatch(value):
        raise ValueError(f"invalid_{name}")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid_{name}") from exc
    if not parsed.is_finite() or parsed <= 0 or parsed > MAX_RATE_PER_MILLION:
        raise ValueError(f"invalid_{name}")
    return value


def bounded_positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid_{name}")
    if value <= 0 or value > MAX_TOKEN_BOUND:
        raise ValueError(f"invalid_{name}")
    return value


def bounded_non_negative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid_{name}")
    if value < 0 or value > MAX_RESULT_VALUE:
        raise ValueError(f"invalid_{name}")
    return value


def bounded_non_negative_float(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid_{name}")
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0 or parsed > MAX_RESULT_VALUE:
        raise ValueError(f"invalid_{name}")
    return parsed


def exact_provider(value: object) -> str:
    if not isinstance(value, str) or not _PROVIDER_PATTERN.fullmatch(value):
        raise ValueError("invalid_provider")
    return value


def exact_model_id(name: str, value: object) -> str:
    if not isinstance(value, str) or not _TOKEN_PATTERN.fullmatch(value):
        raise ValueError(f"invalid_{name}")
    if not value.isascii():
        raise ValueError(f"invalid_{name}")
    return value


@dataclass(frozen=True)
class ConfiguredGatewayReasoningControlEvidence:
    mode: str
    effort: str
    supported_efforts: tuple[str, ...]
    catalog_evidence_digest: str

    def normalized(self) -> "ConfiguredGatewayReasoningControlEvidence":
        if self.mode != "effort":
            raise ValueError("invalid_reasoning_mode")
        effort = exact_model_id("reasoning_effort", self.effort)
        supported = tuple(
            exact_model_id("supported_reasoning_effort", item)
            for item in self.supported_efforts
        )
        if not supported or len(set(supported)) != len(supported):
            raise ValueError("invalid_reasoning_supported_efforts")
        if effort not in supported:
            raise ValueError("unsupported_reasoning_effort")
        return ConfiguredGatewayReasoningControlEvidence(
            mode="effort",
            effort=effort,
            supported_efforts=supported,
            catalog_evidence_digest=require_sha256(
                "catalog_evidence_digest",
                self.catalog_evidence_digest,
            ),
        )

    def to_dict(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "mode": item.mode,
            "effort": item.effort,
            "supported_efforts": list(item.supported_efforts),
            "catalog_evidence_digest": item.catalog_evidence_digest,
        }


@dataclass(frozen=True)
class ConfiguredGatewayModelBudgetEvidence:
    assignment_model_id: str
    provider: str
    api_model: str
    input_cost_per_million: str
    output_cost_per_million: str
    request_overhead_input_tokens: int
    max_completion_tokens: int
    reasoning_control: ConfiguredGatewayReasoningControlEvidence

    def normalized(self) -> "ConfiguredGatewayModelBudgetEvidence":
        provider = exact_provider(self.provider)
        assignment = exact_model_id("assignment_model_id", self.assignment_model_id)
        api_model = exact_model_id("api_model", self.api_model)
        if not assignment.startswith(provider + "/"):
            raise ValueError("assignment_provider_mismatch")
        return ConfiguredGatewayModelBudgetEvidence(
            assignment_model_id=assignment,
            provider=provider,
            api_model=api_model,
            input_cost_per_million=canonical_decimal(
                "input_cost_per_million",
                self.input_cost_per_million,
            ),
            output_cost_per_million=canonical_decimal(
                "output_cost_per_million",
                self.output_cost_per_million,
            ),
            request_overhead_input_tokens=bounded_positive_int(
                "request_overhead_input_tokens",
                self.request_overhead_input_tokens,
            ),
            max_completion_tokens=bounded_positive_int(
                "max_completion_tokens",
                self.max_completion_tokens,
            ),
            reasoning_control=self.reasoning_control.normalized(),
        )

    def to_dict(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "assignment_model_id": item.assignment_model_id,
            "provider": item.provider,
            "api_model": item.api_model,
            "input_cost_per_million": item.input_cost_per_million,
            "output_cost_per_million": item.output_cost_per_million,
            "request_overhead_input_tokens": item.request_overhead_input_tokens,
            "max_completion_tokens": item.max_completion_tokens,
            "reasoning_control": item.reasoning_control.to_dict(),
        }


@dataclass(frozen=True)
class ConfiguredGatewayModelBudgetEvidenceBundle:
    allowed_providers: tuple[str, ...]
    model_budgets: tuple[ConfiguredGatewayModelBudgetEvidence, ...]
    evidence_digest: str
    schema_version: str = BUDGET_SCHEMA_VERSION

    def normalized(self) -> "ConfiguredGatewayModelBudgetEvidenceBundle":
        if self.schema_version != BUDGET_SCHEMA_VERSION:
            raise ValueError("invalid_model_budget_schema_version")
        providers = tuple(exact_provider(item) for item in self.allowed_providers)
        budgets = tuple(item.normalized() for item in self.model_budgets)
        _validate_budget_collection(providers, budgets)
        body = {
            "schema_version": BUDGET_SCHEMA_VERSION,
            "allowed_providers": list(providers),
            "model_budgets": [item.to_dict() for item in budgets],
        }
        if digest_payload(body) != require_sha256("evidence_digest", self.evidence_digest):
            raise ValueError("model_budget_evidence_digest_mismatch")
        return ConfiguredGatewayModelBudgetEvidenceBundle(
            allowed_providers=providers,
            model_budgets=budgets,
            evidence_digest=self.evidence_digest,
        )

    def to_dict(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "schema_version": item.schema_version,
            "allowed_providers": list(item.allowed_providers),
            "model_budgets": [budget.to_dict() for budget in item.model_budgets],
            "evidence_digest": item.evidence_digest,
        }


def _validate_budget_collection(
    providers: tuple[str, ...],
    budgets: tuple[ConfiguredGatewayModelBudgetEvidence, ...],
) -> None:
    if not providers or len(set(providers)) != len(providers):
        raise ValueError("configured_gateway_runner_allowed_providers_required")
    if not budgets:
        raise ValueError("configured_gateway_runner_model_budgets_required")
    assignments = [item.assignment_model_id for item in budgets]
    routes = [(item.provider, item.api_model) for item in budgets]
    if len(set(assignments)) != len(assignments):
        raise ValueError("configured_gateway_runner_duplicate_assignment_model_budget")
    if len(set(routes)) != len(routes):
        raise ValueError("configured_gateway_runner_duplicate_route_model_budget")
    if set(providers) != {item.provider for item in budgets}:
        raise ValueError("configured_gateway_runner_model_budget_provider_set_mismatch")


def rehydrate_model_budget_evidence_bundle(
    payload: Mapping[str, object],
) -> ConfiguredGatewayModelBudgetEvidenceBundle:
    raw_budgets = payload.get("model_budgets")
    if not isinstance(raw_budgets, list):
        raise ValueError("malformed_model_budget_evidence")
    budgets = tuple(_rehydrate_budget(item) for item in raw_budgets)
    providers = payload.get("allowed_providers")
    if not isinstance(providers, list):
        raise ValueError("malformed_model_budget_evidence")
    return ConfiguredGatewayModelBudgetEvidenceBundle(
        schema_version=payload.get("schema_version"),  # type: ignore[arg-type]
        allowed_providers=tuple(providers),  # type: ignore[arg-type]
        model_budgets=budgets,
        evidence_digest=payload.get("evidence_digest"),  # type: ignore[arg-type]
    ).normalized()


def _rehydrate_budget(payload: object) -> ConfiguredGatewayModelBudgetEvidence:
    if not isinstance(payload, Mapping):
        raise ValueError("malformed_model_budget_evidence")
    reasoning = payload.get("reasoning_control")
    if not isinstance(reasoning, Mapping):
        raise ValueError("malformed_model_budget_evidence")
    return ConfiguredGatewayModelBudgetEvidence(
        assignment_model_id=payload.get("assignment_model_id"),  # type: ignore[arg-type]
        provider=payload.get("provider"),  # type: ignore[arg-type]
        api_model=payload.get("api_model"),  # type: ignore[arg-type]
        input_cost_per_million=payload.get("input_cost_per_million"),  # type: ignore[arg-type]
        output_cost_per_million=payload.get("output_cost_per_million"),  # type: ignore[arg-type]
        request_overhead_input_tokens=payload.get("request_overhead_input_tokens"),  # type: ignore[arg-type]
        max_completion_tokens=payload.get("max_completion_tokens"),  # type: ignore[arg-type]
        reasoning_control=ConfiguredGatewayReasoningControlEvidence(
            mode=reasoning.get("mode"),  # type: ignore[arg-type]
            effort=reasoning.get("effort"),  # type: ignore[arg-type]
            supported_efforts=tuple(reasoning.get("supported_efforts", ())),  # type: ignore[arg-type]
            catalog_evidence_digest=reasoning.get("catalog_evidence_digest"),  # type: ignore[arg-type]
        ),
    ).normalized()


@dataclass(frozen=True)
class PromptGuardApprovalReceipt:
    passed: bool
    prompt: str | None
    contract_digest: str
    profile_digest: str
    report_digest: str

    def normalized(self) -> "PromptGuardApprovalReceipt":
        if type(self.passed) is not bool:
            raise ValueError("invalid_prompt_guard_passed")
        if self.passed and not isinstance(self.prompt, str):
            raise ValueError("invalid_prompt_guard_prompt")
        if not self.passed and self.prompt is not None:
            raise ValueError("invalid_prompt_guard_blocked_prompt")
        return PromptGuardApprovalReceipt(
            passed=self.passed,
            prompt=self.prompt,
            contract_digest=require_sha256("guard_contract_digest", self.contract_digest),
            profile_digest=require_sha256("guard_profile_digest", self.profile_digest),
            report_digest=require_sha256("guard_report_digest", self.report_digest),
        )

    def to_dict(self) -> dict[str, object]:
        item = self.normalized()
        return {
            "passed": item.passed,
            "prompt": item.prompt,
            "contract_digest": item.contract_digest,
            "profile_digest": item.profile_digest,
            "report_digest": item.report_digest,
        }


@dataclass(frozen=True)
class ConfiguredGatewayCallAttemptReceipt:
    attempt_receipt_id: str
    attempt_group_id: str
    status: str
    task_id: str
    candidate_id: str
    role: str
    provider: str
    api_model: str
    source_prompt_digest: str
    sent_prompt_digest: str
    reserved_cost_usd: str
    terminal_reason: str | None = None
    schema_version: str = ATTEMPT_RECEIPT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "attempt_receipt_id": self.attempt_receipt_id,
            "attempt_group_id": self.attempt_group_id,
            "status": self.status,
            "task_id": self.task_id,
            "candidate_id": self.candidate_id,
            "role": self.role,
            "provider": self.provider,
            "api_model": self.api_model,
            "source_prompt_digest": self.source_prompt_digest,
            "sent_prompt_digest": self.sent_prompt_digest,
            "reserved_cost_usd": self.reserved_cost_usd,
            "terminal_reason": self.terminal_reason,
        }


@dataclass(frozen=True)
class ConfiguredGatewayRunnerCallReceipt:
    role: str
    provider: str
    api_model: str
    sent_prompt_digest: str
    guard_report_digest: str
    response_digest: str
    reserved_cost_usd: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    output_evidence_record_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ConfiguredGatewayRunnerReceipt:
    receipt_id: str
    task_id: str
    candidate_id: str
    source_prompt_digest: str
    policy_digest: str
    guard_contract_digest: str
    guard_profile_digest: str
    total_reserved_cost_usd: str
    calls: tuple[ConfiguredGatewayRunnerCallReceipt, ...]
    schema_version: str = RUNNER_RECEIPT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "task_id": self.task_id,
            "candidate_id": self.candidate_id,
            "source_prompt_digest": self.source_prompt_digest,
            "policy_digest": self.policy_digest,
            "guard_contract_digest": self.guard_contract_digest,
            "guard_profile_digest": self.guard_profile_digest,
            "total_reserved_cost_usd": self.total_reserved_cost_usd,
            "calls": [item.to_dict() for item in self.calls],
        }


class ConfiguredGatewayReceiptStore(Protocol):
    def append(self, receipt: object) -> str:
        """Append one canonical receipt and return its ID."""


class JsonlConfiguredGatewayReceiptStore:
    """Append-only JSONL receipt store used only with trusted outside-repo paths."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path).resolve()
        self._lock = threading.Lock()

    def append(self, receipt: object) -> str:
        to_dict = getattr(receipt, "to_dict", None)
        if not callable(to_dict):
            raise ValueError("configured_gateway_receipt_invalid")
        payload = to_dict()
        receipt_id = payload.get("attempt_receipt_id") or payload.get("receipt_id")
        if not isinstance(receipt_id, str):
            raise ValueError("configured_gateway_receipt_id_invalid")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        return receipt_id


def build_attempt_receipt(
    *,
    attempt_group_id: str,
    status: str,
    terminal_reason: str | None,
    fields: Mapping[str, object],
) -> ConfiguredGatewayCallAttemptReceipt:
    body = {
        "schema_version": ATTEMPT_RECEIPT_SCHEMA_VERSION,
        "attempt_group_id": attempt_group_id,
        "status": status,
        **fields,
        "terminal_reason": terminal_reason,
    }
    return ConfiguredGatewayCallAttemptReceipt(
        attempt_receipt_id="configured_gateway_call_attempt:" + digest_payload(body)[7:],
        attempt_group_id=attempt_group_id,
        status=status,
        terminal_reason=terminal_reason,
        task_id=str(fields["task_id"]),
        candidate_id=str(fields["candidate_id"]),
        role=str(fields["role"]),
        provider=str(fields["provider"]),
        api_model=str(fields["api_model"]),
        source_prompt_digest=str(fields["source_prompt_digest"]),
        sent_prompt_digest=str(fields["sent_prompt_digest"]),
        reserved_cost_usd=str(fields["reserved_cost_usd"]),
    )


def build_runner_receipt(
    *,
    task_id: str,
    candidate_id: str,
    source_prompt_digest: str,
    policy_digest: str,
    guard_contract_digest: str,
    guard_profile_digest: str,
    total_reserved_cost_usd: str,
    calls: Sequence[ConfiguredGatewayRunnerCallReceipt],
) -> ConfiguredGatewayRunnerReceipt:
    body = {
        "schema_version": RUNNER_RECEIPT_SCHEMA_VERSION,
        "task_id": task_id,
        "candidate_id": candidate_id,
        "source_prompt_digest": source_prompt_digest,
        "policy_digest": policy_digest,
        "guard_contract_digest": guard_contract_digest,
        "guard_profile_digest": guard_profile_digest,
        "total_reserved_cost_usd": total_reserved_cost_usd,
        "calls": [item.to_dict() for item in calls],
    }
    return ConfiguredGatewayRunnerReceipt(
        receipt_id="configured_gateway_runner:" + digest_payload(body)[7:],
        task_id=task_id,
        candidate_id=candidate_id,
        source_prompt_digest=source_prompt_digest,
        policy_digest=policy_digest,
        guard_contract_digest=guard_contract_digest,
        guard_profile_digest=guard_profile_digest,
        total_reserved_cost_usd=total_reserved_cost_usd,
        calls=tuple(calls),
    )


def rehydrate_call_attempt_receipt(
    payload: Mapping[str, object],
) -> ConfiguredGatewayCallAttemptReceipt:
    _require_exact_keys(payload, set(ConfiguredGatewayCallAttemptReceipt.__dataclass_fields__))
    if payload.get("schema_version") != ATTEMPT_RECEIPT_SCHEMA_VERSION:
        raise ValueError("invalid_attempt_receipt_schema_version")
    status, terminal_reason = payload.get("status"), payload.get("terminal_reason")
    terminal_statuses = {
        "CANCELLED",
        "COMPLETED",
        "FAILED",
        "REJECTED_OUTPUT",
        "ROUTE_MISMATCH",
    }
    if status == "ATTEMPTED":
        if terminal_reason is not None:
            raise ValueError("invalid_attempt_receipt_terminal_reason")
    elif status not in terminal_statuses or terminal_reason != str(status).lower():
        raise ValueError("invalid_attempt_receipt_status")
    fields = {
        "task_id": exact_model_id("task_id", payload.get("task_id")),
        "candidate_id": exact_model_id("candidate_id", payload.get("candidate_id")),
        "role": exact_model_id("role", payload.get("role")),
        "provider": exact_provider(payload.get("provider")),
        "api_model": exact_model_id("api_model", payload.get("api_model")),
        "source_prompt_digest": require_sha256(
            "source_prompt_digest", payload.get("source_prompt_digest")
        ),
        "sent_prompt_digest": require_sha256(
            "sent_prompt_digest", payload.get("sent_prompt_digest")
        ),
        "reserved_cost_usd": canonical_decimal(
            "reserved_cost_usd", payload.get("reserved_cost_usd")
        ),
    }
    expected_group = digest_payload(
        {
            "task_id": fields["task_id"],
            "candidate_id": fields["candidate_id"],
            "role": fields["role"],
            "sent_prompt_digest": fields["sent_prompt_digest"],
        }
    )
    if payload.get("attempt_group_id") != expected_group:
        raise ValueError("attempt_group_id_mismatch")
    receipt = build_attempt_receipt(
        attempt_group_id=expected_group,
        status=str(status),
        terminal_reason=terminal_reason if isinstance(terminal_reason, str) else None,
        fields=fields,
    )
    if payload.get("attempt_receipt_id") != receipt.attempt_receipt_id:
        raise ValueError("attempt_receipt_id_mismatch")
    return receipt


def rehydrate_runner_receipt(
    payload: Mapping[str, object],
) -> ConfiguredGatewayRunnerReceipt:
    _require_exact_keys(payload, set(ConfiguredGatewayRunnerReceipt.__dataclass_fields__))
    if payload.get("schema_version") != RUNNER_RECEIPT_SCHEMA_VERSION:
        raise ValueError("invalid_runner_receipt_schema_version")
    raw_calls = payload.get("calls")
    if not isinstance(raw_calls, list) or not raw_calls:
        raise ValueError("invalid_runner_receipt_calls")
    calls = tuple(_rehydrate_runner_call(item) for item in raw_calls)
    total = canonical_decimal(
        "total_reserved_cost_usd", payload.get("total_reserved_cost_usd")
    )
    if sum((Decimal(item.reserved_cost_usd) for item in calls), Decimal(0)) != Decimal(
        total
    ):
        raise ValueError("runner_receipt_total_cost_mismatch")
    receipt = build_runner_receipt(
        task_id=exact_model_id("task_id", payload.get("task_id")),
        candidate_id=exact_model_id("candidate_id", payload.get("candidate_id")),
        source_prompt_digest=require_sha256(
            "source_prompt_digest", payload.get("source_prompt_digest")
        ),
        policy_digest=require_sha256("policy_digest", payload.get("policy_digest")),
        guard_contract_digest=require_sha256(
            "guard_contract_digest", payload.get("guard_contract_digest")
        ),
        guard_profile_digest=require_sha256(
            "guard_profile_digest", payload.get("guard_profile_digest")
        ),
        total_reserved_cost_usd=total,
        calls=calls,
    )
    if payload.get("receipt_id") != receipt.receipt_id:
        raise ValueError("runner_receipt_id_mismatch")
    return receipt


def _rehydrate_runner_call(payload: object) -> ConfiguredGatewayRunnerCallReceipt:
    if not isinstance(payload, Mapping):
        raise ValueError("invalid_runner_receipt_call")
    _require_exact_keys(payload, set(ConfiguredGatewayRunnerCallReceipt.__dataclass_fields__))
    evidence_id = payload.get("output_evidence_record_id")
    if evidence_id is not None:
        evidence_id = exact_model_id("output_evidence_record_id", evidence_id)
    return ConfiguredGatewayRunnerCallReceipt(
        role=exact_model_id("role", payload.get("role")),
        provider=exact_provider(payload.get("provider")),
        api_model=exact_model_id("api_model", payload.get("api_model")),
        sent_prompt_digest=require_sha256(
            "sent_prompt_digest", payload.get("sent_prompt_digest")
        ),
        guard_report_digest=require_sha256(
            "guard_report_digest", payload.get("guard_report_digest")
        ),
        response_digest=require_sha256(
            "response_digest", payload.get("response_digest")
        ),
        reserved_cost_usd=canonical_decimal(
            "reserved_cost_usd", payload.get("reserved_cost_usd")
        ),
        latency_ms=bounded_non_negative_int("latency_ms", payload.get("latency_ms")),
        input_tokens=bounded_non_negative_int(
            "input_tokens", payload.get("input_tokens")
        ),
        output_tokens=bounded_non_negative_int(
            "output_tokens", payload.get("output_tokens")
        ),
        output_evidence_record_id=evidence_id,
    )


def read_call_attempt_receipts_jsonl(
    path: Path | str,
) -> tuple[ConfiguredGatewayCallAttemptReceipt, ...]:
    return tuple(
        rehydrate_call_attempt_receipt(item) for item in _read_jsonl_records(path)
    )


def read_runner_receipts_jsonl(
    path: Path | str,
) -> tuple[ConfiguredGatewayRunnerReceipt, ...]:
    return tuple(rehydrate_runner_receipt(item) for item in _read_jsonl_records(path))


def _read_jsonl_records(path: Path | str) -> tuple[Mapping[str, object], ...]:
    records: list[Mapping[str, object]] = []
    try:
        with Path(path).resolve().open("r", encoding="utf-8") as handle:
            for line in handle:
                if len(line.encode("utf-8")) > MAX_RESPONSE_BYTES * 2:
                    raise ValueError("configured_gateway_receipt_record_too_large")
                payload = json.loads(line)
                if not isinstance(payload, Mapping):
                    raise ValueError("configured_gateway_receipt_record_invalid")
                records.append(payload)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError("configured_gateway_receipt_store_malformed") from None
    return tuple(records)


def _require_exact_keys(payload: Mapping[str, object], expected: set[str]) -> None:
    if set(payload) != expected:
        raise ValueError("configured_gateway_receipt_fields_mismatch")


__all__ = [
    "ConfiguredGatewayCallAttemptReceipt",
    "ConfiguredGatewayModelBudgetEvidence",
    "ConfiguredGatewayModelBudgetEvidenceBundle",
    "ConfiguredGatewayReasoningControlEvidence",
    "ConfiguredGatewayReceiptStore",
    "ConfiguredGatewayRunnerCallReceipt",
    "ConfiguredGatewayRunnerReceipt",
    "JsonlConfiguredGatewayReceiptStore",
    "MAX_RESPONSE_BYTES",
    "PromptGuardApprovalReceipt",
    "bounded_non_negative_float",
    "bounded_non_negative_int",
    "bounded_positive_int",
    "build_attempt_receipt",
    "build_runner_receipt",
    "canonical_decimal",
    "digest_payload",
    "read_call_attempt_receipts_jsonl",
    "read_runner_receipts_jsonl",
    "rehydrate_call_attempt_receipt",
    "rehydrate_model_budget_evidence_bundle",
    "rehydrate_runner_receipt",
    "require_sha256",
]
