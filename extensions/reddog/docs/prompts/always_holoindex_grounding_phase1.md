AUTHOR - REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1

Operate in WSP_00. Apply WSP_97 CoT/CoR before any edit.

PREREQUISITE GATE:

- **#883 LANDED on `main`** (content inclusion + ADDENDUM F redaction-safe snippets, v0.3.22).
- **Branch from `main` after #883 merge** (see ADDENDUM D). Do not branch from pre-#883 main.
- Do **not** widen #883. This is the **next external-lane P0 slice** after #883 lands.
- **Do not** implement `HOLOINDEX_SKILLZ_MANIFEST_PHASE1` in this slice (P1, separate).

LANE LOCK:

External 012-facing Foundups(R)Agent auto-router + bounded-context lane only.
Do NOT touch Lane B / WRE / Sakana / OpenClaw execution dispatch.
Do NOT register HoloIndex as a Skillz manifest in this slice.

---

INVARIANT (012 directive)

```text
RedDog should always ground with proof.
Never assume.
HoloIndex first.
```

**Current behavior (OBSERVED - must change):**

```text
REGULAR -> openrouter_single + context none
HIGH    -> foundups_fusion + wsp_holo_skillz
ULTRA   -> foundups_fusion + wsp_holo_git_skillz
```

REGULAR can answer without HoloIndex grounding. That was originally for cheap smoke tests but conflicts with the invariant above.

**Target behavior (REQUIRED):**

```text
REGULAR -> openrouter_single + wsp_holo
HIGH    -> foundups_fusion + wsp_holo_skillz
ULTRA   -> foundups_fusion + wsp_holo_git_skillz
```

REGULAR stays cheap: single-model GLM principal, no Fusion panel, no Skillz, no git diff.
REGULAR still runs local HoloIndex bundle-json (or honest offline fallback) and reports scorecard evidence.

**HoloIndex is NOT a Skillz today (OBSERVED):**

```text
python -B holo_index.py --bundle-json --search ...
```

Direct Python CLI from `extension.js` (`holoIndexOutput`). Not registered in Skillz/Wardrobe/Rolodex manifest.
P1 follow-up: `HOLOINDEX_SKILLZ_MANIFEST_PHASE1` for formal WRE/OpenClaw discovery.

---

BASELINE EVIDENCE

```yaml
routing_gap:
  function: resolveAutoContextMode
  file: extensions/foundups_advisory_workers/extension.js
  current_regular: none
  required_regular: wsp_holo
  contract_test: verify_extension_contract.js line ~213 asserts REGULAR -> none (must flip)

mode_selection_copy:
  modeSelectionReasoning currently says REGULAR "avoids panel latency/cost"
  must not imply "no repo context" after this slice

acceptance_baseline:
  EXT-ACC-008 run A uses HIGH + wsp_holo_skillz
  REGULAR smoke prompts (smoke_tester) currently expect context none
  after slice: REGULAR smoke must show holoindex_status in Run Trace

docs_drift:
  README.md REGULAR row says "no repo context" (fix ASCII mojibake if present)
  INTERFACE.md resolveAutoContextMode table says "none / WSP+Holo+Skillz / ..."
  REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md context enum includes none for REGULAR paths
```

---

PURPOSE

Ensure **every** RedDog auto-routed run attaches HoloIndex-grounded bounded context at minimum `wsp_holo`, so Copy MD Run Trace always carries HoloIndex scorecard fields and models cannot silently assume repo state.

After this slice lands:

1. 012 runs one **REGULAR-tier smoke** (smoke_tester work focus) and confirms HoloIndex scorecard in Run Trace.
2. Re-run **EXT-ACC-008 run A** pattern at REGULAR tier if useful; do not schedule full 15-pack replacement pass unless architect directs.

---

HARD ACCEPTANCE CHECKS (must pass in PR)

1. **REGULAR auto context = wsp_holo:**
   `resolveAutoContextMode({ tier: 'REGULAR' }, 'auto')` returns `wsp_holo` (not `none`).

2. **HIGH / ULTRA unchanged:**
   HIGH -> `wsp_holo_skillz`; ULTRA -> `wsp_holo_git_skillz`.

3. **REGULAR mode unchanged:**
   `resolveModelMode({ tier: 'REGULAR' }, 'auto', 'smoke_tester')` still returns `openrouter_single`.

4. **buildBoundedRepoContext('wsp_holo', taskText)** includes:
   - `### HoloIndex recall` section
   - HoloIndex scorecard fields in returned `holoindex_scorecard`
   - WSP operating contract (existing)

