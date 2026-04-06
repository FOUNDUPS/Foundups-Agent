# Kosei AI Systems — ROADMAP

## Phase 0: Scaffold (current)

- Module structure created
- Boundary with AutoPost documented
- Contracts defined in `INTERFACE.md` and `src/contracts.py`

## Phase 1: Audit Funnel

- Content audit request intake (web form or API)
- Automated content gap analysis (via AI Gateway)
- Audit report generation
- Trial offer flow

## Phase 2: Client Workspace

- Client dashboard (content review, approval, scheduling)
- Integration with AutoPost for content delivery
- Basic analytics (posts published, engagement summary)

## Phase 3: Onboarding + Trial

- Guided onboarding flow
- Trial provisioning and expiry management
- Conversion funnel tracking

## Phase 4: Admin/Operator Workspace

- 012/agent management console
- Client overview and billing summary
- Escalation routing

## Phase 5: White-Label

- Per-client branding (logo, colors, domain)
- Feature toggles per tier
- Branded deliverables

---

## Dependencies by Phase

| Phase | Depends On |
|-------|-----------|
| 0 | None (scaffold only) |
| 1 | AI Gateway (audit analysis) |
| 2 | AutoPost (external — content engine) |
| 3 | Phase 1 + 2 |
| 4 | Phase 2 |
| 5 | Phase 2 + 4 |
