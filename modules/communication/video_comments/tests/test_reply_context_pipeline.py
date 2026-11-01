"""Exact-source behavioral tests; package imports/constructors/live providers excluded.

The private loader compiles complete production definitions with denied optional
collaborators. No Selenium, profile store, model, network, or posting is started.
DOM checks run the actual extraction JavaScript against synthetic rows in Node.
"""

import ast
import asyncio
import dataclasses
import json
import logging
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import threading
import time
from enum import Enum
from functools import wraps
from threading import RLock, Event
from types import ModuleType, SimpleNamespace
import typing

import pytest


_ROOT = Path(__file__).resolve().parents[4]
_DENIED_DEPENDENCIES = []


def _deny_dependency(*args, **kwargs):
    _DENIED_DEPENDENCIES.append("unexpected dependency")
    raise AssertionError("Live dependency/constructor is forbidden in this fixture")


def _load_definitions(name, relative):
    """Compile source definitions, not import-time lifecycle or optional imports."""
    path = _ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    body = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError):
                value = node.value
                if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id == "frozenset" and len(value.args) == 1):
                    continue
                ast.literal_eval(value.args[0])
            body.append(node)
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module  # dataclass resolves its defining module here.
    module.__dict__.update(vars(typing))
    module.__dict__.update(
        asyncio=asyncio, dataclass=dataclasses.dataclass, Enum=Enum, wraps=wraps,
        RLock=RLock, Event=Event, logger=logging.getLogger(name), os=os,
        random=random, Path=Path, time=time, json=json, math=math,
        requests=SimpleNamespace(post=_deny_dependency, get=_deny_dependency),
        sqlite3=SimpleNamespace(connect=_deny_dependency),
        resolve_general_model_path=_deny_dependency,
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id.endswith("_AVAILABLE"):
            module.__dict__[node.id] = False
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), module.__dict__)
    return module


context_module = _load_definitions(
    "_reply_context_prompt", "modules/communication/video_comments/src/reply_context.py")
row_module = _load_definitions(
    "_reply_context_row", "modules/communication/video_comments/skillz/tars_like_heart_reply/src/comment_row_context.py")
generator_module = _load_definitions(
    "_reply_context_generator", "modules/communication/video_comments/src/intelligent_reply_generator.py")
processor_module = _load_definitions(
    "_reply_context_processor", "modules/communication/video_comments/skillz/tars_like_heart_reply/src/comment_processor.py")
generator_module.build_grounded_prompt = context_module.build_grounded_prompt
generator_module.select_channel_personality = context_module.select_channel_personality
generator_module.is_general_reply_model = context_module.is_general_reply_model
generator_module.parse_reply_review = context_module.parse_reply_review
generator_module.parse_comment_assessment = context_module.parse_comment_assessment
generator_module.reply_text_is_publishable = context_module.reply_text_is_publishable
processor_module.extract_row_comment_data = row_module.extract_comment_data
IntelligentReplyGenerator = generator_module.IntelligentReplyGenerator
CommentProcessor = processor_module.CommentProcessor
processor_module.INTELLIGENT_REPLIES_AVAILABLE = True
processor_module.get_reply_generator = _deny_dependency
processor_module.CommenterType = generator_module.CommenterType


@pytest.fixture(autouse=True)
def _isolate_optional_dependencies(monkeypatch):
    _DENIED_DEPENDENCIES.clear()
    monkeypatch.setattr(IntelligentReplyGenerator, "__init__", _deny_dependency)
    monkeypatch.setattr(CommentProcessor, "__init__", _deny_dependency)
    monkeypatch.setenv("YT_ENABLE_GROK_REPLIES", "false")
    monkeypatch.setenv("YT_FACTCHECK_ENABLED", "false")
    monkeypatch.setenv("USE_SKILL_ROUTER", "true")
    # The old-comment route dynamically imports this exact parser owner.
    monkeypatch.setitem(sys.modules,
        "modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_processor", processor_module)
    yield
    assert _DENIED_DEPENDENCIES == [], "Even caught dependency attempts must fail this test"


