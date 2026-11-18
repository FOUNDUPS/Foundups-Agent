"""HTTP and filesystem boundary checks for the local episode editor."""
import importlib.util
import json
from http.client import HTTPConnection
from pathlib import Path
import threading

import pytest

MODULE = Path(__file__).parents[1] / "src" / "kids_editor_server.py"
spec = importlib.util.spec_from_file_location("kids_editor_server_test", MODULE)
editor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor)


@pytest.fixture
def running(tmp_path):
    calls = []
    (tmp_path / "clip.mp4").write_bytes(b"source")
    def render(payload, target, *, base_dir):
        calls.append(payload)
        target.write_bytes(b"rendered")
        target.with_suffix(".srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
        return {"video_path": str(target), "captions_path": str(target.with_suffix(".srt"))}
    server = editor.EditorServer(tmp_path, 0, render)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, calls, tmp_path
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def request(server, path="/render", *, payload=None, origin=True, host=None, method="POST", length=None):
    connection = HTTPConnection("127.0.0.1", server.server_port)
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = server.origin if origin is True else origin
    if host:
        headers["Host"] = host
    if length:
        headers["Content-Length"] = str(length)
    connection.request(method, path, json.dumps(payload or {"clips": [{"path": "clip.mp4"}]}), headers)
    response = connection.getresponse()
    status, body = response.status, response.read()
    connection.close()
    return status, body


def test_render_returns_only_created_artifacts(running):
    server, calls, root = running
    status, body = request(server)
    assert status == 200
    assert calls[0]["clips"][0]["path"] == str(root / "clip.mp4")
    urls = json.loads(body)
    assert request(server, urls["video_path"], method="GET")[1] == b"rendered"
    assert request(server, "/clip.mp4", method="GET")[0] == 404
    assert request(server, "/artifacts/../../clip.mp4", method="GET")[0] == 404


@pytest.mark.parametrize("origin", [False, "https://attacker.example", "null"])
def test_foreign_or_missing_origin_cannot_render(running, origin):
    server, calls, _ = running
    assert request(server, origin=origin)[0] == 403
    assert not calls


def test_dns_rebinding_host_rejected(running):
    server, calls, _ = running
    assert request(server, host="attacker.example")[0] == 403
    assert request(server, host="attacker.example", method="GET", path="/")[0] == 403
    assert not calls


def test_oversized_body_rejected_before_read(running):
    server, calls, _ = running
    assert request(server, length=editor.MAX_BODY + 1)[0] == 413
    assert not calls


def test_path_escape_and_symlink_rejected(running, tmp_path):
    server, calls, root = running
    outside = root.parent / "outside-kids.mp4"
    outside.write_bytes(b"outside")
    for value in (str(outside), "../outside-kids.mp4"):
        assert request(server, payload={"clips": [{"path": value}]})[0] == 400
    (root / "escape.mp4").symlink_to(outside)
    assert request(server, payload={"clips": [{"path": "escape.mp4"}]})[0] == 400
    assert not calls


def test_output_symlink_rejected(running):
    server, calls, root = running
    (root / ".kids-renders").symlink_to(root.parent, target_is_directory=True)
    assert request(server)[0] == 400
    assert not calls


def test_html_is_available(running):
    server, _, _ = running
    status, body = request(server, path="/", method="GET")
    assert status == 200
    assert b"Render 15-second episode" in body
