# Chrome DevTools MCP

**Chrome 146 Native AI Agent Browser Control**

## Quick Start

### Option 1: Connect to Existing Chrome

Start Chrome with debug port:
```bash
chrome.exe --remote-debugging-port=9222
```

Then use the MCP with `-u` flag:
```bash
npx -y chrome-devtools-mcp@latest -u http://localhost:9222
```

### Option 2: Launch New Browser

```bash
npx -y chrome-devtools-mcp@latest
```

### Option 3: Headless/Slim Mode (Token-Optimized)

```bash
npx -y chrome-devtools-mcp@latest --slim --headless
```

## Available Tools (26 total)

| Category | Tools |
|----------|-------|
| **Input** | click, drag, fill, fill_form, handle_dialog, hover, press_key, type_text, upload_file |
| **Navigation** | close_page, list_pages, navigate_page, new_page, select_page, wait_for |
| **Emulation** | emulate, resize_page |
| **Performance** | performance_start_trace, performance_stop_trace, performance_analyze_insight, take_memory_snapshot |
| **Network** | get_network_request, list_network_requests |
| **Debugging** | evaluate_script, get_console_message, lighthouse_audit, list_console_messages, take_screenshot, take_snapshot |

## Key Benefits Over Selenium

1. **Automatic result waiting** - No manual waits/timeouts
2. **Bidirectional communication** - WebSocket vs HTTP polling
3. **Authenticated sessions** - Reuse logged-in browser state
4. **Performance tracing** - LCP, memory, Lighthouse audits
5. **No chromedriver version mismatches** - Native Chrome integration

## Configuration for Claude Code

Add to `.claude/settings.json`:
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

Or for connecting to existing browser:
```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest", "-u", "http://localhost:9222"]
    }
  }
}
```

## WSP Compliance

- **WSP 77**: Agent Coordination - Tools invocable by Qwen/Gemma
- **WSP 91**: Observability - Performance traces for telemetry
- **WSP 97**: CoT/CoR - Research-verified implementation

## Sources

- [Chrome DevTools MCP - Chrome for Developers](https://developer.chrome.com/blog/chrome-devtools-mcp)
- [ChromeDevTools/chrome-devtools-mcp - GitHub](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [Chrome 146 Release Notes](https://developer.chrome.com/blog/new-in-devtools-146)

---

*Created by 0102 via WSP 97 research protocol | 2026-03-18*
