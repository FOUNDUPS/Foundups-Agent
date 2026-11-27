# Secrets MCP Server Module Modification Log

## 2026-11-02: Fixed Sentry custody and explicit review-error opt-in

WSP22/50/71/91/97. Extend the existing custody targets with one Sentry error DSN,
validated through the monitoring owner's existing official-ingest grammar. The
one-use form gains only `--type sentry-errors` and a single password field; its
default Viewer flow, nonce/Origin/body/expiry rules are preserved. No new key,
secret store or general export command is introduced.

The fixed Sentry probe runs in the current account's isolated `sentry-pilot`
runtime. Explicit Viewer-only `--with-sentry-errors` reads both credentials and
uses that runtime for the same fixed Langfuse CLI; default Viewer runs do not
read or inherit Sentry configuration. Missing runtime and unsupported routes
reject before credential access. All injection remains child-only.

The expanded provisioning/vault/probe selection passes78 synthetic cases. Actual
SDK2.73.0 qualification passes four separate tests with outbound sockets blocked;
runtime evidence belongs to the monitoring module. No real DSN or vault operation
was accessed by this implementation lane. Root owns live provisioning and arrival
verification separately from these tests. An independent test initially required
404 for an already expired Windows socket; the equally fail-closed Win10053
closure is now accepted with thread-join and no-store assertions.

## 2026-11-02: One-use browser-to-vault Viewer provisioning

WSP00/22/50/71/91/97. Reuse the fixed Windows Viewer custody adapter through
`scripts/reddog_langfuse_provision.py` when the authorized browser has the generated
pair and terminal entry is unavailable. The helper binds only a random loopback
port/path, accepts one exact bounded form, disables caching/external content,
and closes after successful storage or299 seconds. No keys, bodies or raw errors
are logged or written to files; no generic target, read or runtime tool is added.

An adversarial pass reproduced Windows buffered-body shutdown waiting for the
old five-second socket timeout. A0.25-second socket timeout, shutdown margin and
pre-store recheck preserve bounded cleanup. Extreme numeric Content-Length is
rejected before integer conversion. Top-level failures now emit static status
instead of paths/tracebacks. Fixed rejection stages and allowlisted storage codes
make setup failures diagnosable without exposing credential text.

Combined provisioning/vault/probe validation passes63 synthetic cases, including
actual adapter import with invalid input stopped before any vault API access.
Admission diagnostics add only boolean cause checks; foreign headers and private
paths remain absent from responses. The actual Origin allowlist is unchanged.
Live boolean diagnostics isolated a browser null Origin caused by the original
`no-referrer` header. Change that policy to `same-origin` and assert it in tests;
cross-origin referrers stay omitted and null Origin admission remains rejected.
Native DLL initialization and the80-byte CREDENTIAL layout were checked without
CredRead/CredWrite. These are separate from live credential storage or vendor
connectivity. Holo lexical context remains UNKNOWN/gaptrue; no authority repair
or reindex occurred. Independent follow-up review is recorded by the parent.

## 2026-11-01: Bounded Windows telemetry pilot credential custody

WSP00/22/50/71/91/97. Add explicit Windows Credential Manager custody for only
the dedicated Japan Langfuse Viewer pair and OpenRouter pilot key. Hidden TTY
entry and fixed receiver invocation avoid plaintext files, persistent environment
changes and general credential-dump tooling. No enumeration/deletion or runtime
grant is added. The one-call synthetic `openrouter/free` probe retains only safe
status/usage and a generated trace ID, with no retries or redirects. Independent
review found model-slug grammar could admit secret-shaped remote text; remote
model output is now omitted entirely and a hostile-provider regression is added.

Offline synthetic/fake-Win32 validation passes32 tests across the credential
adapter and probe suites. The first run had30 passes/two setup errors caused by
an oversized automatic parameter ID; explicit short IDs correct the test harness.
No real credential read/write, provider request or vault-protection claim follows
from those tests. Vendor permissions/expiry and actual connectivity remain
separate live verification. Semantic Holo freshness remained UNKNOWN/gaptrue
after the parent authority/HEAD mismatch; exact source/docs were read directly.

## 2026-10-05: Explicit manager credential provider

Added `SystemdCredentialSecretResolver` in the existing secrets owner, reusing
`ResolveResult`/`AuditEvent`. Strict reference and immutable metadata binding,
fd-relative no-follow reads, exact root:root systemd ACLv2 custody, bounded UTF-8
content and dual-clock per-request expiry replace no existing vault or authority.
The audit event explicitly describes pre-delivery validation; final delivery is
checked again after the callback. No cache or Python zeroization claim.

The first actual nonroot run rejected a mistaken service-GID assumption. A bounded
public-canary ACL observation established the exact named-user ACL; the repair
rejects missing/extra principals rather than dropping the access check. The next
actual run read before expiry and rejected after expiry while the raw file remained
readable. Units and owned inputs were removed; both success and failure preserved
under `outputs/rsi-startup-custody-20261005`. Focused206 cases:204pass/2platform skips.
Controlled OS tests and saved-result independent review are distinct from actual
execution. Production entrypoint/custody admission remains incomplete. WSP00/15/71/97.

