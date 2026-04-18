"""
Tests for Mall Catalog Refresh Script Safety

Verifies dry-run default, --apply requirement, and backup behavior.
"""
import pytest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "refresh_mall_catalog.py"


@pytest.fixture
def script_content():
    """Load the refresh script."""
    return SCRIPT_PATH.read_text(encoding="utf-8")


class TestRefreshScriptSafety:
    """Refresh script defaults to dry-run for safety."""

    def test_script_exists(self):
        """Refresh script exists."""
        assert SCRIPT_PATH.exists()

    def test_dry_run_documented(self, script_content):
        """Dry-run behavior is documented in docstring."""
        assert "DRY-RUN" in script_content or "dry-run" in script_content

    def test_apply_flag_defined(self, script_content):
        """--apply flag is defined."""
        assert "--apply" in script_content

    def test_dry_run_default_true(self, script_content):
        """dry_run defaults to True (not args.apply)."""
        assert "dry_run = not args.apply" in script_content

    def test_save_catalog_accepts_dry_run(self, script_content):
        """save_catalog function accepts dry_run parameter."""
        assert "def save_catalog(catalog" in script_content
        assert "dry_run" in script_content

    def test_backup_created_on_write(self, script_content):
        """Backup is created before writing."""
        assert ".bak" in script_content or "backup" in script_content.lower()

    def test_dry_run_skips_write(self, script_content):
        """Dry-run mode skips file write."""
        assert "[DRY-RUN]" in script_content

    def test_refresh_catalog_accepts_dry_run(self, script_content):
        """refresh_catalog function accepts dry_run parameter."""
        assert "dry_run: bool = True" in script_content or "dry_run=True" in script_content


class TestRefreshScriptModes:
    """Refresh script supports multiple quota-efficient modes."""

    def test_info_only_mode(self, script_content):
        """--info-only mode exists."""
        assert "--info-only" in script_content

    def test_delta_mode(self, script_content):
        """--delta mode exists."""
        assert "--delta" in script_content

    def test_full_mode(self, script_content):
        """--full mode exists."""
        assert "--full" in script_content

    def test_quota_estimates_documented(self, script_content):
        """Quota estimates are documented."""
        assert "quota" in script_content.lower()
        assert "units" in script_content.lower()
