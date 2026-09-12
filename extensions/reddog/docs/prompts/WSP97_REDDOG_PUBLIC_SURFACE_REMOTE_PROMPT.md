# Remote work order: RedDog public host, AutoPost attention, and website adapters

Status: work order only; not completion or execution authority by itself.  
Origin: external principal 012. Role: 0102 architect/engineer.  
Current audit anchor: `docs/audits/architecture/REDDOG_SURFACE_RUNTIME_RECONCILIATION_20260912.md`.

Canonical navigation: [RedDog documentation map](../../../../docs/REDDOG_DOCUMENTATION_MAP.md) ·
[public admission contract](../REDDOG_PUBLIC_SURFACE_ADMISSION.md) ·
[test inventory](../../../../modules/communication/moltbot_bridge/tests/public_surface/README.md).

## Source lineage and completion ledger

Merged baseline:

- PR #1633: public guest consent, caps, expiry, replay/cancellation boundary.
- PR #1635: lost-response nonce/revision status recovery and DatabaseManager-wrapper tests.
- PR #1639: non-biometric Lick PoC; AutoPost PR #11 is the matching mobile client/provenance surface.

Open/stale evidence:

- PR #1641 implemented/tested host leases and orphan recovery but was never merged and is stale relative to current main. Preserve it as evidence; do not merge it directly.
- PR #1648 contains useful foundups.com/eSingularity.ai/OpenRouter delivery work but duplicates the public session/accounting authority in Cloudflare D1 and is stacked on another open branch. Preserve useful UI/provider/knowledge work; do not merge the duplicated authority unchanged.

Current 2026-09-12 reconciliation branch rebuilds the host-lease source from current main. Read its live PR/check state before treating that capability as merged.

| Work | Source state / remaining evidence |
|---|---|
| Public guest consent, caps, expiry and replay | merged; router still optional/unmounted |
| Lost-response nonce/revision recovery | merged; same bearer/surface/origin/subject; never replays inference |
| Non-biometric Lick + AutoPost provenance | merged in both repositories; no identity/authority claim |
| Public host lease/orphan recovery | being reconstructed from current main; requires fresh exact-head CI and merge |
| AutoPost RedDog attention | not implemented; current camera/Liquid/recording paths are not RedDog attention |
| Resident startup/renew/replacement/shutdown lease adapter | not implemented |
| Public-only model responder + trusted edge/shared accounting | not activated |
| foundups.com/eSingularity.ai RedDog | #1648 is reusable evidence/UI/provider work, not merge-ready architecture |
| Protected 012/0102 identity and 3V integration | public Lick evidence remains provisional/no-authority |
| Private context deltas, voice/TTS and omission critic | separate dual-loop work after public surface boundaries are proven |
| Live HoloIndex recursive repair | requires reachable configured owner and exact receipt; GitHub CI is not that proof |

## Recover and isolate

1. Read `AGENTS.md`, WSP_00, WSP_97, WSP_10, WSP_15, the RedDog documentation map, public admission contract, and current surface reconciliation audit.
2. Run the real WSP_00 bootstrap/tracker from canonical repo root.
3. Run the canonical HoloIndex owner query. Require current/no-gap evidence.
4. Record exact current HEAD, working trees, owned PRs and runtime bindings. Preserve concurrent work.
5. Never revive stale branch state by force-resetting current main.

If HoloIndex fails, preserve the original failure/HEAD, use the governed owner incident/repair route, test that owning repair, requery, then return to the RedDog transaction. Missing owner/runtime configuration is not permission to weaken freshness or reindex in a user-facing query.

## Transaction A — merge current-main host lease recovery

The public gate must have exactly these invariants before exposure:

- fresh random owner token per public-host process lifetime;
- raw owner token never persisted;
- one registration per owner; expired identity cannot resurrect;
- renewal only while live;
- busy reservations bound to the owner;
- replacement can reclaim only after recorded owner expiry;
- recovery clears busy ownership only: never revision/nonce/Lick/quota/expiry;
- no inference replay/refund;
- pre-lease ownerless busy rows remain fail closed;
- HTTP `PublicSurfaceBinding` refuses an unleased gate.

Use current-main tests/TestModLog and regenerate the canonical registry. Run focused public boundary and repository CI on the exact final head. Merge through a clean squash PR only after those gates pass.

## Transaction B — AutoPost RedDog attention

