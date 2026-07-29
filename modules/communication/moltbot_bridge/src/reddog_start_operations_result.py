"""Wire schemas and typed terminal result for start operations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping


RESULT_SCHEMA = "reddog_start_operations_control_result.v1"
PROGRESS_SCHEMA = "reddog_start_operations_progress.v1"
EFFECT_EVIDENCE_LEVEL = "IMPLEMENTATION_BOUNDARY_ATTESTATION"


@dataclass(frozen=True)
class StartOperationsControlResult:
    schema_version: str
    response_id: str
    accepted: bool
    action: str
    control_request_id: str
    operations_profile_id: str
    intent_id: str
    cycle_id: str
    status: str
    repo_head_sha: str
    architect_action: str
    architect_next_slice: str
    determination_id: str
    task_status_counts: Mapping[str, int]
    duplicate_intent_reused: bool
    recovered_existing_cycle: bool
    deferred_holo_maintenance: bool
    rejection_reasons: tuple[str, ...]
    effect_evidence_level: str = EFFECT_EVIDENCE_LEVEL
    no_extension_fusion_call_performed: bool = True
    no_maintenance_performed: bool = True
    no_repo_mutation_performed: bool = True
    no_shell_command_executed: bool = True
    no_hermes_dispatch_performed: bool = True
    no_worktree_operation_performed: bool = True
    no_pr_created: bool = True
    no_merge_performed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def result_json(result: StartOperationsControlResult) -> str:
    return json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "EFFECT_EVIDENCE_LEVEL",
    "PROGRESS_SCHEMA",
    "RESULT_SCHEMA",
    "StartOperationsControlResult",
    "result_json",
]
