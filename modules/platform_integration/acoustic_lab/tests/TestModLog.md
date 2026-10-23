# Acoustic Lab TestModLog

## 2026-10-23 - PR1338 inventory recovery before adapter tests

This module previously had no test inventory log. Read both existing unit files
before adding tests: test_web_app.py (8 cases) and test_acoustic_processor.py
(7 cases). Existing operational probes test_x_upload.py, test_coordinates.py,
test_coordinate_extraction.py, test_google_earth.py and scripts/test_phase1.py
are not offline acceptance. No new test family or quarantine rule is introduced.

Extend existing test_web_app.py with real installed YoutubeDL constructors and
controlled extraction/download/ffmpeg boundaries. Fake ffmpeg proves arguments
and temporary-file cleanup, not native child settlement. Four baseline failures
remain explicit. Record execution results after qualification.

## Qualification results - 2026-10-23

- Existing two-file suite: baseline and candidate each run 22 cases after the seven-case extension: 18 pass and four unchanged failures under pytest; native unittest records the same cases as two failures and two errors. No skips, xfails or quarantine changes. The original eight web-app and seven processor cases retain their assertions.
- New `TestXVideoURL` cases cover real installed downloader construction and adapter options, metadata-only extraction, unavailable dependency, invalid metadata/extractor failure, download failure, nonzero/short FFmpeg result, process spawn failure, timeout error and temporary-file removal. Seven cases include subcases; they are counted as seven, not inflated by subcases. Extraction, download, FFmpeg and RPC/provider boundaries are controlled; no real X or media process runs.
- The separately retained timeout-child negative fails in both versions because production does not kill/wait the child. It is external evidence and a repair obligation, excluded from the seven-case passing denominator and repository suite. Temporary-file removal is not child settlement.
- External two-case candidate backend check and three optional-capability checks pass: Urllib fallback/HTTPS-proxy limitation, gzip/deflate decoding without Brotli advertisement, retained Crypto AES known-answer/native-HLS acceptance, and no configured metadata postprocessor. They do not prove live X, complete encrypted-HLS transfer, all formats or network behavior.
- Executed under Windows CPython 3.12.10, fresh full requirements installs and `pip check`, with environment allowlisting, `PYTHONDONTWRITEBYTECODE=1`, `PYTHON_DOTENV_DISABLED=1` and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. External guard denies sockets/DNS/listeners/native processes before source imports; optional host probes fail as unavailable. The existing 2173 harness was reused byte-for-byte, with an external guarded launcher. Initial fixture/guard failures remain in the evidence directory.
- Repeatable repository gate: `.github/workflows/ci.yml`, job `acoustic-x-adapter`, installs complete module requirements in a separate environment and selects exactly `test_web_app.py::TestXVideoURL`. Its pre-collection Python API guards record denied effects, reject unexpected attempts and require all seven collected/passed IDs. These are Python guards, not an OS security sandbox. An independent Windows-adapted replay passes; caught unexpected effects and missing-result controls fail the gate. Hosted Ubuntu execution remains pending at this checkpoint.
- Exact commands, source hashes, residual identifiers and all logs: `O:/RedDog-Builder-Artifacts/pr-reconciliation-20261021/refresh/1338-qualification/qualification-receipt.json`. No installed-service, Linux, Python 3.11, account, FFmpeg, native RSI or live operational claim.

### Hosted collection correction

First Ubuntu job `120166049591` passed full installation and `pip check`, then
failed before collecting cases: pytest 8 used `/dev/null`'s parent as its default
collection boundary and probed `/home/packer/__init__.py`. Explicit
`--confcutdir=.` keeps ancestor collection within the checkout. No permissions,
source assertions or effect guards changed. This was not an application failure
or a passing test run; fresh hosted evidence remains required.

Second Ubuntu job `120167490136` collects and passes all seven cases but fails
the effect gate on three unclassified denied process probes. Denied-event
records now include bounded module/function names for diagnosis, with no command
arguments, environment values or frame locals. Rejection remains unchanged.

Third Ubuntu job `120168933047` identifies all three denied calls as optional
PyCryptodome GMP discovery (`ldconfig`, compiler and linker helpers in ctypes).
The isolated test environment now explicitly selects the supported
`PYCRYPTODOME_DISABLE_GMP=1` fallback already reached after denial. Production
configuration and all effect rejection remain unchanged; this does not qualify
GMP. Seven cases passed in that failed gate; corrected hosted acceptance is pending.
