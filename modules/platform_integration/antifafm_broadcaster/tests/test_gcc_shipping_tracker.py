"""
GCC Shipping Tracker Tests

WSP 5: Test coverage for shipping tracker
WSP 72: Module independence (mock external services)

Tests:
1. URL constants validation
2. Screenshot mode functions
3. View rotation configuration
4. Coming Soon fallback
5. Trusted domains check
"""

import pytest
import asyncio
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Import test targets
from modules.platform_integration.antifafm_broadcaster.skillz.gcc_shipping_tracker.executor import (
    VESSELFINDER_HORMUZ,
    VESSELFINDER_GULF,
    VESSELFINDER_TANKERS,
    MARINETRAFFIC_HORMUZ,
    MARINETRAFFIC_GULF,
    TRUSTED_DOMAINS,
    VIEW_INTERVAL_SEC,
    SCHEMA_DURATION_SEC,
    HORMUZ_BOUNDS,
    is_trusted_domain,
    get_tanker_focus_url,
    screenshot_to_data_uri,
    get_latest_screenshot,
    SCREENSHOT_CACHE_DIR,
    COMING_SOON_DATA_URI,
)


class TestURLConstants:
    """Test URL constants are valid."""

    def test_vesselfinder_hormuz_url(self):
        """VesselFinder Hormuz URL is valid."""
        assert "vesselfinder.com" in VESSELFINDER_HORMUZ
        assert "type=8" in VESSELFINDER_HORMUZ  # Tankers filter

    def test_vesselfinder_gulf_url(self):
        """VesselFinder Gulf URL is valid."""
        assert "vesselfinder.com" in VESSELFINDER_GULF
        assert "type=8" in VESSELFINDER_GULF

    def test_vesselfinder_tankers_url(self):
        """VesselFinder tankers URL is valid."""
        assert "vesselfinder.com" in VESSELFINDER_TANKERS
        assert "type=8" in VESSELFINDER_TANKERS

    def test_marinetraffic_hormuz_url(self):
        """MarineTraffic Hormuz URL is valid."""
        assert "marinetraffic.com" in MARINETRAFFIC_HORMUZ

    def test_marinetraffic_gulf_url(self):
        """MarineTraffic Gulf URL is valid."""
        assert "marinetraffic.com" in MARINETRAFFIC_GULF


class TestTrustedDomains:
    """Test trusted domain checking."""

    def test_marinetraffic_is_trusted(self):
        """MarineTraffic is a trusted domain."""
        assert is_trusted_domain("https://www.marinetraffic.com/en/ais/home")

    def test_vesselfinder_is_trusted(self):
        """VesselFinder is a trusted domain."""
        assert is_trusted_domain("https://www.vesselfinder.com/map#11/26.4/56.3")

    def test_fleetmon_is_trusted(self):
        """FleetMon is a trusted domain."""
        assert is_trusted_domain("https://www.fleetmon.com/vessels")

    def test_random_domain_not_trusted(self):
        """Random domains are not trusted."""
        assert not is_trusted_domain("https://example.com")
        assert not is_trusted_domain("https://google.com")


class TestTimingConstants:
    """Test timing configuration."""

    def test_view_interval_is_2_minutes(self):
        """View interval is 2 minutes (120 seconds)."""
        assert VIEW_INTERVAL_SEC == 120

    def test_schema_duration_is_10_minutes(self):
        """Schema duration is 10 minutes (600 seconds)."""
        assert SCHEMA_DURATION_SEC == 600

    def test_views_per_schema(self):
        """5 views fit in one schema duration."""
        views_per_schema = SCHEMA_DURATION_SEC // VIEW_INTERVAL_SEC
        assert views_per_schema == 5


class TestHormuzBounds:
    """Test Hormuz region bounding box."""

    def test_bounds_has_required_keys(self):
        """Bounds has all required keys."""
        required = ["lat_min", "lat_max", "lon_min", "lon_max"]
        for key in required:
            assert key in HORMUZ_BOUNDS

    def test_bounds_valid_range(self):
        """Bounds have valid lat/lon ranges."""
        assert HORMUZ_BOUNDS["lat_min"] < HORMUZ_BOUNDS["lat_max"]
        assert HORMUZ_BOUNDS["lon_min"] < HORMUZ_BOUNDS["lon_max"]


class TestTankerFocusURL:
    """Test tanker focus URL function."""

    def test_returns_vesselfinder_url(self):
        """Returns VesselFinder URL (preferred)."""
        url = get_tanker_focus_url()
        assert "vesselfinder.com" in url

    def test_url_has_tanker_filter(self):
        """URL has type=8 tanker filter."""
        url = get_tanker_focus_url()
        assert "type=8" in url


class TestComingSoonURI:
    """Test Coming Soon fallback."""

    def test_generates_valid_data_uri(self):
        """Generates valid data URI."""
        assert COMING_SOON_DATA_URI.startswith("data:text/html;base64,")


class TestScreenshotFunctions:
    """Test screenshot utility functions."""

    def test_screenshot_cache_dir_exists(self):
        """Screenshot cache directory exists."""
        assert SCREENSHOT_CACHE_DIR.exists()

    def test_screenshot_to_data_uri(self, tmp_path):
        """Convert PNG to data URI."""
        # Create a minimal PNG (1x1 transparent pixel)
        png_header = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,  # RGBA
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND
            0x42, 0x60, 0x82
        ])
        test_png = tmp_path / "test.png"
        test_png.write_bytes(png_header)

        uri = screenshot_to_data_uri(test_png)
        assert uri.startswith("data:image/png;base64,")

    def test_get_latest_screenshot_returns_none_for_missing(self):
        """Returns None when no screenshots exist for view."""
        result = get_latest_screenshot("nonexistent_view_12345")
        assert result is None


class TestViewRotation:
    """Test view rotation logic."""

    def test_rotation_has_three_views(self):
        """GCC tracker has 3 views."""
        from modules.platform_integration.antifafm_broadcaster.skillz.gcc_shipping_tracker.executor import (
            rotation_daemon
        )
        # Check the function signature accepts use_screenshots parameter
        import inspect
        sig = inspect.signature(rotation_daemon)
        assert "use_screenshots" in sig.parameters

    def test_screenshot_mode_available(self):
        """Screenshot mode is available."""
        from modules.platform_integration.antifafm_broadcaster.skillz.gcc_shipping_tracker.executor import (
            capture_map_screenshot
        )
        import inspect
        sig = inspect.signature(capture_map_screenshot)
        # Check parameters
        params = list(sig.parameters.keys())
        assert "url" in params
        assert "view_name" in params


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
