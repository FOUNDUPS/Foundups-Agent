# HoloIndex Neutral Freshness Authority P1A

## 1. Problem Statement

- **What:** Move the existing query freshness snapshot/gate, binding
  normalization, maintenance reason, and stable error mapping from the
  infrastructure bridge into a dependency-light HoloIndex authority.
- **Why:** `holo_index.query_admission` was a lower-level package importing an
  infrastructure-owned RedDog adapter solely to reuse its proof semantics.
- **Who:** Authorized by the external principal's continuing RedDog/HoloIndex
  architecture direction and assigned as a bounded P1A worker slice.
- **Execution plane:** Local build in an isolated Git worktree. WRE is not
  applicable because this slice performs no routed runtime or autonomous
  dispatch.
- **MPS:** Complexity 3 + Importance 5 + Deferability 4 + Impact 5 = 17 / P0.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | The bridge file is the current sole owner of the shared freshness decisions. | Import search found the bridge owner and one production HoloIndex dependency in `holo_index.query_admission`. | HIGH |
| A2 | Moving the implementation and re-exporting exact objects can preserve public behavior. | The bridge consumers import only its published constants, class, and functions; the compatibility module re-exports those identical objects. | HIGH |
| A3 | Storage, models, providers, timeouts, and lifecycle need no change for dependency inversion. | The extracted code depends only on HoloIndex receipt, lock, query-receipt, and storage-contract helpers. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | HoloIndex authority imports bridge, transport, or model/provider code. | LOW | HIGH | AST boundary and cold-import module-delta regressions. |
| F2 | Bridge and HoloIndex expose different classes, constants, or mapping functions. | LOW | HIGH | Exact `__all__` and object-identity re-export regression. |
| F3 | Error codes, stale reasons, or receipt bindings drift during extraction. | LOW | CRITICAL | Behavior-identical move plus existing owner, raw admission, and direct-diagnostic suites. |
| F4 | Slice expands into storage namespace or semantic-loader changes. | LOW | HIGH | Explicit scope exclusions in code docs, roadmap, and receipt. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Keep the bridge as authority | Preserves the lower-level-to-infrastructure dependency that P1A exists to remove. |
| Copy the gate into HoloIndex | Creates two proof implementations and permits reason-code drift. |
| Create a new cross-system shared package | Adds a package boundary without evidence that another neutral consumer needs it; HoloIndex owns the underlying receipts, locks, and storage identity. |
| Change all bridge consumers to import HoloIndex directly | Unnecessarily breaks the historical bridge import surface; an exact re-export preserves compatibility. |

## 5. Decision Record

- **Decision:** PROCEED with a behavior-identical move to
  `holo_index.query_freshness_gate`, invert `holo_index.query_admission`, and
  retain a decision-free bridge compatibility re-export.
- **Owner:** 0102 worker
- **Date:** 2026-07-24
- **WSP 81 classification:** No WSP framework document changes. The governed
  mirror, notification, approval, and archive requirements are therefore not
  applicable; Git history is the recovery path for this code/docs slice.
- **Truth boundary:** This proves dependency ownership and regression parity
  only. It does not prove the shared SSD current, migrate storage, repair
  semantic loading, or change owner availability.

## 6. Validation Evidence

- RED: 5 focused failures before the neutral authority existed.
- Initial GREEN: 108 passed, 1 optional platform symlink skip across the new
  import/re-export contract, raw admission, owner freshness/runtime, and
  RedDog direct/receipt boundaries.
- Wider no-instrumentation parity: 214 passed, 1 optional symlink skip.
- Focused branch coverage: 92% with 93 passed, 1 optional skip, and the
  existing 20ms timeout test deliberately deselected under instrumentation;
  that test passed standalone without coverage overhead.
- Final wider validation and exact WSP 97 receipt results are recorded in
  `HOLOINDEX_NEUTRAL_FRESHNESS_AUTHORITY_WSP97_EXECUTION_RECEIPT_P1A.json`.
