# DOCKER_MCP_AND_AI_OVERSEER_CONTROL_PLANE_AUDIT_PHASE1

**Type:** READ-ONLY decision audit (Phase 1, decision-only — no code/config/registry mutation)
**WSP discipline:** WSP_00 zen state · WSP_97 Truth Boundary · WSP 96 MCP Governance
**Date:** 2026-06-02
**Scope class:** `READ_ONLY_AUDIT_ONLY`

---

## 1. Mission + Scope

Audit two coupled questions and emit verdicts, **without creating any Docker MCP profile, installing any catalog server, enabling any Hermes gateway, or mutating any config**:

- **Part A — Docker MCP Toolkit profile audit:** Should Docker Desktop's MCP Toolkit be used as a FoundUps AI **client profile surface**, and under what constraints does `.mcp.json` + WSP 96 remain the source of truth?
- **Part B — AI Overseer control-plane audit:** Should the AI Overseer **directly use** Docker MCP / Hermes, or should it only **authorize, route, and status-check**, leaving execution to WRE / OpenClaw / Hermes under WSP_97 gates?

Part A is ordered first because the AI Overseer governance decision depends on knowing what the Docker MCP Toolkit actually does.

**Out of scope (hard):** profile creation, catalog install, OAuth, Hermes gateway/messaging enablement, OpenClaw import, Docker Model Runner adoption, any code/config/env/`.mcp.json`/registry/manifest mutation.

---

## 2. Predecessors / Current Context

| Predecessor | Conclusion carried forward | Cite |
|---|---|---|
| MCPA1 — MCP Surface Authority Audit (2026-05-08) | Canonical authority is the **engine** (`HoloIndex` class) with transport adapters: **S1 external MCP**, **S2 internal Python**; **S3 must delegate or stand down**. Authority is **not** registry-based. | `MCPA1_MCP_SURFACE_AUTHORITY_AUDIT.md:70-72,286` |
| MCPA6 — MCP Conformance Audit (2026-05-08) | Conformance scored S1 2/16, S2 11/16, S3 3/16 → `NON_CONFORMANT_BLOCKING`; live-flip **NO-GO** pending slices S6.1–S6.3. | `MCPA6_MCP_CONFORMANCE_AUDIT.md:169-174,336-342` |
| MCP_FOUNDUP_SCOPE_CURRENT_ARCHITECTURE_REAUDIT_PHASE1 | FoundUp-scope architecture re-audit baseline. | `docs/audits/mcp_system/MCP_FOUNDUP_SCOPE_CURRENT_ARCHITECTURE_REAUDIT_PHASE1.md` |
| WSP 96 — MCP Governance & Consensus | 8-step adoption consensus + Skill Supply-Chain Security Gate + External Non-MCP Runtime Intake Rule (wrapper-first). | `WSP_framework/src/WSP_96_MCP_Governance_and_Consensus_Protocol.md:53-138` |

Machine-state context (companion continuity, non-repo): a model-store migration moved the active model SSD to `E:`; Hermes is installed in WSL; Docker containment is operational; **OpenClaw import/gateway remain blocked pending audit**. This audit governs how that runtime is *exposed and controlled*, not how it was installed.

---

## 3. Repo MCP Source-of-Truth Statement

The **repo-owned `.mcp.json`** is the canonical declaration of the active MCP **client server set** for this repository. It currently declares exactly four local servers, all stdio/process-launched, **no OAuth, no catalog, no cloud dependency**:

```
holo_index      → python -m holo_index.mcp_server         (cwd .)
wsp_governance  → python -m WSP_framework.mcp_server       (cwd .)
web_search      → python -m mcp_servers.web_search.server  (cwd .)
chrome-devtools → npx -y chrome-devtools-mcp@latest        (env: no usage stats)
```
*Evidence:* `.mcp.json:3-26`.

