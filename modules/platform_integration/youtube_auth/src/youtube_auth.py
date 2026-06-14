import os
import logging
from dotenv import load_dotenv
import google.oauth2.credentials
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from modules.platform_integration.youtube_auth.src.quota_monitor import QuotaMonitor
from modules.platform_integration.youtube_auth.src import oauth_health

logger = logging.getLogger(__name__)

# Reduce noisy upstream logging that is not actionable for Foundups DAEs.
# Example: "file_cache is only supported with oauth2client<4.0.0"
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)

# Fixed OAuth redirect-listener ports per credential set. These MUST mirror the
# authorize scripts so the supervised preflight reauth lands on the SAME port
# Google has whitelisted for each client (authorize_set1.py -> 8080,
# authorize_set10.py -> 8090). Historically preflight used run_local_server(port=0)
# which picks a random port; that mismatch can cause redirect_uri_mismatch and
# silently swallowed Set-1 failures. Env overrides mirror the authorize scripts.
OAUTH_PORT_SET1 = 8080
OAUTH_PORT_SET10 = 8090


def _oauth_port_for_set(set_id: int) -> int:
    """Resolve the fixed OAuth listener port for a credential set.

    Mirrors authorize_set1.py / authorize_set10.py exactly (env override first,
    then the fixed default). Unknown sets fall back to OAUTH_PORT_SET1's default
    so we never regress to a random port=0 in the supervised path.
    """
    if set_id == 10:
        return int(os.getenv("OAUTH_PORT_SET10", str(OAUTH_PORT_SET10)))
    return int(os.getenv("OAUTH_PORT_SET1", str(OAUTH_PORT_SET1)))

# Initialize quota monitor
quota_monitor = QuotaMonitor()

# Load environment variables once when the module is imported
load_dotenv()

def get_credentials_for_index(index):
    """
    Get credentials for a specific index (1-5).
    Returns tuple of (client_secrets_file, token_file) or None if not found.
    """


    client_secrets = os.getenv(f'GOOGLE_CLIENT_SECRETS_FILE_{index}')
    token_file = os.getenv(f'OAUTH_TOKEN_FILE_{index}')
    
    if not client_secrets or not token_file:
        return None
        
    if not os.path.exists(client_secrets):
        logger.error(f"Client secrets file not found at: {client_secrets}")
        return None
        
    return client_secrets, token_file

def _persist_health_snapshot(failing_set=None, failing_status=None, failing_reason=None):
    """
    Write modules/platform_integration/youtube_auth/reports/oauth_credential_health.json
    summarizing the current rotation state. Called whenever we classify an
    invalid_grant or preflight completes so operators see real capacity.

    Healthy sets = configured sets not marked exhausted/dead.
    The caller may pass a specific failing set to override its status in the
    snapshot (used when marking a fresh invalid_grant before it appears in
    exhausted_sets downstream).
    """
    from modules.platform_integration.youtube_auth.src.quota_monitor import get_available_credential_sets

    configured = get_available_credential_sets()
    exhausted = getattr(get_authenticated_service, 'exhausted_sets', set())

    per_set = []
    for set_id in configured:
        if set_id == failing_set and failing_status:
            entry = oauth_health.build_set_entry(set_id, failing_status, failing_reason)
        elif set_id in exhausted:
            # exhausted_sets is ambiguous (quota OR auth failure); caller path
            # supplies classification for auth failures. Default to quota.
            entry = oauth_health.build_set_entry(set_id, oauth_health.STATUS_QUOTA_EXHAUSTED)
        else:
            entry = oauth_health.build_set_entry(set_id, oauth_health.STATUS_HEALTHY)
        per_set.append(entry)

    try:
        oauth_health.write_health_report(per_set)
    except Exception as write_e:
        logger.warning(f"[OAUTH-HEALTH] Failed to persist health report: {write_e}")


