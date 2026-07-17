# Secrets MCP Server - Interface Documentation

## Module Interface

**Domain**: infrastructure  
**Purpose**: Secure environment variable and .env file access  
**WSP Compliance**: WSP 77 (Agent Coordination), WSP 90 (UTF-8 Enforcement)

## Public API

### Core Classes

#### `SecretsMCPServer`
Main server class implementing FastMCP protocol with security filtering.

```python
class SecretsMCPServer:
    def __init__(self)
    async def get_environment_variable(key: str) -> Dict[str, Any]
    async def list_environment_variables(filter_pattern: str = "") -> Dict[str, Any]
    async def check_env_var_exists(key: str) -> Dict[str, Any]
    async def read_env_file(filepath: str) -> Dict[str, Any]
    async def get_project_env_info() -> Dict[str, Any]
```

#### `OpCliSecretResolver`
WSP 71 Annex A `op://` resolver backed by the 1Password CLI.

```python
class OpCliSecretResolver:
    def __init__(
        *,
        op_executable: str = "op",
        timeout_s: float = 10.0,
        ttl_seconds: int = 300,
        max_secret_chars: int = 65536,
        session_id: str = "op-cli-session",
        runner: OpCliCommandRunner | None = None,
        audit_callback: Callable[[AuditEvent], None] | None = None,
    )
    def resolve(reference: str, requester_id: str | None = None) -> ResolveResult
```

Security boundary:
- Calls `op read <reference> --no-newline` as argv, never through a shell.
- Accepts only `op` or an absolute/path-like executable whose basename is
  `op` or `op.exe`.
- Returns the resolved secret value only through `ResolveResult.get_value()`.
- Audit dictionaries contain reference hashes, status, TTL and requester only;
  stdout/stderr secret content is never serialized.
- Tests use an injected runner. Production may use the default shell-free
  subprocess runner when the 1Password CLI is installed and authenticated.

## Tool Specifications

### 1. get_environment_variable

**Purpose**: Retrieve a specific environment variable value with security filtering

**Parameters**:
- `key` (str): Environment variable name

**Returns**:
```python
{
    "success": bool,
    "key": str,
    "value": str,  # Only if accessible and not sensitive
    "length": int,
    "is_sensitive": bool,
    "error": str   # Only on failure
}
```

**Security**: Blocks access to variables matching sensitive patterns

### 2. list_environment_variables

**Purpose**: List all accessible environment variables

**Parameters**:
- `filter_pattern` (str, optional): Filter variables by name pattern

**Returns**:
```python
{
    "success": bool,
    "total_variables": int,
    "variables": {
        "VAR_NAME": {
            "length": int,
            "is_sensitive": bool
        }
    },
    "filter_applied": bool,
    "error": str  # Only on failure
}
```

**Security**: Only shows allowed variables, masks sensitive content

### 3. check_env_var_exists

**Purpose**: Check if an environment variable exists without revealing its value

**Parameters**:
- `key` (str): Environment variable name

**Returns**:
```python
{
    "success": bool,
    "key": str,
    "exists": bool,
    "accessible": bool,  # exists AND allowed
    "is_sensitive": bool
}
```

**Security**: Safe to call on any variable name

### 4. read_env_file

**Purpose**: Read and parse .env files with security filtering

**Parameters**:
- `filepath` (str): Path to .env file

**Returns**:
```python
{
    "success": bool,
    "filepath": str,
    "total_variables": int,
    "variables": {
        "VAR_NAME": {
            "value": str,
            "line": int,
            "length": int,
            "is_sensitive": bool
        }
    },
    "error": str  # Only on failure
}
```

**Security**: Only allows .env files in project directory, filters sensitive variables

### 5. get_project_env_info

**Purpose**: Get comprehensive project environment information

**Parameters**: None

**Returns**:
```python
{
    "success": bool,
    "project_info": {
        "python_version": str,
        "platform": str,
        "working_directory": str,
        "env_files_found": [
            {
                "name": str,
                "path": str,
                "size": int
            }
        ],
        "total_env_vars": int,
        "allowed_env_vars": int
    },
    "error": str  # Only on failure
}
```

## Error Handling

### Error Response Format
```python
{
    "success": false,
    "error": "Descriptive error message",
    "context": "Additional error context"
}
```

### Common Errors
- `"Access denied: sensitive"`: Variable matches sensitive pattern
- `"Access denied: file path not allowed"`: File outside allowed directories
- `"File not found"`: .env file doesn't exist
- `"Environment variable not found"`: Variable doesn't exist

## Security Specifications

### Sensitive Pattern Detection
```python
sensitive_patterns = [
    r'password|pwd|secret|key|token|auth',
    r'api.*key|access.*key|secret.*key',
    r'database.*url|db.*url|connection.*string',
    r'private.*key|ssl.*key|certificate',
    r'credential|login|username|user',
    r'salt|hash|encrypt'
]
```

### Allowed Variable Prefixes
```python
allowed_prefixes = [
    'PYTHON', 'PATH', 'HOME', 'USER', 'SHELL', 'TERM',
    'FOUNDUPS', 'WSP', 'MCP', 'HOLO', 'GIT',
    'LANG', 'LC_', 'TZ', 'HOSTNAME'
]
```

### Path Restrictions
- Only `.env` files allowed
- Must be within project directory
- Cannot access system directories (`/etc`, `/root`, Windows system dirs)

## MCP Protocol Integration

### Server Configuration
```python
app = FastMCP("Foundups Secrets MCP Server")

# Tool registration
@app.tool()
async def get_environment_variable(key: str) -> Dict[str, Any]:
    # Implementation
```

### Health Check Endpoint
```python
@app.get("/")
async def root():
    return {
        "status": "Secrets MCP Server running",
        "version": "1.0.0",
        "security": "Filtered access with sensitive data protection"
    }
```

## Integration Requirements

### Dependencies
- `fastmcp`: MCP protocol implementation
- `os`: Environment variable access
- `pathlib`: Path manipulation
- `re`: Pattern matching

### Environment Setup
```bash
# Required environment variables
REPO_ROOT=/path/to/foundups-agent
PYTHONPATH=/path/to/foundups-agent
```

### Port Configuration
- **Default Port**: 8006
- **Host**: 0.0.0.0 (all interfaces)

## Testing

### Security Testing
- Verify sensitive variables are blocked
- Confirm allowed variables are accessible
- Test path restriction enforcement
- Validate .env file parsing

### Functionality Testing
- Environment variable retrieval
- Variable existence checking
- .env file reading
- Error handling validation

### Integration Testing
- MCP protocol compliance
- Qwen/Gemma gateway routing
- MCP manager integration
- Health monitoring
