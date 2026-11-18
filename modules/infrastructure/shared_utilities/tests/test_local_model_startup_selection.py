"""Offline role selection and exact native initialization; no model/service use."""
import inspect
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from modules.infrastructure.shared_utilities import ai_engine_singletons as singletons
from modules.infrastructure.shared_utilities import local_llm_backends as backends
from modules.infrastructure.shared_utilities import local_llm_resolver as resolver
from modules.infrastructure.shared_utilities import local_model_selection as selection
from modules.infrastructure.shared_utilities.lm_studio_native_transport import (
    LMStudioAuthenticationError, LMStudioLoadedInstance, LMStudioModelState,
    LMStudioResidencyState,
)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    for name in ("LOCAL_MODEL_CODE_PATH", "LOCAL_MODEL_CODE_DIR", "LOCAL_MODEL_TRIAGE_PATH",
                 "LOCAL_MODEL_TRIAGE_DIR", "HOLO_QWEN_MODEL", "HOLO_GEMMA_MODEL",
                 "LOCAL_MODEL_CODE_NATIVE_KEY", "LOCAL_MODEL_TRIAGE_NATIVE_KEY",
                 "LM_STUDIO_NATIVE_MODEL_KEY", "LM_STUDIO_MODEL", "LOCAL_MODEL_GENERAL_PATH"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LOCAL_MODEL_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("LOCAL_MODEL_ENABLE_LEGACY_FALLBACK", "0")
    for name in ("_qwen_engine", "_gemma_engine"):
        monkeypatch.setattr(singletons, name, None)
    for name in ("_qwen_initialized", "_gemma_initialized"):
        monkeypatch.setattr(singletons, name, False)
    observed = SimpleNamespace(states={}, probes=[], sdk=[], files=[], offline=False,
                               auth=False, sdk_missing=False, file_ready=False)

    def native(key, **kwargs):
        observed.probes.append((key, kwargs))
        if observed.auth: raise LMStudioAuthenticationError("synthetic_auth_required")
        state = LMStudioResidencyState.SERVER_UNREACHABLE if observed.offline else observed.states.get(key, LMStudioResidencyState.NOT_INSTALLED)
        instances = (LMStudioLoadedInstance("instance-" + key, {}),) if state is LMStudioResidencyState.RESIDENT else ()
        return LMStudioModelState(key, state, instances, total_resident_instances=len(instances))

    def client(**kwargs):
        observed.sdk.append(kwargs)
        if observed.sdk_missing: raise ImportError("synthetic_sdk_unavailable")
        return SimpleNamespace()

    def file_initialize(self):
        observed.files.append(self.model_path)
        return observed.file_ready

    sdk = ModuleType("openai")
    sdk.OpenAI = client
    monkeypatch.setitem(sys.modules, "openai", sdk)
    monkeypatch.setattr(backends, "inspect_lm_studio_model", native)
    monkeypatch.setattr(backends.LlamaCppBackend, "initialize", file_initialize)
    return observed


def role_key(role):
    owner = getattr(selection, "resolve_role_native_key", None)
    assert callable(owner), "native role keys belong to the existing local_model_selection owner"
    return owner(role)


@pytest.mark.parametrize("role,expected", [("code", "qwen-coder-7b"), ("triage", "gemma-270m")])
def test_declared_role_defaults_are_preserved(runtime, role, expected):
    assert role_key(role) == expected


@pytest.mark.parametrize("role", ["code", "triage"])
def test_explicit_role_native_key_is_used_without_basename_inference(runtime, tmp_path, monkeypatch, role):
    path = tmp_path / "arbitrary-file-name.gguf"
    path.write_bytes(b"not-a-model")
    monkeypatch.setenv("LOCAL_MODEL_" + role.upper() + "_PATH", str(path))
    monkeypatch.setenv("LOCAL_MODEL_" + role.upper() + "_NATIVE_KEY", "operator-" + role)
    assert role_key(role) == "operator-" + role


@pytest.mark.parametrize("override", ["LOCAL_MODEL_CODE_PATH", "LOCAL_MODEL_CODE_DIR", "HOLO_QWEN_MODEL",
                                     "LOCAL_MODEL_TRIAGE_PATH", "LOCAL_MODEL_TRIAGE_DIR", "HOLO_GEMMA_MODEL"])
def test_custom_role_path_needs_explicit_native_key_instead_of_guessing(runtime, tmp_path, monkeypatch, override):
    monkeypatch.setenv(override, str(tmp_path / "opaque-local-model.gguf"))
    role = "code" if "CODE" in override or "QWEN" in override else "triage"
    assert role_key(role) is None


def test_general_native_key_never_retargets_code_or_triage(runtime, monkeypatch):
    monkeypatch.setenv("LM_STUDIO_NATIVE_MODEL_KEY", "gemma4-e2b")
    assert role_key("code") == "qwen-coder-7b"
    assert role_key("triage") == "gemma-270m"


@pytest.mark.parametrize("role,getter", [("code", "get_qwen_engine"), ("triage", "get_gemma_engine")])
def test_selected_native_resident_can_be_borrowed_with_missing_local_file_once(runtime, tmp_path, monkeypatch, role, getter):
    monkeypatch.setenv("LOCAL_MODEL_" + role.upper() + "_PATH", str(tmp_path / "missing.gguf"))
    monkeypatch.setenv("LOCAL_MODEL_" + role.upper() + "_NATIVE_KEY", "operator-" + role)
    runtime.states["operator-" + role] = LMStudioResidencyState.RESIDENT
    engine = getattr(singletons, getter)()
    assert engine is not None and engine.backend_name == "lm_studio"
    assert engine.model_id == "operator-" + role
    assert engine.expected_instance_id == "instance-operator-" + role
    assert [key for key, _ in runtime.probes] == ["operator-" + role]
    assert runtime.files == [] and len(runtime.sdk) == 1


@pytest.mark.parametrize("entry,key", [("resolve_qwen_backend", "qwen-coder-7b"), ("resolve_gemma_backend", "gemma-270m")])
def test_reachable_nonresident_is_not_reported_as_server_unreachable(runtime, caplog, entry, key):
    runtime.states[key] = LMStudioResidencyState.INSTALLED_NOT_RESIDENT
    with caplog.at_level(logging.DEBUG):
        assert getattr(resolver, entry)() is None
    assert [model for model, _ in runtime.probes] == [key]
    assert "installed_not_resident" in caplog.text
    assert "not reachable" not in caplog.text and "unreachable" not in caplog.text
    assert runtime.sdk == runtime.files == []


@pytest.mark.parametrize("role,entry", [("code", "resolve_qwen_backend"), ("triage", "resolve_gemma_backend")])
def test_singleton_resolves_its_role_once_even_when_no_backend_exists(runtime, monkeypatch, role, entry):
    original = getattr(resolver, entry)
    calls = []
    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(resolver, entry, counted)
    getter = singletons.get_qwen_engine if role == "code" else singletons.get_gemma_engine
    assert getter() is None
    assert len(calls) == 1
    assert len(runtime.probes) == 1 and runtime.files == []


def test_missing_explicit_file_does_not_construct_or_initialize_file_loader(runtime, tmp_path):
    assert resolver.resolve_qwen_backend(model_path=tmp_path / "missing.gguf") is None
    assert runtime.files == []


def test_explicit_existing_file_fallback_contract_is_preserved(runtime, tmp_path):
    runtime.offline, runtime.file_ready = True, True
    path = tmp_path / "explicit.gguf"
    path.write_bytes(b"synthetic-gguf-placeholder")
    engine = resolver.resolve_qwen_backend(model_path=path)
    assert engine is not None and engine.backend_name == "llama_cpp"
    assert runtime.files == [path] and runtime.sdk == []


def test_backend_initialization_retains_exact_native_state_for_diagnostics(runtime):
    runtime.states["selected"] = LMStudioResidencyState.INSTALLED_NOT_RESIDENT
    engine = backends.LMStudioBackend("selected")
    assert engine.initialize() is False
    assert getattr(engine, "last_initialization_status", None) == "installed_not_resident"
    assert len(runtime.probes) == 1 and runtime.sdk == runtime.files == []


def test_sdk_failure_is_distinct_from_reachable_residency_failure(runtime):
    runtime.states["selected"] = LMStudioResidencyState.RESIDENT
    runtime.sdk_missing = True
    engine = backends.LMStudioBackend("selected")
    assert engine.initialize() is False
    assert getattr(engine, "last_initialization_status", None) == "sdk_unavailable"


def test_native_authentication_failure_still_propagates(runtime):
    runtime.auth = True
    with pytest.raises(LMStudioAuthenticationError): resolver.resolve_qwen_backend()
    assert runtime.files == runtime.sdk == []


def test_cached_engine_and_status_do_not_probe_or_select_another_model(runtime):
    runtime.states["qwen-coder-7b"] = LMStudioResidencyState.RESIDENT
    first = singletons.get_qwen_engine()
    before = len(runtime.probes)
    assert first is not None and singletons.get_qwen_engine() is first
    assert singletons.get_engine_status()["qwen"]["loaded"] is True
    assert len(runtime.probes) == before


def test_explicit_none_native_key_skips_unrelated_server_probe(runtime, tmp_path):
    assert "native_model_key" in inspect.signature(resolver.resolve_qwen_backend).parameters
    assert resolver.resolve_qwen_backend(model_path=tmp_path / "missing.gguf", native_model_key=None) is None
    assert runtime.probes == runtime.files == runtime.sdk == []
