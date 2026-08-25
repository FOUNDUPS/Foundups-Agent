# FoundUps Domain - ModLog

## Chronological Change Log

### 2026-08-26 - Canonical FoundUps/RedDog Lifecycle Alignment

- Repaired the master architecture's false "no PWA" and fixed-scale claims.
- Distinguished the implemented p.fMALL PWA shell from the target Progressive
  Web Agent, stake gate, stakeholder interior, and authenticated RedDog
  transport.
- Defined RedDog/0102, OpenClaw, WRE, Hermes, phone, and p.fMALL boundaries
  without making the browser or one OpenClaw instance authoritative.
- Documentation-only; no catalog, route, wallet, model, worker, or runtime
  state changed. WSP 15/22/50/62/73/97/98.


### 2026-05-21 - Public Portfolio Status Schema (W9: FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1)

**By:** 0102 (W9) — **Slice:** `FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1`
**WSP References:** WSP 97 (Truth), WSP 104 (Route Namespace), WSP 102 (Web Design), WSP 15 (Doc Standards)

**Modified**:
- `modules/foundups/foundup_registry.schema.json` — Added portfolio display field definitions
- `modules/foundups/foundup_registry.example.json` — Updated all 6 entities with portfolio fields
- `modules/foundups/foundup_registry.json` — Updated all 14 entities with portfolio fields

**Created**:
- `modules/foundups/tests/test_foundup_registry_schema.py` — 15 portfolio schema tests
- `docs/audits/architecture/FOUNDUPS_PUBLIC_PORTFOLIO_STATUS_SCHEMA_PHASE1.md` — Schema audit

**New Schema Fields (12)**:
- `portfolio_status`: not_portfolio | portfolio_candidate | portfolio_ready | portfolio_featured
- `poc_landing_status`: none | placeholder | functional | polished
- `website_url`, `poc_url`, `app_url`, `github_url`, `docs_url`, `screenshot_url`: URL fields (nullable)
- `public_summary`: 280 char max for portfolio display
- `portfolio_priority`: 1-100 display order (nullable)
- `portfolio_ready`: boolean flag for display eligibility
- `portfolio_evidence_docs`: evidence doc paths array

**Portfolio Candidates (2)**:
- gotjunk_001: portfolio_candidate, poc_landing_status=functional
- kosei: portfolio_candidate, poc_landing_status=functional

**Tests**: 15/15 passed

**No runtime changes. No route creation. No pFMALL catalog mutation. Schema only.**

---

### 2026-05-21 - FoundUp Registry Read-Only Loader (W6: FOUNDUP_REGISTRY_READONLY_LOADER_PHASE1)

**By:** 0102 (W6) — **Slice:** `FOUNDUP_REGISTRY_READONLY_LOADER_PHASE1`
**WSP References:** WSP 97 (Truth), WSP 96 (MCP Governance), WSP 87 (HoloIndex), WSP 15 (Doc Standards)

**Created**:
- `modules/foundups/src/foundup_registry_loader.py` — Read-only loader for MCP scope validation
- `modules/foundups/tests/test_foundup_registry_loader.py` — 28 tests covering all loader functionality
- `docs/audits/architecture/FOUNDUP_REGISTRY_READONLY_LOADER_PHASE1.md` — Implementation audit

**API exposed**:
- `load_registry(path?)` — Load and return registry dict
- `list_foundup_ids(path?)` — Return all known IDs as tuple
- `is_valid_foundup_id(id, path?)` — Validate ID exists and matches pattern
- `get_module_path(id, path?)` — Get module path for ID
- `get_entity_type(id, path?)` — Get entity type for ID
- `FoundUpRegistryLoader` — Class-based loader for custom paths

**Behavior**:
- Read-only file access (WSP 97: NO_REGISTRY_MUTATION)
- Fail-closed on malformed/missing registry
- Pattern validation: `^[a-z0-9_]+$`
- Unknown IDs return False/None

**Tests**: 28/28 passed + 30 schema tests = 58 total

**No MCP route changes. No HoloIndex mutation. No pFMALL catalog changes.**

---

### 2026-05-18 - FoundUp Canonical Registry Population (W6: FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1)

**By:** 0102 (W6 coordinator) — **Slice:** `FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1`
**WSP References:** WSP 97 (Truth), WSP 87 (HoloIndex), WSP 15 (Doc Standards), WSP 50 (Pre-Action)

