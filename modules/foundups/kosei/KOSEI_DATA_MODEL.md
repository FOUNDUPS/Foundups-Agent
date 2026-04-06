# Kosei AI Systems — Data Model

**Worker**: F
**Date**: 2026-04-06
**Slice**: `KOSEI_BACKEND_DATA_AND_WORKSPACE_CONTRACT_PHASE1`

---

## 1. Firestore Collection Map

All Kosei collections live in the shared Firebase project (`gen-lang-client-0061781628`). Collections are prefixed or namespaced to avoid collision with GotJunk and root landing data.

```
Firestore
├── kosei_audit_requests/{request_id}       # Lead intake
├── kosei_workspaces/{workspace_id}         # Client workspace root
│   ├── /integrations/{platform}            # Connected platform status
│   ├── /content_queue/{item_id}            # Pending content items
│   ├── /post_history/{post_id}             # Delivered posts
│   ├── /analytics/{period}                 # Aggregated metrics
│   └── /notes/{note_id}                    # Operator notes (admin-only)
├── kosei_trials/{trial_id}                 # Trial state
├── kosei_issues/{issue_id}                 # Client feedback/issues
├── kosei_whitelabel/{workspace_id}         # Per-client branding
└── kosei_metrics/{period}                  # System-wide aggregates
```

---

## 2. Lead Intake Record

Collection: `kosei_audit_requests/{request_id}`

```typescript
interface AuditRequestDoc {
  // Identity
  id: string;                     // Auto-generated Firestore doc ID
  created_at: Timestamp;
  updated_at: Timestamp;

  // Lead source
  lead_source: "web_form" | "referral" | "pfmall" | "discord" | "other";
  referral_code?: string;         // If lead came via referral

  // Contact
  contact_email: string;          // Required — consent checkbox on form
  contact_name?: string;
  business_name?: string;
  locale: "en" | "ja";            // Captured from i18n toggle at submission

  // Audit input
  content_urls: string[];         // URLs the lead wants audited
  platform_handles: {             // Social handles by platform
    [platform: string]: string;   // e.g., { "youtube": "@handle", "linkedin": "url" }
  };
  business_goals?: string;        // Free text — what do they want from AI content?
  current_posting_frequency?: string; // e.g., "2x/week", "never", "daily"

  // Audit output (written by processAuditRequest Cloud Function)
  audit_status: "pending" | "in_progress" | "complete" | "expired";
  gaps?: string[];                // Identified content gaps
  recommendations?: string[];     // Service recommendations
  recommended_tier?: "trial" | "starter" | "professional" | "enterprise";
  audit_completed_at?: Timestamp;

  // Funnel tracking
  trial_offered: boolean;
  trial_accepted: boolean;
  workspace_id?: string;          // Set when trial/onboarding begins
  converted_at?: Timestamp;       // Set when trial converts to paid
}
```

**Firestore rules**:
- Public create (anyone can submit intake form)
- No public read (leads are not visible to other visitors)
- Admin read/write (012/agents manage the pipeline)
- Client read of own record (after auth, scoped by workspace_id)

---

## 3. Client Workspace

Collection: `kosei_workspaces/{workspace_id}`

```typescript
interface WorkspaceDoc {
  // Identity
  workspace_id: string;           // Deterministic: sha256(client_email)[:16]
  client_name: string;
  client_email: string;
  owner_uid: string;              // Firebase Auth UID
  created_at: Timestamp;
  updated_at: Timestamp;

  // Service tier
  tier: "trial" | "starter" | "professional" | "enterprise";
  tier_changed_at?: Timestamp;

  // Status
  status: "onboarding" | "active" | "paused" | "churned";
  onboarding_step: number;        // 0-based index into onboarding checklist
  onboarding_complete: boolean;

  // Preferences
  locale: "en" | "ja";
  timezone: string;               // IANA timezone (e.g., "Asia/Tokyo")
  posting_preferences: {
    frequency: string;            // e.g., "3x/week"
    preferred_days: string[];     // e.g., ["mon", "wed", "fri"]
    preferred_times: string[];    // e.g., ["09:00", "18:00"]
    platforms: string[];          // e.g., ["linkedin", "x", "youtube"]
  };

  // Billing (future — Stripe)
  stripe_customer_id?: string;
  current_period_end?: Timestamp;
}
```

### Subcollection: `integrations/{platform}`

