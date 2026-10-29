"""Offline meaning/review contracts. Fixture judgments are not live model evidence."""
import asyncio
import importlib.util
import json
import sys
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
GEN.normalize_reply_theme = CONTEXT.normalize_reply_theme


def assessment(text, **changes):
    return dict(dict(intent='question', meaning='Asks where the film is available',
                question='Where can I watch it?', stance='unclear', uncertainty='No release information supplied',
                evidence_quote=text, strategy='answer', theme_relevant=False), **changes)


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
    assessment_json, review_json = json.dumps(assessment(text)), json.dumps(helper.GOOD)
    if 'sarcasm' in text.lower():
        assessment_json = '```json\n' + assessment_json + '\n```'
        review_json = '```json\n' + review_json + '\n```'
    answers = iter([assessment_json, 'The film details are at HornetHunter.com.', review_json])
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
    assert all(call['reasoning_effort'] == 'none' for call in calls)
    assert 'Write one concise YouTube reply' in calls[1]['messages'][0]['content']
    assert 'behind Move2Japan' not in calls[1]['messages'][0]['content']
    schema = calls[2]['response_format']['json_schema']
    assert schema['strict'] is True
    assert set(schema['schema']['required']) == set(helper.GOOD)
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
    assert CONTEXT.parse_comment_assessment('prose ```json\n' + json.dumps(
        assessment('Where is the film?')) + '\n```', 'Where is the film?') is None
    assert not CONTEXT.parse_reply_review('```json\n' + json.dumps(helper.GOOD) + '\n``` trailing')['approved']


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
    assert not generator.inspect_reply({'text': 'Why assume that?'},
        'My response was based on the text provided in the comment.')['approved']


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


def local_livechat_fixture(monkeypatch, draft='Film details are at HornetHunter.com.'):
    """Actual generation/review definitions, temporary collaborators, no package startup or providers."""
    native = {'message':'Film details are at HornetHunter.com.', 'surfaces':['livechat'],
              'source_command_id':'live-theme-1', 'expires_at_unix':4102444800,
              'updated_at':'fixture-time'}
    current, calls = [native], []
    monkeypatch.setitem(sys.modules, 'modules.communication.livechat.src.operator_command_queue',
        SimpleNamespace(load_active_theme=lambda surface: current[0] if current[0] and surface in current[0]['surfaces'] else None))
    monkeypatch.setitem(sys.modules, 'modules.communication.video_comments.src.reply_context', CONTEXT)
    monkeypatch.setitem(sys.modules, 'modules.communication.livechat.src.news_context_provider',
                        SimpleNamespace(get_news_context=lambda message: None))
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    generator._generation_lock = threading.RLock()
    generator.lm_studio_available, generator.lm_studio_model_id = True, 'qwen3.5-4b'
    generator.qwen_engine = generator.grok_connector = generator.banter_engine = None
    generator._load_reply_theme = lambda: pytest.fail('Livechat read stored-comment context')
    generator._semantic_reply_history = lambda *a: pytest.fail('Livechat used comment cooldown')
    generator._load_personalization_context = lambda **kw: ''
    generator._load_voice_memory_context = lambda *a, **kw: ''
    values = iter([json.dumps(assessment('Where can I watch the film?', theme_relevant=True)),
                   draft, json.dumps(helper.GOOD)])
    def post(url, **kwargs):
        calls.append(kwargs['json'])
        return SimpleNamespace(status_code=200, json=lambda:{'choices':[{'message':{'content':next(values)}}]})
    monkeypatch.setattr(GEN, 'requests', SimpleNamespace(post=post), raising=False)
    monkeypatch.setitem(sys.modules, 'modules.communication.video_comments.src.intelligent_reply_generator',
                        SimpleNamespace(get_reply_generator=lambda: generator))
    chat = object.__new__(CHAT.IntelligentLivechatReply)
    chat.channel_id, chat.stream_title = 'receiving-channel', 'Film discussion stream'
    chat.grok_available, chat.grok_client, chat.system_prompt = False, None, 'Reply concisely'
    chat.classify_chatter = lambda *a: SimpleNamespace()
    chat._check_pattern_response = chat._generate_banter_response = lambda *a: pytest.fail('Theme failure used template')
    return chat, generator, native, current, calls, post