class _FakeQwen:
    def __init__(self):
        self.call = None

    def generate_response(self, **kwargs):
        self.call = kwargs
        return "That lyric lands because the video connects solidarity with action."


def _bare_generator():
    generator = object.__new__(IntelligentReplyGenerator)
    generator.lm_studio_available = False
    generator.lm_studio_model_id = None
    generator.qwen_engine = _FakeQwen()
    generator.grok_connector = None
    generator.banter_engine = None
    generator._last_llm_source = None
    generator._generation_lock = RLock()
    generator._current_content_analysis = None
    generator._load_reply_theme = lambda: None
    generator._load_personalization_context = lambda **_: "Prior topic: mutual aid"
    generator._load_voice_memory_context = (
        lambda comment_text, video_title=None: "Verified channel position: build cooperatively"
    )
    return generator


def test_local_qwen_receives_comment_video_guidance_and_memory():
    generator = _bare_generator()

    reply = generator._generate_contextual_reply(
        comment_text="This verse nails why organizing matters",
        author_name="Aki",
        custom_prompt="Treat #FFCPLN as shared music context.",
        tier=2,
        video_title="FFCPLN Song 97 - Mutual Aid",
    )

    prompt = generator.qwen_engine.call["prompt"]
    assert reply.startswith("That lyric lands")
    assert "This verse nails why organizing matters" in prompt
    assert "Treat #FFCPLN as shared music context" in prompt
    assert "FFCPLN Song 97 - Mutual Aid" in prompt
    assert "Prior topic: mutual aid" in prompt
    assert "Verified channel position: build cooperatively" in prompt
    assert generator.qwen_engine.call["stop"] == ["###"]
    assert generator.get_last_llm_source() == "qwen"


def test_voice_memory_query_includes_video_title():
    captured = {}

    class _VoiceMemory:
        def query(self, text, k):
            captured.update(text=text, k=k)
            return [{"score": 0.9, "text": "grounded fact", "source_type": "video"}]

    generator = object.__new__(IntelligentReplyGenerator)
    generator._voice_memory_enabled = True
    generator._get_voice_memory = lambda: _VoiceMemory()

    context = generator._load_voice_memory_context(
        "What did you mean by this?",
        video_title="A specific video",
    )

    assert captured == {
        "text": "A specific video\nWhat did you mean by this?",
        "k": 3,
    }
    assert "grounded fact" in context


def test_ffcpln_pattern_does_not_classify_supporter_as_troll():
    pattern = IntelligentReplyGenerator.SEMANTIC_PATTERN_PROMPTS["ffcpln"]

    assert pattern["keywords"] == ["ffcpln", "ffc pln", "#ffcpln"]
    assert "Do NOT assume the commenter is a troll" in pattern["variation_prompt"]
    assert "actual point first" in pattern["variation_prompt"]


def test_generate_reply_for_comment_forwards_video_title():
    captured = {}
    generator = object.__new__(IntelligentReplyGenerator)
    generator.generate_reply = lambda **kwargs: captured.update(kwargs) or "reply"

    reply = generator.generate_reply_for_comment(
        {
            "text": "comment",
            "author_name": "Kai",
            "channel_id": "commenter-channel",
            "video_title": "Exact Studio row title",
        },
        target_channel_id="receiving-channel",
    )

    assert reply == "reply"
    assert captured["video_title"] == "Exact Studio row title"
    assert captured["target_channel_id"] == "receiving-channel"


