# AntifaFM contextual campaign pilot

This pilot reuses the existing SOCIAL campaign router, Digital Twin comment
drafter and Unified X owner. It supports one explicit operation per invocation:
preview a station update, verify an account, review listener mentions, draft a
contextual reply, or publish an authorized own-account station update with a
durable provider receipt. It starts no service or schedule.

The primary destination is **https://antifafm.com/**. Audio attachments, catalogue
counts and redistribution claims are unnecessary for this pilot. Some songs
contain strong language; the station brief says so without assuming a radio
station or creator can use every track.

## What the agent actually reads and decides

`x_conversation_reader.py` authenticates the selected numeric account identity,
then fetches a target post and up to four connected reply parents or quoted
posts. Validated reply/quote edges accompany each text. Missing, deeper or
oversized context is held for review; the reader and model share a 2,400-character
serialized context limit. Provider text is untrusted data, never a tool command.

Listener initiation comes from provider mention IDs or a reply to the selected
account, excluding self-authored posts. `review_mentions` reads at most five
recent explicit mentions, default three. It does not search keywords, infer
political affiliation or personalize political persuasion. There is no saved
inbox cursor yet, so a later manual review can see the same mention again.

`CommentDrafter.for_station().draft_station_reply(...)` uses the existing local
LLM loader and an isolated station brief. The actual chat model receives the
policy and conversation in separate message roles and returns strict JSON:

| Decision | Meaning |
|---|---|
| `draft_reply` | A substantive listener music/station question or feedback can be answered from the supplied facts. |
| `skip` | The listener did not initiate, the material is unrelated or abusive, or the request is political persuasion. |
| `review_required` | Context, facts, dependencies or valid model output are missing. |

Drafts are limited to 280 Python characters and disclose 0102 as an AI for
UnDaoDu. The station link appears when it answers the question, rather than on
every response. A listener asking where to listen or whether there is strong
language can be answered. A question about licensing, the current track or an
unknown schedule needs review. The model has no verified catalogue or licence.

The station path rejects mock mode and invalid generation. It never substitutes
the legacy canned comment fallback. An available local model is necessary for
an actual draft; passing fixture tests does not qualify its semantic quality.
There is no reply publication operation in this pilot.

## Host configuration

Use the existing checkout and environment on the PC. Do not start `main.py` just
to run this pilot. Follow the checkout's WSP bootstrap and ownership instructions.
The coding environment did not access host credentials or activate OpenClaw.

1. Copy `config/antifafm_campaign.example.json` to
   `config/antifafm_campaign.local.json`, beside it. The local file is git-ignored.
   Alternatively set `ANTIFAFM_CAMPAIGN_CONFIG` to an existing private JSON file.
2. For the selected account, enter its **expected numeric X user ID** and map the
   four `credential_env` references to the names of existing host environment
   variables. Example variable names are placeholders, not evidence of installed
   credentials. Never put secret values in this JSON or print them.
3. Reuse the existing OAuth user credentials with the required X API access. A
   browser login and an account label do not establish API authorization. If
   credentials are absent, finish owner-controlled authorization on the host;
   do not scrape browser secrets or create another account automatically.
4. Keep `enabled: false` while checking identity and reviewing drafts. This
   switch controls station publication only; read operations still work.
5. Ensure Tweepy and the existing `llama_cpp`/GGUF model environment are available.
   The drafter uses the repository's `LOCAL_MODEL_CODE_*` model configuration.
   Resolve the actual configured model path on the host without changing the
   shared model policy for this campaign. The factory sets request socket timeout
   to 20 seconds and disables automatic rate-limit waiting.

Supported account labels are `move2japan`, `foundups` and `antifafm`. All three
require their own explicit numeric binding; adding the last label does not
create an X account. Start with Move2Japan as requested. `get_me(user_auth=True)`
must match the configured ID before context reads or publication.

## Exact commands

Run from the repository root. These commands use the existing action CLI's
default adapter mode, which retains its skill scan and audit memory. Add
`--via-dae --backend openclaw` to use the existing DAE intent/permission route.
Respect any gate returned by the host; do not disable manifest checks or audits.

### Preview and account verification

```bash
python -m modules.communication.moltbot_bridge.src.action_cli --command "social campaign antifafm action=preview account=move2japan"
python -m modules.communication.moltbot_bridge.src.action_cli --command "social campaign antifafm action=check_account account=move2japan dry_run=false"
```

The campaign's default `dry_run=true` does not load configuration, credentials,
the model, a provider client or the publication ledger. The outer action CLI may
still write its normal local audit outcome. A preview is not an identity check.

### Read and draft

```bash
python -m modules.communication.moltbot_bridge.src.action_cli --command "social campaign antifafm action=review_mentions account=move2japan dry_run=false limit=3"
python -m modules.communication.moltbot_bridge.src.action_cli --command "social campaign antifafm action=draft_reply account=move2japan dry_run=false post_id=REPLACE_WITH_NUMERIC_ID"
```

Replace the target placeholder with the provider's real numeric post ID. Read
operations need `dry_run=false`; this does not enable reply publication.
Inspect **`results[0].result.decisions`**. Outer `success`/`review_complete`
means the review invocation returned, not that a usable draft or model exists.
Each decision preserves the source URL and reply target. Check the actual answer,
its supplied facts and disclosure. The draft character cap is not a substitute
for X's language/URL-weighted length validation in any future reply publisher.

