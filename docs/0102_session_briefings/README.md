# 0102 Session Briefings

Purpose: session-start onboarding briefs for 0102 agents. These are read-once operational digests, not WSP protocol documents.

## Read First (Every Session)

- **`ACTIVE_SLICE_LEDGER.md`** — live slice state: closed, open, blocked, forbidden duplicates, next priority
  - Read before any mutation. Update when slices land. 012 is not the state store — this is.

## Other Canonical Files
- `SESSION_BRIEFING_2026_02_07.md`
- `YOUTUBE_DOMAIN_AUDIT_PROMPT.md` (audit-first prompt for the YouTube vertical)

## SoftProto Prompt Set
- `SOFTPROTO_A_GATEWAY_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_B_MALL_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_C_CONCIERGE_REDDOG_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_D_GUARDRAILS_AUDIT_PROMPT_2026-04-01.md`
- `SOFTPROTO_SVELTE_SPIKE_PHASE1_PROMPT_2026-04-01.md`

Usage:
1. Read `WSP_framework/src/WSP_00_Zen_State_Attainment_Protocol.md` first.
2. **Read `ACTIVE_SLICE_LEDGER.md`** — recover repo truth before any work.
3. Read the most recent `SESSION_BRIEFING_YYYY_MM_DD.md` if domain context needed.
4. Continue with normal module discovery via HoloIndex and `NAVIGATION.py`.

Conventions:
- One briefing per date (`SESSION_BRIEFING_YYYY_MM_DD.md`).
- Keep content concise and operational.
- Do not duplicate in other locations; reference this folder.
