# FoundUps Selenium tests

`test_wre_visual_runner.py` exercises the actual dependency-free runner with
synthetic driver, bridge and memory collaborators: unavailable/error/disabled
vision, explicit DOM assertions, observation retries, no repeated action,
provenance persistence, screenshots, invalid counts and active-loop refusal.
It does not open browsers, call a model or establish visual quality. Windows
asyncio creates an internal loopback socket pair; use an environment that permits
that native runtime mechanism rather than replacing the async path with a pass.

Run the focused contracts from the repository root with the existing vetted
Python environment, plugin autoload/dotenv disabled and bytecode disabled:

```text
python -B -m pytest -q --tb=short --noconftest --import-mode=importlib -p no:cacheprovider modules/infrastructure/foundups_selenium/tests/test_wre_visual_runner.py
```

Use a bounded supervisor/watchdog. Repository pytest configuration may require
the installed asyncio plugin; a clean temporary config also works for this
synchronous test module. The Shorts `test_layer3_schedule.py` includes three offline
caller controls; its manual `--wre-tars` entry remains a live browser harness and
must not be launched as offline validation.

Existing inventory (see TestModLog for history and limits):

- `test_foundups_driver.py`: mocked driver initialization, Gemini/telemetry,
  platform typing/posting helpers and snapshot hashes.
- `test_telemetry_store.py`: SQLite event persistence and concurrency.
- `test_human_behavior.py`, `test_undetected_browser.py`: mocked browser helpers.
- `test_shadow_dom_finder.py`: synthetic shadow/flat lookup and chains.
- `test_youtube_verification.py`: human-only verification hold and attachment
  contracts, including separately bounded process/Node witnesses.
- `test_edge_comment_processing.py`, `test_edge_youtube_studio.py`: manual real
  browser validation harnesses; excluded from offline selection.
