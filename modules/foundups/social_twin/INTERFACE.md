# Social Twin FoundUp Interface

## Purpose
Define the public contracts for the `social_twin` FoundUp.

## Core Roles

### `orchestrator_0102`
- mutation authority: no direct platform mutation
- responsibilities:
  - scan candidates
  - rank queue
  - choose recommended voice/entity
  - prepare review packets
  - collect approval decisions

### `engager_0102`
- mutation authority: yes, bounded by approval
- responsibilities:
  - execute approved replies
  - execute likes/reposts/schedules
  - capture outcomes and failures

### `amplifier_0102`
- mutation authority: optional and derived from parent approval
- responsibilities:
  - secondary likes
  - repost scheduling
  - follow-up checks

## Queue State Machine

```text
scanned -> ranked -> queued -> discussed -> drafted -> approved
approved -> executing -> executed -> amplified -> followup_scheduled -> closed
approved -> rejected
executing -> failed
```

## Public Contracts

```python
class SocialTwinRole(str, Enum):
    ORCHESTRATOR = "orchestrator_0102"
    ENGAGER = "engager_0102"
    AMPLIFIER = "amplifier_0102"

class QueueStatus(str, Enum):
    SCANNED = "scanned"
    RANKED = "ranked"
    QUEUED = "queued"
    DISCUSSED = "discussed"
    DRAFTED = "drafted"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    AMPLIFIED = "amplified"
    FOLLOWUP_SCHEDULED = "followup_scheduled"
    CLOSED = "closed"
    REJECTED = "rejected"
    FAILED = "failed"
```

```python
@dataclass(frozen=True)
class RoleAssignment:
    role: SocialTwinRole
    runtime: str
    model_policy: str
    mutation_allowed: bool

@dataclass
class OpportunityCandidate:
    platform: str
    source_post_id: str
    author: str
    source_url: str
    source_text: str
    alignment_keys: List[str]
    score: float
    ranking_reasons: List[str]
    recommended_voice: str
    recommended_entity: Optional[str]
    status: QueueStatus = QueueStatus.SCANNED

@dataclass
class MorningReviewPacket:
    queue_id: str
    reviewer_channel: str
    items: List[OpportunityCandidate]

@dataclass(frozen=True)
class SocialTwinTopology:
    foundup_id: str
    orchestrator: RoleAssignment
    engager: RoleAssignment
    amplifier: Optional[RoleAssignment] = None
    approval_required: bool = True
```

## Execution Boundary
- `social_twin` does not replace platform-specific executors.
- It routes approved actions into existing executors.
- LinkedIn is the first execution surface.

## Review Surface Contract
Expected first commands:
- `next`
- `skip`
- `rewrite`
- `approve`
- `reply as <entity>`
- `followup 5d`
- `followup 7d`

## Current Limits
- phone-based control is feasible through Discord/Telegram
- voice walking mode is not yet a remote production path
- direct browser extension is deferred until queue/review/execute is stable
