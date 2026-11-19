# Interface

`modules.foundups.entity_management.src.corp_mgmt.assess(record)` takes a mapping
and returns a new status mapping without mutating input or causing side effects.
Required nonempty keys: entity_ref, jurisdiction, agency, period, role.
Allowed role: applicant, lessee, operator, signatory. One role per assessment;
separate assessments/evidence are needed for other roles.

Boolean role_verified, filing_accepted and payment_applied must each be exactly
True. If joint_proposer_required or city_consultation_required is exactly True,
the corresponding verified/completed Boolean must also be exactly True.
Missing context -> NEEDS_CONTEXT; unknown role -> ROLE_UNVERIFIED; missing gates
-> NEEDS_EVIDENCE; all gates -> RECONCILED. can_execute is always False.
Standing, tax_balance, exemption and renewal are separately echoed or UNKNOWN.

Deliberate narrow scope: caller supplies facts; authenticity, date freshness,
applicability and conflicting sources are not validated. Filing and payment are
mandatory for this PoC, so do not use for obligations where either is inapplicable.
False/unknown applicability is not sufficient to support real-world closure.
No production schema or authority decision is implemented.
