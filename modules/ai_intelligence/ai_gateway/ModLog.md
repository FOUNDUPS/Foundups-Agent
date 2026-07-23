# AI Gateway Module Change Log

## [2026-07-24] - Scheduled Provider Discovery Replay Guard

**Who:** 0102 Codex worker, architect-audited lane
**Type:** Defensive Reliability / Durable Replay Control
**Slice:** SCHEDULED_PROVIDER_DISCOVERY_REPLAY_GUARD_PHASE1

**What:** Added a scheduled-only execution boundary around the existing direct
OpenRouter catalog discovery. The boundary serializes the complete operation
off-loop under one cross-process lock and publishes a strict bounded
per-invocation `ARMED`/terminal replay ledger before and after transport.

**Truth Boundary:**
- IMPLEMENTED: fixed outside-repository guarded identities, admission recheck
  under lock, exact terminal replay, fail-closed ARMED/indeterminate/malformed
  recovery, chronology-proved missing-entry migration, wall-clock rollback
  rejection, capacity/expiry controls, and bounded large-candidate reads.
- IMPLEMENTED: offline same-loop/process concurrency, crash-window, legacy
  evidence, cancellation/lock-waiter continuation, deep-JSON, link,
  ledger-write, large-candidate, and authority isolation regressions.
- NOT IMPLEMENTED: scheduler installation, startup/network routines, selection
  or promotion authority, registry/runtime binding, or changes to manual
  discovery. Manual/direct callers must not use the guarded fixed identities.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 durable replay and duplicate-provider-call prevention boundary).

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

**Validation:** Scheduled/replay/protected focus: 44 passed, 1 Windows symlink
capability skip. Full ai_gateway: 378 passed, 2 Windows capability skips.
Idle automation: 126 passed. Runtime artifact safety: 11 passed, 1 Windows
symlink capability skip. Ruff, compileall, and diff-check passed.

---

## [2026-07-24] - Provider Discovery Defensive Reliability Hotfix

**Who/Type/Slice/WSP:** 0102 Codex / Defensive Reliability / DIRECT_PROVIDER_DEFENSIVE_RELIABILITY_20260723 / 15,22,50,62,97
**What:** Added truthful non-3xx redirect-history receipts; retained verified
artifact identity through publication; added Windows exact-handle rename,
identity-aware cleanup, and exact prior-target rollback on detected mismatch.
**Truth:** Path replacement, hard links, and supported symlinks fail closed.
Non-Windows publication requires a trusted non-shared runtime directory;
parent-directory fsync and Windows sync/mode behavior remain limited.
No live network/provider/runtime/Holo or authority mutations were performed.
**Validation:** 98 passed / 1 Windows symlink skip focused; 339 passed / 1
skip full ai_gateway.

## [2026-07-23] - Provider Catalog Atomic Artifact Repair

**Who:** 0102 Codex worker, independent reviewer-driven repair
**Type:** Security / Crash-Safe Artifact Durability
**Slice:** DIRECT_PROVIDER_SNAPSHOT_AND_BOUNDED_DISCOVERY_PHASE1_REPAIR2

**What:** Replaced destructive runtime artifact writes with a module-local,
same-directory atomic store for both attempt receipts and candidate snapshots.
Exact UTF-8 bytes are flushed and fsynced before locked replacement; failure
removes the temporary file while preserving the prior target byte-for-byte.

**Truth Boundary:**
- IMPLEMENTED: confined exclusive temp files, regular-file and link checks,
  target-mode preservation, injected partial-write/fsync/replace regressions,
  best-effort parent-directory fsync, and reason-specific FAILED evidence.
- NOT IMPLEMENTED: shared runtime-safety changes, live provider calls,
  scheduling, registry/selection/promotion mutation, or runtime binding.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 crash-safety and receipt-truth boundary).

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-23] - Direct Provider Discovery Independent NO-GO Repair

**Who:** 0102 Codex worker, independent reviewer-driven repair
**Type:** Security / Durability Hardening
**Slice:** DIRECT_PROVIDER_SNAPSHOT_AND_BOUNDED_DISCOVERY_PHASE1_REPAIR1

**What:** Closed seven trust-boundary blockers covering exact model identifiers,
future-dated candidate observations, receipt state coherence, hostile HTTP
metadata, candidate-before-COMPLETED durability, truthful pre-call transitions,
and exact prior-candidate ID admission.

