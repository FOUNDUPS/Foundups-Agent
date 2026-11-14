# PQN adapter interfaces

Implementation: [scripts/launch.py](scripts/launch.py). These are synchronous
adapters around the existing alignment owner; some use asyncio.run internally
and must not be treated as awaitable APIs inside an already-running event loop.

| Entry | Result and effects |
| --- | --- |
| run_pqn_dae() | Interactive menu; delegates architect, research, model and experimental diagnostic work. |
| run_pqn_architect_once() | Returns status, report_path and next_action; may execute the selected directive and writes a strategic report. |
| run_pqn_research_session(selected_agents=None, session_name="PQN_Research", save_results=True) | Returns status, session_id, agents_used, tasks_completed and results_path; executes the delegated research session and optionally saves results. |
| run_pqn_simulation_once(config=None) | Returns status, summary_path, run_count, probe_closer_to_target, validated_truth and archive_informed from the delegated theory/archive result. |

The broker adapters do not provide a uniform exception-to-error result contract;
delegate/import/IO errors can propagate. Returned interpretation flags describe
the delegate's result and are not independent scientific validation. The menu
uses an optional preflight decorator, with an identity fallback on ImportError;
presence of that decorator is not a universal enforced safety guarantee.

See [README.md](README.md) for owner and storage boundaries and
[tests/README.md](tests/README.md) for the existing mocked simulation test.
Source review documents implemented interfaces; live delegation is unvalidated.
