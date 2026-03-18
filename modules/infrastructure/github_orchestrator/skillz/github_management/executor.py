"""
GitHub Management Skill Executor

Implements /github command for 0102 GitHub orchestration.

WSP 103: FoundUp Federation + Access Management
WSP 97: Execution Mantra
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def execute(args: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Execute /github command.

    Args:
        args: Command arguments (e.g., "issue create FOUNDUPS/autopost Title")
        context: Optional execution context

    Returns:
        Result dict with success/error and data
    """
    from modules.infrastructure.github_orchestrator import get_github_orchestrator

    try:
        parsed = parse_command(args)
        orchestrator = get_github_orchestrator()

        if parsed["subcommand"] == "issue":
            return await handle_issue(orchestrator, parsed)
        elif parsed["subcommand"] == "collaborator":
            return await handle_collaborator(orchestrator, parsed)
        elif parsed["subcommand"] == "repo":
            return await handle_repo(orchestrator, parsed)
        else:
            return {"error": f"Unknown subcommand: {parsed['subcommand']}"}

    except Exception as e:
        logger.error(f"GitHub skill error: {e}")
        return {"error": str(e)}


def parse_command(args: str) -> Dict[str, Any]:
    """Parse /github command arguments."""
    if not args:
        return {"error": "No arguments provided", "subcommand": None}

    parts = args.split(maxsplit=3)  # Max 4 parts to preserve quoted strings

    if len(parts) < 2:
        return {"error": "Usage: /github <subcommand> <action> [args...]", "subcommand": None}

    return {
        "subcommand": parts[0],  # issue, collaborator, repo
        "action": parts[1],       # create, close, add, remove, list
        "args": parts[2:] if len(parts) > 2 else []
    }


async def handle_issue(orchestrator, parsed: Dict) -> Dict[str, Any]:
    """Handle issue subcommands."""
    action = parsed["action"]
    args = parsed["args"]

    if action == "create":
        if len(args) < 1:
            return {"error": "Usage: /github issue create <repo> <title> [body]"}

        # Parse repo and title from remaining args
        remaining = " ".join(args)
        parts = remaining.split(maxsplit=2)

        repo = parts[0]
        title = parts[1] if len(parts) > 1 else "Untitled Issue"
        body = parts[2] if len(parts) > 2 else ""

        result = await orchestrator.create_issue(repo, title, body)
        return {"success": True, "action": "issue_created", **result}

    elif action == "close":
        if len(args) < 1:
            return {"error": "Usage: /github issue close <repo> <number>"}

        remaining = " ".join(args)
        parts = remaining.split()
        repo = parts[0]
        number = int(parts[1]) if len(parts) > 1 else 1

        result = await orchestrator.close_issue(repo, number)
        return {"success": True, "action": "issue_closed", **result}

    elif action == "list":
        if len(args) < 1:
            return {"error": "Usage: /github issue list <repo>"}

        repo = args[0]
        result = await orchestrator.list_issues(repo)
        return {"success": True, "action": "issues_listed", "issues": result}

    return {"error": f"Unknown issue action: {action}"}


async def handle_collaborator(orchestrator, parsed: Dict) -> Dict[str, Any]:
    """Handle collaborator subcommands."""
    action = parsed["action"]
    args = parsed["args"]

    if action == "add":
        if len(args) < 1:
            return {"error": "Usage: /github collaborator add <repo> <username> [permission]"}

        remaining = " ".join(args)
        parts = remaining.split()

        repo = parts[0]
        username = parts[1] if len(parts) > 1 else None
        permission = parts[2] if len(parts) > 2 else "pull"

        if not username:
            return {"error": "Username required"}

        result = await orchestrator.add_collaborator(repo, username, permission)

        # Emit FAM event for access grant
        await emit_access_event("granted", username, repo)

        return {"success": True, "action": "collaborator_added", **result}

    elif action == "remove":
        if len(args) < 1:
            return {"error": "Usage: /github collaborator remove <repo> <username>"}

        remaining = " ".join(args)
        parts = remaining.split()

        repo = parts[0]
        username = parts[1] if len(parts) > 1 else None

        if not username:
            return {"error": "Username required"}

        result = await orchestrator.remove_collaborator(repo, username)

        # Emit FAM event for access revoke
        await emit_access_event("revoked", username, repo)

        return {"success": True, "action": "collaborator_removed", **result}

    return {"error": f"Unknown collaborator action: {action}"}


async def handle_repo(orchestrator, parsed: Dict) -> Dict[str, Any]:
    """Handle repo subcommands."""
    action = parsed["action"]
    args = parsed["args"]

    if action == "create":
        if len(args) < 1:
            return {"error": "Usage: /github repo create <name> [description] [--public]"}

        remaining = " ".join(args)
        parts = remaining.split()

        name = parts[0]
        is_public = "--public" in parts
        parts = [p for p in parts if p != "--public"]
        description = " ".join(parts[1:]) if len(parts) > 1 else ""

        result = await orchestrator.create_federated_repo(name, description, private=not is_public)
        return {"success": True, "action": "repo_created", **result}

    return {"error": f"Unknown repo action: {action}"}


async def emit_access_event(event_type: str, username: str, repo: str):
    """Emit FAM event for access changes."""
    try:
        from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon, FAMEventType

        daemon = get_fam_daemon()

        if event_type == "granted":
            daemon.emit(
                FAMEventType.ANGEL_SUBSCRIBED,
                payload={"github_username": username, "repo": repo},
                actor_id="github_orchestrator"
            )
        elif event_type == "revoked":
            daemon.emit(
                FAMEventType.SUBSCRIPTION_CANCELLED,
                payload={"github_username": username, "repo": repo},
                actor_id="github_orchestrator"
            )
    except ImportError:
        logger.warning("FAM daemon not available for access event emission")


# CLI entry point
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        args = " ".join(sys.argv[1:])
        result = asyncio.run(execute(args))
        print(result)
    else:
        print("Usage: python executor.py <subcommand> <action> [args...]")
        print("  /github issue create <repo> <title> [body]")
        print("  /github issue close <repo> <number>")
        print("  /github issue list <repo>")
        print("  /github collaborator add <repo> <username> [permission]")
        print("  /github collaborator remove <repo> <username>")
        print("  /github repo create <name> [description] [--public]")
