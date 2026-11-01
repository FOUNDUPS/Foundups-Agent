"""Offline private queue contracts; native IDs and disposable queue files only."""
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.communication.livechat.src import operator_command_queue as queue_module
from modules.communication.livechat.src import video_policy

CHANNEL = 'UC' + 'a' * 22
OTHER_CHANNEL = 'UC' + 'b' * 22
VIDEO = 'a' * 11
OTHER_VIDEO = 'b' * 11


@pytest.fixture
def queue(tmp_path, monkeypatch):
    # Never copy inherited credentials into mocks/assertions or queue payloads.
    monkeypatch.setattr(queue_module, 'gate_snapshot', lambda: (_ for _ in ()).throw(AssertionError('public_gate_not_allowed')))
    instance = queue_module.OperatorCommandQueue(None, tmp_path / 'inbox.json', tmp_path / 'acks.json', tmp_path / 'state.json')
    instance.command_path.write_text(json.dumps({'version': 1, 'commands': []}), encoding='utf-8')
    return instance


def enqueue(queue, identifier='policy-1', action='set_video_policy', **fields):
    payload = {'channel_ids': [CHANNEL], **fields}
    return queue_module.enqueue_operator_command({'id': identifier, 'action': action, 'payload': payload},
        command_path=queue.command_path, acknowledgement_path=queue.acknowledgement_path)


def snapshot(queue, video=VIDEO, surface='metadata'):
    return queue.get_video_policy(CHANNEL, video, surface=surface)


def state(queue):
    return json.loads(queue.state_path.read_text(encoding='utf-8'))


def test_sync_intake_activates_private_policy_before_starved_watcher(queue):
    queue._next_poll_at = float('inf')
    enqueue(queue, title_mode='preserve', scheduling_enabled=False, context='Private research')
    result = snapshot(queue)
    assert result['available'] and not result['blocked']
    assert result['title_mode'] == 'preserve' and result['context'] == 'Private research'
    assert result['matched_command_ids'] == ['policy-1'] and len(result['fingerprint']) == 64
    assert 'scheduling_enabled' not in result
    assert snapshot(queue, surface='scheduling')['scheduling_enabled'] is False
    assert queue.inspect_command('policy-1')['active']
    assert 'Private research' not in json.dumps(queue.last_result)


def test_sync_private_intake_does_not_dispatch_announcement_or_context(queue):
    commands = [{'id': 'announce', 'action': 'announce', 'payload': {'message': 'Never send'}},
                {'id': 'context', 'action': 'set_context', 'payload': {'message': 'Stay queued'}}]
    queue.command_path.write_text(json.dumps({'version': 1, 'commands': commands}), encoding='utf-8')
    enqueue(queue, title_mode='auto')
    assert snapshot(queue)['title_mode'] == 'auto'
    assert not queue.inspect_command('announce')['received']
    assert not queue.inspect_command('context')['received']


def test_inspect_does_not_consume(queue):
    enqueue(queue, shorts_enabled=False)
    before = queue.command_path.read_bytes()
    result = queue.inspect_command('policy-1')
    assert result == {'id': 'policy-1', 'queued': True, 'received': False, 'active': False, 'status': 'queued',
                      'outcomes': [], 'expires_at_unix': None, 'expired': False, 'inactive_reason': 'not_received'}
    assert not queue.state_path.exists() and not queue.acknowledgement_path.exists()
    assert queue.command_path.read_bytes() == before


