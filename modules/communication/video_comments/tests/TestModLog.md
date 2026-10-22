# video_comments TestModLog

## 2026-10-22 — PR #1759 inventory recovery and reader regressions

**Work-order correction:** this file was absent when the reader tests were
authored and run. Review identified the missed WSP 97 section 1.2B inventory gate.
This inventory was recovered during review by reading the actual eight
pre-existing test files, their functions, and effect/mock boundaries. It is not
backdated pre-authoring evidence. Runtime source and reader tests stayed frozen
during this documentation correction.

The pre-existing inventory is bound to base
`02d1c7c14c60487619287a9cb753ff3ddaa53c14`. The directory now contains those eight
files plus `test_commenting_control_plane.py`; `__init__.py` is package support.
The older README omitted `test_ytr1_runtime_hardening.py`. No pass count is
inferred from filenames, docstrings, or source inspection.

### Current inventory and reuse boundaries

| File | Coverage and reuse target | Effects, limits, and status for this slice |
| --- | --- | --- |
| `test_classifier_pipeline.py` | Five functions cover whacked-user tracking, classification timing, confidence by whack count, unknown-user defaults, and profile-to-classifier routing. Reuse for classification/profile integration. | Calls real `get_profile_store()`, `record_whacked_user()` and `get_classifier()` without temporary storage. Checks return booleans for `run_all_tests()` instead of pytest assertions; timing above the nominal threshold still returns success. Stateful; not run. |
| `test_like_single_comment.py` | `test_like_single_comment()` discovers channel uploads/comments and invokes `like_comment()`; heart behavior is described in logs. Reuse for an explicitly scoped capability probe. | Real authentication and API reads, followed by the action helper. Logged API limitations do not make execution offline. Not run. |
| `test_llm_integration.py` | `TestLLMIntegration`, `TestBackwardCompatibility`, and `TestWSPCompliance` cover fallback/errors, mocked responses, prompt structure, response length, dialogue history, missing-LLM behavior, public signatures, and module reuse. | Selected connector responses are mocked, but many real constructors run before replacement; ambient provider configuration and constructor/import effects are not isolated for the whole file. The dialogue case constructs its subsystem with a mock YouTube service. Partial mocks; not run. |
| `test_move2japan_access.py` | `test_move2japan_access()` reads channel metadata, uploads, recent videos, and comments. The final posting check is descriptive logging, not a posting assertion. | Authenticated live API reads and quota use, without a local network boundary. Readiness logs do not establish posting capability. Not run. |
| `test_poc_dialogue.py` | `CommentDialoguePOC.initialize()`, `run_poc()`, `display_status()`, and `test_specific_video()` wire realtime monitoring and status output; the CLI selects the PoC flow. | Authenticates, constructs `RealtimeCommentDialogue`, and starts monitoring that may auto-reply. The status loop is ongoing. Operational demo, not a bounded pytest acceptance suite. Not run. |
| `test_post_comment.py` | `post_comment_on_video()` selects a video and submits a top-level comment; `test_comment_capabilities()` calls it. | Real authentication, reads, and `commentThreads().insert(...).execute()` publication. Normal pytest collection can execute the top-level test function. Not run. |
| `test_reply_to_comment.py` | `test_reply_to_comment()` finds a comment and invokes `reply_to_comment()`; `demonstrate_reply_capability()` drives the demo. | Real authentication, API reads, and reply publication. Logging a sample request after quota failure is not delivery evidence. Not run. |
| `test_ytr1_runtime_hardening.py` | Eleven methods in `TestTTSModelExclusion`, `TestTTSTokenRejection`, `TestDefaultTopic`, and `TestStaleElementRecovery` cover text-model selection, audio-token rejection/numeric parsing, topic defaults, and single/double stale-element handling in the reply executor. | Selected HTTP calls and Selenium driver methods are mocked; production constructors/imports still run. Stale tests use a mock driver, not a real browser. Separate boundary qualification is needed before claiming whole-file offline execution. Not run in this reader slice. |
| `test_commenting_control_plane.py` | 53 parameterized cases cover shared schema/version, surfaces/message/expiry types and boundaries, configured paths across CWD changes, read-only shared precedence, malformed/missing-state fallback, local set/clear, and edits under active shared context followed by expiry/clear. Reuse for reader/storage contracts. | Temporary state and controlled time; actual queue resolver/constructor and reader. Relative-path fixture uses a temporary checkout root. No queue dispatch, account/model/browser calls. 53 passed in the measured run below; local fixture evidence only. |

### Reuse decision

None of the eight pre-existing files covers file-backed broadcast/context
resolution or legacy-setting mutation. A cohesive reader test file was warranted;
its follow-up persistence regressions extend that same file. Recovering this
missing owner artifact does not erase the initial ordering failure.

### Measured reader history

- Initial strict-reader suite: **47 passed**, zero failures/errors/skips, 0.92s.
  It did not cover edits while shared context was active.
- Independent whole-path review found that `set_promo()` read the merged view
  and could copy expiring shared text into non-expiring legacy storage. Six new
  regressions produced **6 failed, 47 passed**, 0.60s before repair.
- After legacy mutators were changed to read only local stored state:
  **53 passed**, zero failures/errors/skips, 0.64s. Cases include existing and
  missing legacy state, expiry and explicit shared clearing, original local
  message/enablement preservation, and local-clear provenance.

Execution used Windows `C:/Python312/python.exe` (CPython 3.12.2), with
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`, `PYTHON_DOTENV_DISABLED=1`, and
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`:

```text
C:/Python312/python.exe -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -o addopts= modules/communication/video_comments/tests/test_commenting_control_plane.py -q --tb=short
```

Local receipts are under
`O:/RedDog-Builder-Artifacts/pr-reconciliation-20261021/refresh/1759-comment-context/`:
`reader-qualification-receipt.json`, `reader-qualification-initial-47pass.json`,
`reader-tests.xml`, `persistence-before.xml`, and `persistence-after.xml`, with
matching logs. The receipt records source hashes observed after execution.
No whole-module coverage, hosted CI, production delivery, native-worker, or OS
sandbox result is claimed here.

Holo retrieval reported `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, freshness
`UNKNOWN`, and an index gap. Source/Git fallback and the missing-artifact
correction are explicit; no index rebuild or model call was used.

Applicable ownership: WSP 22 (test history), WSP 50 (source verification),
WSP 84 (reuse), and WSP 97 section 1.2B (inventory before test authoring).
