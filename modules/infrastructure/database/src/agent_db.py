#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

WSP 78: Agent Memory Database
Shared agent memory and state management.
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional

from .db_manager import DatabaseManager


_ASSURANCE_REQUIRED_FIELDS = (
    "reservation_id",
    "work_order_id",
    "queue_item_id",
    "author_task_id",
    "author_principal_id",
    "verifier_task_id",
    "verifier_principal_id",
    "capability",
    "worker_runtime",
    "operational_snapshot_id",
    "wsp15_allocation_receipt_id",
    "lease_id",
    "reserved_at",
    "expires_at",
)

_POSTMERGE_CLAIM_KEYS = frozenset(
    {
        "claim_id",
        "claim_binding_digest",
        "claim_expires_at",
    }
)


def _postmerge_claim_binding_digest(
    *,
    task_id: str,
    agent_id: str,
    context: Mapping[str, Any],
) -> str:
    base_context = {
        str(key): value
        for key, value in context.items()
        if key not in _POSTMERGE_CLAIM_KEYS
    }
    payload = {
        "task_id": task_id,
        "agent_id": agent_id,
        "context": base_context,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
_ASSURANCE_REQUEST_SCHEMA_VERSION = "reddog_assurance_capacity_request.v1"
_ASSURANCE_MAX_LEASE = timedelta(hours=6)
_ASSURANCE_MAX_RENEWALS = 3
_ASSURANCE_TERMINAL_STATUSES = {
    "ACCEPT",
    "REJECT",
    "VERIFIED",
    "FAILED",
    "CANCELLED",
}
_ASSURANCE_VERIFIER_ROLE = "independent_slice_verifier"


class _AssuranceReservationRejected(Exception):
    """Internal rollback signal for expected assurance-admission rejection."""

    def __init__(self, *reasons: str):
        super().__init__(",".join(reasons))
        self.reasons = tuple(reasons)


def _parse_assurance_utc_timestamp(value: Any, field_name: str) -> tuple[datetime, str]:
    """Parse an aware timestamp and return a canonical UTC ISO value."""
    text = str(value or "").strip()
    if not text:
        raise _AssuranceReservationRejected(f"missing_{field_name}")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _AssuranceReservationRejected(f"invalid_{field_name}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _AssuranceReservationRejected(f"{field_name}_not_utc_aware")
    normalized = parsed.astimezone(timezone.utc)
    return normalized, normalized.isoformat().replace("+00:00", "Z")


def _assurance_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_sha256_digest(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text.removeprefix("sha256:")
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _signed_worker_finalization_binding(
    task_id: str,
    claim: Any,
    use: Any,
) -> Optional[tuple[str, Dict[str, Any], Dict[str, Any]]]:
    if not isinstance(claim, Mapping) or not isinstance(use, Mapping):
        return None
    expected_claim = dict(claim)
    expected_use = dict(use)
    assigned_to = str(expected_claim.get("assigned_to") or "")
    if (
        str(expected_claim.get("task_id") or "") != task_id
        or str(expected_use.get("task_id") or "") != task_id
        or str(expected_claim.get("status") or "") != "CLAIMED"
        or str(expected_use.get("status") or "") != "CONSUMED"
        or str(expected_use.get("claim_receipt_id") or "")
        != str(expected_claim.get("receipt_id") or "")
        or str(expected_use.get("token_digest") or "")
        != str(expected_claim.get("token_digest") or "")
        or not assigned_to
        or not _valid_embedded_receipt(expected_claim)
        or not _valid_embedded_receipt(expected_use)
    ):
        return None
    return assigned_to, expected_claim, expected_use


def _valid_embedded_receipt(receipt: Mapping[str, Any]) -> bool:
    body = dict(receipt)
    receipt_id = str(body.pop("receipt_id", "") or "")
    return _is_sha256_digest(receipt_id) and receipt_id == _assurance_digest(body)


def _matching_signed_worker_execution_context(
    row: Any,
    assigned_to: str,
    expected_claim: Mapping[str, Any],
    expected_use: Mapping[str, Any],
) -> Optional[str]:
    if row is None:
        return None
    payload = dict(row)
    raw_context = str(payload.get("context") or "")
    try:
        stored_context = json.loads(raw_context)
    except (TypeError, ValueError):
        return None
    if (
        payload.get("status") != "executing"
        or str(payload.get("assigned_to") or "") != assigned_to
        or not isinstance(stored_context, dict)
        or stored_context.get("signed_worker_execution_claim") != expected_claim
        or stored_context.get("signed_worker_execution_use") != expected_use
    ):
        return None
    preclaim_context = dict(stored_context)
    preclaim_context.pop("signed_worker_execution_claim", None)
    preclaim_context.pop("signed_worker_execution_use", None)
    if expected_claim.get("context_digest") != _assurance_digest(preclaim_context):
        return None
    return raw_context


def _normalize_sha256_digest(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text.startswith("sha256:") else f"sha256:{text}"


def _assurance_result(
    *,
    accepted: bool,
    status: str,
    rejection_reasons: tuple[str, ...] | list[str] = (),
    reservation: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "accepted": accepted,
        "status": status,
        "rejection_reasons": list(rejection_reasons),
        "reservation": dict(reservation) if reservation is not None else None,
    }


class AgentDB:
    """
    Shared agent memory and state (WSP 78).

    Provides:
    - Agent awakening states
    - Shared memory patterns
    - Error learning (WSP 48)
    """

    def __init__(
        self,
        *,
        assurance_now_provider: Callable[[], datetime] | None = None,
    ):
        """Initialize agent database."""
        self.db = DatabaseManager()
        self._assurance_now_provider = (
            assurance_now_provider or (lambda: datetime.now(timezone.utc))
        )
        self._init_tables()

    def _init_tables(self) -> None:
        """Create agent database tables."""
        with self.db.get_connection() as conn:
            # Agent awakening states
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_awakening (
                    agent_id TEXT PRIMARY KEY,
                    consciousness_level TEXT,
                    last_koan TEXT,
                    awakening_timestamp DATETIME
                )
            ''')

            # Shared memory patterns
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT,
                    pattern_type TEXT,
                    pattern_data JSON,
                    learned_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Error learning (WSP 48)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_hash TEXT UNIQUE,
                    error_type TEXT,
                    solution JSON,
                    occurrences INTEGER DEFAULT 1
                )
            ''')

            # Breadcrumb trails (WSP 54 multi-agent coordination)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_breadcrumbs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action TEXT,
                    agent_id TEXT DEFAULT '0102',
                    query TEXT,
                    results JSON,
                    related_docs JSON,
                    contract_id TEXT,
                    task_id TEXT,
                    data JSON
                )
            ''')

            # Handoff contracts (multi-agent task assignment)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_contracts (
                    contract_id TEXT PRIMARY KEY,
                    task_description TEXT,
                    assigned_agent TEXT,
                    estimated_minutes INTEGER,
                    priority TEXT DEFAULT 'medium',
                    dependencies JSON,
                    deliverables JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deadline DATETIME,
                    completed_at DATETIME,
                    status TEXT DEFAULT 'active'
                )
            ''')

            # Collaboration signals (agent availability)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_collaboration_signals (
                    agent_id TEXT PRIMARY KEY,
                    collaboration_mode TEXT DEFAULT 'active',
                    available_until DATETIME,
                    skills_offered JSON,
                    current_focus TEXT,
                    last_ping DATETIME DEFAULT CURRENT_TIMESTAMP,
                    autonomy_level TEXT DEFAULT 'semi',
                    workload_capacity REAL DEFAULT 1.0
                )
            ''')

            # Coordination events (inter-agent communication)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_coordination_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT,
                    initiator_agent TEXT,
                    target_agents JSON,
                    payload JSON,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolution_status TEXT DEFAULT 'pending'
                )
            ''')

            # Autonomous tasks (discovered work items)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_autonomous_tasks (
                    task_id TEXT PRIMARY KEY,
                    description TEXT,
                    required_skills JSON,
                    estimated_complexity REAL,
                    priority_score REAL,
                    discovered_by TEXT DEFAULT 'autonomous_discovery',
                    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    context JSON,
                    assigned_to TEXT,
                    assigned_at DATETIME,
                    retry_not_before TIMESTAMP
                )

            ''')

            # Independent assurance capacity reservations.
            #
            # This is deliberately separate from collaboration signals. The
            # reservation and verifier-task claim must commit atomically.
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_independent_assurance_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    request_schema_version TEXT NOT NULL,
                    work_order_id TEXT NOT NULL,
                    queue_item_id TEXT NOT NULL,
                    author_task_id TEXT NOT NULL,
                    author_principal_id TEXT NOT NULL,
                    verifier_task_id TEXT NOT NULL UNIQUE,
                    verifier_principal_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    worker_runtime TEXT NOT NULL,
                    operational_snapshot_id TEXT NOT NULL,
                    wsp15_allocation_receipt_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL UNIQUE,
                    reserved_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    reservation_digest TEXT NOT NULL UNIQUE,
                    admission_reservation_digest TEXT NOT NULL,
                    admission_reserved_at TIMESTAMP NOT NULL,
                    renewal_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    terminal_receipt_id TEXT,
                    terminal_receipt_digest TEXT,
                    terminal_status TEXT,
                    completed_at TIMESTAMP,
                    revoked_at TIMESTAMP,
                    revocation_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (work_order_id, author_task_id),
                    FOREIGN KEY (author_task_id) REFERENCES agents_autonomous_tasks(task_id),
                    FOREIGN KEY (verifier_task_id) REFERENCES agents_autonomous_tasks(task_id)
                )
            ''')
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assurance_reservation_status "
                "ON agents_independent_assurance_reservations(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assurance_reservation_expiry "
                "ON agents_independent_assurance_reservations(expires_at)"
            )

            # Index refresh tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS index_refresh_tracking (
                    index_type TEXT PRIMARY KEY,
                    last_refresh DATETIME DEFAULT CURRENT_TIMESTAMP,
                    refresh_count INTEGER DEFAULT 0,
                    last_refresh_duration REAL,
                    total_entries_indexed INTEGER DEFAULT 0
                )
            ''')

            # ============================================================================
            # MODULE DOCUMENTATION REGISTRY (Qwen Module Doc Linker)
            # ============================================================================

            # Module registry
            conn.execute('''
                CREATE TABLE IF NOT EXISTS modules (
                    module_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT NOT NULL,
                    module_path TEXT NOT NULL UNIQUE,
                    module_domain TEXT NOT NULL,
                    linked_timestamp DATETIME,
                    linker_version TEXT DEFAULT '1.0.0'
                )
            ''')

            # Document registry
            conn.execute('''
                CREATE TABLE IF NOT EXISTS module_documents (
                    doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_id INTEGER NOT NULL,
                    doc_type TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    title TEXT,
                    purpose TEXT,
                    last_updated DATETIME,
                    FOREIGN KEY (module_id) REFERENCES modules(module_id) ON DELETE CASCADE
                )
            ''')

            # Document relationships (bidirectional links)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS document_relationships (
                    from_doc_id INTEGER NOT NULL,
                    to_doc_id INTEGER NOT NULL,
                    PRIMARY KEY (from_doc_id, to_doc_id),
                    FOREIGN KEY (from_doc_id) REFERENCES module_documents(doc_id) ON DELETE CASCADE,
                    FOREIGN KEY (to_doc_id) REFERENCES module_documents(doc_id) ON DELETE CASCADE
                )
            ''')

            # WSP implementations per module
            conn.execute('''
                CREATE TABLE IF NOT EXISTS module_wsp_implementations (
                    module_id INTEGER NOT NULL,
                    wsp_number TEXT NOT NULL,
                    PRIMARY KEY (module_id, wsp_number),
                    FOREIGN KEY (module_id) REFERENCES modules(module_id) ON DELETE CASCADE
                )
            ''')

            # Cross-references in documents
            conn.execute('''
                CREATE TABLE IF NOT EXISTS document_cross_references (
                    doc_id INTEGER NOT NULL,
                    reference_type TEXT NOT NULL,
                    reference_value TEXT NOT NULL,
                    PRIMARY KEY (doc_id, reference_type, reference_value),
                    FOREIGN KEY (doc_id) REFERENCES module_documents(doc_id) ON DELETE CASCADE
                )
            ''')

            # ============================================================================
            # SOCIAL MEDIA POST CAPTURE (Agent Post Review)
            # ============================================================================

            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_social_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT UNIQUE NOT NULL,
                    platform TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    identity TEXT,
                    target_url TEXT,
                    target_author TEXT,
                    content TEXT NOT NULL,
                    tone TEXT,
                    trigger_context TEXT,
                    status TEXT DEFAULT 'draft',
                    review_notes TEXT,
                    reviewed_at DATETIME,
                    posted_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata JSON
                )
            ''')

            # Create indexes for common queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_modules_name ON modules(module_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_modules_domain ON modules(module_domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_module ON module_documents(module_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_documents_type ON module_documents(doc_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_wsp_impl_wsp ON module_wsp_implementations(wsp_number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cross_ref_value ON document_cross_references(reference_value)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_social_posts_platform ON agents_social_posts(platform)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_social_posts_status ON agents_social_posts(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_social_posts_identity ON agents_social_posts(identity)')

            # ============================================================================
            # FINANCIAL TRANSACTIONS (Lobster.cash / pAVS)
            # ============================================================================

            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_id TEXT UNIQUE NOT NULL,
                    chain_tx_hash TEXT,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    purpose TEXT,
                    status TEXT DEFAULT 'pending',
                    metadata JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_status ON agents_transactions(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_transactions_currency ON agents_transactions(currency)')

        self._migrate_legacy_tables()

    def _get_table_columns(self, table_name: str) -> set[str]:
        """Return normalized column names for a table across supported backends."""
        columns = set()
        for row in self.db.get_table_info(table_name):
            column_name = row.get("name") or row.get("column_name")
            if column_name:
                columns.add(str(column_name))
        return columns

    def _ensure_table_columns(self, table_name: str, column_definitions: Dict[str, str]) -> None:
        """Add missing columns to legacy tables in a backward-compatible way."""
        existing_columns = self._get_table_columns(table_name)
        missing_columns = {
            column_name: definition
            for column_name, definition in column_definitions.items()
            if column_name not in existing_columns
        }
        if not missing_columns:
            return

        with self.db.get_connection() as conn:
            for column_name, definition in missing_columns.items():
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _migrate_legacy_tables(self) -> None:
        """Backfill columns expected by current AgentDB methods."""
        self._ensure_table_columns(
            "agents_autonomous_tasks",
            {
                "status": "TEXT DEFAULT 'pending'",
                "completed_at": "DATETIME",
                "origin_continuity_id": "TEXT",  # Gateway Continuity Layer
                "retry_not_before": "TIMESTAMP",
            },
        )
        self._ensure_table_columns(
            "agents_independent_assurance_reservations",
            {
                "admission_reservation_digest": "TEXT",
                "admission_reserved_at": "TEXT",
                "renewal_count": "INTEGER DEFAULT 0",
            },
        )

        # Gateway Continuity Layer: Add continuity metadata to breadcrumbs (WSP 60)
        self._ensure_table_columns(
            "agents_breadcrumbs",
            {
                "continuity_id": "TEXT",
                "runtime_surface": "TEXT",
                "sender_normalized": "TEXT",
                "parent_continuity_id": "TEXT",
            },
        )

        with self.db.get_connection() as conn:
            conn.execute(
                """
                UPDATE agents_independent_assurance_reservations
                SET admission_reservation_digest = reservation_digest
                WHERE admission_reservation_digest IS NULL
                   OR admission_reservation_digest = ''
                """
            )
            conn.execute(
                """
                UPDATE agents_independent_assurance_reservations
                SET admission_reserved_at = reserved_at
                WHERE admission_reserved_at IS NULL
                   OR admission_reserved_at = ''
                """
            )
            conn.execute("""
                UPDATE agents_autonomous_tasks
                SET status = 'pending'
                WHERE status IS NULL OR status = ''
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_status ON agents_autonomous_tasks(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_autonomous_tasks_assigned_to ON agents_autonomous_tasks(assigned_to)"
            )
            # Indexes for continuity queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_breadcrumbs_continuity_id ON agents_breadcrumbs(continuity_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_breadcrumbs_runtime_surface ON agents_breadcrumbs(runtime_surface)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_breadcrumbs_sender_normalized ON agents_breadcrumbs(sender_normalized)"
            )

    def record_awakening(self, agent_id: str, consciousness_level: str, koan: str = None) -> None:
        """Record agent awakening state."""
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO agents_awakening
                (agent_id, consciousness_level, last_koan, awakening_timestamp)
                VALUES (?, ?, ?, ?)
            ''', (agent_id, consciousness_level, koan, datetime.now().isoformat()))

    def get_awakening_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get awakening state for agent."""
        result = self.db.execute_query('''
            SELECT * FROM agents_awakening WHERE agent_id = ?
        ''', (agent_id,))

        if result:
            return dict(result[0])
        return None

    def learn_pattern(self, agent_id: str, pattern_type: str, pattern_data: Dict[str, Any]) -> int:
        """Store a learned pattern."""
        return self.db.execute_write('''
            INSERT INTO agents_memory (agent_id, pattern_type, pattern_data)
            VALUES (?, ?, ?)
        ''', (agent_id, pattern_type, json.dumps(pattern_data)))

    def get_patterns(self, agent_id: str = None, pattern_type: str = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve learned patterns."""
        query = "SELECT * FROM agents_memory WHERE 1=1"
        params = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)

        query += " ORDER BY learned_at DESC LIMIT ?"
        params.append(limit)

        return self.db.execute_query(query, tuple(params))

    def record_error(self, error_hash: str, error_type: str, solution: Dict[str, Any]) -> None:
        """Record error learning (WSP 48)."""
        with self.db.get_connection() as conn:
            # Try to update existing error
            updated = conn.execute('''
                UPDATE agents_errors
                SET occurrences = occurrences + 1
                WHERE error_hash = ?
            ''', (error_hash,)).rowcount

            # If no existing error, insert new one
            if updated == 0:
                conn.execute('''
                    INSERT INTO agents_errors
                    (error_hash, error_type, solution, occurrences)
                    VALUES (?, ?, ?, 1)
                ''', (error_hash, error_type, json.dumps(solution)))

    def get_error_solution(self, error_hash: str) -> Optional[Dict[str, Any]]:
        """Get solution for error."""
        result = self.db.execute_query('''
            SELECT * FROM agents_errors WHERE error_hash = ?
        ''', (error_hash,))

        if result:
            row = dict(result[0])
            row['solution'] = json.loads(row['solution'])
            return row
        return None

    # ============================================================================
    # BREADCRUMB TRAILS (WSP 54 Multi-Agent Coordination)
    # ============================================================================

    def add_breadcrumb(self, session_id: str, action: str, agent_id: str = "0102",
                      query: str = None, results: List[Dict] = None,
                      related_docs: List[str] = None, contract_id: str = None,
                      task_id: str = None, data: Dict[str, Any] = None,
                      continuity_id: str = None, runtime_surface: str = None,
                      sender_normalized: str = None, parent_continuity_id: str = None) -> int:
        """
        Add a breadcrumb to the trail.

        Args:
            session_id: Session identifier
            action: Action performed
            agent_id: Agent identifier (default: "0102")
            query: Query text if applicable
            results: Results data
            related_docs: Related document paths
            contract_id: Associated contract ID
            task_id: Associated task ID
            data: Additional data
            continuity_id: Cross-surface continuity identifier (Gateway Continuity Layer)
            runtime_surface: Runtime surface (cli, openclaw, messaging, etc.)
            sender_normalized: Normalized sender identity
            parent_continuity_id: Parent continuity ID for lineage tracking
        """
        return self.db.execute_write('''
            INSERT INTO agents_breadcrumbs
            (session_id, action, agent_id, query, results, related_docs, contract_id, task_id, data,
             continuity_id, runtime_surface, sender_normalized, parent_continuity_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, action, agent_id, query,
            json.dumps(results) if results else None,
            json.dumps(related_docs) if related_docs else None,
            contract_id, task_id,
            json.dumps(data) if data else None,
            continuity_id, runtime_surface, sender_normalized, parent_continuity_id
        ))

    def get_breadcrumbs(self, session_id: str = None, agent_id: str = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """Get breadcrumbs with optional filtering."""
        query = "SELECT * FROM agents_breadcrumbs WHERE 1=1"
        params = []

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        results = self.db.execute_query(query, tuple(params))

        # Parse JSON fields
        for row in results:
            for field in ['results', 'related_docs', 'data']:
                if row[field] and isinstance(row[field], str):
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        row[field] = None

        return results

    def get_recent_breadcrumb_agents(self, minutes: int = 120, limit: int = 5) -> List[str]:
        """Get distinct breadcrumb agent IDs within the time window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).replace(tzinfo=None)
        rows = self.db.execute_query(
            """
            SELECT agent_id, MAX(timestamp) AS last_seen
            FROM agents_breadcrumbs
            WHERE agent_id IS NOT NULL AND agent_id != ''
            GROUP BY agent_id
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (max(limit * 5, limit),)
        )

        recent_agents: List[str] = []
        for row in rows:
            last_seen = row.get("last_seen")
            if not last_seen:
                continue
            if isinstance(last_seen, str):
                parsed_last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            else:
                parsed_last_seen = last_seen
            if getattr(parsed_last_seen, "tzinfo", None) is not None:
                parsed_last_seen = parsed_last_seen.astimezone(timezone.utc).replace(tzinfo=None)
            if parsed_last_seen >= cutoff:
                recent_agents.append(row["agent_id"])
            if len(recent_agents) >= limit:
                break
        return recent_agents

    # ============================================================================
    # GATEWAY CONTINUITY LAYER - Cross-Surface Queries (WSP 60)
    # ============================================================================

    def get_breadcrumbs_by_continuity(
        self, continuity_id: str, include_children: bool = True, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get breadcrumbs by continuity ID across all surfaces.

        Args:
            continuity_id: The continuity ID to search for
            include_children: Include breadcrumbs with this as parent_continuity_id
            limit: Maximum results

        Returns:
            List of breadcrumbs ordered by timestamp (newest first)
        """
        if include_children:
            query = """
                SELECT * FROM agents_breadcrumbs
                WHERE continuity_id = ? OR parent_continuity_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """
            params = (continuity_id, continuity_id, limit)
        else:
            query = """
                SELECT * FROM agents_breadcrumbs
                WHERE continuity_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """
            params = (continuity_id, limit)

        results = self.db.execute_query(query, params)
        return self._parse_breadcrumb_json_fields(results)

    def get_breadcrumbs_by_surface(
        self, runtime_surface: str, minutes: int = 60, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent breadcrumbs from a specific runtime surface.

        Args:
            runtime_surface: The surface (cli, openclaw, messaging, etc.)
            minutes: Time window in minutes
            limit: Maximum results
        """
        # Use datetime format compatible with SQLite CURRENT_TIMESTAMP
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        results = self.db.execute_query(
            """
            SELECT * FROM agents_breadcrumbs
            WHERE runtime_surface = ? AND timestamp >= ?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (runtime_surface, cutoff, limit),
        )
        return self._parse_breadcrumb_json_fields(results)

    def get_breadcrumbs_by_sender(
        self, sender_normalized: str, minutes: int = 60, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent breadcrumbs from a specific normalized sender across all surfaces.

        Args:
            sender_normalized: Normalized sender identity
            minutes: Time window in minutes
            limit: Maximum results
        """
        # Use datetime format compatible with SQLite CURRENT_TIMESTAMP
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        results = self.db.execute_query(
            """
            SELECT * FROM agents_breadcrumbs
            WHERE sender_normalized = ? AND timestamp >= ?
            ORDER BY timestamp DESC LIMIT ?
            """,
            (sender_normalized, cutoff, limit),
        )
        return self._parse_breadcrumb_json_fields(results)

    def get_continuity_summary(
        self, continuity_id: str
    ) -> Dict[str, Any]:
        """
        Get a summary of activity for a continuity ID.

        Returns:
            Dict with surfaces, action counts, time range, and lineage info
        """
        rows = self.db.execute_query(
            """
            SELECT
                COUNT(*) as count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                GROUP_CONCAT(DISTINCT runtime_surface) as surfaces,
                GROUP_CONCAT(DISTINCT action) as actions
            FROM agents_breadcrumbs
            WHERE continuity_id = ? OR parent_continuity_id = ?
            """,
            (continuity_id, continuity_id),
        )
        if not rows or rows[0]["count"] == 0:
            return {"found": False, "continuity_id": continuity_id}

        row = rows[0]
        return {
            "found": True,
            "continuity_id": continuity_id,
            "breadcrumb_count": row["count"],
            "first_seen": row["first_seen"],
            "last_seen": row["last_seen"],
            "surfaces": row["surfaces"].split(",") if row["surfaces"] else [],
            "actions": row["actions"].split(",") if row["actions"] else [],
        }

    def get_cross_surface_activity(
        self, minutes: int = 30, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent work items that span multiple runtime surfaces.

        Detects cross-surface activity by:
        1. Same continuity_id across different surfaces
        2. Lineage-linked work (parent_continuity_id relationships)

        Returns work items that transitioned across surfaces (e.g., CLI -> OpenClaw -> Supervisor).

        Uses recursive CTE to resolve ultimate lineage root for multi-hop chains
        (e.g., OpenClaw -> Idle -> Supervisor all grouped under OpenClaw's root).

        Ancestry resolution follows parent links regardless of time window - only the
        final activity filter uses the time cutoff. This ensures old roots are still
        discovered when recent follow-up work references them.
        """
        # Use datetime format compatible with SQLite CURRENT_TIMESTAMP
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")

        # Recursive CTE to resolve ultimate lineage root for each continuity_id
        # IMPORTANT: continuity_map includes ALL breadcrumbs (no time filter) so ancestry
        # can be resolved even when roots are older than the activity window.
        # The time filter is applied only to the final grouping/reporting.
        results = self.db.execute_query(
            """
            WITH RECURSIVE
            -- Get distinct continuity mappings from ALL breadcrumbs (no time filter)
            -- This allows ancestry resolution to old roots that recent work references
            continuity_map AS (
                SELECT DISTINCT
                    continuity_id,
                    parent_continuity_id
                FROM agents_breadcrumbs
                WHERE continuity_id IS NOT NULL AND continuity_id != ''
            ),
            -- Recursively resolve ultimate root for each continuity_id
            lineage_roots AS (
                -- Base case: nodes without parents are their own root
                SELECT
                    continuity_id,
                    continuity_id as ultimate_root,
                    0 as depth
                FROM continuity_map
                WHERE parent_continuity_id IS NULL OR parent_continuity_id = ''

                UNION ALL

                -- Recursive case: follow parent chain
                SELECT
                    cm.continuity_id,
                    lr.ultimate_root,
                    lr.depth + 1
                FROM continuity_map cm
                JOIN lineage_roots lr ON cm.parent_continuity_id = lr.continuity_id
                WHERE cm.parent_continuity_id IS NOT NULL
                  AND cm.parent_continuity_id != ''
                  AND lr.depth < 10  -- Prevent infinite loops
            ),
            -- Get the deepest resolution for each continuity_id (ultimate root)
            resolved_roots AS (
                SELECT continuity_id, ultimate_root
                FROM lineage_roots
                GROUP BY continuity_id
                HAVING depth = MAX(depth)
            )
            -- Group RECENT breadcrumbs by ultimate root (time filter here only)
            SELECT
                COALESCE(rr.ultimate_root, b.continuity_id) as lineage_root,
                COUNT(DISTINCT b.runtime_surface) as surface_count,
                GROUP_CONCAT(DISTINCT b.runtime_surface) as surfaces,
                GROUP_CONCAT(DISTINCT b.continuity_id) as continuity_ids,
                MIN(b.timestamp) as started_at,
                MAX(b.timestamp) as last_activity
            FROM agents_breadcrumbs b
            LEFT JOIN resolved_roots rr ON b.continuity_id = rr.continuity_id
            WHERE b.continuity_id IS NOT NULL
              AND b.continuity_id != ''
              AND b.timestamp >= ?
            GROUP BY lineage_root
            HAVING surface_count > 1
            ORDER BY last_activity DESC
            LIMIT ?
            """,
            (cutoff, limit),
        )
        return [
            {
                "continuity_id": row["lineage_root"],  # Ultimate root of the lineage
                "lineage_root": row["lineage_root"],
                "continuity_ids": row["continuity_ids"].split(",") if row["continuity_ids"] else [],
                "surface_count": row["surface_count"],
                "surfaces": row["surfaces"].split(",") if row["surfaces"] else [],
                "started_at": row["started_at"],
                "last_activity": row["last_activity"],
            }
            for row in results
        ]

    def _parse_breadcrumb_json_fields(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse JSON fields in breadcrumb results."""
        for row in results:
            for field in ["results", "related_docs", "data"]:
                if row.get(field) and isinstance(row[field], str):
                    try:
                        row[field] = json.loads(row[field])
                    except json.JSONDecodeError:
                        row[field] = None
        return results

    # ============================================================================
    # HANDOFF CONTRACTS (Multi-Agent Task Assignment)
    # ============================================================================

    def create_contract(self, contract_id: str, task_description: str, assigned_agent: str,
                       estimated_minutes: int, priority: str = "medium",
                       dependencies: List[str] = None, deliverables: List[str] = None,
                       deadline: str = None) -> bool:
        """Create a new contract."""
        try:
            self.db.execute_write('''
                INSERT INTO agents_contracts
                (contract_id, task_description, assigned_agent, estimated_minutes, priority,
                 dependencies, deliverables, deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contract_id, task_description, assigned_agent, estimated_minutes, priority,
                json.dumps(dependencies) if dependencies else None,
                json.dumps(deliverables) if deliverables else None,
                deadline
            ))
            return True
        except Exception:
            return False

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get contract by ID."""
        result = self.db.execute_query('''
            SELECT * FROM agents_contracts WHERE contract_id = ?
        ''', (contract_id,))

        if result:
            contract = dict(result[0])
            # Parse JSON fields
            for field in ['dependencies', 'deliverables']:
                if contract[field] and isinstance(contract[field], str):
                    contract[field] = json.loads(contract[field])
            return contract
        return None

    def update_contract(self, contract_id: str, updates: Dict[str, Any]) -> bool:
        """Update contract fields."""
        if not updates:
            return False

        # Build dynamic update query
        set_parts = []
        params = []
        for field, value in updates.items():
            if field in ['dependencies', 'deliverables']:
                value = json.dumps(value)
            set_parts.append(f"{field} = ?")
            params.append(value)

        params.append(contract_id)  # WHERE clause

        query = f"UPDATE agents_contracts SET {', '.join(set_parts)} WHERE contract_id = ?"
        return self.db.execute_write(query, tuple(params)) > 0

    def complete_contract(self, contract_id: str) -> bool:
        """Mark contract as completed."""
        return self.update_contract(contract_id, {
            'status': 'completed',
            'completed_at': datetime.now().isoformat()
        })

    def get_active_contracts(self, agent_filter: str = None) -> List[Dict[str, Any]]:
        """Get active contracts, optionally filtered by assigned agent."""
        query = "SELECT * FROM agents_contracts WHERE status = 'active'"
        params = []

        if agent_filter:
            query += " AND assigned_agent = ?"
            params.append(agent_filter)

        query += " ORDER BY created_at DESC"

        results = self.db.execute_query(query, tuple(params))

        # Parse JSON fields
        for row in results:
            for field in ['dependencies', 'deliverables']:
                if row[field] and isinstance(row[field], str):
                    row[field] = json.loads(row[field])

        return results

    # ============================================================================
    # COLLABORATION SIGNALS (Agent Availability)
    # ============================================================================

    def signal_collaboration(self, agent_id: str, collaboration_mode: str = "active",
                           available_until: str = None, skills_offered: List[str] = None,
                           current_focus: str = "general", autonomy_level: str = "semi",
                           workload_capacity: float = 1.0) -> bool:
        """Signal collaboration readiness."""
        try:
            self.db.execute_write('''
                INSERT OR REPLACE INTO agents_collaboration_signals
                (agent_id, collaboration_mode, available_until, skills_offered,
                 current_focus, autonomy_level, workload_capacity, last_ping)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id, collaboration_mode, available_until,
                json.dumps(skills_offered) if skills_offered else None,
                current_focus, autonomy_level, workload_capacity,
                datetime.now().isoformat()
            ))
            return True
        except Exception:
            return False

    def get_collaborators(self, required_skills: List[str] = None) -> List[Dict[str, Any]]:
        """Get available collaborators, optionally filtered by skills."""
        query = """
            SELECT * FROM agents_collaboration_signals
            WHERE available_until > ?
        """
        params = [datetime.now().isoformat()]

        if required_skills:
            # Complex skill matching query
            skill_conditions = []
            for skill in required_skills:
                skill_conditions.append("skills_offered LIKE ?")
                params.append(f'%"{skill}"%')
            query += f" AND ({' OR '.join(skill_conditions)})"

        query += " ORDER BY workload_capacity DESC, last_ping DESC"

        results = self.db.execute_query(query, tuple(params))

        # Parse JSON fields
        for row in results:
            if row['skills_offered'] and isinstance(row['skills_offered'], str):
                row['skills_offered'] = json.loads(row['skills_offered'])

        return results

    # ============================================================================
    # COORDINATION EVENTS (Inter-Agent Communication)
    # ============================================================================

    def create_coordination_event(self, event_id: str, event_type: str,
                                initiator_agent: str, target_agents: List[str],
                                payload: Dict[str, Any]) -> bool:
        """Create a coordination event."""
        try:
            self.db.execute_write('''
                INSERT INTO agents_coordination_events
                (event_id, event_type, initiator_agent, target_agents, payload)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                event_id, event_type, initiator_agent,
                json.dumps(target_agents), json.dumps(payload)
            ))
            return True
        except Exception:
            return False

    def get_coordination_events(self, status: str = "pending", limit: int = 50) -> List[Dict[str, Any]]:
        """Get coordination events by status."""
        results = self.db.execute_query('''
            SELECT * FROM agents_coordination_events
            WHERE resolution_status = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (status, limit))

        # Parse JSON fields
        for row in results:
            for field in ['target_agents', 'payload']:
                if row[field] and isinstance(row[field], str):
                    row[field] = json.loads(row[field])

        return results

    def get_coordination_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get one coordination event with parsed JSON fields."""
        results = self.db.execute_query(
            "SELECT * FROM agents_coordination_events WHERE event_id = ?",
            (event_id,),
        )
        if not results:
            return None
        row = dict(results[0])
        for field in ["target_agents", "payload"]:
            if row.get(field) and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except json.JSONDecodeError:
                    row[field] = None
        return row

    def resolve_coordination_event(self, event_id: str, status: str = "completed") -> bool:
        """Mark coordination event as resolved."""
        return self.db.execute_write('''
            UPDATE agents_coordination_events
            SET resolution_status = ?
            WHERE event_id = ?
        ''', (status, event_id)) > 0

    # ============================================================================
    # AUTONOMOUS TASKS (Discovered Work Items)
    # ============================================================================

    def create_autonomous_task(self, task_id: str, description: str,
                             required_skills: List[str], estimated_complexity: float,
                             priority_score: float, context: Dict[str, Any] = None,
                             origin_continuity_id: str = None) -> bool:
        """Create an autonomous task.

        Args:
            task_id: Unique task identifier.
            description: Task description.
            required_skills: List of required skill names.
            estimated_complexity: Complexity score (0.0-1.0).
            priority_score: Priority score (higher = more urgent).
            context: Optional context dict for task.
            origin_continuity_id: Optional continuity ID from the work that discovered this task.
                                  Enables background correlation when task is executed later.
        """
        try:
            self.db.execute_write('''
                INSERT OR REPLACE INTO agents_autonomous_tasks
                (task_id, description, required_skills, estimated_complexity,
                 priority_score, context, origin_continuity_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id, description, json.dumps(required_skills),
                estimated_complexity, priority_score,
                json.dumps(context) if context else None,
                origin_continuity_id
            ))
            return True
        except Exception:
            return False

    def create_autonomous_task_if_absent(
        self,
        task_id: str,
        description: str,
        required_skills: List[str],
        estimated_complexity: float,
        priority_score: float,
        context: Dict[str, Any] = None,
        origin_continuity_id: str = None,
    ) -> bool:
        """Insert a task without replacing concurrent or already-claimed state."""
        try:
            return self.db.execute_write(
                """
                INSERT OR IGNORE INTO agents_autonomous_tasks
                (task_id, description, required_skills, estimated_complexity,
                 priority_score, context, origin_continuity_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    description,
                    json.dumps(required_skills),
                    estimated_complexity,
                    priority_score,
                    json.dumps(context) if context else None,
                    origin_continuity_id,
                ),
            ) > 0
        except Exception:
            return False

    def get_autonomous_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a single autonomous task by ID.

        Args:
            task_id: The task identifier.

        Returns:
            Task dict with parsed JSON fields, or None if not found.
        """
        results = self.db.execute_query('''
            SELECT * FROM agents_autonomous_tasks WHERE task_id = ?
        ''', (task_id,))

        if not results:
            return None

        row = dict(results[0])
        for field in ['required_skills', 'context']:
            if row.get(field) and isinstance(row[field], str):
                row[field] = json.loads(row[field])

        return row

    def get_autonomous_tasks(self, status: str = "pending", limit: int = 50) -> List[Dict[str, Any]]:
        """Get autonomous tasks by status."""
        results = self.db.execute_query('''
            SELECT * FROM agents_autonomous_tasks
            WHERE status = ?
            ORDER BY priority_score DESC, discovered_at DESC LIMIT ?
        ''', (status, limit))

        # Parse JSON fields
        for row in results:
            for field in ['required_skills', 'context']:
                if row[field] and isinstance(row[field], str):
                    row[field] = json.loads(row[field])

        return results

    def assign_autonomous_task(self, task_id: str, agent_id: str) -> bool:
        """Atomically claim one pending autonomous task for an agent."""
        return self.db.execute_write('''
            UPDATE agents_autonomous_tasks
            SET assigned_to = ?, assigned_at = ?, status = 'assigned'
            WHERE task_id = ? AND status = 'pending'
        ''', (agent_id, datetime.now().isoformat(), task_id)) > 0

    def claim_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        expected_source: str,
        expected_schema_version: str,
        expected_target_repo_head_sha: str,
        expected_authority_root_digest: str,
        lease_seconds: int = 7500,
    ) -> str:
        """Claim one exact-SHA task and return its immutable claim ID."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT status, assigned_to, context
                    FROM agents_autonomous_tasks
                    WHERE task_id = ?
                    """,
                    (task_id,),
                ).fetchone()
                if row is None:
                    return ""
                raw_context = str(row.get("context") or "")
                context = self._parse_task_context(dict(row))
                target_sha = str(context.get("target_repo_head_sha") or "")
                authority_digest = str(
                    context.get("authority_root_digest") or ""
                )
                if (
                    str(row.get("status") or "") != "pending"
                    or str(row.get("assigned_to") or "").strip()
                    or context.get("source") != expected_source
                    or context.get("schema_version") != expected_schema_version
                    or target_sha != expected_target_repo_head_sha
                    or task_id != f"holoindex_postmerge_refresh:{target_sha}"
                    or len(target_sha) != 40
                    or any(char not in "0123456789abcdef" for char in target_sha)
                    or authority_digest != expected_authority_root_digest
                    or not authority_digest.startswith("sha256:")
                    or len(authority_digest) != 71
                    or any(
                        char not in "0123456789abcdef"
                        for char in authority_digest[7:]
                    )
                    or lease_seconds < 1
                ):
                    return ""
                claim_id = "hpmc_" + uuid.uuid4().hex
                claim_digest = _postmerge_claim_binding_digest(
                    task_id=task_id,
                    agent_id=agent_id,
                    context=context,
                )
                now = datetime.now(timezone.utc)
                claimed_context = dict(context)
                claimed_context.update(
                    {
                        "claim_id": claim_id,
                        "claim_binding_digest": claim_digest,
                        "claim_expires_at": (
                            now + timedelta(seconds=lease_seconds)
                        ).isoformat(),
                    }
                )
                claimed = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET assigned_to = ?, assigned_at = ?, status = 'assigned',
                        context = ?
                    WHERE task_id = ?
                      AND status = 'pending'
                      AND (assigned_to IS NULL OR assigned_to = '')
                      AND context = ?
                    """,
                    (
                        agent_id,
                        now.isoformat(),
                        json.dumps(claimed_context),
                        task_id,
                        raw_context,
                    ),
                ).rowcount
                return claim_id if claimed == 1 else ""
        except Exception:
            return ""

    def start_holoindex_postmerge_execution(
        self,
        task_id: str,
        agent_id: str,
        *,
        claim_id: str,
        claim_binding_digest: str,
    ) -> bool:
        """Consume one exact claim before any post-merge authority effect."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT status, assigned_to, context
                    FROM agents_autonomous_tasks
                    WHERE task_id = ?
                    """,
                    (task_id,),
                ).fetchone()
                if row is None:
                    return False
                raw_context = str(row.get("context") or "")
                context = self._parse_task_context(dict(row))
                recomputed = _postmerge_claim_binding_digest(
                    task_id=task_id,
                    agent_id=agent_id,
                    context=context,
                )
                expires_raw = str(context.get("claim_expires_at") or "")
                try:
                    expires_at = datetime.fromisoformat(
                        expires_raw.replace("Z", "+00:00")
                    )
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                except ValueError:
                    return False
                if (
                    str(row.get("status") or "") != "assigned"
                    or str(row.get("assigned_to") or "") != agent_id
                    or context.get("claim_id") != claim_id
                    or context.get("claim_binding_digest")
                    != claim_binding_digest
                    or recomputed != claim_binding_digest
                    or datetime.now(timezone.utc) >= expires_at
                ):
                    return False
                started = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET status = 'executing'
                    WHERE task_id = ?
                      AND status = 'assigned'
                      AND assigned_to = ?
                      AND context = ?
                    """,
                    (task_id, agent_id, raw_context),
                ).rowcount
                return started == 1
        except Exception:
            return False

    def fail_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        claim_id: str,
        claim_binding_digest: str,
        status: str = "failed",
    ) -> bool:
        """Finalize a claimed post-merge task into a bounded failure state."""
        if status not in {"failed", "superseded"}:
            return False
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT status, assigned_to, context
                    FROM agents_autonomous_tasks
                    WHERE task_id = ?
                    """,
                    (task_id,),
                ).fetchone()
                if row is None:
                    return False
                raw_context = str(row.get("context") or "")
                context = self._parse_task_context(dict(row))
                if (
                    str(row.get("status") or "")
                    not in {"assigned", "executing"}
                    or str(row.get("assigned_to") or "") != agent_id
                    or context.get("claim_id") != claim_id
                    or context.get("claim_binding_digest")
                    != claim_binding_digest
                    or _postmerge_claim_binding_digest(
                        task_id=task_id,
                        agent_id=agent_id,
                        context=context,
                    )
                    != claim_binding_digest
                ):
                    return False
                finalized = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET status = ?, completed_at = ?
                    WHERE task_id = ?
                      AND status IN ('assigned', 'executing')
                      AND assigned_to = ?
                      AND context = ?
                    """,
                    (
                        status,
                        datetime.now(timezone.utc).isoformat(),
                        task_id,
                        agent_id,
                        raw_context,
                    ),
                ).rowcount
                return finalized == 1
        except Exception:
            return False

    def reclaim_expired_holoindex_postmerge_task(
        self,
        task_id: str,
        agent_id: str,
        *,
        expected_assigned_at: str,
    ) -> bool:
        """CAS one expired assignment into retryable failure."""
        return (
            self.db.execute_write(
                """
            UPDATE agents_autonomous_tasks
            SET status = 'failed', completed_at = ?
            WHERE task_id = ?
              AND status IN ('assigned', 'executing')
                  AND assigned_to = ?
                  AND assigned_at = ?
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                    agent_id,
                    expected_assigned_at,
                ),
            )
            == 1
        )

    def commit_holoindex_postmerge_completion(
        self,
        *,
        task_id: str,
        agent_id: str,
        request_event_id: str,
        request_payload_digest: str,
        completion_event_id: str,
        completion_payload: Dict[str, Any],
        claim_id: str,
        claim_binding_digest: str,
    ) -> bool:
        """Atomically publish post-merge proof and finalize its task/request."""
        try:
            with self.db.get_connection() as conn:
                task = conn.execute(
                    """
                    SELECT status, assigned_to, context
                    FROM agents_autonomous_tasks
                    WHERE task_id = ?
                    """,
                    (task_id,),
                ).fetchone()
                request = conn.execute(
                    """
                    SELECT resolution_status, payload
                    FROM agents_coordination_events
                    WHERE event_id = ?
                    """,
                    (request_event_id,),
                ).fetchone()
                existing = conn.execute(
                    """
                    SELECT payload
                    FROM agents_coordination_events
                    WHERE event_id = ?
                    """,
                    (completion_event_id,),
                ).fetchone()
                expected_payload_json = json.dumps(completion_payload)
                task_context_raw = (
                    str(task.get("context") or "")
                    if task is not None
                    else ""
                )
                request_payload_raw = (
                    str(request.get("payload") or "")
                    if request is not None
                    else ""
                )
                task_context = (
                    self._parse_task_context(dict(task))
                    if task is not None
                    else {}
                )
                claim_valid = bool(
                    task is not None
                    and task_context.get("claim_id") == claim_id
                    and task_context.get("claim_binding_digest")
                    == claim_binding_digest
                    and _postmerge_claim_binding_digest(
                        task_id=task_id,
                        agent_id=agent_id,
                        context=task_context,
                    )
                    == claim_binding_digest
                )

                if existing is not None:
                    try:
                        existing_payload = json.loads(str(existing.get("payload") or ""))
                    except (TypeError, ValueError):
                        return False
                    return bool(
                        task is not None
                        and str(task.get("status") or "") == "completed"
                        and str(task.get("assigned_to") or "") == agent_id
                        and claim_valid
                        and request is not None
                        and str(request.get("resolution_status") or "") == "completed"
                        and existing_payload == completion_payload
                    )

                if (
                    task is None
                    or str(task.get("status") or "") != "executing"
                    or str(task.get("assigned_to") or "") != agent_id
                    or not claim_valid
                    or request is None
                    or str(request.get("resolution_status") or "") != "pending"
                ):
                    return False
                try:
                    request_payload = json.loads(str(request.get("payload") or ""))
                except (TypeError, ValueError):
                    return False
                if (
                    not isinstance(request_payload, dict)
                    or request_payload.get("payload_digest") != request_payload_digest
                ):
                    return False

                conn.execute(
                    """
                    INSERT INTO agents_coordination_events
                    (event_id, event_type, initiator_agent, target_agents, payload)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        completion_event_id,
                        "holoindex_postmerge_maintenance_completed",
                        agent_id,
                        json.dumps(["wre"]),
                        expected_payload_json,
                    ),
                )
                request_count = conn.execute(
                    """
                    UPDATE agents_coordination_events
                    SET resolution_status = 'completed'
                    WHERE event_id = ?
                      AND resolution_status = 'pending'
                      AND payload = ?
                    """,
                    (request_event_id, request_payload_raw),
                ).rowcount
                task_count = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET completed_at = ?, status = 'completed'
                    WHERE task_id = ?
                      AND status = 'executing'
                      AND assigned_to = ?
                      AND context = ?
                    """,
                    (
                        datetime.now().isoformat(),
                        task_id,
                        agent_id,
                        task_context_raw,
                    ),
                ).rowcount
                if request_count != 1 or task_count != 1:
                    raise RuntimeError("holoindex_postmerge_completion_conflict")
                return True
        except Exception:
            return False

    def complete_autonomous_task(self, task_id: str) -> bool:
        """Mark autonomous task as completed."""
        return self.db.execute_write('''
            UPDATE agents_autonomous_tasks
            SET completed_at = ?, status = 'completed'
            WHERE task_id = ?
        ''', (datetime.now().isoformat(), task_id)) > 0

    def finalize_signed_worker_execution(
        self,
        task_id: str,
        *,
        context: Mapping[str, Any],
        accepted: bool,
    ) -> bool:
        """Finalize only the exact executing context admitted by the worker CAS."""
        claim = context.get("signed_worker_execution_claim")
        use = context.get("signed_worker_execution_use")
        binding = _signed_worker_finalization_binding(task_id, claim, use)
        if binding is None:
            return False
        assigned_to, expected_claim, expected_use = binding
        status = "completed" if accepted is True else "failed"
        try:
            with self.db.get_connection() as connection:
                row = connection.execute(
                    "SELECT status, assigned_to, context "
                    "FROM agents_autonomous_tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                raw_context = _matching_signed_worker_execution_context(
                    row, assigned_to, expected_claim, expected_use
                )
                if raw_context is None:
                    return False
                changed = connection.execute(
                    "UPDATE agents_autonomous_tasks "
                    "SET completed_at = ?, status = ? "
                    "WHERE task_id = ? AND status = 'executing' "
                    "AND assigned_to = ? AND context = ?",
                    (
                        datetime.now().isoformat(),
                        status,
                        task_id,
                        assigned_to,
                        raw_context,
                    ),
                ).rowcount
                return changed == 1
        except Exception:
            return False

    def schedule_autonomous_task_retry(
        self,
        task_id: str,
        *,
        context: Dict[str, Any],
        retry_not_before: str,
    ) -> bool:
        """Move a failed task into a durable bounded retry wait state."""
        return self.db.execute_write(
            """
            UPDATE agents_autonomous_tasks
            SET status = 'retry_wait',
                context = ?,
                retry_not_before = ?,
                assigned_to = NULL,
                assigned_at = NULL
            WHERE task_id = ? AND status = 'failed'
            """,
            (json.dumps(context), retry_not_before, task_id),
        ) > 0

    def requeue_autonomous_task(
        self,
        task_id: str,
        *,
        expected_status: str = "retry_wait",
    ) -> bool:
        """Requeue a task only from the caller's exact expected state."""
        return self.db.execute_write(
            """
            UPDATE agents_autonomous_tasks
            SET status = 'pending',
                retry_not_before = NULL,
                assigned_to = NULL,
                assigned_at = NULL,
                completed_at = NULL
            WHERE task_id = ? AND status = ?
            """,
            (task_id, expected_status),
        ) > 0

    # ============================================================================
    # INDEPENDENT ASSURANCE CAPACITY RESERVATIONS
    # ============================================================================

    @staticmethod
    def _parse_task_context(task: Mapping[str, Any]) -> Dict[str, Any]:
        context = task.get("context")
        if isinstance(context, Mapping):
            return dict(context)
        if isinstance(context, str):
            try:
                parsed = json.loads(context)
            except (TypeError, ValueError) as exc:
                raise _AssuranceReservationRejected("task_context_invalid") from exc
            if isinstance(parsed, Mapping):
                return dict(parsed)
        raise _AssuranceReservationRejected("task_context_missing")

    @staticmethod
    def _load_assurance_reservation(
        conn: Any,
        reservation_id: str,
    ) -> Optional[Dict[str, Any]]:
        row = conn.execute(
            """
            SELECT *
            FROM agents_independent_assurance_reservations
            WHERE reservation_id = ?
            """,
            (reservation_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    @staticmethod
    def _validate_assurance_task_binding(
        *,
        task: Mapping[str, Any],
        task_kind: str,
        expected: Mapping[str, str],
    ) -> None:
        context = AgentDB._parse_task_context(task)
        signed_dispatch = context.get("signed_authority_worker_dispatch_receipt")
        signed_dispatch = (
            dict(signed_dispatch) if isinstance(signed_dispatch, Mapping) else {}
        )
        allocation = context.get("wsp15_allocation_receipt")
        allocation = dict(allocation) if isinstance(allocation, Mapping) else {}
        role = str(
            context.get("worker_role")
            or context.get("role")
            or context.get("task_role")
            or ""
        ).strip()
        principal = str(
            context.get("worker_principal_id")
            or context.get("principal_id")
            or ""
        ).strip()

        if task_kind == "verifier":
            if role != _ASSURANCE_VERIFIER_ROLE:
                raise _AssuranceReservationRejected("verifier_task_role_mismatch")
            required_skills = task.get("required_skills")
            if isinstance(required_skills, str):
                try:
                    required_skills = json.loads(required_skills)
                except (TypeError, ValueError) as exc:
                    raise _AssuranceReservationRejected(
                        "verifier_task_required_skills_invalid"
                    ) from exc
            skill_names = (
                {str(skill).strip() for skill in required_skills}
                if isinstance(required_skills, list)
                else set()
            )
            if (
                expected["capability"] not in skill_names
                and f"capability:{expected['capability']}" not in skill_names
            ):
                raise _AssuranceReservationRejected(
                    "verifier_task_capability_mismatch"
                )
        elif role == _ASSURANCE_VERIFIER_ROLE:
            raise _AssuranceReservationRejected("author_task_role_invalid")

        if principal != expected[f"{task_kind}_principal_id"]:
            raise _AssuranceReservationRejected(
                f"{task_kind}_task_principal_id_mismatch"
            )

        task_bindings = {
            "work_order_id": str(
                context.get("work_order_id")
                or signed_dispatch.get("work_order_id")
                or ""
            ).strip(),
            "queue_item_id": str(context.get("queue_item_id") or "").strip(),
            "operational_snapshot_id": str(
                context.get("operational_snapshot_id") or ""
            ).strip(),
            "wsp15_allocation_receipt_id": str(
                context.get("wsp15_allocation_receipt_id")
                or allocation.get("receipt_id")
                or signed_dispatch.get("wsp15_allocation_receipt_id")
                or ""
            ).strip(),
        }
        for field_name, actual_value in task_bindings.items():
            if actual_value != expected[field_name]:
                raise _AssuranceReservationRejected(
                    f"{task_kind}_task_{field_name}_mismatch"
                )

        if task_kind == "verifier":
            for field_name in ("capability", "worker_runtime"):
                if str(context.get(field_name) or "").strip() != expected[field_name]:
                    raise _AssuranceReservationRejected(
                        f"verifier_task_{field_name}_mismatch"
                    )

    @staticmethod
    def _expire_assurance_row(
        conn: Any,
        reservation: Mapping[str, Any],
        *,
        now_utc: datetime,
        now_iso: str,
    ) -> Dict[str, Any]:
        if str(reservation.get("status") or "") != "RESERVED":
            return dict(reservation)
        expires_at, _ = _parse_assurance_utc_timestamp(
            reservation.get("expires_at"),
            "expires_at",
        )
        if expires_at > now_utc:
            return dict(reservation)

        updated = conn.execute(
            """
            UPDATE agents_independent_assurance_reservations
            SET status = 'EXPIRED', completed_at = ?
            WHERE reservation_id = ? AND status = 'RESERVED'
            """,
            (now_iso, reservation["reservation_id"]),
        ).rowcount
        if updated:
            task_updated = conn.execute(
                """
                UPDATE agents_autonomous_tasks
                SET status = 'expired', completed_at = ?
                WHERE task_id = ? AND status = 'assigned' AND assigned_to = ?
                """,
                (
                    now_iso,
                    reservation["verifier_task_id"],
                    reservation["verifier_principal_id"],
                ),
            ).rowcount
            if task_updated != 1:
                raise _AssuranceReservationRejected(
                    "verifier_task_expiration_transition_failed"
                )
        refreshed = AgentDB._load_assurance_reservation(
            conn,
            str(reservation["reservation_id"]),
        )
        return refreshed or dict(reservation)

    def reserve_independent_assurance(
        self,
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Atomically reserve independent assurance capacity and claim its task."""
        if not isinstance(request, Mapping):
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("request_not_mapping",),
            )

        normalized = {
            field_name: str(request.get(field_name) or "").strip()
            for field_name in _ASSURANCE_REQUIRED_FIELDS
        }
        supplied_schema_version = str(request.get("schema_version") or "").strip()
        normalized["schema_version"] = (
            supplied_schema_version or _ASSURANCE_REQUEST_SCHEMA_VERSION
        )
        missing = tuple(
            f"missing_{field_name}"
            for field_name, value in normalized.items()
            if not value
        )
        if missing:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=missing,
            )
        if normalized["schema_version"] != _ASSURANCE_REQUEST_SCHEMA_VERSION:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("request_schema_version_unsupported",),
            )
        if normalized["author_task_id"] == normalized["verifier_task_id"]:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("author_verifier_task_equality",),
            )
        if normalized["author_principal_id"] == normalized["verifier_principal_id"]:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("author_verifier_principal_equality",),
            )

        original_digest_payload = {
            field_name: normalized[field_name]
            for field_name in _ASSURANCE_REQUIRED_FIELDS
        }
        if supplied_schema_version:
            original_digest_payload["schema_version"] = normalized["schema_version"]
        original_request_digest = _assurance_digest(original_digest_payload)

        try:
            reserved_at, normalized["reserved_at"] = _parse_assurance_utc_timestamp(
                normalized["reserved_at"],
                "reserved_at",
            )
            expires_at, normalized["expires_at"] = _parse_assurance_utc_timestamp(
                normalized["expires_at"],
                "expires_at",
            )
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )

        now_utc = self._assurance_now_provider().astimezone(timezone.utc)
        if expires_at <= now_utc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_expired",),
            )
        if reserved_at > now_utc + timedelta(minutes=5):
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reserved_at_in_future",),
            )
        if expires_at <= reserved_at:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("invalid_reservation_window",),
            )
        if expires_at - reserved_at > _ASSURANCE_MAX_LEASE:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_window_exceeds_maximum",),
            )

        digest_payload = {
            field_name: normalized[field_name]
            for field_name in _ASSURANCE_REQUIRED_FIELDS
        }
        if supplied_schema_version:
            digest_payload["schema_version"] = normalized["schema_version"]
        normalized_request_digest = _assurance_digest(digest_payload)
        supplied_digest = str(request.get("reservation_digest") or "").strip().lower()
        if not supplied_digest:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_digest_missing",),
            )
        normalized_supplied_digest = (
            _normalize_sha256_digest(supplied_digest)
        )
        if normalized_supplied_digest not in {
            original_request_digest,
            normalized_request_digest,
        }:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_digest_mismatch",),
            )
        reservation_digest = normalized_supplied_digest

        try:
            with self.db.get_connection() as conn:
                author_task = conn.execute(
                    "SELECT * FROM agents_autonomous_tasks WHERE task_id = ?",
                    (normalized["author_task_id"],),
                ).fetchone()
                verifier_task = conn.execute(
                    "SELECT * FROM agents_autonomous_tasks WHERE task_id = ?",
                    (normalized["verifier_task_id"],),
                ).fetchone()
                if author_task is None:
                    raise _AssuranceReservationRejected("author_task_not_found")
                if verifier_task is None:
                    raise _AssuranceReservationRejected("verifier_task_not_found")
                if (
                    str(author_task.get("status") or "") != "pending"
                    or str(author_task.get("assigned_to") or "").strip()
                ):
                    raise _AssuranceReservationRejected(
                        "author_task_not_pending"
                    )

                self._validate_assurance_task_binding(
                    task=author_task,
                    task_kind="author",
                    expected=normalized,
                )
                self._validate_assurance_task_binding(
                    task=verifier_task,
                    task_kind="verifier",
                    expected=normalized,
                )

                claim_count = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET status = 'assigned', assigned_to = ?, assigned_at = ?
                    WHERE task_id = ?
                      AND status = 'pending'
                      AND (assigned_to IS NULL OR assigned_to = '')
                    """,
                    (
                        normalized["verifier_principal_id"],
                        normalized["reserved_at"],
                        normalized["verifier_task_id"],
                    ),
                ).rowcount
                if claim_count != 1:
                    raise _AssuranceReservationRejected(
                        "verifier_task_not_pending"
                    )

                conn.execute(
                    """
                    INSERT INTO agents_independent_assurance_reservations (
                        reservation_id,
                        request_schema_version,
                        work_order_id,
                        queue_item_id,
                        author_task_id,
                        author_principal_id,
                        verifier_task_id,
                        verifier_principal_id,
                        capability,
                        worker_runtime,
                        operational_snapshot_id,
                        wsp15_allocation_receipt_id,
                        lease_id,
                        reserved_at,
                        expires_at,
                        reservation_digest,
                        admission_reservation_digest,
                        admission_reserved_at,
                        renewal_count,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'RESERVED')
                    """,
                    (
                        normalized["reservation_id"],
                        normalized["schema_version"],
                        normalized["work_order_id"],
                        normalized["queue_item_id"],
                        normalized["author_task_id"],
                        normalized["author_principal_id"],
                        normalized["verifier_task_id"],
                        normalized["verifier_principal_id"],
                        normalized["capability"],
                        normalized["worker_runtime"],
                        normalized["operational_snapshot_id"],
                        normalized["wsp15_allocation_receipt_id"],
                        normalized["lease_id"],
                        normalized["reserved_at"],
                        normalized["expires_at"],
                        reservation_digest,
                        reservation_digest,
                        normalized["reserved_at"],
                    ),
                )
                reservation = self._load_assurance_reservation(
                    conn,
                    normalized["reservation_id"],
                )
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        except Exception:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_conflict_or_database_error",),
            )

        return _assurance_result(
            accepted=True,
            status="RESERVED",
            reservation=reservation,
        )

    def renew_independent_assurance(
        self,
        request: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Renew one expired verifier lease without changing its admission scope."""

        if not isinstance(request, Mapping):
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("request_not_mapping",),
            )
        normalized = {
            field_name: str(request.get(field_name) or "").strip()
            for field_name in _ASSURANCE_REQUIRED_FIELDS
        }
        normalized["schema_version"] = str(
            request.get("schema_version") or ""
        ).strip()
        missing = tuple(
            f"missing_{field_name}"
            for field_name, value in normalized.items()
            if not value
        )
        if missing:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=missing,
            )
        if normalized["schema_version"] != _ASSURANCE_REQUEST_SCHEMA_VERSION:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("request_schema_version_unsupported",),
            )
        try:
            renewal_count = int(request.get("renewal_count"))
        except (TypeError, ValueError):
            renewal_count = -1
        if renewal_count < 1 or renewal_count > _ASSURANCE_MAX_RENEWALS:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("renewal_count_invalid",),
            )
        original_digest_payload = {
            field_name: normalized[field_name]
            for field_name in _ASSURANCE_REQUIRED_FIELDS
        }
        original_digest_payload["schema_version"] = normalized["schema_version"]
        original_digest_payload["renewal_count"] = renewal_count
        original_request_digest = _assurance_digest(original_digest_payload)
        try:
            reserved_at, normalized["reserved_at"] = _parse_assurance_utc_timestamp(
                normalized["reserved_at"],
                "reserved_at",
            )
            expires_at, normalized["expires_at"] = _parse_assurance_utc_timestamp(
                normalized["expires_at"],
                "expires_at",
            )
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        now_utc = self._assurance_now_provider().astimezone(timezone.utc)
        if (
            expires_at <= now_utc
            or reserved_at > now_utc + timedelta(minutes=5)
            or expires_at <= reserved_at
        ):
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("invalid_renewal_window",),
            )
        if expires_at - reserved_at > _ASSURANCE_MAX_LEASE:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_window_exceeds_maximum",),
            )

        digest_payload = {
            field_name: normalized[field_name]
            for field_name in _ASSURANCE_REQUIRED_FIELDS
        }
        digest_payload["schema_version"] = normalized["schema_version"]
        digest_payload["renewal_count"] = renewal_count
        supplied_digest = _normalize_sha256_digest(
            str(request.get("reservation_digest") or "").strip().lower()
        )
        normalized_request_digest = _assurance_digest(digest_payload)
        if (
            not supplied_digest
            or supplied_digest
            not in {original_request_digest, normalized_request_digest}
        ):
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_digest_mismatch",),
            )

        immutable_fields = tuple(
            field_name
            for field_name in _ASSURANCE_REQUIRED_FIELDS
            if field_name not in {"lease_id", "reserved_at", "expires_at"}
        )
        try:
            with self.db.get_connection() as conn:
                reservation = self._load_assurance_reservation(
                    conn,
                    normalized["reservation_id"],
                )
                if reservation is None:
                    raise _AssuranceReservationRejected(
                        "reservation_not_found"
                    )
                if str(reservation.get("status") or "") != "EXPIRED":
                    raise _AssuranceReservationRejected(
                        "reservation_not_expired"
                    )
                if (
                    str(reservation.get("request_schema_version") or "")
                    != normalized["schema_version"]
                ):
                    raise _AssuranceReservationRejected(
                        "renewal_schema_version_mismatch"
                    )
                existing_renewal_count = int(
                    reservation.get("renewal_count") or 0
                )
                if renewal_count != existing_renewal_count + 1:
                    raise _AssuranceReservationRejected(
                        "renewal_count_mismatch"
                    )
                admission_reserved_at, _ = _parse_assurance_utc_timestamp(
                    reservation.get("admission_reserved_at"),
                    "admission_reserved_at",
                )
                if (
                    expires_at - admission_reserved_at
                    > _ASSURANCE_MAX_LEASE
                ):
                    raise _AssuranceReservationRejected(
                        "renewal_horizon_exceeds_maximum"
                    )
                for field_name in immutable_fields:
                    stored_name = (
                        "request_schema_version"
                        if field_name == "schema_version"
                        else field_name
                    )
                    if str(reservation.get(stored_name) or "") != normalized[
                        field_name
                    ]:
                        raise _AssuranceReservationRejected(
                            f"renewal_{field_name}_mismatch"
                        )
                author_task = conn.execute(
                    "SELECT status FROM agents_autonomous_tasks WHERE task_id = ?",
                    (normalized["author_task_id"],),
                ).fetchone()
                verifier_task = conn.execute(
                    "SELECT status FROM agents_autonomous_tasks WHERE task_id = ?",
                    (normalized["verifier_task_id"],),
                ).fetchone()
                if (
                    author_task is None
                    or str(author_task["status"]) != "completed"
                ):
                    raise _AssuranceReservationRejected(
                        "author_task_not_completed"
                    )
                if (
                    verifier_task is None
                    or str(verifier_task["status"]) != "expired"
                ):
                    raise _AssuranceReservationRejected(
                        "verifier_task_not_expired"
                    )
                updated = conn.execute(
                    """
                    UPDATE agents_independent_assurance_reservations
                    SET lease_id = ?,
                        reserved_at = ?,
                        expires_at = ?,
                        reservation_digest = ?,
                        renewal_count = ?,
                        status = 'RESERVED',
                        completed_at = NULL
                    WHERE reservation_id = ? AND status = 'EXPIRED'
                    """,
                    (
                        normalized["lease_id"],
                        normalized["reserved_at"],
                        normalized["expires_at"],
                        supplied_digest,
                        renewal_count,
                        normalized["reservation_id"],
                    ),
                ).rowcount
                if updated != 1:
                    raise _AssuranceReservationRejected(
                        "reservation_renewal_race_lost"
                    )
                task_updated = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET status = 'assigned',
                        assigned_to = ?,
                        assigned_at = ?,
                        completed_at = NULL
                    WHERE task_id = ? AND status = 'expired'
                    """,
                    (
                        normalized["verifier_principal_id"],
                        normalized["reserved_at"],
                        normalized["verifier_task_id"],
                    ),
                ).rowcount
                if task_updated != 1:
                    raise _AssuranceReservationRejected(
                        "verifier_task_renewal_transition_failed"
                    )
                renewed = self._load_assurance_reservation(
                    conn,
                    normalized["reservation_id"],
                )
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        except Exception:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("renewal_conflict_or_database_error",),
            )
        return _assurance_result(
            accepted=True,
            status="RESERVED",
            reservation=renewed,
        )

    def get_independent_assurance_reservation(
        self,
        reservation_id: str,
    ) -> Optional[Mapping[str, Any]]:
        """Rehydrate a reservation and expire elapsed active leases."""
        normalized_id = str(reservation_id or "").strip()
        if not normalized_id:
            return None
        now_utc = self._assurance_now_provider().astimezone(timezone.utc)
        now_iso = now_utc.isoformat().replace("+00:00", "Z")
        try:
            with self.db.get_connection() as conn:
                reservation = self._load_assurance_reservation(conn, normalized_id)
                if reservation is None:
                    return None
                reservation = self._expire_assurance_row(
                    conn,
                    reservation,
                    now_utc=now_utc,
                    now_iso=now_iso,
                )
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        status = str(reservation.get("status") or "UNKNOWN")
        return _assurance_result(
            accepted=status == "RESERVED",
            status=status,
            rejection_reasons=() if status == "RESERVED" else (f"reservation_{status.lower()}",),
            reservation=reservation,
        )

    def get_independent_assurance_reservation_for_task(
        self,
        task_id: str,
        *,
        task_kind: str,
    ) -> Optional[Mapping[str, Any]]:
        """Rehydrate the active reservation bound to one author/verifier task."""

        normalized_task_id = str(task_id or "").strip()
        query = {
            "author": """
                SELECT reservation_id
                FROM agents_independent_assurance_reservations
                WHERE author_task_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
            "verifier": """
                SELECT reservation_id
                FROM agents_independent_assurance_reservations
                WHERE verifier_task_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """,
        }.get(str(task_kind or "").strip().lower())
        if not normalized_task_id or query is None:
            return None
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(query, (normalized_task_id,)).fetchone()
        except Exception:
            return None
        if row is None:
            return None
        reservation_id = (
            row["reservation_id"] if hasattr(row, "keys") else row[0]
        )
        return self.get_independent_assurance_reservation(str(reservation_id))

    def complete_independent_assurance(
        self,
        reservation_id: str,
        *,
        admission_reservation_digest: str,
        terminal_receipt_id: str,
        terminal_receipt_digest: str,
        status: str,
        now_iso: str,
    ) -> Mapping[str, Any]:
        """Bind a terminal verifier receipt and release its reservation once."""
        normalized_id = str(reservation_id or "").strip()
        admission_digest = _normalize_sha256_digest(
            admission_reservation_digest
        )
        receipt_id = str(terminal_receipt_id or "").strip()
        receipt_digest = _normalize_sha256_digest(terminal_receipt_digest)
        terminal_status = str(status or "").strip().upper()
        reasons = []
        if not normalized_id:
            reasons.append("missing_reservation_id")
        if not _is_sha256_digest(admission_digest):
            reasons.append("invalid_admission_reservation_digest")
        if not receipt_id:
            reasons.append("missing_terminal_receipt_id")
        if not _is_sha256_digest(receipt_digest):
            reasons.append("invalid_terminal_receipt_digest")
        if terminal_status not in _ASSURANCE_TERMINAL_STATUSES:
            reasons.append("invalid_terminal_status")
        try:
            now_utc, canonical_now = _parse_assurance_utc_timestamp(now_iso, "now_iso")
        except _AssuranceReservationRejected as exc:
            reasons.extend(exc.reasons)
            now_utc = datetime.now(timezone.utc)
            canonical_now = ""
        if reasons:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=tuple(reasons),
            )

        try:
            with self.db.get_connection() as conn:
                reservation = self._load_assurance_reservation(conn, normalized_id)
                if reservation is None:
                    raise _AssuranceReservationRejected("reservation_not_found")
                if (
                    str(
                        reservation.get("admission_reservation_digest")
                        or reservation.get("reservation_digest")
                        or ""
                    )
                    != admission_digest
                ):
                    raise _AssuranceReservationRejected(
                        "admission_reservation_digest_mismatch"
                    )
                reservation = self._expire_assurance_row(
                    conn,
                    reservation,
                    now_utc=now_utc,
                    now_iso=canonical_now,
                )
                if reservation["status"] != "RESERVED":
                    raise _AssuranceReservationRejected("reservation_not_active")
                updated = conn.execute(
                    """
                    UPDATE agents_independent_assurance_reservations
                    SET status = ?,
                        terminal_receipt_id = ?,
                        terminal_receipt_digest = ?,
                        terminal_status = ?,
                        completed_at = ?
                    WHERE reservation_id = ? AND status = 'RESERVED'
                    """,
                    (
                        terminal_status,
                        receipt_id,
                        receipt_digest,
                        terminal_status,
                        canonical_now,
                        normalized_id,
                    ),
                ).rowcount
                if updated != 1:
                    raise _AssuranceReservationRejected("reservation_not_active")
                task_updated = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET status = 'completed', completed_at = ?
                    WHERE task_id = ? AND status IN ('assigned', 'executing')
                      AND assigned_to = ?
                    """,
                    (
                        canonical_now,
                        reservation["verifier_task_id"],
                        reservation["verifier_principal_id"],
                    ),
                ).rowcount
                if task_updated != 1:
                    raise _AssuranceReservationRejected(
                        "verifier_task_terminal_transition_failed"
                    )
                completed = self._load_assurance_reservation(conn, normalized_id)
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        except Exception:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_completion_database_error",),
            )
        return _assurance_result(
            accepted=True,
            status=terminal_status,
            reservation=completed,
        )

    def revoke_independent_assurance(
        self,
        reservation_id: str,
        *,
        reason: str,
        now_iso: str,
    ) -> Mapping[str, Any]:
        """Revoke one active reservation and make its verifier task non-claimable."""
        normalized_id = str(reservation_id or "").strip()
        normalized_reason = str(reason or "").strip()
        try:
            _, canonical_now = _parse_assurance_utc_timestamp(now_iso, "now_iso")
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        if not normalized_id or not normalized_reason:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=tuple(
                    reason_name
                    for condition, reason_name in (
                        (not normalized_id, "missing_reservation_id"),
                        (not normalized_reason, "missing_revocation_reason"),
                    )
                    if condition
                ),
            )

        try:
            with self.db.get_connection() as conn:
                reservation = self._load_assurance_reservation(conn, normalized_id)
                if reservation is None:
                    raise _AssuranceReservationRejected("reservation_not_found")
                updated = conn.execute(
                    """
                    UPDATE agents_independent_assurance_reservations
                    SET status = 'REVOKED',
                        revoked_at = ?,
                        revocation_reason = ?,
                        completed_at = ?
                    WHERE reservation_id = ? AND status = 'RESERVED'
                    """,
                    (
                        canonical_now,
                        normalized_reason,
                        canonical_now,
                        normalized_id,
                    ),
                ).rowcount
                if updated != 1:
                    raise _AssuranceReservationRejected("reservation_not_active")
                task_updated = conn.execute(
                    """
                    UPDATE agents_autonomous_tasks
                    SET status = 'cancelled', completed_at = ?
                    WHERE task_id = ? AND status = 'assigned' AND assigned_to = ?
                    """,
                    (
                        canonical_now,
                        reservation["verifier_task_id"],
                        reservation["verifier_principal_id"],
                    ),
                ).rowcount
                if task_updated != 1:
                    raise _AssuranceReservationRejected(
                        "verifier_task_revocation_transition_failed"
                    )
                revoked = self._load_assurance_reservation(conn, normalized_id)
        except _AssuranceReservationRejected as exc:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=exc.reasons,
            )
        except Exception:
            return _assurance_result(
                accepted=False,
                status="REJECTED",
                rejection_reasons=("reservation_revocation_database_error",),
            )
        return _assurance_result(
            accepted=True,
            status="REVOKED",
            reservation=revoked,
        )

    def expire_independent_assurance_reservations(
        self,
        *,
        now_iso: str,
    ) -> Mapping[str, Any]:
        """Expire every elapsed active reservation in one transaction."""
        try:
            now_utc, canonical_now = _parse_assurance_utc_timestamp(now_iso, "now_iso")
        except _AssuranceReservationRejected as exc:
            return {
                "accepted": False,
                "status": "REJECTED",
                "rejection_reasons": list(exc.reasons),
                "expired_reservation_ids": [],
            }

        expired_ids = []
        try:
            with self.db.get_connection() as conn:
                candidates = conn.execute(
                    """
                    SELECT *
                    FROM agents_independent_assurance_reservations
                    WHERE status = 'RESERVED' AND expires_at <= ?
                    ORDER BY reservation_id
                    """,
                    (canonical_now,),
                ).fetchall()
                for candidate in candidates:
                    refreshed = self._expire_assurance_row(
                        conn,
                        candidate,
                        now_utc=now_utc,
                        now_iso=canonical_now,
                    )
                    if refreshed["status"] == "EXPIRED":
                        expired_ids.append(refreshed["reservation_id"])
        except _AssuranceReservationRejected as exc:
            return {
                "accepted": False,
                "status": "REJECTED",
                "rejection_reasons": list(exc.reasons),
                "expired_reservation_ids": [],
            }
        return {
            "accepted": True,
            "status": "EXPIRED" if expired_ids else "NOOP",
            "rejection_reasons": [],
            "expired_reservation_ids": expired_ids,
        }

    # ============================================================================
    # INDEX REFRESH TRACKING (HoloIndex Automation)
    # ============================================================================

    def record_index_refresh(self, index_type: str, duration: float, entries_count: int) -> None:
        """Record successful index refresh."""
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO index_refresh_tracking
                (index_type, last_refresh, refresh_count, last_refresh_duration, total_entries_indexed)
                VALUES (
                    ?,
                    ?,
                    COALESCE((SELECT refresh_count FROM index_refresh_tracking WHERE index_type = ?), 0) + 1,
                    ?,
                    ?
                )
            ''', (index_type, datetime.now(), index_type, duration, entries_count))

    def get_last_index_refresh(self, index_type: str) -> Optional[datetime]:
        """Get timestamp of last index refresh."""
        result = self.db.execute_query(
            "SELECT last_refresh FROM index_refresh_tracking WHERE index_type = ?",
            (index_type,)
        )
        return result[0]['last_refresh'] if result else None

    def should_refresh_index(self, index_type: str, max_age_hours: int = 24) -> bool:
        """Check if index should be refreshed based on age."""
        last_refresh = self.get_last_index_refresh(index_type)
        if not last_refresh:
            return True  # Never refreshed, should refresh

        # Parse the datetime string
        if isinstance(last_refresh, str):
            last_refresh = datetime.fromisoformat(last_refresh.replace('Z', '+00:00'))

        age = datetime.now() - last_refresh
        return age.total_seconds() > (max_age_hours * 3600)

    # ============================================================================
    # MODULE DOCUMENTATION REGISTRY (Qwen Module Doc Linker)
    # ============================================================================

    def register_module(self, module_name: str, module_path: str, module_domain: str,
                       linker_version: str = "1.0.0") -> int:
        """
        Register or update a module in the documentation registry.

        Args:
            module_name: Name of the module (e.g., "liberty_alert")
            module_path: Full path to module directory
            module_domain: Domain (e.g., "communication")
            linker_version: Version of the linker

        Returns:
            module_id (int)
        """
        with self.db.get_connection() as conn:
            # Try to insert, on conflict update timestamp
            cursor = conn.execute('''
                INSERT INTO modules (module_name, module_path, module_domain, linked_timestamp, linker_version)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(module_path) DO UPDATE SET
                    module_name = excluded.module_name,
                    module_domain = excluded.module_domain,
                    linked_timestamp = excluded.linked_timestamp,
                    linker_version = excluded.linker_version
            ''', (module_name, module_path, module_domain, datetime.now().isoformat(), linker_version))

            # Get the module_id (either newly inserted or existing)
            result = conn.execute(
                "SELECT module_id FROM modules WHERE module_path = ?",
                (module_path,)
            ).fetchone()

            return result[0] if result else cursor.lastrowid

    def register_document(self, module_id: int, doc_type: str, file_path: str,
                         title: str, purpose: str) -> int:
        """
        Register a document in the module documentation registry.

        Args:
            module_id: ID of the parent module
            doc_type: Type of document (modlog, readme, interface, etc.)
            file_path: Full path to document
            title: Document title
            purpose: Document purpose/summary

        Returns:
            doc_id (int)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO module_documents (module_id, doc_type, file_path, title, purpose, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    doc_type = excluded.doc_type,
                    title = excluded.title,
                    purpose = excluded.purpose,
                    last_updated = excluded.last_updated
            ''', (module_id, doc_type, file_path, title, purpose, datetime.now().isoformat()))

            # Get the doc_id
            result = conn.execute(
                "SELECT doc_id FROM module_documents WHERE file_path = ?",
                (file_path,)
            ).fetchone()

            return result[0] if result else cursor.lastrowid

    def add_document_relationship(self, from_doc_id: int, to_doc_id: int) -> bool:
        """
        Add a relationship between two documents.

        Args:
            from_doc_id: Source document ID
            to_doc_id: Target document ID

        Returns:
            True if successful
        """
        try:
            self.db.execute_write('''
                INSERT OR IGNORE INTO document_relationships (from_doc_id, to_doc_id)
                VALUES (?, ?)
            ''', (from_doc_id, to_doc_id))
            return True
        except Exception:
            return False

    def add_wsp_implementation(self, module_id: int, wsp_number: str) -> bool:
        """
        Record that a module implements a WSP protocol.

        Args:
            module_id: Module ID
            wsp_number: WSP protocol number (e.g., "WSP 90")

        Returns:
            True if successful
        """
        try:
            self.db.execute_write('''
                INSERT OR IGNORE INTO module_wsp_implementations (module_id, wsp_number)
                VALUES (?, ?)
            ''', (module_id, wsp_number))
            return True
        except Exception:
            return False

    def add_cross_reference(self, doc_id: int, reference_type: str, reference_value: str) -> bool:
        """
        Add a cross-reference in a document.

        Args:
            doc_id: Document ID
            reference_type: Type of reference ('wsp', 'module', 'file')
            reference_value: Value of the reference

        Returns:
            True if successful
        """
        try:
            self.db.execute_write('''
                INSERT OR IGNORE INTO document_cross_references (doc_id, reference_type, reference_value)
                VALUES (?, ?, ?)
            ''', (doc_id, reference_type, reference_value))
            return True
        except Exception:
            return False

    def get_module(self, module_name: str = None, module_path: str = None) -> Optional[Dict[str, Any]]:
        """
        Get module by name or path.

        Args:
            module_name: Module name
            module_path: Module path

        Returns:
            Module dictionary or None
        """
        if module_path:
            result = self.db.execute_query(
                "SELECT * FROM modules WHERE module_path = ?",
                (module_path,)
            )
        elif module_name:
            result = self.db.execute_query(
                "SELECT * FROM modules WHERE module_name = ?",
                (module_name,)
            )
        else:
            return None

        return dict(result[0]) if result else None

    def get_module_documents(self, module_id: int) -> List[Dict[str, Any]]:
        """
        Get all documents for a module.

        Args:
            module_id: Module ID

        Returns:
            List of document dictionaries
        """
        return self.db.execute_query('''
            SELECT * FROM module_documents WHERE module_id = ?
            ORDER BY doc_type, title
        ''', (module_id,))

    def get_document_relationships(self, doc_id: int) -> List[Dict[str, Any]]:
        """
        Get all related documents for a document.

        Args:
            doc_id: Document ID

        Returns:
            List of related document dictionaries
        """
        return self.db.execute_query('''
            SELECT d.* FROM module_documents d
            JOIN document_relationships r ON d.doc_id = r.to_doc_id
            WHERE r.from_doc_id = ?
        ''', (doc_id,))

    def get_module_wsp_implementations(self, module_id: int) -> List[str]:
        """
        Get all WSP implementations for a module.

        Args:
            module_id: Module ID

        Returns:
            List of WSP numbers
        """
        results = self.db.execute_query('''
            SELECT wsp_number FROM module_wsp_implementations
            WHERE module_id = ?
            ORDER BY wsp_number
        ''', (module_id,))

        return [row['wsp_number'] for row in results]

    def get_modules_implementing_wsp(self, wsp_number: str) -> List[Dict[str, Any]]:
        """
        Get all modules implementing a specific WSP protocol.

        Args:
            wsp_number: WSP protocol number (e.g., "WSP 90")

        Returns:
            List of module dictionaries
        """
        return self.db.execute_query('''
            SELECT m.* FROM modules m
            JOIN module_wsp_implementations w ON m.module_id = w.module_id
            WHERE w.wsp_number = ?
            ORDER BY m.module_name
        ''', (wsp_number,))

    def get_all_modules(self) -> List[Dict[str, Any]]:
        """
        Get all registered modules.

        Returns:
            List of module dictionaries
        """
        return self.db.execute_query('''
            SELECT * FROM modules
            ORDER BY module_domain, module_name
        ''')

    def get_document_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get document by file path.

        Args:
            file_path: Full path to document

        Returns:
            Document dictionary or None
        """
        result = self.db.execute_query(
            "SELECT * FROM module_documents WHERE file_path = ?",
            (file_path,)
        )
        return dict(result[0]) if result else None

    def delete_module_documentation(self, module_id: int) -> bool:
        """
        Delete all documentation for a module (cascade delete).

        Args:
            module_id: Module ID

        Returns:
            True if successful
        """
        try:
            with self.db.get_connection() as conn:
                # Foreign keys with CASCADE will handle related records
                conn.execute("DELETE FROM modules WHERE module_id = ?", (module_id,))
            return True
        except Exception:
            return False

    # ============================================================================
    # SOCIAL MEDIA POST CAPTURE (Agent Post Review)
    # ============================================================================

    def record_post(self, platform: str, post_type: str, content: str,
                   identity: str = None, target_url: str = None,
                   target_author: str = None, tone: str = None,
                   trigger_context: str = None, status: str = 'pending_review',
                   metadata: Dict[str, Any] = None) -> str:
        """
        Record an agent-generated social media post for review.

        Args:
            platform: Social platform (linkedin, x_twitter, youtube)
            post_type: Type of post (comment, reply, repost, original)
            content: The actual post text
            identity: Which sub-account posted (e.g., UnDaoDu, EduIT)
            target_url: URL of post being replied to
            target_author: Author being engaged with
            tone: Voice tone (pushback, collaborative, philosophical)
            trigger_context: What prompted this post
            status: Initial status (default: pending_review)
            metadata: Additional data (links, mentions, scheduling)

        Returns:
            post_id (str) — UUID for this post
        """
        post_id = str(uuid.uuid4())
        self.db.execute_write('''
            INSERT INTO agents_social_posts
            (post_id, platform, post_type, content, identity, target_url,
             target_author, tone, trigger_context, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_id, platform, post_type, content, identity, target_url,
            target_author, tone, trigger_context, status,
            json.dumps(metadata) if metadata else None
        ))
        return post_id

    def get_posts_for_review(self, platform: str = None, status: str = 'pending_review',
                            limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get posts awaiting 012 review.

        Args:
            platform: Filter by platform (None for all)
            status: Filter by status (default: pending_review)
            limit: Max results

        Returns:
            List of post dictionaries
        """
        query = "SELECT * FROM agents_social_posts WHERE status = ?"
        params: list = [status]

        if platform:
            query += " AND platform = ?"
            params.append(platform)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        results = self.db.execute_query(query, tuple(params))
        for row in results:
            if row.get('metadata') and isinstance(row['metadata'], str):
                try:
                    row['metadata'] = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    pass
        return results

    def approve_post(self, post_id: str, notes: str = None) -> bool:
        """Approve a post for publishing."""
        return self.db.execute_write('''
            UPDATE agents_social_posts
            SET status = 'approved', review_notes = ?, reviewed_at = ?
            WHERE post_id = ?
        ''', (notes, datetime.now().isoformat(), post_id)) > 0

    def reject_post(self, post_id: str, notes: str) -> bool:
        """Reject a post with feedback."""
        return self.db.execute_write('''
            UPDATE agents_social_posts
            SET status = 'rejected', review_notes = ?, reviewed_at = ?
            WHERE post_id = ?
        ''', (notes, datetime.now().isoformat(), post_id)) > 0

    def mark_posted(self, post_id: str) -> bool:
        """Mark a post as successfully published."""
        return self.db.execute_write('''
            UPDATE agents_social_posts
            SET status = 'posted', posted_at = ?
            WHERE post_id = ?
        ''', (datetime.now().isoformat(), post_id)) > 0

    def get_post_stats(self) -> Dict[str, Any]:
        """Get posting statistics by platform and status."""
        stats = {}

        # By status
        status_counts = self.db.execute_query('''
            SELECT status, COUNT(*) as count FROM agents_social_posts
            GROUP BY status
        ''')
        stats['by_status'] = {row['status']: row['count'] for row in status_counts}

        # By platform
        platform_counts = self.db.execute_query('''
            SELECT platform, COUNT(*) as count FROM agents_social_posts
            GROUP BY platform
        ''')
        stats['by_platform'] = {row['platform']: row['count'] for row in platform_counts}

        # By identity
        identity_counts = self.db.execute_query('''
            SELECT identity, COUNT(*) as count FROM agents_social_posts
            WHERE identity IS NOT NULL
            GROUP BY identity
        ''')
        stats['by_identity'] = {row['identity']: row['count'] for row in identity_counts}

        # Total
        total = self.db.execute_query('SELECT COUNT(*) as count FROM agents_social_posts')
        stats['total'] = total[0]['count'] if total else 0

        return stats

    def get_posts_by_identity(self, identity: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all posts by a specific identity/sub-account."""
        results = self.db.execute_query('''
            SELECT * FROM agents_social_posts
            WHERE identity = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (identity, limit))
        for row in results:
            if row.get('metadata') and isinstance(row['metadata'], str):
                try:
                    row['metadata'] = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    pass
        return results

    # ============================================================================
    # FINANCIAL TRANSACTIONS (Lobster.cash / pAVS)
    # ============================================================================

    def record_transaction(self, tx_id: str, amount: float, currency: str,
                          purpose: str, status: str = 'pending',
                          chain_tx_hash: str = None, metadata: Dict[str, Any] = None) -> str:
        """
        Record a financial transaction (Lobster.cash / pAVS).

        Args:
            tx_id: UUID for the transaction
            amount: Value amount
            currency: Currency code (USDC, SOL)
            purpose: Reason for payment (e.g., 'AVS_Staking')
            status: Transaction status
            chain_tx_hash: On-chain hash if available
            metadata: Additional details

        Returns:
            tx_id
        """
        self.db.execute_write('''
            INSERT INTO agents_transactions
            (tx_id, chain_tx_hash, amount, currency, purpose, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            tx_id, chain_tx_hash, amount, currency, purpose, status,
            json.dumps(metadata) if metadata else None
        ))
        return tx_id

    def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent financial transactions."""
        results = self.db.execute_query('''
            SELECT * FROM agents_transactions
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        for row in results:
            if row.get('metadata') and isinstance(row['metadata'], str):
                try:
                    row['metadata'] = json.loads(row['metadata'])
                except json.JSONDecodeError:
                    pass
        return results
