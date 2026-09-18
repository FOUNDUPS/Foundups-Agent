# Red Dog public website runtime

The repository-wide [OpenRouter consumer inventory](../../../../extensions/reddog/docs/OPENROUTER_CREDENTIAL_CONSUMERS.md) records environment ownership and restart/deployment requirements. Browser surfaces never receive provider credentials.

Status: implemented and locally tested; native Site version 28 saved, not deployed.
Production activation and provider replies remain unverified.
Review date: 2026-09-09. Owned branch: `feat/reddog-public-openrouter`.

## Behavior and ownership

The eSingularity Worker serves one public Q&A service to `https://esingularity.ai`
and `https://foundups.com`. Both website controls use the same browser transport
and D1 accounting. The existing Foundups sign-in gates remain in charge of their
own pages. Chat admission is explicitly public and does not reuse member tokens.

Red Dog answers project questions from a reviewed public knowledge packet under
0102's operating boundaries. It can explain YUMORI.me, the proposed reuse of
Sukatto Land Kuzuryu, FoundUps and the committee signup. It cannot perform work,
claim official approval, or expose private resident memory. No tool calling is
available. `CHAT / FAST / NONE` is a scope declaration, not proof of cognition.

The interface supports Japanese, English and Portuguese, consent, source links,
explicit conversation ending and unavailable/error states. Transcript and bearer
token remain in browser memory. Each model request answers one question; prior
chat messages are not stored or sent. End/reload discards the local transcript.
A source list identifies retrieved context, not proof every model sentence is correct.

## Request contract

POST `/api/reddog/public/{surface}/{operation}`, where surface is `esingularity`
or `foundups`, with exact matching Origin and JSON content type. Cross-origin
preflight permits only POST and Authorization/Content-Type. No wildcard origins.

| Operation | Body | Result |
| --- | --- | --- |
| encounter | `consent:true`, `consent_version:"reddog.public-guest.v1"`, `actor_claim:"human"/"agent"/"unspecified"` | memory-only bearer token, nonce, revision and expiry |
| turn | `nonce`, integer `revision`, `message` plus Bearer token | plain answer, source metadata, next nonce/revision |
| status | `{}` plus Bearer token | current nonce, revision, busy state and expiry; no answer replay |
| withdraw | `{}` plus Bearer token | closes the session; a late answer is suppressed |

Unknown fields and duplicate JSON keys are rejected. A lost turn is never
silently retried; the client checks status and waits for a new explicit question.
GET `/api/reddog/health` reports configuration presence and knowledge revision.
`configured:true` does not verify tables, ingress attribution, model access or a
successful provider request. Missing settings fail closed with a public 503 code.

Public limits mirror `reddog_public_policy.py`: 10 turns/session, 600 seconds
absolute/120 seconds idle, 3 sessions and 20 turns per subject/day, 200 sessions
and 1,000 turns globally/day, 4 active provider transports, 2,000 input characters,
256 output tokens, 4,000 reply characters, 15-second provider deadline, 12 KiB
request body/2-second body deadline. Output/source overhead is separate.

## Server configuration and activation

| Setting | Required value |
| --- | --- |
| `OPENROUTER_API_KEY` | server-only funded key scoped to this service |
| `OPENROUTER_MODEL` | an explicitly selected OpenRouter model ID supporting the configured provider policy |
| `REDDOG_SUBJECT_KEY` | independent random secret, at least 32 characters; preserve across deploys |
| `REDDOG_INGRESS_VERIFIED` | `cloudflare-connecting-ip-v1`, only after ingress canaries pass |
| `REDDOG_ENABLED` | `true` only for the verified activation |
| `DB` | existing Sites D1 binding |

Use the existing Site `appgprj_6a917b21b1a4819181a61738ed5274a5`. Runtime secrets
belong in Site environment settings, never Git, client code or logs. No default
model is guessed. The fixed OpenRouter chat endpoint requests non-streamed,
non-tool output, `require_parameters:true`, `data_collection:"deny"`, and
`allow_fallbacks:false`. A model/provider incompatibility produces unavailable.
No OpenRouter credential or Firebase publishing connection was found in this
session; Plugin Management returned no Firebase/OpenRouter integration.

The generated Drizzle migration adds three namespaced public-accounting tables;
it does not alter `community_interest`. Package `drizzle/` with the Worker so
Sites can apply migrations. Do not deploy a frontend-only archive. Before enabling:

