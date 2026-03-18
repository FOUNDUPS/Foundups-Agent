"""
Chrome DevTools MCP Adapter - Unified Browser Automation Interface

Provides a unified interface that can use EITHER Selenium OR Chrome DevTools MCP
for browser automation. This enables gradual migration from Selenium to MCP
while maintaining backwards compatibility.

Chrome DevTools MCP Tools (26 total):
- Input: click, drag, fill, fill_form, handle_dialog, hover, press_key, type_text, upload_file
- Navigation: close_page, list_pages, navigate_page, new_page, select_page, wait_for
- Emulation: emulate, resize_page
- Performance: performance_start_trace, performance_stop_trace, performance_analyze_insight
- Network: get_network_request, list_network_requests
- Debugging: evaluate_script, take_screenshot, take_snapshot, lighthouse_audit

WSP Compliance:
    WSP 72: Module Independence
    WSP 91: Observability (logging)
    WSP 11: Interface Documentation

Usage:
    # Auto-detect best backend
    adapter = BrowserAdapter(backend="auto")

    # Force Selenium
    adapter = BrowserAdapter(backend="selenium", driver=existing_driver)

    # Force MCP
    adapter = BrowserAdapter(backend="mcp")

    # Unified operations
    await adapter.navigate("https://youtube.com")
    await adapter.click("button#submit")
    await adapter.type_text("input#search", "hello")
    screenshot = await adapter.take_screenshot()
"""

import asyncio
import logging
import os
import subprocess
import json
from dataclasses import dataclass
from typing import Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BrowserResult:
    """Result from browser operation."""
    success: bool
    data: Any = None
    error: str = None
    backend: str = None


class MCPClient:
    """
    Client for Chrome DevTools MCP server.

    Communicates with the MCP server via stdio protocol.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._connected = False
        self._request_id = 0

    async def connect(self) -> bool:
        """Start and connect to Chrome DevTools MCP server."""
        if self._connected:
            return True

        try:
            # Start MCP server via npx
            self._process = subprocess.Popen(
                ["npx", "-y", "chrome-devtools-mcp@latest"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    "CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1"
                }
            )

            # Wait briefly for server to start
            await asyncio.sleep(1)

            if self._process.poll() is not None:
                stderr = self._process.stderr.read() if self._process.stderr else ""
                logger.error(f"[MCP] Server failed to start: {stderr}")
                return False

            self._connected = True
            logger.info("[MCP] Chrome DevTools MCP server connected")
            return True

        except FileNotFoundError:
            logger.error("[MCP] npx not found - ensure Node.js is installed")
            return False
        except Exception as e:
            logger.error(f"[MCP] Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self._connected = False

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the MCP tool (e.g., "navigate_page", "click")
            arguments: Tool-specific arguments

        Returns:
            Tool result dict
        """
        if not self._connected:
            if not await self.connect():
                return {"error": "MCP not connected"}

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        try:
            # Send request
            request_line = json.dumps(request) + "\n"
            self._process.stdin.write(request_line)
            self._process.stdin.flush()

            # Read response
            response_line = self._process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                if "error" in response:
                    return {"error": response["error"].get("message", "Unknown error")}
                return response.get("result", {})
            else:
                return {"error": "No response from MCP server"}

        except Exception as e:
            logger.error(f"[MCP] Tool call failed: {e}")
            return {"error": str(e)}

    @property
    def is_connected(self) -> bool:
        return self._connected


