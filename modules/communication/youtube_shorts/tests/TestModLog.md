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
