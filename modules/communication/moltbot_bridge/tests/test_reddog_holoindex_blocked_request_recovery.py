from __future__ import annotations

import ast
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

from holo_index.authority_worktree import (
    AUTHORITY_ROOT_HEAD_MISMATCH,
    HoloIndexAuthoritySelection,
)
from holo_index.query_receipt import build_query_receipt, canonical_semantic_evidence
from modules.communication.moltbot_bridge.src import (
    reddog_holoindex_blocked_request_recovery as recovery,
    reddog_holoindex_blocked_request_recovery_events as recovery_events,
)
from modules.communication.moltbot_bridge.src.reddog_holoindex_incident_repair_contract import (
    HoloIndexIncidentRepairReceipt,
    canonical_digest,
    seal_receipt,
)
from modules.infrastructure.idle_automation.src.holoindex_postmerge_contract import (
    CLAIM_AGENT_ID,
    COMPLETION_EVENT_PREFIX,
    INCIDENT_EVENT_TYPE,
    REQUEST_EVENT_PREFIX,
    SCHEMA_VERSION,
    SOURCE,
    TASK_PREFIX,
    _event_payload,
    incident_binding_event_id,
    incident_binding_event_payload,
)
from modules.infrastructure.database.src.agent_db import AgentDB
from modules.infrastructure.database.src.db_manager import DatabaseManager


HEAD = "a" * 40
ROOT_DIGEST = "sha256:" + "b" * 64
GENERATION = "sha256:" + "c" * 64
FRESHNESS = "sha256:" + "d" * 64
INCIDENT = "sha256:" + "e" * 64
STALE_HEAD = "f" * 40
QUERY = "audit HoloIndex"
TASK_ID = TASK_PREFIX + HEAD
NOW_MS = 1_786_083_200_000
REQUEST = {
    "command": "ask", "text": QUERY, "contextMode": "wsp_holo",
    "workerType": "architect", "effort": "high", "mode": "foundups_fusion",
    "useLastPacket": False,
}


def _durable_incident_binding() -> dict[str, str]:
    return {
        "schema_version": "reddog_holoindex_incident_repair.v2",
        "incident_kind": AUTHORITY_ROOT_HEAD_MISMATCH,
        "incident_id": INCIDENT,
        "workspace_repo_head_sha": HEAD,
        "observed_authority_head_sha": STALE_HEAD,
    }


class _Database:
    def __init__(self, *, completed: bool = True) -> None:
        self.reads: list[str] = []
        self.task = _task(completed)
        self.events = _events()
        self.lock = threading.Lock()

    def get_autonomous_task_by_id(self, task_id: str):
        self.reads.append("task:" + task_id)
        return self.task

    def get_coordination_event_by_id(self, event_id: str):
        self.reads.append("event:" + event_id)
        return self.events.get(event_id)

    def create_coordination_event(
        self, event_id, event_type, initiator_agent, target_agents, payload
    ):
        with self.lock:
            if event_id in self.events:
                return False
            self.events[event_id] = {
                "event_type": event_type, "initiator_agent": initiator_agent,
                "target_agents": target_agents, "payload": payload,
            }
            return True


def _task(completed: bool) -> dict:
    return {
        "status": "completed" if completed else "executing",
        "assigned_to": CLAIM_AGENT_ID,
        "required_skills": ["holo-search"],
        "context": {
            "schema_version": SCHEMA_VERSION,
            "source": SOURCE,
            "target_repo_head_sha": HEAD,
            "authority_root_digest": ROOT_DIGEST,
            "request_event_id": REQUEST_EVENT_PREFIX + HEAD,
        },
    }


