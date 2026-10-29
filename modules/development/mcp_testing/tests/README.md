# Manual MCP gateway probe

[enhanced_mcp_test.py](enhanced_mcp_test.py) is an interactive script, not a pytest
acceptance suite: it has no assertions or test functions. Running it as __main__
opens show_mcp_services_menu; importing it still imports the real MCP manager.
Its completion message does not certify server availability or a successful tool.

No unattended run command is prescribed for this operational menu. Use the MCP
manager owner's current service/permission instructions for an intentional probe,
and record the concrete selected operation and observed result separately.
No service was started or exercised for this source-only documentation update.
