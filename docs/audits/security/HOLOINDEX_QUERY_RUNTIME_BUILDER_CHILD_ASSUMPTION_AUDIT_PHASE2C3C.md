# HoloIndex Query Runtime Builder Child Assumption Audit - Phase 2C3c

**Status:** Implemented and physically falsified as inert child evidence
**Decision:** GO for bounded observation; NO-GO for activation/closure claims
**Base:** `96d5db5685a015932205bd573b7ea1674b0897cd`
**WSP_15:** 19/P0, ULTRA

## Retrieved evidence

Governed Holo retrieval was CURRENT at exact base, reported no index gap, and
performed no reindex. It found the existing process-authority proof, exact
builder/runtime composition, held executable primitive, and bounded
maintenance child. Direct repository reads supplied the required module docs,
tests, generator, extension pin, and Python-version constraints that semantic
retrieval did not rank reliably. This local correction prevented a duplicate
launcher and repaired the version-query noise/missing-artifact gap.

Official Python release metadata was checked before selecting a physical
runtime. CPython 3.12.14 is the current 3.12 source-only security release;
3.12.10 is the final official Windows binary release. The exact reviewed
3.12.10 AMD64 archive hash matched the official Windows manifest before its
O:-only inert base was materialized. That known patch gap is retained as a
blocking nonclaim rather than disguised as current runtime authority.

## Dialectic result

- Returning `BuilderProcessAuthority` across JSON was rejected because the
  capability seal is meaningful only inside the proving process.
- Creating another subprocess implementation was rejected; the existing
  maintenance runner was extracted into a generic bounded child runner while
  preserving its public compatibility names and limits.
- Inheriting ambient environment or `sys.path` was rejected. The child receives
  only O:/E:-local temp values and an exact six-entry import path.
- Trusting child output was rejected. Strict canonical parsing, complete
  identity cross-binding, and full before/after composition proofs are required.
- Using a synthetic executable as physical proof was rejected. The opt-in
  integration launches the actual O:-materialized interpreter.
- Treating CPython 3.12.10 as production-current was rejected. Current-patch
  runtime migration and provenance/pre-import/native-loader proof remain P0.

## Falsifiers and limits

Tests cover command flags, environment closure, one-child execution, bounded
output and direct input size, duplicate/noncanonical JSON, forged runtime
bindings, wrong child identity, every protected-root class, timeout/output/read
failure mapping, after-child composition mutation, live-overflow tree cleanup,
accidental evidence construction, maintenance compatibility, and one real
qualified child. Runner unit evidence is 22/22; focused physical runner/
maintenance/process-image/child evidence is 70 passed / two capability skips in
108.06 seconds and includes the real physical child. That call rehashes
the complete composition before and after execution, so it is deliberately slow
and is not a scale test.

The first independent WSP_00/WSP_97 audit issued NO-GO. It found an incomplete
receipt, unstaged `-B`, 1,003-line extension README, coverage overstatement,
parser/evidence hardening debt, and a newly polluted writable base. Investigation
preserved two invalid generations: 21 pycache directories / 181 pyc files and 6
directories / 32 files. The exact official source reproduced the same sealed
generation, descriptor, and inventory IDs. Test hosts were moved to that clean
source, subprocess fixtures and the O:/E:-restricted conversation harness now
use `-B`, README is 998 lines, and final replays leave both runtime trees clean.

The second independent audit remained NO-GO until two additional findings were
reproduced: overflow cleanup could enter an unbounded `wait()`, and the Windows
conversation tier still admitted an ambient interpreter fallback. Both now fail
closed. A subsequent real conversation run exposed a deeper dependency leak:
the O: interpreter discovered per-user packages outside O:/E:. The harness now
uses `-B -s`, disables user-site discovery, erases ambient Python controls, and
validates the O:/E: interpreter, dependency, repository, and temporary roots.

The same audit's governed Holo attempts failed with
`HOLOINDEX_QUERY_SERVICE_EXITED_DURING_STARTUP`. Direct bounded diagnostics
proved the O: virtual environment still named a different-volume base Python,
so the trusted source interpreter correctly withheld its dependency path and
the owner exited on missing NumPy. Rebinding that local environment to the
already verified O: CPython 3.12.10 source restored one-attempt CURRENT retrieval
at exact base, no gap, and no reindex. This was an environment repair, not an
index refresh or query-time mutation.

