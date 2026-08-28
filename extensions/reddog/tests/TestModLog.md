# Foundups(R)Agent TestModLog

## 2026-08-28 - Linked-control dependency runtime release (0.4.133)

- RED independent audit reproduced an escaping resolver exception that left a
  valid claimed task executing. GREEN normalizes the fault, durably fails the
  task, and proves zero authority calls. Five pre-transaction gate cases and
  the distinct runtime/source argument case pass in the bounded 155-line test
  module; the exact three-file selection is **38 passed**.
- WSP_62 differential is green: the executor main function is 181 lines versus
  186 at base, the helper is 27 lines, and inherited oversized suites did not
  grow. Independent WSP_97 re-audit returned GO after documentation truth was
  narrowed to exclude installed-payload byte closure.
- Backend generator **8 passed** at `b58778d3358e...19dc7b6`; fast 14-member,
  conversation 32-test, contract 3-member, deterministic package, candidate
  WSP_62, and exhaustive four-group release gates pass. Exact release wall is
  224.617 seconds; package is 946,123 bytes at
  `89f19ddb703b...b491e773`.
- The read-only VSIX inspection found 69 safe entries, 67 extension members,
  no encryption/duplicate/path/source-byte mismatch, and zero credential-value
  patterns. Artifact: 275,743 bytes at
  `sha256:0cd9288febe9...5c17971`.

## 2026-08-28 - Producer-ranked Holo owner release (0.4.132)

- Producer-rank, HoloDAE Tier-0, synthetic runtime identity, and host-package
  isolation falsifiers are green. Focused Holo/bridge/HoloDAE is 246/246 and
  the complete bridge matrix is 1,188 passed / 14 expected skips.
- Fast 14-member, conversation 32-test, contract 3-member, deterministic
  package, backend compatibility, candidate WSP_62, and exhaustive four-group
  release gates pass. Exhaustive wall is 203.191 seconds with no timeout.
- Exact identities: backend `64e314c2931b...9b77d3`, contract
  `052b944c5bd7...0cc96`, package `a492686c440f...f0c589`, and VSIX
  `sha256:f40ed659c685...25e40b` / 275,728 bytes.

## 2026-08-28 - Current-truth Holo retrieval (0.4.131)

- Added executable counterexamples for premature docs truncation, duplicate
  section starvation, mixed historical/current intent, temporal queries,
  nested audit classification, and exact PR/slice bypass.
- Added exact canonical-source admission and per-path current-section
  allowlisting. All indexing tests remain fake-collection/read-only and cannot
  open or mutate the live Holo store.
- The 0.4.130 pre-release artifact was rejected at the governed-adapter
  boundary. Final 0.4.131 identities are backend `43705c230f38...e59ec`,
  contract `21f7ff0902c6...e4b7d`, package `cc0f6a6c5830...23e57`, and VSIX
  `sha256:736c307fcb91...58f9d1` / 275,738 bytes.
- Candidate retrieval/WSP/generator validation is **299 passed / 1 capability
  skip** with no deselection. Generator is **8 passed**; framework coherence is
  **6 passed**; fast, conversation, contract, package, and exhaustive
  four-group release tiers pass in 207.169 seconds.

## 2026-08-28 - Claim-clock fencing and RSI truth release (0.4.129)

- Independent audit reproduced deferred-SQLite lease-clock races. Three new
  on-disk contention falsifiers pass for delayed issuance and start/completion
  waits that cross expiry; no sleep, timeout, or lease ceiling was widened.
- Affected Python selection is **309 passed**; backend manifest **8 passed**;
  WSP_62 **16 passed**; registry/differential/Holo indexing **52 passed**. The
  canonical registry is **1,607 tests / 268 quarantined** after rebase.
- Fast 14-member, conversation 32-test, contract 3-member, deterministic
  package, and exhaustive 4-group release tiers pass; final wall is 202.154s.
- Rebase validation exposed a Windows CRLF materialization false positive in
  the raw-compared generated shard manifest; its exact path is now pinned to
  LF without changing any packaged RedDog source byte.
- Exact identities: backend `6160d5be6d36...5fdaffd8`, contract
  `772c72ece00c...e50aa6f0`, package `5d7a7f254548...99461e93`, VSIX
  `sha256:7e9bad6a3e02...6c39f4d1e` / 275,700 bytes.

## 2026-08-28 - Exact-task liveness and v2 claim-fence release (0.4.128)

- WSP_97 audit found two P0 counterexamples: claim digest omission of claim
  identity/expiry with non-atomic late completion, and a permissive top-level
  `scripts` namespace extension. Both were reproduced and closed without
  increasing a WSP_62 ceiling.
- The affected Python selection is **303 passed**; backend manifest is **8
  passed**; WSP_62 is **16 passed**; registry/differential/Holo indexing is
  **52 passed**. The canonical registry is **1,605 tests / 268 quarantined**.
- Fast 14-member, conversation 32-test, contract 3-member, deterministic
  package, and exhaustive 4-group release tiers pass. The exact final package
  release completed in 201.201 seconds.
- The 1,363-file backend digest is `61bcfeb6ce69...e16c0d58`; the 18-shard
  contract digest is `16bcddfc83a8...f6557361`; the 67-file package is 945,990
  bytes at `e5eb5e0b0035...bf00d146`.
- The independently inspected 0.4.128 VSIX is 275,700 bytes at
  `sha256:f9fa068d79ff...7ab3ce30f`. Broad database audit separately exposed
  inherited Chroma handle/corruption and quantum-test debt; none is relabeled
  as a passing claim or attributed to the v2 lease slice.

## 2026-08-28 - Receipt-bound owner reproof release (0.4.127)

- Independent WSP_97 review first rejected malformed error types, stale
  deadline accounting, coupled retry ceilings, and top-level-only retry
  telemetry. Exact counterexamples now pass and the final verifier returned GO.
- Owner-result consumers: **148 passed**; bridge lifecycle: **84 passed / 1
  skipped**; query receipt plus one-shot: **68 passed**; WSP_62: **16 passed**;
  backend manifest: **8 passed**; registry/differential/indexing: **94 passed**.
- The canonical registry is **1,601 tests / 268 quarantined**. Fast 14-member,
  conversation 32-test, contract 3-member, deterministic package, and exhaustive
  4-group release tiers pass; the latter completed in 195.725 seconds.
- The 67-file package is 945,836 bytes at `f080f99bb960...8831d`; the VSIX is
  275,672 bytes at `sha256:287853f6e933...6b830` and independently matches all
  67 source members. Live exact-main replay remains separate.

## 2026-08-27 - Exact-main post-merge lifecycle release (0.4.126)

- Rebound version/contract fixtures and the authenticated 1,357-file backend
  manifest to the exact-completion and register-only bootstrap hardening.
- Added Python lifecycle falsifiers for owned/pre-existing runtimes and
  thread-dead cleanup; the exact controller file is 22 passed and the complete
  controller/launch/supervisor selection is 90 passed. Packaging evidence is
  18-shard contract, and exhaustive 4/4 release groups pass in 184.570 seconds.
- Kept the Holo-specific supervisor cases in a separate 269-line test module;
  the inherited supervisor test host is smaller than base and receives no new
  WSP 62 exemption.
- The exact 67-file package is 945,801 bytes at
  `sha256:7a1a8fb2e803...9a27f7c9`; the VSIX is 275,668 bytes at
  `sha256:639d6c82b195...b52b94b`.
- The canonical staged-index registry is current at 1,600 tests / 267
  quarantined entries; its focused registry selection passed 52 tests.

## 2026-08-27 - Inert dependency-runtime closure release (0.4.125)

- Advanced the immutable extension identity because the authenticated backend
  manifest now includes changed reachable filesystem-safety dependencies. The
  five inert materializer modules remain maintenance-only and outside that
  thin-client runtime closure.
- No activation or A-grade assertion is inferred from package authentication;
  fast 14/14, conversation 32/32, contract 3/3, deterministic package, and
  exhaustive 4/4 release groups pass in 178.717 seconds. The 18-shard contract
  is `bd15011d599f...98c4ed`; the 67-file package is 945,746 bytes at
  `dc90aba585c6...36436ae`.
- Built and independently inspected
  `O:\RedDog-Releases\reddog-0.4.125.vsix`: 275,634 bytes,
  `sha256:e3dc0884f8e411245385734aae0abb3a783c3129a24971d3642beaf7d07f8b31`,
  69 entries, zero duplicate/unsafe names or package-member byte mismatches,
  and exact 0.4.125 package identity. (WSP 00/15/22/50/62/83/87/97)

## 2026-08-27 - Runtime-environment binding release (0.4.124)

- Rebound version, authenticated contract shards, backend manifest, and VSIX
  expectations to the runtime-environment identity transaction.
- Added a deterministic checked-in shard-manifest producer so shard hashes,
  aggregate identity, line ranges, and duplicated guard constants are generated
  and independently checkable rather than hand-edited.
- Added no passing cold-start claim; current one-shot timeout evidence remains
  explicit and resident owner activation stays P0.
- Fast 14/14, contract 3/3, package, and exhaustive 4/4 release gates pass.
  The final source closure is 1,356 files at `76911818b5f2...47461`; package
  identity is 67 files below the 1 MiB cap; the exhaustive
  wall is 190.138 seconds. Focused Python evidence is 611 passed / one expected
  capability skip.
- Built `O:\RedDog-Releases\reddog-0.4.124.vsix`; its exact size and SHA-256
  are recorded externally because they identify the built artifact, not source.

## 2026-08-27 - Cold-owner readiness documentation release (0.4.123)

- Rebound the authenticated 18-shard contract from 0.4.122 to 0.4.123 because
  the package README changed; backend behavior and its 1,355-file manifest did
  not change.
- Fast, conversation, contract, package, and four-group exhaustive release
  tiers passed. WSP_97 validation passed 74 tests with one expected capability
  skip; the deterministic package surface is 67 files / 944,804 bytes.
- Built `O:\RedDog-Releases\reddog-0.4.123.vsix`: 275,471 bytes,
  `sha256:10a7fa644c7492268259413fed536bf7a882c9dde9dce1cad5dafe11960ffb13`.

## 2026-08-27 - Holo source-ranker evidence gate (0.4.122)

- Advanced current-version fixtures and the authenticated exhaustive shards so
  the new owner-loaded source-ranker contract cannot ship as 0.4.121.
- Added negative coverage for missing/malformed/mismatched runtime ranker
  digests, linked or mixed runtime roots, caller-weakened quality floors,
  private raw-composer access, and resident-adapter field loss.
- The release evidence remains intentionally non-promotional: cold owner
  startup is P0-failed, and independent signer/caller plus exact executable and
  dependency-environment identity remain required before A-grade/RSI.

## 2026-08-27 - Governed WRE health admission binding (0.4.121)

- Advanced all current-version fixtures and rebound the authenticated shared
  FMAS/path closure to `914cb7db8cb5...f5e2` rather than bypassing compatibility
  preflight. The separate health gate remains outside reachable runtime closure.
- Adversarial WRE coverage proves source-independent WSP 62 quarantine,
  Windows alias/ADS rejection, full evidence identity, deep receipt snapshots,
  job mutation detection, explicit UTF-8 Git inventory, canonical traversal,
  and bounded segment-delimited regex parsing after CodeQL rejected backtracking.
- Focused WRE closure is **310 passed / 1 capability skip**; the registry is
  **1,589 / 268 quarantined** and RedDog's 14-member fast tier passes after the
  current 18-shard rebinding.

## 2026-08-27 - Holo retrieval truth binding (0.4.120)

- Advanced every current-version fixture so the repaired authenticated backend
  cannot be distributed under the prior 0.4.119 package identity.
- The Linux-reproduced backend-preflight failure is GREEN after regenerating
  the 1,350-file manifest and pinning `ee679968a31a...ab80`.
- Fresh evidence: generator parity plus focused Holo/NAV tests are **13 passed /
  13 optional skips**; the 18-shard contract is `d1e4f7f54bab...97f22` and the
  complete fast tier is **14/14 PASS**.

## 2026-08-27 - Stable-route resolver binding (0.4.119)

- Advanced version fixtures so the extension cannot accept the corrected
  activation backend under 0.4.118 identity.
- RED added the production `query_once` resolver shape: canonical roots plus an
  existing `environment` keyword. It reproduced committed-unverified before
  the fix. GREEN proves the callback passes exactly the committed route-file
  mapping and drops the hostile legacy root.
- Focused: **13 passed / 1 expected skip**, **90%** coverage. Current adjacent:
  **191 passed / 1 expected skip**. Complete bridge macro: **1,136 passed / 8
  expected skips in 549.69 seconds**. Backend: **1,350 files** at
  `0de0c08c0181...afa28`; registry: **1,588 / 268 quarantined**. Fast **14/14**,
  conversation **32/32**, contract **3/3**, package, and release **4/4 groups
  in 191.972 seconds** pass. Contract identity is
  `a6d2e50c1c97...43ecfaa`; package identity is **67 files / 945,469 bytes** at
  `59a710359237...25101de`. Exact-main and VSIX identities remain pending.

## 2026-08-27 - Post-commit Holo proof recovery binding (0.4.118)

- Advanced the version and current contract fixtures so the extension cannot
  accept the changed activation backend under the 0.4.117 package identity.
- Backend RED/GREEN proves one typed post-commit recovery, no candidate retry,
  terminal `COMMITTED_UNVERIFIED` after two failures, and immutable
  revalidation after recovery. Focused result: **13 passed / 1 expected skip**
  at **90%** coverage; adjacent result: **205 passed / 1 expected skip**.
- The authenticated manifest is **1,350 files** at
  `9f1867c334c9...566685d`; registry is **1,588 / 268 quarantined**. The complete
  bridge macro is **1,136 passed / 8 expected skips in 550.92 seconds**. The
  rebound 18-shard / 6,929-line / 490-assertion aggregate is
  `e08abe4e0fb9...513509ef`. Fast **14/14**, conversation **32/32**, contract
  **3/3**, package, and release **4/4 groups in 167.248 seconds** pass. Package
  identity is **67 files / 945,324 bytes** at
  `51fde503c1d8...6e65ef02`. Exact-main OpenClaw and commit-bound VSIX remain
  separate post-merge gates.


## 2026-08-27 - Post-merge Holo route continuity release binding (0.4.117)

- Advanced version and contract fixtures so the extension cannot accept the
  changed post-merge backend under the 0.4.116 package identity.
- The generated authenticated closure remains **1,350 files** at
  `8c411cb8ea86...2870660a`; the canonical registry remains **1,588 / 268
  quarantined**. Backend evidence is **34 focused passed** and **85 adjacent
  passed**; the complete bridge macro is **1,135 passed / 8 expected skips in
  548.82 seconds**.
- Reauthenticated the unchanged 18-shard / 6,929-line / 490-assertion contract
  at `27aca704f4aa...9ede4a9e`. Fast **14/14**, conversation **32/32**,
  contract **3/3**, deterministic package, and release **4/4 groups in 179.863
  seconds** pass. Package identity is **67 files / 945,212 bytes** at content
  digest `78102b01b82a...57033417`. Exact-main live replay and artifact audit
  remain post-merge gates.

## 2026-08-27 - Holo owner acquisition release binding (0.4.116)

- Advanced version and contract fixtures so the extension cannot silently use
  a changed authenticated Python backend under the previous package identity.
- Canonical registry is current at **1,588 / 268 quarantined** and the generated
  **1,350-file** backend closure includes the acquisition module at
  `52cacf9a4cf2...1f818d9b`. Exhaustive release validation passed; only the
  exact-merge-commit VSIX build and archive audit remain as artifact gates.
- The unchanged 18-shard / 6,929-line / 490-assertion exhaustive contract is
  reauthenticated after version-only edits at
  `sha256:69cbeda89fbb...664295d07`.
- The four-group release supervisor passed in **166.480 seconds**. Its
  deterministic package surface is **67 files / 945,191 bytes** at content
  digest `sha256:829981b2246a...562138469d`; a final exact-merge-commit VSIX
  remains the post-merge artifact gate.

## 2026-08-27 - Exact-main live acceptance and VSIX audit (0.4.115)

- The real broker-managed OpenClaw supervisor completed the canonical
  post-merge AgentDB task at exact main `cfd1e0051`; independent read-only
  verification recomputed the claim and request/completion payload bindings.
- A fresh owner query returned CURRENT/no-gap/no-reindex at generation
  `sha256:60d06274...`; full revalidation preserved all 33 artifacts /
  220,800,343 bytes.
- Re-ran conversation **32/32** and the four-group release supervisor **4/4 in
  172.611s** under the repository `.venv`; fast **14/14**, contract **3/3**,
  and the deterministic package gate remain green.
- Direct VSIX inspection passed CRC, path, duplicate, symlink, encryption,
  compression, version, and byte-equivalence checks. Artifact:
  `O:\RedDog-Releases\reddog-0.4.115-cfd1e0051.vsix`, 275,502 bytes,
  `sha256:6ee390270377...0f1adbb`.
- Reproducible secret-free runtime rows and artifact identity are attached at
  `docs/audits/infrastructure/REDDOG_EXACT_MAIN_LIVE_ACCEPTANCE_EVIDENCE_PHASE1.json`.

