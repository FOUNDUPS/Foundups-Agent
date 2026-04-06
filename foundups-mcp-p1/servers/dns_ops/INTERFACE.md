# dns_ops MCP Server — Interface Contract

**Status**: SPEC (Phase 1)
**Worker**: U (DNS_OPS_MCP_SERVER_CONTRACT_PHASE1)
**WSP**: 11 (Interface), 96 (MCP Governance), 49 (Module Structure)
**Date**: 2026-04-06

---

## Purpose

Capability-layer MCP server for DNS and hosting operations. Agents get **tools, not credentials**. The server holds provider API keys internally and exposes constrained operations with policy enforcement and audit logging.

Design principle: **012 holds the keys. MCP server holds the capabilities. Agents hold neither.**

---

## Architecture

```
Agent (0102 / Qwen / Gemma)
    |
    | MCP tool call (no credentials in payload)
    v
dns_ops MCP server (holds GODADDY_API_KEY, GODADDY_API_SECRET internally)
    |
    |--- read ops: execute immediately, return result
    |--- write ops: check policy -> approval gate -> execute or queue
    |
    v
Provider API (GoDaddy DNS API / Firebase Admin SDK)
    |
    v
Audit log (JSONL, every operation)
```

---

## Environment Variables

The server reads these from its own process environment. Agents never see them.

```bash
# Required — provider credentials (injected at server launch, never exposed)
GODADDY_API_KEY=<key>              # GoDaddy API key
GODADDY_API_SECRET=<secret>        # GoDaddy API secret
GODADDY_API_ENV=production         # "production" or "ote" (test environment)

# Optional — Firebase companion checks
FIREBASE_PROJECT_ID=<project>      # For hosting status checks (uses gcloud ADC)

# Policy
DNS_OPS_ALLOWED_DOMAINS=foundups.com  # Comma-separated domain allowlist
DNS_OPS_ALLOWED_RECORDS=A,AAAA,CNAME,TXT,MX  # Allowed record types
DNS_OPS_MUTATIONS_REQUIRE_APPROVAL=1  # 1=queue for 012 approval, 0=execute immediately
DNS_OPS_DRY_RUN=0                     # 1=never execute writes, only simulate

# Audit
DNS_OPS_AUDIT_LOG=dns_ops_audit.jsonl  # Path relative to server dir
```

### IronClaw Integration

Add to `SENSITIVE_ENV_KEYS` in `ironclaw_gateway_client.py`:
```python
"GODADDY_API_KEY",
"GODADDY_API_SECRET",
```

This ensures worker subprocesses spawned via IronClaw cannot access DNS credentials even if they read `os.environ`.

---

## Tools

### Read-Only Tools (no approval required)

#### `dns_query`

Query live DNS records for a domain.

```python
@mcp.tool()
async def dns_query(
    domain: str,           # e.g., "foundups.com" or "www.foundups.com"
    record_type: str = "A" # A, AAAA, CNAME, TXT, MX, NS, SOA
) -> dict:
    """Query live DNS records. Read-only, no credentials needed for public DNS."""
```

**Returns:**
```json
{
  "success": true,
  "domain": "www.foundups.com",
  "record_type": "CNAME",
  "records": [
    {"value": "foundupscom.web.app", "ttl": 3600}
  ],
  "query_source": "system_resolver"
}
```

**Implementation**: Uses `socket.getaddrinfo` / `dns.resolver` (dnspython). No provider credentials needed — public DNS resolution.

---

#### `dns_verify_tls`

Check TLS certificate validity for a hostname.

```python
@mcp.tool()
async def dns_verify_tls(
    hostname: str,         # e.g., "www.foundups.com"
    port: int = 443
) -> dict:
    """Verify TLS certificate for a hostname. Reports CN, SANs, expiry, chain validity."""
```

**Returns:**
```json
{
  "success": true,
  "hostname": "www.foundups.com",
  "tls_valid": false,
  "cert_cn": "firebaseapp.com",
  "cert_sans": ["firebaseapp.com"],
  "hostname_match": false,
  "issuer": "Google Trust Services",
  "not_after": "2026-07-01T00:00:00Z",
  "chain_valid": true,
  "error": "SEC_E_WRONG_PRINCIPAL: cert CN=firebaseapp.com does not match hostname www.foundups.com"
}
```

**Implementation**: Uses `ssl.create_default_context()` + `SSLSocket.getpeercert()`. No provider credentials needed.

---

#### `dns_check_hosting`

Check which hosting platform serves a domain, by inspecting HTTP headers and DNS.

```python
@mcp.tool()
async def dns_check_hosting(
    domain: str            # e.g., "foundups.com"
) -> dict:
    """Determine hosting platform for a domain via DNS + HTTP header inspection."""
```