1. Apply/verify the migration on the target D1 database and exercise atomic
   batch rollback, shared budgets, nonce races and durable busy reservations.
2. Prove the deployed edge replaces a caller-supplied `CF-Connecting-IP`, retains
   the real peer through Sites routing, and does not collapse all users into one
   service IP. The application intentionally does not trust X-Forwarded-For.
3. Configure the selected provider and independent subject key. Verify a bounded
   successful reply, a provider failure, wrong origin, replay and withdrawal.
4. Deploy the exact reviewed Site version, then publish `public/` to the existing
   Firebase hosting site `foundupscom`. Verify both real website paths reach the
   same service and offer the committee link. Native browser QA was not requested
   or performed during this implementation; it is distinct from the Node tests.

At the current checkpoint no settings were enabled, migration applied to production,
provider call made, or existing live website replaced. A saved build is staging evidence.

## Accounting and recovery

D1 stores only token hashes, HMAC peer subjects, timestamps, nonces, counters and
reservation IDs. It is not a second AgentDB or Mosh Pit store. Hashing is
pseudonymization; shared IPs share guest quotas. Token checks bind origin, surface
and subject. All quota spending and nonce advancement share one atomic batch;
CHECK failures roll back the entire admission. A global monotonic clock rejects
clock rollback. Concurrent global limits span both websites and Worker instances.

The four-call limit bounds active local transports. Abort/timeout does not prove
remote generation has stopped; daily quota is never refunded. A transient admission read failure before provider start releases its exact
reservation while retaining daily charges and the consumed nonce. A crash or failed
cleanup retains the durable busy slot. Operator recovery must first establish
that the owning request is no longer live, then clear that exact reservation and
its matching in-flight count atomically. Do not reset all counters or clear them
on restart. No automatic orphan recovery endpoint is exposed. Expired nonbusy
session rows and old daily budgets are pruned during new encounters.

## Knowledge and refresh

`content/reddog-public-sources.json` snapshots the publicly readable 01 story,
03 economic draft and project master. `lib/reddog-knowledge.ts` adds a reviewed
public account of the mayor-proposal draft, profile, committee purpose and
September 6–9 activity. Private 02/04 documents and the private Mosh Pit log are
not embedded. Public readability does not verify a draft's assertions.

The canonical signup is the existing [YUMORI.me committee form](https://docs.google.com/forms/d/e/1FAIpQLScSKFyzCym8NCarvNIa5cT9c2Pe8C-cY2AbC4zLgsDOKspYKA/viewform).
The September 25, 2026 vote is project-reported, not independently confirmed by
this integration. The prompt distinguishes preparation budget from total
estimated demolition cost, scenario spending from profit, and proposals from
approved commitments. It includes an after-September-25 uncertainty rule.

Mosh Pit mode is **curated public snapshot as of 2026-09-09**, not live recall.
The separate authenticated `/api/mosh-pit` reader stays gated. Updating knowledge
requires a fresh source read and disclosure review, updating source timestamps,
public summaries and `KNOWLEDGE_REVISION`, rerunning focused tests, and building
and publishing a new exact version. Never connect a private Drive credential to
the anonymous responder. A future live public projection needs its own approved
source and freshness contract.

## Local evidence and review

- `node --test tests/reddog-public.test.mjs tests/mosh-pit*.test.mjs`: 18 checks
  passed (real SQLite transactions using a D1-shaped adapter; not production D1).
- `node public/member/tests/reddog-public-client.mjs` from repo root: passes
  consent, loss recovery, nonce progression, explicit restart and withdrawal.
- `python -m pytest modules/foundups/esingularity/tests public/member/tests/test_red_dog_concierge.py -q`:
  41 passed; two unrelated missing pytest-asyncio configuration warnings.
- `npx tsc --noEmit`: passes. Production build passes (all five Vinext environments).
- No live model accuracy, hosted ingress, visual layout or Firebase canary is claimed.

Implementation references: frontend `lib/reddog-{policy,store,http,knowledge,openrouter}.ts`,
`components/RedDogChat.tsx`, and shared `public/js/reddog-public-client.js`.
The focused [WSP delivery audit](../../../../extensions/reddog/docs/REDDOG_WEBSITE_DELIVERY_AUDIT_20260909.md)
records WSP 00 fallback, retrieval limitations, protocol changes and release gates.

Provider references: [OpenRouter routing](https://openrouter.ai/docs/guides/routing/provider-selection)
and [D1 atomic batches](https://developers.cloudflare.com/d1/worker-api/d1-database/).
