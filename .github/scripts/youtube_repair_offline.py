"""Fixed YouTube repair selections in separate credential-free children.

The guards reuse the qualified startup, inventory and rotation mechanisms.
This adapter accepts no caller-supplied tests, commands or application roots.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCHEDULER_TESTS = 'modules/platform_integration/youtube_shorts_scheduler/tests/'
SUITES = {
    'routing': (88, '05ac81da16c7f890eaf338321563e69b98bdc27cce6833a90c37feb4ad9f0e53', (
        'modules/ai_intelligence/ai_gateway/tests/test_youtube_model_routing.py',
        'modules/ai_intelligence/ai_gateway/tests/test_youtube_model_composition.py',
        'modules/communication/video_comments/tests/test_llm_integration.py',
        'modules/communication/livechat/tests/test_antima_factcheck.py',
        'modules/communication/livechat/tests/test_antima_savage.py')),
    'quality': (69, '5c1486a10845dd2dd4b44b72304a2eb1a4f2afdbb8d849ccdeccce64e3b15469', (
        'modules/communication/video_comments/tests/test_reply_quality_safety.py',
        'modules/communication/video_comments/tests/test_inbox_completion_evidence.py',
        'modules/communication/video_comments/tests/test_reply_memory_readiness.py',
        'modules/communication/video_comments/tests/test_reply_visual_evidence.py')),
    'quality_stop': (68, '2a5ac5f9e9a8bd249f78ddf959a99e319a613df2b6a346749d49304f34f18b73', (
        'modules/communication/livechat/tests/test_comment_quality_stop.py',)),
    'studio': (137, '012d0519ef03b757222bb16b021f3e297fd9b82908d251fdbce9391024f498d4', (
        'modules/communication/video_comments/tests/test_studio_row_identity.py',
        'modules/communication/video_comments/tests/test_reply_editor_input.py')),
    'startup': (185, 'f0bb505c605a5e9d7ca810589a2033ed842248350578196f46c326772776c2dc', (
        'modules/infrastructure/dependency_launcher/tests/test_llmster_startup_fallback.py',
        'modules/infrastructure/shared_utilities/tests/test_local_model_selection.py',
        'modules/infrastructure/shared_utilities/tests/test_lm_studio_dependency_boundary.py',
        'modules/infrastructure/shared_utilities/tests/test_lm_studio_model_lifecycle.py',
        'modules/infrastructure/shared_utilities/tests/test_local_model_startup_selection.py',
        'modules/infrastructure/shared_utilities/tests/test_local_llm_backends.py',
        'modules/ai_intelligence/ai_overseer/tests/test_preflight_model_boundary.py',
        'modules/ai_intelligence/ai_overseer/tests/test_wsp_framework_sentinel.py',
        'modules/infrastructure/cli/tests/test_console_prompt.py',
        'modules/communication/moltbot_bridge/tests/test_supervisor_model_startup.py')),
    'inventory': (102, 'dc14189b4474df1d2f62cb18858206d861078fabad24de6451d242aeb098ef49', (
        SCHEDULER_TESTS + 'test_scheduled_inventory.py',
        SCHEDULER_TESTS + 'test_visibility_filter_enforcement.py',
        SCHEDULER_TESTS + 'test_schedule_audit_breadcrumb.py')),
    'rotation': (35, '664830788a43165c40b0166e2f7736d63cc06e1f73346db9b1d1f2cb1a0bc07d', (
        SCHEDULER_TESTS + 'test_schedule_rotation_fairness.py',)),
    'directives': (114, '1325d6466530d3e89f41c97020080795ceb0f0ec79f739dbdeb7e7da9f27d432', (
        SCHEDULER_TESTS + 'test_presave_audit.py',
        SCHEDULER_TESTS + 'test_video_policy_consumers.py',
        SCHEDULER_TESTS + 'test_video_policy_save_readback.py',
        SCHEDULER_TESTS + 'test_video_policy_inline.py',
        'modules/communication/youtube_shorts/tests/test_operator_upload_policy.py')),
    'calendar': (154, 'f54b0a7d33867ae0df88d013007ca0555c28ad6d4275592596ab6a5931bfab68', (
        'modules/communication/livechat/tests/test_operator_stream_schedule.py',
        SCHEDULER_TESTS + 'test_stream_schedule_calendar.py',
        SCHEDULER_TESTS + 'test_calendar_reservations.py')),
}

# Reviewed literals only; no caller-provided JavaScript or runtime browser.
NODE_FIXTURES = {
    'modules/communication/video_comments/tests/test_studio_row_identity.py':
        ('STUDIO_DOM', 'c93324766519e5b7d15a60990df6c816ba12cee04fcad5b6e0436147f1350e5c'),
    'modules/communication/video_comments/tests/test_reply_editor_input.py':
        ('EDITOR_DOM', '2d949aaebc6b2258c1711e4d9fe9ba7950356ddcb6f6ab13a55035420ac4b1cf'),
}


def minimal_environment(out):
    """Fixed platform values and private paths only; inherit no credentials."""
    env = dict(HOME=str(out / 'profile'), USERPROFILE=str(out / 'profile'),
               APPDATA=str(out / 'profile/AppData/Roaming'),
               LOCALAPPDATA=str(out / 'profile/AppData/Local'),
               TEMP=str(out / 'tmp'), TMP=str(out / 'tmp'), TMPDIR=str(out / 'tmp'),
               USERNAME='offline-youtube-test', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
               PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1',
               PYTHON_DOTENV_DISABLED='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    if os.name == 'nt':
        env.update(SYSTEMROOT=r'C:\Windows', WINDIR=r'C:\Windows', SYSTEMDRIVE='C:',
                   COMSPEC=r'C:\Windows\System32\cmd.exe',
                   PATH=r'C:\Windows\System32;C:\Windows', OS='Windows_NT')
    else:
        env.update(PATH='/usr/bin:/bin', LANG='C.UTF-8')
    return env


def admitted(suite):
    sys.path.insert(0, str(ROOT))
    from modules.infrastructure.wre_core.src.wre_test_registry_classification import classify_test_file
    registry = json.loads((ROOT / 'WSP_knowledge/WSP_Test_Registry.json').read_text(encoding='utf-8'))
    entries = {row['path']: row for row in registry['tests']}
    for path in SUITES[suite][2]:
        current = classify_test_file(ROOT, path)
        recorded = entries.get(path, {})
        if (not current.collectable or current.quarantine_reasons
                or recorded.get('collectable') is not True
                or recorded.get('quarantine_reasons')
                or recorded.get('suite_class') != current.suite_class):
            return False
    return True


class EffectGuard:
    def __init__(self, out, suite):
        import socket
        import sqlite3
        self.out, self.suite = out, suite
        self.denied, self.in_socketpair = 0, False
        self.original_pair = socket.socketpair
        self.original_run, self.original_popen = subprocess.run, subprocess.Popen
        self.original_connect = sqlite3.connect
        self.node, self.node_hash, self.node_programs = None, None, set()
        self.node_call, self.sqlite_call = None, None
        self.node_calls, self.sqlite_calls = 0, 0
        if suite == 'studio':
            bound = json.loads((out / 'owner.json').read_text(encoding='utf-8'))['node']
            self.node, self.node_hash = Path(bound['path']).resolve(), bound['sha256']
            if hashlib.sha256(self.node.read_bytes()).hexdigest() != self.node_hash:
                self.deny()
            for relative, (name, expected) in NODE_FIXTURES.items():
                tree = ast.parse((ROOT / relative).read_text(encoding='utf-8'))
                programs = [ast.literal_eval(item.value) for item in tree.body
                    if isinstance(item, ast.Assign) and len(item.targets) == 1
                    and isinstance(item.targets[0], ast.Name) and item.targets[0].id == name]
                if len(programs) != 1 or hashlib.sha256(programs[0].encode()).hexdigest() != expected:
                    self.deny()
                self.node_programs.add(programs[0])

    def node_run(self, args, *positional, **kwargs):
        if (self.suite != 'studio' or positional or not isinstance(args, (list, tuple))
                or len(args) != 3 or args[1] != '-e' or args[2] not in self.node_programs
                or Path(args[0]).resolve() != self.node
                or set(kwargs) not in ({'input', 'capture_output', 'text', 'timeout', 'check'},
                                      {'input', 'capture_output', 'text', 'timeout', 'check', 'env'})
                or ('env' in kwargs and kwargs['env'] != {'SystemRoot': r'C:\Windows', 'WINDIR': r'C:\Windows'})
                or kwargs['capture_output'] is not True or kwargs['text'] is not True
                or kwargs['timeout'] != 5 or kwargs['check'] is not True
                or not isinstance(kwargs['input'], str) or self.node_call is not None
                or hashlib.sha256(self.node.read_bytes()).hexdigest() != self.node_hash):
            self.deny()
        command, env = [str(self.node), '-e', args[2]], minimal_environment(self.out)
        self.node_call = (command, str(self.out), env)
        try:
            self.node_calls += 1
            kwargs.pop('env', None)  # Discard the literal fixture's platform hint.
            return self.original_run(command, **kwargs, cwd=str(self.out), env=env, shell=False)
        finally:
            self.node_call = None

    def node_popen(self, args, *positional, **kwargs):
        if self.node_call is None or positional:
            self.deny()
        command, cwd, env = self.node_call
        if (list(args) != command or str(kwargs.get('cwd')) != cwd or kwargs.get('env') != env
                or kwargs.get('shell') is not False or kwargs.get('text') is not True
                or any(kwargs.get(key) != subprocess.PIPE for key in ('stdin', 'stdout', 'stderr'))
                or set(kwargs) != {'stdin', 'stdout', 'stderr', 'text', 'cwd', 'env', 'shell'}):
            self.deny()
        return self.original_popen(args, **kwargs)

    def private_sqlite(self, database, *args, **kwargs):
        if (self.suite != 'quality_stop' or args or kwargs.get('uri')
                or not isinstance(database, (str, os.PathLike))
                or str(database).startswith(('file:', ':')) or not self.allowed(database)
                or Path(database).resolve() == Path(os.devnull).resolve()
                or self.sqlite_call is not None):
            self.deny()
        self.sqlite_call = str(Path(database).resolve())
        try:
            self.sqlite_calls += 1
            return self.original_connect(database, **kwargs)
        finally:
            self.sqlite_call = None

    def deny(self, *_args, **_kwargs):
        self.denied += 1
        raise RuntimeError('Offline effect denied; arguments suppressed')

    def allowed(self, path):
        if isinstance(path, int):
            return True
        try:
            value = Path(os.fsdecode(path)).resolve()
            return value == Path(os.devnull).resolve() or (
                value.is_relative_to(self.out) and not value.is_relative_to(ROOT)
                and not ROOT.is_relative_to(value))
        except (TypeError, ValueError, OSError):
            return False

    def pair(self, *args, **kwargs):
        self.in_socketpair = True
        try:
            return self.original_pair(*args, **kwargs)
        finally:
            self.in_socketpair = False

    def private_pair_event(self, event, args):
        if (event in {'socket.bind', 'socket.connect'} and self.suite in {'startup', 'rotation', 'directives', 'quality', 'routing', 'quality_stop', 'studio', 'calendar'}
                and self.in_socketpair):
            frame = sys._getframe(1)
            while frame and frame.f_code is not self.original_pair.__code__:
                frame = frame.f_back
            if frame and isinstance(args[1], tuple) and args[1][0] == '127.0.0.1':
                return True
        return False

    def audit(self, event, args):
        if self.private_pair_event(event, args):
            return
        if event == 'subprocess.Popen' and self.suite == 'studio' and self.node_call is not None:
            command, cwd, env = self.node_call
            expected = ((None, subprocess.list2cmdline(command), cwd, env) if os.name == 'nt'
                        else (command[0], command, cwd, env))
            if args == expected:
                return
        if (event == 'sqlite3.connect' and self.suite == 'quality_stop' and self.sqlite_call is not None
                and str(Path(args[0]).resolve()) == self.sqlite_call and self.allowed(args[0])):
            return
        if event in {'subprocess.Popen', 'os.system', 'os.exec', 'os.spawn', 'socket.bind',
                     'socket.connect', 'socket.connect_ex', 'socket.sendto', 'sqlite3.connect',
                     'winreg.CreateKey', 'winreg.SetValue', 'winreg.DeleteKey', 'winreg.DeleteValue'}:
            self.deny()
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0]))
            if path.name.lower() == '.env' or path.name.lower().startswith('.env.'):
                self.deny()
            mode, flags = args[1], args[2] if isinstance(args[2], int) else 0
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writing and not self.allowed(path):
                self.deny()
        if event == 'os.truncate' and (isinstance(args[0], int) or not self.allowed(args[0])):
            self.deny()
        if event == 'os.link':
            if not all(self.allowed(path) for path in args[:2]):
                self.deny()
            if any(value not in (None, -1) for value in args[2:]):
                self.deny()
        if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename'}:
            for path in args[:2] if event == 'os.rename' else args[:1]:
                if isinstance(path, (str, bytes, os.PathLike)) and not self.allowed(path):
                    self.deny()


def install_effects(stack, guard):
    import socket
    from unittest.mock import patch
    socket.has_ipv6 = False  # Avoid urllib3's import-time IPv6 bind probe.
    if guard.suite in {'startup', 'rotation', 'directives', 'quality', 'routing', 'quality_stop', 'studio', 'calendar'}:
        socket.socketpair = guard.pair
    sys.addaudithook(guard.audit)
    stack.enter_context(patch('subprocess.run', new=guard.node_run if guard.suite == 'studio' else guard.deny))
    stack.enter_context(patch('subprocess.Popen', new=guard.node_popen if guard.suite == 'studio' else guard.deny))
    if guard.suite == 'quality_stop':
        stack.enter_context(patch('sqlite3.connect', new=guard.private_sqlite))
    for target in ('os.system', 'socket.create_connection',
                   'urllib.request.OpenerDirector.open', 'urllib.request.urlopen'):
        stack.enter_context(patch(target, new=guard.deny))
    if hasattr(os, 'startfile'):
        stack.enter_context(patch('os.startfile', new=guard.deny))
    try:
        import dotenv
        stack.enter_context(patch.object(dotenv, 'load_dotenv', return_value=False))
    except ImportError:
        pass


def prepare_startup(stack):
    from unittest.mock import patch
    from modules.infrastructure.shared_utilities import runtime_artifact_safety as safety
    original_lock = safety.runtime_operation_lock

    def private_lock(identity, **kwargs):
        return original_lock('offline-startup-20261029:' + identity, **kwargs)

    stack.enter_context(patch.object(safety, 'runtime_operation_lock', private_lock))


def prepare_inventory(stack, out, guard):
    import asyncio
    import time
    from unittest.mock import patch
    from modules.infrastructure.shared_utilities import youtube_channel_registry as registry
    registry._REGISTRY_PATH = out / 'youtube_channels.json'
    registry._REGISTRY_PATH.write_text(json.dumps({'version': 1, 'channels': registry._default_channels()}), encoding='utf-8')
    stack.enter_context(patch.object(registry, 'get_company_id', return_value=None))
    stack.enter_context(patch.object(registry, '_write_registry', new=guard.deny))

    class OfflineLoop(asyncio.SelectorEventLoop):
        def _make_self_pipe(self):
            self._ssock = self._csock = None

        def _close_self_pipe(self):
            pass

        def _write_to_self(self):
            pass

        def __init__(self):
            super().__init__()
            self._selector.select = lambda timeout=None: (time.sleep(min(timeout, 0.01)) if timeout and timeout > 0 else None) or []

    class OfflinePolicy(asyncio.DefaultEventLoopPolicy):
        _loop_factory = OfflineLoop

    asyncio.set_event_loop_policy(OfflinePolicy())


def prepare_rotation(out):
    import importlib
    import types
    from modules.infrastructure.shared_utilities import youtube_channel_registry as registry
    registry._REGISTRY_PATH = out / 'youtube_channels.json'
    parent = importlib.import_module('modules.infrastructure.foundups_selenium')
    package = types.ModuleType(parent.__name__ + '.src')
    package.__path__ = [str(ROOT / 'modules/infrastructure/foundups_selenium/src')]
    sys.modules[package.__name__] = package; parent.src = package
    name = 'modules.communication.livechat.src.multi_channel_coordinator'
    coordinator = types.ModuleType(name)
    coordinator._is_oops_page = lambda *_a, **_k: False
    coordinator.CHANNEL_FALLBACKS = {'Move2Japan': 'UnDaoDu', 'UnDaoDu': 'Move2Japan', 'FoundUps': 'antifaFM', 'antifaFM': 'FoundUps'}
    coordinator.CHANNEL_IDS = {row['name']: row['id'] for row in registry.get_channels()}
    sys.modules[name] = coordinator
    importlib.import_module('modules.communication.livechat.src').multi_channel_coordinator = coordinator


def run_child(suite, out):
    from contextlib import ExitStack
    import tempfile
    os.environ.clear(); os.environ.update(minimal_environment(out))
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    os.chdir(out); sys.path.insert(0, str(ROOT)); sys.dont_write_bytecode = True
    tempfile.tempdir = str(out / 'tmp')
    guard = EffectGuard(out, suite)
    if suite == 'studio':
        os.environ['NODE_BINARY'] = str(guard.node)
    if suite in {'quality', 'quality_stop', 'calendar'}:
        os.environ['YT_AUTOMATION_STOP_FILE'] = str(out / 'STOP')
    with ExitStack() as stack:
        install_effects(stack, guard)
        if not admitted(suite):
            raise RuntimeError('Selection includes a quarantined or unregistered program')
        if suite == 'startup':
            prepare_startup(stack)
        elif suite == 'inventory':
            prepare_inventory(stack, out, guard)
        elif suite in {'rotation', 'directives', 'calendar'}:
            prepare_rotation(out)
        import pytest
        code = pytest.main(['-c', str(ROOT / 'pytest.ini'), '--import-mode=importlib',
            '-p', 'pytest_asyncio.plugin', '-p', 'no:cacheprovider', '-o', 'addopts=',
            '-o', 'log_file=' + str(out / 'pytest.log'), '--basetemp=' + str(out / 'test-temp'),
            '--junitxml=' + str(out / 'raw-results.xml'), '-s', '-q', '--tb=short',
            *[str(ROOT / path) for path in SUITES[suite][2]]])
        if guard.denied:
            raise RuntimeError('Offline effect attempt; qualification failed; arguments suppressed')
        (out / 'effects.json').write_text(json.dumps(dict(denied=guard.denied,
            node_calls=guard.node_calls, private_sqlite_calls=guard.sqlite_calls)), encoding='utf-8')
        return code


def fresh_output(suite):
    import secrets
    parent = Path(os.environ['RUNNER_TEMP']).resolve()
    if parent.is_relative_to(ROOT) or ROOT.is_relative_to(parent) or not parent.is_dir():
        raise RuntimeError('Expected a private runner temporary directory outside Git')
    out = parent / ('youtube-repair-' + suite)
    out.mkdir(mode=0o700)
    for name in ('tmp', 'profile/AppData/Local', 'profile/AppData/Roaming'):
        (out / name).mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_hex(32)
    marker = dict(kind='youtube_repair_offline_child.v1', suite=suite, repository=str(ROOT),
                  nonce_sha256=hashlib.sha256(nonce.encode()).hexdigest())
    if suite == 'studio':
        binary = shutil.which('node')
        if not binary:
            raise RuntimeError('The fixed Node fixture runtime is unavailable')
        binary = Path(binary).resolve()
        marker['node'] = dict(path=str(binary), sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    (out / 'owner.json').write_text(json.dumps(marker), encoding='utf-8')
    return out, nonce


def validate_child(suite, value, nonce):
    out = value.resolve()
    if (out.is_relative_to(ROOT) or ROOT.is_relative_to(out) or not out.is_dir()
            or out.name != 'youtube-repair-' + suite or not nonce):
        raise RuntimeError('Child output ownership mismatch')
    try:
        marker = json.loads((out / 'owner.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise RuntimeError('Child output ownership mismatch') from None
    expected = dict(kind='youtube_repair_offline_child.v1', suite=suite, repository=str(ROOT),
                    nonce_sha256=hashlib.sha256(nonce.encode()).hexdigest())
    if suite == 'studio':
        bound = marker.get('node', {})
        if (set(bound) != {'path', 'sha256'} or not Path(bound['path']).is_absolute()
                or hashlib.sha256(Path(bound['path']).read_bytes()).hexdigest() != bound['sha256']):
            raise RuntimeError('Node fixture runtime binding mismatch')
        expected['node'] = bound
    if marker != expected:
        raise RuntimeError('Child output ownership mismatch')
    return out


def launch(suite):
    out, nonce = fresh_output(suite)
    os.environ.clear(); os.environ.update(minimal_environment(out))
    if not admitted(suite):
        raise RuntimeError('Selection includes a quarantined or unregistered program')
    with (out / 'child-output.private').open('xb') as stream:
        result = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-B', str(Path(__file__).resolve()),
            '--suite', suite, '--child', str(out), '--child-token', nonce], cwd=out, env=minimal_environment(out),
            stdout=stream, stderr=stream, timeout=180, check=False)
    count, expected, _ = SUITES[suite]
    raw = out / 'raw-results.xml'
    cases = list(ET.parse(raw).getroot().iter('testcase')) if raw.is_file() else []
    digest = hashlib.sha256('\n'.join(sorted(case.get('name') for case in cases)).encode()).hexdigest()
    issues = sum(case.find(tag) is not None for case in cases for tag in ('failure', 'error', 'skipped'))
    ok = result.returncode == 0 and len(cases) == count and digest == expected and issues == 0
    # Upload only sanitized XML; no raw assertion/traceback/kwargs artifact.
    clean = ET.Element('testsuite', tests=str(len(cases)))
    for case in cases:
        safe = ET.SubElement(clean, 'testcase', {k: v for k, v in case.attrib.items() if k in {'name', 'classname', 'time'}})
        for tag in ('failure', 'error', 'skipped'):
            if case.find(tag) is not None:
                ET.SubElement(safe, tag, message='Private offline selection did not qualify')
    ET.ElementTree(clean).write(out / 'results.xml', encoding='utf-8', xml_declaration=True)
    summary = dict(suite=suite, ok=ok, returncode=result.returncode, cases=len(cases),
                   expected_cases=count, name_digest=digest, issues=issues,
                   explicit_minimal_child_environment=True, raw_diagnostics_uploaded=False)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--suite', choices=tuple(SUITES), required=True)
    parser.add_argument('--child', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--child-token', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        return run_child(args.suite, validate_child(args.suite, args.child, args.child_token))
    return launch(args.suite)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Offline repair selection did not qualify; details retained privately')
        raise SystemExit(1)
