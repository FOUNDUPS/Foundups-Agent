# FOUNDUP_PUBLIC_SURFACE_STATUS_AUDIT_PHASE1

**WSP_97 Labels**: DOCS_ONLY, AUDIT_ONLY, NO_IMPLEMENTATION, NO_MODULE_DELETION, NO_MANIFEST_CREATION, NO_TOKEN_ASSIGNMENT, TOKEN_DEFERRED_WHERE_UNKNOWN, NO_RUNTIME_CHANGE, NO_CABR_READY, NO_PAYOUT_READY, NO_DAO_ACTIVATION

**Worker**: W9E
**Branch**: `docs/foundup-public-surface-status-audit-phase1`
**Date**: 2026-05-18
**WSP Compliance**: WSP_00, WSP_97, WSP_87, WSP_15, WSP_50

---

## Executive Summary

This audit cross-checks which FoundUps have public-facing pages/PWA surfaces now. Of 12 identified FoundUps with manifest/module.json files, **2 have live public URLs**, **1 has external repo with public surface**, and **9 are invite-only or have no public entry_url**.

---

## HoloIndex vs Grep Comparison Table

| Search Method | Query | Results | Notes |
|---------------|-------|---------|-------|
| HoloIndex | `foundup public surface entry_url deployment` | 20 hits (code=5, wsp=5, docs=5, knowledge=5) | Returned high-level architectural matches; top hits: hermes_adapter.py, CABR_Engine.md |
| Grep | `entry_url\|public.*surface` | 50+ matches | Raw pattern matching, more noise but comprehensive |
| Grep (manifests) | `is_invite_only\|launch_readiness` | 30 matches | Directly found manifest fields |

**Assessment**: HoloIndex provides conceptual/architectural context; Grep provides exhaustive field-level coverage. Both complement each other for manifest audits.

---

## FoundUp Public Surface Status Matrix

| FoundUp | foundup_id | entry_url | Deployment | is_invite_only | launch_readiness | Public PoC Capable |
|---------|------------|-----------|------------|----------------|------------------|-------------------|
| **GotJunk** | `gotjunk_001` | `https://gotjunk-56566376153.us-west1.run.app/` | Cloud Run (GitHub Actions) | true | conditional | YES (live) |
| **Kosei** | `kosei` | `https://foundupscom.web.app/kosei/app/` | Firebase Hosting | true | ready | YES (live) |
| **AutoPost** | (external) | AI Studio app | External repo (`O:/repos/AutoPost/`) | N/A | N/A | YES (external) |
| **VoteBallots/VOTE** | `voteballots` | `""` (empty) | None | true | discoverable_only | NO |
| **Trade** | `trade` | `null` | None | true | discoverable_only | NO |
| **MAGADOOM** | `magadoom_001` | `""` (empty) | None (livechat only) | true | discoverable_only | NO |
| **antifaFM** | `antifafm_001` | `""` (empty) | None (YouTube Live bridge) | true | discoverable_only | NO |
| **PQN Portal** | `pqn_portal` | (none in manifest) | Planned Cloud Run | true (implied) | poc | NO (frontend exists) |
| **Move2Japan** | `move2japan` | (surfaces in module.json) | `movetojapan.info` funnel | N/A | poc | PARTIAL |
| **Social Twin** | `social_twin` | (no entry_url) | Local browser automation | N/A | poc | NO |
| **PQN Swarm Hub** | (exfoliated) | (external) | GitHub package | N/A | proto | YES (package) |
| **p.fMALL** | (shell) | (none) | Shell runtime only | N/A | N/A | NO (orchestrator) |

---

## Detailed Surface Analysis

### 1. GotJunk (`gotjunk_001`)

**Status**: LIVE PUBLIC SURFACE

| Field | Value |
|-------|-------|
| `entry_url` | `https://gotjunk-56566376153.us-west1.run.app/` |
| `tier` | F0_DAE |
| `lifecycle_stage` | proto |
| `is_invite_only` | true |
| `launch_readiness` | conditional |
| Deployment | Cloud Run via GitHub Actions |
| Workflow | `.github/workflows/deploy-gotjunk.yml` |

