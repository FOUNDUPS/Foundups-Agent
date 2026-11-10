"""Bounded stream requests owned by the existing private manifest queue.

No new store, worker or publisher. Browser owners read a frozen request, verify
access and complete discovery, then claim its immutable selection before writes.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import time

from . import video_policy
from .automation_gates import stop_active, _env_truthy

ACTION = 'schedule_stream_shorts'
STATE_KEY = 'stream_schedule_requests'
MAX_REQUESTS = 500
MAX_SELECTION = 1000
_FROZEN = {'id', 'command_digest', 'channel_id', 'parent_video_id', 'stream_title',
           'session_id', 'live_chat_id', 'accepted_at_unix', 'expires_at_unix', 'source_key'}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def validate_payload(payload):
    if not isinstance(payload, dict) or set(payload) - {'ttl_seconds', 'expires_at_unix'}:
        raise ValueError('invalid_stream_schedule_payload')
    ttl = payload.get('ttl_seconds', 3600)
    deadline = payload.get('expires_at_unix')
    if type(ttl) is not int or not 60 <= ttl <= 86400:
        raise ValueError('invalid_stream_schedule_expiry')
    if deadline is not None and (type(deadline) not in (int, float)
            or not math.isfinite(deadline) or not 0 < deadline < 1e12):
        raise ValueError('invalid_stream_schedule_expiry')
    return ttl, deadline


def _selection(value):
    if not isinstance(value, list) or len(value) > MAX_SELECTION:
        raise ValueError('invalid_stream_schedule_selection')
    if value:
        video_policy.ids(value, video_policy.VIDEO, MAX_SELECTION)
    if len(set(value)) != len(value):
        raise ValueError('invalid_stream_schedule_selection')
    return list(value)


def validate_state(state, rows):
    requests = state.get(STATE_KEY, [])
    if not isinstance(requests, list) or len(requests) > MAX_REQUESTS:
        raise ValueError('invalid_stream_schedule_state')
    seen, sources = set(), set()
    for request in requests:
        if not isinstance(request, dict) or set(request) != _FROZEN | {
                'request_digest', 'execution_status', 'video_ids', 'result'}:
            raise ValueError('invalid_stream_schedule_record')
        video_policy.ids([request['channel_id']], video_policy.CHANNEL, 1)
        video_policy.ids([request['parent_video_id']], video_policy.VIDEO, 1)
        for key, limit in (('id', 200), ('stream_title', 100), ('session_id', 300), ('live_chat_id', 300)):
            video_policy.text(request[key], limit)
        for key in ('accepted_at_unix', 'expires_at_unix'):
            if type(request[key]) not in (int, float) or not 0 < request[key] < 1e12:
                raise ValueError('invalid_stream_schedule_time')
        if not 0 < request['expires_at_unix'] - request['accepted_at_unix'] <= 86400:
            raise ValueError('invalid_stream_schedule_time')
        video_policy.validate_artifact(request['command_digest'])
        if (request['source_key'] != _digest([request['channel_id'], request['parent_video_id']])
                or request['request_digest'] != _digest({k: request[k] for k in _FROZEN})):
            raise ValueError('stream_schedule_binding_changed')
        if request['id'] in seen or request['source_key'] in sources:
            raise ValueError('duplicate_stream_schedule_source')
        seen.add(request['id']); sources.add(request['source_key'])
        if request['execution_status'] not in {'pending', 'unknown', 'blocked'}:
            raise ValueError('invalid_stream_schedule_status')
        selected = _selection(request['video_ids'])
        if request['execution_status'] == 'pending' and selected:
            raise ValueError('unclaimed_stream_schedule_selection')
        result = request['result']
        if not isinstance(result, dict) or set(result) - {'reason', 'submitted_ids'}:
            raise ValueError('invalid_stream_schedule_result')
        video_policy.text(result.get('reason', ''), 100, empty=True)
        if not set(_selection(result.get('submitted_ids', []))) <= set(selected):
            raise ValueError('stream_schedule_result_out_of_scope')
        row = rows.get(request['id'])
        if (not row or row.get('action') != ACTION or row.get('command_digest') != request['command_digest']
                or row.get('status') not in {'accepted', 'unknown'}):
            raise ValueError('stream_schedule_receipt_mismatch')
        if row['status'] == 'accepted' and (row.get('result') or {}).get('request_digest') != request['request_digest']:
            raise ValueError('stream_schedule_receipt_mismatch')
    for row in rows.values():
        if row.get('action') == ACTION and row.get('status') == 'accepted' and row['id'] not in seen:
            raise ValueError('stream_schedule_state_missing')
    return requests


def dispatch(self, command, row):
    from . import operator_video_policy_owner as owner
    try:
        ttl, deadline = validate_payload(command.get('payload', {}))
    except ValueError:
        return {'status': 'rejected', 'reason': 'invalid_stream_schedule_payload'}
    now = time.time()
    expiry = min(row['first_seen_unix'] + ttl, deadline if deadline is not None else float('inf'))
    if expiry <= now:
        return {'status': 'expired', 'reason': 'stream_schedule_expired'}
    live = getattr(self.dae, 'livechat', None)
    if live is None or getattr(live, 'is_running', False) is not True:
        return {'status': 'blocked', 'reason': 'confirmed_live_session_unavailable'}
    # Only confirmed live owner fields; speculative DAE current_video_id is not used.
    frozen = {'id': command['id'], 'command_digest': row['command_digest'],
        'channel_id': getattr(live, 'channel_id', None),
        'parent_video_id': getattr(live, 'video_id', None),
        'stream_title': getattr(live, 'stream_title', None),
        'session_id': getattr(getattr(live, 'memory_manager', None), 'current_session', None),
        'live_chat_id': getattr(live, 'live_chat_id', None),
        'accepted_at_unix': now, 'expires_at_unix': expiry}
    frozen['source_key'] = _digest([frozen['channel_id'], frozen['parent_video_id']])
    try:
        video_policy.ids([frozen['channel_id']], video_policy.CHANNEL, 1)
        video_policy.ids([frozen['parent_video_id']], video_policy.VIDEO, 1)
        for key, limit in (('stream_title', 100), ('session_id', 300), ('live_chat_id', 300)):
            video_policy.text(frozen[key], limit)
    except (ValueError, TypeError):
        return {'status': 'blocked', 'reason': 'confirmed_live_context_incomplete'}
    _, _, rows, _, state = owner._load_queue(self)
    requests = state.setdefault(STATE_KEY, [])
    if any(r.get('action') == ACTION and r['status'] == 'unknown' and r['id'] != command['id'] for r in rows.values()):
        return {'status': 'blocked', 'reason': 'stream_schedule_outcome_unknown'}
    if any(r['source_key'] == frozen['source_key'] for r in requests):
        return {'status': 'blocked', 'reason': 'stream_source_already_reserved'}
    request = {**frozen, 'request_digest': _digest(frozen), 'execution_status': 'pending',
               'video_ids': [], 'result': {'reason': 'awaiting_existing_browser_owner'}}
    requests.append(request)
    validate_state(state, rows)
    self._atomic_write(self.state_path, state)
    return {'status': 'accepted', 'result': {'request_digest': request['request_digest'],
        'execution_status': 'pending', 'expires_at_unix': expiry, 'delivery_verified': False}}


def pending(self):
    from . import operator_video_policy_owner as owner
    with self._locked():
        _, _, rows, _, state = owner._load_queue(self)
        if any(r.get('action') == ACTION and r['status'] == 'unknown' for r in rows.values()):
            raise ValueError('stream_schedule_outcome_unknown')
        return deepcopy([r for r in validate_state(state, rows)
                         if r['execution_status'] == 'pending' and r['expires_at_unix'] > time.time()])


def claim(self, request, video_ids):
    from . import operator_video_policy_owner as owner
    selected = _selection(video_ids)
    with self._locked():
        _, _, rows, _, state = owner._load_queue(self)
        current = next((r for r in validate_state(state, rows) if r['id'] == request.get('id')), None)
        if current is None or current != request or rows[current['id']]['status'] != 'accepted':
            raise ValueError('stream_schedule_request_changed')
        if current['execution_status'] != 'pending':
            raise ValueError('stream_schedule_already_claimed')
        if current['expires_at_unix'] <= time.time():
            raise ValueError('stream_schedule_expired')
        if (stop_active('scheduling') or not _env_truthy('YT_AUTOMATION_ENABLED', 'true')
                or not _env_truthy('YT_SHORTS_SCHEDULING_ENABLED', 'true')):
            raise ValueError('stream_schedule_gate_closed')
        current.update(execution_status='unknown', video_ids=selected,
                       result={'reason': 'claimed_before_scheduling'})
        self._atomic_write(self.state_path, state)
        return deepcopy(current)


def finish(self, command_id, *, reason, submitted_ids=(), no_submission=False):
    """A reported scheduler count never proves delivery; unknown stays terminal."""
    from . import operator_video_policy_owner as owner
    video_policy.text(reason, 100)
    submitted = _selection(list(submitted_ids))
    with self._locked():
        _, _, rows, _, state = owner._load_queue(self)
        current = next((r for r in validate_state(state, rows) if r['id'] == command_id), None)
        if (current is None or current['execution_status'] != 'unknown'
                or current['result'].get('reason') != 'claimed_before_scheduling'):
            raise ValueError('stream_schedule_not_claimed')
        if not set(submitted) <= set(current['video_ids']) or (no_submission and submitted):
            raise ValueError('stream_schedule_result_out_of_scope')
        current.update(execution_status='blocked' if no_submission is True else 'unknown',
                       result={'reason': reason, 'submitted_ids': submitted})
        self._atomic_write(self.state_path, state)
        owner._write_receipt(self, {**rows[command_id], 'reason': reason,
            'result': {'execution_status': current['execution_status'], 'delivery_verified': False}})
        return deepcopy(current)


def inspect(state, command_id):
    request = next((r for r in state.get(STATE_KEY, []) if r['id'] == command_id), None)
    if request is None:
        return {}
    return {'execution_status': request['execution_status'],
            'request_digest': request['request_digest'], 'expires_at_unix': request['expires_at_unix'],
            'selection_count': len(request['video_ids']), 'execution_reason': request['result'].get('reason'),
            'delivery_verified': False}
