# YouTube Shorts TestModLog

## 2026-08-25 — AutoPost / Foundups Mall publisher boundary

| Contract | Evidence |
|---|---|
| Explicit channel role selects the hardened credential set | `test_uses_hardened_pinned_auth_factory` |
| Configured authorized-channel mismatch fails before upload | `test_rejects_authorized_channel_mismatch` |
| Foundups Mall cannot publish without an exact channel-ID pin | `test_foundups_mall_requires_explicit_channel_pin` |
| Foundups publishing is unlisted, resumable, notification-free and playlist-aware | `test_publishes_unlisted_and_attaches_playlist` |
| Existing Shorts caller still receives its URL/public behavior | `test_upload_short_keeps_backward_compatible_url` |
| Non-video payload is rejected | `test_rejects_non_video_file` |
| Explicitly pinned dead OAuth sets do not silently rotate channels | `youtube_auth/tests/test_oauth_no_silent_fallback.py` |

Focused repository gate: 9 passed. All services/files are fakes or temporary fixtures. No credentials were read, refreshed, logged or uploaded; no live YouTube write is claimed.

## 2026-10-23 — OpenRouter storyboard boundary

Added offline tests for reference-byte requests, output/provenance, denied admission, changed references, invalid IDs/directories, malformed responses, redacted transport errors, replay refusal, review failure, reviewed-frame handoff and post-review mutation. Included the suite in Kids Episodes CI. Fixtures are local images and fake transport/review/video callbacks; tests do not establish live quality or account access.

Validation: 266 selected tests passed, including the existing renderer/editor/research, all Kids story contracts, OpenClaw route, registry loader/schema and CI security gate. The regenerated global test registry adds only this new test module.

## 2026-10-25 — Local Little Shrew animation

140 focused tests passed, including 3 new real authoring cases for six-character motion/joins, deterministic bounded audio and overwrite refusal, plus a real three-shot render with asset hashes, timed SRT and 450-frame output. Existing renderer, OpenRouter and Kids suites included. Independent final-frame inspection and technical audio decoding passed; no perceptual audio listening or publication approval claimed.

## 2026-10-26 — Us_Story_Time publisher policy

35 publisher/CI-security cases passed offline. Tests cover FoundUps set 10 reuse, optional explicit set override, invalid override refusal, missing environment pins/mismatched live identities, Story Time-only routing, unlisted made-for-kids metadata and explicit synthetic disclosure. Existing publisher regressions included. Fakes verify API arguments, not live OAuth or uploads. Added this existing suite to Kids CI and loaded only the publisher owner to avoid unrelated generation SDK imports.

## 2026-10-26 — Little Shrew editorial revision 2

012 requested removing the oversized sixth shrew. The rightmost of three equal-sized children now wakes after an early short tremor, wiggles and reaches the root by 5.5 seconds; parents and siblings stay asleep. Audio/captions retimed. Three five-second clips still total 15 seconds. Provenance labels this an editorial override of the original nine-beat source. Existing real render/audio tests passed; motion regression updated to inspect the smaller hero region and verifies five characters, equal child scales and sleeping family. No perceptual audio review or upload claimed for this revision.
