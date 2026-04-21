"""
YTR3 - Human Behavior Anti-Detection Test Harness

Tests HumanBehavior class methods with mocked Selenium driver.
No live browser, no sleep delays, deterministic randomness.

WSP 97: Mocks external systems (Selenium, time, random), tests production code.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import os

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


# =============================================================================
# TEST A: human_delay - bounded delay generation
# =============================================================================

class TestHumanDelay:
    """Test HumanBehavior.human_delay() returns bounded values."""

    def test_delay_within_bounds(self):
        """human_delay returns value within [base*(1-variance), base*(1+variance)]."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        # Test multiple times with different seeds
        for _ in range(100):
            delay = hb.human_delay(base=1.0, variance=0.5)
            assert 0.5 <= delay <= 1.5, f"Delay {delay} out of bounds [0.5, 1.5]"

    def test_delay_respects_variance(self):
        """human_delay with variance=0 returns exactly base."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        # With zero variance, should return exactly base
        delay = hb.human_delay(base=2.0, variance=0.0)
        assert delay == 2.0, f"Expected 2.0, got {delay}"

    def test_delay_non_negative(self):
        """human_delay never returns negative values."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        for _ in range(100):
            delay = hb.human_delay(base=0.1, variance=0.9)
            assert delay >= 0, f"Delay {delay} is negative"


# =============================================================================
# TEST B: bezier_curve - curve generation
# =============================================================================

class TestBezierCurve:
    """Test HumanBehavior.bezier_curve() generates valid paths."""

    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.random.randint')
    def test_bezier_returns_list_of_tuples(self, mock_randint):
        """bezier_curve returns list of (x, y) tuples."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        # Deterministic: control points at origin, 20 steps
        mock_randint.side_effect = [0, 0, 0, 0, 20]  # cp offsets + steps

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        points = hb.bezier_curve(start=(0, 0), end=(100, 100))

        assert isinstance(points, list), "Should return list"
        assert len(points) > 0, "Should have at least one point"
        for point in points:
            assert isinstance(point, tuple), f"Point should be tuple: {point}"
            assert len(point) == 2, f"Point should be (x, y): {point}"

    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.random.randint')
    def test_bezier_starts_and_ends_correctly(self, mock_randint):
        """bezier_curve starts near start and ends near end."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        # Deterministic with zero control point offsets
        mock_randint.side_effect = [0, 0, 0, 0, 10]  # cp offsets + steps

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        start = (50, 50)
        end = (200, 300)
        points = hb.bezier_curve(start=start, end=end)

        # First point should be at start
        assert points[0] == start, f"First point {points[0]} should be {start}"
        # Last point should be at end
        assert points[-1] == end, f"Last point {points[-1]} should be {end}"


# =============================================================================
# TEST C: human_click - ActionChains integration
# =============================================================================

class TestHumanClick:
    """Test HumanBehavior.human_click() uses ActionChains correctly."""

    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.time.sleep')
    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.ActionChains')
    def test_human_click_calls_action_chains(self, mock_action_chains_class, mock_sleep):
        """human_click creates ActionChains and calls click().perform()."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        # Setup mocks
        mock_driver = Mock()
        mock_driver.execute_script.return_value = 1920  # viewport

        mock_action = MagicMock()
        mock_action_chains_class.return_value = mock_action
        # Chain methods return self
        mock_action.move_by_offset.return_value = mock_action
        mock_action.pause.return_value = mock_action
        mock_action.click.return_value = mock_action

        mock_element = Mock()
        mock_element.location = {'x': 100, 'y': 200}
        mock_element.size = {'width': 50, 'height': 30}

        hb = HumanBehavior(mock_driver)
        hb.human_click(mock_element)

        # Verify ActionChains was created
        mock_action_chains_class.assert_called_with(mock_driver)
        # Verify click was called
        mock_action.click.assert_called()
        # Verify perform was called
        mock_action.perform.assert_called()

    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.time.sleep')
    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.ActionChains')
    def test_human_click_includes_delay(self, mock_action_chains_class, mock_sleep):
        """human_click includes a delay after clicking."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        mock_driver.execute_script.return_value = 1920

        mock_action = MagicMock()
        mock_action_chains_class.return_value = mock_action
        mock_action.move_by_offset.return_value = mock_action
        mock_action.pause.return_value = mock_action
        mock_action.click.return_value = mock_action

        mock_element = Mock()
        mock_element.location = {'x': 100, 'y': 200}
        mock_element.size = {'width': 50, 'height': 30}

        hb = HumanBehavior(mock_driver)
        hb.human_click(mock_element)

        # Verify time.sleep was called (post-click delay)
        assert mock_sleep.called, "time.sleep should be called after click"


# =============================================================================
# TEST D: human_type - character-by-character typing
# =============================================================================

