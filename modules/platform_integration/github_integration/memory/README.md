# GitHub integration memory

Retrieve README, INTERFACE, ROADMAP, ModLog and both test documents before changes.
The client and the RedDog permission probe have separate contracts; neither a file
observation nor a permission label is an authenticated FoundUp issuer grant.

The client test owner is tests/test_github_api_client.py. Extend its existing HTTP
mocks for request compatibility and file observations. The sibling permission
probe suite is the other canonical unit-shard member. Other tests are explicitly
quarantined in WSP_knowledge/WSP_Test_Registry.json; do not run discovery across
the directory or substitute mock API adapters for the real client.

Regular-file observations use Git trees/modes and blob identity. Contents may
dereference symlinks. Repository metadata brackets are non-atomic and do not
exclude name-reuse races. Later claim admission must resolve this at its own
authenticated provider boundary, then verify a fresh nonce and key possession.

Historical README completeness/security percentages are not current audit results.
Use exact source, test IDs, environment and hosted receipts for current claims.

Observation HTTP has a private bounded GET policy; legacy requests retain theirs.
Count actual chunks before JSON parsing and preserve cancellation/cleanup. Library
deadlines are not hard wall-time/RSS guarantees; logical GET counts are distinct
from aiohttp reconnect retries. Never infer authenticated control from these bounds.
