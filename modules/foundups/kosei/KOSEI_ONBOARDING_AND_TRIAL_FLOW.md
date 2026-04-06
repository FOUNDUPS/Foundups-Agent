# Kosei AI Systems — Onboarding and Trial Flow

**Worker**: F
**Date**: 2026-04-06
**Slice**: `KOSEI_BACKEND_DATA_AND_WORKSPACE_CONTRACT_PHASE1`

---

## 1. End-to-End Funnel

```
Visitor                Lead                 Trial Client           Paid Client
  │                      │                      │                      │
  │  /audit form         │  Audit runs          │  Trial starts        │  Converts
  ▼                      ▼                      ▼                      ▼
┌─────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ INTAKE  │───→│   AUDIT      │───→│  ONBOARDING  │───→│   ACTIVE     │
│         │    │              │    │              │    │              │
│ - form  │    │ - AI analysis│    │ - workspace  │    │ - content    │
│ - email │    │ - gap report │    │ - connect    │    │ - posting    │
│ - URLs  │    │ - recommend  │    │ - trial      │    │ - analytics  │
│ - goals │    │ - tier       │    │ - branding   │    │ - billing    │
└─────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                     │                    │                    │
                     ▼                    ▼                    ▼
                 EXPIRED             CANCELLED              CHURNED
              (no response)        (client opts out)     (subscription ends)
```

---

## 2. Audit State Machine

```
              ┌───────────────────────────────────────┐
              │         kosei_audit_requests           │
              └───────────────────────────────────────┘

              ┌──────────┐
              │ PENDING  │  ← Form submitted
              └────┬─────┘
                   │ processAuditRequest trigger
                   ▼
              ┌──────────────┐
              │ IN_PROGRESS  │  ← AI analysis running
              └────┬─────────┘
                   │ Analysis complete
                   ▼
              ┌──────────┐
              │ COMPLETE │  ← Report ready, trial offered
              └────┬─────┘
                   │
           ┌───────┴────────┐
           ▼                ▼
    ┌────────────┐    ┌──────────┐
    │ ACCEPTED   │    │ EXPIRED  │  ← No response in 30 days
    │ (→ trial)  │    │          │
    └────────────┘    └──────────┘
```

**Transitions**:

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| — | PENDING | Form submission | Visitor (public) |
| PENDING | IN_PROGRESS | Firestore `onCreate` trigger | Cloud Function |
| IN_PROGRESS | COMPLETE | AI analysis finishes | Cloud Function |
| COMPLETE | ACCEPTED | Client clicks "Start Trial" or admin enrolls | Client or Admin |
| COMPLETE | EXPIRED | 30 days, no action | Scheduled Cloud Function |
| PENDING | EXPIRED | 30 days, no action | Scheduled Cloud Function |

---

## 3. Onboarding Checklist

When a lead accepts the trial offer, a workspace is provisioned and onboarding begins.

```
Onboarding Steps (0-indexed):

Step 0: WORKSPACE_CREATED
  └─ Workspace doc created in kosei_workspaces
  └─ Trial doc created in kosei_trials
  └─ Firebase Auth account created (email/password invite sent)

Step 1: ACCOUNT_VERIFIED
  └─ Client clicks email verification link
  └─ First login to /app/

Step 2: PLATFORMS_CONNECTED
  └─ At least 1 platform connected (YouTube, LinkedIn, or X)
  └─ Integration doc in kosei_workspaces/{id}/integrations/

Step 3: BRANDING_SET
  └─ Brand name and logo uploaded (minimum viable branding)
  └─ WhiteLabelDoc created in kosei_whitelabel/

Step 4: FIRST_CONTENT_APPROVED
  └─ Client reviews and approves first content item
  └─ ContentQueueItem status → "approved"

Step 5: FIRST_POST_PUBLISHED
  └─ First post delivered to connected platform
  └─ PostHistoryItem created
  └─ Onboarding marked COMPLETE
```

**Onboarding state in workspace doc**:
```typescript
{
  onboarding_step: 3,              // Currently at step 3
  onboarding_complete: false,      // Not yet complete
  onboarding_started_at: Timestamp,
  onboarding_completed_at?: Timestamp
}
```

**Admin view**: `/admin/onboarding` shows each client's current step with a visual checklist. Steps can be manually advanced by admin if needed (e.g., skip branding for quick-start clients).

---

## 4. Trial State Model

### Trial parameters

| Parameter | Default | Configurable? |
|-----------|---------|---------------|
| Duration | 14 days | YES — admin can extend once by 7 days |
| Content limit | 10 items | YES — admin can adjust per client |
| Platforms | Up to 3 | Fixed for trial |
| Analytics | Basic only | Fixed for trial |
| White-label | Disabled | Fixed for trial |

### Trial state machine

