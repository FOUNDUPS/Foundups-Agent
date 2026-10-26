# Acoustic Lab TestModLog

## 2026-10-25 - Timeout repair author and independent local results

The original 18 selected identities are preserved. Only the existing timeout
method is strengthened; the new TestFFmpegChildOwnership case is a separate
one-child phase, never a process permission for the 18 deny-all cases. Download
and FFmpeg command validation use controlled mocks; only the disposable Python
child is an actual process. All six
Gunicorn methods and every other prior test method remain AST-identical.

Baseline replay: 17/18 passed; the timeout assertion failed because kill was
not called. Repaired v3: exactly 18/18 pass (32.216s), followed by exactly 1/1
owned-child case (0.294s), zero failures/errors/skips and matching JUnit IDs.
The controlled first communication verifies the production 30-second argument
then uses a real 0.05-second fixture timeout. The actual product cleanup kills
and communicates with its five-second bound. Windows pipe closure, finished
reader thread and signaled process handle are asserted before adapter return;
POSIX waitpid reaping remains a separate hosted platform assertion. The small
Python fixture writes one owned ready marker and pipe payload; it never runs
FFmpeg or spawns descendants. Outer rescue makes the case fail.

Preserve rejected v2: the 18 cases passed, but native setup failed before a PID
existed because Popen._get_devnull's O_RDWR open was denied. The v3 guard admits
exactly that one open during the already validated constructor, bound to the
saved code object/instance/path/flags; unrelated null writes and launches remain
denied. Windows flags were observed as 130 (O_RDWR|O_NOINHERIT). Existing guarded
Windows processor/ZIP/console adaptations remain disclosed; no OS sandbox is
claimed. The corresponding Linux CI gate has separate platform acceptance pending.

Evidence under the existing external refresh directory:
- acoustic-timeout-baseline-20261025-execution.json: original failure.
- acoustic-timeout-positive-v2-execution-20261025.json: rejected guard attempt.
- acoustic-timeout-positive-v3-execution-20261025.json and matching output folder:
  exact command/environment, source hashes, collection, JUnit and child receipt.
- acoustic-timeout-independent-null-admission-review-20261025.json: independent
  capability preflight only, not an independent test outcome.

Independent review accepts the bounded source and local lifecycle outcomes. Its
separate one-case positive passes; missing-kill and missing-drain controls each
select one case, producing one call failure plus an intentional rescue teardown
error. The two JUnit entries in each rejected control are not two selected tests.
All controlled children, pipes and reader threads are settled after recorded
rescue; that rescue is failure evidence, never product acceptance. No unknown
effects occurred. All 16 source and 84 distribution metadata hashes stayed stable.
The formal receipt is acoustic-timeout-independent-outcome-review-20261025.json.
Fresh hosted Linux/native Gunicorn gates remain pending. Four broader historical
failures were not rerun. The original pre-repair inventory below is history.

## 2026-10-25 - FFmpeg timeout settlement inventory before repair

Preserve the 18 selected application/Web3 identities and six native Gunicorn
cases. Strengthen the existing X timeout case to require owned-child kill and
bounded second communication before tempfile cleanup. Preserve the prior 1338
negative and reproduce this assertion against the current unmodified adapter
before repair. A separate exact Python-child oracle must establish actual
settlement, descriptor closure and reaping; rescue cleanup counts as failure.
No FFmpeg binary, live download, account, provider or network call is admitted.
Code, real-child capability review and execution outcomes are pending.


## 2026-10-25 - PR1355 Flask request-instance compatibility inventory

