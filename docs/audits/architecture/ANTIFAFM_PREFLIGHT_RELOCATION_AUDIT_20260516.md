# antifaFM Preflight Relocation Audit

**Audit ID**: ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516
**Date**: 2026-05-16
**Worker**: W10
**WSP Lock**: WSP_00, WSP_50, WSP_97, WSP_22
**Mode**: Audit/Spec Only -- NO IMPLEMENTATION

---

## Required Labels

- SPEC_ONLY
- NO_RUNTIME_MUTATION
- AUDIT_ONLY
- PREFLIGHT_RELOCATION_BOUNDARY

---

## 1. Executive Summary

This audit documents the root cause and target architecture for relocating antifaFM/OBS initialization away from `main.py` startup. The current `ANTIFAFM_AUTO_START` block causes side effects at main startup that should be deferred to explicit user action.

**Root Cause**: `ANTIFAFM_AUTO_START` environment variable check in `main.py` triggers OBS/streaming initialization at application startup.

**Target Behavior**: No antifaFM/OBS side effects at main startup. Initialization occurs only via explicit preflight in YouTube DAE menu.

---

## 2. Root Cause Analysis

### 2.1 Current Behavior

Location: `main.py` (startup block)

```python
# PROBLEMATIC: Runs at import/startup time
if os.environ.get("ANTIFAFM_AUTO_START") == "1":
    # Side effects: OBS connection, FFmpeg process, stream health monitoring
    ...
```

**Issues**:
1. OBS WebSocket connection attempted at startup
2. FFmpeg processes may spawn before user intent confirmed
3. Stream health monitoring activates prematurely
4. Resource consumption before explicit user action
5. Error states if OBS not running

### 2.2 Affected Components

| Component | Current Location | Side Effect |
|-----------|------------------|-------------|
| OBS WebSocket | main.py startup | Connection attempt |
| FFmpegStreamer | main.py startup | Potential process spawn |
| StreamHealthMonitor | main.py startup | Monitoring loop |
| antifaFMBroadcaster | main.py startup | Full initialization |

---

## 3. Target Architecture

### 3.1 Relocation Target

**From**: `main.py` startup block
**To**: YouTube DAE menu preflight (option 1) and shared control path (option 10)

### 3.2 Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| Option 1 | `modules/platform_integration/video_comments/src/youtube_menu.py` | Preflight check before stream |
| Option 10 | `modules/platform_integration/video_comments/src/youtube_menu.py` | Shared antifaFM control |

### 3.3 Target Behavior

```
main.py startup:
  - NO antifaFM initialization
  - NO OBS connection
  - NO FFmpeg processes
  - NO stream health monitoring

YouTube DAE menu (option 1 - preflight):
  - Check OBS availability
  - Validate stream configuration
  - Report readiness status
  - NO automatic start

YouTube DAE menu (option 10 - shared control):
  - Initialize antifaFMBroadcaster on demand
  - Start OBS connection when user confirms
  - Launch FFmpeg when stream begins
  - Monitor health during active stream only
```

---

## 4. Implementation Boundary

### 4.1 Files to Modify

| File | Change |
|------|--------|
| `main.py` | Remove `ANTIFAFM_AUTO_START` block |
| `youtube_menu.py` | Add preflight check (option 1) |
| `youtube_menu.py` | Ensure option 10 handles full init |
| `antifafm_broadcaster.py` | Add lazy initialization support |

### 4.2 Files NOT to Modify

| File | Reason |
|------|--------|
| `ffmpeg_streamer.py` | No changes needed |
| `stream_health_monitor.py` | No changes needed |
| Consensus/ROC audit files | Different workstream |

---

## 5. Safety Constraints

### 5.1 WSP 97 Truth Boundaries

| Constraint | Status |
|------------|--------|
| No runtime mutation in this audit | ENFORCED |
| Spec only | ENFORCED |
| Implementation requires separate PR | ENFORCED |

### 5.2 Operational Safety

| Constraint | Status |
|------------|--------|
| No OBS side effects at startup | TARGET |
| No FFmpeg processes at startup | TARGET |
| Explicit user action required | TARGET |
| Graceful degradation if OBS unavailable | TARGET |

---

## 6. Approval Boundary

### 6.1 Role Definitions

| Actor | Role |
|-------|------|
| 012 | Provides feedback on implementation approach |
| 0102/W1 | Implements relocation per this spec |
| W10 | Manages branch hygiene, commits, PRs |

### 6.2 Approval Architecture

- **Approval authority**: Sovereign internal agent consensus (for autonomous changes)
- **This audit**: Requires 012 review before implementation proceeds
- **Implementation PR**: Standard CI gates

---

## 7. W1 Implementation Prompt

```text
ANTIFAFM_PREFLIGHT_RELOCATION_IMPL_PHASE1

You are W1 operating under WSP_00, WSP_50, WSP_97.

Branch: feat/antifafm-preflight-relocation

Reference: docs/audits/architecture/ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516.md

Task:
1. Remove `ANTIFAFM_AUTO_START` block from `main.py`
2. Add preflight check to `youtube_menu.py` option 1:
   - Check OBS WebSocket availability
   - Validate stream config exists
   - Report status (ready/not ready)
   - Do NOT auto-start
3. Ensure option 10 handles full antifaFMBroadcaster initialization
4. Add lazy init support to antifafm_broadcaster.py if needed
5. Update ModLog.md per WSP 22

Constraints:
- Do NOT touch consensus/ROC files
- Do NOT add new dependencies
- Maintain backwards compatibility with manual OBS launch
- Test with OBS both running and not running

Return:
- Files modified
- Commit hash
- Test results
- Blockers
```

---

## 8. Next Slice

**Slice ID**: `ANTIFAFM_PREFLIGHT_RELOCATION_IMPL_PHASE1`

**Purpose**: Implement the relocation per this specification.

**Dependencies**: This audit merged.

**Worker**: W1

---

## 9. WSP 97 Verdict

| Claim | Status |
|-------|--------|
| Audit is spec-only | VERIFIED |
| No runtime mutation | VERIFIED |
| Implementation boundary defined | VERIFIED |
| W1 prompt included | VERIFIED |
| Safety constraints documented | VERIFIED |

---

Worker-Lane: W10
Slice: ANTIFAFM_PREFLIGHT_RELOCATION_AUDIT_20260516
