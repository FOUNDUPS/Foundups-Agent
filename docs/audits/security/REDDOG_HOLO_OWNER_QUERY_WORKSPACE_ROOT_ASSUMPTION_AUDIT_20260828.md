# Assumption Audit: RedDog Holo Owner-Query Workspace Root Phase 2

## 1. Problem Statement

- **What:** A successful exact-main OpenClaw maintenance transaction was
  reported as `owner_result_invalid_after_completion` by the controller.
- **Why:** The shared post-completion classifier entered `query_once` through
  the selected authority checkout rather than the original workspace/control
  checkout. Because that same authority was also configured, the independent
  selector correctly rejected `authority == workspace`.
- **Who:** Authorized by 012; executed by 0102/architect under WSP 00, WSP 06,
  WSP 15, WSP 22, WSP 50, WSP 62, WSP 84, WSP 87, and WSP 97.
- **Base:** `724954fa3799b19174a7ac0b653da8c95e9ccf13`.
- **Allocation:** WSP 15 `C3/I5/D5/Impact5 = 18/P0`.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | `query_once.repo_root` represents the caller workspace/control entry root, not the already selected authority. | The one-shot query independently calls the authority selector. Exact live reproduction with the authority root returned `HOLOINDEX_AUTHORITY_ROOT_INVALID`; the original control root returned CURRENT against that same authority. | HIGH |
| A2 | Authority selection must remain independent of query-entry selection. | `classify_verified_owner_result()` compares the result with the captured `HoloIndexAuthoritySelection`; the repair changes only the query-entry argument. | HIGH |
| A3 | The workspace root cannot be selected by prompt or query payload. | Every changed caller derives it from its internal `repo_root`/controller root and passes only `{query, limit}` to the query runner. | HIGH |
| A4 | The maintenance transaction succeeded despite the controller rejection. | Exact-main OpenClaw execution completed atomically at generation `sha256:4ede3b9d...`; a fresh governed query was CURRENT/no-gap/no-reindex and full replica verification was unchanged. | HIGH |
| A5 | Candidate proof is not merged-runtime acceptance. | Focused tests and a production-shaped CURRENT call prove argument topology, but only the first new exact-main post-merge event can prove the merged controller accepts completion end to end. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | The selected authority is reused as the query workspace and self-rejects. | HIGH before repair | HIGH | Require `workspace_repo_root` explicitly at the shared classifier and all four production caller paths. |
| F2 | The repair weakens `authority == workspace` rejection. | LOW | CRITICAL | Keep `authority_worktree.py` unchanged and add a direct negative regression for configured same-root authority. |
| F3 | A query payload injects an arbitrary workspace root. | LOW | CRITICAL | Root is an internal keyword derived from the controller/recovery entrypoint; payload remains query plus bounded limit only. |
| F4 | Classification trusts the workspace instead of the clean authority. | LOW | CRITICAL | Continue passing the independently captured selection to `classify_verified_owner_result()` and compare all result bindings against it. |
| F5 | One caller retains the old topology and produces an intermittent false negative. | MED | HIGH | Cover post-completion proof, incident recheck, CURRENT coordination, and blocked-request recovery separately. |
| F6 | Candidate tests are described as production closure. | MED | MED | Documentation states merged exact-main replay remains the acceptance gate. |

## 4. Alternatives Considered

| Alternative | Why Rejected for This Phase |
|---|---|
| Pass `selection.selected_root` and suppress same-root rejection | This collapses independent authority selection and weakens a deliberate fail-closed boundary. |
| Teach `query_once` to accept a preselected authority | This creates a second privileged query API and risks bypassing independent current-state revalidation. |
| Clear the authority environment around the query | Process-environment mutation races other callers and hides rather than models the two-root contract. |
| Re-run maintenance after the rejection | The maintenance already completed; repeating an external transaction masks the controller defect and adds needless effects. |
| Add fallback from authority to workspace on failure | Error-driven fallback can turn malformed or hostile topology into authority and violates fail-closed selection. |

## 5. Decision Record

- **Decision:** PROCEED with the smallest explicit contract. The original
  workspace/control root is mandatory as `workspace_repo_root` for query entry;
  the captured clean authority remains the independent verification target.
- **Non-goals:** no resolver relaxation, no payload-selected root, no reindex,
  maintenance, route, Git, model, Hermes, promotion, A-grade, or retrieval-RSI
  authority.
- **Acceptance:** focused and exhaustive tests, WSP 62 bounds, packaged-source
  equality, independent WSP_00/WSP_97 audit, squash merge, and first-pass
  exact-main controller replay.
- **Owner:** 0102/architect.
- **Timestamp:** 2026-08-28T22:50:30+09:00.
