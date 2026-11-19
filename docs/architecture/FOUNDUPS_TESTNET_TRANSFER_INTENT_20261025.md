# FoundUps restricted TestNet transfer-intent plan — 2026-10-25

## Current-main reconciliation allocation — 2026-10-25

WSP15 C1/I4/D5/Impact4=14/P1; WSP22/50/84/97. Preserve frozen8723 product,
oracles and historical receipts. Reconcile published main0909b941 after PR2208's
38 successful checks and16-file/whole-tree readback against reviewed99f81820.
Read-only three-way review finds only ledger/root ModLog/test-registry shared;
no FAM adapter/ORM/migration source intersection. Retain all main-only changes.
Expected main-first exact approval union2,277; this approves no new finding.
Regenerate the existing registry for both new test owners, expected1,772/273.
Retain main's newest f427 manifest/pins and fixed1,471 member/cap boundary;
intent ownership is still outside that resident list. No source/caller/effect,
signer, schema, authority or oracle extension is allocated. Scope stays17 paths.
Require immutable parent-blob review, registry check and fresh hosted gates;
GitGuardian38962564 remains a separate unresolved public-commit classification.
The actual merge has two insertion conflicts: preserve both root-log sections
and the exact main-first2,277-entry ledger union. Registry regeneration/check
passes1,772/273 after resolving and staging; retain main's unchanged manifest
and pins. Prior TestNet qualification is historical source-bound evidence;
immutable parent review and fresh hosted checks are still required.

Status: repaired local runtime candidate frozen after173 passing controls; independent
review pending. No transport activation, publication or settlement qualification.

## Allocation and exact source

Parent allocation: WSP15 complexity3 / importance4 / deferability5 / impact4 =
16/P0. The missing prerequisite is a durable, explicitly denominated and
authorized probe instruction. The system cannot infer an asset quantity from a
unitless FAM reward. This allocation blocks advancing a restricted transport
experiment; it does not classify optional BTC anchoring as a transfer dependency.

Worktree: `C:/Users/user/.codex/worktrees/foundups-testnet-intents/Foundups-Agent`.
Branch: `agent/foundups-testnet-intents-20261025`. Observed HEAD and cached
`origin/main` are both `944127df3856c0be4a545fce926ac17b86320576`. These are
readback facts, not a live remote freshness claim. The earlier qualified research source was
`e6f2c2c7395a69cc5fc3c3c9637e1fe77cd85969`; do not relabel it as this base.

The supplied external research report has SHA256
`1f636ef906cb3009e624d95d4b7b635e2cd666048678870526acc8d3029261f5`.
Eight source owners and the six FAM module/test documents are byte-identical
Git blobs between that research source and this base. Current working files use
CRLF; their raw hashes differ, while LF-normalized hashes match the report.
The exact comparison is in host temp:
`foundups-testnet-intent-plan-c3806aa510aa45d1b7d8d7b9c37125b8/source_comparison.json`.

## Retrieval and existing architecture

WSP00 awakening ran in this worktree; the tracker returned
`is_zen_compliant=true`, coherence0.700. WSP97, WSP CORE memory requirements,
WSP15, WSP62, the master index and NAVIGATION were refreshed. Current FAM
README, INTERFACE, ROADMAP and test README were read; current/relevant ModLog
and TestModLog entries were refreshed without claiming a full reread of the
718-line historical ModLog. `memory/README.md` and `requirements.txt` are absent.

Canonical Holo owner query:
`agent_market durable pending payout SQLite transaction immutable transfer intent authorization treasury retry migration`.
It returned `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`,
`freshness=UNKNOWN`, `index_gap_detected=true`: authority
`a519f0ad758618c5d82f0ebf8b48a3c4a0eae7f0`, workspace HEAD as above. No reindex
or raw semantic search was run. Generation authority is not CURRENT.

Retrieval evaluation: historical blockchain plans add noise and are not effect
evidence. Current source/tests precede older proposals; direct scoped `rg` and
reads supplied missing test hits. The absent memory/dependency files are
recorded rather than invented. Git-blob comparison reduces staleness risk for
the reused report, but does not qualify runtime/network state. Duplicate
initiation/verification patterns are reused rather than copied into a ledger.
Manual source design plus independent agent review is appropriate here; loading
Qwen/Gemma or provider runtimes would add no authority or transaction evidence.

All following references are in `modules/foundups/agent_market/` on this base:

| Existing owner | Contract to preserve |
|---|---|
| `src/authorization.py:19–46` | Exact immutable CallerAuthorization; principal and exact FoundUp treasury grant. No issuer, expiry or revocation service. |
| `src/persistence/sqlite_adapter.py:131–164` | Stored VERIFIED task/proof/independent approved decision and positive reward identity. |
| `src/persistence/sqlite_adapter.py:210–282` | Complete pending-payout lineage, original compute debit and exact event cardinality; ambiguous history holds. |
| `src/persistence/sqlite_adapter.py:324–395` | One existing engine/Base/session; create_all precedes migration; session commits or rolls back. |
| `src/persistence/sqlite_adapter.py:647–677` | SQLite BEGIN IMMEDIATE admission, current authority, exact existing initiation retry. |
| `src/task_pipeline.py:261–273` | trigger_payout delegates initiation; task remains VERIFIED. |
| `src/persistence/orm_models.py:121–138` | Payout has integer amount but no asset/network/unit declaration. |
| `src/persistence/migrations.py:20–164` | Version2 and additive migrations; get_current_version opens another transaction. |
| `src/persistence/verification.py:16–22` | Existing extracted transaction owner imports adapter validators; reuse that dependency direction. |