**Created**:
- `modules/foundups/foundup_registry.json` — Production registry with 14 evidence-backed entities
- `docs/audits/architecture/FOUNDUP_CANONICAL_REGISTRY_POPULATION_PHASE1.md` — Population audit

**Modified**:
- `modules/foundups/tests/test_foundup_registry_schema.py` — Added 8 production validation tests (30 total)

**Entities populated (14)**:
- **Manifest-bearing FoundUps (6)**: gotjunk_001, kosei, voteballots, trade, magadoom_001, antifafm_001
- **Platform/Infra (4)**: pfmall, agent_market, simulator, social_twin
- **External FoundUps (2)**: autopost, science_swarm_hub
- **Access Service (1)**: move2japan
- **Skeleton Candidate (1)**: pqn_portal

**Token status distribution**:
- EXISTS: 6 (JUNK, KOSEI, VOTE, TRADE, DOOM, ANTI)
- TOKEN_DEFERRED: 4
- NOT_APPLICABLE: 4

**Tests**: 30/30 passed (8 new production validation tests)

**No manifests created. No tokens invented. No runtime changes.**

---

### 2026-05-18 - FoundUp Canonical Registry Schema (W6: FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1)

**By:** 0102 (W6 coordinator) — **Slice:** `FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1`
**WSP References:** WSP 97 (Truth), WSP 87 (HoloIndex), WSP 15 (Doc Standards), WSP 50 (Pre-Action)

**Created**:
- `modules/foundups/foundup_registry.schema.json` — JSON Schema v1.0.0 for typed registry
- `modules/foundups/foundup_registry.example.json` — Example registry with 6 evidence-backed entries
- `modules/foundups/tests/test_foundup_registry_schema.py` — 22 validation tests
- `docs/audits/architecture/FOUNDUP_CANONICAL_REGISTRY_SCHEMA_PHASE1.md` — Implementation audit

**Schema defines**:
- 7 entity types: foundup, platform_layer, infra_service, tool_simulator, external_foundup, skeleton_candidate, access_service
- 10 implementation statuses: SPECIFIED, IMPLEMENTED, TESTED, RUNTIME_ENFORCED, DOC_ONLY, etc.
- 4 token statuses: EXISTS, TOKEN_DEFERRED, NOT_APPLICABLE, UNKNOWN
- 4 public surface statuses: hidden, discoverable, listed, promoted
- Conditional validation: foundup requires tier/stage, external requires repo, EXISTS requires symbol

**Example entries**:
- gotjunk_001 (foundup, JUNK token)
- voteballots (skeleton_candidate, VOTE token)
- pfmall (platform_layer, NOT_APPLICABLE)
- move2japan (access_service, TOKEN_DEFERRED)
- autopost (external_foundup, TOKEN_DEFERRED)
- pqn_portal (skeleton_candidate, TOKEN_DEFERRED)

**Tests**: 22/22 passed

**Hermes/OpenClaw build contract**: Registry provides entity discovery, build eligibility, manifest binding, stage gating, and token validation for job creation and capability token issuance.

**No manifests created. No tokens assigned. No runtime changes.**

---

### 2026-04-21 - RedDog Catalog Classification Gate Spec (W2: REDDOG-CATALOG-CLASSIFICATION-GATE)

**By:** 0102 (W2) — **Slice:** `REDDOG-CATALOG-CLASSIFICATION-GATE`
**WSP References:** WSP 97 (Truth), WSP 104 (Namespace), WSP 29 (CABR Engine)

**Added**:
- `docs/0102_session_briefings/REDDOG_CATALOG_CLASSIFICATION_GATE_PHASE1.md` — Architecture + schema spec

**Defines**:
- `RedDogCatalogClassification` schema (candidate_type, confidence, wsp97_state, evidence, conflicts, recommended_action)
- 6 decision rules (R1–R6) for classifying raw discoveries as FoundUp candidates
- Classification pipeline: signal intake → catalog lookup → marker detection → classification → enum validation → truth state → downstream routing
- FAM event types for classification lifecycle (created, proposed, accepted, rejected, escalated)
- Catalog validator boundary: RedDog classifies/proposes, validator accepts/rejects, only validator writes to catalog
- Integration with PR #421 truth gate (classifications must pass all 25 truth gate tests)
- 3-phase implementation roadmap (REDDOG-CATALOG1/2/3)

**RedDog role boundary**: classify / question / propose — NOT declare / register / promote. Advisory until FAM or catalog validator accepts.

