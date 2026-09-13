# 0102 Session Briefings

Purpose: session-start onboarding briefs for 0102 agents. These are read-once operational digests, not WSP protocol documents.

## Read First (Every Session)

- [System roadmap](../../ROADMAP.md) — current RSI planning authority, completion gates and packet dependencies.
- [ACTIVE_SLICE_LEDGER.md](ACTIVE_SLICE_LEDGER.md) — dated handoffs and the preserved April 21 snapshot. Historical rows do not establish current ownership.
  - Verify the selected source, open changes and current owner before mutation. Record evidence-backed dispositions instead of treating the old snapshot as live state.
- [R02 enforcement map](../roadmaps/R02_WSP_RSI_ENFORCEMENT_MAP.md) — requirement owners, test surfaces and missing operational proof for R00–R25.

## Other Canonical Files
- `SESSION_BRIEFING_2026_02_07.md`
- `YOUTUBE_DOMAIN_AUDIT_PROMPT.md` (audit-first prompt for the YouTube vertical)
- `MAIN_PY_MCP_REMOTE_OPERATIONS_PREFLIGHT_PROMPT_2026-08-17.md` (MCP-only implementation work order for remote 0102 operation)

## SoftProto Prompt Set
- `SOFTPROTO_A_GATEWAY_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_B_MALL_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_C_CONCIERGE_REDDOG_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_D_GUARDRAILS_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_SVELTE_SPIKE_PHASE1_PROMPT_2026-04-01.md`

Usage:
1. Read `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md` first.
2. Read the system roadmap and dated ledger handoffs, then verify the selected slice against current Git/PR and owner evidence.
3. Read the most recent `SESSION_BRIEFING_YYYY_MM_DD.md` if domain context needed.
4. Continue with normal module discovery via HoloIndex and `NAVIGATION.py`.

Conventions:
- One briefing per date (`SESSION_BRIEFING_YYYY_MM_DD.md`).
- Keep content concise and operational.
- Do not duplicate in other locations; reference this folder.