@pytest.mark.parametrize('grok_failure', ['unavailable', 'empty', 'exception', 'review_rejected'])
def test_themed_livechat_uses_actual_local_assessment_writer_review_after_grok_failure(monkeypatch, grok_failure):
    chat, generator, native, current, calls, _ = local_livechat_fixture(monkeypatch)
    if grok_failure != 'unavailable':
        chat.grok_available = True
        if grok_failure == 'empty':
            respond = lambda **kw: None
        elif grok_failure == 'exception':
            def respond(**kw): raise RuntimeError('Fixture provider unavailable')
        else:
            values = iter(['An unapproved cloud draft.', '{}'])
            respond = lambda **kw: next(values)
        chat.grok_client = SimpleNamespace(get_response=respond)
    monkeypatch.setattr(CHAT.random, 'random', lambda:1)
    result = chat.generate_reply('Where can I watch the film?', '@Aki', 'actual-viewer-id', role='MOD')
    assert isinstance(result, CHAT.ReviewedLivechatReply)
    assert result.theme_snapshot == native and result.theme_snapshot is not native
    assert result == result.reviewed_text == '@Aki Film details are at HornetHunter.com.'
    assert len(calls) == 3
    assessed = json.loads(calls[0]['messages'][1]['content'])
    assert assessed['channel_id'] == 'actual-viewer-id'
    assert assessed['receiving_channel_id'] == 'receiving-channel'
    assert assessed['video_title'] == 'Film discussion stream'
    reviewed = json.loads(calls[2]['messages'][1]['content'])
    assert reviewed['candidate'] == result and reviewed['reply_surface'] == 'livechat'
    assert reviewed['author_channel_id'] == 'actual-viewer-id'
    assert reviewed['supplied_generation_context']['reply_surface'] == 'livechat'
    assert 'at most 195 characters' in calls[1]['messages'][1]['content']


def test_successful_reviewed_grok_reply_does_not_call_local_fallback(monkeypatch):
    chat, _, native, _, calls, _ = local_livechat_fixture(monkeypatch)
    chat.grok_available = True
    values = iter(['Film details are on the website.', json.dumps(helper.GOOD)])
    chat.grok_client = SimpleNamespace(get_response=lambda **kw:next(values))
    monkeypatch.setattr(CHAT.random, 'random', lambda:1)
    result = chat.generate_reply('Where can I watch the film?', 'Aki', 'actual-viewer-id')
    assert isinstance(result, CHAT.ReviewedLivechatReply)
    assert result == '@Aki Film details are on the website.' and result.theme_snapshot == native
    assert calls == []


@pytest.mark.parametrize('characters,accepted', [(195, True), (196, False)])
def test_local_livechat_reviews_the_exact_final_mention_and_never_truncates(monkeypatch, characters, accepted):
    chat, _, _, _, calls, _ = local_livechat_fixture(monkeypatch, draft='x' * characters)
    result = chat.generate_reply('Where can I watch the film?', 'Aki', 'actual-viewer-id')
    assert (result is not None) is accepted
    if accepted:
        assert len(result) == 200
        assert json.loads(calls[2]['messages'][1]['content'])['candidate'] == result
    else:
        assert len(calls) == 2


@pytest.mark.parametrize('when', [2, 3])
@pytest.mark.parametrize('change', ['expired', 'superseded', 'native_metadata_changed'])
def test_local_livechat_expiry_or_replacement_during_generation_or_review_blocks_payload(monkeypatch, when, change):
    chat, _, native, current, calls, original_post = local_livechat_fixture(monkeypatch)
    def post(*args, **kwargs):
        response = original_post(*args, **kwargs)
        if len(calls) == when:
            current[0] = (None if change == 'expired' else
                          {**native, 'source_command_id':'new-theme'} if change == 'superseded' else
                          {**native, 'expires_at_unix':4102444801})
        return response
    monkeypatch.setattr(GEN, 'requests', SimpleNamespace(post=post), raising=False)
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'actual-viewer-id') is None