NAVIGATION still includes a general verified-to-paid lifecycle label; current
persistent contracts above take precedence. TokenFactory has no Algorand
backend or transfer implementation. Its mock deployment/vesting operations
are not this transport API.

## Boundary and smallest alternative

Create one opt-in host facade in proposed
`src/persistence/testnet_transfer_intents.py`. It prepares one
`TEST_TRANSPORT_PROBE` tied to an already initiated, validated payout. It does
not run from trigger_payout, a daemon, HTTP route, simulator or TokenFactory.
There is no present authenticated production host caller for this facade;
the acceptance caller supplies trusted policy and authorization explicitly.

A parser alone would leave no durable consumer binding. Calling a new helper
automatically from initiation would change the existing contract and import
unresolved policy. A separate preparation facade is the smallest usable local
contract: it consumes the actual pending payout and commits a distinct record,
while leaving transport activation to a separately admitted host integration.
No adapter method or public root-package export is needed in this slice.

The row proves local preparation only. Payout remains INITIATED, reference and
paid_at remain null, task remains VERIFIED. No EventRecord has this transport
intent's payout_id or payload. No new compute debit, reward balance, account,
asset, reservation, issuance, vesting, conversion, BTC claim or PAID effect is
created. WSP26:98,107,269 describes bound/non-transferable UPS and FoundUp
tokens; external-exit proposals do not resolve that policy. A disposable probe
asset must not be described as UPS, F_i, redeemable, tradable or reward payment.

## Proposed immutable API and trust contract

Proposed explicit import: `persistence.testnet_transfer_intents`.

```python
service = TestnetTransferIntentService(adapter, host_policy)
intent = service.prepare(payout_id, actor_id, submitted_binding,
                         authorization=caller_authorization)
```

The service and its three record types are frozen/slots records. The adapter
reference is an existing repository; host policy and returned data contain only
immutable scalar fields and an exact frozenset of address strings. There is one
prepare method, no dispatch/update/confirm/delete/renew method. While current
authority and policy remain valid, an exact retry through a new service/reopened
adapter returns the original immutable record.
There is no JSON-to-policy or request-to-CallerAuthorization constructor.

`HostTestnetPolicy` is supplied by a trusted host composition root, separately
from submitted data. Its typed fields are:

- policy_id and positive policy_version; principal_id; exact foundup_id;
  payout_recipient_id; required role is fixed to treasury, not a requested role.
- network fixed to `algorand-testnet`, genesis_id fixed to `testnet-v1.0`,
  expected genesis_hash_hex, positive asset_id and asset_decimals.
- sender_address and expected_auth_address; exact recipient_allowlist.
- max_amount_atoms, max_fee_microalgos, expires_at_epoch_s.

`SubmittedTestnetBinding` repeats policy_id/version, format_version1, fixed
purpose TEST_TRANSPORT_PROBE, network/genesis/asset/decimals/sender/auth identity,
one recipient_address, amount_atoms, fee_cap_microalgos and expires_at_epoch_s.
All repeated identity fields and expiry must exactly equal host policy. The
stored payout recipient must equal policy.payout_recipient_id and the selected
address must be in the host allowlist. Amount and fee cap must be within the
host's respective caps. These are per-intent ceilings, not an aggregate budget.

CallerAuthorization is checked on every prepare, including retry, against the
explicit actor, policy.principal_id and stored task's exact FoundUp treasury
grant. Policy FoundUp must equal stored FoundUp. Profiles, admin labels, compute
payment, repository ownership, a client's policy-shaped object or a matching
ticker confer no authority. A Python frozen type is not proof of host origin:
production must resolve current policy/grants outside untrusted deserialization.
Existing CallerAuthorization has no issuer signature, expiry or revocation
mechanism; calling it fresh does not prove those properties.

Numeric admission uses exact built-in int, excluding bool and coercible text:
amount, fee cap, asset_id, policy_version and expiry are positive and at most
2**63-1; format_version equals1; asset_decimals is0..19. No float, unit scaling,
rounding or reward_amount conversion. Native fee units are explicitly
microalgos; asset amount units are atoms of the bound asset. The fixture will
deliberately use a probe quantity different from reward_amount.

Identifiers and addresses are exact nonempty bounded strings; no trimming,
case-folding or aliases. FoundUp/actor/payout-recipient/policy IDs are <=64
characters. Addresses are <=128; genesis hash is exactly64 lowercase hex.
Bounded text is syntactic input only. Policy and submitted objects must have
the exact expected types; no extension/unknown-field map is accepted. Canonical
serialization uses known keys, sorted keys, compact JSON, sorted allowlist and
no float values. Text spellings and policy version remain part of identity.

