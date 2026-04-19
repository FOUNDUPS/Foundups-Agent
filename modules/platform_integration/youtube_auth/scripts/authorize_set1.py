"""
Authorize OAuth credential set 1 for YouTube API
Run this directly: python authorize_set1.py
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

import os
import sys
import webbrowser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube API scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.readonly'
]


def _pick_chrome_browser() -> str:
    chrome_paths = [
        os.getenv("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in chrome_paths:
        if path and os.path.exists(path):
            webbrowser.register("chrome", None, webbrowser.BackgroundBrowser(path))
            return "chrome"
    return None


def main():
    """Authorize set 1"""

    client_secret_file = 'credentials/client_secret.json'
    token_file = 'credentials/oauth_token.json'

    print("\n" + "=" * 60)
    print("AUTHORIZING SET 1")
    print("=" * 60)
    print(f"Client Secret: {client_secret_file}")
    print(f"Token Output: {token_file}")

    # Check if client secret exists
    if not os.path.exists(client_secret_file):
        print(f"[FAIL] Client secret file not found: {client_secret_file}")
        return False

    print("\n[OK] Found client secret file")

    try:
        # Run the OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_file, SCOPES)

        browser_name = _pick_chrome_browser()
        port = int(os.getenv("OAUTH_PORT_SET1", "8080"))

        print("\n[U+1F310] Opening browser for authorization...")
        print(f"   Port: {port}")
        print(f"   Browser: {'Chrome' if browser_name else 'default'}")
        print("\nIMPORTANT: Use the UnDaoDu Google account (NOT FoundUps)")
        print("   Set 1 = UnDaoDu / Move2Japan channels")
        print("   Set 10 = FoundUps / antifaFM channels (use Edge for Set 10)")

        # Run local server on port 8080 for Set 1
        credentials = flow.run_local_server(port=port, browser=browser_name)

        # Save the credentials
        with open(token_file, 'w', encoding="utf-8") as token:
            token.write(credentials.to_json())

        print("\n[OK] Successfully authorized Set 1!")
        print(f"[U+1F4BE] Token saved to: {token_file}")

        # Test the credentials
        print("\n[SEARCH] Testing credentials...")
        service = build('youtube', 'v3', credentials=credentials)
        request = service.channels().list(part='snippet', mine=True)
        response = request.execute()

        if 'items' in response and len(response['items']) > 0:
            channel_title = response['items'][0]['snippet']['title']
            print(f"[OK] Successfully connected to channel: {channel_title}")
            return True

        print("[WARN] Connected but no channel found. This is normal for some accounts.")
        return True

    except Exception as e:
        print(f"[FAIL] Failed to authorize: {e}")
        return False


if __name__ == '__main__':
    success = main()
    if success:
        print("\n[CELEBRATE] Set 1 authorization complete!")
    else:
        print("\n[U+1F4A5] Set 1 authorization failed!")
        sys.exit(1)