def get_authenticated_service(token_index=None):
    """
    Authenticates the user using OAuth 2.0 and returns a YouTube API service object.
    Handles token loading, refreshing, and the initial authorization flow.
    Implements multi-client OAuth fallback for quota management with auto-rotation.
    
    Args:
        token_index: Optional specific token index to use (0-3). If None, tries all.
    """
    scopes_str = os.getenv('YOUTUBE_SCOPES', '').strip()
    
    if not scopes_str:
        logger.error("YouTube scopes not defined in .env file.")
        raise ValueError("YOUTUBE_SCOPES must be defined in .env")
        
    scopes = scopes_str.split()
    
    if not scopes:
        logger.error("YouTube scopes is empty in .env file.")
        raise ValueError("YOUTUBE_SCOPES must be defined in .env")

    # Track quota-exhausted sets persistently
    if not hasattr(get_authenticated_service, 'exhausted_sets'):
        get_authenticated_service.exhausted_sets = set()
    if not hasattr(get_authenticated_service, 'last_reset'):
        import time
        get_authenticated_service.last_reset = time.time()
    
    # Reset exhausted sets daily (quotas reset at midnight PT)
    import time
    current_time = time.time()
    if current_time - get_authenticated_service.last_reset > 86400:  # 24 hours
        logger.info("[REFRESH] Daily reset: Clearing exhausted credential sets")
        get_authenticated_service.exhausted_sets.clear()
        get_authenticated_service.last_reset = current_time

    # Determine which credential sets to try
    if token_index is not None:
        # Use specific token index (already 1-based from caller)
        indices_to_try = [token_index]
        logger.info(f"[TARGET] Using specific credential set {token_index}")
    else:
        # Auto-rotation: Only use available credential sets (dynamic detection)
        from modules.platform_integration.youtube_auth.src.quota_monitor import get_available_credential_sets
        all_sets = get_available_credential_sets()  # Only configured sets (1, 10)
        available_sets = [s for s in all_sets if s not in get_authenticated_service.exhausted_sets]
        
        if not available_sets:
            # All exhausted - try all again (quotas might have reset)
            logger.warning("[U+26A0]️ All credential sets exhausted, retrying all...")
            get_authenticated_service.exhausted_sets.clear()
            available_sets = all_sets
        
        indices_to_try = available_sets
        logger.info(f"[REFRESH] Auto-rotating through sets: {indices_to_try} (Exhausted: {get_authenticated_service.exhausted_sets})")

        # WSP 97: emit truthful effective-capacity log so operators see that
        # exhausted / dead sets reduce real quota, not just rotation targets.
        capacity_snapshot = oauth_health.compute_effective_capacity([
            oauth_health.build_set_entry(
                s,
                oauth_health.STATUS_QUOTA_EXHAUSTED
                if s in get_authenticated_service.exhausted_sets
                else oauth_health.STATUS_HEALTHY,
            )
            for s in all_sets
        ])
        logger.info(f"[OAUTH-HEALTH] {oauth_health.format_capacity_log(capacity_snapshot)}")
    
    for index in indices_to_try:
        logger.info(f"[U+1F511] Attempting authentication with credential set {index}")
        creds_data = get_credentials_for_index(index)
        if not creds_data:
            # This should not happen with dynamic detection, but log it as debug instead of warning
            logger.debug(f"[SEARCH] Credential set {index} not configured or files missing")
            continue
            
        client_secrets_file, token_file = creds_data
        creds = None

        # Try to load existing credentials
        if os.path.exists(token_file):
            try:
                creds = google.oauth2.credentials.Credentials.from_authorized_user_file(token_file, scopes)
                logger.info(f"Loaded credentials from {token_file}")
            except Exception as e:
                logger.error(f"Failed to load credentials from {token_file}: {e}")
                # If loading fails, skip to the next credential set
                continue

        # Proactive token refresh - refresh if expiring within 10 minutes
        if creds and creds.valid and creds.expiry:
            from datetime import datetime, timedelta, timezone
            # Handle both timezone-aware and naive datetimes
            if creds.expiry.tzinfo is None:
                # If expiry is naive, assume UTC (compare UTC to UTC, not UTC to local time)
                time_until_expiry = creds.expiry - datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                # If expiry is aware, use aware comparison
                time_until_expiry = creds.expiry - datetime.now(timezone.utc)
            if time_until_expiry < timedelta(minutes=10):
                logger.info(f"[REFRESH] Token expiring in {int(time_until_expiry.total_seconds() // 60)} minutes for set {index}, proactively refreshing...")
                try:
                    creds.refresh(Request())
                    logger.info(f"[OK] Proactive refresh successful for set {index} (new expiry: {creds.expiry})")
                    # Save the refreshed credentials
                    try:
                        with open(token_file, 'w', encoding="utf-8") as token:
                            token.write(creds.to_json())
                        logger.info(f"[U+1F4BE] Refreshed credentials saved for set {index}")
                    except Exception as save_e:
                        logger.warning(f"[U+26A0]️ Could not save refreshed credentials: {save_e}")
                except Exception as refresh_e:
                    logger.warning(f"[U+26A0]️ Proactive refresh failed for set {index}: {refresh_e}")
                    # Mark as invalid to trigger normal refresh flow
                    creds = None

        # Handle credential refresh or new authentication
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info(f"[REFRESH] Credentials expired for set {index}, attempting refresh...")
                try:
                    creds.refresh(Request())
                    logger.info(f"[OK] Credentials refreshed successfully for set {index}")
                    # Log the new expiration time
                    if creds.expiry:
                        logger.info(f"[U+1F4C5] New token expires at: {creds.expiry} (valid for ~1 hour)")
                except Exception as e:
                    error_msg = str(e)
                    status, reason = oauth_health.classify_refresh_error(error_msg)
                    if 'invalid_grant' in error_msg:
                        # CRITICAL log with exact reauth command per WSP 97
                        oauth_health.emit_critical_reauth(index, status, reason)
                        # Mark this set offline for this process to avoid repeated retries during fallback flows
                        get_authenticated_service.exhausted_sets.add(index)
                    else:
                        logger.error(f"[FAIL] Failed to refresh token for set {index}: {e}")

                    # Persist operator-visible health artifact for this failure
                    _persist_health_snapshot(failing_set=index, failing_status=status, failing_reason=reason)

                    # Continue to next credential set instead of trying OAuth flow
                    continue
            else:
                if creds and creds.expired and not creds.refresh_token:
                    logger.warning(f"[U+26A0]️ Credentials expired for set {index} but no refresh token available")
                    logger.info(f"ℹ️ To fix: Run 'python modules/platform_integration/youtube_auth/scripts/authorize_set{index}.py'")
                else:
                    logger.info(f"🆕 No valid credentials found for set {index}, initiating OAuth flow...")

                try:
                    import webbrowser
                    import subprocess
                    from modules.platform_integration.youtube_auth.src.oauth_browser import (
                        resolve_browser_for_set,
                        BrowserNotFoundError,
                    )

                    # Browser selection based on credential set (WSP 84: single
                    # source of truth in oauth_browser.resolve_browser_for_set).
                    # Set 1 = UnDaoDu/Move2Japan = Chrome
                    # Set 10 = FoundUps/antifaFM = Edge
                    try:
                        browser_name, browser_path = resolve_browser_for_set(index)
                    except BrowserNotFoundError as browser_err:
                        logger.critical(
                            f"[BROWSER] Cannot launch OAuth for set {index}: "
                            f"{browser_err}. Operator action: {browser_err.operator_action}"
                        )
                        raise

                    logger.info(f"[BROWSER] Set {index} will use {browser_name.upper()} for OAuth")
                    print(f"\n[IMPORTANT] Opening {browser_name.upper()} for Set {index} authentication")
                    print(f"  - Set 1: Chrome (UnDaoDu/Move2Japan account)")
                    print(f"  - Set 10: Edge (FoundUps/antifaFM account)\n")

                    # Verify the resolved executable before launching. The
                    # resolver already checked existence, but re-verify here so
                    # a removed binary surfaces a CRITICAL operator action
                    # rather than an opaque Popen failure.
                    if not os.path.exists(browser_path):
                        action = oauth_health.reauth_command_for(index)
                        logger.critical(
                            f"[BROWSER] Resolved browser for set {index} no longer "
                            f"exists at {browser_path}. Operator action: {action}"
                        )
                        raise BrowserNotFoundError(
                            set_id=index,
                            attempted_paths=[browser_path],
                            operator_action=action,
                        )

                    # Override webbrowser.open to use the correct browser
                    original_open = webbrowser.open
                    def custom_open(url, new=0, autoraise=True):
                        subprocess.Popen([browser_path, url])
                        return True
                    webbrowser.open = custom_open

                    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                        client_secrets_file, scopes)
                    creds = flow.run_local_server(port=0)

                    # Restore original webbrowser.open
                    webbrowser.open = original_open

                    logger.info(f"[OK] OAuth flow completed successfully for set {index}")
                    if creds.expiry:
                        logger.info(f"[U+1F4C5] Token expires at: {creds.expiry}")
                except Exception as e:
                    logger.error(f"[FAIL] OAuth flow failed for set {index}: {e}")
                    # Restore original webbrowser.open on error
                    try:
                        webbrowser.open = original_open
                    except:
                        pass
                    continue

            # Save the credentials with improved error handling
            if creds:
                try:
                    os.makedirs(os.path.dirname(token_file), exist_ok=True)
                    with open(token_file, 'w', encoding="utf-8") as token:
                        token.write(creds.to_json())
                    logger.info(f"[U+1F4BE] Credentials saved to {token_file}")
                except Exception as e:
                    logger.error(f"[FAIL] Failed to save credentials to {token_file}: {e}")
                    # Don't continue here - we can still use the credentials even if saving fails
                    logger.warning(f"[U+26A0]️ Proceeding with unsaved credentials for set {index}")

        if not creds:
            logger.error(f"[FAIL] Failed to obtain credentials for set {index}")
            continue

        try:
            # Try to build service with current credentials
            # Disable discovery caching to avoid noisy `googleapiclient.discovery_cache` logs on Windows
            # (file_cache requires oauth2client<4.0.0).
            youtube_service = build('youtube', 'v3', credentials=creds, cache_discovery=False)
            logger.info(f"[CELEBRATE] YouTube API service built successfully with credential set {index}")
            
            # Test the service with a lightweight call to ensure it's working
            try:
                test_response = youtube_service.channels().list(part='snippet', mine=True).execute()
                # Track the quota usage for this test call
                quota_monitor.track_api_call(index, 'channels.list')
                
                if test_response.get('items'):
                    logger.info(f"[OK] Service validation successful for set {index}")
                    # Store the active set for tracking
                    youtube_service._credential_set = index
                    return youtube_service
                else:
                    logger.warning(f"[U+26A0]️ Service built but no channel data returned for set {index}")
                    continue
            except Exception as test_e:
                if 'quotaExceeded' in str(test_e):
                    logger.warning(f"[DATA] Validation failed due to quota for set {index}, marking as exhausted...")
                    get_authenticated_service.exhausted_sets.add(index)
                    continue  # Try next set
                else:
                    # Log full error details for debugging
                    error_msg = str(test_e)
                    if error_msg == str(index):
                        # This is the weird case where just the number is returned
                        logger.warning(f"[U+26A0]️ Service built but validation returned credential set number {index} as error")
                    else:
                        logger.warning(f"[U+26A0]️ Service built but validation failed for set {index}: {test_e}")
                    # Continue to next credential set instead of returning
                    continue
                
        except HttpError as e:
            if 'quotaExceeded' in str(e) or 'quota' in str(e).lower():
                logger.warning(f"[DATA] Quota exceeded for credential set {index}, marking as exhausted...")
                get_authenticated_service.exhausted_sets.add(index)
                continue
            else:
                logger.error(f"[FAIL] HTTP error building YouTube service with set {index}: {e}")
                continue
        except Exception as e:
            logger.error(f"[FAIL] Failed to build YouTube service with set {index}: {e}")
            continue

    # If we get here, all credential sets failed
    error_msg = f"[U+1F4A5] All credential sets failed to authenticate (tried {len(indices_to_try)} sets)"
    logger.critical(error_msg)
    logger.critical("[U+1F513] FALLING BACK TO NO-AUTH MODE - Read-only YouTube operations")

    # Return a no-auth YouTube service for read-only operations
    # This allows checking if streams are live without consuming quota
    try:
        youtube_service = build(
            'youtube',
            'v3',
            developerKey=os.getenv('YOUTUBE_API_KEY', None),
            cache_discovery=False,
        )
        if youtube_service:
            # WSP 97: No false success claims - this is a FALLBACK, not a success
            logger.warning("[FALLBACK] No-auth YouTube service created - Limited to public read-only operations (OAuth FAILED)")
            return youtube_service
    except Exception as e:
        logger.error(f"[FAIL] Failed to create no-auth service: {e}")

    # Only raise if we can't even create a no-auth service
    raise Exception("Could not authenticate with any Google credential set and no API key available.")

