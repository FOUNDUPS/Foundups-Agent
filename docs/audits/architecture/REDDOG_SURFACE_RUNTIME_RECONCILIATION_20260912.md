# RedDog Surface Runtime Reconciliation Audit — 2026-09-12

Status: point-in-time evidence and repair decision; not deployment evidence.

Audited roots:

- `FOUNDUPS/Foundups-Agent` main: `3b74a04205b05fc0d84172d52b8862ff608b1d6e`
- `FOUNDUPS/autopost` main: `4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147`
- superseded/stale RedDog host branch: PR #1641, head `7faa4e90b9648f30b653e41c2341ac54965b96ef`
- stacked website RedDog branch: PR #1648, head `a77e284b8b72f1e731b97a987e1a48478755fda9`

This audit follows the canonical RedDog documentation map. It distinguishes merged implementation from open-PR evidence and does not promote an old green check to current-main acceptance.

## 1. Canonical architecture remains aligned

Current architecture is coherent and should not be replaced:

```text
012
 <-> RedDog — fast interaction / attention surface
 <-> 0102 — deep cognition / continuity / orchestration
 <-> governed FoundUps Agent tools and workers
```

`extensions/reddog/ARCHITECTURE.md` owns the identity boundary. `docs/architecture/REDDOG_DUAL_LOOP_COGNITION_ARCHITECTURE.md` owns the fast/deep cognition split. RedDog may consume speech, text, gestures, device events, and permitted live context, but deep memory, verification, WSP application, model escalation, and worker orchestration remain below the surface in 0102.

## 2. Lick is implemented as a non-authoritative encounter handshake

Foundups-Agent main contains the non-biometric Lick PoC. AutoPost main contains the matching memory-only client, consent/guest UI, one-use challenge flow, and bounded capture provenance linkage.

The current Lick remains:

- consent-aware;
- provisional;
- unsigned;
- non-biometric in the PoC;
- `authority_granted: none`;
- an input to Verification, not identity or execution authority.

AutoPost is a capture surface. It does not become identity authority merely because it hosts RedDog.

## 3. AutoPost is not yet the RedDog conversational/sensory runtime

AutoPost already instantiates `useLickEncounter()` and attaches the resulting encounter context to capture records. It does **not** currently provide a RedDog conversation loop, STT/TTS exchange, or explicit RedDog attention state.

Current camera behavior matters:

- `useCameraSession()` initializes a camera stream while the camera screen is active.
- `CaptureController.getStream()` requests video and audio together.
- `useVisionAgent()` can perform local Liquid/WebGPU frame analysis on a cadence while the camera view is active.
- `RecordButton` currently owns capture semantics: tap photo; hold video; release stop; optional record lock.

Therefore camera preview, microphone track availability, local Liquid perception, recording, and RedDog attention are currently separate concepts even though the UI makes them appear adjacent.

## 4. Required AutoPost RedDog attention contract

The physical interaction discovered through 012/0102 alpha use is now explicit:

```text
camera preview available
        |
        +-- RedDog DORMANT
        |
press/hold RedDog attention control
        v
RedDog ATTENDING
  - may sample the same camera viewport the principal is pointing
  - may process permitted microphone audio through the governed STT path
  - may send bounded transcript/percept events into the RedDog/0102 loop
        |
release / cancellation / surface loss
        v
RedDog DORMANT
```

Invariants:

1. Preview alone is not permission for RedDog conversational vision/audio processing.
2. Local camera intelligence may continue locally for capture UX, but it must not be mislabeled as RedDog attention or silently exported.
3. RedDog visual ingress is sampled/bounded, not an implicit raw-video upload.
4. RedDog audio/STT ingress is active only during explicit attention unless a separate visible continuous-listen mode is later designed and consented.
5. Existing photo/video recording semantics and media retention remain separate from RedDog attention.
6. Releasing attention ends RedDog sensory ingress even if the camera preview remains open.
7. Browser/device interruption, backgrounding, Lick/session expiry, participant change, or network loss returns the remote RedDog attention path to dormant/fail-closed state.
8. No attention event creates identity, memory-disclosure, work, or execution authority.

The first implementation should expose an explicit `dormant | attending` state and lifecycle hooks. It should reuse the current camera stream and existing STT ownership rather than create another camera or speech stack.

## 5. Voice/STT ownership already exists

