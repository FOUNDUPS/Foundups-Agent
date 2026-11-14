# Private operator video policies

`operator_command_queue.py` owns intake, claims, acknowledgements and active state.
`operator_video_policy_owner.py` is its private implementation helper, receiving
the same queue instance and using that instance's IO and lock methods.
`video_policy.py` only validates/resolves bounded data; it performs no IO or
provider/model/browser execution. Existing manifest path overrides are honored:
`YT_012_MANIFEST_FILE`, `YT_012_MANIFEST_ACK_FILE`, `YT_012_MANIFEST_STATE_FILE`.
Defaults remain checkout-rooted `memory/012_manifest*.json`.

## Commands

Use `enqueue_operator_command`; producers only append immutable commands with a
unique ID. Never edit acknowledgements or state. Both new actions are private:

- `set_video_policy`: flat payload with nonempty `channel_ids` (up to20 native
  `UC` channel IDs), optional nonempty `video_ids` (up to50 native11-character IDs),
  and at least one policy field. At most500 atomic channel/video scopes.
- `clear_video_policy`: exactly `policy_id`, or exact `channel_ids` with optional
  `video_ids`. Clearing a channel-wide scope does not clear a video-specific
  scope. It never clears comment/livechat context.

Policy fields:

| Field | Accepted value |
| --- | --- |
| `title_mode`, `description_mode` | `preserve`, `auto`, `replace` |
| `title_text`, `description_text` | Required only with corresponding `replace`; up to100/5000 characters; exactly one scoped video ID |
| `scheduling_enabled`, `shorts_enabled` | Actual booleans |
| `max_per_cycle` | Integer1..100 |
| `interval_minutes` | Integer1..10080 |
| `topics` | One to20 nonempty strings, up to100 characters each |
| `context` | Nonempty private grounding, up to2000 characters |
| `sources` | One to10 HTTPS URLs, up to2048 characters, no userinfo |
| `ttl_seconds` | Integer60..86400; default3600 |
| `expires_at_unix` | Optional finite positive numeric absolute deadline |

Boolean numbers, malformed/empty identities, unknown fields, model control tokens
and unsafe control characters are rejected. Replacement text is exact operator
input researched outside this runtime; context/sources are private grounding and
must not be appended to published text or interpreted as executable instructions.

Expiry is `min(first_seen + ttl_seconds, expires_at_unix)` when a deadline is
provided. The producer should attach the enqueue-time deadline so offline queued
work cannot start a fresh hour days later. Legacy commands without a deadline
retain first-observation TTL. `set_context` and `announce` honor the same deadline.

## Frozen stream scheduling requests

`schedule_stream_shorts` accepts `ttl_seconds` and `expires_at_unix` with
the same bounds. Without an explicit recorded source, the existing watcher freezes the confirmed running LiveChatCore
channel, video, exact stream title, chat and memory session at acceptance. No
speculative DAE video or later stream supplies missing fields. The title rule is
operator authorization to select every matching UNLISTED Short on that channel;
it is not independent evidence of a native parent-child relationship. A later
stream ending or changing does not retarget the frozen request.

For an ended stream, the same action accepts the paired fields
`recorded_source={channel_id, parent_video_id, stream_title}` and
`first_test_only=true`. All three source fields are required and native IDs are
validated; alternate keys or a missing/false test flag are rejected. This is an
explicit operator target, not proof that the parent is accessible or has the
claimed title. The browser owner must freshly verify both before discovery.
The immutable record adds `source_kind=recorded` and `first_test_only=true`, with
empty chat/session IDs rather than an invented live session. Legacy live records
retain their exact shape and digest. Both forms share the same channel/parent
reservation, so another command or mode cannot retry an uncertain source.

`await queue.refresh_stream_schedule_request(command_id, recorded_only=False)` validates the existing
inbox, ledger and state under the current manifest lock, and consumes only that
exact scheduling action using the existing claim/finish owner. It never polls or
dispatches unrelated announcements, policies or context commands. It returns a
copied unexpired pending request, or `None` for missing, other-action or terminal
work; corrupt/conflicting state and unknown intake raise. No acknowledged command
is dispatched again. Browser work must begin after this method releases the lock.
The native recorded-only consumer passes `recorded_only=True`: legacy live and
non-first-test commands are neither claimed nor returned, including already
accepted live work. General daemon callers retain live intake by default.

