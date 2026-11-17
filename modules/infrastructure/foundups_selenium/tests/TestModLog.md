## TestModLog - FoundUps Selenium

### 2026-11-15 — Visual runner test reuse decision

The existing inventory below covers driver/Gemini helpers, telemetry, human
behavior, shadow lookup and the human-only verification hold. None exercises
`WREVisualTestRunner`, its PatternMemory result or observation/action boundary.
A separate offline runner contract suite is justified; use fake driver, bridge
and memory only. The browser `test_edge_*` harnesses are not offline tests.
No historical pass count below is evidence for this new contract.

Fresh validation: 25 runner cases passed; the adjacent pre-CLI-final selection
passed 118 (runner, two then-current caller controls, driver, shadow lookup,
human-only verification hold and attachment). After the CLI correction, the
71-case focused selection passed, including all 25 runner/three caller controls
plus registry/import-safety cases. Counts overlap. Existing CI contract tests
passed 40; canonical registry and Codex projection checks passed. Strict managed
workspace skill manifest and existing safety scanner passed (10 skill files).
Independent review passed 25 runner/three caller cases, a real active-event-loop
held-out and exact CLI-entrypoint exit controls. Both unavailable-vision cases
fail specifically on `True is False` against exact base e62e9eb.

Windows sandbox attempts stalled while asyncio created its internal socket pair;
owned test sessions were interrupted and a 10-second diagnostic reproduced the
runtime block before any mocked inference. Bounded unsandboxed offline reruns
passed without replacing asyncio or inventing a vision receipt. CI Bash contract
tests initially failed with Windows process-initialization exit 3221225794 in
the sandbox; the unchanged bounded rerun outside it passed 40. One inherited
`datetime.utcnow` warning occurred in the 118 selection. These are source tests,
not live browser/model, deployed site, installed Red Dog or production RSI proof.

First-head hosted CI then exposed the manual caller's eager scheduler import
(`pytz` absent in the bounded CI environment). Defer the actual DOM constructor
import and add a fourth native import-guard control, without adding dependencies.
The final local runner/caller/security selection passes 81 of 82; its one
unchanged deployment-shell test selects unavailable Windows WSL Bash through an
intentionally empty child environment. Initial cp932 read failures disappear
under UTF-8. This host limitation remains explicit; hosted Linux security-gate
regressions had passed before the separate tree scan's reviewed-prose binding
failure. No test or scanner gate is disabled. Fresh corrected-head CI is required.

Independent source review confirms the bridge ModLog finding is unchanged,
previously approved Markdown prose. Append one exact whole-file/rule/line binding
through the existing security ledger; all 4,500 old records and scanning rules
are retained. Full-tree/history scanner acceptance remains a hosted check.

### 2026-11-10 — Match attachment doubles to the CDP owner

The actual Chrome/Edge attachment fixture now supplies a Selenium-style command
executor map. Assertions retain driver identity and human-only handoff, and also
verify connection-specific `goog`/`ms` routing without mutating the shared map.
No production guard or test assertion was relaxed. The source-bound offline
selection passes **73 cases**, with zero failures/errors/skips or denied effects;
one existing synthetic-session `datetime.utcnow` deprecation warning remains.
The three isolated Python/Node process witnesses are deliberately deselected in
the process-denying local runner and remain in the full **76-case hosted suite**.
This repairs the CI test interface; it is not live browser qualification. WSP11/22/50/97.

### 2026-11-10 — Verification handoff inventory and offline checks

Final import-boundary correction: **85 passed, zero skips**, with one inherited
`datetime.utcnow` deprecation warning from synthetic session persistence.
Hosted Windows had exposed two import failures on hosts without an O drive;
the existing BrowserManager now creates the session directory only when saving.
A fresh subprocess forbids mkdir during guard import, and a synthetic save/load
retains persistence behavior. Hosted acceptance is required on this corrected
source; the earlier83-pass result did not cover this absent-drive boundary.

- `test_youtube_verification.py`: fake-clock 30-second minimum, longer visible
  challenge, STOP/unknown/corrupt control preservation, same-target release,
  waiting worker cancellation, per-port isolation, original uncertain transport
  error, real Selenium command names, actual attachment composition, synthetic
  Node DOM/shadow/iframe recognition and an isolated OS-lock subprocess witness.
  No browser, authentication, network or model operation is exercised.
- Reuse decision: `test_shadow_dom_finder.py` tests element lookup rather than
  handoff state; `dependency_launcher/tests/test_attach_recovery_no_kill.py`
  remains the attachment/no-kill owner, with its fake driver's interface extended.
- Existing inventory: `test_foundups_driver.py` covers driver/vision/telemetry
  helpers; `test_telemetry_store.py` covers SQLite events and concurrency;
  `test_human_behavior.py` and `test_undetected_browser.py` cover mocked driver
  interactions; `test_shadow_dom_finder.py` covers shadow lookup. The two
  `test_edge_*` files are browser validation harnesses and are excluded here.
- Initial combined run: 56 passed, 10 failed because attach doubles lacked
  `execute`. After the interface correction and protocol/error cases: 73 passed,
  zero skips; two expected asyncio configuration warnings with plugins disabled.
  Final results are recorded in the private task receipt and CI. Live popup
  recognition, daemon activation and scheduler manual takeover remain unproven.
- Final focused and adjacent Windows run: **83 passed, zero skips or warnings**,
  including the actual OS-lock subprocess, both comment-driver handle tests and
  existing shadow finder. CI runs the handoff/attachment selection on Windows
  and Linux. No live browser or network verification was performed.
- Added pytest-based smoke tests for FoundUpsDriver initialisation paths (2025-10-16).
- Expanded FoundUpsDriver coverage with telemetry, vision, typing, and posting behaviour tests (2025-10-17).
- Added annotation checks for analyze_ui and failure telemetry coverage for post_to_x (2025-10-18).
- Added screenshot hashing assertions for telemetry events (2025-10-18).
- Persisted session snapshots with hashes into JSONL archives and validated in tests (2025-10-18).
- **WSP 49 Compliance**: Relocated Edge browser validation tests from root to proper module location (2025-12-16):
  - Added `test_edge_youtube_studio.py` - BrowserManager Edge browser validation for YouTube Studio access
  - Added `test_edge_comment_processing.py` - Edge browser comment engagement validation (Like/Heart/Reply actions)
  - Tests validate Sprint 3 architecture (separate browsers for vision vs comments)
  - Cross-reference: [docs/EDGE_BROWSER_VALIDATION_TEST.md](../../../../docs/EDGE_BROWSER_VALIDATION_TEST.md)