**No implementation code written. No catalog or manifest modifications.**

---

### 2026-04-23 - Catalog FoundUp Truth Gate (W2: PFMALL-CATALOG-FOUNDUP-TRUTH-GATE)

**By:** 0102 (W2) — **Slice:** `PFMALL-CATALOG-FOUNDUP-TRUTH-GATE`
**WSP References:** WSP 97 (Truth), WSP 104 (Namespace)

**Added**:
- `modules/foundups/pfmall/tests/test_catalog_foundup_truth_gate.py` — 25 tests validating every catalog entry as a FoundUp

**Updated**:
- `modules/foundups/pfmall/shell_core.py`
  - Added `VALID_CATEGORIES` frozenset (11 categories: 5 original + 6 catalog-emergent)
  - Added `active`, `staging` to `VALID_STAGES` (used by catalog, were missing)

**Validation gate enforces**:
- Every catalog entry has foundup_id, category, lifecycle_stage, launch_readiness, tier
- All enum values match canonical frozensets in shell_core.py
- Bound tenants (routing_prefix + data_namespace) must have matching manifests
- Discoverable-only FoundUps pass without manifests
- No partial binding (route without namespace or vice versa)
- Regression guards: no SHA256 IDs, no angel/ultimate tiers, minimum 13 entries

**Category enum drift fixed**:
- shell_core.py had no VALID_CATEGORIES — created with all 11 valid categories
- `active` and `staging` lifecycle stages added to VALID_STAGES (catalog uses them, validation rejected them)

**Tests**: 25/25 passed. Existing tests unaffected (82/83 shell_core pass, 1 pre-existing entry_url failure; 23/23 namespace guardrail pass).

---

### 2026-04-21 - PFMALL Launch Catalog Taxonomy Reconciliation (W2: PFMALL-LAUNCH-CATALOG-TAXONOMY-RECON)

**By:** 0102 (W2) — **Slice:** `PFMALL-LAUNCH-CATALOG-TAXONOMY-RECON`
**WSP References:** WSP 97 (Truth), WSP 104 (Namespace), WSP 3 (Domains), WSP 100 (SmartDAO Tiers)

**Updated**:
- `modules/foundups/docs/PFMALL_LAUNCH_CATALOG_TAXONOMY.md` — Reconciled against `mall-video-catalog.json` truth

**Category drift corrected**:
- Spec had 5 categories; catalog has 9. Added: `travel`, `music`, `startup`, `thought-leadership`, `ai-education`, `ai-research`
- `games` and `community` specified but absent from catalog

**Portfolio drift corrected**:
- Spec listed 6 FoundUps; catalog contains 13
- Added Kosei (was missing from spec entirely)
- Corrected antifaFM lifecycle: `incubating` → `proto`
- Identified 3 spec-only entries absent from catalog: Whack-a-Magot, YouTube Engagement, LinkedIn Agent

**Enum drift corrected** (consistent with PFMALL-MANIFEST-SCHEMA-RECON):
- `required_subscription_tier`: `angel, ultimate` → `basic, enterprise` (per `subscription_tiers.py`)
- `foundup_id` format: SHA256 hex → human-readable slug (per actual catalog/manifests)

**Bound vs unbound tenant distinction added**:
- Only `gotjunk_001` and `kosei` are bound tenants (manifest + route + namespace)
- Remaining 11 are discoverable-only video tiles

**WSP 97 truth markers applied**: 12 features assessed. Added Implementation Status table.

**Finding**: Catalog taxonomy doc significantly diverged from actual catalog. Original 5-category, 6-FoundUp spec now reflects actual 9-category, 13-entry catalog with bound/unbound tenant hierarchy. No code changes; doc-only reconciliation.

---

### 2026-04-22 - p.fMALL Identity Propagation (W2: PFMALL-IDENTITY-PROPAGATION)

**By:** 0102 (W2) — **Slice:** `PFMALL-IDENTITY-PROPAGATION`
**WSP References:** WSP 97 (Truth)

**Updated** (12 architecture docs — identity statement added to Section 1 Purpose):
- `PFMALL_SHELL_CONTRACT.md`
- `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md`
- `PFMALL_ROUTING_DISCOVERY_MODEL.md`
- `PFMALL_DATA_ISOLATION_MODEL.md`
- `PFMALL_VIDEO_MALL_RUNTIME_FOUNDATION_2026-04-02.md`
- `PFMALL_MALL_NAVIGATION_CONTRACT.md`
- `PFMALL_STATE_OVERLAY_CONTRACT.md`
- `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md`
- `PFMALL_MEDIA_DELIVERY_CONTRACT.md`
- `PFMALL_FOUNDUP_ENTRY_AND_STAKE_GATE_CONTRACT.md`
- `PFMALL_FULLSCREEN_PLAYER_CONTRACT.md`
- `PFMALL_VIDEO_MALL_CATALOG_SCHEMA.md`

