---
name: antifafm_dj
description: DJ automation and music playlist management for antifaFM
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen]
primary_agent: qwen
intent_type: ORCHESTRATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals: []
trigger:
  event: stream_active
---
# antifaFM DJ Skill

## Purpose

Autonomous audio health monitoring for antifaFM stream. Ensures the radio stream stays playing via OBS Media Source.

## Audio Source

**Stream URL**: `https://a12.asurahosting.com/listen/antifafm/radio.mp3`
**OBS Source**: `antifaFM Radio` (Media Source)

## Capabilities

### 1. Audio Health Check
- Verify `antifaFM Radio` media source state
- Expected: `OBS_MEDIA_STATE_PLAYING`
- Alert if: `OBS_MEDIA_STATE_ENDED`, `OBS_MEDIA_STATE_STOPPED`, `OBS_MEDIA_STATE_ERROR`

### 2. Auto-Restart
- If audio stopped, trigger `OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART`
- Ensure source is unmuted
- Log restart events to telemetry

### 3. Stream Reachability
- Verify stream URL responds (HEAD request)
- Alert if stream server unreachable

### 4. Volume Monitor
- Check volume level is not 0 dB (muted equivalent)
- Warn if volume too low (< -20 dB)

## Commands

```bash
# Check audio health
python executor.py --check

# Restart audio source
python executor.py --restart

# Run as daemon (check every 30 seconds)
python executor.py --daemon

# Show status
python executor.py --status
```

## WRE Connection

```yaml
trigger:
  type: cadence
  interval_minutes: 1
  source: wre_master_orchestrator
  gate: ANTIFAFM_DJ_ENABLED=1

events_emitted:
  - audio_health_ok: {source, state, volume_db}
  - audio_restarted: {source, previous_state, reason}
  - audio_error: {source, state, error}
  - stream_unreachable: {url, error}

integration_points:
  - boot_layer_rotator: Called at rotation daemon startup
  - launch.py: Can be triggered during OBS orchestration
```

## CLI Menu Integration

OpenClaw Menu → antifaFM DJ:
```
1. Check Audio Health
2. Restart Audio Source
3. Start Health Daemon
4. Show Stream Status
5. Test Stream URL
0. Back
```

## WSP Compliance

- WSP 27: Universal DAE Architecture (sensor: OBS state, actuator: media restart)
- WSP 91: Observability (audio health telemetry)
- WSP 103: CLI Interface Standard
