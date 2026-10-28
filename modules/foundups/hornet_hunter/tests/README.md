# Validation

Run `python -B -m unittest discover -s tests` from the module root. Tests build
in an isolated temporary directory, inspect canonical/JSON-LD/CSP consistency,
check the public video field allowlist and verify pinned public asset contracts.
No network, form submission, deployment or third-party message is performed.

Privacy also requires review of actual diff content; passing tests cannot prove
that every sentence is suitable for public release. The imported build was
compared against all 17 content pages of the published-source snapshot.

## Foundups-Agent integration preflight

When adding, moving or changing Python test files, stage the intended test paths
first: the canonical inventory uses `git ls-files`, not untracked discovery.
From the repository root, regenerate and verify through the existing owner:

```sh
python -B modules/infrastructure/wre_core/scripts/generate_test_registry.py --write
python -B modules/infrastructure/wre_core/scripts/generate_test_registry.py --check
```

Review the registry diff and commit it alongside the test change. Do not edit
classification or quarantine policy to bypass a failure. Module tests passing
does not establish repository CI acceptance; inspect the exact PR head's checks.
