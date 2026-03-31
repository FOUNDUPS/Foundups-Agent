# p.fMALL State Overlay Contract

**Status**: Architecture specification (first tranche)
**Owner**: 0102
**Slice**: `pfmall_state_overlay_contract`
**WSP References**: WSP 29 (CABR Engine), WSP 97 (Concatenation Gate), WSP 91 (Observability)

---

## 1. Purpose

The state overlay is the **dynamic layer** that augments `foundup_manifest.json` with live lifecycle, health, economics, and activity data. The manifest is static identity; the overlay is live condition.

### 1.1 Why the Manifest is Insufficient

The manifest declares **what a FoundUp is**:
- Identity: name, version, owner
- Contract: tier, capabilities, CABR rules
- Configuration: entry URL, routing prefix, icon

The manifest does NOT declare **how a FoundUp is doing**:
- Is it online right now?
- What is its current CABR score?
- How many agents are active?
- Is the lifecycle progressing or stalled?

### 1.2 Why the Overlay Must Remain Separate

1. **Freshness**: Overlay data has TTL; manifest is versioned and signed
2. **Authority**: Overlay is advisory; manifest is authoritative
3. **Providers**: Overlay may come from SIM, pAVS, or the FoundUp itself
4. **Failure**: Overlay may be stale or unavailable; manifest is cached

---

## 2. Static vs Dynamic Boundary

### 2.1 Static (Manifest Only)

These fields are in `foundup_manifest.json` and NEVER in the overlay:

| Field | Reason |
|-------|--------|
| `foundup_id` | Identity anchor (signed, immutable) |
| `name`, `version` | Identity (version-bumped on change) |
| `description`, `tagline` | Identity (version-bumped on change) |
| `tier` | Declared tier (promotion requires new manifest) |
| `lifecycle_stage` | Declared stage (advancement requires new manifest) |
| `entry_url`, `routing_prefix` | Configuration (signed) |
| `required_subscription_tier` | Access policy (signed) |
| `capabilities`, `agent_routes` | Declared contract (signed) |
| `cabr_contract` | CABR rules (v1_gate, v2_proof, v3_score_min) |
| `owner_id`, `token_symbol` | Identity (immutable) |
| `signature` | Integrity proof |

### 2.2 Dynamic (Overlay Only)

These fields are ONLY in the overlay, never in the manifest:

| Field | Type | Description |
|-------|------|-------------|
| `foundup_id` | string | Key to join with manifest |
| `health_status` | enum | `healthy` \| `degraded` \| `offline` \| `unknown` |
| `availability` | enum | `online` \| `maintenance` \| `suspended` |
| `cabr_score` | float | Live CABR V3 score (0.0-1.0) |
| `lifecycle_progress` | object | Observed stage advancement metrics |
| `agent_activity` | object | Agent count and recent action summary |
| `reserve_summary` | object | BTC reserve health (abstracted) |
| `last_updated_at` | ISO 8601 | When overlay was last refreshed |
| `state_provider` | string | Provider identifier |
| `freshness_ttl` | int | Seconds until this overlay is considered stale |

---

## 3. Canonical Overlay Schema

### 3.1 FoundUpStateOverlay

```json
{
  "$schema": "https://foundups.org/schemas/state-overlay/v1.json",

  "foundup_id": "string",

  "health_status": "healthy | degraded | offline | unknown",
  "availability": "online | maintenance | suspended",

  "cabr_score": 0.0,
  "cabr_trend": "rising | stable | falling | unknown",

  "lifecycle_progress": {
    "declared_stage": "string (from manifest)",
    "observed_stage": "string (from provider)",
    "tasks_completed": 0,
    "milestones_published": 0,
    "days_in_stage": 0
  },

  "agent_activity": {
    "active_agents": 0,
    "tasks_in_flight": 0,
    "last_agent_action": "string (ISO 8601) | null"
  },

  "reserve_summary": {
    "reserve_health": "strong | adequate | low | critical | unknown",
    "reserve_trend": "growing | stable | shrinking | unknown"
  },

  "last_updated_at": "string (ISO 8601)",
  "state_provider": "string",
  "freshness_ttl": 300
}
```

### 3.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `foundup_id` | string | YES | Must match manifest `foundup_id` |
| `health_status` | enum | YES | Overall health signal |
| `availability` | enum | YES | Whether FoundUp is accepting traffic |
| `cabr_score` | float | YES | Live CABR V3 score (0.0-1.0) |
| `cabr_trend` | enum | NO | Score trajectory over last epoch |
| `lifecycle_progress` | object | YES | Stage advancement metrics |
| `agent_activity` | object | YES | Agent fleet summary |
| `reserve_summary` | object | NO | BTC reserve health (abstracted) |
| `last_updated_at` | ISO 8601 | YES | Provider timestamp |
| `state_provider` | string | YES | Provider identifier |
| `freshness_ttl` | int | YES | Seconds until stale |

