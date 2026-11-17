# Research, verification, prioritization and project relevance

Apply this shared WSP 97 contract with the selected lane's specific research scope.
Research tools discover evidence; they do not certify their own answers. No prompt,
model, second-model agreement or checklist guarantees absence of hallucinations.

## Claim admission before writing

1. Establish cutoff date/timezone, previous issue coverage and research questions.
2. Search original-language and English sources; inspect actual source documents.
   Record coverage gaps, inaccessible/paywalled sources and failed retrievals.
3. Maintain a claim ledger: claim ID; exact proposed assertion; original URL/title;
   publisher/author; publication, event and retrieval dates; page/section or video
   timestamp; evidence type; supporting passage; limitations/conflicts; status.
4. Use statuses VERIFIED_WITHIN_SCOPE, ATTRIBUTED_CLAIM, ANALYSIS, DISPUTED or
   UNVERIFIED_LEAD. A company source proves what it announced, not that its claim
   is independently established. Multiple copies of one release are one source.
5. Check units, geography, phase, denominator, translation and causal scope. Seek
   independent corroboration for disputed/high-consequence claims and record
   counterevidence. Missing evidence means qualify, omit or retain as a lead.
6. For papers, read methods/results/limitations, identify DOI/version/date and
   peer-reviewed versus preprint status. Check corrections/retractions and whether
   geography, workload and assumptions transfer. An abstract is discovery only.
7. Before review, map every material factual assertion to ledger evidence. Recheck
   volatile claims before publication; unsupported assertions must not survive as
   facts. Preserve uncertainty in Japanese and English alike.

Primary sources include public records, filings, original research and firsthand
recordings. News reports and resident groups remain valuable, attributed evidence.
JHR retains OFFICIAL / REPORTED / COMMUNITY / ANALYSIS alongside verification
status; provenance category alone is not truth certification.

## Gemini / Google / YouTube source discovery

Reuse `modules/ai_intelligence/video_indexer/skillz/transcript_ask/SKILLz.md` and
`src/action_surface.py` in that owner for authorized owned-channel Studio Ask.
The inspected single-video path requires a known owning channel and usable Studio
edit surface. It does not establish access to arbitrary third-party news videos.
Do not launch portfolio indexing or a daemon for a newsletter research request.

Gemini in Google/YouTube may locate passages and source links through an available
authorized UI without a local Gemini model. Verify actual feature/session access;
do not assume it exists or install a model to imitate the UI. In Work use its
advertised browser skill, not repository Selenium or debugging ports. Elsewhere
reuse the owned action surface after its documented preflight; no ad-hoc scraper.

For third-party videos use public originals, accessible transcripts/captions or
the actually available supported research UI. Retain video ID, channel, date,
timestamp and language; verify quotations and numbers against the recording and
underlying document. An AI-generated summary is a lead, not independent evidence
or a verbatim transcript. Clearly flag unavailable transcripts and audio ambiguity.
Avoid circular corroboration between two model summaries of the same source.

Studio Ask/Gemini manifests retain requested/returned identity, response digest
and provider provenance, with retrieval_eligible=true and training_eligible=false.
Never turn Gemini output into 012 speech or training rows. Current Gemini API and
Whisper action IDs include registered-only routes: inspect implementation status
before relying on them. No live indexer execution is implied by this document.

## WSP 15 editorial ordering

012's explicit queue is JHR -> ROC -> Good/Bad/Ugly -> FoundUps/Eat the Startup.
Preserve it until redirected; do not fabricate scores to reverse-engineer it.
Within a piece, first admit evidence, then score candidate research/section work
with canonical MPS: Complexity + Importance + Deferability + Impact, each 1–5.
Record components, rationale and score in the brief; distinguish wsp01 APS, which
uses urgency. This is an editorial application of WSP 15, not a new formula.

