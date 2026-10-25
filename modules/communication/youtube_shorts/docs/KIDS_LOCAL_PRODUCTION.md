# First Little Shrew episode and autonomous production boundary

Observed 2026-10-25 JST against base `c8eb983629454c6bef6e88d33826112ea19dc620`.

## Produced locally

The first existing Little Shrew episode now has a deterministic 2D authoring
command. It consumes the shared SVG rig and first segment of `build_pilot`, creates
three five-second clips, synthesizes original instrumental music/foley, then calls
the existing `kids_episode.render_episode` encoder. It is actual moving video,
not a storyboard slideshow or a diffusion-model benchmark. The fixed set keeps
all six family members visible. Little Shrew slides/tilts into the root pocket;
the parents notice gently bouncing pebbles. No new character artwork is invented.

```bash
python -m pip install -r modules/communication/youtube_shorts/requirements-local-preview.txt
python modules/communication/youtube_shorts/src/little_shrew_preview.py --output-dir /absolute/new-output --preset final
```

System Cairo, FFmpeg/libx264/libass and DejaVu Sans are required. Optional Python
dependencies stay separate from cloud generation dependencies. `draft` exports
854x480; `final` exports 1920x1080 from 960x540 authored frames. The latter is
upscaled, not native 1080p generation. Both export exactly 450 frames at 30 fps.
See official [CairoSVG API](https://cairosvg.org/documentation/) and
[FFmpeg image sequence format](https://ffmpeg.org/ffmpeg-formats.html#image2-1).

Output includes three clips, original-score.wav, episode.json, final MP4/SRT and
provenance.json with source/asset hashes, canonical project/episode identity,
creation time and explicit limits. An existing output directory is refused.
Partial failed local renders are preserved; choose a new directory for another
authoring attempt. This command is not a new checkpoint owner or paid-job retry
mechanism. It implements only beats b01-b03 and must not stand in for arbitrary
stories or the remaining six beats.

Source references are rechecked before and after rendering. Caption times follow
the authored foley windows. There is no speech, copied song, recording or paid
provider call. `status=rendered_unreviewed` remains until actual independent
audio/visual review; technical tests do not promote it.

## Verification receipt

140 focused tests passed: new local authoring (3), existing Kids renderer,
OpenRouter boundary and Kids story/preset suites. Real integration checks three
150-frame clips, a 450-frame final video, original audio coverage, provenance
hashes and refusal to overwrite. Frame-difference checks cover actual movement
and shot joins rather than merely counting declared frames.

Independent review sampled actual final frames at 1.5, 6.5, 8.5, 10.3, 10.5,
12.5 and 14.9 seconds plus joins: six consistent rigs, continuous movement,
legible sound captions and no visible harm. The inspected final MP4 is H264/AAC,
15.000 seconds and 450 frames; SHA-256
`ba76032630e7def91e71dfd2ff21e32ab63eb766aa3f61168191826b53ea186b`.
Decoded audio has finite samples without clipping. **Actual listening was not
available**: sound resemblance, musical quality and full audiovisual acceptance
remain unverified. This is a preview, not a publishing or whole-story approval.

WSP 97 execution plane: local media authoring/source development. WRE is not
applicable to this direct local render; no production admission was fabricated.
Governed Holo lexical fallback returned workspace-head evidence with UNKNOWN
semantic freshness/index gap. Relevant preset/docs ranked first; tests and
renderer were read directly because query hits omitted them. Optional module
memory docs and Shorts tests README were absent. WSP00 V2 failed for absent
torch; canonical tracker fallback reported compliant, without detector success.

## Existing autonomy owners and missing bindings

The target interaction is: story -> capability discovery -> concrete proposal
when additional authority is needed -> admitted execution -> independent review
-> retained outcome. Approval should bind what will happen, not require 012 to
find providers or manually manage each shot. The following are source findings,
not claims of an installed service:

| Responsibility | Existing owner | What still needs qualification |
|---|---|---|
| RedDog intake | `moltbot_bridge/src/openclaw_execution_routes.py`, Kids `work_order_adapter.py` | Authenticated local commander, production executor and host binding. Kids remains prototype/no executor. |
| Shot/audio/render/review sequence | Kids `story_pipeline.run_story` | Actual callback binding and independent review. It already bounds attempts, hashes assets and re-reviews on resume. |
| Delayed work | `idle_automation/src/schedule_claim_state.py` | Existing durable claims/leases and retry backoff must be composed with provider job IDs/status/next-poll time; Kids currently has no such binding. |
| Hermes execution | `wre_core/src/hermes_job_executor.py`, `foundup_job_consumer.py` | Media action not qualified; repository-build actions must not be repurposed to bypass admission. Queue draining alone is not a daemon. |
| Credentials | `secrets_mcp` OpCli/Systemd credential resolvers | Operator-provisioned credentials and service-specific onboarding. Secret resolution does not create accounts or authorize spending. |
| Bounded model spend | `ai_gateway/src/model_autoresearch_configured_gateway_runner.py` | Existing reservation/budget pattern is autoresearch-scoped; no generic Kids spending binding is established. |
| Retained improvement | `wre_core/src/pattern_memory.py`, `openclaw_skill_evolution.py`, `improvement_job_contract.py` | Independent evaluation, authorized promotion/rollback, then a later successful reuse. Candidate nomination is not self-promotion authority. |

**Funds truth boundary:** `modules/economy/src/lobster_client.py` returns mock
wallet balances and synthetic transaction signatures with status `confirmed`.
Its nominal daily USDC limit checks a single request, not accumulated spend.
Do not call it a funded payment service or use it for real Kids purchases.
No wallet was invoked and no financial account or subscription was opened.

## Next admitted production slice

1. Qualify the simplest generation capability on the actual host. Local rig
   animation needs no account. General open-model video still requires the
   Wan/ComfyUI host described in OPEN_VIDEO_AUDIT.md; this host has no configured
   GPU worker or OpenRouter/Gemini credentials. That does not describe 012's PC.
2. Reuse the existing secrets/approval owner for a provider-specific proposal:
   service/account, allowed actions/model, currency, maximum total spend,
   expiry, output destination and cancellation scope. Request only missing
   authority. Account challenges requiring human identity remain a handoff.
3. Bind provider intent/job ID/result hashes under the existing execution owner.
   Persist `next_poll_at` and release the worker between polls. Resume polls the
   same job; an uncertain submit must reconcile before another paid request.
   Existing `started` effect refusal must not be weakened into blind retry.
4. Bind independent actual-media review and bounded repair. Save failure,
   correction, usage/cost and accepted artifact evidence through existing
   outcome memory. Changes to skills/code require tests and independent
   promotion; a worker cannot grant itself authority or enlarge its budget.
5. Qualify restart/recovery and later reuse before claiming autonomous RSI.
   Publishing stays with the pinned YouTube uploader and PF Mall media owner.

The separate ChatGPT trend scout was disabled at 012's request on 2026-10-24.
Do not recreate it to compensate for absent runtime job polling. No WRE worker,
timer, provider, account, paid generation or upload was activated in this slice.

## Us_Story_Time publishing destination — 2026-10-26

012 designated **Us_Story_Time** as the headless Story Time channel under the
FoundUps YouTube account. Canonical publisher key: `us_story_time`; educational
FoundUp identity remains `kids_episodes`, in the EDUIT context.

**OBSERVED:** channel name and intended use are operator-provided. 012 confirmed reuse of the FoundUps OAuth binding (set 10), like antifafm. The immutable
YouTube channel ID has not been independently observed. Operator-supplied channel URL:
https://www.youtube.com/@Us_Story_Time (canonical handle `@Us_Story_Time`).
A shared Google account does not prove that an existing token selects this channel.

Configure the production host (never commit credentials):

- `YT_UPLOAD_CHANNEL_ID_US_STORY_TIME`: exact channel ID verified in Studio and
  against the authenticated `channels.list(mine=True)` result; never the display name.
- `YT_UPLOAD_CREDENTIAL_SET_US_STORY_TIME`: optional positive integer override; defaults to the existing
  FoundUps set 10, as requested by 012, following the antifafm pattern. Reuse the
  existing hardened `youtube_auth` owner and verify its observed channel. No new
  credentials are required by this registration.

After rights, actual audio/video and independent episode review:

```python
from modules.communication.youtube_shorts.src.youtube_uploader import YouTubeShortsUploader

publisher = YouTubeShortsUploader("us_story_time")
result = publisher.publish_story_episode(
    "reviewed-episode.mp4", "Little Shrew — Episode 1", "Original Story Time preview.",
    contains_synthetic_media=False,  # Explicit reviewed disclosure decision, not a default.
)
```

The Story Time helper requires this channel role, sets made-for-kids true, uploads
unlisted and does not notify subscribers. Synthetic-media disclosure is a separate
explicit boolean, chosen for the actual content. It returns the existing publish
receipt. Generic publishing APIs retain their existing behavior; callers must use
this helper for the preschool review workflow. This is not a generic adult-story
publishing helper.

**CODED / OFFLINE-TESTED:** channel policy, FoundUps OAuth reuse and optional override, channel-ID
mismatch refusal, preschool review helper. **BLOCKED / UNVERIFIED:** live account
binding, upload and headless worker activation. No upload occurs from configuration.
Use the Kids story pipeline and existing headless assembler for media, then this
publisher after review; do not introduce another uploader, credential system or
scheduler. A queue consumer/WRE binding remains separate unfinished work.

WSP 97 retrieval: governed lexical query on main `a490cadb5` found existing publisher
and Kids owners; semantic freshness UNKNOWN, index gap true. Direct source/test
reads filled the omitted test inventory; no duplicate owner added. WSP 00 V2 could
not load torch; canonical tracker fallback passed, not detector execution. This
change does not access credentials or activate runtime authority.
