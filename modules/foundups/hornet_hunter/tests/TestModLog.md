# TestModLog

## 2026-10-28 — Registry integration repair

- Reproduced the stale registry at PR head f9aa7bf.
- Canonical regeneration adds only this module test file and increments total.
- Both public build unittest cases pass in isolated temporary directories.
- Exact-head hosted CI remains the acceptance gate after publication.

## 2026-10-28 — Public source import

- Two unittest cases pass: sanitized media contracts and isolated public/private
  builds with title/H1/schema/CSP checks across 17 content pages.
- All 18 generated HTML documents (including 404) match the published-source
  snapshot byte for byte after removal of legacy email strings in overwritten
  generator content.
- Nine published asset sizes and SHA-256 values match the retained source assets.
- Reviewed source allowlist and scanned for common credential formats, email
  addresses and private Google document/editor URLs. No matches remain.
- Initial tests were corrected to allow public `/forms/d/e/` responder URLs and
  legitimate timestamp parameters on public YouTube links; editor URLs remain
  forbidden. No production behaviour was changed to satisfy those tests.
- Download restoration was not exercised over the network in this lane; its
  pinned manifest was verified locally. No external forms were submitted.
- Repository-wide CI and bootstrap acceptance are separate gates, not implied
  by these local results.
