"""Two-process actual same-inode fence; synthetic authority, actual crypto and stores."""
from contextlib import contextmanager
import multiprocessing
from pathlib import Path
import sys

import pytest

from .reddog_live_lease_composition_support import setup, StrictLease
from .test_reddog_live_lease_composition import route, permit
from modules.infrastructure.shared_utilities.reddog_runtime_artifact_generation import (
    reddog_runtime_artifact_generation_lock, REDDOG_RUNTIME_ARTIFACT_GENERATION_LOCK,
)


def _probe(path, channel):
    import fcntl
    import os
    try:
        while channel.recv() == 'probe':
            with Path(path).open('rb') as stream:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    held = True
                else:
                    held = False
                    fcntl.flock(stream, fcntl.LOCK_UN)
                channel.send((held, os.fstat(stream.fileno()).st_ino))
    finally:
        channel.close()


@contextmanager
def observer(path):
    context = multiprocessing.get_context('spawn')
    parent, child = context.Pipe()
    process = context.Process(target=_probe, args=(str(path), child))
    process.start()
    child.close()
    def check(expected):
        parent.send('probe')
        assert parent.poll(30), 'bounded_lock_probe_did_not_respond'
        held, inode = parent.recv()
        assert held is expected and inode == path.stat().st_ino
    try:
        yield check
    finally:
        if process.is_alive():
            parent.send('stop')
        process.join(5)
        if process.is_alive():
            process.terminate()
            process.join(2)
        parent.close()
        assert process.exitcode == 0


@contextmanager
def bounded_call():
    import signal
    assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    prior = signal.getsignal(signal.SIGALRM)
    def timeout(*args):
        raise TimeoutError('bounded_test_generation_lock_wait')
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 30.0)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prior)


class NativeLease(StrictLease):
    @contextmanager
    def _lease_current(self, token):
        with reddog_runtime_artifact_generation_lock(self.state.store,
                repo_root=self.state.repo, allow_sealed=True):
            with super()._lease_current(token) as selection:
                yield selection


@pytest.mark.skipif(sys.platform != 'linux', reason='actual POSIX two-process fence')
@pytest.mark.parametrize('domain', ['parent', 'effect'])
def test_factory_revalidates_under_same_inode_without_nested_lock(monkeypatch, tmp_path, domain):
    state = setup(monkeypatch, tmp_path)
    state.lease = NativeLease(state)
    provider = route(monkeypatch, tmp_path / 'grant', state, domain)
    admitted = permit(state, domain)
    assert admitted is not None
    path = state.store / REDDOG_RUNTIME_ARTIFACT_GENERATION_LOCK
    with observer(path) as check:
        check(False)
        state.scope_probe = lambda: check(True)
        with bounded_call():
            grant = provider.issue_grant(state.kw['target'], elevated_consensus_signing_permit=admitted)
        check(False)
    assert grant['expires_at'] <= 1020 and state.responses[-1].accepted is True
    assert not state.nonces._owned and not state.lease.active
