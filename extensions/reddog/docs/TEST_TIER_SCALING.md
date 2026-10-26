# RedDog Test Tier Scaling

The release owner keeps the exact 18-shard shared-VM body and its seven existing
focused tail contracts: five governed-Git tails and two bridge/package gates.
It runs them as four process-isolated groups with a
fixed worker cap of four, a 400-second child timeout, the unchanged 420-second
release ceiling, and 2 MiB output caps. Plan-order logs, per-group durations,
the slowest group, and final exit status are emitted without environment values.

The plan rejects omitted, duplicated, reordered, or stale tail members before
execution; no assertion, shard digest, or negative diagnostic is removed. The
canonical command always enters the full parent promotion path; ambient
environment cannot select a group. A dedicated internal worker requires an
exact parent-generated nonce binding.

The parent enforces the 420-second wall deadline from command start. Child
timeouts are recorded before bounded graceful/forced process-tree termination.
Timeout, termination failure, or unconfirmed termination remains FAIL even if a
child later exits zero.

On Windows, a `taskkill.exe` attempt is confirmed only by a zero exit. Its
absolute `SystemRoot` path is launched with `shell: false`; asynchronous launch
error, nonzero exit, or the bounded 750-millisecond taskkill timeout records
termination failure. Both graceful and forced outcomes feed the final receipt,
and a late child-process error remains handled without reopening settlement.

Historical acceptance evidence:

- First complete aligned promotion: 295.928 seconds, leaving 124.072 seconds
  (29.5%) beneath the ceiling.
- Repeat aligned promotion: 266.709 seconds. Acceptance used the slower receipt.
- Hostile ambient-selector repair run: all four groups in 279.723 seconds with
  every timeout field false.
- Loop-3 hostile-selector run: all four groups in 274.537 seconds (owner
  273.762 seconds) with every timeout and termination field false.

These are historical verification receipts. Current promotion requires a fresh
exact-candidate release receipt; this document grants no execution authority.