# YouTube Comment API Extensions (Per WSP 84 - Enhance existing module)
def list_video_comments(youtube_service, video_id: str, max_results: int = 100):
    """
    List all comment threads for a video.
    Cost: 1 unit per call (returns up to 100 comments)
    """
    try:
        request = youtube_service.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=max_results,
            order="relevance"  # or "time" for newest first
        )
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        logger.error(f"Error fetching comments for video {video_id}: {e}")
        return []

def like_comment(youtube_service, comment_id: str):
    """
    Like a YouTube comment.
    Note: YouTube API doesn't have a direct 'like comment' endpoint.
    We can only rate comments as 'none' or 'spam'.
    For liking, we need to use the video rating system.
    """
    logger.warning("YouTube API doesn't support liking individual comments directly")
    return False

def reply_to_comment(youtube_service, parent_id: str, text: str):
    """
    Reply to a YouTube comment.
    Cost: 50 units per call
    """
    try:
        request = youtube_service.comments().insert(
            part="snippet",
            body={
                "snippet": {
                    "parentId": parent_id,
                    "textOriginal": text
                }
            }
        )
        response = request.execute()
        logger.info(f"[OK] Posted reply to comment {parent_id}")
        return response
    except Exception as e:
        logger.error(f"[FAIL] Error replying to comment {parent_id}: {e}")
    return None