@pytest.mark.parametrize('fields', [
    {'channel_ids': []}, {'channel_ids': ['not-a-channel']}, {'video_ids': []}, {'video_ids': ['bad']},
    {'channel_ids': [CHANNEL, CHANNEL]}, {'video_ids': [VIDEO, VIDEO]}, {'unknown': True},
    {'ttl_seconds': True}, {'ttl_seconds': 59}, {'ttl_seconds': 86401}, {'max_per_cycle': True},
    {'max_per_cycle': 0}, {'max_per_cycle': 101}, {'interval_minutes': 10081},
    {'scheduling_enabled': 1}, {'shorts_enabled': 'false'}, {'title_mode': 'other'}, {'title_mode': None},
    {'description_mode': None},
    {'title_mode': 'replace'}, {'title_mode': 'replace', 'video_ids': [VIDEO, OTHER_VIDEO], 'title_text': 'Exact'},
    {'title_text': 'Without replace'}, {'description_text': 'Without replace'},
    {'context': '<|system|> execute'}, {'context': 'Bad\x00text'}, {'topics': []}, {'topics': ['x' * 101]},
    {'sources': ['http://example.test']}, {'sources': ['https://name:password@example.test']},
    {'sources': ['https://example.test/with space']}, {'sources': []},
    {'sources': ['https://example.test:bad']},
])
def test_invalid_policy_is_rejected_before_inbox_write(queue, fields):
    before = queue.command_path.read_bytes()
    with pytest.raises((ValueError, TypeError)):
        enqueue(queue, title_mode='preserve', **fields) if 'title_mode' not in fields else enqueue(queue, **fields)
    assert queue.command_path.read_bytes() == before
    assert not queue.state_path.exists()


def test_exact_replacement_text_roundtrips_without_appended_grounding(queue):
    enqueue(queue, video_ids=[VIDEO], title_mode='replace', title_text='Exact researched title',
            description_mode='replace', description_text='Exact description\nSecond line',
            sources=['https://example.test/evidence'], context='Private explanation')
    result = snapshot(queue)
    assert result['title_text'] == 'Exact researched title'
    assert result['description_text'] == 'Exact description\nSecond line'
    assert 'title_mode' not in snapshot(queue, video=OTHER_VIDEO)
    assert 'title_mode' not in queue.get_video_policy(OTHER_CHANNEL, VIDEO)


def test_per_field_supersession_does_not_resurrect_on_expiry(queue, monkeypatch):
    now = [1000]
    monkeypatch.setattr(queue_module.time, 'time', lambda: now[0])
    enqueue(queue, title_mode='preserve', description_mode='preserve', ttl_seconds=1000)
    assert snapshot(queue)['title_mode'] == 'preserve'
    enqueue(queue, 'new', title_mode='auto', ttl_seconds=60)
    assert snapshot(queue)['title_mode'] == 'auto'
    now[0] += 61
    result = snapshot(queue)
    assert 'title_mode' not in result
    assert result['description_mode'] == 'preserve'
    assert result['matched_command_ids'] == ['policy-1']


def test_overlapping_scopes_newest_field_wins_other_videos_preserved(queue):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    enqueue(queue, 'exact', video_ids=[VIDEO], title_mode='auto')
    assert snapshot(queue)['title_mode'] == 'auto'
    assert snapshot(queue, video=OTHER_VIDEO)['title_mode'] == 'preserve'
    enqueue(queue, 'latest-wide', title_mode='preserve')
    assert snapshot(queue)['title_mode'] == 'preserve'


@pytest.mark.parametrize('by_id', [False, True])
def test_clear_removes_only_video_policies_and_preserves_legacy_context(queue, by_id):
    queue.state_path.write_text(json.dumps({'version': 1, 'active_context': {'message': 'Retained'}, 'legacy': {'value': 1}}), encoding='utf-8')
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    payload = {'policy_id': 'policy-1'} if by_id else {'channel_ids': [CHANNEL]}
    queue_module.enqueue_operator_command({'id': 'clear', 'action': 'clear_video_policy', 'payload': payload},
        command_path=queue.command_path, acknowledgement_path=queue.acknowledgement_path)
    assert 'title_mode' not in snapshot(queue)
    assert state(queue)['active_context']['message'] == 'Retained'
    assert state(queue)['legacy'] == {'value': 1}


