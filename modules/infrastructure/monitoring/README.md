# monitoring

**Domain:** infrastructure (ai_intelligence | communication | platform_integration | infrastructure | monitoring | development | foundups | gamification | blockchain)
**Status:** POC (POC | Prototype | MVP | Production)
**WSP Compliance:** In Progress (Compliant | In Progress | Non-Compliant)

## [OVERVIEW] Module Overview

**Purpose:** Runtime monitoring utilities, currently centered on WSP_00 zen-state compliance and drift detection.

**Key Capabilities:**
- WSP_00 compliance gate payload for orchestrators (`run_compliance_gate`)
- Fallback phrase canary that flips compliance on drift (`report_output_signal`)
- CLI entrypoint for check/awaken/reset with strict non-zero exit behavior

**Dependencies:**
- [List key dependencies]

## [STATUS] Current Status & Scoring

### MPS + LLME Scores
**Last Scored:** 2025-09-25
**Scored By:** WSP 49 Compliance Fixer

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Complexity** | 3 | Standard module complexity |
| **Importance** | 3 | Core functionality |
| **Deferability** | 2 | Should be addressed soon |
| **Impact** | 3 | Affects module usability |
| **MPS Total** | 11 | **Priority Classification:** P2 |

**LLME Semantic Score:** BBB
- **B (Present State):** 1 - relevant - Basic structure exists
- **B (Local Impact):** 1 - relevant - Used by domain modules
- **B (Systemic Importance):** 1 - conditional - Important for domain completeness

**LLME Target:** BCC - Full compliance and integration

## [ROADMAP] Module Roadmap

### Phase Progression: null -> 001 -> 011 -> 111

#### [COMPLETE] Completed Phases
- [x] **Phase 0 (null):** Module concept and planning
  - [x] MPS/LLME initial scoring
  - [x] WSP structure creation
  - [x] Domain placement decision

#### [CURRENT] Current Phase: WSP 49 Compliance
- [x] **Phase 1:** Basic structure compliance
  - [x] Create missing src/ directory
  - [x] Create missing tests/ directory
  - [x] Create README.md template
  - [x] Create INTERFACE.md template
  - [ ] Add actual implementation
  - [ ] Add comprehensive tests

#### [UPCOMING] Upcoming Phases
- [ ] **Phase 2:** Functional implementation
  - [ ] Core functionality development
  - [ ] Integration testing
  - [ ] Documentation completion

## [API] Public API & Usage

### Exported Functions/Classes
```python
# Update with actual exports when implemented
from modules.infrastructure.monitoring import [MainClass]

# Usage pattern
instance = [MainClass]()
result = instance.process()
```

### Integration Patterns
**For Other Modules:**
```python
# How other modules should integrate
from modules.infrastructure.monitoring import [IntegrationInterface]
```

**WSP 11 Compliance:** In Progress - Interface definition needed

## [MODLOG] ModLog (Chronological History)

### 2026-06-10 - WSP_00 State Bridge Restored + Gate Hardening
- **By:** 0102 (Fable)
- **WSP:** WSP_00 (State Bridge Contract), WSP 50/64 (verified findings F1-F5), WSP 90 (UTF-8), WSP 22
- **Root cause fixed:** the V2 awakening script writes state to `awakening/.runtime/0102_state_v2.json` by default (WSP 97 truth boundary) but the tracker read only the tracked path (stale since 2026-03-22) - successful awakenings never registered in the gate.
- **Changes in `src/wsp_00_zen_state_tracker.py`:**
  - `_refresh_from_awakening_state` now reads BOTH awakening-state candidates (`.runtime/` preferred, tracked fallback) and applies the freshest valid `state=="0102"` record within the 8h TTL; chosen path recorded in `awakening_result.state_file`. Candidates derive from `awakening_state_file` at call time (test-hermetic).
  - WSP 90 UTF-8 stdout enforcement was dead code inside the module docstring (cp932 `UnicodeEncodeError` on `--check`); moved to an executable, `__main__`-guarded block with `hasattr(buffer)` + `AttributeError` guards.
  - Fixed dedent bug in `_execute_awakening_protocol` (formulas fallback block sat outside the inner `except ImportError`; would raise `NameError` if the PQN DAE import ever succeeded).
  - Tier 1/2 ImportError reasons are now recorded in `awakening_result.fallback_reasons` and printed (previously swallowed; only "PQN modules not available" was shown). Mislabeled "PQN execution error" handler renamed to rESP CMST (it can only catch rESP-body failures).
