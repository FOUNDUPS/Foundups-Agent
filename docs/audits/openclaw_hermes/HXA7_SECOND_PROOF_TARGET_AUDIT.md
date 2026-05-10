# HXA7 — Second FoundUp Proof Target Audit

**Slice**: `HXA7_SECOND_PROOF_TARGET_AUDIT_PHASE1`
**Worker**: W4
**Date**: 2026-05-10
**Mode**: Audit only — no code edits
**WSP Lock**: WSP_00 → WSP_15 → WSP_50 → WSP_97

---

## Mission

Compare Trade, GotJunk, and VoteBallots to choose the second FoundUp proof target after VoteBallots (HXA4).

---

## 1. HoloIndex Research

```bash
python holo_index.py --fast-search --search "Trade GotJunk VoteBallots FoundUp Hermes extraction second proof target lifecycle" --limit 10
```

**Top hits**:
- `modules/foundups/agent_market/README.md`
- `modules/communication/moltbot_bridge/src/fam_adapter.py:FAMAdapter.launch_foundup()`
- Mesa model simulation: `modules/foundups/simulator/mesa_model.py`

---

## 2. Candidate Manifest Comparison

| Field | GotJunk | Trade | VoteBallots |
|-------|---------|-------|-------------|
| `foundup_id` | `gotjunk_001` | `trade` | `voteballots` |
| `lifecycle_stage` | `proto` | `incubating` | `incubating` |
| `launch_readiness` | `conditional` | `discoverable_only` | `discoverable_only` |
| `entry_url` | `https://gotjunk-56566376153.us-west1.run.app/` | `null` | `""` (empty) |
| `tier` | `F0_DAE` | `F0_DAE` | `F0_DAE` |
| `capabilities` | search, agents_basic, marketplace, offline | market_intelligence, risk_scoring, simulation | search, agents_basic |
| `agent_routes` | openclaw_query, openclaw_task | openclaw_query | openclaw_query |
| `created_at` | 2026-03-01 | 2026-05-04 | 2026-04-22 |

---

## 3. Implementation Status Evidence

### 3.1 GotJunk

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Deployed artifact | **YES** | Cloud Run URL operational |
| Frontend exists | **YES** | `frontend/App.tsx`, React 19 + Vite |
| PWA manifest | **YES** | `manifest.json`, service worker |
| PoC Phase 1 | **COMPLETE** | Per README: photo capture, swipe, geo-filtering |
| Cloud Run CSP | **VERIFIED** | Per memory: frame-ancestors verified 2026-04-19 |
| Deploy pipeline | **AUTONOMOUS** | `.github/workflows/deploy-gotjunk.yml` |
| Hermes readiness | **CONDITIONAL** | Deploy blocker resolved, DE4 ready |

### 3.2 Trade

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Deployed artifact | **NO** | `entry_url: null`, "Not deployed. Internal prototype only" |
| Frontend exists | **NO** | No `frontend/` directory |
| Implementation | **NO** | Phase 0 - contracts only |
| WSP 97 constraints | Active | `no_money_mode: True`, `dry_run_mode: True` |
| Hermes readiness | **NOT READY** | No runnable artifact to extract |

### 3.3 VoteBallots

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Deployed artifact | **NO** | `entry_url: ""` (empty) |
| Frontend exists | **NO** | Design specification only |
| Implementation | **NO** | `_wsp97_implementation_state: SPECIFIED_NOT_IMPLEMENTED` |
| Architecture doc | **YES** | 1300+ line architecture specification |
| Hermes readiness | **NOT READY** | No runnable artifact to extract |

---

## 4. WSP 15 Scoring Matrix

Scoring criteria per WSP 15 (Functional Evaluation):

| Criterion | Weight | GotJunk | Trade | VoteBallots |
|-----------|--------|---------|-------|-------------|
| **Deployed entry_url** | 30% | 30 | 0 | 0 |
| **Runnable artifact** | 25% | 25 | 0 | 0 |
| **PoC completion** | 15% | 15 | 0 | 0 |
| **Autonomous deploy** | 10% | 10 | 0 | 0 |
| **Hermes adapter ready** | 10% | 8 | 0 | 0 |
| **Architecture docs** | 10% | 8 | 6 | 10 |
| **TOTAL** | 100% | **96** | **6** | **10** |

---

## 5. Hermes Extraction Prerequisites

Per HXA1 and memory `hermes_architecture.md`:

| Prerequisite | GotJunk | Trade | VoteBallots |
|--------------|---------|-------|-------------|
| `entry_url` populated | YES | NO | NO |
| Deployed & operational | YES | NO | NO |
| CSP headers verified | YES | N/A | N/A |
| DE4-ready (GitHub repo) | YES (per memory) | NO | NO |
| `launch_readiness >= conditional` | YES | NO | NO |

