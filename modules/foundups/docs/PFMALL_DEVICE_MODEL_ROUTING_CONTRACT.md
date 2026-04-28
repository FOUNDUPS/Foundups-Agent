# p.fMALL Device Capability and Model Routing Contract

**Status**: Architecture Specification (ADR)
**Owner**: 0102
**Slice**: `PFM4_DEVICE_CAPABILITY_AND_MODEL_ROUTING_CONTRACT_SPEC_PHASE1`
**WSP References**: WSP 97 (Truth Boundaries), WSP 11 (Interface Protocol)

---

## WSP 97 Truthfulness Statement

This document is an **architecture specification only**. No implementation code is included.

| Claim | Status |
|-------|--------|
| DeviceCapabilityProfile schema defined | `SPECIFIED_NOT_IMPLEMENTED` |
| Browser capability detection | `SPECIFIED_NOT_IMPLEMENTED` |
| Local/browser Gemma routing | `SPECIFIED_NOT_IMPLEMENTED` |
| WebGPU/WebNN runtime | `SPECIFIED_NOT_IMPLEMENTED` |
| PWA capability APIs | `SPECIFIED_NOT_IMPLEMENTED` |
| Device-aware FoundUpJob routing | `SPECIFIED_NOT_IMPLEMENTED` |

**Architect Constraint**: Browser/local Gemma is feasible only as a future opt-in triage layer on capable devices. Current behavior must remain cloud/server-side. This spec defines the safe placement in the roadmap.

---

## 1. Purpose

Define the contract for device-aware model routing in p.fMALL so that:

1. Future PWA/browser Gemma work has a clear, safe place in the architecture
2. Device capability context can inform server-side routing decisions
3. Browser-side AI boundaries remain constrained per VerificationGapGuard
4. RedDog can surface device limitations without overriding policy gates

**Canonical Rule**: Device capability is advisory context. It informs UX and routing hints but cannot bypass FoundUpJob/WRE/Hermes/FAM/pAVS verification pipeline.

---

## 2. DeviceCapabilityProfile

### 2.1 Schema Definition

```typescript
interface DeviceCapabilityProfile {
  // === Device Classification ===
  device_class: "phone" | "tablet" | "desktop" | "unknown";
  
  // === Hardware Capabilities ===
  webgpu_supported: boolean;        // navigator.gpu available
  webnn_supported: boolean;         // navigator.ml available (WebNN)
  estimated_memory_gb: number;      // navigator.deviceMemory or heuristic
  estimated_vram_mb: number | null; // WebGPU adapter limits or null
  cpu_cores: number;                // navigator.hardwareConcurrency
  
  // === Power State ===
  battery_level: number | null;     // 0.0-1.0 or null if unavailable
  battery_charging: boolean | null; // true/false or null if unavailable
  thermal_state: "nominal" | "fair" | "serious" | "critical" | "unknown";
  low_power_mode: boolean;          // OS low-power mode detected
  
  // === Network State ===
  network_state: "online" | "offline" | "metered" | "unknown";
  effective_connection_type: "slow-2g" | "2g" | "3g" | "4g" | "unknown";
  
  // === User Preferences ===
  user_prefers_local: boolean;      // User explicitly opted into local processing
  privacy_mode: boolean;            // User prefers on-device over cloud
  
  // === Derived Capability Flags ===
  can_run_local_triage: boolean;    // Device could run local triage model
  can_run_browser_gemma: boolean;   // Device could run browser Gemma (future)
  
  // === Metadata ===
  profile_version: string;          // Schema version
  captured_at: string;              // ISO 8601 timestamp
  detection_method: "api" | "heuristic" | "user_provided" | "unknown";
}
```

### 2.2 Detection Sources

| Field | Browser API | Fallback |
|-------|-------------|----------|
| `device_class` | User-agent + screen size | Heuristic |
| `webgpu_supported` | `navigator.gpu !== undefined` | `false` |
| `webnn_supported` | `navigator.ml !== undefined` | `false` |
| `estimated_memory_gb` | `navigator.deviceMemory` | `4` (conservative) |
| `estimated_vram_mb` | `GPUAdapter.limits.maxBufferSize` | `null` |
| `cpu_cores` | `navigator.hardwareConcurrency` | `4` |
| `battery_level` | `navigator.getBattery()` | `null` |
| `battery_charging` | `BatteryManager.charging` | `null` |
| `thermal_state` | Not available in browsers | `"unknown"` |
| `low_power_mode` | Not standardized | `false` |
| `network_state` | `navigator.onLine` + `navigator.connection` | `"unknown"` |
| `effective_connection_type` | `NetworkInformation.effectiveType` | `"unknown"` |

### 2.3 Capability Derivation Rules

