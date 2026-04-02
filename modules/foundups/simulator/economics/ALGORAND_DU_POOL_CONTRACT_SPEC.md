# Algorand Du Pool Contract Specification

**Version**: 1.0.0
**Status**: SPEC (no implementation yet)
**Date**: 2026-03-31
**Source of Truth**: `modules/foundups/simulator/economics/pool_distribution.py`

---

## 1. Overview

This document specifies how the Du pool distribution mechanics map to an Algorand smart contract. The simulator implementation in `pool_distribution.py` and `channel_partner_pool.py` serves as the canonical economic source of truth.

### 1.1 Scope

**In scope:**
- BTC staker weighted allocation
- Staker hurdle state machine
- Post-hurdle rate reduction
- Withheld conservation accounting
- Channel partner registry and equal split
- Mainnet genesis closure semantics

**Out of scope:**
- I_i investor bonding curve (separate lane in `investor_staking.py`)
- Un/Dao pool mechanics (active participation, not passive)
- Network drip and fund pool mechanics
- PyTeal implementation (future slice)

### 1.2 Why Algorand

Algorand is selected as Layer 1 for Du pool accounting because:

1. **Pure Proof-of-Stake**: Aligns with BTC staker participation model
2. **Falcon-1024 signatures**: Quantum-resistant cryptography
3. **Instant finality**: No reorg risk for distribution accounting
4. **Low fees**: Enables micro-distributions without fee erosion
5. **AVM storage model**: Global/local/box state maps well to staker positions
6. **Atomic transactions**: Enables conservation-preserving batch distributions

---

## 2. Simulator-to-Contract Mapping

### 2.1 Constants

| Simulator Constant | Value | Contract Mapping |
|-------------------|-------|------------------|
| `STAKE_WEIGHT_EXPONENT` | 1.5 | Global state: `weight_exponent` (fixed-point) |
| `STAKER_HURDLE_TARGET_MULTIPLE` | 10.0 | Global state: `hurdle_multiple` (fixed-point) |
| `STAKER_POST_HURDLE_RATE_FACTOR` | 0.0526 | Global state: `post_hurdle_rate_bps` (526 bps) |
| `UPS_TO_BTC_RATE` | 0.00001 | Global state: `ups_to_sats` (1000 sats/UPS) |
| `CHANNEL_PARTNER_CAP` | 21 | Global state: `partner_cap` |
| `CHANNEL_PARTNER_PASSIVE_SHARE` | 0.50 | Global state: `partner_share_bps` (5000 bps) |

### 2.2 Enums

| Simulator Enum | Values | Contract Mapping |
|---------------|--------|------------------|
| `StakerHurdleState.PRE_HURDLE` | 0 | Local state: `hurdle_state = 0` |
| `StakerHurdleState.HURDLE_MET` | 1 | Local state: `hurdle_state = 1` |
| `StakerHurdleState.POST_HURDLE_LOCKED` | 2 | Local state: `hurdle_state = 2` |
| `RegistryState.OPEN` | 0 | Global state: `registry_closed = 0` |
| `RegistryState.CLOSED` | 1 | Global state: `registry_closed = 1` |

### 2.3 Functions

| Simulator Function | Contract Method | Notes |
|-------------------|-----------------|-------|
| `btc_stake_weight(stake, exp)` | `compute_weight(stake)` | Fixed-point math required |
| `calculate_weighted_share(stake, total, pool)` | `compute_share(staker_addr)` | Uses stored total weight |
| `distribute_weighted_staker_pool(stakes, pool)` | `distribute_epoch(epoch, pool_amount)` | Batch via atomic txn |
| `StakerPosition.record_distribution_btc()` | `record_distribution(staker_addr, amount)` | Updates local state |
| `ChannelPartnerPool.register_partner()` | `register_partner(partner_addr)` | Pre-genesis only |
| `ChannelPartnerPool.close_on_mainnet_genesis()` | `close_registry(genesis_event_id)` | Permanent, one-time |
| `ChannelPartnerPool.distribute_epoch()` | `distribute_partner_epoch(epoch, pool_amount)` | Equal split |

