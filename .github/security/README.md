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

Local invocation (with the pinned Gitleaks on PATH):

```
SECURITY_EVENT=pull_request SECURITY_BASE=<base-commit> SECURITY_HEAD=<head-commit> python .github/scripts/security_gate.py
```

Validation: `scripts/tests/test_ci_security_gate.py` covers fail-closed scanner
status, missing reports/binary, nested environment files, history ranges,
content-bound exceptions, and actual deployment-header shell success/failures.
The GotJunk deployment check now requires an HTTP success, a CSP frame-ancestors
directive, and nosniff; absence is a failed deployment verification.