**Truth Boundary:**
- IMPLEMENTED: content-free rejection of hostile response objects and metadata,
  truthful durable intent/armed/terminal transitions, last-known-good
  preservation on candidate failure, and adversarial regression coverage.
- NOT IMPLEMENTED: provider calls in tests, automatic scheduling, registry or
  selection mutation, promotion, runtime binding, or RedDog evidence changes.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 security and durable-truth boundary).

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-23] - Direct Provider Snapshot and Bounded Discovery

**Who:** 0102 Codex worker, architect-audited lane
**Type:** Provider Evidence / Offline-Bounded Discovery
**Slice:** DIRECT_PROVIDER_SNAPSHOT_AND_BOUNDED_DISCOVERY_PHASE1

**What:** Added an explicit, unauthenticated OpenRouter model-list refresh with
strict JSON and record normalization, digest-bound invocation/attempt/candidate
receipts, freshness-aware rehydration, and an idempotent bridge to the existing
canonical model catalog builder.

**Truth Boundary:**
- IMPLEMENTED: manual or pre-authorized scheduled one-shot invocation, fixed
  GET envelope, redirect/deadline/body/record bounds, duplicate-group poison
  handling, allowlisted candidate metadata, separate outside-repository attempt
  and last-known-good artifacts, and offline injected-transport tests.
- NOT IMPLEMENTED: automatic scheduling, registry mutation, model selection or
  promotion, runtime binding, RedDog provider evidence, provider credentials,
  startup imports, or live provider calls in tests.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

---

## [2026-07-18] - Signed Aggregate Fusion PANEL Evidence

**Who:** 0102 Codex worker, architect-audited lane
**Type:** Production Evidence / Runtime Binding Security
**Slice:** MODEL_SIGNED_PANEL_EVIDENCE_PHASE1

**What:** Added a separate signed aggregate PANEL envelope and required it for
PANEL runtime binding. Every member's existing signed benchmark/promotion chain
is verified first; the aggregate binds ordered roles, models, providers,
per-member evidence IDs/digests, catalog, selection, task, topology, policy,
runtime surface and explicit synthesizer before aggregate signature and nonce
admission.

**Truth Boundary:**
- IMPLEMENTED: process-local sealed PANEL proof, deterministic rehydration,
  independent member verification, anti-splice checks, signer trust/revocation/
  freshness, replay rejection, exact runtime identity/projection gate, and
  adversarial construction/replacement/copy/pickle tests.
- NOT IMPLEMENTED: Fusion consumer wiring, provider calls, model discovery or
  ranking, artifact supply/bootstrap, WRE scheduling, OpenClaw/Hermes changes,
  signing/private-key custody, durable nonce/trust stores, live execution.

**WSP References:** WSP 00, WSP 15, WSP 22, WSP 50, WSP 62, WSP 97.

**WSP_15 Score:** Complexity 4 + Importance 5 + Deferability 5 + Impact 5 =
19 (P0 security boundary).

---

## [2026-07-18] - Kimi K3 OpenRouter AutoResearch Candidate

**Who:** 0102 Codex
**Type:** Model Candidate / Configured Gateway Wiring
**Slice:** MODEL_AUTORESEARCH_OPENROUTER_KIMI_K3_PHASE1

**What:** Added Kimi K3 to the static candidate catalog and enabled the existing
configured AutoResearch gateway to target exact OpenRouter model assignments.

**Why:** The combination harness and campaign loop were already implemented, but
`AIGatewayConfiguredModelCaller` could not execute an OpenRouter candidate. This
prevented governed held-out comparison of Kimi K3 with RedDog's existing panel.

**Truth Boundary:**
- IMPLEMENTED: explicit `openrouter` provider, exact `moonshotai/kimi-k3`
  candidate metadata, mandatory-max-reasoning request shape, 4096-token default,
  separate input/output cost accounting, catalog and caller tests.
- NOT IMPLEMENTED: automatic fallback to OpenRouter, automatic promotion,
  implicit candidate-pool mutation, or bypass of benchmark/verifier receipts.

**WSP References:** WSP 15, WSP 22, WSP 50, WSP 84, WSP 97.

**WSP_15 Score:** Complexity 3 + Importance 4 + Deferability 4 + Impact 4 =
15 (P1).

---

## Future Changes
- Enhanced routing algorithms (Phase 1)
- Cost optimization features (Phase 2)
- Enterprise monitoring (Phase 3)
- Multi-provider ensemble methods (Phase 4)
