# WSP Tools - ModLog

## 2026-10-29 — Document actual bulk-tool interfaces

Add the missing INTERFACE for the flagged wrapper-repair script, older hard-coded
bulk remover and orchestration entrypoint. Record mode precedence, return/status
limitations, write effects and the absence of replacement-code validation. The
older tool is not presented as a dry-run alternative, and historical counts are
not refreshed without a real inventory. This is documentation only: no bulk
rewrite, campaign, model invocation or source test was executed. Source/hash and
relative-link review provide the bounded evidence. WSP 11/22/49/50/84/90/97.


## 2026-02-26: WSP 90 Bulk Fix Script

**Issue**: "lost sys.stderr" error during main.py startup
**Root Cause**: 379 modules copy-pasted WSP 90 UTF-8 wrapping pattern at import time. Each re-wrap eventually broke stderr.

**Solution Implemented**:
1. **main.py** sets `FOUNDUPS_UTF8_WRAPPED=1` flag BEFORE wrapping
2. **fix_wsp90_utf8_bulk.py** created to fix modules:
   - Safe mode (default): Fixes non-entrypoint files only (~78 files)
   - Entrypoint mode: Includes `if __name__ == "__main__"` files (~155 additional)
3. **Guard pattern** added to key files:
   ```python
   if sys.platform.startswith('win') and not os.environ.get('FOUNDUPS_UTF8_WRAPPED'):
       sys.stdout = io.TextIOWrapper(...)
       sys.stderr = io.TextIOWrapper(...)
   ```

**Files Fixed (Phase 1 - Safe Mode)**:
- 78 non-entrypoint library modules
- Key files with explicit guards:
  - `modules/infrastructure/cli/src/social_media_menu.py`
  - `modules/infrastructure/cross_platform_memory/src/breadcrumb_trail.py`
  - `modules/infrastructure/cross_platform_memory/src/agent_coordination.py`
  - `modules/infrastructure/cross_platform_memory/src/cross_platform_memory_orchestrator.py`
  - `modules/infrastructure/cross_platform_memory/src/pattern_memory.py`

**Validation**:
- `--dry-run` reports 0 pending in safe mode
- `py_compile` passed on all modified files
- main.py runs cleanly

**Deferred (Phase 2)**:
- 155 entrypoint files - require individual review as they may legitimately need wrapping when run standalone

**WSP References**:
- WSP 90: UTF-8 Encoding Enforcement Protocol (updated with bug fix section)
- WSP 50: Pre-Action Verification (search before modify)

---

## 2025-10-11: Initial WSP 90 Implementation

- Created wsp90_orchestrator.py for UTF-8 compliance checking
- Defined UTF-8 enforcement pattern for Windows
