"""Offline uploader/DAE definitions with fake media, service and generators."""
import ast
import hashlib
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import threading
import time
from types import ModuleType, SimpleNamespace
from typing import Dict, List, Optional

import pytest

from modules.communication.livechat.src import operator_command_queue as queue

CHANNEL = "UC" + "a" * 22
VIDEO = "a" * 11
ROOT = Path(__file__).parents[1] / "src"


@pytest.fixture
def upload_owner(tmp_path, monkeypatch):
    google = ModuleType("googleapiclient")
    google.__path__ = []
    media = ModuleType("googleapiclient.http")
    class Media:
        def __init__(self, path, **_kwargs): self.source = Path(path).open("rb")
        def stream(self): return self.source
    media.MediaFileUpload = Media
    monkeypatch.setitem(sys.modules, google.__name__, google)
    monkeypatch.setitem(sys.modules, media.__name__, media)
    spec = importlib.util.spec_from_file_location("offline_policy_publisher", ROOT / "youtube_uploader.py")
    owner = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, owner)
    spec.loader.exec_module(owner)
    private = queue.OperatorCommandQueue(None, tmp_path / "inbox.json", tmp_path / "ack.json", tmp_path / "state.json")
    for name in ("get_video_policy", "claim_video_policy_upload", "record_video_policy_observation"):
        monkeypatch.setattr(queue, name, getattr(private, name))
    monkeypatch.setenv("YT_UPLOAD_CHANNEL_ID_FOUNDUPS", CHANNEL)
    calls = {"insert": 0, "generation": 0}
    def insert(**_kwargs):
        calls["insert"] += 1
        return SimpleNamespace(next_chunk=lambda: (None, {"id": VIDEO}))
    service = SimpleNamespace(
        channels=lambda: SimpleNamespace(list=lambda **_: SimpleNamespace(execute=lambda: {"items": [{"id": CHANNEL, "snippet": {"title": "Test"}}]})),
        videos=lambda: SimpleNamespace(insert=insert))
    uploader = owner.YouTubeShortsUploader("foundups", youtube_service=service)
    path = tmp_path / "owned.mp4"
    path.write_bytes(b"synthetic-media")
    return owner, uploader, path, calls, private


def definition(name, filename, extra):
    """Compile the complete production class; SDK/constructor collaborators stay fake."""
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    namespace = {"time": time, "threading": threading, "List": List, "Optional": Optional,
                 "Dict": Dict, **extra}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / filename), "exec"), namespace)
    return namespace[name]


def test_short_upload_claim_precedes_insert_and_repeat_survives_new_uploader(upload_owner):
    owner, uploader, path, calls, private = upload_owner
    assert uploader.upload_short(str(path), "Title", "Body") == f"https://youtube.com/shorts/{VIDEO}"
    claims = private._read_json(private.state_path, {})["video_effect_claims"]
    assert claims[-1]["outcome"] == "unknown"
    restarted = owner.YouTubeShortsUploader("foundups", youtube_service=uploader.youtube)
    with pytest.raises(owner.YouTubeUploadPolicyBlocked, match="already claimed"):
        restarted.upload_short(str(path), "Different draft", "Changed body")
    assert calls["insert"] == 1


@pytest.mark.parametrize("problem", ["pause", "unknown_identity", "unavailable", "stop", "disabled"])
def test_final_upload_gate_blocks_public_api(upload_owner, monkeypatch, tmp_path, problem):
    owner, uploader, path, calls, private = upload_owner
    if problem == "pause":
        monkeypatch.setattr(queue, "get_video_policy", lambda *_a, **_k: {"available": True, "shorts_enabled": False})
    if problem == "unknown_identity": uploader.channel_info = {}
    if problem == "unavailable":
        monkeypatch.setattr(queue, "get_video_policy", lambda *_a, **_k: {"available": False, "blocked": True})
    if problem == "stop":
        stop = tmp_path / "STOP"; stop.write_text("stop", encoding="utf-8")
        monkeypatch.setenv("YT_AUTOMATION_STOP_FILE", str(stop))
    if problem == "disabled": monkeypatch.setenv("YT_AUTOMATION_ENABLED", "false")
    with pytest.raises(owner.YouTubeUploadPolicyBlocked): uploader.upload_short(str(path), "Title", "Body")
    assert calls["insert"] == 0
    assert not private._read_json(private.state_path, {}).get("video_effect_claims")