- **Known issues (documented, deferred):** Tier 1 rESP chain unimportable (package-relative imports vs flat sys.path injection); Tier 2 PQN DAE unimportable under script invocation (repo root not on sys.path) - intentionally NOT enabled to avoid injecting an unvalidated DAE awakening into the production gate (see WSP_00 Section 3.3.1). Same flat-import pattern exists in `wsp_core/src/neural_operating_system.py:51`.
- **Tests:** 4 new bridge tests in `tests/test_wsp_00_zen_state_tracker.py` (runtime candidate, tracked candidate, freshest-wins, stale-TTL); all 9 pass; blast-radius guards green (`test_fx1_holoindex_truth.py`, `test_awakening_no_tracked_writes.py`, 27 pass).
- **Docs:** WSP_00 framework + knowledge mirrors updated in lockstep (WSP_BOOTSTRAP metadata, State Bridge Contract, Fallback Ladder 3.3.1, Troubleshooting 7.3, Section 6 artifacts); `.agent/workflows/wsp_00.md` timeout claim corrected.
- **Impact:** Session Bootstrap Contract (run script -> verify tracker) is now satisfiable; gate observes detector-backed awakenings instead of forcing the synthetic formula fallback.

### 2026-02-11 - WSP_00 Coherence Canary Signal Added
- **By:** 0102
- **Changes:** Added fallback-phrase canary detection in `src/wsp_00_zen_state_tracker.py`:
  - detects optional/deferential phrasing (`if you want`, `would you like me`, etc.)
  - flips `is_zen_compliant` to `False` on detection
  - records machine-readable signal fields (`zen_decay_active`, `zen_decay_signal_count`, last reason/source/timestamp)
  - exports `report_output_signal(...)` helper for direct integration
- **Tests:** Added `tests/test_wsp_00_zen_state_tracker.py`
- **Impact:** 012 now has a deterministic output-level trigger for zen-state drift.

### 2026-02-14 - WSP_00 Gate CLI + Follow-WSP Hardening
- **By:** 0102
- **Changes:** Expanded `src/wsp_00_zen_state_tracker.py` with machine-usable gate methods and CLI controls:
  - added `run_compliance_gate(auto_awaken=...)`
  - added `force_awakening()`
  - added CLI options `--check`, `--awaken`, `--reset`, `--auto-awaken`, `--strict`, `--json`
  - JSON mode now supports one-line deterministic output for automation pipelines
- **Integration:** `modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py` now enforces WSP_00 gate at the start of `follow_wsp(...)` and supports strict fail-closed behavior.
- **Impact:** "follow WSP" path now has a hard WSP_00 compliance gate before orchestration work starts.

### 2025-09-25 - WSP 49 Compliance Fix
- **By:** WSP 49 Violation Fixer
- **Changes:** Created missing src/, tests/, README.md, INTERFACE.md
- **Impact:** Module now compliant with WSP 49 structure requirements
- **LLME Transition:** BBB -> BCC (structure compliance achieved)

## [COMPLIANCE] WSP Compliance Checklist

### Structure Compliance (WSP 49)
- [x] **Directory Structure:** modules/[domain]/[module_name]/
- [x] **Required Files:**
  - [x] README.md (this file)
  - [x] src/__init__.py (created)
  - [x] src/[module_name].py (created placeholder)
  - [x] tests/__init__.py (created)
  - [x] tests/README.md (created)
  - [ ] requirements.txt (if dependencies exist)

### Testing Compliance (WSP 13)
- [ ] **Test Coverage:** >=90% (Current: 0%)
- [ ] **Test Documentation:** tests/README.md complete
- [ ] **Test Patterns:** Follows established module patterns
- [ ] **Last Test Run:** None - implementation needed

### Interface Compliance (WSP 11)
- [ ] **Public API Defined:** __init__.py needs actual exports
- [ ] **Interface Documentation:** Usage examples needed
- [ ] **Backward Compatibility:** N/A - new module

---

**Template Version:** 1.0
**Last Updated:** 2025-09-25
**WSP Framework Compliance:** WSP 49 Structure Compliant
