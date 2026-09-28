# GitPushDAE Test Suite

## Runner entrypoint evidence — 2026-09-28

Existing owner: `test_post_commit_social_runner.py`. The three original pytest
functions remain source-identical. The named hosted selection adds six unittest
controls; it does not count the original three as freshly executed.

```sh
python -I -B modules/infrastructure/git_push_dae/tests/test_post_commit_social_runner.py TestEntrypointEvidence -v
```

| Fixed case | Exit | Event/result rows | Router import / constructor / handoff |
|---|---:|---:|---:|
| Missing root, default | 1 | 1 / 1 error | 1 / 0 / 0 |
| Missing root, enqueue-only | 0 | 1 / 0 | 0 / 0 / 0 |
| Inert router, default | 0 | 1 / 1 fake result | 1 / 1 / 1 |
| Inert router, enqueue-only | 0 | 1 / 0 | 0 / 0 / 0 |
| Inert router failure | 1 | 1 / 1 error | 1 / 1 / 1 |
| Unsupported `--dispatch-direct` | 2 | 0 / 0 | 0 / 0 / 0 |

Each case creates two commits in a disposable repository. Hooks/templates,
global/system Git configuration, signing and credential helpers are disabled;
All Git commands are local. Setup/check commands each have a 10s timeout. The
unchanged production context collector has no per-command timeout; its nested
Git reads are enclosed by the isolated child's 30s timeout. The child has
controlled argv/environment/cwd and records its actual `sys.path`, argv and
source hash.
It first requires the application package to be absent. Missing-root controls
then preserve the natural import failure; positive controls inject only inert
modules with empty search paths before running the unchanged getter.

The real parser/main/context collector and JSONL writer are exercised. Assertions
check exact fixture metadata, dedupe/payload correlation, import/constructor/call
counts, exit codes, expected-only spool files and temporary cleanup. Each passing
case emits one `HOOK_EVIDENCE` record with the child-observed source hash,
expected synthetic payload and exact JSONL text/digests for independent review. The fake
result says `delivered=false`; exit0 is not verified social delivery.

Candidate `5935983ef8` passed **6/6** fixed methods, zero failures/errors/skips, in 1.11s in [CI36424604965](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36424604965). All six original `HOOK_EVIDENCE` records, child-source/argv bindings and synthetic JSONL hashes/payloads were independently checked. All ten PR checks and CI/CodeQL passed.

Final-head/main checks remain required. This is restricted hosted entrypoint evidence, not the
ambient Windows shell hook, production router dependencies, durable crash recovery,
spool replay, native work admission or retained learning. No real hook is run.

Current inventory: `test_git_push_dae.py` covers daemon decisions/logging;
`test_launch_runtime.py` covers runtime stop/lifecycle adapters; this file covers
normalized events, spooling, mocked dispatch and the six bounded entrypoint cases.
Do not launch the whole module suite as a substitute for the named effect review.

## Test Strategy

The GitPushDAE test suite focuses on validating autonomous decision-making and WSP 91 observability compliance. Tests are designed to ensure the daemon makes correct push decisions based on agentic parameters without human intervention.

## Test Categories

### Unit Tests
- **Decision Logic**: Validate agentic parameter evaluation
- **Cost Tracking**: Verify WSP 91 cost observability
- **Circuit Breaker**: Test resilience patterns
- **State Persistence**: Ensure atomic state management

### Integration Tests
- **Git Bridge Integration**: Test social media posting
- **Health Monitoring**: Validate WSP 91 health checks
- **Lifecycle Management**: Test daemon start/stop cycles

### End-to-End Tests
- **Full Daemon Operation**: Complete autonomous cycles
- **Decision Path Logging**: Verify WSP 91 observability
- **Error Recovery**: Test failure scenarios and recovery

## Agentic Parameters Under Test

### Primary Criteria
1. **Code Quality**: `quality_score >= 0.8`
2. **Change Significance**: `len(changes) >= 3`
3. **Time Windows**: Sleep hour avoidance (22:00-06:00)
4. **Frequency Control**: `time_since_last >= 1800s`

### Secondary Criteria
5. **Social Value**: `social_value_score >= 0.6`
6. **Repository Health**: No conflicts, clean state
7. **Cost Efficiency**: Benefit vs. analysis cost

## Test Data

### Mock Scenarios
- **High-Quality Push**: All criteria pass, expect push
- **Quality Gate Fail**: Code quality too low, expect wait
- **Time Window Block**: Sleep hours, expect wait
- **Spam Prevention**: Too frequent, expect wait

### Edge Cases
- **Empty Repository**: No changes, expect no action
- **Conflict State**: Merge conflicts, expect no push
- **Circuit Breaker**: API failures, expect graceful degradation
- **Cost Limits**: Budget exceeded, expect reduced operation

## Running Tests

```bash
# Run all tests
pytest modules/infrastructure/git_push_dae/tests/

# Run with coverage
pytest --cov=modules/infrastructure/git_push_dae/src/ modules/infrastructure/git_push_dae/tests/

# Run specific test category
pytest -k "decision" modules/infrastructure/git_push_dae/tests/
```

## Expected Behavior

### Autonomous Operation
- **Zero Human Intervention**: All decisions based on objective criteria
- **Consistent Reasoning**: Same inputs produce same decisions
- **Observable Decisions**: Full WSP 91 decision path logging

### Resilience
- **Graceful Degradation**: Circuit breaker prevents cascade failures
- **State Persistence**: Survives restarts without losing context
- **Error Recovery**: Automatic retry with exponential backoff

### Cost Efficiency
- **Token Awareness**: Operations respect budget constraints
- **Value-Driven**: Only pushes when benefits outweigh costs
- **Transparent Tracking**: All costs logged per WSP 91

## Test Metrics

### Coverage Targets
- **Statement Coverage**: >90%
- **Branch Coverage**: >85%
- **Decision Path Coverage**: All agentic criteria combinations

### Performance Benchmarks
- **Decision Latency**: <500ms per decision cycle
- **Memory Usage**: <100MB during operation
- **Log Volume**: Reasonable observability without spam

## Integration Requirements

### External Dependencies
- **Git Repository**: Local repo for testing push operations
- **Mock APIs**: Simulated social media APIs for integration tests
- **Time Control**: Ability to mock system time for time-window tests

### Test Environment
- **Isolated**: Each test runs in clean environment
- **Deterministic**: Same inputs produce same outputs
- **Fast**: Tests complete in <30 seconds total

## Future Test Enhancements

### Phase 2: Advanced Scenarios
- **Multi-Repository**: Test daemon managing multiple repos
- **Collaborative Decisions**: Test daemon coordination
- **Dynamic Criteria**: Test parameter learning and adaptation

### Phase 3: Production Validation
- **Load Testing**: High-frequency change scenarios
- **Longevity Testing**: 24/7 operation simulation
- **Chaos Engineering**: Random failure injection and recovery

### Phase 4: LLM Integration Testing
- **Quality Assessment**: LLM-based code quality evaluation
- **Social Value Prediction**: LLM-based content value assessment
- **Reasoning Validation**: LLM-based decision reasoning verification
