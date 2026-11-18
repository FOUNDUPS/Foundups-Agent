"""Model-free Qwen package boundary and fixed public API controls.

Real package/leaf imports are guarded before other application imports execute.
Synthetic owners prove export dispatch only; no real coordinator is exercised.
Run directly with Python -I -S -B; every case uses a fresh isolated child.
"""
from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PACKAGE = "holo_index.qwen_advisor"
# Frozen from the original public API, independent of the candidate dispatch.
EXPECTED = {
    "HoloDAECoordinator": "holodae_coordinator",
    "start_holodae": "holodae_coordinator",
    "stop_holodae": "holodae_coordinator",
    "get_holodae_status": "holodae_coordinator",
    "show_holodae_menu": "holodae_coordinator",
    "WorkContext": "models.work_context",
    "MonitoringResult": "models.monitoring_types",
    "HealthViolation": "models.monitoring_types",
    "PatternAlert": "models.monitoring_types",
    "MonitoringState": "models.monitoring_types",
    "QwenOrchestrator": "orchestration.qwen_orchestrator",
    "MPSArbitrator": "arbitration.mps_arbitrator",
    "ArbitrationDecision": "arbitration.mps_arbitrator",
    "MPSAnalysis": "arbitration.mps_arbitrator",
    "PriorityLevel": "arbitration.mps_arbitrator",
    "ActionType": "arbitration.mps_arbitrator",
    "FileSystemWatcher": "services.file_system_watcher",
    "ContextAnalyzer": "services.context_analyzer",
    "HoloDAEMenuSystem": "ui.menu_system",
    "StatusDisplay": "ui.menu_system",
}
OWNERS = {PACKAGE + "." + value for value in EXPECTED.values()}
PARENTS = {name.rsplit(".", 1)[0] for name in OWNERS} - {PACKAGE}
REAL_MODULES = {"holo_index", PACKAGE, PACKAGE + ".llm_engine"}


