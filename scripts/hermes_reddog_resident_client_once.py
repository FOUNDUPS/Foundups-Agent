#!/usr/bin/env python3
"""One-shot Hermes instrument bridge to the canonical resident RedDog client.

The host must provide REDDOG_AUTHENTICATED_PRINCIPAL_ID from its authenticated
channel/session. A principal value inside the request body is never authority.
Input and output are one bounded JSON document. This bridge adds no Hermes
model, shell, repository-write, worktree, PR, merge, or HoloIndex-indexing path.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.foundups.agent.src.hermes_reddog_resident_client_adapter import (  # noqa: E402
    HermesRedDogResidentClientAdapter,
)


MAX_INPUT_BYTES = 256_000


def _result(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    principal = str(os.getenv("REDDOG_AUTHENTICATED_PRINCIPAL_ID", "")).strip()
    if not principal:
        return _reject("authenticated_principal_missing")
    authorized_foundups = tuple(
        dict.fromkeys(
            item.strip()
            for item in str(os.getenv("REDDOG_AUTHORIZED_FOUNDUP_IDS", "")).split(",")
            if item.strip()
        )
    )
    if not authorized_foundups:
        return _reject("authorized_foundup_scope_missing")
    root_text = str(os.getenv("FOUNDUPS_REPO_ROOT", "")).strip()
    repo_root = Path(root_text).resolve() if root_text else REPO_ROOT
    runtime_defaults = {
        key: value
        for key, value in {
            "work_state_path": str(os.getenv("REDDOG_AUTHORITATIVE_WORK_STATE_PATH", "")).strip(),
            "holoindex_receipt_path": str(os.getenv("HOLOINDEX_FRESHNESS_RECEIPT", "")).strip(),
            "holoindex_ssd_path": str(os.getenv("HOLOINDEX_SSD_PATH", "")).strip(),
        }.items()
        if value
    }
    try:
        adapter = HermesRedDogResidentClientAdapter(
            repo_root=repo_root,
            authenticated_principal_id=principal,
            authorized_foundup_ids=authorized_foundups,
            runtime_defaults=runtime_defaults,
        )
        receipt = adapter.handle(payload)
    except Exception as exc:
        return _reject("hermes_reddog_bridge_failed", error_class=type(exc).__name__)
    return receipt.to_dict()


def _read_payload() -> Mapping[str, Any] | None:
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return {"_bridge_error": "input_too_large"}
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"_bridge_error": "invalid_json"}
    return value if isinstance(value, Mapping) else {"_bridge_error": "payload_not_mapping"}


def _reject(reason: str, *, error_class: str = "") -> dict[str, Any]:
    return {
        "schema_version": "hermes_reddog_resident_bridge_rejection.v1",
        "accepted": False,
        "rejection_reasons": [reason],
        "error_class": error_class,
        "canonical_reddog_authority_used": False,
        "hermes_is_transport_only": True,
        "no_hermes_model_invoked": True,
        "no_hermes_execution_performed": True,
        "no_shell_command_executed": True,
        "no_repo_mutation_performed": True,
        "no_holoindex_reindex_performed": True,
        "no_worktree_operation_performed": True,
        "no_pr_created": True,
        "no_merge_performed": True,
    }


def main() -> int:
    payload = _read_payload()
    if isinstance(payload, Mapping) and payload.get("_bridge_error"):
        output = _reject(str(payload["_bridge_error"]))
    else:
        output = _result(payload)
    sys.stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