def _events() -> dict[str, dict]:
    requested = _event_payload(
        target_repo_head_sha=HEAD, authority_root_digest=ROOT_DIGEST,
        status="REQUESTED",
    )
    completed = _event_payload(
        target_repo_head_sha=HEAD, authority_root_digest=ROOT_DIGEST,
        status="COMPLETED", generation_id=GENERATION,
        freshness_receipt_digest=FRESHNESS,
    )
    incident = _durable_incident_binding()
    incident_event_id = incident_binding_event_id(incident)
    return {
        REQUEST_EVENT_PREFIX + HEAD: {
            "event_id": REQUEST_EVENT_PREFIX + HEAD,
            "event_type": "holoindex_postmerge_maintenance",
            "initiator_agent": "wre", "target_agents": [CLAIM_AGENT_ID],
            "payload": requested,
        },
        incident_event_id: {
            "event_id": incident_event_id,
            "event_type": INCIDENT_EVENT_TYPE,
            "initiator_agent": "wre",
            "target_agents": [CLAIM_AGENT_ID],
            "payload": incident_binding_event_payload(
                incident_binding=incident,
                target_repo_head_sha=HEAD,
                authority_root_digest=ROOT_DIGEST,
            ),
        },
        COMPLETION_EVENT_PREFIX + HEAD: {"payload": completed},
    }


def _selection(root: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        True, root, HEAD, HEAD, ROOT_DIGEST, False, "workspace_root"
    )


def _stale_selection(root: Path) -> HoloIndexAuthoritySelection:
    return HoloIndexAuthoritySelection(
        False,
        root,
        HEAD,
        STALE_HEAD,
        ROOT_DIGEST,
        False,
        "deterministic_sibling",
        (AUTHORITY_ROOT_HEAD_MISMATCH,),
    )


def _incident() -> dict:
    return seal_receipt(HoloIndexIncidentRepairReceipt(
        accepted=True,
        status="QUEUED",
        incident_kind=AUTHORITY_ROOT_HEAD_MISMATCH,
        incident_id=INCIDENT,
        task_id=TASK_ID,
        request_event_id=REQUEST_EVENT_PREFIX + HEAD,
        target_repo_head_sha=HEAD,
        workspace_repo_head_sha=HEAD,
        observed_authority_head_sha=STALE_HEAD,
        authority_root_digest=ROOT_DIGEST,
        maintenance_enqueued=True,
    )).to_dict()


def _binding() -> dict:
    created = NOW_MS - 1_000
    expires = created + recovery.MAX_AGE_MS
    request_digest = canonical_digest({
        "schema_version": recovery.REQUEST_SCHEMA, "request": REQUEST
    })
    return {
        "request": REQUEST, "request_digest": request_digest,
        "query_digest": canonical_digest({"query": QUERY}),
        "recovery_id": canonical_digest({
            "request_digest": request_digest,
            "incident_receipt_id": _incident()["receipt_id"],
        }),
        "created_at_epoch_ms": created, "expires_at_epoch_ms": expires,
    }


def _owner_result(**changes) -> dict:
    result = {
        "ok": True, "source": "holoindex_owner_service", "query": QUERY,
        "freshness": "CURRENT", "error": "", "index_gap_detected": False,
        "raw_result": {}, "no_holoindex_reindex_performed": True,
        "owner_attempts": 1, "repo_head_sha": HEAD,
        "repo_root_digest": ROOT_DIGEST, "freshness_generation_id": GENERATION,
        "freshness_receipt_digest": FRESHNESS, "workspace_repo_head_sha": HEAD,
        "authority_repo_head_sha": HEAD, "authority_repo_root_digest": ROOT_DIGEST,
        "workspace_overlay_present": False,
        "semantic_evidence_authority": "committed_head_only",
        "no_authority_worktree_mutation_performed": True,
    }
    result.update(changes)
    serialized, _, _ = canonical_semantic_evidence(result["raw_result"])
    result["semantic_evidence_json"] = serialized
    result["query_receipt"] = build_query_receipt(
        source="holoindex_owner_service", source_class="holoindex",
        query=QUERY, result=result, require_generation=True,
    )
    return result


