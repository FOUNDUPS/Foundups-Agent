# WSP 62 Refactoring Plan: ai_overseer.py

> **2026-06-07 NOTE (AI_OVERSEER_AUTOFIX_SHELL_EXEC_REMEDIATION_PHASE1):** the
> `src/auto_fix_engine.py` referenced below was DELETED as a dead/stale duplicate
> (0 production imports; carried a `shell=True` auto-fix path). The auto-fix surface
> is now the typed, allowlisted, `shell=False` `src/autofix_executor.py`. References
> to `auto_fix_engine` / `AutoFixEngine` in this plan are historical and no longer
> apply.

**Status:** In Progress
**Date:** 2025-12-19
**Violation:** 1833 lines (333 lines over 1500 critical window)
**Target:** < 1200 lines (OK threshold)
**Strategy:** Module Splitting (WSP 62 Section 3.3.2)

## Current Analysis

### File Size Breakdown
- **Total Lines:** 1833
- **Largest Methods:**
  1. `_apply_auto_fix()` - 365 lines (HUGE!)
  2. `monitor_daemon()` - 177 lines
  3. `__init__()` - 106 lines
  4. `_announce_to_chat()` - 85 lines
  5. `spawn_agent_team()` - 66 lines

### Functional Groups
1. **Auto-Fix System** (~450 lines):
   - `_apply_auto_fix()` (365 lines) - Apply Qwen-generated fixes
   - `_qwen_classify_bugs()` (39 lines) - Bug classification
   - `_verify_unicode_patch()` (47 lines) - Patch verification

2. **Daemon Monitoring** (~200 lines):
   - `monitor_daemon()` (177 lines) - Main monitoring loop
   - Related state tracking and logging

3. **Mission Orchestration** (~250 lines):
   - `analyze_mission_requirements()` (49 lines)
   - `generate_coordination_plan()` (49 lines)
   - `_generate_mission_phases()` (58 lines)
   - `spawn_agent_team()` (66 lines)
   - `_execute_mission_phases()` (46 lines)
   - `coordinate_mission()` (57 lines)

4. **Chat Integration** (~100 lines):
   - `_announce_to_chat()` (85 lines)

## Refactoring Strategy

### Phase 1: Extract Auto-Fix System
**File:** `src/auto_fix_engine.py` (~450 lines)

**Extractions:**
- `_apply_auto_fix(fix_data, daemon_name, target_module)` - Main auto-fix logic (365 lines)
- `_qwen_classify_bugs(issues)` - Bug classification with Qwen (39 lines)
- `_verify_unicode_patch(file_path)` - Verify patch correctness (47 lines)

**Dependencies:**
- `self.repo_root` (Path)
- `self.patch_executor` (PatchExecutor)
- `self.autonomous_orchestrator` (AutonomousRefactoringOrchestrator)
- Logger

**New Class:** `AutoFixEngine`
```python
class AutoFixEngine:
    def __init__(self, repo_root: Path, patch_executor: PatchExecutor,
                 autonomous_orchestrator, logger):
        self.repo_root = repo_root
        self.patch_executor = patch_executor
        self.autonomous_orchestrator = autonomous_orchestrator
        self.logger = logger

    def apply_auto_fix(self, fix_data: Dict, daemon_name: str,
                       target_module: Optional[str] = None) -> Dict[str, Any]:
        """Apply Qwen-generated auto-fix with safety validation."""
        ...

    def qwen_classify_bugs(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """Classify bugs using Qwen strategic analysis."""
        ...

    def verify_unicode_patch(self, file_path: Path) -> bool:
        """Verify Unicode patch was applied correctly."""
        ...
```

**Integration in AI Overseer:**
```python
from .src.auto_fix_engine import AutoFixEngine

# In __init__:
self.auto_fix_engine = AutoFixEngine(
    repo_root=self.repo_root,
    patch_executor=self.patch_executor,
    autonomous_orchestrator=self.autonomous_orchestrator,
    logger=logger
)

# Replace method calls:
# OLD: result = self._apply_auto_fix(fix_data, daemon_name, target_module)
# NEW: result = self.auto_fix_engine.apply_auto_fix(fix_data, daemon_name, target_module)
```

**Lines Saved:** ~450
**New AI Overseer Size:** 1833 - 450 = ~1383 lines

### Phase 2: Extract Daemon Monitoring
**File:** `src/daemon_monitor.py` (~200 lines)

**Extractions:**
- `monitor_daemon(daemon_name, check_interval)` - Main monitoring loop (177 lines)
- Related state tracking methods

**Dependencies:**
- `self.repo_root`
- `self.autonomous_orchestrator`
- `self.auto_fix_engine` (from Phase 1)
- `self.pattern_memory`
- Logger

**New Class:** `DaemonMonitor`
```python
class DaemonMonitor:
    def __init__(self, repo_root: Path, autonomous_orchestrator,
                 auto_fix_engine, pattern_memory, logger):
        self.repo_root = repo_root
        self.autonomous_orchestrator = autonomous_orchestrator
        self.auto_fix_engine = auto_fix_engine
        self.pattern_memory = pattern_memory
        self.logger = logger

    async def monitor_daemon(self, daemon_name: str,
                            check_interval: int = 300) -> None:
        """Monitor daemon health and apply auto-fixes."""
        ...
```

**Lines Saved:** ~200
**New AI Overseer Size:** 1383 - 200 = ~1183 lines ✅ (under 1200!)

### Phase 3 (Optional): Further Optimization
If needed, extract:
- **Mission Orchestration** (~250 lines) → `src/mission_orchestrator.py`
- **Chat Integration** (~100 lines) → `src/chat_announcer.py`

## Rollback Plan

If refactoring fails:
1. Git revert to current commit
2. Keep extracted modules for reference
3. Document issues in ModLog.md

## Testing Strategy

1. **Unit Tests** (for extracted modules):
   - Test `AutoFixEngine.apply_auto_fix()` with mock patches
   - Test `DaemonMonitor.monitor_daemon()` with mock issues

2. **Integration Tests** (for refactored overseer):
   - Run daemon monitoring cycle
   - Verify auto-fix detection and application
   - Check WSP 77 coordination works

3. **Regression Tests**:
   - Compare monitoring behavior before/after
   - Verify all auto-fix types still work

## Success Criteria

- [ ] ai_overseer.py < 1200 lines (OK threshold)
- [ ] All extracted modules < 800 lines each
- [ ] Zero functional regressions
- [ ] All integration tests pass
- [ ] ModLog.md updated with refactoring documentation
- [ ] Git commit created with refactored code

## Timeline

- **Phase 1** (Auto-Fix Engine): 30-45 min
- **Phase 2** (Daemon Monitor): 30-45 min
- **Testing**: 15-20 min
- **Documentation**: 10 min
- **Total**: ~100 minutes

## WSP Compliance

- **WSP 62:** Large File Refactoring Enforcement
- **WSP 49:** Module Directory Structure (src/ subdirectory)
- **WSP 3:** Functional Distribution
- **WSP 22:** ModLog Updates
- **WSP 50:** Pre-Action Research (HoloIndex search completed)
- **WSP 77:** Agent Coordination (preserved in refactoring)

---

**Next Step:** Begin Phase 1 extraction (Auto-Fix Engine)