## 2026-08-27 - Post-merge Holo activation compatibility (0.4.115)

- Pinned version and contract shards to 0.4.115 and rebound the generated
  backend closure to 1,349 files at `4095e31c989b...1a714e46`.
- Reauthenticated the unchanged 18-shard/6,929-line/490-assertion exhaustive
  contract at `sha256:01160dcae591...c405576` after the version-only edits.
- Registry generation/check is current at 1,587 tests / 268 quarantined.
  Python activation-order evidence is 62 passed; extension package, shard, and
  release gates remain required before the exact-main VSIX is published.
- Final candidate results: fast **14/14 in 2.673s**, contract **3/3**, package
  **67 files / 944,930 bytes** with content digest
  `sha256:f48a934ca411...c9cb452c`, and release **4/4 groups in
  164.090s** without timeout.

## 2026-08-27 - Governed resident Holo usability (0.4.114)

- Bumped the thin-client identity and contract fixtures after the shared
  generation-bound resident adapter repair.
- The bridge-owned focused result is 25 passed; its expanded owner/worker/
  supervisor matrix is 428 passed / 1 skipped. The historical canary at
  `61c2c3003bc4c2086f105f4c39effd499a026627` returned CURRENT but does not
  authorize the candidate or any later commit.
- The regenerated backend closure is 1,343 files at
  `ba41d84612db22b5d24621c4b3ca8ea1c7a6e2f69ee131e963369fa12b30819e`.
- Replaced the obsolete expectation that canonical WSP_95 contains a blocked
  phrase with separate positive and negative proofs: the current protocol
  passes audit mode, and an explicit `private_reasoning` probe still blocks.
- Rebound the 18-shard aggregate to
  `sha256:a042b670b7f1ef12f80edeb18c26f3bfe78ddc360d1fd1f9ca2d2021053aa1ee`;
  the full four-group release supervisor passes.
- Refreshed the canonical Git-tracked Python test registry after CI correctly
  rejected stale bytes: **1,585 tests / 268 quarantined**. The registry check
  and its 45 focused registry/differential tests pass.
- This entry records extension compatibility only; no extension Holo mutation,
  worker dispatch, or Hermes authority was added.

## 2026-08-26 - Backend WSP 62 compatibility (0.4.113)

- Pinned the 1,385-file authenticated closure at
  `6e022fb56e5e8775eac9814654fcaf4b338a699a8c91829edb96c9e5b868fa32`.
- The manifest generator asserts the new bootstrap-result dependency appears
  exactly once with a bound content hash. Version, backend compatibility,
  shard, package, and release suites remain the acceptance surface.

## 2026-08-26 - RedDog package EOL reproducibility (0.4.112)

- Added exact and effective `.gitattributes` verification for 66 packaged text
  files at `text eol=lf` and the packaged PNG at `-text`.
- Upgraded `reddog_package_surface_receipt` to v2 with effective-policy and
  sorted member-content digests, CR-byte rejection, LF mode, and text/binary
  counts while retaining the measured working-tree byte total and 1 MiB cap.
- Added hostile CRLF, bare-CR, missing/overridden-attribute cases and fresh
  `core.autocrlf=true/false` index-materialization equivalence.
- Made materialization fixtures exclusively owned through `mkdtemp` and added
  a sparse over-cap member proving rejection before package-byte reads.
- Removed host-specific raw-byte claims from current documentation; artifact
  inspection remains authoritative for each built VSIX archive.

## 2026-08-26 - Durable first-TURN link compatibility (0.4.111)

- Rebound the exact 1,384-file authenticated backend closure after atomic
  two-FoundUp capability/session delegation. Canonical digest:
  `d58c0098b3c873683becbce6e2228ba41841f111913ce72e72bf49eb1df786cb`.
- Canonical staged-index registry: **1,582 tests / 268 quarantined**.
- Candidate Python/backend-generator/registry evidence passes, alongside fast
  `14/14`, conversation `32 passed`, and a deterministic 67-file package
  surface within the 1 MiB cap.
- Version, package, generated-manifest, focused conversation, and release gates
  bind the VSIX to the backend slice without claiming a host caller, handler,
  immediate CAS, model/worker execution, or live adapter.
- Added adversarial backend evidence for signed immutable E0 request identity
  and exactly-once atomic consumption of one replay authority.

## 2026-08-26 - Trusted new-scope backend compatibility (0.4.110)

- Rebound the authenticated backend closure after the repaired new-scope slice;
  only the extracted signer-context dependency entered the extension import
  graph. The unwired resolver/admission aggregate remains outside the closure.
  Closure: **1,384 files** at
  `3211a4e5c83d7a8fca27ec7155933659164587fa5ca9813899d3dc79b51c8498`;
  registry: **1,581 / 268 quarantined**.
- Backend Python evidence includes 17 focused and 127 adjacent passes; the
  repaired-byte independent WSP 97 audit is GO with 46 focused passes. The
  initial independent NO-GO and production-shaped nonce-split regression remain
  recorded rather than erased.

## 2026-08-26 - Resident admission compatibility regression (0.4.109)

- Rebound the exact 1,383-file backend closure and extension version contract
  to the final current-session admission hashes without expanding runtime
  dependencies. Canonical digest: `5d8ef0cf64ffc12c4a8dda5fef6259653791e91e5824b7baba815bdfccb5feea`.
- Generator/staged-index plus canonical registry matrix: **36 passed**; registry
  current at **1,580 tests / 268 quarantined**. No live aggregate caller or
  effect surface is introduced.
- Rebound contract aggregate: 18 shards / 6,929 lines / 490 assertions at
  `sha256:77c56bd30c800a50785d48bb77e5fb788f5ff5c85116d747ef16f5d34ddca0f9`.
  Fast `14/14`, contract `3/3`, conversation `32 passed`, and deterministic
  67-file package tiers pass.

## 2026-08-26 - Resident replay manifest parity regression (0.4.108)

- Linux fast-tier CI exposed two stale authenticated-scope runtime hashes that
  Windows release validation did not exercise through the fast preflight.
  Regenerated the existing 1,383-file closure, updated its canonical pin, and
  retained the staged-index parity test; no assertion or threshold was
  weakened. (WSP 00/15/22/50/62/84/97)

## 2026-08-26 - Canonical identity grounding repair (0.4.108)

- Updated the exhaustive contract to assert the post-PR-1553 canonical RedDog
  identity in README and ROADMAP independently. The exact-main release gate
  exposed the stale pre-alignment sentence; no threshold or production policy
  was weakened. The rebound 18-shard aggregate is
  `969770f05975a4f357e65ca8f9268a54d9107c97728c7539f35f88bd1291602f`;
  contract/fast/package tiers pass, and the final release passed 4/4 in
  **158,071 ms** with no timeout. (WSP 00/15/22/50/84/97)

## 2026-08-26 - Activation and webview security falsification (0.4.108)

- Expanded the exact activation/route/planner/materializer/descriptor/
  maintenance/acceptance/authority/CLI suite to **470 passed / 7 expected
  host-capability skips** with TEMP/TMP/base temp confined to O:.
- Added default-off evaluation-fallback and webview CSP/nonce contracts, then
  rebound the exact **1,383-file** backend closure and 18-shard source identity.
  The 14-member fast tier now executes the behavioral no-effect evaluation
  topology gate. The exact package is **67 files / 964,953 bytes** under 1 MiB. No live Holo
  authority or consumer state was changed. The final release passed 4/4 in
  **172,357 ms** with no worker or release timeout; the canonical staged-index
  registry is current at **1,577 tests / 267 quarantined**. (WSP
  00/15/22/50/62/97)

## 2026-08-23 - Governed Holo maintenance release closure (0.4.107)

- Added strict launcher/session/child runtime-provenance tests and refreshed the
  1,382-file authenticated backend pin. Python evidence is 13/1 focused
  diagnostics, 106/2 complete maintenance boundary, 119/2 adjacent integration,
  and 8/8 backend generation/provenance.
- Retained the first full RDD-003 NO-GO and the targeted RDD-004/RDD-009
  follow-on failures. Their repair confines forced-Git-unavailable discovery to
  an ordinary O:-local repository fixture and reuses that root for the real
  bundle regression. Production focus, completeness, recall, link, and size
  gates remain unchanged.
- The first candidate WSP_62 replay rejected a 34-line fixture constructor.
  Extracting cleanup into a separate bounded helper produced the final PASS;
  no ceiling or exemption changed.
- Final shard identity is **18 / 6,929 lines / 490 assertions** at
  sha256:563b7efc4d012d7166d0e7dbdba8a9ebe5d0a66093419dc66070123dae6ebbcc.
  Final post-extraction release passed **4/4 in 162,441 ms**, no timeout. Exact package surface:
  **66 files / 961,383 bytes**. Registry remains current at **1,574 tests / 267
  quarantined**. Candidate WSP_62 passed without increasing a limit.
  (WSP 00/15/22/50/62/97)

## 2026-08-23 - Compact Holo snapshot runtime canary (0.4.106)

- Regenerated and pinned the authenticated 1,381-file backend closure after the
  snapshot-only Holo runtime correction. Focused Holo/owner tests and the
  production-shaped warmup/query canary prove CURRENT semantic retrieval from
  the 33-artifact replica with post-query hashes unchanged. Version and package
  contracts advance together to 0.4.106. The final closure digest is
  `04d3e3de5683...e8a67aae`, and the exact package is 66 files / 961,130 bytes.
- Candidate WSP_62 forced the changed README below its 1,000-line ceiling by
  extracting detailed release scaling receipts to a companion document.

## 2026-08-23 - Stable route-file bounded propagation

- Extended the exhaustive bridge-environment matrix so
  `REDDOG_HOLOINDEX_QUERY_ROUTE_FILE` survives the `holoindex_owner` and
  `resident_architect` profiles and the separate Start Operations
  promotion/control allowlist, while remaining absent from unrelated bridge
  profiles. Start Operations drops empty and non-string values.
- Python resolver integration separately proves direct-root ambiguity and exact
  terminal-journal/route-record/descriptor binding before owner use.
- Backend generator/provenance is **8/8 in 86.48 seconds** at the exact
  1,381-file closure digest `d818aefa512d...9e88e`; backend compatibility,
  environment, Start Operations, and the 13-member fast tier pass. The exact
  package contract passes at **66 files / 962,637 bytes** under 1 MiB. The
  independent manifest check passed in **85.9 seconds** with the same digest and
  file/manifest/package measurements; registry is **1,574 / 267**.
- Candidate WSP_62 file/function/document proof passes after extracting the
  profile expectation data from the formerly growing assertion function;
  RedDog README is 998 physical lines and no threshold was raised.
- An exhaustive release attempt returned **NO-GO** at core assertion RDD-004
  after 197.649 seconds; governed Git, Git-format/environment, bridge/WSP_62,
  package, and timeout evidence passed with no timeout. The failure is retained
  as non-promotion evidence. Base/candidate comparison proved it inherited and
  deterministic: denied partial-clone Git reached a bespoke fallback that
  omitted root, `public`, `docs`, and `WSP_framework` evidence.
- Replaced that allowlist with one bounded non-link-following root walk and
  added an exact-string/out-of-range parser boundary plus forced-unavailable
  RDD regressions. A second inherited FWG-002 failure was a host-dependent test,
  not grounds for a production filesystem fallback; its success path now uses
  `foundup_integration_test_fixture.js`, a confined ordinary-Git repository with
  canonical registry/manifests, hook/signing suppression, real digest/use-time
  checks, process-exit cleanup, and traversal rejection.
- Final authenticated identity is **18 shards / 6,928 lines / 489 counted
  assertions** at aggregate `sha256:940aa9cc...93452`. Independent frozen-source
  `npm run test:release` passed **4/4 in 288,505 ms**: core 273,730 ms,
  governed Git 288,395 ms, Git formats/environment 180,643 ms, and
  bridge/WSP_62 3,683 ms. There were no group/release timeouts. An earlier run
  under concurrent reviewer load timed out core/governed Git at
  402,674/402,672 ms and is retained as NO-GO contention evidence. No guard was
  widened; the isolated governed-Git margin is 111,605 ms.

## 2026-08-23 - Holo authority-root profile confinement

- Extended the exhaustive bridge-environment fixture to prove
  `REDDOG_HOLOINDEX_AUTHORITY_REPO_ROOT` survives the `holoindex_owner` and
  `resident_architect` profiles plus the bounded Start Operations control
  environment and remains absent from unrelated bridge profiles.
- This is the regression for the dedicated clean-authority checkout binding;
  Python remains responsible for topology and exact-HEAD admission.

## 2026-08-22 - Continuous conversation and lifecycle candidate (0.4.105)

- Added the operational `test:conversation` tier with 15 shared JS vectors and
  32 Python contracts covering chat, research, proposal, authorization, status,
  cancellation, explicit/bare continuation, risk-only depth escalation, strict
  rehydration, async-admission derivation, and effect-ceiling rejection.
- Fast tier: 13/13 members PASS. Contract tier: 3/3 PASS. Package: exact 66
  files/62 runtime files under the 1 MiB raw cap. Candidate WSP 62: PASS with
  `extension.js` at 8,370 lines and the new policy below its module ceilings.
- Authenticated aggregate: 18 shards, 6,913 lines, 483 assertions PASS. The
  Start Operations source contract was advanced from the removed draft-only
  prompt expression to the new policy selector while preserving presence and
  authority-first order.
- The first independent frozen-tree audit returned NO-GO and exposed prior
  work-summary ingress into chat, a forged-decision effect bypass, malformed
  nested routing dependencies, cross-language astral-length drift, and a
  56-line Python WSP-62 violation. All received focused adversarial tests; the
  validator is now 44 lines.
- Backend manifest equality and VSIX digest pin PASS at 1,372 files. An initial
  five-minute wrapper produced no assertion result; the final staged-index
  eight-case generator suite then passed 8/8 in 351.51 seconds.
- The repaired-tree independent audit returned GO with all five blockers
  closed. Final `npm run test:release`: four groups PASS in 341,658 ms; core
  341,520 ms, governed Git 227,289 ms, Git formats/environment 140,627 ms, and
  bridge/WSP62 2,956 ms. No group or release timeout occurred; package receipt
  was 66 files / 960,354 raw bytes.

## 2026-08-21 - Governed topology-consumer closure (0.4.104)

- Added v2 extension-query coverage for explicit available-provider inventory,
  exact role/provider/model topology, expiry, and fail-closed fallback policy.
- Added bridge-environment coverage for runtime-binding, provider-inventory,
  and isolated Holo replica-route inputs without widening credential profiles.
- Backend manifest, package surface, and exhaustive release receipts are
  regenerated only from the final composed RedDog/Holo tree.
- Added the missing `model_runtime_blocked` stage action and updated the exact
  19-stage exhaustive assertion plus authenticated shard/aggregate hashes.
- Added stale-at-use and webview-aging runtime-binding regressions. The focused
  source contract proves `callFusion` re-queries before provider spawn, and the
  Fusion stdin matrix proves only fresh receipt-bound topology reaches the
  bridge. Commands: `node tests/test_model_runtime_binding_query.js`,
  `node tests/verify_fusion_panel_input_contract.js`, and
  `node tests/test_reddog_candidate_wsp62.js` -> PASS; `npm test` -> 12-member
  PASS in 2.931 seconds; `npm run test:contract` -> 3-member PASS in 0.595 seconds;
  `npm run test:package` -> 65 files / 948,219 bytes PASS;
  `npm run test:release` -> 4 groups PASS in 323.643 seconds with no timeout.
- Evidence location: this entry plus the final-SHA check rollup on PR #1529.

## 2026-08-21 - Nemotron/Qwen routing contract refresh (0.4.103)

- Pinned Qwen 3.8 Max as the current evaluation fallback critic, retained exact
  GLM/DeepSeek/Kimi IDs, and regenerated authenticated shard/backend manifests.
- AI Gateway separately covers local Nemotron proposal and verified topology
  authority; the extension suite remains offline.
- Independent WSP_97 repair added fail-closed modality, topology-expiry, and
  incumbent-comparison coverage before release promotion.
- Regenerated the 1,365-file backend closure after advisory decomposition and
  aligned the independent generator's exact golden digest fixture.
## 2026-08-21 - Query-replica profile confinement

- Added the query-replica root fixture and proved it crosses only the
  `holoindex_owner` and `resident_architect` closed profiles.
- The existing ambient secret and arbitrary-key exclusions remain unchanged.
  Integrated Node environment, backend-manifest, package, contract, and release
  gates are regenerated and rerun from the final 0.4.104 tree.

## 2026-08-21 - Mainline release/candidate gate separation

- Removed the changed-worktree-only WSP 62 proof from the committed-main
  release closure after `npm run test:release` correctly exposed its empty
  `git diff HEAD` mismatch on the squashed main commit.
- Replaced the historical hard-coded JavaScript candidate list with the exact
  current changed/new RedDog JavaScript surface. The focused proof now remains
  useful for future candidate worktrees and fails closed when invoked without
  a governed candidate surface.
- Added a tier contract preventing the candidate-only proof from re-entering
  promotion. The seven committed-main tail members remain authenticated by the
  shard manifest and release plan.
