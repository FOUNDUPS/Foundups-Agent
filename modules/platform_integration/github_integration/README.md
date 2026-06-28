# GitHub Integration Module

**Complete GitHub API integration and automation for FoundUps Agent**

---

## [TARGET] Module Overview

**Module Name:** `github_integration`  
**Domain:** `platform_integration`  
**Purpose:** Comprehensive GitHub API integration with automated workflows for WSP-compliant development  
**Phase:** Production Ready (v1.0.0)  

## [ROCKET] Core Functionality

### **RedDog Permission Probe (read-only)**
- **`probe_repo_permission()`**: Read-only GitHub permission snapshot for governed work orders
- **Conservative mapping**: `write`/`maintain`/`admin` -> `can_write`; `unknown` fail-closed
- **No mutation**: allowlisted `gh` GET commands only; injectable mock backend for tests

### **GitHub API Client**
- **Complete REST API Coverage**: Repository, pull requests, issues, branches, commits, workflows
- **Async/Await Architecture**: High-performance async operations with aiohttp
- **Authentication**: GitHub personal access token support with rate limit handling
- **Error Handling**: Comprehensive error handling with custom exceptions

### **Automated Workflows**
- **WSP Compliance PR Creation**: Automatic pull requests for WSP protocol updates
- **Module Update Automation**: Automated PRs for module version updates
- **Violation Issue Creation**: Automatic issue creation for WSP violations
- **Documentation Synchronization**: Automated doc syncing and PR creation
- **Release Management**: Automated release PR creation and management

### **Repository Management**
- **Branch Operations**: Create, list, and manage branches
- **Pull Request Management**: Create, merge, monitor, and auto-merge PRs
- **Issue Management**: Create, close, and track issues with labels
- **File Operations**: Read, create, and update files via API
- **Workflow Integration**: Trigger and monitor GitHub Actions workflows

## [U+1F50C] Interface Definition

### **Core Classes**

```python
class GitHubAPIClient:
    """Complete GitHub API client with full REST API coverage"""
    
    # Repository Operations
    async def get_repository() -> GitHubRepository
    async def get_branches() -> List[str]
    async def create_branch(branch_name: str, source_branch: str = "main") -> bool
    
    # Pull Request Operations  
    async def create_pull_request(title: str, body: str, head_branch: str, base_branch: str = "main") -> PullRequest
    async def get_pull_requests(state: str = "open") -> List[PullRequest]
    async def merge_pull_request(pr_number: int, commit_title: str = None, commit_message: str = None, merge_method: str = "merge") -> bool
    
    # Issue Operations
    async def create_issue(title: str, body: str, labels: List[str] = None) -> Issue
    async def get_issues(state: str = "open") -> List[Issue]
    async def close_issue(issue_number: int) -> bool
    
    # File Operations
    async def get_file_content(file_path: str, branch: str = "main") -> Tuple[str, str]
    async def create_or_update_file(file_path: str, content: str, commit_message: str, branch: str = "main", sha: str = None) -> bool
    
    # Workflow Operations
    async def get_workflows() -> List[Dict[str, Any]]
    async def trigger_workflow(workflow_id: str, ref: str = "main", inputs: Dict = None) -> bool
    async def get_workflow_runs(workflow_id: str = None) -> List[Dict[str, Any]]

class GitHubAutomation:
    """High-level automation for common GitHub workflows"""
    
    async def auto_create_wsp_compliance_pr(wsp_number: int, changes_description: str, files_changed: List[str]) -> str
    async def auto_create_module_update_pr(module_name: str, module_domain: str, update_description: str, version: str) -> str
    async def auto_create_violation_issue(violation_type: str, violation_description: str, affected_files: List[str], wsp_protocol: int = None) -> str
    async def auto_sync_documentation(docs_path: Path) -> str
    async def auto_create_release_pr(version: str, release_notes: str, breaking_changes: List[str] = None) -> str
    async def monitor_pr_status(pr_number: int, callback: Callable = None) -> Dict[str, Any]
    async def auto_merge_ready_prs(max_prs: int = 5) -> List[str]
```

