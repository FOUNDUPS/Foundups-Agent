"""
No-network unit tests for dual-set supervised OAuth preflight
(slice YT-OAUTH-DUAL-PREFLIGHT-MENU-PHASE1, stacks on #811 browser resolver).

Covers the acceptance contract:
    - both sets dead -> supervised reauth opens Set 1 (Chrome/UnDaoDu) BEFORE
      Set 10 (Edge/FoundUps); order asserted.
    - Set 1 reauth failure does NOT swallow / short-circuit -> Set 10 is still
      attempted, and Set 1 stays in expired[] (WSP 97: no false OK).
    - the menu 1->1 entry path (main.monitor_youtube) calls the dual-set
      preflight with credential_sets=[1, 10].
    - the new supervised path uses FIXED ports (8080 / 8090), NOT port=0.

All network + browser launch is mocked: InstalledAppFlow.run_local_server and
oauth_browser.resolve_browser_for_set are patched. No tokens are ever written
to disk (builtin open is mocked inside the module under test).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest

from modules.platform_integration.youtube_auth.src import youtube_auth as ya


# -- helpers ------------------------------------------------------------------

def _expired_invalid_grant_creds():
    """A creds mock whose refresh() raises invalid_grant (set is dead)."""
    m = MagicMock()
    m.expired = True
    m.refresh_token = "rt"
    m.valid = False
    m.refresh.side_effect = Exception("invalid_grant: Token has been expired or revoked.")
    return m


def _make_from_file(behaviors):
    """Map token_file suffix -> creds mock factory, exact-suffix matched."""
    def from_file(token_file, scopes):
        if token_file.endswith("_set_1.json"):
            return behaviors[1]()
        if token_file.endswith("_set_10.json"):
            return behaviors[10]()
        raise AssertionError(f"unexpected token_file: {token_file}")
    return from_file


def _run_preflight(behaviors, reauth_results, *, resolve_side_effect=None):
    """
    Run preflight_oauth_check(auto_reauth=True, credential_sets=[1, 10]) with all
    network/browser dependencies mocked.

    Args:
        behaviors: {set_id: creds-factory} for from_authorized_user_file.
        reauth_results: {set_id: bool} the supervised reauth outcome per set.
        resolve_side_effect: optional override for resolve_browser_for_set.

    Returns:
        (result_dict, run_local_server_mock, resolve_mock, supervised_calls_order)
    """
    supervised_calls_order = []

    def fake_run_local_server(port=0, **kwargs):
        # Capture the port so tests can assert fixed-port usage.
        fake_run_local_server.ports.append(port)
        # Determine which set this call is for via the resolve order tracker.
        set_id = fake_run_local_server.current_set[0]
        supervised_calls_order.append(set_id)
        if reauth_results.get(set_id, False):
            creds = MagicMock()
            creds.to_json.return_value = "{}"
            return creds
        raise Exception("operator cancelled consent")

    fake_run_local_server.ports = []
    fake_run_local_server.current_set = [None]

    def fake_resolve(set_id):
        # Track which set is being reauthed so fake_run_local_server knows.
        fake_run_local_server.current_set[0] = set_id
        if resolve_side_effect:
            return resolve_side_effect(set_id)
        return ("chrome" if set_id == 1 else "edge", f"/fake/browser_{set_id}.exe")

    resolve_mock = MagicMock(side_effect=fake_resolve)

    flow_instance = MagicMock()
    flow_instance.run_local_server.side_effect = fake_run_local_server
    flow_cls = MagicMock()
    flow_cls.from_client_secrets_file.return_value = flow_instance

    with patch.object(ya, 'get_credentials_for_index') as mock_creds, \
         patch.object(ya.os.path, 'exists', return_value=True), \
         patch.object(ya.os, 'makedirs'), \
         patch.object(
             ya.google.oauth2.credentials.Credentials,
             'from_authorized_user_file',
         ) as mock_from_file, \
         patch(
             'modules.platform_integration.youtube_auth.src.oauth_browser.resolve_browser_for_set',
             resolve_mock,
         ), \
         patch.object(ya.google_auth_oauthlib.flow, 'InstalledAppFlow', flow_cls), \
         patch.dict(
             ya.os.environ,
             {'YOUTUBE_SCOPES': 'https://www.googleapis.com/auth/youtube.readonly'},
             clear=False,
         ), \
         patch.object(ya, 'open', new_callable=MagicMock, create=True), \
         patch.object(ya.oauth_health, 'write_health_report'):

        mock_creds.side_effect = lambda index: (
            f"/fake/secrets_{index}.json", f"/fake/token_for_set_{index}.json"
        )
        mock_from_file.side_effect = _make_from_file(behaviors)

        result = ya.preflight_oauth_check(auto_reauth=True, credential_sets=[1, 10])

    return result, fake_run_local_server, resolve_mock, supervised_calls_order


# -- both sets dead: order Set 1 then Set 10 ----------------------------------

class TestBothSetsDeadOpensSet1ThenSet10:
    def test_both_sets_dead_opens_set1_then_set10(self):
        behaviors = {
            1: _expired_invalid_grant_creds,
            10: _expired_invalid_grant_creds,
        }
        # Both reauths succeed.
        result, run_server, resolve_mock, order = _run_preflight(
            behaviors, {1: True, 10: True}
        )

        # ORDER: Set 1 reauthed before Set 10 (run_local_server blocks).
        assert order == [1, 10], f"expected Set 1 before Set 10, got {order}"

        # Browser resolver consulted for each set, in order.
        assert resolve_mock.call_args_list == [call(1), call(10)]

        # FIXED ports, NOT port=0.
        assert run_server.ports == [8080, 8090], run_server.ports

        # Both became healthy.
        assert sorted(result['healthy']) == [1, 10]
        assert result['expired'] == []


# -- Set 1 failure does not stop Set 10 ---------------------------------------

class TestSet1FailureSet10StillAttempted:
    def test_set1_reauth_failure_set10_still_attempted(self):
        behaviors = {
            1: _expired_invalid_grant_creds,
            10: _expired_invalid_grant_creds,
        }
        # Set 1 reauth FAILS (cancelled), Set 10 succeeds.
        result, run_server, resolve_mock, order = _run_preflight(
            behaviors, {1: False, 10: True}
        )

        # Set 10 MUST still be attempted after Set 1 fails (no swallow).
        assert order == [1, 10], f"Set 10 must run after Set 1 fails, got {order}"

        # Fixed ports still used for both attempts.
        assert run_server.ports == [8080, 8090]

        # WSP 97: Set 1 stays dead (in expired), Set 10 recovered.
        assert 1 in result['expired'], "Set 1 must remain expired after reauth failure"
        assert 10 in result['healthy']
        assert result['reauth_needed'] is True


# -- supervised function uses fixed ports directly ----------------------------

class TestSupervisedReauthFixedPort:
    def test_supervised_reauth_uses_fixed_port_set1(self):
        flow_instance = MagicMock()
        creds = MagicMock()
        creds.to_json.return_value = "{}"
        flow_instance.run_local_server.return_value = creds
        flow_cls = MagicMock()
        flow_cls.from_client_secrets_file.return_value = flow_instance

        with patch(
                'modules.platform_integration.youtube_auth.src.oauth_browser.resolve_browser_for_set',
                return_value=("chrome", "/fake/chrome.exe"),
             ), \
             patch.object(ya.os.path, 'exists', return_value=True), \
             patch.object(ya.os, 'makedirs'), \
             patch.object(ya.google_auth_oauthlib.flow, 'InstalledAppFlow', flow_cls), \
             patch.object(ya, 'open', new_callable=MagicMock, create=True):

            ok = ya.run_supervised_reauth_for_set(
                1, "/fake/secrets.json", "/fake/token.json", ["scope"]
            )

        assert ok is True
        flow_instance.run_local_server.assert_called_once_with(port=8080)

    def test_supervised_reauth_uses_fixed_port_set10(self):
        flow_instance = MagicMock()
        creds = MagicMock()
        creds.to_json.return_value = "{}"
        flow_instance.run_local_server.return_value = creds
        flow_cls = MagicMock()
        flow_cls.from_client_secrets_file.return_value = flow_instance

        with patch(
                'modules.platform_integration.youtube_auth.src.oauth_browser.resolve_browser_for_set',
                return_value=("edge", "/fake/edge.exe"),
             ), \
             patch.object(ya.os.path, 'exists', return_value=True), \
             patch.object(ya.os, 'makedirs'), \
             patch.object(ya.google_auth_oauthlib.flow, 'InstalledAppFlow', flow_cls), \
             patch.object(ya, 'open', new_callable=MagicMock, create=True):

            ok = ya.run_supervised_reauth_for_set(
                10, "/fake/secrets.json", "/fake/token.json", ["scope"]
            )

        assert ok is True
        flow_instance.run_local_server.assert_called_once_with(port=8090)

    def test_browser_not_found_returns_false_no_crash(self):
        from modules.platform_integration.youtube_auth.src.oauth_browser import (
            BrowserNotFoundError,
        )
        with patch(
                'modules.platform_integration.youtube_auth.src.oauth_browser.resolve_browser_for_set',
                side_effect=BrowserNotFoundError(
                    set_id=1, attempted_paths=["/x"], operator_action="run authorize_set1.py"
                ),
             ):
            ok = ya.run_supervised_reauth_for_set(
                1, "/fake/secrets.json", "/fake/token.json", ["scope"]
            )
        assert ok is False


# -- menu 1->1 path calls dual-set preflight ----------------------------------

class TestMenuPathCallsDualSetPreflight:
    @pytest.mark.asyncio
    async def test_menu_path_calls_dual_set_preflight(self):
        """
        Menu 1->1 launches main.monitor_youtube(), which is the single OAuth
        preflight entry point. Assert it calls preflight_oauth_check with
        credential_sets=[1, 10] (dual-set contract) before starting the monitor.
        """
        import os as _os
        from pathlib import Path as _Path

        # Importing main configures a FileHandler on logs/foundups_agent.log.
        # That dir is gitignored and may not exist in a fresh worktree; create
        # it so the import does not fail for an environment reason unrelated to
        # the contract under test.
        repo_root = _Path(__file__).resolve().parents[4]
        (repo_root / "logs").mkdir(parents=True, exist_ok=True)

        import main

        preflight_mock = MagicMock(return_value={
            'healthy': [1, 10], 'expired': [], 'missing': [], 'reauth_needed': False,
        })
        dae_instance = MagicMock()

        async def fake_run():
            return None

        dae_instance.run = fake_run
        dae_cls = MagicMock(return_value=dae_instance)

        # SECTION C quota log runs after preflight; give it a benign summary.
        quota_instance = MagicMock()
        quota_instance.get_usage_summary.return_value = {
            'sets': {
                1: {'used': 0, 'limit': 10000, 'available': 10000, 'status': 'HEALTHY'},
                10: {'used': 0, 'limit': 10000, 'available': 10000, 'status': 'HEALTHY'},
            }
        }
        quota_cls = MagicMock(return_value=quota_instance)

        with patch(
                'modules.platform_integration.youtube_auth.src.youtube_auth.preflight_oauth_check',
                preflight_mock,
             ), \
             patch(
                'modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE',
                dae_cls,
             ), \
             patch(
                'modules.platform_integration.youtube_auth.src.quota_monitor.QuotaMonitor',
                quota_cls,
             ):
            # disable_lock=True so we skip the instance-lock branch (no input()).
            await main.monitor_youtube(disable_lock=True, auto_reauth=True)

        preflight_mock.assert_called_once()
        _, kwargs = preflight_mock.call_args
        assert kwargs.get('credential_sets') == [1, 10], (
            f"menu/monitor path must pass credential_sets=[1, 10], got {kwargs}"
        )
        assert kwargs.get('auto_reauth') is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
