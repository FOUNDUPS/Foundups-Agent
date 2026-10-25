"""
Tests for GitHub API Client
Comprehensive testing of all GitHub API client functionality with mocked responses.
"""

import pytest
import aiohttp
import base64
import copy
import dataclasses
import hashlib
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from aioresponses import aioresponses

from modules.platform_integration.github_integration.src.github_api_client import (
    GitHubAPIClient,
    GitHubAPIError,
    GitHubRepository,
    PullRequest,
    Issue,
    PullRequestState,
    IssueState
)


@pytest.fixture
def github_client():
    """Create GitHub API client for testing"""
    return GitHubAPIClient(token="test_token", owner="TestOwner", repo="TestRepo")


@pytest.fixture
def mock_repository_response():
    """Mock repository API response"""
    return {
        "name": "TestRepo",
        "owner": {"login": "TestOwner"},
        "full_name": "TestOwner/TestRepo", 
        "description": "Test repository",
        "private": False,
        "default_branch": "main",
        "html_url": "https://github.com/TestOwner/TestRepo"
    }


@pytest.fixture
def mock_pull_request_response():
    """Mock pull request API response"""
    return {
        "number": 123,
        "title": "Test PR",
        "body": "Test PR body",
        "state": "open",
        "head": {"ref": "feature/test"},
        "base": {"ref": "main"},
        "user": {"login": "testuser"},
        "html_url": "https://github.com/TestOwner/TestRepo/pull/123",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_issue_response():
    """Mock issue API response"""
    return {
        "number": 456,
        "title": "Test Issue",
        "body": "Test issue body",
        "state": "open",
        "user": {"login": "testuser"},
        "labels": [{"name": "bug"}, {"name": "high-priority"}],
        "html_url": "https://github.com/TestOwner/TestRepo/issues/456",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


class TestGitHubAPIClientInit:
    """Test GitHub API client initialization"""
    
    def test_init_with_token(self):
        client = GitHubAPIClient(token="test_token", owner="TestOwner", repo="TestRepo")
        assert client.token == "test_token"
        assert client.owner == "TestOwner"
        assert client.repo == "TestRepo"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "token test_token"
    
    def test_init_without_token(self):
        with patch.dict('os.environ', {}, clear=True):
            client = GitHubAPIClient(owner="TestOwner", repo="TestRepo")
            assert client.token is None
            assert "Authorization" not in client.headers
    
    def test_init_with_env_token(self):
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'env_token'}):
            client = GitHubAPIClient(owner="TestOwner", repo="TestRepo")
            assert client.token == "env_token"


class TestGitHubAPIClientRepositoryOperations:
    """Test repository operations"""
    
    @pytest.mark.asyncio
    async def test_get_repository_success(self, github_client, mock_repository_response):
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo',
                payload=mock_repository_response
            )
            
            async with github_client as client:
                repo = await client.get_repository()
                
            assert isinstance(repo, GitHubRepository)
            assert repo.name == "TestRepo"
            assert repo.owner == "TestOwner"
            assert repo.full_name == "TestOwner/TestRepo"
            assert repo.description == "Test repository"
            assert repo.private is False
            assert repo.default_branch == "main"
    
    @pytest.mark.asyncio
    async def test_get_repository_api_error(self, github_client):
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo',
                status=404,
                payload={"message": "Not Found"}
            )
            
            async with github_client as client:
                with pytest.raises(GitHubAPIError, match="GitHub API error: Not Found"):
                    await client.get_repository()
    
    @pytest.mark.asyncio
    async def test_get_branches_success(self, github_client):
        branches_response = [
            {"name": "main"},
            {"name": "develop"},
            {"name": "feature/test"}
        ]
        
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo/branches',
                payload=branches_response
            )
            
            async with github_client as client:
                branches = await client.get_branches()
                
            assert branches == ["main", "develop", "feature/test"]
    
    @pytest.mark.asyncio
    async def test_create_branch_success(self, github_client):
        # Mock getting source branch SHA
        source_ref_response = {
            "object": {"sha": "abc123"}
        }
        
        # Mock creating new branch
        create_ref_response = {
            "ref": "refs/heads/feature/new-feature",
            "object": {"sha": "abc123"}
        }
        
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo/git/refs/heads/main',
                payload=source_ref_response
            )
            m.post(
                'https://api.github.com/repos/TestOwner/TestRepo/git/refs',
                payload=create_ref_response
            )
            
            async with github_client as client:
                result = await client.create_branch("feature/new-feature")
                
            assert result is True