---

## 3. State Schema

### 3.1 Global State

| Key | Type | Description |
|-----|------|-------------|
| `epoch_index` | uint64 | Current epoch number |
| `total_weighted_stake` | uint64 | Sum of all staker weights (fixed-point, 6 decimals) |
| `staker_count` | uint64 | Number of registered stakers |
| `partner_count` | uint64 | Number of registered channel partners |
| `partner_cap` | uint64 | Maximum channel partners (21) |
| `registry_closed` | uint64 | 0 = open, 1 = closed at genesis |
| `genesis_event_id` | bytes[32] | Event ID that triggered closure |
| `genesis_timestamp` | uint64 | Unix timestamp of closure |
| `genesis_foundup_id` | bytes[32] | FoundUp ID at closure |
| `weight_exponent_num` | uint64 | Exponent numerator (15 for 1.5) |
| `weight_exponent_denom` | uint64 | Exponent denominator (10 for 1.5) |
| `hurdle_multiple` | uint64 | Hurdle target (10) |
| `post_hurdle_rate_bps` | uint64 | Post-hurdle rate in basis points (526) |
| `cumulative_du_distributed` | uint64 | Total Du distributed all epochs |
| `cumulative_du_withheld` | uint64 | Total withheld due to post-hurdle |
| `cumulative_partner_distributed` | uint64 | Total partner distributions |

### 3.2 Local State (Per-Staker)

Each staker opts into the contract and has local state:

| Key | Type | Description |
|-----|------|-------------|
| `original_stake_sats` | uint64 | Initial BTC stake in satoshis |
| `stake_timestamp` | uint64 | Unix timestamp when staked |
| `cumulative_dist_sats` | uint64 | Cumulative distributions in sats |
| `hurdle_state` | uint64 | 0=PRE, 1=MET, 2=LOCKED |
| `hurdle_locked_epoch` | uint64 | Epoch when lock triggered (0 if not locked) |
| `hurdle_locked_at_sats` | uint64 | Distribution level when locked |
| `cached_weight` | uint64 | Pre-computed weight (updated on stake change) |

### 3.3 Box Storage (Channel Partners)

Channel partners stored in boxes for unbounded registry:

| Box Key | Content | Description |
|---------|---------|-------------|
| `partner:{addr}` | `ChannelPartnerRecord` | Partner registration data |

**ChannelPartnerRecord structure:**
```
offset 0:  partner_id (bytes[32])
offset 32: display_name (bytes[64])
offset 96: channel_url (bytes[128])
offset 224: registered_at (uint64)
offset 232: cumulative_allocated (uint64)
offset 240: epochs_participated (uint64)
```

---

## 4. Method Specifications

### 4.1 Staker Methods

#### `register_staker(stake_sats: uint64)`
Registers a new BTC staker.

**Preconditions:**
- Caller has not already registered
- `stake_sats > 0`
- Caller has sufficient BTC in reserve contract

**Effects:**
- Creates local state for caller
- Sets `original_stake_sats = stake_sats`
- Computes and stores `cached_weight`
- Updates `total_weighted_stake` in global state
- Increments `staker_count`

**Returns:** void (success) or fails

---

#### `compute_weight(stake_sats: uint64) -> uint64`
Computes weighted stake using `stake^1.5` formula.

**Algorithm (fixed-point):**
```
// stake^1.5 = stake * sqrt(stake)
// Using integer approximation:
weight = stake_sats * isqrt(stake_sats) / SCALE_FACTOR
```

**Returns:** Weight in fixed-point units (6 decimal places)

---

#### `compute_share(staker_addr: address, pool_amount: uint64) -> uint64`
Computes a staker's share of the distribution pool.

**Algorithm:**
```
weight = local_state[staker_addr].cached_weight
total_weight = global_state.total_weighted_stake
rate_factor = 10000  // 100% in bps

if local_state[staker_addr].hurdle_state == 2:  // POST_HURDLE_LOCKED
    rate_factor = global_state.post_hurdle_rate_bps  // 526 bps

share = (weight * pool_amount * rate_factor) / (total_weight * 10000)
```

