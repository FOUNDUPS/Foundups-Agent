# WSP 80: Cube-Level DAE Orchestration Protocol

- **Status:** Active
- **Version:** 3.0
- **Updated:** 2026-08-26
- **Purpose:** Apply WSP 27's FoundUp/DAE lifecycle to independently scoped
  cubes of modules without hard-coding a model, tool transport, worker runtime,
  or unbounded resource claim.
- **Dependencies:** WSP 3, WSP 15, WSP 27, WSP 46, WSP 49, WSP 60, WSP 73,
  WSP 77, WSP 84, WSP 95, WSP 97, WSP 103, WSP 104

## 1. Canonical definition

A **cube** is the complete, independently scoped set of modules and contracts
that realizes one FoundUp capability or one cohesive FoundUp. A **cube DAE** is
the 0102/WRE orchestration state operating that cube under current WSP,
identity, memory, and effect authority.

```text
CubeDAE := FoundUp scope + modules + interfaces + memory + skills
           + admitted workers + verification + receipts
```

DAE means Decentralized or Distributed Autonomous Entity/Ecosystem under WSP
27. "Digital Autonomous Entity" may describe its software embodiment. A DAE is
not conscious or self-authorizing, and a model, module, interface, daemon, or UI
does not become a DAE by adopting state vocabulary.

## 2. Why cube scope exists

Whole-repository agents repeatedly rediscover unrelated code, mix tenant
authority, and spend compute without improving a specific outcome. Cube scope
provides:

- one FoundUp/problem/outcome boundary;
- bounded retrieval and context;
- explicit module and dependency ownership;
- reusable skills and receipts;
- local health and roadmap evidence; and
- independent evolution without copying a parallel platform stack.

The architecture can create many cubes, but real compute, storage, model calls,
workers, and authority remain finite and scheduled. "Unbounded-by-design" is
not an infinite-capacity or zero-cost claim.

## 3. Distinctions

| Term | Meaning | Non-claim |
|---|---|---|
| Module | Code and documentation with one bounded responsibility | Not an agent or authority |
| Interface | Public contract between modules/cubes | Not an implementation or worker |
| Skill | Executable instruction/capability contract admitted by WRE | Not standing permission |
| Worker | One model or scaffolded runtime performing a bounded job | Not the cube or sovereign authority |
| Cube | Cohesive modules/contracts for one FoundUp scope | Not automatically autonomous |
| Cube DAE | Governed orchestration of a cube through 0102/WRE | Not conscious or permanently privileged |
| RedDog | Principal-scoped 0102 Digital Twin identity and operator interface | Not one cube or worker runtime |

## 4. Required cube contract

Every admitted cube declares:

1. `foundup_id` or infrastructure-scope identity;
2. problem, desired outcome, and current lifecycle stage;
3. owned modules and public interfaces;
4. inbound/outbound dependencies and data classifications;
5. memory ownership under WSP 60;
6. allowed skills, worker types, and effect ceilings;
7. health, test, documentation, security, and readiness evidence;
8. current roadmap and WSP 15 priorities; and
9. rollback, cancellation, and receipt locations.

FoundUp routes and data namespaces satisfy WSP 104. Cross-cube work uses public
interfaces or WSP 103 federation contracts; it does not reach into another
cube's internal files, memory, credentials, or tenant state.

## 5. Four-phase lifecycle

WSP 27 remains authoritative:

```text
-1 Signal  -> problem/outcome candidate
 0 Knowledge -> research, repository discovery, memory, constraints
 1 Protocol  -> interfaces, WSPs, acceptance, threat/failure model
 2 Agentic   -> bounded execution, verification, operation, learning
```

Each phase is revisitable. A failed test, changed requirement, security finding,
or observed outcome may return the cube to Knowledge or Protocol. Phase 2 is
not a permanent autonomy grant.

## 6. Orchestration authority

```text
012 work focus
  -> RedDog/0102 requirements and evidence
  -> WSP 15 allocation
  -> WRE decomposition and admission
  -> AI Gateway model topology and/or deterministic local tools
  -> OpenClaw supervision when a channel/job runtime is required
  -> WRE execution/effect authority
  -> Hermes or another bounded leaf worker
  -> tests, receipts, Overseer review
  -> governed memory/roadmap candidates
```

WRE owns repository/process execution, verification, and recursive learning.
OpenClaw can supervise policy and job lifecycle. Hermes can execute a bounded
leaf job. HoloIndex supplies generation-bound discovery. MCP may carry a tool
contract. None of these names is mandatory when the capability is unnecessary,
and none acquires authority merely by appearing in a route.

## 7. Model and worker selection

No protocol may hard-code Qwen, Gemma, Nemotron, GLM, Kimi, DeepSeek, or another
model as the universal cube orchestrator.

- RedDog emits task requirements.
- AI Gateway admits eligible providers/models and current runtime topology.
- Local deterministic tools should perform deterministic work.
- Nemotron or another proposer may suggest evaluation candidates but cannot
  promote itself.
- AutoResearch measurements require held-out, reserved campaigns and
  independent promotion authority.
- A static evaluation roster is dialogue/evaluation only and cannot open
  execution.
- Every worker receives the smallest context and effect capability needed for
  one job.

Changing models must not change cube identity, memory ownership, work-order
scope, acceptance criteria, or effect authority.

