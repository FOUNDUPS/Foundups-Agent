# Discord Operating Surface Audit — Science Swarm Phase 1

**Worker**: BE  
**Date**: 2026-04-09  
**Scope**: All Discord-facing modules in Foundups-Agent codebase  

---

## Surface Table

| Component | Status | Evidence | Operator Dependency | Next Gap |
|-----------|--------|----------|---------------------|----------|
| **OBAI Discord Bot** | CODE-VERIFIED | 26 tests pass; README documents bot ID `1218413610750423061`, guild `412646632992014336`; runbook + smoke test in README | Token `OBAI_BOT` required; no guild filter (responds anywhere invited) | No live guild verification logged yet |
| **0102/OpenClaw Bot** | LIVE-VERIFIED | `DISCORD_OPERATOR_SURFACE.md` verified 2026-04-09; App ID `839968873851387944`; OAuth fix documented; TestModLog exists | Token `DISCORD_0102_BOT_TOKEN`; requires Message Content + Server Members (Presence optional) | Webhook lane spec-only (not deployed) |
| **antifaFM Radio Bot** | CODE-VERIFIED | 6 Discord voice tests pass; README V3.3.2 documents live guild verification | Token `ANTIFAFM_DISCORD_BOT_TOKEN`; env gate `ANTIFAFM_DISCORD_VOICE_ENABLED` | Requires manual join to voice channel; no auto-reconnect on disconnect |
| **Science Swarm Discord** | EMBEDDED-CATEGORY | Standalone server rejected; embedded as category inside FOUNDUPS server per `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md` | Uses existing FOUNDUPS guild; no separate server | Category channels not yet created in FOUNDUPS server |

---

## Truth Corrections

1. **Three distinct bots, three tokens**: OBAI, 0102, and antifaFM are separate Discord applications with separate OAuth flows. Do not conflate.

2. **No unified Discord gateway**: Each module manages its own `discord.py` client. No shared connection pool or event router exists.

3. **Science Swarm is embedded, not standalone**: Per `FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md` and `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`, standalone server was rejected. Science Swarm is a category inside the existing FOUNDUPS Discord server.

4. **Intents are module-specific**: 0102 requires Message Content + Server Members (Presence optional). OBAI requires only Message Content. antifaFM requires voice-specific permissions.

---

## Drift Analysis

| Drift Type | Finding |
|------------|---------|
| Token naming | Inconsistent: `OBAI_BOT` vs `DISCORD_0102_BOT_TOKEN` vs `ANTIFAFM_DISCORD_BOT_TOKEN` |
| Guild filtering | OBAI has none (responds anywhere); 0102 and antifaFM filter by env var |
| Test coverage | OBAI: 26 tests; antifaFM: 6 tests; 0102/moltbot: extensive TestModLog exists |
| Operator runbooks | All three modules have runbooks: OBAI (README), 0102 (DISCORD_OPERATOR_SURFACE.md), antifaFM (README) |

---

## Recommended Next Ops Slice

**Priority**: Create Science Swarm embedded category channels in FOUNDUPS Discord

**Rationale**: All three bots have code-verified or live-verified surfaces with runbooks. The remaining gap is the Science Swarm embedded category:
- Category channels not yet created in FOUNDUPS server
- No bot permissions scoped to Science Swarm channels
- Onboarding flow not wired

**Deliverable**: FOUNDUPS server category creation + channel taxonomy per `FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md`

---

## Appendix: Evidence Sources

- `modules/communication/obai_discord_bot/README.md` (runbook lines 59-133)
- `modules/communication/moltbot_bridge/README.md` (operator ref line 71)
- `modules/communication/moltbot_bridge/docs/DISCORD_OPERATOR_SURFACE.md` (Presence optional line 75)
- `modules/communication/moltbot_bridge/tests/TestModLog.md` (extensive test log)
- `modules/platform_integration/antifafm_broadcaster/README.md`
- `modules/platform_integration/antifafm_broadcaster/tests/TestModLog.md`
- `docs/audits/science_swarm_external_foundup/FOUNDUPS_SCIENCE_SWARM_NONCLAIMS.md` (standalone rejected lines 78-85)
- `docs/audits/science_swarm_external_foundup/FOUNDUPS_SCIENCE_SWARM_EMBED_SPEC.md` (embedded decision lines 11-20)
