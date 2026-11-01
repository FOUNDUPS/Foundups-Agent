"""Private implementation functions of the existing OperatorCommandQueue.

Every function receives that queue owner and uses its existing locks, claims,
ledger and atomic writes. No independent manager, store or dispatch bus exists.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
from datetime import datetime, timezone
import math
import time
from typing import Any
from modules.communication.livechat.src import video_policy

_TERMINAL = {'accepted', 'blocked', 'rejected', 'failed', 'unknown', 'simulated', 'expired', 'superseded'}

def private_status(self, gates):
    try:
        state = _policy_state(self)
    except (OSError, ValueError, TypeError, OverflowError):
        return {'gates': gates, 'video_policy_available': False, 'active_policy_ids': [], 'observations': []}
    return {'gates': gates, 'video_policy_available': True,
            'active_policy_ids': sorted({p['id'] for p in video_policy.validate_state(state)
                                         if p['expires_at_unix'] > time.time()}),
            'observations': state.get('video_policy_observations', [])}
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _finite_number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False

def message_request(payload, action, first_seen, now, context_surfaces, chat_limit, message_limit):
    """Existing bounded context/announcement validation, before any state/effect."""
    message = payload.get('message')
    surfaces = payload.get('surfaces', ['livechat', 'comments']) if action == 'set_context' else ['livechat']
    if not isinstance(surfaces, list) or not surfaces or any(not isinstance(s, str) or s not in context_surfaces for s in surfaces):
        return {'status': 'rejected', 'reason': 'invalid_context_surfaces'}
    limit = chat_limit if 'livechat' in surfaces else message_limit
    if not isinstance(message, str) or not message.strip() or len(message) > limit:
        return {'status': 'rejected', 'reason': 'invalid_message'}
    ttl = payload.get('ttl_seconds', 3600)
    if type(ttl) is not int or not 60 <= ttl <= 86400:
        return {'status': 'rejected', 'reason': 'invalid_ttl'}
    expires = first_seen + ttl
    deadline = payload.get('expires_at_unix', expires)
    if not _finite_number(deadline) or not 0 < deadline < 1e12:
        return {'status': 'rejected', 'reason': 'invalid_deadline'}
    expires = min(expires, deadline)
    if expires <= now:
        return {'status': 'expired', 'reason': 'command_expired'}
    return {'message': message, 'surfaces': surfaces, 'expires': expires}

def _dispatch_video_policy(self, command, row):
    try:
        video_policy.text(command['id'], 200)
        payload = video_policy.validate_payload(command['action'], command.get('payload', {}))
    except (ValueError, TypeError, OverflowError):
        return {'status': 'rejected', 'reason': 'invalid_video_policy_payload'}
    if command['action'] == 'set_video_policy' and min(row['first_seen_unix'] + payload['ttl_seconds'], payload.get('expires_at_unix', float('inf'))) <= time.time():
        return {'status': 'expired', 'reason': 'command_expired'}
    state = self._read_json(self.state_path, {'version': 1, 'active_context': None})
    try:
        video_policy.apply_policy(state, command, payload, row)
    except ValueError as exc:
        if str(exc) == 'video_policy_capacity_reached':
            return {'status': 'rejected', 'reason': str(exc)}
        raise
    self._atomic_write(self.state_path, state)
    return {'status': 'accepted', 'result': {'policy_activated': command['action'] == 'set_video_policy', 'policy_cleared': command['action'] == 'clear_video_policy', 'public_message_sent': False, 'policy_state_digest': video_policy.state_digest(state), 'cleared_policy_id': payload.get('policy_id'), 'expires_at_unix': min(row['first_seen_unix'] + payload['ttl_seconds'], payload.get('expires_at_unix', float('inf'))) if command['action'] == 'set_video_policy' else None, 'policy_scopes': [[channel, video] for channel, video in video_policy.scope(payload)] if 'channel_ids' in payload else [], 'policy_fields': sorted(set(payload) & video_policy.FIELDS)}}

def _refresh_video_policies(self):
    _policy_state(self)
    commands, ledger, rows, digests, _ = _load_queue(self)
    seen = set()
    for command in commands:
        command_id = command['id']
        if command.get('action') not in video_policy.ACTIONS or command_id in seen:
            continue
        seen.add(command_id)
        if command_id in rows:
            continue
        row = _claim(self, command, digests[command_id], ledger, rows)
        try:
            result = _dispatch_video_policy(self, command, row)
        except Exception as exc:
            result = {'status': 'unknown', 'reason': type(exc).__name__}
        _finish(self, row, result, ledger)
    return _policy_state(self)

def _policy_state(self):
    _, _, rows, _, state = _load_queue(self)
    if any((r.get('action') in video_policy.ACTIONS and r['status'] in {'unknown', 'deferred'} for r in rows.values())):
        raise ValueError('video_policy_outcome_unknown')
    for policy in video_policy.validate_state(state):
        row = rows.get(policy['id'])
        if not row or row['status'] != 'accepted' or row.get('command_digest') != policy['digest']:
            raise ValueError('video_policy_receipt_mismatch')
    accepted = {r['id'] for r in rows.values() if r.get('action') == 'set_video_policy' and r['status'] == 'accepted'}
    if accepted and 'video_policies' not in state:
        raise ValueError('video_policy_state_missing')
    accepted_rows = [r for r in rows.values() if r.get('action') in video_policy.ACTIONS and r['status'] == 'accepted']
    if accepted_rows and accepted_rows[-1].get('result', {}).get('policy_state_digest') != video_policy.state_digest(state):
        raise ValueError('video_policy_state_digest_mismatch')
    return state

def _unavailable(exc):
    return {'available': False, 'blocked': True, 'reason': str(exc) if isinstance(exc, ValueError) else type(exc).__name__, 'matched_command_ids': [], 'fingerprint': None, 'expires_at_unix': None, 'field_expiries': {}}

def get_video_policy(self, channel_id, video_id=None, *, surface='metadata'):
    """Consume only private policy commands, then bind one exact writer snapshot."""
    try:
        with self._locked():
            state = _refresh_video_policies(self)
            return video_policy.resolve_policy(state, channel_id, video_id, surface, time.time())
    except (OSError, ValueError, TypeError, TimeoutError, OverflowError) as exc:
        return _unavailable(exc)

def inspect_command(self, command_id):
    """Read-only private status; does not consume or dispatch queued commands."""
    video_policy.text(command_id, 200)
    with self._locked():
        commands, _, rows, _, state = _load_queue(self)
        row = rows.get(command_id)
        exists = any((command['id'] == command_id for command in commands))
        active = any((p['id'] == command_id and p['expires_at_unix'] > time.time() for p in video_policy.validate_state(state)))
        try:
            _policy_state(self)
        except (OSError, ValueError, TypeError, OverflowError):
            active = False
        context = state.get('active_context')
        active = active or (isinstance(context, dict) and context.get('source_command_id') == command_id and _finite_number(context.get('expires_at_unix')) and (context['expires_at_unix'] > time.time()))
        active = active and row is not None and (row['status'] == 'accepted')
        observations = [o for o in state.get('video_policy_observations', []) if command_id in o['policy_ids']]
        expiry, reason = _inspection_duration(command_id, row, rows, commands, active)
        return {'id': command_id, 'queued': exists, 'received': row is not None, 'active': active, 'status': row['status'] if row else 'queued' if exists else 'not_found', 'expires_at_unix': expiry, 'expired': expiry is not None and expiry <= time.time(), 'inactive_reason': reason, 'outcomes': [{k: o[k] for k in ('surface', 'channel_id', 'video_id', 'outcome', 'recorded_at')} for o in observations[-20:]]}

def _inspection_duration(command_id, row, rows, commands, active):
    result = row.get('result') if row else None
    expiry = result.get('expires_at_unix') if isinstance(result, dict) else None
    command = next((c for c in commands if c['id'] == command_id), {})
    payload = command.get('payload', {})
    action = row.get('action') if row else command.get('action')
    if expiry is None and isinstance(payload, dict) and action in {'set_context', 'set_video_policy', 'announce'}:
        deadline = payload.get('expires_at_unix')
        ttl = payload.get('ttl_seconds', 3600)
        if _finite_number(deadline):
            expiry = deadline
        if row and _finite_number(row.get('first_seen_unix')) and (type(ttl) is int):
            expiry = min(expiry or float('inf'), row['first_seen_unix'] + ttl)
    if not _finite_number(expiry):
        expiry = None
    if active:
        return (expiry, None)
    if row and row['status'] != 'accepted':
        return (expiry, row['status'])
    later = list(rows.values())[list(rows).index(command_id) + 1:] if row else []
    reason = _known_inactive_reason(row, later)
    return (expiry, reason or ('expired' if expiry is not None and expiry <= time.time() else 'inactive' if row else 'not_received'))

def _known_inactive_reason(row, later):
    if not row:
        return None
    own = row.get('result') if isinstance(row.get('result'), dict) else {}
    own_scopes = {tuple(p) for p in own.get('policy_scopes', [])}
    for newer in reversed(later):
        if newer['status'] != 'accepted':
            continue
        action = newer.get('action')
        result = newer.get('result') if isinstance(newer.get('result'), dict) else {}
        if row.get('action') == 'set_context' and action in {'clear_context', 'set_context'}:
            return 'cleared' if action == 'clear_context' else 'superseded'
        if row.get('action') == 'set_video_policy' and action in video_policy.ACTIONS:
            overlap = own_scopes & {tuple(p) for p in result.get('policy_scopes', [])}
            if result.get('cleared_policy_id') == row['id'] or overlap:
                return 'cleared' if action == 'clear_video_policy' else 'superseded'
    return None

def record_video_policy_observation(self, policy_ids, *, surface, channel_id, video_id, outcome, detail):
    """Private writer evidence; applied requires caller's verified persisted readback."""
    observation = video_policy.observation(policy_ids, surface, channel_id, video_id, outcome, detail)
    with self._locked():
        state = _policy_state(self)
        _, _, rows, _, _ = _load_queue(self)
        if any((pid not in rows or rows[pid].get('action') != 'set_video_policy' or rows[pid]['status'] != 'accepted' for pid in policy_ids)):
            raise ValueError('unknown_observation_policy')
        _validate_observation_binding(self, observation, state, rows)
        observation['recorded_at'] = _utc_now()
        state['video_policy_observations'] = [*state.get('video_policy_observations', []), observation][-video_policy.MAX_OBSERVATIONS:]
        for claim in state.get('video_effect_claims', []):
            if claim['kind'] == 'save':
                continue
            digest = detail.get('artifact_sha256' if claim['kind'] == 'upload' else 'draft_sha256')
            if claim['channel_id'] == channel_id and claim['content_sha256'] == digest:
                if surface not in claim['fingerprints'] or not set(policy_ids) <= set(claim['policy_ids']):
                    raise ValueError('video_upload_observation_scope_mismatch')
                if claim['kind'] == 'save' and claim['video_id'] != video_id:
                    raise ValueError('video_save_observation_scope_mismatch')
                claim['outcome'] = outcome
        self._atomic_write(self.state_path, state)
    return {'recorded': True, 'outcome': outcome}

