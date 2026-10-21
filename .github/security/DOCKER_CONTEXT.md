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

## Reproduced application-image build failure

The full root build at candidate f6b2e921 failed in job 119110949749 of
workflow 39566766401: pinned llama-cpp-python 0.2.72 could not find GCC,
and CMake reported unset C and C++ compilers. The earlier native-context
success did not reveal this application dependency defect.

The repair preserves Python 3.10, every Python requirement and the application
command. Install build-essential only for package compilation, purge it with
its unused dependencies in the same RUN layer, and retain libgomp1/libstdc++6
for the native runtime. Package indexes are removed in that same layer.
A new application-image job builds the actual Dockerfile with synthetic
credential canaries, checks source retention and compiler removal, imports
llama_cpp/whisper/fastapi/sqlalchemy offline, and runs pip check. It does not
start the application, use a model or publish/deploy the image. Its result
must be verified on the final candidate; a prepared test is not a passing test.

Installation requirement: https://pypi.org/project/llama-cpp-python/0.2.72/
Container cleanup guidance: https://docs.docker.com/build/building/best-practices/

## Verification and truthful limits

Local authoring checks cover Python syntax, unique confined fixture paths, JSON
and YAML structure. This authoring container has no Docker daemon and cannot clone
the repository; no local native-Docker, full pytest or Pyright pass is claimed.
Native fixture results, actual-image results and repository-bound receipt
validation must come from the candidate hosted workflow. The pinned Pyright
step checks the new verifier explicitly and requires at least one analyzed file
and zero errors; this is not a whole-repository typing baseline. A successful context
probe alone is NOT a successful application build. Even a successful image build
does not establish application behavior, GPU qualification or absence of secrets
under arbitrary filenames. Existing secret scanning remains a separate blocking owner.
The committed receipt deliberately records the broader mission as `blocked`.

## External directive: corrections and remaining work

| Item | Evidence-based disposition |
| --- | --- |
| WSP 97 v1.9 | Verified current. Seven mantra stages expand into nine operator actions. The supplied mission JSON is not itself a receipt or runtime work order. |
| PR backlog | The first 30 current account-owned open PRs were inspected; many are distinct product/campaign lanes. No global backlog clearance or safe-to-merge conclusion follows. Preserve unique work and require fresh checks. |
| HoloIndex memory | Actual root name is `E` followed by U+F03A, not `E` plus an abacus emoji. Its tracked tree contains vector binaries, pickle metadata and a WSP summary. The canonical `holo_index/storage_contract.py` already supplies platform-safe defaults and canonical/legacy environment resolution. Preserve historical data until provenance, active consumers, backup and migration/retrieval equivalence are verified; audit legacy callers instead of adding a duplicate resolver. Do not merge distinct memory authorities or reset semantic freshness. |
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

Need: prevent local sensitive paths entering image layers and repair the
reproduced application build failure. The context probe uses one stdlib verifier
and three scratch exports without application dependencies. The separate, bounded
application-image job installs the unchanged root dependencies. Neither job makes
model calls; the changed-file Pyright invocation is version-pinned.
Deferral: address this context boundary now; defer destructive migrations until
source and operational ownership are established. No authenticated WSP 15 runtime
allocation receipt or worker execution authority is asserted.

## Closure requirements

Review the exact diff; pass native context, changed-file Pyright, actual-image
and receipt checks plus all applicable existing checks; squash-merge only with
current review/protection requirements; read back main and verify the corresponding
Docker workflow run. Until then this
is an owned recoverable candidate, not merged remediation. This record does not
advance any RSI gate or claim full hardening-mission closure.

## Additional governance observations

The canonical catalog names WSP 62 Large File and Refactoring Enforcement
Protocol, and WSP 82 Citation and Cross-Reference Protocol. The external
wording is not authority for broad linter exemptions. WSP 71 and WSP 12
also govern security and dependency work.

Retrieved active rulesets 7923253 and 8987382 contain no required-status-check
rule; the latter requires a PR. Main metadata reports check enforcement off.
The separate legacy protection endpoint returns 403 to this integration.
Therefore complete administrative enforcement is not certified or changed.
This PR must still satisfy its own exact-source checks; no bypass is permitted.
