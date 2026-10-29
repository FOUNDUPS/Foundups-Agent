# WSP core change log

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
