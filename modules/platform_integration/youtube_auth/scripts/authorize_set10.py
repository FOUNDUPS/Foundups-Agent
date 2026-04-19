"""
Authorize OAuth credential set 10 for YouTube API
Run this directly: python authorize_set10.py
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
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# YouTube API scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.readonly'
]


def _pick_edge_browser() -> str:
    edge_paths = [
        os.getenv("EDGE_PATH"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in edge_paths:
        if path and os.path.exists(path):
            webbrowser.register("edge", None, webbrowser.BackgroundBrowser(path))
            return "edge"
    return None


def main():
    """Authorize set 10"""
    parser = argparse.ArgumentParser(description="Authorize YouTube OAuth credential set 10")
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Do not auto-open a browser. Print a clean consent URL and wait for the callback.",
    )
    parser.add_argument(
        "--browser",
        choices=["edge", "default"],
        default="edge",
        help="Browser to use for auto-open mode. Ignored by --manual.",
    )
    args = parser.parse_args()

    client_secret_file = 'credentials/client_secret10.json'
    token_file = 'credentials/oauth_token10.json'

    print("\n" + "=" * 60)
    print("AUTHORIZING SET 10")
    print("=" * 60)
    print(f"Client Secret: {client_secret_file}")
    print(f"Token Output: {token_file}")

    # Check if client secret exists
    if not os.path.exists(client_secret_file):
        print("\n[FAIL] ERROR: Client secret not found!")
        print(f"   Expected location: {os.path.abspath(client_secret_file)}")
        print("\nPlease ensure client_secret10.json is in the credentials/ folder")
        return False

    print("\n[OK] Found client secret file")

    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)

        browser_name = _pick_edge_browser() if args.browser == "edge" else None
        port = int(os.getenv("OAUTH_PORT_SET10", "8090"))

        print("\n[U+1F310] Starting authorization flow...")
        print(f"   Port: {port}")
        if args.manual:
            print("   Mode: manual URL copy/paste")
            print("\nIMPORTANT:")
            print("   1. Open a clean browser window for the account you want on set 10")
            print("   2. Paste the printed URL into that window")
            print("   3. Complete consent and let Google redirect to localhost")
            print("   4. This avoids broken Google account delegation pages")
            auth_message = (
                "\n" + "=" * 60 + "\n"
                "COPY THIS URL INTO A CLEAN BROWSER WINDOW:\n{url}\n"
                + "=" * 60 + "\n"
            )
            creds = flow.run_local_server(
                port=port,
                open_browser=False,
                authorization_prompt_message=auth_message,
                success_message="Authorization complete. You may close this window.",
            )
        else:
            print(f"   Browser: {'Edge' if browser_name else 'default'}")
            print("\nIMPORTANT: Use the FoundUps Google account (NOT UnDaoDu)")
            print("   Set 10 = FoundUps / antifaFM channels")
            print("   Set 1 = UnDaoDu / Move2Japan channels (use Chrome for Set 1)")
            print("   If Google opens a 400 delegation page, rerun with --manual")
            creds = flow.run_local_server(
                port=port,
                browser=browser_name,
                success_message="Authorization complete. You may close this window.",
            )

        # Save the credentials
        with open(token_file, 'w', encoding="utf-8") as token:
            token.write(creds.to_json())

        print("\n[OK] Successfully authorized Set 10!")
        print(f"[U+1F4BE] Token saved to: {token_file}")

        # Test the credentials
        print("\n[SEARCH] Testing credentials...")
        service = build('youtube', 'v3', credentials=creds)
        response = service.channels().list(part='snippet', mine=True).execute()
        if response.get('items'):
            channel = response['items'][0]['snippet']['title']
            print(f"[OK] Authenticated as channel: {channel}")

        print("\n" + "=" * 60)
        print("SUCCESS! Set 10 is ready to use")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[FAIL] Failed to authorize: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
