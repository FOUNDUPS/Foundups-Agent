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

### Explicit Windows telemetry pilot CLI

Invoke `python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py`.
`store --type langfuse-viewer|openrouter-pilot|sentry-errors` requires a real Windows TTY and
hidden credential entry. Writes use only `FOUNDUPS/telemetry-pilot/langfuse-jp-viewer/v1`
or `FOUNDUPS/telemetry-pilot/openrouter/v1` or
`FOUNDUPS/telemetry-pilot/sentry-errors/v1`, with `CRED_TYPE_GENERIC` and
`CRED_PERSIST_LOCAL_MACHINE` (same account, same computer).

`run --type langfuse-viewer -- <review args>` launches only
`scripts/reddog_langfuse_review.py` with Japan fixed. Forwardable name/value pairs:
`--from-time`, `--to-time`, `--trace-id`, `--max-pages`, `--timeout`; duplicate,
unknown or incomplete pairs reject before credential access. The reader owns
value validation. `run --type openrouter-pilot` accepts no forwarded arguments
and launches only `scripts/reddog_openrouter_telemetry_probe.py` for one fixed
synthetic free-model request.

`run --type sentry-errors` takes no forwarded arguments and launches only
`scripts/reddog_sentry_probe.py`. Its fixed isolated runtime is
`~/.codex/telemetry-runtimes/sentry-pilot/Scripts/python.exe`, checked before a
vault read. The stored `{dsn}` must satisfy the monitoring owner's strict HTTPS
ingest grammar. Only this child receives DSN and enable variables.
`run --type langfuse-viewer --with-sentry-errors -- <review args>` explicitly
reads both credentials and uses that same runtime for the fixed Langfuse CLI.
Other credential types reject this flag. Without it the Viewer receiver and
credential-access behavior are unchanged and ambient Sentry configuration is
dropped. No caller-selected runtime path or arbitrary process is accepted.

No dump/list/delete or arbitrary subprocess CLI exists. Secrets are injected only
into the selected child environment; unrelated inherited credentials/hooks are
dropped. CLI status failures are static JSON, exit2; receiver exit codes propagate.
Successful vault-read audit metadata goes to stderr, not raw values. Process
timeout is120 seconds. These utilities require explicit principal authorization;
they are not registered as runtime MCP tools or WRE secret grants.

### One-use browser provisioning transport

`python -B scripts/reddog_langfuse_provision.py` explicitly creates one temporary
loopback form. Its only selection is `--type langfuse-viewer|sentry-errors`, with
Viewer as default; no credential values are accepted as CLI parameters. A random port and
256-bit path identify the form; `public_key` and `secret_key` are password inputs
with autocomplete disabled. Successful POST calls only
`store_credentials("langfuse-viewer", values)` and consumes the form.
Explicit Sentry mode exposes only `dsn` and calls
`store_credentials("sentry-errors", {"dsn": value})`; the shared monitoring
validator rejects nonofficial/HTTP/password/port/query/fragment DSNs before storage.

The helper rejects foreign/duplicate Host or Origin headers, wrong paths,
duplicate/framing headers, transfer encoding, non-form content, bodies over4,096
bytes and missing/duplicate/extra fields. Origin may be absent; if present it
must exactly equal the bound loopback origin. CSP is `default-src 'none'` with
same-origin form action and forbidden framing; responses are not cacheable.
Referrer policy is `same-origin` so same-origin POSTs preserve their Origin
header while cross-origin referrers are omitted; null Origin remains rejected.
POST failures return fixed diagnostic stage/code values, not submitted data or
exception text. Admission failure details contain only boolean used/expiry/path/
Host/Origin/missing/duplicate/null checks, never header values or the nonce.
Console output contains only the private local entrypoint URL
and static status. No read/list/delete operation is exposed.

The listener closes on success or after299 seconds; socket timeout is0.25s and
pre-store admission is rechecked. An expiry timer closes the active connection
and listening socket. This is authorized setup transport to the existing vault,
not a new secret store, general credential server, runtime grant or persistent
service. Python erasure and isolation from other same-account programs are not
claimed.

### `SystemdCredentialBinding` / `SystemdCredentialSecretResolver`

The immutable binding contains `credential_directory`, positive nonroot
`expected_uid`/`expected_gid`, `expected_requester`, finite `issued_at`/`expires_at`
(maximum 300 seconds), a frozen allowlist `credential_ids`, and
`max_secret_bytes` (1–65536). Construction performs no credential reads.
Binding metadata alone is not permission or authenticated owner state.

`SystemdCredentialSecretResolver(binding, *, clock, monotonic, audit_callback)`
exposes `resolve(reference, requester_id=None) -> ResolveResult`.
Production defaults use system clocks. `parse_systemd_credential_reference`
returns one strict ASCII credential ID or `None`; `op://`, traversal, URI query,
percent escapes and additional path segments reject.

Resolution requires the bound Linux identity, descriptor-relative no-symlink
root-owned ancestry and read-only manager credential custody. Missing/extra
access principals, wrong permissions, changed/oversized/non-UTF8 content and
expired or regressing clocks fail closed. No value survives in a failed result.
Audit callbacks receive metadata only; `credential_pre_delivery_validation`
is not a delivery receipt. Final lifetime/identity checks follow the callback.
The caller owns prompt disposal of a successful value and permission admission.

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
