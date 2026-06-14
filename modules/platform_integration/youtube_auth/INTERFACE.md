# YouTube Authentication Module Interface

## Overview
The YouTube Authentication module handles OAuth 2.0 authentication with the YouTube API, managing credential loading, refreshing, and the initial authorization flow. It implements multi-client OAuth fallback for quota management.

## Exports
This module exports:
- `get_authenticated_service`: Function to authenticate and obtain a YouTube API service object
- `oauth_browser.resolve_browser_for_set`: Resolve the per-set OAuth browser executable
- `oauth_browser.BrowserNotFoundError`: Raised when no browser executable can be resolved for a set

## Functions

### `get_authenticated_service() -> googleapiclient.discovery.Resource`
Authenticates the user with YouTube API using OAuth 2.0 and returns a YouTube API service object.

**Parameters:**
- None

**Returns:**
- `googleapiclient.discovery.Resource`: A YouTube API service object that can be used to make API calls

**Behavior:**
- Sequentially tries up to 4 credential sets defined in environment variables
- Loads existing credentials from token files if available
- Refreshes credentials if expired
- Initiates a new OAuth flow if no valid credentials are found
- Saves new or refreshed credentials to the appropriate token file
- Falls back to the next credential set if authentication fails or quota is exceeded
- Raises an exception if all credential sets fail

## oauth_browser (per-set OAuth browser resolution)

`src/oauth_browser.py` is the single source of truth for which browser
executable the OAuth consent flow opens per credential set. It centralizes the
candidate-path ordering that previously lived (and drifted) inline in
youtube_auth.py and in the authorize_setN.py scripts.

### `resolve_browser_for_set(set_id: int) -> tuple[str, str]`
Returns `(browser_name, executable_path)` for a credential set.

- `set_id == 1` -> `browser_name == "chrome"`; candidate order (first existing wins):
  `CHROME_PATH` env, then 64-bit Chrome, then x86 Chrome (mirrors `authorize_set1.py`).
- `set_id == 10` -> `browser_name == "edge"`; candidate order:
  `EDGE_PATH` env, then 64-bit Edge, then x86 Edge (mirrors `authorize_set10.py`).
- Raises `BrowserNotFoundError` if no candidate exists, or if `set_id` is unknown.

### `class BrowserNotFoundError(Exception)`
Carries operator-actionable context:
- `set_id`: the credential set that failed resolution.
- `attempted_paths`: concrete candidate paths that were checked (unset env vars skipped).
- `operator_action`: the exact reauth command from `oauth_health.reauth_command_for(set_id)`.

## Environment Variables
The module requires the following environment variables to be set:

- `YOUTUBE_SCOPES`: Space-separated list of OAuth scopes required
- `GOOGLE_CLIENT_SECRETS_FILE_1` through `GOOGLE_CLIENT_SECRETS_FILE_4`: Paths to client secrets files
- `OAUTH_TOKEN_FILE_1` through `OAUTH_TOKEN_FILE_4`: Paths to token files for credential storage

Optional (used by `oauth_browser.resolve_browser_for_set`):
- `CHROME_PATH`: Override the Chrome executable used for set 1 OAuth.
- `EDGE_PATH`: Override the Edge executable used for set 10 OAuth.

## Usage Example
```python
from modules.youtube_auth import get_authenticated_service

try:
    # Get authenticated YouTube API service
    youtube = get_authenticated_service()
    
    # Use the service to make API calls
    response = youtube.channels().list(
        part='snippet',
        mine=True
    ).execute()
    
    channel_title = response['items'][0]['snippet']['title']
    print(f"Authenticated as channel: {channel_title}")
    
except Exception as e:
    print(f"Authentication failed: {e}")
```

## Dependencies
- google.oauth2.credentials
- google_auth_oauthlib.flow
- googleapiclient.discovery
- google.auth.transport.requests
- dotenv

## Error Handling
- `ValueError`: Raised if required environment variables are missing
- `Exception`: Raised if all credential sets fail to authenticate
- HTTP errors from the YouTube API are logged but handled internally during authentication

## Internal Functions
The module contains internal helper functions not part of the public interface:
- `get_credentials_for_index(index)`: Helper function to retrieve credential paths for a specific index

---

## OAuth Credential Health Reporting (`oauth_health.py`)

WSP 97 truth signaling for credential capacity visibility.

### Status Vocabulary
| Status | Meaning |
|--------|---------|
| `healthy` | Refresh token valid, quota available |
| `token_revoked` | User revoked grant in Google account UI |
| `token_expired_or_revoked` | `invalid_grant` but cause not distinguishable |
| `refresh_failed` | Network or non-auth exception during refresh |
| `credential_set_unconfigured` | Env or token/secret file missing |
| `no_refresh_token` | Credential loaded but lacks refresh_token |
| `quota_exhausted` | Exhausted this cycle, not an auth failure |

### Key Functions

#### `classify_refresh_error(error_msg: str) -> Tuple[str, str]`
Maps a Google OAuth refresh exception to `(status, reason)`. Only claims `token_revoked` when message explicitly contains "revoked".

#### `write_health_report(per_set, output_path=None) -> Path`
Persists JSON artifact to `reports/oauth_credential_health.json`:
```json
{
  "generated_at": "<iso8601>",
  "credential_sets": {
    "total_configured": 2,
    "operational": [10],
    "dead": [1],
    "quota_exhausted_today": [],
    "effective_daily_quota_estimate": 10000
  },
  "per_set": [
    {
      "set_id": 1,
      "status": "token_expired_or_revoked",
      "operator_action": "python modules/platform_integration/youtube_auth/scripts/authorize_set1.py",
      ...
    }
  ]
}
```

#### `format_capacity_log(capacity) -> str`
Returns a one-line log message surfacing dead sets and action required.

#### `emit_critical_reauth(set_id, status, reason)`
Emits CRITICAL log with exact reauth command.

### Operator Visibility
When Set 1 is dead and Set 10 is healthy:
- Artifact: `dead=[1]`, `operational=[10]`, `effective_daily_quota_estimate=10000`
- Log: `"1/2 sets operational; dead=[1]; action_required=python .../authorize_set1.py"`
- CRITICAL: `"operator must run: python modules/.../authorize_set1.py (use Chrome)"` 