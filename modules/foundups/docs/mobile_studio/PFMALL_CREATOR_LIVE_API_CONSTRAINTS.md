# PFMall Creator Live: YouTube API Constraints

**Status:** Planning evidence; no executable admission.

**External documentation checked:** 2026-10-17.

**Project/channel checks:** UNVERIFIED.

**Owner:** `modules/foundups/pfmall`; proposed Foundups/Play creator studio.

The existing [README](../../pfmall/README.md), [INTERFACE](../../pfmall/INTERFACE.md),
and [ROADMAP](../../pfmall/ROADMAP.md) establish a presentation/read shell.
They do not establish a creator publishing backend or authenticated resident
RedDog adapter. This document proposes constraints for a later bounded slice.
Under WSP 97, documentation evidence does not confer execution authority.

## 1. Eligibility and service ceilings

Verified external rules follow.

| Constraint | Verified external rule | Proposed handling |
|---|---|---|
| Live eligibility | Channel verification, no live restriction in the preceding 90 days, and current age requirements apply. First enablement can take 24 hours. [C], [E] | Resolve eligibility before presenting a ready-to-publish state. |
| Mobile versus encoder | YouTube's mobile-app workflow requires 50 subscribers; the separate encoder instructions do not state that threshold. [M], [E] | Do not advertise a restriction bypass or infer eligibility from subscriber count alone. |
| Embedding | Live embedding requires advanced-feature access. [F] | Treat live and embed eligibility separately. If embedding is unavailable, offer a creator-approved YouTube watch link. |
| Concurrency | Maximum 10 active streams per channel and 3 per stream key. Both ceilings apply. [C] | Reserve capacity locally, then respect provider admission/errors; these are not three camera inputs to a mixer. |
| Channel daily limits | Stream creation has a separate 24-hour channel limit; advanced access can raise it. No universal number is published. [D], [F] | Surface the provider limit without inventing an allowance. |

## 2. Current quota model

Use the canonical calculator checked above, updated **2026-10-15**. These
defaults do not prove the actual project's allocation. [Q]

| Bucket or operation | Documented default/cost |
|---|---|
| General daily allocation | 10,000 units, shared across endpoints other than the separate search/upload buckets |
| `search.list` | Separate 100 calls/day; 1 unit/call |
| `videos.insert` | Separate 100 calls/day; 1 unit/call |
| `liveBroadcasts` insert/bind/list/update/transition/delete | 1 unit/call |
| `liveStreams` insert/list/update/delete | 1 unit/call |
| `liveChatMessages.list` / `streamList` | 5 units/call |
| `thumbnails.set` / `videos.update` | 50 units/call |

Daily quota resets at midnight **Pacific Time**. Invalid requests also cost
quota. Extensions require the applicable compliance review; no credential or
project sharding is proposed. [Q], [A]

**Illustrative budget:** creating a broadcast and new stream, binding,
transitioning directly to live, and completing costs
`1 + 1 + 1 + 1 + 1 = 5` write units. Reusing an existing input saves one;
a testing transition adds one. This excludes reads, retries, chat, thumbnails,
and unrelated application traffic.

Five-second chat polling, only if the returned interval permits it, costs
`720 calls/hour × 5 = 3,600 units/hour`. Prefer `streamList`; each new request
still incurs its documented cost. Obey `pollingIntervalMillis` when polling
and retain continuation tokens for reconnects. [CP], [CS]

## 3. Broadcast lifecycle and input reuse

A broadcast identifies the public event/video. A stream identifies an ingest
configuration; its secret stream key is a different value. One broadcast binds
one stream, while a reusable stream can serve multiple broadcasts. [BI], [S]

| Stage | Provider constraint | Proposed control |
|---|---|---|
| Create | Broadcast insertion requires title, scheduled start, and privacy; audience designation must be handled. [I] | Preserve creator choices and a local operation identifier. Reconcile ambiguous insertion results before retrying. |
| Select input | Reusable inputs support subsequent broadcasts. Non-reusable inputs can disappear after completion and are omitted from `mine=true` stream listings. [S] | Persist input IDs and retrieve non-reusable inputs by ID when needed. |
| Bind | Omitting `streamId` removes a binding; state can prevent binding. [BI] | Bind explicitly before publication. Never use omission as a retry default. |
| Send media | RTMPS uses `cdn.ingestionType=rtmp` and the returned `rtmpsIngestionAddress`. [S] | Keep ingestion secrets outside catalog projections and logs. |
| Start | The input must be active before testing/live transitions. Monitoring defaults to enabled, requiring testing before an explicit live transition. Disabling monitoring permits direct ready-to-live. [B], [T] | Choose the monitoring path before starting; include its extra transition in budgeting. |
| Reconnect | Auto-stop can complete a broadcast approximately one minute after input stops. [L] | Proposed mobile default: auto-stop disabled and explicit End. This provides no guaranteed outage grace period. |
| Finish | `complete` is finished; `revoked` represents administrative removal. [B] | Treat both as terminal for recovery. A later show needs a new broadcast; reuse its input only if still valid. |

Auto-start should be an explicit creator choice. For the initial controlled
flow, propose manual start to avoid publishing setup footage. Do not complete
an event merely because the phone loses connectivity. [L]