@pytest.mark.parametrize('surface', ['comments', 'livechat'])
def test_actual_queue_reader_keeps_livechat_and_comment_themes_separate(tmp_path, monkeypatch, surface):
    from modules.communication.livechat.src import operator_command_queue as queue
    from modules.communication.video_comments.src import commenting_control_plane as control
    state, legacy = tmp_path/'state.json', tmp_path/'legacy.json'
    native = {'message':surface + ' theme', 'surfaces':[surface],
              'source_command_id':'scoped-theme', 'expires_at_unix':4102444800}
    state.write_text(json.dumps({'version':1, 'active_context':native}), encoding='utf-8')
    monkeypatch.setenv('YT_012_MANIFEST_STATE_FILE', str(state))
    monkeypatch.setattr(control, 'load_broadcast', lambda:control._load_shared_manifest_context() or control._load_legacy_broadcast(legacy))
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    comment_theme = generator._load_reply_theme_for_surface('comments')
    chat_theme = generator._load_reply_theme_for_surface('livechat')
    assert (comment_theme is not None) is (surface == 'comments')
    assert (chat_theme is not None) is (surface == 'livechat')
    assert queue.load_active_theme('livechat') == (native if surface == 'livechat' else None)


@pytest.mark.parametrize('surface', [None, '', 'all', 'comments,livechat', True])
def test_invalid_surface_never_reaches_generation_or_review_provider(surface):
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    generator._generation_lock = threading.RLock()
    generator._load_reply_theme = lambda:pytest.fail('Invalid surface reached context')
    result = generator.generate_reply_with_source('Question?', 'Aki', reply_surface=surface)
    assert result.text is None and result.source == 'unknown' and result.theme is None
    assert generator.generate_reply('Question?', 'Aki', reply_surface=surface) is None
    assert generator.inspect_reply({'text':'Question?', '_reply_surface':surface}, 'Draft')['reason'] == 'invalid_reply_surface'


def test_livechat_local_failure_never_invokes_paid_or_template_fallback(monkeypatch):
    chat, generator, _, _, _, _ = local_livechat_fixture(monkeypatch)
    generator.lm_studio_available = False
    generator._assess_comment = lambda data:assessment(data['text'])
    generator.grok_connector = SimpleNamespace(get_response=lambda **kw:pytest.fail('Local fallback called cloud'))
    generator.banter_engine = SimpleNamespace(process_input_enhanced=lambda *a:pytest.fail('Local fallback used template'))
    monkeypatch.setenv('YT_ENABLE_GROK_REPLIES', 'true')
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'actual-viewer-id') is None


def test_livechat_factory_binds_cached_generator_to_exact_channel_and_stream(monkeypatch):
    created = []
    def construct(**kwargs):
        created.append(kwargs)
        return SimpleNamespace(**kwargs)
    monkeypatch.setattr(CHAT, 'IntelligentLivechatReply', construct)
    monkeypatch.setattr(CHAT, '_livechat_reply_generators', {})
    first = CHAT.get_livechat_reply_generator(persona_key='same-persona', channel_id='channel-a', stream_title='Stream A')
    assert CHAT.get_livechat_reply_generator(persona_key='same-persona', channel_id='channel-a', stream_title='Stream A') is first
    second = CHAT.get_livechat_reply_generator(persona_key='same-persona', channel_id='channel-b', stream_title='Stream B')
    assert second is not first and second.channel_id == 'channel-b' and second.stream_title == 'Stream B'
    assert len(created) == 2


@pytest.mark.parametrize('source', ['template', 'grok', 'qwen', 'lm_studio:extra', 'qwen:unverified'])
def test_livechat_accepts_only_exact_local_generation_receipts(monkeypatch, source):
    chat, generator, native, _, _, _ = local_livechat_fixture(monkeypatch)
    generator.generate_reply_with_source = lambda **kw:GEN.ReplyGenerationResult('Draft', source,
        CONTEXT.normalize_reply_theme(native), {'reply_surface':'livechat'})
    generator.inspect_reply = lambda *a, **kw:pytest.fail('Nonlocal draft reached reviewer')
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer') is None