Work in `FOUNDUPS/autopost` from fresh main. Reuse its existing camera stream, `CaptureController`, Lick client, provenance, correction UI and local Liquid vision. Do **not** create a second camera stack.

Implement an explicit RedDog sensory state:

```text
DORMANT
  preview may exist; local capture intelligence may exist
  no remote RedDog visual/audio/STT processing

ATTENDING
  entered only by explicit visible engagement/hold
  may sample bounded frames from the same viewport
  may process permitted microphone audio through a governed browser/STT adapter
  may emit bounded transcript/percept events to RedDog/0102

release/cancel/background/session invalidation/transport loss -> DORMANT
```

Keep separate:

- camera permission/preview;
- local Liquid/WebGPU analysis;
- photo/video recording and media retention;
- Lick encounter/provenance;
- RedDog attention;
- RedDog conversation transcript;
- publishing.

Do not send raw continuous video by default. The first visual contract should be sampled/bounded and explicitly scoped. Do not save RedDog bearer or raw conversation to localStorage.

Before writing tests, read AutoPost's closest test inventory/TestModLog/fixtures. Extend existing test files when possible.

## Transaction C — resident lease lifecycle

Reuse the existing broker-managed OpenClaw resident service and DAE launch broker. Do not create a second server.

Bind the public gate lifecycle:

1. generate owner on public resident startup;
2. initialize AgentDB gate and register once before public binding exists;
3. renew on a bounded scheduler safely inside the 60-second lease;
4. replacement process registers a new owner and reclaims only expired-owner busy slots;
5. stop renewal before shutdown; never reuse old owner;
6. status/health exposes bounded lifecycle state without owner material;
7. provider/PublicSurfaceBinding remains a distinct zero-tool public surface, never private OpenClaw/Memex fallback.

DAE heartbeat can trigger/observe renewal only through an explicit tested adapter; existing heartbeat records alone are not the lease.

## Transaction D — visual/audio transport

There is no authorization to push camera/microphone data through the ordinary text `turn` shape.

Inventory existing STT and perception contracts first. Current Foundups-Agent STT ownership includes `modules/infrastructure/cli/src/openclaw_voice.py`; the Japanese-call module reuses that policy. A browser adapter may use browser-native/local encoding/transport as needed, but language selection, transcript normalization and RedDog/0102 admission must conform to the existing voice ownership rather than create a competing STT authority.

Define separate bounded sensory event shapes with purpose, surface, encounter/Lick reference, timestamp/freshness and retention/disclosure. Prove dormant state sends none. Raw media storage/biometric extraction remains off unless a separate consented contract explicitly adds it.

## Transaction E — websites

Rebase/salvage #1648 on current main only after the shared public contract is merged.

Keep useful work where still valid:

- public RedDog UI on foundups.com/eSingularity.ai;
- fixed server-side OpenRouter model/provider selection;
- no browser provider key;
- public knowledge packet/source links;
- strict public/private context boundary;
- deployment-owned ingress/key configuration.

Do not maintain an undocumented second public-session authority. Choose and document one of these before implementation:

1. route website sessions to the canonical resident public gate; or
2. keep Cloudflare/D1 as an edge deployment adapter **only** with explicit contract-parity tests against the canonical semantics and a clear single-authority/conformance rule.

The edge may enforce stricter limits. It must not diverge on Lick, nonce/revision, quotas, expiry, recovery, disclosure or authority ceilings. Public website sessions never inherit 012's private bearer/context.

## Identity and 3V

Lick contributes evidence to Verification. It does not perform Validation/Valuation or grant work authority. A human account uses separately verified possession proof; an agent uses its own key/registration/delegation. Names, voice, conversational knowledge, `tSingularity`, or the answer to "why 0102?" are not authentication and never remove caps.

## Acceptance

For every slice:

- WSP_97 evidence before design;
- HoloIndex owner retrieval when runtime exists;
- reuse test inventory before new test files;
- focused tests, dependency/security tests, then appropriate macro CI;
- exact-final-head checks, no historical aggregate substitutions;
- no deployment claim from source/tests;
- clean PR and squash merge;
- update TestModLog/documentation map/HoloIndex only where ownership requires it.

Return after public surfaces are proven to the private dual-loop sequence:

`authenticated private conversation -> authorized context deltas -> fast RedDog injection -> voice/TTS -> omission critic -> WSP_15 intervention ranking -> governed workers`.
