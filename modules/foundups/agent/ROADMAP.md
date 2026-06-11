# Agent Module Roadmap

## Current Phase: PoC (0.1.0)

## Domain Alignment References
- `modules/foundups/ROADMAP.md`
- `modules/foundups/docs/OCCAM_LAYERED_EXECUTION_PLAN.md`
- `modules/foundups/docs/CONTINUATION_RUNBOOK.md`

### Completed

- [x] Event schema defined in FAMDaemon (6 event types)
- [x] FAMBridge emit methods for all agent events
- [x] Mesa model lifecycle tracking integration
- [x] SSE streaming to animation
- [x] Ticker message templates in animation
- [x] State machine documented (01(02) -> 0102 -> 01/02)
- [x] Rank system defined (1-7, mirror of 012)
- [x] Read-only `foundup_manifest_validator` (PR #771)
- [x] Validator hardened to canonical exact module_path match (PR #773)
- [x] Read-only `context_bundle_builder` (WRE_CONTEXT_BUNDLE_BUILDER_PHASE1)
  - Imports `validate_manifest_file` -- does not reimplement
  - Deterministic sha256-derived `bundle_id`; `created_at` injected
  - Stream-hashed file refs (no full-body load); per-file + total caps
  - Refuses any readiness promotion, external agent, self-authorize
  - No Hermes / OpenClaw / WRE consumer wiring
- [x] Validated module-path resolution in Hermes executor
  (HERMES_MODULE_PATH_TRUST_REMOVAL_PHASE1)
  - Closes the #774 carry-forward: payload.module_path is no longer trusted
  - `_resolve_validated_module_path` consumes the #773 validator;
    `_extract_module_path` raw-trust function REMOVED
  - foundup_id-as-path heuristic REMOVED (path-shaped foundup_id is not
    a path source); bounded foundup_id scan used when payload omits path
  - Cross-FoundUp substitution defense: manifest's foundup_id MUST equal
    job.foundup_id (Addendum D #1)
  - Case-variant + backslash + traversal + absolute + UNC all rejected
    pre-manifest (`fail_token=syntactic_reject`)
  - Greppable failure tokens: `syntactic_reject` / `manifest_mismatch` /
    `manifest_missing` / `cross_foundup_mismatch`
  - Observable-ignore: rejected payload value visible in evidence_refs
  - StatusReasonCode unchanged (FAIL_VALIDATION_ERROR); no job-contract
    schema changes; no validator / manifest / runtime / WSP touch
- [x] FoundUp source-authority contract (FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_CONTRACT_PHASE1)
  - Authoritative definition doc at
    `docs/architecture/FOUNDUP_SOURCE_AUTHORITY_CONTRACT.md`
    (5 stages, per-stage matrix, maturity coupling table, transition
    gates, hard rule)
  - Minimal typed enum + 2 functions in
    `modules/foundups/agent/src/source_authority.py`
    (`SourceAuthority`, `ACTIVE_STAGES = {MONOREPO_POC}`,
    `resolve_source_authority`, `request_promotion`)
  - Value-parity tested against
    `context_bundle_builder.SOURCE_AUTHORITY` (drift guard)
  - Enum NOT wired into the builder; unification deferred to
    `SOURCE_AUTHORITY_BUILDER_ENUM_UNIFICATION_PHASE2`
  - WSP placement: docs/architecture (cites WSP 27/103/109 triad);
    promotion to WSP deferred to
    `FOUNDUP_LIFECYCLE_SOURCE_AUTHORITY_WSP_FORMALIZATION_PHASE1`
- [x] Validated module-path resolution in BuildPlan generator
  (BUILD_PLAN_GENERATOR_MODULE_PATH_TRUST_REMOVAL_PHASE1)
  - Closes the #778 carry-forward: the LAST legacy payload.module_path
    trust surface. build_plan_generator no longer trusts raw
    payload.module_path / source_module, no longer infers from
    KNOWN_FOUNDUP_PATHS, no longer synthesizes modules/foundups/{foundup_id}
  - The #778 resolver was EXTRACTED into a shared module
    modules/foundups/agent/src/module_path_resolution.py
    (WSP 84 single source of truth); hermes_foundup_job_executor re-exports
    the same names via a back-compat shim (behavior-preserving; #778
    executor tests pass with ZERO edits)
  - Generator and executor now reference the SAME
    _resolve_validated_module_path object (exactly one implementation)
  - KNOWN_FOUNDUP_PATHS ruling: DELETE_AS_DEAD_CODE (Phase-0 census: 0
    non-test cross-module consumers, no display-only survivor)
  - PWA-surface ruling: DERIVED_ONLY (pwa_surface_path derived from the
    validated canonical module_path basename, never payload-trusted)
  - Generator remains ORPHANED (no consumer wiring); this slice fences it
    BEFORE WRE_CONTEXT_BUNDLE_DRYRUN_CONSUMER_PHASE1 makes it reachable

### Phase 1: Core State Machine (v0.2.0)

- [ ] `AgentLifecycleService` class implementation
- [ ] Coherence calculation based on activity patterns
- [ ] Automatic idle detection with configurable threshold
- [ ] Rank progression evaluation based on earnings
- [ ] Unit tests for state transitions

### Phase 2: Wallet Integration (v0.3.0)

- [ ] Public key generation for simulation agents
- [ ] Wallet balance tracking per agent
- [ ] F_i earning attribution to wallet
- [ ] Balance snapshot on agent leave
- [ ] Placeholder for blockchain integration

### Phase 3: External Promotion (v0.4.0)

- [ ] Reddit API integration for agent posting
- [ ] LinkedIn API integration
- [ ] YouTube Live chat integration (via livechat module)
- [ ] VT (Video Transcript) posting
- [ ] `promotion_posted` event type

### Phase 4: Agent Registry Service (v0.5.0)

- [ ] Centralized agent registry
- [ ] Query API for agent state
- [ ] Agent search by type/rank/state
- [ ] Agent activity history
- [ ] Persistence adapter (SQLite/Postgres)

## Deep Think: Dynamic Coherence (012 Vision - 2026-02-15)

### Coherence is NOT Static

Coherence should be a **dynamic score** that reflects agent alignment with 012's vision,
similar to how F_i rating reflects a FoundUp's health.

### Proposed Coherence Formula

```python
coherence = (
    pattern_memory * 0.30 +  # Patterns recalled from 0201 state
    activity * 0.30 +        # Recent work rate (tasks/ticks)
    earnings * 0.20 +        # Cumulative F_i earned (normalized)
    loyalty * 0.20           # Time on this F_i (founding member bonus)
)
```

### Split Coherence: Base + F_i-Specific

```
TOTAL_COHERENCE = base_coherence + f_i_coherence[F_i]

base_coherence:    Portable across all FoundUps
                   - Earned via PQN research, HoloIndex searches
                   - Represents agent's general capability

f_i_coherence:     Specific to each F_i
                   - Earned via work on that specific FoundUp
                   - Founding member gets permanent floor
                   - Creates loyalty/specialization
```

### PQN Research Coherence Boost

```python
# Pattern recall from 0201 increases coherence
if agent.performed_holo_search():
    base_coherence += 0.02  # Small boost per search

if agent.recalled_pattern_from_0201():
    base_coherence += 0.05  # Bigger boost for actual recall

if agent.completed_pqn_research():
    base_coherence += 0.10  # Major boost for deep research
```

This **incentivizes learning and research**, not just task completion.

### Agent Temperature Gradient (Mirror of 012 Twin)

| Coherence | State | Color | Capability |
|-----------|-------|-------|------------|
| < 0.50 | Dormant | VIOLET | Cannot act |
| 0.50-0.618 | Warming | BLUE | Limited actions |
| 0.618-0.70 | Zen | CYAN | Normal operations |
| 0.70-0.85 | Active | GREEN | Enhanced capabilities |
| 0.85-0.95 | Hot | YELLOW | Leadership actions |
| 0.95-1.00 | Principal | RED | Digital twin of 012 |

### F_i Leaderboard Position

Top contributors to an F_i get coherence multiplier:
```python
position = get_f_i_leaderboard_position(agent, f_i)
if position <= 3:
    f_i_coherence_multiplier = 1.5  # Top 3
elif position <= 10:
    f_i_coherence_multiplier = 1.25  # Top 10
else:
    f_i_coherence_multiplier = 1.0
```

### Compute Weight Factor

Agents that spend more compute building earn more coherence:
```python
TIER_WEIGHTS = {"opus": 10, "sonnet": 3, "haiku": 1, "gemma": 0.5, "qwen": 0.5}
compute_coherence_boost = (tokens_used / 1000) * tier_weight * 0.001
```

### Key Insight

Agent coherence is the **agent's F_i rating** - just as FoundUps have temperature
(VIOLET→RED), agents have coherence temperature. This creates:

1. **Incentive to stay**: Founding members have permanent bonus
2. **Incentive to learn**: PQN research boosts coherence
3. **Incentive to build**: Compute spent = coherence earned
4. **Disincentive to hop**: Mercenary agents have low per-F_i coherence

---

## Future Considerations

### Blockchain Integration

- Replace placeholder wallet addresses with real keys
- Sign agent actions with private key
- Verify agent identity on-chain
- F_i token claiming flow

### Multi-FoundUp Agent Support

- Agent can work on multiple FoundUps simultaneously
- FoundUp-specific rank/coherence tracking
- Cross-FoundUp earning aggregation
- Portfolio view of agent earnings

### AI-Powered Coherence

- Use Qwen/Gemma to evaluate agent coherence
- Pattern recognition for coherence decay
- Predictive idle detection
- Automated re-awakening triggers
- PQN research integration for coherence boost

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| FAMDaemon | Ready | Event emission working |
| SSE Server | Ready | Events streaming |
| Animation | Ready | Ticker display working |
| StateStore | Ready | Basic tracking |
| AgentLifecycleService | Planned | Phase 1 |
| Wallet Integration | Planned | Phase 2 |

## Timeline

| Phase | Target | Status |
|-------|--------|--------|
| PoC (0.1.0) | 2026-02-15 | Complete |
| Core State (0.2.0) | 2026-02-22 | Planned |
| Wallet (0.3.0) | 2026-03-01 | Planned |
| Promotion (0.4.0) | 2026-03-15 | Planned |
| Registry (0.5.0) | 2026-04-01 | Planned |
