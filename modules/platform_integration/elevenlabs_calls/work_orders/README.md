# Japanese call agent work orders

Eight authored M2M assignments for the remaining build. **None is dispatched or
completed by this pack.** The repo and prototype already exist in
[draft PR #1674](https://github.com/FOUNDUPS/Foundups-Agent/pull/1674).

| Order | Assignment | Depends on | Initial state |
|---|---|---|---|
| [JP-CALL-01](01_baseline.json) | baseline | — | ready |
| [JP-CALL-02](02_provider_setup.json) | provider setup | 01 | blocked_credentials |
| [JP-CALL-03](03_live_acceptance.json) | live acceptance | 02 | blocked_provider_and_test_targets |
| [JP-CALL-04](04_request_preparation.json) | request preparation | 03 | waiting_dependencies |
| [JP-CALL-05](05_runtime_binding.json) | runtime binding | 04 | waiting_dependencies |
| [JP-CALL-06](06_end_to_end.json) | end to end | 05 | waiting_dependencies |
| [JP-CALL-07](07_sound_poc.json) | sound poc | 03 | waiting_dependencies |
| [JP-CALL-08](08_closeout.json) | closeout | 06 | waiting_dependencies |

The shortest working CLI prototype closes at **03**. The full spoken assistant
workflow closes at **08** after **06** passes. **07** is the subsequent sound POC,
not an MVP requirement. Run 04 and 07 independently only with isolated file
ownership/worktrees and serialized provider experiments; shared docs belong to
the coordinator. All other dependency edges are mandatory.

## Coordinator starter

```text
Read work_orders/PROMETHEUS.md and work_orders/CONTRACT.md in the
elevenlabs_calls module. Use the eight JSON files as the dispatch inventory.
Bind the current repository revision and actual authority. Start with JP-CALL-01.
Dispatch only dependency-ready work. Preserve blockers until evidenced resolved.
Assign exact owners and require RESULT_TEMPLATE.json evidence from every job.
Review before accepting completion; issue a narrow repair order on failure.
Update the draft PR and roadmap with observed results, not planned outcomes.
```

## Worker starter

```text
Your task frames are work_orders/CONTRACT.md and the assigned numbered JSON.
Execute only that assignment under its ROLE, S, I and effect boundary.
Apply WSP 97 using current repository evidence. Return a redacted result in
work_orders/results/<T>.json using RESULT_TEMPLATE.json. If blocked, finish
useful permitted preparation and state the exact missing prerequisite.
```

Paths above are relative to this module. [Prometheus brief](PROMETHEUS.md) is
principal-readable; [contract](CONTRACT.md) plus a numbered JSON is the worker
handoff. The [result template](RESULT_TEMPLATE.json) is a local evidence format,
not a signed WRE receipt. No automatic queue loader is installed.

Do not reopen completed adapter work by default. Historical tests and limitations
are in [TestModLog](../tests/TestModLog.md). Jobs 02 and 03 need actual provider
configuration and controlled call targets; currently neither is available.
