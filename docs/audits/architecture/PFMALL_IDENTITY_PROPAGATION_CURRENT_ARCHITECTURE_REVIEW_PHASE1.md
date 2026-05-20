# PFMALL_IDENTITY_PROPAGATION_CURRENT_ARCHITECTURE_REVIEW_PHASE1

**Worker**: W6  
**Date**: 2026-05-21  
**Status**: COMPLETE (READ_ONLY_REVIEW)  
**Mode**: Docs-only audit  

## 1. current_main_commit

```
bb06ebf3a docs(architecture): add FoundUp build system registry integration audit template (#634)
```

Fetched: 2026-05-21

## 2. stale_pr_419_summary

**PR #419**: `docs/pfmall-identity-propagation`  
**Title**: `docs(pfmall): propagate p.fMALL AI interaction space identity`  
**State**: OPEN (stale - created 2026-04-21, last updated 2026-04-21)  
**Branch**: `docs/pfmall-identity-propagation`  

### Intent
Propagate the p.fMALL identity statement across all architecture docs and key code entry points:
- p.fMALL is an "AI interaction space" — a new way of interacting with AI and the world
- Video is the default surface, but the paradigm extends to any content type
- Same interaction model (pinch, zoom, navigate) everywhere, with AI mediating all engagement

### Files touched (17)
- **12 architecture docs**: Identity block added to Section 1 Purpose
- **4 code entry points**: Identity docstrings added
- **1 ModLog**: Propagation entry

### Change type
DOCS_ONLY — no runtime changes, no behavioral changes.

## 3. current_pFMALL_identity_architecture

### Shell Contract (`PFMALL_SHELL_CONTRACT.md`)
Current definition (line 12):
> p.fMALL is a PWA shell/gateway that hosts, discovers, and routes into multiple FoundUps. The shell is a **thin platform layer** — it provides discovery, navigation, auth, and shared services. It does NOT own FoundUp business logic, data, or UI.

### Shell Core (`shell_core.py`)
Current docstring (lines 3-6):
> p.fMALL Shell Core Scaffold
> Minimal shell runtime providing manifest discovery, catalog assembly, route resolution, and manifest+overlay merge. Non-UI scaffold only.

### Identity Contracts
| Contract | Purpose | Identity mention |
|----------|---------|------------------|
| PFMALL_SHELL_CONTRACT.md | Shell responsibilities | "thin platform layer" |
| PFMALL_ROUTING_DISCOVERY_MODEL.md | Route resolution | None |
| PFMALL_DATA_ISOLATION_MODEL.md | Tenant isolation | None |
| PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md | Catalog schema | None |

**Gap**: No doc defines what p.fMALL IS from a user/paradigm perspective. All describe plumbing.

## 4. current_catalog_boundary

### pFMALL catalogs (runtime display/routing)
| Catalog | Location | Purpose |
|---------|----------|---------|
| `catalog.json` | `public/member/` | Launch catalog for shell boot |
| `mall-video-catalog.json` | `public/member/` | Video mall content lanes |

### Validation gate
`test_catalog_foundup_truth_gate.py` validates catalog entries against:
- `VALID_CATEGORIES` (11 values in shell_core.py)
- `VALID_STAGES` (11 values including simulator + operational)
- `VALID_READINESS` (3 values: ready, conditional, discoverable_only)
- `VALID_TIERS` (6 values: F0-F5)

## 5. registry_boundary_interaction

### Canonical registry (`foundup_registry.json`)
Purpose: Inventory/build-contract for Hermes/OpenClaw
- "What exists, what class is it, what stage is it in, what can builders touch?"
- 14 entities with typed classification
- NOT a runtime catalog

### Boundary statement (per population audit)
> The canonical FoundUp registry does not replace `catalog.json`, `mall-video-catalog.json`, or pFMALL runtime catalogs. It may later validate or generate projections for them, but Phase 1 is inventory/build-contract only.

### pfmall entry in registry
```json
{
  "foundup_id": "pfmall",
  "entity_type": "platform_layer",
  "manifest_status": "not_applicable",
  "token_status": "NOT_APPLICABLE",
  "hermes_openclaw_build_status": "none"
}
```

**Interpretation**: pFMALL is correctly classified as container, not a FoundUp.

## 6. conflict_risk_assessment

### Does PR #419 conflict with canonical registry boundaries?
**NO CONFLICT.**

| Concern | Assessment |
|---------|------------|
| Identity vs technical | PR #419 describes UX paradigm ("AI interaction space"). Shell contract describes technical implementation ("PWA shell/gateway"). These are complementary layers. |
| Catalog ownership | PR #419 does not change catalog ownership. pFMALL catalogs remain separate from canonical registry. |
| Registry mutation | PR #419 does not touch registry. DOCS_ONLY. |
| Truth gate | PR #419 does not change validation logic. |

### Does PR #419 conflict with current shell_core.py?
**NO CONFLICT.**

PR #419 adds docstrings to `shell_core.py` and `__init__.py`. It does not modify:
- `VALID_CATEGORIES`
- `VALID_STAGES`
- `VALID_TIERS`
- Any runtime logic

