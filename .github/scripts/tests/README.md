# CI merge verification tests

These stdlib unittest suites use disposable Git repositories and synthetic policy
documents. Run `python -B -m unittest discover -s .github/scripts/tests -p 'test_ci_merge_*.py'`.

- `test_ci_merge_scope.py` owns exact base/head/test-merge identity, complete raw
  diffs, ordinary prose, protected/mixed changes, deletion/rename and mode checks.
- `test_ci_merge_policy.py` owns changed WSP mirrors/catalog and proposal-only
  Skill document governance. Structural acceptance grants no runtime admission.

Security workflow/source regressions remain in
`scripts/tests/test_ci_security_gate.py`. WRE owns dependency scope, differential
evidence and exact-main check acceptance; reuse its existing suites.