### **Data Structures**

```python
@dataclass
class GitHubRepository:
    owner: str
    name: str
    full_name: str
    description: Optional[str]
    private: bool
    default_branch: str
    url: str

@dataclass  
class PullRequest:
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
    number: int
    title: str
    body: str
    state: IssueState
    author: str
    labels: List[str]
    url: str
    created_at: datetime
    updated_at: datetime
```

## [U+1F3D7]️ WSP Integration

- **WSP 3**: Platform Integration Domain - External API integration function
- **WSP 11**: Clean interface definition for modular consumption
- **WSP 22**: ModLog management integration for automated documentation
- **WSP 34**: Git Operations Protocol integration for repository management
- **WSP 54**: Agent coordination for automated workflows
- **WSP 71**: Secrets management for GitHub API credentials

## [ROCKET] Quick Start

### **Basic GitHub API Usage**

```python
import asyncio
from modules.platform_integration.github_integration import GitHubAPIClient

async def main():
    # Initialize client with token
    async with GitHubAPIClient(token="your-github-token") as client:
        # Get repository info
        repo = await client.get_repository()
        print(f"Repository: {repo.full_name}")
        
        # Create a new branch
        await client.create_branch("feature/new-feature")
        
        # Create a pull request
        pr = await client.create_pull_request(
            title="Add new feature",
            body="This PR adds a new feature to the system",
            head_branch="feature/new-feature"
        )
        print(f"Created PR: {pr.url}")

asyncio.run(main())
```

### **Automated Workflow Usage**

```python
import asyncio
from modules.platform_integration.github_integration import GitHubAutomation

async def main():
    automation = GitHubAutomation(token="your-github-token")
    
    # Automatically create WSP compliance PR
    pr_url = await automation.auto_create_wsp_compliance_pr(
        wsp_number=34,
        changes_description="Updated git operations protocol",
        files_changed=["WSP_framework/src/WSP_34_Git_Operations_Protocol.md"]
    )
    print(f"Created WSP compliance PR: {pr_url}")
    
    # Create violation issue
    issue_url = await automation.auto_create_violation_issue(
        violation_type="Architecture Violation",
        violation_description="Duplicate module structure found",
        affected_files=["modules/platform_integration/presence_aggregator/"],
        wsp_protocol=57
    )
    print(f"Created violation issue: {issue_url}")

asyncio.run(main())
```

### **Convenience Functions**

```python
import asyncio
from modules.platform_integration.github_integration import create_feature_branch_and_pr, create_issue_for_bug

async def main():
    # Quick feature branch and PR creation
    branch_name, pr = await create_feature_branch_and_pr(
        title="Fix authentication bug",
        description="Fixes issue with OAuth token refresh",
        token="your-github-token"
    )
    print(f"Created branch: {branch_name}, PR: {pr.url}")
    
    # Quick bug report issue
    issue = await create_issue_for_bug(
        title="Login fails with special characters",
        description="Users cannot login when password contains special characters",
        steps_to_reproduce="1. Use password with @#$ characters\n2. Try to login\n3. See error",
        token="your-github-token"
    )
    print(f"Created bug report: {issue.url}")

asyncio.run(main())
```

## [TOOL] Configuration

### **Environment Variables**

```bash
# GitHub API credentials
GITHUB_TOKEN=your_personal_access_token

# Repository settings (optional, defaults provided)
GITHUB_OWNER=Foundup
GITHUB_REPO=Foundups-Agent
```

### **Token Requirements**

Your GitHub personal access token needs the following scopes:
- `repo` - Full repository access
- `workflow` - GitHub Actions workflow access
- `issues` - Issues read/write access
- `pull_requests` - Pull requests read/write access

## [DATA] Automated Workflows

### **WSP Compliance Automation**
- Automatically creates PRs for WSP protocol updates
- Includes compliance checklists and validation
- Tags with appropriate WSP protocol labels

### **Module Update Automation**
- Tracks module version changes
- Creates standardized update PRs
- Includes testing and documentation checklists

### **Violation Detection Integration**
- Creates issues for WSP violations automatically
- Categorizes by violation type and priority
- Includes resolution guidance

