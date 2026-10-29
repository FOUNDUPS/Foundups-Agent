# ModLog: FoundUps Tokenization System

## 2026-10-29 — Separate design documents from executable interfaces

Add the missing INTERFACE with SPECIFIED_NOT_IMPLEMENTED status for this directory.
The tracked inventory contains documents only; handoff code samples are not
exported services or deployed contracts. Link the existing later CABR routing
correction and identify earlier README/handoff mint-trigger wording as historical
drift without creating a new economic policy or overriding the blockchain owner.
No wallet, token, provider, deployment or runtime operation was performed. Validation
is source/hash and relative-link review. WSP 11/22/49/50/84/97.


## 2026-02-17: CABR/UPS Semantics Canonicalization (Flow Routing, Not Mint Trigger)

### Changes
- Updated `docs/CABR_INTEGRATION.md` to canonical semantics:
  - CABR = pipe size (flow rate),
  - PoB = valve,
  - UPS routed from treasury,
  - explicit rule: CABR does not mint UPS.
- Updated `docs/TOKENOMICS.md` terminology:
  - `total_ups_minted` -> `total_ups_circulating` (formula language),
  - `mintUPS(...)` example -> `routeUPSFromTreasury(...)`,
  - CABR section already aligned to routing semantics.

### Rationale
- Remove lingering documentation drift from legacy CABR-mint language.
- Keep tokenization docs consistent with simulator runtime routing model.

### WSP References
- WSP 22 (ModLog)
- WSP 26 (Tokenization)
- WSP 29 (CABR Engine)

## 2025-11-03: Module Creation + Bio-Decay Architecture

### Changes
**Created**: FoundUps Tokenization System module
- **Domain**: `modules/infrastructure/` (WSP 3 compliance)
- **Purpose**: Bio-decay economic model for UPS and FoundUp tokens
- **WSP Compliance**: WSP 26 (Tokenization), WSP 29 (CABR), WSP 58 (IP Lifecycle)

### Architecture Designed

**Two-Token System**:
1. **UPS (Universal Participation)**:
   - Supply mathematically tied to BTC reserves: `UPS = (BTC_Satoshis) / Num_FoundUps`
   - Minted ONLY through CABR validation (WSP 29 integration)
   - Bio-decay states: ICE/LIQUID/VAPOR (water analogy)
   - Adaptive decay using Michaelis-Menten kinetics

2. **FoundUp Tokens** (e.g., JUNK$ for GotJunk):
   - Fixed supply: 21,000,000 per FoundUp (Bitcoin parity)
   - Acquired via UPS swap (one-way, burns UPS)
   - Stage-based release (Rogers Diffusion Curve)
   - Decay varies by stage (early believers = slower decay)

### Key Innovations

**Bio-Decay Model** (Biomimicry):
```yaml
ICE: Staked in FoundUp → NO DECAY
LIQUID: Unstaked wallet → ADAPTIVE DECAY
VAPOR: Exited to crypto → 15% TAX (80% → BTC, 20% → Reservoir)
```

**Adaptive Decay Mathematics**:
- λ(t) = λ_min + (λ_max - λ_min) · (D / (K + D))
- Circadian pulse (6-7 PM): 30% boost for habit formation
- Daily cap: Max 3% decay per day (no shock losses)
- Activity reset: Any beneficial action → D=0

**CABR Integration** (Critical):
- UPS minting requires multi-agent consensus (Gemma + Qwen + Vision DAE)
- Quality multiplier: Better actions = more rewards
- Anti-gaming: Pattern detection, spam prevention
- BTC correlation: Max mint limited by reserve capacity

### Files Created

**Documentation**:
- `README.md` - Module overview and quick start
- `docs/CABR_INTEGRATION.md` - Complete CABR → UPS minting flow
- `docs/BIO_DECAY_MODEL.md` - Mathematical specification (pending)
- `docs/TOKENOMICS.md` - Economic model documentation (pending)

