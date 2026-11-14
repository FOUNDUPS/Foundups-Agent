# WSP 95: WRE Skillz Wardrobe Protocol

**Version**: 2.1 (Admission Receipt Binding)
**Date**: 2026-08-26
**Status**: Active
**Authority**: WSP framework under 012 sovereignty
**Relationships**: WSP 3, WSP 22, WSP 46, WSP 48, WSP 50, WSP 62, WSP 71, WSP 73, WSP 77, WSP 84, WSP 97

---

## 1. Purpose

WSP 95 governs how task-specific Skillz are discovered, admitted, executed,
measured, evolved, and considered for production. A Skillz document is an
instruction artifact. It is not code authority, effect authority, an
authenticated outcome, or proof of recursive self-improvement.

The Wardrobe pattern distributes Skillz beside the module that owns them while
the WRE registry provides exact discovery and admission metadata. This supports
many FoundUps without granting filesystem location or model output implicit
authority.

This version replaces the contradictory fallback, automatic-promotion,
automatic-rollback, and model-as-verifier wording formerly retained in this
protocol. Git history preserves that historical design; it is not active
runtime authority.

---

## 2. Canonical terms

- **Skillz**: a task-specific instruction document named `SKILLz.md`.
- **Legacy Skill**: a `SKILL.md` accepted only when `SKILLz.md` is absent.
- **Wardrobe**: the distributed set of module-owned Skillz directories.
- **Registry**: `skills_registry_v2.json`, whose checkout-relative location
  is the only generic WRE discovery authority.
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
exactly for:

- `name`;
- `version`;
- `intent_type`;
- `promotion_state: production`.

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

`SKILL.md` is a compatibility fallback only when `SKILLz.md` is absent.
An optional programmatic executor must be exactly:

```text
modules/<domain>/<module>/skillz/<skill_name>/executor.py
```

Repository-wide same-name search cannot substitute a different executor.

### 4.3 Manifest and scanner gate

Every production Skillz directory requires `SKILL_MANIFEST.json`. The
manifest binds every present `SKILLz.md`, legacy `SKILL.md`, and
`executor.py` by SHA-256.

Before execution, WRE must:

1. verify exact production registry/frontmatter agreement;
2. resolve the registered Skillz inside the active checkout;
3. reject link/reparse components before resolution;
4. verify the manifest and unexpected-file set;
5. execute the configured skill scanner in required/enforced mode;
6. bind any scanner cache to the exact current bundle fingerprint;
7. prove the bundle fingerprint is unchanged after scanning;
8. bind dispatch to that exact admitted fingerprint and captured executor bytes.

Disabling either production scanner requirement or verdict enforcement is a
misconfiguration and must fail admission closed.

A TTL-only path cache is insufficient. A changed Skillz, executor, or manifest
must produce a different fingerprint and a new admission decision.

---

## 5. Execution truth

### 5.1 Fail-closed loading

Missing, malformed, retired, unhealthy, unregistered, unreadable, or
non-production Skillz fail that execution closed without crashing the
orchestration process.

Synthetic fallback instructions cannot create a successful outcome. A cache
hit cannot bypass a fresh hygiene decision, and cached content must be bound to
the current source digest.

### 5.2 Local model boundary

Local model inference produces a proposal only. Non-empty text, structured
text, refusal text, or apparent completion language is not effect evidence.
Unsupported agents, unavailable model paths, import failures, initialization
failures, and generation exceptions return stable typed failures without raw
exception text.

A proposal may inform a later governed action. It cannot be stored as a
successful effect execution.

### 5.3 Programmatic executor boundary

An executor is eligible only when it is:

- adjacent to the exact registry-bound Skillz document;
- a regular non-link/non-reparse file;
- included in the adjacent manifest;
- read with the manifest-bound digest;
- dispatched only after production admission and scanner success;
- captured with the exact bundle whose fingerprint passed admission.

Executor results require an exact built-in Boolean `success`. Truthy strings
and integers are malformed. A successful result also requires a non-empty list
of typed effect receipts containing at least `receipt_id` and `effect_type`.
Missing/malformed results, reported failure, import/compile failure, and
exceptions remain failures. Raw exception text must not enter logs, returned
records, PatternMemory, or continuity breadcrumbs.

### 5.4 PatternMemory and fidelity

Structural fidelity answers only whether expected fields or patterns were
present. It cannot establish:

- effect success;
- outcome quality;
- semantic correctness;
- non-regression;
- security;
- production authority.

Post-dispatch outcomes may be stored with actual effect success. Failed
execution has `outcome_quality = 0.0`. Successful execution also retains
`outcome_quality = 0.0` until an independently authenticated evaluator binds
stronger evidence. Admission failures may be recorded by a separate typed audit
surface; absence from PatternMemory is not success.

### 5.5 ReAct acceptance

A ReAct attempt exposes two separate facts:

- `execution_success`: an admitted executor supplied effect evidence;
- `success`: execution succeeded and structural fidelity met the requested
  acceptance threshold.

Exhausting retries with low fidelity returns `success: false`, even when the
last underlying executor attempt succeeded.

