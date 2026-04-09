# Discord Operating Surface Audit — Science Swarm Phase 1

**Worker**: BE  
**Date**: 2026-04-09  
**Scope**: All Discord-facing modules in Foundups-Agent codebase  

---

## Surface Table

| Component | Status | Evidence | Operator Dependency | Next Gap |
|-----------|--------|----------|---------------------|----------|
| **OBAI Discord Bot** | CODE-VERIFIED | 26 tests pass; README documents bot ID `1218413610750423061`, guild `412646632992014336` | Token `OBAI_BOT` required; no guild filter (responds anywhere invited) | No live verification runbook; missing operator smoke test |
| **0102/OpenClaw Bot** | LIVE-VERIFIED | `DISCORD_OPERATOR_SURFACE.md` verified 2026-04-09; App ID `839968873851387944`; OAuth fix documented | Token `DISCORD_0102_BOT_TOKEN`; requires Message Content + Server Members + Presence intents | Webhook lane spec-only (not deployed) |
| **antifaFM Radio Bot** | CODE-VERIFIED | 6 Discord voice tests pass; README V3.3.2 documents live guild verification | Token `ANTIFAFM_DISCORD_BOT_TOKEN`; env gate `ANTIFAFM_DISCORD_VOICE_ENABLED` | Requires manual join to voice channel; no auto-reconnect on disconnect |
| **Science Swarm Discord** | PLANNING-ONLY | Worker I audit 2026-04-03: "Discord is planning-only, not instantiated" | No server exists; no bot deployed | Server creation, channel taxonomy, bot invitation |

---

## Truth Corrections

1. **Three distinct bots, three tokens**: OBAI, 0102, and antifaFM are separate Discord applications with separate OAuth flows. Do not conflate.

2. **No unified Discord gateway**: Each module manages its own `discord.py` client. No shared connection pool or event router exists.

3. **Science Swarm Discord does not exist**: Prior Worker I audit confirmed this is spec-only. No guild ID, no channels, no deployed bots.

4. **Intents are module-specific**: 0102 requires privileged intents (Message Content, Server Members, Presence). OBAI and antifaFM have lighter requirements.

---

## Drift Analysis

| Drift Type | Finding |
|------------|---------|
| Token naming | Inconsistent: `OBAI_BOT` vs `DISCORD_0102_BOT_TOKEN` vs `ANTIFAFM_DISCORD_BOT_TOKEN` |
| Guild filtering | OBAI has none (responds anywhere); 0102 and antifaFM filter by env var |
| Test coverage | OBAI: 26 tests; antifaFM: 6 tests; 0102/moltbot: unknown (no TestModLog found) |
| Operator runbooks | Only antifaFM has verification runbook with failure modes table |

---

## Recommended Next Ops Slice

**Priority**: Create moltbot_bridge operator runbook + TestModLog

**Rationale**: 0102/OpenClaw is live-verified but lacks:
- `tests/TestModLog.md` (test evolution tracking)
- Operator smoke test procedure in README
- Failure modes table matching antifaFM pattern

**Deliverable**: `modules/communication/moltbot_bridge/tests/TestModLog.md` + README operator section

---

## Appendix: Evidence Sources

- `modules/communication/obai_discord_bot/README.md`
- `modules/communication/moltbot_bridge/README.md`
- `modules/communication/moltbot_bridge/docs/DISCORD_OPERATOR_SURFACE.md`
- `modules/platform_integration/antifafm_broadcaster/README.md`
- `modules/platform_integration/antifafm_broadcaster/tests/TestModLog.md`
- `docs/audits/science_swarm_external_foundup/DISCORD_OPERATING_SURFACE_AUDIT.md` (Worker I, 2026-04-03)
- `public/member/tests/TestModLog.md` (test log pattern reference)
