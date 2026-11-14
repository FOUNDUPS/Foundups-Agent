# Assumption Audit: RedDog Holo Owner Acquisition Reliability Phase 1

## 1. Problem Statement

- **What:** The supported one-shot HoloIndex caller can inherit an obsolete
  replica-root environment and independent caller processes can contend for the
  fixed loopback owner port.
- **Why:** RedDog, ChatGPT/Codex, and IDE processes must reach the same verified
  CURRENT Holo generation without manual environment repair or accidental
  `HOLOINDEX_QUERY_SERVICE_PORT_IN_USE` failures.
- **Who:** Authorized by 012; executed by 0102/architect under WSP 00, WSP 15,
  WSP 50, WSP 62, and WSP 97.
- **Base:** `90e9eca19f810a03ffaacde0edfffbce2de9513b`.
- **Allocation:** WSP 15 `C4/I5/D5/Impact5 = 19/P0`.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | The active sealed replica and canonical authority are healthy. | A governed query passed `CURRENT`, exact base, no gap, no reindex after explicit route normalization. | HIGH |
| A2 | User-scope route state is configuration, not authority. | The route resolver independently proves the private route record, terminal journal, repository, receipt, descriptor, and immutable replica. | HIGH |
| A3 | Port selection grants no trust. | The supervisor creates a process-private bearer and accepts readiness only after authenticated exact-binding health. | HIGH |
| A4 | One process-sharded port range is an availability layer, not final scale. | Each caller still starts an isolated semantic owner; shared resident service/IPC is absent. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | A stale process-local legacy replica root masks the current user route. | HIGH | HIGH | The supported wrapper reads only the two non-secret user-scope routing values, prefers a non-empty current route pointer, and removes the legacy root only in its private copied environment. The strict low-level resolver remains unchanged. |
| F2 | The user route is malicious, stale, malformed, or races activation. | LOW | HIGH | No route is trusted by precedence. Existing terminal-journal, private-path, descriptor, repository, receipt, generation, and replica proofs still fail closed before owner startup. |
| F3 | Two independent callers choose the same port. | MED | MED | Use a bounded PID-sharded range and give every process-owned second attempt a different candidate from its own first. `HOLOINDEX_QUERY_SERVICE_PORT_IN_USE` is the newly admitted acquisition failure within the existing bounded transient retry set. The 4,032 ordered pairs are not globally unique. |
| F4 | An unknown local process occupies a candidate port. | MED | HIGH | Treat the known listener as foreign; the supervisor's exclusive bind probe fails before token creation/spawn. The wrapper may try one different port, then stops without adoption or kill. |
| F5 | A process binds after the availability probe but before owner spawn. | LOW | HIGH | The private bearer and exact health binding remain required, so the attempt fails closed. This is not hardened against a hostile same-user process; one bounded next-port attempt is allowed and no identity, freshness, or token rule is relaxed. |
| F6 | Port sharding is misreported as horizontal scale. | MED | MED | Documentation labels it bounded multi-caller availability only and keeps resident per-user broker plus authenticated local IPC as the next scaling slice. |
| F7 | A route refresh reads or publishes a credential. | LOW | CRITICAL | The refresh allowlist contains authority-root and route-file names only. Service URL/token and all unrelated environment values are neither read from user scope nor serialized. |

## 4. Alternatives Considered

| Alternative | Why Rejected for This Phase |
|---|---|
| Keep manual environment sanitation/restart | It leaves RedDog and long-lived ChatGPT/IDE processes unusable after governed activation. |
| Relax the low-level dual-route rejection | It would hide ambiguous direct callers and weaken an intentional security boundary. |
| Connect to the existing listener on port 8127 | The independent caller has no authenticated process-private handoff and must not trust port ownership. |
| Persist or publish the owner bearer token | It expands secret lifetime and creates a reusable local credential. |
| Cross-process lease around fixed port 8127 | It is correct for short one-shots but serializes 30-plus-second cold starts and can make a second caller exceed the existing 60-second operation deadline; a long-lived resident owner would block it entirely. |
| Build the resident broker and Windows named-pipe transport in this patch | It is the scalable target, but it is a distinct security/IPC lifecycle requiring its own reviewed layer and acceptance matrix. |

## 5. Decision Record

- **Decision:** PROCEED with the smallest bounded layer: private user-route
  environment refresh in the supported wrapper, exact validated owner-port
  propagation, PID-sharded candidate selection, and one bounded transient
  retry that includes `HOLOINDEX_QUERY_SERVICE_PORT_IN_USE`.
- **Non-goals:** no shared token, no listener adoption, no owner kill by PID,
  no reindex, no route mutation, no timeout increase, and no final scale claim.
- **Owner:** 0102/architect.
- **Timestamp:** 2026-08-27T09:40:00+09:00.