def _inspect(monkeypatch, tmp_path: Path, *, database=None, owner=None, incident=None):
    monkeypatch.setattr(recovery, "resolve_holoindex_authority_root", _selection)
    database = database or _Database()
    binding = _binding()
    incident_value = incident or _incident()
    if incident is None:
        staged = recovery.stage_holo_blocked_request_recovery(
            repo_root=tmp_path, query=QUERY, incident_receipt=incident_value,
            **binding, now_epoch_ms=NOW_MS, db=database,
        )
        assert staged["status"] == recovery.STAGED
    return recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=incident_value,
        **binding, now_epoch_ms=NOW_MS, db=database,
        query_runner=lambda *_args, **_kwargs: owner or _owner_result(),
    )


def test_exact_existing_completion_and_current_owner_are_ready(monkeypatch, tmp_path):
    database = _Database()
    result = _inspect(monkeypatch, tmp_path, database=database)

    assert result["status"] == recovery.READY
    assert result["generation_id"] == GENERATION
    assert result["freshness_receipt_digest"] == FRESHNESS
    assert result["authority_effect"] == "none"
    assert result["no_holoindex_reindex_performed"] is True
    assert len(database.reads) == 8
    claim = database.events[result["claim_event_id"]]
    assert QUERY not in str(claim)
    assert claim["payload"]["request_digest"] == _binding()["request_digest"]


def test_tampered_incident_rejected_before_durable_reads(monkeypatch, tmp_path):
    database = _Database()
    incident = _incident()
    incident["task_id"] = "attacker-selected"

    result = _inspect(monkeypatch, tmp_path, database=database, incident=incident)

    assert result["reason"] == "recovery_incident_receipt_invalid"
    assert database.reads == []


def test_attacker_rehash_still_cannot_substitute_task(monkeypatch, tmp_path):
    incident = _incident()
    receipt = seal_receipt(HoloIndexIncidentRepairReceipt(
        **{**incident, "task_id": "attacker-selected", "receipt_id": "",
           "rejection_reasons": tuple(incident["rejection_reasons"])}
    )).to_dict()

    result = _inspect(monkeypatch, tmp_path, incident=receipt)

    assert result["status"] == recovery.REJECTED
    assert result["reason"] == "recovery_incident_receipt_invalid"


def test_incomplete_maintenance_waits_without_owner_query(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(recovery, "resolve_holoindex_authority_root", _selection)
    database = _Database(completed=False)
    binding = _binding()
    assert recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **binding, now_epoch_ms=NOW_MS, db=database,
    )["status"] == recovery.STAGED
    result = recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **binding, now_epoch_ms=NOW_MS, db=database,
        query_runner=lambda *_args, **_kwargs: called.append(True),
    )

    assert result["status"] == recovery.WAITING
    assert result["reason"] == "recovery_maintenance_not_completed"
    assert called == []


def test_stale_authority_can_stage_but_cannot_claim_before_refresh(
    monkeypatch, tmp_path
):
    database = _Database(completed=False)
    binding = _binding()
    monkeypatch.setattr(
        recovery, "resolve_holoindex_authority_root", _stale_selection
    )

    staged = recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path,
        query=QUERY,
        incident_receipt=_incident(),
        **binding,
        now_epoch_ms=NOW_MS,
        db=database,
    )
    claimed = recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path,
        query=QUERY,
        incident_receipt=_incident(),
        **binding,
        now_epoch_ms=NOW_MS,
        db=database,
        query_runner=lambda *_args, **_kwargs: _owner_result(),
    )

    assert staged["status"] == recovery.STAGED
    assert claimed["status"] == recovery.REJECTED
    assert claimed["reason"] == "recovery_authority_binding_changed"


def test_stale_stage_rejects_wrong_workspace_head_or_authority_digest(
    monkeypatch, tmp_path
):
    binding = _binding()
    for selection in (
        HoloIndexAuthoritySelection(
            False, tmp_path, "0" * 40, STALE_HEAD, ROOT_DIGEST, False,
            "deterministic_sibling", (AUTHORITY_ROOT_HEAD_MISMATCH,),
        ),
        HoloIndexAuthoritySelection(
            False, tmp_path, HEAD, STALE_HEAD, "sha256:" + "0" * 64,
            False, "deterministic_sibling",
            (AUTHORITY_ROOT_HEAD_MISMATCH,),
        ),
    ):
        monkeypatch.setattr(
            recovery,
            "resolve_holoindex_authority_root",
            lambda _root, value=selection: value,
        )
        result = recovery.stage_holo_blocked_request_recovery(
            repo_root=tmp_path,
            query=QUERY,
            incident_receipt=_incident(),
            **binding,
            now_epoch_ms=NOW_MS,
            db=_Database(completed=False),
        )
        assert result["status"] == recovery.REJECTED
        assert result["reason"] == "recovery_authority_binding_changed"