def test_comment_processor_forwards_row_context_and_personality(monkeypatch):
    captured = {}

    class _Generator:
        def generate_reply(self, **kwargs):
            captured.update(kwargs)
            return "contextual"

    monkeypatch.setattr(processor_module, "get_reply_generator", lambda: _Generator())
    processor = object.__new__(CommentProcessor)
    processor.video_title = "DAE-wide fallback title"
    processor.target_channel_id = "receiving-channel"

    result = processor._generate_intelligent_reply(
        {
            "text": "row comment",
            "author_name": "Mina",
            "channel_id": "commenter-channel",
            "video_title": "Per-row title",
        }
    )

    assert result == "contextual"
    assert captured["video_title"] == "Per-row title"
    assert captured["target_channel_id"] == "receiving-channel"


def test_dom_extraction_retains_per_row_video_context():
    expected = {
        "text": "comment",
        "author_name": "Mina",
        "author_handle": "@mina",
        "channel_id": "channel",
        "is_mod": False,
        "is_subscriber": True,
        "published_time": "2 hours ago",
        "video_title": "Per-row title",
        "video_id": "abc123",
        "video_url": "https://studio.youtube.com/video/abc123/comments/inbox",
    }

    class _Driver:
        def execute_script(self, script, index):
            assert "ytcp-video-thumbnail-with-info" in script
            assert index == 2
            return expected

    processor = object.__new__(CommentProcessor)
    processor.driver = _Driver()

    assert processor.extract_comment_data(3) == expected


def test_context_gate_rejects_generic_and_stale_sources():
    assert CommentProcessor.is_contextual_reply_source("skill_1:qwen")
    assert CommentProcessor.is_contextual_reply_source("lm_studio")
    assert not CommentProcessor.is_contextual_reply_source("skill_1:template_regular")
    assert not CommentProcessor.is_contextual_reply_source("skill_2:personalized_stats")
    assert not CommentProcessor.is_contextual_reply_source("unknown")


@pytest.mark.parametrize("source", [
    "skill_0:unknown", "skill_0:whack_a_maga_fallback", "not_qwen",
    "qwen:template", "skill_1:not_qwen", "gemma_emoji:unknown",
    "gemma_emoji:gemma_fallback", None, 42,
])
def test_context_gate_rejects_unproven_or_forged_labels(source):
    assert not CommentProcessor.is_contextual_reply_source(source)


def _fake_generation(monkeypatch, text, source):
    generator = _bare_generator()
    generator._generation_lock = RLock()
    def generate(**kwargs):
        generator._last_llm_source = source
        return text
    generator.generate_reply = generate
    generator._add_0102_signature = lambda text, **_: text + " 0102"
    generator.inspect_reply = lambda *args: {'approved': True, 'reason': 'fixture_review'}
    monkeypatch.setattr(processor_module, "get_reply_generator", lambda: generator)
    monkeypatch.setattr(processor_module, "INTELLIGENT_REPLIES_AVAILABLE", True)
    return generator


def _offline_processor(monkeypatch):
    monkeypatch.setenv("YT_ALLOW_GENERIC_REPLY_FALLBACK", "false")
    processor = object.__new__(CommentProcessor)
    processor.video_title = "Unrelated inbox title"
    processor.target_channel_id = "receiving-channel"
    processor.extract_comment_data = lambda _: {
        "text": "specific comment", "author_name": "Fixture", "channel_id": "fixture",
        "video_title": "Row title", "video_id": "row123", "published_time": "1 day ago",
    }
    processor.get_comment_count = lambda: 1
    processor.check_moderators = processor.use_vision = processor.action_debug = False
    processor.reply_basic_only = processor.reply_debug_tags = False
    processor.no_classification = True
    processor.human = None
    processor._randomize_action_queue = lambda actions: actions
    processor._get_random_delay_multiplier = lambda: 0
    async def heartbeat(_, stop):
        await stop.wait()
    processor._thinking_heartbeat = heartbeat
    processor.stats = {"replies": 0}
    posted = []
    async def execute(index, text, **kwargs):
        posted.append((index, text))
        return True
    processor.reply_executor = SimpleNamespace(execute_reply=execute, last_submission_status='verified')
    async def inspect_posted(*args):
        return True
    processor._inspect_posted_reply = inspect_posted
    async def inspect_draft(*args):
        return {'approved': True, 'reason': 'fixture_review'}
    processor._inspect_reply = inspect_draft
    return processor, posted


