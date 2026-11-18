# AmIBot - Chat, PWA and Safety Research

Date: 2026-09-15. Status: researched design recommendation, NOT_IMPLEMENTED.
Owner: 012; documentation: 0102. Internal FoundUp ID remains `detect_ai`.

## Decision

Build a phone-friendly browser/PWA interface backed by one trusted round service. Recommend Socket.IO for the small text-chat POC, conditional on first inspecting existing FoundUps transport/authentication owners. Colyseus is the alternative when its room/auth/matchmaking abstractions reduce more work than they add. Do not introduce both.

Begin with one clean, adult-only, invite-gated queue. Basic moderation is required before real participants exchange messages. Defer the mature/NSFW lane, strong age-proof integration for that lane, and optional phone-hosted AI experiments. The display name is AmIBot; the tagline is "Can you detect AI?".

This recommendation follows source review, not a deployment, benchmark, security audit or legal clearance. No license/package compatibility or device-performance pass is implied.

## Open-source shortlist

| Candidate | What the source establishes | Fit and decision |
|---|---|---|
| Socket.IO (MIT) | Client/server events, rooms, acknowledgements and reconnect support; not a finished chat product [S1-S4] | Recommended transport. AmIBot still needs queue admission, random pairing, moderation, identity hiding, scoring and UI. |
| Colyseus (MIT) | Authoritative room framework, matchmaking and room authentication [S5-S7] | Strong alternate backend. Keep hidden truth outside synchronized state; its join functions do not themselves define the experiment's random sampling. |
| GAPITA (MIT) | Complete random one-to-one browser text-chat application, C#/SignalR and TypeScript; no-login design [S8] | Useful reference, not a production-ready shortcut. Inspected target is net6.0 and client dependency includes a legacy SignalR preview [S9-S10]; modernization and audit would precede reuse. |
| Chitchatter (GPL-2.0) | Self-hostable, ephemeral WebRTC peer chat; shared room URLs; encrypted direct connections where possible, relay fallback [S12] | Good private-chat reference, poor default for centrally moderated blinded rounds. It does not supply our trusted random assignment, scoring or age control. |

GAPITA's .NET 6 target is out of vendor support: Microsoft lists November 12, 2024 as its end date [S11]. That specific finding is not a claim that every dependency is vulnerable or that no maintenance has occurred.

A random-looking room name is not random stranger matching. None of these sources establishes an off-the-shelf AmIBot with audited age checks, consented training and our three benchmark tracks. Do not copy an entire chat application's identity/history assumptions into this experiment.

No source code was copied in this slice. Before dependency adoption, pin a supported release/commit, inspect its license and transitive dependencies, run the dependency audit and prove the minimal two-client flow. MIT/Apache components still carry notice obligations; GPL reuse requires a compatibility review. The application license is a separate decision.

## Smallest useful architecture

Use existing FoundUps sign-in and entitlement services where their actual interfaces prove suitable. For a closed pilot, an expiring invite session can be the admission mechanism; it is not proof of adulthood. Do not expose profile pictures, account names, provider identifiers or login methods to the partner.

The phone runs the chat view and controls. The backend validates sessions, owns the queue and assignment, applies moderation, relays accepted messages, enforces the round deadline, locks guesses and computes scores. AI calls stay behind the approved server inference boundary. A small persistent event/score store supports duplicate prevention and recovery; do not assume all raw text needs permanent storage.

An AmIBot game room is product logic, not a second FoundUps orchestrator. WRE remains development/execution coordination; it need not route every keystroke. Reuse proven owners rather than exposing WRE/agent tools to public chat users.

Proposed participant flow: sign in/invite -> accept rules -> join clean queue -> neutral chat -> locked human/AI verdict and confidence -> coordinated reveal -> provisional score -> rematch. Start the declared 120-second conversation only after endpoints are ready.

Server admission considers content policy, declared language, age eligibility, bans and blocked pairs before matching. Choose the experimental assignment independently of current human availability; if the human arm has no partner, offer waiting or labeled AI practice, not silent substitution. Keep human enrollment and completion/attrition records separate from the nominal 50/50 assignment target.

Socket.IO guarantees ordering for delivered events, but default arrival semantics are at-most-once [S3]. Therefore define event IDs, acknowledgements, server sequence offsets and idempotent verdict/score writes. Reject expired queued sends after reconnect. Revalidate permissions after disconnect; recovery is not a substitute for ban or age-expiry checks [S4].

## Phone and PWA feasibility

Yes: the interface can run as an installable web app. Apple documents Home Screen web apps, and Safari 26 includes WebGPU and updated web-app behavior [S13-S14]. For a Vite-based client, `vite-plugin-pwa` can supply a manifest and service-worker integration [S15]. Reuse the existing frontend toolchain if one is suitable; do not migrate a working app just to use this plugin.

The POC does not need an App Store binary or Discord account. It does need HTTPS and a reachable backend. A phone acting as a client is not the same as a phone hosting reliable global matchmaking.