class BrowserAdapter:
    """
    Unified interface for Selenium and Chrome DevTools MCP.

    Provides a consistent API for browser automation regardless of backend.
    Supports auto-detection, graceful fallback, and mixed usage.
    """

    def __init__(
        self,
        backend: str = "auto",
        driver: Any = None,
        chrome_port: int = 9222
    ):
        """
        Initialize browser adapter.

        Args:
            backend: "auto", "selenium", or "mcp"
            driver: Existing Selenium WebDriver (for selenium backend)
            chrome_port: Chrome debugging port (for MCP backend)
        """
        self._requested_backend = backend
        self._active_backend: Optional[str] = None
        self._driver = driver
        self._mcp_client: Optional[MCPClient] = None
        self._chrome_port = chrome_port
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the adapter and detect/connect to backend."""
        if self._initialized:
            return True

        backend = self._requested_backend

        if backend == "auto":
            # Try MCP first, fall back to Selenium
            if await self._try_mcp():
                self._active_backend = "mcp"
            elif self._try_selenium():
                self._active_backend = "selenium"
            else:
                logger.error("[ADAPTER] No backend available")
                return False

        elif backend == "mcp":
            if not await self._try_mcp():
                logger.error("[ADAPTER] MCP backend requested but unavailable")
                return False
            self._active_backend = "mcp"

        elif backend == "selenium":
            if not self._try_selenium():
                logger.error("[ADAPTER] Selenium backend requested but unavailable")
                return False
            self._active_backend = "selenium"

        self._initialized = True
        logger.info(f"[ADAPTER] Initialized with backend: {self._active_backend}")
        return True

    async def _try_mcp(self) -> bool:
        """Try to connect to MCP backend."""
        try:
            self._mcp_client = MCPClient()
            return await self._mcp_client.connect()
        except Exception as e:
            logger.debug(f"[ADAPTER] MCP unavailable: {e}")
            return False

    def _try_selenium(self) -> bool:
        """Try to use Selenium backend."""
        if self._driver:
            return True

        # Try to connect to existing Chrome debug session
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            opts = Options()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{self._chrome_port}")
            self._driver = webdriver.Chrome(options=opts)
            return True
        except Exception as e:
            logger.debug(f"[ADAPTER] Selenium unavailable: {e}")
            return False

    @property
    def backend(self) -> Optional[str]:
        """Current active backend."""
        return self._active_backend

    @property
    def driver(self) -> Any:
        """Selenium WebDriver (if using selenium backend)."""
        return self._driver

    # ==========================================
    # Navigation Methods
    # ==========================================

    async def navigate(self, url: str) -> BrowserResult:
        """Navigate to URL."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("navigate_page", {"url": url})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                self._driver.get(url)
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def wait_for(self, selector: str, timeout: int = 30000) -> BrowserResult:
        """Wait for element to appear."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("wait_for", {
                "selector": selector,
                "timeout": timeout
            })
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC

                wait = WebDriverWait(self._driver, timeout / 1000)
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                return BrowserResult(success=True, data=element, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    # ==========================================
    # Input Methods
    # ==========================================

    async def click(self, selector: str) -> BrowserResult:
        """Click element by selector."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("click", {"selector": selector})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                from selenium.webdriver.common.by import By
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def type_text(self, selector: str, text: str) -> BrowserResult:
        """Type text into element."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("type_text", {
                "selector": selector,
                "text": text
            })
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                from selenium.webdriver.common.by import By
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                element.send_keys(text)
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def fill(self, selector: str, value: str) -> BrowserResult:
        """Fill input field (clears first)."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("fill", {
                "selector": selector,
                "value": value
            })
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                from selenium.webdriver.common.by import By
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(value)
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def hover(self, selector: str) -> BrowserResult:
        """Hover over element."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("hover", {"selector": selector})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.action_chains import ActionChains
                element = self._driver.find_element(By.CSS_SELECTOR, selector)
                ActionChains(self._driver).move_to_element(element).perform()
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def press_key(self, key: str) -> BrowserResult:
        """Press keyboard key."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("press_key", {"key": key})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys

                key_map = {
                    "Enter": Keys.ENTER,
                    "Tab": Keys.TAB,
                    "Escape": Keys.ESCAPE,
                    "ArrowUp": Keys.ARROW_UP,
                    "ArrowDown": Keys.ARROW_DOWN,
                }
                selenium_key = key_map.get(key, key)

                active = self._driver.switch_to.active_element
                active.send_keys(selenium_key)
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    # ==========================================
    # Debugging/Screenshot Methods
    # ==========================================

    async def take_screenshot(self, path: Optional[str] = None) -> BrowserResult:
        """Take screenshot."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            args = {}
            if path:
                args["path"] = path
            result = await self._mcp_client.call_tool("take_screenshot", args)
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                if path:
                    self._driver.save_screenshot(path)
                    return BrowserResult(success=True, data={"path": path}, backend="selenium")
                else:
                    png = self._driver.get_screenshot_as_png()
                    return BrowserResult(success=True, data={"png": png}, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def evaluate_script(self, script: str) -> BrowserResult:
        """Execute JavaScript."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("evaluate_script", {"script": script})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                result = self._driver.execute_script(script)
                return BrowserResult(success=True, data=result, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    # ==========================================
    # Page Management Methods
    # ==========================================

    async def new_page(self) -> BrowserResult:
        """Open new page/tab."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("new_page", {})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                self._driver.execute_script("window.open('');")
                handles = self._driver.window_handles
                self._driver.switch_to.window(handles[-1])
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def close_page(self) -> BrowserResult:
        """Close current page/tab."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("close_page", {})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                # Use JavaScript close to avoid Chrome 146 timeout issue
                self._driver.execute_script("window.close();")
                handles = self._driver.window_handles
                if handles:
                    self._driver.switch_to.window(handles[-1])
                return BrowserResult(success=True, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    async def list_pages(self) -> BrowserResult:
        """List open pages/tabs."""
        if not await self.initialize():
            return BrowserResult(success=False, error="Not initialized")

        if self._active_backend == "mcp":
            result = await self._mcp_client.call_tool("list_pages", {})
            return BrowserResult(
                success="error" not in result,
                data=result,
                error=result.get("error"),
                backend="mcp"
            )
        else:
            try:
                handles = self._driver.window_handles
                pages = []
                current = self._driver.current_window_handle
                for h in handles:
                    self._driver.switch_to.window(h)
                    pages.append({
                        "handle": h,
                        "title": self._driver.title,
                        "url": self._driver.current_url
                    })
                self._driver.switch_to.window(current)
                return BrowserResult(success=True, data=pages, backend="selenium")
            except Exception as e:
                return BrowserResult(success=False, error=str(e), backend="selenium")

    # ==========================================
    # Cleanup
    # ==========================================

    async def close(self):
        """Close adapter and cleanup resources."""
        if self._mcp_client:
            await self._mcp_client.disconnect()
        # Don't close Selenium driver - it may be shared
        self._initialized = False


# Convenience function
def get_browser_adapter(
    backend: str = "auto",
    driver: Any = None,
    chrome_port: int = 9222
) -> BrowserAdapter:
    """
    Get a browser adapter instance.

    Args:
        backend: "auto", "selenium", or "mcp"
        driver: Existing Selenium WebDriver
        chrome_port: Chrome debugging port

    Returns:
        BrowserAdapter instance
    """
    return BrowserAdapter(backend=backend, driver=driver, chrome_port=chrome_port)
