"""
GitHub API Client - Complete GitHub Integration
Provides comprehensive GitHub API integration for repository management, 
pull requests, issues, and automated workflows.

WSP Compliance:
- WSP 3: Platform Integration Domain (external API integration)
- WSP 11: Clean interface definition for modular consumption
- WSP 34: Git Operations Protocol integration
- WSP 71: Secrets management for GitHub API credentials
"""

import json
import base64
import binascii
import hashlib
import re
import unicodedata
from urllib.parse import quote
import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path


_OBSERVATION_BODY_LIMIT = 2 * 1024 * 1024
_OBSERVATION_TIMEOUT = 30


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass


class PullRequestState(Enum):
    """Pull request states"""
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class IssueState(Enum):
    """Issue states"""
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class GitHubRepository:
    """GitHub repository information"""
    owner: str
    name: str
    full_name: str
    description: Optional[str]
    private: bool
    default_branch: str
    url: str


@dataclass(frozen=True, slots=True)
class GitHubFileObservation:
    """Immutable response-consistency record; not a repository-control grant."""
    repository_id: int
    owner_id: int
    repository_full_name: str
    default_branch: str
    private: bool
    observed_default_commit_sha: str
    commit_sha: str
    tree_sha: str
    path: str
    mode: str
    blob_sha: str
    content: bytes
    size_bytes: int


def _observation_invalid(field: str):
    raise GitHubAPIError(f"Invalid file observation: {field}") from None


def _observation_text(value, field: str, limit: int) -> str:
    if type(value) is not str or not value or len(value) > limit:
        _observation_invalid(field)
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        _observation_invalid(field)
    if size > limit or any(unicodedata.category(c) == "Cc" for c in value):
        _observation_invalid(field)
    return value


