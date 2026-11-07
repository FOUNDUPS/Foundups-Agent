# TestModLog — Vote/Ballots FoundUp

<!-- WSP 22: anti-vibecoding test inventory. NEWEST entries at TOP. -->

## [2026-11-07] — Independent local Coalition draft contract

New Node `test_coalition_draft.mjs` covers a distinct browser-export boundary;
the existing Python funding/shell tests do not exercise it. The verifier froze
107 cases before reading implementation. Exact 11,914-byte prefix SHA256:
`8459db930f24ef51ed2e596c8f12d652ecbf215e7834a486cacb93288c9678b8`.
Initial 93 pass / 14 fail: export included out-of-contract `joined`/`reviewed`
fields. Separate probes reproduced deceptive raw authority and encoded-control
URLs. Seven appended cases preserve the original prefix and include a valid
default-port control. The final test SHA256 is
`4fc02770e67f29305e15e90c7b4f958e585c1a774154ff197fc2cd0b91c8631f`.
Final 114 pass, no skips. Cases cover fixed unverified/unsubmitted status,
strict consent, bounds, literal JSON text and URL confusion without a network
call or authority grant. CI runs the Node suite in `wre-verification-contracts`.
The unchanged Python Vote suite separately passes 398 tests.

## [2026-11-01] — Aggregate and displayed-confidence closure

Independent aggregate oracle29: baseline25 passed/4 failed; coordinator repair29
passed. Integration test SHA256 remains
`527c92634c47605a630886b6d3e983e5e938c0104acad9bb843fd8b4f651115f`.
One local worker proposed unchanged source in an invalid envelope and was rejected
without materialization. The original full scorer-only replay351 passed, but four
independent display probes exposed incorrect VERIFIED total wording/metadata.

Separate consumer oracle47 was frozen before consumer repair: baseline3 passed/
44 failed; repaired47 passed. Frozen quick-answer test SHA256
`a970c19c05a840a0a98f46ed555a634e368c1798270a38338c1633c68ee84223`.
All three formats and actual shell propagation are covered, including missing,
duplicate and invalid-label claims, lower/UNKNOWN and approved direct controls.
Two historical fixtures lacked their stated aggregate claims; add explicit claims
without changing assertions. Final quick-answer test SHA256
`96d7d8f30c2d4e3f0b0989c67cde17368116852ea70657b7554ddb792626576e`.
Independent final replay: frozen29/47 and full398 pass (overlapping scopes),
0.59s/0.30s/1.71s. No skips. Use the existing CI-equivalent command below.
This is source/test review, not native independent acceptance or retained RSI.


## [2026-11-01] — Production source provenance micro oracle

Extended `test_confidence_scoring_integration.py`:19 added cases and one tightened
missing-reference test. Three indirect types,12 lower/UNKNOWN controls, three
approved direct types and verified-facts consumption. Synthetic references only.
Frozen20: baseline16 passed/4 failed; local worker candidate13 passed/7 failed;
coordinator repair20 passed. Frozen test SHA256:
`898327ec40945318140abdea6ad547609ec325d4c6de42733dc1b7353e43a3f6`.
Independent full replay322 passed in1.77s, plus21 separately executed synthetic
probes (noncanonical types, repeated calls, mixed labels, input preservation).
Do not add overlapping scopes or equate legacy stub tests with production proof.
After that comparison, the indirect assertion was strengthened to exact HIGH and
`downgraded_from_verified_due_to_indirect_source`, both specified before inference.
Strengthened20 passed in0.60s; final test SHA256:
`1f3a6cc94bf1100eacfc6a2a4a237738df45e2facbaebccb51d1d214ed8f22f5`.
The independent reviewer reproduced two aggregate total_raised counterexamples;
that distinct pre-existing gap remains open in the module roadmap.

Reproduce the CI-equivalent module closure from root:
`python -B -m pytest -q --tb=short -c /dev/null --noconftest --import-mode=importlib -o pythonpath=. -p no:cacheprovider modules/foundups/voteballots/tests`
Use `NUL` on Windows; set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and
`PYTHONDONTWRITEBYTECODE=1`. No network, API key or model call is needed.

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