def test_stage_requires_exact_durable_maintenance_task_and_request(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(recovery, "resolve_holoindex_authority_root", _stale_selection)
    binding = _binding()
    for mutate in (
        lambda db: setattr(db, "task", None),
        lambda db: db.task["context"].update(source="attacker"),
        lambda db: db.task["context"].update(
            incident_binding=_durable_incident_binding()
        ),
        lambda db: db.task.update(assigned_to="attacker"),
        lambda db: db.events.pop(REQUEST_EVENT_PREFIX + HEAD),
        lambda db: db.events[REQUEST_EVENT_PREFIX + HEAD]["payload"].update(
            incident_binding=_durable_incident_binding()
        ),
        lambda db: db.events[REQUEST_EVENT_PREFIX + HEAD].update(
            initiator_agent="attacker"
        ),
        lambda db: db.events[REQUEST_EVENT_PREFIX + HEAD].update(
            target_agents=["attacker"]
        ),
        lambda db: db.events.pop(
            incident_binding_event_id(_durable_incident_binding())
        ),
        lambda db: db.events[
            incident_binding_event_id(_durable_incident_binding())
        ].update(initiator_agent="attacker"),
    ):
        database = _Database(completed=False)
        mutate(database)
        before = set(database.events)
        result = recovery.stage_holo_blocked_request_recovery(
            repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
            **binding, now_epoch_ms=NOW_MS, db=database,
        )
        assert result["status"] == recovery.REJECTED
        assert result["reason"] == "recovery_maintenance_request_invalid"
        assert set(database.events) == before


def test_rehashed_stale_head_substitution_lacks_durable_binding(
    monkeypatch, tmp_path
):
    substituted = "c" * 40
    monkeypatch.setattr(
        recovery, "resolve_holoindex_authority_root",
        lambda root: HoloIndexAuthoritySelection(
            False, root, HEAD, substituted, ROOT_DIGEST, False,
            "deterministic_sibling", (AUTHORITY_ROOT_HEAD_MISMATCH,),
        ),
    )
    forged = _incident()
    forged["observed_authority_head_sha"] = substituted
    forged["rejection_reasons"] = tuple(forged["rejection_reasons"])
    forged = seal_receipt(HoloIndexIncidentRepairReceipt(
        **{**forged, "receipt_id": ""}
    )).to_dict()
    binding = _binding()
    binding["recovery_id"] = canonical_digest({
        "request_digest": binding["request_digest"],
        "incident_receipt_id": forged["receipt_id"],
    })
    database = _Database(completed=False)
    before = set(database.events)

    result = recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=forged,
        **binding, now_epoch_ms=NOW_MS, db=database,
    )

    assert result["status"] == recovery.REJECTED
    assert result["reason"] == "recovery_maintenance_request_invalid"
    assert set(database.events) == before


def test_forged_completion_payload_rejects(monkeypatch, tmp_path):
    database = _Database()
    database.events[COMPLETION_EVENT_PREFIX + HEAD]["payload"]["generation_id"] = (
        "sha256:" + "f" * 64
    )

    result = _inspect(monkeypatch, tmp_path, database=database)

    assert result["status"] == recovery.REJECTED
    assert result["reason"] == "recovery_maintenance_completion_invalid"