# Compatibility wrapper so legacy callers can import from this module.
# The canonical implementation lives in modules.platform_integration.utilities.oauth_management.
def get_authenticated_service_with_fallback(token_index=None):
    """
    Provide get_authenticated_service_with_fallback for callers that import it
    directly from youtube_auth. Delegates to the OAuth manager which performs
    rotation and returns (service, credentials, credential_set).
    """
    try:
        from modules.platform_integration.utilities.oauth_management.src.oauth_manager import (
            get_authenticated_service_with_fallback as _fallback,
        )
        return _fallback()
    except Exception as e:
        logger.error(f"[ERROR] Fallback authentication failed: {e}")
        return None

def get_latest_video_id(youtube_service, channel_id: str):
    """
    Get the latest video ID from a channel.
    Cost: 1 unit
    """
    try:
        request = youtube_service.search().list(
            part="id",
            channelId=channel_id,
            maxResults=1,
            order="date",
            type="video"
        )
        response = request.execute()
        items = response.get('items', [])
        if items:
            return items[0]['id']['videoId']
        return None
    except Exception as e:
        logger.error(f"Error fetching latest video: {e}")
        return None

# Example usage (for testing purposes, typically called from main.py)
if __name__ == '__main__':
    from utils.logging_config import setup_logging
    setup_logging()
    try:
        service = get_authenticated_service()
        # Test call (optional)
        response = service.channels().list(part='snippet', mine=True).execute()
        logger.info(f"Successfully authenticated as channel: {response['items'][0]['snippet']['title']}")
    except FileNotFoundError:
        logger.error("Setup error: Ensure GOOGLE_CLIENT_SECRETS_FILE points to a valid file.")
    except ValueError as ve:
        logger.error(f"Configuration error: {ve}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


def run_supervised_reauth_for_set(set_id, client_secrets, token_file, scopes) -> bool:
    """Run a supervised, fixed-port OAuth reauth for ONE credential set.

    This is the supervised counterpart to the authorize scripts. It is BLOCKING
    by design: run_local_server() blocks until the operator completes (or cancels)
    the consent in the browser. Callers MUST invoke this sequentially per set so
    Set 1's browser window resolves before Set 10's opens (012 sees Chrome then
    Edge, not just Edge).

    Behavior:
      - Resolves the correct browser per set via #811's
        oauth_browser.resolve_browser_for_set (Set 1 -> Chrome, Set 10 -> Edge).
      - Uses the FIXED listener port for the set (OAUTH_PORT_SET1=8080 /
        OAUTH_PORT_SET10=8090), NOT port=0, so the redirect_uri matches the
        client Google whitelisted.
      - Prints the account label from oauth_health.SET_METADATA so the operator
        knows which Google account to pick.
      - On success, persists the new token to token_file and returns True.
      - On any failure (browser-not-found, cancelled consent, save error), logs
        and returns False; the caller keeps the set in its expired list.

    Never logs/prints tokens or client_secret contents (WSP security).

    Args:
        set_id: credential set id (1 or 10).
        client_secrets: path to the client secrets JSON for this set.
        token_file: path to write the authorized-user token JSON.
        scopes: list of OAuth scopes.

    Returns:
        True if reauth completed and the token was obtained, else False.
    """
    # Function-local imports to avoid top-of-file collisions with concurrent
    # edits to get_authenticated_service (PR3) and to keep import-light.
    import webbrowser
    import subprocess
    from modules.platform_integration.youtube_auth.src.oauth_browser import (
        resolve_browser_for_set,
        BrowserNotFoundError,
    )

    meta = oauth_health.SET_METADATA.get(set_id, {})
    account_label = meta.get("account_label", f"Set {set_id}")
    port = _oauth_port_for_set(set_id)

    # Resolve which browser executable to launch for this set (single source of
    # truth in oauth_browser per #811). Failure here is a hard stop for the set.
    try:
        browser_name, browser_path = resolve_browser_for_set(set_id)
    except BrowserNotFoundError as browser_err:
        logger.critical(
            f"[REAUTH] Cannot launch OAuth for set {set_id} ({account_label}): "
            f"{browser_err}. Operator action: {browser_err.operator_action}"
        )
        return False

    # Re-verify the executable still exists (resolver checked, but a binary can
    # be removed between resolution and launch).
    if not os.path.exists(browser_path):
        action = oauth_health.reauth_command_for(set_id)
        logger.critical(
            f"[REAUTH] Resolved browser for set {set_id} no longer exists at "
            f"{browser_path}. Operator action: {action}"
        )
        return False

    # CodeQL-safe operator banner: log ONLY sanitized non-secret scalars - an
    # int set id, the resolver-derived browser name, an int port, and a STATIC
    # public channel-role literal (NOT read from any credential/oauth container,
    # so it cannot be tainted as sensitive). Never logs token/client_secret.
    _sid = int(set_id)
    _port_num = int(port)
    _browser = str(browser_name).upper()
    _role = {1: "UnDaoDu/Move2Japan", 10: "FoundUps/antifaFM"}.get(_sid, "channel")
    logger.info(
        "[REAUTH] credential set %s -> %s on port %s (%s)",
        _sid, _browser, _port_num, _role,
    )
    print(f"\n{'=' * 60}")
    print(f"[IMPORTANT] credential set {_sid} reauth: open {_browser} ({_role})")
    print(f"  - Set 1: Chrome (UnDaoDu/Move2Japan account)")
    print(f"  - Set 10: Edge (FoundUps/antifaFM account)")
    print(f"  - Listener port: {_port_num} (fixed, matches authorize_set{_sid}.py)")
    print(f"{'=' * 60}\n")

    original_open = webbrowser.open
    try:
        # Route the consent URL through the per-set browser executable.
        def custom_open(url, new=0, autoraise=True):
            subprocess.Popen([browser_path, url])
            return True

        webbrowser.open = custom_open

        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets, scopes
        )
        # BLOCKING: fixed port (not port=0) so redirect_uri matches the client.
        creds = flow.run_local_server(port=port)
    except Exception as auth_e:
        logger.error(f"[REAUTH] Set {set_id} ({account_label}) reauth failed: {auth_e}")
        return False
    finally:
        webbrowser.open = original_open

    if not creds:
        logger.error(f"[REAUTH] Set {set_id} ({account_label}) returned no credentials")
        return False

    try:
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())
        logger.info(f"[REAUTH] Set {set_id} ({account_label}) re-authenticated successfully")
    except Exception as save_e:
        logger.error(f"[REAUTH] Set {set_id} reauth succeeded but token save failed: {save_e}")
        return False

    return True