Before corrected execution: retain the existing 18 selected cases (seven X,
five multipart and six Web3) and the separate six native Gunicorn cases.
The first Flask 3.1.3 Windows run collected all 18: 17 passed, while the
oversized-metadata test stopped before its POST because a class-level property
was compared to 500000. Preserve that rejected run and its guard/JUnit output.
Only that assertion now reads the real request instance in a test context;
the 600000-byte multipart POST, 413/error checks and no-processor assertions
are unchanged. The production limit/configuration is unchanged. Corrected author
execution passes 18/18 with exact collected/passed/JUnit identities, zero
failures/errors/skips and no unknown or duplicate effects (29.829 seconds).
The real oversized POST executed and returned 413 before processor access.
All 16 source hashes remained stable. Independent review passes: its separate
18-case replay took 31.734 seconds; an in-memory 700000-byte limit caused only
the intended existing limit assertion to fail, with the other 17 cases passing.
All 16 source and 84 distribution metadata bindings stayed unchanged; no unknown
effects occurred. Receipt `pr1355-independent-review-20261025.json` records the
review. Fresh hosted Linux Python 3.11/3.12 plus native Gunicorn acceptance
remain pending.

Use pr1355-author-corrected-execution-20261025.json and the separate
pr1355-author-corrected-20261025/ guard, XML and log in the existing external
refresh directory. The rejected pr1355-author-20261025/ output remains intact.
The existing Windows guarded harness clears application environment values,
denies network/process/SQLite/private configuration effects and permits owned
output writes only. It retains the documented processor-name/yt-dlp terminal
adaptations, omits a proven absent interpreter ZIP and disables AVX probing.
This instrumentation is not an OS sandbox or hosted Linux acceptance.

All other test methods/fixtures and the six separate native Gunicorn cases
remain unchanged. The prior four broader failures (triangulation, index,
invalid upload type and geolocation failure) are historical and were not rerun
or solved. No live X/RPC/account/transaction or model execution was performed.


## 2026-10-23 - PR1356 Web3 compatibility inventory before edits

Preserve all seven existing processor/audio-library tests and their fixtures,
the 12 selected X/multipart cases and six native Gunicorn cases. The broader
33-case baseline retains four documented failures and six Windows-only skips.
Read the actual Web3 7.15.0 and eth-account 0.13.6 wheels before extending the
existing processor test file with six logical compatibility cases. Independent
source review confirms the real default middleware, controlled JSONBaseProvider,
both block-query routes and missing/wrong-layer rejection controls.

The original Web3-only proposal fails full dependency resolution because its
eth-account 0.10.0 pin violates Web3's minimum 0.13.6. The repaired full graph
resolves to 76 binary packages. Hash-locked installation and pip check pass in
the reused Windows environment; seven preexisting orphan distributions remain
alongside pip. This is not a fresh environment or application test result.
Record normal-import guarded execution, fault controls and fresh Linux 3.11/3.12
hosted acceptance after they run. No RPC, wallet, transaction or live service
effect is admitted. Existing simulated logging remains simulation.

### PR1356 local qualification results

- Exactly 18 selected cases pass in both the author and independent Windows
  runs: seven existing X cases, five existing multipart cases and six new Web3
  cases. No failures, errors, skips, unknown effects or duplicate capability
  probes; exact collected/passed/JUnit identities agree. The author run took
  28.797 seconds. Keep the two runs separate rather than adding denominators.
- Actual installed Web3, default middleware and JSONBaseProvider execute with
  synthetic replies. Both block-query routes transform oversized PoA extraData
  only with the inner middleware; default and outer-layer controls reject it.
  Connection fallback, network-stat conversions, canonical hashing and continued
  simulated logging are checked. No provider call beyond the declared sequence
  is permitted, including an attempt swallowed by application error handling.
- Independent in-memory controls retain disk source and installed packages:
  the old import yields six intended availability failures; removed injection
  and outer-layer injection each yield two intended failures. A caught DNS
  attempt leaves 18 passing tests but fails the guard; losing one collection
  identity leaves 17 passing tests but fails inventory acceptance.
- The Windows harness uses public SYSTEMROOT/WINDIR inventory, disables the
  processor-name probe and yt-dlp's console-mode setup, excludes only a proven
  absent interpreter ZIP path and allows linecache to read the exact frozen
  harness. Fifteen console setup calls are suppressed, not exercised. File,
  SQLite, account-configuration, network and process guards remain active.
  These are Python checks, not OS confinement or hosted Linux acceptance.
