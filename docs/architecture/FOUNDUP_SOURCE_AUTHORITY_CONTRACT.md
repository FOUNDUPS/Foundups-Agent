# FoundUp Source-Authority Contract -- Phase 1

**Slice**: `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1`
**Type**: Contract / design slice (decision-only). Authoritative definition of the
source-authority axis. Pins `monorepo_poc` as the only reachable stage in Phase-1.
**Worker-Lane**: W6
**Operator / Commander**: 012 (routing + merge authority, sovereign valve)
**Executor / 0102**: W6 (autonomous implementation)
**Effort**: ULTRA
**Date**: 2026-06-10
**Base**: `96a860cc3` (origin/main; post-#775 ContextBundle FIX2c)
**Status**: Phase-1 docs/architecture contract (not a WSP; see "WSP placement" below)

**WSP Lock**: WSP_00 -> WSP_11 -> WSP_27 -> WSP_30 -> WSP_50 -> WSP_64 -> WSP_84 ->
WSP_97 -> WSP_103 -> WSP_109 -> WSP_22

**Predecessors**
- #775 (merged `96a860cc3`): read-only `ContextBundle` producer with
  builder-constant `SOURCE_AUTHORITY = "monorepo_poc"`
  (`modules/foundups/agent/src/context_bundle_builder.py:132`). A manifest
  CANNOT self-promote -- `source_authority` is builder-set and ignored if
  declared by the manifest.
- `96314ab6c` `fix(wre): close authority laundering in ContextBundle output
  (W10 return)` -- load-bearing precedent. The prior builder forwarded
  `build_contract` list/scalar fields verbatim, allowing
  `safe_mutation_surface = {"payout_ready": true, "dao_approved": true}` and
  `readiness.build_ready = {"is_authorized": true}` to launder authority into
  `bundle.to_dict()`. FIX1 closed that via `_require_str_tuple` +
  `_require_strict_bool`, repaired WSP_97 rows
  `GATE_NAMES_ONLY_NOT_PASS_BOOLEANS` and `NO_CABR_PAYOUT_DAO`, and added
  `MANIFEST_LIST_FIELDS_STRING_ONLY`. That precedent is why **"cannot
  promote by declaration" is a hard rule, not a guideline**.

---

## 0. Phase 0 -- Mandatory Discovery (HoloIndex + WSP reads)

### HoloIndex retrieval (3 queries)

| # | Query | Signal | Notes |
|---|-------|--------|-------|
| 1 | `foundup lifecycle stage source authority monorepo proto mvp dao` | MEDIUM | Surfaced WSP_58 (IP lifecycle), WSP_98 (mesh-native architecture), WSP_100 (DAE/SmartDAO escalation); no existing `source_authority` enum hit. |
| 2 | `WSP 30 build orchestration foundup lifecycle IDEA PoC MVP` | HIGH | Direct hit on WSP_30, WSP_ORCHESTRATION_HIERARCHY, WSP_80 (cube-level DAE orchestration). |
| 3 | `source_authority lifecycle_stage enum SourceAuthority` | MEDIUM | Closest schema candidates: `modules/foundups/agent_market/src/models.py`, `modules/ai_intelligence/digital_twin/src/schemas.py`. **No existing `SourceAuthority` enum**. |

**Retrieval evaluation** (per WSP 87, recursive HoloIndex improvement):

- **Noise**: low-to-moderate. Marketing/viz hits (`public/litepaper.html`,
  `foundup-cube.js`) surfaced above pure-domain code for query 1 -- useful for
  terminology cross-check but borderline noise.
- **Ordering**: query 2 correct; queries 1 and 3 missed cross-linking
  `agent_market/src/models.py` between them.
- **Missing artifacts**: zero `[DOCS]` and `[KNOWLEDGE]` results across all
  three queries -- suspicious. Either those indices are sparse for this
  topic or the topic genuinely lacks canonical documentation (the latter
  is consistent with the gap this contract closes). WSP_27 (the canonical
  lifecycle reference) did not surface despite being load-bearing here --
  possible HoloIndex indexing gap to report separately.
- **Staleness risk**: WSP_98 / WSP_100 are recent; `litepaper.html` cadence
  unknown.
- **Duplication**: none across kinds.

**Recommendation logged**: a separate HoloIndex tuning slice should
investigate why WSP_27 / WSP_103 / WSP_109 did not surface for the
lifecycle queries.

### WSP placement audit

| Concern | Existing Coverage | Gap |
|---------|-------------------|-----|
| Entity type at intake | WSP 109 `entity_type` enum | Only at intake; no transitions |
| Tier progression | WSP 27 Section 11, WSP 100 | Tier != source ownership |
| Build stage (POC/Proto/MVP) | WSP 30 LLME | Code maturity, not source authority |
| Federation end-state | WSP 103 | Assumes external; no migration contract |
| External onboarding | WSP 106 | Entry only, no lifecycle transitions |
| CABR scoring | WSP 29 | Orthogonal axis |
| **Source-authority axis (who owns the source root per stage)** | **NONE** | **Gap confirmed** |
| **Promotion rules `monorepo_poc -> external_proto -> dao_managed_mvp`** | **NONE** | **Gap confirmed** |
| **Anti-self-promotion guard** | Implemented in builder; not specified | **Gap confirmed** |

**Recommendation**: `(c) REMAIN a docs/architecture contract for now`.

Justification (grounded in evidence, not asserted):

1. **Single consumer at present**. Only `context_bundle_builder.py` consumes
   `source_authority`. WSP 64 + WSP MASTER_INDEX decision matrix says
   "create new WSP" only when addressing a completely new domain proven
   across multiple consumers. Premature WSP risks lock-in.
2. **WSP 27 + WSP 103 + WSP 109 are the citation triad**. WSP 27 Section
   11.0 owns the maturity lifecycle (`WSP_27:637-642`); WSP 103 owns the
   OPO transition gate (`WSP_103:616-617`); WSP 109 owns intake / RedDog
   intake role and the `entity_type` enum (`WSP_109:42, :89-103, :350-360`).
   A docs/architecture contract citing the triad is sufficient binding.
3. **WSP 109 already partially covers intake-time source-authority** via
   `entity_type` (`WSP_109:350-360`). A new WSP would duplicate or force a
   WSP 109 amendment; neither is justified by current evidence.
4. **Promotion trigger** (when to revisit as a WSP): a SECOND module (FAM
   registry, OpenClaw launcher, or WRE planner) reads or writes
   `source_authority` outside the builder, OR a FoundUp actually
   transitions stage. At that point: follow-up slice
   `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_WSP_FORMALIZATION_PHASE1`.

This slice does NOT mutate any WSP file (`NO_WSP_FILE_MUTATION` is a
WSP_97 row below).

---

## 1. The two axes

This contract distinguishes two axes that are **coupled but distinct**:

- **Maturity axis** -- WHEN a FoundUp matures. Owned by WSP 27.
  Canonical sequence (verbatim from `WSP_27:637-642`):
  ```
  IDEA -> Validate (OBAI/0102) -> Passive Crowdfunding -> PoC ("blueprint")
    -> TEAM forms -> Soft-Proto ("Model") -> Crowdfunding 1
      -> Proto ("1st version") -> Crowdfunding 2
        -> MVP ("Customers") -> LAUNCH as Open Corp
          -> smartDAO / DAE -> spawns new IDEAS -> cycle repeats
  ```
- **Source-authority axis** -- WHERE the source / state lives and WHO may
  mutate it. **This contract defines it.** Five stages, defined in Section 2.

The source-authority axis is a finer-grained refinement of WSP 103's binary
(Pre-OPO `F0_DAE` vs Post-OPO `F1_OPO+`, `WSP_103:616-617`), with the OPO
gate as the inflection point. The coupling between the two axes is given
in Section 3.

### Why two axes (not one)

A FoundUp at maturity `Tier 4 Growing / Proto` may be either monorepo-resident
(if the team is small and trusted) or already living in an external repo
(if a "soft fork" spin-out happened earlier). Maturity does not uniquely
determine source ownership; the OPO gate (WSP 103) is the one mandatory
inflection, and even there the source may transition from external_proto
to mvp_runtime at the same maturity (LAUNCH event), independently of
whether the team has changed.

### OBAI / RedDog: actor, not stage (terminology drift recorded, not fixed)

WSP 27 does NOT name "OBAI" or "RedDog" as a maturity stage. The stages
list (`WSP_27:637-642`) treats OBAI as the validator inside Tier 7 Genesis
(`WSP_27:657` -- "OBAI (0102) validates the idea"). WSP 109 confirms
(`WSP_109:42, :89-103`): RedDog/0102 is the intake actor at the Validate
gate. This contract honors that distinction; OBAI/RedDog is not a
source-authority value.

### OPO LAUNCH vs smartDAO: sequential, not equal (derivation)

The dispatch demanded this be DERIVED from tier numbers, not assumed.

- WSP 27 places "LAUNCH as Open Corp" at Tier 2 Thriving (`WSP_27:640`
  and `WSP_27:663`).
- WSP 27 places "smartDAO" at Tier 1 Sovereign (`WSP_27:651, :663` --
  "When a FoundUp reaches Tier 1 (Sovereign), it becomes a smartDAO").
- WSP 103 names the operative launch event "OPO" (`WSP_103:616-620`),
  the visibility flip from Pre-OPO `F0_DAE` (PRIVATE) to Post-OPO
  `F1_OPO+` (PUBLIC).
- WSP 27's "LAUNCH as Open Corp" and WSP 103's "OPO" are the same event.

Therefore: **OPO LAUNCH = Tier 2; smartDAO = Tier 1**. These are
SEQUENTIAL points on the maturity axis. OPO LAUNCH precedes smartDAO.
This contract treats them as distinct points; `mvp_runtime` brackets
post-OPO LAUNCH operation, `dao_managed` brackets post-Tier-1-Sovereign
operation.

### Terminology drift recorded (not fixed in this slice)

- WSP 27 uses "smartDAO" (Tier 1 terminal autonomy state).
  WSP 103 uses "OPO LAUNCH" / "Post-OPO (F1_OPO+)". The two WSPs
  refer to overlapping but non-identical points on the lifecycle.
- WSP 27 does not name OBAI / RedDog as a stage; it is the validator
  at Tier 7 Genesis (WSP 109 confirms intake-actor reading).
- WSP 109's actual filename is
  `WSP_109_FoundUp_Onboarding_Intake_Protocol.md` (the dispatch used
  a federation-protocol filename; corrected in citations here).

**Recommended follow-up (do not execute here)**:
`WSP27_LIFECYCLE_TERMINOLOGY_ALIGNMENT_PHASE1` to harmonize the WSP 27 /
WSP 103 vocabularies (smartDAO vs OPO LAUNCH naming) and to give RedDog
an explicit actor-vs-stage callout in WSP 27 Section 11.

---

## 2. The five source_authority stages

Exactly **five** values. The string values are EXACT and stable; they are
the wire format of any downstream consumer.

| # | `source_authority` (enum value) | Phase-1 reachable? |
|---|---------------------------------|--------------------|
| 1 | `monorepo_poc`                  | YES (only value)   |
| 2 | `external_proto`                | NO (defined; not reachable) |
| 3 | `mvp_runtime`                   | NO (defined; not reachable) |
| 4 | `dao_managed`                   | NO (defined; not reachable) |
| 5 | `archived`                      | NO (defined; not reachable) |

### Per-stage matrix

Concrete for `monorepo_poc`; intent (not implementation) for the other four.

#### 2.1 `monorepo_poc` (ACTIVE in Phase-1)

| Dimension | Value |
|-----------|-------|
| Source location | `modules/foundups/<name>/**` inside the canonical monorepo (`FOUNDUPS/Foundups-Agent`). Cross-domain Phase-1 exceptions (e.g. `modules/gamification/whack_a_magat`, `modules/platform_integration/antifafm_broadcaster`) are permitted ONLY when the manifest's `build_contract.module_path` exact-matches the manifest's parent (validator-enforced per #773). |
| Test contract | `build_contract.test.command` argv-or-null only (no shell strings, no shell metacharacters, validator-enforced per #771/#773). Bundle includes declared test refs only when they resolve inside `module_root` (post-`Path.resolve()` symlink-escape check, #775). |
| Evidence store | `ContextBundle` provenance envelope (`build_context_bundle`, #775): refs + sha256 + size + role; no file bodies; deterministic `bundle_id`; stream-hashed; `max_context_bytes` fail-closed. |
| Ownership / governance | 012 (Commander, routing + merge authority, sovereign valve) + 0102 (Executor, autonomous within Truth Boundary). No external agent. No DAO. |
| CABR readiness | NOT READY. `build_contract.readiness.*` MUST be false; bundle refuses promotion (#775 step 3a/3b). |
| Mutation permissions | `safe_mutation_surface` declares the allowed source-mutation scope. Bundle enforces string-only elements + authority-keyword denylist (#775 FIX1) + ASCII-only + control-character refusal (FIX2/FIX2b) + fullwidth-Unicode evasion refusal (FIX2). |
| Runtime executor permissions | `execution_routing.executor = "hermes"`, `auditor = "ai_overseer"`, `orchestrator = "openclaw"`, `declarative_only = True`, `external_agent_allowed = False`, `can_self_authorize = False`, `wre_coordinator = True` (validator-enforced). No live launch (`no_live_launch` is a required gate per #771). |
| Human / sovereign valve | 012 sovereign valve REQUIRED for any non-dry-run action (`policy_required_sovereign_valve_for_non_dry_run` required gate). Phase-1: all action stays dry-run-default at the manifest layer. |
| Payout / DAO gates | NONE. CABR / payout / DAO surfaces are forbidden in the bundle (#775 row 24, repaired by FIX1). |

#### 2.2 `external_proto` (DEFINED; not reachable in Phase-1)

| Dimension | Intent |
|-----------|--------|
| Source location | External repo owned by the spin-out team (WSP 103: "FoundUps are NOT subdirectories. They are autonomous entities that CONNECT to pAVS." `WSP_103:32`). Source is no longer in the monorepo. |
| Test contract | Defined by the external repo; pAVS no longer validates exact-match against a monorepo path. A separate federation-bound validator will be required (out of scope). |
| Evidence store | Federation-bound provenance envelope (TBD). pAVS holds a pointer (signed sha256), not the source. |
| Ownership / governance | Spin-out team; 012 retains routing authority over the pAVS federation registry, not the source repo. |
| CABR readiness | NOT READY (still pre-OPO). |
| Mutation permissions | External repo's own rules; pAVS validates only the federation contract, not the source. |
| Runtime executor permissions | Hermes federation client only; no monorepo executor reach into external_proto. |
| Human / sovereign valve | Spin-out team's governance + 012's pAVS-registry sovereign valve. |
| Payout / DAO gates | NONE (still pre-OPO). |

#### 2.3 `mvp_runtime` (DEFINED; not reachable in Phase-1)

| Dimension | Intent |
|-----------|--------|
| Source location | External repo, post-OPO LAUNCH (Tier 2 Thriving). Visibility flipped to PUBLIC per `WSP_103:620`. |
| Test contract | Production CI in the external repo; pAVS observes results, does not run them. |
| Evidence store | OPO-attested attestation envelope (TBD). Signed by the OPO transition event. |
| Ownership / governance | OPO entity (Open Corp). Token holders begin to influence governance. |
| CABR readiness | OPO-attested readiness becomes meaningful. WSP 29 CABR engine outputs are observable. |
| Mutation permissions | OPO entity governance. |
| Runtime executor permissions | OPO-entity-managed runtime; pAVS no longer holds executor authority. |
| Human / sovereign valve | OPO entity governance + token-weighted decisions. 012's role evolves to network arbiter. |
| Payout / DAO gates | OPEN (CABR-gated). Payouts begin per WSP 29. |

#### 2.4 `dao_managed` (DEFINED; not reachable in Phase-1)

| Dimension | Intent |
|-----------|--------|
| Source location | smartDAO-managed repo (Tier 1 Sovereign). Mutations are contract-gated. |
| Test contract | DAO-ratified test contracts. |
| Evidence store | On-chain attestations + off-chain evidence envelopes. |
| Ownership / governance | smartDAO (`WSP_27:651, :663`). Fully autonomous; maximal CABR; all 21M tokens in circulation; can spawn child FoundUps. |
| CABR readiness | MAXIMAL (terminal autonomy state per WSP 27). |
| Mutation permissions | DAO contracts; no individual mutate-authority. |
| Runtime executor permissions | DAO-ratified executors only. |
| Human / sovereign valve | DAO-governance; 012's sovereign valve is replaced by token-weighted governance. |
| Payout / DAO gates | FULLY OPEN. CABR / payout / DAO surfaces are DAO-managed. |

#### 2.5 `archived` (DEFINED; not reachable in Phase-1)

| Dimension | Intent |
|-----------|--------|
| Source location | Frozen repo state, anywhere on the axis. Per `WSP_27:899-902`: "Code remains in repository (never deleted -- future FoundUps may reuse) FoundUp status set to SUNSET in registry." |
| Test contract | None. |
| Evidence store | Frozen final envelope (TBD). |
| Ownership / governance | Read-only; original owners retain attribution. |
| CABR readiness | n/a (terminal). |
| Mutation permissions | NONE. |
| Runtime executor permissions | NONE. |
| Human / sovereign valve | n/a. |
| Payout / DAO gates | Closed; final payouts (if any) settled before archive. |

`archived` is **orthogonal** to maturity: any tier can decay to sunset per
`WSP_27:846-854`.

---

## 3. Maturity coupling table

Which maturity stages each source-authority value can coexist with.
Citations indicate where the maturity stage is defined; `INFERRED` marks
rows whose source-authority binding is proposed by this contract (the WSPs
do not state it directly).

| Maturity (WSP 27 Section 11) | Tier | WSP 103 phase | Compatible `source_authority` | Evidence / Inference |
|-----------------------|------|---------------|-------------------------------|----------------------|
| IDEA -> Validate           | 7 Genesis    | F0_DAE   | `monorepo_poc`                              | `WSP_109:42` -- "0102/RedDog executes this protocol to add it to the codebase monorepo". Intake lands in monorepo. |
| PoC ("blueprint")          | 6 Seeded     | F0_DAE   | `monorepo_poc`                              | `WSP_103:616` -- "Pre-OPO (F0_DAE): PRIVATE". Coupling INFERRED from `WSP_109:42`. |
| TEAM -> Soft-Proto         | 5 Active     | F0_DAE   | `monorepo_poc` OR `external_proto` (transition) | `WSP_103:32` -- "FoundUps are NOT subdirectories. They are autonomous entities that CONNECT to pAVS." Spin-out is supported but not tier-pinned. INFERRED. |
| Proto                      | 4 Growing    | F0_DAE   | `external_proto`                            | `WSP_103:26` -- "External contributors work on FoundUps without the main codebase". INFERRED tier binding. |
| MVP approaching            | 3 Established | F0_DAE  | `external_proto` OR `mvp_runtime` (transition) | `WSP_103:617` implies still Pre-OPO. INFERRED. |
| MVP / LAUNCH as Open Corp  | 2 Thriving   | OPO -> F1_OPO+ | `mvp_runtime`                          | `WSP_103:620` -- "When FoundUp does OPO, owner can flip visibility to PUBLIC." INFERRED that `mvp_runtime` aligns here. |
| smartDAO / Open Corp       | 1 Sovereign  | F1_OPO+  | `dao_managed`                               | `WSP_27:663` -- "Self-sustaining. Fully autonomous. Maximal CABR. All 21M tokens in circulation. Can spawn child FoundUps." INFERRED. |
| Sunset / Dissolution       | n/a (terminal) | n/a    | `archived`                                  | `WSP_27:899-902` (Phase 3 Dissolution); `WSP_27:846-854` (decay from any tier). |

---

## 4. Transition gates (defined; NOT implemented)

This contract DEFINES the evidence each transition requires. It DOES NOT
implement any transition. Phase-1 implementation is `monorepo_poc` only.

### 4.1 `monorepo_poc -> external_proto`

Required evidence:

- Spin-out team identified, named, and accepted by 012 (sovereign valve).
- External repo URL registered via WSP 106 entry surface
  (`WSP_106:71-89`).
- Federation envelope (TBD) signed by both the monorepo (pAVS) and the
  external repo.
- Final monorepo `ContextBundle` recorded as the predecessor envelope.
- No CABR readiness required; this is a pre-OPO transition.

Required WSP gate: WSP 103 federation contract (TBD verification) + WSP
109 intake-archive (`entity_type` updates to `external_foundup`,
`WSP_109:520-526`).

### 4.2 `external_proto -> mvp_runtime`

Required evidence:

- OPO transition event executed (`WSP_103:616-620`).
- OPO visibility flip from PRIVATE to PUBLIC, attested.
- Token contracts deployed and verified.
- Independent CABR audit per WSP 29 (V1 / V2 / V3 gates).

Required WSP gate: WSP 103 OPO transition + WSP 29 CABR readiness +
WSP 100 escalation to F1_OPO+.

### 4.3 `mvp_runtime -> dao_managed`

Required evidence:

- Tier 1 Sovereign attainment per `WSP_27:651` ("When a FoundUp reaches
  Tier 1 (Sovereign), it becomes a smartDAO").
- All 21M tokens in circulation (`WSP_27:663`).
- DAO contract suite deployed, audited, and ratified.
- Maximal CABR sustained.

Required WSP gate: WSP 100 SmartDAO escalation + WSP 29 CABR maximal
+ WSP 27 Tier 1 attainment proof.

### 4.4 Any stage -> `archived`

Required evidence:

- Sunset decision (012 sovereign valve in pre-OPO; DAO vote post-OPO).
- Final settlement of payouts (if any).
- Frozen evidence envelope.

Required WSP gate: WSP 27 Section 13 Sunset Protocol (`WSP_27:846-854`,
`WSP_27:899-902`).

Phase-1 IMPLEMENTS NONE OF THESE. The enum function `request_promotion`
ALWAYS raises `NotImplementedError`.

---

## 5. The Hard Rule (verbatim, load-bearing)

> **A context bundle / manifest must be lifecycle-aware but CANNOT promote
> its lifecycle stage by declaration; promotion requires evidence + WSP
> gate + CABR / DAO proof. A declared stage from any manifest / external
> input is NEVER trusted.**

### Enforcement (Phase-1)

1. **`SOURCE_AUTHORITY` is a BUILDER constant.** Set in
   `modules/foundups/agent/src/context_bundle_builder.py:132`. NOT read from
   the manifest. NOT read from `build_contract`. NOT read from
   `execution_routing`. If a manifest happens to carry a `source_authority`
   or `lifecycle_stage` key, the builder IGNORES it entirely
   (`context_bundle_builder.py:119-131`).
2. **`SourceAuthority.resolve_source_authority(declared)` ALWAYS returns
   `MONOREPO_POC`** and reports any non-None declared value as the second
   tuple element (observable, never silently swallowed). The function
   NEVER raises and NEVER trusts the declared input. See the enum module
   (Section 6).
3. **`SourceAuthority.request_promotion(target)` ALWAYS raises
   `NotImplementedError`** in Phase-1. Promotion is not a function call;
   it is a multi-WSP, multi-evidence event.
4. **The laundering-fix precedent (`96314ab6c`) is the reason this is a
   hard rule, not a guideline.** That commit closed `build_contract` list
   and scalar fields that were declaration-trusted by the prior builder,
   letting `safe_mutation_surface = {"payout_ready": true, "dao_approved":
   true}` and `readiness.build_ready = {"is_authorized": true}` launder
   authority into `bundle.to_dict()`. Source-authority declaration trust
   would be the same exploit class at a higher abstraction. The hard rule
   prevents this exploit class from re-emerging at the lifecycle layer.

---

## 6. Code-pin: `modules/foundups/agent/src/source_authority.py`

A minimal typed enum module pins the contract in code. The enum is
**pure / read-only**: no subprocess, no Popen, no os.system, no eval,
no exec, no importlib dynamic loading, no network, no file writes, no
runtime / executor / consumer imports, no CABR / payout / DAO.

```python
class SourceAuthority(str, enum.Enum):
    MONOREPO_POC   = "monorepo_poc"
    EXTERNAL_PROTO = "external_proto"
    MVP_RUNTIME    = "mvp_runtime"
    DAO_MANAGED    = "dao_managed"
    ARCHIVED       = "archived"

ACTIVE_STAGES = frozenset({SourceAuthority.MONOREPO_POC})


def resolve_source_authority(
    declared: str | SourceAuthority | None = None,
) -> tuple[SourceAuthority, str | None]:
    """ALWAYS returns (MONOREPO_POC, ignored_declaration)."""


def request_promotion(target: str | SourceAuthority) -> NoReturn:
    """ALWAYS raises NotImplementedError in Phase-1."""
```

### Builder value-parity (drift guard)

The enum module's `SourceAuthority.MONOREPO_POC.value` MUST equal
`context_bundle_builder.SOURCE_AUTHORITY`. A test enforces this
(value-parity verification only -- the enum is NOT wired into the builder
in Phase-1). If the builder constant ever drifts, the parity test fails.

Recommended follow-up (do not execute here):
`SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2` to re-point the
builder constant at the enum (single source of truth).

---

## 7. Relationship to the consumer-wiring precondition

Consumer wiring (WRE / Hermes / OpenClaw / FoundUpJob consumer) remains
**BLOCKED** until BOTH:

(a) this contract exists (this slice satisfies (a)), AND

(b) legacy `payload.module_path` trust is removed or
    validator/bundle-guarded in Hermes legacy executor (#774 carry-forward;
    NOT satisfied by this slice).

Therefore: this slice unblocks ONE of two preconditions. Consumer wiring
is still blocked. A future slice must satisfy (b) before any consumer
slice may proceed.

---

## 8. Non-goals (explicit; do not implement)

This slice does NOT:

- Implement any external-state handling
  (`external_proto` / `mvp_runtime` / `dao_managed` / `archived` remain
  unreachable).
- Wire any consumer (no Hermes / OpenClaw / WRE / FoundUpJob touch).
- Modify the #775 builder (`context_bundle_builder.py` is untouched in
  this slice; the constant remains the builder's single source).
- Mutate WSP files
  (`WSP_framework/**`, `WSP_knowledge/**`, `WSP_MASTER_INDEX.md`
  untouched). Follow-up
  `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_WSP_FORMALIZATION_PHASE1` may
  promote this to a WSP later.
- Add any CABR / payout / DAO / token logic.
- Edit the #771/#773 validator.
- Touch manifests, registry, runtime executors, `main.py`, `*_dae.py`,
  `vendor/`, or `.env`.

---

## 9. Proposed follow-ups (recorded; not executed here)

- `WSP27_LIFECYCLE_TERMINOLOGY_ALIGNMENT_PHASE1` -- harmonize WSP 27 /
  WSP 103 vocabularies (smartDAO vs OPO LAUNCH) and add an explicit
  OBAI/RedDog actor-vs-stage callout in WSP 27 Section 11.
- `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_WSP_FORMALIZATION_PHASE1` --
  promote this contract to a WSP (WSP 110 candidate slot) when at least
  one additional module (FAM registry, OpenClaw launcher, or WRE
  planner) consumes `source_authority`.
- `SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2` -- replace the
  builder constant with an import of `SourceAuthority.MONOREPO_POC.value`
  once the enum lands.
- `HOLOINDEX_LIFECYCLE_TUNING_PHASE1` -- investigate why WSP_27 /
  WSP_103 / WSP_109 did not surface for the lifecycle queries despite
  being load-bearing here.

---

## 10. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|-------------------------------|--------|----------|
| 1 | HOLOINDEX_PRIOR_ART_SEARCHED | YES | Section 0 records 3 queries with verbatim top hits. No prior `SourceAuthority` enum found. |
| 2 | HOLOINDEX_RETRIEVAL_ASSESSED | YES | Section 0 records noise / ordering / missing artifacts / staleness / duplication explicitly. Proposed follow-up `HOLOINDEX_LIFECYCLE_TUNING_PHASE1` documented in Section 9. |
| 3 | LIFECYCLE_AXIS_RECONCILED_NOT_DUPLICATED | YES | Section 1 cites WSP 27 Section 11.0 verbatim and explicitly states "The source-authority axis is a finer-grained refinement of WSP 103's binary, with the OPO gate as the inflection point." No competing maturity lifecycle invented. |
| 4 | OPO_SMARTDAO_RELATION_DERIVED_NOT_ASSUMED | YES | Section 1 derives OPO LAUNCH = Tier 2 (`WSP_27:640, :663`) and smartDAO = Tier 1 (`WSP_27:651, :663`), conclusion SEQUENTIAL, with tier-number evidence. |
| 5 | MATURITY_COUPLING_TABLE_PRESENT | YES | Section 3 lists 8 maturity rows x source_authority bindings with WSP citations and INFERRED markers where the WSPs do not state the binding directly. |
| 6 | TERMINOLOGY_DRIFT_RECORDED_NOT_FIXED | YES | Section 1 records two drift findings (smartDAO vs OPO LAUNCH; OBAI/RedDog actor vs stage) with file:line evidence. Follow-up `WSP27_LIFECYCLE_TERMINOLOGY_ALIGNMENT_PHASE1` proposed; no WSP text edited here. |
| 7 | WSP_PLACEMENT_AUDITED_NOT_MUTATED | YES | Section 0 gap analysis + recommendation (c) docs/architecture + promotion trigger documented. No file under `WSP_framework/` or `WSP_knowledge/` is modified by this slice. |
| 8 | FIVE_STAGES_DEFINED | YES | Section 2 defines exactly 5 stages: `monorepo_poc`, `external_proto`, `mvp_runtime`, `dao_managed`, `archived`. The enum (Section 6) carries exactly 5 members. |
| 9 | ENUM_VALUES_EXACT | YES | Enum member string values are EXACTLY `"monorepo_poc"`, `"external_proto"`, `"mvp_runtime"`, `"dao_managed"`, `"archived"`. Test `test_enum_values_exact` asserts each. |
| 10 | PER_STAGE_MATRIX_DEFINED | YES | Section 2.1 - 2.5 define per-stage matrix dimensions: source location, test contract, evidence store, ownership/governance, CABR readiness, mutation permissions, runtime executor permissions, human/sovereign valve, payout/DAO gates. Concrete for `monorepo_poc`; intent for the four future stages. |
| 11 | TRANSITION_GATES_DEFINED_NOT_IMPLEMENTED | YES | Section 4 defines 4 transition gates (`monorepo_poc -> external_proto`, `external_proto -> mvp_runtime`, `mvp_runtime -> dao_managed`, any -> `archived`) with required evidence + required WSP gate. Section 4 closes with "Phase-1 IMPLEMENTS NONE OF THESE". The enum function `request_promotion` ALWAYS raises `NotImplementedError`. |
| 12 | CANNOT_PROMOTE_BY_DECLARATION_ENFORCED | YES | Section 5 records the verbatim hard rule. Enforcement (Phase-1): (a) builder constant `SOURCE_AUTHORITY` at `context_bundle_builder.py:132` is NOT manifest-sourced, (b) `resolve_source_authority(declared)` ALWAYS returns `MONOREPO_POC`, (c) `request_promotion(target)` ALWAYS raises, (d) laundering-fix precedent `96314ab6c` cited. |
| 13 | DECLARED_MISMATCH_OBSERVABLE | YES | `resolve_source_authority` returns `tuple[SourceAuthority, str | None]`. The second element carries the ignored declaration verbatim (`None` if the caller passed None, otherwise the stringified declared value). Tests parametrize over `dao_managed` / `mvp_runtime` / `external_proto` / `archived` / garbage and assert the observable ignored-value report. |
| 14 | GARBAGE_INPUT_FUZZED | YES | Tests parametrize garbage inputs (`"DAO_MANAGED"`, `"MonoRepo_PoC"`, `42`, `""`, `None`, `{}`, `[]`, control chars). `resolve_source_authority` returns `(MONOREPO_POC, stringified_declared_or_None)` for ALL; never raises. |
| 15 | ONLY_MONOREPO_POC_ACTIVE | YES | `ACTIVE_STAGES = frozenset({SourceAuthority.MONOREPO_POC})`. Test `test_active_stages_is_only_monorepo_poc`. |
| 16 | ENUM_BUILDER_VALUE_PARITY | YES | Test `test_enum_monorepo_poc_value_matches_builder_constant` asserts `SourceAuthority.MONOREPO_POC.value == context_bundle_builder.SOURCE_AUTHORITY`. The test-only import is the ONLY contact between this slice and the builder; the builder is otherwise untouched. |
| 17 | NO_EXTERNAL_STATE_IMPLEMENTED | YES | The four non-active stages are DEFINED in this doc and PRESENT in the enum, but no function implements transitions, dispatches, or runtime handling. `request_promotion` ALWAYS raises. |
| 18 | NO_CONSUMER_WIRING | YES | No `executor` / `consumer` / `dispatcher` / `hermes` / `openclaw` / `wre` / `broker` / `job_queue` parameter in either enum function. AST scan in tests rejects runtime executor imports. |
| 19 | NO_BUILDER_CHANGE | YES | `git diff` confirms `context_bundle_builder.py` is untouched in this slice. The test-only import of the builder constant is in the test file, not the enum module. |
| 20 | NO_WSP_FILE_MUTATION | YES | `git diff` confirms no file under `WSP_framework/` or `WSP_knowledge/` is modified. `WSP_MASTER_INDEX.md` is untouched. |
| 21 | NO_RUNTIME_OR_EXECUTOR_IMPORT | YES | AST scan in `test_source_authority.py` rejects any import matching `hermes` / `openclaw` / `ai_overseer` / `job_consumer` / `foundup_job_consumer` / `build_plan_executor` / `wre_core` / `wre_master_orchestrator` / `build_plan_swarm`. Source-only stdlib imports: `enum`, `typing`. |
| 22 | NO_CABR_PAYOUT_DAO | YES | Enum module source contains no `cabr` / `payout` / `dao_ratify` / `treasury` / `f_i` / `ups` identifier. AST scan checks. |
| 23 | CONSUMER_WIRING_REMAINS_BLOCKED | YES | Section 7 records that consumer wiring is BLOCKED until BOTH (a) this contract (satisfied) AND (b) legacy `payload.module_path` trust removed / guarded (#774 carry-forward, NOT satisfied). |
| 24 | ENUM_PURE_READ_ONLY | YES | AST scan in tests rejects `subprocess`, `socket`, `urllib`, `importlib`, `multiprocessing`, `pickle`, `marshal`, `os`, `sys`, `shutil` imports and any banned-attribute calls (`run`, `Popen`, `system`, `write_text`, `urlopen`, etc.). |
| 25 | INTERFACE_MD_UPDATED | YES | `modules/foundups/agent/INTERFACE.md` adds a new "Source-Authority Contract" public-API section describing `SourceAuthority`, `ACTIVE_STAGES`, `resolve_source_authority`, `request_promotion`, and the hard rule. WSP_22 doc update order honored (INTERFACE -> ROADMAP -> ModLog -> TestModLog). |
| 26 | NO_SKIP_XFAIL | YES | Test suite reports 0 skipped, 0 xfailed (see TestModLog entry). |
| 27 | CITES_PR_775_AND_LAUNDERING_FIX | YES | Header cites #775 (`96a860cc3`); Section 5 cites the laundering-fix commit `96314ab6c` and quotes its core mechanism. Both are load-bearing precedent for the hard rule. |
| 28 | ASCII_CLEAN | YES | Contract doc, enum module, test file, INTERFACE.md additions, ROADMAP additions, ModLog entry, and TestModLog entry are 0 non-ASCII bytes. Pre-existing non-ASCII bytes elsewhere in `ModLog.md` / `INTERFACE.md` / `ROADMAP.md` are unchanged and out of slice scope. |

**WSP_97 VERDICT**: PASS (28/28).

---

**Worker-Lane**: W6
**Slice**: `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1`
**WSP Lock**: WSP_00 -> WSP_11 -> WSP_27 -> WSP_30 -> WSP_50 -> WSP_64 -> WSP_84
  -> WSP_97 -> WSP_103 -> WSP_109 -> WSP_22
