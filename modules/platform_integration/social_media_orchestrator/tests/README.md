# Social Media Orchestrator Tests

## Caller acknowledgement and reload characterization — 2026-09-28

PR1943 is merged and main-verified at `6821aac32774f5be36038bb3fb40cc55920a56cd`.
Its unchanged42 methods/48 inputs passed on final PR and main; independent
closure verified its exact tree, owned retirement and preserved peer state.

Fresh WSP15 C3/I4/D3/Impact4=14/P1 selects nine current-behavior cases in the
existing fixture. Three callers (`understand_command`, `execute_pending_actions`,
`cancel_action`) each receive normal publication, replacement failure, and
parent-sync failure after replacement. Production code remains unchanged.

Observe actual returns/identities, caller logs, statuses, exact primary file
bytes/hash and independent reload before any replay changes the file. Creation
uses the actual reminder/default +5-minute path with fixed UUID/time, preserving
an unrelated future reminder. Execution uses a coherent fake typed response.
Cancellation targets a due local reminder. Before-replace errors preserve old
state despite success-shaped caller returns; post-replace errors leave complete
new visible JSON with uncertain durability. These are characterization witnesses,
not a new persistence acknowledgement guarantee.

After fault release, the same instance performs no repeated action. A fresh
instance replays exactly one fake posting only for pre-replace execution failure,
or one local reminder for pre-replace cancellation failure. Creation stays future;
normal/post-replace terminal actions do not repeat. No real posting or clock advance.

Reuse the source-bound leaf/DTO loader, denied constructor, `_PersistenceFixture`
and real shared atomic writer. Writes remain under per-case disposable roots;
restore faults/cwd before removal. Scoped UUID and private writer patches are
sequential hosted effects, not a general async/concurrency guarantee. No host-local
application execution, accounts, provider, service or native dispatch is admitted.

Fixed selection:51 methods/57 finite inputs (42/48 unchanged plus9/9); eight legacy
bodies remain unchanged and unselected. Emit25 `PERSISTENCE_EVIDENCE` records and
nine `CALLER_EVIDENCE` records; preserve primary bytes before replay.

`python -I -B modules/platform_integration/social_media_orchestrator/tests/test_autonomous_scheduler.py TestExecutionEvidence TestPersistenceEvidence TestPublicationEvidence TestCallerPersistenceEvidence -v`

WSP62 cohesion review: the existing780-line fixture grows within the800–1000
guideline range, retaining one source loader, file fixture and caller boundary.
New helpers remain<=50lines and class<=200. No new test module, exemption or
threshold change. Reassess decomposition before further growth.

Authored fixture and exact hosted effects require independent review before
execution. Results are pending. Passing witnesses do not establish safe restart,
Windows/crash behavior, verified delivery, retained learning or native RSI.

## Historical scheduler safe-publication qualification — 2026-09-28

PR1942 closed the six-case persistence characterization on exact main
`12663d7e4f`. Its main CI36393612150 and CodeQL36393612401 passed;
the owned lane was preserved and retired. Four passing defect witnesses
confirmed typed-response serialization could truncate a synthetic schedule.

WSP15 C3/I4/D4/Impact4=15/P1 now selects the existing save owner. Freeze the
same26 completion methods/32 inputs, two persistence controls, four full-field
typed-result round trips and ten publication/compatibility cases:42 methods,
48 finite inputs. All eight legacy methods remain unchanged and unselected.
The unchanged production baseline is expected to fail the repaired contract.

Acceptance preserves all PostResponse fields, ordering and in-memory identities;
old JSON-compatible records; first saves; configured parent paths; rejection of
unsupported values before writing; old bytes through temporary write, file-sync
and replacement failure; and complete new JSON when parent-sync fails after
replacement. That last case does not establish crash durability.

The source-bound fixture loads the unchanged stdlib atomic writer with inert
package parents. Actual file operations stay beneath per-case scratch roots.
The fsync patch is process-wide only during one synchronous save in the named
sequential hosted process; patches/cwd are restored before scratch removal.
No local application execution, real posting, accounts or native admission.