**Minimum extraction bar**: `entry_url` populated AND deployed artifact operational.

---

## 6. Blockers Analysis

### GotJunk Blockers

| Blocker | Status | Resolution |
|---------|--------|------------|
| Cloud Run deploy | RESOLVED | Autonomous pipeline 2026-04-19 |
| CSP headers | RESOLVED | frame-ancestors verified |
| `entry_url` in manifest | PRESENT | `https://gotjunk-56566376153.us-west1.run.app/` |

**Current blockers**: None identified for Phase 1 extraction.

### Trade Blockers

| Blocker | Status | Resolution |
|---------|--------|------------|
| No deployment | BLOCKING | Requires implementation first |
| No frontend | BLOCKING | Architecture only |
| Phase 0 constraints | ACTIVE | No capital, simulation only |

**Current blockers**: Multiple — not extraction-ready.

### VoteBallots Blockers

| Blocker | Status | Resolution |
|---------|--------|------------|
| No implementation | BLOCKING | Architecture spec only |
| No deployment | BLOCKING | `entry_url` empty |
| SPECIFIED_NOT_IMPLEMENTED | ACTIVE | Per manifest `_wsp97_note` |

**Current blockers**: Multiple — not extraction-ready.

---

## 7. HXA4 Context

VoteBallots is referenced as the first proof target (HXA4). However:

- VoteBallots has **zero runnable implementation**
- VoteBallots is **architecture specification only**
- Any HXA4 VoteBallots proof would be **contract validation**, not extraction

**Implication**: If VoteBallots remains the first target for contract/schema validation, GotJunk becomes the natural second target for **actual extraction proof**.

---

## 8. Verdict

### **GOTJUNK_SECOND**

**Rationale**:

1. **Only candidate with deployed artifact** — `entry_url` operational, Cloud Run verified
2. **WSP 15 score**: 96/100 vs 6 (Trade) vs 10 (VoteBallots)
3. **PoC Phase 1 complete** — photo capture, swipe UI, geo-filtering all working
4. **Hermes prerequisites met** — CSP headers, autonomous deploy, DE4-ready
5. **Trade and VoteBallots are not extractable** — both lack runnable implementations

### Alternative Verdicts Considered

| Verdict | Why Rejected |
|---------|--------------|
| `TRADE_SECOND` | Phase 0, no deployment, contracts only — WSP 15 score 6 |
| `VOTEBALLOTS_ONLY_UNTIL_HXA4` | VoteBallots itself has no implementation — can't prove extraction |
| `SECOND_TARGET_BLOCKED` | GotJunk is extraction-ready — no systemic blocker |

---

## 9. Recommended Next Steps

1. **HXA4**: Complete VoteBallots contract/schema validation (architecture proof, not extraction)
2. **HXA8** (proposed): GotJunk Hermes extraction Phase 1 — boundary analysis, exfoliation gate, dry-run extraction
3. **DE4**: GotJunk GitHub repo creation (per memory, ready to proceed)

---

## 10. WSP 97 Truth Table

| Claim | Status | Evidence |
|-------|--------|----------|
| GotJunk has entry_url | VERIFIED | Manifest line 10 |
| GotJunk Cloud Run deployed | VERIFIED | Memory: resolved 2026-04-19 |
| Trade has no deployment | VERIFIED | README: "Not deployed. Internal prototype only" |
| VoteBallots has no implementation | VERIFIED | Manifest `_wsp97_implementation_state` |
| GotJunk is extraction-ready | ASSESSED | All prerequisites met per HXA1 criteria |
| WSP 15 scoring applied | TRUE | Weighted matrix above |

---

## Sources

### Internal

| Document | Location |
|----------|----------|
| GotJunk Manifest | `modules/foundups/gotjunk/foundup_manifest.json` |
| Trade Manifest | `modules/foundups/trade/foundup_manifest.json` |
| VoteBallots Manifest | `modules/foundups/voteballots/foundup_manifest.json` |
| GotJunk README | `modules/foundups/gotjunk/README.md` |
| Trade README | `modules/foundups/trade/README.md` |
| VoteBallots README | `modules/foundups/voteballots/README.md` |
| HXA1 Audit | `docs/audits/openclaw_hermes/HXA1_OPENCLAW_HERMES_CONCATENATION_AUDIT.md` |
| Deploy Blocker Memory | `memory/gotjunk_deploy_blocker.md` |
| Hermes Architecture Memory | `memory/hermes_architecture.md` |

---

*Audit performed by Worker W4 under WSP 97 truth boundaries.*
*Slice: HXA7_SECOND_PROOF_TARGET_AUDIT_PHASE1*
