# GitPushDAE Test Module Log

## 2026-09-28 — Six entrypoint controls independently verified in hosted CI

WSP5/15/22/97. Existing `test_post_commit_social_runner.py` is extended rather
than creating another test file. Its three original pytest function ASTs are
unchanged. New `TestEntrypointEvidence` has six fixed case IDs and emits six
`HOOK_EVIDENCE` records when successful. See [fixed matrix](README.md#runner-entrypoint-evidence--2026-09-28).

Named hosted command:
`python -I -B modules/infrastructure/git_push_dae/tests/test_post_commit_social_runner.py TestEntrypointEvidence -v`.

Candidate `5935983ef8` passed **6/6** fixed methods, zero failures/errors/skips, in 1.11s in [CI36424604965](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36424604965). All six original `HOOK_EVIDENCE` records, child-source/argv bindings and synthetic JSONL hashes/payloads were independently checked. All ten PR checks and CI/CodeQL passed.

Exact final-head/main validation and owned closure remain receipt-bound. No production repair, ambient Windows reproduction, social delivery or retained RSI improvement is claimed. The original three pytest functions were preserved but not selected by this six-case command. Local application tests:0. A passing negative control demonstrates the qualified failure boundary.

## [2026-03-08] Post-Commit Social Runner Coverage
**WSP Protocol**: WSP 5 (Testing Standards), WSP 22 (Documentation), WSP 91 (Operational Reliability)

### Summary
- Added `test_post_commit_social_runner.py`.
- Verifies:
  - git commit metadata is normalized into a durable `git_push` event
  - JSONL event spooling works deterministically
  - social dispatch routes through `SocialMediaEventRouter`

### Verification
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest modules/infrastructure/git_push_dae/tests/test_post_commit_social_runner.py -q`
- Result: `3 passed`
## 2026-03-18: GitPushDAE launch stop-hook coverage
- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/infrastructure/git_push_dae/tests/test_launch_runtime.py tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Coverage:
  - Confirms `stop_git_push_dae()` returns `not_running` when no broker-managed instance exists.
  - Confirms the launch wrapper exposes a live GitPushDAE instance that can be stopped through the broker hook.
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `git_push_dae` with a real `stop_callable`.