def test_processor_cannot_borrow_later_provider_source(monkeypatch):
    generator = _fake_generation(monkeypatch, "Generic 0102", "template")
    processor, posted = _offline_processor(monkeypatch)
    real_to_thread = asyncio.to_thread
    async def interleave(call, *args, **kwargs):
        result = await real_to_thread(call, *args, **kwargs)
        generator._last_llm_source = "qwen"  # A different completed generation.
        return result
    monkeypatch.setattr(processor_module.asyncio, "to_thread", interleave)
    result = asyncio.run(processor.engage_comment(1, do_like=False, do_heart=False))
    assert result["reply"] is False
    assert posted == []


def test_processor_receipt_stays_bound_after_post_await(monkeypatch):
    generator = _fake_generation(monkeypatch, "Grounded 0102", "qwen")
    processor, posted = _offline_processor(monkeypatch)
    async def execute(index, text, **kwargs):
        posted.append((index, text))
        generator._last_llm_source = "template"
        return True
    processor.reply_executor.execute_reply = execute
    result = asyncio.run(processor.engage_comment(1, do_like=False, do_heart=False))
    assert posted == [(1, "Grounded 0102")]
    assert result["llm_source"] == "qwen"


@pytest.mark.parametrize("source", ["qwen", "grok", "lm_studio", "skill_1:qwen",
    "skill_1_sub:lm_studio", "skill_2:grok", "skill_3:qwen",
    "skill_0:contextual_mockery", "skill_0:grok_greeting", "gemma_emoji:heuristic_love"])
def test_context_gate_accepts_exact_supported_strategies(source):
    assert CommentProcessor.is_contextual_reply_source(source)


@pytest.mark.parametrize("text,source", [(None, "qwen"), ("", "qwen"), ("   ", "qwen"),
    ("Generic 0102", "unknown"), ("Generic 0102", "skill_0:whack_a_maga_fallback")])
def test_actual_processor_no_post_for_missing_or_unproven_reply(monkeypatch, text, source):
    _fake_generation(monkeypatch, text, source)
    processor, posted = _offline_processor(monkeypatch)
    result = asyncio.run(processor.engage_comment(1, do_like=False, do_heart=False))
    assert result["reply"] is False
    assert posted == []


def test_explicit_legacy_opt_in_is_not_provider_attribution(monkeypatch):
    _fake_generation(monkeypatch, None, "qwen")
    processor, posted = _offline_processor(monkeypatch)
    monkeypatch.setenv("YT_ALLOW_GENERIC_REPLY_FALLBACK", "true")
    result = asyncio.run(processor.engage_comment(1, do_like=False, do_heart=False))
    assert len(posted) == 1
    assert result["llm_source"] == "template"


def _full_generator(monkeypatch, skill_result=None):
    generator = _bare_generator()
    generator.commenter_history_store = None
    generator.content_analyzer = None
    generator.classify_commenter = lambda **_: SimpleNamespace(
        commenter_type=generator_module.CommenterType.REGULAR, is_ally=False)
    generator._is_repeat_comment = lambda *args: False
    generator._get_recent_reply_norms = lambda *args, **kwargs: set()
    generator._is_emoji_comment = lambda *_: False
    generator._get_semantic_pattern_prompt = lambda *_: None
    generator._add_0102_signature = lambda text, **_: text + " 0102"
    def execute(context):
        if isinstance(skill_result, Exception):
            raise skill_result
        return skill_result or {"strategy": "llm_contextual", "reply_text": context.llm_reply, "confidence": 1}
    generator.skill_0 = generator.skill_1 = generator.skill_2 = SimpleNamespace(execute=execute)
    monkeypatch.setattr(generator_module, "SKILLS_AVAILABLE", True)
    for name in ("Skill0Context", "Skill1Context", "Skill2Context", "Skill3Context"):
        monkeypatch.setattr(generator_module, name, SimpleNamespace, raising=False)
    return generator


