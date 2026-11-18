"""Local broadcast/context reader contracts; every state file is temporary."""
import json
from types import SimpleNamespace

import pytest

from modules.communication.livechat.src import operator_command_queue as queue
from modules.communication.video_comments.src import commenting_control_plane as control


@pytest.fixture
def files(tmp_path, monkeypatch):
    state = tmp_path / 'shared.json'
    legacy = tmp_path / 'legacy.json'
    legacy.write_text(json.dumps({
        'enabled': True, 'promo_handles': ['legacy'], 'promo_message': 'legacy message',
        'updated_at_unix': 900.0, 'updated_by': 'legacy operator',
    }), encoding='utf-8')
    monkeypatch.setenv('YT_012_MANIFEST_STATE_FILE', str(state))
    monkeypatch.setattr(control.time, 'time', lambda: 1000.0)
    return SimpleNamespace(state=state, legacy=legacy)


def write_context(files, **changes):
    context = {'surfaces': ['comments'], 'message': '  shared message  ', 'expires_at_unix': 1100}
    context.update(changes)
    files.state.write_text(json.dumps({'version': 1, 'active_context': context}), encoding='utf-8')


def assert_legacy(files):
    result = control.load_broadcast(files.legacy)
    assert result == control.CommentingBroadcast(
        enabled=True, promo_handles=['@legacy'], promo_message='legacy message',
        updated_at_unix=900.0, updated_by='legacy operator',
    )


@pytest.mark.parametrize('surfaces,expiry', [(['comments'], 1100), (['livechat', 'comments'], 1100.5)])
def test_valid_shared_context_precedes_legacy(files, surfaces, expiry):
    write_context(files, surfaces=surfaces, expires_at_unix=expiry)
    before = files.state.read_bytes(), files.legacy.read_bytes()
    result = control.load_broadcast(files.legacy)
    assert result.enabled is True
    assert result.promo_message == 'shared message'
    assert result.promo_handles == []
    assert result.updated_by == '012_manifest'
    assert (files.state.read_bytes(), files.legacy.read_bytes()) == before


def test_shared_message_at_maximum_length_is_valid(files):
    write_context(files, message='x' * 500)
    assert control.load_broadcast(files.legacy).promo_message == 'x' * 500


def test_queue_and_reader_share_relative_configured_path_independent_of_cwd(files, tmp_path, monkeypatch):
    checkout = tmp_path / 'checkout'
    files.state = checkout / 'memory' / 'shared.json'
    files.state.parent.mkdir(parents=True)
    write_context(files)
    monkeypatch.setattr(queue, 'REPO_ROOT', checkout)
    monkeypatch.setenv('YT_012_MANIFEST_STATE_FILE', 'memory/shared.json')
    other_cwd = tmp_path / 'unrelated-cwd'
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    owner = queue.OperatorCommandQueue(
        SimpleNamespace(), command_path=tmp_path / 'commands.json',
        acknowledgement_path=tmp_path / 'acks.json',
    )
    assert control.resolve_manifest_state_path is queue.resolve_manifest_state_path
    assert owner.state_path == files.state
    assert control.load_broadcast(files.legacy).promo_message == 'shared message'


@pytest.mark.parametrize('field,value', [
    ('surfaces', None), ('surfaces', 'comments'), ('surfaces', {'comments': True}),
    ('surfaces', []), ('surfaces', ['livechat']), ('surfaces', ['comments', None]),
    ('surfaces', ['comments', []]), ('surfaces', ['comments', 'unknown']),
    ('message', None), ('message', True), ('message', 123), ('message', []),
    ('message', {}), ('message', '   '), ('message', 'x' * 501),
    ('expires_at_unix', None),
    ('expires_at_unix', '1100'), ('expires_at_unix', float('nan')),
    ('expires_at_unix', float('inf')), ('expires_at_unix', float('-inf')),
    ('expires_at_unix', 999), ('expires_at_unix', 1000),
    ('expires_at_unix', 10 ** 400), ('expires_at_unix', {}), ('expires_at_unix', []),
])
def test_invalid_or_expired_shared_context_retains_legacy(files, field, value):
    write_context(files, **{field: value})
    assert_legacy(files)


