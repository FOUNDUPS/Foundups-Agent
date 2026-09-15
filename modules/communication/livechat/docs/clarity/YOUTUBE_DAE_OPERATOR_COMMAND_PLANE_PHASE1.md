# Assumption Audit: YouTube DAE Operator Command Plane Phase 1

## 1. Problem Statement

The live-stream operator needs a low-friction way for a realtime conversation agent to request a bounded action while the YouTube DAE is running. This is not authorization for arbitrary LLM, shell, browser, moderation, or code-changing execution.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|
| A1 | The heartbeat is continuously scheduled while the DAE runs. | `youtube_dae_heartbeat.py` | High |
| A2 | Existing automation gates are the canonical send/stop policy. | `automation_gates.py` | High |
| A3 | The local `memory/` directory is suitable for ephemeral control data. | root `.gitignore` | High |

## Command Contract

The realtime supervising agent writes this local file; the running heartbeat
checks it no more often than once per minute:

```json
{
  "version": 1,
  "commands": [
    {
      "id": "voice-20260915-001",
      "action": "announce",
      "payload": {"message": "We are testing the live control plane."}
    }
  ]
}
```

Default inbox: `memory/012_manifest.json`.
Default acknowledgement ledger:
`memory/012_manifest_acknowledgements.json`. Command IDs are immutable and
must be unique. A completed ID is never dispatched again, including after a
DAE restart. `status` returns the current automation gates; `announce` sends a
maximum 500-character chat message only when those gates allow it.
The watcher starts independently of the optional AI Overseer and leaves an
announcement pending until LiveChat is connected.

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---:|---:|---|
| F1 | A malformed JSON file crashes the DAE. | Medium | High | Treat it as an empty queue and log a warning. |
| F2 | A command repeats after restart. | Medium | Medium | Atomically persist command-id acknowledgements. |
| F3 | A command bypasses YouTube safety gates. | Low | High | Dispatch only allowlisted actions after gate checks. |
| F4 | A JSON file becomes arbitrary agent execution. | Medium | Critical | No prompt, shell, code, browser, or model-routing action exists in Phase 1. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Direct OpenRouter/LLM execution from JSON | It blurs operator intent, model selection, and external side effects. |
| A network API | It adds credentials and a public attack surface before the local contract is proven. |
| Polling the main chat loop | The heartbeat already has observability and a bounded background cadence. |

## 5. Decision Record

- Decision: PROCEED with a local, allowlisted inbox and acknowledgement ledger.
- Owner: 0102 / worker / external_principal.
- Timestamp: 2026-09-15.
- Follow-on: New actions require separate tests, gate policy, and a renewed assumption audit.
