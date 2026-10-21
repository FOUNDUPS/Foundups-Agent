# Blocking secret scan

## Signing CI coverage budget — 2026-10-21

The grant-aware signing regression's three-minute step limit interrupted job
119109373540 at83% while tests were still progressing, without a failing
assertion or final result. Duplicate job119109577954 checked out the identical
merge16b8a01 and finished1469 passed/3 skipped in97.32seconds. The interrupted
run remains incomplete coverage; the successful duplicate does not erase it.

Raise only that CI step's bounded budget from3 to5minutes to accommodate the
observed slower runner. Test selection, commands, per-test/runtime deadlines,
job limits and failure enforcement remain unchanged. This is CI configuration,
not a production timeout or security-policy change.

WSP97 research compared both hosted logs and the exact workflow against main
da3a39e32. WSP15 allocation: C1/I3/D3/Impact3 =10; existing-owner maintenance.
Configuration validation compares parsed YAML against main after restoring only
this timeout field, requiring full structural equality. Existing17 secret-gate
regressions remain the test owner; no timing-sensitive duplicate test is added.
Hosted exact-head CI remains required; no service or credential is exercised.

## Grant startup changelog prose re-review — 2026-10-21

PR2167 security job119107129537 reported one `generic-api-key` finding in
`modules/communication/moltbot_bridge/ModLog.md` at line3612. Independent review
compared the full finding span against line3603 on main `a6b5efa2`: identical
ordinary committed-profile key-resolution prose, with no credential assignment
or literal. The nine-line changelog addition changed its whole-file binding.

Replayed both exact committed files with Gitleaks8.30.1 after verifying the release
archive against the workflow's SHA256 pin. Each scan returned exactly one finding,
exit1, and zero stderr bytes, with full redaction, the existing config, inline
allowances ignored and implicit ignore disabled. Sanitized binding evidence:

- Prior file SHA256: `a69ac33da83ce48ac53fc8743c738acb42885a63f3c1327c105da8996be41c69`.
- Prior exact reviewed binding: `e9a4a29140a6ec5052f328c50d4ef2872734699d814c107c69287f5bbd3539ef`.
- Current file SHA256: `a95a097d38132d4bf5712543e8f0ccf45fc3f60a5fc585f14fd36064be880a78`.
- Current exact binding: `2902fa07012568ff448d61c33fb6f823df973f1b111e17545f805d159c758f9a`.

Preserve all1291 existing records and add only this binding, for1292 total.
No matched value, scanner rule, exclusion, fingerprint algorithm or failure
behavior changed. Temporary redacted scan reports were removed after review.

## Move2Japan shared member page review — 2026-10-18

PR #2151 head `57a2a7a3e3b4fb41b7562585966e11b7d5384033` failed security
job `117808506171` on one current-tree finding in `public/member/index.html`.
Independent review compared the exact committed HTML with main `b9051be2`:
the Clerk publishable identifier and complete SDK script block are unchanged.
Clerk documents this identifier and SDK attribute for public frontend use.
The page changes invalidated its whole-file binding and moved the line from
23 to 25; the prior exact binding is already reviewed.

A checksum-verified Gitleaks 8.30.1 replay of the exact committed HTML produced
only that one `generic-api-key` finding at line 25, with zero stderr bytes.
Preserve all 828 existing records and append only its independently recomputed
whole-file/rule/line fingerprint (829 total). Runtime source, scanner rules,
scan scope, fingerprint calculation and failure behavior are unchanged.
Sanitized evidence: `reviewed-move2japan-member-evidence.json`. No matched value
is retained in the evidence. This review does not grant account or provider
authority and does not approve any other occurrence.
The existing `scripts/tests/test_ci_security_gate.py` regressions passed:
**17 passed in 0.33 seconds**, with plugin auto-loading disabled and no skips.
## Descriptor path-cost binding review — 2026-10-19

