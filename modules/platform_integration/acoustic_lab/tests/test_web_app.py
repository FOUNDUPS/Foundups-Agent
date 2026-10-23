#!/usr/bin/env python3
"""
Acoustic Lab - Test Suite for Web Application

Tests the Flask web application endpoints and functionality.
"""



import unittest
import json
from unittest.mock import patch, MagicMock
from src.web_app import create_app


class TestWebApp(unittest.TestCase):
    """Test cases for web application functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.client = self.app.test_client()

    def test_index_page(self):
        """Test that index page loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Acoustic Lab', response.data)
        self.assertIn(b'Educational Platform', response.data)

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'Acoustic Lab')
        self.assertIn('stats', data)

    @patch('src.web_app.check_ip_geofencing')
    def test_upload_missing_file(self, mock_geofence):
        """Test upload endpoint with missing file."""
        response = self.client.post('/upload')
        self.assertEqual(response.status_code, 400)

        data = json.loads(response.data)
        self.assertIn('Missing audio file', data['error'])

    @patch('src.web_app.check_ip_geofencing')
    def test_upload_invalid_file_type(self, mock_geofence):
        """Test upload endpoint with invalid file type."""
        data = {'audio': (b'test', 'test.mp3')}
        response = self.client.post('/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.data)
        self.assertIn('Only WAV files are accepted', response_data['error'])

    @patch('src.web_app.check_ip_geofencing')
    def test_upload_invalid_metadata(self, mock_geofence):
        """Test upload endpoint with invalid metadata JSON."""
        data = {
            'audio': (b'test', 'test.wav'),
            'metadata': 'invalid json'
        }
        response = self.client.post('/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)

        response_data = json.loads(response.data)
        self.assertIn('Invalid metadata JSON', response_data['error'])


class TestIPGeofencing(unittest.TestCase):
    """Test cases for IP geofencing functionality."""

    @patch('requests.get')
    def test_valid_utah_ip(self, mock_get):
        """Test IP geofencing with valid Utah IP."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'success',
            'region': 'UT',
            'regionName': 'Utah'
        }
        mock_get.return_value = mock_response

        from src.web_app import check_ip_geofencing
        # Should not raise exception
        check_ip_geofencing('192.168.1.1')

    @patch('requests.get')
    def test_invalid_non_utah_ip(self, mock_get):
        """Test IP geofencing with non-Utah IP."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'status': 'success',
            'region': 'CA',
            'regionName': 'California'
        }
        mock_get.return_value = mock_response

        from src.web_app import check_ip_geofencing, IPGeofencingError
        with self.assertRaises(IPGeofencingError):
            check_ip_geofencing('192.168.1.1')

    @patch('requests.get')
    def test_geolocation_service_failure(self, mock_get):
        """Test graceful handling when geolocation service fails."""
        mock_get.side_effect = Exception("Service unavailable")

        from src.web_app import check_ip_geofencing
        # Should not raise exception (graceful degradation)
        check_ip_geofencing('192.168.1.1')


import io
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch
import wave

from src import web_app as web_app_module
from werkzeug.exceptions import BadRequest


class TestXVideoURL(unittest.TestCase):
    def setUp(self):
        self.assertTrue(web_app_module.YT_DLP_AVAILABLE)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory(
            dir=os.environ.get("PR1338_QUALIFICATION_TMP")))
        self.paths = []
        self.url = "https://x.com/offline/status/1"
        self.wav = self._wav_bytes()
        self.child = MagicMock(returncode=0)
        self.child.communicate.return_value = (self.wav, None)
        self.ydl_type = web_app_module.yt_dlp.YoutubeDL
        self._guard_effects()
        self._install_adapter_boundaries()

    @staticmethod
    def _wav_bytes():
        data = io.BytesIO()
        with wave.open(data, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(44100)
            audio.writeframes(b"\0\0" * 1000)
        return data.getvalue()

    def _guard_effects(self):
        def denied(*args, **kwargs):
            raise AssertionError("External effect attempted in offline adapter case")
        for name in ("connect", "connect_ex", "bind", "listen"):
            self.stack.enter_context(patch.object(socket.socket, name, side_effect=denied))
        for name in ("create_connection", "getaddrinfo"):
            self.stack.enter_context(patch.object(socket, name, side_effect=denied))
        self.stack.enter_context(patch("requests.sessions.Session.request", side_effect=denied))
        for name in ("get_ethereum_logger", "log_to_ethereum_testnet", "get_acoustic_processor"):
            self.stack.enter_context(patch.object(web_app_module, name, side_effect=denied))

    def _install_adapter_boundaries(self):
        real_temp = tempfile.NamedTemporaryFile
        def temporary_video(**kwargs):
            result = real_temp(dir=self.temp, **kwargs)
            self.paths.append(Path(result.name))
            return result
        self.stack.enter_context(patch.object(tempfile, "NamedTemporaryFile", side_effect=temporary_video))
        self.extract = self.stack.enter_context(patch.object(
            self.ydl_type, "extract_info", autospec=True,
            return_value={"formats": [{"format_id": "offline"}]}))
        self.download = self.stack.enter_context(patch.object(
            self.ydl_type, "download", autospec=True, side_effect=self._download))
        self.constructor = self.stack.enter_context(patch.object(
            web_app_module.yt_dlp, "YoutubeDL", wraps=self.ydl_type))
        self.popen = self.stack.enter_context(patch.object(
            subprocess, "Popen", side_effect=self._ffmpeg))

    def _download(self, downloader, urls):
        self.assertIsInstance(downloader, self.ydl_type)
        self.assertEqual(urls, [self.url])
        target = Path(downloader.params["outtmpl"]["default"]
                      if isinstance(downloader.params["outtmpl"], dict)
                      else downloader.params["outtmpl"])
        self.assertIn(target, self.paths)
        self.assertTrue(target.exists())
        target.write_bytes(b"offline media placeholder")
        return 0

    def _ffmpeg(self, command, **kwargs):
        self.assertEqual(command, ["ffmpeg", "-i", str(self.paths[-1]),
                                  "-f", "wav", "-t", "3", "-ac", "1",
                                  "-ar", "44100", "pipe:1"])
        self.assertEqual(kwargs, {"stdin": subprocess.PIPE, "stdout": subprocess.PIPE,
                                  "stderr": subprocess.DEVNULL})
        self.assertTrue(self.paths[-1].exists())
        return self.child

    def _assert_files_removed(self):
        self.assertTrue(all(not path.exists() for path in self.paths))
        self.assertEqual(list(Path(self.temp).iterdir()), [])

    def test_x_video_real_constructors_and_audio_contract(self):
        result = web_app_module.process_x_video_url(self.url)
        self.assertEqual(result, self.wav)
        with wave.open(io.BytesIO(result), "rb") as audio:
            self.assertEqual((audio.getnchannels(), audio.getframerate()), (1, 44100))
        self.assertEqual(self.constructor.call_count, 2)
        first = self.extract.call_args
        self.assertIsInstance(first.args[0], self.ydl_type)
        self.assertEqual(first.args[1:], (self.url,))
        self.assertEqual(first.kwargs, {"download": False})
        for call in self.constructor.call_args_list:
            self.assertEqual(call.args[0]["format"], "best[height<=720]")
            self.assertIs(call.args[0]["extract_flat"], False)
            self.assertIs(call.args[0]["quiet"], True)
            self.assertIs(call.args[0]["no_warnings"], True)
        self.download.assert_called_once()
        self.popen.assert_called_once()
        self.child.communicate.assert_called_once_with(timeout=30)
        self.assertEqual(len(self.paths), 1)
        self._assert_files_removed()

    def test_x_video_missing_dependency_fails_before_constructor(self):
        with patch.object(web_app_module, "YT_DLP_AVAILABLE", False):
            with self.assertRaisesRegex(BadRequest, "yt-dlp not installed"):
                web_app_module.process_x_video_url(self.url)
        self.constructor.assert_not_called()
        self.popen.assert_not_called()
        self.assertEqual(self.paths, [])

    def test_x_video_missing_metadata_and_extractor_failure(self):
        for info in (None, {}, ValueError("offline extractor failure")):
            with self.subTest(info=info):
                self.extract.side_effect = info if isinstance(info, Exception) else None
                self.extract.return_value = info
                with self.assertRaisesRegex(BadRequest, "Unable to access X video"):
                    web_app_module.process_x_video_url(self.url)
        self.download.assert_not_called()
        self.popen.assert_not_called()
        self.assertEqual(self.paths, [])

    def test_x_video_download_failure_removes_temporary_file(self):
        self.download.side_effect = web_app_module.yt_dlp.utils.DownloadError("offline download failure")
        with self.assertRaisesRegex(BadRequest, "offline download failure"):
            web_app_module.process_x_video_url(self.url)
        self.assertEqual(len(self.paths), 1)
        self.popen.assert_not_called()
        self._assert_files_removed()

    def test_x_video_bad_ffmpeg_result_removes_temporary_file(self):
        for status, data in ((1, self.wav), (0, b"x" * 999)):
            with self.subTest(status=status, size=len(data)):
                self.child.returncode = status
                self.child.communicate.return_value = (data, None)
                with self.assertRaisesRegex(BadRequest, "No audio detected"):
                    web_app_module.process_x_video_url(self.url)
                self._assert_files_removed()

    def test_x_video_ffmpeg_spawn_failure_removes_temporary_file(self):
        self.popen.side_effect = FileNotFoundError("offline ffmpeg unavailable")
        with self.assertRaisesRegex(BadRequest, "offline ffmpeg unavailable"):
            web_app_module.process_x_video_url(self.url)
        self._assert_files_removed()

    def test_x_video_timeout_reports_error_and_removes_temporary_file(self):
        self.child.communicate.side_effect = subprocess.TimeoutExpired("ffmpeg", 30)
        with self.assertRaisesRegex(BadRequest, "Audio extraction timeout"):
            web_app_module.process_x_video_url(self.url)
        self.child.communicate.assert_called_once_with(timeout=30)
        self._assert_files_removed()


import sys


def _gunicorn_fixture_application(root, temporary, omit_factory=False):
    """Load the checked-in config, replacing only provisioned-host fixture fields."""
    import hashlib
    import json
    import os
    import sys
    from pathlib import Path
    from gunicorn.app.wsgiapp import WSGIApplication
    root, temporary = Path(root), Path(temporary)
    config = root / 'modules/platform_integration/acoustic_lab/scripts/gunicorn.conf.py'
    overrides = dict(user=os.getuid(), group=os.getgid(), workers=1,
                     bind='127.0.0.1:0', accesslog='-', errorlog='-',
                     pidfile=str(temporary / 'gunicorn.pid'), tmp_upload_dir=str(temporary),
                     worker_tmp_dir=str(temporary), pythonpath=str(root),
                     raw_env=['NODE_ENV=production', 'PYTHONPATH=' + str(root),
                              'HOME=' + str(temporary)])
    class FixtureApplication(WSGIApplication):
        def get_config_from_filename(self, filename):
            assert Path(filename).resolve() == config.resolve()
            values = super().get_config_from_filename(filename)
            fields = ('wsgi_app', 'user', 'group', 'worker_class', 'preload_app',
                      'daemon', 'timeout', 'graceful_timeout', 'max_requests',
                      'max_requests_jitter')
            evidence = dict(config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
                            factory_sha256=hashlib.sha256((config.parent.parent / 'src/web_app.py').read_bytes()).hexdigest(),
                            source={key: values.get(key) for key in fields},
                            fixture_overrides=overrides, omit_factory_control=omit_factory)
            (temporary / 'config.json').write_text(json.dumps(evidence, indent=2))
            values.update(overrides)
            if omit_factory:
                values.pop('wsgi_app', None)
            return values
    old_argv = sys.argv
    try:
        sys.argv = ['gunicorn', '--config', str(config)]  # No positional APP.
        return FixtureApplication()
    finally:
        sys.argv = old_argv


def _gunicorn_guard_denial(kind, command, probes):
    """Reject effects; allow each provenance-bound denied capability probe once."""
    import os
    import sys
    frames, frame = set(), sys._getframe(1)
    while frame is not None:
        frames.add((frame.f_globals.get('__name__'), frame.f_code.co_name))
        frame = frame.f_back
    probe = None
    if (kind == 'bind' and command == ('::1', 0)
            and ('urllib3.util.connection', '_has_ipv6') in frames):
        probe = 'urllib3-ipv6-capability'
    if (kind == 'process' and command == 'lscpu'
            and ('numpy.testing._private.utils', 'check_support_sve') in frames):
        probe = 'numpy-sve-capability'
    accepted = probe is not None and probe not in probes
    probes.add(probe)
    os.write(2, ('PR1354_GUARD ' + (probe if accepted else 'UNEXPECTED') + '\n').encode())
    raise PermissionError('Offline Gunicorn fixture denied ' + kind)


def _gunicorn_child_guards():
    """Python API boundaries only; one Gunicorn-owned fork/listener is enabled."""
    import os
    import socket
    import subprocess
    import sys
    original_bind, original_listen, original_fork = socket.socket.bind, socket.socket.listen, os.fork
    probes, owned = set(), {}
    denied = lambda kind, command=None: _gunicorn_guard_denial(kind, command, probes)
    def is_socket_owner(frame, method):
        module = sys.modules.get('gunicorn.sock')
        return module is not None and frame.f_code is getattr(module.BaseSocket, method).__code__
    def bind(sock, address):
        if (address != ('127.0.0.1', 0) or owned
                or not is_socket_owner(sys._getframe(1), 'bind')):
            return denied('bind', address)
        result = original_bind(sock, address)
        owned.update(socket=sock, listening=False, forked=False)
        os.write(2, b'PR1354_OWNED bind\n')
        return result
    def listen(sock, backlog):
        if (owned.get('socket') is not sock or owned.get('listening')
                or not is_socket_owner(sys._getframe(1), 'set_options')):
            return denied('listen')
        result = original_listen(sock, backlog)
        owned['listening'] = True
        os.write(2, b'PR1354_OWNED listen\n')
        return result
    def fork():
        frame = sys._getframe(1)
        if (not owned.get('listening') or owned.get('forked')
                or (frame.f_globals.get('__name__'), frame.f_code.co_name) != ('gunicorn.arbiter', 'spawn_worker')):
            return denied('fork')
        owned['forked'] = True
        return original_fork()
    socket.socket.bind, socket.socket.listen, os.fork = bind, listen, fork
    for name in ('connect', 'connect_ex', 'sendto', 'sendmsg'):
        if hasattr(socket.socket, name):
            setattr(socket.socket, name, lambda *a, **k: denied('outbound socket'))
    for name in ('getaddrinfo', 'create_connection', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr', 'getnameinfo'):
        setattr(socket, name, lambda *a, **k: denied('DNS/outbound connection'))
    subprocess.Popen.__init__ = lambda self, command, *a, **k: denied('process', command)
    for name in dir(os):
        if name in ('system', 'popen', 'forkpty') or name.startswith(('exec', 'spawn', 'posix_spawn')):
            if callable(getattr(os, name)):
                setattr(os, name, lambda *a, **k: denied('OS process'))


def _run_gunicorn_fixture(root, temporary):
    _gunicorn_child_guards()
    application = _gunicorn_fixture_application(root, temporary)
    assert application.cfg.wsgi_app == 'modules.platform_integration.acoustic_lab.src.web_app:create_app()'
    application.run()


@unittest.skipUnless(sys.platform.startswith('linux'), 'Gunicorn requires the explicit hosted Linux gate')
class TestGunicorn(unittest.TestCase):
    """Actual installed parser and bounded foreground server; no deployment."""
    def setUp(self):
        self.root = Path(__file__).resolve().parents[4]
        temporary = tempfile.TemporaryDirectory(dir=os.environ.get('RUNNER_TEMP'))
        self.addCleanup(temporary.cleanup)
        self.temporary = Path(temporary.name)

    def test_config_factory_and_production_defaults(self):
        import gunicorn
        self.assertEqual(gunicorn.__version__, '22.0.0')
        application = _gunicorn_fixture_application(self.root, self.temporary)
        cfg = application.cfg
        self.assertEqual(cfg.wsgi_app, 'modules.platform_integration.acoustic_lab.src.web_app:create_app()')
        retained = dict(worker_class='sync', preload_app=True, daemon=False, timeout=60,
                        graceful_timeout=30, max_requests=500, max_requests_jitter=50)
        strict = dict(tolerate_dangerous_framing=False, strip_header_spaces=False,
                      permit_unconventional_http_method=False, permit_unconventional_http_version=False,
                      casefold_http_method=False, header_map='drop')
        for name, expected in {**retained, **strict}.items():
            self.assertEqual(cfg.settings[name].value, expected, name)
        self.assertEqual(application.app_uri, cfg.wsgi_app)

    def test_original_missing_factory_binding_is_rejected(self):
        import contextlib
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit) as stopped:
            _gunicorn_fixture_application(self.root, self.temporary, omit_factory=True)
        self.assertEqual(stopped.exception.code, 1)
        self.assertIn('No application module specified', output.getvalue())

    def test_deployment_uses_module_requirements(self):
        module = self.root / 'modules/platform_integration/acoustic_lab'
        expected = 'pip install -r modules/platform_integration/acoustic_lab/requirements.txt'
        for path in ('scripts/deploy.sh', 'DEPLOYMENT.md'):
            self.assertIn(expected, (module / path).read_text())
        self.assertIn('--config modules/platform_integration/acoustic_lab/scripts/gunicorn.conf.py',
                      (module / 'scripts/acoustic-lab.service').read_text())

    @staticmethod
    def _parse(raw):
        from gunicorn.config import Config
        from gunicorn.http.parser import RequestParser
        return next(RequestParser(Config(), [raw], ('127.0.0.1', 12345)))

    def test_parser_accepts_valid_requests(self):
        requests = [(b'GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n', b''),
                    (b'POST /offline HTTP/1.1\r\nHost: localhost\r\nContent-Length: 3\r\n\r\nabc', b'abc'),
                    (b'POST /offline HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n0\r\n\r\n', b'abc')]
        for raw, body in requests:
            with self.subTest(raw=raw.split(b'\r\n', 1)[0]):
                self.assertEqual(self._parse(raw).body.read(), body)

    def test_parser_rejects_ambiguous_framing(self):
        from gunicorn.http.errors import InvalidHeader
        # Exercise the shared parser API before importing target-only errors.
        with self.assertRaises(InvalidHeader):
            self._parse(b'POST /offline HTTP/1.1\r\nHost: localhost\r\n'
                        b'Transfer-Encoding: chunked\r\nContent-Length: 4\r\n\r\n0\r\n\r\n')
        from gunicorn.http.errors import UnsupportedTransferCoding
        cases = [(b'Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked', InvalidHeader),
                 (b'Transfer-Encoding: gzip', UnsupportedTransferCoding),
                 (b'Transfer-Encoding: ', UnsupportedTransferCoding)]
        for headers, error in cases:
            with self.subTest(headers=headers):
                raw = b'POST /offline HTTP/1.1\r\nHost: localhost\r\n' + headers + b'\r\n\r\n0\r\n\r\n'
                with self.assertRaises(error):
                    self._parse(raw)
        with self.assertRaises(InvalidHeader):
            self._parse(b'POST /offline HTTP/1.0\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n')

    @staticmethod
    def _owned_pids(group):
        members = []
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                fields = path.read_text().rsplit(')', 1)[1].split()
                if int(fields[2]) == group:
                    members.append(int(path.parent.name))
            except (OSError, ProcessLookupError):
                pass
        return members

    def _close_owned_server(self, child, log):
        import json
        import signal
        import time
        observed = self._owned_pids(child.pid)
        forced_kill = False
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=8)
        except subprocess.TimeoutExpired:
            forced_kill = True
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
        survivors = self._wait_owned_exit(child.pid)
        if survivors:
            forced_kill = True
            os.killpg(child.pid, signal.SIGKILL)
            survivors = self._wait_owned_exit(child.pid)
        report = dict(master=child.pid, observed_owned_pids=observed,
                      worker_pids=self.worker_pids, survivors=survivors, returncode=child.returncode,
                      forced_kill=forced_kill)
        destination = Path(os.environ.get('ACOUSTIC_GUNICORN_REPORT_DIR', str(self.temporary)))
        destination.mkdir(parents=True, exist_ok=True)
        (destination / 'gunicorn-closure.json').write_text(json.dumps(report, indent=2))
        (destination / 'gunicorn.log').write_text(log.read_text())
        if (self.temporary / 'config.json').exists():
            (destination / 'gunicorn-config.json').write_text((self.temporary / 'config.json').read_text())
        self.assertEqual(survivors, [], 'Owned Gunicorn process group still exists')
        self.assertFalse(forced_kill, 'Normal foreground shutdown required forced kill')
        self.assertEqual(child.returncode, 0)
        self.assertNotIn('PR1354_GUARD UNEXPECTED', log.read_text())
        self.assertEqual(log.read_text().count('PR1354_OWNED bind\n'), 1)
        self.assertEqual(log.read_text().count('PR1354_OWNED listen\n'), 1)

    def _wait_owned_exit(self, group):
        import time
        deadline = time.monotonic() + 3
        while self._owned_pids(group) and time.monotonic() < deadline:
            time.sleep(0.05)
        return self._owned_pids(group)

    def _start_server(self):
        import inspect
        import re
        import time
        helpers = (_gunicorn_fixture_application, _gunicorn_guard_denial,
                   _gunicorn_child_guards, _run_gunicorn_fixture)
        program = '\n'.join(inspect.getsource(fn) for fn in helpers)
        program += '\nimport sys\n_run_gunicorn_fixture(*sys.argv[1:])\n'
        env = dict(PATH=str(Path(sys.executable).parent) + ':/usr/bin:/bin', HOME=str(self.temporary),
                   TMPDIR=str(self.temporary), LANG='C.UTF-8', PYTHONDONTWRITEBYTECODE='1',
                   PYTHON_DOTENV_DISABLED='1', PYCRYPTODOME_DISABLE_GMP='1',
                   NUMBA_CACHE_DIR=str(self.temporary / 'numba'))
        log = self.temporary / 'server.log'
        output = log.open('wb')
        self.addCleanup(output.close)
        child = subprocess.Popen([sys.executable, '-I', '-B', '-c', program, str(self.root), str(self.temporary)],
                                 cwd=self.root, env=env, stdout=output, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        self.worker_pids = []
        self.addCleanup(self._close_owned_server, child, log)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            text = log.read_text()
            address = re.search(r'Listening at: http://127\.0\.0\.1:(\d+)', text)
            self.worker_pids = [int(pid) for pid in re.findall(r'Booting worker with pid: (\d+)', text)]
            if address and self.worker_pids:
                return child, int(address.group(1))
            self.assertIsNone(child.poll(), text)
            time.sleep(0.05)
        self.fail('Gunicorn did not report a bound loopback endpoint and worker within 45 seconds')

    @staticmethod
    def _exchange(port, payload):
        result = bytearray()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(5)
            connection.connect(('127.0.0.1', port))
            connection.sendall(payload)
            while len(result) < 65536:
                part = connection.recv(4096)
                if not part:
                    return bytes(result)
                result.extend(part)
        raise AssertionError('Loopback response did not close within its size bound')

    def test_foreground_health_rejection_and_owned_shutdown(self):
        import json
        child, port = self._start_server()
        self.assertEqual(len(self.worker_pids), 1)
        self.assertEqual(os.getpgid(self.worker_pids[0]), child.pid)
        for path in ('/health', '/'):
            response = self._exchange(port, ('GET ' + path + ' HTTP/1.0\r\nHost: localhost\r\n\r\n').encode())
            self.assertIn(b'200 OK', response.split(b'\r\n', 1)[0])
            if path == '/health':
                self.assertEqual(json.loads(response.split(b'\r\n\r\n', 1)[1])['status'], 'healthy')
        payload = (b'POST /offline HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n'
                   b'Content-Length: 4\r\n\r\n0\r\n\r\nGET /health HTTP/1.1\r\nHost: localhost\r\n\r\n')
        response = self._exchange(port, payload)
        self.assertIn(b'400 Bad Request', response.split(b'\r\n', 1)[0])
        self.assertNotIn(b'200 OK', response)
        self.assertEqual(response.count(b'HTTP/'), 1)


if __name__ == '__main__':
    unittest.main()