## 4. Observation and failure handling

Proposed observation separates local encoder output, stream activity/health,
and broadcast lifecycle. An active input alone does not establish a publicly
live event. Check `status.streamStatus`, `status.healthStatus`, and
`status.lifeCycleStatus` independently. [S], [B]

Transitions are asynchronous and can take up to about a minute; reconcile
observed state instead of treating the request response as finality. [L]
Classify `concurrentBroadcastsExceedLimit`,
`sharedIngestionBroadcastsExceedLimit`, permission failures, inactive inputs,
and invalid/redundant transitions. `userRequestsExceedRateLimit` is documented
without a fixed numerical request rate. Back off retryable failures; do not
loop on every HTTP 403 or delete an event as generic recovery. [I], [T]

## 5. Delegated authorization

YouTube Live requires creator OAuth; service-account authorization is
unsupported. Broadcast writes accept `youtube` or `youtube.force-ssl` scopes.
A future unattended controller therefore needs valid delegated authorization
for the actual channel, not a service account standing in for its owner. [O], [I]

YouTube Studio channel-permissions invitations do not grant invited delegates
YouTube API access. Managing Live Control Room does not establish API authority.
Require an API-supported channel OAuth authorization path, verified independently
of Studio roles. [DE]

An external OAuth application in Testing is limited to 100 test users, and
YouTube-scope test authorizations/refresh tokens expire after seven days.
Production publishing and required OAuth verification are separate checks. [OT]

Request only scopes currently needed. Clearly identify the channel,
visibility, and proposed writes, with prior creator consent. [P]
The future backend must enforce that scope; browser messages, manifests, and
Mall admission cannot manufacture publishing authority.

## 6. Retention and monetization constraints

| Area | Constraint and planning consequence |
|---|---|
| Recording | Streams under 12 hours can be archived; longer streams may not be captured at all. This is not a 12-hour transmission cap. Preserve creator-original recordings independently where required. [R] |
| API metadata | Generally refresh/delete stored API data within 30 days. Authorized analytics/statistics exceptions require continued authorization checks. [P] (III.E.4) |
| Revocation/deletion | In-app revocation requires immediate token revocation and authorized-data deletion within 7 calendar days. Google-settings revocation requires related deletion within 30 days. User deletion/account-deletion requests require deletion within 7 days. [P] (III.D.2; III.E.4) |
| Playback pricing | Do not charge for embedded YouTube playback or reward YouTube engagement. Ordinary application login is distinguished from playback-specific gating. [P] (III.F.3) |
| Commercial surfaces | Selling an API client is permitted subject to policy. Selling API access or ads within YouTube content/player requires written approval; surrounding page advertising requires independent value. [P] (III.G) |

Proposed Foundups fees should purchase independently defined studio/services
value. Live eligibility does not establish monetization eligibility. [F]
Separate original footage, provider metadata, and application records in the
future retention design; this document grants no storage exception.

## 7. Outstanding verification

| Check | Current result |
|---|---|
| Actual channel identity, live restrictions, daily capacity, embed access | UNVERIFIED |
| Actual Cloud quota allocation, usage, OAuth production/verification status | UNVERIFIED |
| Creator consent, secure token storage, deletion/revocation handling | UNVERIFIED |
| Device reconnect behavior, monitoring transitions, archive outcome | UNVERIFIED |
| Monetization permissions and independent-value pricing review | UNVERIFIED |
| Authenticated creator backend and runtime admission | NOT ESTABLISHED BY THIS DOCUMENT |

**Documentation conflicts:** older quota material can show 50-unit broadcast
writes; use the current canonical calculator. The general API overview still
contains a one-stream/one-broadcast description that conflicts with dedicated
binding/resource documentation. Prefer those specific references and actual
provider responses. [Q], [G], [BI], [S]

## Primary source register

All links checked 2026-10-17.

[Q]: https://developers.google.com/youtube/data/determine_quota_cost
[A]: https://developers.google.com/youtube/data/guides/quota_and_compliance_audits
[C]: https://support.google.com/youtube/answer/2474026?hl=en
[E]: https://support.google.com/youtube/answer/2907883?hl=en
[M]: https://support.google.com/youtube/answer/9228390?hl=en
[F]: https://support.google.com/youtube/answer/9890437?hl=en
[D]: https://support.google.com/youtube/answer/3006768?hl=en
[I]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveBroadcasts/insert
[BI]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveBroadcasts/bind
[S]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveStreams
[B]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveBroadcasts
[T]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveBroadcasts/transition
[L]: https://developers.google.com/youtube/data/live/life-of-a-broadcast
[CP]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveChatMessages/list
[CS]: https://developers.google.com/youtube/data/live/reference/rest/v3/liveChatMessages/streamList
[O]: https://developers.google.com/youtube/data/live/authentication
[OT]: https://support.google.com/cloud/answer/15549945?hl=en
[DE]: https://support.google.com/youtube/answer/9481328?hl=en
[R]: https://support.google.com/youtube/answer/6247592?hl=en
[P]: https://developers.google.com/youtube/terms/developer-policies
[G]: https://developers.google.com/youtube/data/live/getting-started
