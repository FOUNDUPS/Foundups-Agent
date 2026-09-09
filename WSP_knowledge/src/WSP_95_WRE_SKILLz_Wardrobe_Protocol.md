# WSP 95: WRE Skillz Wardrobe Protocol

**Version**: 2.2 (Skillz Necessity and Progressive Disclosure)
**Date**: 2026-09-10
**Status**: Active
**Authority**: WSP framework under 012 sovereignty
**Relationships**: WSP 3, WSP 15, WSP 22, WSP 46, WSP 48, WSP 50, WSP 62, WSP 71, WSP 73, WSP 77, WSP 84, WSP 97

---

## 1. Purpose

WSP 95 governs how task-specific Skillz are justified, designed, discovered,
admitted, executed, measured, evolved, and considered for production. A Skillz
document is an instruction artifact. It is not code authority, effect authority,
an authenticated outcome, or proof of recursive self-improvement.

The Wardrobe pattern distributes Skillz beside the module that owns them while
the WRE registry provides exact discovery and admission metadata. This supports
many FoundUps without granting filesystem location or model output implicit
authority.

---

## 2. Canonical terms

- **Skillz**: a task-specific instruction document named `SKILLz.md`.
- **Legacy Skill**: a `SKILL.md` accepted only when `SKILLz.md` is absent.
- **Wardrobe**: the distributed set of module-owned Skillz directories.
- **Registry**: `skills_registry_v2.json`, whose checkout-relative location is
  the only generic WRE discovery authority.
- **Programmatic executor**: an optional adjacent `executor.py`.
- **Structural fidelity**: a shape/completeness signal. It is not correctness.
- **Effect receipt**: a typed record declared by an admitted programmatic
  executor for an attempted effect. Its presence is necessary but does not by
  itself authenticate the effect outside the executor trust boundary.
- **Outcome quality**: independently evaluated quality evidence. It is unknown
  until an authenticated evaluator supplies it.
- **Candidate**: a non-production variation awaiting independent verification.
- **Production admission**: an explicit authority decision bound to an exact
  artifact, runtime, evidence set, and rollback plan.

### 2.1 The Three Skill Questions

Before creating a new Skillz, materially expanding one, or splitting a parent
Skillz into child Skillz, 0102 MUST answer:

1. **Do we need it?** Is the workflow recurring or consequential enough that
   repeated manual reasoning creates material cost, delay, inconsistency, or
   risk?
2. **Can we live without it?** Can an existing WSP, tool, Skillz, parent branch,
   or short one-off procedure handle the work reliably without another
   persistent abstraction?
3. **Can we afford not to have it?** What is the expected cost of omission:
   missed actions, repeated work, context loss, inconsistent execution, lost
   evidence, safety failure, or operational drift?

The answers and rationale are part of the creation/evolution evidence. A new
Skillz is not justified merely because a workflow can be written down.

Default decision discipline:

- If an existing Skillz can absorb the behavior coherently, **extend or branch
  the existing Skillz** rather than create a sibling.
- If the task is rare, low-consequence, and easily reconstructed, **do not
  Skillz it**.
- If recurrence and omission cost are material and no existing instruction unit
  can own it coherently, **create a prototype Skillz**.
- A child branch becomes a separate Skillz only when it has a distinct trigger,
  procedure, resource set, evaluation contract, or lifecycle and independently
  passes the Three Skill Questions.

These questions are a creation gate, not production authority. A Skillz that
passes them still enters the lifecycle at `prototype` unless separately admitted.

### 2.2 Skillz authoring and progressive disclosure

Skillz should be coherent, triggerable LEGO blocks rather than large context
dumps. Current cross-agent Skill formats reinforce the same scalable pattern:
small discovery metadata, instructions loaded only when relevant, and supporting
resources loaded only when needed.

FoundUps therefore requires:

- `name` and `description` must make the positive trigger clear; descriptions
  SHOULD also make important near-miss/non-trigger boundaries clear.
- Keep the main `SKILLz.md` focused on the procedure, invariants, routing, and
  resource map. Move conditional depth into adjacent `references/`, `scripts/`,
  or other governed resources when that reduces routine context load.
- Prefer one parent Skillz with explicit conditional branches when branches
  share the same identity, evidence, tools, and lifecycle.
- Split only when branch independence passes Section 2.1.
- New or materially changed Skillz SHOULD include representative evaluations
  covering normal triggers, near-miss non-triggers, edge cases, and known risky
  failure modes. Production still requires the stronger independent evidence in
  Section 3.1.
- Instructions must be grounded in observed workflows, repository contracts,
  and known failure modes rather than speculative complexity.
- External Agent Skills portability uses the open `SKILL.md` convention. FoundUps
  retains canonical internal `SKILLz.md` under WSP 95; any portable export or
  compatibility surface must preserve the internal authority boundary rather
  than silently renaming or promoting artifacts.