def test_unknown_claim_is_terminal_across_restart_and_blocks_old_policy(queue, monkeypatch):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    enqueue(queue, 'new', title_mode='auto')
    original = queue._atomic_write
    def fail_active(path, value):
        if path == queue.state_path:
            raise OSError('private write failed')
        original(path, value)
    monkeypatch.setattr(queue, '_atomic_write', fail_active)
    assert snapshot(queue)['blocked']
    fresh = queue_module.OperatorCommandQueue(None, queue.command_path, queue.acknowledgement_path, queue.state_path)
    result = snapshot(fresh)
    assert result['blocked'] and not result['available']
    assert result['reason'] == 'video_policy_outcome_unknown'
    assert fresh.inspect_command('new')['status'] == 'unknown'


@pytest.mark.parametrize('target,contents', [('command_path', '{broken'), ('acknowledgement_path', '[]'),
    ('state_path', '{broken'), ('state_path', '{"version":1,"video_policies":null}')])
def test_corruption_is_explicit_unavailable_and_preserved(queue, target, contents):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    path = getattr(queue, target)
    path.write_text(contents, encoding='utf-8')
    assert snapshot(queue)['blocked']
    assert path.read_text(encoding='utf-8') == contents


def test_busy_queue_is_explicit_unavailable(queue):
    with queue._locked():
        result = snapshot(queue)
    assert result['blocked'] and not result['available']


def test_payload_mutation_blocks_without_using_previous_policy(queue):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    data = json.loads(queue.command_path.read_text())
    data['commands'][0]['payload']['title_mode'] = 'auto'
    queue.command_path.write_text(json.dumps(data), encoding='utf-8')
    assert snapshot(queue)['blocked']


def test_missing_active_state_is_not_empty_default_after_activation(queue):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    queue.state_path.unlink()
    assert snapshot(queue)['blocked']


def test_observations_distinguish_observed_from_verified_applied(queue):
    enqueue(queue, shorts_enabled=True)
    policy = snapshot(queue, surface='shorts')
    args = dict(surface='shorts', channel_id=CHANNEL, video_id=VIDEO)
    assert queue.record_video_policy_observation(['policy-1'], outcome='observed', detail={}, **args)['recorded']
    with pytest.raises(ValueError, match='persisted_readback'):
        queue.record_video_policy_observation(['policy-1'], outcome='applied', detail={}, **args)
    queue.record_video_policy_observation(['policy-1'], outcome='applied', detail={
        'persisted_readback': True, 'policy_fingerprint': policy['fingerprint'], 'readback_sha256': 'b' * 64}, **args)
    assert [o['outcome'] for o in queue.inspect_command('policy-1')['outcomes']] == ['observed', 'applied']


def test_upload_unknown_reservation_survives_restart_and_prevents_duplicate(queue):
    enqueue(queue, shorts_enabled=True)
    policy = queue.get_video_policy(CHANNEL, surface='shorts')
    args = {'command_ids': policy['matched_command_ids'], 'fingerprint': policy['fingerprint']}
    assert queue.claim_video_policy_upload(CHANNEL, 'a' * 64, **args)['claimed']
    fresh = queue_module.OperatorCommandQueue(None, queue.command_path, queue.acknowledgement_path, queue.state_path)
    result = fresh.claim_video_policy_upload(CHANNEL, 'a' * 64, **args)
    assert result['blocked'] and not result['claimed']
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'unknown'


def test_upload_claim_rechecks_fresh_policy(queue):
    enqueue(queue, shorts_enabled=True)
    policy = queue.get_video_policy(CHANNEL, surface='shorts')
    enqueue(queue, 'pause', shorts_enabled=False)
    result = queue.claim_video_policy_upload(CHANNEL, 'a' * 64,
        command_ids=policy['matched_command_ids'], fingerprint=policy['fingerprint'])
    assert not result['claimed'] and result['blocked']
    assert not state(queue).get('video_effect_claims')


