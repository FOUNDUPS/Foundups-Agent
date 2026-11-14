# Assumption Audit: RedDog Holo Control Runtime Root Phase 1

## 1. Problem Statement

- **What:** A clean linked post-merge control checkout can lack the Python
  dependency runtime required by the sealed authority transaction's isolated
  snapshot probe.
- **Why:** Control-plane cleanliness and indexed-source authority must remain
  separate from dependency loading; copying a virtual environment into every
  worktree or weakening the probe would create drift.
- **Who:** Authorized by 012; executed by 0102/architect under WSP 00, WSP 15,
  WSP 50, WSP 62, WSP 84, WSP 87, and WSP 97.
- **Base:** `8842cbcdbeb5cd53407fcc3f60a2a9f774941e70`.
- **Allocation:** WSP 15 `C3/I5/D5/Impact5 = 18/P0`.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | The linked control and primary runtime root belong to one repository. | Existing `resolve_holoindex_runtime_root()` requires both paths to resolve to the same Git common directory and falls back to the caller on uncertainty. | HIGH |
| A2 | Supplying `workspace_root` to the authority transaction grants dependency location and acts as the same-Git-common-directory identity witness, not indexed-source authority. | The transaction reproves common-directory equality and the authority digest, then receives the dedicated authority separately as `repo_root`; the successful recovery used the primary checkout for runtime dependencies and the clean authority checkout for all semantic/index inputs. | HIGH |
| A3 | The selected dependency runtime remains untrusted until probed, but is not byte-sealed. | The existing maintenance subprocess validates process-image/virtualenv path association and final collection snapshot behavior; the original missing-runtime run failed closed at that probe. Installed payload bytes remain outside exact closure. | HIGH |
| A4 | The current manual recovery proves the boundary but not automatic replay. | Exact-main recovery and immutable post-query verification passed only after manually supplying the primary runtime root. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | An unrelated checkout supplies executable dependencies. | LOW | CRITICAL | Reuse the existing same-common-directory resolver; never accept an arbitrary configured runtime root in this slice. |
| F2 | The dirty primary IDE checkout becomes the indexed source. | LOW | CRITICAL | Keep the dedicated authority as the transaction's separate `repo_root`; regression coverage asserts the authority argument is unchanged. |
| F3 | A missing or structurally incompatible primary runtime is silently accepted. | MED | HIGH | Resolver uncertainty falls back to the clean control root and the existing runtime/snapshot probes reject unavailable or structurally incompatible dependencies. Exact installed-payload proof remains a separate blocked slice. |
| F4 | Runtime resolution bypasses task, request, claim, or authority validation. | LOW | HIGH | Resolution changes only the argument supplied after all existing task/request/claim/authority gates; no validation contract is relaxed. |
| F5 | The focused test is misreported as production acceptance. | MED | MED | Documentation labels automatic OpenClaw replay as pending until a later exact-main event exercises the merged path. |
| F6 | A dependency runtime reads uncommitted semantic source from the primary checkout. | LOW | HIGH | The authority transaction's `repo_root` remains the dedicated clean checkout; runtime-root use is limited to interpreter/dependency discovery and isolated probing. |

## 4. Alternatives Considered

| Alternative | Why Rejected for This Phase |
|---|---|
| Install or copy `.venv` into the control checkout | It duplicates a large mutable runtime, increases drift, and does not improve source authority. |
| Launch from the dirty primary IDE checkout | The controller correctly rejects dirty control state; relaxing that gate would weaken exact-main proof. |
| Make the authority checkout the dependency runtime | It has the same missing-runtime problem and conflates source authority with dependency provisioning. |
| Add a new runtime-root environment variable | It enlarges configuration and trust surface when a same-repository resolver already exists and is tested. |
| Move resolution into the 599-line authority transaction | It crosses WSP 62 pressure and hides a caller-specific control/runtime selection concern inside the sealed transaction. |

## 5. Decision Record

- **Decision:** PROCEED with the smallest reusable layer: resolve the existing
  same-repository primary runtime root in the post-merge executor and pass it
  only as `workspace_root`; retain the configured dedicated authority as
  `repo_root`.
- **Non-goals:** no cleanliness relaxation, no arbitrary runtime override, no
  reindex/query authority change, no route mutation, no runtime exact-closure
  claim, and no retrieval-RSI claim.
- **Owner:** 0102/architect.
- **Timestamp:** 2026-08-28T21:52:04+09:00.