@pytest.mark.parametrize('expiry', [True, False])
def test_boolean_expiry_is_rejected_even_when_numeric_value_would_be_future(files, monkeypatch, expiry):
    monkeypatch.setattr(control.time, 'time', lambda: -1.0)
    write_context(files, expires_at_unix=expiry)
    assert_legacy(files)


@pytest.mark.parametrize('version', [None, True, 1.0, '1', 2])
def test_only_integer_schema_version_one_is_current(files, version):
    write_context(files)
    document = json.loads(files.state.read_text(encoding='utf-8'))
    document['version'] = version
    files.state.write_text(json.dumps(document), encoding='utf-8')
    assert_legacy(files)


@pytest.mark.parametrize('document', [
    [], None, {}, {'version': 1}, {'version': 1, 'active_context': None},
    {'version': 1, 'active_context': []}, {'version': 1, 'active_context': 'context'},
])
def test_non_context_state_retains_legacy(files, document):
    files.state.write_text(json.dumps(document), encoding='utf-8')
    assert_legacy(files)


@pytest.mark.parametrize('content', [b'{', b'\xff', None])
def test_unreadable_or_missing_shared_state_retains_legacy(files, content):
    if content is not None:
        files.state.write_bytes(content)
    assert_legacy(files)


def test_legacy_set_clear_and_missing_defaults_remain_available(files):
    files.legacy.unlink()
    assert control.load_broadcast(files.legacy) == control.CommentingBroadcast()
    saved = control.set_promo(enabled=True, promo_handles=['sample'], promo_message='legacy update',
                              updated_by='local fixture', path=files.legacy)
    assert saved.promo_handles == ['@sample']
    assert control.load_broadcast(files.legacy) == saved
    cleared = control.clear_promo(files.legacy)
    assert cleared.enabled is False
    assert cleared.promo_message == ''
    assert cleared.promo_handles == []
    assert control.load_broadcast(files.legacy) == cleared


@pytest.mark.parametrize('shared_end', ['expiry', 'clear'])
@pytest.mark.parametrize('legacy_exists', [True, False])
def test_legacy_edit_during_shared_context_does_not_persist_shared_text(
    files, monkeypatch, shared_end, legacy_exists,
):
    if not legacy_exists:
        files.legacy.unlink()
    write_context(files)
    shared_before = files.state.read_bytes()

    saved = control.set_promo(promo_handles=['updated'], path=files.legacy)
    assert saved.promo_message == ('legacy message' if legacy_exists else '')
    assert saved.enabled is legacy_exists
    assert saved.promo_handles == ['@updated']
    assert json.loads(files.legacy.read_text(encoding='utf-8')) == saved.to_dict()
    assert files.state.read_bytes() == shared_before
    assert control.load_broadcast(files.legacy).promo_message == 'shared message'

    if shared_end == 'expiry':
        monkeypatch.setattr(control.time, 'time', lambda: 1100.0)
    else:
        files.state.write_text(json.dumps({'version': 1, 'active_context': None}), encoding='utf-8')
    assert control.load_broadcast(files.legacy) == saved


@pytest.mark.parametrize('shared_end', ['expiry', 'clear'])
def test_legacy_clear_during_shared_context_preserves_legacy_provenance(files, monkeypatch, shared_end):
    write_context(files)
    shared_before = files.state.read_bytes()

    cleared = control.clear_promo(files.legacy)
    assert cleared == control.CommentingBroadcast(updated_at_unix=1000.0, updated_by='legacy operator')
    assert json.loads(files.legacy.read_text(encoding='utf-8')) == cleared.to_dict()
    assert files.state.read_bytes() == shared_before
    assert control.load_broadcast(files.legacy).promo_message == 'shared message'

    if shared_end == 'expiry':
        monkeypatch.setattr(control.time, 'time', lambda: 1100.0)
    else:
        files.state.write_text(json.dumps({'version': 1, 'active_context': None}), encoding='utf-8')
    assert control.load_broadcast(files.legacy) == cleared