WSP 96 supplies the **governance authority** that `.mcp.json` operates under: adoption consensus, supply-chain scanning, and conformance gates. Therefore the source of truth is the **pair**: `.mcp.json` (what client servers exist) **governed by** WSP 96 (whether/how a surface may be activated). Predecessor audits establish that canonical *tool authority* is engine-level (`HoloIndex`), not the registry — so `.mcp.json` is authoritative for **client wiring**, WSP 96 + engine adapters are authoritative for **tool truth**. Any external surface (incl. Docker MCP Toolkit) must **derive from**, never override, this pair.

---

## 4. Docker MCP Toolkit Local-State Analysis

**Epistemic flag (WSP_97):** The repository contains **no Docker MCP Toolkit artifacts** — no profile, no catalog config, no Docker MCP references except a *roadmap mention* of "Docker MCP" as a future commodity integration for Rubik_Build (`MCP_Master_Services.md:17,42,72`). Therefore claims in this section about Docker MCP Toolkit runtime behavior are **`EXTERNAL_TOOL_BEHAVIOR` — not repo-verified**, and are evaluated under a **fail-closed default** per WSP 96's External Non-MCP Runtime Intake Rule (`WSP_96:111-124`).

| # | Question | Finding (fail-closed default where unverified) |
|---|---|---|
| 1 | Can Docker MCP Toolkit import/mirror repo `.mcp.json`? | **Not natively / unverified.** Docker MCP Toolkit is driven by Docker Desktop's own catalog + enabled-server UI, not by a repo `.mcp.json`. No repo mechanism exports `.mcp.json` into it today. Treat as: **does not mirror `.mcp.json`** unless an explicit repo-exported profile is built. |
| 2 | Does it create local profile state outside the repo? | **Yes (external).** Toolkit/catalog/enabled-server state lives in Docker Desktop's config domain, **outside the repo tree** → not versioned, not WSP-22 logged, violates source-of-truth unless exported back. |
| 3 | Can profile state be exported/versioned? | **Only via deliberate export.** A repo-exported profile (server command set derived from `.mcp.json`) can be checked in and versioned; the Toolkit does not do this automatically. |
| 4 | Does it require OAuth / cloud / catalog access? | **Catalog = cloud dependency.** Pulling servers from the Docker MCP Catalog reaches Docker Hub; several catalog servers require OAuth/secrets. The four repo servers require **none** of this. |
| 5 | Does it weaken WSP 96 governance? | **Yes, if used for catalog installs.** The catalog-install path bypasses WSP 96's 8-step adoption consensus and Skill Supply-Chain Security Gate (`WSP_96:53-138`). Used *only* to launch repo-owned server commands, it does not. |

---

## 5. Docker MCP Toolkit Profile / Export / Versioning Analysis

- **Authoritative direction must be `.mcp.json` → profile**, never profile → repo. A one-way, repo-owned export (generated from `.mcp.json`) is the only shape that keeps the source of truth intact.
- **No bidirectional sync.** Any path where the Docker Toolkit UI mutates the effective server set and that drifts back into agents is a governance regression (recreates the multi-surface drift MCPA1 flagged: `MCPA1:230-237`).
- **Versioning requirement:** if a Docker MCP profile is ever adopted, it must be (a) generated from `.mcp.json`, (b) committed under the repo, (c) WSP-22 logged, (d) re-generated (not hand-edited) on `.mcp.json` change.
- **Secrets:** profile export must carry **command + args only**, never secret values (`web_search` API keys stay in env, not in any exported profile) — `NO_SECRET_VALUES`.

---

## 6. Safe Repo MCP Server Matrix

Suitability of each **repo-owned** server as an *optional* Docker MCP client-profile entry (launched as the same local command `.mcp.json` already defines):

