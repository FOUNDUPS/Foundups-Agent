"""Current-checkout fixtures for authenticated RedDog conversation scope tests."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

from modules.ai_intelligence.ai_overseer.src.foundup_genesis.intake_auth_provider import (
    _make_session_token,
)
from modules.communication.moltbot_bridge.src.reddog_authority_runtime_store import (
    PrincipalAuthorityRecord,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_authentication import (
    authenticate_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_grounded_target_assignment_continuity import (
    canonical_digest,
)


ROOT = Path(__file__).resolve().parents[4]
NOW = 1_800_000_000
SECRET = "conversation-scope-test-secret-current"
PREVIOUS_SECRET = "conversation-scope-test-secret-previous"
FOCUS = "Assess the TRADE FoundUp runtime using current repository evidence."
SNAPSHOT_ID = "sha256:" + "8" * 64
SNAPSHOT_DIGEST = "sha256:" + "9" * 64
HOLO_GENERATION = "sha256:" + "a" * 64


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


class SqliteLayer:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def get_connection(self):
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> list[Any]:
        with self.get_connection() as connection:
            return list(connection.execute(query, params).fetchall())


class TestAgentDb:
    __test__ = False

    def __init__(self, path: Path) -> None:
        self.db = SqliteLayer(path)


class Resolver:
    def __init__(
        self,
        principal_id: str = "principal_012",
        *,
        public_key: str = "ed25519:principal-public-key",
        foundup_scope: tuple[str, ...] = ("trade",),
    ) -> None:
        self.record = PrincipalAuthorityRecord(
            principal_id=principal_id,
            principal_provider="test-provider",
            principal_public_key=public_key,
            repo_scope=("FOUNDUPS/Foundups-Agent",),
            foundup_scope=foundup_scope,
            verified_subject_digest=digest({"subject": principal_id}),
        )

    def resolve(self, principal_id: str, principal_provider: str):
        if (
            principal_id == self.record.principal_id
            and principal_provider == self.record.principal_provider
        ):
            return self.record
        return None


def session_token(
    principal_id: str = "principal_012", *, secret: str = SECRET
) -> str:
    return _make_session_token(secret, principal_id, NOW - 10, NOW + 1800)


def capability(
    *,
    resolver: Resolver | None = None,
    principal_id: str = "principal_012",
    secret: str = SECRET,
    previous_secret: str | None = None,
    transport: str = "editor",
    session_binding: str = "window:one",
    now_epoch: int = NOW,
):
    return authenticate_conversation_scope(
        session_token=session_token(principal_id, secret=secret),
        principal_provider="test-provider",
        transport=transport,
        session_binding=session_binding,
        principal_resolver=resolver or Resolver(principal_id),
        now_epoch=now_epoch,
        secret_provider=lambda: (secret, previous_secret),
    )


def target_receipt(foundup_id: str = "trade") -> dict[str, Any]:
    registry_path = ROOT / "modules/foundups/foundup_registry.json"
    schema_path = ROOT / "modules/foundups/foundup_registry.schema.json"
    registry_bytes, schema_bytes = registry_path.read_bytes(), schema_path.read_bytes()
    registry = json.loads(registry_bytes)
    entity = next(item for item in registry["entities"] if item["foundup_id"] == foundup_id)
    manifest_path = ROOT / entity["manifest_path"]
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    evidence = [
        {"path": "modules/foundups/foundup_registry.json", "content_digest": digest(registry_bytes)},
        {"path": "modules/foundups/foundup_registry.schema.json", "content_digest": digest(schema_bytes)},
        {"path": entity["manifest_path"], "content_digest": digest(manifest_bytes)},
    ]
    payload = {
        "schema_version": "registered_foundup_target_receipt.v1",
        "applied": True,
        "passed": True,
        "rejection_reasons": [],
        "foundup_id": foundup_id,
        "registry_digest": digest(registry_bytes),
        "registry_schema_digest": digest(schema_bytes),
        "registry_entity_digest": digest(entity),
        "manifest_path": entity["manifest_path"],
        "evidence_digests": evidence,
        "safe_mutation_surfaces": manifest["build_contract"]["safe_mutation_surface"],
        "repo_root_digest": digest(str(ROOT.resolve())),
        "repo_head_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "grants_authority": False,
    }
    return {**payload, "receipt_id": digest(payload)}


def grounding_receipt(foundup_id: str = "trade", *, focus: str = FOCUS) -> dict[str, Any]:
    target = target_receipt(foundup_id)
    coverage = [
        {"target": focus, "verdict": "SUFFICIENT", "evidence_refs": ["code:trade"]}
    ]
    typed = {
        "repo_file_targets": [],
        "semantic_targets": [focus],
        "external_research_targets": [],
        "quoted_reference_blocks_count": 0,
        "quoted_reference_blocks_digest": canonical_digest([]),
    }
    payload = {
        "schema_version": "reddog_grounded_target_receipt.v1",
        "source_surface": "editor_thin_client",
        "work_focus_digest": canonical_digest({"work_focus": focus}),
        "typed_targets": typed,
        "typed_targets_digest": canonical_digest(typed),
        "grounding_preflight_applied": True,
        "grounding_preflight_passed": True,
        "grounding_preflight_rejection_reasons": [],
        "grounding_target_universe_required": True,
        "repo_file_targets_count": 0,
        "semantic_targets_count": 1,
        "external_research_targets_count": 0,
        "quoted_reference_blocks_count": 0,
        "semantic_target_coverage": coverage,
        "semantic_target_coverage_digest": canonical_digest(
            {"semantic_target_coverage": coverage}
        ),
        "target_recall_ok": None,
        "required_targets_missing": [],
        "direct_read_paths": [],
        "holoindex_owner_query_ok": True,
        "holoindex_freshness": "CURRENT",
        "holoindex_generation_id": HOLO_GENERATION,
        "holoindex_freshness_receipt_digest": "sha256:" + "b" * 64,
        "holoindex_repo_head_sha": target["repo_head_sha"],
        "holoindex_query_receipt_id": "sha256:" + "c" * 64,
        "holoindex_index_gap_detected": False,
        "no_holoindex_reindex_performed": True,
        "foundup_id": foundup_id,
        "registered_foundup_target_receipt_id": target["receipt_id"],
        "registered_foundup_target": target,
    }
    return {**payload, "receipt_id": canonical_digest(payload)}


def item(label: str, kind: str = "operator_statement") -> dict[str, Any]:
    return {
        "item_id": digest({"label": label}),
        "kind": kind,
        "summary": label,
        "evidence_refs": ["code:trade"] if kind == "repository_fact" else [],
    }


def state_patch(parent_turn_id: str) -> Mapping[str, Any]:
    return {
        "turn_id": digest({"turn": "second"}),
        "parent_turn_id": parent_turn_id,
        "discussion_foundup_ids": ["trade"],
        "active_topic": "TRADE runtime",
        "current_objective": "Identify the next grounded implementation slice.",
        "accepted_decisions": [item("Use current repository evidence.", "repository_fact")],
        "rejected_options": [],
        "open_questions": [item("Which bounded slice is highest priority?", "unresolved")],
        "repository_evidence_refs": ["code:trade"],
    }


__all__ = [
    "FOCUS", "HOLO_GENERATION", "NOW", "PREVIOUS_SECRET", "ROOT", "SECRET",
    "SNAPSHOT_DIGEST", "SNAPSHOT_ID", "Resolver", "TestAgentDb", "capability",
    "digest", "grounding_receipt", "item", "session_token", "state_patch",
]