## 8. Memory and retrieval

Cube operation begins with repository discovery, not generation from recall.

1. Query the governed HoloIndex owner when it can prove `CURRENT`, gap-free,
   exact-generation evidence.
2. Evaluate retrieval noise, ordering, missing artifacts, staleness, and
   duplication.
3. Verify results through `NAVIGATION.py`, module documentation, interfaces,
   tests, and direct repository reads.
4. If HoloIndex fails, preserve the exact failure and route maintenance; never
   reindex from the query path.
5. Use Principal Memex only under principal scope and FoundUp Memex only under
   the selected FoundUp scope.

Memory informs decisions. Current repository/receipt evidence controls code and
work truth. Learning is proposed and promoted through governed receipts rather
than written directly by the worker that generated it.

## 9. Micro-sprint execution

One cube transaction follows this loop:

```text
identify outcome
  -> WSP 15 score and smallest layer
  -> research existing modules/interfaces
  -> enumerate assumptions and failure modes
  -> choose deterministic tool or admitted worker topology
  -> execute in bounded scope
  -> run focused and adjacency tests
  -> update interfaces/docs/ModLogs
  -> independent WSP 97 audit
  -> land receipt or rollback
  -> allocate the next layer
```

If a touched module exceeds WSP 62 structure limits or has no safe growth
headroom, extraction is part of the transaction before additional behavior is
added. Thresholds are refactoring signals, not permission to raise a ceiling.

## 10. Health and recursive operation

A cube health view distinguishes observed evidence from target work:

- repository and dependency freshness;
- upstream patches and security advisories;
- interface and documentation drift;
- WSP/structure violations and scores;
- focused, adjacency, and release-test state;
- open jobs, claims, cancellations, and receipts;
- resource/capacity limits; and
- last independent audit.

Overseer/sentinel workers may inspect and propose jobs. Their findings cannot
self-authorize repairs. WRE admits only jobs with current scope, authority,
acceptance, rollback, and concurrency evidence.

## 11. Scaling and federation

Cube independence enables scheduling and horizontal execution; it does not
prove scale. Capacity claims require measured named deployments.

- One process may host multiple logically isolated cubes.
- One cube may use multiple stateless workers behind durable ordering.
- A phone/PWA normally remains a thin client to resident RedDog services.
- WSP 103 governs cross-FoundUp federation.
- WSP 98 governs peer-assisted/mesh progression.
- No browser/device becomes identity, memory, policy, or execution authority by
  participating in a mesh.

## 12. Current repository truth

| Capability | State |
|---|---|
| WSP 27 FoundUp/DAE lifecycle | Active protocol |
| WRE, WSP orchestrator, HoloIndex, Skill wardrobe, OpenClaw, and Hermes adapters | Implemented components with differing maturity and gates |
| AI Gateway receipt-bound model topology | Implemented building blocks |
| Universal automatic cube spawning | Not implemented |
| One measured health/readiness view for every cube | Not implemented |
| Automatic safe remediation from Overseer findings | Not implemented |
| Cross-FoundUp federation | Protocol/partial building blocks; not a universal runtime |
| Mesh-native/zero-server cubes | Target, not implemented |
| Fixed token, latency, uptime, fidelity, or scale guarantees | Not established |

Historical diagrams that assigned one Qwen instance to every cube, mandatory
MCP servers, Bell-state authentication, fixed five-DAE infrastructure,
zero-latency operation, or specific Cursor/Claude workers were design donors.
They are not current implementation or mandatory topology.

## 13. Acceptance checklist

- [ ] Cube identity, outcome, stage, modules, and namespaces are explicit.
- [ ] Existing code and interfaces were verified before creation.
- [ ] Retrieval quality and gaps are recorded.
- [ ] WSP 15 selects one smallest viable layer.
- [ ] Model/tool/worker choice is requirement- and receipt-bound, not
      hard-coded.
- [ ] Principal, FoundUp, repository, memory, and effect scopes are isolated.
- [ ] Concurrency, retry, cancellation, rollback, and resource bounds exist.
- [ ] Focused and adjacency verification passes.
- [ ] README, INTERFACE, ROADMAP, ModLog, and test docs reflect current truth.
- [ ] Independent WSP 97 review asks, "Did we assume instead of know?"

## 14. Anti-patterns

- Whole-repository context for a cube-local task.
- A universal model name embedded in the protocol.
- Model output treated as policy, identity, or effect authority.
- A module/interface/daemon labelled a DAE without the cube contract.
- Cross-cube private imports or memory access instead of a public contract.
- New databases, routers, queues, signers, or worker stacks without verifying
  the existing implementation.
- Big-bang FoundUp construction before one layer is tested.
- "Infinite," "zero cost," "zero latency," "100% uptime," or similar claims
  without bounded measurements.

## 15. References

- WSP 27: FoundUp/Partifact DAE architecture
- WSP 46: WRE
- WSP 60: memory ownership and isolation
- WSP 73: RedDog / 012 Digital Twin architecture
- WSP 77: agent coordination
- WSP 95: skills wardrobe
- WSP 97: truth-labelled system execution
- WSP 103: FoundUp federation
- WSP 104: tenant namespace isolation
- `modules/infrastructure/wre_core/`
- `modules/infrastructure/wsp_orchestrator/`
- `extensions/reddog/`
