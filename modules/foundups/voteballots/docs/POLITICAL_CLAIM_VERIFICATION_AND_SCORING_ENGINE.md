# Vote - Political Claim Verification and Scoring Engine

**Feature name**: Bullshit Meter / BS Meter  
**Date**: 2026-10-30 (Asia/Tokyo)  
**Classification**: EXISTING_FOUNDUP_UPDATE  
**Status**: DESIGN / ROADMAP ONLY - NOT IMPLEMENTED  
**Owner**: existing `modules/foundups/voteballots/` under current WRE/architect authority  
**Source**: [original 012 specification](intake/CLAIM_VERIFICATION_SOURCE_20261030.md)

## 1. Outcome and position in Vote

A person can inspect a factual claim made in a political speech, debate, advertisement, broadcast, or public post; follow its exact source words; inspect the underlying evidence and its limitations; and understand a transparent assessment that can be corrected.

This extends Vote's existing funding-transparency and candidate-record direction. It adds statement verification alongside funding evidence, then later a caption/video overlay and a live meter. It does not create a separate FoundUp, repository, identity system, video shell, or general governance owner.

The existing Python v0.6.0 chain remains a mock-data FEC boundary, candidate resolution, funding summary, confidence scoring, template quick answer, and local shell payload. That code does not implement this feature. The May 25 closure's 303 passing tests are historical funding-chain evidence, not claim-engine validation. Live FEC access and public Vote activation remain separate unfinished work.

An internal asynchronous evaluation may proceed alongside roadmap Phases 0/1 after its own architecture/reuse review. Public and member feature activation still require the existing public PoC and prototype gates. The current task records the feature in the documentation; it does not run the ten-speech experiment or deploy a service.

## 2. Requested pipeline and implementation contracts

### A. Ingestion and atomic claim extraction

- Start with public text transcripts. Candidate future inputs include congressional records, floor speeches, C-SPAN archives, historical addresses, public posts, political ads, and broadcasts. Verify lawful access, reuse terms, API availability, and retention before an adapter is selected.
- Preserve source URL, publisher, speaker identity/attribution, event date, language, retrieval date, content hash/version, exact quote, surrounding context, and source offsets. Add audio/video timestamps only when the source supplies them or alignment has been validated.
- Extract individual empirical, statistical, historical, and legal/definitional assertions. Preserve geography, population, time period, denominator, units, comparison baseline, qualifiers, and whether the words quote another speaker.
- Exclude opinions, rhetoric, promises, and presently unfalsifiable predictions from truth scoring; retain the original text and exclusion reason in the audit record. Mixed sentences must be split without changing their meaning.
- Handle sarcasm, negation, transcript corrections, speaker overlap, and low-confidence ASR explicitly. A questionable transcript cannot support a confident adverse verdict.
- Require schema validation and reproducible extraction evaluations. Deterministic serialization or a fixed model configuration does not establish semantically deterministic or accurate claim extraction.
- Streaming ASR, including Whisper-family or another vetted shared adapter, belongs to CV4 after asynchronous behavior is validated.

### B. Primary-source retrieval and evidence graph

Route by the claim's domain, jurisdiction, date, and relevant institution. Identify who produced the data or holds the applicable legal/scientific authority before constructing queries.

The requested search operators (`site:`, `filetype:pdf`, `filetype:csv`, `intitle:methodology`) are retrieval aids. A .gov, .org, or .edu suffix does not establish truth, independence, or competence. Prefer the exact primary dataset, release, methodology, statute, judgment, filing, or relevant specialist synthesis; retain secondary sources as discovery leads when needed, not as substituted primary evidence.

For each retrieval, store the query, access/result status, source version, publication and effective dates, precise locator, quoted evidence span, and the relationship to the atomic claim: SUPPORTS, CONTRADICTS, CONTEXTUALIZES, or INSUFFICIENT. Similarity search retrieves candidates; it never establishes entailment.

Five articles repeating one dataset are not five independent confirmations. Track common data provenance. A speech or press release is primary evidence of what its author said, not necessarily evidence that the underlying assertion is true. Show failed retrievals, unavailable records, source revisions, conflicting authoritative evidence, and trail termination.