def preflight_oauth_check(auto_reauth: bool = False, credential_sets=None) -> dict:
    """
    Preflight check for OAuth token health. Call at startup to detect invalid_grant errors.

    Args:
        auto_reauth: If True, automatically launch re-auth flow for failed tokens
        credential_sets: Optional specific credential set indices to check.

    Returns:
        dict with keys:
            - healthy: List of working credential set indices
            - expired: List of credential sets with invalid_grant errors
            - missing: List of credential sets with missing files
            - reauth_needed: True if any tokens need re-authentication
    """
    from modules.platform_integration.youtube_auth.src.quota_monitor import get_available_credential_sets

    result = {
        'healthy': [],
        'expired': [],
        'missing': [],
        'reauth_needed': False
    }
    # Classified per-set entries for the health report (WSP 97)
    per_set_classified = {}

    scopes_str = os.getenv('YOUTUBE_SCOPES', '').strip()
    if not scopes_str:
        logger.error("[PREFLIGHT] YOUTUBE_SCOPES not defined")
        return result
    scopes = scopes_str.split()

    raw_sets = credential_sets if credential_sets is not None else get_available_credential_sets()
    # Process in ascending set order so supervised reauth opens Set 1 (Chrome /
    # UnDaoDu) BEFORE Set 10 (Edge / FoundUps). run_local_server blocks, so a
    # stable order guarantees 012 sees Chrome first, then Edge.
    all_sets = sorted(raw_sets)
    logger.info(f"[PREFLIGHT] Checking {len(all_sets)} credential sets (sorted): {all_sets}")

    for index in all_sets:
        creds_data = get_credentials_for_index(index)
        if not creds_data:
            result['missing'].append(index)
            per_set_classified[index] = oauth_health.build_set_entry(
                index, oauth_health.STATUS_UNCONFIGURED,
                "Client secrets or token file path not configured in .env"
            )
            continue

        client_secrets_file, token_file = creds_data

        if not os.path.exists(token_file):
            logger.warning(f"[PREFLIGHT] Token file missing for set {index}")
            result['missing'].append(index)
            per_set_classified[index] = oauth_health.build_set_entry(
                index, oauth_health.STATUS_UNCONFIGURED,
                f"Token file missing at {token_file}"
            )
            continue

        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(token_file, scopes)

            # Try to refresh if expired
            if creds.expired and creds.refresh_token:
                logger.info(f"[PREFLIGHT] Attempting refresh for set {index}...")
                creds.refresh(Request())

                # Save refreshed token
                with open(token_file, 'w', encoding='utf-8') as f:
                    f.write(creds.to_json())
                logger.info(f"[PREFLIGHT] Set {index} refreshed successfully")
                result['healthy'].append(index)
                per_set_classified[index] = oauth_health.build_set_entry(
                    index, oauth_health.STATUS_HEALTHY
                )

            elif creds.valid:
                logger.info(f"[PREFLIGHT] Set {index} is valid")
                result['healthy'].append(index)
                per_set_classified[index] = oauth_health.build_set_entry(
                    index, oauth_health.STATUS_HEALTHY
                )
            else:
                logger.warning(f"[PREFLIGHT] Set {index} invalid (no refresh token)")
                result['expired'].append(index)
                per_set_classified[index] = oauth_health.build_set_entry(
                    index, oauth_health.STATUS_NO_REFRESH_TOKEN,
                    "Credential loaded but has no refresh_token"
                )

        except Exception as e:
            error_msg = str(e)
            if 'invalid_grant' in error_msg:
                status, reason = oauth_health.classify_refresh_error(error_msg)
                oauth_health.emit_critical_reauth(index, status, reason)
                result['expired'].append(index)
                result['reauth_needed'] = True
                per_set_classified[index] = oauth_health.build_set_entry(
                    index, status, reason
                )

                if auto_reauth:
                    # Supervised, fixed-port, SEQUENTIAL reauth (WSP 84: single
                    # source of truth in run_supervised_reauth_for_set, which uses
                    # the per-set browser (#811 resolve_browser_for_set) and the
                    # FIXED port OAUTH_PORT_SET1/10 -- NOT port=0). run_local_server
                    # blocks, so Set 1 fully completes/cancels before Set 10 opens.
                    reauth_ok = run_supervised_reauth_for_set(
                        index, client_secrets_file, token_file, scopes
                    )
                    if reauth_ok:
                        result['expired'].remove(index)
                        result['healthy'].append(index)
                        result['reauth_needed'] = len(result['expired']) > 0
                        per_set_classified[index] = oauth_health.build_set_entry(
                            index, oauth_health.STATUS_HEALTHY
                        )
                    else:
                        # WSP 97: no false OK. Keep the set in expired[] and tell
                        # the operator exactly how to fix it.
                        logger.critical(
                            f"[PREFLIGHT] Set {index} reauth FAILED -- still dead. "
                            f"Operator action: {oauth_health.reauth_command_for(index)}"
                        )
            else:
                logger.error(f"[PREFLIGHT] Set {index} error: {error_msg}")
                result['expired'].append(index)
                per_set_classified[index] = oauth_health.build_set_entry(
                    index, oauth_health.STATUS_REFRESH_FAILED, error_msg[:200]
                )

    # Summary
    if result['healthy']:
        logger.info(f"[PREFLIGHT] Healthy sets: {result['healthy']}")
    if result['expired']:
        logger.warning(f"[PREFLIGHT] Expired/invalid sets: {result['expired']}")
        for idx in result['expired']:
            logger.warning(f"  -> Fix set {idx}: {oauth_health.reauth_command_for(idx)}")
    if result['missing']:
        logger.warning(f"[PREFLIGHT] Missing sets: {result['missing']}")

    # WSP 97: persist operator-visible health artifact + capacity log
    per_set_list = [per_set_classified[i] for i in sorted(per_set_classified)]
    try:
        oauth_health.write_health_report(per_set_list)
    except Exception as write_e:
        logger.warning(f"[OAUTH-HEALTH] Failed to persist health report: {write_e}")
    capacity = oauth_health.compute_effective_capacity(per_set_list)
    logger.info(f"[OAUTH-HEALTH] {oauth_health.format_capacity_log(capacity)}")

    return result
