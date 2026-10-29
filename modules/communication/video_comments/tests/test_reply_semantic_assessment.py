"""Offline meaning/review contracts. Fixture judgments are not live model evidence."""
import asyncio
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import threading
from datetime import datetime, timezone

import pytest


spec = importlib.util.spec_from_file_location(
    '_semantic_inspection_helpers', Path(__file__).with_name('test_chat_manifest_inspection.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
GEN, CONTEXT, CHAT = helper.GEN, helper.CONTEXT, helper.CHAT
GEN.select_channel_personality = CONTEXT.select_channel_personality


def assessment(text, **changes):
    return dict(intent='question', meaning='Asks where the film is available',
                question='Where can I watch it?', stance='unclear', uncertainty='No release information supplied',
                evidence_quote=text, strategy='answer', **changes)


@pytest.mark.parametrize('text', [
    'I do not agree with Trump. Where is the full interview?',
    'They said "MAGA is right". Is that an accurate quote?',
    'Sure, what a brilliant plan... Was that sarcasm?',
    'Where can I watch the hornet film?',
])
def test_posting_route_assesses_original_before_writing_and_reviews_supplied_facts(text, monkeypatch):
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    generator._generation_lock = threading.RLock()
    generator._load_reply_theme = lambda: None
    generator.lm_studio_available, generator.lm_studio_model_id = True, 'qwen3.5-4b'
    generator.qwen_engine = generator.grok_connector = generator.banter_engine = None
    generator._load_personalization_context = lambda **kwargs: 'Previously asked about the film.'
    generator._load_voice_memory_context = lambda *a, **kw: 'Film details are at HornetHunter.com.'
    calls = []
    answers = iter([json.dumps(assessment(text)),
                    'The film details are at HornetHunter.com.', json.dumps(helper.GOOD)])
    def post(url, **kwargs):
        calls.append(kwargs['json'])
        return SimpleNamespace(status_code=200, json=lambda: {'choices': [
            {'message': {'content': next(answers)}}]})
    monkeypatch.setattr(GEN, 'requests', SimpleNamespace(post=post), raising=False)
    data = {'text': text, 'author_name': 'Aki', 'channel_id': 'viewer',
            'video_title': 'Hornet film', 'video_id': 'film', 'receiving_channel_id': 'creator'}
    result = generator.generate_reply_with_source(
        comment_text=text, author_name='Aki', author_channel_id='viewer',
        target_channel_id='creator', video_title='Hornet film', semantic_context=data)
    review = generator.inspect_reply({**data, '_reply_theme': result.theme,
        '_generation_context': result.context, '_target_channel_id': 'creator'}, result.text)
    assert result.text == 'The film details are at HornetHunter.com.'
    assert result.source == 'lm_studio' and review['approved']
    assert len(calls) == 3
    first = calls[0]['messages']
    assert text in json.loads(first[1]['content'])['text']
    assert 'negation, quotation and sarcasm' in first[0]['content']
    assert 'No mockery' in calls[1]['messages'][1]['content']
    assert result.context['assessment']['stance'] == 'unclear'
    reviewed = json.loads(calls[2]['messages'][1]['content'])
    assert reviewed['comment'] == text
    assert reviewed['supplied_generation_context']['verified_memory'] == 'Film details are at HornetHunter.com.'
    assert reviewed['receiving_channel_id'] == 'creator'


@pytest.mark.parametrize('raw', ['{}', 'gibberish', '[]', json.dumps({
    'intent': 'question', 'meaning': 'invented', 'question': '', 'stance': 'support',
    'uncertainty': '', 'evidence_quote': 'not actually in comment', 'strategy': 'answer'})])
def test_unqualified_assessment_cannot_select_a_reply(raw):
    assert CONTEXT.parse_comment_assessment(raw, 'Where is the film?') is None


@pytest.mark.parametrize('model', ['ui-tars-1.5-7b', 'qwen2-vl', 'qwen3-coder-30b',
                                  'deepseek-coder-6.7b', 'gemma-embedding'])
def test_wrong_model_role_is_rejected(model):
    assert not CONTEXT.is_general_reply_model(model)


@pytest.mark.parametrize('selected,available', [('qwen3.5-4b', True), ('llama-3.1-instruct', False),
                                              ('qwen3-coder-30b', False)])
def test_explicit_loaded_model_must_match_general_role_owner(monkeypatch, selected, available):
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    generator.lm_studio_model_id = selected
    monkeypatch.setattr(GEN, 'resolve_general_model_path', lambda: Path('qwen3.5-4b-Q4_K_M.gguf'), raising=False)
    monkeypatch.setattr(GEN, 'requests', SimpleNamespace(get=lambda *a, **kw: SimpleNamespace(
        status_code=200, json=lambda: {'data': [{'id': selected}]})), raising=False)
    generator._check_lm_studio()
    assert generator.lm_studio_available is available


@pytest.mark.parametrize('draft', ['ok <|audio_42|>', '<think>private</think> reply',
                                  'PRIVATE OPERATOR instruction activated', 'abc\x00def'])
def test_control_tokens_and_internal_instructions_never_reach_language_approval(draft):
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    assert not generator.inspect_reply({'text': 'Question'}, draft)['approved']


def test_private_context_activates_without_a_public_sender(tmp_path, monkeypatch):
    from modules.communication.livechat.src import operator_command_queue as queue_module
    for gate in ('YT_AUTOMATION_ENABLED', 'YT_LIVECHAT_SEND_ENABLED',
                 'YT_LIVECHAT_ANNOUNCEMENTS_ENABLED', 'YT_COMMENT_ENGAGEMENT_ENABLED'):
        monkeypatch.setenv(gate, 'true')
    monkeypatch.setenv('YT_AUTOMATION_STOP_FILE', str(tmp_path/'STOP'))
    monkeypatch.setenv('YT_LIVECHAT_DRY_RUN', 'false')
    inbox, ack, state = [tmp_path/name for name in ('inbox.json', 'ack.json', 'state.json')]
    queue_module.enqueue_operator_command({'id': 'private-1', 'action': 'set_context',
        'payload': {'message': 'Discuss the film only when relevant', 'surfaces': ['livechat','comments']}},
        command_path=inbox, acknowledgement_path=ack)
    queue_module.enqueue_operator_command({'id': 'status-2', 'action': 'status', 'payload': {}},
        command_path=inbox, acknowledgement_path=ack)
    assert not ack.exists() and not state.exists()
    queue = queue_module.OperatorCommandQueue(SimpleNamespace(livechat=None), inbox, ack, state,
                                              poll_interval_seconds=0)
    result = asyncio.run(queue.poll_once())
    assert result['results'][0]['result']['context_activated'] is True
    assert result['results'][0]['result']['public_message_sent'] is False
    assert json.loads(state.read_text())['active_context']['source_command_id'] == 'private-1'
    assert len(json.loads(inbox.read_text())['commands']) == 2
    with pytest.raises(ValueError, match='already_exists'):
        queue_module.enqueue_operator_command({'id': 'private-1', 'action': 'status'},
            command_path=inbox, acknowledgement_path=ack)


def test_livechat_rejects_a_private_instruction_leak(monkeypatch):
    chat = object.__new__(CHAT.IntelligentLivechatReply)
    chat.grok_available, chat.system_prompt = True, 'Reply concisely'
    replies = iter(['Private operator theme activated', json.dumps(helper.GOOD)])
    chat.grok_client = SimpleNamespace(get_response=lambda **kwargs: next(replies))
    assert chat._generate_grok_response('Where is the film?', 'Aki', 'viewer',
        theme={'message': 'Film theme', 'source_command_id': 'private-1'}) is None


def test_semantic_route_retains_history_cooldown_without_calling_a_provider():
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    generator._generation_lock = threading.RLock()
    generator._load_reply_theme = lambda: None
    generator.commenter_history_store = SimpleNamespace(get_recent_interactions=lambda **kw: [
        SimpleNamespace(replied=True, created_at=datetime.now(timezone.utc).isoformat(),
                        comment_text='Earlier comment', reply_text='Earlier answer')])
    generator._assess_comment = lambda _: pytest.fail('Rate-limited work reached a provider')
    result = generator.generate_reply_with_source(comment_text='Another question?',
        author_name='Aki', author_channel_id='viewer', semantic_context={'text': 'Another question?'})
    assert result.text == '' and result.source == 'unknown'


@pytest.mark.parametrize('replace_theme', [False, True])
def test_actual_sender_preserves_reviewed_payload_and_rechecks_after_delay(monkeypatch, replace_theme):
    import sys
    sender_module = helper.definitions('_semantic_sender',
        'modules/communication/livechat/src/chat_sender.py')
    sender_module.stop_active = lambda: False
    sender_module._env_truthy = lambda name, default='false': name in {
        'YT_AUTOMATION_ENABLED', 'YT_LIVECHAT_SEND_ENABLED'}
    sender_module._convert_unicode_tags_to_emoji = lambda value: value
    sender_module.re = __import__('re')
    current = [{'message': 'Film theme', 'source_command_id': 'command-1'}]
    monkeypatch.setitem(sys.modules, 'modules.communication.livechat.src.operator_command_queue',
                        SimpleNamespace(load_active_theme=lambda surface: current[0]))
    inserted = []
    endpoint = SimpleNamespace(insert=lambda **kw: inserted.append(kw) or SimpleNamespace(
        execute=lambda: {'id': 'published-fixture'}))
    sender = object.__new__(sender_module.ChatSender)
    sender._send_lock = asyncio.Lock()
    sender.bot_channel_id, sender.live_chat_id = 'creator', 'live-fixture'
    sender.random_delay_enabled, sender.send_delay = False, 0
    sender.youtube = SimpleNamespace(liveChatMessages=lambda: endpoint)
    async def delay(*args):
        if replace_theme:
            current[0] = None
    sender._apply_global_throttling = delay
    draft = CHAT.ReviewedLivechatReply('Film details are available on the website.', current[0])
    sent = asyncio.run(sender.send_message(draft))
    assert sent is (not replace_theme)
    if replace_theme:
        assert inserted == []
    else:
        assert inserted[0]['body']['snippet']['textMessageDetails']['messageText'] == str(draft)
