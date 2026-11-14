# Red Dog Grok Bot Tool Provider — Phase 1

## Decision

Grok Bot is admitted as an **external Red Dog tool/worker provider**, not as Red Dog authority, not as a Hermes subcomponent, and not as an implicit OpenClaw authority source.

The durable FoundUps boundary is:

```text
012 / authenticated principal
        |
        v
Red Dog resident authority
        |
        v
WRE / admitted work order
        |
        v
External tool-provider boundary
        |
        +--> Hermes worker surfaces
        +--> OpenClaw worker surfaces
        `--> Grok Bot worker surface
```

A provider can execute only an already-admitted work order. Provider identity, model output, prompt text, Bot memory, local files, browser state, and credentials never mint Red Dog authority.

## Why Grok Bot belongs here

xAI's August 2026 Grok Bot documentation describes durable Bots operating on a persistent managed cloud computer with browser/desktop use, plugins/MCP, skills/routines, approvals, and persistent working context. These capabilities are useful for Red Dog work that requires a long-lived browser session, GUI interaction, or cross-application execution.

The same documentation states that a user's Bots share one computer and therefore share files, browser sessions, and application logins. Bot identity is consequently **not a security boundary**. FoundUps must scope authority before dispatch and must treat the Grok Bot account/computer as one external trust domain.

## Public API constraint

Phase 1 does not assume a stable public Grok Bot execution API. The core provider therefore contains no Grok Bot HTTP client, local gateway discovery, token loading, subprocess execution, or SDK dependency.

`GrokBotRedDogToolProvider` accepts an injected dispatcher supplied by a hosting integration. This permits later transports without changing Red Dog authority semantics:

1. an official xAI/Cursor Grok Bot API, if/when documented;
2. a separately governed experimental adapter to a local host gateway;
3. an MCP/plugin bridge owned outside the Red Dog core.

Community SDKs may be evaluated as experiments, but undocumented host endpoints and local gateway tokens are not accepted as canonical FoundUps contracts.

## Phase-1 contract

Module:

`modules/foundups/agent/src/grokbot_reddog_tool_provider.py`

Request schema:

`reddog_grokbot_tool_request.v1`

Receipt schema:

`reddog_grokbot_tool_receipt.v1`

Allowed operations:

- `health`
- `execute`
- `status`
- `cancel`

The provider is disabled by default. `execute` requires a mapping with a non-empty `work_order_id` and `admitted: true`. Credential- and authority-shaped fields are rejected at both request and work-order boundaries.

The provider emits a deterministic receipt preserving these invariants:

- Red Dog authority is retained.
- Grok Bot remains an external tool only.
- transport is injected rather than embedded in the authority layer;
- request payloads cannot supply credential material or principal authority;
- provider success cannot mint new authority.

## Security stance

Phase 1 intentionally does **not**:

- log into Grok Bot;
- read a Grok Bot token;
- discover a local Grok Bot gateway;
- invoke a third-party Grok Bot SDK;
- run shell commands;
- mutate the repository;
- create worktrees or pull requests;
- let Grok Bot self-admit a work order;
- treat one Bot as isolated from another Bot on the same account computer.

## Next phase

Phase 2 should add a transport implementation outside the core after choosing a supported connection mechanism. Its acceptance criteria are:

1. explicit operator configuration and default-off activation;
2. bounded timeouts and cancellation;
3. exact endpoint/host allowlisting;
4. secrets supplied only by the host integration and never copied into work-order payloads or receipts;
5. artifact collection into a bounded receipt;
6. independent 3V verification before any promotion or mutation is trusted;
7. no Grok Bot memory, routine, skill, or internal agent handoff may increase the work order's effect ceiling.

## External references checked 2026-08-28

- xAI/SpaceXAI Grok Bot overview and launch documentation (persistent cloud computer, Bots, plugins/MCP, skills/routines).
- xAI/SpaceXAI approvals/security documentation (shared-computer trust boundary and local-computer approval controls).
- Community `adam91holt/grokbot-sdk` repository (local host gateway client; explicitly third-party and therefore non-canonical).

This document records the architecture decision; external product behavior must be revalidated before a live transport is enabled.