@pytest.mark.parametrize("skill_result", [
    {"strategy": "llm_contextual", "reply_text": "", "confidence": 1},
    {"strategy": "llm_contextual", "reply_text": "Unrelated replacement", "confidence": 1},
    {"strategy": "qwen", "reply_text": "Forged provider strategy", "confidence": 1},
    RuntimeError("controlled skill failure"),
])
def test_successful_provider_cannot_credit_skill_replacement(monkeypatch, skill_result):
    generator = _full_generator(monkeypatch, skill_result)
    result = generator.generate_reply_with_source("A specific video comment", "Fixture")
    assert generator.qwen_engine.call is not None  # Provider really succeeded first.
    assert not CommentProcessor.is_contextual_reply_source(result.source)


def test_successful_provider_draft_retained_by_skill(monkeypatch):
    generator = _full_generator(monkeypatch)
    result = generator.generate_reply_with_source("A specific video comment", "Fixture")
    assert result.text == "That lyric lands because the video connects solidarity with action. 0102"
    assert result.source == "skill_1:qwen"
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.source = "template"


def test_dedupe_template_replacement_loses_provider_credit(monkeypatch):
    generator = _full_generator(monkeypatch)
    generator._last_llm_source = "qwen"
    result = generator._dedupe_reply("Repeated draft", {"repeated draft"}, ["Generic fallback"])
    assert result == "Generic fallback"
    assert generator.get_last_llm_source() == "template"


@pytest.mark.parametrize("retains_draft", [False, True])
def test_old_comment_skill_receipt_requires_actual_draft(monkeypatch, retains_draft):
    generator = _full_generator(monkeypatch)
    def execute(context):
        return {"strategy": "llm_reengagement_old", "reply_text":
            "Welcome back " + context.llm_reply if retains_draft else "Generic welcome back"}
    monkeypatch.setattr(generator_module, "OldCommentEngagementSkill",
        lambda: SimpleNamespace(execute=execute), raising=False)
    result = generator.generate_reply_with_source("A specific video comment", "Fixture", published_time="1 year ago")
    assert generator.qwen_engine.call is not None
    assert CommentProcessor.is_contextual_reply_source(result.source) is retains_draft
    assert result.source == ("skill_3:qwen" if retains_draft else "skill_3:unknown")


def test_timeout_discards_active_result_and_cancels_queued_provider(monkeypatch):
    generator = _full_generator(monkeypatch)
    entered, release = Event(), Event()
    calls = []
    def provider(**kwargs):
        calls.append(kwargs["prompt"])
        entered.set()
        assert release.wait(3), "fixture did not release provider"
        return "A grounded delayed answer"
    generator.qwen_engine.generate_response = provider
    monkeypatch.setattr(processor_module, "get_reply_generator", lambda: generator)
    first, first_posts = _offline_processor(monkeypatch)
    second, second_posts = _offline_processor(monkeypatch)
    real_wait_for = asyncio.wait_for
    async def short_timeout(awaitable, timeout):
        task = asyncio.create_task(awaitable)
        if not entered.is_set():
            assert await asyncio.to_thread(entered.wait, 2), "fixture provider did not start"
        return await real_wait_for(task, timeout=0.03)
    monkeypatch.setattr(processor_module.asyncio, "wait_for", short_timeout)
    async def run():
        try:
            one = await first.engage_comment(1, do_like=False, do_heart=False)
            assert entered.is_set()
            two = await second.engage_comment(2, do_like=False, do_heart=False)
            assert not one["reply"] and not two["reply"]
        finally:
            release.set()
    asyncio.run(run())  # Waits for both controlled worker threads to finish.
    assert len(calls) == 1
    assert first_posts == second_posts == []


