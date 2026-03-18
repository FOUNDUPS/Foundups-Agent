---
name: github_management
description: Manage GitHub org resources (issues, repos, collaborators) via 0102 orchestration
version: 1.0.0
author: 0102
agents: [0102]
dependencies: [github_orchestrator, fam_daemon]
domain: infrastructure
intent_type: COMMAND
promotion_state: prototype
category: workflow
evals: []
---
# GitHub Management Skill

**Skill Type**: User-Invokable Command
**Intent**: COMMAND (manual trigger via /github)
**Agents**: 0102 (orchestrator)
**Promotion State**: prototype
**Version**: 1.0.0
**Created**: 2026-03-15
**WSP References**: WSP 103 (FoundUp Federation), WSP 77 (Agent Coordination)

---

## Skill Purpose

Enable 0102 to MANAGE (not participate in) GitHub org resources autonomously. Provides command interface for issue management, collaborator access, and federated repo creation.

**Trigger Source**: User command `/github <subcommand>`

**Success Criteria**:
- Issues created/closed on correct repos
- Collaborators added/removed correctly
- Federated repos created with dual-remote pattern
- FAM events emitted for access changes

---

## Commands

### Issue Management

```bash
# Create issue
/github issue create FOUNDUPS/autopost "Bug: Login fails" "Description of the issue"

# Close issue
/github issue close FOUNDUPS/autopost 42

# List issues
/github issue list FOUNDUPS/autopost
```

### Collaborator Management

```bash
# Add collaborator (default: pull access)
/github collaborator add FOUNDUPS/autopost username123

# Add with write access
/github collaborator add FOUNDUPS/autopost username123 push

# Remove collaborator
/github collaborator remove FOUNDUPS/autopost username123
```

### Repository Management

```bash
# Create federated repo (FOUNDUPS + Foundup dual-remote)
/github repo create gotjunk "Photo organization PWA"

# Create public repo
/github repo create gotjunk "Description" --public
```

---

## Execution Flow

### Step 1: Parse Command

```python
def parse_github_command(args: str) -> dict:
    """Parse /github command arguments."""
    parts = args.split()
    subcommand = parts[0]  # issue, collaborator, repo
    action = parts[1]       # create, close, add, remove, list

    return {
        "subcommand": subcommand,
        "action": action,
        "args": parts[2:]
    }
```

### Step 2: Execute via Orchestrator

```python
from modules.infrastructure.github_orchestrator import get_github_orchestrator

async def execute_github_command(parsed: dict) -> dict:
    orchestrator = get_github_orchestrator()

    if parsed["subcommand"] == "issue":
        if parsed["action"] == "create":
            return await orchestrator.create_issue(
                repo=parsed["args"][0],
                title=parsed["args"][1],
                body=parsed["args"][2] if len(parsed["args"]) > 2 else ""
            )
        elif parsed["action"] == "close":
            return await orchestrator.close_issue(
                repo=parsed["args"][0],
                issue_number=int(parsed["args"][1])
            )

    elif parsed["subcommand"] == "collaborator":
        if parsed["action"] == "add":
            return await orchestrator.add_collaborator(
                repo=parsed["args"][0],
                username=parsed["args"][1],
                permission=parsed["args"][2] if len(parsed["args"]) > 2 else "pull"
            )
        elif parsed["action"] == "remove":
            return await orchestrator.remove_collaborator(
                repo=parsed["args"][0],
                username=parsed["args"][1]
            )

    elif parsed["subcommand"] == "repo":
        if parsed["action"] == "create":
            return await orchestrator.create_federated_repo(
                name=parsed["args"][0],
                description=parsed["args"][1] if len(parsed["args"]) > 1 else "",
                private="--public" not in parsed["args"]
            )

    return {"error": "Unknown command"}
```

### Step 3: Emit FAM Event (Access Changes)

```python
from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon, FAMEventType

# When adding collaborator
daemon = get_fam_daemon()
daemon.emit(
    FAMEventType.ANGEL_SUBSCRIBED,  # Or appropriate event
    payload={"github_username": username, "repo": repo},
    actor_id="github_orchestrator"
)
```

---

## FAM Event Integration

| Command | FAM Event Emitted |
|---------|-------------------|
| `collaborator add` | `angel_subscribed` or `du_staked` |
| `collaborator remove` | `subscription_cancelled` or `du_unstaked` |
| `issue create` (security) | `security_alert_forwarded` |
| `repo create` | `foundup_created` (if new FoundUp) |

---

## Required Permissions

```bash
# .env must have GITHUB_TOKEN with scopes:
GITHUB_TOKEN=github_pat_xxxx

# Required scopes:
# - repo (full)
# - admin:org (for team management)
# - project (for project boards)
```

---

## Test Cases

### Test 1: Create Issue

```yaml
Input: /github issue create FOUNDUPS/autopost "Test issue" "Body text"
Expected:
  - Issue created on FOUNDUPS/autopost
  - Returns issue URL
  - No FAM event (not security-related)
```

### Test 2: Add Collaborator

```yaml
Input: /github collaborator add FOUNDUPS/autopost testuser pull
Expected:
  - Collaborator added with pull access
  - FAM event: angel_subscribed OR du_staked
  - Returns confirmation
```

### Test 3: Create Federated Repo

```yaml
Input: /github repo create gotjunk "Photo PWA"
Expected:
  - FOUNDUPS/gotjunk created (private)
  - Foundup/gotjunk created (private)
  - Returns both URLs
  - FAM event: foundup_created (if applicable)
```

---

## Changelog

### v1.0.0 (2026-03-15)
- Initial skill creation
- Issue management (create, close, list)
- Collaborator management (add, remove)
- Federated repo creation
- FAM event integration for access changes
- Promotion state: prototype
