# FoundUps MCP Bridge Interface

## Public API

### `verify_reddog_holoindex_owner_binding(...) -> bool`

Read-only promotion-time proof that the already-running private query owner
serves the exact repository root, repository HEAD, HoloIndex generation, and
on-disk freshness-receipt digest supplied by the caller. It never starts an
owner or re-indexes; absent or mismatched owner state returns `False`.
Successful owner evidence is deep-copied and projected onto repository-relative
POSIX paths before raw, flattened, semantic-evidence, or receipt use. Unknown
rooted, drive-qualified, traversal, and outside-root paths fail closed. The
owner imports the producer-owned executable contract and accepts only
canonical search-result fields, scalar hit values, known collection/backend
mappings, and digest-shaped embedding fingerprints.
Unknown or nested evidence fields reject the complete response.

`flatten_hits(result, limit, query=...)` returns no hits when `limit <= 0`.
For a positive limit and one explicit module, it reserves exact module-root
README/INTERFACE evidence before filling remaining slots by global score.

### `build_mcp_server(repo_root: Optional[Path] = None, server_name: str = "FoundUps MCP Bridge") -> FastMCP`

Builds and returns a configured FastMCP server instance wrapping all 37 perception and read tools from `FoundUpsMCPBridge`. Strips the `repo_root` parameter from tool signatures and exposes standard MCP JSON schemas.

### `run_mcp_bridge_sse(host: Optional[str] = None, port: Optional[int] = None, repo_root: Optional[Path] = None, blocking: bool = True) -> Dict[str, Any]`

Launches the FastMCP SSE server on `http://<host>:<port>/sse`. Supports in-process ASGI execution if `fastmcp` is available, or fallback subprocess execution via `foundups-mcp-env`.

### `stop_mcp_bridge_sse() -> Dict[str, Any]`

Requests graceful shutdown of the broker-managed MCP Bridge SSE server.

### FoundUpsMCPBridge

Main bridge class for MCP tool access.

```python
from modules.infrastructure.foundups_mcp_bridge.src import FoundUpsMCPBridge

bridge = FoundUpsMCPBridge(repo_root=Path("O:/Foundups-Agent"))
```

#### `list_tools() -> Dict`

List all available tools with status.

**Returns:**
```python
{
    "status": "ok",
    "data": {
        "tools": [
            {"name": "get_repo_tree", "description": "...", "status": "active"},
            {"name": "coordinate_mission", "description": "...", "status": "disabled_in_v1"},
        ],
        "count": 21,
        "active_count": 15,
        "disabled_count": 6,
    }
}
```

#### `call_tool(tool_name: str, **kwargs) -> Dict`

Call a tool by name with arguments.

**Parameters:**
- `tool_name`: Tool identifier
- `**kwargs`: Tool-specific arguments

**Returns:** MCPResponse dict

#### `get_status() -> Dict`

Get bridge status and capabilities.

---

### HoloIndexQueryOwnerService

Successful semantic responses project physical `path` and `file` metadata
under the proven repository root to POSIX repository-relative values before
flattening, evidence hashing, or receipt construction. Absolute evidence
outside that root rejects the query. Failed responses always contain empty
raw and flattened evidence, so stale or malformed backend results cannot leak
unprojected paths. Unicode control, formatting, and alternate-whitespace path
characters also reject before projection. This does not mutate or reindex the
store.

Supported private owner for the RedDog operational consumers migrated in this
POC:

    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import (
        HoloIndexQueryOwnerService,
        create_holo_query_app,
        create_stdlib_server,
    )

HTTP surface:

- POST /holoindex/v1/query
- GET /holoindex/v1/health

Both routes require Authorization: Bearer using
HOLOINDEX_QUERY_SERVICE_TOKEN. The supported Phase-1 bind is literal
`127.0.0.1`; hostnames, alternate `127/8` literals, and IPv6 are rejected.
Requests are size-, query-, result-, and
timeout-bounded. The service serializes one cached semantic backend and has no
indexing API.

