#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import io

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

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from .db_manager import DatabaseManager


class AgentDB:
    """
    Shared agent memory and state (WSP 78).

    Provides:
    - Agent awakening states
    - Shared memory patterns
    - Error learning (WSP 48)
    """

    def __init__(self):
        """Initialize agent database."""
        self.db = DatabaseManager()
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
                    assigned_at DATETIME
                )

            ''')

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
        """Assign autonomous task to agent."""
        return self.db.execute_write('''
            UPDATE agents_autonomous_tasks
            SET assigned_to = ?, assigned_at = ?, status = 'assigned'
            WHERE task_id = ?
        ''', (agent_id, datetime.now().isoformat(), task_id)) > 0

    def complete_autonomous_task(self, task_id: str) -> bool:
        """Mark autonomous task as completed."""
        return self.db.execute_write('''
            UPDATE agents_autonomous_tasks
            SET completed_at = ?, status = 'completed'
            WHERE task_id = ?
        ''', (datetime.now().isoformat(), task_id)) > 0

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
