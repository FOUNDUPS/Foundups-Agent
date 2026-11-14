# HoloIndex Query Root Admission P0 Phase 1

**Slice:** `HOLOINDEX_QUERY_ROOT_ADMISSION_P0_PHASE1`
**Date:** 2026-07-24
**Original base:** `c7a3373b867efd077b153901db693979eb3966f7`
**Rebased base:** `545f4b3b828cf083c20e266961c6df2fde1565c7`
**Branch:** `fix/holoindex-root-bound-query-p0`
**Owner:** 0102 architect operating in WSP_00 state
**WSP:** 00, 15, 22, 50, 62, 81, 97

## Assumption Audit

### 1. Problem

The authenticated RedDog owner already enforced exact repository freshness,
but raw persistent CLI search, persistent bundle retrieval, and the explicitly
diagnostic direct adapter could construct a local backend without first
proving that the store receipt belonged to the invoking worktree. A linked or
foreign worktree could therefore read vectors for another root/HEAD before a
later diagnostic check reported staleness.

This slice adds only a read-admission boundary. It does not refresh, migrate,
namespace, or repair the store and grants no worker maintenance authority.

### 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | The canonical owner freshness gate is the correct proof source. | Existing owner tests and `holo_query_freshness_gate.py`. | HIGH |
| A2 | A persistent read is truthful only for the explicit invoking root and SSD. | New foreign-root and wrong-SSD regressions. | HIGH |
| A3 | Clean exact HEAD, generation, complete baseline, and embedding proof are indivisible admission requirements. | Existing owner freshness gate reused without duplicating its proof rules; new focused helper tests. | HIGH |
| A4 | Maintenance must be inactive and provable before backend construction. | Existing maintenance probe reused; fail-before-backend tests. | HIGH |
| A5 | Offline lexical retrieval is useful diagnostic evidence but is not persistent semantic evidence. | CLI bypass test and degraded metadata. | HIGH |
| A6 | Content-free reason codes are sufficient for admission logs and raw CLI/bundle denial. | Admission serialization excludes roots, SSD paths, receipt bindings, prompts, and hits. The direct diagnostic preserves its pre-existing caller-local `query` response field; only its new reasons are content-free, and this adapter does not log the payload here. | HIGH |
| A7 | Persistent admission must run before resolving a caller-controlled module hint. | Ordering regression makes module resolution fail if called before a denied admission. | HIGH |
| A8 | Raw CLI and bundle offline module/WSP/NAVIGATION/artifact discovery must share repository-confined, no-follow, resource-bounded reads. Oversized discovery roots cannot yield a partial filesystem-order-dependent result. | Raw-CLI symlink/reparse/NAVIGATION-byte tests; absolute-drive, traversal, root/component reparse, nested-walk, artifact, module-domain/WSP `cap + 1`, and before/after-cap tests. | HIGH |
| A9 | Direct diagnostic receipt and maintenance identities come from the admitted SSD, never a caller-selected receipt location. | The noncanonical external-receipt regression rejects before repository evaluation, receipt admission, or backend access; `_direct_paths` and both maintenance locations are SSD-derived by code. | HIGH |
| A10 | Module-file evidence is truthful only when the bounded walk proves it saw the complete eligible set. | Match-before/after-cap, depth overflow, scan error, and reverse-order regressions. | HIGH |

### 3. Failure Modes

| ID | Failure mode | Impact | Mitigation |
|---|---|---|---|
| F1 | A foreign worktree reads the canonical store. | HIGH | Compare explicit root with receipt before backend construction. |
| F2 | Same root but wrong HEAD reads stale vectors. | HIGH | Require clean exact receipt HEAD. |
| F3 | A different SSD is silently accepted. | HIGH | Bind the explicit resolved SSD to the receipt store identity. |
| F4 | Missing generation or partial baseline is treated as current. | HIGH | Reuse the canonical complete-baseline evaluator. |
| F5 | A query races maintenance. | CRITICAL | Probe maintenance before receipt evaluation; existing direct diagnostic post-probe remains as race detection. |
| F6 | Raw CLI/bundle admission denial leaks paths, prompts, or binding metadata. | HIGH | Serialize only stable error/freshness/reason flags. The direct adapter's existing caller-local query echo is outside this narrower serialized-admission claim. |
| F7 | Offline lexical fallback is mistaken for semantic retrieval. | HIGH | Bypass the persistent gate/store and label output degraded with UNKNOWN freshness and index gap. |
| F8 | Bundle JSON bypasses the raw CLI gate by importing its own backend. | HIGH | Apply the same helper inside the bundle path before its local backend import. |
| F9 | Absolute/traversal module hints touch a foreign root before admission. | HIGH | Admit persistent queries first; lexical resolution accepts relative components only. |
| F10 | Raw CLI bypasses confinement, NAVIGATION is read without a byte ceiling, or module-domain/WSP discovery returns a partial set after unbounded/filesystem-order-dependent enumeration. A nested link/reparse may also escape a confined module or artifact root. | HIGH | Route raw CLI through the shared lexical loader; lstat every component; reject oversize NAVIGATION; use no-follow classification; bound nested walks; inspect discovery roots only through `cap + 1`; reject the whole discovery result on overflow; sort only a complete bounded set. |
| F11 | An outside receipt redirects direct maintenance probes away from the admitted SSD. | CRITICAL | Derive both redundant direct probes solely from `maintenance_lock_path(ssd_path)`. |
| F12 | A path is replaced between lstat/confinement proof and a later open. | HIGH | P0 performs bounded no-follow checks and fails closed on observed links; descriptor-relative/final-handle identity hardening remains explicit P1 debt. |
| F13 | A valid caller-supplied receipt outside the SSD overrides a disagreeing canonical receipt. | CRITICAL | Derive the receipt solely from `freshness_receipt_path(ssd)`; reject a noncanonical explicit path or final receipt link/reparse before any receipt/backend read. |
| F14 | Entry/depth overflow or a scan error leaves a plausible but incomplete module-file prefix. | HIGH | Make bounded module enumeration complete-or-empty and sort only a fully verified set. |