On Windows, a nonsealed trusted-host supervisor launches the base Python
interpreter as its direct child and prepends only the canonical checkout-local
`.venv/Lib/site-packages` directory. The supervisor validates `pyvenv.cfg`,
the configured base interpreter, Python major/minor compatibility, disabled
system-site packages, and containment under the runtime root before accepting
that dependency path. This avoids the transient venv redirector without
weakening the exact-parent lifecycle watchdog or enabling the user site.
Sealed runtime startup does not use the workspace virtualenv; it remains bound
to the separately bridge-validated dependency path. The sealed manifest
authenticates runtime source and bootstrap bytes, not every dependency file.

The first authenticated health canary has a separate 270-second cold-model
warmup budget. Once warm, health and query work use the ordinary owner budget
(15 seconds by default, never more than 30); the supervising process has a
300-second total startup budget. These are owner/work lifecycle bounds. The
RedDog client enforces a monotonic absolute deadline for repository proof and
response-body reads, but stdlib HTTP connect/header parsing remains
socket-inactivity-bounded under the explicit trusted/cooperative-loopback and
no-hostile-same-user-port-squatter POC assumption.

The query request requires query and expected_repo_head_sha; limit and
doc_type_filter are optional. A successful response proves semantic retrieval,
the exact repository SHA, a stable generation/receipt digest, and verified
manifests for the seven baseline collections on both sides of the query. Every
collection must also have a canonical embedding-space fingerprint exactly
equal in the receipt, the resident backend map, and response metadata. Blank
legacy fingerprints fail closed and cause trusted preflight maintenance.
Lexical fallback, missing proof, stale proof, generation change, and backend
failure all fail closed.

The resident owner forces authoritative sentence_transformers, disables
TurboQuant routing, and sets the generation-unbound legacy SearchCache to
None. Offline model discovery accepts complete flat SentenceTransformer
caches and Hugging Face models--.../snapshots/<revision> caches selected by
refs/main (or by a sole complete snapshot when no ref exists); incomplete or
ambiguous caches are unavailable.

Launch:

    python -m modules.infrastructure.foundups_mcp_bridge.src.holo_query_service --host 127.0.0.1 --port 8127

### HoloQueryServiceSupervisor

Trusted host bootstraps use this lifecycle API instead of distributing a
manually selected bearer token:

    from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service_supervisor import (
        HoloQueryServiceSupervisor,
        HoloQueryServiceSupervisorError,
    )

    with HoloQueryServiceSupervisor(
        repo_root="O:/Foundups-Agent",
        ssd_path="E:/HoloIndex",
    ) as owner:
        child_environment = owner.environment_for_child()

start() returns only after an authenticated loopback health probe proves the
owner ready and semantic. environment_for_child() returns a new mapping with
HOLOINDEX_QUERY_SERVICE_URL and the per-process
HOLOINDEX_QUERY_SERVICE_TOKEN; it never mutates the host environment. stop()
invalidates the handoff, terminates the owner, and kills it after a bounded
grace period. Startup failures raise HoloQueryServiceSupervisorError with a
stable secret-free code. An occupied fixed port fails before process spawn,
and a parent-process watcher exits an auto-owned child when its exact supervisor
process dies without consuming stdin. Ordinary authenticated health probes use
a bounded 30-second response window. Supervisor startup permits the first cold
semantic canary to use the owner's 270-second warmup budget inside the
300-second total startup deadline. The readiness loop is isolated in
`holo_query_owner_startup.py`; process ownership, authenticated validation,
exact binding, and child handoff remain in the supervisor. This supported
adapter boundary does not itself
remove OS filesystem/process privileges from a child; the trusted host must
configure those permissions separately.

Authenticated health responses that prove a terminal semantic backend error
fail immediately with that stable error code. They are not retried until the
startup deadline. Transient connection failures remain bounded retries.