---

## 3. Lifecycle

| State | Meaning | Runtime effect authority |
|---|---|---|
| `prototype` | Design and local evaluation | None |
| `staged` | Controlled evaluation with evidence collection | None by state alone |
| `candidate_ready` | A/B or research evidence nominated a candidate | None |
| `production` | Registry/frontmatter state eligible for runtime admission | Conditional on every runtime gate |

A lifecycle label never proves safety, correctness, or promotion authority.
Movement between locations is an administrative operation, not promotion
evidence. HoloIndex discovery or reindexing never grants runtime authority.

### 3.1 Promotion authority

Production admission requires all of the following:

1. exact Skillz and optional executor digests;
2. independently verified held-out outcome evidence;
3. regression and security evidence;
4. an exact runtime/model/tool binding;
5. an explicit authorized promotion receipt;
6. a tested rollback capability;
7. immutable lineage from proposer through verifier and promoter.

The proposer/author cannot be the sole verifier or promoter. Model consensus,
structural fidelity, A/B statistics, or PatternMemory state cannot replace the
independent authority chain. 012 remains sovereign.

`PatternMemory.promote_variation()` is a legacy compatibility name that fails
closed until the independent signed promoter exists.

---

## 4. Registry and source contract

### 4.1 Registry requirements

Every executable registry entry must contain a checkout-relative module path.
Absolute paths, drive-qualified paths, traversal, links, junctions, and reparse
points fail admission.

For production entries, registry values and Skillz frontmatter must agree
exactly for `name`, `version`, `intent_type`, and `promotion_state: production`.
Provider-neutral role Skillz must also use an allowlisted schema and exact
logical-role bindings. Model names in prose, memory, or Skillz content are not
runtime authority.

JSON command/action configurations are not Skillz. They must be invoked by
their owning handler and must not be registered as executable WRE Skillz.

### 4.2 Source files

The canonical source is:

```text
modules/<domain>/<module>/skillz/<skill_name>/SKILLz.md
```

`SKILL.md` is a compatibility fallback only when `SKILLz.md` is absent. An
optional programmatic executor must be exactly:

```text
modules/<domain>/<module>/skillz/<skill_name>/executor.py
```

Repository-wide same-name search cannot substitute a different executor.

### 4.3 Manifest and scanner gate

Every production Skillz directory requires `SKILL_MANIFEST.json`. The manifest
binds every present `SKILLz.md`, legacy `SKILL.md`, and `executor.py` by SHA-256.

Before execution, WRE must verify exact production registry/frontmatter
agreement, resolve the registered Skillz inside the active checkout, reject
link/reparse components, verify the manifest/unexpected-file set, execute the
configured scanner in required/enforced mode, bind scanner cache to the exact
bundle fingerprint, prove the fingerprint is unchanged after scanning, and bind
dispatch to that admitted fingerprint and captured executor bytes.

Disabling production scanner requirement or verdict enforcement is a
misconfiguration and must fail admission closed. A TTL-only path cache is
insufficient.

---

## 5. Execution truth

### 5.1 Fail-closed loading

Missing, malformed, retired, unhealthy, unregistered, unreadable, or
non-production Skillz fail that execution closed without crashing orchestration.
Synthetic fallback instructions cannot create a successful outcome. A cache hit
cannot bypass a fresh hygiene decision.

### 5.2 Local model boundary

Local model inference produces a proposal only. Non-empty or structured text,
refusal text, or apparent completion language is not effect evidence.
Unsupported agents/model paths and generation failures return stable typed
failures without raw exception text. A proposal may inform a later governed
action; it cannot be stored as successful effect execution.

### 5.3 Programmatic executor boundary

An executor is eligible only when adjacent to the exact registry-bound Skillz,
a regular non-link/non-reparse file, included in the adjacent manifest, read
with the manifest-bound digest, dispatched after production admission/scanner
success, and captured with the exact admitted bundle.

Executor results require an exact built-in Boolean `success`. A successful
result also requires a non-empty list of typed effect receipts containing at
least `receipt_id` and `effect_type`. Missing/malformed results, reported
failure, import/compile failure, and exceptions remain failures.

### 5.4 PatternMemory and fidelity

Structural fidelity cannot establish effect success, outcome quality, semantic
correctness, non-regression, security, or production authority. Failed execution
has `outcome_quality = 0.0`; successful execution also retains 0.0 until an
independently authenticated evaluator binds stronger evidence.

### 5.5 ReAct acceptance

A ReAct attempt exposes separate `execution_success` and overall `success`.
Exhausting retries with low fidelity returns `success: false` even if the last
underlying executor attempt succeeded.

### 5.6 A/B boundary

