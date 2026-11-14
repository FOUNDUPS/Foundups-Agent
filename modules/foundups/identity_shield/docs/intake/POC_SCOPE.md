# Identity Shield - POC Scope

## Minimum Viable POC
Prove that Identity Shield can take one suspected identity-theft/scam event and turn it into a privacy-safe, auditable verification and response plan without collecting a centralized identity profile.

## Included in POC
- User submits a suspicious message/call description/account alert or sanitized document.
- Local-first secret/PII detection and redaction before any optional remote model use.
- Threat classification with confidence and explicit uncertainty.
- Independent verification workflow that identifies an official contact channel from a trusted source, not from the suspicious communication.
- Case/evidence timeline containing event metadata, hashes, decisions, provenance, and user authorization receipts.
- Recommended defensive next actions ordered by reversibility and risk.
- Explicit user gate before any external report, contact, account action, or data transmission.

## Explicitly Excluded from POC
- Autonomous account freezes, fund transfers, credit freezes, police reports, legal filings, or accusations.
- Storage of passwords, authentication secrets, recovery codes, full government IDs, or raw identity dossiers in a central service.
- Offensive penetration testing, impersonation, credential testing against third parties, covert monitoring, or retaliation.
- A production partnership with the FBI or any named government/cybersecurity organization.
- Token issuance, PFmall publication, DAO activation, or public launch.
- Building new SKILLz before WSP 95 governs that work.

## Success Criteria
The PoC passes when a controlled set of benign and simulated malicious scenarios demonstrates that the workflow can: (1) redact secrets before remote processing, (2) avoid attacker-provided verification channels, (3) produce a traceable evidence record, (4) distinguish recommendations from executed actions, and (5) fail closed when verification is insufficient.

## Trust Wedge
A free "Is this identity contact real?" verification flow that gives the user a safe official contact path and a concise evidence/next-action summary without requiring the user to create a centralized identity vault.

## PoC Safety Invariant
When confidence is low or trusted-source verification is unavailable, the system must say that verification is unresolved and route the user to a known official channel rather than infer identity.