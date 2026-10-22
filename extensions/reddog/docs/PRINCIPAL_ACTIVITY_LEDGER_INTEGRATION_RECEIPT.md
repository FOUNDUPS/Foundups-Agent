# Principal Activity Ledger Integration Receipt

PR: #1638
Original branch: `feat/reddog-principal-activity-ledger`
Reconciliation branch: `agent/pr-1638-ledger-closure`
Original reconciliation base: `02d1c7c14c60487619287a9cb753ff3ddaa53c14`
Preserved PR head: `688eb097724ece28aca20e2e3477ca4c7aa9236c`

## Current-main integration — 2026-10-23

Reviewed source checkpoint `6ed3174c` is integrated with main
`4169b051260376237554fba9650af2c77310b2c2` at local checkpoint `8a88810d7`.
The original PR ancestry and all four reviewed PAL source/test hashes remain
unchanged. Three insertion conflicts retain both CI jobs and both sets of log
entries. Main's Python trust bootstrap, operator-command job, 1,450-member
backend manifest/digest bindings and unrelated lanes are preserved exactly.
Only the newly added PAL job's Node pin moves from 24.11.1 to 24.22.1, matching
the security baseline already adopted on main. No runtime generator is changed.

Fresh Windows qualification uses the portable official Node24.22.1 executable,
with archive SHA256 checked against Node's published SHASUMS. All five focused
commands listed below exit0. The full fast tier passes18 members in19,568ms on
a clean source-pinned linked O: worktree. An initial plain O: clone stopped at
the existing default-Python topology check because it had no primary `.venv`;
that failure remains recorded. The linked worktree resolves the existing
primary environment; no runtime or location guard was weakened.

The package-surface test passes69 files /975,019 raw bytes, with68 LF text files,
one binary and the unchanged1MiB cap. An actual new VSCE build produces71
entries /284,535 bytes. Archive inspection verifies68 source files exactly and
README's same eight explicit URL substitutions. The package content digest is
`6eb9fd388a11a0347373be8ab7b5393a51c4a02567d304426a6458361fb4de79`; archive SHA256 is
`4938e1820af71b69692915267c4f4c0ab8f84ec5b0bea1485f8f585a5e61abd7`.
Nothing is installed or published. Existing `current-*` receipts under the
external qualification directory bind runtime, focused/fast/package execution,
archive mapping and exact source. Overlapping commands are not summed as cases.

The sections dated2026-10-22 below retain historical Node24.11.1 and independent
review results. The prior13 adversarial cases were not rerun in this integration;
their reviewed source bytes remain unchanged. Live GitHub was observed OPEN at
the original `688eb097` head with old September checks and no remote reviews;
those checks do not qualify this local candidate. Independent current-head
review, hosted CI/security, publication and main readback remain pending.
Installed-host operation remains `IMPLEMENTED_NOT_VALIDATED`; the existing
privacy, recovery, cross-root, rollback and authority limits remain unchanged.

## WSP97 reconciliation — 2026-10-22

WSP15 C4/I4/D3/Impact4 = 15/P1. This is an isolated local candidate. GitHub
connectivity did not permit fresh remote ownership/main verification or
publication; the cited base is the last verified main, not a claim about the
current remote. Concurrent blockchain/PF Mall planning stays outside this scope.
Installed-host operation remains `IMPLEMENTED_NOT_VALIDATED`.

The original ledger test did not parse. Synthetic negative controls also
reproduced divergent concurrent first keys, silent key replacement beside
existing ciphertext, wrong-key append, incomplete-write success, stale
commitment projection and incorrect truncation metadata. The original full
packaging test expected 67 files after the proposal added two runtime modules
and failed at `69 !== 67`. These findings were repaired in their existing owners:

- A canonical-root operation queue and exclusive cooperating-process lock
  serialize key initialization and ledger operations. No automatic lock theft.
- Stored keys must authenticate every managed ledger under the scoped root.
  Missing/wrong/malformed keys and empty/partial records fail closed. Direct
  append also validates other principals' existing records in that root.
- Strict JSON rejects poison values before writes. Complete writes, flush and
  close precede a success receipt; failures can leave bytes or a preserved lock.
- Commitment relevance is derived before windowing; latest status comes from
  all principal history in append order. Completion cannot be resurrected by a
  narrower filter/window. Counts and truncation reflect capped projections.
