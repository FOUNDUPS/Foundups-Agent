# Appendix D. State Evidentiary Referral Transmittal Package

**Model instrument and operating specification. Version 1.0 — November 5, 2026.**

This package is designed for use by a duly authorized congressional committee after legal review. Citizen researchers use the public evidentiary-packet process instead. This model is complete in its operative provisions; an actual transmittal also requires a completed execution record containing the real matter, authorized sender, verified official recipient, disclosure authority, evidence manifest and date. An incomplete execution record is rejected, rather than filled with invented facts.

## D.1 Mandatory execution record

| Field | Required entry and validation |
| --- | --- |
| referral_id | Unique committee-issued identifier, immutable after execution. |
| matter_id | Identifier of the approved legislative inquiry; links to the authorization and legislative-purpose memorandum in the committee's authorized system. |
| transmitting_body | Actual committee name and Congress number; joint use lists each body and the body owning each record. |
| authorization | Date, decision-maker, rule/resolution/consent/order citation, scope of disclosure, and location of the written approval. Proposed rules do not qualify. |
| sender | Name, official role, official address and callback route of the person authorized to transmit. |
| recipient | Office, named authorized intake official, role, verified official address and verification date. Confirm the office can lawfully receive each included compartment. |
| purpose | Neutral statement of the potential state-law questions, factual nexus, legislative context, and requested custody acknowledgement. |
| conduct_period | Actual dates covered; identify uncertain dates explicitly. |
| package_version | Sequential version, creation timestamp, superseded versions and correction reason when applicable. |
| evidence_manifest | Signed or authenticated inventory naming every included file, size, SHA-256, source, restriction tags and approval decision. |
| approvals | Committee disclosure approval, source-owning counsel review, OGC review, privacy/redaction review and transfer-security review; each records person, role, date and decision. |
| screening_instruction | Receiving office's approved routing for material presenting potential immunity, privilege or source restrictions. |
| disclosure_scope | Whether the package is public, ordinary nonpublic or individually authorized restricted material; identify permitted onward disclosure and applicable retention requirements. |
| transfer_record | Approved channel, transfer timestamp, manifest hash, credential delivery record, recipient acknowledgment and integrity comparison. |

A package may not be transmitted when any included item lacks source ownership, a lawful acquisition record, an onward-disclosure decision, a restriction classification or a hash. “No restrictions identified after review” is an affirmative recorded determination, not an empty field. No recipient, date, signature, court order or approval may be inferred by an agent.

## D.2 Operative transmittal language

**Subject: Evidentiary referral for independent jurisdictional and legal assessment**

The transmitting congressional committee provides the accompanying records pursuant to the authorization identified in the execution record. The committee obtained and reviewed these materials in connection with the legislative inquiry identified there. The receiving office is asked to assess independently whether facts within its lawful jurisdiction warrant preservation, further inquiry, regulatory action, civil proceedings, criminal investigation, or no action.

This transmittal makes no determination that a person has committed a crime or civil violation. It does not request a predetermined outcome, direct prosecutorial discretion, confer jurisdiction, waive a person's rights, or authorize disclosure otherwise prohibited by law. The factual narrative distinguishes source-supported observations, witness assertions, analytical inferences, unresolved questions and legal theories. Contrary and potentially exculpatory information known to the transmitting team is identified in the accompanying schedule.

The package consists only of the items listed in the authenticated manifest. The receiving office should compare the manifest and file hashes before opening substantive material. An unexpected file, integrity mismatch or undisclosed restriction requires quarantine and immediate notice through the verified official callback route. Do not circulate the package to a trial or merits team until any required receiving-office screening is complete.

Each exhibit carries its applicable restriction tags and disclosure decision. No committee certification substitutes for a required statutory permission, court order, source-owner consent or receiving-office authorization. Materials identified as excluded in the restrictions schedule are not included and must not be requested informally from an analyst. Any later request for excluded material must be routed to authorized counsel and resolved under the governing law.

