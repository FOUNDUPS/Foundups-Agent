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
