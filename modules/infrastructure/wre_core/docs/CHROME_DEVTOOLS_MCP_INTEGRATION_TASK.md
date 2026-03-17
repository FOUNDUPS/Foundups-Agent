# Chrome DevTools MCP Integration Task

**Created**: 2026-03-18
**Assigned To**: Qwen Code (via IronClaw)
**Priority**: P1 - Browser Automation Modernization
**WSP Compliance**: WSP 97 (CoT/CoR), WSP 77 (Agent Coordination)

## Executive Summary

Chrome 146 (released March 10, 2026) introduces **native MCP support** for AI browser automation. This task integrates Chrome DevTools MCP into the FoundUps Agent ecosystem, replacing/augmenting Selenium for more reliable browser control.

## Research Findings (2026-03-18)

### Chrome 146 Native MCP Features

1. **Enable via**: `chrome://inspect/#remote-debugging` - toggle MCP/agent access
2. **WebMCP**: Websites can register tools via `navigator.modelContext.registerTool()`
3. **Live Session Control**: AI agents can control authenticated browser sessions
4. **Slim Mode**: `--slim` flag for token-optimized tool descriptions

### Chrome DevTools MCP Server (v0.19.0)

**Installation**:
```bash
# Claude Code CLI
claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
```

**MCP Config** (for `.claude/settings.json` or MCP client):
```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

**Slim mode** (reduced tokens):
```json
"args": ["-y", "chrome-devtools-mcp@latest", "--slim", "--headless"]
```

### 26 Available Tools

| Category | Tools |
|----------|-------|
| **Input (9)** | click, drag, fill, fill_form, handle_dialog, hover, press_key, type_text, upload_file |
| **Navigation (6)** | close_page, list_pages, navigate_page, new_page, select_page, wait_for |
| **Emulation (2)** | emulate, resize_page |
| **Performance (4)** | performance_analyze_insight, performance_start_trace, performance_stop_trace, take_memory_snapshot |
| **Network (2)** | get_network_request, list_network_requests |
| **Debugging (6)** | evaluate_script, get_console_message, lighthouse_audit, list_console_messages, take_screenshot, take_snapshot |

### Key Benefits Over Selenium

1. **Automatic result waiting** (no manual waits/timeouts)
2. **Real-time bidirectional communication** (WebSocket vs HTTP)
3. **Direct access to authenticated sessions** (reuse login state)
4. **Performance tracing** (LCP, memory, Lighthouse audits)
5. **Native Chrome integration** (no chromedriver version mismatches)

## Implementation Plan

### Phase 1: MCP Server Setup (P0)

1. Add Chrome DevTools MCP to project MCP servers
2. Configure in `.claude/settings.json` or `mcp_servers/` directory
3. Test basic connectivity with `navigate_page`, `take_screenshot`

**Files to create/modify**:
- `mcp_servers/chrome_devtools_mcp/config.json` (NEW)
- `.claude/settings.json` (ADD mcpServer)

### Phase 2: Browser Automation Adapter (P1)

Create adapter layer that can use EITHER Selenium OR Chrome DevTools MCP:

```python
# modules/infrastructure/foundups_selenium/src/devtools_mcp_adapter.py

class BrowserAdapter:
    """Unified interface for Selenium and Chrome DevTools MCP."""

    def __init__(self, backend: str = "auto"):
        # "selenium", "mcp", or "auto" (prefer MCP if available)
        self.backend = self._detect_backend(backend)

    async def navigate(self, url: str) -> dict:
        if self.backend == "mcp":
            return await self._mcp_navigate(url)
        return self._selenium_navigate(url)

    async def click(self, selector: str) -> dict:
        if self.backend == "mcp":
            return await self._mcp_click(selector)
        return self._selenium_click(selector)
```

**Files to create**:
- `modules/infrastructure/foundups_selenium/src/devtools_mcp_adapter.py` (NEW)
- `modules/infrastructure/foundups_selenium/src/mcp_client.py` (NEW)

### Phase 3: Migrate Critical Paths (P2)

Replace Selenium calls in highest-error modules:

1. `youtube_shorts_scheduler/scripts/launch.py` (driver.close() crash)
2. `video_comments/skillz/tars_like_heart_reply/` (engagement)
3. `video_indexer/src/studio_ask_indexer.py` (Ask button automation)

### Phase 4: Performance Monitoring (P3)

Add performance tracing to WRE Observability:

```python
# Use MCP performance tools
await mcp.performance_start_trace()
# ... automation actions ...
trace = await mcp.performance_stop_trace()
insights = await mcp.performance_analyze_insight(trace)
# Log to telemetry (WSP 91)
```

## Configuration Options

| Flag | Description | Default |
|------|-------------|---------|
| `--headless` | Run without UI | false |
| `--browserUrl` / `-u` | Connect to running Chrome | - |
| `--wsEndpoint` / `-w` | WebSocket for remote | - |
| `--isolated` | Temp profile (auto-cleanup) | false |
| `--channel` | Chrome variant (stable/canary/beta) | stable |
| `--slim` | Minimal 3-tool set | false |
| `--no-performance-crux` | Disable CrUX API calls | false |

## Security Considerations

1. **Data Exposure**: MCP exposes browser content to AI - avoid sensitive tabs
2. **Session Isolation**: Use `--isolated` for untrusted automation
3. **Credential Safety**: Never automate password entry fields

## Success Criteria

1. Chrome DevTools MCP server added to project MCP config
2. BrowserAdapter created with Selenium/MCP dual-backend
3. youtube_shorts_scheduler crash fixed (no more 20-second timeouts)
4. Performance traces captured for automation workflows
5. Documentation updated in ROADMAP.md

## Sources

- [Chrome DevTools MCP - Chrome for Developers](https://developer.chrome.com/blog/chrome-devtools-mcp)
- [ChromeDevTools/chrome-devtools-mcp - GitHub](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [What's new in DevTools Chrome 146](https://developer.chrome.com/blog/new-in-devtools-146)
- [Chrome 146 Agent Features - AllClaw](https://allclaw.org/blog/chrome-146-agent)
- [Selenium WebDriver BiDi](https://www.selenium.dev/documentation/webdriver/bidi/)

---

*Generated by 0102 via WSP 97 research protocol*