class ImportBoundary(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Allow the real leaf and optionally serve inert, recording API owners."""

    def __init__(self, synthetic: bool, failure: bool):
        self.synthetic = synthetic
        self.failure = failure
        self.loaded: list[str] = []
        self.values: dict[str, object] = {}
        self.attempts: list[str] = []

    def find_spec(self, fullname, path=None, target=None):
        self.attempts.append(fullname)
        if fullname in REAL_MODULES:
            return None
        if self.synthetic and fullname in OWNERS | PARENTS:
            return importlib.util.spec_from_loader(
                fullname, self, is_package=fullname in PARENTS
            )
        if fullname.split(".", 1)[0] in sys.stdlib_module_names:
            return None
        raise ImportError("blocked_import:" + fullname)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        if module.__name__ in PARENTS:
            return
        self.loaded.append(module.__name__)
        if self.failure:
            raise ModuleNotFoundError("synthetic_owner_unavailable")
        for name, owner in EXPECTED.items():
            if module.__name__ == PACKAGE + "." + owner:
                self.values[name] = object()
                setattr(module, name, self.values[name])


def deny_effects(event, args):
    """Reject known external effects before they occur; not an OS sandbox."""
    forbidden = {
        "subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.fork",
        "os.chdir", "os.putenv", "os.unsetenv", "os.mkdir", "os.remove",
        "os.rename", "os.rmdir", "os.link", "os.symlink", "ctypes.dlopen",
    }
    if event in forbidden or event.startswith("socket."):
        raise RuntimeError("blocked_effect:" + event)
    if event == "open":
        path, mode, flags = args
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise RuntimeError("blocked_file_write")
        if isinstance(path, (str, bytes)) and os.fsdecode(path).endswith(".gguf"):
            raise RuntimeError("blocked_model_read")


class BoundedOutput:
    def __init__(self, stream):
        self.stream = stream
        self.remaining = 65536

    def write(self, value):
        self.remaining -= len(value.encode("utf-8"))
        if self.remaining < 0:
            raise RuntimeError("child_output_limit")
        return self.stream.write(value)

    def flush(self):
        self.stream.flush()


def assert_no_owners(boundary):
    assert boundary.loaded == [], boundary.loaded
    assert not (OWNERS & sys.modules.keys())


def check_metadata(package, boundary):
    assert package.__all__ == list(EXPECTED)
    assert package.__version__ == "2.0.0"
    assert set(EXPECTED) <= set(dir(package))
    try:
        getattr(package, "missing_public_name")
    except AttributeError:
        pass
    else:
        raise AssertionError("unknown_attribute_not_rejected")
    assert_no_owners(boundary)


def check_exports(package, boundary):
    for name, owner in EXPECTED.items():
        before = set(boundary.loaded)
        value = getattr(package, name)
        expected_owner = PACKAGE + "." + owner
        assert set(boundary.loaded) == before | {expected_owner}
        assert value is boundary.values[name]
        count = len(boundary.loaded)
        assert getattr(package, name) is value
        assert vars(package)[name] is value
        assert len(boundary.loaded) == count
    assert len(boundary.loaded) == len(OWNERS) == 8


def exercise(case, package, boundary):
    assert_no_owners(boundary)
    if case in {"package", "metadata"}:
        check_metadata(package, boundary)
    elif case in {"leaf", "submodule"}:
        if case == "leaf":
            leaf = importlib.import_module(PACKAGE + ".llm_engine")
        else:
            from holo_index.qwen_advisor import llm_engine as leaf
        assert leaf.QwenInferenceEngine.__module__ == PACKAGE + ".llm_engine"
        assert "llama_cpp" not in sys.modules
        assert_no_owners(boundary)
    elif case == "exports":
        check_exports(package, boundary)
    elif case == "from_import":
        from holo_index.qwen_advisor import WorkContext
        assert WorkContext is boundary.values["WorkContext"]
        assert WorkContext is package.WorkContext
        assert boundary.loaded == [PACKAGE + ".models.work_context"]
    elif case == "star_import":
        namespace = {}
        exec("from holo_index.qwen_advisor import *", namespace)
        assert set(namespace) - {"__builtins__"} == set(EXPECTED)
        assert all(namespace[name] is boundary.values[name] for name in EXPECTED)
        assert len(boundary.loaded) == len(OWNERS) == 8
    elif case == "failure":
        for _ in range(2):
            try:
                package.WorkContext
            except ModuleNotFoundError as error:
                assert str(error) == "synthetic_owner_unavailable"
            else:
                raise AssertionError("owner_failure_swallowed")
            assert "WorkContext" not in vars(package)
        assert boundary.loaded == [PACKAGE + ".models.work_context"] * 2
    else:
        raise AssertionError("unknown_case")


def child(case, root):
    root = Path(root).resolve()
    sys.path.insert(0, str(root))
    sys.stdout = BoundedOutput(sys.stdout)
    sys.stderr = BoundedOutput(sys.stderr)
    boundary = ImportBoundary(case not in {"package", "leaf", "submodule"}, case == "failure")
    sys.meta_path.insert(0, boundary)
    before = (list(sys.path), os.getcwd(), dict(os.environ),
              list(logging.root.handlers), logging.root.level, sys.stdout, sys.stderr)
    sys.addaudithook(deny_effects)
    package = importlib.import_module(PACKAGE)
    exercise(case, package, boundary)
    after = (list(sys.path), os.getcwd(), dict(os.environ),
             list(logging.root.handlers), logging.root.level, sys.stdout, sys.stderr)
    assert before == after, "import_changed_process_state"
    for name in REAL_MODULES & sys.modules.keys():
        expected = root.joinpath(*name.split("."))
        expected = expected / "__init__.py" if name != PACKAGE + ".llm_engine" else expected.with_suffix(".py")
        assert Path(sys.modules[name].__file__).resolve() == expected
    assert not any(name.startswith(("llama_cpp", "chromadb", "sentence_transformers")) for name in sys.modules)
    print(json.dumps({"case": case, "real_modules": sorted(REAL_MODULES & sys.modules.keys()),
                      "synthetic_owners_loaded": boundary.loaded, "model_calls": 0}))


class QwenPackageImportTests(unittest.TestCase):
    def run_case(self, case):
        path = Path(__file__).resolve()
        with tempfile.TemporaryDirectory(prefix="qwen-import-") as scratch:
            env = {key: value for key, value in os.environ.items()
                   if key.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC"}}
            env.update(TMP=scratch, TEMP=scratch, HOME=scratch, USERPROFILE=scratch,
                       PYTHONDONTWRITEBYTECODE="1")
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-B", str(path), "--child", case, str(path.parents[2])],
                cwd=scratch, env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertLessEqual(len(result.stdout.encode()), 65536)
            self.assertEqual(result.stderr, "")
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["case"], case)
            self.assertEqual(receipt["model_calls"], 0)

    def test_package_import(self):
        self.run_case("package")

    def test_real_engine_leaf_import(self):
        self.run_case("leaf")

    def test_real_submodule_from_import(self):
        self.run_case("submodule")

    def test_metadata_without_eager_owners(self):
        self.run_case("metadata")

    def test_all_export_targets_and_identity_cache(self):
        self.run_case("exports")

    def test_public_from_import(self):
        self.run_case("from_import")

    def test_public_star_import(self):
        self.run_case("star_import")

    def test_dependency_failure_propagates_without_caching(self):
        self.run_case("failure")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--child":
        child(sys.argv[2], sys.argv[3])
    else:
        unittest.main()
