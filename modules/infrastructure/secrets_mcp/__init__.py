# -*- coding: utf-8 -*-
"""
Secrets MCP Server Module
Provides secure environment variable and .env file access for 0102 agents.

WSP Compliance: WSP 77 (Agent Coordination), WSP 90 (UTF-8 Enforcement)
"""

from .src.secrets_mcp import SecretsMCPServer
from .src.op_cli_secret_resolver import OpCliSecretResolver

__version__ = "1.0.0"
__all__ = ["OpCliSecretResolver", "SecretsMCPServer"]