In recorded first-test mode the complete matching batch is frozen, but only its
first ID may be submitted, with metadata preserved. Remaining IDs are withheld,
not a new pending batch. The queue permits at most that first submitted ID in its
result, preserves the full selection through restart and keeps the request
terminal unknown after an uncertain attempt. A later continuation requires a
separately qualified existing-owner transition after exact saved-schedule proof;
replay, a new command or a successful click cannot authorize it. This queue layer
does not implement that readback or continuation.
The parent video itself is excluded from every selected batch, for both live and
recorded sources, before claim and whenever persisted selections are validated.
Recorded-only inspection reports `first_test_only`, `withheld_count` (all selected
IDs after the first) and `submission_recorded_count`. These are admission/attempt
counts, not verified schedules; `delivery_verified` remains false and private
source title/channel/video fields are not exposed by inspection.

`operator_stream_schedule_owner.py` uses the existing queue state, acknowledgements,
receipts and lock. There is no separate inbox, worker or publisher. The dispatch
only persists a pending request. The existing browser Phase3 obtains pending
requests and performs exact parent/channel access verification and complete title
discovery outside the manifest lock. A verified candidate atomically freezes the
selected native IDs before any scheduling write. Another browser may verify the
same target before that claim, but cannot claim it twice. Incomplete discovery or
unverified access leaves pending work until expiry; complete empty discovery
terminates as `no_matching_shorts`. No branch widens to unmatched backlog.

The dedicated launcher branch skips ordinary rotation, extra-tab cleanup, later
audits and origin restoration. It passes the already-verified driver and frozen
request to the existing scheduler, retaining STOP, metadata/audience and unknown
Save controls. Browser ownership remains held until the request thread settles,
including timeouts and repeated cancellation. A verification handoff blocks an
unclaimed request when it can still claim it; it never transfers an already-owned
request or automatically retries uncertain work.

After any claim or verification handoff, that browser loop yields for operator
review before later social/comment phases. Its supervisor retains the explicit
hold result instead of treating it as a worker crash and restarting it. The
other browser and main/livechat owner remain separate. Direct launcher attachments
use the existing connection-specific CDP/verification guard. Legacy live
`run_shorts_scheduler(mode='schedule')` refuses before attachment because it lacks
the qualified calendar owner; enhancement and preview retain their existing paths.

Queue instance methods are `get_pending_stream_schedule_requests()`,
`claim_stream_schedule_request(request, video_ids)` and
`finish_stream_schedule_request(command_id, reason=..., submitted_ids=...,
no_submission=False)`. Consumers must use the current immutable queue snapshot.
Inspection separates accepted intake from `execution_status` (`pending`,
`blocked`, `unknown`), selection count and expiry. No scheduler count or Submit
click establishes delivery; these requests never report verified completion.
Source identity deduplication survives new command IDs and restart. An unknown
claim remains terminal; no queue record or STOP control is cleared automatically.

`get_unresolved_scheduling_claims(channel_id)` (queue instance and module export)
returns copied matching unknown Save claims containing a scheduling fingerprint.
It validates the current state under the existing lock without dispatching inbox
work. Corrupt/unreadable state raises; legacy claims without a slot must be
reconciled by the calendar owner, not discarded or treated as free capacity.

This slice has offline fixture qualification only. Live scheduling, persisted
readback and operator-visible completion remain separate acceptance gates.

## Writer API

Module exports and `OperatorCommandQueue` instance methods:

```python
get_video_policy(channel_id, video_id=None, *, surface="metadata")
record_video_policy_observation(policy_ids, *, surface, channel_id,
                                video_id, outcome, detail)
claim_video_policy_upload(channel_id, artifact_sha256, *, command_ids, fingerprint)
claim_video_policy_save(channel_id, video_id, *, command_ids,
                        metadata_fingerprint, scheduling_fingerprint=None, draft_sha256)
verify_video_policy_save(channel_id, video_id, *, draft_sha256, readback_sha256,
                         metadata_fingerprint, scheduling_fingerprint=None)
inspect_command(command_id)  # module export also accepts explicit queue paths
```

