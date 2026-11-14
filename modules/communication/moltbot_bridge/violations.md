# WSP Violations Log - moltbot_bridge

## 2026-07-23: WSP 62 Provider Evidence Review Repair Round 2 - RESOLVED

**Status**: EXACT TEMPORARY NO-GROWTH CEILINGS / REMEDIATION TRACKED

Every touched communication function over 60 lines now has an exact measured
no-growth ceiling with owner, architect reviewer, expiry, and remediation.
The canonical audit matcher now compares `relative_path.as_posix()`, so the
same slash-delimited exemption keys work on Windows and POSIX. A
platform-neutral regression covers both path families; the prior Windows
matching gap is closed.

## 2026-07-23: WSP 62 Provider Evidence Review Repair - RESOLVED

**Status**: TEMPORARY EXEMPTION / REMEDIATION TRACKED

The missing backend-architect source exemption is now explicit, temporary,
review-dated, owner/reviewer assigned, and fixed at the measured 1,618-line
ceiling. The provider contract, audit runtime, architect test, and audit test
ceilings were updated to their exact post-repair sizes. The roadmap separately
tracks provider-store and architect-transaction extraction; no permanent
exemption or unrelated refactor was introduced.

## 2026-07-23: WSP 62 Provider Evidence Review - TEMPORARY CEILINGS RECORDED

**Status**: FOLLOW-UP TRACKED

The phase-2a provider-evidence contract is isolated from OpenClaw/Hermes and
does not add provider logic to root orchestration. Existing legacy audit and
architect integration/test files grew to establish fail-closed parity; their
temporary exact ceilings and the focused contract/store ceiling are recorded
in `wsp_62_exemptions.yaml`. Store extraction and legacy seam decomposition
remain tracked in `ROADMAP.md`; no permanent exemption was added.

## 2026-07-23: inherited create-job contract WSP 62 debt

**Status:** ACTIVE TEMPORARY EXEMPTION

**Owner:** MoltbotBridge

**Exact no-growth ceiling:** `src/foundup_job_contract.py` = 796 lines

**Expiry:** 2026-09-30

**Remediation:** [Create FoundUp job contract WSP62 decomposition](ROADMAP.md#create-foundup-job-contract-wsp62-decomposition)

The contract remains oversized after the nullable create-route fields were
added. The exemption applies only to this inherited file ceiling; it is not a
test exemption and grants no function-ceiling increase.

## 2026-02-07: WSP 95/71 Security Audit - CLEAN

**Auditor**: 0102
**WSP**: 71, 95, 96
**Status**: NO VIOLATIONS

### Audit Scope
Mutating DAE entrypoints checked for scanner gate parity with WSP 95/96 requirements:
- Required mode fail-closed
- Enforced severity threshold
- TTL-bounded cache
- Auditable decision logs

### Findings

**All routes properly gated.** The skill safety gate in `openclaw_dae.py` covers:

| Intent Category | Gate Required | Gate Present | Status |
|-----------------|---------------|--------------|--------|
| COMMAND         | Yes           | Yes          | PASS   |
| SYSTEM          | Yes           | Yes          | PASS   |
| SCHEDULE        | Yes           | Yes          | PASS   |
| SOCIAL          | Yes           | Yes          | PASS   |
| AUTOMATION      | Yes           | Yes          | PASS   |
| FOUNDUP         | Yes           | Yes          | PASS   |
| QUERY           | No (read-only)| N/A          | N/A    |
| MONITOR         | No (read-only)| N/A          | N/A    |
| CONVERSATION    | No (LLM-only) | N/A          | N/A    |

### Architecture Validation

1. **Single entry point**: All skill-driven routes go through `OpenClawDAE.process()`
2. **Gate enforcement**: `_ensure_skill_safety()` called before any mutating route
3. **Downstream coverage**: `fam_adapter.py` and `auto_moderator_bridge.py` are only invoked from `openclaw_dae.py` after gate check
4. **Fail-closed**: Scanner unavailable + required mode = route blocked (WSP 95)
5. **Severity threshold**: Configurable via `OPENCLAW_SKILL_SCAN_MAX_SEVERITY` (default: medium)
6. **TTL cache**: Configurable via `OPENCLAW_SKILL_SCAN_TTL_SEC` (default: 300s)

### Test Coverage

14 tests in `tests/test_skill_safety_guard.py`:
- 7 unit tests for `run_skill_scan()` function
- 7 integration tests for OpenClaw DAE safety gate

All tests passing as of 2026-02-07.

---

*No violations found. Architecture is WSP 95/71 compliant.*