- Preserve the first Windows initialization/readback failure and subsequent
  guard-rejected 18-pass attempts. They prompted narrow harness corrections,
  not application or acceptance-criteria changes. All 13 observed source files
  remained unchanged; independent controls also preserve 84 distribution
  metadata bindings. Four broader historical failures were not rerun here.
- Receipts: `pr1356-author-positive-20261023.json` and
  `pr1356-independent-execution-review-20261023.json` in the existing external
  reconciliation refresh directory. The existing CI selection is being extended
  to these same 18 cases; the six native Gunicorn cases remain a separate gate.
  Fresh hosted Python 3.11/3.12, publication and main readback remain pending.

### PR1356 first hosted failure and bounded harness correction

At published head `1b01ce24b45d4df1980e636064984376397ca8fd`, both
pull-request CI runs 39929152950 and 39929152969 failed the adapter gate on
Python 3.11 and 3.12. Each artifact records 18 collected and 16 passed, including
all six Web3 cases. The two multipart failures attempted system MIME-file reads;
Numba's CPU capability probe also attempted `/proc/cpuinfo`. The guard correctly
rejected those effects. The following native Gunicorn step did not execute.
Do not count these runs as hosted acceptance or add their case denominators.

Configure only this Linux test process with `NUMBA_ENABLE_AVX=0` and initialize
stdlib mimetypes from its built-in table, asserting the expected WAV type. Keep
system MIME reads denied, leave application/tests unchanged, and report these
configurations explicitly. This qualifies neither host MIME configuration nor
AVX performance. Independent source review and fresh exact-head hosted execution
are required; no filesystem allowlist, guard, test selection or assertion is
weakened to accept the earlier runs.

## 2026-10-23 - PR2081 multipart boundary inventory before edits

Read the existing eight web/geofencing cases, seven X-adapter cases, six
Linux Gunicorn cases and seven processor cases before this extension. Keep
their assertions and the four documented broader failures unchanged. Reuse
`TestWebApp` for actual multipart parsing with controlled processor and denied
network, process, downloader and Ethereum boundaries; no server or live upload.

The external paired probe reproduced the same 600,015-byte multipart metadata
request returning missing-file 400 on Werkzeug 3.0.0, but parser
`RequestEntityTooLarge` 413 becoming application 500 on 3.1.9. Preserve that
pre-repair evidence. Add only the missing oversized rejection and small,
invalid, health and exact byte/metadata forwarding controls. Qualification
results follow after execution; the older Gunicorn 21.2 probe environment is
not the current full requirements environment.

### PR2081 local qualification results

- Fresh full requirements on Windows CPython 3.12.10: 81 installed module
  packages plus pip, Werkzeug 3.1.9 and Gunicorn 22.0.0, successful `pip check`.
- Existing CI wrapper replay: seven X cases plus five explicit `TestWebApp`
  cases, exactly 12 collected/passed, no skips or unexpected effects. Original
  whole-X-class collection remains so an unlisted future test fails inventory
  accounting. The Windows replay replaces `/dev/null` with `os.devnull` and
  suppresses the existing Windows processor-name inventory probe; hosted Linux
  Python 3.11/3.12 remains a separate gate.
- The new multipart rejection traverses the actual parser and returns JSON 413
  for a 600,015-byte valid metadata field, retaining its 500,000-byte default.
  Below-limit metadata still reaches missing-file 400. A tiny WAV is forwarded
  with exact bytes and metadata to a controlled domain-error boundary; invalid
  JSON, non-WAV and health behavior remain correct. Effect tripwires also fail
  cleanup if an attempted operation was swallowed by the application's handler.
- Existing setup constructs the real synthetic processor under the outer
  pre-import guard. Only the request fixture substitutes its operation; no real
  audio-processing success, downloader, HTTP/RPC, wallet or logger effect ran.
  Python guards are not an OS sandbox.