- Validation: fast 12/12 in 6,005 ms; contract 3/3 in 1,036 ms; candidate WSP
  62 PASS; deterministic package surface 65 files / 941,467 raw bytes; release
  4/4 groups in 311,358 ms with no timeout (core slowest at 311,273 ms).

## 2026-08-21 - CI conversational-draft grounding repair

- Replaced both stale inline `wireFusionWebview` source assertions for
  conversational-draft and authoritative-work-state empty contexts with exact
  two-hop contracts across `buildContextForRequest` and
  `holoindex_owner_runtime.buildOwnedContext` after the WSP_62 extraction.
- Added both focused grounding contracts to the bounded fast tier so `npm test`
  catches source-shape drift without rehashing the complete backend closure;
  the aggregate remains the separate CI diagnostic security gate. Production
  routing and authority behavior are unchanged.

## 2026-08-21 - Native upstream worker provenance (0.4.102)

- Updated version/package and backend-manifest contracts for Hermes API
  `0.20.4` native leaf proof and OpenClaw `2026.7.1-2` runtime identity.
- Added the repository-authoritative license text to the VSIX contract, raising
  the closed package surface from 64 to 65 files and removing VSCE's warning.
- The live canaries are documented backend evidence; extension tests remain
  deterministic and do not invoke models, expose credentials, or write repos.

## 2026-08-21 - Holo runtime split, streaming provenance, and package contracts

- Final release supervisor receipt: **PASS**, four groups, 309,306 ms wall;
  core 309,218 ms, governed Git 203,295 ms, Git formats/environment 131,072 ms,
  bridge/WSP62 13,555 ms, with no child or release timeout. Package receipt:
  64 files / 936,267 raw bytes under the 1 MiB cap.
- Complete-tree staging made the backend closure truthful: 1,364 runtime files
  at canonical digest
  `3c0cffea72e92ca1acbcd8a1f5a106164dda11ae791afe050f39490c3cd62d10`.
- The corresponding staged-index registry contains 1,544 tests and 266
  quarantines.
- Removed the last raw `holo_index.py --bundle-json` launch from the exhaustive
  contract. DRT-006 now creates the same real `ENOBUFS` shape with a bounded
  8 KiB Node child against a 4 KiB buffer, so promotion no longer couples this
  classifier proof to Holo authority or store state.
- Repaired assertion inventory authentication: the former raw regex counted
  `assert(` text inside comments and strings. The comment/string-masked receipt
  truthfully binds 18 shards, 6,914 lines, 483 static assertion calls, and
  aggregate SHA-256 `7bc3e58227d8db65dc97742d12ebef24984f44eda3d1f8b361961a4471be2635`.
- Preserved EXT-ACC-001 as an executable content-survival contract. Requested
  target snippets are now ordered ahead of broad Holo recall so the 42K final
  bound cannot report target metadata while truncating away the target bytes.
- Added an exact five-second governed Git configuration-probe assertion after
  the parallel release exposed a two-second contention flake. The complete
  supervisor remains the executable concurrency regression.
- Expanded the candidate WSP_62 set to the generation facade, bundle
  projection, interpreter-provenance worker, owner runtime, incident bridge,
  and both async tests. All are at most 400 physical lines with detected
  functions at most 30 lines.
- Added a source and hostile 32 MiB runtime proof that configured-interpreter
  hashing uses fixed 64 KiB `readSync` chunks off the parent event loop and
  contains no whole-file `readFileSync` path.
- Added direct-read projection coverage for source-bearing one-shot owner
  bundles and raised the exact package contract from 61 to 64 files solely for
  the three required runtime helpers. The same surface now rejects non-regular
  entries and aggregate raw size above 1 MiB, emitting a bounded receipt.
- Repaired the WSP_62 audit itself: its static declaration must equal the full
  Git changed/new RedDog JavaScript set, content-line counting ignores only the
  terminal newline, and inherited function debt cannot grow. Split the prior
  475-line Start Operations test to below 400 lines plus a 91-line helper.

## 2026-08-21 - Request-owned asynchronous Holo lifecycle contracts

- Added explicit panel/request ownership from `executeAsk` through bounded
  context, owner query, and incident repair. Disposal is proven to mark the
  panel closed before terminating every owned Holo/provider child; cancellation
  and late callbacks settle once with typed failure.
- Moved configured-interpreter descriptor/stat/SHA proof to a worker thread and
  added a hostile 32 MiB fixture proving the parent does not perform the file
  read/hash. Ambient PATH and unresolved configured commands remain explicitly
  unverified.
- The fast plan now directly executes owner async, incident async, and Fusion
  ingress contracts. Focused tests cover 300-second owner and 90-second incident
  limits, stdin absence/throw/EPIPE, timeout, disposal, and late callbacks.

## 2026-08-21 - Digest-only executable receipt and strict consumer contracts

- Reproduced Python acceptance of a recomputed repository-state body containing
  empty executable identities and a minimal `status: valid` signature.
- Added malformed/missing/unknown/type/bounds/digest/link/identity/signature/
  verifier-containment rejection matrices plus non-Windows exact-shape and live
  JS-to-Python acceptance. Serialized readiness, projection, and repository-
  state receipts are scanned for raw Git and verifier path absence.
- Hostile promotion passed all four groups in 283,268 ms; executable/environment
  was 103,881 ms, governed Git 168,117 ms, core 283,234 ms, and package/WSP62
  2,599 ms. No timeout or termination occurred.

## 2026-08-21 - Governed Git executable provenance contracts

- Tests-first RED covered missing authority, lexical PATH/PATHEXT ordering,
  missing executable, PATH mutation, file replacement, link/reparse rejection,
  hardlink acceptance, absolute invocation, pathless environments, Windows
  signature failure, v2 receipts, and batch output withholding.
- Added a production source scan proving there is no ambient bare-Git child in
  RedDog JS or moltbot-bridge Python. Snapshot tests pass 12/12 and Start
  Operations control tests pass 32/32 using the governed receipt consumer.
- The executable authority plus WSP_62-separated repository-receipt module move
  the deterministic package contract from 59 to 61; no runtime file or public
  metadata was hidden to preserve a stale count.
- The first hostile release truthfully failed `RDD-010` because its legacy
  monkeypatch matched only bare `git`. Moving the fake to the governed
  executable boundary restored the intended oversized-manifest proof without
  weakening production truncation behavior. The reauthenticated closure remains
  18 shards / 6,958 lines / 1,240 assertions. Hostile promotion then passed all
  four groups in 290,894 ms; no group timed out or required termination.

## 2026-08-21 - Workspace capability and package-surface contracts

- Added static fast-tier proof for exact unsupported untrusted/virtual workspace
  capabilities, publisher/version/main/activation commands, the ignore policy,
  and a complete require-derived runtime closure.
- Added a release/package test that invokes the installed VSCE CLI twice without
  a shell and requires the same exact 59-file list both times. All 55 root
  JavaScript files, both dynamic workers, and the Python bootstrap are retained;
  no tests, internal docs, or development artifacts remain.
- Added the fail-closed capability assertion to the authenticated exhaustive
  contract, now 18 shards / 6,954 lines / 1,239 assertions.
- Validation: package list 59/59 twice; fast 8 members in 8,892 ms; contract 3
  members in 271 ms; hostile release 4/4 in 283,993 ms with no timeout.
  Package-surface execution added only 2,362 ms to the bridge/WSP62 group.

## 2026-08-20 - Main/acceptance integration verification

- Governed Git hardening, child-environment isolation, tier plan, authenticated
  shards, and backend closure were reconciled without changing the exhaustive
  assertion body or main-only runtime surfaces.
- Backend generator is 6/6 and compatibility contract/preflight/async suites
  are green. Hostile-ambient `npm run test:release` passed 4/4 process-isolated
  groups in 323,242 ms; slowest was `core` at 323,202 ms, with no timeout or
  signal. Fast and contract tiers passed in 10,012 ms and 528 ms.

## 2026-08-20 - RedDog test tiers and promotion-runtime headroom

- Tests-first RED failed at the exact missing `package.json` scripts assertion.
  `npm test` is now a seven-member bounded developer tier and initially passed in
  9.188 seconds; `npm run test:contract` authenticates plan and shard identity.
  `npm run test:release` is the explicit exhaustive promotion command.
- The release plan extracts every aggregate `require('./test_*.js')` and demands
  exact ordered equality with five unique planned members before any worker
  starts. Missing, duplicate, reordered, or stale membership is a hard failure.
- The first parallel promotion run proved all three focused children green in
  148.498/88.729/0.156 seconds but truthfully failed the core at 0.168 seconds:
  its shared VM required `require.cache`. Restoring the local CommonJS cache
  property preserved backward compatibility; the repaired core-only closure
  passed in 242.789 seconds with all negative diagnostics visible.
- Four process-isolated groups are bounded by worker cap 4, 400-second child
  timeout, 2 MiB per-stream output, and the unchanged 420-second release
  ceiling. Plan-order output includes per-group/slowest/total timing and any
  exit, signal, timeout, or output overflow fails promotion.
- The first complete aligned promotion passed in 295.928 seconds. Group times
  were core 295.219, governed Git 174.351, Git formats/environment 101.531,
  and bridge/WSP_62 0.167 seconds. The resulting 124.072-second (29.5%) margin
  replaces the prior 1.1% near-ceiling posture without removing coverage.
- A complete repeat passed in 266.709 seconds: core 265.850, governed Git
  157.403, Git formats/environment 91.053, and bridge/WSP_62 0.166 seconds.
  Conservative acceptance retains the slower 295.928-second receipt.
- Independent loop-2 RED proved a caller-set `REDDOG_CONTRACT_GROUP` could run
  one valid child group through the canonical command and exit zero. The same
  audit showed no parent deadline and no authoritative timeout state.
- New no-sleep fake-clock tests prove ambient selector rejection, child timeout
  followed by exit zero remains FAIL, parent timeout followed by exit zero
  remains FAIL, and two failed termination attempts settle as explicit failure
  within fixed grace with streams destroyed and the child unrefed.
- The canonical owner now always enters full promotion. A dedicated internal
  worker requires exact argv plus an owner-generated 128-bit nonce. A hostile
  ambient selector and forged nonce still produced all four real groups; the
  repaired promotion passed in 279.723 seconds with all timeout fields false.
- Loop-3 RED reproduced both a deterministic post-spawn error and a real
  invalid-`SystemRoot` `taskkill.exe` ENOENT; the old unobserved child emitted
  an unhandled error and exited 1. GREEN proves error/exit/close observation is
  attached before unref, nonzero/timeout returns failure, graceful and forced
  failures reach the bounded receipt, late errors stay handled, handles/listeners
  settle, argv remains shell-free, and POSIX process-group behavior is unchanged.
- The first aligned loop-3 hostile-selector promotion passed in 274.537 seconds
  wall time: owner 273.762, core 273.724, governed Git 164.376, Git formats/
  environment 96.467, and bridge/WSP_62 0.157 seconds. Every timeout and
  termination field was false; the 18-shard/6,952-line/1,238-assertion closure
  was unchanged.
  (WSP 00/5/6/11/15/22/34/50/57/62/83/87/97)

## 2026-08-20 - Governed Git child-environment least-privilege contract

- The staged pre-repair source was loaded in an isolated VM without changing
  the worktree. Its deterministic exclusion assertion failed in 0.6 seconds:
  `UNRELATED_SENTINEL` actual `ambient-marker`, expected `undefined`. The
  checked-in regression now evaluates ambient exclusion before the new builder
  API assertion, so the original implementation fails on the actual leak.
- The matrix also covers provider/GitHub/AWS/generic credential-shaped names,
  Python/Node/dynamic-loader injection, SSH-agent and SSH/Git configuration,
  ambient Git overrides, and arbitrary caller fields. It proves exact platform
  allowlisting, immutable source/fresh output, fixed-control overwrite, and no
  HOME/profile/virtual-environment inheritance.
- Every real config/content Git child is captured and checked, and an actual
  Node child proves an ambient preload does not execute. The test deliberately
  retains PATH and records the unresolved executable-provenance limitation.
  Focused GREEN passes in 1.6 seconds without network, provider, model, Holo,
  staging, packaging, or Git-authority mutation.
- Projection identity/race pass in 28.688/59.913 seconds; aggregate and ref/
  config/object-format matrices pass in 135.605/83.792 seconds. Bridge Python
  environment/start-operations, backend/preflight/async/Fusion, RDD, FoundUp,
  candidate WSP62, syntax, diff, shard, and manifest gates are green.
- The first exhaustive run failed truthfully at 102.707 seconds because two
  static assertions still assigned environment controls to readiness. After
  rebinding those exact checks to the shared environment source, the 18-shard/
  6,952-line/1,238-assertion closure authenticates at
  `1b26b3dc6e2910c290e6ddae61b670f50a496351d4ed099a8ad820428bd2c3a1`.
  Full exhaustive acceptance passes in 415.462 seconds under the unchanged
  420-second ceiling. Expected adversarial Git, Unicode, sealed-runtime, and
  quarantined Holo dependency diagnostics remain visible.
  (WSP 00/5/6/11/15/22/34/50/57/62/83/87/97)

## 2026-08-20 - R9 loop 3 Python environment documentation truth

- Static documentation RED failed on the exact Interface sentence that claimed
  every bridge child included `PYTHONNOUSERSITE=1`.
- Six-document truth checks now distinguish common isolated profiles from local
  `holo_query`, pin the configured/system interpreter's per-user NumPy need,
  preserve denial of Python injection variables and credentials, and expose the
  sealed-interpreter/package-provenance residual.
- Focused environment/WSP62/shard gates pass in 0.085/0.078/0.086 seconds;
  syntax and cached/unstaged diff checks pass. Canonical exhaustive acceptance
  passes in 405.338 seconds below the unchanged 420-second ceiling. No code,
  test, shard, pin, package, staging, commit, Git authority, or Holo mutation
  occurred. (WSP 00/15/22/50/57/62/83/87/97)

## 2026-08-20 - R9 loop 2 live Holo environment leakage contract

- Tests-first RED failed in 0.2 seconds at `UNRELATED_SENTINEL must not cross
  the Holo query boundary`; the live extracted helper returned the ambient
  marker from its whole-environment clone.
- The deterministic fixture also covers `GITHUB_TOKEN`, a generic credential-
  shaped name, `OPENROUTER_API_KEY`, `PYTHONPATH`, `PYTHONHOME`,
  `PYTHONSTARTUP`, an arbitrary caller key, ambient retrieval-flag override,
  fresh-object identity, and source non-mutation.
- GREEN passes after composing the live helper through the closed `holo_query`
  profile. An independent VM probe of the live function passes separately and
  confirms lexical/read-only synthesis without exposing any forbidden name.
- The repository-audit companion exposed a system-interpreter import failure
  caused by newly forcing `PYTHONNOUSERSITE=1` on this legacy route. A focused
  compatibility RED rejected that flag; the corrected Holo helper retains the
  configured/system interpreter's per-user NumPy visibility without restoring
  any forbidden environment key. Universal isolation remains dependent on a
  sealed/configured Holo interpreter closure.
- Candidate WSP62 then rejected one 30-line test-function overrun; cohesive
  assertion helpers restored the candidate ceiling without weakening coverage.
- The first exhaustive attempt stopped truthfully in 0.170 seconds because
  HSF-002 still required `KEEP_ME` to survive. The shard now requires exclusion;
  shard 2 is `f138a781efe77b1785853f3e1c0a7d90614c6a10720dc33b45f2b8494ffa82c0`
  and the unchanged 18-shard/6,951-line/1,238-assertion closure is authenticated
  at `482671e3f4fc766ae91adf7aac28fcbaea1aae229c9a8765f5a17dadd5e3f0c5`.
- Full exhaustive acceptance passes in 398.366 seconds under the unchanged
  420-second ceiling. Backend manifest parity remains 1,360 files at
  `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`.
  The focused RED/GREEN and independent probe do not query Holo. No Holo
  mutation/reindex, model/provider/network call, stage, package, or commit occurs.
  (WSP 00/5/6/11/15/22/34/50/62/87/97)

## 2026-08-20 - Python bridge environment least-privilege contract

- Pre-fix focused RED failed in 0.087 seconds on the exact whole-editor
  `Object.assign` environment clone.
- Added a closed-profile matrix covering required Windows/POSIX runtime keys,
  absent/empty values, fresh result objects, source non-mutation, unknown and
  object/array profile rejection, unrelated credential/Python injection
  exclusion, and exact provider/Holo/resident/work-state/model-binding keys.
- Post-fix focused, resident-session, provider-spawn Fusion, and start-operations
  companions pass in 0.071/0.057/7.036/16.289 seconds. The actual provider
  spawn receives its configured OpenRouter key while an unrelated sentinel is
  absent. No provider or network call occurs.
- The exhaustive shard closure now invokes the focused contract; authenticated
  structure is 18 shards, 6,951 lines, 1,238 assertions, aggregate SHA-256
  `6478ebeec37d6162abacf2ad51817674a3dc22bcf7c9c6327a4a730a3c322647`.
- One truthful 0.310-second pre-body exhaustive attempt rejected the legacy
  assertion owner after UTF-8 environment flags moved out of `extension.js`.
  After rebinding that assertion to `start_operations_environment.js` and
  authenticating shard 2, full exhaustive acceptance passed in 400.096 seconds
  under the unchanged 420-second release ceiling.
  (WSP 00/5/6/15/22/34/50/62/87/97)

