# OAuth compatibility import

Legacy path: modules.infrastructure.oauth_management.src.oauth_manager.
Canonical path: modules.platform_integration.utilities.oauth_management.src.oauth_manager.

The [compatibility source](src/oauth_manager.py) performs a wildcard re-export
from the canonical module. It adds no wrapper class, argument adaptation or
independent credential store. Public names and behavior follow Python's wildcard
import semantics for the canonical owner; there is no separately frozen export
list here. Import failures and transitive import effects are not isolated.

New integration and behavioral changes belong to the canonical implementation.
Preserve this alias until existing caller migration is verified. This review
opened no credential material, performed no OAuth authorization/token refresh,
and established no independent runtime acceptance or compatibility test suite.