### 4. Alternatives

| Alternative | Disposition |
|---|---|
| Duplicate the owner freshness logic in each caller. | Rejected: divergent proof semantics would recur. |
| Infer the invoking repository from process CWD or singleton state. | Rejected: linked worktrees and embedding callers require an explicit root. |
| Query first, then mark the result stale. | Rejected: the wrong persistent substrate has already been accessed. |
| Refresh automatically when admission fails. | Rejected: a read consumer cannot mutate its evidence substrate. |
| Disable direct diagnostics completely. | Rejected for P0: a trusted-host diagnostic remains useful when admitted, but stays non-operational. |
| Add multi-root namespaces now. | Deferred P1: it requires receipt/store migration and broader maintenance policy. |

### 5. Decision

Proceed with one reusable read-only admission helper that delegates to the
existing canonical freshness/maintenance gate. Call it before persistent
backend construction in raw CLI search, persistent bundle retrieval, and the
RedDog direct diagnostic. Keep offline lexical retrieval current-repository
only and explicitly degraded. Persistent admission precedes module-hint
resolution. Raw CLI and bundle lexical retrieval share the same confined
loader; lexical path/artifact discovery is relative-only, byte/entry bounded,
and no-follow. NAVIGATION and oversized discovery roots fail closed rather
than returning partial evidence. Persistent receipt identity and both direct
maintenance race probes derive solely from the admitted SSD; a caller receipt
argument is accepted only as an exact canonical assertion. Module-file
enumeration is complete-or-empty on entry cap, depth overflow, and scan error.

**Timestamp:** 2026-07-24T06:16:12+09:00

## WSP_15 Priority

| Dimension | Score | Rationale |
|---|---:|---|
| Complexity | 3 | Three callers, but one existing proof can be reused. |
| Importance | 5 | Wrong-root evidence invalidates architectural conclusions. |
| Deferability | 5 | Current RedDog diagnostic behavior can cross worktree identity. |
| Impact | 5 | Closes the common pre-backend read boundary. |
| **Total** | **18 / P0** | Implement immediately as a focused repair. |

LLME is not applied because this is a cross-module work item, not a module
maturity score.

## WSP_62 Boundary

- `holo_index/query_admission.py` is a focused helper module; its public
  evaluator remains below the 50-line Python function threshold.
- The helper deliberately imports the existing infrastructure-owned
  `HoloQueryFreshnessGate` for P0 semantic parity instead of cloning proof
  rules. This is a known dependency-direction debt: lower-level HoloIndex code
  depends on an infrastructure owner module. Import-time tests show no cycle.
  P0 does not relocate that contract or introduce a neutral-owner migration;
  ownership extraction is reserved for a separate reviewed architecture slice.
- The legacy CLI and bundle routers receive only narrow admission hooks; no
  command, indexing, migration, or rendering responsibilities move into them.
- New path confinement is isolated in
  `holo_index/cli/bundle_path_confinement.py` (288 lines; maximum function 47
  lines), and all focused test files remain below the 500-line test threshold.
- `handle_bundle_json` is decomposed to 49 lines through narrow helpers; this
  slice does not add a broad WSP_62 exemption for the handler.
- The direct adapter retains its existing post-query maintenance race probe.
- Historical monolith decomposition remains in `holo_index/ROADMAP.md`; this
  security repair makes no repository-wide WSP_62 compliance claim.

## Execution Boundaries and Evidence

- The work was performed in the dedicated worktree
  `O:\Foundups-Agent-worktrees\holoindex-root-bound-query-p0-20260724`.
- No framework WSP, knowledge backup, canonical index, or `E:\HoloIndex` state
  was modified.
- RED: the focused suite failed collection because
  `holo_index.query_admission` did not exist.