- One full two-file comparison after adding tests: 33 cases, 23 passes, the
  same four failures and six explicit Windows Gunicorn skips. The unchanged
  failures are `test_index_page`, `test_upload_invalid_file_type`,
  `test_geolocation_service_failure` and `test_triangulation_calculation`.
  No xfail, quarantine or assertion change; FFmpeg timeout-child debt remains.
- Evidence in the existing external refresh directory: `pr2081-focused-ci-20261023.*`,
  `pr2081-existing-suite-execution-20261023.json` and the full-environment receipt.
  Fresh hosted acceptance remains pending at this checkpoint.
- Separate independent Windows-adapted verification reran the exact 12 cases
  with no skips. Handler-reversion and disabled-limit controls fail the protected
  assertion. A caught unexpected process attempt and a missing passed-result ID
  each fail the CI gate even with 12 passing tests. Original method ASTs and
  frozen executable hashes remain unchanged. Evidence:
  `pr2081-independent-source-execution-review-20261023.json`; these results are
  separate from the builder's counts and do not replace hosted Linux acceptance.

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

## PR1354 Gunicorn qualification implementation (2026-10-23)

Read the existing two-file inventory and PR1338's seven adapter cases before
preparing this extension. Reuse `tests/test_web_app.py` with six cohesive
`TestGunicorn` cases: exact config/defaults, missing-factory negative control,
deployment manifest path, valid parser controls, rejected ambiguous framing,
and actual foreground health/rejection/shutdown. Existing tests are unchanged.

The parser consumes in-memory bytes; the native fixture uses a fresh process
group, one sync worker, temporary runner-owned paths and loopback port zero.
It permits only Gunicorn's worker fork and declared listener while denying
child outbound/DNS/native-command effects before factory import. Python guards
are not an OS sandbox. Normal cleanup must reap the master, leave no owned
worker/process-group member, and require no forced kill. Cleanup is registered
immediately and reports its own failure without hiding an earlier test failure.

Linux-only tests are explicitly skipped on unsupported platforms; the hosted
Linux selector must collect and pass all six with zero skips. The target's
parser rejection case must also expose baseline 21.2.0's failure using an
isolated import overlay with every other installed dependency unchanged. The
original config's missing binding is tested without positional APP or a
replacement wsgi_app. No compatibility defaults are weakened.

State: source implemented; Linux hosted acceptance pending. Independent source/CI
review, Python/YAML syntax checks and seven guarded Windows adapter regressions
pass. The test registry remains current. The existing CI job selects Python 3.11
and 3.12 while preserving its 15-minute limit and original deny-all adapter step.
Gunicorn 22.0.0 installation, Linux parser/server execution and hosted artifact
review remain pending. Existing four broader failures and the separate FFmpeg child-timeout
obligation remain explicit; neither is xfailed or repaired in this slice.


### PR1354 independently verified Linux outcome (2026-10-23)

Supersedes the pending implementation checkpoint above. CI39881377042 at
`3bc5471a3a2255923be30c4764d1f7d21d67b1f5` passed all six native cases
and seven adapter cases on Python 3.11.17 and 3.12.15, with no skips/errors.
The old 21.2.0 overlay passed valid parsing and failed the protected framing
assertion with `InvalidHeader not raised`, rather than an import/setup error.
Full installs, pinned dependencies and pip checks passed. Independent artifact
review verified exact source/config bindings, three loopback requests, one
master and worker, exit zero, no survivors and no forced cleanup. Unknown or
duplicate effects were absent. All 20 head checks succeeded. Final publication
and main checks remain separate from this observed source checkpoint.

Evidence: `O:/RedDog-Builder-Artifacts/pr-reconciliation-20261021/refresh/`
`pr1354-independent-hosted-review.json`. The four broader failures and FFmpeg
timeout-child obligation remain open. No production or native AI-worker claim.
