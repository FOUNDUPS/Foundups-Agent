"""
No-network unit tests for OAuth credential health reporting (WSP 97).

Covers:
    - invalid_grant classifier maps error messages to the right status literals
    - preflight failure writes the health artifact with correct schema
    - operator_action contains the exact reauth command
    - effective_daily_quota_estimate reflects dead sets (not just exhausted)
    - rotation capacity log surfaces dead sets, not only quota-exhausted ones
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modules.platform_integration.youtube_auth.src import oauth_health


# -- classify_refresh_error ---------------------------------------------------

class TestClassifyRefreshError:
    def test_revoked_token_maps_to_token_revoked(self):
        msg = "('invalid_grant: Token has been expired or revoked.', ...)"
        status, reason = oauth_health.classify_refresh_error(msg)
        assert status == oauth_health.STATUS_TOKEN_REVOKED
        assert "revoked" in reason.lower()

    def test_expired_invalid_grant_maps_to_expired_or_revoked(self):
        # Google's actual response for a long-unused refresh token.
        msg = "invalid_grant: Token has been expired or refresh token missing"
        status, _ = oauth_health.classify_refresh_error(msg)
        assert status == oauth_health.STATUS_TOKEN_EXPIRED_OR_REVOKED

    def test_non_oauth_error_maps_to_refresh_failed(self):
        status, reason = oauth_health.classify_refresh_error("Connection reset by peer")
        assert status == oauth_health.STATUS_REFRESH_FAILED
        assert "Connection reset" in reason

    def test_empty_message_is_safe(self):
        status, _ = oauth_health.classify_refresh_error("")
        assert status == oauth_health.STATUS_REFRESH_FAILED


# -- build_set_entry + operator_action ---------------------------------------

class TestBuildSetEntry:
    def test_healthy_set_has_no_operator_action(self):
        entry = oauth_health.build_set_entry(1, oauth_health.STATUS_HEALTHY)
        assert entry["operator_action"] is None
        assert entry["status"] == oauth_health.STATUS_HEALTHY
        assert entry["account_label"] == "UnDaoDu / Move2Japan"
        assert entry["browser_hint"] == "Chrome"

    def test_dead_set_has_exact_reauth_command(self):
        entry = oauth_health.build_set_entry(
            1, oauth_health.STATUS_TOKEN_EXPIRED_OR_REVOKED, "Refresh token expired or revoked"
        )
        assert entry["operator_action"] == (
            "python modules/platform_integration/youtube_auth/scripts/authorize_set1.py"
        )

    def test_set_10_metadata(self):
        entry = oauth_health.build_set_entry(10, oauth_health.STATUS_HEALTHY)
        assert entry["account_label"] == "FoundUps / antifaFM"
        assert entry["browser_hint"] == "Edge"


# -- compute_effective_capacity ----------------------------------------------

class TestComputeEffectiveCapacity:
    def test_only_healthy_sets_count_toward_quota(self):
        entries = [
            oauth_health.build_set_entry(1, oauth_health.STATUS_TOKEN_EXPIRED_OR_REVOKED, "r"),
            oauth_health.build_set_entry(10, oauth_health.STATUS_HEALTHY),
        ]
        cap = oauth_health.compute_effective_capacity(entries)
        assert cap["total_configured"] == 2
        assert cap["operational"] == [10]
        assert cap["dead"] == [1]
        assert cap["effective_daily_quota_estimate"] == oauth_health.DAILY_QUOTA_PER_SET

    def test_quota_exhausted_is_not_dead(self):
        entries = [
            oauth_health.build_set_entry(1, oauth_health.STATUS_HEALTHY),
            oauth_health.build_set_entry(10, oauth_health.STATUS_QUOTA_EXHAUSTED),
        ]
        cap = oauth_health.compute_effective_capacity(entries)
        assert cap["dead"] == []
        assert cap["quota_exhausted_today"] == [10]
        # Healthy=1 means 1 set's worth of daily quota is currently operational.
        assert cap["effective_daily_quota_estimate"] == oauth_health.DAILY_QUOTA_PER_SET

    def test_all_dead_means_zero_quota(self):
        entries = [
            oauth_health.build_set_entry(1, oauth_health.STATUS_TOKEN_REVOKED, "r"),
            oauth_health.build_set_entry(10, oauth_health.STATUS_UNCONFIGURED, "m"),
        ]
        cap = oauth_health.compute_effective_capacity(entries)
        assert cap["operational"] == []
        assert cap["effective_daily_quota_estimate"] == 0


# -- format_capacity_log ------------------------------------------------------

class TestFormatCapacityLog:
    def test_dead_sets_surface_action_required(self):
        entries = [
            oauth_health.build_set_entry(1, oauth_health.STATUS_TOKEN_EXPIRED_OR_REVOKED, "r"),
            oauth_health.build_set_entry(10, oauth_health.STATUS_HEALTHY),
        ]
        cap = oauth_health.compute_effective_capacity(entries)
        msg = oauth_health.format_capacity_log(cap)

        assert "1/2 sets operational" in msg
        assert "dead=[1]" in msg
        assert "action_required=" in msg
        assert "authorize_set1.py" in msg

    def test_quota_exhausted_only_does_not_claim_action_required(self):
        # Stream resolver's current log says "Set X exhausted" even if the
        # real problem is auth. This asserts that when ONLY quota is the
        # issue (no dead sets), we do NOT falsely ask for reauthorization.
        entries = [
            oauth_health.build_set_entry(1, oauth_health.STATUS_HEALTHY),
            oauth_health.build_set_entry(10, oauth_health.STATUS_QUOTA_EXHAUSTED),
        ]
        cap = oauth_health.compute_effective_capacity(entries)
        msg = oauth_health.format_capacity_log(cap)
        assert "action_required" not in msg
        assert "quota_exhausted_today=[10]" in msg


# -- write_health_report ------------------------------------------------------

class TestWriteHealthReport:
    def test_schema_fields_and_roundtrip(self, tmp_path: Path):
        entries = [
            oauth_health.build_set_entry(1, oauth_health.STATUS_TOKEN_EXPIRED_OR_REVOKED, "r"),
            oauth_health.build_set_entry(10, oauth_health.STATUS_HEALTHY),
        ]
        out = tmp_path / "reports" / "oauth_credential_health.json"
        path = oauth_health.write_health_report(entries, output_path=out)

        assert path == out
        report = json.loads(out.read_text(encoding="utf-8"))
        assert "generated_at" in report
        assert set(report["credential_sets"].keys()) == {
            "total_configured", "operational", "dead",
            "quota_exhausted_today", "effective_daily_quota_estimate",
        }
        assert report["credential_sets"]["dead"] == [1]
        assert report["credential_sets"]["effective_daily_quota_estimate"] == (
            oauth_health.DAILY_QUOTA_PER_SET
        )

        set_1 = next(e for e in report["per_set"] if e["set_id"] == 1)
        assert set_1["operator_action"].endswith("authorize_set1.py")
        assert set_1["reason"] is not None


# -- emit_critical_reauth emits CRITICAL with exact command -------------------

class TestEmitCriticalReauth:
    def test_critical_log_contains_exact_command(self, caplog):
        caplog.set_level(logging.CRITICAL, logger="modules.platform_integration.youtube_auth.src.oauth_health")
        oauth_health.emit_critical_reauth(
            1, oauth_health.STATUS_TOKEN_EXPIRED_OR_REVOKED, "Refresh token expired or revoked"
        )
        messages = [r.getMessage() for r in caplog.records if r.levelno == logging.CRITICAL]
        assert any("authorize_set1.py" in m for m in messages)
        assert any("CRITICAL" in m for m in messages)


# -- preflight_oauth_check end-to-end (no network) ----------------------------

class TestPreflightWritesArtifact:
    """
    Simulates the exact condition described in the Worker YT1 brief:
    Set 1 refresh_token expired, Set 10 still healthy. The artifact must
    report dead=[1], operational=[10], effective_quota=10,000, and the
    capacity log must not falsely claim "only quota exhaustion".
    """

    def _run_preflight_with_mocks(self, tmp_path, set1_behavior, set10_behavior):
        from modules.platform_integration.youtube_auth.src import youtube_auth as ya

        report_path = tmp_path / "oauth_credential_health.json"

        # Redirect the module's default report path so write_health_report()
        # runs unchanged but writes under tmp_path.
        default_path_patch = patch.object(
            oauth_health, "_DEFAULT_REPORT_PATH", report_path
        )

        with default_path_patch, \
             patch.object(ya, 'get_credentials_for_index') as mock_creds, \
             patch.object(ya.os.path, 'exists', return_value=True), \
             patch.object(ya.google.oauth2.credentials.Credentials, 'from_authorized_user_file') as mock_from_file, \
             patch.dict(ya.os.environ, {'YOUTUBE_SCOPES': 'https://www.googleapis.com/auth/youtube.readonly'}, clear=False):

            mock_creds.side_effect = lambda index: (
                f"/fake/secrets_{index}.json", f"/fake/token_for_set_{index}.json"
            )

            def make_creds(behavior):
                m = MagicMock()
                m.expired = behavior["expired"]
                m.refresh_token = behavior["refresh_token"]
                m.valid = behavior["valid"]
                if behavior.get("refresh_raises"):
                    m.refresh.side_effect = Exception(behavior["refresh_raises"])
                else:
                    m.refresh.return_value = None
                    m.to_json.return_value = "{}"
                return m

            def from_file(token_file, scopes):
                # Use exact suffix match — "token_1" would also match "token_10".
                if token_file.endswith("_set_1.json"):
                    return make_creds(set1_behavior)
                if token_file.endswith("_set_10.json"):
                    return make_creds(set10_behavior)
                raise AssertionError(f"unexpected token_file: {token_file}")

            mock_from_file.side_effect = from_file

            # Patch file write so refreshed token doesn't try to hit disk.
            # Don't patch builtins.open globally — oauth_health needs it to
            # write the report artifact.
            with patch.object(ya, "open", new_callable=MagicMock, create=True):
                result = ya.preflight_oauth_check(
                    auto_reauth=False, credential_sets=[1, 10]
                )

        return result, report_path

    def test_invalid_grant_on_set1_writes_truthful_artifact(self, tmp_path):
        set1 = {
            "expired": True, "refresh_token": "rt", "valid": False,
            "refresh_raises": "invalid_grant: Token has been expired or revoked.",
        }
        set10 = {"expired": False, "refresh_token": "rt", "valid": True}
        result, report_path = self._run_preflight_with_mocks(tmp_path, set1, set10)

        assert 1 in result['expired']
        assert 10 in result['healthy']
        assert result['reauth_needed'] is True

        assert report_path.exists(), "health artifact must be persisted"
        report = json.loads(report_path.read_text(encoding="utf-8"))

        assert report["credential_sets"]["dead"] == [1]
        assert report["credential_sets"]["operational"] == [10]
        assert report["credential_sets"]["effective_daily_quota_estimate"] == (
            oauth_health.DAILY_QUOTA_PER_SET
        )

        set_1 = next(e for e in report["per_set"] if e["set_id"] == 1)
        assert set_1["status"] == oauth_health.STATUS_TOKEN_REVOKED
        assert set_1["operator_action"].endswith("authorize_set1.py")

    def test_capacity_log_does_not_report_only_set10_exhaustion(self, tmp_path, caplog):
        """
        Regression guard for the WSP 97 gap in the brief: stream resolver /
        rotation logs were showing 'Set 10 exhausted' only, hiding that Set 1
        was actually dead from invalid_grant. The capacity log must surface
        dead=[1] as well.
        """
        set1 = {
            "expired": True, "refresh_token": "rt", "valid": False,
            "refresh_raises": "invalid_grant: Token has been expired or revoked.",
        }
        set10 = {"expired": False, "refresh_token": "rt", "valid": True}

        caplog.set_level(logging.INFO, logger="modules.platform_integration.youtube_auth.src.youtube_auth")
        self._run_preflight_with_mocks(tmp_path, set1, set10)

        capacity_msgs = [r.getMessage() for r in caplog.records if "OAUTH-HEALTH" in r.getMessage()]
        assert capacity_msgs, "capacity log line must be emitted"
        joined = " | ".join(capacity_msgs)
        assert "dead=[1]" in joined
        assert "1/2 sets operational" in joined


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
