# Metrics Ingestion Critical Fixes

> **Historical issue record — non-authoritative.**
> This 2025 diagnosis is retained for provenance and neither declares the issue
> current nor proves it resolved. Re-verify current code and tests before using
> any claim here for production admission or promotion.

**Date**: 2025-10-20
**Priority**: CRITICAL - Must fix before production use
**Reviewer Findings**: 0102_gpt feedback

---

## Issue 1: INSERT OR REPLACE Overwrites All Fields

### Problem
Current `metrics_ingest.py` uses single `execution_metrics` table with `INSERT OR REPLACE`.
When fidelity, outcome, and performance metrics arrive for same `execution_id`, they overwrite each other:

```sql
-- Fidelity insert
INSERT OR REPLACE INTO execution_metrics (execution_id, pattern_fidelity, ...)

-- Outcome insert (WIPES fidelity fields!)
INSERT OR REPLACE INTO execution_metrics (execution_id, decision, correct, ...)

-- Performance insert (WIPES everything again!)
INSERT OR REPLACE INTO execution_metrics (execution_id, execution_time_ms, ...)
```

**Result**: Only last metric type survives. Promotion checks fail silently.

### Solution
**Split into separate tables** (implemented in `metrics_ingest_v2.py`):

```sql
CREATE TABLE fidelity_metrics (
    execution_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    pattern_fidelity REAL NOT NULL,
    patterns_followed INTEGER NOT NULL,
    patterns_missed INTEGER NOT NULL,
    ...
)

CREATE TABLE outcome_metrics (
    execution_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    correct BOOLEAN NOT NULL,
    ...
)

CREATE TABLE performance_metrics (
    execution_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    exception BOOLEAN NOT NULL,
    ...
)
```

**Benefits**:
- No field conflicts
- Each metric type preserved independently
- Can query specific metric types efficiently
- JOIN when need combined view

---

## Issue 2: Promotion Gating Missing Integrity Checks

### Problem
`skills_registry.py::check_promotion_readiness()` queries `execution_metrics` assuming all fields present.
With current bug, can get:
- Fidelity: 0 rows
- Outcomes: 0 rows
- Performance: 100 rows

**Query returns**: `ready=True` (100 executions found!)

**Reality**: Zero fidelity/outcome data, promotion invalid.

### Solution
Add **metric type coverage checks**:

```python
def _check_staged_to_production(self, skill_name: str) -> Dict[str, Any]:
    # Check ALL metric types present
    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM fidelity_metrics WHERE skill_id = ?) as fidelity_count,
            (SELECT COUNT(*) FROM outcome_metrics WHERE skill_id = ?) as outcome_count,
            (SELECT COUNT(*) FROM performance_metrics WHERE skill_id = ?) as perf_count
    """, (skill_name, skill_name, skill_name))

    counts = cursor.fetchone()

    # All three must have ≥100 samples
    if counts["fidelity_count"] < 100:
        return {"ready": False, "reason": f"Insufficient fidelity metrics: {counts['fidelity_count']}/100"}
    if counts["outcome_count"] < 100:
        return {"ready": False, "reason": f"Insufficient outcome metrics: {counts['outcome_count']}/100"}
    if counts["perf_count"] < 100:
        return {"ready": False, "reason": f"Insufficient performance metrics: {counts['perf_count']}/100"}

    # Now safe to check quality thresholds...
```

---

## Issue 3: Missing Human Approval Tracking

### Problem
Policy mandates human sign-offs (WSP 50 checklist), but SQLite schema has NO columns for:
- Approver identity
- Checklist completion status
- Dependency validation proofs
- Approval timestamps

`promotion_events` table only stores result, not process.

### Solution
Add **approval tracking table**:

```sql
CREATE TABLE approval_checklists (
    approval_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL,
    promotion_path TEXT NOT NULL,  -- "prototype->staged", "staged->production"
    approver TEXT NOT NULL,  -- "0102"
    approval_ticket TEXT NOT NULL,

    -- WSP 50 checks
    wsp_50_no_duplication BOOLEAN NOT NULL,
    wsp_50_evidence TEXT,  -- HoloIndex search results proving no duplication

    -- Test coverage
    test_coverage_complete BOOLEAN NOT NULL,
    test_evidence TEXT,  -- Test execution logs

    -- Instruction clarity
    instruction_clarity_approved BOOLEAN NOT NULL,

    -- Dependencies
    dependencies_validated BOOLEAN NOT NULL,
    dependency_evidence TEXT,  -- List of validated data stores/MCP endpoints

    -- Security
    security_reviewed BOOLEAN NOT NULL,
    security_notes TEXT,

    -- Production-specific (nullable for prototype->staged)
    production_readiness BOOLEAN,
    integration_approved BOOLEAN,
    monitoring_configured BOOLEAN,
    rollback_tested BOOLEAN,

    approval_timestamp TIMESTAMP NOT NULL,
    notes TEXT,

    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
)
```

**Promotion gate enhancement**:
```python
def _check_prototype_to_staged(self, skill_name: str) -> Dict[str, Any]:
    cursor.execute("""
        SELECT * FROM approval_checklists
        WHERE skill_id = ? AND promotion_path = 'prototype->staged'
        ORDER BY approval_timestamp DESC LIMIT 1
    """, (skill_name,))

    approval = cursor.fetchone()
    if not approval:
        return {"ready": False, "reason": "No human approval record found - WSP 50 checklist required"}

    # Verify all checks passed
    if not approval["wsp_50_no_duplication"]:
        return {"ready": False, "reason": "WSP 50 check failed: duplication not verified"}

    # ... check all other fields ...
```