Independent exact-tree review of81e2a305582d974d54c0e4318d57d9c170b6d8bc
against main ed6da441f26a9847a539fb4dbe6315b0701cdedf accepted45 changed
whole-file bindings:7 unchanged historical lines and38 generated source hashes.
All1456 manifest mappings were independently recomputed from exact Git blobs.
Preserve all905 prior entries and add only45 reviewed fingerprints (950total).
No unknown finding, scanner rule, exclusion or runtime authority is approved.
Evidence: existing `next-startup/descriptor-path-publication-review/`
`staged-exact-security-review.json`, SHA256
`7eeac52371ba7f8c0964dcc353a8fee59f20859891e78b48fba834ff34e01f83`.
Review is unsigned independent Codex evidence, not native worker provenance.

## AntifaFM startup manifest re-review — 2026-10-18

The resident-chain CI failure required moving the Shorts launcher's existing
peak-window import into the scheduler function that uses it. Regeneration keeps
all 1,439 runtime members and changes only that launcher's source digest.
This alters the manifest's whole-file hash and invalidates 38 exact bindings.

Independent redacted scans compared accepted PR head
`c7b3c6f9ff76bb6953aa82b313a2c7aafd905dfb` with the staged candidate. Every
finding-bearing line and source-hash value is unchanged; each accepted binding
is in the existing 867-entry ledger. All 1,439 current runtime digests were
recomputed, and each flagged source was also verified against its staged and
accepted bytes using the unchanged generator normalization. Preserve all 867
entries and append only these 38 independently proved bindings (905 total).

The changed launcher hash is not a flagged candidate. No scanner, rule,
exclusion, version or fingerprint policy changes. Sanitized per-finding proof:
`reviewed-antifafm-startup-evidence.json`. This bounded provenance review does
not replace the final full-tree and introduced-history security gate.

## AntifaFM integration metadata review — 2026-10-18

PR2156 head `f90417d3fa53b965e6bd0ccab7c94e246b3d1280` failed security
job117798014049 after changing two files with previously reviewed metadata.
Independent review checked every finding against exact accepted base blobs:
38 unchanged manifest values were recomputed from their referenced source bytes
using the unchanged generator normalization; one unchanged bridge ModLog line
names a documented Python identifier, also verified in argument/variable syntax.
The current file hashes and line positions require 39 new exact fingerprints.
Preserve all 828 entries from main `b9051be28be1d55908b05c65fcb7ba8766edb577`
and append only these 39 individually proved bindings (867 total).

Two newly introduced example environment-variable names were also mistaken for
credentials by the scanner. Shorten those references within the owned commit;
their configuration fields and host-supplied credential mapping are unchanged.
They receive no reviewed exception. Preserve the failed scan as prior evidence.
No rule, path exclusion, version, fingerprint algorithm or scan coverage changes.
Sanitized per-finding proof, exact source bindings and classifications are in
`reviewed-antifafm-metadata-evidence.json`; candidate values are not included.

## Current-time permission source review — 2026-10-16

Independent review of staged tree `5ef8d298fd2b297d07d10f34cbead0ba5babe986`
against main `7a9fe860298398b86398fbb3f6dad79eca52a075` accepted 45 changed
whole-file bindings: seven unchanged previously reviewed historical lines and
38 generated SHA256 values independently recomputed from exact Git source blobs.
Preserve all 732 prior fingerprints and append these 45 exact bindings (777 total).
No unknown finding, scanner rule, path exclusion or authority grant is approved.
Evidence: `O:/RedDog-Builder-Artifacts/rsi-initial-manifest-20261015/next-startup/native-startup-publication-review/staged-exact-security-review.json`
and `proposed-fingerprint-additions.json`; unsigned independent Codex review.

## Initial manifest binding review — 2026-10-15

PR2136 head4aae1646e failed job116406279370 with44 changed whole-file bindings.
Independent exact-blob review proved all44 lines unchanged and previously reviewed:
37 generated source digests, six historical backlog metadata lines and one prior
authority-boundary prose line. Every manifest digest also recomputes from its
referenced committed source using the existing generator normalization. Preserve
all276 historical bindings and append only these44 exact fingerprints (320 total).
No rule, exclusion, fingerprint algorithm or unknown finding is approved.
Evidence: `O:/RedDog-Builder-Artifacts/rsi-initial-manifest-20261015/security-review.json`
and its reproducer; unsigned independent Codex review, not runtime authority.