### Staleness risk
- PR created 30 days ago (2026-04-21)
- No subsequent updates
- main has advanced significantly (PRs #420-#634 merged)
- **Likely merge conflicts** in `ModLog.md` (many entries since)

## 7. keep_rebase_or_replace_verdict

**VERDICT: REBASE WITH ADDENDUM**

| Option | Assessment |
|--------|------------|
| **Close (abandon)** | Not recommended. The identity gap is real — no doc defines what p.fMALL IS. |
| **Rebase as-is** | Acceptable but incomplete. Should add registry boundary reference. |
| **Replace with fresh PR** | Unnecessary overhead. Content is still valid. |
| **Rebase + addendum** | **Recommended.** Rebase #419, resolve conflicts, add one sentence to PFMALL_SHELL_CONTRACT.md linking to registry boundary. |

### Required addendum
Add to PFMALL_SHELL_CONTRACT.md Section 1 Purpose:
> Note: The canonical FoundUp registry (`foundup_registry.json`) is separate from pFMALL runtime catalogs. See `docs/audits/architecture/FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1.md` for boundary definition.

## 8. recommended_current_main_design_path

### Identity propagation remains valid
The identity statement ("p.fMALL is an AI interaction space") is orthogonal to:
- Canonical registry (build contract)
- pFMALL catalogs (runtime display)
- Truth gate tests (validation)

### Smallest safe next slice
`PFMALL-IDENTITY-PROPAGATION-REBASE-PHASE1`:
1. Checkout #419 branch
2. Rebase onto current main
3. Resolve ModLog.md conflicts
4. Add registry boundary reference to PFMALL_SHELL_CONTRACT.md
5. Re-run tests
6. PR review

### What identity propagation is still needed
- All 12 docs need the identity block (unchanged from #419)
- All 4 code entry points need docstrings (unchanged from #419)
- PFMALL_SHELL_CONTRACT.md needs registry boundary reference (new)

## 9. HoloIndex_assessment

### Queries executed (4)
1. `pFMALL identity propagation catalog boundary canonical registry truth gate` → 18 hits
2. `PFMALL_SHELL_CONTRACT identity tenant auth member catalog` → 20 hits
3. `pFMALL Catalog FoundUp Truth Gate validation identity` → 20 hits
4. `PR 419 pfmall identity propagation current architecture` → 20 hits

### Key files surfaced
| File | Relevance |
|------|-----------|
| `test_catalog_foundup_truth_gate.py` | Current validation logic |
| `PFMALL_SHELL_CONTRACT.md` | Shell responsibilities |
| `PFMALL_FOUNDUP_IDENTITY_REPORT.md` | Prior identity audit |
| `WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md` | Namespace isolation |

### HoloIndex assessment
HoloIndex correctly surfaced the relevant architecture files. No false positives requiring correction.

## 10. WSP_97_truth_boundary

### Labels applied
- `DOCS_ONLY` — this review creates only audit documentation
- `READ_ONLY_REVIEW` — no code or catalog changes
- `NO_PFMALL_RUNTIME_CHANGE` — shell_core.py untouched
- `NO_CATALOG_CHANGE` — catalog.json/mall-video-catalog.json untouched
- `NO_AUTH_CHANGE` — auth gateway untouched
- `NO_REGISTRY_MUTATION` — foundup_registry.json untouched
- `NO_STALE_PR_RESURRECTION` — PR #419 not rebased in this slice
- `NO_CABR_READY` — not a CABR-scored deliverable
- `NO_PAYOUT_READY` — not a payout trigger
- `NO_DAO_ACTIVATION` — no governance action

### Truth boundary respected
This audit:
- Did NOT modify any pFMALL runtime code
- Did NOT modify any catalogs
- Did NOT rebase PR #419
- Did NOT create new manifests or tokens
- ONLY created documentation

## 11. WSP_15_next_slice

### Recommended next slice
**Name**: `PFMALL_IDENTITY_PROPAGATION_REBASE_PHASE1`

**Prerequisites**:
- This audit merged
- W10 PR workflow available

**Scope**:
1. Checkout PR #419 branch
2. Rebase onto current main (bb06ebf3a or later)
3. Resolve ModLog.md conflicts
4. Add registry boundary sentence to PFMALL_SHELL_CONTRACT.md
5. Verify tests pass
6. Push and request review

**Constraints**:
- DOCS_ONLY (no runtime changes)
- Must preserve original #419 identity statement
- Must add registry boundary reference

**Estimated effort**: 30 minutes (conflict resolution + addendum)

---

## Evidence Packet

```yaml
branch: main (read-only review, no new branch)
base_commit: bb06ebf3a
files_created:
  - docs/audits/architecture/PFMALL_IDENTITY_PROPAGATION_CURRENT_ARCHITECTURE_REVIEW_PHASE1.md

holoindex_assessment: PASS (4 queries, relevant files surfaced)

wsp_97_verdict: PASS
  - DOCS_ONLY
  - READ_ONLY_REVIEW
  - NO_PFMALL_RUNTIME_CHANGE
  - NO_CATALOG_CHANGE
  - NO_AUTH_CHANGE
  - NO_REGISTRY_MUTATION
  - NO_STALE_PR_RESURRECTION

wsp_15_recommendation:
  next_slice: PFMALL_IDENTITY_PROPAGATION_REBASE_PHASE1
  action: rebase PR #419 + add registry boundary reference

w10_readiness: READY
  - Single file created
  - No dependencies
  - Commit locally, W10 handles PR
```
