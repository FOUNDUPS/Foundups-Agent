# Python CA trust response — 2026-10-22 JST

## Decision and evidence

WSP15 allocation: C2/I5/D5/Impact5 = 17/P0. Repair the package-install trust
boundary before the separate skill-feedback slice. Base: `02d1c7c14c60487619287a9cb753ff3ddaa53c14`.
External principal authorized isolated implementation, PR validation and squash merge.

Mozilla incident 2083449 confirms eight weak intermediate keys, including cross-signs.
Python's security announcement recommends certifi2026.10.19 and pip26.2.2:
- https://bugzilla.mozilla.org/show_bug.cgi?id=2083449
- https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576
- https://pypi.org/pypi/pip/26.2.2/json
- https://pypi.org/pypi/certifi/2026.10.19/json

The two wheel SHA256 values in `requirements-trust-bootstrap.txt` were retrieved
from the corresponding PyPI JSON. Pip's digest also matches Python's security
announcement. Hash authentication is required because the downloader itself may
still trust the compromised CA. No TLS verification bypass is used.

## Implemented scope

- Pinned root certifi dependency; explicit hash-verified pip and certifi wheels.
- Bootstrap before dependency installation in all five current pip-installing
  workflow files and the root Dockerfile, including the separate Windows MCP venv.
- Existing workflow tests extended for ordering/hash binding; no extra scanner.
- No changes to runtime admission, credential custody, other instances or PR branches.

## Verification

A newly created isolated Linux Python3.12 venv upgraded from pip25.0.1 to
pip26.2.2 and certifi2026.10.19 through the real checksum-enforcing command.
Both application certifi and pip's vendored certifi contain120 roots and lack
`emSign Root TLS CA - G3`. The existing security-gate suite plus bootstrap
configuration cases passes20 tests. YAML parsed and `git diff --check` passed.
This is local installation/configuration evidence, not a live forged-chain test,
Docker image build, Windows runtime result or production fleet remediation.
Hosted exact-head checks and independent review remain convergence gates.

## Deployment follow-through

For each owned existing Python3.10+ environment, run its exact interpreter:

```sh
python -m pip --isolated install --upgrade --no-deps --require-hashes -r requirements-trust-bootstrap.txt
python -m pip check
python -c "import pip, certifi, pip._vendor.certifi as c; print(pip.__version__, certifi.__version__, c.__version__)"
```

This installs the reviewed incident baseline. Future versions require refreshed
reviewed hashes. Recreate unsupported older environments on a supported Python.
Rebuild deployed containers with current base images/system CA packages and restart
processes. Inspect custom `SSL_CERT_FILE`/`SSL_CERT_DIR`/`REQUESTS_CA_BUNDLE` and
extra Node CA configuration locally without publishing private paths or values.
Vendor-updated Node/Go/Rust/browser/OS trust remains a separate inventory task;
Python package updates do not remediate those clients or cross-signed trust paths
in other stores. Test rejection of the compromised chains using each actual client,
including cross-signs, plus valid HTTPS controls before claiming fleet protection.
Do not run credential-bearing requests against public incident test servers.

No live host inventory, deploy access or private Moshpit source is present in this
checkout. Production protection remains unverified. No compromise is inferred.

## WSP and coordination

V2 bootstrap was attempted and failed because Torch is absent. WSP00 section3.3.1's
existing torch-free fallback opened the tracker gate; detector witness is ABSENT.
Holo's source-bound lexical bundle succeeded: freshness UNKNOWN, index gap true;
no semantic acceptance, reindex or authority change. Retrieval had low specificity
and missing optional test docs; exact workflow/requirements reads resolved scope.
Current open-PR inventory returned37 items. PR2168 owns Docker context exclusions;
PR1762 owns frontend dependencies. Neither branch is changed by this slice.
Root requirements/CI changes can conflict with future lanes: re-read current main
and exact diff before landing. No claim of another instance's local cleanliness.

## Additional build inventory

Exact Docker inventory found two other Python recipes: simulator SSE and the
NanoClaw template. Both now inline the same hash-bound wheels, preserving their
module-local contexts (no extra context file dependency). The test compares these
URLs/digests with the canonical bootstrap. GotJunk's Node20 builder is now22.23.4,
aligned with its existing Node22 CI family; eSingularity's CI24.19.0 is24.22.1.
Node's official October21 advisory identifies22.23.4/24.22.1 as security releases:
https://nodejs.org/en/blog/vulnerability/october-2026-security-releases
The existing floating Node22 setup actions resolve a supported current22 release.
Docker daemon is unavailable here; actual image builds/rollout remain unverified.
The isolated tampered-wheel negative control also rejected altered bytes before
installation. No unrelated application dependency lockfile was rewritten.

Pre-publication compatibility check: downloaded official Node22.23.4 Linux x64
archive, verified SHA256 against its published SHASUMS
(`1805bcd35e6815559bd2eb97db438d3fdb0eb3a5e6a977b7c1badca76337e9ce`),
and confirmed Docker Hub's22.23.4-alpine manifest includes linux/amd64.
GotJunk `npm ci --ignore-scripts --no-audit --no-fund` and `npm run build` passed
using that exact Node binary (226 packages;470 modules transformed). Existing
large-chunk/deprecated-package warnings remain. This verifies the application
build on Linux; it does not verify Alpine container startup or live Cloud Run.
Merging the Dockerfile change triggers the repository's existing GotJunk deployment
workflow; its remote deployment outcome must be checked separately.
