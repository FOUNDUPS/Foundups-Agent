# CI merge verification test history

## 2026-11-14 - inventory before extension

Retrieved both existing test files before adding coverage. `test_ci_merge_scope.py`
has eleven real-Git tests for prose/policy routing, mixed changes, renamed paths,
modes, merge-time substitution, wrong parents/checkout and shallow history.
`test_ci_merge_policy.py` has three tests for mirror drift, catalog uniqueness,
index removal and reserved numbering. Extend these owners for the bounded CI
pilot. Reuse WRE's differential and GitHub lifecycle suites for stale evidence,
pending/failed/absent checks and exact-main acceptance; do not duplicate them.

Extended the same owners to 21 scope/pipeline and 18 policy/proposal tests.
The 39-test suite passes in 49.849s with actual Git repositories and execution of
the workflow's aggregation Bash. Negative pipeline cases require exact exit 1,
so a shell launch failure cannot masquerade as a rejected prerequisite.
Independent review added seven synthetic schema probes and verified preservation
of all 14 original jobs, all full-route commands and five unchanged security/
required job bodies. Candidate tests were moved to a separate runner after review
identified that they could contaminate the planner environment.

Preserved failed observations: sandbox default temporary directories caused
49 setup/cleanup errors before useful assertions; explicit approved TMP/TEMP
resolved this. A later 38-test run had one Git Bash DLL initialization failure;
the unsandboxed bounded rerun passes all 39. Neither environment failure justified
changing product acceptance. WSP 6/22/34/50/84/97.

The additional publication-shell test executes server opt-in, wrong-base,
missing/stale-schema, push/full-route, moved-base and unavailable-lookup controls.
Final scope selection: 22 pass in 36.565s; unchanged policy selection: 18 pass in
19.947s. Together these cover 40 tests; the earlier 39 is retained history.
Existing WRE impact/registry/differential/scope/exact-main selection passes 168 in
57.12s. Security passes 52 cases; its remaining cleared-environment Bash case
passes separately in 0.90s with explicit native Git Bash lookup. Default Windows
WSL resolution is a recorded host limitation, not a changed assertion. Canonical
registry adds only `process` capability to the policy suite: 1,840 entries,
260 quarantined, unchanged membership. Hosted exact-head results remain required.