## Writer manifest metadata re-review — 2026-10-14

PR2134 head `a1b1e92aa` failed security job115629644317: changing the generated
manifest invalidated37 whole-file bindings. Independent review verified every
reported line against exact-head source bytes using the generator's CRLF-to-LF
normalization:35 generic-key and2 Discord-token matches are source SHA256 metadata.
All37 prior fingerprints and historical source hashes were verified; no unknown
finding was approved. Retain233 prior entries and add37 exact bindings (270 total).
No scanner rule, scope or source changed. Failed CI38495316404 is preserved.
Evidence: existing20261014 enrollment directory,
`writer2/writer-manifest-security-review.json` (unsigned independent review).

## Protected initial writer documentation bindings — 2026-10-14

On base5dd7b7b9f, independent review rechecked the same seven unchanged metadata
findings against exact staged blobs: six backlog lines shifted37 and one ModLog
line shifted12. Five tokenizer source digests were recomputed, one Git blob was
verified (7,701 bytes), and one unchanged prose line was inspected. Add only their
seven reviewed bindings, retaining all226 prior fingerprints (233 total). No
scanner rule or coverage changed. Evidence: existing20261014 enrollment directory,
`writer2/writer-security-review.json`; source blobs are pinned in that review.

## Initial high-water documentation bindings — 2026-10-14

On base1af66972c, independent review rechecked the same seven unchanged metadata
findings against exact staged blobs: six backlog lines shifted36 and one ModLog
line shifted12. Five tokenizer source digests were recomputed, one Git blob was
verified (7,701 bytes), and one unchanged prose line was inspected. Add only their
seven reviewed bindings, retaining all219 prior fingerprints (226 total). No
scanner rule or coverage changed. Evidence: existing20261014 enrollment directory,
`high-water-security-review.json`; source blobs are pinned in that review.

## Isolated enrollment documentation review — 2026-10-14

PR2132 head665011821 produced seven unreviewed whole-file bindings after updates
to existing backlog and module ModLog. Independent exact-blob review checked each
finding against main a3f656700: six backlog lines shifted15 and one unchanged
changelog line shifted14. Five values match the installed tokenizer source SHA256;
one resolves to its recorded7,701-byte Git blob; the final finding is unchanged
previously reviewed prose. All seven old fingerprints are among the212 retained
records. Append only these seven reviewed bindings (219 total); no scanner rule,
path exclusion or history coverage changed. Failed CI38487655164 is preserved.
Evidence: `O:/RedDog-Builder-Artifacts/rsi-enrollment-20261014/security-review.json`.

`ci.yml` calls `security-scan.yml` for every pull request and main push. The
same workflow scans all retained history on Mondays at 05:20 JST and on manual
runs. It requires no service token/license and never uploads source to a scan
service. Gitleaks 8.30.1 is pinned by version and release archive SHA256.

CI accepts PRs targeting any branch, including stacked feature branches, and
reruns when a PR is retargeted. Use each PR's current head and base when checking
coverage; a passing descendant is not evidence that the parent head ran. The
`pull_request` event is retained; no privileged `pull_request_target` execution
is introduced. Workflow coverage is not GitHub branch-protection enforcement.

## 0102 operating loop

WSP 71 sections 5.4–5.5 govern ownership. 0102 retrieves alerts, verifies source,
repairs authorized defects, validates, and retains the result in the owning
module's ModLog/PR. Routine evidence is for 0102 continuity, not a download or
review assignment for 012. Communicate material outcomes and exact access or
authority blockers only; keep working on independent repairs.

1. Pin main, PR head/base and deployment source. Collect actual check/run status.
2. Review changed high-risk boundaries and distinguish scan categories/coverage.
3. For historical secret candidates, inspect the exact blob without emitting
   values. Prove fixture/hash/public-identifier classifications individually.
