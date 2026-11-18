# RedDog Canonical Architecture Alignment - Phase 1

**Date:** 2026-08-26

**Base:** `cc6696924e0163d238fddc9b0809f1fd28a3fd63`

**Scope:** Documentation/protocol truth only

**Protocols:** WSP 00, 15, 22, 50, 62, 73, 80, 81, 97, 98

## Decision

RedDog and 0102 are not separate product identities. RedDog is the
operator-facing name, persona, continuous product identity, and conversation
surface of a principal-scoped 0102 Digital Twin.

```text
012 <-> RedDog / principal-scoped 0102
          |
          +-> RedDog services: session, model, memory adapters, transports
          +-> Principal Memex / scoped FoundUp Memex / HoloIndex
          +-> authenticated promotion
                    -> OpenClaw supervision
                    -> WRE execution and verification authority
                    -> Hermes bounded leaf workers / FoundUp DAEs
```

VSIX, p.fMALL, phone, and future voice surfaces are thin clients. RedDog is not
one browser, server, model, or OpenClaw process. A phone normally emits to a
resident/federated hub. Mesh operation remains a target until durable identity,
ordering, revocation, tenant isolation, policy, and receipts are independently
proved.

## WSP 15 allocation

| Dimension | Score | Evidence |
|---|---:|---|
| Complexity | 4 | Multiple canonical protocols, lifecycle docs, product contracts, mirrors, and terminology surfaces disagreed. |
| Importance | 5 | The drift changed RedDog identity and execution authority. |
| Deferability | 5 | WSP 73/80/98 actively instructed agents to use obsolete or nonexistent topology. |
| Impact | 5 | Every RedDog, FoundUp, PFMall, phone, and worker layer consumes these contracts. |

Total: `19`, canonical `P0`.

## Retrieval and verification

