# Secrets MCP Server - Secure Environment Access

## Overview

**Secrets MCP Server** provides secure, controlled access to environment variables and .env files for 0102 agents. This server implements comprehensive security filtering to prevent exposure of sensitive credentials while enabling legitimate environment configuration access.

## Key Features

- **Security-First Design**: Pattern-based filtering blocks sensitive data (passwords, keys, tokens)
- **Controlled Access**: Whitelist approach for allowed environment variables
- **.env File Support**: Secure reading of environment configuration files
- **WSP 71 op:// Resolution**: Optional 1Password CLI-backed runtime resolver for `op://vault/item/field` references
- **Zero Token Cost**: Local processing prevents expensive AI calls
- **WSP Compliance**: Follows WSP 77 (Agent Coordination) and WSP 90 (UTF-8 Enforcement)

## Architecture

```
Secrets MCP Server
├── Security Layer (Pattern filtering, access control)
├── Environment Access (Filtered env vars, .env files)
├── MCP Integration (FastMCP protocol)
└── WSP Compliance (Secure agent coordination)
```

## Security Model

### Sensitive Data Protection
- **Pattern Filtering**: Blocks variables containing sensitive keywords
- **Path Restrictions**: Only allows .env files within project directory
- **Access Control**: Whitelist-based environment variable access

### Allowed Environment Variables
- **System Variables**: `PATH`, `HOME`, `USER`, `SHELL`, `LANG`, etc.
- **Python Variables**: `PYTHONPATH`, `PYTHON_VERSION`, etc.
- **Project Variables**: `FOUNDUPS`, `WSP`, `MCP`, etc.

### Blocked Patterns
- `password|pwd|secret|key|token`
- `api.*key|access.*key|secret.*key`
- `database.*url|db.*url`
- `credential|login|username`

## Usage

### MCP Integration
The server integrates with the Qwen/Gemma intelligent routing system:

```python
# Automatic routing for environment requests
"Check PYTHONPATH" -> Local Secrets MCP ($0.00)
"Read .env file" -> Local Secrets MCP ($0.00)
"Get API key" -> BLOCKED (security filter)
```

### Available Tools

1. **get_environment_variable**: Retrieve filtered environment variable values
2. **list_environment_variables**: List accessible environment variables
3. **check_env_var_exists**: Check variable existence without revealing value
4. **read_env_file**: Read .env files with security filtering
5. **get_project_env_info**: Get project environment setup information

### WSP 71 Vault Resolver

`OpCliSecretResolver` resolves `op://` secret references at runtime through the
1Password CLI:

```python
from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import OpCliSecretResolver

resolver = OpCliSecretResolver()
result = resolver.resolve("op://foundups-secrets/reddog-signing/private", "signer:reddog")
secret = result.get_value() if result.success else None
```

The resolver calls `op read <reference> --no-newline` as a shell-free argv list.
It records only audit-safe hashes/status metadata. It does not store secrets,
print secret stdout/stderr, mutate the repository, invoke OpenClaw/Hermes, or
re-index HoloIndex.

## Integration Points

### MCP Manager
- **Menu Integration**: Available through MCP Services Gateway
- **Health Monitoring**: Server status and performance tracking
- **Tool Discovery**: Dynamic tool availability inspection

### Qwen/Gemma Gateway
- **Smart Routing**: Automatically routes environment requests to Secrets MCP
- **Cost Optimization**: Zero token cost for environment access
- **Security Enforcement**: Prevents sensitive data leakage

### WSP Framework
- **WSP 77 Compliance**: Secure agent coordination patterns
- **WSP 90 Compliance**: UTF-8 encoding enforcement
- **WSP 3 Compliance**: Infrastructure domain placement

## Benefits

- **Security**: Prevents accidental exposure of sensitive credentials
- **Cost Efficiency**: Zero token cost for environment configuration
- **Reliability**: Local processing avoids network dependencies
- **Compliance**: Full WSP framework integration

## Configuration

### Environment Variables
```bash
# Project root detection
REPO_ROOT=/path/to/foundups-agent

# Python path setup
PYTHONPATH=/path/to/foundups-agent
```

### Security Settings
- **Allowed Paths**: Project directory .env files only
- **Blocked Patterns**: Configurable sensitive data filters
- **Access Control**: Whitelist-based variable permissions

## Example Usage

```python
# Get Python path (allowed)
result = await secrets_mcp.get_environment_variable("PYTHONPATH")
# Returns: {"success": true, "value": "/path/to/python", "is_sensitive": false}

# Try to get password (blocked)
result = await secrets_mcp.get_environment_variable("DB_PASSWORD")
# Returns: {"success": false, "error": "Access denied: sensitive"}
```

This module provides the critical infrastructure for secure environment configuration access in the autonomous FoundUps ecosystem.