The committee preserves its original records and provenance. The copies supplied are intended to permit independent assessment and identification of original custodians. The receiving office should obtain independently any underlying records or testimony needed for its proceeding, including appropriate custodian evidence and authentication. A congressional transcript or forensic summary is not automatically admissible in a state court and does not replace the receiving office's evidentiary foundation.

No agreement concerning immunity, charging, sentencing, nonprosecution, licensing, asset restraint or disposition is offered through this transmittal. The committee cannot bind a state prosecutor or court. The receiving office retains control of its legal process and communications with witnesses. Any coordination must preserve legislative purpose, grand-jury secrecy, constitutional rights and the independence of the respective institutions.

The receiving office is requested to acknowledge receipt, identify its authorized custodian, confirm integrity verification, and identify any routing or restriction issue requiring resolution. An acknowledgment does not represent acceptance of a legal theory or opening of an investigation. No disclosure of grand-jury proceedings, confidential investigative strategy or protected prosecutorial work is requested.

The transmitting committee will provide material corrections, newly identified restrictions and significant contrary evidence through an authorized channel. The receiving office should preserve earlier versions and the dissemination record, mark superseded analytical material, and determine any further notice or remedial steps required by its duties. The committee will publish only information separately approved for public release.

Execution is effective only when the execution record and manifest are authenticated by the actual authorized transmitting official. The recorded authentication applies to the identified version and manifest hash; it does not cover later additions.

## D.3 Required dossier modules

### Module 1 — Neutral factual narrative

Organize the narrative by dated events, entities and transactions. Every factual sentence receives an exhibit and pinpoint or is expressly identified as a witness assertion or inference. State the proposition actually supported: a recorded payment, an ownership filing, a communication or a witness account. Do not convert a chronology into proof of corrupt intent. Explain competing explanations and facts needed to distinguish them. Identify both the confidence in the source and the separate confidence in attribution.

### Module 2 — Jurisdiction and element map

For each potential legal theory, state the complete statute/subsection, conduct-date version, required elements, territorial-jurisdiction rule, venue, relevant limitations question and competent office. Map evidence and gaps to each element. Identify the victim or public interest without disclosing unnecessary personal information. The entry must say “jurisdiction not established” where the only known link is corporate formation, correspondent-bank transit or the location of an evidence custodian.

### Module 3 — Exhibit and provenance manifest

Each exhibit record contains: exhibit_id; original_source; source_custodian; acquisition_authority; acquisition_date; production_identifier; original_filename; preservation_format; byte_count; sha256; date_range; page_or_record_count; transformations; restriction_tags; reviewer; disclosure_authority; recipient_scope; and independent_reacquisition_route. Preserve original timezone and any conversion rule. Hash originals and derivatives separately. OCR text is a derivative and must link to the source image. A forensic extraction must identify software/version, parameters, operator and error log.

### Module 4 — Restriction and exclusion schedule

| Compartment | Default transfer decision | Required resolution |
| --- | --- | --- |
| Public record lawfully acquired | Eligible after privacy and provenance review. | Source URL/identifier, retrieval date and immutable capture or hash when permitted. |
| Ordinary nonpublic committee material | Hold until a valid disclosure decision. | Then-effective committee/House authority, source-owner review and recipient restrictions. |
| Federal tax return or return information | Exclude absent a specifically identified lawful route. | Applicable 26 U.S.C. § 6103 authority and any safeguards; House permission alone is insufficient. |
| SAR or information revealing SAR existence | Exclude absent specific lawful authority and authorized recipient. | BSA/regulatory restrictions and FinCEN/source-owner conditions; do not relabel as an ordinary bank record. |
| Federal or state grand-jury matter | Quarantine and exclude until authorized. | Governing secrecy rule and valid order or exception; Rule 6(e) is not a general committee sharing license. |
| Compelled or immunized testimony; potentially derived material | Route only under the receiving office's approved screening plan, if transmission is otherwise lawful. | Immunity order/agreement, scope, exposed-person log, independent-source history and counsel determination. |
| Attorney-client, work product, executive privilege or contested privilege | Hold for authorized counsel. | Privilege log, assertion, ruling/accommodation and disclosure effects. Sharing does not promise universal nonwaiver. |
| Classified or protected national-security information | No public or ordinary referral channel. | Originator/classification authority and authorized facilities, recipients and transmission method. |
| Court-sealed or protective-order material | Hold. | Governing order, modification/consent where necessary and recipient undertaking. |
| Personal data, trade secrets and protected witness information | Minimize, segregate and redact as authorized. | Necessity finding, access controls and disclosure/privacy review. |