## 2026-08-20 - R9 loop 7 projection pre-open allocation gate

- Pre-fix RED failed in 4.745 seconds: an 8-byte path grown to 2 MiB plus one
  at the open boundary recorded one target allocation before the old late
  identity rejection.
- Added deterministic pre-open growth and replacement probes plus negative,
  fractional, non-safe, exact-cap, and cap-plus-one size coverage. Allocation
  and read counters must remain zero for every rejected pre-allocation case.
- Post-fix projection race passes in 54.393 seconds and a parallel confirmation
  passes in 69.4 seconds; projection identity passes in 36.3 seconds. Aggregate
  governed-Git hardening passes in 145.365 seconds, ref/config semantics in
  60.015 seconds, and candidate WSP_62 in 0.285 seconds.
- RDD/FoundUp grounding passes in 13.3/1.4 seconds; backend contract/preflight/
  async/Fusion pass in 1.4/44.8/1.6/9.7 seconds. Manifest parity remains 1,360
  files at `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`.
  The 18-shard closure remains 6,950 lines and 1,238 assertions at aggregate
  `6f16dfa31ca2504b39509bf93c7848a44a8674d5d6d9103a2716f1418320155e`.
- One truthful 0.068-second pre-body attempt rejected the stale orchestrator
  digest pin. After all three exact pins matched the computed closure, full
  exhaustive acceptance passed in 402.947 seconds under the unchanged
  420-second ceiling. Adversarial Git and Unicode stderr remains expected.
  (WSP 00/15/22/34/50/62/87/97)

## 2026-08-18 - R9 loop 6 projection absence and stable-read bounds

- RED1 failed through the public snapshot API in 9.769 seconds: a present
  dangling `linked` junction was followed by `existsSync()`, misclassified as
  absent, and released as tracked deletion with a receipt.
- RED2 failed in 1.612 seconds and measured 2,101,256 bytes consumed from an
  8-byte open before the old `readFileSync(fd)` path rejected later.
- Identity fixtures cover valid nested deletion, dangling final/interposed
  parent, Windows junction capability, non-directory parent, synthetic lookup
  error, absent untracked record, and component substitution. Race fixtures
  cover bounded allocation/request/read, incomplete-short/zero/truncate,
  existing path replacement, and exact 0/2-MiB/2-MiB-plus-one boundaries.
- Post-fix direct projection identity and race modules pass in 18.612 and
  36.779 seconds. Candidate WSP_62 remains green with projection at 325 lines,
  identity at 377, race at 361, and all detected functions at or below 30.
- Aggregate hardening passes in 91.914 seconds; the R9 ref/config matrix passes
  in 50.932 seconds; RDD/FoundUp grounding passes in 12.202 seconds; and the
  backend/preflight/async/Fusion companion set passes in 44.929 seconds.
- Manifest parity passes at 1,360 files with digest
  `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`.
  The authenticated closure passes at 18 shards, 6,950 lines, 1,238 assertions,
  aggregate digest
  `14b474d304b0d92700c53c2efafd0921ff5fb760e876c4abc7ab52449c42b35a`,
  and 340.746 seconds under the unchanged 420-second exhaustive ceiling.
  Intentional malformed/corrupt Git-fixture stderr is negative-path evidence.
  Syntax, shard integrity, candidate WSP_62, and RedDog diff checks pass.
  (WSP 00/15/22/34/50/62/87/97)

## 2026-08-18 - R9 loop 5 Git-config semantic authority

- Pre-fix RED passed Git's public parser and 64-hex `HEAD^{commit}` for the
  quoted SHA-256 config spelling, then failed because RedDog's partial parser
  returned an invalid receipt. Canonical syntax had passed first.
- Expanded `test_governed_git_ref_formats.js` across canonical, quoted, hash-
  comment, and semicolon-comment SHA-256 settings in direct and real linked
  repositories, plus loose/packed/detached authority, standard SHA-1, and exact
  invalid 39/41/63/65/nonhex rejection.
- SHA-1 repositories carrying a 64-hex shape and SHA-256 repositories carrying
  a 40-hex shape are allowed only through structural receipt validation. The
  matrix requires the full named batch and status/stat/diff projection to fail
  through Git semantics while readiness remains truthfully structural/config-
  READY. True unborn projection behavior remains covered by the exhaustive
  shard.
- The first post-receipt GREEN attempt exposed detached projection fallback;
  the next exposed packed fallback. The final implementation uses internal
  bound/unborn classification only to preserve exact unborn behavior and uses
  Git `HEAD^{commit}` for semantic proof. The dedicated matrix passes in
  50.117 seconds after adding single-operation failure proofs.
- Five direct Git groups pass in 9.835/30.513/8.512/11.856/16.702 seconds and
  the aggregate passes in 89.564 seconds. Candidate WSP_62 and shard structure
  pass, with the projection module explicitly included after loop 5 changed
  that surface, at 18 shards, 6,948 lines, 1,237 assertions, aggregate SHA-256
  `ac4e2b2e0541f3e168911a3d43d7d1d99253556dd83c1f2ebff5f1c29338e72e`.
  RDD/FoundUp passes in 10.378 seconds; backend/runtime companions pass in
  47.702 seconds; manifest parity remains 1,360 files at
  `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`;
  corrected-scope exhaustive acceptance passes in 342.348 seconds under its
  unchanged 420-second ceiling. One pre-body exhaustive invocation truthfully
  failed on the old orchestrator digest pin before that second pin was updated.
  (WSP 00/15/22/34/50/62/87/97)

## 2026-08-18 - R9 loop 4 refs, SHA-256, and focused-suite containment

- RED ran Git's public `check-ref-format` and `HEAD^{commit}` against
  `feature+r9` and `特性-r9`; both were Git-valid 40-hex authorities but the
  pre-fix receipt returned `valid=false`. A supported SHA-256 repository
  produced a 64-hex semantic HEAD and was also rejected pre-fix.
- `test_governed_git_ref_formats.js` now covers valid Unicode/plus names, a
  Git-rejected invalid ref corpus, and SHA-1/SHA-256 direct/linked loose,
  packed, detached, malformed, and mixed-width cases. The matrix passes in
  20.909 seconds on the local SHA-256-capable Git; an explicit capability skip
  is retained for Git versions without SHA-256 initialization.
- Split the former 1,460-physical-line hardening test into shared fixtures and
  five cohesive contract groups, with projection identity/race separated to
  keep both below the JavaScript ceiling. Direct exits are green: projection
  identity 9.341 s, projection races 32.0 s, stable-I/O 8.905 s, topology/ref
  13.0 s, and authority/readiness 17.516 s. The original invocation path runs
  all original assertions in original order and passes in 90.404 s.
- Added `test_reddog_candidate_wsp62.js` as a candidate-only size proof. It
  checks scoped JS at <=400 physical lines, detected function/arrow blocks at
  <=30 lines, and current non-historical docs at <=1,000 lines; it passes in
  0.214 s. It explicitly does not substitute for backend runtime WSP_62 or
  claim general repository-wide compliance. Duplicate historical narrative
  moved to the existing ModLog so `INTERFACE.md` remains below the doc ceiling.
- Exhaustive part13 source-shape checks now bind the Unicode-capable branch
  parser and SHA-1/SHA-256 widths. Part18 invokes the aggregate hardening,
  ref/object-format, and candidate-size tests. Shard structure passes at 18
  shards, 6,948 lines, 1,237 assertions, aggregate SHA-256
  `7f27055731558879137898c74b345184104470180c9fd8bb964581406d70bd6c`.
- Expected adversarial Git stderr for malformed packed refs, shallow state, and
  corrupt objects remains part of the failure-closure fixtures; it is not a
  suite failure. Final gates are green: 14 syntax checks; RDD plus FoundUp in
  15.257 s; four backend compatibility/runtime-WSP_62 companions in 56.802 s;
  canonical manifest parity at 1,360 files and digest
  `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`;
  and final exhaustive validation in 309.251 s, including repair evidence, judgment
  verification, split aggregate, SHA matrix, and candidate proof.
  (WSP 00/15/22/34/50/62/87/97)

## 2026-08-18 - R9 authority receipt and shared-store isolation

- Required RED: safe sibling Git activity left linked `HEAD_SHA` and
  `TRACKED_PATHS` unchanged but the recursive common-store receipt invalidated
  both outputs. The focused suite separately proved the prior unrelated loose-
  object hardlink assertion encoded global hygiene rather than output safety.
- Added real linked fixtures for safe sibling/main index/HEAD/config.worktree,
  unrelated object/ref/replacement/ref-pack churn and snapshot survival. An
  objects/refs `opendirSync` tripwire enforces non-recursive ordinary receipts.
- Added fail-closed current symbolic/detached/packed/loose ref, authority index,
  relevant common/authority control, A/B output, second-pass error, topology,
  alternate/graft/refStorage, relevant-link, and required-object regressions.
  Existing R8 absence/mutation, no-write, safe.directory, replacement-disable,
  unborn, projection race, and output-shape contracts remain active.
- Repair-loop RED proved the old unbounded `readFileSync(fd)` accepted more
  than an 8-byte opened control after deterministic >1 MiB growth, even though
  the later receipt rejected it. Added exact requested/accepted byte bounds,
  incomplete-read, and path-substitution regressions. The implementation now
  allocates only the capped opened size, reads explicit remaining lengths, and
  avoids a binary-index UTF-8 copy.
- Added the exact malformed-packed-ref boundary: unrelated malformed lines are
  outside narrow receipt parsing, while `HEAD_SHA` fails the whole named batch
  when Git rejects the packed storage. No global all-ref validation is claimed.
- Loop2 public-API REDs add nested common-directory confinement, exact supported
  heads grammar, and malformed-current packed classification. The focused RED
  reported all three vulnerabilities before production edits. Post-change
  focused hardening is **PASS** in 80.2 seconds and exhaustive validation is
  **PASS** in 275.644 seconds, including RDD and the former FWG-006 point.
- Loop3 pre-fix RED executed every no-follow presence site and reported all as
  vulnerable, including direct/linked final and intermediate current-ref paths.
  Added public green requirements for exact absent/present/error classification,
  non-ENOENT failure closure, true-absent empty/unborn behavior, required
  `refs/heads`, and no-enumeration parent validation. Post-change focused
  hardening is **PASS** in 84.898 seconds and exhaustive validation is **PASS**
  in 279.575 seconds; loop2 timings above are historical evidence only.
- The three stale
  whole-store source assertions were replaced without changing 18 shards,
  6,944 source lines; source-shape assertions remain 1,236. Direct RDD plus
  FoundUp grounding are **PASS** in 12.830 seconds; backend compatibility/
  WSP_62 is **PASS** in 40.710 seconds; manifest parity is **PASS** at 1,360 files
  and digest `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`.
- Acceptance-worktree performance: 30 receipts averaged 15.248 ms (17.161 ms
  p95); three twice-executed authority quartets plus final receipt averaged
  1,118.705 ms. These measurements are evidence, not a fixed timing contract.
- The test contract explicitly does not claim global unrelated-store hygiene,
  continuous ABA detection, or transactionally enclosed FoundUp registry/
  schema byte reads. Those are separate concerns, not weakened assertions.

## 2026-08-18 - R8 optional worktree-config absence and acceptance boundary

- RED: both ordinary and linked repositories with worktree config enabled but
  the optional file absent failed as `git_configuration_unreadable`.
- Added focused fixtures requiring immutable `worktree_config_state=absent`,
  available `HEAD_SHA`/`TRACKED_PATHS`, READY readiness, no file creation, and
  `config_write_performed=false`. A mid-batch file creation must return only
  `Git storage changed during batch`.
- Focused hardening **PASS** in 65.266 seconds; syntax, direct offline RDD
  (16.006 seconds), and 18-shard/6,944-line/1,230-assertion integrity checks are
  **PASS**. Backend compatibility/preflight is **PASS** in 48.379 seconds, and
  canonical manifest `--check` remains **PASS** at 1,360 runtime files with
  digest `fdf3643a2cb8dd95dce1f31a2c96611f9cf7f60496efd268819cbefc3592129e`.
- The unchanged exhaustive runner is **BLOCKED**, not PASS: it reaches FWG-006
  after RDD and both bridge end-to-end checks. UNI-001 intentionally emits the
  nearby surrogate `UnicodeEncodeError`; a fresh process instead isolated the
  failure to whole-common-store fingerprint churn during the FoundUp
  four-command linked-worktree authority batch. This is recorded for the next
  tests-first P0 and is not masked by this optional-config test layer.
- No exhaustive shard changed, and the JavaScript-only delta is outside the
  authenticated Python backend manifest closure.

## 2026-08-16 - Maintenance backend closure refresh

- Revalidated canonical manifest generation, digest pinning, runtime closure,
  and extension compatibility constant: **5 passed**. No VSIX was built or
  published.

## 2026-08-16 - R7 path identity and exact WSP_62 containment

- RED: a real Windows index with `Foo.txt`/`foo.txt` minted one READY receipt,
  counted two paths, and projected the same NTFS file twice. Added Windows-case,
  ignored-case, ignored-directory-prefix, separator, NFC, canonical-full-path,
  hardlink, ignored-junction, and Linux case-sensitive regressions.
- RED: the direct Fusion WSP_62 contract measured HEAD 8,425, candidate 8,429,
  and hard ceiling 8,428, then failed. `extension.js` now measures exactly 8,425
  without a ceiling/exemption change; the direct contract passes.
- Full Git hardening passes in 37.5 seconds; backend/WSP_62 preflight passes in
  36.9 seconds. The direct Fusion contract is listed as a separate required
  release companion because it is not in the exhaustive shards. The exact
  clean, uninstrumented exhaustive contract passes in 297.6 seconds under the
  unchanged 420-second ceiling; author candidate remains `NEEDS_VERIFICATION`.

## 2026-08-16 - R6 instance isolation and absolute-last-read regressions

- RED: A allow-policy API changed from one path to zero after B deny-policy
  construction. RED: third-capture control mutation still minted a receipt.
- Added both policy orders, third/interleaved instances, mutable option object,
  failed/throwing construction, stable default canonical output equivalence,
  per-instance receipt counts, and cross-repo root-digest isolation.
- Added third-capture control mutation plus runtime call-order instrumentation:
  exactly three receipt starts and no worktree lstat, numeric file capture, or
  Git command after the final proof begins.
- Focused hardening **PASS** in 32.8 seconds; backend/WSP_62 preflight **PASS**
  in 36.8 seconds. The exact clean, uninstrumented exhaustive contract passes
  in 290.9 seconds under the unchanged 420-second ceiling; the author candidate
  remains `NEEDS_VERIFICATION` pending independent verification.

## 2026-08-16 - R5 named batch, projection receipt, ignored viability, and K guard

- REDs proved partial batch disclosure, accepted raw `-c` argv, released stale
  captured worktree bytes, 1,674-entry canonical ignored rejection, and model/
  collection calls for limits zero and negative.
- Added exact named-operation validation and whole-batch failure for unknown,
  duplicate, object, option-shaped, oversized, per-command failure, storage
  mutation, and caller-array mutation cases.
- Added stable-read mutation, ignored non-read/non-return, forced ignored-path
  collision, ignored-junction non-traversal, second-enumeration new/removed/
  renamed/index mutation, receipt-field, and canonical snapshot proofs. The
  expanded focused Git hardening suite passes in 25.2 seconds.
- Added direct `limit=0/-1` backend-untouchable cases; Tier-0 focused suite is
  **29 passed**. Manifest generator is **5 passed** and check reports 1,336
  runtime files at digest `932c35752db3f99a84ca31ee3d90eb2508f8ccac0193ab67d208b8357364cb81`.
- Shard structure is rebound at 18 shards, 6,944 lines, 1,230 assertions.
  WSP_62 split the runtime into 255-line context and 216-line projection
  modules; exact <=400-file/<=30-function gates pass. The maximum-bound
  500-changed/5,000-ignored fixture passed in 5.340 seconds; its named batch
  completed in 589 ms.
  Final expanded exhaustive execution is **PASS** in 303.7 seconds under the 420-second
  ceiling; the author candidate remains `NEEDS_VERIFICATION`.

## 2026-08-16 - Governed Git snapshot TOCTOU regressions

- Added adversarial `.git/HEAD` and config hardlink mutations plus an
  `info/exclude` mutation at three distinct snapshot phases.
- Pinned whole-snapshot failure with the truthful
  `Git storage changed during snapshot` reason.
- Retained exact command-scoped `safe.directory` and sanitized Git environment
  assertions. Focused hardening suite passes.
- Added a bounded multi-command receipt regression: mutation after the first
  command invalidates every result at the forced-uncached final gate.
- Isolated repeated FoundUp authority contexts as the exhaustive-suite long
  pole. Four independent commands previously caused eight full Git-storage
  traversals; the batched path retains two receipts and removes six traversals.
- Clean exhaustive result: **PASS**, 18 shards, 6,944 source lines, 1,229
  assertions, 289.65 seconds under the unchanged 420-second ceiling.