- Package expectations include exactly the two PAL runtime modules: 69 files,
  68 text and one binary, with the existing one MiB limit and LF policy intact.
  An unrelated change to the receipt-bound model setting description was removed.
- The existing fast tier includes all three PAL test files. A focused CI job
  schedules the ledger, adapter, registration, adjacent disclosure and package
  manifest checks on Linux and Windows; configured CI is not an observed CI pass.

## Local execution evidence

Windows Node v24.11.1, temporary fixtures and fake SecretStorage only. The
following existing commands exit 0 from the repository root:

```text
node extensions/reddog/tests/test_principal_activity_ledger.js
node extensions/reddog/tests/test_principal_activity_extension_adapter.js
node extensions/reddog/tests/test_principal_activity_runtime_registration.js
node extensions/reddog/tests/test_principal_memex_disclosure_source.js
node extensions/reddog/tests/test_package_manifest.js
```

The ledger includes an actual child-process contention fixture. Command counts
are not individual assertion/case counts, and reruns are not added together.
Independent review and full package/combined-tier qualification are separate
measurements; their exact-source receipts live under the existing external audit root:
`O:/RedDog-Builder-Artifacts/pr-reconciliation-20261021/refresh/1638-qualification`.
The source-only registration check does not activate an installed extension.

The source-frozen independent review passed 13 adversarial cases and reran six
scoped repository commands. The source-pinned O: checkout at `7615273f6` passed
the existing full fast tier: 18 members in 6,910 ms. Its earlier C: run rejected
the repository-location guard; qualification moved to O: without weakening it.
These runs overlap and are not an aggregate test-case count.

The final package-list contract passes: 69 files / 975,019 raw bytes below the
unchanged 1,048,576-byte cap, with 68 LF text files and one binary. Actual VSCE
packaging succeeds. Archive inspection maps 69 source members plus two VSCE
metadata entries: 68 members match source bytes exactly; README differs only
in eight explicit relative-link substitutions. The first build exposed VSCE's
wrong repository-root link base for this monorepo. The existing README build
command now supplies `extensions/reddog` as its content base; a rebuilt artifact
passes the declared transformation check. No install or URL-reachability claim.

The final archive is 284,536 bytes; its SHA and exact source binding are in
`vsix-inspection.json`. Source review, adversarial probes, failed controls and
reruns are retained separately. Later documentation-only closure does not alter
the reviewed runtime or packaged source; final binding must verify that equality.

## Unqualified boundaries and publication gates

This slice does not prove real VS Code SecretStorage behavior, Windows ACL
confinement, different storage roots sharing a key slot, hostile filesystem
protection, automatic crash recovery, valid-tail rollback detection, universal
power-loss durability or unbounded history performance. Preserve uncertain
append outcomes; do not replay/reset them automatically. See the architecture
recovery boundary. A ledger/context packet grants no disclosure, signing,
promotion, deployment or RSI authority.

Before merge: reconcile fresh remote main and owner, publish to the existing PR through normal gates,
require exact-head CI/security checks, squash and verify main. No local fixture
result substitutes for those publication gates or installed-host acceptance.

## Executable closure

- `extension.js` already activates `principal_memex_disclosure_source.registerCommands(...)`.
- `principal_memex_disclosure_source.js` now registers `principal_activity_extension_adapter` commands.
- `principal_activity_extension_adapter.js` binds RedDog to `principal_activity_ledger.js`.
- `package.json` declares activation and command contributions for capture/context/status.
- package surface contracts include both PAL runtime files.
- fast-tier plan includes PAL ledger, adapter and registration contract tests.

## Storage boundary

- Activity records: extension-local `globalStorageUri/principal-activity-ledger/...`
- Encryption: AES-256-GCM
- Key: VS Code SecretStorage only; not stored beside the ledger
- Network transport: none in PAL/adapter
- Git: mechanism only; no principal activity data

## Authority boundary

A local context packet is not external disclosure authority. Any cloud/model/network egress remains subject to a separate governed disclosure/redaction path.

## Remaining slices

Automatic capture from every RedDog turn, phone capture, AutoPost intake, OCR/voice extraction, Contact Memory entity resolution, Breadcrumb emission, Brain/Memex projection, Mosh Pit rendering, backup, and multi-device E2EE sync remain separate implementation slices.