@pytest.mark.parametrize('review', [{'approved':False, 'review_provider':'lm_studio'},
                                   {'approved':True, 'review_provider':'grok'},
                                   {'approved':True, 'review_provider':'qwen'}, {'approved':True}])
def test_livechat_local_reply_requires_strict_approved_local_review(monkeypatch, review):
    chat, generator, _, _, _, _ = local_livechat_fixture(monkeypatch)
    generator.inspect_reply = lambda *a, **kw:review
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer') is None


@pytest.mark.parametrize('invalid', [{'source_command_id':123}, {'handles':'invalid'}, {'handles':[123]}])
@pytest.mark.parametrize('entrypoint', ['generate', 'local_helper'])
def test_malformed_native_theme_blocks_all_provider_work(monkeypatch, invalid, entrypoint):
    chat, _, native, _, calls, _ = local_livechat_fixture(monkeypatch)
    native.update(invalid)
    cloud_calls = []
    chat.grok_available = True
    def grok(**kwargs):
        cloud_calls.append(kwargs)
        return 'Film details are on the website.' if len(cloud_calls) == 1 else json.dumps(helper.GOOD)
    chat.grok_client = SimpleNamespace(get_response=grok)
    monkeypatch.setattr(CHAT.random, 'random', lambda:1)
    assert CONTEXT.normalize_reply_theme(native) is None
    if entrypoint == 'generate':
        result = chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer')
    else:
        result = chat._generate_local_theme_response('Where can I watch the film?', 'Aki', 'viewer', 'USER', False, native)
    assert result is None
    assert calls == [] and cloud_calls == []


