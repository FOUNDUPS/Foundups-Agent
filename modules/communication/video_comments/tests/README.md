# video_comments Tests

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