class TestGitHubAPIClientPullRequestOperations:
    """Test pull request operations"""
    
    @pytest.mark.asyncio
    async def test_create_pull_request_success(self, github_client, mock_pull_request_response):
        with aioresponses() as m:
            m.post(
                'https://api.github.com/repos/TestOwner/TestRepo/pulls',
                payload=mock_pull_request_response
            )
            
            async with github_client as client:
                pr = await client.create_pull_request(
                    title="Test PR",
                    body="Test PR body",
                    head_branch="feature/test"
                )
                
            assert isinstance(pr, PullRequest)
            assert pr.number == 123
            assert pr.title == "Test PR"
            assert pr.body == "Test PR body"
            assert pr.state == PullRequestState.OPEN
            assert pr.head_branch == "feature/test"
            assert pr.base_branch == "main"
    
    @pytest.mark.asyncio
    async def test_get_pull_requests_success(self, github_client, mock_pull_request_response):
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo/pulls?state=open',
                payload=[mock_pull_request_response]
            )
            
            async with github_client as client:
                prs = await client.get_pull_requests()
                
            assert len(prs) == 1
            assert isinstance(prs[0], PullRequest)
            assert prs[0].number == 123
    
    @pytest.mark.asyncio
    async def test_merge_pull_request_success(self, github_client):
        merge_response = {
            "sha": "merged_sha",
            "merged": True,
            "message": "Pull Request successfully merged"
        }
        
        with aioresponses() as m:
            m.put(
                'https://api.github.com/repos/TestOwner/TestRepo/pulls/123/merge',
                payload=merge_response
            )
            
            async with github_client as client:
                result = await client.merge_pull_request(123)
                
            assert result is True


class TestGitHubAPIClientIssueOperations:
    """Test issue operations"""
    
    @pytest.mark.asyncio
    async def test_create_issue_success(self, github_client, mock_issue_response):
        with aioresponses() as m:
            m.post(
                'https://api.github.com/repos/TestOwner/TestRepo/issues',
                payload=mock_issue_response
            )
            
            async with github_client as client:
                issue = await client.create_issue(
                    title="Test Issue",
                    body="Test issue body",
                    labels=["bug", "high-priority"]
                )
                
            assert isinstance(issue, Issue)
            assert issue.number == 456
            assert issue.title == "Test Issue"
            assert issue.body == "Test issue body"
            assert issue.state == IssueState.OPEN
            assert issue.labels == ["bug", "high-priority"]
    
    @pytest.mark.asyncio
    async def test_get_issues_success(self, github_client, mock_issue_response):
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo/issues?state=open',
                payload=[mock_issue_response]
            )
            
            async with github_client as client:
                issues = await client.get_issues()
                
            assert len(issues) == 1
            assert isinstance(issues[0], Issue)
            assert issues[0].number == 456
    
    @pytest.mark.asyncio
    async def test_close_issue_success(self, github_client):
        close_response = {
            "state": "closed"
        }
        
        with aioresponses() as m:
            m.patch(
                'https://api.github.com/repos/TestOwner/TestRepo/issues/456',
                payload=close_response
            )
            
            async with github_client as client:
                result = await client.close_issue(456)
                
            assert result is True