def test_unknown_backend_outcome_retains_claim_and_never_retries(upload_owner):
    owner, uploader, path, calls, private = upload_owner
    def lost(**_kwargs):
        calls["insert"] += 1
        raise RuntimeError("synthetic response lost")
    uploader.youtube.videos = lambda: SimpleNamespace(insert=lost)
    with pytest.raises(owner.YouTubeUploadOutcomeUnknown): uploader.upload_short(str(path), "Title", "Body")
    with pytest.raises(owner.YouTubeUploadPolicyBlocked): uploader.upload_short(str(path), "Title", "Body")
    assert calls["insert"] == 1


def test_pause_during_generation_stops_inside_orchestrator_before_upload(upload_owner, monkeypatch):
    owner, uploader, path, calls, private = upload_owner
    errors = {name: type(name, (Exception,), {}) for name in ("Veo3GenerationError", "Sora2GenerationError", "InsufficientCreditsError")}
    cls = definition("ShortsOrchestrator", "shorts_orchestrator.py", {**errors, "YouTubeUploadError": owner.YouTubeUploadError,
                     "YouTubeUploadPolicyBlocked": owner.YouTubeUploadPolicyBlocked})
    orchestrator = object.__new__(cls)
    orchestrator.uploader = uploader
    orchestrator._select_engine = lambda *_: "veo3"
    def generated(**_kwargs):
        calls["generation"] += 1
        monkeypatch.setattr(queue, "get_video_policy", lambda *_a, **_k: {"available": True, "shorts_enabled": False})
        return str(path)
    orchestrator._get_generator = lambda *_: SimpleNamespace(generate_video=generated)
    with pytest.raises(owner.YouTubeUploadPolicyBlocked):
        orchestrator.create_and_upload("Specific topic", enhance_prompt=False, use_3act=False)
    assert calls == {"insert": 0, "generation": 1}


def test_dae_scoped_topics_and_interval_do_not_reset_topic_index(upload_owner, monkeypatch):
    owner, uploader, path, calls, private = upload_owner
    cls = definition("ShortsDAE", "shorts_dae.py", {"YouTubeUploadPolicyBlocked": owner.YouTubeUploadPolicyBlocked,
                     "YouTubeUploadOutcomeUnknown": owner.YouTubeUploadOutcomeUnknown})
    dae = object.__new__(cls)
    dae.active, dae.topic_queue, dae.current_topic_index = True, ["Legacy topic"], 1
    now, topics, waits = [0], [], []
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    policies = {"topics": ["Scoped one", "Scoped two"], "interval_minutes": 1, "fingerprint": "f" * 64}
    uploader.get_shorts_policy = lambda: deepcopy(policies)
    def create(**kwargs):
        assert kwargs["policy_fingerprint"] == "f" * 64
        topics.append(kwargs["topic"])
        if len(topics) == 2: dae.active = False
        return "accepted"
    def wait(seconds):
        waits.append(seconds)
        now[0] += seconds
    dae._stop_event = SimpleNamespace(wait=wait)
    dae.orchestrator = SimpleNamespace(uploader=uploader, create_and_upload=create)
    dae._autonomous_loop(24, 30, "public")
    assert topics == ["Scoped two", "Scoped one"]
    assert dae.current_topic_index == 3
    assert sum(waits) == 60 and max(waits) <= 5


def test_dae_unknown_upload_stops_without_hourly_retry(upload_owner):
    owner, uploader, path, calls, private = upload_owner
    cls = definition("ShortsDAE", "shorts_dae.py", {"YouTubeUploadPolicyBlocked": owner.YouTubeUploadPolicyBlocked,
                     "YouTubeUploadOutcomeUnknown": owner.YouTubeUploadOutcomeUnknown})
    dae = object.__new__(cls)
    dae.active, dae.topic_queue, dae.current_topic_index = True, ["Topic"], 0
    waits = []
    dae._stop_event = SimpleNamespace(wait=waits.append)
    def uncertain(**_kwargs): raise owner.YouTubeUploadOutcomeUnknown("synthetic")
    dae.orchestrator = SimpleNamespace(uploader=uploader, create_and_upload=uncertain)
    dae._autonomous_loop(24, 30, "public")
    assert dae.active is False and not waits and dae.current_topic_index == 0


