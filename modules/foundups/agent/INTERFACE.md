# Agent Module Interface

Public API and schema contracts for agent lifecycle management, BuildPlan generation, and controlled execution.

## BuildPlan Pipeline (OC8/OC9/OC12)

### Core Dataclasses

```python
# modules/foundups/agent/src/build_plan.py
BuildPlan        # Multi-step orchestration contract
BuildTarget      # Target paths and scope
BuildStep        # Step definition with action enum
BuildGate        # Gate checkpoints (genesis, dry_run, human_approval)
BuildEvidence    # Evidence reference with verification status
```

### BuildPlan Generator

```python
# modules/foundups/agent/src/build_plan_generator.py
def create_build_plan_from_job(job: FoundUpJob) -> BuildPlan:
    """Generate BuildPlan from FoundUpJob. Always produces dry_run=True plans."""

def can_generate_build_plan(job: FoundUpJob) -> bool:
    """Check if job can generate a BuildPlan."""
```

### BuildPlan Executor (Interface Stub)

```python
# modules/foundups/agent/src/build_plan_executor.py
class BuildPlanExecutor:
    """Controlled step execution. Real execution NOT implemented."""
    
    def __init__(self, dry_run: bool = True): ...
    def validate_plan(self, plan: BuildPlan) -> ValidationResult: ...
    def evaluate_gate(self, plan: BuildPlan, gate_type: GateType) -> GateEvaluationResult: ...
    def simulate_step(self, plan: BuildPlan, step: BuildStep) -> StepExecutionResult: ...
    def execute_step(self, plan: BuildPlan, step: BuildStep) -> StepExecutionResult: ...
    def create_execution_receipt(self, plan: BuildPlan, results: List[StepExecutionResult]) -> ExecutionReceipt: ...

# Execution Result Types
StepExecutionStatus  # SUCCEEDED | FAILED | BLOCKED | SKIPPED | SIMULATED
ExecutionReceipt     # Terminal receipt with WSP 97 truth fields
```

### WSP 97 Truth Fields

ExecutionReceipt enforces these fields as False always:
- `verification_complete = False`
- `cabr_ready = False`
- `payout_ready = False`
- `real_execution_performed = False`

---

## Event Schemas

### agent_joins

Emitted when agent enters the ecosystem in dormant 01(02) state.

```python
{
    "event_type": "agent_joins",
    "actor_id": "founder_001",           # Unique agent identifier
    "foundup_id": "F_0",                 # FoundUp context (F_0 = ecosystem-level)
    "payload": {
        "agent_type": "founder",         # founder | user
        "public_key": "0xfoundup001...", # Wallet address
        "rank": 1,                       # Initial rank (1=Apprentice)
        "state": "01(02)",               # Dormant until awakened
        "foundup_idx": 0,                # FoundUp index for display
    }
}
```

### agent_awakened

Emitted when agent transitions to 0102 zen state (coherence >= 0.618).

```python
{
    "event_type": "agent_awakened",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "coherence": 0.72,               # Coherence score (0.618-1.0)
        "state": "0102",                 # Zen state - active
    }
}
```

### agent_idle

Emitted when agent decays to 01/02 state (inactivity or coherence drop).

```python
{
    "event_type": "agent_idle",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "inactive_ticks": 150,           # Ticks since last activity
        "current_tick": 1000,            # Current simulation tick
        "state": "01/02",                # Decayed - awaiting ORCH
    }
}
```

### agent_ranked

Emitted when agent rank increases.

```python
{
    "event_type": "agent_ranked",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "old_rank": 2,                   # Previous rank (1-7)
        "new_rank": 3,                   # New rank (1-7)
        "old_title": "Builder",          # Previous title
        "new_title": "Contributor",      # New title
    }
}
```

### agent_earned

Emitted when agent receives F_i payout.

```python
{
    "event_type": "agent_earned",
    "actor_id": "founder_001",
    "foundup_id": "F_001",
    "task_id": "task_0042",
    "payload": {
        "amount": 50,                    # F_i tokens earned
        "foundup_idx": 1,                # FoundUp index
        "task_id": "task_0042",          # Task context
    }
}
```

### agent_leaves

Emitted when agent logs off with wallet balance.

```python
{
    "event_type": "agent_leaves",
    "actor_id": "founder_001",
    "foundup_id": "F_0",
    "payload": {
        "public_key": "0xfoundup001...", # Wallet address
        "wallet_balance": 1250.0,        # Final F_i balance
    }
}
```

## State Transitions

### Valid Transitions

```
01(02) → 0102   # agent_awakened (coherence >= 0.618)
0102 → 01/02    # agent_idle (inactivity > threshold OR coherence < 0.618)
01/02 → 0102    # agent_awakened (re-awakening via WSP_00)
```

### Coherence Thresholds

| Threshold | Meaning |
|-----------|---------|
| 0.618 | Minimum for 0102 zen state (golden ratio) |
| 0.50 | Minimum for any activity |
| < 0.50 | Cannot perform actions |

## Dedupe Keys

Each event type has a unique dedupe key pattern:

```
agent_joins:    agent_joins:{agent_id}:{foundup_id}
agent_awakened: agent_awakened:{agent_id}:{timestamp[:19]}
agent_idle:     agent_idle:{agent_id}:{tick // 100}
agent_ranked:   agent_ranked:{agent_id}:{new_rank}
agent_earned:   agent_earned:{agent_id}:{task_id}
agent_leaves:   agent_leaves:{agent_id}:{timestamp[:19]}
```

## Service Boundaries

### AgentLifecycleService (Future)

```python
class AgentLifecycleService:
    """Manage agent state transitions."""

    def join(self, agent_id: str, agent_type: str, public_key: str) -> None:
        """Register agent in 01(02) dormant state."""

    def awaken(self, agent_id: str) -> bool:
        """Transition to 0102 zen state if coherence >= 0.618."""

    def mark_idle(self, agent_id: str, inactive_ticks: int) -> None:
        """Transition to 01/02 decayed state."""

    def rank_up(self, agent_id: str) -> int:
        """Evaluate and update agent rank. Returns new rank."""

    def leave(self, agent_id: str) -> float:
        """Log off agent and return final wallet balance."""

    def get_state(self, agent_id: str) -> str:
        """Return current state: '01(02)', '0102', or '01/02'."""
```

## Integration

### FAMBridge Methods

```python
# In modules/foundups/simulator/adapters/fam_bridge.py
emit_agent_joins(agent_id, agent_type, foundup_id, public_key, rank)
emit_agent_awakened(agent_id, coherence, foundup_id)
emit_agent_idle(agent_id, foundup_id, inactive_ticks, current_tick)
emit_agent_ranked(agent_id, old_rank, new_rank, foundup_id)
emit_agent_earned(agent_id, foundup_id, amount, task_id)
emit_agent_leaves(agent_id, wallet_balance, public_key, foundup_id)
```

### SSE Streaming

Events are streamed via `STREAMABLE_EVENT_TYPES` in `sse_server.py`:

```python
"agent_joins", "agent_awakened", "agent_idle",
"agent_ranked", "agent_earned", "agent_leaves",
```

### Animation Display

Ticker messages in `foundup-cube.js`:

```javascript
agent_joins:    "01(02) 0xfound001... enters (founder)"
agent_awakened: "0102 founder_001 ZEN (0.72)"
agent_idle:     "01/02 founder_001 IDLE (150 ticks)"
agent_ranked:   "founder_001 rank UP: 2→3 (Contributor)"
agent_earned:   "founder_001 earned 50 F₁"
agent_leaves:   "0xfound001... logs off (1250 F_i)"
```
