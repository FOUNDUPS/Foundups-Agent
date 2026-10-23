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


if __name__ == '__main__':
    unittest.main()
