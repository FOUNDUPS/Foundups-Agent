# Provider and research baseline

Checked 2026-10-23; recheck before paid generation or publishing.

- Google Lyria: https://ai.google.dev/gemini-api/docs/music-generation — official Interactions API, Lyria Clip fixed 30 seconds, music output plus text. Trim deliberately to 15 seconds and verify actual lyric alignment.
- Veo: https://ai.google.dev/gemini-api/docs/veo — short generated shots; two eight-second clips can be edited into 15 seconds. Provider capabilities and model IDs can change.
- Suno: https://suno.com/terms — approved exports and plan/rights evidence matter. Official public generation API not verified in this research.
- YouTube search: https://developers.google.com/youtube/data/reference/rest/v3/search/list — strict SafeSearch, date/language/region parameters; quota configurable.
- Charts: https://developers.google.com/youtube/data/revision_history — mostPopular is not a comprehensive children's trending feed.
- Kids quality: https://support.google.com/youtube/answer/10774223 — educational coherence and age-appropriate quality apply to Shorts too.
- Audience: https://developers.google.com/youtube/data/reference/rest/v3/videos — selfDeclaredMadeForKids and containsSyntheticMedia are separate fields.

Research record: video URL/ID, channel, observation timestamp, published timestamp, region/language, view count if actually observed, source method, viewed/listened status, learning theme, rights status. Preserve missing counts as unknown. Only compare matching videos over positive elapsed intervals. A statistical ranking is a signal for review, not an educational-quality verdict.

A research cycle should propose at most three original episode briefs with a learning objective, action, 15-second script, original music brief and evidence links. Do not publish or spend generation credits as a consequence of a trending score.

## Repository findings and design decision

Base reviewed: cfa632775f2b13034320d45559cdc77d46e3ead6.
Existing video_editor.py provides FFmpeg assembly but uses a shared concat file and a fixed format. Existing clip_exporter/shorts_pipeline serves extracted index clips, not original educational episode composition. Existing youtube_uploader.py owns channel verification and audience declarations. Keep this feature within youtube_shorts rather than duplicating auth, publishing or a standalone FoundUp media stack.

The governed Holo owner lexical query returned workspace-head evidence with UNKNOWN freshness and index_gap_detected=true. README and INTERFACE were present; ROADMAP/tests README/memory README were absent. Retrieval initially favored generic orchestrators over editing; direct path verification reranked video_editor, uploader, registry and tests. No semantic index freshness or reindex is claimed.

WSP00 detector script was attempted but unavailable because torch is absent. The current-main tracker subsequently reported is_zen_compliant=true; no detector execution success is claimed. Source implementation and local tests are separate from admitted WRE execution.

## Scope and remaining activation

This slice implements a local editor, deterministic rendering and injectable research/music adapters. No paid model call, YouTube upload, semantic video/audio trend review, live channel mapping, automatic speech alignment or installed WRE worker has been validated. Supplied caption cues produce automatic burn-in and SRT, not automatic transcription. Preserve these distinctions in user-facing reports.

Historical setup: ChatGPT Kids Episode Trend Scout was scheduled from 2026-10-24 and disabled at 012's request that day. No recurring scout should be inferred from this record; it never activated WRE, paid providers or published videos.

## First content baseline — observed 2026-10-23 JST

Method: read the following official English-language song/resource pages. This is **page-text/metadata-only research**: no video playback, audio listening, view counts, retention measurements, or repeated snapshots were collected. Publication dates were not independently established; Sesame's playlist page labels the collection 2023. These are source-grounded evergreen candidates, **not verified current trends**. Source availability today does not establish recent release or popularity growth. The original briefs below are editorial proposals for ages 3–5, not measured learning outcomes.

| Candidate | Observed source evidence | Original 15-second brief and music direction |
|---|---|---|
| Count three actions | [Super Simple: Count & Move](https://supersimple.com/song/count-and-move/) describes combining counting to 20 with movement. | **Three Little Claps:** original round bird mascot; 0–3s invites three claps; 3–9s claps once for each numeral 1, 2, 3; 9–12s pauses for the child to repeat; 12–15s shows three dots and celebrates. Objective: associate three counted beats with three actions. Original plucked-string motif and soft percussion, with distinct beats and room to respond. |
| Explore paint colors | [Super Simple: Mixing Colors](https://supersimple.com/song/mixing-colors/) identifies primary-to-secondary color mixing as an art activity. | **Our Green Leaf:** original snail painter; 0–4s shows blue and yellow paint dabs; 4–8s stirs them into green; 8–12s paints one green leaf; 12–15s invites the child to point to green. Objective: recognize the demonstrated paint mixture and resulting color. Specify paint/pigment, not colored light. Original bell-and-brush rhythm, with short clearly spoken or sung color names. |
| Name and express a feeling | [Sesame Workshop: Happy Dance](https://sesameworkshop.org/resources/happy-dance/) connects preschool music/movement with expression of emotions and body awareness. | **My Happy Wiggle:** original cloud mascot; 0–4s names its happy feeling; 4–9s models a small seated shoulder wiggle; 9–12s invites a wiggle or a wave; 12–15s asks the child to name their own feeling, with no required happy answer. Objective: name one feeling and choose an expressive movement. Original warm keyboard tune, gentle pulse, and a quiet ending. |

Production boundary: create new melodies, lyrics, characters, voice performances, and artwork. These links establish educational themes only; they supply no asset-reuse license. Before promoting a candidate as growing in popularity, collect comparable timestamped observations through the bounded snapshot adapter and label the sampling scope. Before claiming visual or musical analysis, actually inspect the permitted media and record what was watched/listened to.

## Story-production audit update (2026-10-23)

Retain FFmpeg for stitching, captions, audio mixing and inspection. Legacy VideoEditor crossfade hardcodes offset4.5 and does not compose arbitrary-sequence audio. The kids renderer adds internal fade-through-black without shifting15-second duration; full-story assembly retains audio and checks total frames. MoviePy adds a layer over FFmpeg without filling a current gap. Remotion is a later animation-heavy interface option, with Node/browser and licensing considerations. Shotstack adds a hosted render/key/credit boundary unnecessary for the local proof.

Official references: https://ffmpeg.org/legal.html ; https://ffmpeg.org/ffmpeg-filters.html ; https://zulko.github.io/moviepy/getting_started/install.html ; https://www.remotion.dev/docs/license/pricing ; https://shotstack.io/docs/guide/agents/ .

Provider correction superseding earlier cached guidance: https://ai.google.dev/gemini-api/docs/veo announces Gemini Veo3.1 preview IDs shut down2026-10-22. Verify supported endpoint/model/account before activation. Enterprise GA docs list4/6/8-second clips: https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate . Three5-second edited shots may use longer generations, with distinct generation/edit lengths.

Existing GeminiVideoAnalyzer serves public URL indexing/transcript summaries and initializes environment-backed clients, so is not a local unpublished artifact reviewer. The new injected adapter uses configured model and actual MP4 bytes. Semantic model judgments are evidence, not authenticated WRE acceptance. This execution host has no configured Gemini key/Vertex project or google-genai SDK; no live provider call is claimed.

Discovery: add only the canonical generated kids entry to the existing static member catalog. Full export would change unrelated entries/remove HoloIndex, so broader reconciliation is deferred. Existing EDUIT manifest lacks shell-required name/version: a separate discovery gap. Existing video-catalog tests have four HoloIndex baseline failures reproduced against HEAD.