- A second RED proved offline bundle retrieval consumed a foreign SSD
  `wsp_summary.json`; GREEN derives bounded WSP metadata from the invoking
  repository and records zero supplied-SSD reads.
- Independent-review REDs proved module resolution preceded persistent
  admission, absolute/traversal hints escaped, receipt location selected the
  direct maintenance lock, nested reparse enumeration was unbounded, and
  artifact existence checks followed links. GREEN derives canonical receipt
  and maintenance locations from the SSD by code; current regressions prove a
  noncanonical external receipt rejects before repository evaluation, receipt
  admission, or backend access and cover the other listed boundaries. Real
  symlink integrations remain portable skips on this host while deterministic
  reparse seams execute without skips.
- Second-amend REDs proved raw CLI directly followed/read NAVIGATION, oversize
  NAVIGATION was accepted, module-domain/WSP discovery ignored entry caps, and
  a capped partial result remained filesystem-order dependent. GREEN routes raw
  CLI through the shared loader, rejects oversize NAVIGATION, and makes
  `cap + 1` overflow return no discovery result whether a match appears before
  or after the cap.
- Third-amend REDs proved that a valid external receipt could override a
  disagreeing canonical SSD receipt, a final receipt reparse was not rejected
  before reads, capped/depth/error module walks returned partial evidence, and
  `handle_bundle_json` remained 132 lines. The RED matrix was `10 failed, 32
  passed, 4 skipped`. GREEN binds receipt reads to the SSD-derived canonical
  path, makes module walks complete-or-empty and order-independent, and
  decomposes the handler to 49 lines while preserving malformed-payload
  exception containment.
- GREEN and static validation results are recorded in the paired WSP_97
  execution receipt and module TestModLogs.
- Two stale test assertions failed unchanged on detached exact-base
  `c7a3373b8` and current-main `545f4b3b8`: an extension exact-string assertion
  predated semantic-first conditional model selection, and a direct test called
  a removed runtime-private hit normalizer. The tests now target the existing
  semantic/lexical environment contract and canonical adapter normalizer; no
  production compatibility shim or unrelated extension/runtime edit was made.

## Deferred P1

The named
`Neutral Freshness-Gate Contract Extraction / Dependency Inversion` P1 item
must move the proof contract to a neutral owner and invert the current
lower-level-to-infrastructure dependency without cloning semantics. Explicit
multi-repository store namespaces, legacy receipt metadata migration, and
mechanically exclusive maintenance ownership across all direct-store consumers
also require separate reviewed slices. Descriptor-relative/final-handle
identity checks are required to close concurrent path-replacement TOCTOU; P0
stable-ancestor canonical comparison does not close that replacement window,
and P0 does not claim hostile concurrent filesystem mutation resistance.

## Validation Record

- Unfiltered changed-file matrix: `62 passed, 5 skipped`; skips are optional
  real-symlink integrations unavailable under this Windows privilege profile,
  while deterministic link/reparse seam tests ran and passed.
- Canonical owner service/freshness matrix: `60 passed`, including the exact
  repository-root and SSD identity mismatch parameter cases.
- Wider bundle, receipt, owner-client, and RedDog query boundary matrix:
  `126 passed, 4 skipped`; skips are the optional real-symlink integrations.
- WSP_62 guards: `3 passed` for exact bridge exemptions and `16 passed` for
  modular-audit thresholds. AST measurements: admission evaluator 35 lines;
  direct diagnostic 50; focused confinement module 288 lines with a maximum
  function size of 47 lines; bundle handler 49 lines.
- Wider CLI/index command:
  `python -B -m pytest -p no:cacheprovider holo_index/tests/test_cli_index_maintenance_integration.py holo_index/tests/test_cli_index_selection.py holo_index/tests/test_holoindex_storage_contract.py holo_index/tests/test_index_refresh_repair.py -q`
  returned `32 passed, 1 failed`. The exact baseline node is
  `holo_index/tests/test_index_refresh_repair.py::TestWspPurity::test_wsp_purity_only_wsp_files`;
  its source-string assertion requires literal `glob("WSP_*.md")` (or the
  single-quoted equivalent) inside `index_wsp_entries`. It fails identically on
  unmodified `545f4b3b8` and does not import or inspect a touched surface.
- Static checks: focused Ruff passed; legacy `_cli_main.py` critical
  `E9/F63/F7/F82` selection passed; eleven changed Python files compiled in
  memory; import-cycle smoke passed; `git diff --check` and WSP_97 receipt
  validation passed.
- Live offline/fast raw CLI smoke returned current-repository code and WSP
  lexical hits with a caller-supplied nonexistent SSD, confirming the lexical
  metadata path did not require the persistent store.
- Runtime hygiene: two visible loopback owner processes were created more than
  four hours before this worktree and had unrelated exited parent PIDs; this
  lane did not spawn or terminate them and left no attributable service.
