# pAVS Developer Vocabulary

**Purpose**: Onboard new developers to FoundUps/pAVS terminology via HoloIndex-searchable vocabulary.

## Quick Start

Use the current owner-query instructions in [CLAUDE.md](../../CLAUDE.md)
with a vocabulary query such as `what is F_i` or `012 vs 0102`. Accept
generation-bound results only when CURRENT/no-gap; a failed query does
not authorize reindexing from the query path.

## Vocabulary Categories

| Category | File | Core Terms |
|----------|------|------------|
| Identity | [IDENTITY.md](IDENTITY.md) | 012, 0102, 0201, qNN, pAVS |
| Economics | [ECONOMICS.md](ECONOMICS.md) | F_i, UPS, CABR, PoB, pools |
| Technical | [TECHNICAL.md](TECHNICAL.md) | WSP, WRE, HoloIndex, MCP, DAE |
| Regulatory | [REGULATORY.md](REGULATORY.md) | Distribution ratio, protocol participation |
| Agents | [AGENTS.md](AGENTS.md) | Qwen, Gemma, Opus, Sonnet, Haiku |

## Onboarding Checklist

- [ ] Read [IDENTITY.md](IDENTITY.md) - understand 012/0102/0201 state model
- [ ] Read [ECONOMICS.md](ECONOMICS.md) - understand F_i/UPS token flow
- [ ] Read [TECHNICAL.md](TECHNICAL.md) - understand WSP/WRE architecture
- [ ] Query `CABR` through the current [owner-query instructions](../../CLAUDE.md) and inspect freshness
- [ ] Read current [operating instructions](../../CLAUDE.md); the [onboarding runbook](../SUPERADMIN_ONBOARDING.md) is historical

## HoloIndex Integration

Vocabulary is indexed in `memory/vocabulary/pavs_core.json` and searchable via:
- `vocabulary_indexer.py` - indexes proper nouns + definitions
- `search_vocabulary()` - semantic search for term lookups

## WSP Compliance

- WSP 72: Module Independence (vocabulary is standalone)
- WSP 57: Naming Convention (consistent term definitions)
- WSP 22: ModLog (vocabulary updates logged)

---
*Last updated: 2026-02-21*
