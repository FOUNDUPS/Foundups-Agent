"""
Tests for the "no silent Set-10 fallback for a pinned credential set" behavior.

Slice: YT-OAUTH-INVALID-GRANT-NO-SILENT-FALLBACK-PHASE1 (builds on #811)

Verifies get_authenticated_service():
  - When a credential set is EXPLICITLY pinned (token_index=1) and its refresh
    raises invalid_grant, it raises OAuthReauthRequiredError and NEVER tries
    set 10 (no silent fallback to a different account / read-only mode).
  - When auto-rotating (token_index=None), a dead set 1 still falls back to a
    healthy set 10 (explicit fallback log).
  - When ALL sets are dead via invalid_grant during auto-rotation, it raises
    OAuthReauthRequiredError listing every reauth command.

No network: the refresh/flow paths are mocked. The credential .refresh() call
is what raises invalid_grant, mirroring a dead refresh token.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.platform_integration.youtube_auth.src.youtube_auth import (  # noqa: E402
    get_authenticated_service,
    OAuthReauthRequiredError,
)
from google.oauth2.credentials import Credentials  # noqa: E402


YOUTUBE_AUTH = "modules.platform_integration.youtube_auth.src.youtube_auth"
QUOTA_MONITOR = "modules.platform_integration.youtube_auth.src.quota_monitor"

REAUTH_SET1 = (
    "python modules/platform_integration/youtube_auth/scripts/authorize_set1.py"
)
REAUTH_SET10 = (
    "python modules/platform_integration/youtube_auth/scripts/authorize_set10.py"
)


def _make_expired_creds_raising(error_msg):
    """Build a creds mock that is expired/has refresh token and whose refresh()
    raises the given error message (simulates invalid_grant)."""
    creds = MagicMock(spec=Credentials)
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "fake-refresh-token"
    creds.expiry = None
    creds.refresh.side_effect = Exception(error_msg)
    return creds


def _make_valid_creds():
    """Build a creds mock representing a healthy, valid credential."""
    creds = MagicMock(spec=Credentials)
    creds.valid = True
    creds.expired = False
    creds.expiry = None
    return creds


class TestNoSilentFallback(unittest.TestCase):
    def setUp(self):
        # Required env for get_authenticated_service to proceed.
        self._orig_scopes = os.environ.get('YOUTUBE_SCOPES')
        os.environ['YOUTUBE_SCOPES'] = (
            'https://www.googleapis.com/auth/youtube.readonly'
        )
        # Reset per-process rotation memory so prior tests don't leak state.
        if hasattr(get_authenticated_service, 'exhausted_sets'):
            get_authenticated_service.exhausted_sets.clear()

    def tearDown(self):
        if self._orig_scopes is None:
            os.environ.pop('YOUTUBE_SCOPES', None)
        else:
            os.environ['YOUTUBE_SCOPES'] = self._orig_scopes
        if hasattr(get_authenticated_service, 'exhausted_sets'):
            get_authenticated_service.exhausted_sets.clear()

    # ------------------------------------------------------------------
    # 1. Pinned set 1 invalid_grant -> raises, never touches set 10.
    # ------------------------------------------------------------------
    @patch(f"{YOUTUBE_AUTH}._persist_health_snapshot")
    @patch(f"{YOUTUBE_AUTH}.build")
    @patch(f"{YOUTUBE_AUTH}.google.oauth2.credentials.Credentials.from_authorized_user_file")
    @patch(f"{YOUTUBE_AUTH}.os.path.exists")
    @patch(f"{YOUTUBE_AUTH}.get_credentials_for_index")
    def test_pinned_set1_invalid_grant_does_not_use_set10(
        self, mock_get_creds, mock_exists, mock_from_file, mock_build, mock_snap
    ):
        # get_credentials_for_index should only ever be called for set 1.
        def creds_for(index):
            return (f"secrets{index}.json", f"token{index}.json")
        mock_get_creds.side_effect = creds_for
        mock_exists.return_value = True

        # Set 1 refresh raises invalid_grant.
        mock_from_file.return_value = _make_expired_creds_raising(
            "('invalid_grant: Token has been expired or revoked.', {...})"
        )

        with self.assertRaises(OAuthReauthRequiredError) as ctx:
            get_authenticated_service(token_index=1)

        err = ctx.exception
        self.assertEqual(err.set_id, 1)
        self.assertEqual(err.operator_action, REAUTH_SET1)

        # Set 10 must NEVER be consulted for a pinned set.
        called_indices = [c.args[0] for c in mock_get_creds.call_args_list]
        self.assertIn(1, called_indices)
        self.assertNotIn(10, called_indices)
        # No service should have been built (no silent auth via any set).
        mock_build.assert_not_called()

    # ------------------------------------------------------------------
    # 2. Auto-rotation: set 1 dead, set 10 healthy -> falls back to set 10.
    # ------------------------------------------------------------------
    @patch(f"{YOUTUBE_AUTH}._persist_health_snapshot")
    @patch(f"{QUOTA_MONITOR}.get_available_credential_sets")
    @patch(f"{YOUTUBE_AUTH}.build")
    @patch(f"{YOUTUBE_AUTH}.google.oauth2.credentials.Credentials.from_authorized_user_file")
    @patch(f"{YOUTUBE_AUTH}.os.path.exists")
    @patch(f"{YOUTUBE_AUTH}.get_credentials_for_index")
    def test_auto_rotation_set1_dead_falls_back_to_set10_when_set10_healthy(
        self, mock_get_creds, mock_exists, mock_from_file,
        mock_build, mock_avail, mock_snap,
    ):
        mock_avail.return_value = [1, 10]

        def creds_for(index):
            return (f"secrets{index}.json", f"token{index}.json")
        mock_get_creds.side_effect = creds_for
        mock_exists.return_value = True

        dead_set1 = _make_expired_creds_raising(
            "('invalid_grant: Token has been expired or revoked.', {...})"
        )
        healthy_set10 = _make_valid_creds()

        def from_file(token_file, scopes):
            if token_file == "token1.json":
                return dead_set1
            return healthy_set10
        mock_from_file.side_effect = from_file

        # Service validation succeeds for set 10.
        mock_service = MagicMock()
        mock_service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"snippet": {"title": "FoundUps"}}]
        }
        mock_build.return_value = mock_service

        with self.assertLogs(f"{YOUTUBE_AUTH}", level="INFO") as logctx:
            service = get_authenticated_service()  # auto-rotation

        self.assertIs(service, mock_service)
        self.assertEqual(getattr(service, "_credential_set", None), 10)

        # Explicit fallback log to set 10.
        log_text = "\n".join(logctx.output)
        self.assertIn("falling back to remaining healthy set(s): [10]", log_text)
        # Capacity line emitted truthfully after the skip.
        self.assertIn("[OAUTH-HEALTH]", log_text)

    # ------------------------------------------------------------------
    # 3. Auto-rotation: ALL sets dead -> raises listing both reauth commands.
    # ------------------------------------------------------------------
    @patch(f"{YOUTUBE_AUTH}._persist_health_snapshot")
    @patch(f"{QUOTA_MONITOR}.get_available_credential_sets")
    @patch(f"{YOUTUBE_AUTH}.build")
    @patch(f"{YOUTUBE_AUTH}.google.oauth2.credentials.Credentials.from_authorized_user_file")
    @patch(f"{YOUTUBE_AUTH}.os.path.exists")
    @patch(f"{YOUTUBE_AUTH}.get_credentials_for_index")
    def test_all_sets_dead_raises_with_both_commands(
        self, mock_get_creds, mock_exists, mock_from_file,
        mock_build, mock_avail, mock_snap,
    ):
        mock_avail.return_value = [1, 10]

        def creds_for(index):
            return (f"secrets{index}.json", f"token{index}.json")
        mock_get_creds.side_effect = creds_for
        mock_exists.return_value = True

        # Both sets raise invalid_grant on refresh.
        def from_file(token_file, scopes):
            return _make_expired_creds_raising(
                "('invalid_grant: Token has been expired or revoked.', {...})"
            )
        mock_from_file.side_effect = from_file

        with self.assertRaises(OAuthReauthRequiredError) as ctx:
            get_authenticated_service()  # auto-rotation

        err = ctx.exception
        self.assertEqual(sorted(err.set_id), [1, 10])
        # Both reauth commands listed.
        self.assertIn(REAUTH_SET1, err.operator_action)
        self.assertIn(REAUTH_SET10, err.operator_action)
        # No silent degrade to no-auth service.
        mock_build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
