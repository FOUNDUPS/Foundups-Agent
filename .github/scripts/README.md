# CI security verification scripts

## Inventory and reuse

- `security_gate.py`: existing blocking secret-scan owner. Regression coverage
  remains in `scripts/tests/test_ci_security_gate.py`. Scanner policy and reviewed
  fingerprints are unchanged by the Docker work.
- `check_docker_context.py`: native Docker build-context contract. It copies only
  synthetic fixtures, applies the root `.dockerignore`, checks both excluded
  sensitive paths and retained source, and exercises no-ignore/hide-all controls.
  This is a separate container-context contract, not another secret scanner.

Run `python .github/scripts/check_docker_context.py` from a checkout with Docker
and buildx available. Missing Docker, a file-specific ignore override, build
failure, timeout, leaked fixture, or missing source is a failure, never a skip.
The dedicated workflow executes it without application dependencies or credentials.

## Merge scope pilot

CI validates drafts on open and synchronization, and still runs on
reopen, edit and ready-for-review. A future reduction in metadata-triggered
work must preserve fresh results when the base moves or a PR is retargeted.

The shadow job binds the GitHub test-merge commit to both event parents and
compares its complete diff with the reviewed head diff. The initial ordinary
prose allowlist is limited to direct Markdown children of
`docs/ci-pilot/examples/`. Numbered WSPs, their master index and recognized
agent instructions use the policy lane. Unknown paths and mixed runtime
changes select full validation. Missing Git evidence fails the shadow job.

The job checks whitespace and repository links and anchors, using the pinned
Lychee release in offline mode. Policy changes also check changed WSP mirrors,
numbering and the Codex projection. CI continues to run the full existing suite,
including the tracked-tree and introduced-history secret scan. The shadow
job adds no new required status.

Compare the shadow duration with the five required checks on the same PR head,
base and test-merge SHA. Candidate fast-path time is the last of the shadow,
secret-scan and HoloIndex checks to finish. Before cutover, qualify the policy
checks on a real WSP revision, test bad links and unsafe diffs, and verify
draft-to-ready and retarget behavior in GitHub. A required gate also needs
independent review protection for changes to its workflow and validators.

## Change record — 2026-10-21

### Application image build budget — 2026-10-26

Hosted job 121348145185 completed native wheel compilation and requirements
installation, then reached its 15-minute limit while compiler-package removal
was still progressing. The application-image job now allows 30 minutes; native
context remains bounded to 10 minutes. Build, context canaries, offline imports,
read-only/no-network inspection and pip-check remain required and unchanged.
The cancelled run is retained as a failed qualification; the composed head
requires a fresh complete image build and inspection.

### Inline CI dependency qualification — 2026-10-26

Workflow pins were audited separately from requirements files. Public admission
now selects pytest 9.0.3, FastAPI 0.162.0 and explicit Starlette 1.10.0; the old
FastAPI ceiling prevented the Starlette security fixes. Effect-lease consensus
now selects cryptography 50.0.2, including the updated OpenSSL wheel. The existing
public gate passed 210 tests with 95% coverage (90% required), and the unchanged
guarded consensus gate passed all 699 exact cases with stable source hashes in
isolated Python 3.12 environments. Exact-head hosted qualification is still required.

The first aiohttp 3.14.5 trials failed 30 existing cases with released
aioresponses 0.7.8 and 0.7.9; concrete constructor failures exposed a missing
`stream_writer` argument. Those failed trials remain evidence. A separately
qualified, checksum-gated CI-only backport on the released 0.7.9 wheel now passes
all 167 unchanged client cases and 14 focused compatibility/negative controls.
See [the backport provenance and removal condition](../security/AIORESPONSES_COMPAT.md).
Application source, authentication, assertions and the canonical test command
remain unchanged. Fresh hosted acceptance of the composed head is required.
The intentional isolated Gunicorn 21.2 parser negative control and conditionally
affected Chroma pin are unchanged.

2026-10-26 reconciliation keeps the native context contract and adds a supported
Python 3.12 application-image build while preserving current trust bootstrap.
The receipt base and workflow trigger now cover that reconciled source; current
hosted results are required before merge. Windows-host repair remains separate.

The existing secret-gate regression now recognizes literal pip install commands
in order, binds both bootstrap flags to that invocation, and ignores offline
filename checks and comments. Installer text
in unsupported wrappers, opaque code/heredocs, substitutions or conditional and
background execution fails for explicit review, including installer examples
printed by echo/printf. Its original Windows
creation/bootstrap/install ordering assertion remains. The two previously missed
isolated-install jobs (GitHub client and nomination contracts) reuse the existing
hash-bound bootstrap and trigger on trust-file changes. The scanner itself,
dependency selections and runtime authority are unchanged. This is a bounded
workflow-source contract, not a general shell interpreter or host attestation.

Added the Docker context contract after verifying root `COPY . .` had no root
ignore policy. Existing script/workflow inventory and secret-gate ownership were
reviewed before adding this distinct verifier. The fixture matrix is maintained
in the verifier; use its emitted counts rather than historical aggregate totals.
See `../security/DOCKER_CONTEXT.md` for evidence boundaries and audit dispositions.
No existing pytest file, registry entry, scanner, runtime admission, or test
quarantine was modified. The WSP 97 receipt records the broader mission as blocked;
its structural validity does not imply application build or RSI completion.
