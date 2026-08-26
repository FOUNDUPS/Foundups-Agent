# TestModLog — Vote/Ballots FoundUp

<!-- WSP 22: anti-vibecoding test inventory. NEWEST entries at TOP. -->

## [2026-08-26] — Canonical Test Inventory Reconciliation

**Purpose**: Make the existing VOTE test surface visible before any worker creates or modifies tests.

**Rule for future workers**:
1. Read this file before writing a test.
2. Read `tests/README.md` for execution conventions.
3. Inspect the closest existing test file and extend/reuse it when it already covers the target behavior.
4. Create a new test file only when the behavior is materially distinct and cannot be expressed cleanly in the existing suite.
5. Update this TestModLog whenever tests are added, removed, renamed, or materially expanded.

### Current Active Test Files

| Test file | Primary coverage / reuse target |
|---|---|
| `test_fec_adapter.py` | FEC adapter factory, mock adapter, candidate/committee/contribution records, funding-summary adapter behavior, API/error boundaries, no-live-API/no-key test contract. Reuse for any FEC data-source or adapter behavior. |
| `test_entity_resolution.py` | Candidate-name/ID resolution, ambiguity preservation, state/office/party/cycle hints, no hallucinated candidate IDs, adapter error propagation. Reuse for candidate identity/disambiguation behavior. |
| `test_funding_summary.py` | Deterministic funding summaries, top-source ordering, source provenance, trail-termination markers, contribution breakdown, dark-money/foreign-funding truth boundaries. Reuse for candidate funding/influence evidence behavior. |
| `test_confidence_scoring_integration.py` | WSP 97 confidence labels, direct-source requirements, unknown/source-absent handling, trail-marker preservation, human-review triggers, high-risk claim boundaries. Reuse for production confidence-scoring integration. |
| `test_quick_answer.py` | Template-only quick answers, no-new-facts rule, three-line limit, confidence indicators, trail-stop display, human-review preservation, no persuasion/recommendation. Reuse for user-facing answer formatting from scored evidence. |
| `test_shell_integration.py` | Local pfMALL shell payload contract, route/app identifiers, evidence/answer preservation, display readiness, no route/manifest/catalog/public-launch mutation, no persuasion/microtargeting. Reuse for VOTE→pfMALL payload and gate-handoff changes. |
| `test_adversarial_influence_categories.py` | Adversarial influence-category separation: Israel-linked/AIPAC-linked/pro-Israel/foreign-national distinctions and anti-conflation rules. Reuse for influence-taxonomy and high-risk political classification changes. |
| `test_unit_confidence_scoring.py` | Earlier unit-level confidence rubric scaffold covering verified/high/low/unknown classification from source quality, diversity, contradictions, and direct filings. Treat as legacy/unit precedent; prefer the production `test_confidence_scoring_integration.py` surface for current runtime scoring unless the unit rubric itself is the target. |

### Package / Documentation Support Files

- `__init__.py` — test package marker.
- `README.md` — execution commands, suite boundaries, and this TestModLog preflight rule.

### Canonical Suite Evidence

The governance closure snapshot `docs/audits/architecture/VOTE_POC_CHAIN_OBSERVATION_SNAPSHOT_PHASE1.md` records the six-slice VOTE PoC chain as implementation-complete with **303 tests passing** on 2026-05-25. This TestModLog inventories the test files currently present on `main`; it does not invent per-file test counts or claim a new test run for the 2026-08-26 docs-only work.

### Duplicate-Test Prevention Decision Tree

```text
Need a test?
  -> Read TestModLog + tests/README.md
  -> Find closest existing test file
      -> same behavior/contract? EXTEND EXISTING TEST
      -> same fixture/pipeline but new edge? ADD CASE TO EXISTING FILE
      -> materially new subsystem/contract? CREATE NEW TEST FILE
  -> Update TestModLog
```

**WSP Compliance**: WSP 22 (TestModLog), WSP 50 (pre-action verification), WSP 84 (remember existing code/tests), WSP 97 (retrieve evidence before build).

---

## [2026-05-25] — Vote PoC Chain Closure

**Existing suite state recorded by canonical closure**:
- FEC adapter slice merged.
- Entity-resolution slice merged.
- Funding-summary slice merged.
- Confidence-scoring slice merged.
- Quick-answer slice merged.
- Shell-integration slice merged.
- Governance snapshot records `303 passed` for `python -m pytest modules/foundups/voteballots/tests/ -q`.

**Truth boundary**: implementation-complete did not mean publicly launched; the suite explicitly preserved no-public-launch, no-candidate-recommendation, no-targeted-persuasion, and no-microtargeting boundaries.
