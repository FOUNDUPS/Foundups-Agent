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

## Audit Markdown fast path

### Trusted scope and proposal Skill documents - 2026-11-14

The existing scope job now loads its classifier and documentation verifiers
from the exact PR base. It compares complete merge-base-to-head and
event-base-to-test-merge raw diffs, including modes, status and blob IDs.
Candidate regression tests run on a separate runner without selection authority.
`ci_merge_scope.v1` records base, head, test-merge, complete paths and required
gates. Only successful scoped checks, live-base equality, a supported schema and
the server opt-in produce `fast_path=true`. Required `test (3.12)` and
`wre-verification-contracts` explicitly reject missing, failed, cancelled, pending
or malformed scope/regression results. Scoped gate failure cannot become success
through a fallback.

The `skill-proposal` lane admits additions named `SKILL.md` or `SKILLz.md` in a
new module-local `skillz/<name>/` directory. Both exact-base and candidate registry
evidence must be available. Registered names/locations, adjacent files, executors,
manifests, links, frontmatter and existing directories stay outside this pilot.
Its documentation schema requires an explicit PROPOSED / DOCUMENTATION ONLY
status, nonempty intent/boundary, governance, acceptance/learning and handoff
sections, and WSP 00/15/48/95/97/110 references. Formatting, offline repository
links and blocking security scanning still apply. This proves structure only;
independent review must assess content. It grants no runtime admission, production
promotion, semantic guarantee or measured RSI benefit.

The ordinary prose allowlist below is unchanged. WSP/security/runtime contracts,
workflow changes, registered/executable skills, mixed docs/Skill changes, deleted
or renamed paths, mode changes and unknown paths retain full verification.
Python also remains full: WRE registry projections are not an authenticated
general dependency graph. Existing `wre_test_impact_differential_gate.py`,
`wre_test_registry_differential_plan_runtime.py` and
`wre_test_differential_runtime.py` retain their planning/execution/evidence roles
and SYSTEMIC/stale-evidence escalation. This CI documentation pilot is separate
from WRE differential acceptance. Existing Git lifecycle verification still
requires exact-main checks; passing PR-head checks do not verify resulting main.

Security, lint, HoloIndex freshness, GotJunk security and report-only red-team
observations remain unconditional. Six unrelated runtime jobs omit execution only
under the validated pilot; all full-route commands and inventories remain.
Main pushes always run full verification. Separate workflows, including Moshpit
projection, retain their triggers. This is not global elimination of Python.

**Production activation is held.** The 2026-11-14 readback found no fast-path
variable, `strict_required_status_checks_policy=false`, and no CODEOWNERS file.
The invoking workflow remains candidate-controlled: trusted-base loading alone
does not prevent replacing the workflow. Separately protected workflow/policy
ownership, fresh server-required checks, independent review and isolated hosted
positive/negative/full-route qualification remain prerequisites. This change
alters no protection, security setting or Actions variable. Removing the opt-in
continues to restore full runtime execution. Unavailable exact-base verification
owners or a moving documentation base now fail the required checks even with
the opt-in off. Older stacked bases need the existing owners before qualification;
missing evidence is not a passing shadow result.

Reference [CI43583161268](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/43583161268)
at #2387 head `4c73c6486c7a91e028ec3fcaef1d09d37203c541` ran
`test (3.12)` for 484 seconds; an earlier run of that same head also ran full CI.
These are observed durations, not a controlled before/after saving. No production
compute reduction is claimed while activation is held.

### Existing activation contract

CI keeps the required check name `test (3.12)`. A repository administrator can
set the Actions variable `CI_AUDIT_FAST_PATH_BASE` to an exact PR target branch.
Until set, the Python job runs the existing suite. Set it to an isolated preview
branch to qualify the shortcut before enabling `main`. Removing the variable
restores the full suite on the next eligible PR event.

The shortcut admits regular Markdown additions and edits under
`docs/audits/prose/`, the dated Git workflow impact audit, and the existing
`docs/ci-pilot/examples/` fixtures. Reserve the prose directory for human-readable
reports. Policy, handoffs, CI, deployment, executable content and mixed changes
use the full suite. The check verifies both parents of the exact test-merge
commit and compares complete Git diffs. Missing classification evidence routes
full. Failed scoped checks or a moving base fail the required check.

Both routes retain separate secret scanning and the other required checks.
Scoped Markdown uses whitespace and offline relative link and anchor checks.
The shadow job also checks WSP mirrors, numbering and the Codex projection.
All original PR event types and post-merge tests remain in effect.

Before targeting `main`, require an independent code owner's approval for
workflow and validator changes and enable GitHub's up-to-date branch
requirement. Verify the fast and full paths and a rejected docs change on
an isolated target. Compare event-to-green and runner time on the exact
head, base and test-merge SHA.

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