## 2026-08-16 - R3 manifest-closure author correction (0.4.101)

- RED: `git ls-files --error-unmatch` rejected
  `holo_index/core/collection_injections.py` while tracked
  `search_engine.py` imported it, and the checked-in manifest omitted it.
- Added a generator regression proving the tracked relative import resolves
  into `required_runtime_files` with its exact normalized SHA-256.
- Canonical generation now reports 1,335 runtime files and digest
  `4e173152775ebff0d58dd421b9de14446d0c6f05ad509c12c30afe3be7cde796`.
- This corrects the R2 author handoff; final evidence remains author-only and
  the candidate remains `NEEDS_VERIFICATION`.
- Validation: generator **4 passed**; focused Tier-0/MCP **86 passed**;
  canonical manifest check and backend compatibility/preflight PASS; exact
  WSP_62 measurements PASS; staged and unstaged diff checks PASS.
- Exhaustive was not rerun because R3 changed no shard/reconstructed extension
  source and the exhaustive runner does not reference this manifest edge. The
  direct generator, manifest, backend-preflight, and Python behavior gates are
  the WSP_97 equivalent evidence for this correction.

## 2026-08-16 - R2 verifier reconciliation (0.4.101)

- Added temp-only adversarial coverage for cached loose-object hardlinks,
  graft/shallow/info attributes/info exclude/config/config.worktree controls,
  owned-repo override disclosure, and fixed-command execution guards.
- Re-bound the exhaustive contract at 18 shards, 6,944 source lines, and 1,229
  assertions; the new Git hardening suite executes inside the final shard.
- `vsce ls --tree` includes readiness, storage, and hardening-test files.
- Measured metadata fingerprint and one-session snapshot costs; retained the
  20,000-entry fail-closed cap. Results are author evidence pending independent
  verification.
- Final exhaustive result: PASS in 370.4 seconds under the 420-second release
  ceiling, including repair-evidence, judgment-verifier, and governed-Git
  hardening end-to-end contracts.

## 2026-08-16 - Module Tier-0 retrieval compatibility pin (0.4.101)

- Updated package, runtime-build, backend-manifest, and sharded exhaustive
  contract identities for the authenticated Tier-0 retrieval closure.
- Added GGSD-001..008 adversarial contracts for canonical-root confinement,
  traversal/control/symlink-reparse rejection, option-shaped paths, exact
  per-command scope, ownership-readiness disclosure, no wildcard, and no
  config writes.
- Added `governed_git_readiness.js` to the WSP_62 preflight surface and proved
  package enumeration includes it; the split modules are 367/131 lines and
  every scanned function remains within 30 lines.
- Retained the runtime WSP_97 excerpt survival and marker-neutralization gates
  after moving the excerpt ahead of ordinary bounded evidence.
- Retained backend integrity, exact source reconstruction, and no-authority
  regressions.
- Final exhaustive result: 18 shards, 6,943 source lines, 1,229 assertions,
  PASS in 283.4 seconds. This remains a serial release/CI gate, not a fast
  per-query validation path.

## 2026-08-15 - Holo owner path projection pin (0.4.100)

- Updated version and backend-manifest assertions for repository-relative
  semantic evidence while retaining no-authority and integrity regressions.
- Added HUEB-001 through HUEB-009 proving indexed imperative text remains inert,
  embedded evidence-boundary markers are neutralized, and every model role
  prompt receives the untrusted-evidence system rule. The Fusion alias proves
  its outer system boundary and records internal provider roles as unobservable.
- Proved custom prompts always retain exactly one terminal evidence rule even
  when supplied rules occur beyond or across the 6,000-character boundary.
- Revalidated the sharded extension contract after adding the bounded evidence
  wrapper without creating a second retrieval or redaction system.

## 2026-08-15 - Grant-profile atomic provisioning pin (0.4.99)

- Updated version and backend-manifest assertions for the uncomposed atomic
  grant-profile provisioning closure.
- Retained backend-integrity and no-authority regressions.

## 2026-08-14 - Root-owned source-policy compatibility pin (0.4.98)

- Updated extension and backend-manifest assertions for owner config v4 and
  its canonical grant-service source-policy authority.

## 2026-08-14 - Exact-Git effect-admission compatibility pin (0.4.97)

- Updated extension and backend-manifest assertions for signed v7/v3
  grant-authority provenance admission.

## 2026-08-14 - Shared exact-Git runtime hardening pin (0.4.96)

- Updated the canonical build and backend-manifest assertions for the shared
  bounded-Git hardening reachable from the current runtime closure.
- Retained no-authority, backend-integrity, replacement-ref, and bounded-read
  regressions.

## 2026-08-14 - Grant-service archive closure pin (0.4.95)

- Updated version and backend-manifest assertions for the executable archive
  validation dependency closure, including relative-import, generator, and
  control-path rejection. Runtime behavior remains unchanged.

## 2026-08-14 - Owner-E0 generation-selection pin (0.4.94)

- Updated current-version assertions and the reachable canonical backend
  closure while retaining separate permission-rehydrator coverage.
- Retained backend-integrity and no-authority behavior.

## 2026-08-14 - Authenticated grant-service artifact pin (0.4.93)

- Updated current-version assertions and the canonical backend closure.
- Retained backend-integrity and no-authority behavior.

## 2026-08-14 - Grant-authority client manifest pin (0.4.92)

- Updated current-version contract assertions and the backend manifest closure.
- Thin-client behavior and authority remain unchanged.

## 2026-08-14 - Resident artifact-request ownership pin (0.4.91)

- Pinned the regenerated backend manifest and current build fixtures after
  consolidating artifact-request derivation in the bounded-worker stage.
- Retained extension contract, backend integrity and no-authority regressions.

## 2026-08-12 - PowerShell Holo owner-query transport (0.4.90)

- Added direct regressions for a leading UTF-8 BOM and malformed UTF-8.
- Revalidated the generated 1311-file runtime closure and extension version
  pin without granting query-time maintenance authority.

## 2026-08-12 - Elevated-consensus compatibility pin (0.4.89)

- Revalidated the generated 1311-file runtime closure and backend compatibility
  preflight after the canonical elevated-consensus hardening.
- Preserved fail-closed production composition and added no extension execution
  authority.

## 2026-08-12 - Grant-authority epoch compatibility pin (0.4.88)

- Pinned the regenerated backend manifest and current version fixtures after
  owner E0 policy v5 added the grant-authority key epoch.
- Added a full-context regression proving the absolute checkout path is
  replaced before Fusion redaction, including policy-shaped worktree names.
- Revalidated extension contracts without adding client execution authority.

## 2026-08-12 - Root protected-use compatibility pin (0.4.86)

- Re-pinned the backend integrity manifest to the root protected-use transport,
  protocol, client, service, and root-state closure.
- Kept the extension behavior unchanged and retained fail-closed production
  signer activation.

- Updated current build assertions and backend-manifest parity for the exact
  root-anchor foundation runtime files.

## 2026-08-12 - Durable revocation compatibility pin (0.4.83)

- Revalidated backend compatibility and extension contracts against the
  regenerated manifest digest and canonical 0.4.83 build identity.

## 2026-08-12 - Signer authority-separation compatibility (0.4.82)

- Pinned the regenerated backend manifest and version fixtures after signer E0
  authority-separation hardening.
- Revalidated backend compatibility and extension contracts without adding
  client behavior or execution authority.

## 2026-08-12 - Live-canary reconciliation compatibility (0.4.81)

- Pinned the regenerated backend manifest and version fixtures after the
  signer/live-canary contract matrix was reconciled to current WSP_15 policy.
- Revalidated backend compatibility and exhaustive extension contracts without
  adding client or execution authority.

## 2026-08-12 - External signer lease compatibility (0.4.80)

- Pinned the regenerated external signer lease backend manifest and retained
  existing extension/runtime contract assertions.
- No thin-client behavior or execution authority changed; pytest and candidate
  code remain outside this planning slice.

## 2026-08-11 - Live API test quarantine compatibility (0.4.78)

- Re-pinned the backend manifest and version fixtures after WRE registry
  classifier hardening; no extension authority behavior changed.

## 2026-08-11 - Canonical test registry compatibility (0.4.77)

- Pinned the regenerated backend manifest including the shared bounded Git
  archive helper used by WRE collection and differential diagnostics.
- Revalidated manifest generation, backend preflight, extension contracts, and
  source-worktree non-execution invariants.

## 2026-08-11 - Diagnostic differential compatibility (0.4.76)

- Pinned the regenerated 1,259-file backend manifest and canonical digest.
- Revalidated manifest generation, backend preflight, and extension contracts.

## 2026-08-11 - Exhaustive contract suite modularization

- Mechanically partitioned the unchanged 6,857-line exhaustive contract body
  into 18 ordered, syntax-safe shards of at most 400 lines.
- Added a manifest-bound shared-VM orchestrator that verifies every shard and
  the exact aggregate digest before preserving the original execution order.
- Added a fast structural regression for shard uniqueness, complete source
  reconstruction, 1,213 retained assertion calls, syntax, and WSP_62 ceilings.
- No extension runtime, backend manifest, package version, or test assertion
  behavior changed.

## 2026-08-11 - Baseline compatibility regressions (0.4.75)

- Normalized source line endings only for the static Copy-MD sanitizer
  assertion so the same security contract is enforced on Windows and Unix.
- Revalidated the regenerated backend manifest and version pin. No extension
  runtime behavior or disclosure policy changed.

## 2026-08-11 - Backend grounding manifest regressions (0.4.74)

- Pinned the regenerated 1,252-file backend manifest and canonical build ID.
- Revalidated backend compatibility and the complete extension contract after
  immutable repository evidence and bounded refinement entered the closure.

## 2026-08-10 - Orchestration prompt transparency regressions (0.4.73)

- Proved pre-gate projections contain no prompt body, blocked runs disclose no
  prompt, unsuccessful provider calls disclose only a digest, and only a
  successful bridge result with a matching prompt digest can display a body.
- Proved pre-gate metadata uses a process-local keyed correlation value rather
  than a raw prompt digest, and a local sanitizer mismatch withholds the body.
- Proved no-model routes identify themselves explicitly and never claim to be
  waiting for a redaction gate or inherit a speculative model role/context.
- Proved compatibility degradation wins over grounding rejection and remains a
  truthful no-model route with no provider/network call, including the
  pre-route progress messages.
- Proved context/composite review packets cannot impersonate the task prompt,
  dynamic Markdown fences neutralize headings, links, HTML, and embedded
  backticks, and provider identifiers stay absent.
- Proved every generated WSP task prompt requires retrieval, runtime-truth
  precedence, reuse-first classification, CoR refutation, WSP_15 economy,
  query/maintenance separation, and signed execution authority.
- Proved generic `look at the codebase what needs attention` requests enter the
  existing deep-dive manifest/direct-read gate, while prose slash fragments do
  not become fake repository targets.
- Proved generated worker prompts are rejected unless they bind WSP_00,
  WSP_97, WSP_15, selected author profile, execution plane, and authority boundary in addition to the
  mission, reads, failures, validation, and return contract.
- Proved role promotion, evidence invention, WSP bypass wording, and selected
  author-profile mismatch reject even when all required labels are present.
- Proved collapsed keyword-presence text and empty required sections cannot
  impersonate an executable worker prompt; required fields are line-anchored,
  and line/block comments, placeholders, or case-insensitive nested labels
  without values are rejected.
- Required sections now satisfy affirmative executable grammar: substantive
  mission, concrete read path, failure condition, validation action, and return
  artifact. Keyword-only and placeholder-only prompts fail, while novel task
  verbs remain valid without a hardcoded mission vocabulary.
- Governance fields require their own domain vocabulary, affirmative fields
  reject embedded skip/bypass wording, and lexically padded unrelated text
  cannot pass. Authority and failure policy use closed canonical values;
  self-grants, duplicate fields, embedded modal negation, and forward/reverse
  continue-on-invalid conditions reject. Indented duplicate-label smuggling,
  repeated Worker Prompt headings, non-text fences, and multiple prompt fences
  also reject. Failure conditions now use canonical uppercase `REJECT_ON`
  reason codes instead of attempting security decisions from open prose.
- Proved secret-shaped source filenames are denied consistently by JavaScript
  and Python target policies, and a nested Git ref changed to a hardlink after
  cache fill invalidates governed context.
- Proved compound secret-container names reject, safe token-management source
  remains readable, and `READ_PATH` parsing preserves a leading `t` instead of
  accidentally consuming it as whitespace.
- Added CodeQL regressions for 200KB spacing, trailing-dot/space suffixes,
  adversarial execution-plane input, and the alternate `--!>` HTML comment
  terminator, plus a multiple-need-token deep-dive bypass regression.
- Added both extracted 0.4.73 modules to the WSP_62 gate: each file is at most
  400 lines and each function is at most 30 lines.
  Comment syntax is forbidden inside the artifact so validation and worker
  consumption cannot disagree or synthesize tokens through comment stripping;
  list-marker-prefixed comments reject too. Canonical reason codes remain an
  open structural vocabulary rather than a hidden semantic allowlist, with no
  leading, trailing, or repeated underscore segments.
- Read targets use canonical `READ_PATH` entries. Natural-language denials such
  as avoid/without/prohibited/refrain cannot satisfy retrieval requirements;
  traversal, absolute, drive, UNC, device, and noncanonical separators reject.
- Worker-prompt `READ_PATH` and governed direct-read consumption now share one
  deny policy for repository metadata, environments, dependencies, VSIX,
  secret-like paths, and private-key containers. Regression probes preserve
  the authoritative Python bundle gate's stricter segment policy.
- Proved current `reasoning_tier` Run Trace packets and legacy `WSP_15 tier`
  packets both parse correctly, while continuation output emits only the new
  non-authoritative field name.
- Added WSP_62 file/function-span enforcement for both extracted prompt modules.

## 2026-08-09 - Progressive effect-stage regressions (0.4.72)

- Proved invalid and production settings resolve to audit, audit never opens
  action planning, the resident editor clamps bounded requests to audit, and
  the UI setting never grants authority.
- Proved the complete stage receipt survives queue consumption and signing,
  audit chains terminate after read-only worker dispatch, and audit authority
  cannot open the execution valve under a bounded root ceiling.
- Added explicit audit-versus-mutation editor classification coverage and
  canonical WSP_15 recomputation, exact-path attacker regressions, restart
  re-verification for no-effect audits, and regenerated backend-manifest
  coverage.

## 2026-08-09 - Single-input authority boundary hardening (0.4.71)

- Proved false-valued diagnostic fields and terse command-result logs cannot
  request resident work.
- Proved timestamped, JSON, and logfmt evidence starts at the exact diagnostic
  boundary while preceding operator constraints remain authoritative input.
- Proved timestamped logger prefixes (`[worker] ERROR`, dashed logger names),
  and `npm ERR!` remain inert without an explicit boundary, while inline prose
  such as `Fix runtime output formatting` remains ordinary operator scope.
- Proved accepted Wardrobe output requires a receipt and that resident
  submission consumes the Wardrobe admission result rather than the earlier
  generic runtime gate.
- Proved the canonical selector digest and process-local owner proof reject
  copied, mutated, injected, or malformed Wardrobe mappings.
- Proved selector execution rejects an unapproved interpreter, uses sealed
  `-I -S -B` startup with a materialized bootstrap, and that WRE, live-enqueue,
  and action-bearing resident consumers cannot advance when called directly
  without the immutable selector proof.
- Proved unmarked mixed action-looking text plus diagnostics cannot infer
  operator authority; the one-input route requires an explicit evidence marker.
- Proved polite compound implementation directives remain actionable.

## 2026-08-09 - Single conversation input and governed action routing (0.4.70)

- Proved the webview exposes exactly one textarea, Enter sends, and the legacy
  diagnostic bridge field is always empty.
- Proved one-input action-plus-log messages separate operator intent from
  diagnostic evidence without allowing evidence text to request action.
- Proved assessment-only diagnostic output remains non-actionable while an
  explicit operator action can pass the runtime-consumption gate after valid
  output and Fusion quorum.
- Proved generic implementation language sets the governed-action flag used to
  request the existing resident AgentDB/OpenClaw architect session.
- Added independent-review regressions for action words in raw log headers,
  assessment questions mentioning a fix, requested-path preservation, shared
  action vocabulary, and legacy resident-session opt-out precedence.

## 2026-08-09 - Governed DAEmon architect diagnosis (0.4.69)

- Proved explicit diagnostic intent reaches HIGH-tier HoloIndex/Fusion
  analysis while a bare raw log dump remains local and cannot self-promote.
- Proved secret-bearing lines never enter the model evidence projection, late
  root-cause errors survive bounded sampling, and routine INFO noise cannot
  displace them.
- Proved diagnostic architect output cannot become runtime authority and must
  be promoted through a separate explicit work request.
- Proved typed intent remains independent of evidence length/position, while
  raw JSON/logfmt prose, private keys, cookies, and signed URLs cannot
  self-promote or cross the evidence projection boundary.
- Proved prompt-authoring diagnostics cannot bypass projection, typed Run
  Traces take the architect path, recovery binds evidence against tampering,
  and recovered advisory output still grants no runtime action authority.
- Proved unfamiliar operator wording still projects separately typed evidence,
  while injected `Determine:` and worker-prompt text cannot alter validation
  or repair controls.

