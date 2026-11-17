# Reusable editorial review cycle

Status: local deterministic prototype; no provider, publisher, scheduler or WRE
promotion. This extends the existing source-backed content owner, not a second
publishing framework. FoundUps' AGI-as-scaffolding view is the project's design
perspective, not a demonstrated intelligence result.

## Existing owners and audit (2026-11-18 JST)

Baseline: `20a7044c018fcd4a033226db644360cd9b216242`.

- `campaign_brief.py`, `campaign_planner.py`: evidence/audience/brand inputs,
  proposed calendar and measurement join keys. Reused unchanged.
- `publication_reconciliation.py` and SOCIAL `action=reconcile`: source/edition,
  approval, delivery and unresolved-work consistency. Supplied assertions are
  not live readback. Reuse after actual placement; do not invent another ledger.
- `foundup_campaign_operator`: canonical prototype instruction owner. Extended
  with the reusable procedure below; not promoted in the WRE production registry.
- AI Gateway `model_combination_benchmark_harness.py`: held-out task/panel tests.
  The new adapter constructs its existing `ModelBenchmarkTask`; no new scorer.
- AI Gateway `model_intelligence_selection.py`, `model_runtime_binding.py` and
  `scripts/advisory_model_once.py`: model selection/admission and redacted advisory
  execution. No API key handling, routing override or paid call added here.
- `gemini_vision_analyzer.py` analyzes posting UI, not article evidence. It must
  not be presented as a working editorial critic. Gemini may supply a scoped
  review through an already authorized provider/session, with exact model/run
  evidence; its availability and cost are not assumed.
- WRE PatternMemory, existing performance/feedback ledger and publication owner
  retain persistence and admission. Supplied views/clicks are not measured
  improvement, and test fixtures are not provider observations.

Holo retrieval used the documented lexical fallback on the shared checkout;
freshness UNKNOWN, index gap true, overlay present. Broad retrieval was noisy
(deprecated WSP hits and unrelated audits); exact current-main files corrected
the stale checkout's missing November publication reconciler. No semantic
freshness, native model execution or whole-repository audit is claimed. WSP 00
bootstrap/strict gate ran on the host. This slice uses direct supervised work,
not a WRE-dispatched worker or authenticated independent verifier.

## API

```python
from modules.platform_integration.social_media_orchestrator.src.content.editorial_review import (
    evaluate_editorial_cycle, editorial_benchmark_task,
)

rounds = [{"author_id": "writer", "content": "Reviewed draft text goes here.",
           "assets": [], "reviews": []}]
pending = evaluate_editorial_cycle(brief, "selected_topic", rounds)
# Give pending context, actual image bytes/render and its revision to reviewers.
# Append their bounded assertions to rounds[-1]["reviews"], then evaluate again.
```

`brief` uses the existing `social_content_brief.v1`; `topic_id` must survive its
selected package/deduplication. The review artifact may contain up to30,000
characters of multiline long-form copy. It is not converted/truncated into a
LinkedIn post or a Substack payload. No Substack platform adapter is implied.

Each round has exactly `author_id`, `content`, `assets`, `reviews`. Up to12 assets
carry `asset_id`, lowercase64-character `sha256`, caption, alt_text, source_ids
(from this topic), and kind (`original`, `reused`, `illustration`). A supplied
hash does not prove an image was read, created by us or licensed. The reviewer
must inspect actual bytes and final phone/desktop crops.

Each review has exactly lens (`grounding`, `audience`, `writing`, `imagery`),
revision, reviewer_id, decision (`pass`, `revise`, `unknown`), notes, evidence_refs,
provider and model. References are opaque supplied evidence, not fetched URLs.
Use truthful labels for human/local review; never label a fixture as Gemini.
No reviewer may use the same ID as the author; this syntactic check does not
authenticate independence. Actual review provenance belongs to existing owners.

Every review binds full source-package, copy, assets/captions, author, iteration,
previous revision and versioned rubric. Changed copy/source/rubric invalidates
reviews. All four lenses must finish before refinement; missing/unknown lenses
stay awaiting_review. A revised round requires previous revision_requested,
changed content/assets, and fresh reviews. Three rounds maximum; unresolved
changes terminate at iteration_limit for operator intervention. All-pass means
awaiting_principal_review, never publication authority. Preserve draft/review
history in the authorized campaign record, not private research in public Git.

The pure helper is a Python entry only. The current SOCIAL command's prepare
and reconcile routes are unchanged. It does not automatically run critics or
rewrite text. This is deliberate layer-one scaffolding, not the requested fully
autonomous end-to-end system.

## Benchmark and feedback bridge

`editorial_benchmark_task(brief, topic_id, rounds, golden=...)` requires a frozen
independently reviewed `expected_output_digest` and `fixture_ref`. It returns the
existing AI Gateway task with a campaign-qualified identity and rubric digest.
Golden assertions remain supplied/unverified; the adapter cannot self-certify
them. Benchmark runner/verifier, authentic model evidence, costs and promotion
remain in their existing owners. Never derive expected output from a candidate.

Use topic-independent held-out examples, including unsupported claims, misleading
imagery, missing qualifiers, stale revisions and readable non-English copy. Freeze
acceptance before generation. Compare candidate/baseline with independent review;
do not promote a writer based on its own scores. Model/rubric changes require
re-evaluation. Test pass counts measure contracts, not literary merit or RSI.

After authorized publication, retain package/topic/revision plus actual provider
account/post IDs and observation time through the existing publication record.
Collect native impressions/clicks/conversions with scope/window/denominators,
unknown when unavailable. Compare matched observations, not synthetic traffic.
Only admitted, independently verified transferable outcomes enter WRE learning.
This slice retains the existing measurement join keys but does not collect or
persist analytics, schedule posts, or write PatternMemory.

## Acceptance and continuation

Frozen local gate: stale/cross-context reviews reject; all four lenses required;
bounded refinement; no unchanged candidate; asset/claim binding; exact supplied
golden benchmark target; no effect/authority on all-pass. Recovery is reverting
only this owned slice. Parent workflow owns substantive THA review and approval.

Next existing-owner work: authenticated model-review adapter with redaction,
budget and cancellation; actual image/render evidence; provider-native draft and
scheduling/readback; authentic metrics collection and admitted feedback. Exact
consequential copy/destination approval remains required. Missing primary sources
must stay unknown; no family-tree inference or numerical guilt claims from images.

Research/writing procedure: read source material first; identify the reader and
central question; separate verified facts, attribution and inference; lead with
the useful point; prefer concrete, plain wording; cut repetition; review structure
and context before line edits; inspect final rendered links/captions and mobile
layout. These are editorial criteria, not an invented universal quality score.

Primary editorial anchors checked 2026-11-18 JST:
[Digital.gov plain-language principles](https://digital.gov/guides/plain-language/principles)
for audience-first organization and clear wording, and
[W3C WAI image guidance](https://www.w3.org/WAI/tutorials/images/)
for purpose-specific text alternatives. These support the rubric, not factual
verification, causal claims or an assurance that a given article will perform.
