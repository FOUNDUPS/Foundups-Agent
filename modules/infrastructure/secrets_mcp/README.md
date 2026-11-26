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

### Windows telemetry pilot custody

Use the [0102 telemetry runbook](../monitoring/RUNBOOK.md) for the installed
pilot's operating sequence; this section owns the fixed credential receivers.

`src/windows_pilot_credentials.py` is an explicit, principal-operated adapter for
three dedicated Windows Credential Manager generic-credential targets. It uses
`CredWriteW`/`CredReadW`; no plaintext credential files, persistent environment
changes, credential enumeration or deletion are implemented. Windows supplies
vault protection for the current account. Same-account software can access that
account's generic credentials; this is not process isolation or WRE admission.

Provision through a real Windows terminal with hidden `getpass` input:

```powershell
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py store --type langfuse-viewer
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py store --type openrouter-pilot
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py store --type sentry-errors
```

The commands prompt for a Viewer pair, dedicated OpenRouter pilot key or Sentry
error DSN respectively. Reprovisioning replaces only that exact dedicated
target. Provision Langfuse's Viewer permission separately; key syntax cannot prove
server-side scopes. Set expiry and a small OpenRouter spending limit at the vendor.
Never paste credentials into command arguments, source, receipts or chat.

When the existing browser can enter an already generated Viewer pair but an
interactive terminal is unavailable, explicitly run this one-use setup helper:

```powershell
python -B scripts/reddog_langfuse_provision.py
python -B scripts/reddog_langfuse_provision.py --type sentry-errors
```

It emits a random `127.0.0.1` port and unpredictable 256-bit hexadecimal path.
Open that local URL, fill the two password fields, and submit. The helper accepts
only the exact Host/path and same-origin Origin when supplied, a single bounded
form body of at most4,096 bytes, and exactly the public/secret fields. It invokes
only the existing `langfuse-viewer` vault target by default. Explicit Sentry
mode accepts exactly one password field named `dsn`, validates it with the
monitoring owner's strict official HTTPS ingest grammar, and stores only the
`sentry-errors` target. It does not generate API keys or
verify vendor-side Viewer scope. Browser/vault provisioning still requires the
principal's authorization.

There are no request logs, scripts, analytics, external assets, plaintext files,
credential response bodies or reusable daemon. CSP restricts form submission to
the same origin; responses are `no-store`. It closes after one successful store
or a299-second timer; accepted sockets use a0.25-second timeout and admission is
checked again before storage. Rejections expose only fixed admission/framing/
encoding/shape/storage stages and allowlisted vault failure codes.
Admission failures include only boolean used/expiry/path/Host/Origin checks;
header values and the private nonce are never echoed. The entry URL
and static completion/expiry/cancellation status are the only console output.
Same-account software remains outside this transport's isolation boundary.
`Referrer-Policy: same-origin` preserves the browser's local POST Origin while
omitting cross-origin referrers. `no-referrer` would make that Origin null and
correctly trigger the strict admission rejection. The Origin allowlist remains
unchanged. See [the browser policy effect on Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy).

Only three fixed receiver scripts can receive credentials in a child-only
environment (`shell=False`, 120-second process timeout):

```powershell
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py run --type langfuse-viewer -- --from-time 2026-11-01T00:00:00Z --to-time 2026-11-02T00:00:00Z
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py run --type openrouter-pilot
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py run --type sentry-errors
python -B modules/infrastructure/secrets_mcp/src/windows_pilot_credentials.py run --type langfuse-viewer --with-sentry-errors -- --from-time 2026-11-01T00:00:00Z --to-time 2026-11-02T00:00:00Z
```

Viewer calls `scripts/reddog_langfuse_review.py` with the Japan origin fixed. The
probe calls `scripts/reddog_openrouter_telemetry_probe.py`: one explicit
`openrouter/free` request, the fixed synthetic prompt `Reply with OK.`, at most16
completion tokens, 30-second socket timeout, no retries or redirects. Its JSON
contains the generated trace ID, safe numeric usage and a status; no remote model or response
content is retained. A returned provider response is not verified task success.
Normal imports, help and tests do not provision credentials or make API calls.

Sentry runs only `scripts/reddog_sentry_probe.py` using the fixed isolated Python
under the current account's `.codex/telemetry-runtimes/sentry-pilot`. The runtime
must already exist; there is no runtime-path option. It injects only the stored
DSN and `FOUNDUPS_SENTRY_ENABLED=1` into that child. The explicit Viewer-only
`--with-sentry-errors` flag reads both targets and uses the same isolated runtime
for the fixed Langfuse CLI, enabling its bounded error hook. Default Viewer runs
never read Sentry custody or inherit an ambient DSN/enable flag. Neither Sentry
route accepts arbitrary child commands, extra probe arguments or credential
exports. See [the real SDK qualification](../monitoring/README.md).

The wrapper rejects arbitrary child commands and drops unrelated environment
variables, including other provider credentials and Python startup hooks. It
emits credential-free status/audit events only. Python object erasure and native
worker secret permissions are not claimed. Receiver source must be trusted at
invocation time; this local adapter does not authenticate source revisions.
The [Microsoft credential structure contract](https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentialw)
defines the current-account persistence and 2,560-byte blob limit used here.

See [offline pilot tests](tests/README.md). Real vault custody and vendor
connectivity require separate live verification; synthetic tests do not prove them.

### Explicit systemd credential custody

`src/systemd_credential_secret_resolver.py` implements
`SystemdCredentialSecretResolver` for a separately authenticated
`SystemdCredentialBinding`. It reads only allowlisted
`systemd-creds://<credential-id>` references inside the explicitly selected
`/run/credentials/<unit>.service` directory. It does not discover paths from
environment variables, provision credentials, decrypt files, or mint permission.

The caller must establish current owner/generation, secrets permission and process
isolation before resolving. The provider checks nonroot UID/GID, root-owned
descriptor-relative paths, the selected systemd ACL custody shape, read-only
credential storage, bounded UTF-8 content and both wall/monotonic lifetime bounds.
It reads afresh and checks again after reading and after the audit callback.
Less than one second remaining fails conservatively. No secret is cached by the
resolver; Python buffer erasure and physical credential revocation are not claimed.

`credential_pre_delivery_validation` audit events describe validation before the
callback. Only the final `ResolveResult.success` reports delivery. A slow/failing
callback can cause delivery to fail even after a positive validation event.
The existing bridge factory can explicitly select this provider; authenticated
public startup supply and native worker admission remain separate unfinished gates.

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
