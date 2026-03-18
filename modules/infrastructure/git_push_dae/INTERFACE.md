# GitPushDAE Interface Documentation

## Public API

### GitPushDAE Class

```python
class GitPushDAE:
    """WSP 91 compliant DAEMON for autonomous git push decisions."""

    def __init__(self, domain: str, check_interval: int = 300):
        """
        Initialize GitPushDAE daemon.

        Args:
            domain: Monitoring domain (e.g., 'foundups_development')
            check_interval: Seconds between monitoring cycles (default: 300)
        """

    def start(self) -> None:
        """Start the autonomous monitoring daemon with WSP 91 logging."""

    def stop(self) -> None:
        """Stop the daemon with full lifecycle logging."""

    def health_check(self) -> HealthStatus:
        """WSP 91 compliant health check."""

    def make_push_decision(self, context: PushContext) -> PushDecision:
        """Make autonomous push decision with full observability."""

    def monitoring_cycle(self) -> None:
        """Main monitoring logic - checks for push-worthy changes."""
```

### Data Structures

```python
@dataclass
class PushContext:
    """Context for autonomous push decision."""
    uncommitted_changes: List[str]
    quality_score: float
    time_since_last_push: int
    social_value_score: float
    repository_health: str

@dataclass
class PushDecision:
    """Autonomous push decision result."""
    should_push: bool
    confidence: float
    reasoning: str
    expected_impact: str
    cost_estimate: float
    alternatives_considered: List[Dict]

@dataclass
class HealthStatus:
    """WSP 91 health status."""
    daemon_name: str
    status: str  # 'healthy', 'degraded', 'critical', 'failed'
    vital_signs: Dict
    anomalies: List[str]
    recommendations: List[str]
```

### Broker-Managed Runtime Hooks

```python
from modules.infrastructure.git_push_dae.scripts.launch import (
    launch_git_push_dae,
    stop_git_push_dae,
)

launch_git_push_dae(run_once=False)
stop_git_push_dae()  # -> {"status": "stopping"} | {"status": "not_running"}
```

Runtime contract:
- `main.py` registers `git_push_dae` with `stop_callable=stop_git_push_dae`
- generic DAE runtime commands can now stop the broker-managed GitPushDAE honestly

## Agentic Parameters

### Push Decision Criteria (Autonomous)

1. **Code Quality Threshold**: `quality_score >= 0.5`
   - Development quality is iterative - not perfect upfront
   - Encourages frequent progress sharing over perfection

2. **Change Significance**: `len(uncommitted_changes) >= 3`
   - Minimum 3 changed files to warrant push

3. **Time Windows**: Respect deep sleep hours only
   - No pushes between 02:00-06:00 local time
   - Evening coding (22:00-02:00) is prime development time

4. **Frequency Control**: `time_since_last_push >= 1800` (30 minutes)
   - Prevent spam pushes

5. **Social Value**: `social_value_score >= 0.6`
   - Content valuable for LinkedIn/X audience

6. **Repository Health**: Accept "dirty" state during development
   - BLOCKED: "conflicts" (must resolve)
   - ACCEPTABLE: "dirty" (active development)
   - ACCEPTABLE: "clean" (no uncommitted changes)

7. **Cost Efficiency**: Push value vs analysis cost

### Error Handling

- **Retry Logic**: Failed pushes retried with exponential backoff
- **Circuit Breaker**: Stop posting if social media APIs fail repeatedly
- **Fallback Mode**: Continue monitoring even if social posting fails

## Parameter Specifications

### Constructor Parameters

- **domain**: `str` - Monitoring domain identifier
- **check_interval**: `int` - Monitoring cycle interval in seconds (default: 300)

### Return Value Documentation

- **PushDecision.should_push**: `bool` - Whether to execute git push
- **PushDecision.confidence**: `float` 0.0-1.0 - Decision confidence level
- **PushDecision.cost_estimate**: `float` - Estimated token cost in USD

### Error Handling

- **GitPushDAEError**: Base exception for daemon errors
- **QualityAssessmentError**: Quality check failures
- **SocialMediaError**: Posting failures (non-blocking)

## Examples

### Basic Usage
```python
from modules.infrastructure.git_push_dae.src.git_push_dae import GitPushDAE

# Launch autonomous daemon
dae = GitPushDAE(domain="foundups_development")
dae.start()

# Daemon runs indefinitely with full WSP 91 observability
```

### Custom Configuration
```python
# Custom monitoring interval
dae = GitPushDAE(
    domain="foundups_development",
    check_interval=600  # 10-minute checks
)
```

## AI Overseer Integration (WSP 77)

### Activity Routing

GitPushDAE is wired to AI Overseer's activity routing system as `MissionType.GIT_PUSH` with **P2 priority** (MPS score: 12).

