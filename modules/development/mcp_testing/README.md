# Interactive MCP gateway probe

The only tracked file is tests/enhanced_mcp_test.py. It imports show_mcp_services_menu from the existing infrastructure/mcp_manager owner and, when run as a script, opens that interactive menu. It is a manual probe, not an automated acceptance suite with assertions. Its printed completion line does not prove that any MCP server or tool worked.

Review the MCP manager's current dependencies and service behavior before a deliberate run. Importing the probe still imports that manager; no side-effect-free import guarantee is made. Do not include the interactive entrypoint in unattended global collection or represent it as behavioral coverage. No live MCP service was started or exercised for this documentation.
