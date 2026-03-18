# TestModLog - shared tests

## 2026-03-18: Main bootstrap resident OpenClaw registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `openclaw` as a broker-managed launch spec.
  - Confirms resident OpenClaw autostart requests the broker path instead of remaining menu-only.

## 2026-03-18: Main bootstrap PQN simulation registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `pqn_simulation` as a launchable broker spec.
  - Confirms the simulation lane is bootstrapped alongside the other PQN runtime entrypoints.

## 2026-03-18: Main bootstrap OpenClaw supervisor registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `openclaw_supervisor`.
  - Confirms supervisor autostart is routed through the broker-managed runtime surface.

## 2026-03-18: IronClaw startup readiness preflight

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_ironclaw_preflight.py tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Result: `7 passed`
- Notes:
  - Confirms startup skips IronClaw readiness when backend is `openclaw`.
  - Confirms startup blocks when IronClaw is the active backend and readiness fails without fallback.
  - Confirms startup warns but allows boot when local fallback policy is enabled.

## 2026-03-18: Main bootstrap HoloDAE stop-hook registration

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest tests/test_main_runtime_bootstrap.py -q`
- Status: PASS
- Notes:
  - Confirms `main.bootstrap_runtime_dae_launches()` registers `holodae` with a real `stop_callable`.

---

## 2026-03-08: Markdown sanitizer coverage

- Command: `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q tests/test_markdown_sanitizer.py`
- Status: PASS
- Result: `2 passed, 2 warnings`
- Notes:
  - Validates ASCII-safe replacements for arrows, dashes, star, and check glyphs.
  - Confirms recursive sanitization across nested Python containers.
