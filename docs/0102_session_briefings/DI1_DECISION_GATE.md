# DI1 -- GotJunk Extraction Decision Gate

**Date**: 2026-04-18  
**Lane**: D (DE track)  
**Sandbox**: `O:/tmp/de_sandbox/gotjunk_extraction`  
**Target**: GotJunk FoundUp  
**Lifecycle Stage**: proto

---

## WSP 97 Truthfulness Statement

This decision gate records actual state from DE1-DE3 reports. All claims are traceable to sandbox artifacts. No aspirational claims are made.

---

## DE Track Summary

| Phase | Date | Result | Report |
|-------|------|--------|--------|
| DE1 | 2026-04-17 | PASS | `DE_GOTJUNK_EXTRACTION_REPORT.md` (sandbox root) |
| DE2 | 2026-04-18 | NOT READY | `DE2_HERMES_EXTRACTION_SANDBOX_VALIDATION_GATES_PHASE1.md` |
| DE3 | 2026-04-18 | PASS | `DE3_GOTJUNK_EXTRACTION_BOUNDARY_CLEANUP_PHASE1.md` |

### Gate Results (DE3 Final)

| Gate | Result | Evidence |
|------|--------|----------|
| G1 | PASS | No monorepo imports (`grep -rn "from modules\."` returns empty) |
| G2 | PASS | No secrets (regex-only scan) |
| G3 | PASS | 12/12 manifest tests + backend import verification |
| G4 | PASS | Structure complete, no runtime blockers |

### Extraction Metrics

| Metric | Value |
|--------|-------|
| Commits preserved | 239 |
| Extracted size | 2.4 MB |
| Files modified (DE3) | 3 (api.py, liberty_stubs.py, __init__.py) |
| Orphaned imports resolved | 4/4 |

---

## Architect Decision

### DE4: DEFERRED

**Reason**: No immediate consumer for external GotJunk repo. Deploy blocker (`entry_url: null`) is a separate track that must be resolved before GitHub publication provides value.

**Supporting factors**:
1. `lifecycle_stage: proto` -- not yet externalized
2. `entry_url` in manifest is null (deploy blocker pending ops redeploy + CSP verification)
3. No active Hermes consumer requesting external repo discovery
4. Sandbox extraction proves the mechanism works; publication can wait

---

## Trigger Conditions for DE4 Activation

DE4 (GitHub repo creation + push) should be activated when ANY of these conditions are met:

| Trigger | Description |
|---------|-------------|
| T1 | `entry_url` blocker resolved (Cloud Run redeployed, CSP verified) |
| T2 | `lifecycle_stage` upgraded to `externalized` in monorepo manifest |
| T3 | Hermes consumer explicitly requests external GotJunk discovery |
| T4 | Architect directive to proceed despite blockers |

**Gate requirements for DE4**:
- Re-run G1-G4 (may be stale after >7 days)
- Confirm `foundup_manifest.json` has valid `entry_url`
- Verify no new orphaned imports introduced

---

## Sandbox Retention Policy

| Policy | Value |
|--------|-------|
| Location | `O:/tmp/de_sandbox/gotjunk_extraction` |
| Retention | Keep until DE4 activation OR 30 days from 2026-04-18 |
| Expiry date | 2026-05-18 (if no DE4 trigger) |
| Cleanup action | `rm -rf O:/tmp/de_sandbox/gotjunk_extraction` |

**Note**: Sandbox contains working extraction with boundary cleanup. Re-running DE1-DE3 from scratch is low-cost (~10 min) if sandbox expires.

---

## Next Actions When Unblocked

When DE4 trigger conditions are met:

1. **Re-verify gates** (if >7 days stale)
   ```bash
   cd O:/tmp/de_sandbox/gotjunk_extraction
   grep -rn "from modules\." --include="*.py"  # G1
   python -m pytest tests/test_manifest.py -q  # G3
   ```

2. **Create GitHub repo**
   ```bash
   gh repo create FOUNDUPS/gotjunk --public --description "GotJunk FoundUp - Liberty Alert marketplace"
   ```

3. **Add remote and push**
   ```bash
   cd O:/tmp/de_sandbox/gotjunk_extraction
   git remote add origin https://github.com/FOUNDUPS/gotjunk.git
   git push -u origin main
   ```

4. **Verify Hermes discovery**
   - Test external FoundUp contract via MCP Bridge
   - Confirm `foundup_manifest.json` is discoverable

5. **Update monorepo reference**
   - Add external repo pointer to `modules/foundups/gotjunk/README.md`
   - Update lifecycle_stage to `externalized`

---

## Constraint Compliance

| Constraint | Status |
|------------|--------|
| No GitHub repo creation | ✅ DE4 deferred |
| No monorepo edits | ✅ Sandbox only |
| No deploy commands | ✅ entry_url blocker separate track |
| No push | ✅ |

---

## References

- DE1: `O:/tmp/de_sandbox/DE_GOTJUNK_EXTRACTION_REPORT.md`
- DE2: `O:/tmp/de_sandbox/gotjunk_extraction/DE2_HERMES_EXTRACTION_SANDBOX_VALIDATION_GATES_PHASE1.md`
- DE3: `O:/tmp/de_sandbox/gotjunk_extraction/DE3_GOTJUNK_EXTRACTION_BOUNDARY_CLEANUP_PHASE1.md`
- Monorepo briefing: `docs/0102_session_briefings/DE2_HERMES_EXTRACTION_SANDBOX_VALIDATION_GATES_PHASE1.md`

---

**This decision gate closes the DE extraction track until DE4 trigger conditions are met.**