The host genesis and sender/auth/address strings are configured expectations,
not node, checksum, key-control, rekey-state or asset-metadata verification.
No SDK is added. The next transport gate must independently verify actual
TestNet genesis, asset ID/decimals, address checksums/opt-in, sender/auth control,
funding and fees before unsigned preparation/signing. No non-TestNet fallback
or relabeling is permitted. Expiry uses host UTC Unix seconds sampled inside
admission via the existing clock; expired or changed policy rejects retries.
No local expiry-extension or revocation update is introduced. Admission samples
the host clock once under the lock; reject now_epoch_s >= expires_at_epoch_s.
The same sample supplies a new row's creation time. Retry preserves the original
creation time. Lost response followed by expiry retains the committed row and
rejects retry; it cannot renew or create another intent.

## Proposed durable schema and transaction

One additional `TestnetTransferIntentRow` on the existing ORM Base, table
`testnet_transfer_intents`; no second Base and no EventRecord mirror.

| Column | Bound contract |
|---|---|
| intent_id | String64 primary key; generated only after validation. |
| payout_id, purpose | Non-null; UNIQUE(payout_id,purpose), fixed probe purpose. |
| format_version, state | Non-null version1 and PREPARED only. |
| foundup_id, task_id, actor_id | Non-null String64, mirrored exact lineage. |
| identity_json | Non-null canonical text with known policy, binding and lineage keys. |
| identity_sha256 | Non-null lowercase hex of those exact UTF-8 JSON bytes. |
| created_at_epoch_s, expires_at_epoch_s | Non-null signed64 host time/expiry. |

The identity includes payout_id, validated initiation_event_id and a canonical
digest of its complete validated payload, FoundUp/task/recipient identity,
actor, purpose/version and complete host policy plus submitted binding. Raw
proof notes and artifact contents are not copied; the existing event remains
their owner. No signed bytes, key material or transaction ID is stored. Compare
complete canonical content on retry, not only a digest. On row read, validate
known keys/types, digest, mirrored columns and PREPARED state before returning.
Return an immutable scalar DTO including original ID, canonical identity,
digest and timestamps, not the ORM row or a mutable nested dictionary.

Migration3 is additive CREATE TABLE plus its uniqueness/check constraints;
canonical v2 data is preserved. No automatic legacy backfill, repair, deletion,
reconciliation or grant creation. Existing create_all can create the physical
table while a database remains pinned to version2 or migrations are disabled.
Therefore preparation requires recorded schema version exactly3 AND qualified
actual columns/types/nullability/primary key and unconditional uniqueness on
exactly(payout_id,purpose). Missing/partial/noncanonical tables fail closed;
CREATE TABLE IF NOT EXISTS alone is insufficient. Unknown future versions are
unqualified. No silently rebuilt table or partial-index substitute. Types use
SQLite TEXT/INTEGER affinities: VARCHAR64 and TEXT string declarations are
equivalent. No exact CHECK-source spelling comparison is required; malformed
uniqueness witnesses otherwise include the canonical version/purpose/state
checks so their rejection cannot be attributed to missing checks.

Transaction order uses actual existing seams:

1. Reject non-SQLite dialect before opening a session; never fall back.
2. Enter adapter.session(), execute BEGIN IMMEDIATE and inspect schema/version
   through that same session. Do not call MigrationManager.get_current_version
   inside the lock: it creates another write transaction.
3. Load payout and its task; require current actor/policy/CallerAuthorization
   binding before writes. Missing payout raises NotFoundError. Validate policy,
   binding, caps and expiry. Schema/input/conflict failures raise ValidationError;
   authority failures use PermissionDeniedError.
4. Reuse _payout_history(sess, task.foundup_id), including its existing stored
   identity/independence validation. The requested payout must be in that checked
   history. Its initiation actor must also equal the currently authorized actor;
   no actor takeover of an already initiated payout is introduced.
5. Build the canonical detached identity. Query the unique payout/purpose row.
   Exact existing content returns its original immutable result with no writes;
   any conflict or malformed stored record rejects without overwrite.
6. Otherwise add and flush one PREPARED row using adapter._next_id. The existing
   session owner commits before returning. Every failure rolls back this row;
   no initiate_payout, _stage_payout, compute or event method is called.

BEGIN IMMEDIATE serializes two independent adapters before identity admission;
the unique constraint backs that invariant. Identical racers converge to one
ID; conflicting racers preserve one winner. After a lost response, exact retry
reopens that same record while authority and policy remain valid. Expiry leaves
the durable row intact but blocks this API; no historical-read/renewal API is
included. Lock errors propagate without fallback or partial
row, following the existing pending-initiation convention. No external I/O
occurs within this transaction, and this fence makes no claim about future
network exactly-once execution or crash recovery after broadcast.

## Bounded source and acceptance allocation for review

No code release yet. Proposed source limits are ceilings, not line targets:

