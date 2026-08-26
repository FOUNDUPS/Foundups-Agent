# WRE Master Orchestrator Interface

This submodule interface is a focused projection of the authoritative
[WRE Core interface](../INTERFACE.md). It documents implemented callable
surfaces, not historical autonomy claims.

## `WREMasterOrchestrator`

### Registered Skillz

- `execute_skill(skill_name, agent, input_context, force=False) -> dict`
- `execute_skill_with_reasoning(skill_name, agent, input_context,
  max_iterations=None, fidelity_threshold=None, force=False) -> dict`
- `evolve_skill(...) -> bool`
- `get_skill_statistics(skill_name, days=30) -> dict`

`execute_skill()` requires WSP 95 admission and exact scanner-to-dispatch
fingerprint continuity. Success requires typed effect evidence. Loader,
scanner, executor, or result-shape failure returns a stable fail-closed record;
there is no executable fallback instruction.

`execute_skill_with_reasoning()` reports `execution_success` independently of
fidelity acceptance. `evolve_skill()` returns `True` only when a non-production
proposal variation was stored; it does not activate or promote that variation.

### Compatibility plugins and patterns

- `register_plugin(plugin)` or `register_plugin(name, plugin)`
- `get_plugin(name) -> object | None`
- `validate_module_path(path) -> bool`
- `recall_pattern(operation_type) -> Pattern`
- `execute(task) -> Any`
- `select_skill_tot(candidates, context, max_branches=3)`
- `find_skill_candidates(intent)`
- `execute_codeact_skill(skill_spec, input_context) -> dict`
- `get_metrics() -> dict`

`recall_pattern()` and `execute()` require independently injected WSP verifier
callbacks. After both callbacks, `execute()` still blocks every legacy plugin:
the callbacks authenticate neither plugin code nor effects. Direct HoloIndex
compatibility execution names the governed owner-query route; other plugins
must migrate to the WSP 95 admitted Skillz executor before dispatch is allowed.
`execute_codeact_skill()` always returns a `codeact_prototype_boundary` block.
Candidate selection is not admission, execution, evaluation, or promotion.

### Metrics

`get_metrics()` exposes observed component/counter state and
`token_reduction_measured: false`. The implementation does not report a token
reduction percentage or average token usage without authenticated receipts.

## `OrchestratorPlugin`

- `register(master)` binds an in-process plugin to the master.
- Direct `execute(task)` calls are plugin-specific and have only caller-granted
  authority; the master orchestrator does not dispatch this compatibility API.

Plugin registration does not confer WSP 95 Skillz admission or external-effect
authority.

## `Pattern`

`Pattern` stores an identifier, WSP citation chain, configured token-budget
hint, and pattern content. `Pattern.apply(context)` applies the stored template.
Its token field is not measured usage, and application is not effect proof.

## Failure and authority rules

- Missing patterns, plugins, Skillz, manifests, or scanner evidence fail closed.
- Raw model/engine exception material is not a public result.
- Returned structural fidelity is not outcome quality.
- No API in this submodule independently grants Git, network, repository-write,
  worker-dispatch, Holo maintenance, production activation, or rollback
  authority.