class TestHumanType:
    """Test HumanBehavior.human_type() types with delays."""

    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.time.sleep')
    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.ActionChains')
    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.random.random')
    def test_human_type_sends_each_character(self, mock_random, mock_action_chains_class, mock_sleep):
        """human_type sends each character via send_keys."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        # Prevent typos (random() returns >= 0.05)
        mock_random.return_value = 0.5

        mock_driver = Mock()
        mock_driver.execute_script.return_value = 1920

        mock_action = MagicMock()
        mock_action_chains_class.return_value = mock_action
        mock_action.move_by_offset.return_value = mock_action
        mock_action.pause.return_value = mock_action
        mock_action.click.return_value = mock_action

        mock_element = Mock()
        mock_element.location = {'x': 100, 'y': 200}
        mock_element.size = {'width': 50, 'height': 30}

        hb = HumanBehavior(mock_driver)
        hb.human_type(mock_element, "Hi")

        # Verify send_keys was called for each character
        send_keys_calls = [call for call in mock_element.send_keys.call_args_list]
        assert len(send_keys_calls) >= 2, f"Should send at least 2 characters, got {len(send_keys_calls)}"

    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.time.sleep')
    @patch('modules.infrastructure.foundups_selenium.src.human_behavior.ActionChains')
    def test_human_type_clears_element_first(self, mock_action_chains_class, mock_sleep):
        """human_type clears the element before typing."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        mock_driver.execute_script.return_value = 1920

        mock_action = MagicMock()
        mock_action_chains_class.return_value = mock_action
        mock_action.move_by_offset.return_value = mock_action
        mock_action.pause.return_value = mock_action
        mock_action.click.return_value = mock_action

        mock_element = Mock()
        mock_element.location = {'x': 100, 'y': 200}
        mock_element.size = {'width': 50, 'height': 30}

        hb = HumanBehavior(mock_driver)
        hb.human_type(mock_element, "X")

        mock_element.clear.assert_called()


# =============================================================================
# TEST E: should_perform_action - probabilistic decision
# =============================================================================

class TestShouldPerformAction:
    """Test HumanBehavior.should_perform_action() returns bool."""

    def test_returns_boolean(self):
        """should_perform_action always returns a boolean."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        for _ in range(50):
            result = hb.should_perform_action(0.5)
            assert isinstance(result, bool), f"Expected bool, got {type(result)}"

    @patch.dict(os.environ, {"YT_ACTION_RANDOMNESS_MODE": "fixed"})
    def test_fixed_mode_respects_probability(self):
        """In fixed mode, probability directly controls outcome distribution."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        mock_driver = Mock()
        hb = HumanBehavior(mock_driver)

        # With p=1.0 should always return True
        results = [hb.should_perform_action(1.0) for _ in range(20)]
        assert all(results), "p=1.0 should always return True in fixed mode"

        # With p=0.0 should always return False
        results = [hb.should_perform_action(0.0) for _ in range(20)]
        assert not any(results), "p=0.0 should always return False in fixed mode"


# =============================================================================
# TEST F: get_0102_behavior_interface - env var resolution
# =============================================================================

class TestBehaviorInterface:
    """Test get_0102_behavior_interface() env var resolution."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_returns_0102(self):
        """With no env vars, returns default '0102'."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import get_0102_behavior_interface

        result = get_0102_behavior_interface()
        assert result == "0102"

    @patch.dict(os.environ, {"YT_0102_BEHAVIOR_INTERFACE": "0102"}, clear=True)
    def test_env_var_respected(self):
        """YT_0102_BEHAVIOR_INTERFACE env var is respected."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import get_0102_behavior_interface

        result = get_0102_behavior_interface()
        assert result == "0102"

    @patch.dict(os.environ, {"YT_BEHAVIOR_PROFILE": "legacy"}, clear=True)
    def test_legacy_collapses_to_0102(self):
        """Legacy values collapse to '0102'."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import get_0102_behavior_interface

        result = get_0102_behavior_interface()
        assert result == "0102"


# =============================================================================
# TEST G: graceful failure - missing driver
# =============================================================================

class TestGracefulFailure:
    """Test graceful failure paths."""

    def test_none_driver_initialization(self):
        """HumanBehavior accepts None driver (deferred initialization)."""
        from modules.infrastructure.foundups_selenium.src.human_behavior import HumanBehavior

        # Should not raise during construction
        hb = HumanBehavior(driver=None)
        assert hb.driver is None

    def test_singleton_with_driver(self):
        """get_human_behavior returns singleton instance."""
        from modules.infrastructure.foundups_selenium.src import human_behavior

        # Reset singleton
        human_behavior._human_behavior_instance = None

        mock_driver = Mock()
        hb1 = human_behavior.get_human_behavior(mock_driver)
        hb2 = human_behavior.get_human_behavior(mock_driver)

        assert hb1 is hb2, "Should return same singleton instance"

        # Cleanup
        human_behavior._human_behavior_instance = None


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
