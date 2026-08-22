# shared_utilities Test Suite

Offline pytest coverage for shared model, runtime-artifact, registry, policy,
validation, and environment utilities. Network/model/process effects must be
mocked in unit tests.

## LM Studio lifecycle coverage

`test_lm_studio_model_lifecycle.py` proves native installed-versus-resident
truth, exact borrowed and managed leases, cross-process operation ownership,
node/port alias serialization, occupied-capacity and maximum-context rejection,
load/unload verification, timeout observation without blind retry, durable
restart recovery versus ambiguous-load quarantine, cancellation cleanup,
authentication redaction, loopback confinement, and content-addressed receipt
integrity. Both governed native openers prove environment proxy inheritance is
disabled. `test_runtime_artifact_safety.py` includes a real spawned-process
lock-timeout contract whose target lives in the import-stable
`runtime_lock_test_support.py` module so the Windows spawn proof also works
under the documented pytest importlib mode.

`test_local_llm_backends.py` proves backend selection and that initialization
requires one exact native resident instance. Native and legacy OpenAI-compatible
calls revalidate that exact instance before and after use; governed lifecycle
claims require the native response identity/JIT evidence contract.

`test_lm_studio_dependency_boundary.py` proves resolver and required-backend
paths never start LM Studio or invoke subprocess launch machinery.

## Canonical LM Studio lifecycle release gate

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$reddogTestTemp = Join-Path ([IO.Path]::GetTempPath()) `
  ('reddog-lifecycle-' + [guid]::NewGuid().ToString('N'))
python -m pytest -q --import-mode=importlib --basetemp $reddogTestTemp `
  modules/infrastructure/shared_utilities/tests/test_lm_studio_model_lifecycle.py `
  modules/infrastructure/shared_utilities/tests/test_local_llm_backends.py `
  modules/infrastructure/shared_utilities/tests/test_lm_studio_dependency_boundary.py `
  modules/infrastructure/shared_utilities/tests/test_runtime_artifact_safety.py `
  modules/ai_intelligence/ai_gateway/tests/test_model_topology_proposal_lm_studio.py `
  modules/ai_intelligence/ai_gateway/tests/test_model_topology_proposal_admission.py `
  modules/ai_intelligence/ai_gateway/tests/test_model_topology_proposer_authenticated_provenance.py
```

The unique outside-repository base directory prevents unrelated concurrent
pytest runs from contending for pytest's shared Windows temp-root numbering.
Current result: `121 passed, 1 skipped`.

The legacy aggregate command over this entire directory is not a truthful
release gate today: the inherited
`navigation/test_navigation_schema.py` contains an internal U+FEFF and cannot
be collected; removing that character exposes separate NAVIGATION registry
drift. That independent navigation transaction is not silently ignored or
folded into the LM Studio lifecycle layer.

Record material test changes in `TestModLog.md`. See WSP 13, WSP 22, WSP 34,
WSP 50, WSP 62, WSP 77, WSP 91, and WSP 97.