def _observation_sha(value, field: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _observation_invalid(field)
    return value


def _observation_endpoint(owner, repo) -> str:
    if type(owner) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", owner) is None:
        _observation_invalid("repository.owner")
    if (type(repo) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", repo) is None
            or repo in {".", ".."}):
        _observation_invalid("repository.name")
    return f"repos/{owner}/{repo}"


def _observation_path(value) -> List[str]:
    path = _observation_text(value, "path", 1024)
    parts = path.split("/")
    if len(parts) > 8 or "\\" in path or any(p in {"", ".", ".."} for p in parts):
        _observation_invalid("path")
    return parts


def _observation_metadata(data: Dict, endpoint: str) -> Tuple:
    owner = data.get("owner")
    if type(owner) is not dict:
        _observation_invalid("repository.owner")
    for value in (data.get("id"), owner.get("id")):
        if type(value) is not int or value <= 0:
            _observation_invalid("repository.id")
    canonical = _observation_endpoint(owner.get("login"), data.get("name"))
    full_name = canonical.removeprefix("repos/")
    if canonical.casefold() != endpoint.casefold() or data.get("full_name") != full_name:
        _observation_invalid("repository.full_name")
    branch = _observation_text(data.get("default_branch"), "repository.default_branch", 1024)
    if type(data.get("private")) is not bool:
        _observation_invalid("repository.private")
    return data["id"], owner["id"], full_name, branch, data["private"]


async def _observation_read(client, endpoint: str, field: str) -> Dict:
    try:
        data = await client._make_request("GET", endpoint, _observation=True)
    except (GitHubAPIError, aiohttp.ClientError, ValueError, TypeError, AttributeError, TimeoutError):
        _observation_invalid(field)
    if type(data) is not dict:
        _observation_invalid(field)
    return data


def _observation_entry(data: Dict, tree_sha: str, name: str, final: bool) -> Dict:
    if data.get("sha") != tree_sha or data.get("truncated") is not False:
        _observation_invalid("tree.identity")
    entries = data.get("tree")
    if type(entries) is not list or len(entries) > 4096 or any(type(e) is not dict for e in entries):
        _observation_invalid("tree.entries")
    selected = [entry for entry in entries if entry.get("path") == name]
    if len(selected) != 1:
        _observation_invalid("tree.path")
    entry = selected[0]
    modes = {"100644", "100755"} if final else {"040000"}
    if type(entry.get("mode")) is not str or entry["mode"] not in modes:
        _observation_invalid("tree.mode")
    if entry.get("type") != ("blob" if final else "tree"):
        _observation_invalid("tree.type")
    _observation_sha(entry.get("sha"), "tree.entry_sha")
    return entry


async def _observation_walk(client, endpoint: str, root_sha: str, parts: List[str]) -> Dict:
    tree_sha = root_sha
    for index, name in enumerate(parts):
        tree = await _observation_read(client, f"{endpoint}/git/trees/{tree_sha}", "tree.response")
        entry = _observation_entry(tree, tree_sha, name, index == len(parts) - 1)
        tree_sha = entry["sha"]
    return entry


def _observation_blob(data: Dict, blob_sha: str) -> bytes:
    size, encoded = data.get("size"), data.get("content")
    if data.get("sha") != blob_sha or data.get("encoding") != "base64":
        _observation_invalid("blob.identity")
    if type(size) is not int or not 0 <= size <= 16384:
        _observation_invalid("blob.size")
    if type(encoded) is not str or len(encoded) > 32768:
        _observation_invalid("blob.content")
    compact = encoded.replace("\r\n", "\n").replace("\n", "")
    try:
        content = base64.b64decode(compact, validate=True)
    except (ValueError, binascii.Error):
        _observation_invalid("blob.content")
    if len(content) != size or base64.b64encode(content).decode("ascii") != compact:
        _observation_invalid("blob.content")
    header = b"blob " + str(size).encode("ascii") + b"\0"
    if hashlib.sha1(header + content, usedforsecurity=False).hexdigest() != blob_sha:
        _observation_invalid("blob.hash")
    return content


@dataclass
class PullRequest:
    """Pull request information"""
    number: int
    title: str
    body: str
    state: PullRequestState
    head_branch: str
    base_branch: str
    author: str
    url: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Issue:
    """Issue information"""
    number: int
    title: str
    body: str
    state: IssueState
    author: str
    labels: List[str]
    url: str
    created_at: datetime
    updated_at: datetime


class GitHubAPIClient:
    """
    Complete GitHub API Client for repository management
    
    Provides comprehensive GitHub integration including:
    - Repository information and management
    - Pull request creation and management
    - Issue creation and management
    - Branch operations
    - Commit and file operations
    - Workflow and actions management
    """
    
    def __init__(self, token: Optional[str] = None, owner: str = "Foundup", repo: str = "Foundups-Agent"):
        """
        Initialize GitHub API client
        
        Args:
            token: GitHub personal access token (if None, will try to get from env)
            owner: Repository owner (default: "Foundup")
            repo: Repository name (default: "Foundups-Agent")
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.owner = owner
        self.repo = repo
        self.base_url = "https://api.github.com"
        
        if not self.token:
            logging.warning("GitHub token not provided. Some operations may fail.")
            
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "FoundUps-Agent-GitHub-Integration"
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                            *, _observation: bool = False) -> Dict[str, Any]:
        """
        Make HTTP request to GitHub API
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            data: Request data for POST/PUT/PATCH requests
            
        Returns:
            API response as dictionary
            
        Raises:
            GitHubAPIError: If request fails
        """
        if _observation:
            if method != "GET":
                _observation_invalid("request.method")
            return await self._read_observation_response(endpoint)
        if not self.session:
            raise GitHubAPIError("Client not initialized. Use async context manager.")
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                async with self.session.get(url) as response:
                    response_data = await response.json()
            elif method.upper() == "POST":
                async with self.session.post(url, json=data) as response:
                    response_data = await response.json()
            elif method.upper() == "PUT":
                async with self.session.put(url, json=data) as response:
                    response_data = await response.json()
            elif method.upper() == "PATCH":
                async with self.session.patch(url, json=data) as response:
                    response_data = await response.json()
            elif method.upper() == "DELETE":
                async with self.session.delete(url) as response:
                    response_data = await response.json() if response.status != 204 else {}
            else:
                raise GitHubAPIError(f"Unsupported HTTP method: {method}")
                
            if response.status >= 400:
                error_message = response_data.get("message", f"HTTP {response.status}")
                raise GitHubAPIError(f"GitHub API error: {error_message}")
                
            return response_data
            
        except aiohttp.ClientError as e:
            raise GitHubAPIError(f"Request failed: {str(e)}")

    async def _read_observation_response(self, endpoint: str) -> Dict[str, Any]:
        """Bound observation HTTP only; never follow a provider redirect."""
        if (self.base_url != "https://api.github.com" or not self.session
                or type(endpoint) is not str or not endpoint.startswith("repos/")
                or any(c in endpoint for c in "?#\\")):
            _observation_invalid("request.origin")
        timeout = aiohttp.ClientTimeout(total=5, connect=2, sock_connect=2, sock_read=2)
        async with self.session.get("https://api.github.com/" + endpoint,
                allow_redirects=False, auto_decompress=False,
                headers={"Accept-Encoding": "identity"}, timeout=timeout) as response:
            mime = response.content_type
            if (response.status != 200
                    or any(value.strip().lower() != "identity"
                           for value in response.headers.getall("Content-Encoding", ["identity"]))
                    or not (mime == "application/json" or (mime.startswith("application/") and mime.endswith("+json")))):
                _observation_invalid("response.headers")
            if response.content_length is not None and response.content_length > _OBSERVATION_BODY_LIMIT:
                _observation_invalid("response.size")
            body = bytearray()
            while True:
                chunk = await response.content.read(min(65536, _OBSERVATION_BODY_LIMIT + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > _OBSERVATION_BODY_LIMIT:
                    _observation_invalid("response.size")
            try:
                return json.loads(body.decode("utf-8"))
            except (ValueError, UnicodeError, RecursionError):
                _observation_invalid("response.json")

    # Repository Operations
    async def get_file_observation(self, file_path: str, *, commit_sha: Optional[str] = None) -> GitHubFileObservation:
        """Read a regular Git file; identity brackets are non-atomic and advisory."""
        endpoint = _observation_endpoint(self.owner, self.repo)
        parts = _observation_path(file_path)
        if commit_sha is not None:
            _observation_sha(commit_sha, "commit_sha")
        try:
            return await asyncio.wait_for(self._observe_file(endpoint, parts, file_path, commit_sha),
                                          timeout=_OBSERVATION_TIMEOUT)
        except asyncio.TimeoutError:
            _observation_invalid("request.deadline")

    async def _observe_file(self, endpoint: str, parts: List[str], file_path: str,
                            commit_sha: Optional[str]) -> GitHubFileObservation:
        """Use snapshotted selectors inside the whole-observation deadline."""
        identity = _observation_metadata(await _observation_read(self, endpoint, "repository.response"), endpoint)
        branch = identity[3]
        ref = await _observation_read(self, f"{endpoint}/git/ref/heads/{quote(branch, safe='')}", "ref.response")
        target = ref.get("object")
        if ref.get("ref") != f"refs/heads/{branch}" or type(target) is not dict or target.get("type") != "commit":
            _observation_invalid("ref.target")
        tip = _observation_sha(target.get("sha"), "ref.sha")
        selected = commit_sha if commit_sha is not None else tip
        commit = await _observation_read(self, f"{endpoint}/git/commits/{selected}", "commit.response")
        if commit.get("sha") != selected or type(commit.get("tree")) is not dict:
            _observation_invalid("commit.identity")
        root_sha = _observation_sha(commit["tree"].get("sha"), "commit.tree_sha")
        entry = await _observation_walk(self, endpoint, root_sha, parts)
        blob = await _observation_read(self, f"{endpoint}/git/blobs/{entry['sha']}", "blob.response")
        content = _observation_blob(blob, entry["sha"])
        after = _observation_metadata(await _observation_read(self, endpoint, "repository.response"), endpoint)
        if after != identity:
            _observation_invalid("repository.changed")
        return GitHubFileObservation(*identity, tip, selected, root_sha, file_path,
                                     entry["mode"], entry["sha"], content, len(content))

    async def get_repository(self) -> GitHubRepository:
        """Get repository information"""
        data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}")
        
        return GitHubRepository(
            owner=data["owner"]["login"],
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description"),
            private=data["private"],
            default_branch=data["default_branch"],
            url=data["html_url"]
        )
        
    async def get_branches(self) -> List[str]:
        """Get list of repository branches"""
        data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}/branches")
        return [branch["name"] for branch in data]
        
    async def create_branch(self, branch_name: str, source_branch: str = "main") -> bool:
        """
        Create a new branch
        
        Args:
            branch_name: Name of the new branch
            source_branch: Source branch to create from (default: "main")
            
        Returns:
            True if successful
        """
        # Get source branch SHA
        source_data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}/git/refs/heads/{source_branch}")
        source_sha = source_data["object"]["sha"]
        
        # Create new branch
        branch_data = {
            "ref": f"refs/heads/{branch_name}",
            "sha": source_sha
        }
        
        await self._make_request("POST", f"repos/{self.owner}/{self.repo}/git/refs", branch_data)
        return True
        
    # Pull Request Operations
    async def create_pull_request(self, title: str, body: str, head_branch: str, 
                                base_branch: str = "main") -> PullRequest:
        """
        Create a pull request
        
        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (default: "main")
            
        Returns:
            Created pull request
        """
        pr_data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        
        data = await self._make_request("POST", f"repos/{self.owner}/{self.repo}/pulls", pr_data)
        
        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=PullRequestState(data["state"]),
            head_branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            author=data["user"]["login"],
            url=data["html_url"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        )
        
    async def get_pull_requests(self, state: str = "open") -> List[PullRequest]:
        """Get list of pull requests"""
        data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}/pulls?state={state}")
        
        pull_requests = []
        for pr_data in data:
            pull_requests.append(PullRequest(
                number=pr_data["number"],
                title=pr_data["title"],
                body=pr_data["body"],
                state=PullRequestState(pr_data["state"]),
                head_branch=pr_data["head"]["ref"],
                base_branch=pr_data["base"]["ref"],
                author=pr_data["user"]["login"],
                url=pr_data["html_url"],
                created_at=datetime.fromisoformat(pr_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(pr_data["updated_at"].replace("Z", "+00:00"))
            ))
            
        return pull_requests
        
    async def merge_pull_request(self, pr_number: int, commit_title: Optional[str] = None,
                               commit_message: Optional[str] = None, merge_method: str = "merge") -> bool:
        """
        Merge a pull request
        
        Args:
            pr_number: Pull request number
            commit_title: Merge commit title
            commit_message: Merge commit message
            merge_method: Merge method ("merge", "squash", "rebase")
            
        Returns:
            True if successful
        """
        merge_data = {
            "commit_title": commit_title,
            "commit_message": commit_message,
            "merge_method": merge_method
        }
        
        await self._make_request("PUT", f"repos/{self.owner}/{self.repo}/pulls/{pr_number}/merge", merge_data)
        return True
        
    # Issue Operations
    async def create_issue(self, title: str, body: str, labels: Optional[List[str]] = None) -> Issue:
        """
        Create an issue
        
        Args:
            title: Issue title
            body: Issue description
            labels: List of labels
            
        Returns:
            Created issue
        """
        issue_data = {
            "title": title,
            "body": body
        }
        
        if labels:
            issue_data["labels"] = labels
            
        data = await self._make_request("POST", f"repos/{self.owner}/{self.repo}/issues", issue_data)
        
        return Issue(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=IssueState(data["state"]),
            author=data["user"]["login"],
            labels=[label["name"] for label in data["labels"]],
            url=data["html_url"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        )
        
    async def get_issues(self, state: str = "open") -> List[Issue]:
        """Get list of issues"""
        data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}/issues?state={state}")
        
        issues = []
        for issue_data in data:
            # Skip pull requests (they appear as issues in the API)
            if "pull_request" in issue_data:
                continue
                
            issues.append(Issue(
                number=issue_data["number"],
                title=issue_data["title"],
                body=issue_data["body"],
                state=IssueState(issue_data["state"]),
                author=issue_data["user"]["login"],
                labels=[label["name"] for label in issue_data["labels"]],
                url=issue_data["html_url"],
                created_at=datetime.fromisoformat(issue_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(issue_data["updated_at"].replace("Z", "+00:00"))
            ))
            
        return issues
        
    async def close_issue(self, issue_number: int) -> bool:
        """Close an issue"""
        issue_data = {"state": "closed"}
        await self._make_request("PATCH", f"repos/{self.owner}/{self.repo}/issues/{issue_number}", issue_data)
        return True
        
    # File and Commit Operations
    async def get_file_content(self, file_path: str, branch: str = "main") -> Tuple[str, str]:
        """
        Get file content from repository
        
        Args:
            file_path: Path to file in repository
            branch: Branch to get file from
            
        Returns:
            Tuple of (content, sha)
        """
        data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}/contents/{file_path}?ref={branch}")
        
        import base64
        content = base64.b64decode(data["content"]).decode("utf-8")
        return content, data["sha"]
        
    async def create_or_update_file(self, file_path: str, content: str, commit_message: str,
                                  branch: str = "main", sha: Optional[str] = None) -> bool:
        """
        Create or update a file in the repository
        
        Args:
            file_path: Path to file in repository
            content: File content
            commit_message: Commit message
            branch: Branch to commit to
            sha: File SHA (required for updates)
            
        Returns:
            True if successful
        """
        import base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        file_data = {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch
        }
        
        if sha:  # Update existing file
            file_data["sha"] = sha
            
        await self._make_request("PUT", f"repos/{self.owner}/{self.repo}/contents/{file_path}", file_data)
        return True
        
    async def get_commits(self, branch: str = "main", limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits"""
        data = await self._make_request("GET", 
                                      f"repos/{self.owner}/{self.repo}/commits?sha={branch}&per_page={limit}")
        return data
        
    # Workflow and Actions Operations
    async def get_workflows(self) -> List[Dict[str, Any]]:
        """Get repository workflows"""
        data = await self._make_request("GET", f"repos/{self.owner}/{self.repo}/actions/workflows")
        return data.get("workflows", [])
        
    async def trigger_workflow(self, workflow_id: str, ref: str = "main", inputs: Optional[Dict] = None) -> bool:
        """
        Trigger a workflow dispatch
        
        Args:
            workflow_id: Workflow ID or filename
            ref: Branch/tag reference
            inputs: Workflow inputs
            
        Returns:
            True if successful
        """
        dispatch_data = {
            "ref": ref
        }
        
        if inputs:
            dispatch_data["inputs"] = inputs
            
        await self._make_request("POST", 
                               f"repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/dispatches",
                               dispatch_data)
        return True
        
    async def get_workflow_runs(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workflow runs"""
        endpoint = f"repos/{self.owner}/{self.repo}/actions/runs"
        if workflow_id:
            endpoint = f"repos/{self.owner}/{self.repo}/actions/workflows/{workflow_id}/runs"
            
        data = await self._make_request("GET", endpoint)
        return data.get("workflow_runs", [])
        
    # Utility Methods
    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check GitHub API rate limit status"""
        return await self._make_request("GET", "rate_limit")
        
    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        return await self._make_request("GET", "user")
        
    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self.token is not None


# Convenience Functions for Common Operations
async def create_feature_branch_and_pr(title: str, description: str, branch_name: Optional[str] = None,
                                     token: Optional[str] = None) -> Tuple[str, PullRequest]:
    """
    Convenience function to create a feature branch and pull request
    
    Args:
        title: PR title
        description: PR description  
        branch_name: Branch name (auto-generated if None)
        token: GitHub token
        
    Returns:
        Tuple of (branch_name, pull_request)
    """
    if not branch_name:
        # Generate branch name from title
        branch_name = f"feature/{title.lower().replace(' ', '-').replace('_', '-')}"
        
    async with GitHubAPIClient(token=token) as client:
        # Create branch
        await client.create_branch(branch_name)
        
        # Create pull request
        pr = await client.create_pull_request(title, description, branch_name)
        
        return branch_name, pr


async def create_issue_for_bug(title: str, description: str, steps_to_reproduce: str,
                             token: Optional[str] = None) -> Issue:
    """
    Convenience function to create a bug report issue
    
    Args:
        title: Bug title
        description: Bug description
        steps_to_reproduce: Steps to reproduce the bug
        token: GitHub token
        
    Returns:
        Created issue
    """
    bug_body = f"""
## Description
{description}

## Steps to Reproduce
{steps_to_reproduce}

## Environment
- OS: Windows
- Repository: Foundups-Agent
- Created: {datetime.now().isoformat()}

---
*This issue was created automatically by the FoundUps Agent system.*
"""
    
    async with GitHubAPIClient(token=token) as client:
        return await client.create_issue(title, bug_body, labels=["bug"])


async def auto_commit_and_pr_current_changes(commit_message: str, pr_title: str, pr_description: str,
                                           token: Optional[str] = None) -> PullRequest:
    """
    Automatically commit current changes and create a pull request
    
    Args:
        commit_message: Commit message
        pr_title: PR title
        pr_description: PR description
        token: GitHub token
        
    Returns:
        Created pull request
    """
    import subprocess
    from pathlib import Path
    
    # Get current directory (should be repo root)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    
    # Generate branch name
    branch_name = f"auto-update/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        # Create and checkout new branch
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_root, check=True)
        
        # Add and commit changes
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_root, check=True)
        
        # Push branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=repo_root, check=True)
        
        # Create pull request
        async with GitHubAPIClient(token=token) as client:
            pr = await client.create_pull_request(pr_title, pr_description, branch_name)
            return pr
            
    except subprocess.CalledProcessError as e:
        raise GitHubAPIError(f"Git operation failed: {e}")
