# Progressive Execution Agent - Skills Map

## Candidate SKILLz (Not Created - WSP 95 Governs)

| Skill Name | Purpose | Priority |
|---|---|---|
| community_discovery_interview | Guide localized resident interviews and collect evidence | P1 |
| contextual_question_generator | Generate evidence-gap-specific dialogue from project context | P1 |
| field_consent_capture | Record interview/recording consent and constraints | P1 |
| claim_objection_extractor | Extract claims, conditions, objections, and uncertainty from evidence | P1 |
| stakeholder_referral_extractor | Identify named/unnamed referrals and relationship edges | P1 |
| evidence_receipt_builder | Bind inputs, outputs, provenance, and authority state for each execution | P1 |
| community_feasibility_assessor | Evaluate accumulated evidence against graph requirements without converting inference into truth | P1 |
| municipal_site_control_discovery | Discover municipal pathway, prerequisites, officials, and evidence requirements | P2 |
| municipal_requirements_extractor | Convert meeting evidence into structured administrative conditions | P2 |
| academic_compute_demand_discovery | Capture research workload and institutional demand evidence | P2 |
| enterprise_compute_demand_discovery | Capture enterprise workload, constraints, and commercial-intent evidence | P2 |
| grid_feasibility_discovery | Structure utility consultation and extract technical interconnection evidence | P2 |
| document_verification | Validate provenance/status of external documents and signed artifacts | P2 |
| audience_projection_builder | Build minimal audience-specific project status views | P3 |

## WRE Integration Points
- DAE requests capabilities/intents; it should not hard-code model/provider selection.
- WRE/WSP 95 resolves validated SKILLz implementations.
- Skill invocation consumes project-state/evidence references and returns evidence receipts.
- Higher-level domain SKILLz may compose reusable primitives such as consent, transcription, extraction, verification, and receipt generation.
- FoundUp-specific facts and commercial assumptions remain in project state/configuration, not reusable SKILLz.
- Skill authority must be explicit: evidence collection, recommendation, draft generation, verification, or other bounded operations.

## Future Slice
PROGRESSIVE_EXECUTION_AGENT_SKILLZ_WARDROBE_DISCOVERY_PHASE1