```
              ┌──────────┐
              │  ACTIVE  │  ← Trial starts (onboarding Step 0)
              └────┬─────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   ┌─────────┐ ┌────────┐ ┌───────────┐
   │CONVERTED│ │EXPIRED │ │CANCELLED  │
   │         │ │        │ │           │
   │→ paid   │ │→ grace │ │→ data     │
   │  tier   │ │  period│ │  retained │
   │         │ │  7 days│ │  90 days  │
   └─────────┘ └────┬───┘ └───────────┘
                    │
                    ▼
              ┌──────────┐
              │ CHURNED  │  ← Grace period over, no conversion
              └──────────┘
```

**Transitions**:

| From | To | Trigger | Actor |
|------|-----|---------|-------|
| — | ACTIVE | Lead accepts trial | Cloud Function (createWorkspace) |
| ACTIVE | CONVERTED | Client selects paid tier | Client (via /app/billing) |
| ACTIVE | EXPIRED | `expires_at < now` | Scheduled Cloud Function (daily) |
| ACTIVE | CANCELLED | Client requests cancellation | Client or Admin |
| EXPIRED | CONVERTED | Client converts during grace period | Client |
| EXPIRED | CHURNED | Grace period (7 days) ends | Scheduled Cloud Function |

### Trial decision logic (daily scheduled function)

```python
def evaluate_trial(trial: TrialDoc) -> TrialDecision:
    if trial.status != "active":
        return no_action

    days = trial.days_remaining

    if days <= 0:
        return TrialDecision(action="expire", message="Trial period ended")

    if days <= 3 and trial.usage_count >= 5:
        return TrialDecision(
            action="prompt_conversion",
            message="Trial ending soon — you've used {usage_count} of {usage_limit} items"
        )

    if days <= 7 and trial.usage_count == 0:
        return TrialDecision(
            action="prompt_conversion",
            message="Try creating your first content item to see Kosei in action"
        )

    return TrialDecision(action="continue")
```

---

## 5. Conversion Flow

```
Trial (14 days)
    │
    ├─ Usage high + trial ending → Conversion prompt (in-app banner)
    │     │
    │     ├─ Client clicks "Upgrade" → /app/billing
    │     │     │
    │     │     ├─ Selects tier (Starter/Professional/Enterprise)
    │     │     ├─ Stripe checkout (future — manual invoicing for Phase 1)
    │     │     └─ Workspace tier updated → trial.status = "converted"
    │     │
    │     └─ Client ignores → Trial expires → 7-day grace → Churn
    │
    └─ Usage zero → Engagement prompt (email + in-app)
          │
          ├─ Client engages → Trial continues
          └─ No engagement → Trial expires → Grace → Churn
```

**Phase 1 conversion**: Manual. Admin sends invoice (PayPal or bank transfer). Admin updates workspace tier in `/admin/clients`. Stripe integration is Phase 3+.

---

## 6. Data Lifecycle

| Event | Data action | Retention |
|-------|------------|-----------|
| Intake form submitted | `kosei_audit_requests/` created | Indefinite (anonymized on deletion request) |
| Trial starts | `kosei_workspaces/` + `kosei_trials/` created | Active until churn |
| Trial expires | `kosei_trials/` status → expired | 90 days after churn |
| Client churns | Workspace status → churned | 90 days, then purge option |
| Client requests deletion | All workspace subcollections purged, audit request anonymized | Immediate |
| Post published | `post_history/` item created | Indefinite while workspace active |
| Issue submitted | `kosei_issues/` created | Indefinite (operational record) |

**Anonymization on deletion**: `contact_email` → null, `platform_handles` → {}, `contact_name` → null. Audit status and timestamps retained for aggregate metrics.

---

## 7. Email Touchpoints

| Event | Email | Sender | Template |
|-------|-------|--------|----------|
| Intake submitted | "We received your audit request" | Kosei (via Resend) | `audit_received` |
| Audit complete | "Your content audit is ready" | Kosei | `audit_complete` |
| Trial started | "Welcome to Kosei — your trial has begun" | Kosei | `trial_welcome` |
| Trial 3 days left | "Your trial ends in 3 days" | Kosei | `trial_ending` |
| Trial expired | "Your trial has ended — here's what you built" | Kosei | `trial_expired` |
| Converted | "Welcome to {tier} — you're all set" | Kosei | `conversion_welcome` |

**Email infrastructure**: Resend SDK (already in root `functions/` — used for beta signup emails). Add Kosei-specific templates.

---

## 8. Integration with AutoPost

AutoPost is consumed as an external service. The integration point is **content delivery**:

```
Client approves content in Kosei workspace
    │
    ▼
Kosei Cloud Function: routeServiceRequest()
    │
    ├─ Video content → AutoPost API (upload to YouTube, route to FoundUp channel)
    │     └─ AutoPost returns: { video_url, youtube_id, status }
    │
    ├─ Text post → social_media_orchestrator adapter
    │     └─ Orchestrator returns: { post_url, platform, status }
    │
    └─ Content item status → "published" in content_queue
         └─ Post history item created
```

**Kosei does not call AutoPost internals.** It sends a content delivery request and receives a status response. The API contract between them is defined in INTERFACE.md Section C.

---

*Worker F — onboarding and trial flow defined. No runtime changes made.*
