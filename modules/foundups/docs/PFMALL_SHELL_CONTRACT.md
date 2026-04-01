# p.fMALL Shell Contract

**Status**: Architecture specification (first tranche)
**Owner**: 0102
**Slice**: `pfmall_architecture_and_template_contract`
**WSP References**: WSP 3 (Domains), WSP 49 (Structure), WSP 97 (Concatenation Gate)

---

## 1. Purpose

p.fMALL is a PWA shell/gateway that hosts, discovers, and routes into multiple FoundUps. The shell is a **thin platform layer** — it provides discovery, navigation, auth, and shared services. It does NOT own FoundUp business logic, data, or UI.

---

Companion note:
- `PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md` locks the external-repo +
  in-scope-route model that keeps one installed Mall experience without moving
  product logic into the shell.

## 2. Shell Responsibilities

| Responsibility | Description |
|----------------|-------------|
| **App Shell** | Service worker, offline cache, `manifest.json` for installability |
| **Launch Catalog** | Registry of available FoundUps loaded from `catalog.json` |
| **Router** | URL-based routing to FoundUp micro-frontends (`/f/{foundup_id}/*`) |
| **Auth Gateway** | Wallet connect, subscription tier verification, UPs balance check |
| **Nav Chrome** | Top bar, back button, FoundUp switcher, UPs wallet display |
| **HoloIndex Client** | Cross-FoundUp semantic search bar |
| **Notification Bus** | Cross-FoundUp event routing via typed `postMessage` |
| **Telemetry Collector** | Anonymized usage metrics for ROC computation |

## 3. Shell Non-Responsibilities

The shell explicitly does NOT own:

- FoundUp internal state, UI components, or business logic
- FoundUp-specific data storage (each FoundUp owns its own IndexedDB namespace)
- Agent execution (OpenClaw is the control plane; WRE is the execution layer)
- Token operations, staking, or blockchain transactions
- FoundUp-to-FoundUp direct communication (all cross-FoundUp events go through the notification bus)

---

## 4. Shell Boot Sequence

```
1. Load service worker (cache shell assets)
2. Fetch catalog.json (FoundUp manifest registry)
3. Auth check:
   a. Wallet connected? → verify subscription tier
   b. No wallet? → show Free-tier catalog only
4. Register FoundUp routes from catalog
5. Render shell chrome (nav bar, search, wallet display)
6. If deep link (/f/{id}/path) → load target FoundUp
7. Else → show /discover (launch catalog)
```

---

## 5. Shell <-> FoundUp Communication Protocol

All communication uses the browser `postMessage` API with a typed event schema. No shared DOM, no direct function calls, no shared state.

### 5.1 Message Schema

```typescript
interface ShellMessage {
  type: "shell_event";
  event: ShellEventType;
  payload: Record<string, unknown>;
  timestamp: string;  // ISO 8601
  nonce: string;      // dedup
}

type ShellEventType =
  | "route_change"        // Shell tells FoundUp its internal route
  | "auth_state"          // Subscription tier, wallet address
  | "ups_balance"         // Current UPs balance
  | "notification"        // Cross-FoundUp notification
  | "theme_change"        // Light/dark mode
  | "shell_ready";        // Shell boot complete

interface FoundUpMessage {
  type: "foundup_event";
  foundup_id: string;
  event: FoundUpEventType;
  payload: Record<string, unknown>;
  timestamp: string;
  nonce: string;
}

type FoundUpEventType =
  | "navigate"            // FoundUp requests shell navigation
  | "agent_request"       // Request OpenClaw agent execution
  | "ups_spend"           // Debit UPs for agent work
  | "notification_send"   // Send notification to another FoundUp
  | "title_update"        // Update shell title bar
  | "ready";              // FoundUp loaded and ready
```

### 5.2 Message Validation

The shell validates every incoming `postMessage`:

1. **Origin check**: Message origin must match expected FoundUp origin
2. **Schema check**: Message must conform to `FoundUpMessage` schema
3. **Rate limit**: Max 100 messages/sec per FoundUp (circuit breaker)
4. **Size limit**: Max 64KB per message payload
5. **Nonce dedup**: Reject duplicate nonces within 60-second window