| Owner | Proposed bounded change |
|---|---|
| New persistence/testnet_transfer_intents.py | <=260 lines total, <=8 authored functions/methods each<=40; three frozen scalar records plus frozen facade; no class>200. Target220–250. |
| Existing persistence/orm_models.py | One row, <=35 net lines; existing13 mapping identities unchanged. |
| Existing persistence/migrations.py | Version3 and additive schema, <=40 net lines; no migration-manager rewrite. |
| Existing sqlite_adapter.py | Zero intended growth; remains1131 lines, below inherited1330 ceiling. Any required delegation requires new prior allocation, <=12 lines maximum. |
| New tests/test_testnet_transfer_intents.py | One cohesive contract owner initially<=240, then<=390; final pre-product refinement<=405 below. Fixed fixture/helpers; no provider/model imports. |
| Existing tests/test_sqlite_adapter.py | <=12 net lines to explicitly include the14th table/mapper while retaining all13 old alias and pickle assertions. No set-equality weakening. |
| Existing tests/test_migrations.py | Existing default/latest/idempotence controls retained; v2-to-v3 physical-table/pin cases can live in the new intent owner. |

This adds a distinct durable contract/test owner because existing initiation
tests assert payout/debit/event state rather than transport identity. It is not
a generic ledger, transaction engine, backend or second registry. Helper budget
must cover validation, canonical content, schema qualification, lineage read,
row comparison and one transaction; if readable code cannot fit, report actual
pressure before expanding. No compressed control flow to satisfy a line cap.

The24 acceptance criteria below are contract families, not a claim of24 pytest
collected nodes. Exhaustive field/type matrices will expand that count; freeze
the exact IDs and count for parent review before RED. Keeping every field bound
is preferable to hiding a coverage reduction behind the approximate case budget.

| ID | Required observation |
|---|---|
| A01 | Authorized prepare creates one PREPARED intent with explicit units; all13 old tables remain byte/value equivalent to their post-initiation snapshot. Quantity deliberately differs from reward. |
| A02 | Exact retry returns the original complete DTO/ID/time and does not change any row. |
| A03 | Adapter close/reopen plus exact prepare returns the original durable record. |
| A04 | Original payout retry, a later legitimate task in the same FoundUp and its initiation still satisfy the old assertions after probe preparation. |
| A05 | Absent authority rejects before intent writes. |
| A06 | Dictionary/profile-shaped authority or request-shaped policy cannot confer grants. |
| A07 | Actor, current principal, policy principal and original initiation actor must agree; a separately legitimate different treasury principal still cannot take over. |
| A08 | Wrong FoundUp grant, role or policy scope rejects; no wildcard/admin/compute inference. |
| A09 | Every network/genesis/asset/decimals/sender/auth identity field is exact; non-TestNet and mismatched host/submitted identities reject. |
| A10 | Purpose, format version, policy ID/version and exact expiry are bound; changing one on retry cannot replace the intent. |
| A11 | Payout recipient mapping and recipient allowlist both apply; client strings do not prove wallet ownership. |
| A12 | Amount and policy numeric boundaries reject bool, text, nonfinite, zero/negative and >signed64 values before SQL effects. Valid positive integer endpoints do not undergo float conversion. |
| A13 | Fee, decimals and timestamp boundaries reject invalid types/ranges; zero decimals remains valid. |
| A14 | Amount or fee above host cap rejects; their exact cap endpoints remain admitted. |
| A15 | Expired policy rejects first prepare and retry without changing the prior row; there is no automatic renewal. |
| A16 | Malformed persisted identity, changed digest or mirrored column/state rejects without overwrite. Returned DTO and policy/binding cannot be changed through ordinary nested mutation. |
| A17 | Existing corrupted proof/decision/task/event/compute history fails through its old validator, before intent creation; no historical issuer/grant provenance is invented. |
| A18 | Missing/uninitiated payout and non-SQLite adapter reject; no implicit initiation or adapter fallback. |
| A19 | Canonical v2 upgrades additively; repeat migration is idempotent; pinned v2, disabled/unrecorded migration and unknown future version do not gain admission merely from table presence. |
| A20 | Missing required columns or absent/partial/wrong-key uniqueness rejects even when rows look valid; no silent schema repair. |
| A21 | Injected failure after the actual intent INSERT rolls back; reopen shows no intent and unchanged old tables. |
| A22 | Lost response after commit recovers the same record; busy writer rejects without fallback and can retry after release. |
| A23 | Two adapters preparing identical content concurrently return one durable ID with one row and no other effects. |
| A24 | Two adapters racing conflicting content preserve one immutable winner and reject the other; reopen preserves the winner. |

Reuse `_ready_payout` at test_persistent_compute_wiring.py:127, then explicitly
trigger the authorized initiation before snapshotting. Reuse fixed external
authority fixtures and the existing snapshot/row helpers: no grants derived
from an actor under test. Existing rollback(:291), race(:318), lost-response
(:507), busy-writer(:562) and legacy-history assertions remain unchanged.
Snapshot all old tables and schema migration state as appropriate; permit only
the intended new row in positive preparation. Existing exact ORM inventory
assertions explicitly grow to14 mappings, preserving old compatibility checks.

