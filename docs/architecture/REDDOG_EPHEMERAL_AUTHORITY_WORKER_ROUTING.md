# RedDog Ephemeral Authority and Worker Routing

**Status:** DOCS_ONLY / SPECIFIED_NOT_IMPLEMENTED
**Date:** 2026-08-28
**Scope:** RedDog/WRE work-order routing, model requirements, worker scheduling, and ephemeral authority
**Implementation tracking:** GitHub issue #1584

## WSP source-of-truth boundary

Per WSP 81:

- `WSP_framework/src/` is the live canonical WSP source.
- `WSP_knowledge/src/` is the governed backup/mirror for canonical WSPs.
- If framework and knowledge differ, the numbered WSP in `WSP_framework/src/` controls.
- Derived architecture documents such as this file are not automatically mirrored into `WSP_knowledge`.

This document does not create or modify a WSP. It documents how existing WSP 15, WSP 71, WSP 97, RedDog, AI Gateway, and future WRE worker execution should concatenate.

## WSP 97 truth boundary

This slice is documentation-only. It changes no runtime code, credentials, environment variables, queues, model bindings, vault configuration, MCP behavior, or worker execution.

The WSP 97 pass retrieved the governing WSPs and repository evidence first, inspected the local RedDog/AI Gateway surfaces, expanded to the WSP 15/WSP 71 system boundary, and compressed the result to the smallest documentation move. Runtime WRE execution is not applicable to this slice; the future implementation is WRE-distributed and multi-agent.

## 1. First-principles separation

FoundUps must keep five decisions separate:

1. **Priority/economics — WSP 15.** WSP 15 scores Complexity, Importance, Deferability, and Impact and produces P0-P4 priority. It does not select model size.
2. **Task compute requirements.** A separate work-order classification states the capabilities required to perform the task: compute class, reasoning depth, context, tools, modality, latency, verification burden, and cost ceiling.
3. **Model routing — AI Gateway.** AI Gateway owns eligibility, measured selection, promotion evidence, runtime binding, and topology. Nemotron may propose candidate panels/topologies but is not production authority.
4. **Worker scheduling — RedDog/WRE.** RedDog/WRE queues the approved work order and dispatches an eligible worker against the bound requirements.
5. **Authority — WSP 71.** Workers must not possess durable secrets. They receive only task-scoped ephemeral authority, preferably without ever receiving the underlying credential value.

Canonical compression:

```text
WSP 15       = how valuable / urgent is the order?
Task Class   = what capabilities does the order require?
Nemotron     = what candidate model topology may fit?
AI Gateway   = which verified model binding is authorized now?
RedDog / WRE = which worker receives the queued order?
WSP 71       = what temporary authority may that worker exercise?
```

## 2. Restaurant/work-order model

```text
012 / FoundUp goal
      |
      v
RedDog creates approved WorkOrder
      |
      +--> WSP 15 allocation: MPS + P0-P4
      |
      +--> Task requirement classification
      |      compute_class: LOW | MID | HIGH
      |      reasoning_depth
      |      context_requirement
      |      tool_requirements
      |      modality
      |      latency_target
      |      cost_ceiling
      |      verification_class
      |
      +--> Nemotron shadow proposal (optional)
      |
      v
AI Gateway verifies eligible runtime model binding
      |
      v
WRE queue / worker reservation
      |
      v
Worker requests one bounded operation
      |
      v
Ephemeral Authority Broker / MCP gateway
      |
      +--> verify worker identity
      +--> verify exact work_order_id
      +--> verify runtime/model binding where required
      +--> verify resource and operation
      +--> verify WSP permissions/policy
      +--> mint or internally consume temporary authority
      |
      v
External service action
      |
      v
authority expires / is consumed / is revoked
```

The worker is analogous to a cook receiving one restaurant order. The worker receives the exact context and authority required for that order, not the restaurant's master keys.

## 3. WorkOrder requirements are separate from WSP 15

Illustrative future contract:

```yaml
work_order_id: WO-551
priority:
  wsp15_mps: 17
  class: P0
requirements:
  compute_class: HIGH
  reasoning_depth: DEEP
  context_tokens_min: 80000
  modalities: [text]
  tools: [repository_read, repository_write, test_runner]
  latency_class: NORMAL
  verification_class: SECURITY_SENSITIVE
  max_estimated_calls: 12
  cost_ceiling: bounded
runtime_binding:
  authority: AI_GATEWAY_SIGNED_BINDING
  fallback: false
authority_requirements:
  - resource: github:FOUNDUPS/Foundups-Agent
    action: push
    scope: branch:worker/WO-551
    max_uses: 1
    max_ttl_seconds: 60
    delegation: false
```

Exact schemas, persistence, signing, queue semantics, and enums remain implementation work.

Priority and compute are orthogonal. A P0 task may be low compute because it is urgent but deterministic. A P4 task may be high compute because it requires broad research but is not blocking current operations.

## 4. Nemotron boundary

