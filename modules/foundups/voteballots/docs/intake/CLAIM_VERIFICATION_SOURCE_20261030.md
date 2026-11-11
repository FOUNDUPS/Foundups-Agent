# Vote - Political Claim Verification: Original 012 Specification

**Received**: 2026-10-30 (Asia/Tokyo)  
**Source type**: pasted_prompt + spoken_012 clarification  
**Classification**: EXISTING_FOUNDUP_UPDATE  
**Canonical module**: `modules/foundups/voteballots/`  
**Current assignment**: update the existing Outcome, Solution, Pain, roadmap, and related intake documents.

## Provenance and implementation boundary

The following block preserves the supplied feature specification. The subsequent spoken instruction requested its inclusion in Vote's documentation and roadmap. This source is a proposal, not evidence of implementation, a scored politician, a completed evaluation, or deployment.

The [integrated design](../POLITICAL_CLAIM_VERIFICATION_AND_SCORING_ENGINE.md) records the evidence and scoring qualifications required for implementation. Its explicit qualification table resolves conflicts with the proposal below. The repository remains the existing Foundups-Agent module; this intake does not initialize a duplicate repository or database.

## Original supplied text

```text
SYSTEM SPECIFICATION: POLITICAL CLAIM VERIFICATION & SCORING ENGINE ("BULLSHIT METER")
TARGET EXECUTOR: Autonomous Developer Agent
PARADIGM: First-Principles Data Verification, Game-Theoretic Incentive Auditing, Zero-Sycophancy Fact Extraction
OBJECTIVE: Architect and deploy an end-to-end automated system that ingests political speech, extracts verifiable factual claims, audits underlying data sources for statistical and funding bias, and outputs a dynamic, transparent Truth Score (analogous to a credit score) alongside a real-time overlay ("Bullshit Meter").
1. CORE ARCHITECTURAL PIPELINE
Module A: Ingestion & Claim Extraction Engine
 * Input Streams:
   * Historical Corpus: Scrape and ingest public transcripts, C-SPAN archives, congressional records, floor speeches, and social media feeds.
   * Real-Time Stream: Low-latency audio-to-text transcription (e.g., Whisper-large-v3 / streaming ASR) for live debates, ads, and broadcasts.
 * Claim Classification & Filtering:
   * Parse text into atomic statements.
   * Discard: Pure rhetorical fluff, subjective value judgments, and unfalsifiable predictions.
   * Extract: Concrete factual assertions, statistical citations, historical claims, and legal/definitional classifications (e.g., "Crime dropped 15%", "90% of surveyed citizens agree", "Event X does not meet legal definition Y").
Module B: Automated "Dorking" & Retrieval Engine
 * Source Identification (First-Principles Routing):
   * Query logic must ask: Which primary institution or specialist body holds the ground-truth data or legal mandate for this specific domain?
   * Route queries away from secondary media summaries and political press releases; target primary repositories.
 * Advanced Search Execution:
   * Execute programmatic search queries using strict operators (site:.gov, site:.org, site:.edu, filetype:pdf, filetype:csv, intitle:methodology).
   * Target raw datasets, peer-reviewed meta-analyses, court filings, statutory definitions, and international specialist bodies (e.g., UN Commissions, ICJ rulings, Bureau of Labor Statistics, NBER).
Module C: Methodological & Statistical Validity Auditor
Every cited study, poll, or dataset used by a politician—or retrieved during verification—must pass an automated statistical audit:
 * Sample Size & Power Check: Reject or flag surveys failing minimum statistical significance thresholds (e.g., n < 1000 for national polling, or margin of error > \pm 3.5\%). Flag p-hacking or cherry-picked timeframes.
 * Methodology Inspection: Parse PDF documentation for sampling methods (e.g., opt-in online poll vs. probability-based random digit dialing), leading question phrasing, and survivorship bias.
 * Definitional Alignment: For contested classifications (e.g., genocide, recession, inflation), map empirical evidence directly against codified statutory or specialist criteria (e.g., UN Genocide Convention Article II elements) rather than geopolitical statements from allied/adversarial state actors.
Module D: Game-Theoretic Bias & Funding Auditor
Apply game theory to evaluate the incentives of both the speaker and the data source:
 * Funding Trace: Cross-reference think tanks, NGOs, and polling firms against IRS Form 990 filings, OpenSecrets, FARA registries, and corporate donor disclosures.
 * Incentive Weighting: Calculate a Conflict_of_Interest_Multiplier (C_i \in [0.1, 1.0]). Data produced by an entity whose funding depends on a specific policy outcome receives a penalized weight unless independently replicated by non-aligned institutions.
 * Flip-Flop & Contradiction Detection: Compare current claims against the politician's own historical transcript vector database and voting/donor records to expose strategic deception.
2. SCORING MATHEMATICS: THE POLITICAL CREDIT SCORE
Claim-Level Verdict Vector
Each extracted claim c is assigned a veracity score V_c \in [-1.0, +1.0]:
 * +1.0 (Verified Fact): Supported by primary, statistically valid, multi-source specialist data.
 * 0.0 (Unsubstantiated / Missing Context): Cherry-picked timeframe, statistically underpowered (n too small), or relies on a single biased source.
 * -1.0 (Fabrication / Blatant Lie): Directly contradicted by primary empirical data or specialist legal/scientific consensus.
Politician Truth Score (S_p)
Scaled from 300 to 850 (mirroring FICO credit scoring):
 * w_i (Severity & Recency Weight): Claims regarding war, public health, economy, and human rights carry higher weight than trivial statements. Exponential time-decay ensures recent behavior impacts the score more than decades-old statements.
 * P_{\text{deception}} (Repeat Offender Penalty): Game-theoretic penalty applied when a politician repeats a claim after it has already been publicly refuted by primary data (proving intent/weaponization of the bullshit asymmetry principle).
3. TRANSPARENCY & USER INTERFACE (THE "BS METER")
 * Zero-Black-Box Citation Graph: Every rating must output a clickable JSON evidence tree. When a user clicks a "FALSE" or "SKEWED DATA" tag, the UI renders:
   * Exact quote and timestamp.
   * Direct link to the primary PDF/dataset (with page and paragraph highlights).
   * Statistical audit summary (e.g., "Flagged: Cited poll had sample size of n=45 and was funded by Lobbying Group X").
 * Real-Time Barometer: A visual gauge fluctuating from Spot On (Green / 750–850) to Spin/Skewed (Yellow / 550–749) to Bullshit (Red / 300–549).
4. PHASED ROLLOUT ROADMAP
| Phase | Scope & Deliverable | Core Technical Execution |
|---|---|---|
| Phase 1: Proof of Concept (PoC) — Asynchronous Transcript Engine | Static CLI & Web Dashboard analyzing historical transcripts of 2–5 high-profile politicians (e.g., Trump, Obama, Vance, Newsom). | Build the ingestion pipeline for existing text transcripts. Implement the Claim Extractor and programmatic Dorking agent (site:.gov / filetype:pdf). Generate the first static Political Credit Scores (300–850) with full clickable source trees. |
| Phase 2: Methodological & Funding Graph Integration | Automated Statistical & Bias Auditor. | Integrate Form 990 / OpenSecrets APIs to map think-tank and pollster funding. Train the parser to read study methodology sections and automatically flag low sample sizes (n), high margins of error, and non-specialist political opinions. |
| Phase 3: Browser Extension & Asynchronous Video Overlay | YouTube / Social Media Video Overlay Plugin. | Build a browser extension that ingests video captions on YouTube/X political ads and speeches, runs verification against the pre-indexed claim database + live dorking, and overlays clickable veracity tags directly onto the video timeline. |
| Phase 4: Full-Scale Real-Time Debate & Broadcast "BS Meter" | Low-Latency Live Stream Engine. | Deploy streaming ASR (<500ms latency) linked to a high-speed vector cache of pre-dorked primary datasets and live parallel search agents. Render a live, fluctuating "Bullshit Meter" barometer during televised debates with instant click-to-verify source cards. |
5. IMMEDIATE DEVELOPER EXECUTION STEPS (START HERE)
 * Initialize Repository & Schema: Set up a PostgreSQL + pgvector database with tables for Politicians, Transcripts, Extracted_Claims, Primary_Sources, Funding_Entities, and Audit_Logs.
 * Build the Claim Extractor Prompt/Pipeline: Write a deterministic extraction module that takes a raw speech transcript and outputs structured JSON containing only falsifiable empirical/statistical/legal claims.
 * Write the Dorking Tool: Implement a search wrapper that forces queries into primary document spaces (filetype:pdf, .gov, .edu, specialist international bodies) and strips out opinion journalism.
 * Run PoC Test: Feed 10 historical speeches into the pipeline, audit the extracted claims, compute the initial 300–850 Truth Score, and output the raw JSON verification tree.
```