def test_async_watcher_activates_private_policy_without_gates(queue):
    enqueue(queue, title_mode='preserve', context='Never public')
    result = asyncio.run(queue.poll_once())
    assert result['results'][0]['status'] == 'accepted'
    assert 'Never public' not in json.dumps(result)
    assert snapshot(queue)['title_mode'] == 'preserve'


@pytest.mark.parametrize('corruption', ['empty', 'changed', 'orphan'])
def test_accepted_state_digest_rejects_missing_or_modified_policy_snapshot(queue, corruption):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    stored = state(queue)
    if corruption == 'empty':
        stored['video_policies'] = []
    elif corruption == 'changed':
        stored['video_policies'][0]['fields']['title_mode'] = 'auto'
    else:
        stored['video_policies'][0]['id'] = 'orphaned'
    queue.state_path.write_text(json.dumps(stored), encoding='utf-8')
    result = snapshot(queue)
    assert result['blocked'] and not result['available']


def test_legacy_deferred_private_claim_never_resurrects_expired_superseded_field(queue):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    ledger = json.loads(queue.acknowledgement_path.read_text(encoding='utf-8'))
    ledger['acknowledgements'][0]['status'] = 'deferred'
    queue.acknowledgement_path.write_text(json.dumps(ledger), encoding='utf-8')
    before = queue.acknowledgement_path.read_bytes()
    assert snapshot(queue)['blocked']
    assert queue.acknowledgement_path.read_bytes() == before
    assert asyncio.run(queue.poll_once())['processed'] == 0


@pytest.mark.parametrize('action', ['set_context', 'clear_context'])
def test_context_actions_preserve_policy_snapshot_and_private_observations(queue, action):
    enqueue(queue, scheduling_enabled=False)
    snapshot(queue, surface='scheduling')
    queue.record_video_policy_observation(['policy-1'], surface='scheduling', channel_id=CHANNEL,
        video_id=VIDEO, outcome='observed', detail={})
    queue_module.enqueue_operator_command({'id': 'context', 'action': action, 'payload': {'message': 'Private context'}},
        command_path=queue.command_path, acknowledgement_path=queue.acknowledgement_path)
    result = asyncio.run(queue.poll_once())
    assert 'Private context' not in json.dumps(result)
    if action == 'set_context':
        assert result['results'][0]['result']['context_activated'] is True
    result = snapshot(queue, surface='scheduling')
    assert result['scheduling_enabled'] is False and result['available']
    assert len(state(queue)['video_policy_observations']) == 1


def test_module_exports_use_resolved_overrides_without_current_directory_dependence(queue, monkeypatch, tmp_path):
    monkeypatch.setenv('YT_012_MANIFEST_FILE', str(queue.command_path))
    monkeypatch.setenv('YT_012_MANIFEST_ACK_FILE', str(queue.acknowledgement_path))
    monkeypatch.setenv('YT_012_MANIFEST_STATE_FILE', str(queue.state_path))
    monkeypatch.chdir(tmp_path)
    enqueue(queue, scheduling_enabled=False)
    assert queue_module.get_video_policy(CHANNEL, VIDEO, surface='scheduling')['scheduling_enabled'] is False
    assert queue_module.inspect_command('policy-1')['active']


def test_applied_upload_observation_never_erases_reservation(queue):
    enqueue(queue, shorts_enabled=True)
    policy = queue.get_video_policy(CHANNEL, surface='shorts')
    args = {'command_ids': policy['matched_command_ids'], 'fingerprint': policy['fingerprint']}
    assert queue.claim_video_policy_upload(CHANNEL, 'a' * 64, **args)['claimed']
    queue.record_video_policy_observation(['policy-1'], surface='shorts', channel_id=CHANNEL, video_id=VIDEO,
        outcome='applied', detail={'artifact_sha256': 'a' * 64, 'persisted_readback': True,
                                 'policy_fingerprint': policy['fingerprint'], 'readback_sha256': 'b' * 64})
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'applied'
    assert not queue.claim_video_policy_upload(CHANNEL, 'a' * 64, **args)['claimed']