| Server | Transport / launch | External deps | OAuth/cloud | Safe as optional client-profile entry? | Note |
|---|---|---|---|---|---|
| `holo_index` | stdio `python -m holo_index.mcp_server` | local engine | None | ✅ **SAFE** | Canonical engine surface (S1); read-oriented semantic search. |
| `wsp_governance` | stdio `python -m WSP_framework.mcp_server` | local | None | ✅ **SAFE** | Governance/lookup; local only. |
| `web_search` | stdio `python -m mcp_servers.web_search.server` | network egress (DuckDuckGo / optional Serper) | API key in **env only** | ✅ **SAFE (egress-aware)** | Network egress is the only sensitivity; secret stays in env, never in profile. |
| `chrome-devtools` | `npx -y chrome-devtools-mcp@latest` | npm package fetch + local browser control | None | ⚠️ **CONDITIONAL** | Pulls an external npm package at launch and drives a browser. Acceptable as-is in `.mcp.json`; if mirrored to a Docker profile, pin the version and keep it local-only. |

All four are launchable from a repo-exported profile **without** touching the Docker MCP Catalog.

---

## 7. Blocked Catalog MCP Server Policy

**Policy: `BLOCK_PENDING_SECURITY_GATE` for every Docker MCP Catalog (third-party) server.** None may be enabled until it passes WSP 96 adoption:

- WSP 15 scoring (Research → Trial) — `WSP_96:162-181`
- Qwen technical review → Gemma safety validation → 0102 strategic approval → Bell-state verification — `WSP_96:53-70`
- **Skill Supply-Chain Security Gate**: scan before activation, **fail-closed if scanner unavailable**, block above severity threshold, persist evidence — `WSP_96:126-138`
- Conformance Gate C1–C7 (truth envelope, real backend, truth-status label, manager registration) — `WSP_96 Annex A.5:445-462`

Explicitly blocked pending the gate: Git/GitHub/GitLab MCP, **Docker MCP**, Memory-Bank/Knowledge-Graph MCP, Postman MCP, Snyk MCP, Puppeteer/Playwright MCP, and any other catalog entry (roadmap list: `MCP_Master_Services.md:66-80`). Default posture per `WSP_96:111-124`: **external research runtime first, MCP wrapper later, no direct production repo mutation.**

---

## 8. AI Overseer Current Authority Map

| # | Question | Finding | Evidence |
|---|---|---|---|
| 1 | Authority today? | **Monitor + govern**, not tool-execute. MCP is optional and gracefully degraded (`self.mcp = None` path). | `ai_overseer.py:265-270`; `MCP_DEPENDENCY_ANALYSIS.md:1-92` |
| 2 | Can it call MCP Manager status safely? | **Capability exists; not actively used.** MCP Manager exposes read-only `get_server_status()` / `perform_health_check()` / `discover_all_surfaces()`. AI Overseer only holds passive in-memory `get_mcp_status()`. | `mcp_manager.py:392-419,540-602`; `mcp_integration.py:449-468` |
| 3 | Can it trigger MCP tools directly today? | **No.** `execute_mcp_tool()` returns "Server not connected"; `_execute_tool()` returns `{"simulated": True}`. Scaffold only. | `mcp_integration.py:351-366,395-425` |
| 4 | What does it monitor today? | OpenClaw security, WSP-framework drift, IronClaw runtime, HoloDAE telemetry. **Not** Docker, **not** Hermes doctor, **not** MCP availability. | `ai_overseer.py:429-495,508-537,584-630`; `holo_telemetry_monitor.py:92-157` |
| 5 | WRE jobs vs inline? | Hybrid: inline for low-complexity auto-fix; **creates WRE missions** for complex/high-risk activities. | `ai_overseer.py:1878-1892,2318-2472` |

MCP Manager itself **does not implement tool invocation** (documented "Future") — only lifecycle + discovery (`mcp_manager INTERFACE.md:64-70`). Execution authority lives in `hermes_job_executor.py`, which enforces D0–D6 action classification, HXA27 token validation, HXA23 destructive-action guard, and **blocks real delegation in Phase 1** (`hermes_job_executor.py:1387-1711`).

