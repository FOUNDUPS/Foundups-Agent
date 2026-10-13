# Blocking secret scan

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
