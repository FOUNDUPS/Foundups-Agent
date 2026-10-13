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