---

## 9. Proposed Control-Plane Flow

```
                 ┌─────────────────────────────────────────────┐
                 │              AI OVERSEER                      │
                 │  (govern · authorize · status-check ONLY)    │
                 │                                              │
   status signals│  reads → MCP Manager status/health (RO)      │
   ◀─────────────│  reads → Docker running? (RO probe)          │
                 │  reads → Hermes doctor READY/NOT_READY (RO)  │
                 │  reads → gateway disabled? OpenClaw import?   │
                 │                                              │
                 │  authorizes ↓ (issues a governed job)        │
                 └───────────────┬──────────────────────────────┘
                                 │ WRE job (no inline tool call)
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │     WRE / OpenClaw / Hermes (EXECUTION)       │
                 │  hermes_job_executor: D0–D6 classify →        │
                 │  HXA27 token → HXA23 destructive guard →      │
                 │  real delegation BLOCKED (Phase 1)            │
                 └─────────────────────────────────────────────┘
                                 │ tool calls flow ONLY here
                                 ▼
                 repo-owned MCP servers (.mcp.json)  ·  [catalog = BLOCKED]
```

AI Overseer **never** calls Docker MCP Toolkit or an MCP tool inline. It reads status and issues governed WRE jobs; the gated executor decides and (in Phase 2+) executes.

---

## 10. Allowed Actions

- AI Overseer **read-only status** calls: `mcp_manager.get_server_status()` / `perform_health_check()` / `discover_all_surfaces()`.
- Read-only probes: Docker daemon running?, Hermes doctor READY/NOT_READY, MCP servers available, Hermes gateway disabled (assert-disabled), OpenClaw import **not** applied (assert-not-applied).
- AI Overseer **issuing governed WRE jobs** (which then pass through `hermes_job_executor` gates).
- Launching **repo-owned** `.mcp.json` servers as local processes (already permitted today).
- Building a **one-way, repo-exported** Docker profile *generated from* `.mcp.json` (future slice; not in this audit).

---

## 11. Blocked Actions

- `NO_DOCKER_MCP_PROFILE_CREATION`, `NO_MCP_CATALOG_INSTALL`, `NO_OAUTH`.
- `NO_HERMES_GATEWAY_ENABLE` (gateway/messaging stays disabled), `NO_OPENCLAW_IMPORT`.
- `NO_DOCKER_MODEL_RUNNER_ENABLE` (pending a separate model-runtime audit).
- AI Overseer **direct** MCP/Docker-MCP tool invocation.
- Any direct shell/file execution **outside** WRE/Hermes gates.
- Catalog server enablement before WSP 96 supply-chain gate + WSP 15 scoring.
- `NO_MCP_JSON_EDIT`, `NO_CONFIG_CHANGE`, `NO_ENV_MUTATION`, `NO_REGISTRY_MUTATION`, `NO_MANIFEST_MUTATION`, `NO_PUBLIC_SURFACE_MUTATION`, `NO_SECRET_VALUES`.

---

## 12. Verdicts

### Part A — Docker MCP Toolkit
- **Primary verdict: `USE_ONLY_WITH_REPO_EXPORTED_PROFILE`** — Docker MCP Toolkit may serve as an *optional* client surface **only** if it consumes a one-way, repo-owned profile generated from `.mcp.json`; the Toolkit's own catalog/UI must never become the source of truth.
- **Catalog sub-verdict: `BLOCK_PENDING_SECURITY_GATE`** — every Docker MCP Catalog (third-party) server is blocked until WSP 96 adoption + Skill Supply-Chain Security Gate pass.

*Net:* Docker MCP is an optional client surface; `.mcp.json` + WSP 96 remain canonical.

