# BH2 - Branch Hygiene Scope Guard Phase 1

```text
Window: AG5
Slice: BH2
Lane: Process / Git Truth
Branch: feat/bh2-pr-scope-guard
Mode: implementation
Status: complete
```

## Summary

Implements a PR scope guard to prevent mixed-scope PRs from merging. Compares expected files declared in PR body against actual changed files and fails if files outside the declared scope appear.

## Motivation: PR #384 Incident

On 2026-04-19, PR #384 ("docs(rolodex): regenerate artifacts after CF4 file-specific binding") was merged with 11 files, but only 2-3 were actually rolodex-related. The remaining files were DJ-OBS work that entered main via branch contamination.

### What Happened

1. DJ-OBS commits (`fde9d64a4`, `1c0ee3f01`) were created on local main without a branch
2. CF lane worker created `cf/rolodex-artifact-regen-cf4` from that dirty local main
3. PR #384 was pushed and merged, carrying the unrelated DJ commits
4. DJ-OBS work bypassed its own review gate

### Evidence

| Check | Expected | Actual |
|-------|----------|--------|
| PR title | rolodex artifact regen | rolodex artifact regen |
| Expected files | 2-3 rolodex artifacts | 11 files |
| DJ files included | NO | YES |
| DJ-OBS files included | NO | YES |

### Contaminated Files in PR #384

```text
docs/0102_session_briefings/DJ_AI_RESOLUTION_HOOK_CONTRACT_PHASE1.md  <- DJ
holo_index/docs/AGENT_CLI_CATALOG.md                                  <- CF5 (expected)
holo_index/docs/command_rolodex.json                                  <- CF5 (expected)
main.py                                                               <- DJ
modules/ai_intelligence/ai_overseer/ModLog.md                         <- DJ
modules/ai_intelligence/ai_overseer/src/preflight_resolution.py       <- DJ
modules/ai_intelligence/ai_overseer/tests/conftest.py                 <- DJ
modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py <- DJ
modules/platform_integration/antifafm_broadcaster/ModLog.md           <- DJ-OBS
modules/platform_integration/antifafm_broadcaster/src/obs_controller.py <- DJ-OBS
modules/platform_integration/antifafm_broadcaster/tests/test_obs_controller_startup.py <- DJ-OBS
```

## Solution

### 1. PR Scope Guard Script

Location: `tools/pr_scope_guard/pr_scope_guard.py`

Usage:
```bash
# Check a PR by number (fetches from GitHub API)
python tools/pr_scope_guard/pr_scope_guard.py --pr-number 384

# Check with explicit inputs
python tools/pr_scope_guard/pr_scope_guard.py \
  --pr-body "Window: AG5\nSlice: BH2\nExpected files:\n- file1.py" \
  --changed-files file1.py file2.py
```

Exit codes:
- `0` - All changed files are within declared scope
- `1` - Scope violation detected (unexpected files)
- `2` - Missing required PR body fields
- `3` - Parse error or invalid input

### 2. Required PR Body Format

Every PR must include:

```text
Window: [assigned window ID]
Slice: [slice ID]
Lane: [lane name]
Expected files:
- path/to/file1.py
- path/to/file2.py
- path/to/file3.md
```

### 3. Policy (Effective Immediately)

No PR is merge-approved unless:

1. **Branch created from origin/main**
   ```bash
   git fetch origin main
   git checkout -b feat/xyz origin/main
   ```

2. **Scope verified before push**
   ```bash
   git diff --name-only origin/main...HEAD
   # Must match expected files only
   ```

3. **PR body declares expected files**
   - Window, Slice, Lane, Expected files sections required

4. **Actual PR files match expected files**
   - Scope guard validates on PR open/update

## Example: How PR #384 Would Have Failed

If scope guard had been in place:

```text
============================================================
PR SCOPE GUARD REPORT
============================================================
PR: #384
Window: NOT DECLARED
Slice: NOT DECLARED
Lane: NOT DECLARED

PARSE ERRORS:
  - Missing 'Window:' field in PR body
  - Missing 'Slice:' field in PR body
  - Missing 'Expected files:' section in PR body

============================================================
RESULT: FAIL - Missing required PR body fields
============================================================
```

Even if the CF5 worker had declared expected files:

```text
Expected files:
- holo_index/docs/AGENT_CLI_CATALOG.md
- holo_index/docs/command_rolodex.json
```

The guard would have caught:

```text
OUT OF SCOPE (VIOLATION):
  - docs/0102_session_briefings/DJ_AI_RESOLUTION_HOOK_CONTRACT_PHASE1.md
  - main.py
  - modules/ai_intelligence/ai_overseer/ModLog.md
  - modules/ai_intelligence/ai_overseer/src/preflight_resolution.py
  - modules/ai_intelligence/ai_overseer/tests/conftest.py
  - modules/ai_intelligence/ai_overseer/tests/test_preflight_resolution.py
  - modules/platform_integration/antifafm_broadcaster/ModLog.md
  - modules/platform_integration/antifafm_broadcaster/src/obs_controller.py
  - modules/platform_integration/antifafm_broadcaster/tests/test_obs_controller_startup.py

============================================================
RESULT: FAIL - Scope violation detected
============================================================
```

## Files Changed

| File | Purpose |
|------|---------|
| `tools/pr_scope_guard/pr_scope_guard.py` | Scope guard script |
| `docs/0102_session_briefings/BH2_BRANCH_HYGIENE_SCOPE_GUARD_PHASE1.md` | This documentation |

## Next Steps

### BH3 - CI Integration (P1)
Add scope guard as a required CI check on pull_request events.

### BH4 - Pre-push Hook (P2)
Add local pre-push hook that warns when branching from dirty main.

---

**Generated**: 2026-04-20
**Window**: AG5
**Slice**: BH2
**Forensics source**: BH1 - BRANCH_HYGIENE_FORENSICS_PHASE1
