# GitHub Orchestrator

**Location**: `modules/infrastructure/github_orchestrator/`
**WSP Compliance**: WSP 103 (FoundUp Federation), WSP 77 (Agent Coordination), WSP 49 (Module Structure)
**Status**: PoC

## Purpose

The GitHub Orchestrator enables **0102 to MANAGE** (not just participate in) GitHub organization resources:
- Projects (create, assign, move cards)
- Issues (create, close, label)
- Repos (create, configure, manage access)
- Teams (manage membership for Access DAE)
- Milestones (track releases)

**Key principle**: 0102 is the orchestrator, not a participant.

## Architecture

```
         012 (Observer)
              │
              ▼
    ┌─────────────────────┐
    │  GitHub Orchestrator │  ← THIS MODULE
    │  (0102 Manager)      │
    └─────────────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
  GitHub API      FAM DAEmon
  (Projects,      (Event sync)
   Issues, etc.)
```

## Capabilities

### Project Management
```python
await orchestrator.create_project_item(
    project_id="PVT_xxx",
    title="Implement WSP 103",
    body="Federation protocol implementation",
    assignee="0102-session-abc"
)

await orchestrator.move_card(
    item_id="PVTI_xxx",
    status="In Progress"
)
```

### Issue Management
```python
await orchestrator.create_issue(
    repo="FOUNDUPS/autopost",
    title="WSP violation detected",
    body="Details...",
    labels=["wsp-violation", "automated"]
)

await orchestrator.close_issue(
    repo="FOUNDUPS/autopost",
    issue_number=42,
    reason="completed"
)
```

### Access Management (WSP 103)
```python
await orchestrator.add_collaborator(
    repo="FOUNDUPS/autopost",
    username="contributor123",
    permission="pull"
)

await orchestrator.add_team_member(
    team="angels",
    username="angel_user"
)
```

### Repo Management
```python
await orchestrator.create_federated_repo(
    name="gotjunk",
    description="Photo organization PWA",
    private=True
)
# Creates FOUNDUPS/gotjunk + Foundup/gotjunk with dual-remote
```

## FAM Event Integration

```python
# FAM events trigger GitHub actions
@fam_listener("task_started")
async def on_task_started(event):
    await orchestrator.move_card(event.task_id, "In Progress")

@fam_listener("task_completed")
async def on_task_completed(event):
    await orchestrator.move_card(event.task_id, "Done")

@fam_listener("wsp_violation")
async def on_wsp_violation(event):
    await orchestrator.create_issue(
        repo=event.repo,
        title=f"WSP {event.wsp_number} Violation",
        body=event.details
    )

@fam_listener("angel_subscribed")
async def on_angel_subscribed(event):
    for repo in get_pre_opo_foundups():
        await orchestrator.add_collaborator(repo, event.github_username)
```

## Required Token Scopes

```bash
# .env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Token must have:
# - repo (full)
# - admin:org (teams, members)
# - project (read/write)
# - write:discussion (optional)
```

## SKILLz

| Skill | Trigger | Description |
|-------|---------|-------------|
| `create_project_item` | Manual/FAM | Add item to project board |
| `move_card` | FAM event | Update card status |
| `create_issue` | WSP violation | Auto-create issue |
| `manage_access` | Subscription event | Add/remove collaborators |
| `create_federated_repo` | Manual | Create dual-remote repo |

## Environment Variables

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxx          # PAT with required scopes
GITHUB_ORG=FOUNDUPS                    # Primary org
GITHUB_BACKUP_ORG=Foundup              # Backup org (personal)
GITHUB_PROJECT_ID=PVT_xxxxxxxxxxxx     # Default project ID
```

## Related Documentation

- [WSP 103: FoundUp Federation Protocol](../../../WSP_knowledge/src/WSP_103_FoundUp_Federation_Protocol.md)
- [WSP 77: Agent Coordination Protocol](../../../WSP_knowledge/src/WSP_77_Agent_Coordination_Protocol.md)
- [FAM DAEmon](../../foundups/agent_market/src/fam_daemon.py)
