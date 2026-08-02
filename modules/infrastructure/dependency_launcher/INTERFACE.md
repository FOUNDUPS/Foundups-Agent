# Dependency Launcher Module - INTERFACE

**Module:** infrastructure/dependency_launcher
**WSP Reference:** WSP 11 (Interface Documentation)

---

## Public API

### `ensure_dependencies(require_lm_studio: bool = True) -> Dict[str, bool]`

Ensure all dependencies are running before DAE starts.

**Parameters:**
- `require_lm_studio`: Whether LM Studio is required (default: True)

**Returns:**
```python
{
    'chrome': True,      # Chrome on port 9222
    'lm_studio': True    # LM Studio on port 1234
}
```

**Example:**
```python
from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies

# In async context
dep_status = await ensure_dependencies(require_lm_studio=False)
if not dep_status['chrome']:
    logger.warning("Chrome not available")
```

---

### `launch_chrome() -> Tuple[bool, str]`

Launch Chrome with remote debugging port.

**Returns:**
- `(True, "Chrome started on port 9222")` on success
- `(False, "error message")` on failure

**Behavior:**
- Uses Chrome profile at `CHROME_PROFILE_PATH`
- Opens YouTube Studio comments inbox
- Creates detached process (non-blocking)
- Waits up to 30 seconds for port to respond

---

### `launch_lm_studio() -> Tuple[bool, str]`

Launch LM Studio for UI-TARS vision.

**Returns:**
- `(True, "LM Studio started on port 1234")` on success
- `(False, "error message")` on failure

**Behavior:**
- Creates detached process (non-blocking)
- Waits up to 120 seconds for API to respond
- Note: Model must be loaded manually in LM Studio

---

### `connect_chrome_with_retry(max_retries=3, retry_delay=2.0, relaunch_on_fail=True) -> Optional[WebDriver]`

Attach Selenium to the debug-port Chrome with retries and DevTools verification.

**Non-destructive recovery (Phase 1):** if DevTools is UP but exposes no
discoverable page target (Selenium "unable to discover open pages"), this opens a
normal tab via `open_devtools_page()` and retries the attach. It does NOT taskkill
the operator's prepared Chrome on this path; if a tab cannot be opened it logs a
clear actionable error and returns `None`. The genuinely-DevTools-DOWN path still
relaunches (follow-up: BROWSER_ATTACH_RECOVERY_DEVTOOLS_DOWN_PHASE2).

### `connect_edge_with_retry(max_retries=3, retry_delay=2.0, relaunch_on_fail=True) -> Optional[WebDriver]`

Same as `connect_chrome_with_retry` for Edge (port 9223), including the
non-destructive no-page recovery (no `msedge.exe` taskkill on the no-page path).

### `open_devtools_page(port: int, url: str = "about:blank", timeout: float = 3.0) -> bool`

Open a new normal page/tab via the DevTools HTTP endpoint (`PUT /json/new?<url>`
with `GET` fallback). Used to recover the "unable to discover open pages" condition
without killing the browser. Returns `True` if DevTools reported a new target,
`False` otherwise. Never raises, never kills any process.

---

### `is_chrome_running() -> bool`

Check if Chrome debug port is responding.

---

### `is_lm_studio_running() -> bool`

Check if LM Studio API is responding.

---

### `get_dependency_status() -> Dict[str, bool]`

Get current status without launching.

**Returns:**
```python
{
    'chrome': True/False,
    'lm_studio': True/False
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_PATH` | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Chrome executable path |
| `FOUNDUPS_CHROME_PORT` | `9222` | Chrome remote debugging port |
| `CHROME_PROFILE_PATH` | `O:/Foundups-Agent/.../youtube_move2japan/chrome` | Chrome user data directory |
| `LM_STUDIO_PATH` | `C:\Users\user\AppData\Local\Programs\LM Studio\LM Studio.exe` | LM Studio executable |
| `LM_STUDIO_PORT` | `1234` | LM Studio API port |

---

## Integration Points

### AutoModeratorDAE (Phase -2)
```python
# In auto_moderator_dae.py run() method
from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
dep_status = await ensure_dependencies(require_lm_studio=False)
```

### CommunityMonitor (Subprocess)
The comment engagement subprocess connects to Chrome on port 9222.

---

## Error Handling

| Error | Behavior |
|-------|----------|
| Chrome not found | Returns False, logs warning |
| Chrome port timeout | Returns False, logs warning |
| LM Studio not found | Returns False, logs warning (optional) |
| LM Studio API timeout | Returns False, suggests manual model load |

---

### `run_runtime_compatibility_advisory(repo_root, *, environment=None)`

Reads a bounded, off-repo `reddog_runtime_compatibility_evidence.v1` artifact
and returns a `RuntimeCompatibilityReceipt`. Required components are OpenClaw,
Hermes, the general and coding Qwen model bindings, and the inference backend.

The Phase 1 result is integrity-only and therefore always remains
`NOT_READY` until a later signed source-admission gate authenticates every
source. Valid component comparisons are still exposed without overclaiming:

- `OBSERVED_MATCH`: the integrity-checked installed and expected references match.
- `OBSERVED_DRIFT`: the integrity-checked references differ.
- component `NOT_READY`: evidence is absent, expired, malformed, or incomplete.

An integrity-only envelope includes the stable overall reason
`evidence_authentication_not_verified`. Recomputing every self-hash cannot
produce an authenticated `CURRENT` result.

The function catches all input failures, prints one safe summary line, and
never blocks startup. It makes no network call and performs no runtime mutation,
model load, route change, package install, or HoloIndex action.
The self-hash is an integrity check, not identity or update authorization.

### `compose_runtime_compatibility_evidence(supply, *, upstream_releases, now=None)`

Rehydrates exact installed-observation and promoted-expectation source
receipts, adds stable OpenClaw/Hermes official-release evidence, and returns the
`reddog_runtime_compatibility_evidence.v1` mapping consumed by startup.

The source sets are exact:

- Installed observations: OpenClaw, Hermes, Qwen general, Qwen code, backend.
- Official upstream expectations: OpenClaw and Hermes only.
- Promoted runtime expectations: Qwen general, Qwen code, backend only.

Receipt self-hashes are recomputed at use time. They establish structural
integrity, not signer identity, so composed envelopes are explicitly marked
`INTEGRITY_ONLY`. A future authenticated source-admission owner remains
required before `CURRENT`, update action, or promotion authority is possible.

### `publish_runtime_compatibility_evidence(...) -> Path`

Validates the composed evidence and uses the canonical runtime-artifact safety
layer for descriptor-verified, locked replacement beneath an off-repo root.
Invalid evidence cannot overwrite the previous cache.
The supply and output paths must be distinct.

### `scripts/refresh_openclaw_ecosystem_watchlist.py`

When the compatibility root, supply, and output are all configured, the
existing WRE watchlist refresh fetches the two allowlisted GitHub API release
documents and publishes the cache. Partial configuration or any retrieval or
validation failure returns nonzero. It never installs or invokes a component.

## 0102 Directive

Dependencies are orchestrated autonomously. The system self-heals. ✊✋🖐️












