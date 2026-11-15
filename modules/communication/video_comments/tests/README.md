# video_comments Tests

## 2026-11-07 driver handle isolation

`test_driver_handle_inheritance.py` compiles the actual connection method and
uses real Chrome/Edge Options and Service objects with inert WebDriver/Popen
boundaries. Both cases verify the existing debugger address and propagation of
`close_fds=True` through Selenium's actual service launch. No browser is started.
These two cases and the livechat capture tests run in the Windows/Ubuntu CI matrix.

## 2026-11-05 visual observation truth

`test_reply_visual_evidence.py` uses complete production definitions and private
synthetic collaborators. Nine cases cover useful DOM-only delivery, unavailable
or misleading vision, screenshot/hash binding, optional evidence-append failure,
and refusal to promote unknown posting. Qualified RED was 8 failures/1 pass;
GREEN with the unchanged quality/memory 60 is 69 passing, zero errors/skips or
denied effects. The existing closed effect guard is unchanged. This validates
result handling, not a real vision model or YouTube delivery.

## 2026-11-05 modern Studio identity

`test_studio_row_identity.py` has 118 cases through complete current extraction,
bind, snapshot and final Submit JavaScript, plus actual executor registry-context
controls. One fixed `STUDIO_DOM` models the observed original tree, toolbar,
zero/expanded controls and native creator badge. A useful zero-to-new-creator
readback follows exactly one synthetic Submit. URL, ownership, conflict,
multiple-inventory, native account-change and incomplete-state controls refuse.
The expanded label-one/four-loaded-row positive explicitly rejects count inference.

The private guard separately admits that exact Node program and binary, permits
no Python fixture workers or SQLite for this selection, clears credentials and
denies network/source writes. Initial RED69 had 35 failures/34 passes; review
RED71 reproduced exactly two additional ownership/baseline findings. Later
creator RED117 and the one-failure RED118 are retained separately. The historical
71 fixture used direct host ancestry; later native toolbar evidence corrected
that assumption in the current fixture/source. All original 71 test assertions
and parameter cases remain present.

`test_reply_editor_input.py` adds 19 cases: the unchanged fixed `EDITOR_DOM`
separates dirty textarea `value` from default text while retaining contenteditable
positives, and three actual Python typing-loop controls force a micro-edit or
stale recovery. RED16 had eight native failures; RED19 exposed micro-edit rewind
and foreign-text continuation. Final 118 + 19 pass with zero issues/denials.
These are source/fixture checks, not live browser/model/publication evidence.
The old 112 reply + 53 context names/assertions remain unchanged and also pass
on the composed final source. Two sender doubles now assert the explicit
`livechat` STOP scope, and the typing double recognizes the exact current
value/text getter. These are fixture contract updates, with no gate relaxation.

## 2026-11-05 optional memory readiness

`test_reply_memory_readiness.py` contains 23 bounded actual-definition controls.
Cold and warm positives reach assess/write/review; cold fixtures ask a useful
clarification and warm fixtures use only supplied grounding. Constructor/model
loader spies, cache-sentinel checks, cancellation between retrieval stages,
legacy defaults and refusal of a cold compatibility retry cover the new boundary.
Initial RED22 had 17 failures/5 passes; stricter RED23 had 18 failures/5 passes.
All 23 pass with the existing quality37 (60 combined), with no errors/skips or
denied effects under the unchanged repository EffectGuard and minimal child.
The strict VoiceMemory double in `test_reply_context_pipeline.py` now asserts
the ready-only flag and token as well as the original query/title fields.
Real models, Chroma stores, corpora, subprocess probes and browsers are excluded.

## 2026-11-05 inbox completion evidence

`test_inbox_completion_evidence.py` adds 13 actual-definition controls for
timeout, empty-state read failure, ambiguous filtered-empty text with a generic
empty node, transient evidence, missing-thread races, clear-feedback suppression,
remaining threads, confirmed empty views and useful processed-comment positives.
The DOM and clock are synthetic; telemetry uses a private test directory.
Seven assertion failures reproduced the initial defect before repair, with four
useful controls already passing. Independent actual-JavaScript review found
newline/repeated-space bypasses in the exact-text veto; two additional controls
failed before whitespace normalization. All 13 then passed with the unchanged 24
quality-stop cases under the existing offline owner's unchanged EffectGuard
and explicit credential-free environment, with zero errors/skips/denials.
The Python DOM answers remain fixtures; the independent actual-JavaScript probe
has its own evidence and must not be inferred from these Python case results.
This does not qualify live global inbox emptiness or add DOM selectors.

## 2026-11-01 quality-stop selection

`test_reply_quality_safety.py` has 24 bounded cases through complete production
definitions and explicit fixture collaborators. It covers current-session halt
on rejected/invalid output, non-quality skip distinctions, receipt reset, useful
approved answers, actual typing-to-Submit late STOP, all four early switches,
synthetic environment key/message separation and provider diagnostic non-echo.
18 cases failed before repair; all 24 pass afterward, without skips. One initial
typing fixture returned no entered text; it was corrected before the qualified
pre-fix replay so the no-STOP positive reaches Submit and late STOP exposes the
actual missing guard.

The existing closed `.github/scripts/youtube_repair_offline.py --suite quality`
owns the fixed 24-case inventory. It clears inherited environment, denies real
network, environment-file access and application effects, permits only the
existing private CPython event-loop socket pair, and uploads sanitized XML only.
Run it in a fresh private `RUNNER_TEMP` outside Git using the qualified Python.
The existing 157 + 12-subtest and 15-stdlib selections remain separate unchanged
regressions. No fixture judgment proves the active model's semantic accuracy.

