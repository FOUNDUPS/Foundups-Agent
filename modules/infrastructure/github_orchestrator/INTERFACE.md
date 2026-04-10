# GitHub Orchestrator — Interface Contract

> WSP 11 Compliant | Version 0.4.0 | Last Updated: 2026-04-10

## Module Identity

| Property | Value |
|----------|-------|
| **Location** | `modules/infrastructure/github_orchestrator/` |
| **Package** | `modules.infrastructure.github_orchestrator` |
| **Status** | PoC (Phase 0 Complete) |
| **WSP Compliance** | WSP 103 (Federation), WSP 77 (Agent Coordination), WSP 49 (Module Structure) |

---

## Public Exports

From `modules.infrastructure.github_orchestrator`:

```python
from modules.infrastructure.github_orchestrator import (
    GitHubOrchestrator,
    get_github_orchestrator,
    create_fam_listener,
    wire_github_to_fam,
)
```

---

## Singleton Access

### `get_github_orchestrator() -> GitHubOrchestrator`

Returns the singleton `GitHubOrchestrator` instance.

```python
from modules.infrastructure.github_orchestrator import get_github_orchestrator

orchestrator = get_github_orchestrator()
```

**Behavior**: Creates instance on first call; returns cached instance thereafter.

---

## GitHubOrchestrator Class

### Constructor

```python
GitHubOrchestrator()
```

**Initialization**:
- Reads `GITHUB_ORG` from env (default: `"FOUNDUPS"`)
- Reads `GITHUB_BACKUP_ORG` from env (default: `"Foundup"`)
- Reads `GITHUB_PROJECT_ID` from env (optional)
- Verifies `gh` CLI authentication via `gh auth status`

**Side Effects**: Logs warning if `gh` CLI is not authenticated.

---

### Issue Management

#### `create_issue(repo, title, body, labels=None) -> dict`

Create a GitHub issue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo` | `str` | Yes | Repository in `owner/repo` format |
| `title` | `str` | Yes | Issue title |
| `body` | `str` | Yes | Issue body (markdown) |
| `labels` | `List[str]` | No | Labels to apply |

**Returns**: `{"url": "<issue_url>"}` on success, `{"error": "<message>"}` on failure.

**Example**:
```python
result = await orchestrator.create_issue(
    repo="FOUNDUPS/autopost",
    title="WSP violation detected",
    body="Details here...",
    labels=["wsp-violation", "automated"]
)
```

---

#### `close_issue(repo, issue_number, reason="completed") -> dict`

Close a GitHub issue.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo` | `str` | Yes | Repository in `owner/repo` format |
| `issue_number` | `int` | Yes | Issue number to close |
| `reason` | `str` | No | Close reason (`"completed"` or `"not_planned"`) |

**Returns**: `{"closed": True, "issue": <number>}` on success.

---

#### `list_issues(repo, state="open") -> List[dict]`

List issues in a repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo` | `str` | Yes | Repository in `owner/repo` format |
| `state` | `str` | No | Filter: `"open"`, `"closed"`, or `"all"` |

**Returns**: List of issue dicts with `number`, `title`, `state`, `labels`.

---

### Repository Management

#### `create_federated_repo(name, description="", private=True) -> dict`

Create dual-remote federated FoundUp repository.

Creates repos in both primary org (`GITHUB_ORG`) and backup org (`GITHUB_BACKUP_ORG`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Repository name |
| `description` | `str` | No | Repository description |
| `private` | `bool` | No | Private visibility (default: `True`) |

**Returns**:
```python
{
    "origin": "https://github.com/FOUNDUPS/<name>",
    "backup": "https://github.com/Foundup/<name>",
    "primary_result": "<gh output>",
    "backup_result": "<gh output>"
}
```

---

### Access Management (WSP 103)

#### `add_collaborator(repo, username, permission="pull") -> dict`

Add collaborator to a repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo` | `str` | Yes | Repository in `owner/repo` format |
| `username` | `str` | Yes | GitHub username |
| `permission` | `str` | No | `"pull"`, `"push"`, `"admin"`, `"maintain"`, `"triage"` |

**Returns**: `{"added": True, "username": "<user>", "repo": "<repo>"}` on success.

---

#### `remove_collaborator(repo, username) -> dict`

Remove collaborator from a repository.

**Returns**: `{"removed": True, "username": "<user>", "repo": "<repo>"}` on success.

---

#### `add_team_member(team, username) -> dict`