def test_missing_row_title_never_uses_unbound_inbox_title(monkeypatch):
    captured = {}
    generator = _fake_generation(monkeypatch, "reply", "qwen")
    generator.generate_reply = lambda **kwargs: captured.update(kwargs) or "reply"
    processor, _ = _offline_processor(monkeypatch)
    processor._generate_intelligent_reply({"text": "comment"})
    assert captured["video_title"] is None
    assert processor._get_context_flags({"text": "comment"})["has_video_context"] is False


_DOM_FIXTURE = r"""
const vm = require('node:vm');
let input = '';
process.stdin.on('data', data => input += data);
process.stdin.on('end', () => {
  const fixture = JSON.parse(input);
  const element = (text, href) => ({textContent:text || '', href,
    getAttribute:name => name === 'href' ? href : name === 'title' ? text : null});
  const rows = fixture.rows.map(row => {
    const title = element(row.title);
    const links = (row.links || []).map(href => element('', href));
    const info = row.metadata === false ? null : {
      querySelector: () => row.title ? title : null,
      querySelectorAll: () => links
    };
    return {textContent:'fixture 1 day ago',
      querySelector: selector => {
        if (selector === 'ytcp-video-thumbnail-with-info') return info;
        if (selector.includes('video-title')) return row.title ? title : null;
        if (selector === 'yt-formatted-string#content-text') return element(row.comment);
        if (selector.startsWith('#author-text')) return element('Fixture');
        return null;
      },
      querySelectorAll: selector => selector === 'a[href]'
        ? [element('', row.foreign), ...links] : []};
  });
  const document = {querySelectorAll: selector => selector === 'ytcp-comment-thread' ? rows : []};
  const program = '(function(){' + fixture.script + '\n}).call(null,' + fixture.index + ')';
  const result = vm.runInNewContext(program, {document, URL, console:{log(){}}}, {timeout:1000});
  process.stdout.write(JSON.stringify(result));
});
"""


def _extract_synthetic_rows(rows):
    node = os.environ.get("NODE_BINARY") or shutil.which("node")
    assert node, "Pinned Node runtime is required for the synthetic DOM fixture"
    class Driver:
        def execute_script(self, script, index):
            run = subprocess.run([node, "-e", _DOM_FIXTURE],
                input=json.dumps({"script":script,"index":index,"rows":rows}),
                capture_output=True, text=True, timeout=5, check=True,
                env={key:os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ})
            return json.loads(run.stdout)
    processor = object.__new__(CommentProcessor)
    processor.driver = Driver()
    return [processor.extract_comment_data(i) for i in range(1, len(rows) + 1)]


def test_actual_dom_script_binds_mixed_rows_to_owned_metadata():
    rows = [
        {"title":"Row A", "comment":"A", "foreign":"https://www.youtube.com/watch?v=FOREIGN_A",
         "links":["https://studio.youtube.com/video/OWN_A/comments/inbox"]},
        {"title":"Row B", "comment":"B", "foreign":"https://other.invalid/video/FOREIGN_B",
         "links":["https://www.youtube.com/watch?v=OWN_B"]},
        {"title":"Untrusted", "comment":"C", "metadata":False,
         "foreign":"https://www.youtube.com/watch?v=FOREIGN_C"},
        {"title":"Row D", "comment":"D", "links":["https://other.invalid/video/FOREIGN_D"]},
    ]
    results = _extract_synthetic_rows(rows)
    assert [(r["video_title"], r["video_id"]) for r in results] == [
        ("Row A", "OWN_A"), ("Row B", "OWN_B"), (None, None), ("Row D", None)]
    assert [r["text"] for r in results] == ["A", "B", "C", "D"]
    assert results[0]["video_url"] == rows[0]["links"][0]
    assert results[1]["video_url"] == rows[1]["links"][0]
    assert results[2]["video_url"] is results[3]["video_url"] is None


