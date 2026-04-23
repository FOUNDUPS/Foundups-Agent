# Vote/Ballots FoundUp

Political transparency application tracing attack ad funding with full evidence provenance.

## Purpose

Track money flows in political advertising, especially:
- Attack ad funding chains
- Dark money (501(c)(4)) disclosure gaps
- AIPAC and pro-Israel PAC spending
- Corporate/industry influence
- Entity relationships and shell company networks

## Core Principle

**Where disclosure is absent, output must say: "The public money trail stops here."**

This is a feature, not a bug. Identifying where transparency ends is part of the value.

## Schema Overview

### Node Types

| Node Type | Description |
|-----------|-------------|
| Person | Natural person (not acting as candidate) |
| Candidate | Person running for office |
| Office | Elected position |
| Committee | Campaign committee |
| PAC | Political Action Committee |
| SuperPAC | Independent Expenditure Committee |
| DarkMoneyEntity | 501(c)(4) or non-disclosing org |
| Donor | Individual or entity contributor |
| Expenditure | Money spent on political activity |
| AdCreative | Specific ad/message |
| AttackTheme | Categorized attack messaging |
| IssueAlignment | Policy position tracking |
| LobbyAdvocacy | Lobbying activity linkage |
| IsraelPolicyAlignment | Israel-specific policy positions |
| AIPACLinkage | AIPAC/pro-Israel PAC connections |
| CorporateIndustryLinkage | Industry influence tracking |
| SourceDocument | Source file reference |

### Evidence Status (WSP-97 Compliant)

Every claim MUST have one of these statuses:

| Status | Description |
|--------|-------------|
| VERIFIED | Confirmed by primary source with citation |
| INFERRED | Derived via entity resolution or pattern matching |
| HYPOTHESIS | User-submitted, pending review |
| UNKNOWN | Explicitly unknown - disclosure gap identified |
| RETRACTED | Previously verified but source removed/retracted |

### Edge Requirements

Every edge MUST carry:
- `source` - Citation(s) backing the relationship
- `date` - When the relationship/transaction occurred
- `evidence_type` - Classification of evidence
- `confidence` - Numeric score with justification
- `status` - VERIFIED/INFERRED/HYPOTHESIS label

## Source Classes

1. **Political Ad Libraries** - Google, Meta, TikTok transparency reports
2. **FEC Disclosures** - Federal campaign finance filings
3. **Outside Spending Databases** - OpenSecrets, FollowTheMoney
4. **Committee/PAC Filings** - Official FEC committee reports
5. **Candidate Statements** - Websites, press releases
6. **Watchdog Reports** - CREW, Sunlight, CLC
7. **Investigative Reporting** - NYT, WaPo, ProPublica
8. **User Submissions** - Community tips (UNVERIFIED until reviewed)

## Query Patterns

### Who is attacking candidate X?

```typescript
const query: AttackersQuery = {
  query_type: 'attackers',
  target_candidate_id: 'cand_001',
  include_indirect: true,
  date_range: { start: '2024-01-01', end: '2024-12-31' },
  min_confidence: 0.5
};
```

### What is the funding chain for PAC Y?

```typescript
const query: FundingChainQuery = {
  query_type: 'funding_chain',
  entity_id: 'spac_001',
  max_depth: 5,
  include_inferred: true,
  min_amount: 10000
};
```

Returns chain with `terminus_nodes` where trail ends.

### What AIPAC-linked spending targets candidate X?

```typescript
const query: AIPACSpendingQuery = {
  query_type: 'aipac_spending',
  target_candidate_id: 'cand_001',
  include_aligned_groups: true,
  spending_type: 'oppose',
  date_range: null
};
```

## Confidence Scoring

Base scores by source class:
- FEC Disclosure: 0.95
- Committee Filing: 0.90
- Ad Library: 0.85
- Outside Spending DB: 0.80
- Watchdog Report: 0.75
- Candidate Statement: 0.70
- Investigative Reporting: 0.70
- User Submission: 0.30

Modifiers applied for corroboration, recency, dead links, inference, etc.

## Directory Structure

```
vote_ballots/
  src/
    evidence_graph_schema.ts   # Complete TypeScript types
  adapters/
    fec_adapter.ts            # FEC.gov API integration
    google_ads_adapter.ts     # Google Ad Library
    meta_ads_adapter.ts       # Meta Ad Library
    opensecrets_adapter.ts    # OpenSecrets API
  tests/
    fixtures/
      sample_graph_data.ts    # Test data
  README.md
```

## WSP Compliance

- **WSP-97**: All fields distinguish verified vs inferred vs unknown
- **WSP-50**: Source verification before any claim
- **WSP-22**: ModLog maintained for changes

## Development Status

- [x] Schema design (evidence_graph_schema.ts)
- [x] Test fixtures (sample_graph_data.ts)
- [ ] FEC adapter implementation
- [ ] Ad library adapters
- [ ] Graph database integration
- [ ] Query engine
- [ ] UI components