The governed Holo owner query failed closed during the parent transaction with
`HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; no retry, repair, or query-path
reindex was performed. The independent audit's PowerShell wrapper also stopped
locally on a parse error before a query executed. Neither path changed Holo
state.

Fallback verification used exact-tree `rg`, `NAVIGATION.py`, direct document
and interface reads, Git diffs, repository path existence checks, and SHA-256
mirror comparison.

Retrieval evaluation:

| Dimension | Finding | Response |
|---|---|---|
| Noise | Historical extension narratives and old architecture audits repeated superseded role language. | Preferred canonical protocols/interfaces and retained history as history. |
| Ordering | WSP 73/80/98 ranked as authority despite containing older topology. | Repaired the canonical sources before downstream summaries. |
| Missing artifacts | WSP 98 named a universal mesh SDK and Liberty Alert mesh modules that do not exist. | Removed implementation mandates and added explicit truth/gates. |
| Staleness | WSP 73 mandated II-Agent/FastAPI/Docker/YAML; WSP 80 mandated Qwen/MCP/Bell-state topology; vision used 2025 as current. | Rewrote protocols and relabelled scenarios. |
| Duplication | Identity and worker responsibilities were restated differently across RedDog, Digital Twin, p.fMALL, and public/member docs. | Established one responsibility map and aligned high-authority consumers. |

## Audited findings and disposition

| Finding | Prior state | Disposition |
|---|---|---|
| RedDog versus 0102 identity | Some docs said RedDog hosts 0102; others called RedDog itself a thin client. | RedDog/0102 is one principal-scoped product identity; services and surfaces are separate. |
| OpenClaw/Hermes/WRE roles | Hermes was often ordered before policy and grouped with authority; OpenClaw and WRE overlapped. | OpenClaw supervises policy/control; WRE owns admitted execution and verification; Hermes is a bounded leaf. |
| WSP 73 topology | Obsolete II-Agent/CommonGround, FastAPI/WebSocket, Docker, YAML, and unrelated video/browser details were mandatory. | Replaced with identity, memory, conversation, model, work, client, and phase-gate invariants. Module docs retain implementation detail. |
| WSP 80 topology | Hard-coded Qwen-per-cube, mandatory MCP/Bell-state claims, fixed DAEs, illustrative code, vendor IDE names, and unmeasured capacity. | Replaced with model-neutral cube contracts, AI Gateway selection, WRE authority, bounded resources, lifecycle, and evidence gates. |
| WSP 98 implementation | Mandatory absent SDK/modules, invented package versions, crypto examples, user thresholds, and zero-server claims. | Replaced with resident, peer-assisted, federation, security, and measurement gates. |
| PWA truth | Master architecture said no PWA existed although p.fMALL/member and some FoundUps are PWA-shaped. | Distinguished implemented PWA surfaces from missing universal FoundUp PWA/stake/interior/Progressive Web Agent capability. |
| Scale truth | Fixed instance/user and exponential/zero-cost claims were unmeasured. | Relabelled as target/scenario or removed; named measurement gates. |
| Vision | Fifth Age, RedDog-to-Red-God, anarchy, and 1494 framing were absent or easily read as literal implementation/history. | Added project framing, current-vs-target caveats, and sourced 1494 accounting waypoint. |
| DAE vocabulary | Decentralized, Distributed, Digital, and Distributive were used as competing definitions. | Canonicalized governance and contextual aliases in WSP 73/80 and identity vocabulary. |

## Current truth after repair

| Capability | WSP 97 state |
|---|---|
| RedDog VSIX conversation and governed model surface | OBSERVED |
| Evaluation fallback isolated from action planning | OBSERVED |
| HoloIndex read-only generation/route contracts | OBSERVED, subject to current route/freshness proof |
| AgentDB/session and Principal Memex admission building blocks | OBSERVED |
| Authenticated durable resident conversation service | SPECIFIED_NOT_IMPLEMENTED |
| ChatGPT-like cross-session/cross-surface continuity | SPECIFIED_NOT_IMPLEMENTED |
| p.fMALL/phone RedDog adapter | SPECIFIED_NOT_IMPLEMENTED |
| Automatic conversation-to-work binding | SPECIFIED_NOT_IMPLEMENTED |
| Universal health-to-autonomous-job loop | SPECIFIED_NOT_IMPLEMENTED |
| Universal Progressive Web Agent scaffold | TARGET |
| WSP 98 mesh/zero-server RedDog | TARGET |
| One OpenClaw process is RedDog | FALSE |
| Browser/PWA text creates work authority | FALSE |
| Hermes is conversation or policy authority | FALSE |
| Model choice creates production authority | FALSE |

## High-risk assumption audit

### Assumptions

- Existing AgentDB, signer/session, HoloIndex, AI Gateway, OpenClaw, WRE, and
  Hermes contracts remain the intended building blocks.
- Product identity can be continuous before durable cross-surface continuity
  is implemented, provided docs label that gap.
- Resident-hub deployment is the safest first scale layer; mesh must preserve
  the same authority invariants.

### Failure modes

- A client impersonates principal, session, FoundUp, or effect scope.
- Conversation success is mistaken for work authorization.
- A model/proposer promotes its own runtime topology.
- OpenClaw supervision or Hermes execution is mistaken for WRE authority.
- Browser state becomes durable policy, wallet, replay, or receipt authority.
- Memory crosses principal/FoundUp scope or overrides current repository truth.
- A target architecture is documented as deployed capacity.

### Alternatives rejected

- RedDog equals one personal OpenClaw process.
- RedDog is only the VSIX/webview.
- The phone hosts the full OpenClaw/WRE/Hermes stack by default.
- A new conversation database/router replaces AgentDB building blocks.
- A speculative universal mesh SDK is implemented before resident identity and
  durable ordering.
- Static GLM/Qwen/Kimi/DeepSeek choices become permanent protocol topology.

### Decision

`PROCEED` for canonical documentation and mirror repair. `HALT` for live
PFMall/phone transport, conversation-to-work promotion, autonomous repair, or
mesh claims until each phase has authenticated runtime evidence and adversarial
tests.

## Files aligned

- `WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md`
- `WSP_framework/src/WSP_80_Cube_Level_DAE_Orchestration_Protocol.md`
- `WSP_framework/src/WSP_98_FoundUps_Mesh_Native_Architecture_Protocol.md`
- exact `WSP_knowledge/src/` mirrors and master index
- `modules/foundups/docs/FOUNDUPS_MASTER_ARCHITECTURE.md`
- `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md`
- `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md`
- RedDog, Digital Twin, p.fMALL, root vision, vocabulary, and registry docs

## Residual separately scoped debt

- RedDog README is at its 1,000-line ceiling; moltbot_bridge README and
  INTERFACE are also near/over documentation thresholds. Decompose history and
  implementation detail before expanding them.
- Durable conversation/session binding is the next implementation layer.
- A shared readiness/security receipt, effect promotion binding, p.fMALL/phone
  adapter, governed Memex recall, and WSP 109 onboarding follow as separate
  WSP 15 transactions.
- Repository-wide WSP mirror validation reports unrelated pre-existing drift
  outside WSP 73/80/98/master index; this transaction does not overwrite those
  protocols without their own audit.

No runtime code, Holo route, model state, browser state, worker queue, wallet,
or external service was changed by this documentation transaction.