**Deploy Blocker Status**: RESOLVED (2026-04-19)
- Workflow run 24640086239 deployed successfully
- CSP headers verified: `frame-ancestors https://foundups.com ...`
- Autonomous pipeline operational

**Evidence**:
- Manifest: `modules/foundups/gotjunk/foundup_manifest.json`
- Workflow: `.github/workflows/deploy-gotjunk.yml`
- Memory: `~/.claude/projects/.../gotjunk_deploy_blocker.md`

---

### 2. Kosei (`kosei`)

**Status**: LIVE PUBLIC SURFACE

| Field | Value |
|-------|-------|
| `entry_url` | `https://foundupscom.web.app/kosei/app/` |
| `tier` | F0_DAE |
| `lifecycle_stage` | incubating |
| `is_invite_only` | true |
| `launch_readiness` | ready |
| Deployment | Firebase Hosting |

**Deployment Artifact**: `public/kosei/app/index.html` at repo root

**Evidence**:
- Manifest: `modules/foundups/kosei/foundup_manifest.json`
- Firebase config at repo root

---

### 3. AutoPost (External)

**Status**: EXTERNAL PUBLIC SURFACE

| Field | Value |
|-------|-------|
| Location | `O:/repos/AutoPost/` |
| AI Studio URL | `https://ai.studio/apps/a53b5519-3cb4-40f0-a999-fcf0fa381023` |
| Description | AI AutoPost Camera for shop owners |
| Type | Vite + TypeScript app |

**Note**: Separate repository, not in monorepo manifest system. Uses Gemini API.

**Evidence**:
- `O:/repos/AutoPost/README.md`
- `O:/repos/AutoPost/metadata.json`

---

### 4. VoteBallots/VOTE (`voteballots`)

**Status**: NO PUBLIC SURFACE

| Field | Value |
|-------|-------|
| `entry_url` | `""` (empty string) |
| `tier` | F0_DAE |
| `lifecycle_stage` | incubating |
| `is_invite_only` | true |
| `launch_readiness` | discoverable_only |
| `_wsp97_implementation_state` | SPECIFIED_NOT_IMPLEMENTED |

**Note**: Architecture and AI hooks spec complete. No runnable implementation. See `docs/VOTEBALLOTS_AI_HOOKS_ARCHITECTURE.md`.

**Evidence**:
- Manifest: `modules/foundups/voteballots/foundup_manifest.json`
- Module: `modules/foundups/voteballots/module.json`

---

### 5. Trade (`trade`)

**Status**: NO PUBLIC SURFACE

| Field | Value |
|-------|-------|
| `entry_url` | `null` |
| `tier` | F0_DAE |
| `lifecycle_stage` | incubating |
| `is_invite_only` | true |
| `launch_readiness` | discoverable_only |

**Note**: Autonomous trading intelligence. Market-adapter driven, chain-agnostic. Design phase.

**Evidence**:
- Manifest: `modules/foundups/trade/foundup_manifest.json`

---

### 6. MAGADOOM (`magadoom_001`)

**Status**: NO PUBLIC SURFACE (livechat only)

| Field | Value |
|-------|-------|
| `entry_url` | `""` (empty string) |
| `tier` | F0_DAE |
| `lifecycle_stage` | incubating |
| `is_invite_only` | true |
| `launch_readiness` | discoverable_only |
| `category` | games |

**Note**: Gamified moderation engine. Quake-style fragging XP from YouTube live chat timeouts. No standalone web surface.

**Evidence**:
- Manifest: `modules/gamification/whack_a_magat/foundup_manifest.json`

---

### 7. antifaFM (`antifafm_001`)

**Status**: NO PUBLIC SURFACE (YouTube Live bridge)

| Field | Value |
|-------|-------|
| `entry_url` | `""` (empty string) |
| `tier` | F0_DAE |
| `lifecycle_stage` | proto |
| `is_invite_only` | true |
| `launch_readiness` | discoverable_only |
| `category` | media |

