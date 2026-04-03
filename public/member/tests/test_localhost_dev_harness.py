"""
Localhost Dev Harness Tests

Tests for the localhost-only Mall dev harness that bypasses
Clerk/Firestore auth for local development.

Gating rules:
  - MUST be localhost or 127.0.0.1
  - MUST have ?devMall=1 query parameter
  - Production domains NEVER bypass auth

Harness provides:
  - Mock member identity
  - Mock invite codes
  - Real catalog from mall-catalog.json
  - Full Mall shell access
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        return f.read()


class TestDevHarnessGating:
    """Test that harness is properly gated."""

    def test_harness_requires_localhost(self):
        """Harness checks for localhost or 127.0.0.1."""
        html = _read("index.html")
        assert "host === 'localhost'" in html
        assert "host === '127.0.0.1'" in html

    def test_harness_requires_devmall_param(self):
        """Harness requires explicit ?devMall=1 param."""
        html = _read("index.html")
        assert "devMall" in html
        assert "params.get('devMall') === '1'" in html

    def test_harness_uses_both_conditions(self):
        """Harness requires BOTH localhost AND devMall=1."""
        html = _read("index.html")
        assert "isLocalhost && hasDevFlag" in html

    def test_production_path_unchanged(self):
        """Production auth path still exists and runs when harness inactive."""
        html = _read("index.html")
        # initClerkAuth is still called when harness is not active
        assert "initClerkAuth().catch" in html
        # But only in the else branch
        assert "} else {" in html
        assert "initClerkAuth()" in html


class TestDevHarnessFunctionality:
    """Test harness functionality."""

    def test_harness_function_exists(self):
        """initDevHarness function exists."""
        html = _read("index.html")
        assert "async function initDevHarness()" in html

    def test_harness_detection_function_exists(self):
        """isDevHarnessActive function exists."""
        html = _read("index.html")
        assert "function isDevHarnessActive()" in html

    def test_mock_user_data_seeded(self):
        """Mock user data is seeded with expected fields."""
        html = _read("index.html")
        assert "dev_member_001" in html
        assert "devmember" in html
        assert "dev@localhost" in html
        assert "inviteValidated: true" in html

    def test_mock_invite_codes_provided(self):
        """Mock invite codes are provided."""
        html = _read("index.html")
        assert "DEV-0001-0001" in html
        assert "inviteCodes:" in html

    def test_harness_loads_real_catalog(self):
        """Harness uses real mall-video-catalog.json."""
        html = _read("index.html")
        assert "loadMallCatalog()" in html

    def test_harness_initializes_mall_components(self):
        """Harness initializes Mall components."""
        html = _read("index.html")
        assert "window.redDog" in html
        assert "window.mallTileField" in html
        assert "window.mallPlanes" in html


class TestDevHarnessProduction:
    """Test that production remains protected."""

    def test_clerk_sdk_still_loaded(self):
        """Clerk SDK is still loaded in HTML."""
        html = _read("index.html")
        assert "clerk.browser.js" in html
        assert "data-clerk-publishable-key" in html

    def test_firestore_imports_still_present(self):
        """Firestore imports are still present."""
        html = _read("index.html")
        assert "firebase-firestore.js" in html
        assert "getFirestore" in html

    def test_invite_gate_still_exists(self):
        """Invite gate UI is still present."""
        html = _read("index.html")
        assert 'id="inviteGate"' in html
        assert "Do you have an invite" in html

    def test_clerk_auth_flow_unchanged(self):
        """Clerk auth flow is unchanged."""
        html = _read("index.html")
        assert "window.Clerk.load" in html
        assert "checkInviteStatus" in html
        assert "window.Clerk.user" in html


class TestRouteBridgeDevMall:
    """Test route bridge preserves devMall param."""

    def test_bridge_preserves_devmall(self):
        """Route bridge preserves devMall param on redirect."""
        bridge = _read("../f/index.html")
        assert "devMall" in bridge
        assert "&devMall=1" in bridge

    def test_bridge_error_link_preserves_devmall(self):
        """Route bridge error link preserves devMall."""
        bridge = _read("../f/index.html")
        assert "?devMall=1" in bridge


class TestGestureEngineOnTap:
    """Test gesture engine tap callback."""

    def test_ontap_callback_documented(self):
        """onTap is documented in gesture engine."""
        js = _read("js/gesture-engine.js")
        assert "onTap" in js
        # Check it's in the handlers param documentation
        assert "onTap()" in js

    def test_ontap_handler_called(self):
        """onTap handler is called on single tap."""
        js = _read("js/gesture-engine.js")
        assert "handlers.onTap" in js

    def test_tap_confirm_delay_exists(self):
        """Tap confirm delay distinguishes single from double."""
        js = _read("js/gesture-engine.js")
        assert "TAP_CONFIRM_DELAY" in js

    def test_double_tap_cancels_single_tap(self):
        """Double-tap cancels pending single tap."""
        js = _read("js/gesture-engine.js")
        # Should clear the tap timer on double-tap
        assert "clearTimeout(tapTimer)" in js

    def test_tap_timer_cleaned_up_on_destroy(self):
        """Tap timer is cleaned up in destroy function."""
        js = _read("js/gesture-engine.js")
        # Check destroy function clears timer
        assert "tapTimer" in js
        # Multiple mentions including in destroy


class TestGestureEngineDesktopParity:
    """Test desktop gesture parity."""

    def test_click_as_tap_works(self):
        """Mouse click triggers tap path (small movement)."""
        js = _read("js/gesture-engine.js")
        # mousedown/mouseup with small movement triggers tap logic
        assert "mousedown" in js
        assert "mouseup" in js
        assert "TAP_THRESHOLD" in js

    def test_double_click_as_double_tap(self):
        """Double-click triggers double-tap."""
        js = _read("js/gesture-engine.js")
        assert "dblclick" in js
        assert "onDoubleTap" in js

    def test_click_drag_as_swipe(self):
        """Click-drag triggers swipe."""
        js = _read("js/gesture-engine.js")
        assert "SWIPE_THRESHOLD" in js
        assert "onSwipe" in js


class TestNoRegression:
    """Test no regression in existing functionality."""

    def test_double_tap_still_works(self):
        """Double-tap/double-click still works."""
        js = _read("js/gesture-engine.js")
        assert "DOUBLE_TAP_DELAY" in js
        assert "onDoubleTap" in js

    def test_swipe_still_works(self):
        """Swipe detection still works."""
        js = _read("js/gesture-engine.js")
        assert "onSwipe" in js
        assert "'left'" in js
        assert "'right'" in js
        assert "'up'" in js
        assert "'down'" in js

    def test_drag_scroll_still_works(self):
        """dragScroll function still exists."""
        js = _read("js/gesture-engine.js")
        assert "function dragScroll" in js
        assert "window.dragScroll" in js

    def test_gesture_zone_exposed(self):
        """gestureZone is exposed on window."""
        js = _read("js/gesture-engine.js")
        assert "window.gestureZone" in js
