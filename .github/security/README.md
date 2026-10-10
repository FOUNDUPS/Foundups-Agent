# Blocking secret scan

`ci.yml` calls `security-scan.yml` for every pull request and main push. The
same workflow scans all retained history on Mondays at 05:20 JST and on manual
runs. It requires no service token/license and never uploads source to a scan
service. Gitleaks 8.30.1 is pinned by version and release archive SHA256.

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

Local invocation (with the pinned Gitleaks on PATH):

```
SECURITY_EVENT=pull_request SECURITY_BASE=<base-commit> SECURITY_HEAD=<head-commit> python .github/scripts/security_gate.py
```

Validation: `scripts/tests/test_ci_security_gate.py` covers fail-closed scanner
status, missing reports/binary, nested environment files, history ranges,
content-bound exceptions, and actual deployment-header shell success/failures.
The GotJunk deployment check now requires an HTTP success, a CSP frame-ancestors
directive, and nosniff; absence is a failed deployment verification.