5. **Copy MD Run Trace for REGULAR run** includes:
   - `context mode: wsp_holo`
   - `holoindex_status: ...` (not absent)
   - `code_hits_count: ...` when bundle-json succeeds

6. **HoloIndex failure is explicit, not silent:**
   When bundle-json fails and offline fallback runs, Run Trace shows `holoindex_status: offline_fallback` or `parse_error` / `unknown` - never implies retrieval succeeded without evidence.
   Model-facing quality string must say NEEDS_VERIFICATION when protocol coverage is uncertain (existing `holoIndexOutput` quality strings - verify, do not weaken).

7. **modeSelectionReasoning** updated:
   REGULAR path must cite `context=wsp_holo` and state HoloIndex grounding (not "no repo context").

8. **Version bump:** `0.3.22` -> **`0.3.23`** (install hygiene).

9. **Contract tests (test-first):**
   - Flip REGULAR context assertion in `verify_extension_contract.js`
   - Add test: REGULAR + `buildBoundedRepoContext` includes HoloIndex section
   - Add TestModLog registry rows (THG-001..); extend `tests/fixtures.js` if needed
   - No OpenRouter calls in tests

10. **Docs:** README, INTERFACE, ROADMAP, ModLog, tests/README.md, tests/TestModLog.md updated in same change.