**Note**: 24/7 headless radio broadcaster. Bridges Icecast to YouTube Live via FFmpeg. Public surface is YouTube Live, not a PWA.

**Evidence**:
- Manifest: `modules/platform_integration/antifafm_broadcaster/foundup_manifest.json`

---

### 8. PQN Portal (`pqn_portal`)

**Status**: NO PUBLIC SURFACE (frontend exists, not deployed)

| Field | Value |
|-------|-------|
| `entry_url` | (not in module.json) |
| `routing_prefix` | `/f/pqn_portal` |
| `data_namespace` | `idb_pqn_portal` |
| Planned deployment | Cloud Run + static frontend |

**Frontend Assets**:
- `modules/foundups/pqn_portal/frontend/index.html`
- `modules/foundups/pqn_portal/frontend/demo.html`
- `modules/foundups/pqn_portal/frontend/gallery.html`

**ROADMAP**: PoC (Hello PQN) -> Prototype (GCP deploy) -> MVP (Firebase auth)

**Note**: No `foundup_manifest.json`, only `module.json`. Frontend exists but not deployed.

**Evidence**:
- Module: `modules/foundups/pqn_portal/module.json`
- README: `modules/foundups/pqn_portal/README.md`
- ROADMAP: `modules/foundups/pqn_portal/ROADMAP.md`

---

### 9. Move2Japan (`move2japan`)

**Status**: PARTIAL PUBLIC SURFACE

| Field | Value |
|-------|-------|
| `surfaces.funnel` | `movetojapan.info` |
| `surfaces.pwa` | `movetojapan.foundups.com` |
| `status` | poc |

**Note**: Agent-driven relocation system. Has declared surfaces but unverified live status.

**Evidence**:
- Module: `modules/foundups/move2japan/module.json`

---

### 10. Social Twin (`social_twin`)

**Status**: NO PUBLIC SURFACE

| Field | Value |
|-------|-------|
| `surfaces.review` | discord_or_telegram |
| `surfaces.execution` | local_browser_automation |
| `surfaces.future_operator_ui` | browser_sidecar |
| `status` | poc |

**Note**: Human-in-the-loop social engagement. No web surface - uses Discord/Telegram and local browser.

**Evidence**:
- Module: `modules/foundups/social_twin/module.json`

---

### 11. PQN Swarm Hub (Exfoliated)

**Status**: EXTERNAL PACKAGE

| Field | Value |
|-------|-------|
| Primary repo | `https://github.com/FOUNDUPS/science-swarm-hub` |
| Backup repo | `https://github.com/Foundup/science-swarm-hub` |
| Package | `pip install science-swarm-hub` |
| Local stub | `modules/foundups/pqn_swarm_hub/` |

**Note**: Module exfoliated to standalone repositories. Monorepo directory is a stub.

**Evidence**:
- README: `modules/foundups/pqn_swarm_hub/README.md`
- External: `O:/repos/science-swarm-hub/`

---

### 12. p.fMALL (Shell)

**Status**: NO PUBLIC SURFACE (orchestrator)

| Field | Value |
|-------|-------|
| Type | Shell runtime / orchestrator |
| Location | `modules/foundups/pfmall/` |

**Note**: p.fMALL is the shell that hosts other FoundUps, not a FoundUp itself. It has no public entry_url - it IS the surface.

**Capabilities**:
- Manifest discovery
- Catalog assembly
- Route resolution
- Overlay merge

**Evidence**:
- Shell: `modules/foundups/pfmall/shell_core.py`

---

## Additional FoundUps Without Manifests

| Directory | Status |
|-----------|--------|
| `modules/foundups/geoze/` | No manifest, src/tests only |
| `modules/foundups/ecosystem_animation/` | Visual animation module, not a FoundUp |
| `modules/foundups/mobile_worker_skills/` | Skills collection, not a FoundUp |

---

## Gate Status Summary