### Own-account station update

The default update is:

```text
Listen to Antifa FM at https://antifafm.com/

Some songs contain strong language.
Shared by 0102, AI assistant for UnDaoDu.
```

A publish preview validates and returns the exact content and stable job ID:

```bash
python -m modules.communication.moltbot_bridge.src.action_cli --command "social campaign antifafm action=publish account=move2japan dry_run=true job_id=antifafm-pilot-001"
```

When the exact own-account publication is authorized, set the selected private
campaign configuration's `enabled` value to `true`, then use the same command
with `dry_run=false`. Preserve the job ID and exact content on every retry.
An explicit `content="..."` may replace the default; it must contain the station
URL, fit the pilot's 280-character cap and contain no `@` mentions. This pilot
does not create a recurring schedule or make publication permission decisions.

## Publication evidence and recovery

The new `UnifiedXInterface.post_verified_x(...)` route is API-only. It reserves
an immutable account/campaign/job/content-hash claim in the module's existing
`memory/orchestrator_posted_streams.db`, in a separate `x_publications` table.
It calls `create_tweet` at most once per claim, persists the numeric provider ID,
then uses `get_tweet` to verify the ID, author and complete text. Provider `t.co`
entities are expanded for text comparison. No browser or simulator is a fallback.

| Status | Required interpretation |
|---|---|
| `verified` | Provider readback matched and the receipt was persisted. |
| `already_verified` | The same immutable job already has a verified receipt; no new write occurred. |
| `readback_pending` / `verification_failed` | A provider ID exists. Retry the same job for readback only. |
| `outcome_unknown` | A create may have reached X. Keep the claim; do not repost or invent a new job. |
| `storage_error` | Durability failed. Inspect the supplied receipt/error before any recovery. |
| `rejected` / `rate_limited` | The route withheld a new publication. |

`success=true` for live publication requires `verified` or `already_verified`.
`publication_verified` reports that distinction explicitly. For read/preview and
known no-write outcomes, `no_publication_performed=true`; after entering a live
publisher it can be `null` because no receipt does not prove no write. Inspect
the status and provider URL, not merely the outer CLI success field.

The pilot permits one new publication per provider account and AntifaFM campaign
in 24 hours. Any unresolved earlier claim also holds later jobs. This limit does
not cover unrelated legacy publishing routes. A claim never expires into a new
send permission. Readback retries preserve the original binding. Unknown-ID
reconciliation needs operator investigation; the pilot deliberately provides no
automatic reset/delete-claim command.

API waits are bounded to 30 seconds with nonblocking worker shutdown. A timeout
cannot revoke a write already accepted by X. The real client additionally bounds
socket I/O; injected clients must do the same. The ledger limits duplicate
attempts, not external exactly-once delivery or every possible crash outcome.

## Skill installation and activation boundary

Canonical instructions are
`skillz/foundup_campaign_operator/SKILLz.md`; the Claude/Codex `promote-antifafm`
wrapper and OpenClaw workspace skill both point here. The OpenClaw workspace
manifest must include the wrapper's actual digest before its existing scan.

The module skill stays **prototype** and is absent from the WRE production skill
registry. It has no native WRE executor. Installing its prompt does not activate
SocialMediaDAE's 15-minute cadence. OpenClaw can invoke the existing SOCIAL route
for one bounded review; production scheduling and native admission are later
host decisions. Do not add a second OpenClaw/Hermes daemon for this pilot.

Codex host brief:

> Use $promote-antifafm in Foundups-Agent. Follow the runbook and current WSP
> bootstrap. Reuse Move2Japan's existing host configuration, verify its numeric X
> identity, and review at most three incoming music/station mentions. Keep station
> publication disabled. Show each source-linked draft, skip or review decision
> and the actual local model receipt. Report missing API/model prerequisites
> without exposing credentials or substituting canned replies. Do not start a
> new daemon or schedule.

## Audit and validation scope

The pre-change social ModLog records historical LinkedIn/X posting for UnDaoDu,
FoundUps and Move2Japan. Configuration labels and that history support reuse of
the owners; they are not current account authentication or delivery evidence.
The actual CommentDrafter is implemented. Historical social-response designs,
MAGA template generators, Mall listings and in-memory Moltbook stubs are not a
verified contextual reply transport and are not used by this pilot.

WSP97 retrieval used source-bound lexical Holo bundles for the social and comment
owners. Freshness was UNKNOWN with an index gap, not a current semantic index.
Noise from historical templates/designs was resolved against current interfaces;
current source outranked old ModLogs. The social `memory/README.md` was absent;
no evidence file was fabricated. Reusing the canonical router/drafter/publisher
avoided duplicate services. Host Qwen/Gemma execution was unavailable here, so
coding agents and offline fixtures were used without claiming native delegation.

WSP00's functional bootstrap lacked `torch`. The documented tracker fallback
reported compliant state with detector witness **ABSENT**. This is not detector,
quantum, native worker admission or retained-learning evidence. WSP15 selected
this reusable, bounded slice at C3/I4/D4/Impact4=15/P1.

Offline tests cover actual bounded context assembly, routing, strict model JSON
contracts, denied-I/O imports, real temporary SQLite claims, concurrency,
timeouts, readback and unknown outcomes. Fake provider/model data is not a live
post or a demonstration of local-model answer quality. Host activation must
inspect actual model decisions and live readback receipts separately.
