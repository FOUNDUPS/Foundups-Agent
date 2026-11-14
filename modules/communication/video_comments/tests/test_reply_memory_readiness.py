"""Offline ready-only reply memory controls through complete owner definitions."""
import asyncio
import importlib.util
import json
import logging
from pathlib import Path
import sys
from threading import Event, RLock
from types import SimpleNamespace

import pytest


GROUNDING_FACT = 'Watch the film through the festival streaming library.'


class Embedding:
    def __init__(self, calls, after=None):
        self.calls, self.after = calls, after

    def encode(self, *_args, **_kwargs):
        self.calls.append('encode')
        if self.after:
            self.after()
        return SimpleNamespace(tolist=lambda: [0.1] * 384)


class Collection:
    def __init__(self, calls, after_count=None, after_query=None):
        self.calls, self.after_count, self.after_query = calls, after_count, after_query

    def count(self):
        self.calls.append('count')
        if self.after_count:
            self.after_count()
        return 1

    def query(self, **kwargs):
        self.calls.append(('query', kwargs.get('where')))
        if self.after_query:
            self.after_query()
        return {'documents': [[GROUNDING_FACT]],
                'metadatas': [[{'video_id': 'fixture-film', 'title': 'Fixture film',
                               'channel': 'fixture', 'start_time': '0:10', 'end_time': '0:20'}]],
                'distances': [[0.1]]}