### Part B — AI Overseer control plane
- **Role verdict: `AI_OVERSEER_GOVERNANCE_ROUTER`** — govern / authorize / status-check; route execution to WRE/OpenClaw/Hermes.
- **Direct-use verdict: `AI_OVERSEER_DIRECT_TOOL_USE_BLOCKED`** — must not invoke Docker MCP Toolkit or MCP tools directly.
- **Implementation readiness: `READY_FOR_STATUS_INTEGRATION_IMPL`** — read-only status-signal integration is the safe next slice; tool execution stays out.
- **Runtime expansion: `BLOCKED_PENDING_SECURITY_GATE`** — catalog install, gateway enable, OpenClaw import, Docker Model Runner all blocked pending their gates.

*Expected answer confirmed:* AI Overseer governs/authorizes/status-checks; execution remains in WRE/OpenClaw/Hermes under WSP_97 gates.

---

## 13. Recommended Next Implementation Slice

**`MCP_AND_RUNTIME_STATUS_PANEL_IMPL_PHASE1`** (status-only, read-only, no tool invocation):

1. Add an AI Overseer **read-only status panel** that calls `mcp_manager.perform_health_check()` / `get_server_status()` for the four repo servers.
2. Add four assert-state signals: **Docker running**, **Hermes doctor READY/NOT_READY**, **Hermes gateway disabled** (assert-disabled), **OpenClaw import not applied** (assert-not-applied).
3. Surface these as monitoring signals only — **no** job issuance, **no** tool calls, **no** gateway/catalog/runner enablement.
4. Gate the slice with the same hard constraints as this audit; ship as a decision→impl PHASE1 (execution-class) branch separate from this decision-only doc.

This is the minimum that lets AI Overseer *see* the Docker/Hermes/MCP runtime without acquiring any execution authority.

---

## 14. WSP_97 Truth Boundary Checklist

| # | Truth Boundary Checklist Item | Status | Evidence |
|---|---|---|---|
| 1 | READ_ONLY_AUDIT_ONLY | ✅ YES | Only one new doc created; no source/config touched. |
| 2 | NO_DOCKER_MCP_PROFILE_CREATION | ✅ YES | No profile created; §4–5 analysis only. |
| 3 | NO_MCP_CATALOG_INSTALL | ✅ YES | Catalog left untouched; §7 sets block policy. |
| 4 | NO_OAUTH | ✅ YES | No OAuth flow initiated; repo servers need none (`.mcp.json:3-26`). |
| 5 | NO_HERMES_GATEWAY_ENABLE | ✅ YES | Gateway stays disabled; §11. |
| 6 | NO_OPENCLAW_IMPORT | ✅ YES | Import not applied; §11. |
| 7 | NO_DOCKER_MODEL_RUNNER_ENABLE | ✅ YES | Deferred to model-runtime audit; §11–12. |
| 8 | NO_CODE_CHANGE | ✅ YES | Zero `.py` edits; evidence reads only. |
| 9 | NO_CONFIG_CHANGE | ✅ YES | No config files modified. |
| 10 | NO_ENV_MUTATION | ✅ YES | No env vars set/changed. |
| 11 | NO_MCP_JSON_EDIT | ✅ YES | `.mcp.json` read only (`.mcp.json:3-26`). |
| 12 | NO_SECRET_VALUES | ✅ YES | No secrets displayed; web_search key noted as env-only. |
| 13 | NO_REGISTRY_MUTATION | ✅ YES | No registry writes. |
| 14 | NO_MANIFEST_MUTATION | ✅ YES | No manifest writes. |
| 15 | NO_PUBLIC_SURFACE_MUTATION | ✅ YES | No public surface changed. |
| 16 | NO_CABR_READY | ✅ YES | No CABR readiness asserted. |
| 17 | NO_PAYOUT_READY | ✅ YES | No payout readiness asserted. |
| 18 | NO_DAO_ACTIVATION | ✅ YES | No DAO activation. |

**WSP_97 Truth Boundary: 18/18 YES.**

---

*Internal Review Verdict: READY. Decision-only audit; one file; verdicts grounded in cited evidence; all hard constraints held.*