**Returns:**
```json
{
  "success": true,
  "domain": "foundups.com",
  "ip_addresses": ["199.36.158.100"],
  "detected_platform": "firebase_hosting",
  "evidence": {
    "ip_range": "199.36.158.0/24 (Google/Firebase)",
    "headers": {
      "x-served-by": "cache-nrt-rjtf7700079-NRT",
      "alt-svc": "h3=\":443\""
    },
    "firebase_indicators": ["Strict-Transport-Security pattern", "Fastly CDN via x-served-by"]
  },
  "tls_valid": true,
  "http_status": 200
}
```

**Implementation**: Combines `dns_query` + `dns_verify_tls` + HTTP HEAD request. No provider credentials needed.

---

### Gated Write Tools (approval required by default)

All write tools follow the same gate sequence:

```
1. Policy check: domain in allowlist? record type allowed?
2. Dry-run check: DNS_OPS_DRY_RUN=1 → simulate only
3. Approval check: DNS_OPS_MUTATIONS_REQUIRE_APPROVAL=1 → queue for 012
4. Execute (if all gates pass)
5. Audit log (always, regardless of outcome)
```

---

#### `dns_create_record`

Create a new DNS record via GoDaddy API.

```python
@mcp.tool()
async def dns_create_record(
    domain: str,           # Base domain: "foundups.com"
    name: str,             # Record name: "mall" or "@" for apex
    record_type: str,      # A, AAAA, CNAME, TXT, MX
    value: str,            # Record value: "199.36.158.100" or "foundupscom.web.app"
    ttl: int = 3600,       # TTL in seconds
    dry_run: bool = False  # Override: force dry-run regardless of env
) -> dict:
    """Create a DNS record. Gated: requires domain/record-type policy + 012 approval."""
```

**Returns (queued for approval):**
```json
{
  "success": true,
  "status": "queued_for_approval",
  "approval_id": "dns_create_20260406_143022_mall_A",
  "proposed_change": {
    "action": "create",
    "domain": "foundups.com",
    "name": "mall",
    "record_type": "A",
    "value": "199.36.158.100",
    "ttl": 3600
  },
  "policy_checks": {
    "domain_allowed": true,
    "record_type_allowed": true,
    "dry_run": false,
    "approval_required": true
  },
  "audit_event_id": "a1b2c3d4"
}
```

**Returns (executed, approval not required):**
```json
{
  "success": true,
  "status": "executed",
  "provider": "godaddy",
  "provider_response_code": 200,
  "verification": {
    "dns_propagated": true,
    "resolved_value": "199.36.158.100"
  },
  "audit_event_id": "e5f6g7h8"
}
```

**Returns (policy denied):**
```json
{
  "success": false,
  "status": "denied",
  "reason": "domain 'evil.com' not in allowlist [foundups.com]",
  "audit_event_id": "i9j0k1l2"
}
```

---

#### `dns_update_record`

Update an existing DNS record.

```python
@mcp.tool()
async def dns_update_record(
    domain: str,
    name: str,
    record_type: str,
    value: str,
    ttl: int = 3600,
    dry_run: bool = False
) -> dict:
    """Update an existing DNS record. Same gate sequence as dns_create_record."""
```

Identical gate sequence and return schema to `dns_create_record`, with `"action": "update"`.

---

#### `dns_delete_record`

Delete a DNS record.

```python
@mcp.tool()
async def dns_delete_record(
    domain: str,
    name: str,
    record_type: str,
    dry_run: bool = False
) -> dict:
    """Delete a DNS record. Highest gate: always requires approval, even if env says otherwise."""
```

**Special policy**: Delete operations **always** require approval, regardless of `DNS_OPS_MUTATIONS_REQUIRE_APPROVAL` setting. This is hardcoded, not configurable.

---

#### `dns_verify_domain_setup`

End-to-end verification of a domain's DNS + TLS + hosting setup.

```python
@mcp.tool()
async def dns_verify_domain_setup(
    domain: str,                   # e.g., "www.foundups.com"
    expected_platform: str = None, # "firebase" | "vercel" | None (auto-detect)
    expected_ip: str = None,       # Expected IP address
    expected_cname: str = None     # Expected CNAME target
) -> dict:
    """Full verification: DNS resolution + TLS validity + hosting platform + content check."""
```

**Returns:**
```json
{
  "success": true,
  "domain": "www.foundups.com",
  "checks": {
    "dns_resolves": true,
    "dns_value_matches_expected": true,
    "tls_valid": true,
    "tls_hostname_match": true,
    "tls_not_expired": true,
    "hosting_platform_matches": true,
    "http_status_ok": true
  },
  "all_passed": true,
  "failures": [],
  "recommendations": []
}
```