Foundups-Agent already owns the current voice/STT runtime in `modules/infrastructure/cli/src/openclaw_voice.py`, including Whisper/Cohere/Google paths and explicit Japanese language selection. The merged Japanese-call work also reuses those capture/STT contracts.

AutoPost RedDog must not invent a second speech-recognition authority merely because the microphone originates in a browser. Browser audio transport/adaptation is a new surface adapter; STT policy, language selection, transcript normalization, and downstream RedDog/0102 context admission should reuse or conform to the existing voice contracts.

## 6. Public host crash recovery is missing from current main

PR #1641 implemented and tested host/process lease semantics, but it was never merged. Current main still has the earlier `PublicSessionGate` without host ownership.

The useful #1641 behavior is retained as evidence, not merged as stale history:

- content-free `reddog_public_host_lease_v1`;
- one-use hashed host owner;
- bounded renewal;
- owner-bound busy reservations;
- replacement-host orphan recovery only after prior lease expiry;
- no nonce/revision/quota rollback;
- no inference replay/refund;
- Lick challenge/profile state preserved;
- pre-lease unknown busy rows remain fail closed;
- public HTTP binding refuses an unleased gate.

This audit branch rebuilds those semantics from current main and requires fresh exact-head verification before replacement of #1641.

## 7. Website PR #1648 duplicates public-session authority

PR #1648 contains valuable website/OpenRouter delivery work, but its current implementation creates a second RedDog public-session/accounting authority in Cloudflare D1:

- separate session rows;
- separate daily/global budgets;
- separate nonce/revision state;
- separate concurrency reservation;
- separate timeout/withdraw/status lifecycle;
- a duplicated TypeScript policy described as a Cloudflare adapter of the Python policy.

This cannot merge unchanged as a second canonical authority beside `reddog_public_session_gate.py`.

Decision:

- The RedDog public-session **contract** is singular.
- AgentDB/Python remains the canonical reference implementation for the resident/public host lane.
- A Cloudflare/D1 implementation may exist only as an explicitly conforming deployment adapter with contract tests proving parity and a documented ownership rule. It may enforce stricter edge ceilings, but it must not silently diverge in identity, Lick, nonce, quota, recovery, or authority semantics.
- Website UI/OpenRouter/knowledge work from #1648 should be salvaged separately from its duplicated session authority.
- #1648 remains unmerged until it is rebased/reconciled onto current main and this ownership conflict is removed.

## 8. Resident host seam exists but public lifecycle binding does not

The repository already has the broker-managed OpenClaw resident service and DAE launch broker. The broker owns runtime threads and heartbeat reporting. This should be extended, not replaced.

Missing runtime slice:

1. generate a fresh public host-owner secret for each resident process lifetime;
2. initialize and register the public lease before exposing `PublicSurfaceBinding`;
3. renew the lease from the resident lifecycle at an interval safely inside the lease window;
4. on replacement startup, register a new owner and reclaim only expired-owner busy slots;
5. stop renewal before shutdown and never reuse the old owner token;
6. keep the public-only responder separate from the private OpenClaw/Memex/worker path.

DAE heartbeat is useful lifecycle evidence but is not itself the public-session lease unless explicitly bound and tested.

## 9. Repair order

WSP 15 planning order for this reconciliation:

1. **P0 — current-main public host lease/orphan recovery.** Shared prerequisite for safe exposure and crash recovery.
2. **P0 — AutoPost RedDog attention state.** Establish dormant/attending consent boundary without inventing duplicate camera/STT stacks.
3. **P0 — resident lifecycle adapter.** Bind real startup/heartbeat/replacement/shutdown to the lease-backed public gate.
4. **P0 — website delivery reconciliation.** Salvage #1648 UI/OpenRouter knowledge work while removing or formally conforming the duplicate D1 authority.
5. **P1 — deeper 0102 context deltas, voice/TTS surface integration, omission critic/WSP_15 intervention ranking.** These remain private-principal capabilities and must not bleed into public guests.

## 10. Truth boundary

This audit does not claim:

- a live HoloIndex owner query from the ChatGPT environment;
- a mounted public router;
- a deployed AutoPost RedDog conversation;
- live public website chat;
- provider inference;
- protected 012/0102 authentication;
- private Memex access from public surfaces;
- live voice transport from AutoPost;
- omission-critic runtime completion.

GitHub exact-source retrieval is the fallback evidence in this environment. Current-main CI and HoloIndex freshness checks must be rerun on each implementation PR; a historical #1641 or #1648 result is not current acceptance.