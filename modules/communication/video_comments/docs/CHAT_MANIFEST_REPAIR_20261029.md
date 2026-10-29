# Private YouTube themes and inspected replies — Windows handoff

012 directive, 2026-10-29: finish PR2254, integrate verified source and prepare
Windows for an observed test. GitHub changes do not automatically update an
existing PC checkout or a running Python process.

## Follow-up private livechat fallback — 2026-10-29

The follow-up source starts at merged-main
`887c09dd2d72162dce4747235bc2e1d0041cbf44` in the same isolated repair worktree,
branch `fix/youtube-livechat-local-theme-route-20261029`. Preserve the older dirty
PC checkout. PR2254's publication/main checks belong to its own receipt; those
checks do not accept this follow-up's source or installed runtime.

A separate private runtime probe observed HTTP403 from the existing Grok client.
That cloud account/service condition remains outside this source repair. Retain
the existing successful reviewed Grok path and, after unavailable/empty/failed/
rejected themed output, reuse `get_reply_generator().generate_reply_with_source`
plus `inspect_reply` through the approved general-language LM Studio HTTP route.
No new provider, store, scheduler or paid retry is introduced. Actual local-model
QA, source publication and live delivery are separate gates; fixture tests do not
substitute for any of them.

The explicit `reply_surface='livechat'` requires semantic context, reads only the
livechat queue theme and excludes embedded Qwen/cloud/template re-entry. Stored
comments keep their default reader, history/cooldown and provider behavior.
Author ID, receiving channel and stream title are supplied to generation/review;
the existing livechat generator cache is bound to channel and stream identity.
Review sees the exact final `@mention` within 200 characters. The reviewed payload
deep-copies the full native theme, retaining its scope/expiry/command metadata
for the existing ChatSender post-delay guard. Theme expiry, replacement or native
metadata drift blocks sending; no truncation follows approval.
Both main generation and the direct local helper reject malformed native theme
normalization before provider calls. The helper retains one qualified normalized
theme for comparison with the generation receipt; `None` cannot serve as proof.

Both existing eligible MessageProcessor call sites use
`wait_for(to_thread(...), 10.0)` with a cancellation event. Existing engagement
and cooldown checks precede them. Livechat rejects busy shared generator/reviewer
locks immediately; comments keep serialized blocking access. Timeout discards
late results and prevents later provider stages/local fallback, including after
news/history/voice preparation. It cannot stop an already-active provider call;
the ten-second await is not a process-kill or browser rollback guarantee. The
caller retains themed mode across the await, so clearing context cannot enable
an unreviewed string/template fallback.

Current direct retrieval independently confirmed the owned branch and source.
The source-bound Holo query returned `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`,
`ok=false`, `freshness=UNKNOWN`, `index_gap_detected=true`; no reindex occurred.
Authority HEAD was `68562f2c8ca4749e360e76758183319d54988879`; workspace HEAD was
the merged-main base above. Retrieval evaluation: lexical WSP ordering was noisy,
the module bundle found existing contracts, optional memory docs and the comments
requirements file were absent, and direct exact-source reads removed staleness/
duplication risk. Reuse the existing general-language model owner; deterministic
API/cancellation checks and independent review govern this bounded repair rather
than introducing another autonomous mutation or inference path.

Local Windows offline verification: semantic **88** + unchanged submission history
**16** = **104 passed**, 12 subtests passed, zero failures/errors/skips. Original
context **53**, adjacent queue/lifecycle/control-plane **116** and separate stdlib
inspection **15** pass independently. The combined157 run is context53 +
the same104 and must not be added to them. The existing task TEMP evidence root
retains `followup-repair-results.xml` for the 104-case CI inventory. Tests execute
real source definitions with fixture providers/synthetic browser data and cover
busy locks, comment serialization, heartbeat, late payload discard, no late local
fallback and theme clearing; no public message, paid API or DAE startup occurred.
Independent read-only review initially reproduced the 151-case selection, then
found invalid native source/handle fields could normalize to `None` and still
produce a reviewed reply. Six new controls reproduced this bypass in both entry
points before repair and now pass without provider work. The earlier acceptance
was withdrawn for this narrow fix. Renewed independent review accepts the fix and
separately passes 157 cases with 12 subtests; that source acceptance awaits final
commit identity. Real local-model QA and exact-head/main checks belong to their
corresponding acceptance steps.

## Source and retrieval boundary

Original repair head: `5aa828e12905659d26784a77df564ea114eb68f9`, based on
`8b345ec206212b1e27868bdc4cacd06474b636a6`. Windows refetch confirmed the open
draft/head. The shared PC checkout `O:/Foundups-Agent` was on an unrelated feature
branch at August commit `0c81418fe94a7786cfd55f01e138ddc5d510583d`, with existing
modifications. Preserve it. Repair checkout:
`C:/Users/user/.codex/worktrees/youtube-comment-repair-20261029/Foundups-Agent`.

