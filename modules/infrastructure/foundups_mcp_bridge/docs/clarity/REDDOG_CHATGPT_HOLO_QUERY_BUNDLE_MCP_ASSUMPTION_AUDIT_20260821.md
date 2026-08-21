# Assumption Audit: RedDog ChatGPT Holo Query Bundle MCP Surface

Status: IMPLEMENTED / LIVE ACCEPTANCE PENDING (expires 2026-08-28)

WSP lock: WSP_00, WSP_15, WSP_50, WSP_62, WSP_87, WSP_96, WSP_97 Annex A

Scope: one authenticated, read-only `holo_query_bundle` FastMCP tool and its
Streamable HTTP `/mcp` route. This record does not claim repository-wide
automation or enforcement of WSP_97 Annex A, whose protocol status remains
`SPEC_ONLY`.

## 1. Problem Statement

- What: expose the existing generation-bound RedDog HoloIndex query and bounded
  WSP memory bundle to ChatGPT through the FoundUps MCP bridge.
- Why: the existing MCP server exposes legacy SSE but ChatGPT's current plugin
  connection contract requires a Streamable HTTP MCP endpoint. The tool must
  reuse the governed owner/replica path and must not introduce indexing,
  maintenance, mutation, execution, or credential disclosure authority.
- Who: authorized by 012 in the RedDog audit/integration request; implementation
  owner is the 0102 RedDog main-integration author.

## 2. Assumptions

| ID | Assumption | Evidence | Confidence |
|---|---|---|---|
| A1 | ChatGPT requires Streamable HTTP rather than legacy SSE as the authoritative plugin route. | OpenAI developer documentation: `https://developers.openai.com/plugins/build/mcp-server` and `https://developers.openai.com/plugins/deploy/connect-chatgpt`, verified 2026-08-21. | HIGH |
| A2 | The pinned local runtime can mount Streamable HTTP. | `fastmcp==2.13.0.2`; runtime introspection shows `FastMCP.http_app(..., transport='http'|'streamable-http'|'sse')`. | HIGH |
| A3 | The bundled server can remain private without pretending a static bearer is ChatGPT user auth. | The server rejects every non-loopback bind. Secure MCP Tunnel supplies the external HTTPS/control-plane boundary; an optional loopback bearer is development defense only. Direct public OAuth 2.1/auth-proxy support is not implemented in this slice. | HIGH |
| A4 | The existing one-shot bridge is the canonical bounded adapter for this slice. | `scripts/reddog_holoindex_owner_query_once.py` validates an exact request allowlist and distinguishes semantic owner queries from store-free lexical/bundle-only retrieval. | HIGH |
| A5 | Semantic reads must retain the verified query-replica route. | `QueryReplicaOwnerRoute.revalidate()` and owner bootstrap require the exact replica binding before owner reuse/start. | HIGH |
| A6 | A public MCP response needs a stricter projection than a local extension response. | Owner/bundle responses may contain local paths and direct-read content; ChatGPT is a remote consumer. | HIGH |

## 3. Failure Modes

| ID | Failure Mode | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| F1 | `/mcp` is exposed directly on a public interface or a static bearer is misrepresented as ChatGPT OAuth. | LOW | CRITICAL | Reject all non-loopback binds. Use Secure MCP Tunnel for the external HTTPS/control plane. Keep optional bearer support explicitly local/dev-only and make no OAuth/live-ChatGPT claim. |
| F2 | Tool bypasses the owner/replica authority or reads the Holo store directly. | MED | HIGH | Delegate only to the one-shot governed adapter; lexical/bundle-only paths remain store-free; semantic rejection remains typed and cannot be relabeled CURRENT. |
| F3 | Tool triggers reindex, maintenance, writes, or execution authority. | LOW | HIGH | Register exactly `holo_query_bundle`; request schema has no maintenance fields; assert `no_holoindex_reindex_performed`; production scan forbids raw `holo_index.py` execution. |
| F4 | Absolute repository, SSD, replica, interpreter, or credential paths leak remotely. | MED | HIGH | Apply a dedicated bounded public projection that removes private path/token fields recursively and emits only repo-relative hit locations plus digests/typed authority metadata. Add hostile projection tests. |
| F5 | Legacy `/sse` is misdocumented as ChatGPT-ready. | MED | HIGH | Expose no `/sse` route, mount Streamable HTTP at `/mcp`, and make readiness tests initialize/list/call through `/mcp`; old launcher names are aliases only. |
| F6 | Oversize requests/responses cause memory or latency amplification. | MED | HIGH | Reuse exact query/limit/hint/must-include caps; cap projected response bytes and result counts; fail closed when projection cannot fit. |
| F7 | Missing/stale semantic authority is presented as successful live recall. | MED | HIGH | Preserve owner `ok`, freshness, gap, authority, attempts, and error fields; never synthesize CURRENT; lexical bundle is labeled separately. |
| F8 | FastMCP session/lifespan integration is mounted incorrectly. | MED | HIGH | Use the supported `http_app(path='/mcp', transport='streamable-http')` surface and validate MCP initialize, tools/list, and one safe tool call with the pinned runtime. |
| F9 | Server or readiness subprocess inherits ambient provider/cloud credentials or Python/loader injection. | MED | CRITICAL | Build children from a closed OS/runtime environment allowlist, then add only exact repository, dependency, and optional local-token fields; hostile tests cover both child paths and the capability probe. |

## 4. Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| Keep SSE only | It is legacy for this product boundary and does not meet the current ChatGPT connection contract. |
| Add a second HoloIndex service for ChatGPT | Duplicates authority, risks store contention, and violates the existing owner/replica design. |
| Expose the local extension bundle unchanged | Local absolute paths and direct-read content are not an acceptable remote projection. |
| Expose raw `holo_index.py` through MCP | Bypasses the governed one-shot adapter and can violate freshness/store ownership rules. |
| Remove legacy SSE immediately | Unnecessary compatibility break; it can remain explicitly non-authoritative while `/mcp` becomes the ChatGPT route. |

## 5. Decision Record

- Decision: PROCEED
- Owner: 0102 RedDog main-integration author
- Timestamp: 2026-08-21T00:00:00+09:00
- Boundary: implement and test only the read-only tool, public projection,
  authenticated `/mcp` transport, and truthful documentation described above.