@pytest.fixture
def owners(monkeypatch):
    path = Path(__file__).with_name('test_chat_manifest_inspection.py')
    spec = importlib.util.spec_from_file_location('_memory_definition_helpers', path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.GEN.select_channel_personality = helper.CONTEXT.select_channel_personality
    helper.PROCESSOR.INTELLIGENT_REPLIES_AVAILABLE = True
    voice = helper.definitions('_ready_voice', 'modules/ai_intelligence/digital_twin/src/voice_memory.py')
    video = helper.definitions('_ready_video', 'holo_index/core/video_search.py')
    monkeypatch.setitem(sys.modules, 'modules.ai_intelligence.digital_twin.src.voice_memory', voice)
    monkeypatch.setitem(sys.modules, 'holo_index.core.video_search', video)
    monkeypatch.setenv('VOICE_MEMORY_VIDEO_INDEX', 'true')
    return SimpleNamespace(helper=helper, voice=voice, video=video)


def ready_index(owners, calls, **changes):
    index = object.__new__(owners.video.VideoContentIndex)
    index.model = Embedding(calls, changes.get('after_encode'))
    index.collection = Collection(calls, changes.get('after_count'), changes.get('after_query'))
    return index


def generator(owners):
    item = object.__new__(owners.helper.GEN.IntelligentReplyGenerator)
    item._generation_lock = RLock()
    item._load_reply_theme_for_surface = lambda _surface: None
    item._semantic_reply_history = lambda *_args: (True, set())
    item._load_personalization_context = lambda **_kwargs: ''
    item._voice_memory_enabled, item._voice_memory = True, None
    calls = []
    def shared(**kwargs):
        calls.append(kwargs)
        text = 'Where can I watch the film?'
        assessment = dict(intent='question', meaning='Asks where to watch the film', question=text,
            stance='unclear', uncertainty='', evidence_quote=text, strategy='answer', theme_relevant=False)
        grounded = GROUNDING_FACT in kwargs['prompt']
        answer = json.dumps(assessment) if kwargs['stage'] == 'assess' else (
            json.dumps(owners.helper.GOOD) if kwargs['stage'] == 'review'
            else (GROUNDING_FACT if grounded
                  else 'Which film do you mean?'))
        return SimpleNamespace(success=True, response=answer, provider='lm_studio_local',
                               model='qwen3.5-4b', route_id='synthetic-shared-route', reason=None)
    item._model_gateway = SimpleNamespace(call_youtube_task=shared)
    return item, calls


def processor(owners, item):
    owner = owners.helper.PROCESSOR
    instance = object.__new__(owner.CommentProcessor)
    instance.target_channel_id = 'receiving-fixture'
    async def heartbeat(*_args): return None
    instance._thinking_heartbeat = heartbeat
    owner.get_reply_generator = lambda: item
    return instance


async def generate_and_review(instance):
    data = dict(text='Where can I watch the film?', author_name='Aki', channel_id='viewer-fixture')
    text, source = await instance._await_reply_generation(data)
    review = await instance._inspect_reply(data, text) if text else None
    return text, source, review


def test_cold_first_comment_still_generates_and_reviews_without_cold_enrichment(owners, monkeypatch):
    item, calls = generator(owners)
    attempted = []
    def cold_probe():
        attempted.append('probe')
        return False
    def cold_constructor(*_args, **_kwargs):
        attempted.append('constructor')
        raise AssertionError('Cold index construction forbidden')
    def cold_model(*_args, **_kwargs):
        attempted.append('embedding_loader')
        raise AssertionError('Cold embedding load forbidden')
    monkeypatch.setattr(owners.voice, '_probe_chromadb_health', cold_probe)
    monkeypatch.setattr(owners.video.VideoContentIndex, '__init__', cold_constructor)
    monkeypatch.setattr(owners.video.VideoContentIndex, '_get_model', cold_model)
    text, source, review = asyncio.run(generate_and_review(processor(owners, item)))
    assert text == 'Which film do you mean?' and source == 'lm_studio' and review['approved'] is True
    assert [call['stage'] for call in calls] == ['assess', 'write', 'review']
    assert attempted == [] and owners.voice._video_index is None
    assert 'never invent' in calls[1]['system_prompt'].lower()
    assert 'Where can I watch the film?' in calls[1]['prompt']
    assert GROUNDING_FACT not in calls[1]['prompt']
    reviewed = json.loads(calls[2]['prompt'])
    assert reviewed['comment'] == 'Where can I watch the film?'
    assert reviewed['candidate'] == text
    assert reviewed['supplied_generation_context']['verified_memory'] == ''


def test_warm_ready_video_memory_is_supplied_to_the_reviewed_writer(owners):
    item, calls = generator(owners)
    reads = []
    owners.voice._video_index = ready_index(owners, reads)
    text, source, review = asyncio.run(generate_and_review(processor(owners, item)))
    assert text and source == 'lm_studio' and review['approved'] is True
    assert [call['stage'] for call in calls] == ['assess', 'write', 'review']
    assert reads == ['count', 'encode', ('query', None)]
    assert GROUNDING_FACT in calls[1]['prompt']
    assert 'Where can I watch the film?' in calls[1]['prompt']
    reviewed = json.loads(calls[2]['prompt'])
    assert reviewed['comment'] == 'Where can I watch the film?' and reviewed['candidate'] == text
    assert GROUNDING_FACT in reviewed['supplied_generation_context']['verified_memory']


@pytest.mark.parametrize('cached', [None, False])
def test_ready_only_query_preserves_cold_or_unavailable_cache_without_probe(owners, monkeypatch, cached):
    owners.voice._video_index = cached
    attempts = []
    monkeypatch.setattr(owners.voice, '_probe_chromadb_health', lambda: attempts.append(True) or False)
    memory = owners.voice.VoiceMemory(include_videos=True)
    assert memory.query('Synthetic question', allow_cold_init=False) == []
    assert owners.voice._video_index is cached and attempts == []


def test_cached_index_without_loaded_embedding_model_does_not_load_or_query(owners, monkeypatch):
    calls = []
    index = ready_index(owners, calls)
    index.model = None
    monkeypatch.setattr(index, '_get_model', lambda: calls.append('cold_model'))
    owners.voice._video_index = index
    assert owners.voice.VoiceMemory().query('Synthetic question', allow_cold_init=False) == []
    assert calls == []


def test_ready_only_embedding_does_not_substitute_legacy_zero_vector(owners, monkeypatch):
    index = object.__new__(owners.video.VideoContentIndex)
    index.model = None
    attempts = []
    monkeypatch.setattr(index, '_get_model', lambda: attempts.append(True))
    assert index._get_embedding('Synthetic question', allow_cold_init=False) is None
    assert attempts == []


def test_embedding_model_lost_during_count_never_triggers_a_cold_load(owners, monkeypatch):
    calls = []
    index = ready_index(owners, calls)
    index.collection.after_count = lambda: setattr(index, 'model', None)
    monkeypatch.setattr(index, '_get_model', lambda: calls.append('cold_model'))
    assert index.search('Synthetic question', allow_cold_init=False) == []
    assert calls == ['count']


def test_cancellation_during_history_does_not_begin_voice_enrichment(owners, monkeypatch):
    item, calls = generator(owners)
    started, deadlines = Event(), []
    def history(**_kwargs):
        started.set()
        assert item._current_cancel_event.wait(1)
        return ''
    item._load_personalization_context = history
    attempts = []
    monkeypatch.setattr(owners.voice, '_probe_chromadb_health', lambda: attempts.append(True) or False)
    real_wait = asyncio.wait_for
    async def bounded(awaitable, *, timeout):
        deadlines.append(timeout)
        task = asyncio.create_task(awaitable)
        assert await real_wait(asyncio.to_thread(started.wait, 1), timeout=2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        raise asyncio.TimeoutError
    monkeypatch.setattr(owners.helper.PROCESSOR.asyncio, 'wait_for', bounded)
    text, source, review = asyncio.run(generate_and_review(processor(owners, item)))
    assert text is None and source == 'unknown' and review is None
    assert [call['stage'] for call in calls] == ['assess'] and attempts == []
    assert deadlines == [10.0]


def test_cancelled_cold_probe_cannot_start_index_construction(owners, monkeypatch):
    token, constructors = Event(), []
    def probe(): token.set(); return True
    monkeypatch.setattr(owners.voice, '_probe_chromadb_health', probe)
    monkeypatch.setattr(owners.video, 'VideoContentIndex', lambda: constructors.append(True))
    assert owners.voice.VoiceMemory().query('Synthetic question', cancel_event=token) == []
    assert constructors == [] and owners.voice._video_index is None


def test_precancelled_memory_query_starts_neither_local_nor_video_stage(owners, monkeypatch):
    token, calls = Event(), []
    token.set()
    memory = owners.voice.VoiceMemory()
    memory.documents, memory.vectorizer = [{'text': 'Synthetic fact'}], object()
    monkeypatch.setattr(memory, '_query_tfidf', lambda *_args: calls.append('local') or [])
    monkeypatch.setattr(memory, '_query_holoindex', lambda *_args, **_kwargs: calls.append('video') or [])
    assert memory.query('Synthetic question', cancel_event=token) == [] and calls == []


def test_cancellation_after_local_memory_prevents_video_stage(owners, monkeypatch):
    token, calls = Event(), []
    memory = owners.voice.VoiceMemory()
    memory.documents, memory.vectorizer = [{'text': 'Synthetic fact'}], object()
    def local(*_args): token.set(); return [{'text': 'Synthetic fact', 'score': 1}]
    monkeypatch.setattr(memory, '_query_tfidf', local)
    monkeypatch.setattr(memory, '_query_holoindex', lambda *_args, **_kwargs: calls.append('video') or [])
    assert memory.query('Synthetic question', cancel_event=token) == [] and calls == []


@pytest.mark.parametrize('phase', ['before_count', 'after_count', 'after_encode', 'after_query'])
def test_cancelled_video_search_never_begins_a_later_stage_or_returns_context(owners, phase):
    token, calls = Event(), []
    index = ready_index(owners, calls,
        after_count=token.set if phase == 'after_count' else None,
        after_encode=token.set if phase == 'after_encode' else None,
        after_query=token.set if phase == 'after_query' else None)
    if phase == 'before_count': token.set()
    assert index.search('Synthetic question', allow_cold_init=False, cancel_event=token) == []
    expected = {'before_count': [], 'after_count': ['count'], 'after_encode': ['count', 'encode'],
                'after_query': ['count', 'encode', ('query', None)]}
    assert calls == expected[phase]


def test_default_voice_query_preserves_legacy_private_call_signature(owners, monkeypatch):
    memory = owners.voice.VoiceMemory()
    calls = []
    def legacy(text, k):
        calls.append((text, k))
        return [{'text': 'Supplied legacy context', 'score': 0.8}]
    monkeypatch.setattr(memory, '_query_holoindex', legacy)
    assert memory.query('Synthetic question', 2) == [{'text': 'Supplied legacy context', 'score': 0.8}]
    assert calls == [('Synthetic question', 2)]


def test_default_voice_query_retains_existing_cold_initialization(owners, monkeypatch):
    calls = []
    class Index:
        def __init__(self): calls.append('construct')
        def search(self, text, k): calls.append(('search', k)); return []
    monkeypatch.setattr(owners.voice, '_probe_chromadb_health', lambda: calls.append('probe') or True)
    monkeypatch.setattr(owners.video, 'VideoContentIndex', Index)
    assert owners.voice.VoiceMemory().query('Synthetic question', 2) == []
    assert calls == ['probe', 'construct', ('search', 2)]
    assert isinstance(owners.voice._video_index, Index)


def test_default_video_search_keeps_embedding_signature_and_channel_filter(owners, monkeypatch):
    calls = []
    index = ready_index(owners, calls)
    def embedding(text): calls.append(('legacy_embedding', text)); return [0.1] * 384
    monkeypatch.setattr(index, '_get_embedding', embedding)
    matches = index.search('Synthetic question', channel='fixture')
    assert len(matches) == 1 and matches[0].video_id == 'fixture-film'
    assert calls == ['count', ('legacy_embedding', 'Synthetic question'), ('query', {'channel': 'fixture'})]


def test_legacy_missing_model_embedding_fallback_is_unchanged(owners, monkeypatch):
    index = object.__new__(owners.video.VideoContentIndex)
    index.model = None
    monkeypatch.setattr(index, '_get_model', lambda: None)
    assert index._get_embedding('Synthetic question') == [0.0] * 384


def test_video_opt_out_still_avoids_lookup(owners, monkeypatch):
    memory, calls = owners.voice.VoiceMemory(include_videos=False), []
    monkeypatch.setattr(memory, '_query_holoindex', lambda *_args, **_kwargs: calls.append(True) or [])
    assert memory.query('Synthetic question', allow_cold_init=False) == [] and calls == []


def test_cold_skip_diagnostic_contains_no_input_or_model_payload(owners, caplog):
    caplog.set_level(logging.DEBUG)
    assert owners.voice.VoiceMemory().query('SYNTHETIC_PRIVATE_COMMENT', allow_cold_init=False) == []
    assert 'cold' in caplog.text.lower() and 'skip' in caplog.text.lower()
    assert 'SYNTHETIC_PRIVATE_COMMENT' not in caplog.text


def test_reply_owner_requests_ready_only_memory_with_current_cancellation(owners):
    item, _calls = generator(owners)
    token, seen = Event(), []
    item._current_cancel_event = token
    class ReadyMemory:
        def query(self, text, k, *, allow_cold_init, cancel_event):
            seen.append((k, allow_cold_init, cancel_event))
            return []
    item._voice_memory = ReadyMemory()
    assert item._load_voice_memory_context('Synthetic question') == ''
    assert seen == [(3, False, token)]


def test_unsupported_ready_only_collaborator_never_retries_cold_legacy_query(owners):
    item, calls = generator(owners)
    legacy_calls = []
    class LegacyMemory:
        def query(self, text, k):
            legacy_calls.append((text, k))
            return [{'text': 'Unqualified legacy context', 'score': 1}]
    item._voice_memory = LegacyMemory()
    assert item._load_voice_memory_context('Synthetic question') == ''
    assert legacy_calls == []
