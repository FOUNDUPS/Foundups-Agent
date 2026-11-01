"""Offline quality-stop controls through complete production definitions.

Only explicit synthetic collaborators are used. Run with the owner's minimal
environment/effect guard, never inherited credentials or module constructors.
"""
import asyncio
import importlib.util
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace, ModuleType
import threading

import pytest


@pytest.fixture
def owners(monkeypatch):
    path = Path(__file__).with_name("test_chat_manifest_inspection.py")
    spec = importlib.util.spec_from_file_location("_quality_definition_helpers", path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.GEN.normalize_reply_theme = helper.CONTEXT.normalize_reply_theme
    helper.GEN.select_channel_personality = helper.CONTEXT.select_channel_personality
    helper.PROCESSOR.INTELLIGENT_REPLIES_AVAILABLE = True
    for name, value in {"YT_ALLOW_GENERIC_REPLY_FALLBACK": "false", "YT_ENABLE_GROK_REPLIES": "false",
                        "YT_AUTOMATION_ENABLED": "true", "YT_COMMENT_ENGAGEMENT_ENABLED": "true",
                        "YT_COMMENT_REPLY_ENABLED": "true", "YT_FACTCHECK_ENABLED": "false"}.items():
        monkeypatch.setenv(name, value)
    return helper


async def settled(*_args, **_kwargs):
    return None


def processor(owners, text="The film details are at HornetHunter.com.", reason=None, review=None):
    module = owners.PROCESSOR
    item = object.__new__(module.CommentProcessor)
    item.target_channel_id = "receiving-channel"
    item.extract_comment_data = lambda _: dict(text="Where can I watch the film?", author_name="Aki")
    item._get_context_flags = lambda _: {}
    item.human = None
    item.check_moderators = item.use_vision = item.action_debug = False
    item.reply_basic_only = item.reply_debug_tags = False
    item.no_classification = True
    item._randomize_action_queue = lambda actions: actions
    item._get_random_delay_multiplier = lambda: 0
    item.delay_multiplier = 0
    item.stats = {"replies": 0}
    item._thinking_heartbeat = settled
    receipt = SimpleNamespace(text=text, source="lm_studio", theme=None,
                              context={"assessment": {"intent": "question"}}, rejection_reason=reason)
    item._generate_intelligent_reply = lambda *_a, **_k: receipt
    posted = []
    async def inspect(*_args):
        return dict(review) if review is not None else {"approved": True}
    async def execute(*args, **kwargs):
        posted.append((args, kwargs))
        return True
    item._inspect_reply = inspect
    item._inspect_posted_reply = lambda *_a: asyncio.sleep(0, result=True)
    item.reply_executor = SimpleNamespace(execute_reply=execute, last_submission_status="verified")
    return item, posted


@pytest.mark.parametrize("reason", ["review_rejected", "review_unavailable_or_invalid"])
def test_processor_final_review_halts_quality_and_never_executes(owners, reason):
    item, posted = processor(owners, review={"approved": False, "reason": reason})
    result = asyncio.run(item.engage_comment(1, do_like=False, do_heart=False))
    assert result.get("halted_for_reply_quality") is True
    assert result.get("quality_halt_reason") == reason
    assert result["reply"] is False and posted == []


def test_processor_receipt_invalid_text_halts_before_final_review_or_execute(owners):
    item, posted = processor(owners, text=None, reason="invalid_reply_text")
    async def forbidden(*_args):
        raise AssertionError("invalid generation must not enter final review")
    item._inspect_reply = forbidden
    result = asyncio.run(item.engage_comment(1, do_like=False, do_heart=False))
    assert result.get("halted_for_reply_quality") is True
    assert result.get("quality_halt_reason") == "invalid_reply_text"
    assert posted == []


def test_actual_await_copies_receipt_quality_reason_to_comment_data(owners):
    item, _ = processor(owners, text=None, reason="invalid_reply_text")
    data = {}
    assert asyncio.run(item._await_reply_generation(data)) == (None, "lm_studio")
    assert data.get("_reply_rejection_reason") == "invalid_reply_text"


@pytest.mark.parametrize("text,reason", [(None, None), (None, "theme_changed"), ("", None)])
def test_unavailable_theme_changed_and_intentional_empty_are_not_quality_halts(owners, text, reason):
    item, posted = processor(owners, text=text, reason=reason)
    result = asyncio.run(item.engage_comment(1, do_like=False, do_heart=False))
    assert not result.get("halted_for_reply_quality")
    assert not result.get("quality_halt_reason")
    assert result["reply"] is False and posted == []


def test_useful_reviewed_answer_still_executes(owners):
    item, posted = processor(owners)
    result = asyncio.run(item.engage_comment(1, do_like=False, do_heart=False))
    assert result["reply"] is True and len(posted) == 1
    assert posted[0][0][1] == "The film details are at HornetHunter.com."
    assert not result.get("halted_for_reply_quality")


@pytest.mark.parametrize("reason", ["review_rejected", "review_unavailable_or_invalid", "invalid_reply_text"])
def test_actual_dae_stops_after_bad_result_before_events_nested_and_refresh(owners, tmp_path, monkeypatch, reason):
    module = owners.definitions("_quality_dae", "modules/communication/video_comments/skillz/tars_like_heart_reply/comment_engagement_dae.py")
    module.TELEMETRY_DIR = tmp_path
    module.FAM_DAEMON_AVAILABLE = True
    events, nested, refresh, processed = [], [], [], []
    module.get_fam_daemon = lambda: SimpleNamespace(publish=lambda *_a: events.append(True))
    module.FAMEventType = SimpleNamespace(COMMENT_IGNORED=SimpleNamespace(value="ignored"))
    module.comment_event_payload = lambda *_a, **_k: {}
    item = object.__new__(module.CommentEngagementDAE)
    item.session_id, item.channel_id, item.parent_pid = "offline", "creator", None
    item.livechat_sender = item.human = None
    item.use_vision = False
    item._sessions_since_long_break = 0
    item.stats = dict(comments_processed=0, likes=0, hearts=0, replies=0)
    item._should_take_break = lambda *_: False
    item._save_break_state = lambda: None
    item._detect_012_manual_replies = settled
    async def loaded(**_kwargs): return 2
    item._wait_for_comments_loaded = loaded
    item.get_comment_count = lambda: 2
    item.driver = SimpleNamespace(current_url="https://studio.youtube.com/inbox", refresh=lambda: refresh.append(True))
    async def engage(*_a, **_k):
        processed.append(True)
        return dict(reply=False, like=False, heart=False, halted_for_reply_quality=True, quality_halt_reason=reason)
    async def replies(*_a, **_k): nested.append(True); return []
    item.comment_processor = SimpleNamespace(engage_comment=engage, delay_multiplier=0)
    item.reply_executor = SimpleNamespace(process_nested_replies=replies)
    monkeypatch.setattr(module.asyncio, "sleep", settled)
    result = asyncio.run(item.engage_all_comments(max_comments=2, do_like=False, do_heart=False))
    assert len(processed) == 1
    assert events == nested == refresh == []
    assert result.get("halted_for_reply_quality") is True
    assert result.get("quality_halt_reason") == reason


def generator(owners):
    item = object.__new__(owners.GEN.IntelligentReplyGenerator)
    item._generation_lock = threading.RLock()
    item._load_reply_theme = lambda: None
    item._semantic_reply_history = lambda *_: (True, set())
    item._load_personalization_context = lambda **_: ""
    item._load_voice_memory_context = lambda *_a, **_k: "Film details are at HornetHunter.com."
    item.lm_studio_available, item.lm_studio_model_id = True, "qwen3.5-4b"
    item.qwen_engine = item.grok_connector = item.banter_engine = None
    return item


def semantic_data():
    return dict(text="Where can I watch the film?", author_name="Aki", channel_id="viewer",
                video_title="Hornet film", video_id="film", receiving_channel_id="creator")


def meaning():
    return dict(intent="question", meaning="Asks where to watch", question="Where can I watch?",
                stance="unclear", uncertainty="", evidence_quote="Where can I watch the film?",
                strategy="answer", theme_relevant=False)


def generate(item):
    return item.generate_reply_with_source(comment_text=semantic_data()["text"], author_name="Aki",
        author_channel_id="viewer", target_channel_id="creator", video_title="Hornet film", semantic_context=semantic_data())


@pytest.mark.parametrize("failure", ["body", "exception"])
def test_writer_provider_failures_do_not_echo_raw_diagnostics(owners, caplog, monkeypatch, failure):
    item = generator(owners)
    marker = "SYNTHETIC_PRIVATE_PROVIDER_DIAGNOSTIC"
    def post(*_a, **_k):
        if failure == "exception": raise RuntimeError(marker)
        return SimpleNamespace(status_code=500, text=marker)
    monkeypatch.setattr(owners.GEN, "requests", SimpleNamespace(post=post), raising=False)
    with caplog.at_level(logging.DEBUG):
        assert item._generate_contextual_reply("Where is the film?", "Aki") is None
    assert marker not in caplog.text


def test_actual_bad_writer_format_has_receipt_reason_without_raw_output_log_and_next_call_clears(owners, caplog, monkeypatch):
    item = generator(owners)
    marker = "SYNTHETIC_BAD_OUTPUT"
    answers = iter([json.dumps(meaning()), "<|audio|>" + marker, json.dumps(meaning()), "The film details are at HornetHunter.com."])
    monkeypatch.setattr(owners.GEN, "requests", SimpleNamespace(post=lambda *_a, **_k: SimpleNamespace(
        status_code=200, json=lambda: {"choices": [{"message": {"content": next(answers)}}]})), raising=False)
    with caplog.at_level(logging.DEBUG):
        bad = generate(item)
        good = generate(item)
    assert bad.text is None and getattr(bad, "rejection_reason", None) == "invalid_reply_text"
    assert marker not in caplog.text
    assert good.text == "The film details are at HornetHunter.com."
    assert getattr(good, "rejection_reason", None) is None


def test_bad_qwen_format_never_falls_through_as_success(owners):
    item = generator(owners)
    item.lm_studio_available = False
    item.qwen_engine = SimpleNamespace(generate_response=lambda **_: "<|audio|>SYNTHETIC_QWEN_BAD_FORMAT")
    item._clean_reply = lambda text, _author: text
    assert item._generate_contextual_reply("Where is the film?", "Aki") is None
    assert getattr(item, "_current_reply_rejection_reason", None) == "invalid_reply_text"


def test_ambient_synthetic_key_never_enters_assessment_writer_review_json(owners, monkeypatch):
    marker = "synthetic-api-key-must-stay-environment-only"
    monkeypatch.setenv("OPENROUTER_API_KEY", marker)
    item = generator(owners)
    calls = []
    answers = iter([json.dumps(meaning()), "The film details are at HornetHunter.com.", json.dumps(owners.GOOD)])
    def post(_url, **kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status_code=200, json=lambda: {"choices": [{"message": {"content": next(answers)}}]})
    monkeypatch.setattr(owners.GEN, "requests", SimpleNamespace(post=post), raising=False)
    result = generate(item)
    review = item.inspect_reply({**semantic_data(), "_reply_theme": result.theme,
        "_generation_context": result.context, "_target_channel_id": "creator"}, result.text)
    assert review["approved"] and len(calls) == 3
    assert all(marker not in json.dumps(call["json"]) for call in calls)
    assert all("Authorization" not in call.get("headers", {}) for call in calls)


@pytest.mark.parametrize("failure", ["body", "exception"])
def test_optin_xai_connector_keeps_key_only_in_auth_header_and_no_raw_error_log(owners, caplog, monkeypatch, failure):
    module = owners.definitions("_quality_connector", "modules/ai_intelligence/rESP_o1o2/src/llm_connector.py")
    module.logging = logging
    connector = object.__new__(module.LLMConnector)
    connector.api_key, connector.model, connector.timeout = "synthetic-xai-header-key", "grok-test", 1
    connector.grok_api_url = "https://api.x.ai/test"
    calls = []
    marker = "SYNTHETIC_XAI_RAW_DIAGNOSTIC"
    def post(_url, **kwargs):
        calls.append(kwargs)
        if failure == "exception": raise RuntimeError(marker)
        return SimpleNamespace(status_code=403, text=marker)
    module.requests = SimpleNamespace(post=post)
    with caplog.at_level(logging.DEBUG):
        assert connector._get_grok_response("Synthetic prompt", 10, 0.1, "Synthetic system") is None
    assert len(calls) == 1 and calls[0]["headers"]["Authorization"] == "Bearer " + connector.api_key
    assert connector.api_key not in json.dumps(calls[0]["json"])
    assert marker not in caplog.text


@pytest.mark.parametrize("gate", ["stop", "automation", "engagement", "reply"])
def test_actual_executor_early_gate_prevents_binding_claim_and_execution(owners, tmp_path, monkeypatch, gate):
    module = owners.EXECUTOR
    gates = owners.definitions("_quality_gates", "modules/communication/livechat/src/automation_gates.py")
    module.gate_snapshot = gates.gate_snapshot
    monkeypatch.setitem(sys.modules, "modules.communication.livechat.src.automation_gates", gates)
    stop = tmp_path / "STOP"
    monkeypatch.setenv("YT_AUTOMATION_STOP_FILE", str(stop))
    if gate == "stop": stop.write_text("stop", encoding="utf-8")
    else:
        flag = {"automation": "YT_AUTOMATION_ENABLED", "engagement": "YT_COMMENT_ENGAGEMENT_ENABLED", "reply": "YT_COMMENT_REPLY_ENABLED"}[gate]
        monkeypatch.setenv(flag, "false")
    calls = []
    item = object.__new__(module.BrowserReplyExecutor)
    item.driver = SimpleNamespace(execute_script=lambda *_: None)
    item.history_store = SimpleNamespace(reply_target_key=lambda *_: "target",
        begin_reply_attempt=lambda *_: calls.append("claim") or "attempt", finish_reply_attempt=lambda *_: None)
    item._bind_reply_target = lambda *_a, **_k: calls.append("bind") or True
    item._reply_snapshot = lambda *_: {"complete": True, "ids": [], "matching_ids": []}
    async def execute(*_a, **_k): calls.append("execute"); return False
    item._execute_reply_unverified = execute
    assert asyncio.run(item.execute_reply(1, "Specific useful reply", expected_comment={"comment_id": "c1"})) is False
    assert calls == []


@pytest.mark.parametrize("late_stop", [False, True])
def test_actual_typing_to_submit_path_rechecks_late_stop_before_click(owners, tmp_path, monkeypatch, late_stop):
    module = owners.EXECUTOR
    gates = owners.definitions("_quality_late_gates", "modules/communication/livechat/src/automation_gates.py")
    module.gate_snapshot = gates.gate_snapshot
    monkeypatch.setitem(sys.modules, "modules.communication.livechat.src.automation_gates", gates)
    row = owners.definitions("_quality_row", "modules/communication/video_comments/skillz/tars_like_heart_reply/src/comment_row_context.py")
    monkeypatch.setitem(sys.modules, "modules.communication.video_comments.skillz.tars_like_heart_reply.src.comment_row_context", row)
    behavior = ModuleType("offline_human_behavior")
    behavior.get_0102_behavior_interface = lambda **_: "0102"
    monkeypatch.setitem(sys.modules, "modules.infrastructure.foundups_selenium.src.human_behavior", behavior)
    stop = tmp_path / "STOP"
    monkeypatch.setenv("YT_AUTOMATION_STOP_FILE", str(stop))
    entered, clicks = [], []
    textarea = object()
    def script(code, *args):
        if "submitBtn.click()" in code:
            clicks.append(True)
            return {"success": True}
        if "replyBtn.click()" in code: return {"success": True}
        if "return textarea;" in code: return textarea
        if "el.textContent += chunk" in code: entered.append(args[1]); return None
        if code == "return arguments[0].textContent": return "".join(entered)
        if "return el ?" in code:
            if late_stop: stop.write_text("stop", encoding="utf-8")
            return "".join(entered)
        return None
    item = object.__new__(module.BrowserReplyExecutor)
    item.driver = SimpleNamespace(execute_script=script)
    item.selectors = {"comment_thread": "ytcp-comment-thread"}
    item.human, item.delay_multiplier = None, 0
    item._bind_reply_target = lambda *_a, **_k: True
    item._pre_submit_guard = lambda: True
    item._submit_invoked = False
    monkeypatch.setattr(module.asyncio, "sleep", settled)
    result = asyncio.run(item._execute_reply_unverified(1, "Useful answer", expected_comment={"comment_id": "c1"}))
    assert "".join(entered) == "Useful answer"
    assert result is (not late_stop)
    assert clicks == ([] if late_stop else [True])
    assert item._submit_invoked is (not late_stop)