Qualified selection after independent fixture/effect review:
`python -I -B modules/platform_integration/social_media_orchestrator/tests/test_autonomous_scheduler.py TestExecutionEvidence TestPersistenceEvidence TestPublicationEvidence -v`

Baseline `5d0da3625d` in [CI36401910480](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36401910480) ran42 methods:29 passed,13 failed with15 assertion failures,0 errors/skips. The identical fixture against candidate `8f36929dc0` in [CI36402439857](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36402439857) passed42/42 methods (48 finite inputs),0 failures/errors/skips; all16 file-evidence records were hash-checked. Candidate CI/CodeQL and all10 PR checks passed. Final reviewed-head/main checks and owned closure remain receipt-bound.

Save acknowledgement, concurrent writers,
restart retry safety, Windows behavior and native RSI remain separate.

## Historical scheduler persistence characterization — 2026-09-28

Extend the existing fixture with `TestPersistenceEvidence`: two positive controls
and four defect witnesses exercise actual `save_schedule`/`load_schedule` in
disposable directories. Production source and the 26 completion methods remain
unchanged; all eight legacy methods remain unselected.

| Fixed case | Required observation |
|---|---|
| Pending action control | Valid JSON, exact field/type round trip into a fresh instance |
| Executed reminder control | Valid terminal round trip; no repeat execution after reload |
| Complete typed posting response | Preserve response/status; record serialization error, invalid replacement bytes and failed fresh reload |
| Partial typed posting response | Preserve failed disposition and original response; same serialization/reload defect |
| All-failed typed posting response | Preserve failed disposition and original response; same serialization/reload defect |
| Typed response plus future action | Future action unchanged in memory; corrupted replacement prevents either record loading |

A passing defect witness confirms broken persistence in a synthetic file. It is
not a durability acceptance pass or evidence of production data loss/reposting.
The log emits six `PERSISTENCE_EVIDENCE` JSON records with exact synthetic before/
after bytes, hashes, save/load errors, memory status and restored IDs.

Only the independently reviewed named hosted process is qualified:

```bash
python -I -B modules/platform_integration/social_media_orchestrator/tests/test_autonomous_scheduler.py TestExecutionEvidence TestPersistenceEvidence -v
```

This selects 32 methods/38 fixed inputs (26/32 existing plus6/6 new). Inert
source-bound producer declarations, denied constructor and fake posting remain.
New effects are limited to `TemporaryDirectory`, sequential process-wide
`chdir`, and fixed `memory/schedule.json` beneath that scratch root. ExitStack
restores patches/cwd before scratch removal, with cleanup assertions. This is
not a generally concurrent async fixture. Host-local application tests and
whole-directory discovery remain unqualified; `-I -B` is not an OS sandbox.

Candidate `e8e06ea86f` passed all 32 methods / 38 fixed inputs in [CI36390957294](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36390957294), with zero failures/errors/skips. All six exact file-evidence records were verified: two valid controls and four serialization/reload defect witnesses. CI and CodeQL passed; final integrated-head and merged-main validation remain receipt-bound.

## In-memory completion repair — closed 2026-09-28

PR1936 closed the13 original behavior witnesses on PR and merged main. The same
`TestExecutionEvidence` now fixes26 test methods /32 input cases for the intended
repair: unsupported actions, complete/failed/partial/empty/malformed responses,
exact counter/platform coverage, invalid targets before effects, and target
mutation during a dependency call. Historical witness receipts remain in the
canonical RSI backlog; passing them was not evidence of successful posting.

This slice admits only the named hosted CI step after source/effect review.
Host-local application execution is not qualified. The exact hosted command is:

```bash
python -I -B modules/platform_integration/social_media_orchestrator/tests/test_autonomous_scheduler.py TestExecutionEvidence -v
```