Current RedDog/AI Gateway architecture treats NVIDIA Nemotron as a shadow topology proposer.

Required invariant:

> Nemotron may recommend candidate model combinations for a task requirement; it must not become its own production authority.

Deterministic/governed code remains responsible for task requirement projection, candidate eligibility, provider availability, benchmark evidence, signed promotion evidence, final runtime binding, topology validity, and no-fallback policy.

## 5. Ephemeral authority: no key movement

The target FoundUps security property is stronger than storing `.env` safely:

> **Workers have identity. Work orders have authority. Workers do not have durable secrets.**

A worker must not receive long-lived API keys, PATs, cloud secrets, database passwords, private signing material, or broadly reusable credentials through prompts, model context, logs, AgentDB, HoloIndex, files, inherited environment variables, or normal worker IPC.

Preferred path:

```text
Worker
  |
  | request: perform bounded action X for WorkOrder Y
  v
Authority Gateway / MCP boundary
  |
  | resolves or mints authority internally
  v
External provider
```

When feasible, the worker never sees even the temporary token. The gateway performs the exact bounded action on the worker's behalf.

When a provider protocol requires temporary credential delivery, that capability must be short-lived, task-scoped, resource-scoped, non-delegable, auditable, and destroyed immediately after use.

## 6. Capability death conditions

Temporary authority should terminate on the earliest applicable condition:

```text
expire_when ANY(
  ttl_exceeded,
  max_uses_consumed,
  work_order_completed,
  worker_lease_lost,
  worker_terminated,
  runtime_binding_expired,
  resource_or_action_changed,
  behavior_anomaly_detected,
  orchestrator_revoked,
  policy_or_verification_failed
)
```

For sensitive writes, the preferred default is single-use OR short TTL, whichever occurs first.

Example:

```yaml
worker_id: worker-37
work_order_id: WO-551
resource: github:FOUNDUPS/Foundups-Agent
operation: push
scope: branch:worker/WO-551
max_uses: 1
ttl_seconds: 45
delegation: false
```

The authority cannot be reused for another repository, branch, provider, administrative operation, or work order.

## 7. Closed worker environment

Worker processes should receive only non-secret runtime state required by their closed execution profile.

```text
ALLOW:
  WORKER_ID
  WORK_ORDER_ID
  runtime-safe OS/interpreter values
  explicitly required non-secret route/config references

DO NOT AMBIENTLY EXPOSE:
  OPENROUTER_API_KEY
  GITHUB_TOKEN
  AWS_SECRET_ACCESS_KEY
  DATABASE_PASSWORD
  PYPI_TOKEN
  SSH private material
  generic inherited credential-shaped variables
```

A compromised dependency inside a worker should therefore gain at most the currently active bounded work-order authority instead of the principal's durable credential set.

## 8. Relationship to WSP 71

WSP 71 already establishes centralized secrets management, permission validation, just-in-time access, no secret persistence, TTL/lease concepts, fail-closed behavior, MCP-gateway runtime resolution, and forbidden prompt/model/log/AgentDB/HoloIndex surfaces.

The future worker-facing contract should evolve away from `get_secret(...)` toward capability/proxy execution such as:

```python
request_capability(
    worker_id,
    work_order_id,
    resource,
    action,
    scope,
    requested_ttl,
    requested_max_uses,
)
```

The provider implementation may use Vault, cloud STS, OAuth token exchange, GitHub App installation tokens, provider-specific short-lived credentials, or an internal proxy. The invariant is provider-independent: **no durable key movement to workers**.

## 9. Future implementation slices — not executed here

Tracked in GitHub issue #1584.

### Slice A — WorkOrder requirement contract
Define the canonical task-requirements schema between RedDog work-order creation and AI Gateway model routing. Keep WSP 15 priority independent from compute class.

### Slice B — Queue/worker binding
Bind work-order priority, task requirements, verified runtime topology, worker identity, lease, and completion receipt without giving model proposers dispatch authority.

### Slice C — Ephemeral Authority Broker PoC
Extend the existing WSP 71 credential-access direction with one fake/test capability. Prove single-use/TTL expiration, fail-closed behavior, no secret in worker context/logs, and audit receipts containing no credential value.

### Slice D — Provider adapters
Implement provider-specific short-lived authority or proxy execution, beginning with the narrowest provider surface that supports it. Durable master credentials remain only behind the trusted gateway.

### Slice E — Supply-chain/red-team validation
Demonstrate that a hostile worker dependency cannot enumerate durable credentials and that captured temporary authority cannot exceed the exact work-order scope or survive its death conditions.

## 10. Acceptance invariant for future runtime

A future implementation is not complete until the following is true:

```text
compromise(worker)
    does NOT imply
compromise(principal_credentials)
```

The maximum credential blast radius must be bounded by the exact active work order, resource, operation, use count, TTL, worker lease, and runtime binding.

---

**Documentation truth:** architecture recorded; runtime implementation remains open and must be completed through the tracked worker issue under WSP 97.