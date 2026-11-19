"""
GitHub API Adapter - Minimal Raw API Interface
Provides minimal GitHub API interface for existing WRE agents to use.
Does NOT duplicate agent logic - just provides GitHub API access.

WSP Compliance:
- WSP 54: Integrates with existing WRE agents (no duplication)
- WSP 71: Uses dynamic token system
- WSP 46: WRE orchestration compatible
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..auth.dynamic_token_manager import get_token_manager, AgentTokenRequest, TokenScope


@dataclass
class GitHubPRRequest:
    """GitHub PR creation request"""
    title: str
    body: str
    head_branch: str
    base_branch: str = "main"
    draft: bool = False
    labels: Optional[List[str]] = None


@dataclass  
class GitHubIssueRequest:
    """GitHub issue creation request"""
    title: str
    body: str
    labels: Optional[List[str]] = None
    assignees: Optional[List[str]] = None


class GitHubAPIAdapter:
    """
    Minimal GitHub API Adapter
    
    Provides raw GitHub API access for existing WRE agents.
    Does NOT contain business logic - that stays in the WRE agents.
    
    This adapter handles:
    - Raw API calls to GitHub
    - Dynamic token management integration
    - Error handling and retries
    - Response formatting for WRE agents
    """
    
    def __init__(self, repository: str = "FOUNDUPS/Foundups-Agent"):
        """
        Initialize GitHub API adapter
        
        Args:
            repository: Target GitHub repository
        """
        self.repository = repository
        self.logger = logging.getLogger(__name__)
        
    async def create_pull_request(self, pr_request: GitHubPRRequest, agent_id: str, 
                                session_id: str, cube_type: str) -> Dict[str, Any]:
        """
        Create pull request via GitHub API
        
        Args:
            pr_request: PR creation parameters
            agent_id: Calling agent ID
            session_id: Agent session ID
            cube_type: FoundUps cube type
            
        Returns:
            Created PR information
        """
        self.logger.info(f"Creating PR '{pr_request.title}' for agent {agent_id}")
        
        # Get dynamic token for agent
        token_manager = await get_token_manager()
        token_request = AgentTokenRequest(
            agent_id=agent_id,
            session_id=session_id,
            cube_type=cube_type,
            foundups_module="github_integration",
            required_scopes=[TokenScope.REPO, TokenScope.PULL_REQUESTS],
            required_capabilities=["pull_requests", "branches"],
            target_repository=self.repository
        )
        
        agent_token = await token_manager.generate_agent_token(token_request)
        
        try:
            # Make GitHub API call (this would be real API call)
            pr_result = await self._make_pr_api_call(pr_request, agent_token.access_token)
            
            self.logger.info(f"Created PR #{pr_result['number']} for agent {agent_id}")
            return pr_result
            
        finally:
            # Clean up token
            await token_manager.revoke_token(agent_token)
            
    async def _make_pr_api_call(self, pr_request: GitHubPRRequest, token: str) -> Dict[str, Any]:
        """Make actual GitHub PR API call"""
        # This would make real GitHub API call
        # For now, return mock response
        
        mock_pr = {
            "number": 12345,
            "url": f"https://github.com/{self.repository}/pull/12345",
            "title": pr_request.title,
            "body": pr_request.body,
            "head": {"ref": pr_request.head_branch},
            "base": {"ref": pr_request.base_branch},
            "state": "open",
            "draft": pr_request.draft,
            "created_at": datetime.now().isoformat()
        }
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        return mock_pr
        
    async def create_issue(self, issue_request: GitHubIssueRequest, agent_id: str,
                          session_id: str, cube_type: str) -> Dict[str, Any]:
        """
        Create issue via GitHub API
        
        Args:
            issue_request: Issue creation parameters
            agent_id: Calling agent ID
            session_id: Agent session ID
            cube_type: FoundUps cube type
            
        Returns:
            Created issue information
        """
        self.logger.info(f"Creating issue '{issue_request.title}' for agent {agent_id}")
        
        # Get dynamic token for agent
        token_manager = await get_token_manager()
        token_request = AgentTokenRequest(
            agent_id=agent_id,
            session_id=session_id,
            cube_type=cube_type,
            foundups_module="github_integration",
            required_scopes=[TokenScope.ISSUES],
            required_capabilities=["issues"],
            target_repository=self.repository
        )
        
        agent_token = await token_manager.generate_agent_token(token_request)
        
        try:
            # Make GitHub API call
            issue_result = await self._make_issue_api_call(issue_request, agent_token.access_token)
            
            self.logger.info(f"Created issue #{issue_result['number']} for agent {agent_id}")
            return issue_result
            
        finally:
            # Clean up token
            await token_manager.revoke_token(agent_token)
            
    async def _make_issue_api_call(self, issue_request: GitHubIssueRequest, token: str) -> Dict[str, Any]:
        """Make actual GitHub issue API call"""
        # This would make real GitHub API call
        # For now, return mock response
        
        mock_issue = {
            "number": 67890,
            "url": f"https://github.com/{self.repository}/issues/67890",
            "title": issue_request.title,
            "body": issue_request.body,
            "state": "open",
            "labels": [{"name": label} for label in (issue_request.labels or [])],
            "created_at": datetime.now().isoformat()
        }
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        return mock_issue
        
    async def update_file(self, file_path: str, content: str, commit_message: str,
                         agent_id: str, session_id: str, cube_type: str,
                         branch: str = "main") -> Dict[str, Any]:
        """
        Update file in repository
        
        Args:
            file_path: Path to file in repository
            content: New file content
            commit_message: Commit message
            agent_id: Calling agent ID
            session_id: Agent session ID
            cube_type: FoundUps cube type
            branch: Target branch
            
        Returns:
            Update result information
        """
        self.logger.info(f"Updating file '{file_path}' for agent {agent_id}")
        
        # Get dynamic token for agent
        token_manager = await get_token_manager()
        token_request = AgentTokenRequest(
            agent_id=agent_id,
            session_id=session_id,
            cube_type=cube_type,
            foundups_module="github_integration",
            required_scopes=[TokenScope.CONTENTS],
            required_capabilities=["contents"],
            target_repository=self.repository
        )
        
        agent_token = await token_manager.generate_agent_token(token_request)
        
        try:
            # Make GitHub API call
            update_result = await self._make_file_update_api_call(
                file_path, content, commit_message, branch, agent_token.access_token
            )
            
            self.logger.info(f"Updated file '{file_path}' for agent {agent_id}")
            return update_result
            
        finally:
            # Clean up token
            await token_manager.revoke_token(agent_token)
            
    async def _make_file_update_api_call(self, file_path: str, content: str, 
                                       commit_message: str, branch: str, token: str) -> Dict[str, Any]:
        """Make actual GitHub file update API call"""
        # This would make real GitHub API call
        # For now, return mock response
        
        mock_update = {
            "commit": {
                "sha": f"abc123_{file_path}_{datetime.now().timestamp()}",
                "url": f"https://github.com/{self.repository}/commit/abc123",
                "message": commit_message
            },
            "content": {
                "path": file_path,
                "sha": f"def456_{file_path}"
            }
        }
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        return mock_update
        
    async def trigger_workflow(self, workflow_id: str, ref: str, inputs: Optional[Dict] = None, *,
                             agent_id: str, session_id: str, cube_type: str) -> Dict[str, Any]:
        """
        Trigger GitHub Actions workflow
        
        Args:
            workflow_id: Workflow ID or filename
            ref: Branch/tag reference
            inputs: Workflow inputs
            agent_id: Calling agent ID
            session_id: Agent session ID
            cube_type: FoundUps cube type
            
        Returns:
            Workflow trigger result
        """
        self.logger.info(f"Triggering workflow '{workflow_id}' for agent {agent_id}")
        
        # Get dynamic token for agent
        token_manager = await get_token_manager()
        token_request = AgentTokenRequest(
            agent_id=agent_id,
            session_id=session_id,
            cube_type=cube_type,
            foundups_module="github_integration",
            required_scopes=[TokenScope.WORKFLOW],
            required_capabilities=["actions"],
            target_repository=self.repository
        )
        
        agent_token = await token_manager.generate_agent_token(token_request)
        
        try:
            # Make GitHub API call
            workflow_result = await self._make_workflow_trigger_api_call(
                workflow_id, ref, inputs, agent_token.access_token
            )
            
            self.logger.info(f"Triggered workflow '{workflow_id}' for agent {agent_id}")
            return workflow_result
            
        finally:
            # Clean up token
            await token_manager.revoke_token(agent_token)
            
    async def _make_workflow_trigger_api_call(self, workflow_id: str, ref: str, 
                                            inputs: Optional[Dict], token: str) -> Dict[str, Any]:
        """Make actual GitHub workflow trigger API call"""
        # This would make real GitHub API call
        # For now, return mock response
        
        mock_workflow = {
            "workflow_id": workflow_id,
            "ref": ref,
            "inputs": inputs or {},
            "run_id": f"run_{datetime.now().timestamp()}",
            "triggered_at": datetime.now().isoformat()
        }
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        return mock_workflow
        
    async def get_repository_info(self, agent_id: str, session_id: str, cube_type: str) -> Dict[str, Any]:
        """
        Get repository information
        
        Args:
            agent_id: Calling agent ID
            session_id: Agent session ID
            cube_type: FoundUps cube type
            
        Returns:
            Repository information
        """
        self.logger.info(f"Getting repository info for agent {agent_id}")
        
        # Get dynamic token for agent
        token_manager = await get_token_manager()
        token_request = AgentTokenRequest(
            agent_id=agent_id,
            session_id=session_id,
            cube_type=cube_type,
            foundups_module="github_integration",
            required_scopes=[TokenScope.METADATA],
            required_capabilities=["metadata"],
            target_repository=self.repository
        )
        
        agent_token = await token_manager.generate_agent_token(token_request)
        
        try:
            # Make GitHub API call
            repo_info = await self._make_repo_info_api_call(agent_token.access_token)
            
            self.logger.info(f"Retrieved repository info for agent {agent_id}")
            return repo_info
            
        finally:
            # Clean up token
            await token_manager.revoke_token(agent_token)
            
    async def _make_repo_info_api_call(self, token: str) -> Dict[str, Any]:
        """Make actual GitHub repository info API call"""
        # This would make real GitHub API call
        # For now, return mock response
        
        mock_repo = {
            "name": self.repository.split("/")[-1],
            "full_name": self.repository,
            "description": "FoundUps Agent Repository",
            "private": False,
            "default_branch": "main",
            "url": f"https://github.com/{self.repository}",
            "clone_url": f"https://github.com/{self.repository}.git"
        }
        
        # Simulate API delay
        await asyncio.sleep(0.1)
        
        return mock_repo