class TestGitHubAPIClientFileOperations:
    """Test file operations"""
    
    @pytest.mark.asyncio
    async def test_get_file_content_success(self, github_client):
        import base64
        
        file_content = "# Test File\nThis is a test file."
        encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
        
        file_response = {
            "content": encoded_content,
            "sha": "file_sha_123"
        }
        
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo/contents/test.md?ref=main',
                payload=file_response
            )
            
            async with github_client as client:
                content, sha = await client.get_file_content("test.md")
                
            assert content == file_content
            assert sha == "file_sha_123"
    
    @pytest.mark.asyncio
    async def test_create_or_update_file_success(self, github_client):
        file_response = {
            "commit": {
                "sha": "commit_sha_123"
            }
        }
        
        with aioresponses() as m:
            m.put(
                'https://api.github.com/repos/TestOwner/TestRepo/contents/test.md',
                payload=file_response
            )
            
            async with github_client as client:
                result = await client.create_or_update_file(
                    file_path="test.md",
                    content="# Updated Test File",
                    commit_message="Update test file"
                )
                
            assert result is True


class TestGitHubAPIClientWorkflowOperations:
    """Test workflow operations"""
    
    @pytest.mark.asyncio
    async def test_get_workflows_success(self, github_client):
        workflows_response = {
            "workflows": [
                {
                    "id": 123,
                    "name": "CI",
                    "path": ".github/workflows/ci.yml"
                }
            ]
        }
        
        with aioresponses() as m:
            m.get(
                'https://api.github.com/repos/TestOwner/TestRepo/actions/workflows',
                payload=workflows_response
            )
            
            async with github_client as client:
                workflows = await client.get_workflows()
                
            assert len(workflows) == 1
            assert workflows[0]["name"] == "CI"
    
    @pytest.mark.asyncio
    async def test_trigger_workflow_success(self, github_client):
        with aioresponses() as m:
            m.post(
                'https://api.github.com/repos/TestOwner/TestRepo/actions/workflows/ci.yml/dispatches',
                status=204
            )
            
            async with github_client as client:
                result = await client.trigger_workflow("ci.yml", ref="main")
                
            assert result is True


class TestGitHubAPIClientUtilityMethods:
    """Test utility methods"""
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_success(self, github_client):
        rate_limit_response = {
            "resources": {
                "core": {
                    "limit": 5000,
                    "remaining": 4999,
                    "reset": 1640995200
                }
            }
        }
        
        with aioresponses() as m:
            m.get(
                'https://api.github.com/rate_limit',
                payload=rate_limit_response
            )
            
            async with github_client as client:
                rate_limit = await client.check_rate_limit()
                
            assert rate_limit["resources"]["core"]["limit"] == 5000
    
    @pytest.mark.asyncio
    async def test_get_user_success(self, github_client):
        user_response = {
            "login": "testuser",
            "id": 123,
            "name": "Test User"
        }
        
        with aioresponses() as m:
            m.get(
                'https://api.github.com/user',
                payload=user_response
            )
            
            async with github_client as client:
                user = await client.get_user()
                
            assert user["login"] == "testuser"
    
    def test_is_authenticated_with_token(self):
        client = GitHubAPIClient(token="test_token")
        assert client.is_authenticated() is True
    
    def test_is_authenticated_without_token(self):
        client = GitHubAPIClient(token=None)
        assert client.is_authenticated() is False


class TestGitHubAPIClientErrorHandling:
    """Test error handling"""
    
    @pytest.mark.asyncio
    async def test_request_without_session(self, github_client):
        with pytest.raises(GitHubAPIError, match="Client not initialized"):
            await github_client._make_request("GET", "repos/test/test")
    
    @pytest.mark.asyncio
    async def test_unsupported_http_method(self, github_client):
        with aioresponses():
            async with github_client as client:
                with pytest.raises(GitHubAPIError, match="Unsupported HTTP method"):
                    await client._make_request("TRACE", "repos/test/test")
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, github_client):
        with aioresponses() as m:
            m.get('https://api.github.com/repos/TestOwner/TestRepo', exception=aiohttp.ClientError("Network error"))
            
            async with github_client as client:
                with pytest.raises(GitHubAPIError, match="Request failed"):
                    await client.get_repository()