Malformed or unauthorized messages are logged to telemetry and silently dropped.

---

## 6. Shell Environment Contract

### 6.1 Required Environment Variables

```env
# Auth
PFMALL_AUTH_PROVIDER=wallet_connect    # Auth mechanism
PFMALL_AUTH_CALLBACK_URL=/auth/callback

# HoloIndex
HOLO_INDEX_API_URL=http://localhost:8200  # HoloIndex MCP endpoint

# OpenClaw
OPENCLAW_API_URL=http://localhost:8100     # Agent execution endpoint

# Catalog
PFMALL_CATALOG_URL=/catalog.json           # Static or API-served

# Telemetry
PFMALL_TELEMETRY_ENABLED=true
PFMALL_TELEMETRY_ENDPOINT=/api/telemetry
```

### 6.2 Feature Flags

```json
{
  "enable_offline_mode": true,
  "enable_holo_search": true,
  "enable_cross_foundup_notifications": false,
  "enable_module_federation": false,
  "max_concurrent_foundups": 1,
  "ups_spending_cap_per_session": 5000
}
```

Phase 1 loads one FoundUp at a time (iframe). `max_concurrent_foundups` and `enable_module_federation` are Phase 2 flags.

---

## 7. Shell Versioning

- Shell version is independent of FoundUp versions
- Shell follows semver: `{major}.{minor}.{patch}`
- FoundUp manifests declare `min_shell_version` for compatibility
- Shell maintains backward compatibility for postMessage schema across minor versions
- Major version bumps may break postMessage schema (documented in migration guide)

---

## 8. Shell URL Structure

```
/                           → Redirect to /discover
/discover                   → Launch catalog (browse FoundUps)
/discover?category=market   → Filtered catalog
/search?q=...               → HoloIndex cross-FoundUp search
/wallet                     → UPs balance, subscription management
/settings                   → Shell preferences
/f/{foundup_id}             → Load FoundUp (default view)
/f/{foundup_id}/{path}      → Deep link into FoundUp internal route
```

Shell routes (`/discover`, `/wallet`, `/search`, `/settings`) are owned by the shell.
FoundUp routes (`/f/{foundup_id}/*`) are delegated to the loaded FoundUp via postMessage.

---

## 9. Offline Strategy

- Shell assets cached by service worker (app shell pattern)
- `catalog.json` cached with stale-while-revalidate strategy
- Each FoundUp manages its own service worker and cache
- Offline FoundUp access depends on FoundUp's own caching implementation
- Shell shows "offline" badge when network unavailable
- UPs spending blocked while offline (requires server verification)

---

## 10. Architectural Precedents

| Pattern | Source | Application |
|---------|--------|-------------|
| iframe isolation | GotJunk 3-app PWA (`FOUNDUP_ECOSYSTEM_ARCHITECTURE.md`) | FoundUp sandboxing |
| postMessage typed events | Web platform standard | Shell <-> FoundUp comms |
| Service worker app shell | PWA best practice | Offline support |
| Graduated autonomy | `agent_permission_manager.py` | Agent request gating |
| Circuit breaker | `circuit_breaker.py` | Message rate limiting |

---

## 11. Constraints

1. **No morphing**: Shell and FoundUps are separate apps. No shared DOM, CSS, or state.
2. **No direct agent access**: FoundUps request agent work through the shell, which gates via OpenClaw.
3. **No cross-FoundUp data access**: IndexedDB namespaced by `foundup_id`. iframe origin isolation enforced.
4. **Infrastructure stays core**: HoloIndex, OpenClaw, WRE are infrastructure — never in the catalog.
5. **HERMES rule**: "OpenClaw=control plane, WRE=execution, HoloIndex=memory" — shell does not add a second runtime or memory authority.
6. **Static contract only**: The shell loads FoundUps based on their static manifest (`foundup_manifest.json`). Dynamic state (lifecycle health, economics, agent metrics) is provided by a separate state overlay layer — not by the shell or manifest. See `PFMALL_STATE_OVERLAY_CONTRACT.md` for the overlay contract. The simulator serves as PoC provider; production uses pAVS services.