### 5.6 A/B boundary

Generic WRE runtime A/B selection is blocked until the treatment content or
executable is bound to an exact immutable candidate digest and runtime receipt.
Control content must never be recorded as treatment evidence.

Generic evolution may store a proposed variation, but it must not automatically
schedule an unbound runtime test. Scheduling is an explicit governed action.
Each named arm must meet its own sample target, and every outcome requires an
exact Boolean. Closing a test durably records only its statistical label.

A/B statistics may call `stage_variation_candidate()` to set
`candidate_ready`. They must not update the production artifact, activate
recall, reindex HoloIndex, authorize effects, or emit a promotion claim.

### 5.7 Legacy experimental paths

Generic CodeAct execution is a prototype and must fail closed until it uses the
same production admission, immutable receipt, and effect-result contract.
Legacy direct Agentic RAG access is not an authorized Holo query route and must
remain disabled. Production retrieval requires the generation-bound read-only
owner service; an unavailable or stale owner route fails closed.

---

## 6. WRE, RSI, and RedDog

WRE is the intended recursive-improvement control plane. WSP 95 supplies one
governed learning boundary inside it:

```text
admit Skillz
  -> execute exact authority
  -> record execution truth
  -> evaluate independently
  -> nominate candidate
  -> verify held-out/regression/security evidence
  -> authorize promotion
  -> bind production artifact/runtime
  -> monitor and retain rollback
```

Only the first three capabilities exist in the generic legacy path.
Candidate storage exists, but governed end-to-end promotion does not. Therefore
generic WRE must not claim production RSI.

RedDog may use WRE to plan and supervise work, OpenClaw to apply governed policy,
and Hermes to execute bounded leaf work. WSP 95 grants none of those systems
authority merely because a Skillz document names them.

---

## 7. Scale and modularity

Wardrobes are module-local LEGO blocks. A registry may index hundreds of
Skillz across hundreds of FoundUps, but runtime execution must remain
tenant-scoped and content-bound.

Scaling requirements:

- metadata discovery before full-content loading;
- deterministic registry lookup, never repository-wide executor search;
- content-fingerprint scanner caches and collision-free per-bundle reports;
- no global mutable production promotion state;
- per-FoundUp namespaces and work-item lineage;
- bounded queues, leases, retries, and independent verification under WSP 77;
- observable typed failures under WSP 91.

WSP 95 does not implement the hundred-agent scheduler. WSP 46, WSP 77,
WSP 80, WSP 98, and WSP 104 own those surrounding contracts.

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
| Generic CodeAct execution | Prototype; runtime blocked |
| Governed Holo owner retrieval adapter | Not implemented; direct path blocked |
| Authenticated A/B candidate/runtime binding | Not implemented; runtime blocked |
| Independent durable production promoter | Not implemented |
| Automatic artifact update and governed rollback | Not implemented |
| HoloIndex promotion activation | Not implemented |
| Production end-to-end RSI canary | Not proven |

---

## 9. Verification requirements

The owning module tests must prove at minimum:

- retired/unhealthy cache poisoning fails;
- unregistered and non-production Skillz fail;
- registry/frontmatter drift fails;
- link/reparse and checkout escape paths fail;
- manifests include adjacent executors and reject digest mismatch;
- mutation during scanning or between scan and dispatch fails;
- truthy-string success fails;
- success without typed effect receipts fails;
- executor exceptions do not leak exception text;
- local model failures return stable failures;
- local model text remains proposal-only;
- structural fidelity cannot create outcome quality;
- low-fidelity ReAct exhaustion returns failure;
- active unbound A/B runtime selection fails closed;
- framework and knowledge copies of WSP 95 are byte-identical.

Tests must isolate `TMP`, `TEMP`, `FOUNDUPS_DB_PATH`, pattern-memory DBs,
pytest base temp, and pytest cache to approved non-production locations.

---

## 10. Documentation and change control

Any runtime behavior change must update the owning README, INTERFACE, ROADMAP,
ModLog, tests README, and TestModLog as applicable. Framework and knowledge
copies of WSP 95 must remain byte-identical under WSP 32.

WSP 62 applies to runtime and documentation. A candidate cannot authorize its
own exemption. A touched hard-limit file must be reduced below the limit or use
an exemption already present at the exact comparison base.

---

## 11. Version history

- **2.1 (2026-08-26)**: Bound scanner success to stable pre/post bundle
  fingerprints and captured executor bytes; blocked unadmitted CodeAct and
  direct legacy Holo access.
- **2.0 (2026-08-26)**: Consolidated execution truth; removed contradictory
  automatic fallback/promotion/rollback claims; defined production admission,
  proposal/effect separation, typed effect receipts, content-bound caching,
  A/B blocking, independent promotion authority, and exact implementation truth.
- **1.6 (2026-08-26)**: Added execution-truth and promotion-authority addendum.
- **1.5 (2026-07-29)**: Added provider-neutral role Skillz constraints.
- **1.4 and earlier**: Historical Wardrobe lifecycle and automatic evolution
  design; superseded where inconsistent with version 2.1.