@pytest.mark.parametrize("change", ["changed_topics", "expired"])
def test_generation_snapshot_change_retains_artifact_without_upload(upload_owner, monkeypatch, change):
    owner, uploader, path, calls, private = upload_owner
    errors = {name: type(name, (Exception,), {}) for name in ("Veo3GenerationError", "Sora2GenerationError", "InsufficientCreditsError")}
    cls = definition("ShortsOrchestrator", "shorts_orchestrator.py", {**errors, "YouTubeUploadError": owner.YouTubeUploadError,
                     "YouTubeUploadPolicyBlocked": owner.YouTubeUploadPolicyBlocked})
    orchestrator = object.__new__(cls)
    orchestrator.uploader = uploader
    orchestrator._select_engine = lambda *_: "veo3"
    initial = uploader.get_shorts_policy()
    def generated(**_kwargs):
        calls["generation"] += 1
        fresh = {**initial, "fingerprint": "b" * 64}
        if change == "changed_topics": fresh["topics"] = ["Different topic"]
        monkeypatch.setattr(queue, "get_video_policy", lambda *_a, **_k: fresh)
        return str(path)
    orchestrator._get_generator = lambda *_: SimpleNamespace(generate_video=generated)
    with pytest.raises(owner.YouTubeUploadPolicyBlocked, match="directive changed"):
        orchestrator.create_and_upload("Initial topic", enhance_prompt=False, use_3act=False)
    assert path.is_file() and calls == {"insert": 0, "generation": 1}
    assert not private._read_json(private.state_path, {}).get("video_effect_claims")


def test_upload_hash_binds_retained_media_descriptor_not_replaced_path(upload_owner, tmp_path, monkeypatch):
    owner, uploader, path, calls, private = upload_owner
    retained = tmp_path / "retained.mp4"
    retained.write_bytes(b"retained-stream-A")
    stream = retained.open("rb")
    monkeypatch.setattr(owner, "MediaFileUpload", lambda *_a, **_k: SimpleNamespace(stream=lambda: stream))
    try:
        uploader.upload_short(str(path), "Title", "Body")
        claim = private._read_json(private.state_path, {})["video_effect_claims"][-1]
        assert claim["content_sha256"] == hashlib.sha256(b"retained-stream-A").hexdigest()
        assert claim["content_sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()
        assert stream.tell() == 0 and calls["insert"] == 1
    finally:
        stream.close()


def test_restarted_dae_waits_from_durable_unknown_upload_attempt(upload_owner, monkeypatch):
    owner, uploader, path, calls, private = upload_owner
    uploader.upload_short(str(path), "Title", "Body")
    real_policy = uploader.get_shorts_policy()
    assert isinstance(real_policy["last_upload_attempt_unix"], (int, float))
    recent = real_policy["last_upload_attempt_unix"]
    now, waits, generated = [recent + 1], [], []
    monkeypatch.setattr(time, "time", lambda: now[0])
    uploader.get_shorts_policy = lambda: {**real_policy, "interval_minutes": 1}
    cls = definition("ShortsDAE", "shorts_dae.py", {"YouTubeUploadPolicyBlocked": owner.YouTubeUploadPolicyBlocked,
                     "YouTubeUploadOutcomeUnknown": owner.YouTubeUploadOutcomeUnknown})
    dae = object.__new__(cls)
    dae.active, dae.topic_queue, dae.current_topic_index = True, ["Topic"], 0
    def wait(seconds): waits.append(seconds); now[0] += seconds
    def create(**_kwargs): generated.append(now[0]); dae.active = False
    dae._stop_event = SimpleNamespace(wait=wait)
    dae.orchestrator = SimpleNamespace(uploader=uploader, create_and_upload=create)
    dae._autonomous_loop(24, 30, "public")
    assert sum(waits) == 59 and generated == [recent + 60]


def test_final_media_handoff_rechecks_generation_fingerprint(upload_owner, monkeypatch):
    owner, uploader, path, calls, private = upload_owner
    initial = uploader.get_shorts_policy()
    original_media = owner.MediaFileUpload
    def prepared(*args, **kwargs):
        media = original_media(*args, **kwargs)
        monkeypatch.setattr(queue, "get_video_policy", lambda *_a, **_k: {**initial, "fingerprint": "b" * 64})
        return media
    monkeypatch.setattr(owner, "MediaFileUpload", prepared)
    with pytest.raises(owner.YouTubeUploadPolicyBlocked, match="directive changed"):
        uploader.upload_short(str(path), "Title", "Body", policy_fingerprint=initial["fingerprint"])
    assert calls["insert"] == 0
    assert not private._read_json(private.state_path, {}).get("video_effect_claims")


def test_stale_dae_selection_is_rejected_before_generation(upload_owner):
    owner, uploader, path, calls, private = upload_owner
    cls = definition("ShortsOrchestrator", "shorts_orchestrator.py", {"YouTubeUploadPolicyBlocked": owner.YouTubeUploadPolicyBlocked})
    orchestrator = object.__new__(cls)
    orchestrator.uploader = uploader
    with pytest.raises(owner.YouTubeUploadPolicyBlocked, match="before generation"):
        orchestrator.create_and_upload("Old topic", policy_fingerprint="b" * 64)
    assert calls == {"insert": 0, "generation": 0}