The register retains excluded-item identifiers and reasons at an appropriately restricted level. It does not expose excluded substance in the public manifest. A sanitization that reveals the existence of a protected SAR, grand jury or witness can itself be impermissible; counsel reviews the description as well as the attachment.

### Module 5 — Immunity and independent-source plan

Identify each immunity or compulsion event, the exact order/agreement, dates, covered person and whether a potentially affected witness or investigator has been exposed. Preserve pre-exposure evidence and interview memoranda. The receiving office selects a screening official who decides what its trial team may see. Log each disclosure and any accidental exposure. An independent-source schedule states when and how each material fact was actually learned, identifies the supporting original record, and records a prospective lawful re-acquisition route. A later subpoena does not erase derivation from immunized testimony. Apply 18 U.S.C. §§ 6002, 6005 and *Kastigar*, together with broader applicable state immunity. D.C. consumer-investigation material also requires review under D.C. Code § 28-3910(a)(3), which restricts later criminal admission against the provider. See Section III, D32–D37.

### Module 6 — Forensic report and reproducibility bundle

Provide methods, assumptions, date/currency normalization, exchange-rate source, reconciliation totals, duplicate-handling rules, identity-match criteria and uncertainty. Separate transaction facts from attribution. Include an error and correction log and identify whether a second analyst reproduced the result. Do not include access tokens, credentials, private source identities or restricted datasets in a public reproducibility bundle. A public version must reproduce only its public claims from its public sources.

### Module 7 — Contrary evidence and unresolved questions

List denials, inconsistent records, innocent explanations, unresolved authenticity or completeness questions, and evidence weakening the proposed theory. Identify provenance and materiality. Maintain this module with the same version discipline as the principal narrative. Do not omit a contrary record because it does not support the research objective.

## D.4 Chain of custody and transfer procedure

The evidence custodian freezes the approved manifest, calculates its SHA-256 and records the package version. The transmitting official authenticates that precise manifest. The custodian encrypts only approved files and transfers them by the mutually approved official channel. Credentials travel separately. The recipient verifies integrity, records receipt and routes any screened material without exposing the trial team. Both custodians log time, operator, system, custody event, artifact hashes and authorized recipients. Originals remain preserved under applicable records and litigation-hold requirements. Retention and deletion decisions are made by authorized records/legal officials; neither an agent nor a contributor deletes source evidence to simplify a public release.

## D.5 Review and completion decisions

The reviewing attorney records a separate pass, fail or hold for: legislative authorization; recipient authority; territorial and venue analysis; disclosure law; tax/SAR restrictions; grand-jury restrictions; immunity and derivation; privilege; court orders; privacy; authentication; evidentiary gaps; contrary evidence; and transfer security. “Hold” blocks transmission of the affected items. The committee may transmit an independently approved subset with its own manifest, while preserving an accurate exclusion schedule.

The recipient's acknowledgment records referral_id, package_version, manifest_hash, receipt_time, custody official, integrity result and routing restrictions. It does not certify truth or admissibility. The public milestone is recorded only after an authorized public disclosure or an official public acknowledgment. The internal intake record, the public tracker and the prosecutor's confidential matter system remain distinct.

## D.6 Corrections and incident notice

When a factual error, changed attribution, hash mismatch, accidental restricted disclosure or undisclosed compulsion is discovered, stop affected dissemination. Preserve the original version and incident evidence. Notify authorized counsel and the verified recipient promptly, identify the affected exhibits and known recipients, and supply a corrected version or quarantine instruction. Receiving officials determine screening, suppression, notification or court-relief obligations. Do not claim that recall or deletion cures legal exposure. Publish a correction when the inaccurate material was public and publication is authorized; keep it linked to the original public claim.