Regression: **do not** remove target content inclusion (#883) or ADDENDUM F sanitization behavior.

---

ADDENDUM A - ASCII / MOJIBAKE CLEAN

Clean touched docs to ASCII-safe text before commit.
Run contract tests + `git diff --check` on touched paths.

---

ADDENDUM B - TEST-FIRST EXECUTION (0102)

Do not wait for 012 Cursor UI to prove routing correctness.

Required deterministic tests:

1. `resolveAutoContextMode(regularClassification, 'auto') === 'wsp_holo'`

2. `resolveAutoContextMode(highClassification, 'auto') === 'wsp_holo_skillz'` (unchanged)

3. `resolveAutoContextMode(ultraClassification, 'auto') === 'wsp_holo_git_skillz'` (unchanged)

4. `buildBoundedRepoContext('wsp_holo', fixtures.REGULAR_SMOKE_PROMPT)` includes `### HoloIndex recall`

5. `extractHoloIndexScorecard('wsp_holo', meta)` returns non-null when holo meta present

6. `modeSelectionReasoning(regular, 'regular', 'openrouter_single', 'wsp_holo')` mentions `wsp_holo`

Reuse `tests/fixtures.js`; add `REGULAR_SMOKE_PROMPT` constant if missing.

Validation:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

---

ADDENDUM C - OUT OF SCOPE (explicit)

- HoloIndex Skillz manifest registration (`HOLOINDEX_SKILLZ_MANIFEST_PHASE1` - P1)
- Target snippet content inclusion changes (#883 - already landed)
- Output schema repair / repair-path redaction (`REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1`)
- HoloIndex ranking/index-gap fixes (#882 - landed)
- Changing HIGH/ULTRA tier boundaries or Fusion panel composition
- Weakening `fusion_redaction_gate.py`
- Lane B / WRE execution dispatch
- Full 15-prompt acceptance replacement pass

---

ADDENDUM D - POST-#883 BASE ONLY

Start from `main` after #883 is landed. Do not branch from pre-#883 main.

Preserve all v0.3.22 target-content inclusion behavior:

```text
target_content_included
target_content_paths
target_content_chars
target_content_sanitized
target_content_sanitized_categories
TCI-001..TCI-010 contract tests (must still pass)
```

This slice **only** changes default REGULAR grounding from `none` to `wsp_holo` and updates docs/tests/trace expectations.

If target-content tests regress, **stop** and return REQUEST_CHANGES.

Does **not** fix (separate slices):

```text
output_validation repair
made_network_call unknown telemetry
model-output mojibake in Copy MD
target_recall_ok HoloIndex ranking instability
```

---

READ BEFORE EDITING (WSP_87)

- extensions/foundups_advisory_workers/extension.js
  (`resolveAutoContextMode`, `resolveModelMode`, `modeSelectionReasoning`, `buildBoundedRepoContext`, `holoIndexOutput`, `buildRunTraceSection`, `extractHoloIndexScorecard`)
- extensions/foundups_advisory_workers/tests/verify_extension_contract.js (~211-214)
- extensions/foundups_advisory_workers/tests/fixtures.js
- extensions/foundups_advisory_workers/docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md (EXT-ACC-008)
- extensions/foundups_advisory_workers/README.md (routing table)
- extensions/foundups_advisory_workers/INTERFACE.md

---

ADDENDUM E - BASE / VERSION PREFLIGHT

Before editing:

1. `git fetch origin main`
2. Confirm #883 is merged on main:
   `gh pr view 883 --json state,mergedAt,mergeCommit`
3. Confirm branch starts from current origin/main:
   `git rev-parse origin/main`
   `git switch -c feat/reddog-always-holoindex-grounding-phase1 origin/main`

Pre-edit source must show v0.3.22 and #883 behavior:

- `EXTENSION_VERSION = 0.3.22`
- `target_content_included` code present
- `target_content_sanitized` code present
- TCI-001..TCI-010 tests present

If any are missing, **STOP** and return `DEFER: #883_NOT_ON_BASE`.

---

IMPLEMENTATION HINTS (verify, do not blindly copy)

Single-line change core in `resolveAutoContextMode`:

```javascript
if (tier === 'REGULAR') {
  return 'wsp_holo';  // was 'none'
}
```

Confirm `buildBoundedRepoContext('wsp_holo', ...)` already calls `holoIndexOutput` (it should - same branch as wsp_holo_skillz minus Skillz/git).

Optional: add Run Trace note when `context mode === wsp_holo` that Skillz/git are intentionally omitted for REGULAR cost control.

---

BRANCH / PR

Branch: `feat/reddog-always-holoindex-grounding-phase1`
Title: feat(extension): REGULAR tier always attaches wsp_holo HoloIndex grounding
Draft PR only. Stop at VERIFIED_READY. Do not merge without sovereign token.

PR body must include:

- Before/after routing table
- Hard checks 1-10 evidence
- Contract test output
- 012 REGULAR smoke steps (post-install 0.3.23)
- Explicit note: HoloIndex Skillz manifest deferred to P1

WSP_97 rows (ModLog + PR):

- REGULAR_NO_CONTEXT_VIOLATES_INVARIANT
- REGULAR_WSP_HOLO_GROUNDING_ADDED
- HIGH_ULTRA_ROUTING_UNCHANGED
- HOLOINDEX_SCORECARD_ALWAYS_ON_AUTO_ROUTE
- HOLOINDEX_FAILURE_EXPLICIT_NOT_SILENT
- HOLOINDEX_NOT_SKILLZ_YET
- SKILLZ_MANIFEST_OUT_OF_SCOPE
- LANE_B_EXCLUDED
- TARGET_CONTENT_INCLUSION_UNCHANGED

WSP_15:

| C | I | D | Impact | MPS | P |
|---:|---:|---:|---:|---:|---|
| 2 | 5 | 1 | 5 | 13 | **P0** |

---

ARCHITECT REVIEW STATUS

```text
APPROVE_WORKER_DISPATCH after #883 lands on main (Addenda A-F).
Do not implement until #883 is merged and worker branches from post-#883 main.
```

SEQUENCE (012):

```text
1. Land #883 (v0.3.22) - target content + sanitized snippets
2. REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1 (v0.3.23) - this prompt
3. Repair/schema/telemetry polish (output validation, made_network_call, mojibake)
```

---

RETURN (worker -> architect review)

1. Files changed
2. Before/after routing table (OBSERVED vs target)
3. Hard checks 1-10 evidence
4. Contract test output
5. PR URL
6. Residual NEEDS_VERIFICATION
7. Ready for 012 REGULAR smoke: yes/no

ADDENDUM F - WORKER RETURN MUST INCLUDE 012 RUN CARD

Also return the exact 012 smoke card:

```text
Version expected: Foundups(R)Agent Build 0.3.23
Role: Smoke Tester
Work focus:
Reply with exactly: regular mode works

Expected Run Trace:
- WSP_15 tier: REGULAR
- mode: openrouter_single
- context mode: wsp_holo
- holoindex_status: present
- code_hits_count: present when bundle-json succeeds
- mode selection reason mentions context=wsp_holo
```

---

012 REGULAR SMOKE (after VERIFIED_READY + VSIX install)

**Role:** Smoke Tester (or any prompt that classifies REGULAR)

**Work focus (example):**

```text
Reply with exactly: regular mode works
```

**Expected Run Trace:**

```text
Build: 0.3.23
WSP_15 tier: REGULAR
mode: openrouter_single
context mode: wsp_holo
holoindex_status: bundle_json_ok|offline_fallback|parse_error (never absent)
code_hits_count: ...
mode selection reason: ... context=wsp_holo ...
```

Pass when HoloIndex scorecard is present and model did not answer as if repo state were unknowable without stating NEEDS_VERIFICATION when HoloIndex failed.