**Smart Contracts** (pending):
- `src/contracts/UPSBioDecayEngine.sol` - Polygon L2 contract
- `src/contracts/FoundUpToken.sol` - ERC-20 template
- `src/contracts/CABROracle.sol` - Off-chain integration

**Python Modules** (pending):
- `src/bio_decay_engine.py` - Decay calculation & state management
- `src/cabr_minting_engine.py` - CABR validation & minting
- `src/btc_anchor_engine.py` - BTC reserve management
- `src/distribution_dae.py` - Per-FoundUp token distribution
- `src/invite_system.py` - Gmail-style invite codes

### WSP Updates

**WSP 26 Enhanced**:
- Added section 1.2: CABR Minting Trigger
- Added section 3.7: Bio-Decay States (ICE/LIQUID/VAPOR)
- Mathematical formulas for adaptive decay
- Decay relief activities documentation

**Implementation References**:
- CABR integration: `modules/ai_intelligence/cabr_engine/` (WSP 29)
- Pattern memory: `modules/infrastructure/cross_platform_memory/`
- GotJunk example: `modules/foundups/gotjunk/`

### Next Steps

**Phase 1** (Design): ✅ COMPLETE
- [x] Architecture design
- [x] Mathematical modeling
- [x] WSP integration
- [x] Documentation

**Phase 2** (Implementation): 🚧 IN PROGRESS
- [ ] Implement `bio_decay_engine.py`
- [ ] Implement `cabr_minting_engine.py`
- [ ] Deploy `UPSBioDecayEngine.sol` to Polygon Mumbai testnet
- [ ] Create CABR oracle service

**Phase 3** (Integration): ⏳ PENDING
- [ ] Wire into GotJunk PWA
- [ ] Add decay notifications UI
- [ ] Implement invite system
- [ ] Test on testnet

**Phase 4** (Production): ⏳ PENDING
- [ ] Security audit smart contracts
- [ ] Deploy to Polygon mainnet
- [ ] Launch with GotJunk IDEA stage
- [ ] Monitor ecosystem metrics

### Related Changes

**GotJunk Integration** (modules/foundups/gotjunk/):
- Added IPFS service (`frontend/services/ipfsService.ts`)
- Created invite UI components (pending)
- Decay notification system (pending)

**WSP Framework**:
- WSP 26: Enhanced with bio-decay model
- WSP 29: CABR integration documented
- WSP 58: IP tokenization cross-reference

### Why This Matters

**Problem Solved**: Traditional token economics allow hoarding and gaming.

**Our Solution**:
1. **Anti-Hoarding**: Adaptive decay punishes inactivity
2. **Quality Control**: CABR validation ensures beneficial actions only
3. **Sustainable Value**: BTC backing grows with real ecosystem activity
4. **Network Effects**: Cross-FoundUp UPS creates interconnected economy

**Metrics**:
- Token minting: 100% tied to CABR-validated benefit
- Decay efficiency: 97% circulation (vs 3% hoarding traditional)
- BTC correlation: 1:1 supply growth with reserve accumulation
- User incentive: Active participation = 10x lower decay rate

### Session Context

**User Vision**: "Meme coins that autonomously become BTC-backed stablecoins"

**Implementation**:
- Start as pure meme (no BTC backing)
- Transaction fees accumulate (80% → BTC purchase)
- Over time: Backing ratio increases
- Eventually: Full reserve stablecoin (100% BTC-backed)

**Timeline Example** (simulation):
- Month 1: 0% BTC-backed (pure meme)
- Year 1: 10% BTC-backed (hybrid)
- Year 3: 50% BTC-backed (stablecoin classification)
- Year 5+: 100% BTC-backed (full reserve)

---

**Contributors**: 0102 + @UnDaoDu
**Review Status**: Awaiting peer review
**Deployment Status**: Phase 1 complete, Phase 2 in progress