def test_current_unrelated_generation_waits(monkeypatch, tmp_path):
    owner = _owner_result(freshness_generation_id="sha256:" + "f" * 64)
    owner["query_receipt"] = build_query_receipt(
        source="holoindex_owner_service", source_class="holoindex",
        query=QUERY, result=owner, require_generation=True,
    )

    result = _inspect(monkeypatch, tmp_path, owner=owner)

    assert result["status"] == recovery.WAITING
    assert result["reason"] == "recovery_completion_generation_not_active"


def test_default_owner_runner_is_used_without_injection(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "resolve_holoindex_authority_root", _selection)
    monkeypatch.setitem(sys.modules, "scripts.reddog_holoindex_owner_query_once", SimpleNamespace(
        query_once=lambda *_args, **_kwargs: _owner_result()
    ))
    database = _Database()
    binding = _binding()
    assert recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **binding, now_epoch_ms=NOW_MS, db=database,
    )["status"] == recovery.STAGED
    result = recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **binding, now_epoch_ms=NOW_MS, db=database,
    )

    assert result["status"] == recovery.READY


def test_concurrent_claims_admit_exactly_one(monkeypatch, tmp_path):
    database = _Database()
    monkeypatch.setattr(recovery, "resolve_holoindex_authority_root", _selection)
    binding = _binding()
    assert recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **binding, now_epoch_ms=NOW_MS, db=database,
    )["status"] == recovery.STAGED

    def run():
        return recovery.admit_holo_blocked_request_recovery(
            repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
            **binding, now_epoch_ms=NOW_MS, db=database,
            query_runner=lambda *_args, **_kwargs: _owner_result(),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(item["status"] for item in executor.map(lambda _n: run(), range(2)))
    assert statuses == [recovery.READY, recovery.REJECTED]


def test_real_agentdb_clients_enforce_one_claim(tmp_path, monkeypatch):
    monkeypatch.setenv("FOUNDUPS_DB_ENGINE", "sqlite")
    monkeypatch.setenv("FOUNDUPS_DB_PATH", str(tmp_path / "claim.db"))
    DatabaseManager.reset_for_tests()
    try:
        clients = (AgentDB(), AgentDB())
        receipt = seal_receipt(HoloIndexIncidentRepairReceipt(
            accepted=True, status="QUEUED",
            incident_kind=AUTHORITY_ROOT_HEAD_MISMATCH, incident_id=INCIDENT,
            task_id=TASK_ID, request_event_id=REQUEST_EVENT_PREFIX + HEAD,
            target_repo_head_sha=HEAD, workspace_repo_head_sha=HEAD,
            observed_authority_head_sha=STALE_HEAD,
            authority_root_digest=ROOT_DIGEST, maintenance_enqueued=True,
        ))
        binding = _binding()
        stage_payload = recovery._stage_payload(
            receipt=receipt, recovery_id=binding["recovery_id"],
            request_digest=binding["request_digest"],
            query_digest=binding["query_digest"],
            created_at_epoch_ms=binding["created_at_epoch_ms"],
            expires_at_epoch_ms=binding["expires_at_epoch_ms"],
        )
        assert recovery_events.stage_once(clients[0], stage_payload)[0] == recovery.STAGED
        payload = recovery_events.build_claim_payload(
            stage_payload=stage_payload, generation_id=GENERATION,
            freshness_receipt_digest=FRESHNESS,
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            statuses = sorted(executor.map(
                lambda database: recovery_events.claim_once(
                    database, stage_payload, payload
                )[0], clients
            ))
        assert statuses == [recovery.READY, recovery.REJECTED]
    finally:
        DatabaseManager.reset_for_tests()


def test_invalid_query_and_schema_fail_before_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(
        recovery, "resolve_holoindex_authority_root",
        lambda _root: (_ for _ in ()).throw(AssertionError("must not select")),
    )
    assert recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query="", incident_receipt=_incident(),
        **_binding(), now_epoch_ms=NOW_MS, db=_Database()
    )["status"] == recovery.REJECTED
    assert recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt={"accepted": True},
        **_binding(), now_epoch_ms=NOW_MS, db=_Database(),
    )["status"] == recovery.REJECTED


