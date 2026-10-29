# HoloIndex external FoundUp interface

This directory's interface is declarative discovery metadata in
[foundup_manifest.json](foundup_manifest.json). It contains no tracked executable
service or public search API. The [README](README.md) separates this external
FoundUp surface from internal HoloIndex infrastructure.

The manifest identifies `holoindex_prod_01`, tier `INFRA`, lifecycle `incubating`
and `launch_readiness=discoverable_only`. Its routing prefix is
`/f/holoindex_prod_01`, while `entry_url` is empty. The declared namespace,
capabilities, agent route and collection names are catalog metadata; their
presence does not provision storage, expose internal collections, grant query
authority or demonstrate an accessible endpoint. Likewise the `HOLO` symbol is
a declaration, not evidence of token issuance, a contract address or settlement.

Internal code remains owned by the repository's HoloIndex and MCP bridge paths,
with their own admission, freshness and runtime contracts. This documentation
does not bypass those boundaries or introduce a second retrieval implementation.
No catalog mutation, deployment, token operation or live endpoint verification
was performed. Status: specification/discovery surface only; executable public
service acceptance remains separate from manifest presence.
