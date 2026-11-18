"""RedDog authoritative work-state source-record supplier.

Slice: REDDOG_AUTHORITATIVE_WORK_STATE_SOURCE_RECORD_SUPPLY_PHASE1

This module materializes the GitHub PR and W10 report source-record JSON files
that the authoritative work-state refresh runtime already consumes. It is a
read-only source collector: it does not refresh work state, claim workers,
enqueue OpenClaw, dispatch Hermes, mutate HoloIndex, execute shell commands, or
write repository files.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, Tuple


SOURCE_RECORD_SUPPLY_APPLIED = "SOURCE_RECORD_SUPPLY_APPLIED"
SOURCE_RECORD_SUPPLY_NOT_READY = "SOURCE_RECORD_SUPPLY_NOT_READY"

_SLICE_ID_RE = r"[A-Z][A-Z0-9]+(?:_[A-Z0-9]+){2,}_PHASE[0-9]+"


class GitHubPullRequestSourceProvider(Protocol):
    """Read-only provider for GitHub pull request records."""

    def collect_pull_request_records(self, *, now_iso: str) -> Sequence[Mapping[str, Any]]:
        """Return refresh-runtime-compatible GitHub PR records."""


class W10ReportSourceProvider(Protocol):
    """Read-only provider for W10 report records."""

    def collect_w10_report_records(self, *, now_iso: str) -> Sequence[Mapping[str, Any]]:
        """Return refresh-runtime-compatible W10 report records."""


@dataclass(frozen=True)
class SourceRecordSupplyReceipt:
    """Receipt for a materialized source-record supply operation."""

    receipt_id: str
    generated_at: str
    github_pr_records_path: str
    w10_report_records_path: str
    github_record_count: int
    w10_record_count: int
    github_source_mode: str
    w10_source_mode: str
    rejection_reasons: Tuple[str, ...]
    no_repo_mutation_performed: bool = True
    no_holoindex_reindex_performed: bool = True
    no_worker_spawn_performed: bool = True
    no_openclaw_enqueue_performed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_execution_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceRecordSupplyResult:
    """Result returned by source-record materialization."""

    accepted: bool
    status: str
    receipt: SourceRecordSupplyReceipt
    github_pr_records_path: str | None = None
    w10_report_records_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "receipt": self.receipt.to_dict(),
            "github_pr_records_path": self.github_pr_records_path,
            "w10_report_records_path": self.w10_report_records_path,
        }


class GitHubRestPullRequestSourceProvider:
    """Read-only GitHub REST source provider for open PR records."""

    def __init__(
        self,
        *,
        repo_full_name: str,
        token: str | None = None,
        state: str = "open",
        timeout_seconds: float = 10.0,
    ) -> None:
        if "/" not in repo_full_name:
            raise ValueError("repo_full_name must be owner/repo")
        self.repo_full_name = repo_full_name.strip()
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
        self.state = state.strip().lower() or "open"
        self.timeout_seconds = timeout_seconds

    def collect_pull_request_records(self, *, now_iso: str) -> Sequence[Mapping[str, Any]]:
        url = (
            f"https://api.github.com/repos/{self.repo_full_name}/pulls"
            f"?state={self.state}&per_page=100"
        )
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Foundups-Agent-RedDog-WorkState-Source-Supply",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"github_pr_source_failed:{exc.__class__.__name__}") from exc
        if not isinstance(payload, list):
            raise RuntimeError("github_pr_source_failed:response_not_list")
        return tuple(_github_pr_to_record(item, now_iso=now_iso) for item in payload if isinstance(item, Mapping))


class WorkLedgerProjectionW10ReportProvider:
    """Project work-ledger slices into conservative W10 report records.

    This is a bridge until a real W10 report service is attached. The evidence
    reference is intentionally labeled as a ledger projection so consumers do
    not confuse it with independent W10 review.
    """

    def __init__(self, *, work_ledger_json_path: Path | str) -> None:
        self.work_ledger_json_path = Path(work_ledger_json_path)

    def collect_w10_report_records(self, *, now_iso: str) -> Sequence[Mapping[str, Any]]:
        try:
            payload = json.loads(self.work_ledger_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"w10_projection_source_failed:{exc.__class__.__name__}") from exc
        if not isinstance(payload, Mapping):
            raise RuntimeError("w10_projection_source_failed:root_not_object")
        records: list[dict[str, Any]] = []
        for item in payload.get("slices") or []:
            if not isinstance(item, Mapping):
                continue
            slice_id = _normalize_slice_id(item.get("slice_id"))
            if not slice_id:
                continue
            score = item.get("wsp15_score")
            evidence_refs = [str(ref) for ref in (item.get("evidence_docs") or []) if ref]
            records.append(
                {
                    "slice_id": slice_id,
                    "status": str(item.get("status") or "PROPOSED").strip().upper(),
                    "priority": item.get("priority"),
                    "lane": item.get("lane"),
                    "branch": item.get("branch"),
                    "pr_number": item.get("pr_number"),
                    "head_commit": item.get("head_commit") or item.get("merge_commit") or item.get("base_commit"),
                    "evidence_refs": (
                        *evidence_refs,
                        f"w10:ledger_projection:{_digest({'slice_id': slice_id, 'now': now_iso})}",
                    ),
                    "wsp15_score": score if isinstance(score, Mapping) else {},
                }
            )
        return tuple(records)


def supply_authoritative_work_state_source_records(
    *,
    repo_root: Path | str,
    github_pr_records_output_path: Path | str,
    w10_report_records_output_path: Path | str,
    github_provider: GitHubPullRequestSourceProvider,
    w10_provider: W10ReportSourceProvider,
    now_iso: str | None = None,
) -> SourceRecordSupplyResult:
    """Materialize fresh GitHub/W10 source-record files outside the repo."""

    root = Path(repo_root).resolve()
    now = now_iso or datetime.now(timezone.utc).isoformat()
    github_path = Path(github_pr_records_output_path).resolve()
    w10_path = Path(w10_report_records_output_path).resolve()
    reasons: list[str] = []

    if _is_inside(github_path, root):
        reasons.append("github_pr_records_output_inside_repo")
    if _is_inside(w10_path, root):
        reasons.append("w10_report_records_output_inside_repo")
    if github_path == w10_path:
        reasons.append("source_record_outputs_must_be_distinct")

    github_records: tuple[Mapping[str, Any], ...] = ()
    w10_records: tuple[Mapping[str, Any], ...] = ()
    if not reasons:
        try:
            github_records = tuple(_valid_record(item) for item in github_provider.collect_pull_request_records(now_iso=now))
        except Exception as exc:  # noqa: BLE001 - provider errors fail closed.
            reasons.append(str(exc) or exc.__class__.__name__)
        try:
            w10_records = tuple(_valid_record(item) for item in w10_provider.collect_w10_report_records(now_iso=now))
        except Exception as exc:  # noqa: BLE001 - provider errors fail closed.
            reasons.append(str(exc) or exc.__class__.__name__)

    github_records = tuple(item for item in github_records if item)
    w10_records = tuple(item for item in w10_records if item)
    if not github_records:
        reasons.append("no_github_pr_records")
    if not w10_records:
        reasons.append("no_w10_report_records")

    if reasons:
        return _result(
            accepted=False,
            status=SOURCE_RECORD_SUPPLY_NOT_READY,
            now_iso=now,
            github_path=github_path,
            w10_path=w10_path,
            github_count=len(github_records),
            w10_count=len(w10_records),
            reasons=tuple(dict.fromkeys(reasons)),
        )

    _atomic_write_json(github_path, list(github_records))
    _atomic_write_json(w10_path, list(w10_records))
    return _result(
        accepted=True,
        status=SOURCE_RECORD_SUPPLY_APPLIED,
        now_iso=now,
        github_path=github_path,
        w10_path=w10_path,
        github_count=len(github_records),
        w10_count=len(w10_records),
        reasons=(),
    )


def _github_pr_to_record(item: Mapping[str, Any], *, now_iso: str) -> Mapping[str, Any]:
    slice_id = _extract_slice_id(
        " ".join(
            str(value or "")
            for value in (
                item.get("title"),
                _nested(item, "head", "ref"),
                item.get("body"),
            )
        )
    )
    if not slice_id:
        return {}
    labels = item.get("labels") if isinstance(item.get("labels"), list) else []
    return {
        "slice_id": slice_id,
        "status": "PR_OPEN" if str(item.get("state") or "").lower() == "open" else "CLOSED",
        "priority": _label_value(labels, prefix="P") or None,
        "lane": _label_value(labels, prefix="lane:") or None,
        "pr_number": item.get("number") if isinstance(item.get("number"), int) else None,
        "branch": _nested(item, "head", "ref"),
        "head_commit": _nested(item, "head", "sha"),
        "evidence_refs": [f"github:pr:{item.get('number')}", f"github:observed:{now_iso}"],
        "wsp15_score": {},
    }


def _valid_record(item: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(item, Mapping):
        return {}
    slice_id = _normalize_slice_id(item.get("slice_id"))
    if not slice_id:
        return {}
    record = dict(item)
    record["slice_id"] = slice_id
    record["status"] = str(item.get("status") or item.get("state") or "PROPOSED").strip().upper()
    return record


def _extract_slice_id(text: str) -> str:
    match = re.search(_SLICE_ID_RE, str(text or "").upper())
    return match.group(0) if match else ""


def _normalize_slice_id(value: object) -> str:
    return _extract_slice_id(str(value or ""))


def _label_value(labels: Sequence[Any], *, prefix: str) -> str:
    wanted = prefix.lower()
    for item in labels:
        name = item.get("name") if isinstance(item, Mapping) else item
        text = str(name or "").strip()
        lowered = text.lower()
        if wanted == "p" and lowered in {"p0", "p1", "p2", "p3", "p4"}:
            return lowered.upper()
        if lowered.startswith(wanted):
            return text.split(":", 1)[1].strip().upper() if ":" in text else text.strip().upper()
    return ""


def _nested(item: Mapping[str, Any], key: str, subkey: str) -> Any:
    value = item.get(key)
    return value.get(subkey) if isinstance(value, Mapping) else None


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write("\n")
        tmp_name = handle.name
    Path(tmp_name).replace(path)


def _digest(payload: Mapping[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _result(
    *,
    accepted: bool,
    status: str,
    now_iso: str,
    github_path: Path,
    w10_path: Path,
    github_count: int,
    w10_count: int,
    reasons: Tuple[str, ...],
) -> SourceRecordSupplyResult:
    payload = {
        "generated_at": now_iso,
        "github_pr_records_path": str(github_path),
        "w10_report_records_path": str(w10_path),
        "github_record_count": github_count,
        "w10_record_count": w10_count,
        "rejection_reasons": reasons,
    }
    receipt = SourceRecordSupplyReceipt(
        receipt_id=_digest(payload),
        generated_at=now_iso,
        github_pr_records_path=str(github_path),
        w10_report_records_path=str(w10_path),
        github_record_count=github_count,
        w10_record_count=w10_count,
        github_source_mode="github_rest_or_injected",
        w10_source_mode="work_ledger_projection_or_injected",
        rejection_reasons=reasons,
    )
    return SourceRecordSupplyResult(
        accepted=accepted,
        status=status,
        receipt=receipt,
        github_pr_records_path=str(github_path) if accepted else None,
        w10_report_records_path=str(w10_path) if accepted else None,
    )


__all__ = [
    "GitHubPullRequestSourceProvider",
    "GitHubRestPullRequestSourceProvider",
    "SOURCE_RECORD_SUPPLY_APPLIED",
    "SOURCE_RECORD_SUPPLY_NOT_READY",
    "SourceRecordSupplyReceipt",
    "SourceRecordSupplyResult",
    "W10ReportSourceProvider",
    "WorkLedgerProjectionW10ReportProvider",
    "supply_authoritative_work_state_source_records",
]
