# Historical Pattern Memory Universal-Learning Proposal

> **HISTORICAL / SUPERSEDED / NON-AUTHORITATIVE:** This 2025 design proposal
> records an intended universal-learning architecture; it is not the current
> production topology or completion status. The implemented PatternMemory is a
> local SQLite observation/candidate store. It does not prove cross-FoundUp
> replication, universal learning, evaluator/promoter authority, activation,
> rollback, or production RSI. Code snippets, automatic-sharing language, and
> token-savings values below are unverified proposal material. Current authority:
> [README.md](README.md), [INTERFACE.md](INTERFACE.md), and source/tests.

**WSP Compliance**: WSP 48 (Recursive Self-Improvement), WSP 60 (Pattern Memory)

## Overview

This historical proposal envisioned **universal collective learning** across FoundUps through shared false-positive storage. That cross-FoundUp replication and universal-benefit contract is not implemented by the current local SQLite store.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Universal PatternMemory                       │
│              (modules/infrastructure/wre_core/)                  │
│                                                                   │
│  SQLite Database: pattern_memory.db                             │
│  ├── skills_registry_v2.db (skill execution outcomes)           │
│  ├── skill_variations.db (A/B testing results)                  │
│  └── false_positives.db (learned incorrect alerts) ◄── NEW!     │
│                                                                   │
│  API:                                                            │
│  • is_false_positive(type, name) -> bool                        │
│  • record_false_positive(type, name, reason, location)          │
│  • get_false_positive_reason(type, name) -> Dict                │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ Shared Access
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          │                    │                    │
┌─────────▼────────┐  ┌────────▼────────┐  ┌───────▼───────┐
│  AI Overseer     │  │  HoloDAE        │  │ WSP           │
│  (Mission Gate)  │  │  (Result Filter)│  │ Automation    │
│                  │  │                 │  │ (Scan Gate)   │
│  Phase 0:        │  │  Phase 0:       │  │               │
│  Check mission   │  │  Filter search  │  │  Skip known   │
│  false positives │  │  results        │  │  violations   │
└──────────────────┘  └─────────────────┘  └───────────────┘
```

## Integration Points

### 1. AI Overseer - Mission Gating (Sprint 3)

**File**: `modules/ai_intelligence/ai_overseer/src/ai_overseer.py`

**Flow**:
```python
def coordinate_mission(mission_description, mission_type):
    # Phase 0: Check PatternMemory BEFORE spawning agent team
    if self._is_known_false_positive("mission", mission_description):
        return {
            "success": True,
            "skipped": True,
            "reason": "Known false positive (learned from collective intelligence)"
        }

    # Phases 1-4: Run WSP 77 coordination only if NOT a false positive
    team = self.spawn_agent_team(...)
```

**Token Efficiency**: 0 tokens (skipped) vs 2,000-5,000 tokens (4-phase coordination)

**Example**:
```python
# User manually fixes "holo_dae is not a module" issue
overseer.record_false_positive(
    entity_type="mission",
    entity_name="fix holo_dae module structure",
    reason="HoloDAE is a coordinator class, not a standalone module",
    actual_location="holo_index/qwen_advisor/holodae_coordinator.py"
)

# Next session, different 0102 tries same mission
overseer.coordinate_mission("fix holo_dae module structure")
# Returns: {"success": True, "skipped": True} - INSTANT!
```

### 2. HoloDAE - Search Result Filtering (Sprint 4)

**File**: `holo_index/qwen_advisor/holodae_coordinator.py`

**Flow**:
```python
def handle_holoindex_request(query, search_results):
    # Phase 0: Filter false positives BEFORE Qwen analysis
    filtered_results = self._filter_false_positive_results(query, search_results)

    # Qwen only sees relevant results
    qwen_report = self.qwen_orchestrator.orchestrate_holoindex_request(query, filtered_results)
