#!/usr/bin/env python3
"""
FoundUps Private MCP Bridge Server.

Read-only perception layer for AI-assisted architectural execution.
Exposes repository, WSP docs, module docs, and AI Overseer state.

v1 Capabilities:
- Repo structure and file reading
- WSP document access
- Module documentation access
- Search and recent changes
- AI Overseer read hooks (missions, patterns, violations)

v1 Disabled:
- All writes
- All execution
- All skill dispatch
- All agent spawning

WSP References:
- WSP 97: Truthful verification
- WSP 48: Recursive Self-Improvement (read hooks)
- WSP 77: Agent Coordination (read hooks)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from .response_schema import ok_response, error_response

# Import tool modules
from . import repo_tools
from . import doc_tools
from . import overseer_tools
from . import execution_stubs
from . import dependency_tools
from . import diff_tools
from . import impact_scoring

logger = logging.getLogger(__name__)

# Default repo root
DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


class FoundUpsMCPBridge:
    """
    Private MCP Bridge for FoundUps repository.

    Provides read-only perception layer for AI-assisted architectural execution.
    """

    VERSION = "1.2.0"
    MODE = "perception-only"

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize MCP Bridge.

        Args:
            repo_root: Repository root path (auto-detected if not provided)
        """
        self.repo_root = Path(repo_root or DEFAULT_REPO_ROOT).resolve()
        self._tools: Dict[str, Callable] = {}
        self._register_tools()
        logger.info(f"[MCP] Bridge initialized: {self.repo_root}")

    def _register_tools(self) -> None:
        """Register all available tools."""
        # Repo perception tools
        self._tools["get_repo_tree"] = self._wrap(repo_tools.get_repo_tree)
        self._tools["read_file"] = self._wrap(repo_tools.read_file)
        self._tools["search_repo"] = self._wrap(repo_tools.search_repo)
        self._tools["get_recent_changes"] = self._wrap(repo_tools.get_recent_changes)

        # Documentation tools
        self._tools["get_wsp_docs"] = self._wrap(doc_tools.get_wsp_docs)
        self._tools["get_module_docs"] = self._wrap(doc_tools.get_module_docs)
        self._tools["get_interface_doc"] = self._wrap(doc_tools.get_interface_doc)
        self._tools["get_test_docs"] = self._wrap(doc_tools.get_test_docs)
        self._tools["get_modlog"] = self._wrap(doc_tools.get_modlog)
        self._tools["get_violations"] = self._wrap(doc_tools.get_violations)

        # Overseer perception tools
        self._tools["get_mission_history"] = self._wrap(overseer_tools.get_mission_history)
        self._tools["get_pattern_memory"] = self._wrap(overseer_tools.get_pattern_memory)
        self._tools["get_overseer_status"] = self._wrap(overseer_tools.get_overseer_status)
        self._tools["get_coordination_state"] = self._wrap(overseer_tools.get_coordination_state)
        self._tools["get_known_failure_patterns"] = self._wrap(overseer_tools.get_known_failure_patterns)

        # Dependency perception tools
        self._tools["get_module_dependencies"] = self._wrap(dependency_tools.get_module_dependencies)
        self._tools["get_reverse_dependencies"] = self._wrap(dependency_tools.get_reverse_dependencies)

        # Diff perception tools
        self._tools["get_file_diff"] = self._wrap(diff_tools.get_file_diff)
        self._tools["get_diff_summary"] = self._wrap(diff_tools.get_diff_summary)

        # Impact prediction tools
        self._tools["get_change_impact_score"] = self._wrap(impact_scoring.get_change_impact_score)

        # Execution stubs (disabled in v1)
        self._tools["coordinate_mission"] = execution_stubs.coordinate_mission
        self._tools["spawn_agent_team"] = execution_stubs.spawn_agent_team
        self._tools["trigger_skill"] = execution_stubs.trigger_skill
        self._tools["write_file"] = execution_stubs.write_file
        self._tools["create_branch"] = execution_stubs.create_branch
        self._tools["create_pr"] = execution_stubs.create_pr

    def _wrap(self, func: Callable) -> Callable:
        """Wrap tool function to inject repo_root."""
        def wrapped(**kwargs):
            return func(self.repo_root, **kwargs)
        wrapped.__name__ = func.__name__
        wrapped.__doc__ = func.__doc__
        return wrapped

    def list_tools(self) -> Dict[str, Any]:
        """
        List all available tools.

        Returns:
            MCPResponse with tool listing
        """
        tools = []
        for name, func in self._tools.items():
            is_disabled = name in {
                "coordinate_mission", "spawn_agent_team", "trigger_skill",
                "write_file", "create_branch", "create_pr",
            }
            tools.append({
                "name": name,
                "description": (func.__doc__ or "").strip().split("\n")[0],
                "status": "disabled_in_v1" if is_disabled else "active",
            })

        return ok_response(
            {
                "tools": tools,
                "count": len(tools),
                "active_count": sum(1 for t in tools if t["status"] == "active"),
                "disabled_count": sum(1 for t in tools if t["status"] == "disabled_in_v1"),
            },
            version=self.VERSION,
            mode=self.MODE,
        )

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool by name.

        Args:
            tool_name: Name of tool to call
            **kwargs: Tool-specific arguments

        Returns:
            MCPResponse from tool
        """
        if tool_name not in self._tools:
            return error_response(
                f"Unknown tool: {tool_name}. Use list_tools() to see available tools.",
                available_tools=list(self._tools.keys()),
            )

        try:
            return self._tools[tool_name](**kwargs)
        except TypeError as e:
            return error_response(f"Invalid arguments for {tool_name}: {e}")
        except Exception as e:
            logger.error(f"[MCP] Tool {tool_name} error: {e}")
            return error_response(f"Tool execution error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get bridge status.

        Returns:
            MCPResponse with bridge status
        """
        return ok_response(
            {
                "version": self.VERSION,
                "mode": self.MODE,
                "repo_root": str(self.repo_root),
                "repo_exists": self.repo_root.exists(),
                "tools_registered": len(self._tools),
                "capabilities": {
                    "repo_perception": True,
                    "wsp_docs": True,
                    "module_docs": True,
                    "overseer_read": True,
                    "dependency_analysis": True,
                    "diff_perception": True,
                    "impact_prediction": True,
                    "holoindex_search": False,  # v2
                    "execution": False,  # v2
                },
            },
            source="bridge",
        )


# =====================================================================
# CLI Interface
# =====================================================================


def main():
    """CLI entry point for testing."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="FoundUps Private MCP Bridge (v1 - perception-only)"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repository root path",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List available tools",
    )
    parser.add_argument(
        "--call",
        type=str,
        default=None,
        help="Tool to call",
    )
    parser.add_argument(
        "--args",
        type=str,
        default="{}",
        help="JSON arguments for tool",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show bridge status",
    )
    args = parser.parse_args()

    bridge = FoundUpsMCPBridge(repo_root=args.repo_root)

    if args.status:
        print(json.dumps(bridge.get_status(), indent=2))
    elif args.list_tools:
        print(json.dumps(bridge.list_tools(), indent=2))
    elif args.call:
        try:
            kwargs = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON args: {e}")
            return 1
        result = bridge.call_tool(args.call, **kwargs)
        print(json.dumps(result, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