def test_bounded_observation_tail_retains_latest_records(queue):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    for index in range(video_policy.MAX_OBSERVATIONS + 1):
        queue.record_video_policy_observation(['policy-1'], surface='metadata', channel_id=CHANNEL, video_id=VIDEO,
            outcome='observed', detail={'index': index})
    observations = state(queue)['video_policy_observations']
    assert len(observations) == video_policy.MAX_OBSERVATIONS
    assert observations[0]['detail']['index'] == 1
    assert observations[-1]['detail']['index'] == video_policy.MAX_OBSERVATIONS


@pytest.mark.parametrize('channel,video,surface', [('bad', VIDEO, 'metadata'), (CHANNEL, 'bad', 'metadata'),
    (CHANNEL, VIDEO, 'unknown'), (None, VIDEO, 'shorts')])
def test_invalid_receiving_identity_or_surface_is_explicitly_blocked(queue, channel, video, surface):
    result = queue.get_video_policy(channel, video, surface=surface)
    assert result['blocked'] and not result['available']


def test_no_matching_policy_has_stable_empty_sparse_snapshot(queue):
    first = snapshot(queue)
    second = snapshot(queue)
    assert first == second
    assert first['available'] and not first['blocked'] and not first['matched_command_ids']
    assert first['expires_at_unix'] is None and 'title_mode' not in first


@pytest.mark.parametrize('fields', [{'expires_at_unix': True}, {'expires_at_unix': float('nan')},
    {'expires_at_unix': float('inf')}, {'expires_at_unix': '100'}, {'expires_at_unix': -1}])
def test_explicit_deadline_rejects_nonfinite_boolean_and_nonnumeric(queue, fields):
    with pytest.raises(ValueError):
        enqueue(queue, title_mode='preserve', **fields)
    assert not queue.state_path.exists()


@pytest.mark.parametrize('deadline,expected', [(999, 'expired'), (1030, 'accepted'), (999999, 'accepted')])
def test_explicit_deadline_bounds_delayed_intake_and_never_extends_ttl(queue, monkeypatch, deadline, expected):
    monkeypatch.setattr(queue_module.time, 'time', lambda: 1000)
    enqueue(queue, title_mode='preserve', ttl_seconds=60, expires_at_unix=deadline)
    result = snapshot(queue)
    assert queue.inspect_command('policy-1')['status'] == expected
    if expected == 'expired':
        assert 'title_mode' not in result
    else:
        assert result['expires_at_unix'] == min(1060, deadline)


@pytest.mark.parametrize('channel,video,surface', [(OTHER_CHANNEL, VIDEO, 'metadata'),
    (CHANNEL, OTHER_VIDEO, 'metadata'), (CHANNEL, VIDEO, 'shorts')])
def test_observation_cannot_claim_wrong_scope_or_surface(queue, channel, video, surface):
    enqueue(queue, video_ids=[VIDEO], title_mode='preserve')
    snapshot(queue)
    with pytest.raises(ValueError, match='scope_mismatch'):
        queue.record_video_policy_observation(['policy-1'], surface=surface, channel_id=channel, video_id=video,
            outcome='observed', detail={})
    assert not state(queue).get('video_policy_observations')


def test_applied_requires_exact_current_snapshot_and_readback_evidence(queue):
    enqueue(queue, title_mode='preserve')
    policy = snapshot(queue)
    args = dict(surface='metadata', channel_id=CHANNEL, video_id=VIDEO, outcome='applied')
    with pytest.raises(ValueError):
        queue.record_video_policy_observation(['policy-1'], detail={'persisted_readback': True}, **args)
    with pytest.raises(ValueError, match='snapshot_mismatch'):
        queue.record_video_policy_observation(['policy-1'], detail={'persisted_readback': True,
            'policy_fingerprint': '0' * 64, 'readback_sha256': 'b' * 64}, **args)
    enqueue(queue, 'newer', title_mode='auto')
    snapshot(queue)
    with pytest.raises(ValueError, match='snapshot_mismatch'):
        queue.record_video_policy_observation(['policy-1'], detail={'persisted_readback': True,
            'policy_fingerprint': policy['fingerprint'], 'readback_sha256': 'b' * 64}, **args)


