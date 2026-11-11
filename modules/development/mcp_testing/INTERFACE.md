# MCP manual probe interface

[tests/enhanced_mcp_test.py](tests/enhanced_mcp_test.py) imports
show_mcp_services_menu from infrastructure/mcp_manager and calls it only when
the file is executed as __main__. It defines no separate exported service API.
The imported manager owns its dependencies, service operations and error behavior.

The probe prints entry/completion messages around the menu call. These messages
contain no assertions or tool/server health verification. Importing the file
still imports the manager; no side-effect-free transitive import guarantee is
established. This is implemented manual tooling, not validated server operation.
See [tests/README.md](tests/README.md); no live MCP operation was performed here.
