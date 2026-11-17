"""Private opaque scope for one authenticated current-owner generation lease."""
from contextlib import contextmanager
from pathlib import Path
from weakref import WeakKeyDictionary
import math
import os
import threading

class _CurrentOwnerUseScope:
    """Opaque, thread/process-local lifetime of one real authenticated lease."""
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("current_owner_scope_construction_forbidden")

    def __copy__(self):
        raise TypeError("current_owner_scope_copy_forbidden")

    def __deepcopy__(self, memo):
        raise TypeError("current_owner_scope_copy_forbidden")

    def __reduce__(self):
        raise TypeError("current_owner_scope_pickle_forbidden")


_SCOPE_LOCK = threading.Lock()
_LIVE_SCOPES = WeakKeyDictionary()


def _scope_clock(record):
    from . import reddog_signer_owner_e0_current_selection as _owner
    wall, mono = _owner.time.time(), _owner.time.monotonic()
    if (type(wall) not in (int, float) or type(mono) not in (int, float)
            or not math.isfinite(wall) or not math.isfinite(mono)
            or min(wall, mono) < 0 or wall < record['wall'] or mono < record['mono']):
        raise ValueError("current_owner_scope_clock_invalid")
    record['wall'], record['mono'] = wall, mono
    return wall


def _scope_admission(scope, *, owner_config_path, repo_root):
    from . import reddog_signer_owner_e0_current_selection as _owner
    from . import reddog_signer_system_service_manifest_selection_loader as loader
    from .reddog_runtime_artifact_manifest_contract import canonical_json
    with _SCOPE_LOCK:
        record = _LIVE_SCOPES.get(scope) if type(scope) is _CurrentOwnerUseScope else None
    if (record is None or record['thread'] != threading.get_ident() or record['pid'] != os.getpid()
            or record['path'] != Path(owner_config_path).resolve() or record['repo'] != Path(repo_root).resolve()):
        raise ValueError("current_owner_scope_not_live")
    _scope_clock(record)
    owner = loader._load_owner_config(record['path'], repo=record['repo'])
    if canonical_json(owner) != record['owner']:
        raise ValueError("current_owner_scope_owner_changed")
    record['boundary']._recheck_current_locked(record['selected'])
    current = _owner._validated_selected_lease(record['repo'], record['selected'], record['policy'])
    if (canonical_json(dict(current.selection)) != record['selection']
            or canonical_json(_owner.thaw_owner_e0_policy(current.policy)) != record['policy_bytes']):
        raise ValueError("current_owner_scope_binding_changed")
    now = _scope_clock(record)
    if not current.selection['selection_issued_at'] <= now < current.selection['selection_expires_at']:
        raise ValueError("current_owner_scope_expired")
    if not current.policy['issued_at'] <= now < current.policy['expires_at']:
        raise ValueError("current_owner_scope_expired")
    return owner, current


@contextmanager
def _lease_validated_owner_e0_current_scope(*, owner_config_path, repo_root, policy):
    from . import reddog_signer_owner_e0_current_selection as _owner
    from . import reddog_signer_system_service_manifest_selection_loader as loader
    from .reddog_runtime_artifact_manifest_contract import canonical_json
    repo, path = Path(repo_root).resolve(), Path(owner_config_path).resolve()
    capability, boundary = _owner.load_system_service_manifest_selection(owner_config_path=path, repo_root=repo)
    scope = object.__new__(_CurrentOwnerUseScope)
    with boundary._lease_current(capability) as selected:
        owner = loader._load_owner_config(path, repo=repo)
        if owner['schema_version'] != loader.SCHEMA_VERSION_V13:
            raise ValueError("current_owner_scope_owner_version")
        current = _owner._validated_selected_lease(repo, selected, policy)
        from .reddog_consensus_nonce_custody import current_consensus_nonce_custody
        current_consensus_nonce_custody(owner, _owner.thaw_owner_e0_policy(current.policy), repo, _owner.time.time())
        record = dict(path=path, repo=repo, owner=canonical_json(owner), boundary=boundary,
            selected=dict(selected), selection=canonical_json(dict(selected)),
            policy=_owner.freeze_owner_e0_policy(_owner.thaw_owner_e0_policy(current.policy)),
            policy_bytes=canonical_json(_owner.thaw_owner_e0_policy(current.policy)),
            thread=threading.get_ident(), pid=os.getpid(), wall=0, mono=0)
        with _SCOPE_LOCK:
            _LIVE_SCOPES[scope] = record
        try:
            _scope_admission(scope, owner_config_path=path, repo_root=repo)
            yield scope
            _scope_admission(scope, owner_config_path=path, repo_root=repo)
        finally:
            with _SCOPE_LOCK:
                _LIVE_SCOPES.pop(scope, None)
