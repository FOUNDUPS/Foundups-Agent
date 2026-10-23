# PFMall Mobile Studio Contract

**Status:** SPECIFIED_NOT_IMPLEMENTED. **Checked:** 2026-10-18.
**Product/capture owner:** external `FOUNDUPS/autopost`.
**Shared integration/planning owner:** `modules/foundups/pfmall`; this does not
move camera ownership into Mall. **Consumer:** the next admitted 0102 slice.
**Source baselines:** Foundups-Agent main
`1c80f15ae2eee0f78300f297fb3e386275bc0aab`; AutoPost main
`4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147`.

## 1. Pain, outcome and decision

Creators need to start a YouTube show from a phone, switch a few scenes, recover
from a connection drop and have the correct live show discoverable in Play.
Today those jobs span a mobile encoder, YouTube Studio, stream-key handling and
Mall catalog updates. Play already has discovery and playback; it does not yet
join creator authorization, mobile production and provider-confirmed live state.

The proposed outcome is: **one authorized creator opens AutoPost, selects Live
and the correct channel, previews a mobile scene, explicitly goes live, appears
in Play, survives a tested network interruption, explicitly ends, and starts a
later show using the same valid ingest configuration without duplicating the
broadcast.**

**Decision after the AutoPost audit:** extend AutoPost with a selectable Live
mode and a separate continuous media adapter. Its camera, review, account and
diagnostic shell already exist. The initial 2026-10-17 plan omitted this owner;
its standalone/native-first wording is superseded by this reuse decision.

The first media proof uses AutoPost's foreground browser camera/mic through an
authenticated WebRTC relay to YouTube RTMPS. An OBS contribution route is a
separate option. Select a native engine inside the AutoPost product if measured
device requirements justify it; a native wrapper alone adds no media capability.
The complete outcome still needs scoped durable creator control and a permitted
Mall projection. Keep media independent of Liquid/LLM responses and the Mall tab.

This is a planning contract and research PR. It authorizes no provider calls,
account linking, broadcast, deployment or autonomous work execution. The
[machine-readable outcome](mobile_studio_outcome.v1.json) is not an executable
work order, manifest, accepted allocation or runtime registration. Implementation
requires the existing [build-plan admission contract](../FOUNDUP_BUILD_PLAN_CONTRACT.md)
and an exact, separately admitted slice. No new FoundUp identity is created here.

## 2. Source-backed reuse map

These findings describe code at the baseline, not deployed or device-tested
behavior. Open PRs are not part of this baseline.