Every writer must call the synchronous getter immediately before its existing
effect guard. It consumes only new private video-policy commands under the same
queue lock, independent of the async watcher's interval. It never dispatches a
queued announcement, status or context command. The async watcher handles the
same private actions through the same claim/dispatch/receipt implementation.

The getter returns `available`, `blocked`, `reason`, `matched_command_ids`,
`fingerprint`, `expires_at_unix` and `field_expiries`, plus sparse policy fields.
Metadata includes title/description; scheduling includes enabled/max-per-cycle;
Shorts includes enabled/topics/interval. Private context/sources are available
for each surface. Missing fields leave the existing policy unchanged. A valid
receiving identity with no match is available with no policy fields; malformed
identity, busy locks, corruption, missing accepted state, digest mismatch or an
unknown/deferred private reservation is unavailable and blocked. Writers must
never treat unavailable as no policy.

Newest matching command wins separately for each field. Replacing a field at
the same atomic channel/video scope removes that older field permanently;
expiry/clear cannot resurrect it. Other scopes remain independent: an expired
video-specific override may reveal an existing channel-wide setting. Mode/text
are one replacement group. Expiry changes future behavior and never rolls back
already published metadata or videos.

Before a Shorts upload, use the channel-level (`video_id=None`) Shorts snapshot
and durable artifact claim. The queue refreshes and checks IDs/fingerprint, then
persists an unknown reservation before returning `claimed=True`. Repeating an
artifact/channel claim always blocks, including after restart, failure or an
uncertain API result. Claims have a hard capacity and are never silently evicted.
The Shorts snapshot also exposes `last_upload_attempt_unix`, derived from the
latest same-channel upload claim, including unknown attempts. This summary is
excluded from the policy fingerprint. Upload reservation checks the current
`interval_minutes` atomically against it, so a restart or new artifact cannot
reset the spacing. A paused Shorts policy cannot reserve an upload.

Metadata/schedule saves use the same queue's effect claims, keyed by receiving
channel and video, independently of draft hash. A different draft, policy or date
cannot bypass an uncertain previous Save. Metadata-only saves can settle through
`verify_video_policy_save` after independent same-target persisted readback whose
canonical title/description digest equals the original draft digest. It binds
the immutable claim's original fingerprints; expiry/clear does not undo an
already saved change and does not prohibit reconciling that past effect. The
verification API consumes no queued commands and performs no public effects.
An identical verified draft is not resubmitted; a different draft can be claimed
only after the previous save is verified. Scheduled-save claims remain unknown
in this layer: metadata-only proof cannot prove slot/date/timezone/visibility.
Passing a scheduling fingerprint therefore forbids settlement until that whole
intent has a qualified readback owner.

## Evidence and recovery

Observations are bounded private records with outcomes `observed`, `applied`,
`unknown`, `blocked` or `failed`. IDs must refer to accepted commands covering the
same receiving channel/video and surface. `applied` additionally requires
`detail.persisted_readback=True`, a `policy_fingerprint` matching the current
snapshot (or original same-artifact Shorts claim), and `readback_sha256` for the
caller's exact persisted readback evidence. These fields bind the claim; the
writer remains responsible for actually obtaining and comparing platform
readback. Clicking Save, a successful submit, upload URL or API acceptance alone
must be recorded as `unknown`, never `applied`. An upload observation includes
`artifact_sha256` to associate it with its durable claim.
Generic observations never settle save claims. Only the dedicated bound save
verifier can mark a metadata-only save applied, including when no policy IDs
were active. Its caller must hash the complete attempted write and independent
persisted readback; a click result or in-memory draft is not readback.

The queue retains the latest200 observations and at most500 combined effect claims.
Status/inspect reads are private. `inspect_command` never activates/refreshes and
reports queued, received, active, absolute expiry/expired, known inactive reason
(expired, superseded or cleared) and bounded outcome identities without raw
context or sources. An unknown reservation can be received/persisted while
inactive and unusable. Full private status stays in the queue ledger; heartbeat
results omit private context/policies/observations. Legacy state keys and context
are preserved by read-modify-write updates.

Unknown reservations are terminal and block subsequent private-policy use; do
not clear/retry them automatically. Preserve files and inspect the actual outcome
through the existing owner before explicit recovery. Offline tests prove these
file/claim contracts with fake effects; they do not prove live YouTube behavior.