Historical assessment must distinguish evidence available when the statement was made from later revisions or findings. Claims about legal classifications must retain jurisdiction, applicable instrument/version, decision-making body, procedural stage, exact holding and scope. Allegations, expert assessments, commission findings, provisional measures, advisory opinions, and judgments are separate source types. See [R4](#r4-legal-authority-and-procedure).

### C. Methodological and statistical audit

Apply the audit both to material cited by the speaker and to evidence selected by the verifier. Record applicability and unknown fields; not every claim requires a poll or significance test.

Inspect population, sampling frame/method, field dates, question wording, sample and subgroup sizes, weighting, design effects/effective sample size when available, interval type, denominators, missing data, and limitations. Probability and nonprobability estimates require different uncertainty treatment. National-poll `n < 1000` and `MOE > 3.5 percentage points` are review signals from the proposal, not universal invalidity gates. This design follows disclosure-oriented assessment rather than a fixed sample-size test. See [R1](#r1-survey-methodology).

Flag selective time windows, mismatched populations, unsupported precision, missing methods, and possible selective reporting. A p-value alone is not the probability that a claim is true. Missing preregistration/raw analyses may justify AUDIT_INFORMATION_MISSING or SELECTIVE_REPORTING_RISK; they do not prove p-hacking or fabrication. See [R2](#r2-statistical-inference).

PDF/OCR extraction must preserve the page, paragraph, table, or cell and its extraction confidence. Automation proposes audit findings; low-confidence extraction, high-impact findings, and disputes need independent review.

### D. Funding, incentives, and historical consistency

Research disclosed relationships using existing Vote funding/entity components and vetted adapters for IRS Form 990, FARA, corporate disclosures, and OpenSecrets or equivalent filings-backed indexes. These are candidate sources, not a claim that an API, license, credential, complete donor list, or working connector already exists.

Record the entity resolution, relationship type, dates, amount where disclosed, funder's documented role, supporting filing, and where the trail stops. Separate speaker funding, study funding, institutional governance, and the verification service's own conflicts. Preserve Vote's existing distinction among PAC, independent expenditure, nonprofit, corporate, and alleged foreign links.

Treat the requested `C_i in [0.1, 1.0]` as an unvalidated weighting hypothesis. A funding relationship triggers scrutiny and a documented mechanism-of-bias assessment; it does not automatically make a result false. Any numerical weighting requires independent calibration and a published rationale. Unknown funding remains unknown. Cochrane provides a relevant methodological analogy, not a validated political scoring standard: [R3](#r3-conflicts-and-mechanisms-of-bias).

Compare source-aligned historical claims and voting/public records. Record contradictions, changed circumstances, corrections, and recurrence after a dated correction. A changed position or repeated contradicted claim does not by itself establish knowledge, deliberate deception, or criminal intent. The requested repeat-offender mechanism becomes an auditable recurrence record; any later score penalty must be bounded, independently validated, separately displayed, and disabled until its rubric passes review.

## 3. Assessment and score contract

### Separate dimensions

| Dimension | Proposed contract |
|---|---|
| Factual verdict | SUPPORTED, CONTRADICTED, MIXED, INSUFFICIENT_EVIDENCE, NOT_CHECKABLE |
| WSP 97 evidence state | VERIFIED_FACT, HIGH_CONFIDENCE_INFERENCE, LOW_CONFIDENCE_INFERENCE, UNKNOWN; describes evidence for the assessment, not whether the original utterance is true |
| Context | Explicit timeframe, denominator, geography, comparison, quotation, and source-revision flags |
| Methodology | Applicable audit findings, missing fields, reviewer disposition |
| Funding/incentives | Sourced conflicts and mechanisms, with independence and trail-stop state |
| Recurrence | Matched claim, dated correction, later occurrence, matching-context confidence |
| Intent | NOT_ESTABLISHED unless separately supported and reviewed |
| Review lifecycle | PENDING, REVIEW_REQUIRED, APPROVED, CHALLENGED, SUPERSEDED |

The source proposal's `V_c in [-1, +1]` is retained for experimental research. +1 represents a supported claim and -1 a contradicted claim under the evaluated rubric. Neither sign establishes intent. A numeric 0 may only represent an explicitly adjudicated mixed result under a published rubric. INSUFFICIENT_EVIDENCE, NOT_CHECKABLE, unresolved context, pending review, and unreliable transcription use `null` and are excluded from numerical aggregation.

### Proposed 300-850 index

The requested scale and color ranges are retained as an experimental interface proposal:

| Proposed range | Proposed label |
|---|---|
| 750-850 | Spot On / green |
| 550-749 | Spin / Skewed / yellow |
| 300-549 | Bullshit / red |
| No eligible score | Pending / insufficient evidence / insufficient coverage; neutral presentation |

These boundaries are not validated. The credit-score analogy describes a display range only; it is not FICO, a probability of honesty, financial creditworthiness, a vote recommendation, or a representative ranking of a politician.

Before any score is published, the implementation packet must specify and evaluate:
- the aggregation formula, eligible verdicts, claim-level review requirements, and rounding;
- claim deduplication/clustering so repeated wording and prolific speech do not dominate;
- severity weights, their neutral domain rationale, and the exponential recency/half-life policy;
- the assessed period, corpus-selection rules, minimum assessed count, topic/speech coverage, and abstention threshold;
- the denominator, excluded/unknown count, source independence, sensitivity to weights, uncertainty, and rubric/version identifier;
- the treatment of recurrence and conflicts without silently converting either into factual falsity.

No exact aggregation equation, weights, penalty, minimum coverage, or calibration is approved by this intake. They remain implementation-research decisions. If the gate fails, output `score: null` plus an explicit reason, not a midpoint or a default red rating. Ten speeches support a bounded PoC evaluation, not a general politician truthworthiness claim. Validation and appeal requirements are informed by [R5](#r5-evaluation-and-correction).

### Explicit qualifications to the supplied proposal

| Supplied proposal | Integrated requirement |
|---|---|
| Unknown/missing context maps to zero | Keep uncertainty/context separate; unresolved cases are null and unscored |
| Contradiction is a blatant lie/fabrication | Report contradicted evidence; intent is a separate evidential question |
| Repetition after correction proves intent | Preserve dated recurrence evidence; intent is not automatically established |
| Sample size or MOE alone rejects a survey | Audit design and applicability; thresholds are review flags |
| Funding alignment directly penalizes truth | Publish conflicts and causal bias concerns; numerical use requires calibration |
| A domain suffix or institutional label guarantees truth | Verify document type, competence, date, methods, and exact evidential scope |
| Instant live truth verification follows fast ASR | Measure transcription, cache lookup, research, review, and display independently |
| Initialize a new repository/schema | Extend the existing Vote module; audit shared storage before migrations |

## 4. Evidence tree, dashboard, and overlays

Every assessment must expose an exportable, clickable JSON evidence graph:
- original transcript/media reference, exact quote, source offsets, and valid timestamp where available;
- normalized atomic claim with date/scope/context;
- source nodes with primary document links, hashes/versions, and PDF page/paragraph/table or dataset row/column locators;
- typed evidence edges and reproducible calculations;
- methodology audit, conflicts, independence, uncertainty, and trail termination;
- verdict rationale, review state, rubric/model/tool versions, and amendment history.

The UI should distinguish the currently spoken claim from any aggregate speech/person index. A changed gauge must be traceable to newly assessed evidence. Color must be accompanied by text and accessible status, not used alone.

Preserve the requested FALSE and SKEWED DATA interaction concepts as evidence-detail labels subject to the adjudication rules. Provide a challenge/correction path with append-only history and recomputation of affected aggregates/caches. Do not silently replace an earlier verdict.

Video/caption overlays must align to the exact source occurrence, handle caption revisions and speaker attribution, and reuse existing FoundUps extension/media surfaces where suitable. Restrict permissions to the supported user-initiated media task; do not infer private political profiles or optimize political persuasion.

Live state must distinguish TRANSCRIBING, CHECKING, PREVIOUSLY_VERIFIED_MATCH, VERDICT_READY, REVIEW_REQUIRED, and INSUFFICIENT_EVIDENCE. Revalidate cached matches for speaker, date, meaning, and source freshness. Incomplete research does not trigger a red accusation.

The requested less-than-500-ms target remains a future, hardware-specific ASR/cache-display objective with a precisely defined metric. It is not a promise to verify a novel claim in that time. Measure partial/final ASR, completed-claim extraction, cache hits, fresh retrieval, review, and display separately, including tail latency and failure states. [R6](#r6-streaming-benchmark-context) illustrates why ASR latency must be benchmarked in its stated setting.

## 5. Proposed data model and reuse boundary

PostgreSQL plus pgvector is a candidate persistence/index design from the supplied specification, not a new installed dependency or provisioned database. Audit existing FoundUps storage, retrieval, transcript indexing, migrations, identity, and provenance before choosing ownership. Relational records and source receipts are authoritative; embeddings are discovery aids.

| Requested table | Minimum design responsibility |
|---|---|
| Politicians | Stable public entity identity, aliases, office/jurisdiction, disambiguation provenance |
| Transcripts | Speaker/event/source, text/version/hash, acquisition/access basis, offsets and optional timing |
| Extracted_Claims | Exact quotation and normalized assertion, context, checkability, extraction version, dedup cluster |
| Primary_Sources | Document/dataset identity and version, authority/scope, dates, precise locators, common-data provenance |
| Funding_Entities | Resolved public entities and typed, dated, sourced relationships |
| Audit_Logs | Append-only acquisition, extraction, assessment, review, challenge, correction, and scoring events |

The schema also needs explicit relations for claim occurrences, claim-to-source edges, methodology audits, versioned assessments, and score snapshots. Their final table ownership and names are determined in the build packet. Preserve nullable timestamps rather than inventing alignment.

Reuse candidates: Vote entity/funding/confidence/trail-stop contracts; existing transcript/YouTube indexing and ASR; WRE/HoloIndex research routing; existing provenance/challenge patterns; AutoPost capture; pfMALL public/member boundaries; and existing browser-extension/media surfaces. The current three-line funding answer and local shell payload are not silently repurposed into a full verification dashboard.

## 6. Feature rollout mapped onto the existing roadmap

All milestones below are PLANNED / NOT IMPLEMENTED.

| Track | Requested phase | Bounded deliverable | Exit evidence |
|---|---|---|---|
| CV1 | Phase 1: asynchronous transcript engine | Internal CLI and review dashboard; ten historical speeches across 2-5 public figures; atomic claim JSON, primary-source receipts, explicit abstention, and experimental score only where its reviewed gate permits | Frozen corpus, independent reviewed labels, extraction/retrieval/verdict error report, evidence graph, versioned rubric and explicit unscored cases |
| CV2 | Phase 2: methodology and funding graph | Methodology-document parser; disclosed funding graph; documented conflicts; historical contradiction/recurrence records | Audited sampling/uncertainty cases, source-independent replication handling, correction propagation, calibrated or still-disabled weighting |
| CV3 | Phase 3: caption/video overlay | Existing-extension integration for supported YouTube/X or other permitted caption surfaces; timestamped asynchronous evidence tags | Caption/source alignment, stale-cache/revision behavior, minimal permissions, accessible evidence detail, correction flow |
| CV4 | Phase 4: live debate/broadcast meter | Streaming ASR, cache and bounded parallel research with provisional/final states | Separate latency and accuracy benchmarks, speaker/claim alignment, abstention, human-review handling, operational and public-release checks |

CV1 can begin internally alongside status reconciliation/public PoC work. Public candidate/race/funding delivery remains roadmap Phase 1. Public claim-score/meter activation belongs to Phase 2 Candidate Record + Scorecard after the prototype gate. Existing Discovery, Parallel Ballot, Registration Assurance, Voter Resilience, and SmartDAO phases retain their meaning and order. A scorecard may summarize evidence; it does not rank whom a person should elect.

### CV1 acceptance and evaluation plan

- [ ] Retrieve existing implementations and write the REUSE / EXTEND / EXTRACT_SHARED / NEW decision with current paths.
- [ ] Freeze ten source-backed historical speeches across 2-5 public figures, with dates, comparable selection rules, topic/length disclosure, access basis, hashes, and no cherry-picking for a desired verdict.
- [ ] Treat Trump, Obama, Vance, and Newsom as examples from the source, not a locked or already ingested corpus.
- [ ] Annotate atomic claims and exclusions; independently review disagreements and high-impact assessments.
- [ ] Report extraction precision/recall, unsupported-verdict rate, source citation/entailment accuracy, abstention/coverage, and reproducibility. Predeclare release thresholds before judging results; do not invent success metrics after observing output.
- [ ] Include adversarial cases: missing denominator, revised historical data, ambiguous entity, quote attribution, changed timeframe, duplicate evidence, conflicting primary sources, absent methodology, small but applicable samples, and nonprobability polling.
- [ ] Audit the verifier's own selection rules, model/rubric versions, review conflicts, and failure modes.
- [ ] Output machine-readable claims, evidence tree, assessment/review log, corpus manifest, and evaluation report. Scores are explicitly experimental or null with reasons.
- [ ] Keep the first dashboard internal until source, privacy, methodology, and public/prototype release requirements are met.

## 7. Next implementation packet - not executed by this intake

1. Retrieve using the concrete queries in [SKILLS_MAP](intake/SKILLS_MAP.md); verify current source and the six-slice closure. Direct code reads are a documented fallback when semantic retrieval is unavailable.
2. Choose existing owners for transcript ingestion, primary search, storage and extension/UI; decide whether PostgreSQL/pgvector is necessary before any migration.
3. Define the claim/evidence/review schema and extraction contract, including unknown states and versioning.
4. Implement one asynchronous transcript-to-evidence slice with a deterministic test harness and explicit network/source fixtures; validate before expanding the layer.
5. Run the ten-speech evaluation and preserve receipts. Do not claim scores or performance before that run exists.
6. Advance CV2-CV4 individually only after their exit criteria. Public launch is a separate tested activation.

Relevant existing reopen criteria: V5 for confidence/review changes; V6 for new facts, model output or expanded answer generation; V8 for shell/payload changes; V1 if live FEC is activated; V2 for public activation; V3/V7 for any registry/catalog/readiness change. Source acquisition/search also requires an explicitly documented network/data boundary. WSP 99 carries the downstream assignment; WRE retains orchestration authority.

## 8. References and remaining decisions

These sources ground the methodology qualifications. They do not certify Vote or establish the accuracy of the proposed index. Checked for this intake on 2026-10-30.

### R1. Survey methodology
[AAPOR Disclosure Standards](https://aapor.org/standards-and-ethics/disclosure-standards/), especially sampling, question wording, weighting, design effects, and probability/nonprobability precision.

### R2. Statistical inference
[American Statistical Association statement on significance and p-values](https://www.amstat.org/asa/files/pdfs/p-valuestatement.pdf), six principles and reporting transparency.

### R3. Conflicts and mechanisms of bias
[Cochrane Handbook, Chapter 7](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-07), section 7.8.3. Adapted as a methodology principle; the handbook addresses intervention reviews, not political scoring.

### R4. Legal authority and procedure
[Statute of the International Court of Justice](https://www.un.org/en/about-us/un-charter/statute-of-the-international-court-of-justice), Articles 40-41, 59-60 and 65; [Court-hosted text](https://icj-web.leman.un-icc.cloud/statute). Record exact procedural and substantive scope rather than substituting institutional prestige.

### R5. Evaluation and correction
[NIST AI RMF 1.0 Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), MEASURE: documented tests, realistic validation, independent assessment, limitations, and feedback/appeal.

### R6. Streaming benchmark context
[Machacek, Dabre and Bojar, 2023, Turning Whisper into Real-Time Transcription System](https://aclanthology.org/2023.ijcnlp-demo.3.pdf). Historical ASR research illustrating task/hardware-specific latency; it is not a current model recommendation or a Vote latency result.

### Decisions reserved for a build packet
- Corpus/jurisdiction selection and allowed acquisition adapters.
- Storage/migration owner and exact shared transcript/search/extension interfaces.
- Extraction/verdict rubric, aggregation equation, weighting, calibration, coverage thresholds, and recurrence policy.
- Model/hardware selection, source licenses/credentials, review ownership, and latency/quality budgets.
- Which evidence views are public versus member-gated after the existing release checks.

The original specification remains preserved. These open decisions do not block the requested documentation update and are not assertions that implementation has already begun.
