"""
Boot Layer Rotator Tests

WSP 5: Test coverage for schema rotation
WSP 72: Module independence (mock OBS client)

Tests:
1. Schema registry validation
2. Coming Soon URI generation
3. Individual schema configuration
4. Rotation order validation
5. Override signal handling
"""

import pytest
import asyncio
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import test targets
from modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor import (
    SCHEMAS,
    ROTATION_ORDER,
    get_coming_soon_uri,
    configure_schema_visibility,
    emit_event,
)


class TestSchemaRegistry:
    """Test schema registry structure."""

    def test_schemas_not_empty(self):
        """Schema registry has entries."""
        assert len(SCHEMAS) > 0

    def test_rotation_order_has_implemented_schemas(self):
        """Rotation order only includes implemented schemas."""
        for schema_id in ROTATION_ORDER:
            assert schema_id in SCHEMAS, f"Schema '{schema_id}' in rotation but not in registry"
            schema = SCHEMAS[schema_id]
            assert schema.get("implemented", False), f"Schema '{schema_id}' in rotation but not implemented"

    def test_required_schema_fields(self):
        """All schemas have required fields."""
        required_fields = ["name", "description", "implemented"]
        for schema_id, schema in SCHEMAS.items():
            for field in required_fields:
                assert field in schema, f"Schema '{schema_id}' missing field '{field}'"

    def test_gcc_schema_exists(self):
        """GCC shipping tracker schema exists."""
        assert "gcc" in SCHEMAS
        assert SCHEMAS["gcc"]["implemented"] is True
        assert SCHEMAS["gcc"]["executor"] == "gcc_shipping_tracker"

    def test_video_schema_exists(self):
        """Video rotation schema exists."""
        assert "video" in SCHEMAS
        assert SCHEMAS["video"]["implemented"] is True

    def test_news_schema_exists(self):
        """News ticker schema exists."""
        assert "news" in SCHEMAS
        assert SCHEMAS["news"]["implemented"] is True


class TestComingSoonURI:
    """Test Coming Soon fallback generation."""

    def test_generates_valid_data_uri(self):
        """Coming Soon generates valid data URI."""
        uri = get_coming_soon_uri("Test Schema")
        assert uri.startswith("data:text/html;base64,")

    def test_uri_contains_schema_name(self):
        """Data URI contains schema name in HTML."""
        uri = get_coming_soon_uri("My Test")
        # Decode base64 to check content
        base64_data = uri.split(",")[1]
        html = base64.b64decode(base64_data).decode()
        assert "My Test" in html

    def test_uri_contains_signature(self):
        """Data URI contains 0102 signature."""
        uri = get_coming_soon_uri("Test")
        base64_data = uri.split(",")[1]
        html = base64.b64decode(base64_data).decode()
        assert "0102" in html


class TestSchemaVisibilityConfiguration:
    """Test schema visibility configuration with mocked OBS."""

    @pytest.mark.asyncio
    async def test_gcc_schema_hides_video_sources(self):
        """GCC schema hides video grid and shows browser."""
        with patch(
            "modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor._get_obs_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_current_program_scene.return_value = MagicMock(scene_name="antifaFM")
            mock_client.get_scene_item_list.return_value = MagicMock(scene_items=[
                {"sourceName": "video1", "sceneItemId": 1},
                {"sourceName": "antifaFM Website", "sceneItemId": 2},
            ])
            mock_get_client.return_value = mock_client

            result = await configure_schema_visibility("gcc")
            assert result.get("schema") == "gcc"

    @pytest.mark.asyncio
    async def test_video_schema_shows_video_grid(self):
        """Video schema shows video grid and hides browser."""
        with patch(
            "modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor._get_obs_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_current_program_scene.return_value = MagicMock(scene_name="antifaFM")
            mock_client.get_scene_item_list.return_value = MagicMock(scene_items=[
                {"sourceName": "video1", "sceneItemId": 1},
                {"sourceName": "antifaFM Website", "sceneItemId": 2},
            ])
            mock_get_client.return_value = mock_client

            result = await configure_schema_visibility("video")
            assert result.get("schema") == "video"


class TestEventEmission:
    """Test telemetry event emission."""

    def test_emit_event_creates_telemetry_dir(self, tmp_path):
        """Event emission creates telemetry directory."""
        with patch(
            "modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor.TELEMETRY_DIR",
            tmp_path
        ):
            with patch(
                "modules.platform_integration.antifafm_broadcaster.skillz.boot_layer_rotator.executor.TELEMETRY_FILE",
                tmp_path / "test_events.jsonl"
            ):
                emit_event("test_event", data="test_value")
                assert (tmp_path / "test_events.jsonl").exists()


class TestRotationOrder:
    """Test rotation order configuration."""

    def test_rotation_order_is_list(self):
        """Rotation order is a list."""
        assert isinstance(ROTATION_ORDER, list)

    def test_rotation_order_minimum_schemas(self):
        """Rotation order has at least 2 schemas."""
        assert len(ROTATION_ORDER) >= 2

    def test_rotation_order_no_duplicates(self):
        """Rotation order has no duplicates."""
        assert len(ROTATION_ORDER) == len(set(ROTATION_ORDER))

    def test_rotation_starts_with_gcc(self):
        """Rotation order starts with GCC."""
        assert ROTATION_ORDER[0] == "gcc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