| Existing owner | Reuse | Gap or constraint |
|---|---|---|
| [AutoPost product and module registry](https://github.com/FOUNDUPS/autopost/blob/4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147/src/modules/MODULE_REGISTRY.md) | Camera/mic acquisition, capture shell, local original-media storage, provider-neutral perception and DAEmon | External owner; no second camera stack in this repository. Current recording is completed segments, not live transmission |
| [AutoPost YouTube connector](https://github.com/FOUNDUPS/autopost/blob/4b9e2fd8958f54e5b4c0c36e690d781ac1e8f147/src/modules/integrations/youtube/youtubeApiClient.ts) | Reviewed operator-owned upload, channel discovery, browser authorization and returned provider IDs | No broadcast/input lifecycle; short-lived browser grant is not a durable creator service |
| [p.fMALL shell](../../pfmall/README.md) | Manifest discovery, routes, catalog projection and advisory state overlays | Read surfaces do not authorize creator writes; development FastAPI is unauthenticated |
| [Member runtime](../../../../public/member/INTERFACE.md) | Video tiles, creator/category filtering, queue player and bounded presentation commands | Opening the player does not prove playback or a publicly live broadcast |
| [Broadcast manager](../../../platform_integration/antifafm_broadcaster/src/youtube_broadcast_manager.py) | Broadcast creation, input reuse, binding and transitions | Channel/token defaults and fallbacks are AntifaFM-specific; audit before extracting a general adapter |
| [Ingest resolver](../../../platform_integration/antifafm_broadcaster/src/youtube_ingest_resolver.py) | Fetch the selected broadcast's bound ingest configuration | Uses heuristic broadcast selection, warning-only key mismatch and RTMP fallback; replace these with exact session/channel/binding checks and required RTMPS |
| [FFmpeg streamer](../../../platform_integration/antifafm_broadcaster/src/ffmpeg_streamer.py) | Server/desktop production patterns | Not an Android/iOS capture and audio engine |
| [YouTube channel pull](../../../communication/youtube_channel_pull/README.md) and [Mall discovery](../../../ai_intelligence/pfmall_discovery/README.md) | Known-channel ingestion and reviewable discovery proposals | Neither proves creator ownership or permission to publish |
| [Member control dispatcher](../../../../public/member/js/pfmall-control-dispatcher.js) | Allowlisted UI presentation actions | No OAuth, resident identity, broadcast or worker authority |

The reviewed catalog is a creator-labelled presentation collection, not evidence
of an operating multi-creator publishing network. AutoPost supplies browser mobile
capture and recorded-file publishing; a general live-session service, continuous
live output and native scene/audio composition remain absent. Existing channel
automation is useful evidence, but its
hard-coded audience/channel choices and key logging must not become defaults in
the new adapter. Preserve creator-selected audience and privacy explicitly.

### AutoPost determination and source limits

Consume the external [Live-mode audit and publishing boundary](https://github.com/FOUNDUPS/autopost/blob/main/docs/architecture/YOUTUBE_PUBLISHING_BOUNDARIES.md#planned-live-mode--source-audit-2026-10-18)
and [Phase 4B roadmap](https://github.com/FOUNDUPS/autopost/blob/main/ROADMAP.md#phase-4b--autopost-live-mode-planned)
before changing its source. The baseline has specific continuity gaps: visibility
changes stop camera tracks, camera flips stop audio/video before reacquisition,
recording buffers completed Blobs, and local originals are saved after stop.
Its portrait preview does not prove portrait encoded output; DOM graphics are
not automatically part of the feed. These findings require a Live adapter,
compositor/audio policy and device tests, not just a new button.

AutoPost already requests `youtube.upload` and `youtube.force-ssl`; the latter
is accepted for broadcast creation. Actual granted scope, current channel and
live eligibility still need checks. An attended browser can perform the REST
lifecycle without a new backend requirement from YouTube. The shared backend
here is a product choice for durable machine-to-machine control, managed channel
custody, restart recovery and multi-creator isolation, using a supported delegated
[authorization code flow](https://developers.google.com/identity/oauth2/web/guides/use-code-model).
An attended proof retains
explicit token-expiry/reconnect limits and is not evidence of that full service.

AutoPost PR #12 (Lick/lens/OAuth), Foundups-Agent #1689 (continuous Lick) and #1886
(receipt accounting) were open at this audit. They are not merged Live capability
or prerequisites for a basic creator-controlled feed. Preserve their unique work.
The external repository has no declared license file at this baseline; do not
mistake private source access for a public open-source distribution license.

### Native and open-source candidates

OBS publishes desktop code for Windows/macOS/Linux; a mobile product needs mobile
capture, audio, graphics, permissions and lifecycle work, not only a smaller UI.
Source is already available, so reverse engineering OBS is unnecessary.
[OBS source and license](https://github.com/obsproject/obs-studio).

Evaluate [Moblin](https://github.com/eerimoq/moblin) as the iOS product spike;
[RootEncoder](https://github.com/pedroSG94/RootEncoder) is an Android media-engine
candidate, and [HaishinKit.swift](https://github.com/HaishinKit/HaishinKit.swift)
is an iOS engine alternative. They are different levels of reuse, not equivalent
finished products. Moblin declares MIT, RootEncoder Apache-2.0 and HaishinKit BSD-3;
pin an exact revision and inspect the complete dependency/asset license inventory
before adoption. OBS is GPL-licensed; importing it requires a separate licensing
decision. This contract selects no dependency or distribution license.

General reverse-engineering research can inform interoperability and testing.
It does not establish that another project's code/assets are reusable or that a
Photoshop/game reimplementation solves the phone's media pipeline. Prefer source
and documented interfaces; record provenance and rights for anything imported.

## 3. Proposed ownership and data flow

```mermaid
flowchart TD
    A[AutoPost Live mode] --> B[Selected media adapter]
    A --> C[Authenticated creator sessions]
    C --> D[YouTube Live API]
    B -->|Browser WebRTC| R[Authenticated relay]
    R -->|RTMPS media| E[YouTube ingest]
    B -->|Future native RTMPS| E
    D -->|Observed lifecycle| C
    C -->|Public projection| F[Play catalog and player]
    E --> G[YouTube playback]
    F --> G
```

| Plane | Required responsibility |
|---|---|
| AutoPost product | Explicit Live selection, channel/destination/privacy review, local preview, Go Live/End and DAEmon; preserve ordinary photo/record gestures and four primary Options tabs |
| AutoPost media adapter | Continuous capture, portrait/landscape output, mic/media mixing, encoding, bounded local recording, transport recovery and local stop; foreground browser proof first, native implementation if justified |
| Relay for the browser route | Authenticate a session-scoped publisher, negotiate ingress, convert codecs when required, forward to the exact authorized YouTube input, supervise output and expose measured health |
| Creator backend | Authenticate principal and actual YouTube channel; hold delegated tokens; serialize mutations; persist IDs, intent and observed state; enforce quota and revoke access |
| YouTube | Authoritative provider event, ingest health, visibility and playback availability |
| Play browser | Discover and display permitted metadata; embed where permitted, otherwise offer a watch link; issue untrusted intents only |
| Future 0102 adapter | Translate admitted creator intent through existing RedDog/OpenClaw/WRE boundaries; it cannot grant itself channel or publication authority |

The relay is required for the selected browser WebRTC-to-RTMPS proof; a future
native direct-RTMPS adapter can omit it. It is a separate service from AutoPost's
current static nginx deployment. [MediaMTX browser publishing](https://mediamtx.org/docs/publish/web-browsers)
and [re-encoding guidance](https://mediamtx.org/docs/features/remuxing-reencoding-compression)
are candidates, not deployed infrastructure. Verify codecs against the current
[YouTube encoder requirements](https://support.google.com/youtube/answer/2853702?hl=en);
H.264/AAC is the initial interoperability target,
with conversion for Opus or incompatible video as needed. Measure relay CPU,
egress, latency, NAT/TURN and recovery before release.

For OBS contribution, the relay supplies a compatible
[OBS media source](https://mediamtx.org/docs/read/obs-studio); desktop OBS then
produces the show. [OBS WebSocket](https://github.com/obsproject/obs-websocket)
controls scenes and start/stop but carries no phone camera feed. A transport
relay alone provides neither scene mixing nor guest audio mix-minus. Browser
widgets may render visuals in a composed scene;
their digital audio route, especially with headphones/external microphones,
requires device evidence. Playing alerts through a speaker into the mic is not
proof of a proper audio mix.

Preview remains local until the creator explicitly approves media export.
Media start is bound to the selected session/destination and provider input;
for the browser relay route, provider keys remain at the relay and browser
publisher grants are scoped and short lived. End stops local transmission even
when the controller is unreachable and invalidates stale reconnect work. Relay
forwarding/lease termination and provider completion are reported separately.
Liquid sampling is optional and cannot block capture/start/stop. Current signed
completed-file manifests do not prove a live subject or every frame of a stream.

## 4. Proposed machine contract

The following are logical adapter operations for the **integrated M2M service**,
**not implemented endpoints**. Its durable session/mutation envelope does not
apply unchanged to the separately admitted attended feasibility profile below.

| Operation | Required precondition | Durable result |
|---|---|---|
| `PrepareSession` | Verified principal/channel mapping; explicit title, schedule, privacy, audience, monitoring and start mode | Server-issued session ID/revision; creator consent reference; normalized request digest; planned channel |
| `CreateBroadcast` | Session scope, quota budget, reconciled prior attempt | Broadcast ID and observed lifecycle, or explicit uncertainty |
| `ResolveInput` | Correct channel; compatible ingest format; reusable-input policy | Input ID and credential reference; never a key in a public result |
| `BindInput` | Explicit broadcast and input IDs; ownership and state verified | Provider-confirmed binding |
| `StartLive` | Explicit creator intent; bound input active; chosen monitoring path satisfied | Start requested; live only after provider observation |
| `InspectSession` | Read authorization and budget | Separate encoder, ingest and broadcast observations with timestamps |
| `EndLive` | Authorized end intent; current state reconciled | Complete only when observed; preserve archive-pending separately |

Each mutation must carry `request_id`, `principal_id`, `youtube_channel_id`,
`intent_digest`, `consent_ref` and an expiry. `PrepareSession` uses these common
fields and returns a server-issued `session_id` and initial revision; subsequent
session mutations also require that ID and `expected_revision`. A repeated
prepare request returns the same accepted session when its authenticated scope
and digest match. The backend independently resolves identity and credentials;
those fields are claims until checked. A credential reference is not a bearer grant.
Reject a changed payload under the same request ID and concurrent controllers
with stale revisions. Persist mutation intent before the external request and
results afterwards. Do not imply that YouTube supplies an idempotency-key API.

An insertion can succeed while its response is lost. Reconcile durable IDs and
provider observations before retrying. If an ambiguous creation cannot be
identified safely, return `uncertain` for operator resolution; do not blindly
create again or delete a possibly valid show. Track any orphaned provider object
for explicit cleanup. Two independent encoders must not concurrently publish to
the same input in the initial product.

For MS2A/L1, a separately admitted attended proof can precede completed durable
MS1. It still verifies actual granted scope, the exact authorized channel,
broadcast/input, eligibility and bounded creator consent. Select and document
either a deliberately preconfigured exact relay/input or bounded authenticated
provisioning, including who holds the input key and issues the scoped publisher
grant. Browser OAuth does not itself establish relay custody or admission.
Bind observations and stale-work rejection to a local proof ID, media generation
and independently verified relay admission; those local IDs grant no authority.
Expiry/reload limits and operator reconciliation of ambiguous writes remain
explicit. This profile creates no durable server-session or Play-projection claim.

Observations must distinguish:

- `transport_state`: phone/relay connectivity and local encoding evidence.
- `ingest_state`: provider stream activity and health.
- `broadcast_state`: provider lifecycle, including transitional states.
- `playback_state`: embed capability and actual player result, if observed.
- `observed_at`, `source` and `revision`: freshness and evidence provenance.

The local session may report preparing, ingesting, starting, live, reconnecting,
ending, complete, blocked, failed or uncertain. These are local workflow states,
not replacements for YouTube enums. Terminal provider states cannot be revived.
Stale/unavailable evidence yields unknown; it never upgrades to live. Persist
secrets separately and redact them from receipts, telemetry and error strings.

## 5. Provider limits that shape the build

The [API constraints register](PFMALL_CREATOR_LIVE_API_CONSTRAINTS.md) owns dated
quota values, eligibility, OAuth, lifecycle, retention and playback-policy facts.
Revalidate it at implementation and release; actual project/channel status is
UNVERIFIED. In particular:

- A later show reuses a valid input, but gets a new broadcast/event identity.
- Live eligibility and live-embedding eligibility are separate gates.
- Choose monitoring/auto-start/auto-stop before publishing. The first controlled
  mobile flow proposes manual start and explicit end with auto-stop disabled;
  no outage duration is guaranteed by that choice.
- Reserve write quota for start/end/recovery. Multiplex chat observations and
  respect the provider's polling interval; many browser viewers must not each
  run an independent API polling loop.
- Mall membership and a catalog creator label do not establish YouTube OAuth
  authority. A Studio delegate may also lack API access.

Publish only creator-approved, public-safe fields: creator identity, broadcast
ID, title, watch URL, optional approved embed URL, lifecycle evidence, freshness
and archive state. A private/unlisted event is excluded from public discovery
unless an explicit policy appropriate to that visibility admits the projection.
No OAuth token, ingest secret, private channel/account detail or raw API payload
belongs in static catalog JSON, browser commands or Holo ingestion.

Keep Play's ordinary membership/account experience distinct from paid access to
YouTube playback. Any proposed paid benefit needs an independent deliverable and
policy review; YouTube membership status, payment settlement and creator payouts
are separate systems. No entitlement, payout or revenue-sharing ledger is built
or assumed here. Preserve YouTube attribution and player controls; place studio
graphics in the creator's composed output, not over embedded player controls.

## 6. Ordered build slices and measurable gates

These are proposed slices, not authorized worker assignments or delivery dates.
One implementation PR should take one bounded slice and update this contract,
the [owner roadmap](../../pfmall/ROADMAP.md), interfaces and ModLog before promotion.

| Slice | Intended delivery | Exit evidence | Current blocker |
|---|---|---|---|
| MS0: evidence and plan | AutoPost owner audit, current reuse map, API register and machine outcome | Linked, parseable, reviewed docs | Documentation only; original plan corrected after external source audit |
| MS1: account and API spike | One explicitly authorized test channel; scoped adapter and deterministic provider fakes | AC01–AC04; quota/consent receipts; controlled real-channel round trip when separately authorized | OAuth project/client/channel selection and actual capability checks |
| MS2: AutoPost media spike | MS2A: foreground browser WebRTC/relay proof; MS2B: measured media continuity and browser/native adapter decision | AC10–AC11 for first proof; AC05–AC06 for complete media slice | Phone/control-profile/relay selection, codecs, capture/audio lifecycle and thermal evidence |
| MS3: Play live projection | Provider-confirmed discovery, permitted embed or watch fallback | AC07–AC08; stale-state and visibility cases | Secure creator service and authoritative read projection |
| MS4: production reliability | Reconnect/runbook, quotas, OAuth release verification, data deletion and support | AC04, AC06, AC09; real-device soak and revoke evidence | Multi-creator isolation, provider approval, operational ownership |
| MS5: optional expansion | Second OS, richer scenes, OBS integration, multistream, guests and independent paid services | A separate contract and measured demand for each feature | No assumptions that a relay, API or membership solves these features |

MS2A is one phone, one camera/mic, AI disabled and one explicit destination for
10 minutes while foregrounded, with A/V observed in remote YouTube playback.
It may be separately admitted after MS0 and the attended-control/relay checks
above, before full MS1 completion. **Integrated MS2 promotion still requires
completed MS1, MS2A and MS2B; MS3 still depends on completed MS1 and MS2.** The
attended proof cannot satisfy durable-backend/restart gates by itself.
MS2B adds actual portrait output, composition, audio continuity,
bounded local recording and recovery. A native adapter is selected only if the
required device matrix or operational cost favors it. Record browser/native
control and media profiles explicitly; do not build duplicate auth stacks by default.

### Acceptance identifiers

| ID | Testable result required for implementation promotion |
|---|---|
| AC01 | Wrong creator/channel, expired consent and browser-supplied identity fail closed before any provider write; selected privacy/audience survive round trip |
| AC02 | A controlled event creates, binds, starts and ends on the selected channel; source observations distinguish requested versus completed transitions |
| AC03 | A second event has a different broadcast ID and can reuse the original valid input ID; no duplicate binding or event after duplicate commands |
| AC04 | Lost create response, process restart, stale controller and repeated end are reconciled; ambiguous creation stays uncertain without a new duplicate |
| AC05 | Proposed initial target: portrait 720p30, mic plus one graphic and local recording for 30 minutes; measure encode drops, A/V sync, heat, battery and recording integrity; set device-specific release thresholds before promotion |
| AC06 | Wi-Fi/cellular handover and controlled 10/30/90-second interruptions produce truthful status and bounded retries; separately test lock/background, calls, denied permissions and headphones/external-mic alert mixing; no support claim for an unpassed case |
| AC07 | The correct creator's show appears only from fresh permitted provider evidence; terminal/stale/private cases never appear as an asserted public live show |
| AC08 | Embed-denied and player-failure cases offer a working approved YouTube watch link; UI-open events are not accepted as playback proof |
| AC09 | Project/creator quota limits, 403 categories, token revoke and deletion requests are exercised; secrets never appear in catalog, logs or evidence artifacts |
| AC10 | AutoPost Live selection does not publish; explicit channel/privacy/audience review and Go Live authorize export; End stops local sending despite controller failure and stale reconnect work cannot restart it; ordinary photo/record gestures and four primary tabs remain intact |
| AC11 | A foreground 10-minute camera/mic feed is observed in remote YouTube playback through the selected browser-relay-YouTube route with exact channel/input binding and negotiated formats; preview or relay ingress alone never proves the route or asserts provider live; this proves only the initial route |

For AC05, the proposed target is a spike workload, not a validated hardware claim.
For AC06, report measured recovery time and final provider state for each trial;
do not promise that every network outage can preserve a broadcast. Record actual
device, OS, browser or native build, dependency revision, negotiated/encoded
formats, provider IDs and observation times
in access-controlled evidence; publish only redacted references to the repository.

## 7. Handoff, verification and closure

Consume in this order: current AutoPost README/ROADMAP/module registry/publishing
boundary, pfMALL README/INTERFACE/ROADMAP, this contract, the API register, then
`mobile_studio_outcome.v1.json`. The adjacent `doc_index.json`
provides hashes and attachment paths. It covers this bounded subcollection; it
does not claim a semantic Holo generation was rebuilt or a runtime was admitted.

The [WSP 97 receipt](wsp97_execution_receipt.json) records this documentation
execution, including the documented WSP 00 fallback and lexical Holo evidence.
Receipt validation establishes structural/repository evidence only. The next
implementation must reread current main, inspect active related PRs, revalidate
external facts and produce new exact-slice verification. Docs-only validation
must not be presented as successful streaming, device tests or deployed behavior.
