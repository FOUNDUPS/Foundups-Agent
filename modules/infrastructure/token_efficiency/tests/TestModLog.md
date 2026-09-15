# Token Efficiency TestModLog

## 2026-09-15 — AmIBot G0 legacy-invariant regression

Reused `test_m2m_compiler_compat.py` and unchanged `test_m2m_fidelity.py`.
Initial matrix: 30 failed/169 passed. Final selection: 222 passed in 0.46s;
independent review reran 222 and nine targeted probes. Runs overlap and are not
additive coverage. The original 162 cases remain; 44 rejection cases cover both
object/public-wrapper paths, and 16 scalar cases preserve legacy text semantics.

Review first rejected two representable-input regressions despite 207 passing
tests. Empty values/internal-space keys are now retained; Unicode line separators
are rejected within invariants. Tests do not qualify the full machine envelope,
other compact fields, YAML, runtime authority or product acceptance.
Eight manifest tests pass in 69.08s and 15 RedDog fast groups pass. Registry remains
1,650/269 quarantined. Exact commands/source/review/failure evidence is recorded
under `amibot_g0_continuation_20260915`; no new test file or fixture owner.

## Inventory — 2026-09-14

WSP 22/97 retrieval inventory, recorded before extending the existing tests.
No new test file is required for the stop-rule handoff repair.

| Existing test file | Reuse for |
|---|---|
| `test_bypass_classifier.py` | Sensitive-output bypass, unknown-command rejection, classification priority |
| `test_compute_governor.py` | Pre-execution routing, digests, redaction, dry-run boundaries |
| `test_m2m_fidelity.py` | Compact prompt field preservation, corrupted handoffs, context-object checks, role checks, raw references |
| `test_m2m_compiler_compat.py` | Compiler modes, compact grammar, legacy packets, decompilation, public wrappers |
| `test_rtk_evaluation_dryrun.py` | Candidate evaluation, recovery reference, savings, no runtime execution |
| `test_rtk_openclaw_hermes_adapter_dryrun.py` | Adapter planning, preserved raw output, invalid routing, no live wiring |
| `test_telemetry_service.py` | Measurement, serialization, aggregation, memory store, no secret persistence |

The existing 158-case fidelity/compatibility result belongs to PR1712; it is
historical evidence, not a fresh run. The current repair extends the two M2M
files and retains the existing fixture/parameterization structure.

## 2026-09-14 — Stop-rule handoff regression

Extended both M2M test files: one existing preservation assertion plus four
new cases produced five failures / 157 passes before the repair. Afterward,
162 tests pass in 0.48s. The two warnings concern asyncio configuration while
automatic plugins are disabled; these selected tests are synchronous.

Dependency verification: 15 RedDog fast groups pass after configuring the
existing `REDDOG_TEST_SITE_PACKAGES`/`REDDOG_TEST_PYTHON` inputs for an isolated
worktree. The initial attempt lacked that dependency-root setting. Eight
staged manifest tests pass in 61.71s; the same two configuration warnings apply.

Coverage: stop text reaches decompiled instructions; missing, weakened or
substituted instructions fail the gate; legacy packets retain stops; stop-free
legacy rendering remains unchanged. Existing action, scope and malformed-list
rejections remain included. No full-context fidelity or independent evaluation
claim follows from these local tests.

Focused command (use isolated temporary paths and the qualified interpreter):
`python -B -m pytest modules/infrastructure/token_efficiency/tests/test_m2m_fidelity.py modules/infrastructure/token_efficiency/tests/test_m2m_compiler_compat.py --import-mode=importlib -p no:cacheprovider -q`
