---
name: dns_ops
version: "0.1"
description: DNS and hosting operations via MCP — agents get capabilities, not credentials
category: capability-uplift
trigger: on_demand
cadence: null
agents: [qwen, gemma, 0102]
evals: []
retirement_date: null
---

# dns_ops MCP Server Skill

## Purpose

Expose DNS query, TLS verification, and gated DNS mutation tools to agents via MCP protocol. Provider credentials are held server-side; agents interact through constrained tool calls with policy enforcement and audit logging.

## Entry Point

`foundups-mcp-p1/servers/dns_ops/server.py`

## Dependencies

- `httpx` (async HTTP for GoDaddy API)
- `dnspython` (DNS resolution)
- `fastmcp` (MCP server framework)

## Read-Only Tools

- `dns_query` — resolve DNS records
- `dns_verify_tls` — check TLS cert validity
- `dns_check_hosting` — detect hosting platform
- `dns_verify_domain_setup` — end-to-end domain health check

## Gated Write Tools

- `dns_create_record` — create record (approval required)
- `dns_update_record` — update record (approval required)
- `dns_delete_record` — delete record (always requires approval)

## Policy

- Domain allowlist (fail-closed)
- Record type allowlist
- Mutation approval gate (012 CLI)
- Dry-run mode
- Append-only audit log
