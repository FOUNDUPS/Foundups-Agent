"""Local Kids Episodes editor. Run this file with --workspace /path/to/media.

Only loopback is bound. Media inputs must resolve inside the selected workspace;
only outputs created in this process are downloadable. No generation or upload
credentials are used. This is a single-operator development editor, not hosting.
"""
from __future__ import annotations

import argparse
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import importlib.util
import json
from pathlib import Path
import shutil
import uuid

MAX_BODY = 64 * 1024
HTML_PATH = Path(__file__).resolve().parents[1] / "assets" / "kids_editor.html"


def _renderer():
    spec = importlib.util.spec_from_file_location("kids_episode_local", Path(__file__).with_name("kids_episode.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_episode


def contained_file(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("Each media asset needs a local file path.")
    path = (root / value).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Media must be files inside the selected workspace.")
    if path.suffix.lower() not in {".mp4", ".webm", ".mov", ".mkv", ".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
        raise ValueError("Unsupported media file extension.")
    return path


def confine_inputs(spec: dict, root: Path) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("Episode must be a JSON object.")
    result = copy.deepcopy(spec)
    clips = result.get("clips", [])
    if not isinstance(clips, list) or len(clips) > 30:
        raise ValueError("Use at most 30 clips.")
    assets = list(clips)
    for name in ("music", "voice"):
        if result.get(name) is not None:
            assets.append(result[name])
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("Media entries must be objects.")
        asset["path"] = str(contained_file(root, asset.get("path")))
    return result


class EditorServer(HTTPServer):
    def __init__(self, workspace: Path, port: int = 8767, render=None):
        self.workspace = workspace.resolve(strict=True)
        if not self.workspace.is_dir():
            raise ValueError("Workspace must be a directory.")
        self.render = render or _renderer()
        self.artifacts = {}
        super().__init__(("127.0.0.1", port), EditorHandler)

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server_port}"


class EditorHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_args):
        pass

    def send_bytes(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; media-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, payload):
        self.send_bytes(code, json.dumps(payload).encode(), "application/json")

    def valid_host(self):
        return self.headers.get("Host") == self.server.origin.removeprefix("http://")

    def do_GET(self):
        if not self.valid_host():
            self.send_json(403, {"error": "Use the printed loopback address."})
            return
        if self.path == "/":
            self.send_bytes(200, HTML_PATH.read_bytes(), "text/html; charset=utf-8")
            return
        path = self.server.artifacts.get(self.path)
        if path is None or not path.is_file() or not path.resolve().is_relative_to(self.server.workspace):
            self.send_json(404, {"error": "Artifact not found."})
            return
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4" if path.suffix == ".mp4" else "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        with path.open("rb") as source:
            shutil.copyfileobj(source, self.wfile)

    def do_POST(self):
        if not self.valid_host() or self.headers.get("Origin") != self.server.origin:
            self.send_json(403, {"error": "Rendering requires the editor's own origin."})
            return
        if self.path != "/render":
            self.send_json(404, {"error": "Unknown action."})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.send_json(415, {"error": "Send application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BODY or self.headers.get("Transfer-Encoding"):
            self.send_json(413, {"error": "Episode JSON must be under 64 KiB."})
            return
        job_dir = None
        try:
            spec = confine_inputs(json.loads(self.rfile.read(length)), self.server.workspace)
            output_root = self.server.workspace / ".kids-renders"
            output_root.mkdir(exist_ok=True)
            if output_root.is_symlink() or not output_root.resolve().is_relative_to(self.server.workspace):
                raise ValueError("Output directory must stay inside the workspace.")
            job_id = uuid.uuid4().hex
            job_dir = output_root / job_id
            job_dir.mkdir()
            (job_dir / "episode.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
            result = self.server.render(spec, job_dir / "episode.mp4", base_dir=self.server.workspace)
            urls = {}
            for key, suffix in (("video_path", "mp4"), ("captions_path", "srt")):
                artifact = Path(result[key]).resolve(strict=True)
                if not artifact.is_relative_to(job_dir.resolve()) or not artifact.is_file():
                    raise ValueError("Renderer returned an invalid artifact.")
                url = f"/artifacts/{job_id}.{suffix}"
                self.server.artifacts[url] = artifact
                urls[key] = url
            self.send_json(200, urls)
        except (ValueError, TypeError, KeyError, OSError) as exc:
            self.send_json(400, {"error": str(exc)[:500]})
        except Exception:
            self.send_json(500, {"error": "Render failed. Check media files and FFmpeg availability."})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="Directory containing your video and audio assets")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    with EditorServer(args.workspace, args.port) as server:
        print(f"Kids Episodes editor: {server.origin}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
