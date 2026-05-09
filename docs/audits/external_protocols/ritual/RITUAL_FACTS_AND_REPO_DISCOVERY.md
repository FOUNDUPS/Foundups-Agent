# Ritual Facts and Repo Discovery Audit

**Audit Date**: 2026-05-09  
**Slice**: RITUAL_FACTS_AND_REPO_DISCOVERY_PHASE1  
**Worker**: W2  
**WSP References**: WSP 97 (Truth), WSP 15 (Priority), WSP 50 (Pre-Action)

---

## 1. Verified Facts

### Company Identity
- **Official Name**: Ritual (also: Ritual Foundation, Ritual Chain)
- **Website**: https://ritual.net, https://ritualfoundation.org
- **Description**: Open, modular, sovereign execution layer for AI on blockchain
- **Tagline**: "The world's sovereign chain for AI"

### Funding (VERIFIED)
| Round | Amount | Date | Lead | Status |
|-------|--------|------|------|--------|
| Series A | $25M | November 8, 2023 | Archetype | CONFIRMED |
| Follow-on | "Multimillion" | April 2024 | Polychain | CONFIRMED |

### Investors (VERIFIED from Archetype announcement + Ritual blog)
**Institutional**:
- Archetype (lead)
- Polychain Capital (follow-on)
- Accomplice
- Robot Ventures
- dao5
- Accel
- Dialectic
- Anagram
- Avra
- Hypersphere

**Angels (named)**:
- Balaji Srinivasan
- Nicola Greco
- Chase Lochmiller
- DC Builder
- Keone Hon
- Sergey Gorbunov
- Georgios Vlachos
- Kevin Pang
- Daniel Shorr
- Ryan Cao

### Founding Team (VERIFIED)
- **Niraj Pant** - Co-founder (ex-GP/Head of Investments at Polychain)
- **Akilesh Potti** - Co-founder (ex-Partner at Polychain, ML expertise from Palantir)
- Team size: ~27 employees (as of Jan 2026 per Tracxn)

### Advisors (VERIFIED from Ritual blog)
- **Illia Polosukhin** - NEAR Protocol Co-Founder, Transformers Co-Creator
- **Sreeram Kannan** - EigenLayer Founder, UW CS Associate Professor
- **Tarun Chitra** - Gauntlet Founder/CEO, Robot Ventures GP
- **Arthur Hayes** - BitMEX Co-founder (mentioned in press)

### Network Status (VERIFIED)
- **Testnet**: LIVE (launched December 2025)
- **Mainnet**: NOT YET (no confirmed launch date)
- **Chain ID**: 1979
- **Block time**: ~350ms
- **RPC**: rpc.ritualfoundation.org
- **Explorer**: explorer.ritualfoundation.org

---

## 2. Corrected / Rejected Prior Claims

### Prior Claim: "$25M Series A led by Archetype with participation from Polychain..."
**STATUS**: PARTIALLY INCORRECT

**Correction**: Polychain was NOT part of the original Series A. Polychain joined in a *separate* follow-on round in April 2024, described as a "multimillion-dollar" top-up investment. The original $25M Series A (Nov 2023) was led by Archetype with the other named investors.

### Prior Claim: "8,000+ independent Infernet nodes"
**STATUS**: UNVERIFIED - Marketing claim

This figure appears in marketing materials but cannot be independently verified. No on-chain data source provided.

---

## 3. Official Sources

### Primary Sources Used
| Source | URL | Type |
|--------|-----|------|
| Ritual Official Site | https://ritual.net | Primary |
| Ritual Foundation Docs | https://docs.ritualfoundation.org | Primary |
| Archetype Investment Announcement | https://www.archetype.fund/media/announcing-our-investment-in-ritual | Investor |
| Ritual Blog - Introducing Ritual | https://ritual.net/blog/introducing-ritual | Primary |
| CoinDesk - Polychain Investment | https://www.coindesk.com/business/2024/04/04/crypto-vc-firm-polychain-tops-up-ai-platform-rituals-25m-funding-round-with-multimillion-dollar-investment | Press |
| The Block - Testnet Launch | https://www.theblock.co/post/327108/decentralized-ai-project-ritual-launches-testnet-to-bring-ai-onchain | Press |
| Tracxn Company Profile | https://tracxn.com/d/companies/ritual/__0Q3mZKBw8d-g73u3fOI3D2G1WJjfe2-YQmC8tRMFHKk | Data |

---

## 4. GitHub Organization and Repos

### GitHub Organizations Identified

| Organization | URL | Relationship | Status |
|--------------|-----|--------------|--------|
| ritual-net | https://github.com/ritual-net | Original Infernet repos | **REPOS NOW PRIVATE/UNAVAILABLE** |
| ritual-foundation | https://github.com/ritual-foundation | Foundation repos | ACTIVE (1 public repo) |
| ritual | https://github.com/ritual | Unrelated (e-commerce company) | N/A |