def test_tampered_or_expired_request_binding_fails_before_selection(monkeypatch, tmp_path):
    monkeypatch.setattr(
        recovery, "resolve_holoindex_authority_root",
        lambda _root: (_ for _ in ()).throw(AssertionError("must not select")),
    )
    tampered = _binding()
    tampered["request"] = {**REQUEST, "mode": "exec"}
    assert recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **tampered, now_epoch_ms=NOW_MS, db=_Database(),
    )["reason"] == "recovery_request_binding_invalid"
    expired = _binding()
    assert recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **expired, now_epoch_ms=expired["expires_at_epoch_ms"], db=_Database(),
    )["reason"] == "recovery_request_binding_invalid"


def test_restamped_or_rehashed_request_lacks_original_stage_binding(monkeypatch, tmp_path):
    monkeypatch.setattr(recovery, "resolve_holoindex_authority_root", _selection)
    database = _Database()
    binding = _binding()
    assert recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **binding, now_epoch_ms=NOW_MS, db=database,
    )["status"] == recovery.STAGED

    restamped = {**binding, "created_at_epoch_ms": binding["created_at_epoch_ms"] + 500}
    restamped["expires_at_epoch_ms"] = restamped["created_at_epoch_ms"] + recovery.MAX_AGE_MS
    assert restamped["recovery_id"] == binding["recovery_id"]
    assert recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **restamped, now_epoch_ms=NOW_MS, db=database,
    )["reason"] == "recovery_stage_binding_missing"
    assert recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **restamped, now_epoch_ms=NOW_MS, db=database,
    )["status"] == recovery.STAGED

    modified_request = {**REQUEST, "mode": "exec"}
    modified_digest = canonical_digest({
        "schema_version": recovery.REQUEST_SCHEMA, "request": modified_request,
    })
    modified = {
        **binding, "request": modified_request, "request_digest": modified_digest,
        "recovery_id": canonical_digest({
            "request_digest": modified_digest,
            "incident_receipt_id": _incident()["receipt_id"],
        }),
    }
    assert recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **modified, now_epoch_ms=NOW_MS, db=database,
    )["reason"] == "recovery_stage_binding_missing"


def test_restaging_cannot_replay_a_claimed_request(monkeypatch, tmp_path):
    database = _Database()
    first = _inspect(monkeypatch, tmp_path, database=database)
    assert first["status"] == recovery.READY
    binding = _binding()
    restamped = {**binding, "created_at_epoch_ms": binding["created_at_epoch_ms"] + 500}
    restamped["expires_at_epoch_ms"] = restamped["created_at_epoch_ms"] + recovery.MAX_AGE_MS
    assert recovery.stage_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **restamped, now_epoch_ms=NOW_MS, db=database,
    )["status"] == recovery.STAGED
    replay = recovery.admit_holo_blocked_request_recovery(
        repo_root=tmp_path, query=QUERY, incident_receipt=_incident(),
        **restamped, now_epoch_ms=NOW_MS, db=database,
        query_runner=lambda *_args, **_kwargs: _owner_result(),
    )
    assert replay["status"] == recovery.REJECTED
    assert replay["reason"] == "recovery_already_claimed"


def test_runtime_is_read_only_and_within_wsp62_boundaries():
    source_path = Path(__file__).parents[1] / "src" / "reddog_holoindex_blocked_request_recovery.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        alias.name.split(".")[0] for node in ast.walk(tree)
        if isinstance(node, ast.Import) for alias in node.names
    }
    assert imported.isdisjoint({"subprocess", "socket", "requests", "sqlite3", "openai"})
    assert "PatternMemory" not in source
    assert "reindex(" not in source.lower()
    assert len(source.splitlines()) <= 300
    assert all(
        node.end_lineno - node.lineno + 1 <= 50 for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    event_source = (source_path.parent / "reddog_holoindex_blocked_request_recovery_events.py").read_text(encoding="utf-8")
    event_tree = ast.parse(event_source)
    assert len(event_source.splitlines()) <= 200
    assert all(
        node.end_lineno - node.lineno + 1 <= 50 for node in ast.walk(event_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