## Execution gates and remaining transport work

Runtime release requires parent review of the frozen API, schema and expanded
RED inventory. Sequence: unchanged bounded baseline; new acceptance RED before product;
candidate GREEN; independent held-outs/source review; affected FAM closure.
Every runner must use the qualified Python -B/UTF-8 interpreter, disabled
dotenv/plugin/cache/bytecode, guarded sockets/DNS and scratch databases/TMP
outside the checkout. No default daemon path, provider/model, SDK installation,
key inspection or chain call. Record exact IDs/results, setup failures, source
hash domains and network attempts. The initial planning pass ran no FAM tests
or runtime probes.

After source freeze, module/test memory updates and source-closure membership,
pins, caps, derived artifacts and exact security findings are separately
measured/allocated by the parent; no automatic cap or exemption increase.

A later, separately authorized transport slice must confirm actual public
TestNet/asset/account facts, authenticate host policy issuance/revocation,
prepare unsigned native transaction content, define signer custody, bind
transaction identity/expiry/fee and persist broadcast/confirmation recovery.
It must revalidate policy, balance and network conditions before effects; this
PREPARED row is not an executable authorization lease. Physical confirmation
still cannot change the original unitless reward to PAID without a separately
resolved unit/asset/economic settlement contract. No claim that blockchain work
or TestNet operation is complete follows from this layer.

## Test-only release and chronology

Parent accepted the contract and released unchanged baseline plus acceptance
test authoring only. With FOUNDUPS_SKIP_POST_COMMIT=1, the authorized fetch and
fast-forward preserved this plan and advanced HEAD from the initial944127df
base to `6fe7eba424c17f7813043dfb104cd845617cab38`. All eight FAM owners and six
module/test documents remain Git-blob identical to the e6 research source;
`source_comparison_after_main.json` in the same host-temp directory records the
new readback. A fresh Holo query again rejected the authority/root HEAD mismatch
with UNKNOWN freshness and gap=true; the untracked plan is a workspace overlay,
not qualified semantic evidence.

Before adding declarations or tests, the external guarded runner executed the
unchanged pending-payout, SQLite ORM and migration suites:80 passed, two inherited
inactive asyncio-option warnings, zero guarded network or forbidden runtime
imports, stable raw source/test hashes. Receipt: host-temp directory above,
`baseline/receipt.json`. This is baseline evidence, not intent implementation.

Parent then expressly released a declaration-only scaffold <=95 lines: four
frozen slots declarations (policy, submitted binding, prepared result, facade),
imports and one prepare method raising NotImplementedError. No validator,
helper, SQL, schema, ORM row, effect, adapter/root export or runtime implementation
is released. Acceptance RED will bind these added API declarations; it must not
be described as a wholly unchanged-product baseline or collection-error proof.
The exact declaration hash and expanded test IDs will be recorded before RED.

Before canonical test authoring, a readable external draft measured315 lines
and22 test functions (76 projected collected nodes), with additional migration,
busy-writer, expiry and uniqueness controls still needed. Parent expressly
revised only this test owner's ceiling to390 lines, <=26 test functions, each
<=50 lines. No generic fixture framework, separate fixture file or old-oracle
weakening is authorized. The runtime260-line/eight-function/40-line limits,
ORM+35, migration+40 and adapter+0 allocations remain unchanged. External draft
setup/oracle corrections precede canonical copy and RED; they are not executed
failure evidence. Scaffold:74 lines, SHA256
`c8b39b3112736a09ccbf2ff7d7ac92828b8bc218580165400137ec24021bca02`;
declaration_receipt.json verifies four frozen slots classes, one raise-only
method and all original tracked FAM owners unchanged.

Before the first behavioral RED, the final acceptance owner froze at381 lines,
26 test functions and89 collected nodes, no skip/xfail markers. SHA256
`dbddc0200c8d156eb97f7c60c24b3bd29d2d6ce0fe1e862a23d511a00e9c2bb4`.
The exact IDs and per-function AST hashes are in acceptance_inventory_v1.json,
SHA256 `5d9a1bbff85a1bff4f088281f1d8f0d4073147244e914c9b4ff7257ceb255d02`.
An initial88-node collection was extended with stored self-verification rejection
before any RED; no collection or fixture/setup failure is being erased.

First desired-contract RED against the declaration-only facade:89 failed,
80 unchanged baseline tests passed, two inherited inactive asyncio warnings.
All89 failures were call-phase:88 NotImplementedError and one expected missing
schema-version assertion (migrate still returns2, contract requires3). There
were no collection/setup/teardown failures, guarded network attempts, forbidden
imports or raw source/test drift. This proves unimplemented acceptance behavior,
not an unsafe deployed admission path or a live custody exploit.
Receipt: host-temp red_contract_v1/receipt.json, SHA256
`eae18a49209e9520c46e92602213030b556fa2681c0083bc9539d4790942fe76`;
full captured output is red_contract_v1_output.txt. Original eight FAM sources,
ORM/migration files and existing baseline test assertions remain unchanged.
No runtime implementation is authorized by this result; parent review comes next.