### Critical Finding: ritual-net Repos No Longer Public

**Discovery**: As of 2026-05-09, the `ritual-net` GitHub organization returns:
- Organization page: "0 public repositories"
- Direct API calls to repos like `infernet-node`: 404 Not Found
- WebFetch to repo pages: 404

**Prior State (per search index/cache)**:
The following repos *were* public and indexed by search engines:
- `ritual-net/infernet-node` - Off-chain client for compute workloads
- `ritual-net/infernet-ml` - ML library (archived June 2024, moved to monorepo)
- `ritual-net/infernet-container-starter` - Deployment examples
- `ritual-net/infernet-router` - REST server for routing requests

**Possible Explanations**:
1. Repos moved to private ahead of mainnet launch
2. Consolidation into different org or monorepo
3. Security/IP protection measures

---

## 5. Repo Maturity Table

### Currently Accessible Repos

| Repo | Org | Stars | Forks | Issues | License | Last Push | Language | Status |
|------|-----|-------|-------|--------|---------|-----------|----------|--------|
| ritual-dapp-skills | ritual-foundation | 16 | 8 | 4 | BSD-3-Clause-Clear | 2026-04-24 | HTML | ACTIVE |

### Historical Repos (Now Inaccessible)

| Repo | Last Known Status | Notes |
|------|------------------|-------|
| ritual-net/infernet-node | WAS PUBLIC | Core node implementation, search indexed but 404 now |
| ritual-net/infernet-ml | ARCHIVED (Jun 2024) | Moved to Infernet Monorepo |
| ritual-net/infernet-container-starter | WAS PUBLIC | Deployment examples |
| ritual-net/infernet-router | WAS PUBLIC | REST routing server |

### Maturity Assessment

**Overall Code Maturity**: CANNOT FULLY ASSESS

- Only 1 public repo currently accessible
- Historical repos show professional structure (releases, CI/CD, docs)
- Archived repo pattern (infernet-ml) shows code consolidation practice
- Private repos prevent independent code review

---

## 6. Unsupported Claims

The following claims from prior research context CANNOT be verified:

| Claim | Status | Reason |
|-------|--------|--------|
| "8,000+ independent Infernet nodes" | UNVERIFIED | Marketing figure, no on-chain verification |
| Specific repo code quality | CANNOT ASSESS | Repos now private |
| Production readiness | CANNOT ASSESS | No mainnet, repos inaccessible |
| Specific technical implementation details | PARTIALLY VERIFIED | Docs exist but code not reviewable |

---

## 7. Open Questions

### Technical
1. **Why are ritual-net repos now private?** No announcement found.
2. **Where is the Infernet Monorepo?** Referenced as destination for infernet-ml but not discoverable.
3. **What is the mainnet launch timeline?** No confirmed date.

### Architecture Fit (for pAVS evaluation)
1. Does Ritual's TEE-EOVMT model align with WSP verification requirements?
2. Can Ritual's async execution model integrate with FoundUp CABR gates?
3. What is the actual node operator economics vs. stated claims?

### Due Diligence
1. Have ritual-net repos been audited by third parties?
2. What is the token distribution model (if any)?
3. Is the testnet permissioned or permissionless?

---

## WSP 97 Truth Boundary Note

**Capital Signal vs. Protocol Fit**:
Ritual has strong investor backing (Archetype, Polychain, Accel, angels like Balaji). However:

- Strong funding does NOT prove technical architecture fit
- Advisor quality (Illia, Sreeram, Tarun) suggests credibility but not integration compatibility
- Private repos prevent independent technical verification
- Marketing claims (8,000+ nodes) remain unverified

**Per WSP 97**: Claims about Ritual's fitness for FoundUps integration MUST be verified through:
1. Published interface specifications (available via docs)
2. Open source code review (BLOCKED - repos private)
3. Testnet operational verification (POSSIBLE)
4. Economic model alignment (REQUIRES DEEPER ANALYSIS)

---

## Summary

| Category | Status |
|----------|--------|
| Funding Claims | VERIFIED (with Polychain timing correction) |
| Team/Advisor Claims | VERIFIED |
| Investor List | VERIFIED |
| Testnet Status | VERIFIED (LIVE) |
| Mainnet Status | NOT YET LAUNCHED |
| GitHub Repos | MOSTLY INACCESSIBLE (1 public repo) |
| Technical Claims | PARTIALLY VERIFIABLE (docs only, no code access) |
| Node Count Claims | UNVERIFIED |

---

*Audit performed by Worker W2 under WSP 97 truth boundaries.*
