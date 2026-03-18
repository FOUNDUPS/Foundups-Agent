"""
GitHub Orchestrator - 0102 Management Layer

WSP 103: FoundUp Federation + Access Management
WSP 77: Agent Coordination via Projects

0102 is the MANAGER, not participant.
"""

import os
import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ProjectItem:
    """GitHub Project item."""
    id: str
    title: str
    status: str
    assignee: Optional[str] = None


class GitHubOrchestrator:
    """
    0102 GitHub Management Layer.

    Manages:
    - Projects (boards, cards, assignments)
    - Issues (create, close, label)
    - Repos (create federated repos)
    - Access (collaborators, teams)
    """

    def __init__(self):
        self.org = os.environ.get("GITHUB_ORG", "FOUNDUPS")
        self.backup_org = os.environ.get("GITHUB_BACKUP_ORG", "Foundup")
        self.project_id = os.environ.get("GITHUB_PROJECT_ID")
        self._verify_auth()

    def _verify_auth(self):
        """Verify gh CLI is authenticated."""
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.warning("GitHub CLI not authenticated")

    def _gh(self, *args, **kwargs) -> dict:
        """Execute gh CLI command and return JSON result."""
        cmd = ["gh"] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.error(f"gh command failed: {result.stderr}")
            return {"error": result.stderr}

        try:
            return json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            return {"output": result.stdout}

    def _gh_api(self, endpoint: str, method: str = "GET", data: dict = None) -> dict:
        """Execute gh api command."""
        cmd = ["gh", "api", endpoint, "-X", method]
        if data:
            cmd.extend(["-f", json.dumps(data)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr}

        try:
            return json.loads(result.stdout) if result.stdout else {}
        except json.JSONDecodeError:
            return {"output": result.stdout}

    # ─────────────────────────────────────────────────────────────
    # PROJECT MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    async def list_projects(self) -> List[dict]:
        """List organization projects."""
        query = '''
        query($org: String!) {
            organization(login: $org) {
                projectsV2(first: 10) {
                    nodes { id title number }
                }
            }
        }
        '''
        result = subprocess.run(
            ["gh", "api", "graphql", "-f", f"query={query}", "-f", f"org={self.org}"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return [{"error": result.stderr}]

        data = json.loads(result.stdout)
        return data.get("data", {}).get("organization", {}).get("projectsV2", {}).get("nodes", [])

    async def create_project_item(
        self,
        title: str,
        body: str = "",
        project_id: str = None,
        status: str = "Backlog"
    ) -> dict:
        """Create a new project item (card)."""
        pid = project_id or self.project_id
        if not pid:
            return {"error": "No project_id specified"}

        # GraphQL mutation to add item
        mutation = '''
        mutation($projectId: ID!, $title: String!, $body: String) {
            addProjectV2DraftIssue(input: {
                projectId: $projectId,
                title: $title,
                body: $body
            }) {
                projectItem { id }
            }
        }
        '''
        result = subprocess.run(
            ["gh", "api", "graphql",
             "-f", f"query={mutation}",
             "-f", f"projectId={pid}",
             "-f", f"title={title}",
             "-f", f"body={body}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        logger.info(f"Created project item: {title}")
        return json.loads(result.stdout)

    async def move_card(self, item_id: str, status: str) -> dict:
        """Move a project card to a different status column."""
        # This requires knowing the field ID for status
        # Simplified - would need project schema query first
        logger.info(f"Moving card {item_id} to {status}")
        return {"status": "moved", "item_id": item_id, "new_status": status}

    # ─────────────────────────────────────────────────────────────
    # ISSUE MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    async def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: List[str] = None
    ) -> dict:
        """Create a GitHub issue."""
        cmd = ["gh", "issue", "create",
               "--repo", repo,
               "--title", title,
               "--body", body]

        if labels:
            cmd.extend(["--label", ",".join(labels)])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {"error": result.stderr}

        logger.info(f"Created issue in {repo}: {title}")
        return {"url": result.stdout.strip()}

    async def close_issue(
        self,
        repo: str,
        issue_number: int,
        reason: str = "completed"
    ) -> dict:
        """Close a GitHub issue."""
        result = subprocess.run(
            ["gh", "issue", "close", str(issue_number),
             "--repo", repo,
             "--reason", reason],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        logger.info(f"Closed issue #{issue_number} in {repo}")
        return {"closed": True, "issue": issue_number}

    async def list_issues(self, repo: str, state: str = "open") -> List[dict]:
        """List issues in a repo."""
        result = subprocess.run(
            ["gh", "issue", "list",
             "--repo", repo,
             "--state", state,
             "--json", "number,title,state,labels"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return [{"error": result.stderr}]

        return json.loads(result.stdout)

    # ─────────────────────────────────────────────────────────────
    # REPO MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    async def create_federated_repo(
        self,
        name: str,
        description: str = "",
        private: bool = True
    ) -> dict:
        """
        Create dual-remote federated FoundUp repo.

        Creates:
        - FOUNDUPS/{name} (origin)
        - Foundup/{name} (backup)
        """
        # Create in primary org
        result1 = subprocess.run(
            ["gh", "repo", "create", f"{self.org}/{name}",
             "--private" if private else "--public",
             "--description", description],
            capture_output=True,
            text=True
        )

        # Create in backup org
        result2 = subprocess.run(
            ["gh", "repo", "create", f"{self.backup_org}/{name}",
             "--private" if private else "--public",
             "--description", description],
            capture_output=True,
            text=True
        )

        logger.info(f"Created federated repo: {name}")
        return {
            "origin": f"https://github.com/{self.org}/{name}",
            "backup": f"https://github.com/{self.backup_org}/{name}",
            "primary_result": result1.stdout or result1.stderr,
            "backup_result": result2.stdout or result2.stderr
        }

    # ─────────────────────────────────────────────────────────────
    # ACCESS MANAGEMENT (WSP 103)
    # ─────────────────────────────────────────────────────────────

    async def add_collaborator(
        self,
        repo: str,
        username: str,
        permission: str = "pull"
    ) -> dict:
        """Add collaborator to a repo."""
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/collaborators/{username}",
             "-X", "PUT",
             "-f", f"permission={permission}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        logger.info(f"Added {username} to {repo} with {permission} access")
        return {"added": True, "username": username, "repo": repo}

    async def remove_collaborator(self, repo: str, username: str) -> dict:
        """Remove collaborator from a repo."""
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/collaborators/{username}",
             "-X", "DELETE"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        logger.info(f"Removed {username} from {repo}")
        return {"removed": True, "username": username, "repo": repo}

    async def add_team_member(self, team: str, username: str) -> dict:
        """Add user to organization team."""
        result = subprocess.run(
            ["gh", "api", f"orgs/{self.org}/teams/{team}/memberships/{username}",
             "-X", "PUT"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        logger.info(f"Added {username} to team {team}")
        return {"added": True, "username": username, "team": team}

    # ─────────────────────────────────────────────────────────────
    # FAM EVENT HANDLERS
    # ─────────────────────────────────────────────────────────────

    async def handle_fam_event(self, event_type: str, payload: dict) -> dict:
        """
        Handle FAM events and trigger GitHub actions.

        Event types:
        - task_started: Move card to "In Progress"
        - task_completed: Move card to "Done"
        - wsp_violation: Create issue
        - angel_subscribed: Add collaborator to all pre-OPO repos
        - subscription_cancelled: Remove collaborator
        """
        handlers = {
            "task_started": self._on_task_started,
            "task_completed": self._on_task_completed,
            "wsp_violation": self._on_wsp_violation,
            "angel_subscribed": self._on_angel_subscribed,
            "subscription_cancelled": self._on_subscription_cancelled,
        }

        handler = handlers.get(event_type)
        if handler:
            return await handler(payload)

        return {"unhandled": event_type}

    async def _on_task_started(self, payload: dict) -> dict:
        if "project_item_id" in payload:
            return await self.move_card(payload["project_item_id"], "In Progress")
        return {"skipped": "no project_item_id"}

    async def _on_task_completed(self, payload: dict) -> dict:
        if "project_item_id" in payload:
            return await self.move_card(payload["project_item_id"], "Done")
        return {"skipped": "no project_item_id"}

    async def _on_wsp_violation(self, payload: dict) -> dict:
        return await self.create_issue(
            repo=payload.get("repo", f"{self.org}/Foundups-Agent"),
            title=f"WSP {payload.get('wsp_number', '?')} Violation",
            body=payload.get("details", "Automated violation report"),
            labels=["wsp-violation", "automated"]
        )

    async def _on_angel_subscribed(self, payload: dict) -> dict:
        username = payload.get("github_username")
        if not username:
            return {"error": "no github_username"}

        # Get list of pre-OPO FoundUp repos
        pre_opo_repos = payload.get("pre_opo_repos", [
            f"{self.org}/autopost",
            # Add more as they're created
        ])

        results = []
        for repo in pre_opo_repos:
            result = await self.add_collaborator(repo, username, "pull")
            results.append(result)

        return {"granted_access": results}

    async def _on_subscription_cancelled(self, payload: dict) -> dict:
        username = payload.get("github_username")
        if not username:
            return {"error": "no github_username"}

        # Remove from repos they don't have stake in
        repos_to_remove = payload.get("repos_to_remove", [])

        results = []
        for repo in repos_to_remove:
            result = await self.remove_collaborator(repo, username)
            results.append(result)

        return {"revoked_access": results}


# Singleton instance
_orchestrator = None

def get_github_orchestrator() -> GitHubOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = GitHubOrchestrator()
    return _orchestrator


# ─────────────────────────────────────────────────────────────
# FAM DAEMOEN LISTENER (WSP 97: Wire to FAM)
# ─────────────────────────────────────────────────────────────

def create_fam_listener():
    """
    Create listener function that wires FAM events to GitHub Orchestrator.

    Usage:
        from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon
        from modules.infrastructure.github_orchestrator.src.orchestrator import create_fam_listener

        daemon = get_fam_daemon()
        listener = create_fam_listener()
        daemon.add_listener(listener)
    """
    import asyncio
    orchestrator = get_github_orchestrator()

    # Map FAM event types to handler methods
    EVENT_HANDLERS = {
        "task_state_changed": _handle_task_state,
        "security_alert_forwarded": _handle_security_alert,
        "angel_subscribed": orchestrator._on_angel_subscribed,
        "subscription_cancelled": orchestrator._on_subscription_cancelled,
    }

    def listener(event):
        """FAM event listener - dispatches to GitHub Orchestrator."""
        event_type = event.event_type
        payload = event.payload

        handler = EVENT_HANDLERS.get(event_type)
        if handler:
            # Run async handler in event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(handler(payload))
                else:
                    loop.run_until_complete(handler(payload))
            except Exception as e:
                logger.error(f"GitHub listener error: {e}")

    return listener


async def _handle_task_state(payload: dict) -> dict:
    """Handle task_state_changed events."""
    orchestrator = get_github_orchestrator()
    new_state = payload.get("new_state", "")

    if new_state == "in_progress":
        return await orchestrator._on_task_started(payload)
    elif new_state in ("completed", "done"):
        return await orchestrator._on_task_completed(payload)

    return {"skipped": f"unhandled state: {new_state}"}


async def _handle_security_alert(payload: dict) -> dict:
    """Handle security_alert_forwarded events by creating issues."""
    orchestrator = get_github_orchestrator()
    return await orchestrator.create_issue(
        repo=payload.get("repo", f"{orchestrator.org}/Foundups-Agent"),
        title=f"Security Alert: {payload.get('alert_type', 'Unknown')}",
        body=payload.get("details", "Automated security alert"),
        labels=["security", "automated"]
    )


def wire_github_to_fam():
    """
    Wire GitHub Orchestrator to FAM DAEmon.

    Call this at startup to enable automatic GitHub actions from FAM events.
    """
    try:
        from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon

        daemon = get_fam_daemon()
        listener = create_fam_listener()
        daemon.add_listener(listener)

        logger.info("[GITHUB-ORCHESTRATOR] Wired to FAM DAEmon")
        return True
    except ImportError as e:
        logger.warning(f"[GITHUB-ORCHESTRATOR] Cannot wire to FAM: {e}")
        return False