Generic WRE runtime A/B selection is blocked until treatment content/executable
is bound to an immutable candidate digest and runtime receipt. Generic evolution
may store a proposed variation but must not automatically schedule an unbound
runtime test. A/B statistics may set `candidate_ready`; they must not update the
production artifact, activate recall, reindex HoloIndex, authorize effects, or
emit a promotion claim.

### 5.7 Legacy experimental paths

Generic CodeAct execution is a prototype and must fail closed until it uses the
same production admission, immutable receipt, and effect-result contract.
Legacy direct Agentic RAG access is not an authorized Holo query route.

---

## 6. WRE, RSI, and RedDog

WRE is the intended recursive-improvement control plane:

```text
apply Three Skill Questions
  -> discover/author smallest coherent Skillz
  -> admit Skillz
  -> execute exact authority
  -> record execution truth
  -> evaluate independently
  -> nominate candidate
  -> verify held-out/regression/security evidence
  -> authorize promotion
  -> bind production artifact/runtime
  -> monitor and retain rollback
```

Only bounded portions of this chain are implemented in generic legacy paths.
Candidate storage exists, but governed end-to-end promotion does not. Generic
WRE must not claim production RSI.

RedDog may use WRE to plan/supervise work, OpenClaw to apply governed policy,
and Hermes to execute bounded leaf work. WSP 95 grants none of those systems
authority merely because a Skillz document names them.

---

## 7. Scale and modularity

Wardrobes are module-local LEGO blocks. Scaling requires metadata discovery
before full-content loading, deterministic registry lookup, content-fingerprint
scanner caches, no global mutable production promotion state, per-FoundUp
namespaces/work-item lineage, bounded queues/retries/independent verification,
and observable typed failures.

WSP 95 does not implement the hundred-agent scheduler. WSP 46, WSP 77, WSP 80,
WSP 98, and WSP 104 own surrounding contracts.

---

## 8. Current implementation truth

| Capability | State |
|---|---|
| Checkout-local registered Skillz resolution | Implemented |
| Production registry/frontmatter admission | Implemented |
| Hygiene before digest-bound cache return | Implemented |
| Manifest/scanner bundle admission | Implemented |
| Scanner receipt-bound captured executor dispatch | Implemented |
| Exact Boolean result and typed effect-receipt validation | Implemented |
| Local model proposal-only boundary | Implemented |
| Post-dispatch failure propagation into PatternMemory | Implemented |
| ReAct success/fidelity separation | Implemented |
| `candidate_ready` storage primitive | Implemented |
| Three Skill Questions runtime enforcement | Specified; not yet generic runtime-enforced |
| Progressive resource loading | Design requirement; runtime support varies |
| Generic CodeAct execution | Prototype; runtime blocked |
| Governed Holo owner retrieval adapter | Not implemented; direct path blocked |
| Authenticated A/B candidate/runtime binding | Not implemented; runtime blocked |
| Independent durable production promoter | Not implemented |
| Automatic artifact update and governed rollback | Not implemented |
| HoloIndex promotion activation | Not implemented |
| Production end-to-end RSI canary | Not proven |

---

## 9. Verification requirements

Owning module tests must prove applicable admission, manifest, scanner,
mutation, exact-Boolean/effect-receipt, exception-hygiene, proposal-only,
fidelity, ReAct, A/B, and framework/knowledge-copy invariants. New or materially
changed Skillz should additionally test trigger boundaries and representative
output-quality/failure cases derived from Section 2.2.

Tests must isolate temporary paths and pattern-memory DBs to approved
non-production locations.

---

## 10. Documentation and change control

Any runtime behavior change must update owning structured memory as applicable.
Framework and knowledge copies of WSP 95 must remain byte-identical under WSP
32. WSP 62 applies to runtime and documentation. A candidate cannot authorize
its own exemption.

Changes to Skillz creation policy must record the Section 2.1 rationale and
consult WSP_MASTER_INDEX per WSP 64 before creating any new WSP. WSP 95 owns
Skillz governance; overlapping Skillz-creation WSPs should not be created unless
a genuinely separate domain passes the WSP creation decision matrix.

---

## 11. Version history

- **2.2 (2026-09-10)**: Added the mandatory Three Skill Questions creation/
  branching gate; parent-before-child discipline; progressive disclosure,
  trigger-boundary, evaluation, and portable Agent Skills compatibility guidance.
- **2.1 (2026-08-26)**: Bound scanner success to stable pre/post bundle
  fingerprints and captured executor bytes; blocked unadmitted CodeAct and
  direct legacy Holo access.
- **2.0 (2026-08-26)**: Consolidated execution truth and independent promotion
  authority; removed contradictory automatic fallback/promotion/rollback claims.
- **1.6 (2026-08-26)**: Added execution-truth and promotion-authority addendum.
- **1.5 (2026-07-29)**: Added provider-neutral role Skillz constraints.
- **1.4 and earlier**: Historical Wardrobe lifecycle/evolution design;
  superseded where inconsistent with current protocol.
