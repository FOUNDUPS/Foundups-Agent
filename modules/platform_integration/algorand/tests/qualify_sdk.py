"""Prepare a fixed SDK profile; execute only after a separate explicit test release.

The Python effect pattern derives from reviewed qualify_dependencies.py:117-177.
It is not an OS sandbox or a claim that native code cannot bypass Python hooks.
"""
import argparse
import ast
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import struct
import sys
import tempfile
import unittest
import zipfile
from email.parser import BytesParser

PREFIX = "modules.platform_integration.algorand"
TEST = PREFIX + ".tests.test_unsigned_asa_probe"
ADAPTER = Path(__file__).resolve()
TEST_INVENTORY_SHA256 = "8dc3199b3e49348552bd871a9265842d11356986e2718241931c6aae2b5f03d7"

def need(ok, reason):
    if not ok:
        error = RuntimeError(reason); error.foundups_reason = reason; raise error

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")

def test_inventory(identifiers):
    need(type(identifiers) is list and len(identifiers) == 52 and all(type(i) is str for i in identifiers), "test_inventory")
    need(identifiers == sorted(identifiers) and len(set(identifiers)) == 52, "test_inventory")
    digest = hashlib.sha256(json.dumps(identifiers, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
    need(digest == TEST_INVENTORY_SHA256, "test_inventory")
    return dict(schema="asa-codec-tests-v2", count=52, ids_sha256=digest)

def plain(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        need(not part.is_symlink() and not part.is_junction(), "linked_profile_parent")
    return path.resolve(strict=True)

def diagnostic(error):
    frames = []; trace = error.__traceback__; code = getattr(error, "foundups_reason", None)
    while trace is not None:
        frames.append(dict(source_filename=trace.tb_frame.f_code.co_filename[-512:], source_line=trace.tb_lineno)); frames = frames[-12:]
        trace = trace.tb_next
    return dict(exception_type=type(error).__name__[:120], reason_code=code if isinstance(code, str) and re.fullmatch("[a-z_]{1,80}", code) else None, frames=frames)

def note_failure(receipt, case, error):
    if len(receipt["diagnostics"]) < 64: receipt["diagnostics"].append(dict(case=case, **diagnostic(error)))
    else: receipt["diagnostic_overflow"] += 1

def origins(data):
    observed = {name: dict(path=str(Path(module.__file__).resolve()), raw_sha256=sha(module.__file__)) for name, module in list(sys.modules.items()) if getattr(module, "__file__", None) and Path(module.__file__).is_file()}
    need(all(data["files"].get(row["path"]) == row["raw_sha256"] for row in observed.values()), "loaded_origin")
    for name, relative in data["namespaces"].items():
        if name in sys.modules: need(list(sys.modules[name].__path__) == [str((Path(data["repo"]) / relative).resolve())], "loaded_namespace")
    return observed

def assert_guarded():
    profile = sys.getprofile()
    state = getattr(profile, "foundups_guard", {})
    need(state.get("protocol") == "asa-codec-v1" and state.get("active") is True, "profile_not_admitted")
    need(Path(profile.__code__.co_filename).resolve() == ADAPTER and state["adapter"] == str(ADAPTER), "profile_origin")
    return profile

def expected_denial(kind, action):
    profile = assert_guarded(); state = profile.foundups_guard
    need(kind in {"socket", "dns", "subprocess", "account_sign_client"} and state["expected"] is None, "control_kind")
    before = len(state["attempts"]); state["expected"] = kind
    try:
        try: action()
        except PermissionError: pass
        else: raise AssertionError("expected_denial_missing")
    finally:
        state["expected"] = None
        sys.setprofile(profile)
    need(state["attempts"][before:] == [{"kind": kind, "expected": True}], "control_events")

def tree(root, excluded=()):
    root = plain(root); result = {}
    for path in Path(root).rglob("*"):
        if any(path == x or x in path.parents for x in excluded): continue
        need(not path.name.lower().startswith(".env"), "dotenv_profile_path")
        need(not path.is_symlink() and not path.is_junction(), "linked_profile_path")
        if path.is_file(): result[str(path.resolve())] = sha(path)
    return result

def identity():
    need(sys.version_info[:3] == (3, 12, 10) and sys.platform == "win32", "fixed_python")
    need(sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.optimize == 0 and not sys.flags.no_site, "python_flags")
    need(sys.implementation.name == "cpython" and struct.calcsize("P") == 8 and not hasattr(sys, "gettotalrefcount"), "fixed_abi")
    need(sys.prefix != sys.base_prefix, "distinct_venv")
    for path in (Path(sys.executable), Path(sys.base_prefix) / "python.exe", Path(sys.base_prefix) / "python312.dll"):
        path = plain(path)
        raw = path.read_bytes(); offset = int.from_bytes(raw[60:64], "little")
        need(raw[:2] == b"MZ" and raw[offset:offset+4] == b"PE\0\0" and int.from_bytes(raw[offset+4:offset+6], "little") == 0x8664 and int.from_bytes(raw[offset+24:offset+26], "little") == 0x20b, "amd64_pe")
    return {"executable": str(plain(sys.executable)), "prefix": str(plain(sys.prefix)), "base": str(plain(sys.base_prefix))}

def prepare(args):
    ident = identity(); repo = plain(args.repo); site = plain(Path(ident["prefix"]) / "Lib/site-packages")
    output = Path(args.profile).resolve(); need(repo not in output.parents and re.fullmatch("[a-f0-9]{40}", args.head), "profile_context")
    lock = repo / "modules/platform_integration/algorand/tests/requirements-win312.lock"
    lines = [x.strip() for x in lock.read_text(encoding="utf-8").replace("\\\n", "").splitlines() if x.strip() and not x.lstrip().startswith("#")]
    pins = {}
    for line in lines:
        if line == "--only-binary=:all:": continue
        match = re.fullmatch(r"([\w.-]+)==([^\s]+)\s+--hash=sha256:([a-f0-9]{64})", line)
        need(match is not None, "lock_declaration")
        name, version, digest = match.groups(); name = re.sub(r"[-_.]+", "-", name).lower()
        need(name not in pins, "duplicate_pin"); pins[name] = (version, digest)
    wheels = list(Path(args.wheelhouse).resolve().glob("*.whl")); need(len(pins) == len(wheels) == 15, "wheel_count")
    files = tree(Path(ident["base"]), (Path(ident["base"]) / "Lib/site-packages",)); metadata = {}; archives = {}
    baseline = tree(Path(ident["prefix"]), (site,))
    need(ident["executable"] in baseline and str(Path(ident["prefix"]) / "pyvenv.cfg") in baseline, "venv_baseline")
    files.update(baseline)
    need(not list(site.rglob("*.pth")), "site_startup_hook")
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            entries = [n for n in archive.namelist() if not n.endswith("/")]
            need(all(not Path(n).is_absolute() and ".." not in Path(n).parts and "\\" not in n and ".data/" not in n for n in entries), "wheel_layout")
            names = [n for n in entries if n.endswith(".dist-info/METADATA")]; need(len(names) == 1, "wheel_metadata")
            meta = BytesParser().parsebytes(archive.read(names[0])); name = re.sub(r"[-_.]+", "-", meta["Name"]).lower()
            need(name in pins and pins[name] == (meta["Version"], sha(wheel)) and name not in metadata, "wheel_pin")
            archives[wheel.name] = sha(wheel); metadata[name] = {"version": meta["Version"], "metadata_sha256": hashlib.sha256(archive.read(names[0])).hexdigest()}
            for name in entries:
                if name.endswith(".dist-info/RECORD"): continue
                target = plain(site / name); digest = hashlib.sha256(archive.read(name)).hexdigest()
                need(target.is_file() and not target.is_symlink() and sha(target) == digest, "installed_wheel_payload")
                files[str(target.resolve())] = digest
    sources = {"modules": "modules/__init__.py", PREFIX: "modules/platform_integration/algorand/__init__.py", PREFIX + ".src": "modules/platform_integration/algorand/src/__init__.py", PREFIX + ".src.unsigned_asa_probe": "modules/platform_integration/algorand/src/unsigned_asa_probe.py", PREFIX + ".tests.qualify_sdk": str(ADAPTER.relative_to(repo)), TEST: "modules/platform_integration/algorand/tests/test_unsigned_asa_probe.py"}
    namespaces = {"modules.platform_integration": "modules/platform_integration", PREFIX + ".tests": "modules/platform_integration/algorand/tests"}
    for relative in [*sources.values(), str(lock.relative_to(repo))]: files[str(plain(repo / relative))] = sha(repo / relative)
    for relative in namespaces.values(): need((repo / relative).is_dir() and not (repo / relative / "__init__.py").exists(), "namespace_shape")
    parsed = ast.parse((repo / sources[TEST]).read_bytes()); ids = sorted(TEST + "." + c.name + "." + f.name for c in parsed.body if isinstance(c, ast.ClassDef) for f in c.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"))
    inventory = test_inventory(ids)
    save(output, dict(schema="asa-codec-profile-v2", test_inventory=inventory, head=args.head, installation_profile=args.installation_profile, identity=ident, repo=str(repo), site=str(site), sources=sources, namespaces=namespaces, files=files, venv_baseline=baseline, test_ids=ids, metadata=metadata, archives=archives, lock_sha256=sha(lock), adapter_sha256=sha(ADAPTER), startup_limit="Python startup precedes these hooks; fixed controlled venv required. Installer-added RECORD/INSTALLER/scripts are not wheel-payload equality; non-site launchers/config have a distinct measured baseline."))

class SourceGate(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, data, deny):
        self.data, self.deny = data, deny
    def admit(self, ok, reason):
        if not ok: self.deny(reason)
    def read(self, origin):
        try: path = plain(origin); raw = path.read_bytes()
        except (OSError, RuntimeError, ValueError): self.deny("source_read")
        self.admit(hashlib.sha256(raw).hexdigest() == self.data["files"].get(str(path)), "source_hash")
        return str(path), raw
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "dotenv" or fullname.startswith("dotenv."): self.deny("dotenv_import")
        owned = fullname == "modules" or fullname.startswith(("modules.", "holo_index"))
        if owned and fullname not in self.data["sources"] and fullname not in self.data["namespaces"]: self.deny("repository_import")
        spec = importlib.machinery.PathFinder.find_spec(fullname, [self.data["repo"]] if fullname == "modules" else path)
        if spec is None:
            if owned: self.deny("source_missing")
            return None
        if spec.origin is None and spec.submodule_search_locations is not None:
            locations = [Path(location).resolve() for location in spec.submodule_search_locations]
            self.admit(not any(Path(self.data["repo"]) == location or Path(self.data["repo"]) in location.parents for location in locations) or fullname in self.data["namespaces"], "source_name_origin")
        if fullname in self.data["namespaces"]:
            try: location = str(plain(Path(self.data["repo"]) / self.data["namespaces"][fullname]))
            except (OSError, RuntimeError, ValueError): self.deny("source_namespace")
            self.admit(spec.origin is None and list(spec.submodule_search_locations or []) == [location], "source_namespace"); return spec
        if owned: self.admit(spec.origin not in {None, "built-in", "frozen"}, "source_origin")
        if spec.origin in {None, "built-in", "frozen"}: return spec
        origin, raw = self.read(spec.origin); spec.origin = origin
        if owned or Path(self.data["repo"]) in Path(origin).parents:
            self.admit(fullname in self.data["sources"] and origin == str((Path(self.data["repo"]) / self.data["sources"][fullname]).resolve()), "source_name_origin")
        if origin.endswith(".py"): spec.loader = self
        return spec
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        origin, raw = self.read(module.__spec__.origin)
        exec(compile(raw, origin, "exec", dont_inherit=True), module.__dict__)

def install_guard(data, phase):
    state = dict(protocol="asa-codec-v1", active=True, adapter=str(ADAPTER), expected=None, attempts=[])
    def deny(kind):
        state["attempts"].append(dict(kind=kind, expected=state["expected"] == kind))
        error = PermissionError(kind + " denied"); error.foundups_reason = kind; raise error
    def dns(*args, **kwargs): deny("dns")
    socket.getaddrinfo = dns
    sys.meta_path.insert(0, SourceGate(data, deny))
    def check_write(value):
        if isinstance(value, int): return
        path = Path(os.fsdecode(value)).resolve()
        if path != phase and phase not in path.parents: deny("outside_phase_write")
    def audit(event, args):
        if event.startswith("socket."): deny("socket")
        if event == "subprocess.Popen": deny("subprocess")
        if event in ("os.system", "os.posix_spawn", "os.spawn", "os.fork", "os.exec"): deny("process")
        if event == "sqlite3.connect": deny("sqlite")
        if event == "open":
            value, mode, flags = args
            if not isinstance(value, int) and Path(os.fsdecode(value)).name.lower().startswith(".env"): deny("dotenv_read")
            if (isinstance(mode, str) and any(x in mode for x in "wax+")) or (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)): check_write(value)
        if event in ("os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.utime", "os.truncate"): check_write(args[0])
        if event in ("os.rename", "os.replace", "os.link", "os.symlink"): check_write(args[0]); check_write(args[1])
        if event == "os.chdir":
            try: accepted = Path(args[0]).resolve() == phase
            except (OSError, TypeError, ValueError): accepted = False
            if not accepted: deny("outside_phase_chdir")
    sys.addaudithook(audit)
    def profile(frame, event, arg):
        if event != "call": return
        file = frame.f_code.co_filename.replace("\\", "/").lower(); name = frame.f_code.co_name
        bad = "/algosdk/" in file and (name in ("generate_account", "sign", "raw_sign", "estimate_size") or ("/v2client/" in file and name == "__init__") or (file.endswith(("/wallet.py", "/kmd.py")) and name == "__init__"))
        bad = bad or ("/nacl/" in file and name in ("sign", "generate", "crypto_sign", "crypto_sign_seed_keypair", "crypto_sign_keypair"))
        bad = bad or ("/cryptodome/" in file and ("/signature/" in file or name in ("generate", "sign")))
        if bad: deny("account_sign_client")
    profile.foundups_guard = state; sys.setprofile(profile)
    return profile

def run(args):
    data = json.loads(Path(args.profile).read_text(encoding="utf-8")); authorization = json.loads(Path(args.release).read_text(encoding="utf-8"))
    phase = Path(args.phase).resolve(); repo = Path(data["repo"])
    inventory = test_inventory(data["test_ids"])
    need(type(data["test_inventory"]) is dict and type(data["test_inventory"].get("count")) is int
         and data["test_inventory"] == inventory, "test_inventory_descriptor")
    need(authorization == dict(status="RELEASED_FOR_CODEC_TESTS_V2", profile_sha256=sha(args.profile), adapter_sha256=sha(ADAPTER), head=data["head"], phase=str(phase), test_inventory_sha256=TEST_INVENTORY_SHA256), "release_binding")
    need(data["schema"] == "asa-codec-profile-v2" and data["adapter_sha256"] == sha(ADAPTER) and identity() == data["identity"], "profile_binding")
    need(ADAPTER == (repo / data["sources"][PREFIX + ".tests.qualify_sdk"]).resolve(), "adapter_real_path")
    need(repo not in phase.parents and not phase.exists(), "new_external_phase")
    need(all(Path(p).is_file() and sha(p) == digest for p, digest in data["files"].items()), "frozen_file_drift")
    need(tree(Path(data["identity"]["prefix"]), (Path(data["site"]),)) == data["venv_baseline"], "venv_baseline_drift")
    need(not list(Path(data["site"]).rglob("*.pth")), "site_changed_startup")
    need(not any(n == "modules" or n.startswith(("modules.", "algosdk", "msgpack", "dotenv")) for n in sys.modules), "preloaded_candidate")
    origins(data)
    phase.mkdir(parents=True); os.chdir(phase)
    clean_env = {name: os.environ[name] for name in ("SystemRoot", "WINDIR", "COMSPEC") if name in os.environ}; os.environ.clear(); os.environ.update(clean_env)
    for name in ("TEMP", "TMP", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA"): os.environ[name] = str(phase)
    tempfile.tempdir = str(phase)
    guard = install_guard(data, phase); state = guard.foundups_guard
    receipt = dict(status="FAILED", stage="test_import", test_inventory=inventory, profile_sha256=sha(args.profile), installation_profile=data["installation_profile"], attempts=state["attempts"], cases=[], diagnostics=[], diagnostic_overflow=0, limitation="Python hooks, not OS/native isolation; startup is separate from guarded execution.")
    try:
        suite = unittest.defaultTestLoader.loadTestsFromName(TEST)
        def ids(group): return [identifier for item in group for identifier in (ids(item) if isinstance(item, unittest.TestSuite) else [item.id()])]
        collected = sorted(ids(suite)); receipt["collected_ids"] = collected; need(collected == data["test_ids"], "collected_ids")
        outcomes = {identifier: "NOT_RUN" for identifier in collected}
        class Result(unittest.TestResult):
            def addSuccess(self, test): super().addSuccess(test); outcomes[test.id()] = "PASS"
            def addFailure(self, test, error): super().addFailure(test, error); outcomes[test.id()] = "FAIL"; note_failure(receipt, test.id(), error[1])
            def addError(self, test, error): super().addError(test, error); outcomes[test.id()] = "ERROR"; note_failure(receipt, test.id(), error[1])
            def addSkip(self, test, reason): super().addSkip(test, reason); outcomes[test.id()] = "SKIP"
            def addExpectedFailure(self, test, error): super().addExpectedFailure(test, error); outcomes[test.id()] = "XFAIL"; note_failure(receipt, test.id(), error[1])
            def addUnexpectedSuccess(self, test): super().addUnexpectedSuccess(test); outcomes[test.id()] = "XPASS"
            def addSubTest(self, test, subtest, error):
                super().addSubTest(test, subtest, error)
                if error: outcomes[test.id()] = "FAIL"; note_failure(receipt, test.id(), error[1])
            def stopTest(self, test):
                super().stopTest(test)
                if sys.getprofile() is not guard or any(not a["expected"] for a in state["attempts"]): outcomes[test.id()] = "GUARD_FAILURE"; self.stop()
        receipt["stage"] = "test_execute"; result = Result(); suite.run(result)
        receipt["cases"] = [dict(id=identifier, status=outcomes[identifier]) for identifier in collected]
        receipt["stage"] = "postconditions"
        need(result.testsRun == len(collected) and all(x == "PASS" for x in outcomes.values()), "unit_outcomes")
        need(sys.getprofile() is guard and not any(not a["expected"] for a in state["attempts"]), "guard_integrity")
        need({a["kind"] for a in state["attempts"]} == {"socket", "dns", "subprocess", "account_sign_client"}, "negative_controls")
        receipt["status"] = "PASS"
    except BaseException as error: receipt["phase_failure"] = diagnostic(error)
    finally:
        try:
            need(all(Path(p).is_file() and sha(p) == digest for p, digest in data["files"].items()), "post_file_drift")
            need(tree(Path(data["identity"]["prefix"]), (Path(data["site"]),)) == data["venv_baseline"], "post_venv_baseline_drift")
            receipt["origins"] = origins(data)
        except BaseException as error: receipt.update(status="FAILED", final_failure=diagnostic(error))
        state["active"] = False; sys.setprofile(None); receipt["unexpected_attempt_count"] = sum(not a["expected"] for a in state["attempts"]); save(phase / "receipt.json", receipt)
    return 0 if receipt["status"] == "PASS" else 1

def main():
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser("prepare")
    for name in ("repo", "wheelhouse", "profile", "head"): preparation.add_argument("--" + name, required=True)
    preparation.add_argument("--installation-profile", choices=("local-materialized", "ci-pip"), required=True)
    execution = commands.add_parser("run")
    for name in ("profile", "phase", "release"): execution.add_argument("--" + name, required=True)
    args = parser.parse_args()
    return prepare(args) if args.command == "prepare" else run(args)

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(json.dumps(dict(status="FAILED", stage="adapter_cli", failure=diagnostic(error))))
        raise SystemExit(1)