### **Documentation Synchronization**
- Monitors documentation changes
- Creates PRs for doc updates
- Maintains consistency across README, ROADMAP, and ModLog files

### **Release Management**
- Automates release PR creation
- Includes changelogs and breaking changes
- Manages version tagging and release notes

## [U+1F9EA] Testing

### **Run Tests**
```bash
cd modules/platform_integration/github_integration/
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### **Integration Testing**
```bash
# Test with real GitHub API (requires token)
GITHUB_TOKEN=your_token python -m pytest tests/test_integration.py -v
```

## [UP] Performance Metrics

### **Target Performance**
- **API Response Time**: <1s for standard operations
- **Bulk Operations**: Handle 100+ items efficiently
- **Rate Limit Compliance**: Automatic rate limit handling
- **Concurrent Operations**: Support for parallel API calls

### **Monitoring**
- GitHub API rate limit tracking
- Request/response logging
- Error rate monitoring
- Automated workflow success rates

## [U+1F510] Security & Privacy

### **Security Features**
- Token-based authentication with secure storage
- Rate limit compliance to prevent API abuse
- Input validation and sanitization
- Secure credential management

### **Privacy Considerations**
- No sensitive data logging
- GitHub API compliance
- User consent for automated actions
- Audit logging for all operations

## [LINK] Integration Points

### **WRE Integration**
- Integrated with WRE Core for autonomous operations
- WSP 34 compliance for git operations
- Agent coordination for automated workflows

### **Module Ecosystem**
- Coordinates with all platform integration modules
- Supports cross-module automation
- Integrates with violation detection systems

## [NOTE] API Reference

### **Core Methods**

```python
# Repository Management
async def get_repository() -> GitHubRepository
async def get_branches() -> List[str]  
async def create_branch(branch_name: str, source_branch: str = "main") -> bool

# Pull Request Management
async def create_pull_request(title: str, body: str, head_branch: str, base_branch: str = "main") -> PullRequest
async def get_pull_requests(state: str = "open") -> List[PullRequest]
async def merge_pull_request(pr_number: int, **kwargs) -> bool

# Issue Management
async def create_issue(title: str, body: str, labels: List[str] = None) -> Issue
async def get_issues(state: str = "open") -> List[Issue]
async def close_issue(issue_number: int) -> bool

# File Operations
async def get_file_content(file_path: str, branch: str = "main") -> Tuple[str, str]
async def create_or_update_file(file_path: str, content: str, commit_message: str, **kwargs) -> bool

# Workflow Operations
async def get_workflows() -> List[Dict[str, Any]]
async def trigger_workflow(workflow_id: str, ref: str = "main", inputs: Dict = None) -> bool
async def get_workflow_runs(workflow_id: str = None) -> List[Dict[str, Any]]

# Automation Methods
async def auto_create_wsp_compliance_pr(wsp_number: int, changes_description: str, files_changed: List[str]) -> str
async def auto_create_module_update_pr(module_name: str, module_domain: str, update_description: str, version: str) -> str
async def auto_create_violation_issue(violation_type: str, violation_description: str, affected_files: List[str], wsp_protocol: int = None) -> str
```

## [TARGET] Use Cases

### **Development Automation**
- Automated PR creation for code changes
- WSP compliance validation and PR creation
- Module update automation
- Documentation synchronization

### **Issue Management** 
- Automated violation issue creation
- Bug report automation
- Feature request management
- Issue lifecycle automation

### **Release Management**
- Automated release PR creation
- Changelog generation
- Version tagging automation
- Release note management

### **Repository Management**
- Branch cleanup automation
- PR monitoring and auto-merge
- Workflow trigger automation
- Repository health monitoring

---

**Module**: GitHub Integration  
**Version**: 1.0.0  
**Domain**: platform_integration  
**WSP Compliance**: [OK] Fully compliant  
**Maintainer**: FoundUps Agent Development Team

**[BOT] Enhanced with [Claude Code](https://claude.ai/code)**

**Co-Authored-By: Claude <noreply@anthropic.com>**