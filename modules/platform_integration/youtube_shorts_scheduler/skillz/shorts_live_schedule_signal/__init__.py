"""shorts_live_schedule_signal SKILLz package.

Read-only LIVE signal from the YouTube Studio shorts list:
  1. Accurate "Has schedule" scheduled count (fixes the [CPS-AUDIT] false-0).
  2. Per-video VIEW count -> a low-viewed signal (012: "re-schedule low viewed shorts").

Agent-invoked only (WRE/daemon + --agent-command surface). NO scheduling mutation.
"""