This is a **read-only** verification tool — no approval needed. Used after 012 makes console changes to confirm they took effect.

---

## Policy Engine

### Domain Allowlist

```python
ALLOWED_DOMAINS = set(os.getenv("DNS_OPS_ALLOWED_DOMAINS", "foundups.com").split(","))

def check_domain_policy(domain: str) -> tuple[bool, str]:
    """Returns (allowed, reason)."""
    base = extract_base_domain(domain)  # "www.foundups.com" -> "foundups.com"
    if base in ALLOWED_DOMAINS:
        return True, f"domain {base} in allowlist"
    return False, f"domain {base} not in allowlist {ALLOWED_DOMAINS}"
```

### Record Type Allowlist

```python
ALLOWED_RECORDS = set(os.getenv("DNS_OPS_ALLOWED_RECORDS", "A,AAAA,CNAME,TXT,MX").split(","))

def check_record_type_policy(record_type: str) -> tuple[bool, str]:
    if record_type.upper() in ALLOWED_RECORDS:
        return True, f"record type {record_type} allowed"
    return False, f"record type {record_type} not in allowlist {ALLOWED_RECORDS}"
```

### Mutation Approval Gate

```python
class ApprovalGate:
    """Queue write operations for 012 approval."""

    def __init__(self, queue_path: Path):
        self.queue_path = queue_path  # JSONL file of pending approvals
        self.required = env_truthy("DNS_OPS_MUTATIONS_REQUIRE_APPROVAL", "1")

    def submit(self, proposed_change: dict) -> str:
        """Write proposed change to approval queue. Returns approval_id."""
        approval_id = f"dns_{proposed_change['action']}_{timestamp}_{name}_{type}"
        entry = {
            "approval_id": approval_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
            "proposed_change": proposed_change,
            "submitted_by": "mcp_agent",
        }
        with open(self.queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return approval_id

    def approve(self, approval_id: str) -> dict:
        """012 approves a pending change. Called via CLI, not by agent."""
        # Load queue, find entry, mark approved, execute via provider
        ...

    def deny(self, approval_id: str, reason: str) -> dict:
        """012 denies a pending change."""
        ...

    def list_pending(self) -> list[dict]:
        """List all pending approvals."""
        ...
```

### Dry-Run Mode

When `DNS_OPS_DRY_RUN=1` or `dry_run=True` on the tool call:
- All policy checks execute normally
- Provider API is NOT called
- Response includes `"status": "dry_run"` with the exact payload that would be sent
- Audit log records the dry-run attempt

---

## Approval CLI (012 Operator Interface)

Approvals are managed outside the MCP server, via CLI that 012 runs directly:

```bash
# List pending DNS changes
python -m foundups_mcp_p1.servers.dns_ops.approve --list

# Approve a change
python -m foundups_mcp_p1.servers.dns_ops.approve --approve dns_create_20260406_143022_mall_A

# Deny a change
python -m foundups_mcp_p1.servers.dns_ops.approve --deny dns_create_20260406_143022_mall_A --reason "not ready"

# Approve and execute immediately
python -m foundups_mcp_p1.servers.dns_ops.approve --approve-and-execute dns_create_20260406_143022_mall_A
```

The approval CLI reads the queue file, authenticates directly with GoDaddy API, and writes the result back. The agent is notified on next tool call that references the approval_id.

---

## Audit Log Schema

Every operation (read or write, success or failure, approved or denied) produces a JSONL entry:

```json
{
  "event_id": "sha256_hash_16chars",
  "timestamp": "2026-04-06T14:30:22.123Z",
  "tool": "dns_create_record",
  "category": "mutation",
  "caller": "mcp_agent",
  "domain": "foundups.com",
  "record_name": "mall",
  "record_type": "A",
  "proposed_value": "199.36.158.100",
  "policy_result": {
    "domain_allowed": true,
    "record_type_allowed": true,
    "approval_required": true,
    "dry_run": false
  },
  "outcome": "queued_for_approval",
  "approval_id": "dns_create_20260406_143022_mall_A",
  "provider_response": null,
  "error": null
}
```

Read operations use `"category": "query"` and omit approval fields.

**Log location**: `foundups-mcp-p1/servers/dns_ops/dns_ops_audit.jsonl`

---

## Provider Abstraction

