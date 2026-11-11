# Legacy OAuth import compatibility

This module preserves older imports of `modules.infrastructure.oauth_management.src.oauth_manager`. Its src/oauth_manager.py re-exports the canonical implementation from `modules.platform_integration.utilities.oauth_management.src.oauth_manager`. It does not implement a separate OAuth service.

Use the canonical owner for behavior, dependency requirements, tests and interface changes. The compatibility module uses a wildcard re-export, so its available names follow that owner rather than a separately frozen export list. Importing it imports the canonical module; this documentation does not establish a side-effect-free import boundary.

No credential files were opened, credentials displayed, browser authorization started or tokens refreshed for this documentation. There is no tracked dedicated test suite or dependency manifest in this compatibility folder at this revision. Preserve the old import path until caller migration has been verified.