4. Repair source in an owned lane and test failure behavior. Preserve unresolved
   history and failed coverage; never auto-regenerate reviewed exceptions.
5. Record repair revision, validation, residual risk and deployment applicability.
   Production closure requires separate deployment and configuration evidence.

The current gate does not triage history automatically. WRE `security_scan`
remains a prototype/manual skill; AI Overseer's skill sentinel is a narrower
preflight. Neither is evidence of an installed full-repository security daemon.

The gate scans the entire tracked tree (all extensions), then the complete
introduced commit range, so adding and subsequently removing a secret in the
same pull request still fails. Scheduled/manual/new-branch scans use `--all`.
Nested `.env` files and environment variants fail independently of secret
content; only exact `.example`, `.sample`, and `.template` suffixes are allowed,
and their content is still scanned. Missing scanner, timeout, invalid output,
and other scanner errors fail. Only rule/path/line/commit metadata reaches logs;
reports are fully redacted, temporary, and not uploaded. Inline `gitleaks:allow`
and implicit `.gitleaksignore` files cannot silently suppress the gate.
Shallow checkouts fail before either scan: fetch full history first. This
guards local/manual callers as well as CI; `--all` only covers fetched refs,
so record the fetched-ref scope separately from complete commit ancestry.

## Reviewed findings — 2026-10-10

The initial tree scan of b4f1a97 produced 109 findings. 108 were inspected as
synthetic test canaries, public Firebase application identifiers, public Discord
server IDs, class/type/import names, enum/routing constants, or file/commit
hashes in generated manifests and historical roadmap/training records. The
hardcoded Cesium JWT in GotJunk `map-test.html` was **not** approved.

`reviewed-findings.json` records only opaque fingerprints, never credentials.
Each fingerprint is SHA256 of the NUL-separated relative file path, SHA256 of
**the entire file**, scanner rule, and start line. For historical findings the
file is loaded from the finding's exact commit, never current HEAD. Any content
change invalidates the exception, including replacing a synthetic value with a
real credential at the same line. There is no blanket test, directory, hash, or
provider exclusion. Reviewed findings cannot clear scanner errors.

Do not automatically regenerate this list. Review each new finding first; for
real exposed credentials revoke/rotate them and remove the literal. Editing a
reviewed file may require re-review of its synthetic/metadata findings. History
can contain older findings that are not covered by current-tree reviews; those
remain visible and blocking on full-history runs until individually resolved.

### Canary changelog prose re-review — 2026-10-13

PR #2129 added 11 lines to the moltbot bridge changelog at
`416b9cf79c472764ed7dcb7596f8637406770227`. The single generic-api-key
finding at line 3206 is unchanged authority-boundary prose from line 3195 of
`0bb7e6c68f05dd82dd69579ae5d81b93b55871c7`, whose exact fingerprint was
already reviewed. The same terminology appears in the module interface at
line 1834; the finding contains no credential assignment or literal. Independent
review verified exact committed bytes and retained all 109 existing records,
adding only one whole-file/rule/line fingerprint (110 total for this branch).
No matched values, scanner rules or exclusions changed. Sanitized evidence:
`O:/RedDog-Builder-Artifacts/rsi-owned-closure-20261013/canary-modlog-review.json`.

### Manifest metadata re-review — 2026-10-13

PR #2115 changed one generated manifest member hash. This invalidated 37
whole-file-bound reviews even though the 37 flagged lines were unchanged.
Each finding was independently inspected: 35 generic-api-key and two
discord-api-token matches are `required_runtime_sha256` entries whose 64-hex
values match the actual source members under the generator's CRLF normalization.
Append only those 37 exact fingerprints for the committed manifest at
`3af34371d4dcd8b1b2a7fe8f5c015462df8e04aa`; retain the 109 historical records.
No scanner rule, path exclusion or fingerprint algorithm changes. Any subsequent
manifest change requires another review. Sanitized per-finding evidence is at
`O:/RedDog-Builder-Artifacts/rsi-ci-closure-20261013/reviewed-metadata-evidence.json`.