MPS allocates attention and research effort; it does not establish truth or dictate
sentence order. Lead with the most consequential verified finding, then necessary
context, evidence, limitations/counterarguments and implications. Record when a
definition/dependency precedes a higher-scored section for reader comprehension.
High importance cannot promote an unverified lead into a factual headline.

## Project discovery through substance

Plan one relevant reader path in every brief: project, contextual bridge, useful
destination and reason. JHR can connect regional implications to proposed
eSingularity.ai/COGDC work; ROC to ownership and FoundUps.com; FoundUps to actual
GitHub implementation; group discussion to a relevant technical example.

Use a short case-study paragraph or restrained relevant link when it helps the
reader. Disclose project involvement; subtle means proportionate, not concealed
promotion. Never distort selection, omit contrary evidence or imply endorsement,
partnership or derivation to attract attention. The piece must remain useful with
the project link removed. If no honest connection exists, record NO_RELEVANT_LINK
rather than forcing a plug. Preserve eSingularity.ai, FoundUps.com and YUMORI.me.

## Google Docs collaboration and learning

Maintain one stable **master moshpit per lane**, including Good/Bad/Ugly as a
separate group editorial lane. Discover existing Docs and continuity first; reuse
an existing lane index rather than create a duplicate. A manuscript is not an
index: preserve its content and link it from the master. If converting an existing
document, add the requested index without deleting history or changing its ID.
Record NOT_FOUND_IN_CHECKED_SCOPE when an earlier draft cannot be recovered.

The master shows current issue/next action first, then newest-first issue history,
source/history links and private editorial session decisions. Each issue links
back to its master. New issues are prepended; revisions update the same issue.
Keep a stable issue key, Doc ID, status, verification time, approval state and
next action/owner. The Google Doc is the human-readable projection over existing
continuity, not a second runtime database. Keep actual private Doc pointers in
authorized private continuity, never public repository templates.

Use one Google Doc per issue as the authoritative working manuscript; discover
and reuse its existing identity before creating another. Follow the Docs skill:
fresh read before edits, preserve structure and collaborators' changes, make scoped
updates, read back the changed sections. Keep document ID/URL, section anchors,
revision/check time, evidence ledger and unresolved decisions in the issue brief.
If access is unavailable, retain an explicitly provisional draft and report the
blocker; do not claim a Docs update or silently appoint a new master.

Layer 1: research and suggest angle, evidence and outline. Layer 2: work through
opening and sections with 012; capture feedback and update the same Doc. Layer 3:
validate the final revision and route its exact approved copy to publishing.
Conversation edits become accepted manuscript only after the corresponding Doc
update is verified. Publication approval remains distinct from editorial feedback.

Keep a private linked session/change record: explicit instruction; previous draft
revision; correction; accepted revision; concise stated editorial reason; sources;
speaker/provenance; approval and retention/training eligibility. Preserve verbatim
012 feedback only when actually available and authorized; otherwise label summary.
Capture editorial decisions and observable outcomes, not private chain-of-thought.

Reuse Digital Twin `src/trajectory_logger.py` and its documented draft/action
contracts only in a verified authorized private runtime/store. Existing
`log_draft` has context, draft_text and accepted fields; a written skill does not
wire automatic capture. Record context metadata and actual approval truthfully.
Do not pass private sessions through a logger that feeds training automatically
without reviewing its storage/export behavior. Curated feedback capture, retrieval
memory, dataset admission and model-weight training are separate stages. For
unqualified dialogue exports retain training_eligible=false pending privacy,
provenance and quality review; the video transcript allowlist is not a dialogue
training contract. Do not run training or claim learned weights from this workflow.

The inspected video dataset builder has permissive early-return paths before
some eligibility/provenance checks. Do not rely on it to enforce dialogue exclusion
or inject session records through transcript-shaped inputs. The existing trajectory
logger is a training-data collector, so its storage/export path needs review before
use. This editorial contract does not repair either runtime implementation.
