# BTC anchor replay and realm integrity — 2026-10-25

Status: locally implemented, tested and independently reviewed; publication and
main readback remain parent-owned. The following allocation preceded authoring.
Parent source is the frozen P0C
candidate `b6d2cf31666e23707d84ca9adb154650cc2e1b24`, not a claim of main convergence.
WSP15: C3/I4/D3/Impact4 = **14/P1** while this is optional mock infrastructure.
Non-mock activation would require a separate P0 gate and actual effect design.

## Retrieval and decision

WSP00 session bootstrap is inherited; self=0102, role=worker,
origin=internal_handoff. Refreshed WSP00/97/15 and current simulator README,
INTERFACE, ROADMAP, ModLog, tests/README and tests/TestModLog before authoring.
Read current connector, epoch producer, Mesa consumer and both existing tests.
Simulator memory/README and requirements.txt are absent (requirements-sse.txt is
an optional SSE dependency owner). NAVIGATION has no dedicated connector entry.

Canonical owner query used the Git-common-directory-derived original root,
qualified Python with `-B` and `PYTHONDONTWRITEBYTECODE=1`. Query:
`BTCAnchorConnector publish_commitment content-bound replay commitment format realm database migration force confirmation tests`.
Result: `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`,
`freshness=UNKNOWN`, `index_gap_detected=true`; authority head
`a519f0ad758618c5d82f0ebf8b48a3c4a0eae7f0`, original-root workspace head
`0c81418fe94a7786cfd55f01e138ddc5d510583d`, owner_attempts=0,
workspace_overlay_present=true, no reindex or authority-worktree mutation.
Those heads describe the owner-query authority, not this managed branch.

Retrieval evaluation: generated training material and dated settlement promises
are noise; order current code/contracts before history. Missing memory and
requirements are explicit above. P0C v2 evidence supersedes old hash descriptions.
There is one connector/database/test owner; do not add a parallel ledger or
generic transaction framework. Exact contract and adversarial tests need source
inspection; no Qwen/Gemma model/provider startup is needed for this local repair.

First principles: preserve the existing optional mock consumer and make its
durable replay identity truthful. FAM payouts lack currency/asset/address units;
an unsigned Algorand adapter cannot infer those. Aggregate F_i caps need stake
liability/release policy. Those remain separate gates. This repair is not a
necessary Algorand-transfer dependency unless BTC evidence is later selected as
authority, and it neither grants entitlement nor verifies Merkle inclusion.

## Approved bounded contract

- Own only `economics/btc_anchor_connector.py`, Mesa's existing connector builder,
  `tests/test_btc_anchor_connector.py`, `tests/test_layer_d_anchor_runtime.py`,
  and existing simulator structured memory after source/test freeze. No generated
  manifests, security ledgers, dependencies, keys, Git or publication operations.
- Fresh inputs must be exact dictionaries with the complete known v2 scalar
  field set. Reject unknown/missing fields and unsupported/unversioned formats.
  Preserve the existing bad-status and bad-anchor diagnostic meaning.
- Require exact builtin types: nonempty identity strings, nonnegative epoch
  within SQLite signed64 capacity, nonnegative participant count, lowercase
  40/64-character hexadecimal hashes, literal pending labels, and exact bool
  force. Amounts accept finite nonnegative builtin int/float only; normalize
  integral floats and signed zero without rounding integers. JSON conversion
  failures reject before dispatch/database mutation.
- Timestamps must parse as timezone-aware UTC; retain the supplied text exactly.
  `Z` and `+00:00` are individually valid but different intent identities.
  This asserts neither freshness nor source authenticity.
- Copy/normalize the payload before the SQLite fence; canonical compact sorted
  JSON with allow_nan=False binds every known field and the mock realm. Store
  full canonical JSON plus digest, format_version and anchor_realm so later
  confirmation can validate the stored identity without a fresh input payload.
- Migrate inside BEGIN IMMEDIATE by adding nullable identity columns to the
  existing table, preserving UNIQUE(foundup_id,epoch). Old rows retain existing
  values and NULL identity fields: visible/unclassified, never inferred,
  backfilled, overwritten or promoted. Reopen and concurrent migration must be
  idempotent. Malformed/partial schema fails closed or completes only additive
  nullable columns; it must never manufacture row identity.
- One SQLite transaction compares/reserves one immutable identity and performs
  only deterministic, effect-free mock publication. Replace INSERT OR REPLACE
  with insert and identity-constrained updates. Conflict/foreign/legacy/pending/
  failed records never dispatch or overwrite, including with force.
- Preserve all 15 positive/validation case oracles except the explicitly unsafe
  non-mock coercion oracle. Exact same-content mock force still performs a second
  simulated publish, returns the same reference, idempotent_hit=False and count2;
  preserve first receipt/confirmation history. Exact non-force replay is a hit.
- Reject unsupported non-mock modes before DB side effects regardless of feature
  flag. Reject explicit singleton mode/path mismatch; no-argument reuse remains.
  Mesa must reject malformed selected modes instead of choosing mock.
- Only validated current-realm published/confirmed records with a matching mock
  reference may advance mock confirmations. Pending/failed/legacy/missing-reference
  records cannot become confirmed. Validate positive builtin confirmation counts.