def _validate_observation_binding(self, observation, state, rows):
    channel, video, surface = (observation[k] for k in ('channel_id', 'video_id', 'surface'))
    _validate_policy_scope(observation['policy_ids'], channel, video, surface, rows)
    if observation['outcome'] != 'applied':
        return
    detail = observation['detail']
    if 'draft_sha256' in detail:
        raise ValueError('save_requires_bound_verification')
    fingerprint = detail.get('policy_fingerprint')
    video_policy.validate_artifact(detail.get('readback_sha256'))
    snapshot = video_policy.resolve_policy(state, channel, video, surface, time.time())
    claimed = any((c['kind'] == 'upload' and c['channel_id'] == channel and (c['content_sha256'] == detail.get('artifact_sha256')) and (c['fingerprints'].get(surface) == fingerprint) and (sorted(c['policy_ids']) == sorted(observation['policy_ids'])) for c in state.get('video_effect_claims', []))) if surface == 'shorts' else False
    if not claimed and (fingerprint != snapshot['fingerprint'] or sorted(observation['policy_ids']) != snapshot['matched_command_ids']):
        raise ValueError('applied_policy_snapshot_mismatch')

def _validate_policy_scope(policy_ids, channel, video, surface, rows):
    for pid in policy_ids:
        if pid not in rows or rows[pid].get('action') != 'set_video_policy' or rows[pid]['status'] != 'accepted':
            raise ValueError('unknown_observation_policy')
        result = rows[pid].get('result', {})
        scopes = result.get('policy_scopes', [])
        if [channel, video] not in scopes and [channel, None] not in scopes or not set(result.get('policy_fields', [])) & (video_policy.SURFACES[surface] | video_policy.GROUNDING):
            raise ValueError('observation_policy_scope_mismatch')