```typescript
function deriveCapabilities(profile: DeviceCapabilityProfile): void {
  // can_run_local_triage: Minimal requirements
  profile.can_run_local_triage = 
    profile.cpu_cores >= 4 &&
    profile.estimated_memory_gb >= 4 &&
    !profile.low_power_mode &&
    profile.battery_level !== null ? profile.battery_level >= 0.2 : true;
  
  // can_run_browser_gemma: More demanding requirements
  profile.can_run_browser_gemma =
    profile.webgpu_supported &&
    profile.estimated_memory_gb >= 8 &&
    (profile.estimated_vram_mb ?? 0) >= 2048 &&
    profile.cpu_cores >= 4 &&
    !profile.low_power_mode &&
    profile.battery_level !== null ? profile.battery_level >= 0.3 : true;
}
```

---

## 3. Routing Modes

### 3.1 Mode Definitions

| Mode | Description | When Used |
|------|-------------|-----------|
| `cloud_only` | All AI processing via server-side models | Default for all devices |
| `local_triage` | Local model performs initial classification, server verifies | Future opt-in, capable devices |
| `hybrid` | Local triage + cloud verification + local display | Future opt-in, capable devices |
| `offline_limited` | Cached responses only, no new AI processing | Network unavailable |
| `human_review_required` | Protected decision class, requires human | VerificationGapGuard trigger |
| `blocked_by_verification_gap` | AI cannot proceed, human gate | Protected class encountered |

### 3.2 Mode Selection Logic

```typescript
type RoutingMode = 
  | "cloud_only" 
  | "local_triage" 
  | "hybrid" 
  | "offline_limited" 
  | "human_review_required"
  | "blocked_by_verification_gap";

function selectRoutingMode(
  profile: DeviceCapabilityProfile,
  requestType: string,
  isProtectedClass: boolean
): RoutingMode {
  // Protected classes always require human review
  if (isProtectedClass) {
    return "blocked_by_verification_gap";
  }
  
  // Offline falls back to limited
  if (profile.network_state === "offline") {
    return "offline_limited";
  }
  
  // Current default: always cloud
  // Future: check user_prefers_local && can_run_local_triage
  return "cloud_only";
}
```

### 3.3 Mode Transition Rules

| Current Mode | Can Transition To | Trigger |
|--------------|-------------------|---------|
| `cloud_only` | `local_triage` | User opts in + device capable |
| `cloud_only` | `offline_limited` | Network lost |
| `cloud_only` | `blocked_by_verification_gap` | Protected class |
| `local_triage` | `cloud_only` | User opts out |
| `local_triage` | `hybrid` | User opts in + device capable |
| `local_triage` | `blocked_by_verification_gap` | Protected class |
| Any | `human_review_required` | Anomaly detected |

---

## 4. RedDog Interaction

### 4.1 What RedDog MAY Do with DeviceCapabilityProfile

| Action | Allowed | Example |
|--------|---------|---------|
| Receive profile as context | YES | Profile passed to RedDog session |
| Summarize device limitations | YES | "Your device may have limited offline capabilities" |
| Recommend routing mode | YES | "Would you like to enable local triage?" |
| Ask user for permission | YES | "Enable on-device processing?" |
| Display capability indicators | YES | Battery icon, offline badge |
| Log profile for analytics | YES | Anonymous capability telemetry |

### 4.2 What RedDog MAY NOT Do

| Action | Blocked | Reason |
|--------|---------|--------|
| Override WRE/policy gates | BLOCKED | Profile is advisory only |
| Bypass FoundUpJob contract | BLOCKED | Job pipeline is canonical |
| Skip server verification | BLOCKED | Cloud verification required |
| Make protected decisions | BLOCKED | VerificationGapGuard applies |
| Force local routing | BLOCKED | User consent required |
| Claim capability certainty | BLOCKED | Detection is heuristic |

### 4.3 RedDog Capability Notification

```typescript
interface RedDogCapabilityNotice {
  notice_type: "capability_info" | "limitation_warning" | "preference_prompt";
  summary: string;
  device_class: string;
  routing_mode: RoutingMode;
  can_improve: boolean;          // User action could improve capability
  suggested_action?: string;     // "Plug in charger", "Connect to WiFi"
  preference_prompt?: {
    question: string;            // "Enable on-device processing?"
    options: string[];           // ["Yes", "No", "Ask later"]
  };
}
```

---

## 5. FoundUpJob Relation

### 5.1 Profile Informs Job Creation

DeviceCapabilityProfile MAY inform `compute_tier` and `model_preference` fields in FoundUpJob:

```typescript
function informJobFromProfile(
  job: FoundUpJob,
  profile: DeviceCapabilityProfile
): void {
  // Profile can suggest model preference
  if (profile.user_prefers_local && profile.can_run_local_triage) {
    job.payload.device_routing_hint = "local_triage_eligible";
  }
  
  // Profile can inform compute tier selection
  if (profile.network_state === "metered") {
    job.payload.device_routing_hint = "minimize_data_transfer";
  }
  
  // Profile CANNOT mutate:
  // - job.requested_action (canonical action)
  // - job.status (lifecycle state)
  // - job.policy_flags (gate results)
}
```

### 5.2 Profile CANNOT

| Field | Mutable by Profile? | Reason |
|-------|---------------------|--------|
| `requested_action` | NO | Canonical job action |
| `status` | NO | Lifecycle is pipeline-controlled |
| `policy_flags` | NO | Gate results are authoritative |
| `evidence_refs` | NO | Evidence comes from execution |
| `worker_id` | NO | Set by executing worker |

### 5.3 Profile Payload Extension

```typescript
// In FoundUpJob.payload
interface DeviceRoutingPayload {
  device_routing_hint?: 
    | "local_triage_eligible"
    | "minimize_data_transfer"
    | "offline_fallback"
    | "full_cloud";
  device_profile_summary?: {
    device_class: string;
    can_run_local: boolean;
    network_state: string;
  };
}
```

---

## 6. Browser Gemma Truth Boundary

### 6.1 What Browser Gemma MAY Do (Future)

| Action | Allowed | Constraint |
|--------|---------|------------|
| Intent classification | YES | Triage only, not final |
| Text summarization | YES | Display only |
| Spam pre-filtering | YES | Soft filter, reversible |
| UI assistance | YES | UX helper |
| Offline suggestions | YES | Cached responses |

### 6.2 What Browser Gemma MAY NOT Do

| Action | Blocked | Reason |
|--------|---------|--------|
| Code generation/execution | BLOCKED | Security boundary |
| Build execution | BLOCKED | Server-side only |
| Reward decisions | BLOCKED | VerificationGapGuard |
| Fraud/scam accusations | BLOCKED | Protected class |
| Payout authorization | BLOCKED | Protected class |
| Wallet actions | BLOCKED | Protected class |
| pAVS/CABR decisions | BLOCKED | Server-side authority |
| Public Trust Ledger writes | BLOCKED | Protected class |
| Identity/reputation impact | BLOCKED | Protected class |

### 6.3 Browser Model Output Classification

```typescript
type BrowserModelOutputClass =
  | "triage_only"           // Classification signal, not decision
  | "summarization"         // Display text, no action
  | "ui_assistance"         // UX helper, reversible
  | "BLOCKED_protected";    // Attempted protected action

function classifyBrowserOutput(output: any): BrowserModelOutputClass {
  // All browser model outputs are advisory
  // Protected actions are blocked at invocation, not output
  return "triage_only";
}
```

---

## 7. VerificationGapGuard Relation

### 7.1 Integration Points

| Component | Relation |
|-----------|----------|
| DeviceCapabilityProfile | Informs routing, does not override guard |
| Browser Gemma (future) | Constrained by guard, cannot bypass |
| RedDog notifications | Surfaces guard alerts |
| FoundUpJob | Guard applies to job execution |
| Protected classes | Same list as VerificationGapGuard |

### 7.2 Guard Takes Precedence

```typescript
function routeWithGuard(
  profile: DeviceCapabilityProfile,
  requestType: string,
  decisionClass: string
): RoutingMode {
  // VerificationGapGuard always takes precedence
  if (isProtectedClass(decisionClass)) {
    return "blocked_by_verification_gap";
  }
  
  // Then apply device-aware routing
  return selectRoutingMode(profile, requestType, false);
}

function isProtectedClass(decisionClass: string): boolean {
  const PROTECTED = [
    "fraud_accusation",
    "scam_accusation", 
    "deepfake_accusation",
    "reward_denial",
    "reputation_impact",
    "legal_exposure",
    "identity_risk",
    "trust_ledger_publication",
    "wallet_action",
    "payout_finality"
  ];
  return PROTECTED.includes(decisionClass);
}
```

---

## 8. First-Run Phone Question Protocol

### 8.1 When Allowed

A first-run capability question is allowed ONLY when:

1. Capability detection APIs are unavailable or ambiguous
2. User has not previously set a preference
3. Question is phrased as setup preference, not hard gate

### 8.2 When NOT Allowed

| Scenario | Question Allowed? | Reason |
|----------|-------------------|--------|
| APIs available, clear detection | NO | Use API results |
| User previously answered | NO | Respect stored preference |
| Critical functionality blocked | NO | Cannot gate core features |
| Privacy-sensitive context | NO | Don't prompt in sensitive flows |

### 8.3 Question Format

