# dns_ops MCP Server

Capability-layer MCP server for DNS and hosting operations. Agents call tools; the server holds credentials and enforces policy.

## Principle

**012 holds the keys. MCP server holds the capabilities. Agents hold neither.**

## Quick Start

```bash
# 1. Set credentials (012 only — never commit these)
export GODADDY_API_KEY=<key>
export GODADDY_API_SECRET=<secret>

# 2. Set policy
export DNS_OPS_ALLOWED_DOMAINS=foundups.com
export DNS_OPS_MUTATIONS_REQUIRE_APPROVAL=1

# 3. Start server
python foundups-mcp-p1/servers/dns_ops/server.py
```

## Tools

| Tool | Type | Approval | Description |
|------|------|----------|-------------|
| `dns_query` | read | no | Query live DNS records |
| `dns_verify_tls` | read | no | Check TLS certificate validity |
| `dns_check_hosting` | read | no | Detect hosting platform |
| `dns_create_record` | write | yes | Create DNS record via GoDaddy |
| `dns_update_record` | write | yes | Update DNS record via GoDaddy |
| `dns_delete_record` | write | always | Delete DNS record (always gated) |
| `dns_verify_domain_setup` | read | no | End-to-end domain health check |

## Approval Queue (012 Operator)

```bash
python -m foundups_mcp_p1.servers.dns_ops.approve --list
python -m foundups_mcp_p1.servers.dns_ops.approve --approve <id>
python -m foundups_mcp_p1.servers.dns_ops.approve --deny <id> --reason "not ready"
```

## Security

- Credentials read from process env at startup, never exposed to agents
- IronClaw env scrub blocks `GODADDY_API_KEY` / `GODADDY_API_SECRET` from worker subprocesses
- Domain allowlist is fail-closed (empty = deny all)
- All operations audit-logged to `dns_ops_audit.jsonl`
- Agents cannot approve their own submissions

## Full Contract

See [INTERFACE.md](INTERFACE.md) for complete tool signatures, policy engine, provider abstraction, and audit log schema.