```typescript
interface IntegrationDoc {
  platform: string;               // "youtube" | "linkedin" | "x" | "instagram" | "tiktok"
  status: "disconnected" | "connecting" | "connected" | "error" | "revoked";
  connected_at?: Timestamp;
  last_health_check?: Timestamp;
  health_status?: "healthy" | "degraded" | "down";
  account_handle?: string;        // e.g., "@client_handle"
  error_message?: string;         // Last error if status = "error"
  scopes?: string[];              // Granted OAuth scopes
}
```

### Subcollection: `content_queue/{item_id}`

```typescript
interface ContentQueueItem {
  item_id: string;
  status: "draft" | "pending_approval" | "approved" | "scheduled" | "published" | "failed";
  content_type: "post" | "video" | "story" | "article";
  platform: string;
  title?: string;
  body?: string;
  media_urls?: string[];
  scheduled_at?: Timestamp;
  published_at?: Timestamp;
  autopost_job_id?: string;       // Reference to AutoPost delivery (external)
  created_at: Timestamp;
  approved_by?: string;           // Client UID or "auto"
}
```

### Subcollection: `post_history/{post_id}`

```typescript
interface PostHistoryItem {
  post_id: string;
  platform: string;
  published_at: Timestamp;
  content_type: string;
  title?: string;
  url?: string;                   // Link to published post
  engagement: {
    likes?: number;
    comments?: number;
    shares?: number;
    views?: number;
    last_updated: Timestamp;
  };
}
```

### Subcollection: `notes/{note_id}` (admin-only)

```typescript
interface NoteDoc {
  note_id: string;
  author_uid: string;             // 012 or agent UID
  author_name: string;
  content: string;                // Free text
  category: "follow_up" | "escalation" | "internal" | "billing";
  created_at: Timestamp;
  pinned: boolean;
}
```

---

## 4. Trial State

Collection: `kosei_trials/{trial_id}`

```typescript
interface TrialDoc {
  trial_id: string;               // Same as workspace_id
  workspace_id: string;
  client_email: string;

  // Timing
  started_at: Timestamp;
  expires_at: Timestamp;          // started_at + 14 days
  days_remaining: number;         // Computed daily by scheduled function

  // Usage
  usage_count: number;            // Number of content items processed
  usage_limit: number;            // Trial limit (e.g., 10 posts)
  platforms_connected: number;

  // Status
  status: "active" | "expired" | "converted" | "cancelled";
  decision: "continue" | "prompt_conversion" | "expire" | "extend";
  decision_reason?: string;

  // Conversion
  converted_at?: Timestamp;
  converted_to_tier?: string;
  cancellation_reason?: string;
}
```

**Trial rules**:
- Default: 14 days, 10 content items
- Extension: Admin can extend once (7 days) via `decision: "extend"`
- Expiry: Scheduled Cloud Function checks daily, sets `status: "expired"` when `expires_at < now`
- Conversion: Client accepts tier → `status: "converted"`, workspace tier updated

---

## 5. White-Label Client Config

Collection: `kosei_whitelabel/{workspace_id}`

```typescript
interface WhiteLabelDoc {
  workspace_id: string;

  // Branding
  brand_name: string;             // Displayed in client workspace header
  logo_url: string;               // Firebase Storage URL
  favicon_url?: string;
  primary_color: string;          // Hex (e.g., "#1a73e8")
  secondary_color?: string;
  font_family?: string;           // Google Fonts name

  // Domain (future — custom domain mapping)
  custom_domain?: string;         // e.g., "content.clientbrand.com"
  domain_verified: boolean;

  // Feature flags
  feature_flags: {
    [flag: string]: boolean;      // e.g., { "analytics_advanced": true, "video_content": false }
  };

  // Templates
  post_footer?: string;           // Appended to all posts (e.g., "Powered by ClientBrand")
  email_from_name?: string;       // Sender name for notifications
}
```

**Tier-gated features**:

| Feature flag | Trial | Starter | Professional | Enterprise |
|-------------|-------|---------|-------------|------------|
| `analytics_basic` | YES | YES | YES | YES |
| `analytics_advanced` | NO | NO | YES | YES |
| `video_content` | NO | YES | YES | YES |
| `custom_domain` | NO | NO | NO | YES |
| `white_label_full` | NO | NO | YES | YES |
| `api_access` | NO | NO | NO | YES |
| `multi_user` | NO | NO | YES | YES |