```typescript
interface FirstRunCapabilityPrompt {
  prompt_type: "setup_preference";  // NOT "hard_gate"
  question: string;
  context: string;                  // Why we're asking
  options: Array<{
    value: string;
    label: string;
    is_default: boolean;
  }>;
  skip_allowed: boolean;            // User can skip, defaults apply
  remember_choice: boolean;
}

// Example
const FIRST_RUN_PROMPT: FirstRunCapabilityPrompt = {
  prompt_type: "setup_preference",
  question: "How would you like AI assistance to work?",
  context: "This helps us optimize your experience based on your device.",
  options: [
    { value: "cloud", label: "Cloud processing (recommended)", is_default: true },
    { value: "local_when_possible", label: "On-device when possible", is_default: false },
    { value: "ask_each_time", label: "Ask me each time", is_default: false }
  ],
  skip_allowed: true,
  remember_choice: true
};
```

---

## 9. Current Build Seam (Unchanged)

This spec does NOT modify the current build seam:

```
pfMALL / RedDog / OpenClaw
    |
    v
FoundUpJob (created with optional device_routing_hint)
    |
    v
WRE (skill routing, model selection)
    |
    v
Hermes (bounded execution)
    |
    v
FAM receipt (proof of work)
    |
    v
pAVS placeholder (verification)
```

DeviceCapabilityProfile is advisory context that travels alongside the job, not a replacement for any pipeline stage.

---

## 10. WSP 97 Truth Boundaries

### 10.1 What This Contract DOES

- Defines DeviceCapabilityProfile schema
- Specifies routing modes and selection logic
- Establishes RedDog interaction boundaries
- Documents FoundUpJob relation (advisory, not authoritative)
- Defines browser Gemma truth boundary
- Integrates with VerificationGapGuard
- Specifies first-run question protocol

### 10.2 What This Contract DOES NOT

- Implement capability detection JS
- Implement browser Gemma runtime
- Implement WebGPU/WebNN integration
- Modify public/member files
- Modify FoundUpJob contract
- Implement local model downloads
- Create PWA service worker changes
- Build routing infrastructure

### 10.3 What This Contract ENABLES

- Future PWA capability detection implementation
- Future browser Gemma integration (opt-in triage)
- Future device-aware UX improvements
- Clear boundary for browser-side AI
- Safe roadmap placement for local AI work

---

## 11. Future Work

### 11.1 Next Atomic Slice: PWA Detection Skeleton

**Candidate slice**: `PFM4_PWA_CAPABILITY_DETECTION_SKELETON_PHASE2`

Would create:

```
public/member/js/device-capability-detector.js
  - detectDeviceCapabilities(): Promise<DeviceCapabilityProfile>
  - deriveCapabilityFlags(profile): void
  - getStoredPreference(): UserPreference | null
  - storePreference(pref: UserPreference): void
  
public/member/tests/test_device_capability_detector.mjs
  - Mock navigator APIs
  - Test derivation rules
  - Test preference persistence
```

**NOT in scope for skeleton**:
- WebGPU model loading
- Gemma runtime
- Routing implementation
- RedDog integration

### 11.2 Roadmap Stages

| Stage | Scope | Status |
|-------|-------|--------|
| **Phase 1** | Contract spec (this doc) | `SPECIFIED_NOT_IMPLEMENTED` |
| **Phase 2** | PWA detection skeleton | Future |
| **Phase 3** | RedDog capability notices | Future |
| **Phase 4** | Local triage opt-in | Future |
| **Phase 5** | Browser Gemma integration | Future, opt-in only |

---

## 12. Related Documents

- [VERIFICATION_GAP_GUARD_CONTRACT.md](VERIFICATION_GAP_GUARD_CONTRACT.md) - Protected decision classes
- [PFMALL_ROUTING_DISCOVERY_MODEL.md](PFMALL_ROUTING_DISCOVERY_MODEL.md) - Shell routing
- [PFMALL_SHELL_CONTRACT.md](PFMALL_SHELL_CONTRACT.md) - Shell responsibilities
- [public/member/INTERFACE.md](../../../public/member/INTERFACE.md) - pfMALL Agent Control Contract
- [foundup_job_contract.py](../../communication/moltbot_bridge/src/foundup_job_contract.py) - Job schema

---

## Appendix: Decision Record

**ADR-DMR-001**: Device Capability and Model Routing Contract

- **Date**: 2026-04-27
- **Status**: Accepted
- **Context**: Need safe roadmap placement for future browser Gemma without drifting current architecture
- **Decision**: Spec-only contract establishing DeviceCapabilityProfile as advisory context, not authority
- **Consequences**: 
  - Current cloud-only routing unchanged
  - Browser AI remains triage-only when implemented
  - VerificationGapGuard remains authoritative for protected decisions
  - FoundUpJob pipeline unmodified