## 2026-08-09 - Defensive Fusion critic failover (0.4.68)

- Proved defensive retry wording contains no adversarial instruction language.
- Proved one provider abstention fails over to one distinct critic, records
  both attempts, and admits synthesis only when the second critic supplies a
  qualifying framing/evidence and WSP_15 priority challenge.
- Proved two non-challenging retries remain bounded and fail closed, while Copy
  MD exposes retry and abstention identities.

## 2026-08-09 - Stale HoloIndex authority recovery admission (0.4.67)

- Added current-versus-stale authority selection tests that preserve the
  independently read stale HEAD and root digest while rejecting dirty,
  unrelated, same-HEAD, or substituted authority bindings.
- Added incident runtime tests for zero-attempt mismatch admission, exact-SHA
  post-merge coordination, current-generation re-resolution, and fail-closed
  stale-after-CURRENT behavior.
- Added blocked-request tests proving staging can precede maintenance while
  claim/retry cannot, plus deterministic no-model dialogue and tri-state recall
  regressions.

## 2026-08-07 - HoloIndex blocked-request recovery binding (0.4.66)

- Added Python tests for strict incident rehydration, canonical task identity,
  the existing atomic Holo completion event, forged completion rejection, and
  exact generation-bound owner verification. Two real AgentDB clients sharing
  one SQLite file prove the coordination-event primary key admits one winner.
- Added extension tests for Unicode canonicalization, full incident binding,
  SecretStorage tamper detection and pre-call consumption, asynchronous
  waiting/terminal behavior, stale-packet replacement, post-stage poll re-arm,
  advisory-only retry, and bounded backoff.

## 2026-08-07 - Grounding-failure architect dialogue (0.4.65)

- Added focused receipt, prompt-boundary, sanitization, fallback, and immutable
  no-authority tests for the conversation-only grounding diagnosis.
- Extended the exhaustive extension contract to prove principal-only mode,
  zero history/repository evidence, stable runtime denial, and no process
  execution in the focused contract module.

## 2026-08-06 - Principal Memex live resident source (0.4.64)

- Added one-use SecretStorage source tests for exact shape, delete-before-use,
  invalid-packet destruction, cancellation, and unavailable-storage closure.
- Added extension contract assertions proving source bytes cross only the
  one-shot bridge packet and never enter resident intent or output state.
- Re-ran the resident source/admission/durable-cycle matrix, WSP 62, backend
  manifest parity, and the complete extension contract.
- Updated and ran the HoloIndex incident-repair version fixture so the full
  documented extension matrix agrees on 0.4.64.
- Proved failed resident preflight returns exact rejection reasons with zero
  bridge invocation or SecretStorage access.

## 2026-08-06 - Explicit signer request authority (0.4.63)

- Verified the regenerated 1,238-file backend closure and canonical manifest
  digest against the thin-client compatibility preflight.
- Re-ran signer domain, request-substitution, manifest, version, and extension
  contract regressions without granting extension-side authority.

## 2026-08-06 - Principal Memex resident-admission backend (0.4.62)

- Re-ran the complete extension contract and backend manifest parity checks.
- Confirmed version `0.4.62` uniquely pins the Principal Memex admission
  dependency closure without adding extension-side authority.

## 2026-08-06 - Conversation scope-kind backend boundary (0.4.61)

- Re-ran the complete extension contract suite against the new backend manifest
  pin and scope-kind boundary.
- Confirmed install version `0.4.61` uniquely identifies the accepted backend
  digest.

## 2026-08-06 - Conversation session authority source (0.4.60)

- Added forged, expired, ambiguous-subject, expected-principal, FoundUp-scope,
  protected-storage, narrow-environment, and no-credential-in-intent regressions.
- Re-ran the resident bridge/authentication matrix and exhaustive extension
  contract; no model/client call survives source verification failure.
- Added backend-manifest parity for the shared authority-profile rehydrator and
  re-ran compatibility checks after its effect-path integrations.

## 2026-08-06 - Conversation proposal backend compatibility (0.4.59)

- Regenerated the backend manifest and pinned its canonical digest after P2
  added authenticated conversation proposal dependencies.
- Re-ran manifest generation, compatibility preflight, extension contract, and
  scoped conversation/promotion gates.

## 2026-08-06 - Linked-worktree HoloIndex runtime-root resolution (0.4.58)

- Added same-repository primary-worktree resolution and unrelated-worktree
  fail-closed regressions.
- Added query-owner proof that repository evidence and dependency roots remain
  distinct.
- Re-ran owner, maintenance, manifest, compatibility, and extension contract
  gates plus one real generation-bound semantic query.

## 2026-08-06 - Conversation history policy enforcement (0.4.57)

- Added focused zero-admission tests for disabled, enabled-without-authenticated-
  scope, missing input, cross-FoundUp/secret-shaped raw history, setting changes,
  provider-history discard, and content-free telemetry.
- Extended the full extension contract to prove Fusion receives only policy-
  admitted history, editor state does not retain provider history, and Run Trace
  reports zero admitted turn IDs.

## 2026-08-05 - Current-generation trust binding manifest (0.4.56)

- Updated the exact generated backend-manifest pin and RedDog build identity
  after adding signer current-generation use-time evidence and preserving the
  external signer peer as the only future effect-authority issuer.
- Raised only the bounded manifest serialization cap to 320 KiB after the
  1,194-file closure exceeded 256 KiB, preserving reviewable pretty JSON and
  the independent 1,250-file and 32 MiB runtime bounds.
- Revalidated generator parity, backend compatibility, sealed-runtime negative
  paths, start-operations control, HoloIndex repair, and the complete extension
  contract.

## 2026-08-04 - HoloIndex convergence backend manifest

- Updated the exact generated backend-manifest pin after adding bounded,
  fail-closed vector-segment convergence to the trusted HoloIndex probe.
- Revalidated generator parity and the extension compatibility contracts.

## 2026-08-03 - Fusion critic retry route failover (0.4.54)

- Added the blocked-first/usable-second panel regression proving the one bounded
  adversarial retry selects the usable critic and can satisfy quorum only with a
  real evidence and WSP_15 challenge.
- Retained existing no-challenge, abstention, retry-recovery, and fail-closed
  synthesis coverage.

## 2026-08-03 - Upstream Hermes artifact runtime (0.4.53)

- Updated the extension/backend compatibility contract for the Hermes provider
  runtime files and RedDog 0.4.53 package identity.

## 2026-08-02 - Upstream OpenClaw artifact runtime (0.4.52)

- Updated exact extension-version and generated backend-manifest assertions.
- Covered provider effect truth, durable receipt rehydration, OpenClaw
  preflight/confinement, bounded command execution, and fail-closed Hermes
  production selection.

## 2026-08-02 - Canonical WSL agent runtime binding (0.4.51)

- Updated the exact generated backend-manifest pin and extension version.
- Added focused regressions for default-disabled probing, trusted Windows WSL
  resolution, strict version normalization, and startup menu continuity.

## 2026-08-02 - Governed runtime compatibility supplier contract (0.4.50)

- Updated extension/version and backend-manifest assertions for the tracked
  WRE compatibility evidence supplier.
- Preserved the cached-only, nonblocking startup and no-update boundary.
- Added adversarial coverage for recomputed self-hashes, mixed relative/absolute
  path aliasing, and production redirect-handler construction; integrity-only
  evidence cannot report authenticated `CURRENT`.

## 2026-08-02 - Runtime compatibility advisory manifest binding (0.4.49)

- Regenerated the backend manifest at 1,115 runtime files.
- Re-ran backend compatibility, generator, extension contract, and focused
  runtime/startup regressions after the version and digest pin update.

## 2026-08-02 - HoloIndex incident to WRE repair runtime (0.4.48)

- Commands:
  - `pytest -q test_reddog_holoindex_incident_repair_runtime.py test_holoindex_postmerge_coordinator.py test_reddog_start_operations_holo_repair.py test_generate_reddog_backend_manifest.py`
  - `node extensions/reddog/tests/test_holoindex_incident_repair.js`
- Status: PASS (`59 passed`; owner-query bridge `18 passed`; focused JavaScript contract passed).
- Coverage: process-local owner provenance, independent receipt-bound requery,
  authenticated owner-failure shape, authority binding, exact-HEAD
  coordinator reuse, deferred retry/cooldown state, current-generation owner
  re-query, strict primitive/digest boundaries, active-task deferral,
  startup-exhaustion receipts, bounded input/output, and no direct model/index.

## 2026-08-02 - HoloIndex persisted vector-segment proof (0.4.47)

- Revalidated the generated 1,109-file backend manifest, exact extension pin,
  and local compatibility preflight after the cold-start proof was added.
- Folded independent NO-GO reviews covering the incremental owner, forged
  query results, output bounds, writer finalization, Chroma migration behavior,
  and dependency pinning before publishing a replacement exact SHA.

## 2026-08-02 - Registry-driven FoundUp work grounding (0.4.46)

- Added generic resolver regressions across every canonical registry entity,
  conversational and cross-domain aliases, unknown/ambiguous identity,
  malformed registry/schema, traversal, dirty authority files, sensitive
  evidence paths, deterministic receipt, tampering, no hard-coded names, and
  no execution surfaces.
- Added extension integration checks proving registry targets reach typed
  grounding; identity survives continuity, wardrobe, work-order, WRE,
  OpenClaw, and resident-intent handoffs; missing evidence or widened mutation
  scope blocks; and direct-read evidence grants no authority.
- Added reviewer-driven regressions for recomputed forged receipts, nested
  mutation, checked-in schema conditionals, missing wardrobe use-time proof,
  and stale checkout rejection at WRE, OpenClaw, and resident dispatch.
- Reproduced the AntiFaFM direct-read budget failure through the real Holo
  bundle and proved mandatory evidence now fits. Added conversational generic
  and named-target grammar cases plus Python IPC boundary rejection tests.

## 2026-08-01 - Authority-worktree semantic owner repair (0.4.45)

- Added authority/workspace runtime-root forwarding regressions and
  revalidated the generated backend manifest and extension pin.
- Live generation-bound queries returned CURRENT evidence for the retrieval
  AutoResearch evaluator and M2M benchmark after the repair.

## 2026-07-30 - HoloIndex owner runtime compatibility release (0.4.44)

- Revalidated the generated backend manifest and exact extension pin after the
  HoloIndex owner-runtime dependency fix.
- Retained the canonical thin-client and authority-bound worker contracts.

## 2026-07-30 - Canonical thin-client release (0.4.43)

- Updated package, runtime banner, governed-work-order identity, README, and
  contract assertions to one canonical 0.4.43 version.
- Added packaging verification against current tracked source and generated
  backend compatibility constants.
- Confirmed the quarantined 0.4.42 Codex-intercept draft is not the packaged
  source.

## 2026-07-29 - Imperative semantic grounding normalization (0.4.37)

- Reproduced the `continue do the work needed to fix enhance holoindex`
  preflight failure and proved HoloIndex evidence now grounds the named subject.
- Added unrelated-evidence, coordinated-subject, explicit-target,
  quoted-action, and subjectless-pronoun regressions so normalization cannot
  weaken the fail-closed grounding boundary.
- Proved alternate connectors and smart-quoted action mentions cannot produce
  partial or accidental grounding.

## 2026-07-29 - HoloIndex health timeout calibration (0.4.36)

- Bound the production asynchronous health deadline to 30 seconds and retained
  the injected one-millisecond timeout regression.
- Live exact-SHA smoke proves the calibrated worker returns `CURRENT` without
  blocking the extension host thread.

## 2026-07-29 - Receipt-bound health and model freshness routing (0.4.35)

- Proved simple HoloIndex health questions route locally with no model call,
  Fusion panel, re-index, or execution authority, with a bounded worker timeout.
- Proved audit/repair/re-index and compound prompts cannot enter the fast path.
- Proved explicit freshness questions consume digest-validated provider
  receipts through a secret-free environment and cannot change model selection
  or runtime bindings.
- Added forged/extra/stale/future receipt, spawn/timeout/output-bound,
  missing-chronology, provider-recency, exact-header normalization, and live
  official-catalog coverage.

## 2026-07-29 - Generation-bound owner fallback preservation (0.4.34)

- Proved accepted owner evidence survives a non-JSON legacy bundle fallback.
- Proved untrusted fallback text is discarded and rejected owner results
  cannot manufacture a semantic bundle.
- Proved attacker-recomputed receipt hashes lack the process-local owner proof
  and admitted owner objects are deeply immutable.
- Proved caller dependency injection and shared-module monkeypatching cannot
  manufacture an admitted owner result.
- Proved the alternate rejected-owner scorecard path drops forged multiline
  errors plus unverified generation, freshness, and receipt claims.
- Proved telemetry no longer degrades to `parse_error` when the owner receipt
  is valid.

## 2026-07-29 - Provider-neutral RedDog Operations Skillz (0.4.33)

- Proved checkout confinement, role-only metadata, deterministic integrity
  receipts, model independence, and fail-closed missing/tampered Skillz.
- Revalidated start-operations binding, Holo repair, model-role separation,
  backend compatibility, and the complete extension contract.

## 2026-07-29 - HoloIndex cold owner startup alignment (0.4.32)

- Revalidated the generated backend manifest, exact extension pin, and complete
  extension contract after the supervisor lifecycle correction.

## 2026-07-29 - Start operations Holo repair/resume (0.4.31)

- Proved healthy-owner reuse performs no maintenance.
- Proved failed/stale grounding creates one bound AgentDB task, OpenClaw claims
  it, the exact route repairs Holo, and grounding retries once.
- Added tamper, stale-repository, execution-proof, handoff-failure, and forged
  extension-telemetry regressions.
- Proved the checked-in profile invokes owner health, semantic-evidence
  companions do not suppress a failed-owner repair, wrong assignees and replay
  reject, expired assignments recover once, and terminal tasks never requeue.
- Proved refreshed and already-current repair receipts, and sealed startup rather than
  the live checkout and do not inherit provider or authority credentials.

## 2026-07-29 - Start operations control (0.4.30)

- Added exact-command, homoglyph/newline rejection, receipt integrity,
  asynchronous bridge progress, model-binding, and no-effect boundary tests.
- Added Python-to-JavaScript receipt parity, stale request replay, cumulative
  stdout/frame caps, environment allowlist, and durable intent regressions.
- Proved bare/redirected interpreters and Python startup injection are rejected;
  a malicious `.pth` sentinel cannot run under the sealed `-I -S -B` bootstrap.
- Proved standard/dependency imports cannot be shadowed by the audited checkout
  and the control script exists only in a manifest-materialized source tree.
- Proved a hostile temp-root selection cannot materialize inside the repository.
- Proved a hostile dependency `modules` package loses to sealed source and
  post-copy source tampering fails before execution.
- Proved deleting a sealed package cannot fall through to a dependency package.
- Proved status, cancel, and resume authorization rejections preserve their
  validated resident intent IDs at the Python control boundary.
- Proved the frame cap rejects before dispatching an over-limit progress frame.
- Added backend tests for profile/head/model/budget bindings, dirty-root
  rejection, Holo deferral, resident controls, and WSP 62 module boundaries.
- Revalidated the generated 1,072-file manifest and exact extension pin.

## 2026-07-28 - Signed Memex dispatch compatibility (0.4.29)

- Proved exact Memex lineage survives signed dispatch and independent review.
- Proved post-signing substitution, malformed pairs, queue conflicts, falsy
  non-string values, and pre-schema serialized dispatches fail before effects.
- Revalidated the generated 1,062-file manifest and exact extension pin.

## 2026-07-28 - Signed-worker security repair compatibility (0.4.28)

- Proved canonical envelope verification yields a process-local sealed proof
  that cannot be reconstructed from a self-hashed mapping.
- Proved invalid assignment quarantine, finalization, result-ledger append, and
  assurance transitions are atomic and lease-fenced.
- Split the signed-worker and assurance regression monoliths into bounded,
  concern-specific suites without changing the collected test set.
- Revalidated the generated 1,060-file backend manifest and its exact digest.

## 2026-07-28 - Signed queue-lineage compatibility (0.4.27)

- Locked package, runtime, README, generated VSIX name, and context fixtures to
  0.4.27.
- Revalidated the 1,055-file backend manifest and bounded 1,100-file client
  capacity with unchanged integrity and byte limits.

## 2026-07-27 - Exact-SHA commit compatibility (0.4.26)

- Covered exact-base enforcement, scoped commit evidence, crash
  reconciliation, work-order lineage, canonical verifier admission, and
  separated author/verifier claims.

## 2026-07-27 - Checkout-local WRE Skillz compatibility (0.4.25)

- Proved the regenerated manifest and extension-pinned digest bind both the
  checkout-local WRE loader and its authoritative registry.
- Re-ran backend compatibility, extension contract, and packaging checks.

## 2026-07-27 - HoloIndex owner cold-start retry (0.4.24)

- Proved one transient process-private owner restart can recover semantic
  grounding and that a second failure stops at the retry ceiling.
- Proved configured owners are never restarted and stale failures remain
  single-attempt.
- Proved retry telemetry reaches bundle metadata and Copy MD Run Trace.

