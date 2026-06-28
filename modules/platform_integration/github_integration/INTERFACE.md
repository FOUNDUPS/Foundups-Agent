# INTERFACE (WSP 11)

## RedDog read-only permission probe

**Module:** `reddog_github_permission_probe.py`
**Slice:** `REDDOG_GITHUB_PERMISSION_PROBE_PHASE1`

### `probe_repo_permission(repo_full_name, *, principal_login=None, principal_provider="github", backend=None, now=None, ttl_seconds=300) -> RepoPermissionProbeSnapshot`

Read-only probe of GitHub repository permission for the authenticated principal.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `repo_full_name` | `str` | yes | `owner/repo` |
| `principal_login` | `str` | no | Override login; default from backend |
| `principal_provider` | `str` | no | Default `github` |
| `backend` | `PermissionProbeBackend` | no | Injectable backend; default `gh_cli` read-only |
| `now` | `datetime` | no | Test clock |
| `ttl_seconds` | `int` | no | Snapshot freshness TTL (default 300) |

**Returns:** `RepoPermissionProbeSnapshot` with conservative `can_read` / `can_write` / `can_admin`, `evidence_digest`, `raw_secret_included=false`.

**Errors:** Does not raise on missing auth; returns `permission=unknown` fail-closed.

### `RepoPermissionProbeSnapshot.to_repo_permission_snapshot() -> dict`

Maps into `#889` work-order `repo_permission_snapshot` fields.

### `is_snapshot_fresh(snapshot, now=None) -> bool`

Returns false when `expires_at` is in the past.

## Parameters
## Returns
## Errors
## Examples
