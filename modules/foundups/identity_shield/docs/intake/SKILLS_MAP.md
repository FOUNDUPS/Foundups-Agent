# Identity Shield - Skills Map

## Candidate SKILLz (Not Created - WSP 95 Governs)

| Skill Name | Purpose | Priority |
|---|---|---|
| identity_signal_intake | Normalize suspicious calls, messages, notices, and account alerts into a case event | P1 |
| pii_secret_redaction | Detect/minimize sensitive identity data before remote processing | P1 |
| counterparty_verification | Resolve trusted official channels independently of the suspicious contact | P1 |
| identity_incident_triage | Classify likely compromise type, uncertainty, urgency, and reversible next actions | P1 |
| evidence_timeline_builder | Produce provenance-rich case chronology and exportable evidence packets | P1 |
| recovery_route_planner | Select appropriate institution/reporting/recovery routes by incident and jurisdiction | P2 |
| consented_external_action | Execute explicitly approved adapter actions with least privilege and receipts | P2 |
| defensive_social_engineering_eval | Test verification workflow resistance under bounded authorized scenarios | P3 |

## WRE Integration Points
- RedDog/0102 intake should hand structured Identity Shield work to WRE rather than hard-code worker/model assignments.
- Local preprocessing should be preferred for secret detection/redaction when device capabilities support it.
- External verification/reporting adapters should be selected by downstream research and registered as replaceable tools.
- Security/evaluator workers should validate fail-closed behavior, provenance, authorization gates, and adversarial resistance.

## Reuse Candidates Requiring Audit
- AutoPost/AutoCase-style PWA capture patterns may be reusable if current codebase discovery confirms an appropriate shared surface.
- Broader Shield-family privacy patterns may be reused if/when a canonical Shield module exists.
- Existing orchestration/model routing should be reused rather than embedding a FoundUp-specific LLM selector.

## Future Slice
IDENTITY_SHIELD_SKILLZ_WARDROBE_PHASE1

## Boundary
This document names candidate capabilities only. It does not create or promote SKILLz; WSP 95 owns that lifecycle.