A final hostile review found three remaining defects. First, direct-parent exit
could leave an inherited-stdout descendant alive because tree cleanup returned
after the parent had exited. An authentic RED reproducer now passes under a
Windows kill-on-close Job Object: the child starts suspended, assignment and
resume fail closed, and cleanup explicitly terminates every descendant before
releasing the handle without resolving an external executable. Second, the conversation confinement
contract had source-text assertions but no executable negative boundary tests;
missing, relative, wrong-volume, ambient-control, and intermediate-junction
cases now execute against exported guards. Third, the new 2026-08-28 memory
entries preceded 2026-08-29/30 history; all affected ModLog, TestModLog, and
roadmap entries now preserve honest reverse chronology. The expanded focused
runner/maintenance/builder-child surface passes 50 tests with one capability
skip.

The final independent pass remained NO-GO on four executable boundaries. The
conversation harness inherited unlisted `PYTHON*` and `PYTEST*` controls, so
`PYTEST_ADDOPTS=--collect-only` could false-green the tier. Windows cleanup
could resolve ambient `taskkill`, Job terminate/close results were unchecked,
and reader-thread startup failure occurred outside the cleanup guard. Authentic
REDs now strip both control families case-insensitively before setting six exact
values, resolve no cleanup executable, terminate the Job before handle release,
surface every lifecycle failure, and contain reader startup. Direct evidence is
22/22 runner falsifiers, 70/2 physical adjacency, and the 32-Python/15-JS
conversation tier passing under deliberately hostile controls.

The first complete bridge macro then produced one authentic order-dependent
failure after 1,685 passes: health JSON nesting was bounded only by whatever
recursion limit the host process currently exposed. A falsifier raises that
limit above a 2,000-level payload. A string-aware byte scan now rejects more
than 128 structural levels before `json.loads` while ignoring brackets inside
strings. The focused boundary is 160/160 and the same original-order macro is
1,694 passed / 23 capability skips in 638.81 seconds.

A final cleanliness inspection found four encodings pyc files timestamped
07:30:22 in the writable qualified source runtime. The creator cannot be
attributed from filesystem evidence, so the full affected runtime is preserved
in O: forensic quarantine rather than silently cleaned. Rematerialization from
the qualified `sha256:8649692d...39415d` archive is byte-exact for all 3,845
members with zero missing, changed, or extra files. The canonical Holo command
now sets `PYTHONDONTWRITEBYTECODE=1` and invokes Python with `-B`; a subsequent
verification leaves source and active materialized runtimes at zero pycache/pyc.

The post-gate hygiene check found a second four-file encodings cache stamped
08:27:30, before the resumed exhaustive and release runs. Filesystem evidence
cannot identify its creator. The complete image is preserved at
`O:\RedDog-Builder-Artifacts\quarantine\source-runtime-3.12.10-encodings-pycache-recurrence-20260830-091617`.
Archive-only rematerialization again proved all 3,845 members with zero missing,
changed, or extra files; the active sealed runtime had remained clean.

Backend is 1,398 files at
`sha256:700d50f84e12d6deece513092ee6cab153defcc99c51f5a543aafdd1286e09ed`;
registry is 1,640 / 269 quarantined. Conversation is 32 Python tests plus 15 JS
vectors. The deterministic package is 67 files / 948,410 bytes at
`sha256:c1036d6fb9b27a906f04eeca480788fa9af52ab536505b9e58b6dbe43fbf0559`.
Four release groups pass in 214.279 seconds. The inspected 276,270-byte VSIX is
`sha256:13b629dd280120c87e206cec90243c7b2132ab81ac32d4b0537cefe71c8eaff6`,
with 69 safe entries, 67 exact source members, and zero archive, path, sensitive
name, source-byte, or credential-value findings.

The evidence does not prove authenticated production origin, package import
closure, Windows loader resolution, native or subprocess loaded-image closure,
deterministic side effects, signature, persistent write denial, route/owner
activation, A-grade retrieval, or retrieval RSI.