def claim_video_policy_upload(self, channel_id, artifact_sha256, *, command_ids, fingerprint):
    """Durably reserve an artifact before upload; every repeated claim blocks."""
    return _claim_video_effect(self, 'upload', channel_id, None, artifact_sha256, command_ids, {'shorts': fingerprint})

def claim_video_policy_save(self, channel_id, video_id, *, command_ids, metadata_fingerprint, scheduling_fingerprint=None, draft_sha256):
    """Unknown saves block this receiving video, independent of changed drafts."""
    fingerprints = {'metadata': metadata_fingerprint}
    if scheduling_fingerprint is not None:
        fingerprints['scheduling'] = scheduling_fingerprint
    return _claim_video_effect(self, 'save', channel_id, video_id, draft_sha256, command_ids, fingerprints)

def _claim_video_effect(self, kind, channel_id, video_id, digest, command_ids, fingerprints):
    try:
        with self._locked():
            state = _refresh_video_policies(self)
            claims, claim = video_policy.reserve_effect(state, kind, channel_id, video_id, digest, command_ids, fingerprints, time.time())
            claims.append(claim)
            video_policy.validate_state(state)
            self._atomic_write(self.state_path, state)
            return {'claimed': True, 'blocked': False, 'outcome': 'unknown'}
    except (OSError, ValueError, TypeError, TimeoutError, OverflowError) as exc:
        return {'claimed': False, 'blocked': True, 'reason': type(exc).__name__ if not isinstance(exc, ValueError) else str(exc)}