Proposed device acceptance:

- Test actual iPhone/Safari in browser and Home Screen modes, Android/Chrome, and tablet layouts. A desktop mobile viewport is not a physical-device pass.
- Keep the composer, send, report and leave controls visible above the software keyboard; support large text, screen readers and reduced motion. Never make color or vibration the only status cue.
- Display connecting, searching, ready, reconnecting and moderation-hold states. Avoid an unexplained loading label; expose failures without revealing partner class.
- On suspension or network loss, resume from server state within a declared grace policy or terminate explicitly. Do not auto-submit a guess, invent a partner reply or double-score.
- Cache versioned public shell assets only. Chat, authentication, age proofs and verdict/score APIs must bypass service-worker caches. Clear private local state on logout; do not auto-replay old chat through background sync.
- Prompt for PWA updates between rounds, not during a timed conversation. Offline access means help/shell or a separately labeled local practice mode, never offline stranger matching.

Browsers can suspend pages and terminate service workers [S16-S17]. A PWA is not an always-running daemon. Optional Web Push can notify an opted-in user on supported installed iOS web apps [S18], but it does not keep matchmaking or model inference running continuously. Avoid private transcript/age information in notifications.

## Can a model run on the phone?

WebLLM supplies WebGPU-accelerated in-browser inference under Apache-2.0 [S19]. Transformers.js supplies browser inference through ONNX Runtime, including WASM/CPU and WebGPU options for supported models [S20]. These are real implementation options, not proof that every Qwen checkpoint fits every phone.

A later device probe should test GPU adapter/features, supported compiled model format, allocation and a bounded warmup generation. Ask before downloading model weights; show download progress and permit cancellation/removal. Measure load time, memory pressure, reply latency and observed stability. Use a foreground Web Worker to preserve UI responsiveness, without promising survival after suspension. Offer server-backed practice when the device cannot run the approved checkpoint.

Local inference must not undermine the test: running the opponent model in the judge's browser exposes inspectable code, weights and execution cues. Keep verified ranked trials server-controlled. Put phone-local experiments in explicitly unverified practice, with no economic rewards. A future opt-in compute-donation pool needs its own trusted-provenance, privacy, isolation and verification design; it is not enabled here.

## Clean and mature policies

SFW means safe for work; NSFW means not safe for work. Use clearer product labels: **Clean chat** and a future **18+ Mature** mode. "Anything goes" is not a suitable service promise.

Clean pilot policy: no profanity or sexual chat; reject harassment, hate, threats, scams and personal-data solicitation. Begin with one declared pilot language and test its filter; do not promise cross-language coverage from a word-list package name. All pilot participants are adults, admitted through a documented process before play. Clean content does not make unsupervised stranger matching appropriate for minors.

The future mature policy may relax language, but consent and baseline protections remain. Explicit sexual-content permission is a separate unresolved product/provider/legal decision. Do not equate an NSFW flag with permission for exploitation, non-consensual sexual conduct, abuse or illegal content. Under-18 participation requires a separate safeguarding design.

Separate queues by immutable round policy; no mid-round policy change or adult-to-clean fallback. Require explicit opt-in from both participants. Keep mature transcripts out of clean previews, notifications and training exports by default, and report mature/clean evaluation results separately.

## Minimum safety implementation

Enforce moderation on the server, not solely in editable browser code. Before delivery: validate membership and policy -> normalize a scanning copy of text -> apply rate/length and configured profanity rules -> evaluate conversation context -> deliver or hold/reject. Preserve accepted original text; do not silently rewrite it to sound more human.

`@2toad/profanity` is an MIT TypeScript word-list filter with configurable matching [S21]. It is a candidate first layer, not a detector for all harassment or sexual solicitation. Qwen3Guard-Gen-0.6B is an Apache-2.0 safety model candidate [S22]; its classifications still need calibration against AmIBot's stricter clean-chat policy. A model's generic Safe label does not mean "contains no profanity".

Use a tested contextual model or pre-delivery human review in a tightly bounded, staffed pilot. Apply the same content policy to human messages and AI responses. Buffer responses before moderation; do not stream harmful tokens and remove them afterwards. If moderation times out or fails, hold delivery and explain the technical hold neutrally.

Include report, block, immediate leave, blocked-pair exclusion, rate limits, plain-text rendering, no uploads/active links, and an operator kill switch. Test direct-API bypasses and reconnects, not only visible buttons. Evaluate false positives, obfuscated profanity, multi-turn harassment and policy drift; no filter guarantees zero abuse.

Server inspection means this design is not end-to-end encrypted between participants. Use encrypted transport and protected, access-limited storage, with an explicit notice explaining moderation access. Minimize transcript retention; the prior proposed seven-day maximum remains a proposal pending policy approval. Separate safety evidence, minimal score events and opt-in research/training data, with distinct retention/withdrawal processes.

