"""Pure bounded validation/resolution for the manifest queue's private policies.

No IO, providers or execution. Only OperatorCommandQueue persists this state.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit

CHANNEL = re.compile(r"UC[A-Za-z0-9_-]{22}\Z")
VIDEO = re.compile(r"[A-Za-z0-9_-]{11}\Z")
SURFACES = {
    'metadata': {'title_mode', 'title_text', 'description_mode', 'description_text'},
    'scheduling': {'scheduling_enabled', 'max_per_cycle'},
    'shorts': {'shorts_enabled', 'topics', 'interval_minutes'},
}
GROUNDING = {'context', 'sources'}
FIELDS = set().union(*SURFACES.values(), GROUNDING)
ACTIONS = {'set_video_policy', 'clear_video_policy'}
MAX_POLICIES = 500
MAX_OBSERVATIONS = 200
MAX_EFFECT_CLAIMS = 500


def text(value, limit, *, empty=False):
    if (not isinstance(value, str) or len(value) > limit or (not empty and not value.strip())
            or any(unicodedata.category(c) in {'Cc', 'Cf', 'Cs'} and c not in '\n\t' for c in value)
            or any(token in value.lower() for token in ('<|', '|>', '[inst]', '[/inst]', '<<sys>>'))):
        raise ValueError('invalid_policy_text')
    return value


def ids(value, pattern, maximum):
    if (not isinstance(value, list) or not 1 <= len(value) <= maximum
            or any(not isinstance(v, str) or pattern.fullmatch(v) is None for v in value)
            or len(set(value)) != len(value)):
        raise ValueError('invalid_policy_scope')
    return sorted(value)


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('invalid_policy_integer')
    return value


def validate_payload(action, payload):
    if not isinstance(payload, dict):
        raise ValueError('payload_must_be_an_object')
    if action == 'clear_video_policy' and 'policy_id' in payload:
        if set(payload) != {'policy_id'}:
            raise ValueError('invalid_clear_policy_fields')
        return {'policy_id': text(payload['policy_id'], 200)}
    allowed = {'channel_ids', 'video_ids'} | (FIELDS | {'ttl_seconds', 'expires_at_unix'} if action == 'set_video_policy' else set())
    if set(payload) - allowed:
        raise ValueError('unknown_policy_fields')
    result = {'channel_ids': ids(payload.get('channel_ids'), CHANNEL, 20)}
    result['video_ids'] = ids(payload['video_ids'], VIDEO, 50) if 'video_ids' in payload else []
    if len(result['channel_ids']) * max(1, len(result['video_ids'])) > MAX_POLICIES:
        raise ValueError('video_policy_scope_capacity_exceeded')
    if action == 'set_video_policy':
        result['ttl_seconds'] = integer(payload.get('ttl_seconds', 3600), 60, 86400)
        if 'expires_at_unix' in payload:
            value = payload['expires_at_unix']
            if type(value) not in (int, float) or not 0 < value < 1e12 or not math.isfinite(value):
                raise ValueError('invalid_policy_deadline')
            result['expires_at_unix'] = value
        result.update(validate_fields(payload, result['video_ids']))
    return result


def validate_fields(payload, videos):
    values = {k: payload[k] for k in FIELDS if k in payload}
    if not values:
        raise ValueError('empty_video_policy')
    for kind, limit in (('title', 100), ('description', 5000)):
        mode, content = values.get(kind + '_mode'), values.get(kind + '_text')
        if kind + '_mode' in values and mode not in ('preserve', 'auto', 'replace'):
            raise ValueError('invalid_policy_mode')
        if mode == 'replace':
            if len(videos) != 1:
                raise ValueError('replacement_requires_one_video')
            values[kind + '_text'] = text(content, limit)
        elif kind + '_text' in values:
            raise ValueError('replacement_text_requires_replace_mode')
    for name in ('scheduling_enabled', 'shorts_enabled'):
        if name in values and type(values[name]) is not bool:
            raise ValueError('invalid_policy_boolean')
    for name, maximum in (('max_per_cycle', 100), ('interval_minutes', 10080)):
        if name in values:
            integer(values[name], 1, maximum)
    if 'topics' in values:
        topics = values['topics']
        if not isinstance(topics, list) or not 1 <= len(topics) <= 20:
            raise ValueError('invalid_policy_topics')
        values['topics'] = [text(topic, 100) for topic in topics]
    if 'context' in values:
        text(values['context'], 2000)
    if 'sources' in values:
        validate_sources(values['sources'])
    return values


def validate_sources(sources):
    if not isinstance(sources, list) or not 1 <= len(sources) <= 10:
        raise ValueError('invalid_policy_sources')
    for source in sources:
        text(source, 2048)
        parsed = urlsplit(source)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or any(c.isspace() for c in source)
                or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
            raise ValueError('invalid_policy_source_url')


def scope(payload):
    return [(channel, video) for channel in payload['channel_ids']
            for video in (payload['video_ids'] or [None])]


def validate_state(state):
    policies = state.get('video_policies', [])
    observations = state.get('video_policy_observations', [])
    claims = state.get('video_effect_claims', [])
    if not isinstance(policies, list) or len(policies) > MAX_POLICIES:
        raise ValueError('invalid_video_policy_state')
    for item in policies:
        if not isinstance(item, dict) or set(item) != {'id', 'digest', 'channel_id', 'video_id', 'expires_at_unix', 'fields'}:
            raise ValueError('invalid_video_policy_record')
        ids([item['channel_id']], CHANNEL, 1)
        if item['video_id'] is not None:
            ids([item['video_id']], VIDEO, 1)
        text(item['id'], 200)
        if not re.fullmatch('[0-9a-f]{64}', str(item['digest'])):
            raise ValueError('invalid_video_policy_digest')
        expiry = item['expires_at_unix']
        if type(expiry) not in (int, float) or not 0 < expiry < 1e12:
            raise ValueError('invalid_video_policy_expiry')
        if not isinstance(item['fields'], dict) or set(item['fields']) - FIELDS:
            raise ValueError('invalid_video_policy_fields')
        if item['fields']:
            validate_fields(item['fields'], [item['video_id']] if item['video_id'] else [])
    if not isinstance(observations, list) or len(observations) > MAX_OBSERVATIONS:
        raise ValueError('invalid_video_policy_observations')
    if not isinstance(claims, list) or len(claims) > MAX_EFFECT_CLAIMS:
        raise ValueError('invalid_video_effect_claims')
    for item in observations:
        if not isinstance(item, dict) or set(item) != {'policy_ids', 'surface', 'channel_id', 'video_id', 'outcome', 'detail', 'recorded_at'}:
            raise ValueError('invalid_video_policy_observation')
        observation(item['policy_ids'], item['surface'], item['channel_id'], item['video_id'], item['outcome'], item['detail'])
        text(item['recorded_at'], 80)
    seen = {}
    for claim in claims:
        validate_claim(claim, seen)
    return policies


def validate_artifact(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('invalid_artifact_sha256')


def validate_receipt(row):
    if row.get('action') not in ACTIONS or row.get('status') != 'accepted':
        return
    result = row.get('result')
    if not isinstance(result, dict):
        raise ValueError('invalid_video_policy_receipt')
    validate_artifact(result.get('policy_state_digest'))
    fields, scopes = result.get('policy_fields'), result.get('policy_scopes')
    if (not isinstance(fields, list) or any(not isinstance(k, str) or k not in FIELDS for k in fields)
            or not isinstance(scopes, list) or len(scopes) > MAX_POLICIES):
        raise ValueError('invalid_video_policy_receipt_fields')
    if row['action'] == 'set_video_policy' and (not fields or not scopes):
        raise ValueError('invalid_video_policy_receipt_scope')
    if row['action'] == 'set_video_policy':
        expiry = result.get('expires_at_unix')
        if type(expiry) not in (int, float) or not 0 < expiry < 1e12 or not math.isfinite(expiry):
            raise ValueError('invalid_video_policy_receipt_expiry')
    for pair in scopes:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('invalid_video_policy_receipt_scope')
        ids([pair[0]], CHANNEL, 1)
        if pair[1] is not None:
            ids([pair[1]], VIDEO, 1)


def policy_ids(value):
    if not isinstance(value, list) or len(value) > 100 or any(not isinstance(v, str) for v in value):
        raise ValueError('invalid_observation_policy_ids')
    if len(set(value)) != len(value):
        raise ValueError('invalid_observation_policy_ids')
    for item in value:
        text(item, 200)
    return list(value)


def observation(command_ids, surface, channel_id, video_id, outcome, detail):
    command_ids = policy_ids(command_ids)
    ids([channel_id], CHANNEL, 1)
    if video_id is not None:
        ids([video_id], VIDEO, 1)
    if surface not in SURFACES or outcome not in {'observed', 'applied', 'unknown', 'blocked', 'failed'}:
        raise ValueError('invalid_observation_outcome_or_surface')
    if not isinstance(detail, dict) or len(detail) > 10:
        raise ValueError('invalid_observation_detail')
    for key, value in detail.items():
        text(key, 80)
        if isinstance(value, str):
            text(value, 500, empty=True)
        elif type(value) not in (bool, int) or (type(value) is int and not -1000000 <= value <= 1000000):
            raise ValueError('invalid_observation_detail_value')
    if outcome == 'applied' and detail.get('persisted_readback') is not True:
        raise ValueError('applied_requires_persisted_readback')
    for key in ('artifact_sha256', 'draft_sha256', 'readback_sha256', 'policy_fingerprint'):
        if key in detail:
            validate_artifact(detail[key])
    return {'policy_ids': command_ids, 'surface': surface, 'channel_id': channel_id,
            'video_id': video_id, 'outcome': outcome, 'detail': dict(detail)}


def validate_claim(claim, seen):
    if not isinstance(claim, dict) or set(claim) != {'kind', 'channel_id', 'video_id', 'content_sha256', 'policy_ids', 'fingerprints', 'outcome', 'claimed_at'}:
        raise ValueError('invalid_video_effect_claim')
    ids([claim['channel_id']], CHANNEL, 1)
    validate_artifact(claim['content_sha256'])
    if claim['kind'] not in ('upload', 'save'):
        raise ValueError('invalid_video_effect_kind')
    if claim['kind'] == 'save':
        ids([claim['video_id']], VIDEO, 1)
    elif claim['video_id'] is not None:
        raise ValueError('invalid_video_effect_scope')
    fingerprints = claim['fingerprints']
    required = {'shorts'} if claim['kind'] == 'upload' else {'metadata'}
    if not isinstance(fingerprints, dict) or not required <= set(fingerprints) or set(fingerprints) - SURFACES.keys():
        raise ValueError('invalid_video_effect_fingerprints')
    for value in fingerprints.values():
        validate_artifact(value)
    policy_ids(claim['policy_ids'])
    if claim['outcome'] not in {'observed', 'applied', 'unknown', 'blocked', 'failed'}:
        raise ValueError('invalid_video_effect_claim_outcome')
    text(claim['claimed_at'], 80)
    claim_timestamp(claim)
    identity = effect_identity(claim)
    if identity in seen and (claim['kind'] == 'upload' or seen[identity]['outcome'] != 'applied'):
        raise ValueError('duplicate_video_effect_claim')
    seen[identity] = claim


def effect_identity(claim):
    return (claim['kind'], claim['channel_id'], claim['video_id'] if claim['kind'] == 'save' else claim['content_sha256'])


def claim_timestamp(claim):
    value = datetime.fromisoformat(claim['claimed_at'])
    if value.tzinfo is None:
        raise ValueError('invalid_video_effect_timestamp')
    return value.timestamp()


def reserve_effect(state, kind, channel, video, digest, command_ids, fingerprints, timestamp):
    validate_artifact(digest)
    command_ids = policy_ids(command_ids)
    snapshot_ids = set()
    for surface, fingerprint in fingerprints.items():
        snapshot = resolve_policy(state, channel, video, surface, timestamp)
        if snapshot['fingerprint'] != fingerprint:
            raise ValueError('video_policy_snapshot_changed')
        snapshot_ids.update(snapshot['matched_command_ids'])
        if kind == 'upload':
            if snapshot.get('shorts_enabled') is False:
                raise ValueError('shorts_policy_paused')
            previous = snapshot.get('last_upload_attempt_unix')
            interval = snapshot.get('interval_minutes')
            if previous is not None and interval is not None and timestamp < previous + interval * 60:
                raise ValueError('shorts_interval_not_due')
    if sorted(snapshot_ids) != sorted(command_ids):
        raise ValueError('video_policy_snapshot_changed')
    claims = state.setdefault('video_effect_claims', [])
    claim = {'kind': kind, 'channel_id': channel, 'video_id': video, 'content_sha256': digest,
             'policy_ids': command_ids, 'fingerprints': dict(fingerprints), 'outcome': 'unknown',
             'claimed_at': datetime.fromtimestamp(timestamp, timezone.utc).isoformat()}
    prior = next((c for c in reversed(claims) if effect_identity(c) == effect_identity(claim)), None)
    if prior and (kind == 'upload' or prior['outcome'] != 'applied' or prior['content_sha256'] == digest):
        raise ValueError('video_effect_already_claimed')
    if len(claims) >= MAX_EFFECT_CLAIMS:
        raise ValueError('video_effect_claim_capacity_reached')
    return claims, claim


def verify_save(state, channel, video, draft, readback, fingerprints):
    validate_artifact(draft)
    validate_artifact(readback)
    if draft != readback:
        raise ValueError('persisted_readback_mismatch')
    claim = next((c for c in reversed(state.get('video_effect_claims', []))
                  if c['kind'] == 'save' and c['channel_id'] == channel and c['video_id'] == video), None)
    if not claim or claim['content_sha256'] != draft or claim['fingerprints'] != fingerprints:
        raise ValueError('video_save_claim_mismatch')
    if 'scheduling' in claim['fingerprints']:
        raise ValueError('schedule_readback_not_qualified')
    return claim


def apply_policy(state, command, payload, row):
    policies = validate_state(state)
    target = set(scope(payload)) if 'channel_ids' in payload else set()
    if command['action'] == 'clear_video_policy':
        state['video_policies'] = [p for p in policies if not (
            p['id'] == payload.get('policy_id') or (p['channel_id'], p['video_id']) in target)]
        return
    fields = {key: payload[key] for key in FIELDS if key in payload}
    for previous in policies:
        if (previous['channel_id'], previous['video_id']) in target:
            for key in fields:
                previous['fields'].pop(key, None)
            # Mode/text form one field group: preserve/auto cannot retain old text.
            for kind in ('title', 'description'):
                if kind + '_mode' in fields:
                    previous['fields'].pop(kind + '_text', None)
    policies[:] = [p for p in policies if p['fields']]
    if len(policies) + len(target) > MAX_POLICIES:
        raise ValueError('video_policy_capacity_reached')
    policies.extend({'id': command['id'], 'digest': row['command_digest'],
                     'channel_id': channel, 'video_id': video, 'fields': dict(fields),
                     'expires_at_unix': min(row['first_seen_unix'] + payload['ttl_seconds'], payload.get('expires_at_unix', float('inf')))}
                    for channel, video in sorted(target, key=lambda pair: (pair[0], pair[1] or '')))
    state['video_policies'] = policies


def state_digest(state):
    return hashlib.sha256(json.dumps(state.get('video_policies', []), sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def resolve_policy(state, channel_id, video_id, surface, now):
    if not isinstance(channel_id, str) or CHANNEL.fullmatch(channel_id) is None:
        raise ValueError('invalid_receiving_channel')
    if video_id is not None and (not isinstance(video_id, str) or VIDEO.fullmatch(video_id) is None):
        raise ValueError('invalid_receiving_video')
    if surface not in SURFACES:
        raise ValueError('invalid_policy_surface')
    chosen = {}
    for item in validate_state(state):
        if (item['channel_id'] != channel_id or item['video_id'] not in (None, video_id)
                or item['expires_at_unix'] <= now):
            continue
        for key, value in item['fields'].items():
            if key in SURFACES[surface] | GROUNDING:
                chosen[key] = (value, item)
    contributing = {entry[1]['id']: entry[1] for entry in chosen.values()}
    expiry = {key: entry[1]['expires_at_unix'] for key, entry in chosen.items()}
    binding = {'channel_id': channel_id, 'video_id': video_id, 'surface': surface,
               'fields': {key: entry[0] for key, entry in chosen.items()},
               'commands': {key: item['digest'] for key, item in contributing.items()}, 'expiry': expiry}
    fingerprint = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'available': True, 'blocked': False, 'reason': None,
            **binding['fields'], 'matched_command_ids': sorted(contributing),
            'fingerprint': fingerprint, 'field_expiries': expiry,
            'expires_at_unix': min(expiry.values()) if expiry else None,
            **({'last_upload_attempt_unix': max((claim_timestamp(c) for c in state.get('video_effect_claims', [])
                if c['kind'] == 'upload' and c['channel_id'] == channel_id), default=None)} if surface == 'shorts' else {})}
