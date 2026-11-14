# WSP core change log

## 2026-10-29 — Share WSP 3 policy and preserve unqualified ownership hints

F6a centralizes immutable domain/exception/reserved-name constants and the pure
module-evidence rule in this existing owner. FMAS and WSPComplianceChecker reuse
it. Data-only containers no longer create false missing module contracts; they
remain explicit architecture hints even under document suppressions. Git/source
inspection, Holo committed-generation acquisition and physical layout are unchanged.

Three frozen existing-consumer regressions fail on main34b and pass unchanged on
the candidate. The checker now has ten additional cases, including both canonical
WSP 3 mirrors, generator input, direct contract evidence, reserved names, exception
compatibility and no-IO policy calls. Focused checker/FMAS/frozen selection: 83
passed. The integrated audit selection passes 255 tests plus 28 subtests; runtime
and idle-consumer selection passes 24 tests; three Node compatibility suites pass.
Exact-base Mode 2 reports 0 errors/127 warnings/306 advisories. The unchanged test
registry is current at 1787 owners/260 quarantined. A structural-only inspection
of clean main34b confirms both auditors agree on 158 roots/eight unresolved
containers, with unchanged Git status. The checker still reports the uninspected
Hermes submodule explicitly; no whole-repository security coverage is claimed.

The runtime closure adds only this pure helper (1473 total) and changes only the
checker digest. Bind both manifest pins; admit exactly 1473 files and reject 1474,
keeping 329 KiB/2 MiB/32 MiB byte caps. Review 39 exact source-hash metadata findings:
38 previously reviewed unchanged digests and one newly reported unchanged digest,
all recomputed against staged source. Preserve all 2705 prior review bindings;
no security rule or source-path exclusion changes. Hosted/main acceptance remains
required; these are source compatibility and local deterministic checks.
Manual API and boundary verification was needed; no Qwen/Gemma or independent
review is claimed. WSP 3/5/6/11/22/49/50/60/64/84/87/97.

## 2026-10-29 — Tracked, bounded, read-only compliance hints

Replace recursive traversal and implicit PatternMemory construction with one
validated Git index snapshot per scan. Source reads are bounded; untracked files,
environment content, links and reparse points cannot enter ordinary inspection.
Unsupported/unreadable content yields explicit SCAN_INCOMPLETE records. Reuse the
existing bounded WRE Git reader. Stored learning data is neither read nor removed;
an explicit in-memory snapshot is available for documented false-positive hints.

Use current WSP 62 advisory thresholds, direct component counts and real block
names. Recognize monitoring and the documented wre_core exception. Findings never
claim test coverage from directory presence or authorize placeholder auto-fixes.
Replace non-existent validator/enforcer examples with the actual interface.

Frozen acceptance on main3ad: 31 failures / 8 controls. Candidate: 39 passing
synthetic cases, including the adjacent GitHub constructor root binding. A real
read-only scan of main3ad completed in 14.11 seconds, with unchanged Git status;
it reported 270 size, 38 component, 11 architecture, 43 ModLog, 62 test-document
and 69 dependency hints plus one uninspected Hermes submodule. These are bounded
source/metadata observations, not full module/security/deployment acceptance.

Integrated selection: 173 passed plus 28 subtests; runtime/idle-consumer selection
24 passed; registry selections 62 passed; three Node compatibility suites passed.
Exact-base FMAS reports 0 errors, 127 warnings and 306 advisories. Registry 1785/260
preserves every prior row. Runtime closure remains 1472 files with only the checker
source hash changed; the GitHub adapter is outside that existing closure. Rebind
both compatibility pins and 38 previously reviewed unchanged source-hash findings
to the new manifest bytes, preserving all 2667 prior review bindings. This is
metadata review, not a security-rule exclusion or independent security audit.

Manual analysis was required to prove side-effect and Git-root boundaries with
executable regressions. No Qwen/Gemma execution or independent reviewer is claimed.
WSP 3/6/11/12/22/50/57/60/62/63/71/87/97. Shared FMAS domain constants, remaining
external scanner repetition and substantive debt repair remain follow-on work.
