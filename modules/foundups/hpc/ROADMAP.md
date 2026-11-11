# HPC roadmap

| Stage | Status | Dependencies | Acceptance criteria and evidence |
| --- | --- | --- | --- |
| 0 · Genesis | Implemented in the review candidate | WSP 109, Vote ID, registry and manifest validators | Eight intake artifacts, valid genesis envelope, canonical `hpc` registry and `/f/hpc` namespace. Evidence in [intake](docs/intake/INTAKE_SOURCE.md) and [ModLog](ModLog.md). |
| 1 · PoC | Initial release live; playback recovery implemented and tested locally | Shared Mall shell, reviewed Move2Japan metadata, Vote's manual contact page | Eight Shorts, in-Mall play, separate immersive action, stable return, and guest boundaries. [Shared incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md) tracks provider evidence, physical iPhone and release gates. |
| 2 · Prototype | Specified | PoC acceptance, provenance and rights policy, shared preference owner and privacy review | Nomination, duplicate/source review, moderation, discoverable filters, persistent seven-level preferences, edit/clear, and abuse tests. Accepted events remain separate from evidence and economics. |
| 3 · MVP | Specified | Qualified moderation and escalation, independent Voice admission, preference aggregation and governance review | Moderated community submissions, working consented Voice handoff and recovery, reproducible aggregate reports and governance interfaces with correction and appeal. |
| 4 · Federation | Specified | WSP 103/104 interoperability, verified Vote/Voice interfaces and tenant isolation | Cross-FoundUp discovery, versioned context with consent, provenance and access scopes preserved in conformance tests. |

## Shared preferences and evidence

The Mall owns interaction design for video tiles. The existing player implements a browser-local bookmark and sharing. The seven-level press-and-hold preference control is specified in the Vote/Voice discussion and [EduIT interaction notes](../eduit/docs/EPISODE_TILE_CONTROLS.md). The audited Mall has no selector, approved scale, persistent preference event or aggregation integration.

Prototype acceptance requires a shared, visible preference control with press-and-hold and accessible keyboard/button access to the same signed scale. A participant can revise or clear a rating. Absence, neutral and negative values are distinct. Confirm the labels and endpoints with the interaction owner. Define event identity, source video identity, consent and retention, edit/delete semantics, deduplication, anti-bot and coordinated-abuse tests, aggregate coverage and uncertainty before collecting preferences.

[WSP 29 CABR](../../../WSP_framework/src/WSP_29_CABR_Engine.md) owns validation, verification and valuation. Preference can inform discovery after consent and abuse checks. Independent source records and review govern credibility and factual verification. Any future CABR mapping requires a reviewed event/evidence contract and independent tests. No issuance, rewards or governance authority comes from PoC viewing or saving.

## H1 — Responsive WikiTube-style discovery and shared thumb dock (specified; 012 request 2026-11-11)

**Outcome:** HPC is a configured Vote-family projection of the canonical Play FoundUps Mall. The same corpus supports a phone-first portrait field and a desktop theater view without a second player, shell, router or video store. This is a requested roadmap expansion, **not implemented, tested, or deployed** by this documentation change.

### H1A · Verify the prior art and current platform before implementation

- Search the full available organization/local source history for **WikiTube TV / WikiTubeTV / WikiTube.tv** and the historical desktop theater: dominant video viewport, continuously advancing bottom thumbnail/queue strip, search feeding the strip, player controls, and restoration. A prior user-referenced public deployment is `wikitube-tv-56566376153.us-west1.run.app`; that URL is an identification lead, **not verified present-day source or runtime evidence**. If source cannot be recovered, record the retrieval gap; do not rebuild based on an assumed implementation.
- Audit shared `public/member/` desktop responsive behavior, `mall-tile-field.js`, `mall-video-player.js`, `mall-state-restore.js`, `account-concierge.js`, `pfmall-control-dispatcher.js`, current public projections, and AutoPost's external repository/approved handoffs. Compare existing data/gesture/route contracts before any UX mutation.
- Determine whether the existing Mall's category/creator search, queue advancement and responsive layouts meet part of the specification. Record `REUSE_AS_IS`, `EXTEND_SHARED`, `ADAPTER_REQUIRED`, or `PLANNED_ONLY` per feature. Video playback and YouTube availability remain independently gated by [shared incident](../pfmall/MEDIA_PLAYBACK_INCIDENT_HPC.md).