This fence is safe only because the publisher is pure mock. It does not solve
future external-I/O ambiguity, process/power loss, signing, broadcast/recovery,
network identity or real confirmations. Do not hold it out as a future transaction
protocol. Actual publishing remains absent and disabled.

## Source budget and test-first gates

Existing connector is563 lines with inherited oversized class debt; shrink/reuse
that owner and do not increase its class span. No new product/test file. Keep
new/modified helpers small and cohesive. Mesa changes only its existing builder.

1. Run unchanged BTC/runtime owners under the same external offline runner and
   save exact baseline IDs, source hashes, failures and guard events.
2. Extend existing tests first: payload/version/hex/type/capacity/UTC/force
   rejection; all semantic-field conflicts with/without force; equivalent numeric
   retry versus textually different UTC timestamps; legacy additive migration,
   concurrent initialization/admission, restart, rollback and response loss;
   failed/pending/missing-ref/foreign-realm confirmation; constructor/singleton/
   Mesa mode rejection. Add current v2 metadata to existing fixtures; retain
   their assertion bodies where valid. Deliberately replace coercion expectation.
3. Save desired RED before production changes. Preserve setup failures separately.
4. Candidate focused owners, then adjacent epoch/parameter consumers; broaden to
   affected simulator scope only when justified. Use qualified Python -B/UTF8,
   disabled dotenv/plugin/cache/bytecode, external TEMP/DB/daemon paths and
   instrumented socket/DNS guards. This is not an OS sandbox claim.
5. Freeze source/tests with exact hashes; obtain independent source review and
   held-outs before structured-memory updates. Parent owns hosted CI, generated
   closure, security review, Git/PR and main readback.

## Local closure and retained history

Repaired focused211 and affected simulator513 pass with zero guarded network
and source drift; the same3 named SSE HTTP cases are deselected. Independent21
held-outs/source review pass. Counts overlap. Source remains two existing Python
owners plus two existing test owners; connector563→399 lines/class435→161.

Parent review reproduced duplicate-key replay from a supplied unsupported schema.
Six RED controls preceded constructor schema validation; required columns/types,
primary-key/nullability and canonical full uniqueness now validate before additive
identity columns. Legacy data is not rebuilt/backfilled. Earlier205/507 candidate
results do not qualify this repair. The initial legacy SQL fixture failure,
after-authoring corrected-fixture negative control, WAL race and external probe
path-oracle correction retain their exact timing in tests/TestModLog.md.

Parent verified prior epoch PR2192 at main
`7d3d7f64390762040bc2ca737ff0964d94d887c1`; local BTC evidence still originates
from the allocated P0C candidate, not a claimed execution on that later main.
No manifest/security/Git/PR or live chain/provider action was performed here.

## Pre-authoring documentation allocation — portable evidence packaging

Approved2026-10-25 documentation-only worker handoff, WSP15 **14/P1**
(C2/I4/D4/Impact4). Package the existing external handoff/run evidence into
`docs/architecture/receipts/FOUNDUPS_BTC_ANCHOR_INTEGRITY_20261025.json` and
its `.testcases.json` companion, reusing WSP97v1.1 receipt structure. Base
commit remains allocated `b6d2cf31666e23707d84ca9adb154650cc2e1b24` until parent
reconciliation. Frozen Python/test and structured-memory bytes are read-only.

Preserve exact cases, commands, exclusions, source-hash domains, isolation
limits and failure timing. In particular retain the SQL fixture setup failure,
later original-source negative control, WAL defect/fix, unsupported-schema
witness and6RED controls, and the independent Win32 physical-samefile oracle
correction. Counts211/513/21 overlap; three named SSE cases remain excluded.
Whitelist safe metadata; do not copy raw logs, source or opaque attributes.
Validate receipt structure, inventory parity and frozen source hashes without
rerunning product tests, scanners, models, providers or chain operations.
Parent owns source-manifest/security/Git/PR/main/publication gates. Packaging
completion is local evidence delivery, not completion of those gates or the
overall blockchain goal.

## Portable evidence packaging outcome

The WSP97v1.1 receipt and companion exact-case inventory are authored from the
external handoff,13 recorded pytest runs, original/qualified independent21
receipts, parent schema witness and retained setup/correction metadata. No
product/test rerun occurred. Recorded pytest commands are preserved; neither
independent21 receipt nor parent retained its exact argv, so that gap is explicit
rather than reconstructed. Interpreter, required root argument and both external
probe hashes remain available.

Receipt repository-evidence validation passes at actual allocated base/HEAD
b6d2cf31666e23707d84ca9adb154650cc2e1b24. This validates structure, canonical
WSP paths and base ancestry only; other evidence remains opaque. Exact-case
parity confirms211 focused IDs are contained in513 simulator IDs and the two
independent runs have the same ordered21 IDs. Current168 raw source hashes,
the four-file freeze and all non-plan handoff structured-memory hashes match.
No Git mutation, source, test, module-memory, scanner, credential, provider or
chain action was performed by the packaging worker. The receipt validator uses
read-only Git ancestry/WSP checks. Parent must reconcile/rebind and
rerun applicable gates before publication/main completion.

Artifacts:

- docs/architecture/receipts/FOUNDUPS_BTC_ANCHOR_INTEGRITY_20261025.json
- docs/architecture/receipts/FOUNDUPS_BTC_ANCHOR_INTEGRITY_20261025.testcases.json