WSP00 awakening/gate passed. Current AGENTS, WSP10/97, NAVIGATION and module
README/INTERFACE/ROADMAP/ModLog/test contracts were retrieved before changes.
Owner Holo query failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`: authority
`5e938253...`, workspace `0c81418...`, `ok=false`, `freshness=UNKNOWN`,
`index_gap_detected=true`. No reindex occurred; existing governed postmerge
maintenance owns recovery.

Retrieval evaluation: exact-commit direct inspection removed checkout staleness;
module-first ordering reduced noise and duplicate reads. Historical production
claims were not runtime proof. Video-comments memory README/requirements were
missing; Tier-0 README/INTERFACE and explicit offline selectors existed. Existing
owners were extended. Manual review was necessary for cross-module API/browser
correctness; Qwen/Gemma roles cannot replace deterministic independent checks.

## Owners and spoken commands

| Purpose | Existing owner |
|---|---|
| Inbox | `memory/012_manifest.json`, override `YT_012_MANIFEST_FILE` |
| Receipt | `memory/012_manifest_acknowledgements.json`, override `YT_012_MANIFEST_ACK_FILE` |
| Theme | `memory/012_manifest_state.json`, override `YT_012_MANIFEST_STATE_FILE` |
| Queue/producer/lifecycle | `livechat/src/operator_command_queue.py`, `auto_moderator_dae.py` |
| Comment consumer | `video_comments/src/commenting_control_plane.py` |
| Assessment/draft/review | `reply_context.py`, `intelligent_reply_generator.py` |
| Browser identity/submission | existing `skillz/tars_like_heart_reply/src/` owners |
| Durable history/evidence | `commenter_history_store.py`, override `YT_COMMENT_HISTORY_DB` |

“Live stream …” selects livechat; “Commenting …” selects video comments; “Push …”
selects both. “Update the chat manifest with …” is private and honors stated
scope, otherwise both. Only explicit announcement intent selects `announce`.
`set_context` does not publicly announce receipt or repeat operator wording.

Resolve paths from actual launch configuration. `enqueue_operator_command`
appends one unique immutable ID under the existing ledger lock, preserving work.
Producers never write acknowledgements/state. TTL, supersession, STOP/automation,
selected-surface and dry-run gates remain. Private activation needs no sender.
Shared clear does not clear legacy local promo state.

## Implemented source behavior

- Posting assesses full original meaning, question, stance and uncertainty before
  selecting a reply. Names alone establish no stance; negation, quotation and
  sarcasm receive conservative evaluation. Content-neutral rate/history/repetition
  checks remain before provider work.
- The general-role owner selects the writer; GUI/audio/embedding/coder models,
  including explicit LM Studio overrides, are rejected. UI-TARS remains visual.
  Model-name checks are not signed runtime admission.
- Generation retains supplied history, verified memory and assessment. Final
  review sees that snapshot plus original author/channel/video/comment/theme.
  Malformed review, gibberish, control tokens, unrelated answers and unsupported
  facts reject. Per-call scores are judgments, not calibrated probabilities.
- Themes enter generation and must still be current at submission. No wording is
  appended afterward. Livechat preserves reviewed text/theme into ChatSender,
  which rechecks after delays/conversion and retains existing cooldown gates.
- Studio binds real comment/video/author/receiving-channel identity on the exact
  Studio origin. The final script checks identity and exact editor text and
  clicks once. Settled existing reply IDs form the baseline; verification needs
  a new exact-text reply ID from the actual creator. Ambiguity/disappearance is
  uncertain. Nested submission remains disabled pending equivalent qualification.
- Existing SQLite history reserves before browser work, independently of draft
  text. Unknown reservations survive restart and block retry; proven no-submit
  failures alone release them. Verified delivery/history commit together.
  Approved review/context, creator reply IDs and unique screenshot/hash/inspection
  evidence stay private through the same owner.

## Verification and Windows preparation

The original 53 context plus 116 adjacent queue/lifecycle/reader cases pass on
Windows CPython3.12. The 15-case stdlib selector passes. New semantic and durable
history selectors use actual source definitions, temporary real SQLite restart/
concurrency and exact production JavaScript in synthetic DOMs. Positive controls
exercise useful answers, creator readback and actual sender payloads. Providers/
DOMs are fixtures; these are not live inference or delivery receipts.

Additional private QA exercised the actual installed Qwen3.5-4B through the
existing assessment/writer/reviewer route with synthetic comments and supplied
facts. A useful documentary-website answer passed review. Unrelated promotion
and unsupported claims were rejected. These examples are not calibrated quality
or public delivery evidence. The short local requests disable reasoning output;
the legacy system prompt's unrelated Japan/topic redirects are excluded from the
assessed route. The final neutral prompt preserves the comment's subject and
distinguishes missing context from a claim that a date/event does not exist.
Actual QA also showed unstructured reviewers misspelling/omitting required keys.
The local reviewer now uses the supported strict JSON-schema response shape;
semantic decisions and thresholds are unchanged. A sole complete JSON code fence
is accepted for evaluation envelopes, with prose/trailing output still rejected.
Theme relevance is assessed before writing, and irrelevant themes are withheld
from generation rather than relying on a promotional suffix or writer hint.
Private local Gemma4-E2B QA uses the same route; model scores never replace
independent inspection of the original comment, supplied facts and final reply.

Independent fresh-context review read all original files, reproduced wrong-row
and coder-model acceptance, and reviewed their repairs. Canonical registry,
backend manifest, digest pins and security findings use existing generators/gates.
Exact final SHA/checks belong to PR2254 and the runtime receipt; historical passing
checks do not accept a new head.

Initial discovery found no YouTube DAE, browser debug endpoint or model server.
No manifest overrides existed. Old September worktree state was inactive.
The existing general Qwen3.5-4B GGUF is installed on E:.
Private runtime preparation is at `O:/Foundups-Agent-runtime/youtube/`, with
absolute queue/receipt/state/history paths. The old history was backed up through
SQLite read-only backup. No public action was taken. Model listing is not model
loading or admission; source, role and live account/channel must be checked.

For the observed test: pin the release checkout, general model service/role,
account/channel, browser connection, private paths and gates. Poll a harmless
status command, then inspect private activation and relevant generation. Verify
the exact published creator reply under its original comment; Submit is not
proof. Do not create public test comments merely to prove polling. Report
separately: queued, received, activated, draft reviewed, delivery observed.
Repository completion requires applicable checks on resulting main under
WSP97 v1.10. Offline source validation claims no live model judgment, native RSI
or measured transferable learning.