## 2026-07-27 - Backend manifest post-merge refresh (0.4.23)

- Recomputed the generated dependency closure and pinned its canonical digest.
- Added regression sentinels for the exact-SHA HoloIndex maintenance runtime.
- Re-ran generator, backend preflight, extension contract, and package
  integrity checks.

## 2026-07-25 - Semantic evidence receipt binding (0.4.22)

- Added canonical evidence serialization, digest, count, tamper, missing-evidence, and mutable-outer-result regressions.
- Proved RedDog consumes only the receipt-bound evidence serialization before Fusion.

## 2026-07-25 - HoloIndex parent-process watchdog (0.4.21)

- Proved an injected parent waiter terminates the child and a real child exits after its real intermediate parent terminates.
- Proved supervisor argv carries only the public parent PID, stdin is `DEVNULL`, and no bearer moves to argv.

## 2026-07-25 - HoloIndex owner probe budget (0.4.20)

- Proved an authenticated semantic health response beyond the legacy one-second socket window is accepted within the new 30-second bound.
- Re-ran owner lifecycle, manifest, extension, and backend compatibility gates.

## 2026-07-25 - HoloIndex owner lifecycle hardening (0.4.19)

- Proved occupied loopback ports fail before process spawn.
- Proved the parent liveness pipe is passed to the owner and closed during shutdown.
- Proved a real child watchdog exits after parent-pipe EOF.

## 2026-07-25 - HoloIndex authority-worktree binding (0.4.18)

- Added clean/dirty, same/foreign Git common-directory, exact/wrong HEAD, configured-path, owner-root forgery, post-query state-change, and no-mutation regressions.
- Extended the exhaustive extension contract to require root-digest and overlay bindings in both the owner result and canonical query receipt.
- Retained the exact 8,428-line `extension.js` WSP_62 ceiling.

## 2026-07-25 - Receipt-bound model runtime binding (0.4.17)

- Proved unconfigured fallback, valid panel topology, partial configuration, inside-repo rejection, tampered digest, reserved verifier role, role-model mismatch, policy/evidence mismatch, and zero verifier threshold rejection.
- Proved JavaScript canonical receipt validation, receipt-bound worker projection, explicit evaluation fallback, configured-invalid blocking, tampering rejection, reserved-role rejection, and bridge parsing.
- Extended the exhaustive extension contract with 0.4.17 model-binding Run Trace metadata.

## 2026-07-25 - Fusion semantic retry and quorum evidence (0.4.16)

- Proved an empty/`None` lead receives exactly one semantic retry and still blocks if the retry is empty.
- Proved an initially non-challenging panel receives one targeted adversarial retry and synthesis runs only after a material challenge.
- Proved `No material challenge:` cannot satisfy quorum even when it mentions framing and WSP_15 priority.
- Proved repeated lead/panel progress stages and calls remain valid, digest-bound, content-free receipts.

## 2026-07-25 - Conversational drafting route (0.4.15)

- Replayed the social reply-rewrite prompt and proved it selects regular single-model drafting with no HoloIndex or repository context.
- Proved manual Fusion, ULTRA effort, and repository-context selections are overridden for the bounded route.
- Proved pasted text is wrapped as untrusted data, worker-prompt authoring remains governed, and drafting output cannot pass the runtime-consumption gate.
- Added WSP_62 file/function checks for the extracted drafting policy.

## 2026-07-25 - Slash-token semantic suppression reconciliation (0.4.14)

- Replayed the exact `OpenClaw/WRE/Hermes` worker-state prompt and proved it produces a semantic target without a repo-file target.
- Proved the slash phrase remains in low-confidence telemetry and path-backed audits preserve the existing no-duplicate semantic behavior.
- Proved the accepted 189-character prompt fits the 500-character semantic query envelope while over-limit targets still fail closed.

## 2026-07-25 - Authoritative work-state grounding (0.4.13)

- Proved direct current/next-work questions route to a local read-only receipt while audits and implementation requests remain on the grounded reasoning path.
- Proved revision tamper, stale state, selected-slice mismatch, invalid WSP_15 allocation, missing governed lineage, internal paths, bridge failures, and malformed receipts fail closed.
- Proved local fast paths are selected before context construction and never call HoloIndex, Fusion, queue mutation, or execution.

## 2026-07-25 - Backend compatibility preflight (0.4.12)

- Proved extension-pinned manifest/API/executable-contract acceptance, the generated 989-file runtime dependency closure, and fail-closed rejection for omitted/tampered non-bridge dependencies.
- Added independent sentinels for `holo_index.py`, package-initializer relative imports, file-based dynamic loading, and digest-cache invalidation after a runtime file changes.
- Added exact-case tracked-path parity, package-relative dynamic-import, async event-loop, post-model bridge-gate, and webview-handler non-growth regressions.
- Proved every intermediate path component rejects in-root and escaping junctions/symlinks, and all new JavaScript modules/functions remain within WSP_62 ceilings.
- Proved an incompatible workspace stops before work-focus classification, HoloIndex, model, permission, and work-order paths and exposes only bounded compatibility telemetry.
- Reconciled the exhaustive live-enqueue expectation with the existing stronger
  admission-before-writer rejection order observed on the clean base.

## 2026-07-20 - Resident cycle CAS and authenticated editor client (0.4.11)

- Added canonical genesis, full-intent conflict, stale-revision, transition-state tamper, cancellation race, terminal retry, legacy cancel-only, and monotonic attempt-history regressions.
- Proved the editor bridge fails without host principal/FoundUp scope and routes accepted requests through `RedDogResidentArchitectClient`.

## 2026-07-20 - REDDOG_REPO_AUDIT_GROUNDING_FALLBACK_PHASE1 (RAG-001..RAG-012)

- Proved punctuation/case aliases resolve to one safe audit entity and select content-bearing implementation plus independent test/contract evidence outside the active-editor bias.
- Proved weak, missing, stale, or denied structured evidence activates bounded deterministic fallback; fixed private/tool-state roots are never entered, read, or selected.
- Proved final 12-file/96KB packing, 4KB-per-file/512KB candidate scanning, secure path/identity failures, stable receipts, protected-context non-vacuity, local pre-provider blocking, primary Fusion packet preservation, defensive critic wording, and abstention truth.

## 2026-07-20 - Fusion progress and OpenRouter usage receipts (0.4.10)

- Added receipt digest, hash-chain, tamper, usage, routing allowlist, failed-call, cap, and redaction-block regressions.
- Added fragmented stderr JSON decoding, bridge-run binding, safe UI projection, and Run Trace usage-summary coverage.

## 2026-07-19 - REDDOG_REPO_DEEP_DIVE_FOCUS_BOUND_TARGET_SELECTION_PHASE1

- Proved a complete p.fMALL corpus activates focus-core selection and an unrelated semantic runtime hit is excluded.
- Proved a cross-cutting semantic dependency receives a bounded slot only when its evidence text names p.fMALL.
- Proved explicit focus phrases outrank leading prose and focus matching is token-bound (`mall` does not match `small`; `api` does not match `rapid`).
- Proved incomplete focus corpora preserve broad discovery and off-pool targets fail the repository evidence gate.
- Proved a character-truncated `git ls-files` manifest remains explicitly incomplete after target filtering.
- Proved the Run Trace exposes anchor provenance, match mode, pool strategy, candidate count, cross-cutting targets, and fallback reason.

## 2026-07-19 - REDDOG_DEEP_DIVE_OWNER_FAILURE_DIRECT_READ_CONTINUITY_PHASE1

- Reproduced the exact 0.4.7 p.fMALL host prompt with an unavailable semantic owner.
- Proved the structured bundle remains active, all discovered targets enter governed direct read, source bytes survive, and the repository evidence gate passes.
- Proved generic repository wording creates no external-research target and instruction/WSP words cannot outrank the p.fMALL implementation, tests, and docs.
- Proved off-focus readable files cannot satisfy the deep-dive gate and the Run Trace exposes focus coverage.
- Proved repository prompt-injection text remains untrusted data, offline lexical fallback cannot forge direct-read use, and owner failures receive stable safe categories.
- Proved a capped repository manifest is surfaced and blocks deep-dive grounding rather than silently omitting later files.
- Preserved explicit semantic/external fail-closed behavior and query-only HoloIndex boundaries.

## 2026-07-19 - REDDOG_GROUNDED_TARGET_ASSIGNMENT_CONTINUITY_PHASE1

- Added extension contract coverage for resident intent v2, immutable grounded-target receipt generation, work-focus binding, and rejection when grounding is not ready.
- Added Python tamper batteries for receipt rehash, typed-target substitution, semantic-coverage downgrade, stale generation, index-gap, query-receipt, repo-recall, assignment, and AgentDB task bindings.
- Proved prompt-derived repository targets reach every OpenClaw assignment and task, semantic targets reach the worker HoloIndex query, and any substituted focus/target/receipt fails before index or model calls.
- Re-ran 136 resident bootstrap, bridge, durable-cycle, OpenClaw, worker, and research/decision tests plus the RedDog extension and Fusion ingress contracts.

## 2026-07-19 - REDDOG_HOLOINDEX_GENERATION_BOUND_QUERY_RUNTIME_PHASE1

- Added HGBQ-001..010 to prove the exact generation-bound acceptance predicate, stale/lexical/mismatched/reindex rejection, unbound semantic-hit removal, governed direct-read preservation, and Run Trace generation receipts.
- Added six Python bridge tests covering process-owned and configured owners, private handoff use, canonical query receipt creation, cleanup, bounded input validation, and secret-free failures.
- Added owner-supervisor regression tests proving authenticated stale-generation startup stops immediately, while unauthorized, malformed, and non-loopback responses cannot forge a terminal freshness error.
- Re-ran 69 owner-client, query-boundary, and owner-service tests plus the complete RedDog extension and Fusion ingress contracts.

## 2026-07-19 - REDDOG_BROAD_SEMANTIC_GROUNDING_NONVACUITY_PHASE1

- Proved `Audit pfmall.` derives one semantic target and no invented repository path, while the extension source contains no hardcoded `pfmall` literal.
- Proved a content-bearing HoloIndex hit for the requested subject passes and an unrelated hit fails per-target semantic coverage.
- Proved one topical hit and a path-only hit cannot certify a broad audit; distinct implementation plus test/docs evidence is required.
- Proved a single bounded expanded HoloIndex query preserves the original query, records its strategy, remains read-only, and never adds indexing or direct-read flags.
- Proved test, symbol, and knowledge HoloIndex buckets reach semantic evidence coverage.
- Proved `Audit it.` fails before Fusion with `grounding_target_universe_empty` instead of passing an empty target universe.
- Proved simple identity and pasted operational-diagnostic prompts retain their local exemptions and the grounding seam contains no runtime reindex path.
- Proved implementation requests containing diagnostic logs do not inherit the diagnostic exemption, and mixed repo-plus-architecture prompts retain both grounding obligations.
- Re-ran the complete Node extension contract and JavaScript syntax check.

## 2026-07-18 - REDDOG_EXPLICIT_EMPTY_FUSION_PANEL_FAIL_CLOSED_PHASE1

- Proved omitted/non-list panel input still selects compatibility defaults while explicit empty and invalid-only lists remain empty.
- Proved the extension ingress and `callFusion` stdin payload preserve omitted / non-list / explicit-empty / invalid-only / above-four / above-six panels across both Fusion modes; the focused contract uses a fake local child, removes the provider key, and asserts argv contains only the bridge script.
- Bound the JavaScript runtime cap to Python's canonical six-model cap, the extension forwarding limit and both package `maxItems` values to seven, and final receipts to `panel_models_truncated=true` when the extension-origin overflow sentinel arrives.
- Validated the exact-file `extension.js` WSP_62 ceiling and the exact-function Python bridge exemption, including temporary status, owner, 2026-09-30 expiry, named functions, and roadmap remediation anchors.
- Proved manual FoundUps Fusion and the OpenRouter Fusion alias reject explicit empty panels before `_chat_completion` / `_post_openrouter` can make a provider call.
- Exercised both Python modes end to end over the same six-case panel matrix and proved hostile `bridge_meta` cannot replace bridge-owned mode, lead, panel, truncation, quorum, or retry truth.
- Pinned `_openrouter_fusion_alias` to 45 lines after focused rejection/success extraction, moved manual rejection into a compliant public wrapper around the body-preserved Fusion core, split the new Python matrix into `test_advisory_model_panel_input_contract.py` (239 lines), and kept every focused JavaScript contract helper within the 30-line WSP_62 limit.
- Verification: `python -B -m pytest -q -p no:cacheprovider --tb=short scripts/tests/test_advisory_model_once_hardening.py scripts/tests/test_advisory_model_panel_input_contract.py` (39 passed, 17 subtests), `node extensions/reddog/tests/verify_fusion_panel_input_contract.js` (PASS), and `node --check` for the extension plus both contract runners. The exhaustive Node runner remains managed-sandbox blocked at its internal `spawnSync python` with `EPERM`.

## 2026-07-18 - REDDOG_KIMI_K3_ALL_ROLE_RUNTIME_BUDGET_HARDENING_PHASE1

- Added exact Kimi K3 and non-K3 `openrouter_single` receipt coverage for requested and provider-effective token budgets.
- Moved the new K3 all-role budget proofs into the focused `KimiK3RuntimeBudgetTests` class so the oversized legacy hardening class does not grow.
- Covered K3's 4096-token floor in direct, Fusion principal, and synthesis calls while retaining the existing panel-budget proof and non-K3 behavior.
- Verification: `python -B -m pytest -q -p no:cacheprovider --tb=short scripts/tests/test_advisory_model_once_hardening.py` and `node extensions/reddog/tests/verify_extension_contract.js`.

## 2026-07-18 - REDDOG_HOLO_SEMANTIC_FIRST_PHASE1

- Asserted semantic is the production default and lexical retrieval requires explicit `REDDOG_HOLO_RETRIEVAL_MODE=lexical` opt-down.
- Asserted semantic mode removes inherited `HOLO_SKIP_MODEL`, preserves an operator-set `HOLO_OFFLINE` network boundary, and keeps the read-only query guard.
- Asserted requested mode, actual retrieval mode, embedding backend, and routing state reach RedDog metadata, scorecards, and summaries.
- Simulated primary semantic failure and proved exactly one offline lexical fallback receives a valid scoped environment, closing the previous `env` block-scope failure.
- The exhaustive contract suite opts down to lexical for deterministic runtime; a separate live smoke proves the production semantic path and `sentence_transformers` receipt.

## 2026-07-18 - REDDOG_FUSION_KIMI_K3_PHASE1

- Asserted the 0.4.1 package/runtime version lock and default Kimi K3 panel membership.
- Asserted the bridge emits Kimi K3 requests with mandatory `max` reasoning, without temperature, and with the 4096-token panel budget.
- Retained Kimi K2.7 Code coverage so the default panel can compare the two Kimi generations.
- Reconciled the stale resident-session contract assertion with the already-shipped durable AgentDB runtime symbol; production resident code was not changed.

## 2026-07-09 - REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1 (WRE-DRY-001..WRE-DRY-010)

| ID | Asserts |
| --- | --- |
| WRE-DRY-001 | `buildWreOperationalSpineDryRunPreview` / section builder exported and reachable |
| WRE-DRY-002 | Preview emits `REDDOG_EXTENSION_TO_WRE_OPERATIONAL_SPINE_DRYRUN_WIRE_PHASE1` and target `reddog_wre_operational_spine` |
| WRE-DRY-003 | Preview records `dry_run_only=true`, no Python invocation, no spine invocation, no worktree create, no task execution |
| WRE-DRY-004 | Preview records no OpenClaw enqueue, no Hermes dispatch, no PR, no merge |
| WRE-DRY-005 | Preview uses full SHA256 `command_digest` and does not store raw work focus |
| WRE-DRY-006 | Secret-adjacent env-name text is sanitized in `command_redacted_summary` and Copy MD |
| WRE-DRY-007 | Copy MD includes `## WRE Operational Spine Dry-Run Preview` after governed handoff |
| WRE-DRY-008 | Source has no `execFileSync(...reddog_wre_operational_spine.py...)` call in this slice |
| WRE-DRY-009 | Blocked-local packets skip WRE preview wiring |
| WRE-DRY-010 | Future live use is gated by `VALVE_OPEN_WORKTREE_CREATE` and `012_sovereign` |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-07-07 - REDDOG_WORK_FOCUS_READ_CAPTURE_PROSE_TOKENIZATION_PHASE1 (WFTD-015..WFTD-020, v0.3.45)

