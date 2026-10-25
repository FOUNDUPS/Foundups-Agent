"""Tamper, rotation, and static boundary tests for conversation scope."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

from modules.communication.moltbot_bridge.src.reddog_authenticated_conversation_scope_state import (
    advance_authenticated_conversation_scope,
    create_authenticated_conversation_scope,
    resume_authenticated_conversation_scope,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_contract import (
    canonical_digest,
    with_record_digest,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_store import (
    AgentDbConversationScopeStore,
)
from modules.communication.moltbot_bridge.src.reddog_conversation_scope_request import (
    ConversationScopeAdvanceRequest,
    ConversationScopeCreateRequest,
)
from modules.communication.moltbot_bridge.tests.reddog_conversation_scope_test_support import (
    FOCUS,
    HOLO_GENERATION,
    NOW,
    PREVIOUS_SECRET,
    ROOT,
    SECRET,
    SNAPSHOT_DIGEST,
    SNAPSHOT_ID,
    TestAgentDb,
    capability,
    digest,
    grounding_receipt,
    state_patch,
)


def _store(path: Path) -> AgentDbConversationScopeStore:
    return AgentDbConversationScopeStore(lambda: TestAgentDb(path))


def _create(path: Path):
    return create_authenticated_conversation_scope(
        store=_store(path), capability=capability(), repo_root=ROOT,
        request=ConversationScopeCreateRequest(
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            discussion_foundup_ids=("trade",), conversation_nonce="tamper-test",
            turn_id=digest({"turn": "first"}), active_topic="TRADE runtime",
            current_objective="Ground the next slice.", source_snapshot_id=SNAPSHOT_ID,
            source_snapshot_digest=SNAPSHOT_DIGEST,
        ), now_epoch=NOW,
    )


def _resume(path: Path, conversation_id: str, proof):
    return resume_authenticated_conversation_scope(
        store=_store(path), capability=proof, conversation_id=conversation_id,
        expected_head_sha=grounding_receipt()["holoindex_repo_head_sha"],
        expected_holoindex_generation_id=HOLO_GENERATION,
        expected_source_snapshot_id=SNAPSHOT_ID,
        expected_source_snapshot_digest=SNAPSHOT_DIGEST, now_epoch=NOW + 3,
    )


def test_attacker_rehashing_record_and_revision_cannot_forge_mac(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    record = _store(path).load(created.conversation_id)["record"]
    forged = copy.deepcopy(record)
    forged["active_topic"] = "attacker-selected topic"
    state = {
        key: value for key, value in forged.items()
        if key not in {"revision_receipts", "record_auth_mac", "record_digest"}
    }
    receipt = dict(forged["revision_receipts"][-1])
    receipt["state_digest"] = canonical_digest(state)
    receipt.pop("receipt_id")
    receipt["receipt_id"] = canonical_digest(receipt)
    forged["revision_receipts"][-1] = receipt
    forged = with_record_digest(forged)
    with TestAgentDb(path).db.get_connection() as connection:
        connection.execute(
            "UPDATE reddog_conversation_scopes SET scope_json = ? WHERE conversation_id = ?",
            (json.dumps(forged, sort_keys=True, separators=(",", ":")), created.conversation_id),
        )
    assert _resume(path, created.conversation_id, capability()).accepted is False


def test_secret_rotation_reauthenticates_state_then_retires_old_key(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    current = _store(path).load(created.conversation_id)["record"]
    rotated = advance_authenticated_conversation_scope(
        store=_store(path),
        capability=capability(secret=PREVIOUS_SECRET, previous_secret=SECRET),
        repo_root=ROOT,
        request=ConversationScopeAdvanceRequest(
            conversation_id=created.conversation_id, expected_revision=0,
            work_focus=FOCUS, grounding_receipt=grounding_receipt(),
            state_patch=state_patch(current["turn_id"]),
            expected_source_snapshot_id=SNAPSHOT_ID,
            expected_source_snapshot_digest=SNAPSHOT_DIGEST,
        ), now_epoch=NOW + 2,
    )
    assert rotated.accepted is True
    assert _resume(
        path, created.conversation_id, capability(secret=PREVIOUS_SECRET)
    ).accepted is True
    assert _resume(path, created.conversation_id, capability(secret=SECRET)).accepted is False


def test_unknown_record_or_revision_fields_fail_before_disclosure(tmp_path: Path) -> None:
    path = tmp_path / "scope.sqlite"
    created = _create(path)
    record = _store(path).load(created.conversation_id)["record"]
    for mutation in ("record", "revision"):
        forged = copy.deepcopy(record)
        if mutation == "record":
            forged["attacker_field"] = "ignored-by-lenient-parser"
        else:
            forged["revision_receipts"][-1]["attacker_field"] = "ignored"
        forged = with_record_digest(forged)
        with TestAgentDb(path).db.get_connection() as connection:
            connection.execute(
                "UPDATE reddog_conversation_scopes SET scope_json = ? WHERE conversation_id = ?",
                (json.dumps(forged, sort_keys=True, separators=(",", ":")), created.conversation_id),
            )
        assert _resume(path, created.conversation_id, capability()).accepted is False
        with TestAgentDb(path).db.get_connection() as connection:
            connection.execute(
                "UPDATE reddog_conversation_scopes SET scope_json = ? WHERE conversation_id = ?",
                (json.dumps(record, sort_keys=True, separators=(",", ":")), created.conversation_id),
            )


def test_production_modules_have_no_effect_or_raw_history_surfaces() -> None:
    module_paths = list(
        (ROOT / "modules/communication/moltbot_bridge/src").glob(
            "reddog_conversation_scope_*.py"
        )
    ) + [
        ROOT / "modules/communication/moltbot_bridge/src/reddog_authenticated_conversation_scope_state.py"
    ]
    forbidden_imports = {"subprocess", "requests", "httpx", "socket"}
    for path in module_paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        } | {
            str(node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not imported.intersection(forbidden_imports)
        assert "state.history" not in source
        assert "commit_all" not in source
        assert "enqueue" not in source
        calls = {
            str(node.func.attr).lower()
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        } | {
            str(node.func.id).lower()
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not calls.intersection({"reindex", "index_all", "refresh_index"})
