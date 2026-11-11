# Bounded aiohttp test-mock compatibility backport

## Scope and provenance

The GitHub client contract job uses aiohttp 3.14.5 with the released aioresponses
0.7.9 wheel. The latter lacks aiohttp 3.14's required response `stream_writer`
argument and the parser required for large-body pause/resume flow control.
This blocks qualification of the security update with the existing client tests.

The CI-only helper applies exactly the seven added runtime lines in
[upstream PR #292](https://github.com/pnuckowski/aioresponses/pull/292), immutable
commit `1a48e1f898035e3bedc981f06520842c55977706`, authored by `kleine-safie`.
Its constructor fix incorporates [PR #288](https://github.com/pnuckowski/aioresponses/pull/288).
These are open contributor proposals, not a released or maintainer-approved fix.
The released 0.7.9 runtime files match upstream tag commit
`f95f26bdf226b0c8329e7d4e96b623a3dc33ab22` exactly.

Only the two installed aioresponses runtime files change, inside the selected
ephemeral test interpreter. The helper accepts only aioresponses 0.7.9 and
aiohttp 3.14.5, verifies both original and final SHA-256 values before writing,
and rejects altered, mixed or already patched sources. It does not import or
patch application/aiohttp classes, change assertions, or catch client errors.
The real StreamReader remains responsible for delivering body bytes and EOF.

The wheel is installed with `--only-binary`, `--no-deps` and `--require-hashes`.
Its original distribution RECORD is retained; the separate backport receipt
explicitly identifies the local source overlay and must accompany pip/JUnit
evidence. Do not describe the installed result as an unmodified upstream wheel.
Run this helper only in a disposable CI or qualification environment.

## Qualification and removal

The existing two canonical GitHub client/permission test files and their command
remain unchanged: 167 cases are required with no skipped or expected failures.
Qualification must additionally show complete large-body delivery, over-limit
rejection, unmatched-request/assertion failures, status/MIME errors, timeout and
cancellation cleanup, and rejection of version/source/repeat mismatches.
Mocked HTTP tests do not prove wire framing, network confinement or deployment.

Remove this helper, its pinned mock-wheel requirement and its workflow step when
an official aioresponses release supporting the selected patched aiohttp passes
the same unchanged suite and focused controls. A version bump alone is not that
removal evidence. Requalify rather than relaxing hashes for an unreviewed version.

## License and attribution

The backported runtime changes are derived from the MIT-licensed aioresponses
project and the upstream contributors cited above. The upstream license follows.

MIT License

Copyright (c) 2016 pnuckowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
