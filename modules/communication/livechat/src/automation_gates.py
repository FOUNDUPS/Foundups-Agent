"""
YouTube Automation Gates (WSP 77/91)
===================================

Centralizes "can we act?" checks for YouTube automation surfaces.

Design goals:
- Single STOP file to immediately halt automation without code edits.
- Small, dependency-free helpers callable from multiple modules.
- Telemetry-friendly snapshot for heartbeat + gate-lab correlation.

Non-goals:
- This module does not attempt to bypass platform enforcement.
"""

from __future__ import annotations

import os
import json
import math
import re
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Dict
from uuid import uuid4

from modules.infrastructure.shared_utilities.runtime_artifact_safety import runtime_operation_lock


REPO_ROOT = Path(__file__).resolve().parents[4]
COMMENTS_HALTED_EXIT_CODE = 78
QUALITY_REASONS = frozenset({'invalid_reply_text', 'review_rejected', 'review_unavailable_or_invalid'})
_INCIDENT_KEYS = {'version', 'kind', 'scope', 'incident_id', 'reason', 'recorded_at_unix'}
_YOUTUBE_RUNTIME_LOCK = Lock()


@contextmanager
def youtube_runtime_owner():
    """Exclude cooperating DAE and bounded request owners across checkouts."""
    # A Windows mutex reenters on the same thread, including across asyncio tasks.
    if not _YOUTUBE_RUNTIME_LOCK.acquire(blocking=False):
        raise TimeoutError('youtube_runtime_owner_busy')
    try:
        with runtime_operation_lock('foundups-youtube-runtime-owner', timeout_seconds=0.01):
            yield
    finally:
        _YOUTUBE_RUNTIME_LOCK.release()


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def stop_file_path() -> Path:
    path = Path(os.getenv("YT_AUTOMATION_STOP_FILE", "memory/STOP_YT_AUTOMATION"))
    return Path(os.path.abspath(path if path.is_absolute() else REPO_ROOT / path))


def _valid_incident(value) -> bool:
    try:
        return _incident_fields_valid(value)
    except (ValueError, TypeError, OverflowError):
        return False


def _incident_fields_valid(value) -> bool:
    return (isinstance(value, dict) and set(value) == _INCIDENT_KEYS
            and type(value['version']) is int and value['version'] == 1
            and value['kind'] == 'comment_reply_quality' and value['scope'] == 'comments'
            and isinstance(value['incident_id'], str)
            and re.fullmatch(r'[a-f0-9]{32}', value['incident_id']) is not None
            and isinstance(value['reason'], str) and value['reason'] in QUALITY_REASONS
            and type(value['recorded_at_unix']) in (int, float)
            and math.isfinite(value['recorded_at_unix']) and 0 < value['recorded_at_unix'] < 1e12)


def _safe_stop_path(path):
    if path.parent == path:
        raise ValueError('unsafe_stop_path')
    for component in (path, *path.parents):
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, 'st_file_attributes', 0) & 0x400:
            raise ValueError('unsafe_stop_path')


def _file_identity(metadata):
    return (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns)


def _unique_stop_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_stop_field')
        result[key] = value
    return result


def _stop_state():
    """Only a complete known incident gets a scoped exception; uncertainty is global."""
    try:
        path = stop_file_path()
        _safe_stop_path(path)
        try:
            before = path.lstat()
        except FileNotFoundError:
            return 'absent', None, None
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            return 'unknown', None, None
        with path.open('rb') as stream:
            opened = os.fstat(stream.fileno())
            raw = stream.read(4097)
        after = path.lstat()
        if _file_identity(before) != _file_identity(opened) or _file_identity(opened) != _file_identity(after):
            return 'unknown', None, None
        if len(raw) > 4096:
            return 'global', None, _file_identity(after)
        try:
            record = json.loads(raw, object_pairs_hook=_unique_stop_fields)
        except (ValueError, UnicodeError):
            return 'global', None, _file_identity(after)
        return ('quality', record, _file_identity(after)) if _valid_incident(record) else ('global', None, _file_identity(after))
    except (OSError, ValueError, TypeError, OverflowError, RecursionError):
        return 'unknown', None, None


def stop_active(scope: str = 'any') -> bool:
    """No argument retains any-STOP behavior; explicit other surfaces see global STOP."""
    if not isinstance(scope, str) or scope not in ('any', 'global', 'comments', 'livechat', 'scheduling', 'shorts', 'indexing'):
        return True
    state, _, _ = _stop_state()
    return state != 'absent' if scope in ('any', 'comments') else state not in ('absent', 'quality')


def read_comment_quality_stop():
    state, record, _ = _stop_state()
    return dict(record) if state == 'quality' else None


def _stop_lock_identity():
    return 'youtube-automation-stop:' + os.path.normcase(str(stop_file_path()))