Parent's pre-product review clarified two test contracts before runtime release.
The legacy _ORM_TABLES dictionary remains exactly13 mappings: old-table snapshots
assert that length, and future ORM inventory changes may only union the new
table/mapper in the two set-equality assertions. Alias and pickle loops remain
unchanged; no new sqlite_adapter alias is needed.
The actual constructor keywords are schema_version=2 and auto_migrate=False.
Parent approved both explicit configurations in the existing fixture for the
migration test only, with fixed trusted authority unchanged. Snapshot handling
records an absent schema_migrations table without creating it. Rejection is
checked before removing the new physical table; an explicit migration must then
create it and preserve old rows. This supplements synthetic version deletion.
The first89-node RED/source/inventory remain preserved; the clarified inventory
and second RED are separate evidence, still before runtime implementation.

The second inventory froze90 nodes/385 lines/26 functions, SHA256
`f4d904360501fa25fcc327a696b694de41962055f7b78d8a16eb6441c30b40a3`.
Second RED:90 call-phase failures against the raise-only declarations and80
unchanged compatibility passes, zero guarded network/import attempts or drift;
red_contract_v2/receipt.json and acceptance_inventory_v2.json remain separate.
Before any runtime implementation, independent review requested elapsed valid
retry/reopen (NOW+1), complete identical-racer DTO equality, explicit conflicting
loser ValidationError, complete persisted winning DTO content and durable winner
retry after reopening. Parent allocated the measured refinement at<=405 lines,
still26 test functions each<=50, before these edits. No generic schema framework
or broader policy is added. All earlier RED and source snapshots are retained.

Final pre-runtime test freeze:397 lines/26 functions,90 collected contract cases,
SHA256 `ed58302f1b62526358cb7d2129fe578fd6c4b76a5ff4d4a5b3a082ecbb7b2dd7`.
acceptance_inventory_v3.json SHA256
`c51e94a69db0bc5cf12e2b4067d34ef44b419eba9f84425c672029c078e51be2`
records exact IDs and ASTs before execution. Third RED:90 call-phase
NotImplementedError failures,80 unchanged baseline passes, two inactive asyncio
warnings; no setup/collection/teardown failures, guarded network/import attempts
or source drift. red_contract_v3/receipt.json SHA256
`0f5c3ac1103882928ae1b2cc4c5b11b54ed9c58e79992b5eaf8d24a04d3d1a8a`.
test_only_handoff_v3.json summarizes all three preserved runs. Independent
read-only review of these exact397-line test and74-line declaration hashes
reported no material unresolved issue; it did not run tests or qualify runtime.
The original eight FAM owners and all existing baseline assertions are still
unchanged. Runtime, ORM and migration authoring remain unreleased.

## Runtime release before product edits

Parent reviewed and accepted the exact v3 contract and90-case RED plus80
unchanged compatibility passes. Runtime authoring is now released for this
16/P0 probe-only contract: existing declaration owner<=260 lines, <=8 authored
functions/methods each<=40; one ORM row<=35 net lines; migration3<=40 net lines;
only the two explicit table/mapper unions in the existing inventory test.
The old13 dictionary, alias/pickle loops, adapter and frozen acceptance tests
remain unchanged. Reuse current scoped authorization, _payout_history, one
same-session schema/version fence and the existing session commit owner.
No broader state/economic/transport/SDK/effect work is authorized. Report
readable measured source pressure before expanding a ceiling. Run the frozen
v3 plus80 controls, then freeze passing source for independent review before
broader FAM qualification. No Git publication or derived artifact changes.
New main outside this lane has advanced; no merge during product authoring.

## Passing runtime candidate freeze

The first implementation run passed170/170:90 frozen v3 contract controls and80
existing pending/ORM/migration controls, two inherited inactive asyncio warnings.
Zero guarded network or forbidden runtime imports; raw hashes stable during the
run. Frozen v3 acceptance source is byte-identical. Runtime owner232 lines,
eight authored functions with maximum31 lines; ORM+24 net, migration+23 net,
adapter+0. All13 original ORM class ASTs, legacy mapping dictionary and pickle
test ASTs are unchanged; the existing inventory has only the two explicit unions.

Runtime raw SHA256
`86c01c12f45acb41999e4b0fd45298c3cab6a370c9854778d92f0ff5652203da`;
ORM raw `349defcfd9ab0c8cd6f4065498a31078840c12d734f173a4517658aed3f80a01`;
migrations raw `ac07db235215bcda94bc9e35cabac138bd2282e3139d40e175b5a8336278bd54`.
The runtime is LF; existing owners retain their working CRLF domain. Exact raw
and normalized pins, function sizes and preservation checks are recorded in
runtime_freeze_v1.json in the same host-temp evidence directory.
green_candidate_v1/receipt.json SHA256
`c30a562b435ad939325d71f838e2cfa4b8393ab0d5241d96d01d24ba13bad40f`.