### H1B · Shared responsive interface (PoC proposal, no independent HPC shell)

| Surface | Requested interaction | Owner and verification gate |
| --- | --- | --- |
| Desktop / larger monitor | WikiTube-style theater: constrained main video (not browser fullscreen), bottom continuously advancing thumbnail/queue strip, **bottom search** between video and strip; clicking starts in-context playback and advances to the next eligible queue item | Existing Mall player, field, and search; real desktop browser queue/search regression tests |
| Phone | Existing three-column portrait tile grid with vertical browsing, inline play when user taps, separate expand/pinch and return; fixed HPC header and safe-area **floating bottom dock** | Shared Mall tile/gesture/state owners; physical iPhone PWA tests |
| Search | Google-like single input near the thumb/mouse rest area; search updates the same catalog/playlist rather than opening an unrelated webpage. Query/filters and selected video retain stable identity and reversible state | Existing bounded `search_catalog`/catalog owners, with scope-aware rules; no remote semantic search claim without a working adapter |
| Dock left | **+** opens an upward agent/model options sheet. Only list actually available, authorized, device-compatible agents; preserve active selection and explain unavailable models without claiming their presence | Shared RedDog/agent-admission owner; never expose model secrets or allow browser to select execution authority directly |
| Dock right | Red Dog/FoundUps icon: press-and-hold for agent-directed speech, release to submit; adjacent **mic** invokes platform/browser speech-to-text input where supported; **camera** navigates through an approved AutoPost handoff and returns to the same Mall context | Explicit permission, authenticated resident handoff, STT capability detection, AutoPost route contract and user gesture/consent gates |
| Search by voice | “Give me the new videos” produces a request to the authorized agent, with a bounded `latest` sort that ignores popularity; preserve transparent sort/filter state and original sources | Read-only catalog adapter and real resident speech→intent→projection proof; no simulated agent execution |

HPC's earlier **hidden global-search** scoped-view choice is superseded by this **HPC-scoped bottom search** request; it does **not** grant search access to unrelated FoundUps or bypass route/catalog permissions. Keep the separate master-Mall navigation by the existing FoundUps dog logo and the independent-site disclosure.

### H1C · Voice and capture architecture dependencies

- **Input separation:** platform STT mic = dictated query/text, where available; Red Dog hold control = speech input routed through authorized resident conversation/agent ingress. Both may use phone STT as a supported fallback only with clear indication and user permission. The presence of `startListening` UI effects is not transcription, model orchestration, or a working conversation.
- **Resident boundary:** do not connect browser model picker to raw WRE/Hermes execution, unverified model inventories, or credentials. Bind to the existing approved identity, speech, context, admission and auditing protocols. Speech remains user-controlled; no background recording.
- **AutoPost boundary:** external `FOUNDUPS/autopost` owns camera/capture implementation. Launch it through an existing route or agreed authenticated cross-app handoff, with explicit origin and return-state tests; do not copy its camera stack into the Mall. Its local model/capture features do not establish an available Red Dog speech backend.
- **Touch conflict:** account for scroll, pinch, press-and-hold, plus-sheet swipes, iOS safe areas, keyboard opening, and iframe touch ownership. All gestures need accessible non-gesture alternatives.

### H1D · Stage and evidence gates

1. **Research / contract addendum (current):** identify WikiTube source/runtime or record absence; inventory current Mall and AutoPost owners; choose a shared responsive search/dock contract and device/desktop test cases.
2. **PoC extension (planned):** implement **one** bounded search/query→tile/queue update for HPC using shared catalog APIs; prove desktop bottom strip and mobile dock are different responsive presentations of the same state; preserve the deployed video repair branch and other FoundUps.
3. **Prototype (planned):** gated mic/STT and resident Red Dog speech-to-query (with genuine execution receipts), agent-picker admission and AutoPost handoff; verify cross-app return and denial/error states. Do not call this working before tested.
4. **MVP (planned):** continuous catalog updates, measured playback/queue robustness, accessibility and device matrix; verified provider consent/privacy, observability and recovery. Creator/community nomination and seven-level preference stages remain independent.

No deploy/merge assertion is made. Maintain `PAIN.md`, `INTERFACE.md`, tests and ModLog for each actual implementation slice; record source/revision evidence and physical iPhone outcomes.