class TestGitHubAPIClientContextManager:
    """Test async context manager"""
    
    @pytest.mark.asyncio
    async def test_context_manager_creates_session(self, github_client):
        assert github_client.session is None
        
        async with github_client as client:
            assert client.session is not None
            
        assert github_client.session is None or github_client.session.closed
    
    @pytest.mark.asyncio
    async def test_context_manager_closes_session(self, github_client):
        async with github_client as client:
            session = client.session
            assert not session.closed
            
        assert session.closed

_OBSERVATION_SENTINEL = "provider-private-sentinel-must-not-appear"


def _git_blob_sha(content):
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def _observation_case(path="proof/challenge.bin", content=b"project evidence\n", commit_sha=None):
    parts = path.split("/")
    tip, selected = "a" * 40, commit_sha or "a" * 40
    trees = [format(i + 100, "040x") for i in range(len(parts))]
    blob = _git_blob_sha(content)
    meta = dict(id=101, owner=dict(id=202, login="TestOwner"), name="TestRepo",
                full_name="TestOwner/TestRepo", default_branch="release/ready", private=False)
    endpoints = ["repos/TestOwner/TestRepo", "repos/TestOwner/TestRepo/git/ref/heads/release%2Fready",
                 "repos/TestOwner/TestRepo/git/commits/" + selected]
    responses = [copy.deepcopy(meta), {"ref": "refs/heads/" + meta["default_branch"],
                                     "object": {"type": "commit", "sha": tip}},
                 {"sha": selected, "tree": {"sha": trees[0]}}]
    for i, part in enumerate(parts):
        final = i == len(parts) - 1
        entry = dict(path=part, mode="100644" if final else "040000",
                     type="blob" if final else "tree", sha=blob if final else trees[i + 1])
        endpoints.append("repos/TestOwner/TestRepo/git/trees/" + trees[i])
        responses.append(dict(sha=trees[i], truncated=False, tree=[entry]))
    endpoints += ["repos/TestOwner/TestRepo/git/blobs/" + blob, "repos/TestOwner/TestRepo"]
    responses += [dict(sha=blob, encoding="base64", size=len(content),
                       content=base64.b64encode(content).decode()), copy.deepcopy(meta)]
    expected = dict(repository_id=101, owner_id=202, repository_full_name=meta["full_name"],
                    default_branch=meta["default_branch"], private=False,
                    observed_default_commit_sha=tip, commit_sha=selected, tree_sha=trees[0],
                    path=path, mode="100644", blob_sha=blob, content=content, size_bytes=len(content))
    return dict(path=path, endpoints=endpoints, responses=responses, expected=expected)


def _assert_observation(result, expected):
    from modules.platform_integration.github_integration.src import github_api_client as api
    assert type(result) is api.GitHubFileObservation
    assert {f.name for f in dataclasses.fields(result)} == set(expected)
    for name, value in expected.items():
        assert type(getattr(result, name)) is type(value)
        assert getattr(result, name) == value


async def _mock_observation(client, case, **kwargs):
    request = AsyncMock(side_effect=case["responses"])
    with patch.object(client, "_make_request", request):
        result = await client.get_file_observation(case["path"], **kwargs)
    assert [c.args[:2] for c in request.call_args_list] == [("GET", p) for p in case["endpoints"]]
    assert request.await_count <= 13
    return result


def _assert_observation_error(error):
    assert str(error).startswith("Invalid file observation: ")
    assert _OBSERVATION_SENTINEL not in str(error)
    assert "proof/challenge.bin" not in str(error)
    assert error.__cause__ is None
    if error.__context__ is not None:
        assert error.__suppress_context__