def verify_video_policy_save(self, channel_id, video_id, *, draft_sha256, readback_sha256, metadata_fingerprint, scheduling_fingerprint=None):
    """Settle a save only against an equal independent persisted readback digest."""
    fingerprints = {'metadata': metadata_fingerprint}
    if scheduling_fingerprint is not None:
        fingerprints['scheduling'] = scheduling_fingerprint
    try:
        with self._locked():
            _, _, rows, _, state = _load_queue(self)
            claim = video_policy.verify_save(state, channel_id, video_id, draft_sha256, readback_sha256, fingerprints)
            for surface in fingerprints:
                _validate_policy_scope(claim['policy_ids'], channel_id, video_id, surface, rows)
            claim['outcome'] = 'applied'
            observations = state.setdefault('video_policy_observations', [])
            for surface, fingerprint in fingerprints.items():
                observation = video_policy.observation(claim['policy_ids'], surface, channel_id, video_id, 'applied', {'persisted_readback': True, 'readback_sha256': readback_sha256, 'draft_sha256': draft_sha256, 'policy_fingerprint': fingerprint})
                observation['recorded_at'] = _utc_now()
                observations.append(observation)
            state['video_policy_observations'] = observations[-video_policy.MAX_OBSERVATIONS:]
            self._atomic_write(self.state_path, state)
            return {'verified': True, 'blocked': False, 'outcome': 'applied'}
    except (OSError, ValueError, TypeError, TimeoutError, OverflowError) as exc:
        return {'verified': False, 'blocked': True, 'reason': type(exc).__name__ if not isinstance(exc, ValueError) else str(exc)}

def _write_receipt(self, result: dict) -> None:
    status = result['status']
    delivery_unknown = result.get('result', {}).get('delivery_verified') is False
    health = 'green' if status == 'accepted' and (not delivery_unknown) else 'amber' if status in {'accepted', 'deferred', 'unknown', 'simulated'} else 'red'
    state = self._read_json(self.state_path, {'version': 1, 'active_context': None})
    state['last_receipt'] = {key: result.get(key) for key in ('id', 'action', 'status', 'reason', 'result')}
    state['last_receipt'].update(health=health, recorded_at=_utc_now())
    self._atomic_write(self.state_path, state)