```python
from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer

overseer = AIIntelligenceOverseer(repo_root)

# Check if git push is needed
git_status = overseer.check_git_status()
# Returns: {"staged_files": 5, "modified_files": 10, "untracked_files": 3}

# Route based on system state (will return GIT_PUSH if staged files exist)
routing = overseer.route_activity()
# Returns: {"next_activity": MissionType.GIT_PUSH, "mps_score": 12, ...}

# Execute git push activity (creates mission for skill coordination)
result = overseer.execute_git_push_activity(dry_run=False)
```

### Skill Wiring: qwen_gitpush

The `qwen_gitpush` skill provides Qwen/Gemma AI analysis for autonomous commit decisions:

**Skill Path**: `modules/infrastructure/git_push_dae/skillz/qwen_gitpush/SKILLz.md`

**Chain of Thought (4 Steps)**:
1. **Analyze Git Diff** (Qwen Strategic Analysis)
2. **Calculate WSP 15 MPS Score** (Custom Scoring)
3. **Generate Semantic Commit Message** (Qwen Generation)
4. **Decide Push Action** (Threshold Logic)

**Integration Pattern**:
```python
# AI Overseer creates mission with skill context
mission = overseer.create_mission(
    mission_type=MissionType.GIT_PUSH,
    context={
        "staged_files": git_status["staged_files"],
        "skill_path": "modules/infrastructure/git_push_dae/skillz/qwen_gitpush/SKILLz.md"
    },
    expected_outputs=["commit_hash", "commit_message", "pr_url"]
)

# WRE Core routes to qwen_gitpush skill for analysis
# Skill returns: action (push_now/defer), commit_message, mps_score

# GitPushDAE executes pre-analyzed commit
gitpush_dae.execute_from_skill(
    commit_message=skill_result.commit_message,
    mps_score=skill_result.mps_score,
    skip_analysis=True  # Qwen already analyzed
)
```

### Activity State Detection

AI Overseer detects git push needs via:

1. **Direct git status check**: `overseer.check_git_status()`
2. **Daemon signal detection**: Patterns like `"git_staged"`, `"files_changed"`

```python
# State detection for activity routing
state = {
    "is_live": False,           # P0: Live stream override
    "unprocessed_comments": 0,  # P1: Comments pending
    "all_processed": True,      # Comments cleared signal
    "schedule_queue": 0,        # P2: Scheduling queue
    "git_staged_files": 5,      # P2: Files ready for commit
    "social_queue": 0,          # P3: Social media pending
    "maintenance_due": False    # P4: System maintenance
}

# Activity routing will return GIT_PUSH for this state
next_activity = overseer.get_next_activity(state)
# Returns: MissionType.GIT_PUSH (P2 priority, staged files detected)
```

### WSP 77 Agent Coordination

Git push operations follow WSP 77 agent coordination:

| Phase | Agent | Role | Git Push Action |
|-------|-------|------|-----------------|
| 1 | Gemma | Associate | Validate diff format, check patterns |
| 2 | Qwen | Partner | Analyze changes, calculate MPS, generate message |
| 3 | 0102 | Principal | Approve/override push decision |
| 4 | Learning | - | Store pattern outcomes for future optimization |

### Autonomous Push Protocol

For fully autonomous operation (0102 executing full push cycle):

```python
# Full autonomous push cycle via AI Overseer
async def autonomous_push_cycle():
    overseer = AIIntelligenceOverseer(repo_root)

    # 1. Check activity routing
    routing = overseer.route_activity()

    if routing["next_activity"] == MissionType.GIT_PUSH:
        # 2. Execute git push with skill analysis
        result = await overseer.execute_git_push_activity()

        # 3. If branch protection, auto-create PR
        if result.get("needs_pr"):
            await overseer.create_pr_mission(
                branch=result["branch"],
                title=result["commit_message"].split("\n")[0]
            )

        return result

    return {"skipped": True, "reason": "No staged files"}
```

### Module-by-Module Batching

For WSP-aligned commits per module:

```python
# Batch commits by module domain
MODULE_BATCHES = {
    "youtube-scheduler": "modules/platform_integration/youtube_shorts_scheduler/**",
    "ai-overseer": "modules/ai_intelligence/ai_overseer/**",
    "video-indexer": "modules/ai_intelligence/video_indexer/**",
    "livechat": "modules/communication/livechat/**",
    "video-comments": "modules/communication/video_comments/**",
    "infrastructure": "modules/infrastructure/**",
    "holo-index": "holo_index/**",
    "wsp-docs": "WSP_framework/**"
}

# Each batch gets its own commit with semantic message
for batch_name, pattern in MODULE_BATCHES.items():
    staged = stage_by_pattern(pattern)
    if staged > 0:
        overseer.execute_git_push_activity(batch=batch_name)
```