---

## 6. Connection Status Model

Collection: `kosei_workspaces/{workspace_id}/integrations/{platform}`

State machine:

```
disconnected ──connect──→ connecting ──success──→ connected
                              │                      │
                              ▼                      ▼
                            error ←──health_fail── degraded
                              │                      │
                              ▼                      ▼
                           revoked                  down
```

**Health check**: Hourly Cloud Function pings each connected platform's API. Updates `health_status` and `last_health_check`. If 3 consecutive failures → `status: "error"`.

**Platforms supported (Phase 1)**:
- YouTube (via AutoPost upload flow)
- LinkedIn (via social_media_orchestrator adapter)
- X/Twitter (via social_media_orchestrator adapter)

**Platforms planned (Phase 2+)**:
- Instagram, TikTok, Facebook, Threads (via platform connectors)

---

## 7. Issue / Feedback Model

Collection: `kosei_issues/{issue_id}`

```typescript
interface IssueDoc {
  issue_id: string;
  workspace_id: string;
  author_uid: string;             // Client or admin UID
  author_role: "client" | "admin";

  // Content
  title: string;
  description: string;
  category: "bug" | "feature_request" | "content_issue" | "billing" | "general";
  priority: "low" | "medium" | "high" | "urgent";

  // Status
  status: "open" | "in_progress" | "waiting_client" | "resolved" | "closed";
  assigned_to?: string;           // Admin UID
  resolution?: string;            // Free text

  // Timestamps
  created_at: Timestamp;
  updated_at: Timestamp;
  resolved_at?: Timestamp;

  // Attachments
  attachment_urls?: string[];     // Firebase Storage URLs
}
```

**Firestore rules**:
- Client can create and read own issues (scoped by workspace_id via owner_uid)
- Client can update own issues (add comments, close)
- Admin can read/write all issues
- No public access

---

## 8. Firestore Security Rules (Kosei namespace)

```javascript
// Kosei collections — to be added to root firestore.rules
match /kosei_audit_requests/{requestId} {
  allow create: if true;                              // Public intake
  allow read, update: if isKoseiAdmin();              // Admin pipeline
}

match /kosei_workspaces/{workspaceId} {
  allow read, update: if isWorkspaceOwner(workspaceId) || isKoseiAdmin();
  allow create, delete: if isKoseiAdmin();
}

match /kosei_workspaces/{workspaceId}/{subcollection}/{docId} {
  allow read: if isWorkspaceOwner(workspaceId) || isKoseiAdmin();
  allow write: if isWorkspaceOwner(workspaceId) || isKoseiAdmin();
}

match /kosei_trials/{trialId} {
  allow read: if isTrialOwner(trialId) || isKoseiAdmin();
  allow write: if isKoseiAdmin();                     // Only admin manages trials
}

match /kosei_issues/{issueId} {
  allow create: if request.auth != null;              // Any authenticated user
  allow read: if isIssueAuthor(issueId) || isKoseiAdmin();
  allow update: if isIssueAuthor(issueId) || isKoseiAdmin();
}

match /kosei_whitelabel/{workspaceId} {
  allow read: if isWorkspaceOwner(workspaceId) || isKoseiAdmin();
  allow write: if isKoseiAdmin();                     // Only admin sets branding
}

match /kosei_metrics/{period} {
  allow read: if isKoseiAdmin();
  allow write: if false;                              // Backend-only writes
}

// Helpers
function isKoseiAdmin() {
  return request.auth != null && request.auth.token.kosei_admin == true;
}

function isWorkspaceOwner(workspaceId) {
  return request.auth != null &&
    get(/databases/$(database)/documents/kosei_workspaces/$(workspaceId)).data.owner_uid == request.auth.uid;
}
```

---

## 9. Indexes

| Collection | Fields | Order | Purpose |
|-----------|--------|-------|---------|
| `kosei_audit_requests` | `audit_status ASC, created_at DESC` | Composite | Admin pipeline view |
| `kosei_workspaces` | `status ASC, created_at DESC` | Composite | Admin client list |
| `kosei_trials` | `status ASC, expires_at ASC` | Composite | Trial expiry check |
| `kosei_issues` | `workspace_id ASC, status ASC, created_at DESC` | Composite | Client issue list |

---

*Worker F — data model defined. No runtime changes made.*
