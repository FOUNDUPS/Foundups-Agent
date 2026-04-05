# Kosei AI Systems — INTERFACE.md (WSP 11 Contract Memory)

## Service Contracts

### A. Audit Funnel

- **Inputs**: Lead source (web form, referral, pfMALL), content URLs, platform handles
- **Outputs**: Content audit report, gap analysis, service recommendation, trial offer
- **Contract**: `AuditRequest -> AuditReport`

### B. Onboarding

- **Inputs**: Accepted audit, client preferences, branding assets
- **Outputs**: Provisioned workspace, connected integrations, welcome sequence
- **Contract**: `OnboardingRequest -> ClientWorkspace`

### C. Service Orchestration

- **Inputs**: Client workspace config, content schedule, approval queue
- **Outputs**: Routed automation tasks, status updates, delivery confirmations
- **Contract**: `ServiceRequest -> TaskRouting`
- **External dependency**: AutoPost (content creation engine, separate repo)

### D. Client Workspace

- **Inputs**: Client login, workspace ID
- **Outputs**: Dashboard (content review, approval, scheduling, analytics)
- **Contract**: `WorkspaceQuery -> DashboardState`

### E. Admin/Operator Workspace

- **Inputs**: Operator login (012 / agent)
- **Outputs**: Client overview, billing summary, system health, escalations
- **Contract**: `AdminQuery -> AdminDashboardState`

### F. Trial Management

- **Inputs**: Trial signup, usage metrics
- **Outputs**: Trial status, conversion prompts, expiry handling
- **Contract**: `TrialState -> TrialDecision`

### G. White-Label Config

- **Inputs**: Client branding (logo, colors, domain, feature toggles)
- **Outputs**: Themed workspace, branded deliverables
- **Contract**: `WhiteLabelConfig -> ThemedInstance`

---

## External Dependencies

| Dependency | Location | Relationship |
|-----------|----------|-------------|
| AutoPost | `O:\repos\AutoPost` (external repo) | Content creation engine — consumed as service, not embedded |
| pfMALL | `modules/foundups/pfmall/` | Discovery surface — Kosei may appear as a pfMALL lane |
| AI Gateway | `modules/ai_intelligence/ai_gateway/` | LLM routing for audit analysis and content processing |

---

## Boundary Rules

1. Kosei **does not** contain AutoPost source code
2. Kosei **does not** directly call AutoPost internals — only service APIs
3. AutoPost **does not** depend on Kosei — it operates independently
4. White-label config lives in Kosei, not in AutoPost
5. Client data (workspace, billing, preferences) lives in Kosei, not in AutoPost