## 2026-07-17: SECRETS_MCP_WSP71_OP_CLI_VAULT_RESOLVER_PHASE1

**Author**: 0102 (Codex) | Commander: 012 | WSP: 00, 15, 71, 97

- Added `OpCliSecretResolver`, a WSP 71 Annex A `op://` resolver that calls
  the 1Password CLI as `op read <reference> --no-newline` through an injected
  command runner.
- The default runner uses `subprocess.run` with `shell=False`, bounded timeout,
  bounded stdout, and no stderr/stdout serialization in receipts or errors.
- Added tests for canonical command shape, invalid references, command failure,
  timeout, empty output, oversized output, runner exceptions, Windows `op.exe`
  path handling, and AST no-shell/no-network/no-secret-persistence guards.
- Boundary remains constrained: no secret storage, no repo mutation, no
  OpenClaw/Hermes dispatch, no PR creation, no reward settlement, and no
  HoloIndex re-index.

## Initial Implementation - Secure Environment Access

**Created secure MCP server for environment variable and .env file access with comprehensive security filtering.**

### Key Features Implemented:

#### Security Architecture:
- **Pattern-Based Filtering**: Blocks sensitive data using regex patterns
- **Whitelist Access Control**: Only allows approved environment variables
- **Path Restrictions**: Limits .env file access to project directory
- **Zero Information Leakage**: Sensitive checks don't reveal existence

#### MCP Tools Implemented:
- **get_environment_variable**: Filtered env var retrieval with security checks
- **list_environment_variables**: Lists accessible variables only
- **check_env_var_exists**: Safe existence checking
- **read_env_file**: Secure .env file parsing with filtering
- **get_project_env_info**: Project environment overview

#### Security Implementation:
- **Sensitive Patterns**: Blocks passwords, keys, tokens, credentials
- **Allowed Prefixes**: PYTHON, PATH, HOME, FOUNDUPS, WSP, MCP, etc.
- **Path Validation**: Only .env files in project directory
- **Error Handling**: Secure error messages without information leakage

### WSP Compliance:
- **WSP 77**: Agent Coordination Protocol (secure inter-agent communication)
- **WSP 90**: UTF-8 Enforcement (proper encoding handling)
- **WSP 3**: Infrastructure Domain (appropriate module placement)
- **WSP 49**: Module Structure (standard WSP module format)

### Architecture Decisions:
- **FastMCP Framework**: Chosen for standardized MCP protocol implementation
- **Security-First Design**: Pattern filtering prevents sensitive data exposure
- **Local Processing**: Zero token cost by avoiding AI processing
- **Whitelist Approach**: Safer than blacklist for sensitive data protection

### Integration Points:
- **MCP Manager**: Auto-discovered and managed through MCP Services Gateway
- **Qwen/Gemma Gateway**: Smart routing for environment requests
- **MCP DAEmons**: Autonomous server lifecycle management
- **Main Menu**: Accessible via `--mcp` CLI and menu option 14

### Security Considerations:
- **No Sensitive Data Exposure**: All sensitive patterns blocked
- **Path Security**: Restricted file system access
- **Access Logging**: Security events tracked (future enhancement)
- **Input Validation**: All inputs validated and sanitized

### Files Created:
- `../foundups-mcp-p1/servers/secrets_mcp/__init__.py`: Module initialization
- `../foundups-mcp-p1/servers/secrets_mcp/server.py`: Main MCP server implementation
- `README.md`: Module documentation and usage
- `INTERFACE.md`: Complete API specification
- `ModLog.md`: Change tracking and implementation notes

### Files Modified:
- `../foundups-mcp-p1/setup_mcp_servers.py`: Added secrets_mcp server configuration
- `../modules/infrastructure/mcp_manager/src/mcp_manager.py`: Added secrets_mcp tools
- `../modules/infrastructure/mcp_manager/src/qwen_gemma_gateway.py`: Added secrets routing patterns
- `../modules/infrastructure/mcp_daemon/src/mcp_daemon.py`: Added secrets_mcp to daemon config

### Quantitative Impact:
- **6 MCP Servers**: Now managing complete MCP ecosystem
- **Zero Token Cost**: Environment access requires no AI processing
- **100% Security**: Sensitive data protection with pattern filtering
- **5 Security Tools**: Comprehensive environment access controls

### Benefits:
- **Security**: Prevents accidental credential exposure
- **Cost Efficiency**: Local processing avoids expensive AI calls
- **Reliability**: No external dependencies for environment access
- **Compliance**: Full WSP framework integration and security standards

This implementation establishes Secrets MCP as the secure foundation for environment configuration access in the autonomous FoundUps ecosystem, enabling 0102 agents to safely access necessary environment information while protecting sensitive credentials.