**Returns:** Share amount in microAlgo or token units

---

#### `record_distribution(staker_addr: address, amount_sats: uint64)`
Records a distribution and checks hurdle transition.

**Preconditions:**
- Caller is contract itself (inner call) or authorized distributor
- `amount_sats > 0`

**Effects:**
1. Add `amount_sats` to `cumulative_dist_sats`
2. Compute hurdle target: `target = original_stake_sats * hurdle_multiple`
3. If `cumulative_dist_sats >= target` and `hurdle_state != 2`:
   - Set `hurdle_state = 2` (POST_HURDLE_LOCKED)
   - Set `hurdle_locked_epoch = current_epoch`
   - Set `hurdle_locked_at_sats = cumulative_dist_sats`

**Returns:** New hurdle state (0, 1, or 2)

---

#### `distribute_epoch(epoch: uint64, pool_amount: uint64)`
Distributes Du pool to all stakers for an epoch.

**Preconditions:**
- Caller is authorized epoch distributor
- `epoch > global_state.epoch_index` (no double-distribution)

**Effects (atomic group):**
1. For each staker with local state:
   - Compute pre-reduction share
   - Apply rate factor based on hurdle state
   - Compute withheld amount
   - Record distribution to staker
   - Accumulate actual distributed
   - Accumulate withheld
2. Update `cumulative_du_distributed`
3. Update `cumulative_du_withheld`
4. Update `epoch_index`

**Conservation invariant:**
```
pre_reduction_total == actual_distributed + withheld
```

**Returns:** `(actual_distributed, withheld)`

---

### 4.2 Channel Partner Methods

#### `register_partner(partner_addr: address, display_name: bytes, channel_url: bytes)`
Registers a channel partner before genesis.

**Preconditions:**
- `registry_closed == 0`
- `partner_count < partner_cap`
- Partner not already registered (no box exists)

**Effects:**
- Create box `partner:{partner_addr}` with registration data
- Increment `partner_count`

**Returns:** `(success: bool, message: bytes)`

---

#### `close_registry_on_genesis(event_id: bytes, timestamp: uint64, foundup_id: bytes)`
Permanently closes the channel partner registry.

**Preconditions:**
- `registry_closed == 0`
- Caller is authorized genesis trigger

**Effects:**
- Set `registry_closed = 1`
- Store `genesis_event_id`, `genesis_timestamp`, `genesis_foundup_id`

**Returns:** success bool (false if already closed)

---

#### `distribute_partner_epoch(epoch: uint64, pool_amount: uint64)`
Distributes to channel partners using equal split.

**Preconditions:**
- Caller is authorized distributor
- `partner_count > 0`

**Algorithm:**
```
per_partner = pool_amount / partner_count
for each partner box:
    transfer per_partner to partner_addr
    update partner.cumulative_allocated
    update partner.epochs_participated
```

**Returns:** `per_partner_amount`

---

## 5. Algorand-Specific Notes

### 5.1 State Location Decisions

| Data | Storage | Rationale |
|------|---------|-----------|
| Global constants | Global state | Rarely changes, needs contract-wide access |
| Staker positions | Local state | Per-account, opt-in model, ~248 bytes |
| Channel partners | Box storage | Unbounded registry (up to 21), survives opt-out |
| Distribution history | Off-chain | Too large for on-chain; use indexer |
| Epoch orchestration | Off-chain | Trigger contract from authorized backend |

### 5.2 Fixed-Point Arithmetic

Algorand AVM uses uint64 integers. All decimal values must use fixed-point:

| Value | Representation | Scale |
|-------|---------------|-------|
| BTC amounts | Satoshis (uint64) | 1 BTC = 100,000,000 sats |
| Weights | Fixed-point (uint64) | 6 decimal places (1.0 = 1,000,000) |
| Percentages | Basis points (uint64) | 100% = 10,000 bps |
| Rate factors | Basis points | 5.26% = 526 bps |