The implementation validates exact record types and builtin field values before
serialization, reads actual schema and current grants under BEGIN IMMEDIATE,
compares full canonical policy/binding/lineage content on retry and inserts only
the new intent row. It neither mutates the existing payout nor writes a payout
event. Stored schema qualification additionally rejects intent-table triggers
and requires BINARY business-key collation to avoid accepting unsupported
persisted effects or aliases. No generic schema engine is introduced.
Source is frozen for independent held-outs/review before broader FAM tests;
this result is local preparation evidence only.

## Independent schema finding and narrow repair allocation

Independent review/probes on the exact86c01c runtime reported14 passes/one
failure, zero guarded network/import/dotenv attempts and stable source pins.
Receipt: `C:/Users/user/AppData/Local/Temp/foundups-testnet-intent-independent-v1-20261025/receipt.json`,
SHA256 `f75d8f8d1356705c3c295b4c04ce5f322f8fb62f652b31cdc272d82e861282bd`.
pragma_table_info omits generated columns: an otherwise canonical supplied DB
with an extra VIRTUAL generated column was incorrectly admitted. This is a real
schema-contract defect in supplied/altered persisted data, not custody-exploit
evidence. The first170-pass run and failed independent witness remain preserved.

The independent genuine second task/proof/independent decision in f_1 passed.
The original90 tests used suffix2/f_2 for the later-task case; they must not be
relabeled as same-FoundUp coverage. Parent accepted correcting that fixture via
real existing create APIs/fixed grants, preserving the old other-FoundUp branch
as another parameter. This correction follows initial product authoring; no
retroactive test-first claim is made.

Before canonical edits, parent allocated a narrow regression-first repair:
two schema variants (extra VIRTUAL generated column and required non-PK column
replaced with generated content), then only table_info to table_xinfo and
explicit hidden==0 within the unchanged runtime260/8/40 ceiling. Crossed
messages first allocated test420, then425 to retain both compatibility branches
and both generated controls; still26 test functions each<=50, no framework or
other scenarios. The readable external draft measures422 lines and projects93
contract cases plus80 compatibility cases, superseding the92-case estimate.
Schema rejection must precede new ID allocation/INSERT. Existing source remains
86c01c until these controls are frozen and RED is recorded.

Repair inventory froze93 cases/422 lines/26 functions before the checker edit,
SHA256 `16d2963cfcb5d39ef0ca6b468ff8b39109d651390bbe03b841e7ab0d28372b3e`.
On unchanged86c01c runtime: one failed/172 passed, zero setup errors, guarded
network/import attempts or drift. Only extra-generated-column failed, reaching
the test's explicit forbidden-ID-allocation guard; required-generated-column
already rejects because table_info omits a required field. Both positive
later-task branches passed. This supplements the independent actual-admission
witness; it does not relabel every new control as originally failing.
Evidence: acceptance_inventory_v4.json and red_generated_column_v1/receipt.json
in host temp. The tiny allocated schema checker repair follows this RED.

After only table_xinfo/hidden==0 checker edits, GREEN173/173 (93 contract plus80
compatibility), two inherited inactive asyncio warnings, zero guarded network
or forbidden imports and no raw source/test drift. Runtime233 lines/eight
functions/maximum31, SHA256
`d6a9bc8ec4cd82a767e37898cc4f5ee1eaecfd023e22de675f60d015f40056bc`.
ORM/migration/adapter pins remain unchanged from the first runtime freeze.
runtime_freeze_v2.json SHA256
`b856ceac9217ad5e8fe5eca9e8927da1b708a54793a7582b6056937e0428d6dc`;
green_candidate_v2/receipt.json SHA256
`239b7ba5909782cbfc14e50e96d2636513f5efadcd5cc78c29ba7644068f3231`.
The independent reviewer will replay the same15 probes on repaired pins,
retaining its original14/1 result. Broader FAM qualification still waits.

## Parent local qualification and publication preparation

The preceding checkpoints are historical. Repaired independent review passes
all 16 cases: the same original 15 plus one explicitly later STORED generated
column control. Its raw receipt is
`foundups-testnet-intent-independent-v2-20261025/receipt.json`, SHA256
7513dd853f2caedfbe2396ab0b4959ec068e805570873f4c48266de95e8873a4.

The agreed whole-directory FAM qualification passes all 459 cases across 19
actual test owners, without skips, exclusions or AST projection. Both pytest
and the separate qualification verdict are zero. All 203 prebound source files
and six repaired-freeze pins stay unchanged; 1,061 audited SQLite connections
remain in external scratch or memory, with zero recorded guard attempts and
unchanged default-store size/mtime observations. Real central configuration is
in scratch before FAM imports and remains stopped. Only optional help enrichment
returns None; neither the FAM constructor nor its supplied paths are rewritten.
Two inherited inactive asyncio configuration warnings remain. Final raw receipt:
`foundups-testnet-allfam-prepared-09c1d91256b348318197b70bfaa36fcb/all_fam_repaired_candidate_v2/receipt.json`,
SHA256 adf80cd88de5c17552a1851dee4ce691a189eef58f2e16ed8d71b5bdb0301b91.
Parent independently rehashed all 203 inputs and checked the confined connections.