| ID | Asserts |
| --- | --- |
| WFTD-015 | Flowing-prose `Read first:` prompt (the EXACT failed 0.3.44 shape: 3 files in one sentence, period+prose after breadcrumb_tracer.py, `and the breadcrumb/handoff layer`) derives EXACTLY the 3 real files; breadcrumb_tracer.py is present AND clean (no trailing " Determine..." / period); `derived=true`, source `read_first`; `extractProsePathTokens` + `work_focus_targets_dropped_low_confidence` present in source |
| WFTD-016 | Recall on the prose prompt with all 3 files present: `required_targets_total=3`, `required_targets_recalled=3`, `target_recall_ok=true`, `index_gap_detected=false` (inverts the 0.3.44 `total 4 / recalled 2 / ok false`); the required targets are EXACTLY the 3 real files |
| WFTD-017 | The `breadcrumb/handoff` slash-only fragment IS in `work_focus_targets_dropped_low_confidence`, is NOT a required target, is NOT in `required_targets_missing`, and does NOT flip `target_recall_ok` |
| WFTD-018 | Fix C: trailing `. , ; : ) ] }` trimmed from a derived path (via `extractTargetTokensFromLine`); a `${docs/a/b.py}` brace wrapper trims to the clean path (via `extractProsePathTokens`) |
| WFTD-019 | Option-3 REGRESSION: a BULLETED `Read first:` list (one path per line) still derives all 3 cleanly; clean bullets drop nothing |
| WFTD-020 | Tiered strictness: the M2M tier still accepts an intentionally-named DIRECTORY-style path (slash, no extension) via `m2m_read`; the SAME slash-only shape is DROPPED in flowing prose (prose stricter, explicit/M2M/bullet broader) |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-07-07 - REDDOG_WORK_FOCUS_TARGET_DERIVATION_PHASE1 (WFTD-001..WFTD-014)

| ID | Asserts |
| --- | --- |
| WFTD-001 | Header-only shape: `collectRequiredTargets` == `parseRequiredTargetPaths` (byte-identical, backward compatible); `derived=false`, source `required_block` |
| WFTD-002 | `Read first:` list of 3 repo paths derives all 3; source `read_first` |
| WFTD-003 | WSP_99 M2M `READ:` array derives its paths; source `m2m_read` |
| WFTD-004 | M2M `CTX.FILES` array derives its paths; the `CTX.FILES` KEY token is NOT derived; source `ctx_files` |
| WFTD-005 | Backticked repo paths derive; source `backtick_path` |
| WFTD-006 | Inline prose repo paths derive AND do not capture surrounding prose words; source `inline_path` |
| WFTD-007 | Denied paths (`.env`, traversal) EMITTED honestly by the deriver but DENIED by the existing gate (`isTargetReadPathDenied`); a legitimate path still derives |
| WFTD-008 | HoloIndex miss on derived paths: `required_targets_total > 0`, `index_gap_detected=true` (fetch fires), `work_focus_targets_derived=true` |
| WFTD-009 | No explicit AND no derivable paths: `required_targets_total=0`, recall `unknown`, `derived=false` (inference path intact) |
| WFTD-010 | Guard B-i: a ```powershell validation block naming `extension.js` derives NOTHING |
| WFTD-011 | Guard B-ii: a `SCOPE - OUT` bullet path is NOT derived; an in-scope `Read first` path in the same prompt IS derived |
| WFTD-012 | Regression (real Python CLI): multi-lane orchestration `Read first` prompt -> `required_targets_total >= 3`, `direct_read_fetch_attempted=true`, each named file fetched / rejected / honestly-missing |
| WFTD-013 | `work_focus_targets_derived` + `work_focus_target_derivation_sources` surface in `extractHoloIndexScorecard` and render in the Run Trace scorecard lines |
| WFTD-014 | ReDoS remediation (CodeQL js/polynomial-redos): `stripListMarker` parity (dash/numbered/multi-space bullets stripped; non-list + marker-without-whitespace return `isList=false`); the flagged `.match(/^(?:[-*+]...)` bullet-regex USE is absent from source; pathological 200KB-whitespace input stays linear (<200ms) |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-06-28 - REDDOG_REVIEW_PACKET_MEMORY_AND_FOLLOWUP_PHASE1 (Addendum G)

| ID | Asserts |
| --- | --- |
| G-001 | `buildSanitizedContinuationSummary` success path captures decision + PR refs |
| G-002 | Poisoned output strips private reasoning markers |
| G-003 | Blocked run stores safe redaction gate summary only |
| G-004 | `appendContinuationSummaryToWspPrompt` includes continuation block |
| G-005 | Continuation-augmented prompt passes fusion redaction gate |
| G-006 | Copy MD includes safe Continuation Summary section when provided |

**Run:** `node extensions/foundups_advisory_workers/tests/verify_extension_contract.js`

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING addendum (OSR-007..OSR-010)

| ID | Asserts |
| --- | --- |
| OSR-007 | Primary missing Evidence/Architect Trace/Verification gaps/Next safest step; supplement completes schema |
| OSR-008 | Repair trail maps single/panel stages to `repair_single_started` |
| OSR-009 | Repair prompt lists explicit `## Section` headers |
| OSR-010 | Failed repair still exposes repair metadata + missing_sections_after_repair |

## 2026-06-14 - REDDOG_OUTPUT_SCHEMA_REPAIR_HARDENING_PHASE1 (OSR-001..OSR-006)

| ID | Asserts |
| --- | --- |
| OSR-001 | `buildRepairBoundedContext()` minimal, declares repair pass |
| OSR-002 | Repair context notes egress-safe placeholders |
| OSR-003 | Minimal repair context passes Python gate |
| OSR-004 | `buildRepairPrompt` sanitizes block literals; gate passes |
| OSR-005 | `mergeRepairedOutput` satisfies Fusion schema when supplemented |
| OSR-006 | Run Trace exposes `repair_context_mode` / `repair_mode` |

Regression: UNI, TCI, THG unchanged.

## 2026-06-14 - ADDENDUM B bridge UTF-8 stdin (UNI-008..UNI-010)

| ID | Asserts |
| --- | --- |
| UNI-008 | `evaluate_redaction_gate(safe, EMDASH_UNICODE_CONTEXT)` passes (U+2014) |
| UNI-009 | `buildBridgePythonEnv` sets PYTHONIOENCODING + PYTHONUTF8 |
| UNI-010 | `test_main_em_dash_utf8_stdin_not_redactor_error` passes |

Regression: UNI-001..UNI-007, TCI, THG unchanged.

## 2026-06-14 - REDDOG_CONTEXT_UNICODE_NORMALIZATION_PHASE1 (UNI-001..UNI-007)

| ID | Asserts |
| --- | --- |
| UNI-001 | Lone surrogate breaks UTF-8 digest path without normalization |
| UNI-002 | `evaluate_redaction_gate(safe, MALFORMED_UNICODE_CONTEXT)` -> `redactor_error` |
| UNI-003 | `normalizeBridgeTextForUnicode` replaces lone surrogate; count > 0 |
| UNI-004 | Normalized context passes Python gate |
| UNI-005 | `BLOCKED_POLICY_CONTEXT` still -> `blocked_policy` |
| UNI-006 | `buildRunTraceSection` exposes unicode normalization telemetry |
| UNI-007 | No raw malformed surrogate in normalized text or Run Trace |

Regression: TCI-001..TCI-010 and THG-001..THG-006 must still pass.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-14 - REDDOG_ALWAYS_HOLOINDEX_GROUNDING_PHASE1 (THG-001..006)

| ID | Asserts |
| --- | --- |
| THG-001 | `resolveAutoContextMode(regular, 'auto') === 'wsp_holo'` |
| THG-002 | HIGH -> `wsp_holo_skillz` (unchanged) |
| THG-003 | ULTRA -> `wsp_holo_git_skillz` (unchanged) |
| THG-004 | `buildBoundedRepoContext('wsp_holo', REGULAR_SMOKE_PROMPT)` includes HoloIndex recall |
| THG-005 | `wsp_holo` returns non-null `holoindex_scorecard` |
| THG-006 | `modeSelectionReasoning` cites HoloIndex-grounded `wsp_holo` for REGULAR |

Regression: TCI-001..TCI-010 (#883) must still pass.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-14 - REDDOG_CONTEXT_TARGET_CONTENT_INCLUSION_PHASE1 (ADDENDUM E)

**Reuse:** `tests/fixtures.js` + registry below. Do not duplicate EXT-ACC-001 prompt strings in new tests.

### TEST_REGISTRY (contract runner)

| ID | Location | Asserts | Reuse for |
| --- | --- | --- | --- |
| TCI-001 | `verify_extension_contract.js` | `inferRecallTargetPaths(EXT_ACC_001_PROMPT)` -> `extension.js` | Recall inference regressions |
| TCI-002 | same | `readBoundedTargetSnippet` nonzero body, `omitted_reason: none` | Snippet read regressions |
| TCI-003 | same | `TARGET_READ_DENIED_PATHS` all rejected by `isTargetReadPathDenied` | Path safety regressions |
| TCI-004 | same | `resolveSafeRepoFile` ok for `extension.js` | Workspace confinement |
| TCI-005 | same | `buildTargetRecallContentSection` header + `target_content_included: true` | Section assembly |
| TCI-006 | same | `buildWsp97ProtocolExcerpt` protocol title present | WSP_97 excerpt on task match |
| TCI-007 | same | `buildBoundedRepoContext('wsp_holo_skillz', EXT_ACC_001_PROMPT)` integration | End-to-end bounded context |
| TCI-008 | same | `inferRecallTargetPaths(BUILD_COPY_MARKDOWN_PROMPT)` -> `extension.js` | Symbol/path dual inference |
| TCI-009 | same | `target_content_sanitized` + no raw block literals in target section | ADDENDUM F sanitization |
| TCI-010 | same | Python `evaluate_redaction_gate` PASS on target section + full EXT-ACC-001 context | Egress safety (no OpenRouter) |

**Gate probe helper:** `assertFusionRedactionGatePasses()` in contract runner (stdin to Python policy).

**Fixtures file:** `tests/fixtures.js` exports `EXT_ACC_001_PROMPT`, `EXT_ACC_001_TARGET_PATH`, `BUILD_COPY_MARKDOWN_PROMPT`, `TARGET_READ_DENIED_PATHS`.

**Prior slice (do not recreate):** HoloIndex path ranking -> `holo_index/tests/test_reddog_extension_bundle_recall.py` + TCI predecessor block (`evaluateTargetRecall`, `target_recall_ok`) in same contract file ~line 443.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-26 - HOLOINDEX_REDDOG_EXTENSION_INDEX_GAP_PHASE1
- Verified `extension.js` in top 3 for EXT-ACC-001 review query (bundle-json + pytest).
- Verified `extension.js:buildCopyMarkdown` top hit for buildCopyMarkdown query.
- Verified `scripts/advisory_model_once.py` in top 3 for bridge query.
- Verified `evaluateTargetRecall`: `target_recall_ok` false + `index_gap_detected` true when adjacent hits only.
- Verified Run Trace scorecard includes `code_hits_count` and `target_recall_ok`.

Commands:

```powershell
python -m pytest holo_index/tests/test_reddog_extension_bundle_recall.py -q
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-26 - External acceptance baseline docs
- Verified acceptance baseline doc exists with 15 prompt IDs (EXT-ACC-001..015).
- Verified WSP_97 acceptance rows and baseline-vs-replacement language present.
- Verified static contract references acceptance doc path (no live OpenRouter in CI).

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
python -B -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/advisory_model_once.py').read_text(encoding='utf-8'))"
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-25 - v0.3.21 Blocked Copy MD polish
- Verified adjacent duplicate Work Trail events dedupe; detail-bearing event retained.
- Verified blocked-local Copy MD has no duplicate `redaction_gate_blocked` lines.
- Verified conservative blocked-local handoff: `handoff_needed: unknown`, `reason: blocked_context_needs_local_0102_review`, `WSP_15 priority: P1`, `suggested_slice_name: none`.
- Verified successful substantive runs retain prior assertive handoff behavior when model output exists.
- Verified Copy MD excludes secret-adjacent strings.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-24 - v0.3.20 Redaction Gate + Governed Handoff Contract
- Verified blocked Copy MD includes `## Redaction Gate Report` with `BLOCKED_LOCALLY`, `made_network_call: false`, `blocked_payload_part: unknown`, `raw_snippets_included: false`.
- Verified blocked packet contains no `OPENROUTER_API_KEY`, Bearer, or sk- token patterns.
- Verified substantive Copy MD includes `## Governed Handoff Recommendation` with `authority_level: advisory_only`.
- Verified Work Trail cap at 50 events; `sanitizeCopyMdText` maps key visibility to `key_env_present: true/false`.
- Verified HoloIndex recall scorecard fields in Run Trace for `wsp_holo_skillz` context.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
git diff --check -- extensions/foundups_advisory_workers
```

## 2026-06-24 - v0.3.19 UX + Copy MD Contract
- Verified Working Tail DOM precedes toolbar and work focus composer in HTML order.
- Verified `Worker` UI label removed; `0102 Role` label present.
- Verified `buildCopyMarkdown` Run Trace fields, BLOCKED_LOCALLY redaction block, repair-failure warnings.
- Verified `detectMojibake` catches `` and ``.

## 2026-06-24 - v0.3.18 Branding Contract
- Verified user-facing branding uses Foundups(R)Agent while the internal package id and command id remain stable.
- Verified Fusion remains documented as an internal mode, not the product identity.

## 2026-06-23 v0.3.17 Working Trail Phase 2 CODE Tests

- Trail DOM + progress command shape + operator message rg gate.
- `REDDOG_STAGE_ACTIONS` key set equals unique `_progress` stages from bridge (16/16).
- Stage mapping: redaction_blocked -> barking, single_done -> pointing, panel_blocked -> sitting.
- Regex fallback: Work focus sent -> sniffing; Output schema incomplete -> digging.
- Terminal hold constant 3000ms; enrichRedactionBlockResult metadata contract.
- #870 work-focus regression guards retained.

Commands:

```powershell
node --check extensions/foundups_advisory_workers/extension.js
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
rg "Stopped before OpenRouter. Nothing left the machine." extensions/foundups_advisory_workers/extension.js
```

## 2026-06-22 - v0.3.16 Addendum C Gate Tests

- Python (8 tests): panel truncation meta; 429 main-path redaction-once + same body; 400 no retry; redaction_blocked zero network; panel_models_truncated in review_packet.
- JS contract: bridgeStreamCapExceeded non-vacuity; killBridgeChild once; shouldAcceptBridgeCompletion dispose guard; resolver configured/system/dotvenv paths; WSP_97 survives truncation; #870 work-focus regression guards.

Commands:

```powershell
python -B -m unittest scripts.tests.test_advisory_model_once_hardening -v
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-22 - v0.3.16 Bridge Hardening Tests

- Contract tests for python resolver, context budget, bridge_meta, output_cap_exceeded.
- Python unittest: panel cap, 429 retry then success (same body, one redaction path), 400 no retry.

## 2026-06-22 - v0.3.15 Work Focus to WSP Prompt Tests

- Verified UI uses work focus composer (`#workFocus`) and `012 work focus` scrollback label.
- Verified `constructWspTaskPrompt` embeds WSP_97, WSP_15 tier, and non-authoritative work focus.
- Verified `redactedDigest` hash/excerpt contract.
- Verified review packet fields: `work_focus_digest`, `wsp_prompt_digest`, `prompt_construction`.
- v0.3.14 auto-router contract tests remain unchanged.

## 2026-06-22 - v0.3.14 Auto Router + Skillz Context Tests

- Updated contract test for GLM-5.2 principal, DeepSeek V4 Pro critic, and Kimi K2.7 Code implementation critic.
- Verified Mode/Effort/Context are no longer 012-facing dropdowns.
- Verified auto context mapping: REGULAR -> none, HIGH -> WSP/Holo/Skillz, ULTRA -> WSP/Holo/git/Skillz.
- Verified Skillz/Wardrobe/Rolodex discovery context remains advisory-only and non-vacuous for YouTube comment ops.
- Verified `modeSelectionReasoning`, Architect Trace / Verification gaps schema, Fusion panel structure validation, and Skillz wiring in bounded repo context.
## 2026-06-22 - v0.3.13 Orchestrator Contract Tests

Validation added for REDDOG_FUSION_ORCHESTRATOR_PHASE1:

- Auto effort classifier functions exist in extension source.
- Security/auth prompts classify `ULTRA`.
- WSP/architecture prompts classify `HIGH` or `ULTRA`.
- Simple smoke prompts classify `REGULAR`.
- RedDog WSP work defaults to `foundups_fusion` manual panel.
- OpenRouter Fusion alias remains selectable when explicitly chosen.
- Schema validator detects missing required sections.
- Repair prompt forbids invented evidence and preserves content.
- Review packet includes `output_validation` metadata path.
- Layout contract from v0.3.12 still holds.

Command:

```powershell
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```

## 2026-06-22 - v0.3.12 Contract Tests

Validation added:

- Webview layout contract:
  - grid rows `auto minmax(0, 1fr) auto`
  - output pane owns scrolling
  - composer stays after output in DOM order
  - no Send/Clear buttons required
- WSP operating contract:
  - RedDog Architect worker mode present
  - WSP_15 priority requirement present
  - WSP_97 truth-label requirement present
- HoloIndex retrieval contract:
  - bundle-json first
  - `HOLO_SKIP_MODEL=1`
  - offline fallback only after bundle failure
- Bridge contract:
  - prompt/context redaction gate path present
  - explicit system prompt reaches Fusion alias/manual modes
- Package contract:
  - package version matches README and extension build string

Command:

```powershell
node extensions/foundups_advisory_workers/tests/verify_extension_contract.js
```
## 2026-08-12 - Independent grant-provider compatibility pin (0.4.87)
- Updated exhaustive contract fixtures to the exact extension/backend version.