def test_dae_factory_preserves_injected_dependencies_and_channel():
    fields = ["driver", "human", "stats", "reply_executor", "SELECTORS", "VISION_DESCRIPTIONS",
              "use_vision", "check_moderators", "mod_lookup", "reply_debug_tags", "video_title",
              "channel_id", "session_id"]
    dae = SimpleNamespace(**{name: object() for name in fields})
    captured = row_module.create_comment_processor(dae, lambda **kwargs: kwargs)
    assert captured == {
        "driver": dae.driver, "human": dae.human, "stats": dae.stats,
        "reply_executor": dae.reply_executor, "selectors": dae.SELECTORS,
        "vision_descriptions": dae.VISION_DESCRIPTIONS, "use_vision": dae.use_vision,
        "use_dom": True, "ui_tars_bridge": None, "check_moderators": dae.check_moderators,
        "mod_lookup": dae.mod_lookup, "reply_debug_tags": dae.reply_debug_tags,
        "video_title": dae.video_title, "target_channel_id": dae.channel_id, "session_id": dae.session_id,
    }


@pytest.mark.parametrize("parent", [None, 7])
def test_event_payload_retains_receipt_without_inventing_video(parent):
    result = {"comment_text":"row", "reply_text_posted":"Bound answer", "reply":True,
              "llm_source":"skill_1:qwen", "video_id":None, "video_title":None}
    payload = row_module.comment_event_payload(result, "fixture", "7.1", "channel", "fixed-time", parent)
    assert payload["video_id"] is payload["video_title"] is None
    assert payload["llm_source"] == "skill_1:qwen"
    assert payload["reply_text_posted"] == "Bound answer"
    assert payload["comment_idx"] == "7.1"
    assert payload.get("is_nested", False) is (parent is not None)
    if parent is not None:
        assert payload["parent_comment_idx"] == 7


@pytest.mark.parametrize("service_ok", [True, False])
def test_local_service_has_full_prompt_and_bounded_qwen_fallback(monkeypatch, service_ok):
    generator = _bare_generator()
    generator.lm_studio_available = True
    generator.lm_studio_model_id = "qwen3-fixture"
    calls = []
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=200 if service_ok else 503,
            json=lambda: {"choices":[{"message":{"content":"A grounded service answer"}}]})
    monkeypatch.setattr(generator_module.requests, "post", post)
    result = generator._generate_contextual_reply("specific comment", "Fixture", video_title="Row title")
    assert calls[0][1]["timeout"] == 3
    prompt = calls[0][1]["json"]["messages"][1]["content"]
    assert "specific comment" in prompt and "Row title" in prompt and "Prior topic: mutual aid" in prompt
    assert generator.get_last_llm_source() == ("lm_studio" if service_ok else "qwen")
    assert result
    assert (generator.qwen_engine.call is None) is service_ok


def test_grok_is_not_called_without_explicit_opt_in():
    generator = _bare_generator()
    generator.qwen_engine = None
    generator.grok_connector = SimpleNamespace(get_response=_deny_dependency)
    assert generator._generate_contextual_reply("specific comment", "Fixture") is None


@pytest.mark.parametrize("second_id,expected_id", [("OWN_ID", "OWN_ID"), ("OTHER_ID", None)])
def test_actual_dom_script_requires_unique_video_id(second_id, expected_id):
    first_url = "https://studio.youtube.com/video/OWN_ID/comments/inbox"
    row = {"title":"Metadata title", "comment":"specific comment",
           "links":[first_url, "https://www.youtube.com/watch?v=" + second_id]}
    result, = _extract_synthetic_rows([row])
    assert result["video_id"] == expected_id
    assert result["video_url"] == (first_url if expected_id else None)
    assert result["video_title"] == ("Metadata title" if expected_id else None)
    assert result["text"] == "specific comment"