The host bootstrap must retain the supervisor for the RedDog consumer's
lifetime. A private-adapter QUERY_OWNER_POISONED response replaces the owned
process and retries once; explicitly configured external owners are never
restarted here. See
[HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

### RedDog HoloIndex Owner Bootstrap

main.py uses the process-lifetime policy API:

    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_owner_bootstrap import (
        cleanup_reddog_holoindex_owner,
        ensure_reddog_holoindex_owner,
        resolve_reddog_holoindex_owner_handoff,
    )

    result = ensure_reddog_holoindex_owner(
        repo_root=repo_root,
        requested=holo_dependent_work_requested,
    )

The result contains only ready, status, and a stable error code. It never
contains the URL or bearer token. For requested work, the policy respects an
existing literal-127.0.0.1 HTTP URL/token, honors
REDDOG_HOLOINDEX_OWNER_AUTO_START=0, otherwise resolves the canonical
HOLOINDEX_SSD_PATH and starts one retained supervisor.

Successful automatic startup stores the URL/token only in a process-private
handoff; it does not modify os.environ. In-process RedDog adapters call
resolve_reddog_holoindex_owner_handoff(), which checks the retained supervisor
process rather than health-probing before every query. It replaces a dead
owned process once before returning either the private tuple or None. Poison
replacement is triggered by the actual query response. Explicit environment
configuration remains the boundary for an independently supervised owner.

Configured-service acceptance requires a token of at least 32 characters, an
HTTP URL using literal `127.0.0.1` at the root or
/holoindex/v1/query path, and the exact
authenticated semantic health response. When expected values are supplied,
health must also match the exact repository SHA, freshness generation, and
freshness-receipt digest.
Invalid or unready explicit configuration returns a stable failure without
overwriting either value.

cleanup_reddog_holoindex_owner() is the explicit test and controlled-shutdown
seam. It stops the auto-owned process and erases the private handoff. The
restore_environment parameter remains compatibility-only because auto-start
never edits the environment.

### RedDog HoloIndex Trusted Maintenance Handshake

Interactive/headless operational preflights and startup maintenance dispatch
use:

    from modules.infrastructure.foundups_mcp_bridge.src.reddog_holoindex_maintenance_handshake import (
        ensure_reddog_holoindex_operational,
    )

    result = ensure_reddog_holoindex_operational(
        repo_root=repo_root,
        owner_runtime_root=canonical_workspace_root,
        requested=holo_dependent_work_requested,
    )

The default REDDOG_HOLOINDEX_AUTO_MAINTENANCE=1 permits the trusted host path
to refresh a stale canonical store. It requires a clean exact Git HEAD, stops
only an auto-owned owner, runs one bounded argv-only index-all command with
semantic bypass/source narrowing removed, validates complete canonical source
scope for all seven baseline collections, rechecks HEAD, and then starts the
owner bound to the resulting generation. Startup may route the maintenance
request through governed WRE dispatch, but the trusted host remains the
maintenance authority.

The optional `owner_runtime_root` identifies the trusted canonical workspace
whose `.venv` supplies dependencies to nonsealed refresh and owner children;
it defaults to the already trusted `repo_root`. The same resolved and validated
path is used on both sides of the refresh/start boundary.
Arbitrary inherited `PYTHONPATH` and user-site packages remain disabled.
Sealed refresh continues to use only its separately bridge-validated
dependency path.

Phase 1 requires an exclusive repository-writer window during full refresh.
The canonical lease coordinates migrated writers; it does not constrain an
unleased legacy collection writer or eliminate the transient edit/revert
TOCTOU risk. A successful refresh can leave a valid CURRENT receipt even if
subsequent owner startup/health fails; in that case this operational result is
still false.

### Exact-SHA Authority Worktree Transaction

`advance_reddog_holoindex_authority()` is the trusted WRE effect boundary for
post-merge refresh. It acquires a separate cross-process authority-update
lease, fetches and proves the requested `origin/main` SHA, rejects non-forward
updates, stops the process-owned query service, switches the dedicated clean
worktree in detached mode, and invokes the existing maintenance handshake.
Before any Git effect it re-derives the authority-root digest and common Git
directory under that lease, rejecting any path substitution since queuing.
The inner `MaintenanceSession` remains responsible for SSD invalidation,
refresh, final receipt publication, and its own writer lease.

If main advances during refresh, the owner is stopped and the authority
checkout advances to the newer unindexed HEAD (or the current generation is
explicitly invalidated). No stale completion is published.
If both advancement and canonical invalidation fail, a fixed authority
blocker marker makes repository-state admission fail closed; only the same
leased transaction may clear it after switching to the exact target.

`rehydrate_canonical_freshness_proof()` is read-only. It starts no owner and
opens no persistent index; it reuses canonical query admission to prove exact
HEAD, repo/SSD identity, baseline collections, maintenance-lock state,
generation, and receipt digest.

For model-backed cross-lane audits, HoloIndex supplies candidate discovery and
an exact receipt HEAD while the worker directly reads only its allowlisted
paths. The worker re-proves that clean exact HEAD after the direct reads and a
second time immediately before accepting the report. Either proof failure
returns REJECT_REPOSITORY_STATE_CHANGED.

A stale externally configured owner returns
HOLOINDEX_MAINTENANCE_EXTERNAL_OWNER_UNSUPPORTED and is never terminated by
this process. Any semantic, source-completeness, repository-race, receipt, or
restart failure remains non-operational. See
[HOLO_QUERY_OWNER_RUNBOOK.md](HOLO_QUERY_OWNER_RUNBOOK.md).

Scope note: this owner is wired for the listed RedDog operational consumers.
The legacy `src/holo_tools.py` MCP surface still opens the HoloIndex store
directly and remains a registered migration item; Phase 1 does not claim that
all repository consumers cross this boundary. Normal cleanup is bounded, and
auto-owned v0.4.21+ children terminate when their exact supervisor process exits.
Manually launched and pre-v0.4.21 owners do not inherit that parent-death proof.

---

## Tool Reference

### Repo Perception

#### `get_repo_tree(path=".", depth=3)`

Get directory tree structure.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| path | str | "." | Relative path to start |
| depth | int | 3 | Max traversal depth |

#### `read_file(path)`

Read file content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | str | Yes | Relative file path |

**Limits:** 200KB max, blocked patterns filtered

#### `search_repo(query, path=".", top_k=20)`

Search repository using ripgrep.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search regex |
| path | str | "." | Search scope |
| top_k | int | 20 | Max results |

#### `get_recent_changes(limit=50)`

Get git commit history.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 50 | Max commits |

---

### Documentation Access

#### `get_wsp_docs()`

List all WSP protocol documents.

#### `get_module_docs(module_name)`

Get module README.md.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| module_name | str | Yes | Module name |

#### `get_interface_doc(module_name)`

Get module INTERFACE.md.

#### `get_test_docs(module_name)`

Get module test documentation.

#### `get_modlog(limit=20)`

Get recent ModLog entries from root and key modules.

#### `get_violations(limit=20)`

Get known WSP violations and audit issues.

---

### Overseer Perception

#### `get_mission_history(limit=20)`

Get AI Overseer mission records.

**Sources:** SQLite `overseer.db`, JSONL history

#### `get_pattern_memory(limit=50)`

Get learned patterns (WSP 48).

**Sources:** `adaptive_learning/*.json`

#### `get_overseer_status()`

Get current Overseer system status.

**Returns:**
```python
{
    "available": bool,
    "db_exists": bool,
    "pattern_memory_exists": bool,
    "security_monitor_active": bool,
    "wsp_audit_status": {...},
    "last_mission": {...},
}
```

#### `get_coordination_state()`

Get active teams and recent phases.

#### `get_known_failure_patterns(limit=30)`

Get error patterns for avoidance.

---

### Dependency Perception (v1.1)

#### `get_module_dependencies(module_name, include_external=True, max_depth=1)`

Get dependencies for a FoundUps module.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| module_name | str | - | Module name (e.g., "ai_overseer") |
| include_external | bool | True | Include external package dependencies |
| max_depth | int | 1 | Depth of internal dependency traversal |

**Returns:**
```python
{
    "module": str,
    "module_path": str,
    "files_analyzed": int,
    "internal_dependencies": [
        {"module": str, "imported_by": [str], "import_count": int, "confidence": str}
    ],
    "external_dependencies": [
        {"package": str, "imported_by": [str], "import_count": int}
    ],
    "declared_requirements": [str],
}
```

**Confidence values:** `direct_import`, `manifest_declared`, `search_inferred`

#### `get_reverse_dependencies(module_name, search_scope="modules")`

Find modules that depend on the specified module (blast radius analysis).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| module_name | str | - | Module to find dependents of |
| search_scope | str | "modules" | Scope: "modules" or "all" |

**Returns:**
```python
{
    "module": str,
    "dependents": [
        {"module": str, "import_details": [...], "import_count": int}
    ],
    "dependent_count": int,
    "blast_radius": str,  # "isolated", "low", "medium", "high", "critical"
}
```

---

### Diff Perception (v1.1)

#### `get_file_diff(path, commit_range=None)`

Get diff for a specific file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| path | str | - | Relative file path |
| commit_range | str | None | Git commit range (e.g., "HEAD~3..HEAD") |

**Behavior:**
- If `commit_range` provided: diff across that range
- If omitted: working tree vs HEAD

**Returns:**
```python
{
    "path": str,
    "commit_range": str,
    "has_changes": bool,
    "diff": str,  # Truncated if > 500 lines or 100KB
    "stats": {"additions": int, "deletions": int, "total_changes": int},
    "truncated": bool,
    "commit_info": [{"hash": str, "author": str, "message": str}],
}
```

**Security:** Blocks .env, credentials, secrets, .pem, .key files

#### `get_diff_summary(commit_range, path=".", group_by_module=True)`

Get summary of changes across a commit range.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| commit_range | str | - | Git commit range |
| path | str | "." | Scope path |
| group_by_module | bool | True | Group files by module/domain |

**Returns:**
```python
{
    "commit_range": str,
    "commit_count": int,
    "files_changed": int,
    "overall_stats": {"files_changed": int, "insertions": int, "deletions": int},
    "changed_files": [{"path": str, "status": str}],
    "grouped_by_module": {"domain/module": [str]},
    "commit_messages": [str],
}
```

---

### Impact Prediction (v1.2)

#### `get_change_impact_score(target_type, target)`

Compute blast-radius and risk score for a change target.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| target_type | str | Yes | "module", "file", "diff", or "commit_range" |
| target | str | Yes | Module name, file path, or commit range |

**Returns:**
```python
{
    "target_type": str,
    "target": str,
    "affected_modules": [
        {
            "module": str,
            "risk_weight": float,  # 1.0 = base, higher = more critical
            "is_primary": bool,    # Directly changed vs reverse dep
            "is_critical": bool,   # In CRITICAL_MODULES list
            "internal_dep_count": int,
        }
    ],
    "risk_level": "low" | "medium" | "high" | "critical",
    "risk_score": float,  # 0-1 composite score
    "risk_factors": [str],  # Explanations for risk level
    "test_coverage": {
        "covered": int,
        "total": int,
        "gaps": [str],  # Module names without tests
        "coverage_ratio": float,
    },
    "prior_failures": [
        {
            "pattern": str,
            "last_seen": str,
            "frequency": int,
        }
    ],
    "confidence": float,  # 0-1 based on data completeness
    "confidence_factors": [str],  # What reduced confidence
}
```

**Risk Level Thresholds:**
- `low`: score < 0.3
- `medium`: score 0.3-0.5
- `high`: score 0.5-0.7
- `critical`: score >= 0.85

**Risk Factors Considered:**
1. Number of affected modules (0-0.3)
2. Critical module involvement (0-0.25)
3. Test coverage gaps (0-0.25)
4. Prior failure patterns (0-0.2)

**Critical Modules** (elevated risk weight):
- shared_utilities (1.5x)
- database (1.4x)
- wre_core (1.3x)
- ai_overseer (1.2x)
- foundups_selenium (1.2x)

**Confidence Reduction:**
- No test coverage data: -0.2
- No prior failure data: -0.15
- HoloIndex not available: -0.1
- Many affected modules (>10): -0.1
- Limited dependency resolution: -0.1

---

### HoloIndex Recall (v1.3)

#### `holo_search(query, scope="all", top_k=10)`

Semantic search across the repository using HoloIndex.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search query |
| scope | str | "all" | Filter: "all", "code", "wsp", "test", "skill" |
| top_k | int | 10 | Maximum results |

**Returns:**
```python
{
    "query": str,
    "scope": str,
    "hits": [
        {
            "type": "code" | "wsp" | "test" | "skill",
            "path": str,
            "relevance": float,  # 0-1 semantic similarity
            "preview": str,
        }
    ],
    "hit_count": int,
    "fallback_note": str,  # Present if using ripgrep fallback
}
```

**Fallback:** Uses ripgrep text search if HoloIndex unavailable.

#### `holo_related(target, relation_type="all", limit=10)`

Find modules related to target via multiple signals.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| target | str | - | Module name or file path |
| relation_type | str | "all" | "dependency", "co_change", "failure", "all" |
| limit | int | 10 | Maximum results |

**Returns:**
```python
{
    "target": str,
    "relation_type": str,
    "related": [
        {
            "module": str,
            "relation": "depends_on" | "depended_by" | "semantic_similar" | "co_changed",
            "strength": float,  # 0-1 relation strength
        }
    ],
    "related_count": int,
    "sources_used": [str],  # e.g., ["dependencies", "holoindex_semantic", "co_change"]
}
```

**Sources:** Dependency graph, HoloIndex semantic search, git co-change analysis.

#### `holo_failure_memory(query, limit=10)`

Recall failure patterns from memory.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Search query for failures |
| limit | int | 10 | Maximum results |

**Returns:**
```python
{
    "query": str,
    "failures": [
        {
            "pattern": str,
            "module": str,
            "last_seen": str,
            "frequency": int,
            "severity": str,
            "source": "adaptive_learning" | "holoindex" | "modlog",
        }
    ],
    "failure_count": int,
    "sources_used": [str],
}
```

**Sources:** AI Overseer adaptive learning, HoloIndex, ModLog scanning.

#### `holo_pattern_search(query, limit=10)`

Search learned patterns.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | - | Pattern search query |
| limit | int | 10 | Maximum results |

**Returns:**
```python
{
    "query": str,
    "patterns": [
        {
            "name": str,
            "type": "learned_pattern" | "012_pattern" | "wsp_pattern",
            "data_preview": str,
            "relevance": float,
        }
    ],
    "pattern_count": int,
    "sources_used": [str],
}
```

**Sources:** adaptive_learning/*.json, ChromaDB PatternMemory, WSP protocols.

#### `holo_task_packet(task_description, include_patterns=True, include_failures=True)`

Assemble context packet for a task.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| task_description | str | - | Description of the task |
| include_patterns | bool | True | Include relevant patterns |
| include_failures | bool | True | Include failure warnings |

**Returns:**
```python
{
    "task": str,
    "relevant_modules": [
        {"module": str, "path": str, "relevance": float}
    ],
    "relevant_docs": [
        {"module": str, "doc_type": str, "excerpt": str}
    ],
    "relevant_patterns": [...],
    "known_risks": [
        {"risk": str, "module": str, "severity": str}
    ],
    "suggested_wsp": [
        {"title": str, "path": str, "summary": str}
    ],
    "confidence": float,  # 0-1 based on data completeness
}
```

**Use case:** Pre-task context assembly for better prompts.

---

### Signal Normalization (v1.4)

#### `get_overseer_summary()`

Get compressed overseer situational awareness.

**Returns:**
```python
{
    "top_concerns": [
        {"type": str, "summary": str, "severity": str}
    ],
    "mission_activity": {
        "total": int,
        "by_status": dict,
        "completion_rate": float,
    },
    "failure_clusters": [...],
    "hot_modules": [...],
    "system_posture": "stable" | "degraded" | "critical" | "drifting" | "unmonitored",
    "recommended_focus": [...],
}
```

**Confidence sources:** overseer_status, mission_history, failure_patterns, hot_modules, recommended_focus

#### `get_hot_modules(limit=10)`

Get modules ranked by recent volatility and risk.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum modules to return |

**Returns:**
```python
{
    "modules": [
        {
            "module": str,
            "heat_score": float,  # Heuristic score
            "factors": [str],     # What contributed to score
            "change_count": int,
            "failure_count": int,
            "dependency_count": int,
            "is_critical": bool,
        }
    ],
    "total_scored": int,
    "scoring_note": str,
}
```

**Scoring inputs:** change frequency, critical module status, failure association, dependency centrality

#### `get_repeated_failures(limit=10)`

Get clustered recurring failure patterns.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum clusters to return |

**Returns:**
```python
{
    "clusters": [
        {
            "signature": str,
            "count": int,
            "total_frequency": int,
            "modules": [str],
            "last_seen": str,
            "severity": str,
            "samples": [...],
        }
    ],
    "total_clusters": int,
    "total_failures_analyzed": int,
}
```

**Sources:** known_failures, holo_failure_memory

#### `get_active_risks(limit=10)`

Get normalized active risk objects.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum risks to return |

**Returns:**
```python
{
    "risks": [
        {
            "risk_type": str,  # See taxonomy below
            "scope": str,
            "severity": "low" | "medium" | "high" | "critical",
            "confidence": float,
            "evidence_sources": [str],
            "why_it_matters": str,
        }
    ],
    "total_risks": int,
    "risk_taxonomy": [str],
}
```

**Risk taxonomy:**
- `regression_risk`: Risk of breaking existing functionality
- `coordination_risk`: Risk from multi-agent coordination
- `dependency_risk`: Risk from module dependency chains
- `repeated_failure_risk`: Risk from recurring failure patterns
- `drift_risk`: Risk from state or architecture drift
- `context_gap_risk`: Risk from incomplete information

#### `get_recommended_focus(limit=10)`

Get prioritized next-action recommendations.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 10 | Maximum items to return |

**Returns:**
```python
{
    "focus_items": [
        {
            "focus": str,           # What to do
            "why_now": str,         # Why it's urgent
            "priority": int,        # 1=critical, 2=high, 3=medium, 4=low
            "suggested_context": [str],  # Modules/files to load
        }
    ],
    "total_items": int,
    "priority_note": str,
}
```

#### `get_prompt_context_packet(task_description=None)`

Assemble compressed context for Windsurf prompt.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| task_description | str | None | Optional task for relevance filtering |

**Returns:**
```python
{
    "system_posture": str,
    "hot_modules": [{"module": str, "score": float}],
    "active_risks": [{"type": str, "scope": str, "severity": str}],
    "repeated_failures": [{"signature": str, "count": int}],
    "recommended_focus": [{"focus": str, "priority": int}],
    "suggested_files": [str],
    "suggested_wsp": [{"title": str, "path": str}],
    "task_relevance": {
        "task": str,
        "relevant_modules": [str],
        "suggested_wsp": [str],
    } | None,
}
```

**Use case:** Auto-prepare state for next Windsurf prompt. Answers: what should I worry about? what is unstable? what should I load first?

---


### RedDog Context Tools (v1.5)

#### `get_reddog_state()`

Retrieve current RedDog external state snapshot including active worker lanes, open research threads, recent slice lineage, and live Git HEAD commit/branch.

**Returns:**
```python
{
    "status": "ok",
    "data": {
        "git": {"commit": str, "branch": str},
        "state_dir_exists": bool,
        "active_context_summary": str,
        "active_research_threads": str,
        "work_to_work_lineage": str,
    },
    "meta": {"source": "reddog"}
}
```

#### `get_reddog_analysis_context(prompt, target_module=None)`

Assemble grounded RedDog contextual evidence packet for 0102 analysis (read-only context assembly).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| prompt | str | - | Task or problem statement to assemble context for |
| target_module | str | None | Optional module name to scope documentation |

**Returns:**
```python
{
    "status": "ok",
    "data": {
        "prompt": str,
        "target_module": str | None,
        "git_state": {"commit": str, "branch": str},
        "system_posture": str,
        "active_context": str,
        "module_doc_snippet": str | None,
    },
    "meta": {"source": "reddog_context", "prompt": str}
}
```

---

### FastMCP Remote SSE Server (v1.5)

Exposes strictly allowlisted perception tools over SSE transport with fail-closed Bearer authentication and truthful protocol readiness canary.

```python
from modules.infrastructure.foundups_mcp_bridge.src.mcp_server import (
    REMOTE_READ_ONLY_ALLOWLIST,
    build_mcp_server,
    build_asgi_app,
)
from modules.infrastructure.foundups_mcp_bridge.scripts.launch import (
    run_mcp_bridge_sse,
    stop_mcp_bridge_sse,
    get_mcp_bridge_status,
    verify_mcp_readiness,
)
```

- `REMOTE_READ_ONLY_ALLOWLIST`: Frozen tuple of 33 pure read-only perception tools. Mutation/dispatch tools are strictly omitted.
- `build_mcp_server(repo_root=None)`: Builds FastMCP server registering only allowlisted perception tools.
- `run_mcp_bridge_sse(host=None, port=None, auth_token=None, require_auth=None, repo_root=None, blocking=True)`: Runs SSE server with instance lock invariant and protocol readiness canary.
- `stop_mcp_bridge_sse(timeout_sec=5.0)`: Centralized idempotent stop. Signals shutdown, waits for termination, and releases lock only upon confirmed server exit.
- `verify_mcp_readiness(host, port, auth_token=None, timeout_sec=15.0)`: Protocol canary verifying initialize -> tools/list validation -> safe tool call envelope parsing.

### Execution Stubs (v1 Disabled)

These tools return `{"status": "disabled_in_v1"}` with schema information.

| Tool | Future Use |
|------|------------|
| `coordinate_mission` | WSP 77 agent coordination |
| `spawn_agent_team` | WSP 54 team creation |
| `trigger_skill` | WRE skill dispatch |
| `write_file` | Audited file writes |
| `create_branch` | Git branch creation |
| `create_pr` | PR creation |

---

## Response Format

### Success
```python
{
    "status": "ok",
    "data": Any,
    "meta": {
        "timestamp": "ISO8601",
        "source": str,
        # tool-specific metadata
    }
}
```

### Error
```python
{
    "status": "error",
    "error": str,
    "meta": {...}
}
```

### Disabled (v1)
```python
{
    "status": "disabled_in_v1",
    "error": "Tool 'X' is disabled in v1...",
    "data": {
        "tool": str,
        "schema": Dict  # Parameter/return schema
    }
}
```

---

## Security Constraints

- Path allowlist enforced
- .env, credentials, secrets blocked
- 200KB file size limit
- No write operations
- No execution
