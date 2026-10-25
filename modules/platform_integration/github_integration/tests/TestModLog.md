# TestModLog

## 2026-10-26 — Observation HTTP policy in the existing client owner

- Pre-authoring allocation: FX delivery plan,11/P2; existing client/probe fixtures
  retrieved before edits. Fresh original135-case baseline passes without skips.
- Add13 methods/32 parameter cases to test_github_api_client.py; no new test file,
  dependency, registry entry, workflow or provider call. Retain all120 old client
  IDs/assertions; only the selector callback accepts a private transport keyword.
- Frozen desired RED146PASS/20FAIL, then unchanged-test GREEN166PASS. Independent
  review found duplicate encodings; allocated32nd case gives RED166PASS/1FAIL,
  then final167PASS after checking all encoding headers. Earlier
  context-manager construction and ineffective redirect/depth probes were fixed
  before freezing; their runs remain separate and do not establish acceptance.
- Use the actual ClientSession/aioresponses path, actual StreamReader read loop,
  explicit redirect callback sentinel and cancellation/release events. Byte limits
  test valid metadata plus whitespace below/at/above2MiB, not malformed JSON alone.
- Local Python3.12.10, pytest9.0.3, pytest-asyncio1.3.0, aiohttp3.13.5,
  aioresponses0.7.8; clean selected environment, credentials unset, no installs.
  Mock policy evidence is not live GitHub, wire framing/retry or OS confinement.
  Fresh exact-head hosted/security verification remains required. WSP6/22/50/97.

## 2026-10-26 — Client observation test inventory and baseline

- Reuse test_github_api_client.py for request behavior and immutable Git-file
  observations; preserve the original26 cases except the explicitly allocated
  unsupported-method/network-fixture corrections. Baseline on main5da1876 in a
  clean external venv:24PASS/2FAIL, close_issue_success and network_error_handling.
- Initial runner collection failed because its Windows NUL configuration did not
  admit the package path. Retained separately; fixed runner produced the actual
  baseline above. No baseline test or product source changed to obtain it.
- The other canonical unit member is test_reddog_github_permission_probe.py:
  permission capability mapping, mocked backend/CLI allowlist and work-order
  dry-run integration. It does not prove live permission or repository control.
- test_basic_functionality.py, test_github_integration.py and test_wsp_automation.py
  are quarantined for process-stream mutations; test_github_automation.py and
  test_wre_integration.py contain syntax errors. Their operational execution is
  outside this slice. Existing helper adapters remain mock-only infrastructure.
- Current workflow selects the two real unit owners explicitly, retains JUnit
  and actual wheel-resolution metadata; no directory sweep or provider credential.
  WSP6/22/50/84/97.
- Final:23 new methods/94 new cases;120 client and15 permission-probe cases pass.
  Exact root-tree/ref/mode/hash, one-byte boolean-size, concrete frozen DTO,
  private visibility, bounded IDs and transport/body sentinel controls included.
  Frozen RED26PASS/94FAIL; prior long-ID Windows setup failure stays retained.
  Portable receipt records exact IDs and source/result hashes; no live API proof.

## 2026-06-28 - REDDOG_GITHUB_PERMISSION_PROBE_PHASE1

- ADD `test_reddog_github_permission_probe.py` — 14 tests (capabilities, probe paths, dry-run integration, gh allowlist).
- CI uses mock backend only; no live GitHub.