def _telemetry(row):
    result = dict(row)
    if result.get('action') == 'set_context' and isinstance(result.get('result'), dict):
        result['result'] = {key: result['result'][key] for key in
                            ('context_activated', 'public_message_sent', 'expires_at_unix') if key in result['result']}
    elif result.get('action') in video_policy.ACTIONS | {'status'}:
        result.pop('result', None)
    return result

def _claim(self, command, digest, ledger, rows):
    row = rows.get(command['id'])
    if row is None:
        row = {'id': command['id'], 'action': command.get('action'), 'command_digest': digest, 'first_seen_unix': time.time(), 'status': 'unknown'}
        ledger['acknowledgements'].append(row)
        rows[command['id']] = row
    for field in ('reason', 'result', 'gates', 'completed_at'):
        row.pop(field, None)
    row['status'] = 'unknown'
    self._atomic_write(self.acknowledgement_path, ledger)
    return row

def _finish(self, row, result, ledger):
    row.update(result, completed_at=_utc_now())
    self._atomic_write(self.acknowledgement_path, ledger)
    _write_receipt(self, row)

async def _poll_locked(self) -> dict:
    commands, ledger, rows, digests, _ = _load_queue(self)
    recorded = ledger['acknowledgements']
    results = []
    seen = set()
    for command in commands:
        command_id, digest = (command['id'], digests[command['id']])
        if command_id in seen:
            continue
        seen.add(command_id)
        row = rows.get(command_id)
        if row is not None:
            if row.get('command_digest', digest) != digest:
                raise ValueError('command_id_payload_changed')
            if row['status'] != 'deferred':
                continue
            if command.get('action') in video_policy.ACTIONS:
                continue
        if command.get('action') in video_policy.ACTIONS:
            _policy_state(self)
        row = _claim(self, command, digest, ledger, rows)
        try:
            result = await asyncio.wait_for(self._dispatch(command, row, recorded), self.dispatch_timeout_seconds)
        except Exception as exc:
            result = {'status': 'unknown', 'reason': type(exc).__name__}
        _finish(self, row, result, ledger)
        results.append(_telemetry(row))
    self.last_result = {'checked_at': _utc_now(), 'processed': len(results), 'results': results}
    return self.last_result

def _load_queue(self):
    inbox = self._read_json(self.command_path, {'version': 1, 'commands': []})
    ledger = self._read_json(self.acknowledgement_path, {'version': 1, 'acknowledgements': []})
    state = self._read_json(self.state_path, {'version': 1, 'active_context': None})
    video_policy.validate_state(state)
    commands, recorded = (inbox.get('commands'), ledger.get('acknowledgements'))
    if not isinstance(commands, list) or len(commands) > 100 or (not isinstance(recorded, list)):
        raise ValueError('invalid_manifest_lists')
    rows = {}
    for row in recorded:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or (not row['id']) or (row['id'] in rows):
            raise ValueError('invalid_acknowledgement_id')
        if row.get('status') not in _TERMINAL | {'deferred'}:
            raise ValueError('invalid_acknowledgement_status')
        video_policy.validate_receipt(row)
        if row['status'] == 'deferred' and (not _finite_number(row.get('first_seen_unix')) or not isinstance(row.get('command_digest'), str) or len(row['command_digest']) != 64):
            raise ValueError('invalid_pending_acknowledgement')
        rows[row['id']] = row
    digests = {}
    for command in commands:
        if not isinstance(command, dict) or not isinstance(command.get('id'), str) or (not 1 <= len(command['id']) <= 200):
            raise ValueError('invalid_command_id')
        digest = hashlib.sha256(json.dumps(command, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()
        if command['id'] in digests and digests[command['id']] != digest:
            raise ValueError('conflicting_command_id')
        if command['id'] in rows and rows[command['id']].get('command_digest', digest) != digest:
            raise ValueError('command_id_payload_changed')
        digests[command['id']] = digest
    return (commands, ledger, rows, digests, state)
