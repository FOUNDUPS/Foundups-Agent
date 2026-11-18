"""Actual signed generation selection checks reuse the held fence, not snapshots."""
from contextlib import contextmanager

import pytest

from .test_reddog_current_generation_manifest_launch_selection import _prepared, NOW
from modules.communication.moltbot_bridge.src import reddog_current_generation_manifest_launch_selection as selection


def test_current_signed_generation_is_rechecked_without_nested_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(selection, '_now_epoch', lambda: NOW)
    _, _, boundary = _prepared(tmp_path)
    token = boundary.select({}, now_epoch=NOW)
    original = selection.reddog_runtime_artifact_generation_lock
    calls = []
    @contextmanager
    def counted(*args, **kwargs):
        calls.append(1)
        with original(*args, **kwargs):
            yield
    monkeypatch.setattr(selection, 'reddog_runtime_artifact_generation_lock', counted)
    with boundary._lease_current(token) as selected:
        before = len(calls)
        boundary._recheck_current_locked(selected)
        assert len(calls) == before
        changed = dict(selected, config_digest='sha256:'+'f'*64)
        with pytest.raises(ValueError):
            boundary._recheck_current_locked(changed)
        monkeypatch.setattr(selection, '_now_epoch', lambda: NOW+1000)
        with pytest.raises(ValueError):
            boundary._recheck_current_locked(selected)
