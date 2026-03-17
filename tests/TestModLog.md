# TestModLog - shared tests

## 2026-03-18: Main bootstrap resident OpenClaw registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `openclaw` as a broker-managed launch spec.
  - Confirms resident OpenClaw autostart requests the broker path instead of remaining menu-only.

---

## 2026-03-08: Markdown sanitizer coverage

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q tests/test_markdown_sanitizer.py`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Notes:
  - Validates ASCII-safe replacements for arrows, dashes, star, and check glyphs.
  - Confirms recursive sanitization across nested Python containers.
