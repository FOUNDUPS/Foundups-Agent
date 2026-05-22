# Red-Team Regression Test Suite

Adversarial pytest suite for the agent runtime. Source contract:
[`docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md`](../../../../../docs/audits/security/FOUNDUPS_AGENT_REDTEAM_REGRESSION_SPEC_PHASE1.md).

This README documents what is in the suite **right now** (Phase 2 skeleton)
and how to extend it. The spec document is normative; this README defers to
the spec for any disagreement.

---

## What This Suite Is (and Isn't)

- **Is**: deterministic adversarial tests that verify the agent refuses
  specific classes of misbehaviour AND emits a `[SAFETY-EVENT]` record for
  every refusal.
- **Is NOT**: a unit-test replacement, a model-jailbreak benchmark, a
  performance suite, or a live-secret test. Live secrets and real network
  egress are blocked by harness invariants — see "Invariants" below.

## Phase 2 Scope

| Test family | Phase 2 cases | Future cases (separate slices) |
|-------------|---------------|--------------------------------|
| A — Scope-lock violation | `SL-001` | `SL-002..SL-005` |
| B — Credential exfiltration | `CE-001` | `CE-002..CE-004`, probabilistic `CE-006`. `CE-005` HOLD pending WSP_71 layer. |
| C — Poisoned HoloIndex retrieval | `HP-001` | `HP-002..HP-005`, probabilistic `HP-006` |

Each Phase 2 family also ships:
- A **negative control** (in-scope/benign input must NOT trip the refusal).
- An **invariant test** that directly verifies the harness guard (synthetic-
  only credentials for Family B; network egress block for Family C).

Negative controls are what stop the suite from passing by blocking
everything.

## Invariants (spec §3.3 — enforced by `conftest.py`)

| # | Invariant | Where enforced |
|---|-----------|----------------|
| 1 | Synthetic-only secrets | `_validate_synthetic_only()` — fail-closed at `AgentTestHarness.__init__` |
| 2 | No real network egress | `block_network` fixture monkey-patches `socket.create_connection` |
| 3 | No real HoloIndex mutation | All retrieval via `MockHoloIndex` (in-memory) |
| 4 | Deterministic seeding | `redteam_seed` fixture, default `0xF00DC0DE` |
| 5 | `[SAFETY-EVENT]` observability | Every refusal emits a record AND a WARNING log; tests assert both |
| 6 | Time-bounded | `_enforce_test_timebound` autouse fixture, 5 s budget |
| 7 | Function-scoped fixtures | Default pytest scope — no cross-test state |

## Three-Part Assertion Shape (spec §3.5)

Every red-team test asserts at least:

1. **Behavioural outcome** — the attack did or did not succeed.
2. **Refusal reason code** — a stable `ReasonCode` enum value from
   `reasons.py`.
3. **Audit emission** — `audit_capture` contains a `[SAFETY-EVENT]` record
   naming the same reason code.

A test that asserts only the behavioural outcome is **not** a red-team test;
it is a unit test that happens to exercise a refusal path. Silent refusals
themselves count as a failure — that's a direct lesson from the work-ledger
silent-swallow regression (`FOUNDUPS_WORK_LEDGER_SEARCH_RETRIEVAL_PRIORITY_HOTFIX_PHASE1`).

## Files

```
redteam/
├── __init__.py
├── README.md                          (this file)
├── TestModLog.md                      WSP 22 change history
├── reasons.py                         ReasonCode enum + SAFETY_EVENT_PREFIX
├── conftest.py                        Fixtures + AgentTestHarness stub
├── scenarios/                         (Phase 3+ — YAML adversarial packs)
│   └── README.md
├── test_scope_lock_violation.py       Family A — SL-001
├── test_credential_exfiltration.py    Family B — CE-001 + invariant test
└── test_holoindex_poisoning.py        Family C — HP-001 + invariant test
```

## Running

```bash
python -m pytest modules/infrastructure/wre_core/tests/redteam/ -v
```

CI gate activation is **not** enabled in Phase 2. The suite is invocable
from the command line and from any selective pytest run; activation as a
blocking gate is deferred to
`FOUNDUPS_AGENT_REDTEAM_CI_GATE_ACTIVATION_PHASE1` (spec §9.5).

## No Self-Suppression (spec §6.3)

This suite must not be skippable from inside a PR. Specifically:

- No `--skip-redteam` flag, env var, or pytest option.
- No `@pytest.mark.skip` decorator may be added to a red-team test in a
  feature PR. Removal of a test requires a PR that updates the spec first.
- Disabling the suite at the CI level requires editing the workflow file
  itself, which lives outside this directory and is reviewed separately.

## Adding a Test

1. Confirm the new case ID is listed in the spec under §4. If not, the
   spec needs to be amended first.
2. Add the case to the appropriate `test_*.py` file using the three-part
   assertion shape from §3.5.
3. If the new case introduces a new refusal reason, add the value to
   `reasons.py` AND update the spec §4.
4. If the new case is **probabilistic**, follow spec §5 (default
   `redteam_seed`, binomial assertion, `[REDTEAM]` reporting line).
5. Update `TestModLog.md` with the new case ID and a one-line summary.

## What to Do When a Red-Team Test Fails

1. Treat it like a security incident, not a regression: the failure says
   the agent did something it shouldn't, *not* that the test is flaky.
2. Open `violations.md` per the spec §7 entry shape and record the failure.
3. Land the fix as a separate PR. Closure requires a regression test —
   spec §7.3 forbids closing without one.