def latch_comment_quality_stop(reason):
    """Exclusive create: never overwrite manual, newer or uncertain STOP evidence."""
    if not isinstance(reason, str) or reason not in QUALITY_REASONS:
        raise ValueError('not_a_quality_rejection')
    try:
        with runtime_operation_lock(_stop_lock_identity(), timeout_seconds=5):
            state, existing, _ = _stop_state()
            if state != 'absent':
                return {'created': False, 'persisted': state in ('quality', 'global'), 'incident': existing}
            path = stop_file_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            _safe_stop_path(path)
            record = dict(version=1, kind='comment_reply_quality', scope='comments',
                          incident_id=uuid4().hex, reason=reason, recorded_at_unix=time.time())
            with path.open('xb') as stream:
                stream.write((json.dumps(record, sort_keys=True, allow_nan=False) + '\n').encode())
                stream.flush(); os.fsync(stream.fileno())
            state, readback, _ = _stop_state()
            persisted = state == 'quality' and readback == record
            return {'created': persisted, 'persisted': persisted, 'incident': readback if persisted else None}
    except (OSError, ValueError, TypeError, TimeoutError):
        return {'created': False, 'persisted': False, 'incident': None}


def clear_comment_quality_stop(expected_record):
    """Explicit compare-and-clear for cooperating owners; never clears delivery claims."""
    if not _valid_incident(expected_record):
        return {'cleared': False, 'reason': 'invalid_expected_incident'}
    try:
        with runtime_operation_lock(_stop_lock_identity(), timeout_seconds=5):
            state, current, identity = _stop_state()
            if state != 'quality' or json.dumps(current, sort_keys=True) != json.dumps(expected_record, sort_keys=True):
                return {'cleared': False, 'reason': 'incident_changed_or_unrecognized'}
            check_state, check_record, check_identity = _stop_state()
            if check_state != state or check_record != current or check_identity != identity:
                return {'cleared': False, 'reason': 'incident_changed_or_unrecognized'}
            stop_file_path().unlink()
            return {'cleared': True, 'comments_stop_active': stop_active('comments')}
    except (OSError, ValueError, TypeError, TimeoutError):
        return {'cleared': False, 'reason': 'stop_unavailable'}


def comment_stop_result():
    state, record, _ = _stop_state()
    if state == 'absent':
        return None
    return {'state': 'halted', 'halted_for_comments_stop': True,
            'halted_for_reply_quality': state == 'quality',
            'quality_halt_reason': record['reason'] if record else 'comments_stop_active',
            'quality_stop_persisted': state in ('quality', 'global'),
            'quality_stop_incident_id': record['incident_id'] if record else None,
            'error': 'comments_stop_active', 'stats': {'comments_processed': 0, 'all_processed': False}}


def comments_exit_code(result):
    """Dedicated comments-halted CLI code; all prior other exit behavior remains zero."""
    halted = isinstance(result, dict) and any(result.get(key) is True for key in
        ('halted_for_reply_quality', 'halted_for_comments_stop'))
    return COMMENTS_HALTED_EXIT_CODE if halted else 0


def gate_snapshot() -> Dict[str, object]:
    """
    Snapshot current automation gates for observability (WSP 91).

    Keep this stable/compact; it is emitted frequently (heartbeat).
    """
    state, record, _ = _stop_state()
    comments_stopped = state != 'absent'
    return {
        "stop_file": str(stop_file_path()),
        "stop_active": state not in ('absent', 'quality'),
        "comments_stop_active": comments_stopped,
        "comment_quality_incident_id": record['incident_id'] if record else None,
        "comment_quality_reason": record['reason'] if record else None,
        "comment_stop_status": state,
        "yt_automation": _env_truthy("YT_AUTOMATION_ENABLED", "true"),
        "livechat_send": _env_truthy("YT_LIVECHAT_SEND_ENABLED", "true"),
        "livechat_dry_run": _env_truthy("YT_LIVECHAT_DRY_RUN", "false"),
        "comment_engagement": not comments_stopped and _env_truthy("YT_COMMENT_ENGAGEMENT_ENABLED", "true"),
        "livechat_ui_actions": _env_truthy("YT_LIVECHAT_UI_ACTIONS_ENABLED", "true"),
        "party_reactions": _env_truthy("YT_PARTY_REACTIONS_ENABLED", "true"),
        "announcements": _env_truthy("YT_LIVECHAT_ANNOUNCEMENTS_ENABLED", "true"),
        "stream_scraping": _env_truthy("YT_STREAM_SCRAPING_ENABLED", "true"),
        "stream_resolver": _env_truthy("YT_STREAM_RESOLVER_ENABLED", "true"),
        "comment_only": _env_truthy("YT_COMMENT_ONLY_MODE", "false"),
        "comment_reactions": _env_truthy("YT_COMMENT_REACTIONS_ENABLED", "true"),
        "engagement_tempo": os.getenv("YT_ENGAGEMENT_TEMPO", "012").upper(),
        "comment_like": _env_truthy("YT_COMMENT_LIKE_ENABLED", "true"),
        "comment_heart": _env_truthy("YT_COMMENT_HEART_ENABLED", "true"),
        "comment_reply": not comments_stopped and _env_truthy("YT_COMMENT_REPLY_ENABLED", "true"),
        "reply_basic_only": _env_truthy("YT_REPLY_BASIC_ONLY", "false"),
        "reply_no_classification": _env_truthy("YT_NO_CLASSIFICATION", "false"),
        "reply_no_semantic_state": _env_truthy("YT_NO_SEMANTIC_STATE", "false"),
        "stream_vision_disabled": os.getenv("STREAM_VISION_DISABLED", "true"),
    }