## 2026-10-29 repair selectors

The follow-up private-livechat fallback selection is 88 semantic + 16 submission
history cases (104 total, plus 12 subtests), with the original context 53 retained
as a separate selector. Semantic tests also execute both real MessageProcessor
call sites, busy-lock behavior, comment serialization, async heartbeat/timeout,
late result discard and cancellation before subsequent provider stages. Provider
calls are fixtures. Timeout cannot kill a running thread or HTTP call; it bounds
the caller's wait and invalidates later work. The existing separate operator
queue/lifecycle/control-plane selection passes 116 and stdlib inspection 15.

With the environment isolation below, also run `test_reply_semantic_assessment.py`
and `test_reply_submission_history.py` explicitly with pytest. They cover actual
assessment/write/review ordering, supplied-fact snapshots, format/model-role
rejection, private enqueue/activation, post-delay livechat guards, real SQLite
restart/concurrent claims and exact production JavaScript against a synthetic DOM.
The existing `test_chat_manifest_inspection.py` stdlib selector remains separate.
Model judgments and DOMs are fixtures; these do not certify live inference or
current YouTube selectors. CI binds the new case inventory separately from the
original 53-case context selection.

This directory mixes local regression tests, stateful classification checks, and
live YouTube/model integration demos. A `test_*.py` filename does not establish an
offline boundary. Select an explicitly reviewed file; do not use a blanket
`pytest tests/` run as offline validation.

[TestModLog.md](TestModLog.md) inventories all eight pre-existing test files and
the PR #1759 reader tests, including effects and incomplete mock boundaries.
The missing inventory was recovered during review on 2026-10-22, after reader
test authoring and execution.

## Bounded shared-context reader tests

Run from the repository root with the existing qualified Python environment:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHON_DOTENV_DISABLED = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -o addopts= modules/communication/video_comments/tests/test_commenting_control_plane.py -q --tb=short
```

This file uses temporary shared/legacy state and a controlled clock. It exercises
the actual queue resolver and reader, schema/type/expiry boundaries, shared
precedence, legacy fallback, and local edits during an active shared context
followed by expiry or clearing. The relative-path case supplies a temporary
checkout root; it does not assume the checkout and temporary directory share a
Windows drive.

Measured result: **53 passed, zero failures/errors/skips** under Windows CPython
3.12.2. Six persistence regressions failed before the legacy-only mutation
repair and passed afterward. This is local fixture validation, not live delivery,
model inference, native-worker, or OS sandbox evidence. Exact history and receipt
locations are in the TestModLog.

## Other test surfaces

- `test_classifier_pipeline.py` writes through the real profile store without a
  temporary database fixture.
- `test_llm_integration.py` and `test_ytr1_runtime_hardening.py` mock selected
  collaborators. Their constructors/imports and environment-dependent paths need
  separate qualification before calling a whole-file run offline.
- `test_like_single_comment.py`, `test_move2japan_access.py`,
  `test_poc_dialogue.py`, `test_post_comment.py`, and `test_reply_to_comment.py`
  authenticate or operate against YouTube. Some publish comments/replies or start
  ongoing monitoring. They are outside the bounded reader invocation.

Those eight files were inventoried from source, not executed in this reader
slice. Review their boundaries and the authorized operational scope before
running them. The inventory grants no new execution authority.

## Coverage and maintenance

No line, function, or branch coverage measurement was produced for this slice.
The WSP 13 target remains at least 90%; no aggregate suite pass or coverage claim
is made here.

Before adding or expanding tests, read the TestModLog, this README, and the
nearest existing tests. Extend the existing contract when possible and update
the inventory/history in the same slice (WSP 22 and WSP 97 section 1.2B).

## PR1478 context pipeline reconciliation

Run only this separately reviewed selector with Node available:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHON_DOTENV_DISABLED = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -B -m pytest --import-mode=importlib -p pytest_asyncio.plugin -p no:cacheprovider -o addopts= modules/communication/video_comments/tests/test_reply_context_pipeline.py -q --tb=short
```

**53 passed, zero failures/errors/skips** locally with Python 3.12.2 and
Node 24.11.1. The private loader compiles complete production definitions and
injects controlled collaborators; package import and constructor lifecycle are
excluded. Actual extraction JavaScript executes against synthetic Node rows.
The preserved original seven assertions are extended with timeout, overlapping
generations, stale/discarded attribution, malformed labels, no-post decisions,
full-prompt fallback, explicit Grok opt-in, helper adapters, missing metadata and
conflicting/duplicate video IDs. Existing command/context selectors separately
pass 116 cases; overlapping counts are not a coverage percentage.

The existing Windows/Ubuntu CI job selects this file, pins Node 24.22.1, uploads
JUnit and requires the reviewed 53-case identity with no skips. Hosted results
must be observed separately. The canonical registry still quarantines this file
from broad automatic collection (`module_scope_local_function_invocation`,
process capability); this explicit selector does not waive that classification.

No real models, browser, account, profile database or posting were used. Fixture
boundaries are not an OS sandbox. A timeout does not kill an active provider
thread; later callers can remain blocked behind it. Full application startup,
live Studio selector behavior and native RSI remain separately unqualified.
The original PR's 23-pass blanket command is historical, not an approved run.