| Gate Status | FoundUps |
|-------------|----------|
| **is_invite_only: true** | GotJunk, Kosei, VoteBallots, Trade, MAGADOOM, antifaFM |
| **is_invite_only: false/N/A** | AutoPost (external), Move2Japan, Social Twin, PQN Portal |
| **launch_readiness: ready** | Kosei |
| **launch_readiness: conditional** | GotJunk |
| **launch_readiness: discoverable_only** | VoteBallots, Trade, MAGADOOM, antifaFM |

---

## Public PoC Capability Summary

| Capability | FoundUps |
|------------|----------|
| **LIVE PUBLIC URL** | GotJunk, Kosei |
| **EXTERNAL PUBLIC** | AutoPost, PQN Swarm Hub (package) |
| **FRONTEND EXISTS** | PQN Portal (not deployed) |
| **PARTIAL/DECLARED** | Move2Japan |
| **NO PUBLIC SURFACE** | VoteBallots, Trade, MAGADOOM, antifaFM, Social Twin |
| **ORCHESTRATOR (N/A)** | p.fMALL |

---

## Manifest Coverage Gap

| Has `foundup_manifest.json` | Count |
|-----------------------------|-------|
| Yes | 6 (GotJunk, Kosei, VoteBallots, Trade, MAGADOOM, antifaFM) |
| No (module.json only) | 4 (PQN Portal, Move2Japan, Social Twin, Trade) |
| No (external) | 2 (AutoPost, PQN Swarm Hub) |

**Note**: Trade has both `foundup_manifest.json` AND `module.json`.

---

## WSP_97 Compliance Verdict

| Check | Status |
|-------|--------|
| DOCS_ONLY | PASS - No code changes |
| AUDIT_ONLY | PASS - Cross-reference only |
| NO_IMPLEMENTATION | PASS - No new code |
| NO_MODULE_DELETION | PASS - No deletions |
| NO_MANIFEST_CREATION | PASS - No manifests created |
| NO_TOKEN_ASSIGNMENT | PASS - Token fields documented only |
| TOKEN_DEFERRED_WHERE_UNKNOWN | PASS - No token assumptions |
| NO_RUNTIME_CHANGE | PASS - No runtime modifications |
| NO_CABR_READY | PASS - No CABR state changes |
| NO_PAYOUT_READY | PASS - No payout triggers |
| NO_DAO_ACTIVATION | PASS - No DAO activations |

---

## Next Slice Recommendation

**FOUNDUP_PUBLIC_SURFACE_REGISTRY_FIELDS_PHASE1**

Scope:
- Define standardized `public_surface` registry schema
- Reconcile `entry_url` vs `surfaces` field patterns
- Propose `deployment_status` field for live/pending/none
- Propose `public_poc_capable` boolean field
- Create validation tests for surface field consistency

---

## Files Referenced

| File | Purpose |
|------|---------|
| `modules/foundups/gotjunk/foundup_manifest.json` | GotJunk manifest |
| `modules/foundups/kosei/foundup_manifest.json` | Kosei manifest |
| `modules/foundups/voteballots/foundup_manifest.json` | VoteBallots manifest |
| `modules/foundups/trade/foundup_manifest.json` | Trade manifest |
| `modules/gamification/whack_a_magat/foundup_manifest.json` | MAGADOOM manifest |
| `modules/platform_integration/antifafm_broadcaster/foundup_manifest.json` | antifaFM manifest |
| `modules/foundups/pqn_portal/module.json` | PQN Portal module |
| `modules/foundups/move2japan/module.json` | Move2Japan module |
| `modules/foundups/social_twin/module.json` | Social Twin module |
| `modules/foundups/pfmall/shell_core.py` | p.fMALL shell |
| `O:/repos/AutoPost/README.md` | AutoPost external |
| `O:/repos/science-swarm-hub/README.md` | PQN Swarm Hub external |
| `.github/workflows/deploy-gotjunk.yml` | GotJunk deployment |

---

*Audit complete. W9E.*