**Updated** (4 code entry points — identity reference added to module docstrings):
- `modules/foundups/pfmall/__init__.py`
- `modules/foundups/pfmall/shell_core.py`
- `public/member/js/shell-bridge-interceptor.js`
- `public/member/member-sw.js`

**Identity statement**: "p.fMALL is an AI interaction space — a new way of interacting with AI and the world. Video is the default surface, but the paradigm extends to any content type: documents, community, FoundUps. The same interaction model (pinch, zoom, navigate) works everywhere, with AI mediating all engagement."

**Finding**: No pfmall doc previously defined what p.fMALL IS. All docs described plumbing (shell, routing, isolation, taxonomy). Identity was absent from the entire doc suite and codebase. Now concatenated across all 12 architecture docs and 4 key code entry points.

---

### 2026-04-21 - PFMALL Routing Discovery Model WSP 97 reconciliation

**By:** 0102 (W3) — **Slice:** `PFMALL-ROUTING-RECON`  
**WSP References:** WSP 97

**Updated**:
- `modules/foundups/docs/PFMALL_ROUTING_DISCOVERY_MODEL.md`
  - Added WSP 97 Implementation Status table (Phase 1 vs Phase 2+ truth)
  - Added PMCTRL1 vs Shell Router boundary clarification
  - Added HoloIndex vs Catalog discovery distinction
  - Added companion document cross-references

**Finding**: Routing doc is architecture specification for Phase 2+. Current Phase 1 implementation is video tile field with PMCTRL1 agent control. No code changes; doc-only reconciliation.

---

### 2026-04-21 - PFMALL Manifest Schema Reconciliation (W2: PFMALL-MANIFEST-SCHEMA-RECON)

**By:** 0102 (W2) - **Slice:** `PFMALL-MANIFEST-SCHEMA-RECON`
**WSP References:** WSP 97 (Truth), WSP 104 (Namespace), WSP 49 (Structure)

**Updated**:
- `modules/foundups/docs/PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` - Reconciled against codebase truth

**Enum drift corrected**:
- `required_subscription_tier`: `angel, ultimate` -> `basic, enterprise` (per `subscription_tiers.py` TIERS dict)
- `foundup_id` format: SHA256 hash spec -> human-readable slug (per actual manifests)

**Missing fields added**:
- `category` (present in gotjunk/kosei manifests, used by catalog export)
- `launch_readiness` (present in manifests, validated by `shell_core.py`)

**WSP 97 truth markers applied**:
- `SPECIFIED_NOT_IMPLEMENTED`: HMAC signing, `min_shell_version`, deterministic `foundup_id` generation
- `IMPLEMENTED_IN_MANIFESTS`: 19 fields confirmed in gotjunk/kosei manifests
- `IMPLEMENTED_IN_TESTS`: namespace guardrail (WSP 104), shell_core validation
- `ARCHITECTURAL_CONTRACT`: capabilities gating, agent route gating, length limits

**Shell contract consistency**: Verified against `PFMALL_SHELL_CONTRACT.md` - consistent.

---

### 2026-04-12 - Matrix A local import runbook (prompts 38214 / 84726 / 55108)

**By:** 0102  

**Added**

- `modules/foundups/mobile_worker_skills/MATRIX_A_LOCAL_IMPORT_RUN.md` — step order: import `foundups-edge-load-smoke` → `ping` / `LOAD_OK`; then import `foundups-code-task-parser` → fixed test phrase; pass/fail + example JSON; URL loading explicitly out of scope for this session.

**Updated**

- `modules/foundups/mobile_worker_skills/README.md` — link to Matrix A runbook.

**Note:** Execution is **on-device** (012); repo cannot perform Gallery import from CI.

---

### 2026-04-12 - Device Edge Gallery validation prep (prompt 10003)

**By:** 0102 · **WSP:** 3, 83, 97, 104  

**Added**