The later canonical backlog update at `f73e7b712` shifted six previously reviewed
source-digest findings by21 lines. Each unchanged value was independently checked:
five match the installed `llama_tokenizer.py` SHA256; the sixth resolves to the
7,701-byte Git source blob for `IndependentSignerSecretGrantProvider`. Append only
those six exact current-file fingerprints, retaining146 prior records (152 total).
The introduced-history scan had zero findings. No scanner policy changes.
Evidence: `O:/RedDog-Builder-Artifacts/rsi-review-qualification-20261013/backlog-metadata-evidence.json`.

Archival reconciliation at `53edf24f6424fefb152431b90a2af81e8c0207b4`
shifted those same six backlog findings by49 further lines. Independent review
compared exact committed bytes with `f73e7b712`, rechecked all five installed
source hashes and the Git blob, and verified all six prior review fingerprints.
Append only the six new whole-file/rule/line fingerprints; preserve152 existing
records (158 total). No matched values, exclusions or scanner rules were added.
Evidence: `O:/RedDog-Builder-Artifacts/rsi-review-qualification-20261013/archival-backlog-metadata-evidence.json`.

Local invocation (with the pinned Gitleaks on PATH):

```
SECURITY_EVENT=pull_request SECURITY_BASE=<base-commit> SECURITY_HEAD=<head-commit> python .github/scripts/security_gate.py
```

Validation: `scripts/tests/test_ci_security_gate.py` covers fail-closed scanner
status, missing reports/binary, nested environment files, history ranges,
content-bound exceptions, and actual deployment-header shell success/failures.
The GotJunk deployment check now requires an HTTP success, a CSP frame-ancestors
directive, and nosniff; absence is a failed deployment verification.

## Historical manifest review — 2026-10-13

At main `0bb7e6c68f05dd82dd69579ae5d81b93b55871c7`, a scan of complete
main ancestry (3001 commits) returned 168 candidates: 24 already reviewed and
144 unreviewed. For 53 manifest findings, the referenced source was loaded at
the finding's exact commit and its SHA256 recomputed. Every value matched.
Only those 53 exact fingerprints were added; safe per-finding proof metadata
is retained in `reviewed-history-manifest-evidence.json`. The other 91 remain
unreviewed and blocking. This is neither a full retained-ref scan nor evidence
of credential revocation or secure deployed configuration.


## Historical triage continuation — 2026-10-18

At main `1c80f15ae2eee0f78300f297fb3e386275bc0aab`, reproduced the original
91 unreviewed findings and reviewed all exact historical blobs. Complete main
ancestry (3,031 commits) returned 170 candidates; the current tracked tree
returned 109, all already individually reviewed. Both scans exited 1 for
findings with zero stderr bytes; these results are not a clean whole-repository
security audit or full retained-ref scan.

- Cleared 52 historical occurrences through 51 new exact fingerprints: five
  recomputed source digests and 47 individually reviewed test fixtures, public
  client identifiers, type/class names, enum labels, routing names and prose.
- Kept 16 digest metadata entries blocking because the original referenced
  artifacts or matching source revision were not independently recovered.
  A prior current-tree exception does not substitute for that missing proof.
- Kept 23 credential-candidate occurrences blocking, deduplicated to five
  values (Cesium, LinkedIn, and three Google API keys). No occurrences of these
  values remain in the reviewed current tracked tree. Validity, revocation,
  restrictions and deployed copies remain UNKNOWN. No provider probing occurred.

Safe per-finding decisions and next actions are retained in
`reviewed-history-triage-evidence.json` for agent continuity. No matched values
are retained there. The blocking gate, rules, scan scope and failure handling
are unchanged. WSP 71 sections 5.4–5.5 already govern this work; no new protocol
or WRE scheduler is introduced. Remaining work belongs to the reviewing agent:
recover the original digest artifacts and obtain authorized provider-owner
revocation/restriction evidence. Do not treat source removal as revocation.
