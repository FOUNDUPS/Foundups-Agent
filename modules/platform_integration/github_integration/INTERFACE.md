# INTERFACE (WSP 11)

## Legacy adapter workflow declaration

`await GitHubAPIAdapter.trigger_workflow(workflow_id, ref, inputs=None, *,
agent_id, session_id, cube_type)`

The three identity arguments are required keywords; inputs may be omitted.
The adapter retains its existing mock transport. Syntax and argument binding
are verified; this interface does not establish live workflow dispatch.
It is separate from the GitHubAPIClient observation interface below.

## Immutable regular-file observation

`await GitHubAPIClient.get_file_observation(file_path: str, *,
commit_sha: Optional[str] = None) -> GitHubFileObservation`

Read metadata, the actual default-branch reference, an exact commit, nonrecursive
Git trees and a blob, then compare repository metadata again. At most13 GETs
for an eight-component path; an explicit historical commit is allowed and remains
distinguishable from the initially observed default commit. A client context is
required for real HTTP. This method performs no repository write or file execution.

The frozen, slotted record contains repository_id, owner_id, repository_full_name,
default_branch, private, observed_default_commit_sha, commit_sha, tree_sha (root),
path, mode, blob_sha, content (bytes), and size_bytes. Numeric IDs are positive
builtin integers; absent IDs are rejected. Git IDs are exact lowercase40-hex.
Private visibility is preserved; this reader does not decide admission policy.

Paths contain1..8 nonempty components, at most1024 UTF-8 bytes; dot components,
backslashes and controls reject. Trees must be complete (truncated=False), with
at most4096 entries and one matching entry. Directories use040000/tree; only
100644/blob and100755/blob terminal files qualify. Symlinks and submodules reject.
Blob bytes are at most16384; bounded base64 admits LF/CRLF wrapping, then requires
strict canonical decoding, exact declared length and the Git blob SHA-1 identity.
Malformed observation fields raise GitHubAPIError with a fixed field name.

The record establishes response consistency, not atomic repository provenance.
Before/after metadata checks catch ordinary drift but cannot exclude intervening
name reuse or establish that a previously observed tip remains current.

Observation-only HTTP policy: exact base https://api.github.com, GET, fixed-origin
relative endpoints and no redirects. Request identity encoding, disable automatic
decompression and reject nonidentity Content-Encoding. Require200 and a JSON
application media type (application/json or application/*+json); count actual
body bytes in a read loop up to2MiB before strict UTF-8 JSON decoding. Reject a
declared oversize early; missing or misleading Content-Length cannot raise the
actual-byte limit. Malformed JSON, including recursion errors, stays field-only.
Each request has total5s/connect2s/socket-connect2s/socket-read2s; the complete
observation has a30s timeout. Caller cancellation propagates and response context
cleanup runs. Scheduling and cancellation cleanup can exceed these application
deadlines; no hard process-time/RSS bound is implied. At most13 logical GET calls,
zero application retries; pinned aiohttp3.13.5 may reconnect/retry an idempotent
request once internally. No hard TCP/DNS attempt count is claimed.
Legacy operations keep their prior redirect, timeout, body and authentication
behavior; the new transport policy is a private observation-only request opt-in.
An admitted provider boundary, fresh identity-bound control challenge and proof of
key possession are required before repository claims; no permission, issuer,
minting, reward, agent-work or trading grant follows from this record.

Compatibility: GitHubRepository retains its seven fields, constructor and
serialization shape; get_file_content retains its legacy (text, blob_sha) tuple.
The legacy Contents method does not satisfy the regular-file observation contract.

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