## Age assurance and privacy

Login, a birthday entry and an 18+ checkbox are not interchangeable with verified age. For in-scope UK services allowing pornography, Ofcom requires highly effective age assurance and explicitly rejects self-declaration as sufficient [S23]. Applicability depends on the service and jurisdictions; this document is not universal legal clearance.

The EU age-verification blueprint offers an open-source, privacy-preserving proof-of-age reference [S24-S25]. Its official policy page was updated September 9, 2026. Availability of a blueprint does not establish universal deployment, trusted-issuer coverage or automatic acceptance for AmIBot. Retain it as an integration candidate, not a completed provider selection.

Design the game to consume a verified, session-bound over-18 assertion with issuer, expiry and replay protection where supported. Do not place passports, selfies, exact birth dates or proof tokens into chat logs or on-chain records. EDPB emphasizes using the least intrusive effective approach and protecting personal data [S26].

Before a mature/public launch, resolve country scope, applicable age/access obligations, provider and model terms, data-processing roles, retention, accessibility and an appeal/fallback route. Test unknown age, revoked/expired credentials, tampering, session transfer, endpoint bypass and accidental adult previews. Failed or uncertain eligibility denies mature access; the mature feature stays disabled until the gates pass.

## Build order and remaining evidence

First prove real human chat with admission and safety controls. Then add server-hosted model rounds, blinding and scoring. Then pass the combined PWA flow on actual phones. Multi-model rankings and agent judges follow in prototype; mature access and phone-local inference are independent optional expansions, not reasons to delay the clean POC.

Measure cost per completed valid round, separating inference, moderation, hosting, storage and operator work. Open-source software does not make hosting or moderation free. No pricing or performance estimate is asserted without a workload measurement.

Repository searches found Socket.IO dashboard/architecture references and WebSocket extension/domain references, not a certified reusable game service. Existing-owner inspection, source-bound HoloIndex, catalogs, dependency audit and runnable acceptance tests remain required in issue #1750. No packages, accounts, paid services, tokens, runtime manifest or public routes were activated.

## Primary sources

Sources retrieved 2026-09-15. Source capability is distinguished from our design recommendation above.

- S1: [Socket.IO introduction](https://socket.io/docs/v4/).
- S2: [Socket.IO MIT license](https://github.com/socketio/socket.io/blob/main/LICENSE).
- S3: [Socket.IO delivery guarantees](https://socket.io/docs/v4/delivery-guarantees/).
- S4: [Socket.IO connection-state recovery](https://socket.io/docs/v4/connection-state-recovery/).
- S5: [Colyseus matchmaking](https://docs.colyseus.io/matchmaker).
- S6: [Colyseus room authentication](https://docs.colyseus.io/auth/room).
- S7: [Colyseus MIT license](https://github.com/colyseus/colyseus/blob/master/LICENSE).
- S8: [GAPITA source and README](https://github.com/ehsan-mohammadi/GAPITA).
- S9: [GAPITA target framework](https://github.com/ehsan-mohammadi/GAPITA/blob/master/Gapita.csproj).
- S10: [GAPITA client dependencies](https://github.com/ehsan-mohammadi/GAPITA/blob/master/package.json).
- S11: [Microsoft .NET support policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core).
- S12: [Chitchatter source and architecture](https://github.com/jeremyckahn/chitchatter).
- S13: [WebKit features in Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/).
- S14: [Apple iPhone Home Screen web-app instructions](https://support.apple.com/en-gu/guide/iphone/iphea86e5236/26/ios/26).
- S15: [Vite PWA guide](https://vite-pwa-org.netlify.app/guide/).
- S16: [MDN offline/background PWA operation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation).
- S17: [Chrome page lifecycle](https://developer.chrome.com/docs/web-platform/page-lifecycle-api).
- S18: [WebKit Web Push on iOS/iPadOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).
- S19: [WebLLM source, capabilities and license](https://github.com/mlc-ai/web-llm).
- S20: [Transformers.js documentation](https://huggingface.co/docs/transformers.js/en/index).
- S21: [2Toad profanity filter](https://github.com/2Toad/Profanity).
- S22: [Qwen3Guard-Gen-0.6B model card](https://huggingface.co/Qwen/Qwen3Guard-Gen-0.6B).
- S23: [Ofcom age assurance requirements](https://www.ofcom.org.uk/online-safety/protecting-children/age-checks-to-protect-children-online).
- S24: [European Commission age-verification blueprint](https://digital-strategy.ec.europa.eu/en/factpages/blueprint-age-verification-solution-help-protect-minors-online).
- S25: [European Commission age-verification policy](https://digital-strategy.ec.europa.eu/en/policies/eu-age-verification).
- S26: [EDPB age-assurance principles announcement](https://www.edpb.europa.eu/news/edpb-adopts-statement-on-age-assurance-creates-a-task-force-on-ai-enforcement-and-gives_en).