def test_inspection_does_not_report_uncertain_persisted_policy_active(queue, monkeypatch):
    enqueue(queue, title_mode='preserve')
    original = queue._atomic_write
    def fail_final_ledger(path, value):
        if path == queue.acknowledgement_path and value['acknowledgements'][0]['status'] == 'accepted':
            raise OSError('private write failed')
        original(path, value)
    monkeypatch.setattr(queue, '_atomic_write', fail_final_ledger)
    assert snapshot(queue)['blocked']
    assert state(queue)['video_policies']
    result = queue.inspect_command('policy-1')
    assert result['received'] and result['status'] == 'unknown' and not result['active']


@pytest.mark.parametrize('context', [[], 4, 'bad'])
def test_inspect_malformed_legacy_context_never_claims_activation(queue, context):
    queue.state_path.write_text(json.dumps({'version': 1, 'active_context': context}), encoding='utf-8')
    assert not queue.inspect_command('unknown')['active']


@pytest.mark.parametrize('result', [None, [], {'policy_state_digest': 'bad'},
    {'policy_state_digest': 'a' * 64, 'policy_fields': None, 'policy_scopes': []}])
def test_malformed_accepted_private_receipt_is_unavailable_without_mutation(queue, result):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    ledger = json.loads(queue.acknowledgement_path.read_text(encoding='utf-8'))
    ledger['acknowledgements'][0]['result'] = result
    queue.acknowledgement_path.write_text(json.dumps(ledger), encoding='utf-8')
    before = queue.acknowledgement_path.read_bytes()
    assert snapshot(queue)['blocked']
    assert queue.acknowledgement_path.read_bytes() == before


def claim_save(queue, digest='a' * 64, *, scheduling=False):
    metadata = snapshot(queue)
    schedule = snapshot(queue, surface='scheduling') if scheduling else None
    ids = sorted(set(metadata['matched_command_ids']) | set(schedule['matched_command_ids'] if schedule else []))
    args = {'command_ids': ids, 'metadata_fingerprint': metadata['fingerprint'], 'draft_sha256': digest}
    if schedule:
        args['scheduling_fingerprint'] = schedule['fingerprint']
    return queue.claim_video_policy_save(CHANNEL, VIDEO, **args), args


@pytest.mark.parametrize('changed_draft', [False, True])
def test_unknown_save_blocks_same_target_across_restart_even_if_draft_changes(queue, changed_draft):
    enqueue(queue, title_mode='preserve')
    result, args = claim_save(queue)
    assert result['claimed']
    fresh = queue_module.OperatorCommandQueue(None, queue.command_path, queue.acknowledgement_path, queue.state_path)
    if changed_draft:
        args['draft_sha256'] = 'b' * 64
    repeat = fresh.claim_video_policy_save(CHANNEL, VIDEO, **args)
    assert repeat['blocked'] and not repeat['claimed']
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'unknown'


@pytest.mark.parametrize('has_policy', [False, True])
def test_exact_verified_save_can_settle_empty_or_active_policy_and_allow_new_draft(queue, has_policy):
    if has_policy:
        enqueue(queue, title_mode='preserve')
    result, args = claim_save(queue)
    assert result['claimed']
    verified = queue.verify_video_policy_save(CHANNEL, VIDEO, draft_sha256=args['draft_sha256'],
        readback_sha256=args['draft_sha256'], metadata_fingerprint=args['metadata_fingerprint'])
    assert verified['verified'] and verified['outcome'] == 'applied'
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'applied'
    assert not queue.claim_video_policy_save(CHANNEL, VIDEO, **args)['claimed']
    args['draft_sha256'] = 'b' * 64
    assert queue.claim_video_policy_save(CHANNEL, VIDEO, **args)['claimed']
    assert len(state(queue)['video_effect_claims']) == 2


