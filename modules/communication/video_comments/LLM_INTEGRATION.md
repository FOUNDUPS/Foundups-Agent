# YouTube language routing

## Shared route (2026-11-01)

Studio comments and ordinary/themed live chat use the existing semantic
`IntelligentReplyGenerator` → `AIGateway.call_youtube_task` boundary. The Gateway
owns model/provider dispatch for `assess`, `write`, and `review`. No YouTube
consumer constructs an xAI client, uses the generic social/Grok fallback chain,
or silently revives embedded Qwen inference after a rejected/unavailable route.
The retired `YT_ENABLE_GROK_REPLIES` switch has no effect.

The model assesses the complete original text and author/receiving-channel/video
context, then writes an answer, then separately evaluates the exact final reply.
Live chat reviews the complete final `@mention` string (at most 200 characters),
including when there is no theme. The reviewed text reaches the sender without
truncation or extra slogans. UI-TARS remains visual-only. Existing STOP switches,
identity binding, theme freshness, delivery evidence and unknown-attempt history
remain the publication owners. A rejected writer or final review halts the current
commenting session; a restart is not a durable global quality suspension.

## Local incumbent and dynamic orchestration

With no YouTube binding configuration, the Gateway resolves the existing local
`general` role. An explicit `LM_STUDIO_MODEL` must match that role. The existing
`LM_STUDIO_NATIVE_MODEL_KEY` selects its exact native inventory identity when
the server key differs from the display alias. It must pass the same language-role
guard; signed dynamic routes retain their exact bound model and ignore this
incumbent override. The actual native key is retained in the route receipt.
The existing
LM Studio backend verifies exact native residency/instance identity before and
after inference. It does not start a server, load/download a model, evict another
model, choose any arbitrary loaded model, or use a tiny triage/vision/coder model.
Both reasoning-off controls are passed through the shared backend.

Dynamic replacement consumes the existing signed production model selection and
runtime-binding owners. It re-verifies signatures, trusted time, task, surface,
provider and expiry on each stage; there is no cached authority across calls.
Only a single `principal` is supported, with task family `youtube_reply` and
runtime surface `youtube_comments` or `youtube_livechat`. Panels and bindings
for another task/channel surface cannot become an implicit writer.

The existing NVIDIA Nemotron owner is
`ai_gateway/src/model_topology_proposal_lm_studio.py`. It proposes evaluation-only
topologies. Its output feeds the existing held-out benchmark and signed promotion
path; it is not production model-selection or posting authority. This integration
does not weaken that boundary or silently load Nemotron during a reply.

## Configuration through the existing environment owner

These variables contain paths, never credentials or inline model replies:

| Variable | Meaning |
| --- | --- |
| `YT_MODEL_ROUTING_ROOT` | Absolute outside-repository artifact root |
| `YT_MODEL_RUNTIME_BINDING_RECEIPT_PATH` | Signed/verified runtime binding artifact |
| `YT_MODEL_SELECTION_RECEIPT_PATH` | Corresponding production selection |
| `YT_MODEL_CATALOG_SNAPSHOT_PATH` | Canonical catalog evidence |
| `YT_MODEL_BENCHMARK_EVIDENCE_RECEIPTS_PATH` | Held-out benchmark evidence |
| `YT_MODEL_PROMOTION_EVIDENCE_RECEIPTS_PATH` | Promotion evidence |
| `YT_MODEL_PRODUCTION_EVIDENCE_BUNDLE_PATH` | Authenticated evidence bundle |
| `YT_MODEL_RUNTIME_BINDING_POLICY_PATH` | Exact task/surface admission policy |
| `YT_MODEL_EVIDENCE_TRUSTED_KEYS_PATH` | Existing verifier's public trust configuration |

Stage overrides are `YT_MODEL_<COMMENTS|LIVECHAT>_<ASSESS|WRITE|REVIEW>_BINDING_PATH`
and the matching `_SELECTION_PATH`; otherwise the common paths apply. Any partial
or invalid effective configuration fails closed with no local/paid/xAI fallback.
Use the existing artifact suppliers and verifier bootstrap; hand-written JSON,
an ENV model name, or a private manifest command cannot mint production authority.

Authentication is read separately from `OPENROUTER_API_KEY` or `LM_API_TOKEN`.
No consumer loads `.env` itself, exposes credentials in command status, or puts
them in message payloads. The existing startup environment owner may load local
ignored files. ENV files are not encrypted storage.

## OpenRouter free models

The same verified route supports exact OpenRouter text-model IDs. It rejects
xAI/Grok and unpinned `openrouter/auto` or `openrouter/free` aliases. Request
policy caps prompt/completion prices at zero, denies provider data collection,
disables provider fallback and HTTP redirects, and checks the returned model ID.
No eligible endpoint/rate limit returns unavailable, never a paid fallback.
Kimi K3 is rejected before HTTP because its existing 4096-token minimum conflicts
with this consumer's 2048-token ceiling; the Gateway's K3 contract is preserved.

The existing Fusion approval-only guard scans the complete system/user/schema
payload and output. It blocks rather than silently changing text. Raw provider
bodies, exception messages, rejected drafts and credential values are not logged.
Nonempty rejected output retains `invalid_reply_text` provenance for the existing
quality-stop owner. Format/security guards do not establish factual accuracy.

The existing credential-free catalog discovery tool completed a public GET on
2026-11-01: 355 accepted candidate records, 97 rejected records, including 17
zero prompt/completion price entries. Examples were
`google/gemma-4-26b-a4b-it:free`, `google/gemma-4-31b-it:free`, and
`nvidia/nemotron-3.5-lightning:free`. Listing, pricing, schema support and availability
can change; these examples are not installed models or approved champions.
The bounded private discovery receipt is retained with the task evidence.

Use `scripts/openrouter_model_catalog_snapshot_once.py` for explicit catalog
refresh, then the existing catalog bridge, benchmark, signed promotion and runtime
binding suppliers. No production free model was admitted or called during this
repair; the current credential-rotation/startup guards remain in force.

Official contracts: [free models](https://openrouter.ai/collections/free-models),
[provider policies](https://github.com/OpenRouterTeam/docs/blob/main/guides/routing/provider-selection.mdx),
[privacy](https://github.com/OpenRouterTeam/docs/blob/main/guides/privacy/provider-logging.mdx).

## Legacy consumers and evidence limits

The historical `LLMCommentGenerator` now delegates to the same semantic owner,
requires captured original identity/context, and returns no template on failure.
Its inactive nested-dialogue caller cannot mutate the reviewed text afterward.
This does not qualify nested/API publishing; that path still lacks the Studio
submission owner's safeguards and is not enabled by this work.

Live-chat consciousness commands reuse the channel-bound reviewed generator.
After persona/channel changes their adapter is rebound; requester privileges do
not become the target author's role. Display names/string memories are not author
channel IDs. Missing or ambiguous captured identity yields no language reply.

Tests use explicit credential-free children, mocked providers and private temp
files with real network/credential-file access denied. Passing fixtures proves
routing and mechanics, not actual model semantic quality, YouTube selectors,
live delivery, daemon startup, or production promotion evidence.