def test_busy_shared_generator_rejects_livechat_without_waiting_or_calling_provider(monkeypatch):
    chat, generator, _, _, _, _ = local_livechat_fixture(monkeypatch)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    def hold_lock():
        with generator._generation_lock:
            entered.set()
            assert release.wait(3)
    owner = threading.Thread(target=hold_lock)
    owner.start()
    assert entered.wait(1)
    results = []
    def reply():
        results.append(chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer'))
        finished.set()
    worker = threading.Thread(target=reply)
    worker.start()
    try:
        assert finished.wait(0.5), 'Livechat waited on an unrelated comment generation lock'
        assert results == [None]
    finally:
        release.set()
        owner.join(3)
        worker.join(3)


def test_inspection_rejects_surface_mismatch_before_provider():
    generator = object.__new__(GEN.IntelligentReplyGenerator)
    review = generator.inspect_reply({'text':'Question?', '_reply_surface':'comments',
        '_generation_context':{'reply_surface':'livechat'}}, 'Draft')
    assert review == {'approved':False, 'reason':'invalid_reply_surface'}


def test_livechat_fallback_retains_private_native_snapshot_through_sender_delay(monkeypatch):
    chat, _, native, current, _, _ = local_livechat_fixture(monkeypatch)
    result = chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer')
    sender_module = helper.definitions('_local_theme_sender', 'modules/communication/livechat/src/chat_sender.py')
    sender_module.stop_active = lambda:False
    sender_module._env_truthy = lambda name, default='false':name in {'YT_AUTOMATION_ENABLED','YT_LIVECHAT_SEND_ENABLED'}
    sender_module._convert_unicode_tags_to_emoji = lambda value:value
    inserted = []
    sender = object.__new__(sender_module.ChatSender)
    sender._send_lock = asyncio.Lock()
    sender.bot_channel_id, sender.live_chat_id = 'creator', 'live-fixture'
    sender.random_delay_enabled, sender.send_delay = False, 0
    sender._is_valid_mention = lambda username:True
    sender.youtube = SimpleNamespace(liveChatMessages=lambda:SimpleNamespace(insert=lambda **kw:inserted.append(kw)))
    async def replace_theme(*args):
        native['surfaces'].append('comments')  # A shallow payload copy would silently change too.
    sender._apply_global_throttling = replace_theme
    assert not asyncio.run(sender.send_message(result))
    assert result.theme_snapshot['surfaces'] == ['livechat']
    assert inserted == []


@pytest.mark.parametrize('surface', ['comments', 'livechat'])
def test_inspector_lock_preserves_comment_serialization_and_rejects_busy_livechat(monkeypatch, surface):
    _, generator, _, _, calls, _ = local_livechat_fixture(monkeypatch)
    generator._load_reply_theme = lambda:None
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    results = []
    def hold():
        with generator._generation_lock:
            entered.set()
            assert release.wait(3)
    owner = threading.Thread(target=hold)
    def inspect():
        results.append(generator.inspect_reply({'text':'Question?', '_reply_surface':surface}, 'Draft'))
        finished.set()
    worker = threading.Thread(target=inspect)
    owner.start()
    assert entered.wait(1)
    worker.start()
    try:
        assert finished.wait(0.1) is (surface == 'livechat')
        assert calls == []
    finally:
        release.set()
        owner.join(3)
        worker.join(3)
    assert not owner.is_alive() and not worker.is_alive()
    if surface == 'livechat':
        assert results == [{'approved':False, 'reason':'review_busy'}]
    else:
        assert len(calls) == 1


@pytest.mark.parametrize('stage', ['assessment', 'writer', 'review'])
def test_livechat_http_failure_never_enters_embedded_inference(monkeypatch, stage):
    chat, generator, _, _, calls, original_post = local_livechat_fixture(monkeypatch)
    generator.qwen_engine = SimpleNamespace(generate_response=lambda **kw:pytest.fail('Embedded inference started'))
    failed_call = {'assessment':1, 'writer':2, 'review':3}[stage]
    def post(*args, **kwargs):
        if len(calls) + 1 == failed_call:
            calls.append(kwargs['json'])
            return SimpleNamespace(status_code=503, text='Fixture unavailable')
        return original_post(*args, **kwargs)
    monkeypatch.setattr(GEN, 'requests', SimpleNamespace(post=post), raising=False)
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer') is None
    assert len(calls) == failed_call


@pytest.mark.parametrize('stage', [1, 2, 3])
def test_cancelled_local_http_result_cannot_start_next_stage_or_return_payload(monkeypatch, stage):
    chat, _, _, _, calls, original_post = local_livechat_fixture(monkeypatch)
    cancelled = threading.Event()
    def post(*args, **kwargs):
        response = original_post(*args, **kwargs)
        if len(calls) == stage:
            cancelled.set()
        return response
    monkeypatch.setattr(GEN, 'requests', SimpleNamespace(post=post), raising=False)
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer', cancel_event=cancelled) is None
    assert len(calls) == stage


@pytest.mark.parametrize('preparation', ['news', 'history', 'voice'])
def test_cancellation_during_preparation_prevents_new_provider_dispatch(monkeypatch, preparation):
    chat, generator, _, _, calls, _ = local_livechat_fixture(monkeypatch)
    cancelled = threading.Event()
    def prepare(*args, **kwargs):
        cancelled.set()
        return ''
    if preparation == 'news':
        chat.grok_available = True
        chat.grok_client = SimpleNamespace(get_response=lambda **kw:pytest.fail('Cancelled work started Grok'))
        monkeypatch.setitem(sys.modules, 'modules.communication.livechat.src.news_context_provider',
                            SimpleNamespace(get_news_context=prepare))
    else:
        setattr(generator, '_load_personalization_context' if preparation == 'history' else
                '_load_voice_memory_context', prepare)
    assert chat.generate_reply('Where can I watch the film?', 'Aki', 'viewer', cancel_event=cancelled) is None
    assert len(calls) == (0 if preparation == 'news' else 1)


def livechat_processor_fixture(monkeypatch, reply):
    module = helper.definitions('_bounded_livechat_processor', 'modules/communication/livechat/src/message_processor.py')
    monkeypatch.setitem(sys.modules, 'modules.communication.livechat.src.intelligent_livechat_reply', CHAT)
    module._env_truthy = lambda name, default='false':True
    module._sanitize_username = lambda value:value
    processor = object.__new__(module.MessageProcessor)
    processor.intelligent_reply = reply
    processor.self_improvement = SimpleNamespace(observe_command=lambda *a:None)
    processor.intelligent_throttle = None
    processor.announced_joins = {'viewer'}
    processor._check_pqn_command = lambda text:False
    processor._update_trigger_time = lambda author:None
    processor._generate_banter_response = processor._generate_fallback_response = lambda *a:pytest.fail('Unreviewed fallback')
    return processor


@pytest.mark.parametrize('blocked_call', [1, 2])
def test_actual_async_caller_keeps_heartbeat_and_discards_timed_out_grok_without_local_fallback(monkeypatch, blocked_call):
    chat, _, native, _, calls, _ = local_livechat_fixture(monkeypatch)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    cloud_calls, captured, ticks = [], [], []
    chat.grok_available = True
    def grok(**kwargs):
        cloud_calls.append(kwargs)
        if len(cloud_calls) == blocked_call:
            entered.set()
            assert release.wait(3)
        return 'Film details are on the website.' if len(cloud_calls) == 1 else json.dumps(helper.GOOD)
    chat.grok_client = SimpleNamespace(get_response=grok)
    original_generate = chat.generate_reply
    def generate(**kwargs):
        captured.append(kwargs['cancel_event'])
        try:
            return original_generate(**kwargs)
        finally:
            finished.set()
    processor = livechat_processor_fixture(monkeypatch, SimpleNamespace(generate_reply=generate))
    real_wait_for = asyncio.wait_for
    async def short_wait(awaitable, *, timeout):
        assert timeout == 10.0
        return await real_wait_for(awaitable, timeout=0.08)
    monkeypatch.setattr(asyncio, 'wait_for', short_wait)
    async def run():
        task = asyncio.create_task(processor._await_intelligent_reply(theme_snapshot=native,
            message='Where can I watch the film?', username='Aki', user_id='viewer'))
        try:
            while not task.done():
                ticks.append(1)
                await asyncio.sleep(0.005)
            assert entered.is_set() and len(ticks) >= 3
            assert await task is None and captured[0].is_set()
        finally:
            release.set()
        while not finished.is_set():
            await asyncio.sleep(0.001)
    asyncio.run(run())
    assert len(cloud_calls) == blocked_call and calls == []


@pytest.mark.parametrize('payload', ['plain', 'wrong_theme', 'changed_text'])
def test_themed_async_caller_requires_exact_reviewed_payload(monkeypatch, payload):
    _, _, native, _, _, _ = local_livechat_fixture(monkeypatch)
    value = ('A plain string' if payload == 'plain' else CHAT.ReviewedLivechatReply('Reviewed',
             {**native, 'source_command_id':'other'} if payload == 'wrong_theme' else native))
    if payload == 'changed_text':
        value.reviewed_text = 'Different'
    processor = livechat_processor_fixture(monkeypatch, SimpleNamespace(generate_reply=lambda **kw:value))
    assert asyncio.run(processor._await_intelligent_reply(theme_snapshot=native, message='Question?')) is None


@pytest.mark.parametrize('mode', ['cleared', 'superseded'])
def test_theme_changed_before_worker_starts_cannot_enable_pattern_fallback(monkeypatch, mode):
    chat, _, native, current, calls, _ = local_livechat_fixture(monkeypatch)
    current[0] = None if mode == 'cleared' else {**native, 'source_command_id':'other'}
    assert chat.generate_reply('song', 'Aki', 'viewer', expected_theme_snapshot=native) is None
    assert calls == []


def test_actual_trigger_caller_retains_themed_mode_after_theme_clear(monkeypatch):
    _, _, native, current, _, _ = local_livechat_fixture(monkeypatch)
    processor = livechat_processor_fixture(monkeypatch, SimpleNamespace())
    entries = []
    async def reject(**kwargs):
        entries.append(kwargs)
        assert kwargs['theme_snapshot'] == native
        current[0] = None
        return None
    processor._await_intelligent_reply = reject
    message = {'text':'Where can I watch the film?', 'author_name':'Aki', 'author_id':'viewer',
               'is_moderator':True, 'has_trigger':True}
    assert asyncio.run(processor.generate_response(message)) is None
    assert len(entries) == 1


def test_timed_out_async_caller_discards_late_payload_even_if_worker_ignores_cancel(monkeypatch):
    _, _, native, _, _, _ = local_livechat_fixture(monkeypatch)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    cancelled, produced = [], []
    def generate(**kwargs):
        cancelled.append(kwargs['cancel_event'])
        entered.set()
        assert release.wait(3)
        produced.append(CHAT.ReviewedLivechatReply('@Aki Late answer', native))
        finished.set()
        return produced[0]
    processor = livechat_processor_fixture(monkeypatch, SimpleNamespace(generate_reply=generate))
    real_wait_for = asyncio.wait_for
    async def short_wait(awaitable, *, timeout):
        assert timeout == 10.0
        return await real_wait_for(awaitable, timeout=0.05)
    monkeypatch.setattr(asyncio, 'wait_for', short_wait)
    async def run():
        try:
            result = await processor._await_intelligent_reply(theme_snapshot=native, message='Question?')
            assert entered.is_set() and result is None and cancelled[0].is_set()
        finally:
            release.set()
        while not finished.is_set():
            await asyncio.sleep(0.001)
        assert result is None
    asyncio.run(run())
    assert len(produced) == 1


@pytest.mark.parametrize('path', ['trigger', 'maga'])
def test_actual_callers_preserve_identity_and_accept_reviewed_payload_after_existing_gates(monkeypatch, path):
    _, _, native, _, _, _ = local_livechat_fixture(monkeypatch)
    captured, updates = [], []
    value = CHAT.ReviewedLivechatReply('@Aki The film details are on the website.', native)
    def generate(**kwargs):
        captured.append(kwargs)
        return value
    processor = livechat_processor_fixture(monkeypatch, SimpleNamespace(generate_reply=generate))
    processor.last_global_maga_time, processor.global_maga_cooldown = 0, 60
    processor._is_maga_rate_limited = lambda author:False
    processor._update_maga_time = lambda author:updates.append(author)
    message = {'text':'Where can I watch the film?', 'author_name':'Aki', 'author_id':'viewer',
               'is_moderator':True, 'is_member':True, 'has_trigger':path == 'trigger', 'has_maga':path == 'maga'}
    assert asyncio.run(processor.generate_response(message)) is value
    assert len(captured) == 1
    assert captured[0]['user_id'] == 'viewer' and captured[0]['username'] == 'Aki'
    assert captured[0]['role'] == 'MOD' and captured[0]['is_member'] is True
    assert captured[0]['expected_theme_snapshot'] == native and captured[0]['cancel_event'].is_set()
    assert updates == (['viewer'] if path == 'maga' else [])


def test_default_comment_generation_still_waits_for_existing_serialization_lock(monkeypatch):
    _, generator, _, _, _, _ = local_livechat_fixture(monkeypatch)
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()
    def hold():
        with generator._generation_lock:
            entered.set()
            assert release.wait(3)
    generated, results = [], []
    def generate(*args, **kwargs):
        generated.append(kwargs['reply_surface'])
        return 'Comment answer'
    generator.generate_reply = generate
    generator._last_llm_source = 'lm_studio'
    owner = threading.Thread(target=hold)
    def reply():
        results.append(generator.generate_reply_with_source('Question?', 'Aki'))
        finished.set()
    worker = threading.Thread(target=reply)
    owner.start()
    assert entered.wait(1)
    worker.start()
    try:
        assert not finished.wait(0.1) and generated == []
    finally:
        release.set()
        owner.join(3)
        worker.join(3)
    assert not owner.is_alive() and not worker.is_alive()
    assert generated == ['comments'] and results[0].text == 'Comment answer'