---

## Issue 4: Holo Re-Index Not Automated

### Problem
Promotion/rollback policy says "re-index HoloIndex after state change" but:
- No code actually calls `python holo_index.py --reindex-skills`
- No WSP 22 ModLog updates
- No tracking of what changed

### Solution
Add **re-index automation** to `WRESkillsRegistry`:

```python
def trigger_holo_reindex(self, reason: str, changed_skills: List[str]) -> None:
    """
    Trigger HoloIndex re-index and update ModLog

    Args:
        reason: Why re-index needed (promotion/rollback)
        changed_skills: List of skills that changed state
    """
    import subprocess
    from datetime import datetime

    # Run HoloIndex re-index
    result = subprocess.run(
        ["python", "holo_index.py", "--reindex-skills"],
        capture_output=True,
        text=True,
        cwd=self.repo_root
    )

    if result.returncode != 0:
        logger.error(f"[HOLO-REINDEX] Failed: {result.stderr}")
        raise RuntimeError(f"HoloIndex re-index failed: {result.stderr}")

    # Update ModLog (WSP 22)
    modlog_path = self.repo_root / "modules/infrastructure/wre_core/ModLog.md"
    modlog_entry = f"""
## {datetime.now().strftime("%Y-%m-%d %H:%M")} - Skills {reason}

**Skills Changed**: {', '.join(changed_skills)}
**Action**: HoloIndex re-indexed to reflect skill state changes
**Reason**: {reason}

"""

    with open(modlog_path, 'a', encoding='utf-8') as f:
        f.write(modlog_entry)

    logger.info(f"[HOLO-REINDEX] Complete for {len(changed_skills)} skills")
```

**Call from promoter**:
```python
# After successful promotion
registry.trigger_holo_reindex(
    reason=f"Promotion: {skill_name} {from_state}->{to_state}",
    changed_skills=[skill_name]
)
```

---

## Issue 5: Concurrent Write Safety

### Problem
`metrics_append.py` assumes single-process writes. With multiple DAEs appending concurrently:
- Line interleaving possible
- JSON corruption risk

### Solution
Add **file locking**:

```python
import portalocker  # pip install portalocker

def _append_to_file(self, filename: str, metric: Dict[str, Any]) -> None:
    filepath = self.metrics_dir / filename

    try:
        with portalocker.Lock(filepath, mode='a', encoding='utf-8', timeout=5) as f:
            json.dump(metric, f, ensure_ascii=False)
            f.write('\n')
    except portalocker.LockException:
        logger.error(f"[METRICS-APPEND] Lock timeout on {filename}")
        raise
    except Exception as e:
        logger.error(f"[METRICS-APPEND] Failed: {e}")
        raise
```

**Fallback for Windows** (if portalocker unavailable):
```python
import msvcrt
import os

with open(filepath, 'a', encoding='utf-8') as f:
    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    try:
        json.dump(metric, f, ensure_ascii=False)
        f.write('\n')
    finally:
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
```

---

## Issue 6: Example Code in Production Files

### Problem
Both `metrics_append.py` and `skills_registry.py` have `if __name__ == "__main__":` blocks that execute demos.
These create sample metrics in production directories.

### Solution
**Remove or guard**:

```python
# Option 1: Remove completely (recommended)
# Delete the entire if __name__ == "__main__": block

# Option 2: Add environment guard
if __name__ == "__main__":
    import os
    if os.getenv("WRE_ALLOW_EXAMPLES") != "1":
        print("[SKIP] Set WRE_ALLOW_EXAMPLES=1 to run examples")
        sys.exit(0)

    # ... example code ...
```

---

## Issue 7: skills_registry.json Hardcoded Timestamp

### Problem
`"last_updated": "2025-10-20T00:00:00Z"` is hardcoded, never updates.
Can't audit when registry changed.

### Solution
**Auto-update on save**:

```python
def save_registry_json(self, registry: Dict[str, Any]) -> None:
    from datetime import datetime

    # Update timestamp
    registry["last_updated"] = datetime.utcnow().isoformat() + "Z"

    with open(self.registry_json, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    logger.info(f"[REGISTRY] Updated: {registry['last_updated']}")
```

---

## Implementation Priority

1. **CRITICAL (Fix immediately)**:
   - Issue 1: Separate tables (breaks promotion if not fixed)
   - Issue 2: Integrity checks (silent failures)
   - Issue 3: Approval tracking (WSP 50 compliance)

2. **HIGH (Fix before production)**:
   - Issue 4: Holo re-index automation
   - Issue 5: File locking
   - Issue 7: Timestamp updates

3. **MEDIUM (Fix before release)**:
   - Issue 6: Remove example code

---

## Migration Path

1. Create `metrics_ingest_v2.py` with separate tables
2. Add `approval_checklists` table to schema
3. Update `skills_registry.py` with integrity checks
4. Add `trigger_holo_reindex()` method
5. Test with synthetic metrics
6. Migrate existing JSON (if any)
7. Deprecate `metrics_ingest.py` (v1)

---

**Status**: Documentation complete, implementation pending
**Next**: Create fixed versions of affected files