```

**Token Efficiency**: Eliminates irrelevant results from Qwen analysis (200-500 tokens saved per false positive)

**Example**:
```python
# After learning "gotjunk" is not relevant for "telemetry monitor" searches
pattern_memory.record_false_positive(
    entity_type="module",
    entity_name="gotjunk",
    reason="GotJunk is FoundUp app, not infrastructure/monitoring module"
)

# Future HoloIndex searches for infrastructure automatically filter out gotjunk results
```

### 3. WSP Automation - Violation Gating (Sprint 2)

**File**: `modules/infrastructure/wsp_core/src/wsp_compliance_checker.py`

**Flow**:
```python
async def scan():
    for module in modules:
        # Check pattern memory before flagging violation
        if self._is_known_false_positive("module", module.name):
            continue  # Skip learned false positives

        violations.append(WSPViolation(...))
```

**Benefits**: Reduces violation noise, prevents duplicate alerts

**Example**:
```python
# After confirming "holo_dae is intentionally not in modules/"
checker.pattern_memory.record_false_positive(
    entity_type="module",
    entity_name="holo_dae",
    reason="HoloDAE is a coordinator class, not a standalone module",
    actual_location="holo_index/qwen_advisor/holodae_coordinator.py",
    recorded_by="wsp_automation"
)

