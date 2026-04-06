# Next Build Order — OpenClaw Integration Ledger

**Worker G** · `OPENCLAW_PLUGIN_LEDGER_AUDIT_PHASE1` · 2026-04-05

---

## Tier 0 — Keep ledger honest (no code required)

1. Treat `docs/audits/openclaw_plugins/*` as the **canonical narrative** until a machine-readable manifest exists.
2. When adding any external tool (Firecrawl, new provider, etc.), **update ledger first** — name, env, default, fail mode, owner module.
3. Track OpenRouter module status — currently untracked in git (`modules/infrastructure/openrouter_client/`).

## Tier 1 — Consolidate env surface (smallest useful code)

4. ~~Create `modules/communication/moltbot_bridge/config/openclaw_integration_manifest.json`~~ — **DONE** (Worker G, 2026-04-05): 15-integration manifest committed. Commit `a0fad35`.
5. Optional: CI lint that every `OPENCLAW_*` / `IRONCLAW_*` / `OPENROUTER_*` env in `main.py` + DAE code appears in manifest.
6. ~~Decision: commit or `.gitignore` the OpenRouter client module~~ — **DONE** (Worker G, 2026-04-05): committed to git as tracked module. Consumer: `consciousness_migration/executor.py`.

## Tier 2 — OpenRouter integration decision

7. OpenRouter is a landed module but only consumed by one skill (`consciousness_migration`). Decide:
   - **A**: Promote to AI Gateway provider (alongside OpenAI/Anthropic/Grok/Gemini) — adds unified routing
   - **B**: Keep standalone for skill-specific use — simpler, current state
   - **C**: Deprecate in favor of direct AI Gateway providers — removes indirection

## Tier 3 — Firecrawl (only if product requires)

8. After Tier 0–1: if Firecrawl is still desired, implement **one** integration path (prefer MCP tool), env-gated **default off**, update `PLUGIN_SWITCH_MATRIX.md`.
9. First: evaluate whether existing MCP `fetch_webpage` + OpenRouter web search cover the use case.

---

## Smallest truthful step now

**Adopt Tier 0** — use this audit folder as source of truth. No runtime change required.

**First decision needed from architect**: What to do with the untracked OpenRouter module (Tier 1 item 6).

---

## Architect direction (recorded)

**LM Studio vs OpenRouter** — Non-competing: IronClaw/LM Studio is the **local-first** conversation path (`IRONCLAW_BASE_URL`); OpenRouter is a **cloud router** used by **`consciousness_migration`** (`--backend openrouter`). Ledger should keep both lanes explicit; do not collapse the matrix into “one winner.”

**Tier 1 item 6 (untracked `openrouter_client`)** — **Track in git** once the tree is intended to be canonical: if the executor imports it, leaving it untracked is **worse** than committing or explicitly vendoring—otherwise reproducibility and audits lie. Alternatively: move behind optional extra only if deps are heavy; **do not** `.gitignore` the module solely to hide WIP unless 012 retires the import.

**Tier 2 item 7 (promote vs standalone vs deprecate)** — Default call: **B — keep standalone** for skill-specific cloud routing until a **second** in-repo consumer needs the same key surface or product asks for unified billing in AI Gateway. **A (promote to Gateway)** is a later integration slice with tests + key isolation review. **C (deprecate)** only if direct provider keys cover every model route OpenRouter was buying.

**Firecrawl** — Audit closed: **absent** in repo; further sweeps add no evidence.

**Tier 3** — No Firecrawl work until product owns one integration path and env gate.
