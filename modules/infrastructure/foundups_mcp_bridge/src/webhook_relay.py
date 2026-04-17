#!/usr/bin/env python3
"""
MCP Bridge Webhook Relay for OpenAI GPT Actions.

Exposes the FoundUps MCP Bridge as a REST API at localhost:8100.

Usage:
    python -m modules.infrastructure.foundups_mcp_bridge.src.webhook_relay

    # Or with uvicorn directly:
    uvicorn modules.infrastructure.foundups_mcp_bridge.src.webhook_relay:app --host 0.0.0.0 --port 8100
"""

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .bridge_server import FoundUpsMCPBridge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bridge
bridge = FoundUpsMCPBridge()

# FastAPI app
app = FastAPI(
    title="FoundUps MCP Bridge",
    description="Read-only perception layer for AI-assisted architectural execution",
    version=bridge.VERSION,
)

# CORS for GPT Actions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ToolCallRequest(BaseModel):
    """Request body for tool calls."""
    arguments: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────────
# Status & Discovery Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/mcp/v1/status")
async def get_status():
    """Get bridge status and capabilities."""
    return bridge.get_status()


@app.get("/mcp/v1/tools")
async def list_tools():
    """List all available tools."""
    return bridge.list_tools()


# ─────────────────────────────────────────────────────────────────────────────
# Generic Tool Call Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@app.post("/mcp/v1/call/{tool_name}")
async def call_tool(tool_name: str, request: ToolCallRequest = None):
    """
    Call any MCP tool by name.

    Args:
        tool_name: Tool identifier
        request: Optional arguments in body
    """
    args = request.arguments if request and request.arguments else {}
    logger.info(f"[MCP] Tool call: {tool_name} with args: {args}")

    result = bridge.call_tool(tool_name, **args)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4: Signal Normalization (convenience endpoints)
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/mcp/v1/overseer/summary")
async def get_overseer_summary():
    """Get compressed overseer situational awareness."""
    return bridge.call_tool("get_overseer_summary")


@app.get("/mcp/v1/modules/hot")
async def get_hot_modules(limit: int = 10, since_days: int = 7):
    """Get modules ranked by volatility/risk."""
    return bridge.call_tool("get_hot_modules", limit=limit, since_days=since_days)


@app.get("/mcp/v1/failures/repeated")
async def get_repeated_failures(min_frequency: int = 2, limit: int = 20):
    """Get recurring failure patterns."""
    return bridge.call_tool("get_repeated_failures", min_frequency=min_frequency, limit=limit)


@app.get("/mcp/v1/risks/active")
async def get_active_risks(min_severity: str = "low"):
    """Get active risks with severity levels."""
    return bridge.call_tool("get_active_risks", min_severity=min_severity)


@app.get("/mcp/v1/focus/recommended")
async def get_recommended_focus(limit: int = 5):
    """Get prioritized focus recommendations."""
    return bridge.call_tool("get_recommended_focus", limit=limit)


@app.post("/mcp/v1/context/packet")
async def get_prompt_context_packet(
    task_description: str = "",
    include_failures: bool = True,
    include_risks: bool = True,
):
    """Assemble context packet for prompt generation."""
    return bridge.call_tool(
        "get_prompt_context_packet",
        task_description=task_description,
        include_failures=include_failures,
        include_risks=include_risks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: Impact Prediction
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/mcp/v1/impact/{target_type}/{target:path}")
async def get_change_impact_score(target_type: str, target: str):
    """
    Get blast radius and risk score.

    Args:
        target_type: module, file, diff, or commit_range
        target: Module name, file path, or commit range
    """
    return bridge.call_tool("get_change_impact_score", target_type=target_type, target=target)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: HoloIndex Recall
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/mcp/v1/holo/search")
async def holo_search(query: str, scope: str = "all", top_k: int = 10):
    """Semantic search across the repository."""
    return bridge.call_tool("holo_search", query=query, scope=scope, top_k=top_k)


@app.get("/mcp/v1/holo/related/{target}")
async def holo_related(target: str, relation_type: str = "all", limit: int = 10):
    """Find modules related to target."""
    return bridge.call_tool("holo_related", target=target, relation_type=relation_type, limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: Dependency & Diff
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/mcp/v1/deps/{module_name}")
async def get_module_dependencies(module_name: str, include_external: bool = True):
    """Get dependencies for a module."""
    return bridge.call_tool("get_module_dependencies", module_name=module_name, include_external=include_external)


@app.get("/mcp/v1/deps/{module_name}/reverse")
async def get_reverse_dependencies(module_name: str):
    """Get modules that depend on this module (blast radius)."""
    return bridge.call_tool("get_reverse_dependencies", module_name=module_name)


@app.get("/mcp/v1/diff/summary")
async def get_diff_summary(commit_range: str, group_by_module: bool = True):
    """Get diff summary for commit range."""
    return bridge.call_tool("get_diff_summary", commit_range=commit_range, group_by_module=group_by_module)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 0: Sense
# ─────────────────────────────────────────────────────────────────────────────


@app.get("/mcp/v1/repo/tree")
async def get_repo_tree(path: str = ".", depth: int = 3):
    """Get directory tree."""
    return bridge.call_tool("get_repo_tree", path=path, depth=depth)


@app.get("/mcp/v1/repo/file")
async def read_file(path: str):
    """Read file contents."""
    return bridge.call_tool("read_file", path=path)


@app.get("/mcp/v1/repo/search")
async def search_repo(query: str, path: str = ".", top_k: int = 20):
    """Search repository with ripgrep."""
    return bridge.call_tool("search_repo", query=query, path=path, top_k=top_k)


@app.get("/mcp/v1/repo/changes")
async def get_recent_changes(limit: int = 50):
    """Get recent git commits."""
    return bridge.call_tool("get_recent_changes", limit=limit)


@app.get("/mcp/v1/docs/wsp")
async def get_wsp_docs():
    """Get list of WSP documents."""
    return bridge.call_tool("get_wsp_docs")


@app.get("/mcp/v1/docs/module/{module_name}")
async def get_module_docs(module_name: str):
    """Get module README."""
    return bridge.call_tool("get_module_docs", module_name=module_name)


@app.get("/mcp/v1/docs/modlog")
async def get_modlog(limit: int = 20):
    """Get recent ModLog entries."""
    return bridge.call_tool("get_modlog", limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    """Run the webhook relay server."""
    import uvicorn

    logger.info(f"[MCP] Starting webhook relay v{bridge.VERSION}")
    logger.info(f"[MCP] Repo root: {bridge.repo_root}")
    logger.info(f"[MCP] Tools: {len(bridge._tools)} registered")

    uvicorn.run(app, host="0.0.0.0", port=8100)


if __name__ == "__main__":
    main()