The existing source-bound fixture loads actual producer enum/dataclass
declarations under a private module name, denies the posting constructor and
loads only the scheduler leaf. Awaited posting and save spies, fixed time and
in-memory actions exclude accounts, browsers, providers and real persistence.
The existing CI step `Run social scheduler execution evidence` is unchanged.
Baseline CI36379506634 reproduced21 failing methods/27 assertion failures and
5 passing controls (0 errors/skips). The same frozen fixture will judge the repair;
candidate `9bc31ed6e0` passes all 26 methods/32 inputs in CI36380266749
(0 failures/errors/skips). PR1941 is merged/main-verified at `6acb3f55c2`: the frozen26 methods/32 inputs passed on final PR CI36380808132 and main CI36381188667; both CodeQL runs passed. Its owned branch/worktree were retired after recovery preservation. Finite variants are not extra independent test methods.

The eight `TestAutonomousActionScheduler` methods are preserved historical tests
and remain unselected/unqualified. Direct execution defaults to the isolated class.
Result identity is preserved even on failure; durable serialization, restart
replay, actual delivery verification and retained RSI require separate evidence.

## Historical inventory and commands

The inventory below is historical: several flat filenames no longer exist, and
the directory mixes offline tests with live integration scripts. It is not a
current safe collection list. Use the exact qualified command above for this
slice; do not infer that `TEST_MODE=True` isolates the other scripts.

## Test Structure

### Unit Tests
- `test_orchestrator.py` - Core orchestrator functionality
- `test_oauth_coordinator.py` - OAuth management tests
- `test_content_orchestrator.py` - Content formatting tests
- `test_scheduling_engine.py` - Scheduling functionality tests
- `test_twitter_adapter.py` - Twitter platform adapter tests
- `test_linkedin_adapter.py` - LinkedIn platform adapter tests

### Integration Tests
- `test_integration.py` - Cross-component integration tests
- `test_hello_world.py` - Platform hello world tests

### Vision-Based Engagement Tests (WSP 77 Phase 3: Human Supervision)
- `test_autonomous_with_validation.py` - Post-action validation: AI executes → 012 validates → Pattern Memory learns
- `test_copilot_validation.py` - Pre-action validation: AI announces intent → 012 confirms → AI executes
- `test_live_engagement_existing_chrome.py` - YouTube engagement using existing Chrome on port 9222
- `test_ui_tars_studio.py` - UI-TARS Desktop integration for YouTube Studio engagement
- `test_ui_tars_no_nav.py` - UI-TARS Desktop engagement without navigation

### Performance Tests
- `test_performance.py` - Load and performance testing

## Running Tests

### Individual Test Files
```bash
# Run specific test file
python -m pytest tests/test_orchestrator.py -v

# Run with coverage
python -m pytest tests/test_orchestrator.py --cov=src --cov-report=html
```

### Historical whole-directory command (not qualified by this slice)
```bash
# Run all tests
python -m pytest tests/ -v

# Run with detailed output
python -m pytest tests/ -v --tb=short
```

### Historical Hello World command (execution effects not qualified here)
```bash
# Run hello world tests in dry-run mode (no actual posting)
python tests/test_hello_world.py
```

## Test Configuration

Tests use environment variables for configuration:

```bash
# Optional: Real credentials for integration testing
export TWITTER_BEARER_TOKEN="your_token"
export LINKEDIN_CLIENT_ID="your_client_id"
export LINKEDIN_CLIENT_SECRET="your_secret"
export LINKEDIN_ACCESS_TOKEN="your_token"

# Test mode (default: True for safety)
export TEST_MODE="True"
```

## WSP Compliance

All tests follow WSP 49 (Module Directory Structure) and WSP 22 (ModLog Documentation) standards.

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **Hello World Tests**: Safe platform connectivity tests
4. **Performance Tests**: Load and stress testing

### Safety Measures

- All tests default to dry-run mode
- Real API calls only when explicitly enabled
- Comprehensive mocking for external dependencies
- Rate limiting awareness in all test scenarios