# Future scans automatically skip this false positive
```

## Database Schema

**Table**: `false_positives`

| Column | Type | Description |
|--------|------|-------------|
| entity_type | TEXT | Type: "mission", "module", "wsp", "file" |
| entity_name | TEXT | Name to match against |
| reason | TEXT | Human-readable explanation |
| actual_location | TEXT | Where entity actually exists (optional) |
| created_at | TEXT | ISO timestamp |
| recorded_by | TEXT | Source: "ai_overseer", "wsp_automation", "holodae", "0102" |

**Primary Key**: (entity_type, entity_name)

## API Reference

### Core Methods

```python
class PatternMemory:
    def is_false_positive(entity_type: str, entity_name: str) -> bool:
        """Check if entity is a known false positive"""

    def record_false_positive(
        entity_type: str,
        entity_name: str,
        reason: str,
        actual_location: Optional[str] = None,
        recorded_by: str = "unknown"
    ) -> None:
        """Record new false positive for collective learning"""

    def get_false_positive_reason(
        entity_type: str,
        entity_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get details about why entity is false positive"""
```

### Integration Helpers

**AI Overseer**:
```python
# Check before mission coordination
if overseer._is_known_false_positive("mission", description):
    return {"skipped": True}

# Record after manual fix
overseer.record_false_positive("mission", description, reason)
```

**HoloDAE**:
```python
# Filter results before Qwen analysis
filtered = coordinator._filter_false_positive_results(query, results)

# Extract module from path and check
module = coordinator._extract_module_from_path(file_path)
if coordinator.pattern_memory.is_false_positive("module", module):
    continue  # Skip this result
```

**WSP Automation**:
```python
# Check before flagging violation
if checker._is_known_false_positive("module", module_name):
    continue  # Skip scan

# Uses PatternMemory directly
if checker.pattern_memory.is_false_positive("module", name):
    logger.info(f"[LEARNED] Skipping {name}")
```

## Collective Learning Benefits

### Token Efficiency

| Operation | Before PatternMemory | After Learning | Savings |
|-----------|---------------------|----------------|---------|
| AI Overseer mission (false positive) | 2,000-5,000 tokens | 0 tokens | 100% |
| HoloDAE search (1 FP result) | +200-500 tokens | 0 tokens | 100% |
| WSP scan (1 FP violation) | +50-100 tokens | 0 tokens | 100% |

**Real-World Impact**: After 10 learned false positives, thousands of tokens saved per session.

### Proposed Universal Sharing (Not Implemented)

```
Session 1 (0102-alpha):
  → Encounters "fix holo_dae module" mission
  → Investigates, realizes holo_dae is not a module
  → Records false positive: "HoloDAE is coordinator class"

Session 2 (0102-beta, same user):
  → Tries same mission
  → PatternMemory: "Known false positive, skipping"
  → INSTANT skip, zero investigation needed

Session 3 (0102-gamma, different user, same codebase):
  → WSP scan flags "missing holo_dae in modules/"
  → PatternMemory: "Known false positive, skipping"
  → Clean scan, zero noise
```

### Cross-FoundUp Learning

```
FoundUp: GotJunk (e-commerce app)
  → Records: "gotjunk module is app-specific, not infrastructure"

FoundUp: WhackAMagat (game)
  → Records: "whack_a_magat module is game-specific, not monitoring"

FoundUp: LiveChat (YouTube integration)
  → Records: "livechat module is platform-specific, not AI intelligence"

Infrastructure searches ("telemetry monitor", "wsp compliance"):
  → Automatically skip ALL app-specific modules
  → Only surface infrastructure/monitoring results
```

## Pre-Seeded False Positives

**Location**: `modules/infrastructure/wre_core/src/pattern_memory.py:208`

```python
# Initial seeds (from real 0102 discoveries)
[
    {
        "entity_type": "module",
        "entity_name": "holo_dae",
        "reason": "HoloDAE is a coordinator class, not a standalone module",
        "actual_location": "holo_index/qwen_advisor/holodae_coordinator.py",
    }
]
```

## Integration Testing

```python
# Test AI Overseer integration
overseer = AIIntelligenceOverseer(Path('.'))
result = overseer.coordinate_mission("fix holo_dae module")
assert result["skipped"] is True
assert "false positive" in result["reason"].lower()

# Test HoloDAE integration
coordinator = HoloDAECoordinator()
results = coordinator._filter_false_positive_results(
    query="telemetry monitor",
    search_results={"code": [{"file": "modules/foundups/gotjunk/..."}]}
)
assert len(results["code"]) == 0  # Filtered out gotjunk

# Test WSP Automation integration
checker = WSPComplianceChecker()
violations = await checker.scan()
assert not any(v.affected_files[0].contains("holo_dae") for v in violations)
```

## Observability

**Logging Pattern**:
```
[AI-OVERSEER] [LEARNED] Skipping known false positive: fix holo_dae module
  Reason: HoloDAE is a coordinator class, not a standalone module
  Actual location: holo_index/qwen_advisor/holodae_coordinator.py

[HOLODAE] [LEARNED] Filtered 1 false positive results (3 relevant results remain)

[WSP-CHECKER] [LEARNED] Skipping known false positive: holo_dae
  Reason: HoloDAE is a coordinator class
```

**Metrics** (via HoloDAE telemetry):
```json
{
  "event": "pattern_memory_filter",
  "entity_type": "module",
  "entity_name": "holo_dae",
  "filtered_count": 1,
  "tokens_saved": 300
}
```

## Future Extensions

1. **Confidence Scores**: Track how often false positive is encountered
2. **Expiry**: Auto-remove false positives after N days without encounters
3. **Collaborative Voting**: Multiple 0102 agents vote on false positive validity
4. **Pattern Generalization**: Learn "all *_dae coordinators are not modules"
5. **Cross-Repo Sharing**: Export/import false positives between FoundUps repos

## WSP Compliance

- **WSP 48**: Recursive self-improvement through pattern storage
- **WSP 60**: SQLite persistence for pattern memory
- **WSP 77**: Agent coordination efficiency (skip false positive missions)
- **WSP 48**: Historical collective-intelligence aspiration; universal sharing is not implemented

## Related Documentation

- [PatternMemory README](README.md#pattern-memory)
- [WSP 48: Recursive Self-Improvement](../../../WSP_framework/src/WSP_48_Recursive_Self_Improvement.md)
- [AI Overseer Integration](../../ai_intelligence/ai_overseer/README.md)
- [HoloDAE Architecture](../../../holo_index/docs/README.md)

---

**Last Updated**: 2025-12-01
**Historical planning record**: Sprints 1 (Recon), 2 (Architecture), 3 (AI Overseer), 4 (HoloDAE), 5 (Docs)
**Current status**: Superseded proposal; universal production integration is not implemented
