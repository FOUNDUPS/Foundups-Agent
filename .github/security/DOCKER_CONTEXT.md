# Docker build-context hardening and external-audit disposition

Audit source: `a6b5efa2c83da31712df6d00540a773daa8748b3`, 2026-10-21.
Origin: 012-supplied Gemini 0102 directive. Execution: bounded local/CI/docs slice;
no resident worker, WRE admission, production deployment or credential operation.

## Verified defect and bounded repair

The root Dockerfile uses `COPY . .`, but the audited root tree has no
`.dockerignore`. Its credential warning is documentation, not an enforced context
boundary. Git ignore rules do not exclude files from a local Docker build context.
The new root policy excludes common credential paths, browser authentication,
private work lanes, local runtime state, caches, model files and the historical
malformed-drive index directory. Root memory source modules are explicitly retained.
Nothing is deleted from the repository or operator storage.

The new native verifier uses Docker's actual ignore matcher, not a Python glob
approximation. It builds a `FROM scratch` context export with synthetic fixtures,
requires sensitive paths absent and source paths present, then checks unfiltered
and hide-all controls. It does not load private files, install application
packages, pull a base image, publish an image or launch a service. A Dockerfile-
specific override fails pending separate qualification. The workflow has read-only
permissions, no persisted checkout credentials and no continue-on-error path.

Docker documentation: https://docs.docker.com/build/concepts/context/#dockerignore-files

## Verification and truthful limits

Local authoring checks cover Python syntax, unique confined fixture paths, JSON
and YAML structure. This authoring container has no Docker daemon and cannot clone
the repository; no local native-Docker, full pytest or Pyright pass is claimed.
Native fixture results and repository-bound receipt validation must come from the
exact-head hosted workflow. A successful context probe is NOT a successful build
of the full application Dockerfile and does not establish absence of secrets under
arbitrary filenames. Existing secret scanning remains a separate blocking owner.
The committed receipt deliberately records the broader mission as `blocked`.

## External directive: corrections and remaining work

| Item | Evidence-based disposition |
| --- | --- |
| WSP 97 v1.9 | Verified current. Seven mantra stages expand into nine operator actions. The supplied mission JSON is not itself a receipt or runtime work order. |
| PR backlog | The first 30 current account-owned open PRs were inspected; many are distinct product/campaign lanes. No global backlog clearance or safe-to-merge conclusion follows. Preserve unique work and require fresh checks. |
| HoloIndex memory | Actual root name is `E` followed by U+F03A, not `E` plus an abacus emoji. Its tracked tree contains vector binaries, pickle metadata and a WSP summary. Preserve it until provenance, active consumers, backup and migration/retrieval equivalence are verified. Do not merge distinct memory authorities or reset semantic freshness. |
| Credentials and Docker | Root context protection is the implemented slice. Existing historical secret triage and PR #2166 remain separate. No key is read, rotated or declared revoked here. |
| Dependencies | Root requirements mix provider APIs, tests, Whisper/audio, Torch, local inference, web and ORM packages. Module-specific installation already exists in CI. Modularization needs an import/caller matrix and exact-baseline environment tests, not indiscriminate removal. |
| Strict CI | Existing CI includes exact-source runtime checks, registry validation and blocking secret scanning. Add the distinct native-context check; do not relabel all CI report-only or remove historical baselines to force green. Full pytest/Pyright baselines remain unmeasured in this slice. |
| RedDog session receipts | The external directive supplies no failing receipt, session ID or reproducer. Restore only through the existing verified receipt owner after identifying a concrete defect; never fabricate historical execution evidence. |
| Receipt v1.1 | Existing validator checks structural evidence and canonical tracked WSP retrieval/base ancestry. Other evidence remains opaque. Passing it does not certify all eight mission steps, runtime side effects or RSI. |

## Alternatives and sequencing

A blanket memory rename/deletion or dependency rewrite would enlarge the risk and
interfere with pending RSI work. Copying `.gitignore` wholesale would also suppress
tracked application modules under its historical rules. A custom ignore parser
would test the wrong implementation. The minimal chosen move is a root Docker
policy plus native positive/negative fixtures. Test and reconcile that concern
separately before any memory/dependency migration. Preserve the unpublished
execution-lock work and 17-file installed-service checkpoint from 012's report;
this environment does not independently establish their current local state.

Need: prevent local sensitive paths entering image layers. Affordability: one
stdlib verifier, three scratch exports, no model calls or app-dependency install.
Deferral: address this context boundary now; defer destructive migrations until
source and operational ownership are established. No authenticated WSP 15 runtime
allocation receipt or worker execution authority is asserted.

## Closure requirements

Review the exact diff; pass native context and receipt checks plus all applicable
existing checks; squash-merge only with current review/protection requirements;
read back main and verify the corresponding native-context run. Until then this
is an owned recoverable candidate, not merged remediation. This record does not
advance any RSI gate or claim full hardening-mission closure.