Preserve two other broad runs separately. A competing run with forced optional
central ImportError is diagnostic only. The agreed runner's first run passed
the same 459 assertions but failed qualification because 20 bridge imports had
not been prebound. An inventory-only correction from 183 to 203 files preceded
the fresh qualified run; assertions, guards and product source were unchanged.
These runs overlap, and the focused 173 cases are a subset, not additive totals.

Source commit 800d6f5ccd4ae7b6249fc0773e51878473f564e1 records only the five
allocated source/test changes. The unchanged SQLite adapter and original 13
alias/pickle contracts remain evidence. Canonical test-registry check first
reported stale after tracking the new test; generation and recheck now report
1,771 test files, 273 quarantined. Exactly one unit-test entry is added; every
old entry, owner, capability and quarantine decision remains unchanged.

Read-only source-closure assessment finds the persistence branch absent from
the currently installed resident dependency graph. It predicts no manifest
member/count/pin delta for this explicit module API; final canonical checking
after main reconciliation remains required. Do not add artificial imports,
roots or byte-cap increases to manufacture installed capability. Local source,
resident integration, authenticated host issuance, real network facts, native
transactions, signing and confirmed settlement remain separate gates.

Evidence/docs packaging is a separate 14/P1 allocation. Independent review
found malformed diagnostic source-map paths and a raw-versus-LF validator hash
label. A subsequent metadata repair shadowed a receipt path with a source path.
All rejected packages and original raw receipts are retained. Corrected package
publication waits for fresh independent verification of role-specific paths,
digests, normalized map identities and exact case outcomes. No test result or
runtime source is changed to repair this metadata. WSP97 receipt validation
checks structural/path/base ancestry only, not evidence authenticity or effects.

Corrected portable package v3 passes independent review with no material
findings. All 12 run receipt descriptors and 27 artifact bindings equal the
original records; 46 diagnostic path normalizations have explicit provenance
and independently verified current raw hashes. Main/companion bindings, exact
case outcomes, 203 final source pins, six raw/Git LF candidate pins and the six
updated docs agree. Both rejected drafts remain external. Review raw SHA256:
99ecd7882243fcd6bf46141a3d888cd83b1ddf3a9cfd687e9ed7b6a42fd7f58d.
Parent copies the exact reviewed receipt and case companion into
`docs/architecture/receipts/`; hosted CI/security, final main reconciliation and
dedicated PR publication/readback remain required. No new test run is claimed.

## Hosted metadata and cross-platform binding follow-up

Allocate C2/I4/D4/Impact4=14/P1 before further receipt or ledger changes.
Hosted security job121070812778 reports 17 tracked-tree and the same 17 history
contexts in the committed companion. Investigate exact whole-file/rule/line
identities; no unknown finding, rule or path is approved. Keep that companion's
Git LF blob frozen while parent and peer classify its recorded source hashes.

Independent review also finds a packaging-domain limitation: the original
Windows raw companion has 1,822,244 bytes / SHA256
40c6465ebb1d66551797c5e30e65acf8e9c25718c82b99a2c4d3ebdd3709b530,
while Git's committed LF blob has 1,770,340 bytes / SHA256
63065bd6aaef171eced553b1163ac0cda3aff8fd8bd5324c14d54dce376b2776.
JSON content is identical, and CRLF reconstruction matches exactly. The first
published receipt binds host packaging bytes; it must not be reported as a
Linux raw-file binding. Preserve that original provenance and add explicit
committed Git LF integrity fields to the main receipt. This is metadata only;
no underlying test run, case outcome, assertion or product source changes.

GitGuardian separately flags the main receipt, incident38962564. Its exact
location/value is not exposed by the check output. The portability repair and
companion classification do not locate, approve or clear that separate hold;
the existing pending GitGuardian access decision remains required.

Parent and peer agree on exactly 17 companion source-SHA identities across 34
descriptors. Twenty-six contexts rehash current raw sources; eight reconstruct
the recorded Windows CRLF bytes of two older numeric sources from the preserved
6fe Git LF blobs. This identifies metadata without attesting historical disk or
execution. Append only those 17 to the 2,181 old ledger entries, 2,198 total.
The companion remains byte-frozen, and scanner/rules/unknown findings are unchanged.
Parent classification review SHA256:
042bd59161d065352380d7a869535903ef2012af5d537719fb59360eb0b839dd.
Peer classification review SHA256:
4b710ca59de3ebb0aceef01aeaeb0947a35bc445d0643ede715472021729ff7e.

Independent review passes the bounded main-receipt portability repair: only
the inventory's explicit Git LF/host domains, hash-domain explanation and
packaging bytes/chronology change. All source/test snapshots and case results
stay unchanged; the original published host-bound receipt remains in history.
Portability review SHA256:
826d83576e145d973d618b88e7bcf61f8927f58027b6c2619000a66ded287e46.
No new test run is claimed. Fresh hosted scans and GitGuardian review still gate
merge; these metadata reviews provide no incident disposition.
