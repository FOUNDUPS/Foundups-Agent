# Agent Module Tests

## Test Strategy

Tests cover two surfaces:

- Hermes FoundUp Builder dry-run and boundary gates.
- Planned agent lifecycle state transitions per the 01(02) -> 0102 -> 01/02 state machine.

## Implemented Test Coverage

### Worker Queue Observability

`test_worker_queue_observability.py` verifies:

1. emit_event stores append-only event
2. emit_heartbeat creates heartbeat event with consecutive tracking
3. emit_lease_expired creates lease expiry signal
4. worker availability/unavailability events are recorded
5. snapshot_queue_health reports queued/processing/completed/expired counts
6. get_events filters by worker_id
7. event fields preserve evidence_refs
8. all observability is in-memory only
9. no real worker/process fields imply execution
10. no CABR/reward/payout/token fields exist

### Swarm Dispatch Integration

`test_swarm_dispatch_integration.py` verifies:

1. dispatch_next dequeues matching queue entry and dispatches simulated assignment
2. dispatch_next returns blocked/no-match for wrong capability
3. complete_dispatched_assignment records evidence in queue and dispatcher
4. run_simulated_cycle performs dequeue -> dispatch -> complete
5. multiple workers can process different assignments without file conflicts
6. summary reports all_simulated=True and real_execution_performed=False
7. VoteBallot swarm queue can run one simulated dispatch cycle

### Worker Assignment Protocol

`test_worker_assignment_protocol.py` verifies:

1. register_worker creates tracked worker process
2. register_worker records runtime type and capabilities
3. dispatch_assignment returns simulated/not-implemented status
4. dispatch_assignment does not start process
5. heartbeat updates worker last_seen
6. completion event records evidence_refs
7. deregistration changes status
8. no CABR/reward/payout/token fields exist
9. all WSP_97 truth fields remain false/simulated

### Swarm WRE Queue

`test_build_plan_swarm_queue.py` verifies:

1. Create queue entry from StepAssignment
2. Dequeue matching worker capability succeeds
3. Dequeue mismatched worker capability is blocked
4. Heartbeat renews lease
5. Completion report marks entry complete with evidence
6. Expired entry can be requeued
7. Simulated completion cannot set real_execution_performed=True
8. Queue entry has no CABR/reward/payout/token fields
9. VoteBallot swarm assignment can be enqueued and dequeued by simulated worker

### Swarm Coordination

`test_build_plan_swarm.py` verifies:

1. Register multiple workers
2. Assign different steps to different workers
3. Block duplicate file claims
4. Allow release then re-claim
5. Expire lease releases claim
6. Reject out-of-scope file claim
7. Aggregate evidence from multiple assignments
8. Summary reports simulated-only execution
9. No real_execution_performed field can become true
10. VoteBallot BuildPlan can be split into multiple simulated assignments

### Hermes FoundUp Builder

`test_hermes_foundup_builder.py` verifies:

- Builder initialization when optional FAM dependencies are unavailable.
- Boundary analysis shape and blocker reporting.
- Exfoliation gate checks for contracts, tests, deploy surface, adapter-level dependencies, and Claw participation.
- Deploy surface evidence from `firebase.json`, `app/index.html`, `frontend/index.html`, or `foundup_manifest.json` with `entry_url` and `launch_readiness=ready`.
- Deterministic manifest signing.
- Adapter generation in dry-run mode without writing files.
- `extract_foundup()` dry-run success and failure paths.
- Read-only assertions against real GotJunk and Kosei modules.

## Planned Test Coverage

### State Transition Tests

```python
def test_agent_joins_in_dormant_state():
    """New agent enters in 01(02) dormant state."""

def test_agent_awakens_on_first_action():
    """Agent transitions to 0102 on first successful action."""

def test_agent_becomes_idle_after_threshold():
    """Agent transitions to 01/02 after inactivity threshold."""

def test_idle_agent_can_reawaken():
    """01/02 agent can transition back to 0102."""

def test_coherence_threshold_enforced():
    """Agent cannot awaken with coherence < 0.618."""
```

### Rank Progression Tests

```python
def test_rank_progression_on_earnings():
    """Agent ranks up when earnings exceed thresholds."""

def test_rank_cannot_decrease():
    """Agent rank never decreases once achieved."""

def test_rank_7_is_maximum():
    """Agent cannot exceed rank 7 (Principal)."""
```

### Event Emission Tests

```python
def test_agent_joins_emits_event():
    """FAMDaemon receives agent_joins event."""

def test_agent_awakened_emits_event():
    """FAMDaemon receives agent_awakened event."""

def test_agent_idle_emits_event():
    """FAMDaemon receives agent_idle event."""

def test_agent_ranked_emits_event():
    """FAMDaemon receives agent_ranked event."""

def test_agent_leaves_emits_event():
    """FAMDaemon receives agent_leaves event."""
```

### Dedupe Key Tests

```python
def test_agent_joins_dedupe_key():
    """Duplicate joins are deduplicated."""

def test_idle_events_windowed():
    """Only one idle event per 100-tick window."""
```

## Running Tests

```bash
# From project root
python -m pytest modules/foundups/agent/tests/ -v

# Focused Hermes builder check
python -m pytest modules/foundups/agent/tests/test_hermes_foundup_builder.py -q

# With coverage
python -m pytest modules/foundups/agent/tests/ --cov=modules.foundups.agent
```

## Test Fixtures

```python
@pytest.fixture
def mock_daemon():
    """FAMDaemon mock for event capture."""
    return MockFAMDaemon()

@pytest.fixture
def agent_lifecycle_service(mock_daemon):
    """AgentLifecycleService with mock daemon."""
    return AgentLifecycleService(daemon=mock_daemon)
```

## Status

- Hermes builder tests: Implemented
- Agent lifecycle tests: Planned (Phase 1)
- Coverage Target: 80%
