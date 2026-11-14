# Identity Shield - Prototype Gate

## POC -> Prototype Criteria
- [ ] PII/secret redaction is tested against representative identity documents and scam inputs without persisting raw secrets centrally.
- [ ] Trusted-source counterparty verification is separated from attacker-supplied URLs, phone numbers, QR codes, and contact details.
- [ ] Evidence/provenance records are deterministic enough for audit and export.
- [ ] High-impact external actions are impossible without explicit user authorization.
- [ ] Failure states return `unresolved`/safe routing rather than fabricated verification.
- [ ] Threat-model review confirms adversarial testing is defensive, scoped, authorized, and non-offensive.
- [ ] Model/provider routing remains abstracted through existing orchestration rather than hard-coded to one LLM.
- [ ] Privacy, security, and jurisdictional compliance review is complete for the proposed prototype integrations.

## Prototype Scope Expansion
The prototype may add permissioned adapters for credit bureaus, banks, telecom providers, reporting portals, identity-monitoring/data-removal services, and cybersecurity responders. It may add device-capability-aware local models, encrypted user-controlled case storage, recurring monitoring, and guided recovery workflows. Integration selection must be based on a fresh WSP 97 architecture/vendor audit.

## Risk Gates
- [ ] Privacy validated
- [ ] Security reviewed
- [ ] Compliance checked for target jurisdictions
- [ ] Data-retention/deletion contract defined
- [ ] Consent and revocation behavior tested
- [ ] External adapter permissions are least-privilege
- [ ] No centralized credential/identity honeypot introduced
- [ ] Red-team mode cannot perform unauthorized access or surveillance

## Government / Cybersecurity Cooperation Gate
A future cooperation module may package consented evidence for qualified responders, but no agency is assumed. Before choosing an FBI, FTC, IC3, local law-enforcement, private cybersecurity, financial-institution, or non-U.S. route, downstream research must verify jurisdiction, reporting interfaces, legal authority, privacy terms, and whether programmatic submission is permitted.