@pytest.mark.parametrize('fault', ['readback', 'policy', 'missing_schedule_fingerprint'])
def test_save_verification_mismatch_keeps_unknown_reservation(queue, fault):
    enqueue(queue, title_mode='preserve', scheduling_enabled=True)
    result, args = claim_save(queue, scheduling=True)
    assert result['claimed']
    if fault == 'policy':
        enqueue(queue, 'new', scheduling_enabled=False)
    verification = dict(draft_sha256=args['draft_sha256'], readback_sha256='b' * 64 if fault == 'readback' else args['draft_sha256'],
        metadata_fingerprint=args['metadata_fingerprint'])
    if fault != 'missing_schedule_fingerprint':
        verification['scheduling_fingerprint'] = args['scheduling_fingerprint']
    assert not queue.verify_video_policy_save(CHANNEL, VIDEO, **verification)['verified']
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'unknown'


def test_generic_observation_cannot_release_save_reservation(queue):
    enqueue(queue, title_mode='preserve')
    result, args = claim_save(queue)
    assert result['claimed']
    with pytest.raises(ValueError, match='save_requires_bound_verification'):
        queue.record_video_policy_observation(['policy-1'], surface='metadata', channel_id=CHANNEL, video_id=VIDEO,
            outcome='applied', detail={'draft_sha256': args['draft_sha256'], 'readback_sha256': args['draft_sha256'],
                'persisted_readback': True, 'policy_fingerprint': args['metadata_fingerprint']})
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'unknown'


def test_metadata_digest_alone_never_settles_scheduled_save(queue):
    enqueue(queue, title_mode='preserve', scheduling_enabled=True)
    result, args = claim_save(queue, scheduling=True)
    assert result['claimed']
    verification = queue.verify_video_policy_save(CHANNEL, VIDEO, draft_sha256=args['draft_sha256'],
        readback_sha256=args['draft_sha256'], metadata_fingerprint=args['metadata_fingerprint'],
        scheduling_fingerprint=args['scheduling_fingerprint'])
    assert not verification['verified'] and verification['reason'] == 'schedule_readback_not_qualified'
    assert state(queue)['video_effect_claims'][0]['outcome'] == 'unknown'


@pytest.mark.parametrize('later', ['expiry', 'clear', 'newer_policy'])
def test_complete_metadata_readback_reconciles_immutable_past_claim_after_policy_changes(queue, monkeypatch, later):
    now = [1000]
    monkeypatch.setattr(queue_module.time, 'time', lambda: now[0])
    enqueue(queue, video_ids=[VIDEO], title_mode='replace', title_text='Researched exact title', ttl_seconds=60)
    result, args = claim_save(queue)
    assert result['claimed']
    if later == 'expiry':
        now[0] = 1061
    elif later == 'clear':
        queue_module.enqueue_operator_command({'id': 'clear', 'action': 'clear_video_policy', 'payload': {'policy_id': 'policy-1'}},
            command_path=queue.command_path, acknowledgement_path=queue.acknowledgement_path)
    else:
        enqueue(queue, 'new', video_ids=[VIDEO], title_mode='preserve')
    snapshot(queue)
    verification = queue.verify_video_policy_save(CHANNEL, VIDEO, draft_sha256=args['draft_sha256'],
        readback_sha256=args['draft_sha256'], metadata_fingerprint=args['metadata_fingerprint'])
    assert verification['verified'] and state(queue)['video_effect_claims'][0]['outcome'] == 'applied'
    assert state(queue)['video_policy_observations'][-1]['detail']['policy_fingerprint'] == args['metadata_fingerprint']