**sqrt approximation:**
```python
def isqrt(n: uint64) -> uint64:
    """Integer square root using Newton's method."""
    if n == 0:
        return 0
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    return x
```

### 5.3 Off-Chain Requirements

These operations require off-chain orchestration:

| Operation | Why Off-Chain |
|-----------|---------------|
| Epoch triggering | Scheduled time-based, not event-driven |
| Batch distribution | Must iterate all stakers; AVM opcode limits |
| Weight recomputation | Expensive; batch on stake changes |
| BTC reserve verification | Cross-chain; requires oracle/bridge |
| UPS conversion | Requires external price/rate oracle |

### 5.4 Atomic Transaction Groups

Epoch distribution should use atomic groups:

```
Group {
  Txn 1: Call distribute_epoch(epoch, pool_amount)
  Txn 2-N: Inner calls to record_distribution() for each staker
  Txn N+1: Update global state totals
}
```

If any transaction fails, entire group reverts (conservation preserved).

---

## 6. Invariants

### 6.1 Weighted Share Determinism

```
Given identical inputs (stakes, total_weight, pool_amount):
  compute_share() MUST return identical output

No randomness, no time-dependency, no external oracle in share computation.
```

### 6.2 Post-Hurdle Permanence

```
Once hurdle_state == 2 (POST_HURDLE_LOCKED):
  - State NEVER reverts to 0 or 1
  - Additional distributions do NOT change state
  - hurdle_locked_epoch and hurdle_locked_at_sats are immutable
```

### 6.3 Equal-Split Partner Distribution

```
For N registered partners and pool P:
  each_partner_receives == P / N (integer division)

No weighting, no preference, no variable shares.
```

### 6.4 Conservation

```
For every epoch distribution:
  actual_distributed + withheld == pre_compression_allocation

Where:
  pre_compression_allocation = sum of all pre-reduction shares
  actual_distributed = sum of all post-reduction shares
  withheld = sum of (pre - post) for POST_HURDLE_LOCKED stakers
```

### 6.5 Registry Closure Permanence

```
Once registry_closed == 1:
  - register_partner() MUST fail
  - close_registry_on_genesis() MUST return false
  - genesis_event_id, genesis_timestamp, genesis_foundup_id are immutable
```

### 6.6 Lane Separation

```
Du pool contract MUST NOT:
  - Reference I_i investor state
  - Share hurdle tracking with investor_staking.py lane
  - Allow cross-contamination of distribution accounting

Du lane and I_i lane are economically and contractually separate.
```

---

## 7. Future Work (Out of Scope)

| Item | Notes |
|------|-------|
| PyTeal implementation | Slice 6+ |
| Beaker app scaffold | After spec freeze |
| Testnet deployment | After implementation |
| BTC bridge/oracle | Separate infrastructure concern |
| Mainnet genesis trigger | Operational, not contract spec |
| Gas/fee optimization | Implementation phase |
| Audit preparation | Post-implementation |

---

## 8. References

### 8.1 Simulator Source Files

| File | Purpose |
|------|---------|
| `pool_distribution.py` | Core Du pool mechanics, weighted stake, hurdle state |
| `channel_partner_pool.py` | Channel partner registry and distribution |
| `test_staker_hurdle_state.py` | Hurdle state machine test coverage |
| `test_weighted_stake_allocation.py` | Weighted allocation test coverage |
| `test_channel_partner_pool.py` | Partner pool test coverage |

### 8.2 Architecture Decisions

| Decision | Reference |
|----------|-----------|
| Algorand as Layer 1 | CTO decision 2026-03-11 (memory/MEMORY.md) |
| BTC Hotel California | Layer 0 reserve model |
| Du 4% partition | WSP 97 Slice 1 |
| 10x hurdle multiple | WSP 97 Slice 4 |
| 5.26% post-hurdle rate | Matches I_i lane ratio (0.64/12.16) |

---

*Spec document generated per WSP 97 Slice 5: algorand_du_pool_contract_spec*