### 3.3 Health Status Values

| Value | Meaning | Shell Behavior |
|-------|---------|----------------|
| `healthy` | All systems nominal | Green badge |
| `degraded` | Partial functionality | Yellow badge |
| `offline` | FoundUp unavailable | Red badge, warn on load |
| `unknown` | Provider cannot determine | Gray badge |

### 3.4 Availability Values

| Value | Meaning | Shell Behavior |
|-------|---------|----------------|
| `online` | Accepting traffic | Normal load |
| `maintenance` | Planned downtime | Show notice, allow load |
| `suspended` | Administrative hold | Block load, show reason |

---

## 4. Provider Interface

### 4.1 Abstract Provider Contract

Any state provider must implement:

```python
class StateOverlayProvider:
    """Abstract state overlay provider."""

    def get_foundup_state(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        """Get current state for one FoundUp.

        Returns None if FoundUp unknown or state unavailable.
        """
        raise NotImplementedError

    def list_foundup_states(self) -> List[FoundUpStateOverlay]:
        """Get current state for all known FoundUps.

        Returns empty list if no state available.
        """
        raise NotImplementedError

    def get_state_freshness(self, foundup_id: str) -> Optional[int]:
        """Get seconds until state is considered stale.

        Returns None if FoundUp unknown.
        Returns 0 if already stale.
        """
        raise NotImplementedError

    @property
    def provider_id(self) -> str:
        """Unique identifier for this provider."""
        raise NotImplementedError
```

### 4.2 Provider Implementations

| Provider | Context | Status |
|----------|---------|--------|
| `simulator` | PoC / development | Available now |
| `pavs_lifecycle` | Production lifecycle service | Future |
| `foundup_status_endpoint` | Externalized FoundUp self-report | Future |
| `aggregator` | Multi-source aggregator | Future |

### 4.3 Simulator Provider (PoC)

The simulator can implement the provider interface:

```python
class SimulatorStateProvider(StateOverlayProvider):
    """Adapter from SimulatorState to FoundUpStateOverlay."""

    def __init__(self, state_store: SimulatorState):
        self._state_store = state_store

    def get_foundup_state(self, foundup_id: str) -> Optional[FoundUpStateOverlay]:
        tile = self._state_store.foundups.get(foundup_id)
        if tile is None:
            return None

        return FoundUpStateOverlay(
            foundup_id=foundup_id,
            health_status=self._derive_health(tile),
            availability="online",
            cabr_score=tile.cabr_score,
            lifecycle_progress={
                "observed_stage": tile.lifecycle_stage,
                "tasks_completed": tile.tasks_completed,
                "milestones_published": 0,  # derive from events
            },
            agent_activity={
                "active_agents": self._count_active_agents(foundup_id),
                "tasks_in_flight": tile.task_count - tile.tasks_completed,
            },
            last_updated_at=datetime.utcnow().isoformat(),
            state_provider="simulator",
            freshness_ttl=60,
        )
```

**Important**: This adapter transforms SIM internals into the overlay contract. Shell code NEVER imports simulator dataclasses directly.

---

## 5. Trust and Freshness Rules

### 5.1 Freshness Tiers

| TTL | Freshness | Shell Behavior |
|-----|-----------|----------------|
| 0-60s | Fresh | Display as current |
| 60-300s | Warm | Display with "updated X ago" |
| 300s+ | Stale | Display with warning badge |
| No response | Unavailable | Use last known + "status unknown" |

### 5.2 Provider Failure Behavior

| Scenario | Shell Response |
|----------|----------------|
| Provider timeout | Use cached overlay + stale badge |
| Provider error | Use cached overlay + error badge |
| No cached overlay | Display manifest-only + "status unknown" |
| Provider returns null | Display manifest-only + "not tracked" |

### 5.3 Advisory vs Authoritative

| Data | Authority | Consequence |
|------|-----------|-------------|
| `health_status` | Advisory | Shell shows badge but does not block |
| `availability` | Advisory | Shell warns but allows user override |
| `cabr_score` | Advisory | Shell displays but does not gate |
| `lifecycle_progress` | Advisory | Shell displays but does not enforce |
| Manifest fields | Authoritative | Shell enforces (tier, capabilities) |

**Rule**: Overlay data may influence UX but NEVER overrides manifest authority.

---

## 6. Shell Consumption Rules

### 6.1 Catalog Display

Shell MAY use overlay for:

| Feature | Overlay Field | Behavior |
|---------|---------------|----------|
| Health badge | `health_status` | Green/yellow/red/gray dot |
| CABR chip | `cabr_score` | "CABR: 0.75" chip |
| Activity indicator | `agent_activity.active_agents` | "2 agents active" |
| Freshness hint | `last_updated_at` | "Updated 2m ago" |

### 6.2 Status Filters

Shell MAY use overlay for:

| Filter | Overlay Field | Behavior |
|--------|---------------|----------|
| "Show healthy only" | `health_status == 'healthy'` | Hide degraded/offline |
| "Sort by CABR" | `cabr_score` | Descending sort |
| "Hide stale" | `freshness_ttl` | Hide if TTL exceeded |

### 6.3 Routing Decisions

Shell MAY use overlay for:

| Decision | Overlay Field | Behavior |
|----------|---------------|----------|
| Load warning | `availability == 'maintenance'` | Show notice before load |
| Load block | `availability == 'suspended'` | Block with reason |

### 6.4 Shell MUST NOT

1. **Infer permanent authority** from transient overlay data
2. **Mutate manifest** based on overlay (e.g., auto-promote tier)
3. **Hard-depend on one provider** (always have fallback)
4. **Cache overlay as manifest** (different TTL, different trust)
5. **Import provider internals** (use provider interface only)

---

## 7. Out of Scope

### 7.1 Explicitly Deferred

| Item | Reason | Future Slice |
|------|--------|--------------|
| Provider implementation code | This slice is contract only | `pfmall_state_provider_poc` |
| SSE/WebSocket streaming | Implementation detail | `pfmall_state_streaming` |
| Aggregator logic | Multiple providers later | `pfmall_state_aggregator` |
| Tokenomics details in overlay | Too granular for shell | Never in shell contract |
| Pool breakdowns | SIM internal, not shell data | Never in shell contract |
| Agent individual state | Too granular for catalog | Never in catalog overlay |

### 7.2 Simulator Internals NOT in Overlay

These SIM fields are explicitly excluded from the overlay contract:

| SIM Field | Reason |
|-----------|--------|
| `tick` | Internal simulation time |
| `glow_intensity` | Visual state only |
| `grid_x`, `grid_y` | Layout state only |
| `PoolState` breakdown | Too detailed for shell |
| `ActorState` details | Per-agent, not catalog level |
| `FrozenDict` types | Internal implementation |

---

## 8. Integration Points

### 8.1 Manifest Schema Update

Add to `PFMALL_FOUNDUP_MANIFEST_SCHEMA.md` Section 11 (if not present):

> **Note**: Live state (health, CABR score, agent activity) is NOT in the manifest. See `PFMALL_STATE_OVERLAY_CONTRACT.md` for the dynamic state plane.

### 8.2 Shell Contract Cross-Reference

`PFMALL_SHELL_CONTRACT.md` Section 11.6 already states:

> Static contract only: The shell loads FoundUps based on their static manifest (`foundup_manifest.json`). Dynamic state (lifecycle health, economics, agent metrics) is provided by a separate state overlay layer — not by the shell or manifest. The simulator may serve as one PoC state provider, but is not the permanent architecture for state overlay.

This contract fulfills that reference.

### 8.3 Routing Model Update

Add to `PFMALL_ROUTING_DISCOVERY_MODEL.md` if needed:

> **State-Driven Discovery**: The shell MAY use state overlay to filter, sort, or badge catalog entries. State overlay is advisory only — routing decisions are based on manifest, not overlay.

---

## 9. Example: GotJunk Overlay

```json
{
  "foundup_id": "a1b2c3d4e5f6g7h8",
  "health_status": "healthy",
  "availability": "online",
  "cabr_score": 0.72,
  "cabr_trend": "rising",
  "lifecycle_progress": {
    "declared_stage": "proto",
    "observed_stage": "proto",
    "tasks_completed": 47,
    "milestones_published": 3,
    "days_in_stage": 12
  },
  "agent_activity": {
    "active_agents": 2,
    "tasks_in_flight": 5,
    "last_agent_action": "2026-03-31T14:22:00Z"
  },
  "reserve_summary": {
    "reserve_health": "adequate",
    "reserve_trend": "growing"
  },
  "last_updated_at": "2026-03-31T14:30:00Z",
  "state_provider": "simulator",
  "freshness_ttl": 60
}
```

---

## 10. Migration Path

### 10.1 Phase 1: PoC (Simulator Provider)

- Implement `SimulatorStateProvider` adapter
- Shell fetches overlay from local SIM state
- Used for development and demos only

### 10.2 Phase 2: Production (pAVS Provider)

- Implement `PAVSLifecycleProvider` calling real services
- Shell fetches overlay from pAVS API
- SIM provider remains for testing

### 10.3 Phase 3: Federated (Multi-Provider)

- Implement `StateAggregator` combining multiple providers
- Externalized FoundUps expose own status endpoints
- Aggregator merges with freshness/trust rules

---

## 11. Acceptance Criteria

- [ ] Static vs dynamic boundary is explicit
- [ ] Overlay schema is bounded and versioned
- [ ] Provider interface is abstract (not SIM-specific)
- [ ] Trust/freshness rules are defined
- [ ] Shell consumption rules are explicit
- [ ] Shell prohibitions are explicit
- [ ] SIM is positioned as PoC provider, not architecture

---

*Slice: `pfmall_state_overlay_contract` | 2026-03-31*
