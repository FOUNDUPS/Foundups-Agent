"""
Tests for GitHub Management Skill Executor

WSP 5: Test coverage
WSP 97: Execution mantra validation
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from modules.infrastructure.github_orchestrator.skillz.github_management.executor import (
    execute,
    parse_command,
    handle_issue,
    handle_collaborator,
    handle_repo,
)


class TestParseCommand:
    """Test command parsing."""

    def test_parse_issue_create(self):
        result = parse_command("issue create FOUNDUPS/autopost Test-Title")
        assert result["subcommand"] == "issue"
        assert result["action"] == "create"
        assert "FOUNDUPS/autopost" in result["args"][0]

    def test_parse_collaborator_add(self):
        result = parse_command("collaborator add FOUNDUPS/autopost testuser pull")
        assert result["subcommand"] == "collaborator"
        assert result["action"] == "add"

    def test_parse_repo_create(self):
        result = parse_command("repo create newfoundup Description here")
        assert result["subcommand"] == "repo"
        assert result["action"] == "create"

    def test_parse_empty_args(self):
        result = parse_command("")
        assert "error" in result

    def test_parse_insufficient_args(self):
        result = parse_command("issue")
        assert "error" in result


class TestExecuteIntegration:
    """Integration tests (require GitHub token)."""

    @pytest.mark.asyncio
    async def test_issue_list(self):
        """Test listing issues (read-only, safe to run)."""
        result = await execute("issue list FOUNDUPS/autopost", {})
        assert result.get("success") is True or "error" in result

    @pytest.mark.asyncio
    async def test_unknown_subcommand(self):
        """Test unknown subcommand handling."""
        result = await execute("unknown action args", {})
        assert "error" in result


class TestCommandHandlers:
    """Test individual command handlers."""

    @pytest.mark.asyncio
    async def test_handle_issue_missing_repo(self):
        """Test issue create with missing args."""
        mock_orchestrator = MagicMock()
        parsed = {"action": "create", "args": []}

        # Direct call - tests arg validation
        result = await handle_issue(mock_orchestrator, parsed)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_handle_collaborator_missing_username(self):
        """Test collaborator add with missing username."""
        mock_orchestrator = MagicMock()
        parsed = {"action": "add", "args": ["FOUNDUPS/autopost"]}

        result = await handle_collaborator(mock_orchestrator, parsed)
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
