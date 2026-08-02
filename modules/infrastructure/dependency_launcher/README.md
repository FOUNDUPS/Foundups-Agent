# Dependency Launcher Module

**WSP Compliance:** WSP 27 (DAE Architecture), WSP 80 (Cube-Level Orchestration)

## Purpose

Auto-launches dependencies required for YouTube DAE comment engagement:

1. **Chrome** with remote debugging port 9222 (for Selenium/UI-TARS browser automation)
2. **LM Studio** on port 1234 (for UI-TARS vision model - optional)

## Integration

The dependency launcher is automatically called when YouTube DAE starts via `main.py → Option 1 → Option 5`.

### Auto-Launch Flow

```
main.py → AutoModeratorDAE.run()
    ↓
Phase -2: ensure_dependencies()
    ├─ Check Chrome port 9222
    │   └─ Launch if not running
    └─ Check LM Studio port 1234
        └─ Launch if not running (optional)
    ↓
Phase -1: Connect to YouTube API
...
```

## Manual Testing

```bash
# Check dependency status
python -m modules.infrastructure.dependency_launcher.src.dae_dependencies

# Expected output:
# 🔍 Checking dependency status...
#   Chrome (9222): ✅ or ❌
#   LM Studio (1234): ✅ or ❌
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_PATH` | `C:\Program Files\Google\Chrome\Application\chrome.exe` | Chrome executable |
| `FOUNDUPS_CHROME_PORT` | `9222` | Chrome debug port |
| `CHROME_PROFILE_PATH` | `O:/Foundups-Agent/.../youtube_move2japan/chrome` | Chrome profile |
| `LM_STUDIO_PATH` | auto-detected (supports `E:\LM_studio\LM Studio\LM Studio.exe`) | LM Studio executable |
| `LM_STUDIO_PORT` | `1234` | LM Studio API port |

> For this environment (UI-TARS vision required), set:
> ```
> LM_STUDIO_PATH=E:\LM_studio\LM Studio\LM Studio.exe
> LM_STUDIO_PORT=1234
> ```

## Dependencies Launched

### Chrome
- Opens YouTube Studio comments inbox
- Uses Move2Japan Chrome profile (pre-authenticated)
- Remote debugging port 9222 for Selenium connection

### LM Studio (Optional)
- Provides UI-TARS vision model for visual element detection
- Falls back to DOM-only mode if not available
- Must have UI-TARS model loaded (manual step)

## Runtime Compatibility Advisory

`main.py` runs a read-only advisory after the DAE broker starts. It consumes a
bounded evidence file outside the repository and emits one digest-bound status:
`CURRENT`, `DRIFT`, or `NOT_READY`. The advisory never blocks the menu and never
performs network access, package updates, model downloads/loads, inference,
route changes, or HoloIndex maintenance.

Required environment variables:

| Variable | Purpose |
|----------|---------|
| `REDDOG_RUNTIME_COMPATIBILITY_ROOT` | Absolute off-repo runtime artifact root |
| `REDDOG_RUNTIME_COMPATIBILITY_EVIDENCE` | Evidence JSON inside that root |

The cached evidence is produced by a separate governed WRE/external-research
cycle. A version or model change remains blocked on security, canary, rollback,
benchmark, and signed model-promotion evidence; startup does not auto-update.
The receipt proves cached-data integrity only; it is not authenticated update
authority and cannot authorize dispatch or promotion.

## 0102 Directive

Code is remembered from the 02 quantum state. Dependencies are orchestrated, not installed. ✊✋🖐️