def test_short_cadence_survives_restart_and_new_artifact_without_changing_policy_fingerprint(queue, monkeypatch):
    now = [1000]
    monkeypatch.setattr(queue_module.time, 'time', lambda: now[0])
    enqueue(queue, shorts_enabled=True, interval_minutes=10)
    policy = queue.get_video_policy(CHANNEL, surface='shorts')
    args = {'command_ids': policy['matched_command_ids'], 'fingerprint': policy['fingerprint']}
    assert queue.claim_video_policy_upload(CHANNEL, 'a' * 64, **args)['claimed']
    fresh = queue_module.OperatorCommandQueue(None, queue.command_path, queue.acknowledgement_path, queue.state_path)
    after = fresh.get_video_policy(CHANNEL, surface='shorts')
    assert after['last_upload_attempt_unix'] == 1000 and after['fingerprint'] == policy['fingerprint']
    assert fresh.claim_video_policy_upload(CHANNEL, 'b' * 64, **args)['reason'] == 'shorts_interval_not_due'
    now[0] = 1600
    assert fresh.claim_video_policy_upload(CHANNEL, 'b' * 64, **args)['claimed']


def test_paused_short_policy_cannot_claim_upload(queue):
    enqueue(queue, shorts_enabled=False)
    policy = queue.get_video_policy(CHANNEL, surface='shorts')
    result = queue.claim_video_policy_upload(CHANNEL, 'a' * 64,
        command_ids=policy['matched_command_ids'], fingerprint=policy['fingerprint'])
    assert not result['claimed'] and result['reason'] == 'shorts_policy_paused'


def test_private_status_never_reports_unknown_persisted_policy_as_active(queue, monkeypatch):
    enqueue(queue, title_mode='preserve')
    snapshot(queue)
    ledger = json.loads(queue.acknowledgement_path.read_text(encoding='utf-8'))
    ledger['acknowledgements'][0]['status'] = 'unknown'
    queue.acknowledgement_path.write_text(json.dumps(ledger), encoding='utf-8')
    monkeypatch.setattr(queue_module, 'gate_snapshot', lambda: {})
    result = asyncio.run(queue._dispatch({'action': 'status'}, {}, []))
    assert result['status'] == 'accepted'
    assert not result['result']['video_policy_available'] and result['result']['active_policy_ids'] == []


def test_non_ttl_commands_never_gain_expiry(queue, monkeypatch):
    monkeypatch.setattr(queue_module, 'gate_snapshot', lambda: {})
    commands = [{'id': action, 'action': action, 'payload': {'channel_ids': [CHANNEL]} if action == 'clear_video_policy' else {}}
                for action in ('status', 'clear_context', 'clear_video_policy')]
    queue.command_path.write_text(json.dumps({'version': 1, 'commands': commands}), encoding='utf-8')
    assert asyncio.run(queue.poll_once())['processed'] == 3
    for command in commands:
        info = queue.inspect_command(command['id'])
        assert info['expires_at_unix'] is None and not info['expired']


def test_inspector_reports_expiry_and_clear_without_private_content(queue, monkeypatch):
    now = [1000]
    monkeypatch.setattr(queue_module.time, 'time', lambda: now[0])
    enqueue(queue, title_mode='preserve', ttl_seconds=60, context='Private secret-free instruction')
    snapshot(queue)
    assert queue.inspect_command('policy-1')['expires_at_unix'] == 1060
    now[0] = 1061
    info = queue.inspect_command('policy-1')
    assert info['expired'] and not info['active'] and info['inactive_reason'] == 'expired'
    enqueue(queue, 'clear', action='clear_video_policy')
    snapshot(queue)
    assert queue.inspect_command('policy-1')['inactive_reason'] == 'cleared'
    assert 'Private secret-free instruction' not in json.dumps(queue.inspect_command('policy-1'))