async def _reject_observation(client, case):
    request = AsyncMock(side_effect=case["responses"])
    with patch.object(client, "_make_request", request), pytest.raises(GitHubAPIError) as caught:
        await client.get_file_observation(case["path"])
    _assert_observation_error(caught.value)
    assert request.await_count <= 13


class TestGitHubFileObservation:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("change", ["missing_ref", "wrong_ref", "tag", "pad_bits"])
    async def test_exact_reference_and_canonical_blob(self, github_client, change):
        case = _observation_case(content=b"f")
        if change == "missing_ref":
            del case["responses"][1]["ref"]
        elif change == "wrong_ref":
            case["responses"][1]["ref"] = "refs/heads/another"
        elif change == "tag":
            case["responses"][1]["object"]["type"] = "tag"
        else:
            encoded = case["responses"][-2]["content"]
            case["responses"][-2]["content"] = encoded[0] + chr(ord(encoded[1]) + 1) + encoded[2:]
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("content", [b"", b"f"])
    async def test_root_regular_file_and_empty_blob(self, github_client, content):
        case = _observation_case(path="proof.bin", content=content)
        result = await _mock_observation(github_client, case)
        _assert_observation(result, case["expected"])

    def test_legacy_repository_seven_field_constructor_unchanged(self):
        repo = GitHubRepository("TestOwner", "TestRepo", "TestOwner/TestRepo", None, False, "main", "public-url")
        assert [f.name for f in dataclasses.fields(repo)] == [
            "owner", "name", "full_name", "description", "private", "default_branch", "url"]
        repo.name = "Renamed"
        assert repo.name == "Renamed"

    @pytest.mark.asyncio
    async def test_legacy_content_explicit_ref_still_returns_tuple(self, github_client):
        content, ref = "legacy text", "b" * 40
        with aioresponses() as mocked:
            mocked.get("https://api.github.com/repos/TestOwner/TestRepo/contents/test.md?ref=" + ref,
                       payload=dict(content=base64.b64encode(content.encode()).decode(), sha="legacy-opaque"))
            async with github_client as client:
                result = await client.get_file_content("test.md", branch=ref)
        assert type(result) is tuple and result == (content, "legacy-opaque")

    @pytest.mark.asyncio
    async def test_full_gitdata_route_and_frozen_scalar_record(self, github_client):
        case = _observation_case(path="proof/question #?.bin")
        with aioresponses() as mocked:
            for endpoint, payload in zip(case["endpoints"], case["responses"]):
                mocked.get("https://api.github.com/" + endpoint, payload=payload)
            async with github_client as client:
                result = await client.get_file_observation(case["path"])
            seen = sorted(str(url) for (method, url), calls in mocked.requests.items() for _ in calls)
            assert all(method == "GET" for method, _ in mocked.requests)
        assert seen == sorted("https://api.github.com/" + p for p in case["endpoints"])
        _assert_observation(result, case["expected"])
        assert len(dataclasses.fields(result)) == 13 and not hasattr(result, "__dict__")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.path = "changed"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("wrapping,mode", [("\n", "100644"), ("\r\n", "100755")])
    async def test_binary_wrapped_content_full_route(self, github_client, wrapping, mode):
        case = _observation_case(content=b"\0binary\xff\n" * 30)
        encoded = case["responses"][-2]["content"]
        case["responses"][-2]["content"] = wrapping.join(encoded[i:i+64] for i in range(0, len(encoded), 64))
        case["responses"][-3]["tree"][0]["mode"] = case["expected"]["mode"] = mode
        with aioresponses() as mocked:
            for endpoint, payload in zip(case["endpoints"], case["responses"]):
                mocked.get("https://api.github.com/" + endpoint, payload=payload)
            async with github_client as client:
                result = await client.get_file_observation(case["path"])
        _assert_observation(result, case["expected"])

    @pytest.mark.asyncio
    async def test_explicit_historical_commit_is_labeled(self, github_client):
        historical = "b" * 40
        case = _observation_case(commit_sha=historical)
        result = await _mock_observation(github_client, case, commit_sha=historical)
        _assert_observation(result, case["expected"])
        assert result.commit_sha != result.observed_default_commit_sha

    @pytest.mark.asyncio
    async def test_maximum_depth_bytes_and_call_bound(self, github_client):
        case = _observation_case(path="/".join(["x"] * 8), content=b"x" * 16384)
        result = await _mock_observation(github_client, case)
        _assert_observation(result, case["expected"])
        assert len(case["endpoints"]) == 13

    @pytest.mark.asyncio
    async def test_private_label_and_detached_result(self, github_client):
        case = _observation_case()
        case["responses"][0]["private"] = case["responses"][-1]["private"] = True
        case["expected"]["private"] = True
        result = await _mock_observation(github_client, case)
        case["responses"][0]["owner"]["id"] = 999
        case["responses"][-2]["content"] = "changed"
        _assert_observation(result, case["expected"])

    @pytest.mark.asyncio
    async def test_repository_selectors_are_snapshotted_across_awaits(self, github_client):
        case = _observation_case()
        pending = iter(case["responses"])
        async def reply(method, endpoint):
            github_client.owner, github_client.repo = "OtherOwner", "OtherRepo"
            return next(pending)
        request = AsyncMock(side_effect=reply)
        with patch.object(github_client, "_make_request", request):
            result = await github_client.get_file_observation(case["path"])
        assert [c.args[:2] for c in request.call_args_list] == [("GET", p) for p in case["endpoints"]]
        _assert_observation(result, case["expected"])

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field,value", [("id", True), ("id", 0), ("id", "101"),
        ("owner", {"id": 202.0, "login": "TestOwner"}), ("private", 0),
        ("full_name", "Other/TestRepo"), ("default_branch", ""), ("default_branch", "bad\nbranch")])
    async def test_malformed_repository_metadata(self, github_client, field, value):
        case = _observation_case()
        case["responses"][0][field] = value
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field", ["id", "owner_id", "name", "default_branch", "private"])
    async def test_final_metadata_drift_is_refused(self, github_client, field):
        case = _observation_case()
        final = case["responses"][-1]
        if field == "owner_id":
            final["owner"]["id"] += 1
        elif field == "name":
            final["name"], final["full_name"] = "testrepo", "TestOwner/testrepo"
        else:
            final[field] = {"id": 102, "default_branch": "elsewhere", "private": True}[field]
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("part", ["ref", "commit", "tree", "blob"])
    async def test_object_identity_mismatches(self, github_client, part):
        case = _observation_case()
        if part == "ref":
            case["responses"][1]["object"]["sha"] = "A" * 40
        else:
            case["responses"][{"commit": 2, "tree": 3, "blob": -2}[part]]["sha"] = "f" * 40
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad", [True, None, 0, "false"])
    async def test_truncated_must_be_exact_false(self, github_client, bad):
        case = _observation_case()
        case["responses"][3]["truncated"] = bad
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("problem", ["duplicate", "over_limit", "missing", "wrapper"])
    async def test_tree_selection_and_entry_limit(self, github_client, problem):
        case = _observation_case()
        tree = case["responses"][3]
        entry = tree["tree"][0]
        tree["tree"] = {"duplicate": [entry, copy.deepcopy(entry)], "missing": [], "wrapper": {},
            "over_limit": [entry] + [dict(entry, path="other" + str(i)) for i in range(4096)]}[problem]
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("index,field,value", [(3, "mode", "100644"), (3, "type", "blob"),
        (-3, "mode", "120000"), (-3, "mode", "160000"), (-3, "type", "tree"),
        (-3, "mode", 100644), (-3, "path", "another.bin")])
    async def test_intermediate_and_final_entry_types(self, github_client, index, field, value):
        case = _observation_case()
        case["responses"][index]["tree"][0][field] = value
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field,value", [("encoding", "utf-8"), ("size", True), ("size", -1),
        ("size", 0), ("size", 16385), ("content", None), ("content", "A" * 32769),
        ("content", "@@@="), ("content", "A==="), ("content", "AAA"),
        ("content", "Z m9v"), ("content", "Zm9v\t"), ("content", "Zm9v\r")],
        ids=["encoding", "boolean-size", "negative-size", "wrong-size", "oversize",
             "null-content", "encoded-oversize", "bad-alphabet", "bad-padding",
             "missing-padding", "space", "tab", "carriage-return"])
    async def test_blob_encoding_size_and_content_refused(self, github_client, field, value):
        case = _observation_case(content=b"f") if value is True else _observation_case()
        case["responses"][-2][field] = value
        await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    async def test_decoded_oversize_and_hash_mismatch(self, github_client):
        for case in (_observation_case(content=b"x" * 16385), _observation_case()):
            if len(case["expected"]["content"]) <= 16384:
                changed = b"different bytes"
                case["responses"][-2].update(content=base64.b64encode(changed).decode(), size=len(changed))
            await _reject_observation(github_client, case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", [None, b"proof", False, "", "/proof", "proof/", "proof//file",
        ".", "..", "proof/../file", "proof\\file", "proof/\0file", "proof/\x1ffile",
        "x" * 1025, "\u00e9" * 513, "/".join(["x"] * 9)])
    async def test_invalid_path_refused_before_io(self, github_client, path):
        request = AsyncMock()
        with patch.object(github_client, "_make_request", request), pytest.raises(GitHubAPIError) as caught:
            await github_client.get_file_observation(path)
        request.assert_not_awaited()
        _assert_observation_error(caught.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", [True, 17, b"a" * 40, "", "a" * 39, "A" * 40, "z" * 40])
    async def test_invalid_commit_refused_before_io(self, github_client, commit):
        request = AsyncMock()
        with patch.object(github_client, "_make_request", request), pytest.raises(GitHubAPIError) as caught:
            await github_client.get_file_observation("proof/challenge.bin", commit_sha=commit)
        request.assert_not_awaited()
        _assert_observation_error(caught.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field,value", [("owner", "bad/owner"), ("owner", ".."),
        ("repo", "bad?repo"), ("repo", "bad\nrepo"), ("repo", ""), ("owner", "\u00e9")])
    async def test_unsafe_repository_selectors_refused_before_io(self, github_client, field, value):
        setattr(github_client, field, value)
        request = AsyncMock()
        with patch.object(github_client, "_make_request", request), pytest.raises(GitHubAPIError) as caught:
            await github_client.get_file_observation("proof/challenge.bin")
        request.assert_not_awaited()
        _assert_observation_error(caught.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("failure", ["http", "transport", "json"])
    async def test_actual_http_and_transport_errors_sanitized(self, github_client, failure):
        with aioresponses() as mocked:
            url = "https://api.github.com/repos/TestOwner/TestRepo"
            if failure == "http":
                mocked.get(url, status=403, payload={"message": _OBSERVATION_SENTINEL})
            elif failure == "transport":
                mocked.get(url, exception=aiohttp.ClientError(_OBSERVATION_SENTINEL))
            else:
                mocked.get(url, body=_OBSERVATION_SENTINEL, content_type="application/json")
            async with github_client as client:
                with pytest.raises(GitHubAPIError) as caught:
                    await client.get_file_observation("proof/challenge.bin")
        _assert_observation_error(caught.value)

    @pytest.mark.asyncio
    async def test_malformed_response_and_provider_error_sentinels(self, github_client):
        for bad in (ValueError(_OBSERVATION_SENTINEL), GitHubAPIError(_OBSERVATION_SENTINEL),
                    [_OBSERVATION_SENTINEL], {"id": _OBSERVATION_SENTINEL}):
            case = _observation_case()
            case["responses"][0] = bad
            await _reject_observation(github_client, case)