- `modules/foundups/mobile_worker_skills/DEVICE_EDGE_GALLERY_VALIDATION.md` — device test matrix, pass/fail, 012 report template, Pages notes (**raw GitHub ≠ Gallery**).
- `modules/foundups/mobile_worker_skills/foundups-edge-load-smoke/SKILL.md` — minimal load smoke (`ping` → `LOAD_OK`).

**Updated**

- `modules/foundups/mobile_worker_skills/README.md` — device checklist link; smoke skill row.

---

### 2026-04-12 - Kosei FoundUp Manifest and Route Binding (WSP 104)

**By:** 0102 (Worker BT) - **Slice:** `KOSEI_FOUNDUP_MANIFEST_AND_ROUTE_BINDING_PHASE1`
**WSP References:** WSP 15, WSP 97, WSP 104

**Added**:
- `modules/foundups/kosei/foundup_manifest.json` - Canonical FoundUp manifest

**Updated**:
- `public/member/mall-video-catalog.json` - Added `routing_prefix`, `data_namespace`, `token_symbol` to kosei entry

**Metadata**:
| Field | Value |
|-------|-------|
| `foundup_id` | `kosei` |
| `routing_prefix` | `/f/kosei` |
| `entry_url` | `https://foundups.com/kosei/` |
| `lifecycle_stage` | `proto` |
| `tier` | `F0_DAE` |
| `launch_readiness` | `conditional` |

**Test coverage**: Existing `test_namespace_guardrail.py` validates WSP 104 constraints.

---

### 2026-04-10 - FoundUp README canonical alignment (FoundUp Template Update)

**By:** 0102
**WSP References:** WSP 97, WSP 83

**Updated**:
- `modules/foundups/gotjunk/README.md`
- `modules/foundups/kosei/README.md`
- `modules/foundups/move2japan/README.md`
- `modules/foundups/pqn_portal/README.md`
- `modules/foundups/social_twin/README.md`

All FoundUp READMEs now follow the canonical template from `docs/FOUNDUP_TEMPLATE.md`:
- Consistent header format with emoji identifiers
- Standardized Status, Tier, Token, and Integration sections
- Links to canonical manifests and INTERFACE docs

---

### 2026-04-01 – SoftProto Phase 1 architecture prompts

**By:** 012 → 0102 relay  
**Documents (read-only reference, not current implementation target)**:
- `docs/0102_session_briefings/SOFTPROTO_{A,B,C,D}_*_PROMPT_2026-04-01.md`
- `docs/0102_session_briefings/SOFTPROTO_SVELTE_SPIKE_PHASE1_PROMPT_2026-04-01.md`
- `modules/foundups/docs/SOFTPROTO_*_CONTRACT.md`
- `modules/foundups/docs/SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md`
- `modules/foundups/docs/SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md`

**Status**: ARCHIVE_RECONCILE_NEEDED per `ACTIVE_SLICE_LEDGER.md`. Overlap with PMCTRL1 and WRE contracts requires reconciliation before revival.

---

### 2026-03-31 – p.fMALL architecture docs (first tranche)

**By:** 0102  
**Slice:** `pfmall_architecture_and_template_contract`

**Added**:
- `PFMALL_SHELL_CONTRACT.md` – shell responsibilities, boot, postMessage API
- `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` – manifest fields, validation, HMAC
- `PFMALL_ROUTING_DISCOVERY_MODEL.md` – URL structure, catalog, navigation
- `PFMALL_DATA_ISOLATION_MODEL.md` – IndexedDB isolation, encryption, sentinel
- `PFMALL_LAUNCH_CATALOG_TAXONOMY.md` – categories, launch order

**Note**: Architecture specification only. PWA code is Phase 2+.

---

### 2026-03-28 – GotJunk 3-app architecture extraction

**By:** 0102  
**Slice:** `gotjunk_3app_extraction`

**Added**:
- `FOUNDUP_ECOSYSTEM_ARCHITECTURE.md` – 3-app PWA model (mobile, pwa, dash)
- GotJunk extraction validation gates

---

### 2026-03-25 – FoundUp Exfoliation Protocol

**By:** 0102  
**Slice:** `foundup_exfoliation_protocol`

**Added**:
- `FOUNDUP_EXFOLIATION_PROTOCOL.md` – incubating → proto → externalized lifecycle
- Exfoliation readiness criteria and decision gates

---

### 2026-03-20 – Domain canonical index

**By:** 0102

**Added**:
- `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md` – master index of all FoundUps
- Links to manifests, ROADMAPs, and lifecycle stages

---

*End of ModLog*