Add user to organization team.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team` | `str` | Yes | Team slug (e.g., `"angels"`) |
| `username` | `str` | Yes | GitHub username |

**Returns**: `{"added": True, "username": "<user>", "team": "<team>"}` on success.

**Note**: Requires `admin:org` token scope.

---

### Project Management

#### `list_projects() -> List[dict]`

List organization ProjectsV2.

**Returns**: List of `{"id": "...", "title": "...", "number": N}`.

**Note**: Requires `project` token scope (read).

---

#### `create_project_item(title, body="", project_id=None, status="Backlog") -> dict`

Create a draft issue in a ProjectV2.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | `str` | Yes | Item title |
| `body` | `str` | No | Item body |
| `project_id` | `str` | No | Project ID (uses `GITHUB_PROJECT_ID` if omitted) |
| `status` | `str` | No | Accepted but **not implemented** — item lands in default column |

**Returns**: GraphQL response with `projectItem.id`.

**Note**: Requires `project` token scope (write).

**Limitation**: The `status` parameter is accepted for API compatibility but the implementation does not yet set the initial column. Items are created in the project's default status. To move an item after creation, use `move_card()`.

---

#### `move_card(item_id, status) -> dict`

Move a project card to a status column.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_id` | `str` | Yes | Project item ID |
| `status` | `str` | Yes | Target status column name |

**Returns**: `{"status": "moved", "item_id": "...", "new_status": "..."}`.

**Note**: Currently simplified implementation — requires project schema query for full functionality.

---

## FAM Integration

### `wire_github_to_fam() -> bool`

Wire GitHub Orchestrator to FAM DAEmon at startup.

```python
from modules.infrastructure.github_orchestrator import wire_github_to_fam

# Call once at startup
wire_github_to_fam()
```

**Returns**: `True` if wired successfully, `False` if FAM import fails.

**Behavior**: Registers listener for FAM events:
- `task_state_changed` → moves project cards
- `security_alert_forwarded` → creates issues
- `angel_subscribed` → adds collaborator to pre-OPO repos
- `subscription_cancelled` → removes collaborator

---

### `create_fam_listener() -> Callable`

Create FAM event listener function for manual wiring.

```python
from modules.infrastructure.github_orchestrator import create_fam_listener
from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon

daemon = get_fam_daemon()
listener = create_fam_listener()
daemon.add_listener(listener)
```

---

## Skill Executor (`/github` command)

Location: `skillz/github_management/executor.py`

### `execute(args, context=None) -> dict`

Execute `/github` command.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `args` | `str` | Yes | Command arguments |
| `context` | `dict` | No | Execution context |

**Supported Commands**:

```bash
/github issue create <repo> <title> [body]
/github issue close <repo> <number>
/github issue list <repo>
/github collaborator add <repo> <username> [permission]
/github collaborator remove <repo> <username>
/github repo create <name> [description] [--public]
```

**Returns**: `{"success": True, "action": "...", ...}` or `{"error": "..."}`.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_ORG` | No | `"FOUNDUPS"` | Primary GitHub organization |
| `GITHUB_BACKUP_ORG` | No | `"Foundup"` | Backup organization for dual-remote |
| `GITHUB_PROJECT_ID` | No | None | Default ProjectV2 ID |

**Authentication**: Uses `gh` CLI authentication (no `GITHUB_TOKEN` env var needed).

---

## Token Scopes Required

The following scopes are required for full functionality. The module does not inspect token scopes at runtime — it relies on `gh auth status` to verify authentication is active.

| Scope | Required For |
|-------|--------------|
| `repo` | Issues, collaborators, repo creation |
| `admin:org` | Team membership management |
| `project` | ProjectsV2 read/write |

**Note**: If a scope is missing, the corresponding `gh` CLI command will fail with a permissions error. Run `gh auth refresh -s <scope>` to add missing scopes.

---

## Error Handling

All async methods return `{"error": "<message>"}` on failure.

Common errors:
- `"gh command failed: ..."` — CLI execution error
- `"No project_id specified"` — Missing required parameter
- `"no github_username"` — Missing payload field

---

## Dependencies

**External**:
- `gh` CLI (GitHub CLI) — must be installed and authenticated

**Internal**:
- `modules.foundups.agent_market.src.fam_daemon` — optional, for FAM integration

---

## Test Coverage

| Suite | Tests | Status |
|-------|-------|--------|
| `tests/test_executor.py` | 9 | PASS |

Run tests:
```bash
pytest modules/infrastructure/github_orchestrator/tests/ -v
```

---

## Verified Behavior

The following has been directly confirmed from source:

- All exported symbols match `__all__` in `src/__init__.py`
- All method signatures extracted from `src/orchestrator.py`
- FAM event mapping confirmed from `create_fam_listener()` implementation
- Skill commands confirmed from `skillz/github_management/executor.py`
- Environment variable defaults confirmed from `GitHubOrchestrator.__init__()`

**Inferred** (not directly tested):
- `move_card()` — simplified stub, needs project schema for full implementation
- Team membership — requires `admin:org` scope not currently granted