```python
from abc import ABC, abstractmethod

class DNSProvider(ABC):
    """Abstract DNS provider interface. GoDaddy first, extensible later."""

    @abstractmethod
    async def get_records(self, domain: str, record_type: str = None) -> list[dict]:
        """Fetch DNS records from provider API."""

    @abstractmethod
    async def create_record(self, domain: str, name: str, record_type: str,
                            value: str, ttl: int) -> dict:
        """Create a DNS record via provider API."""

    @abstractmethod
    async def update_record(self, domain: str, name: str, record_type: str,
                            value: str, ttl: int) -> dict:
        """Update a DNS record via provider API."""

    @abstractmethod
    async def delete_record(self, domain: str, name: str, record_type: str) -> dict:
        """Delete a DNS record via provider API."""


class GoDaddyProvider(DNSProvider):
    """GoDaddy DNS API v1 implementation."""

    API_BASE = "https://api.godaddy.com/v1"
    OTE_BASE = "https://api.ote-godaddy.com/v1"  # Test environment

    def __init__(self):
        self.api_key = os.environ["GODADDY_API_KEY"]
        self.api_secret = os.environ["GODADDY_API_SECRET"]
        self.base_url = self.OTE_BASE if os.getenv("GODADDY_API_ENV") == "ote" else self.API_BASE

    def _headers(self) -> dict:
        return {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
        }

    async def get_records(self, domain, record_type=None):
        url = f"{self.base_url}/domains/{domain}/records"
        if record_type:
            url += f"/{record_type}"
        # httpx.AsyncClient GET with self._headers()
        ...

    async def create_record(self, domain, name, record_type, value, ttl):
        url = f"{self.base_url}/domains/{domain}/records"
        payload = [{"type": record_type, "name": name, "data": value, "ttl": ttl}]
        # httpx.AsyncClient PATCH with self._headers()
        ...

    async def update_record(self, domain, name, record_type, value, ttl):
        url = f"{self.base_url}/domains/{domain}/records/{record_type}/{name}"
        payload = [{"data": value, "ttl": ttl}]
        # httpx.AsyncClient PUT with self._headers()
        ...

    async def delete_record(self, domain, name, record_type):
        url = f"{self.base_url}/domains/{domain}/records/{record_type}/{name}"
        # httpx.AsyncClient DELETE with self._headers()
        ...
```

---

## File Structure

```
foundups-mcp-p1/servers/dns_ops/
    INTERFACE.md          # This contract
    README.md             # Setup and usage guide
    SKILLz.md             # WRE skill registration
    server.py             # FastMCP server (tools + policy engine)
    provider_godaddy.py   # GoDaddy DNS API v1 provider
    policy.py             # Domain/record allowlist + approval gate
    approve.py            # 012 CLI for approval queue management
    dns_ops_audit.jsonl   # Audit log (gitignored, runtime artifact)
    approval_queue.jsonl  # Pending approvals (gitignored, runtime artifact)
    requirements.txt      # httpx, dnspython, fastmcp
    tests/
        test_policy.py
        test_provider_godaddy.py
        test_tools_readonly.py
        test_approval_gate.py
```

---

## Security Invariants

1. **GODADDY_API_KEY and GODADDY_API_SECRET never appear in tool inputs or outputs.** They are read from process env at server startup.
2. **IronClaw env scrub blocks these keys** from worker subprocess environments.
3. **Delete operations always require approval**, even if `DNS_OPS_MUTATIONS_REQUIRE_APPROVAL=0`.
4. **Domain allowlist is fail-closed**: if `DNS_OPS_ALLOWED_DOMAINS` is empty or unset, all domains are denied.
5. **Audit log is append-only**: the server process appends; nothing truncates.
6. **Approval queue is not agent-accessible**: agents can submit changes and check status, but cannot approve their own submissions.
7. **Provider credentials are validated at startup**: server refuses to start if `GODADDY_API_KEY` is missing (fail-closed).

---

## WSP Compliance

| WSP | Requirement | How Met |
|-----|-------------|---------|
| 96 | MCP Governance | Domain/record allowlist, approval gate, audit log |
| 71 | Security | Credentials never exposed to agents, IronClaw env scrub |
| 11 | Interface | This contract document |
| 49 | Module Structure | Standard server directory layout |
| 22 | ModLog | Updates on implementation milestones |
| 77 | Agent Coordination | Tools callable by any agent via MCP protocol |

---

## Phase 1 Scope

**In scope:**
- Contract specification (this document)
- Read-only tools (`dns_query`, `dns_verify_tls`, `dns_check_hosting`)
- Write tool contracts with policy engine spec
- GoDaddy provider abstraction
- Approval queue design
- Audit log schema

**Deferred to Phase 2:**
- Firebase custom domain management (requires Firebase Admin SDK)
- Cloudflare provider (if DNS moves)
- Automated post-change verification (trigger `dns_verify_domain_setup` after approval execution)
- Integration with daemon_self_audit_loop for anomaly detection
- MCP Manager auto-discovery registration
