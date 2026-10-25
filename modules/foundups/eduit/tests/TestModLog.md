# EDUIT TestModLog

## 2026-10-26 JST — Story Time PWA and deployment

- `node --test modules/foundups/eduit/tests/*.test.mjs modules/communication/youtube_shorts/tests/kids_review.test.mjs`: **21 passed**.
- `python -B -m unittest discover -s modules/foundups/eduit/tests -p test_build_site.py`: **6 passed**.
- `git diff --check`: passed; existing Windows LF/CRLF conversion notices only.
- Full existing renderer build via Ubuntu-24.04 Cairo/FFmpeg: 15.000s, 1920×1080,
  H.264 + AAC; source provenance retains rendered_unreviewed status.
- Provider preview revision `a73aaf94b71cd2b1`: 24 HTTP URLs 200, video range
  bytes 0–1023 returns 206/1024 bytes, immutable media and no-store worker headers.
- Chrome: video ended at 15s with game still ready; explicit Play and two taps
  reached success; practice and expand/back work; phone-size width no overflow.
  Manifest and installability diagnostics empty; actual install prompt visible.
  Offline reload served game and input advanced; networking/viewport restored.
- Independent audit: all 14 worker shell and 20 revision assets exist, no
  unresolved placeholders or material source/security/ownership blockers.
- Existing Kids Episodes CI now includes all Story Time/PWA/review JavaScript
  checks and the Python packaging tests; renderer/editor/registry checks retained.
- PR #2221 at `68af22d28` exposed the canonical test-registry freshness gate:
  the new tracked `test_build_site.py` was absent from its generated projection.
  Ran the existing `generate_test_registry.py --write` and `--check`: **1,773
  registered / 273 quarantined; current**. The only added entry is EDUIT's
  packaging test; no existing entry, quarantine, capability or execution policy
  changed. Hosted CI rerun remains pending the follow-up commit.
- Merged main `4f37c8505` after the shared root ModLog conflicted; retained both
  lane entries and main's GitHub integration/manifest/security changes unchanged.
  Registry remains current at **1,773 / 273**; impacted checks **21 JS + 6 build
  tests passed**, and `git diff --check` passed. Fresh hosted CI remains pending.
- Live provider URL redirects to /storytime/ and reports the same revision.
  Custom-domain DNS save awaits GoDaddy identity verification; HTTPS not verified.

An initial review-controller test failed because its import-strip regex assumed
LF. Accepting CRLF fixed this test harness portability issue; focused rerun passed.
Staging first exposed inherited target/config-directory and outside-project build
paths; corrected module binding/public path then staged successfully.

No physical touch device or actual OS install was exercised; rendered audio
was technically inspected but listening was not verified. Waiting-worker update
is covered by behavioral harness; first deployment had no prior live revision.
See [deployment receipt](../docs/DEPLOYMENT_RECEIPT_20261026.json) for evidence.
