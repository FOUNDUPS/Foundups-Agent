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

## 6. Dependency qualification — 2026-09-14

Source: main `1173d1ab5e4af8a0e3cbe5381bcd30cf0e865ac3`. This dated
qualification does not renew the expired August decision or admit a runtime.
The system observation is `dependency_qualification_continuation_20260914` in
`docs/roadmaps/RSI_BASELINE_OBSERVATIONS_20260913.json`.

### Advisory scope and repository evidence

- FastMCP [GHSA-vv7q-7jx5-f767](https://github.com/PrefectHQ/fastmcp/security/advisories/GHSA-vv7q-7jx5-f767)
  affects path construction in the OpenAPI provider before 3.2.0. The maintainer
  labels it High; the repository's Dependabot alert 317 labels it Critical.
  `src/mcp_server.py:build_mcp_server()` constructs FastMCP directly and registers
  exactly `holo_query_bundle` with tool decorators. No OpenAPI adapter invocation
  was found in the reviewed Holo/MCP source and launch configuration scope.
  This is a source observation, not a live exposure assessment or alert dismissal.
- ChromaDB alerts 286/322 target Python server collection creation/update with
  caller-controlled embedding configuration. The researchers distinguish
  [pre-authentication creation](https://www.hiddenlayer.com/research/chromatoast-served-pre-auth)
  from [authenticated update](https://www.hiddenlayer.com/sai-security-advisory/2026-06-chromadb-5).
  `holo_index/core/holo_index.py` opens `open_query_snapshot_client()` in readonly
  query mode and a local `PersistentClient` for maintenance. The immutable reader
  lives in `src/holo_query_snapshot_store.py`; it does not expose collection
  mutation endpoints. No Python Chroma server/HTTP-client setup was found in the
  reviewed source/configuration scope. Installed ChromaDB 1.5.5 remains affected
  by the manifest alerts; GitHub reports no first patched version for either.
  Deployment topology and other consumers remain unverified. Do not start a
  vulnerable feature to test it or infer a safe upgrade version.

The bounded search covered Python, PowerShell, shell, YAML and Dockerfile paths
under `holo_index`, this module, `scripts` and `.github`. Negative symbol searches
are not a proof against dynamic registration, external deployment or other repos.
No exploit payload, live listener, service restart, reindex or shared package
change was used for this qualification.

### Existing upgrades and exact-version contract

| Candidate | Observed head | Qualification |
|---|---|---|
| [PR1526](https://github.com/FOUNDUPS/Foundups-Agent/pull/1526), FastMCP only | `9b17a56c61189bcca48bd130a41d9d3dcec35229` | Resolver rejects FastMCP 3.2.0 with MCP 1.20.0; FastMCP requires MCP >=1.24.0,<2.0. |
| [PR1525](https://github.com/FOUNDUPS/Foundups-Agent/pull/1525), MCP only | `b94bbda640fd50579301e8bd187269f4d20184cc` | Quartet resolves, but FastMCP remains 2.13.0.2 and the launcher's pinned MCP version differs. |
| Paired disposable candidate | FastMCP 3.2.0 / MCP 1.28.1 / Pydantic 2.12.3 / Uvicorn 0.38.0 | Resolver succeeds; 25 existing MCP tests pass. This is not production or full-lifecycle acceptance. |

Both open PRs change only `requirements.txt`. Neither updates
`scripts/launch.py:MCP_RUNTIME_VERSIONS`, whose exact equality check is intentional.
`test_runtime_version_contract_matches_requirements` binds those declarations.
Neither one-line upgrade is a complete migration. Their August checks do not
establish current-main compatibility; this qualification does not replace them.

The separate query interpreter reports 3.2.0 / 1.27.0 / 2.12.5 / 0.40.0 for the
same four distributions, plus ChromaDB 1.5.5. Package metadata does not establish
which MCP service is running or satisfy the pinned startup contract.

### Local validation and next action

- Existing launcher, MCP surface and immutable snapshot suites: **38 passed,
  2 deselected in 7.87s** with the query interpreter. The snapshot suite exports
  real Chroma data in temporary storage and reads it without reopening Chroma.
- Fresh external venv containing the paired quartet and the existing test-runner
  versions: **25 passed, 2 deselected in 3.68s** for launcher/MCP suites. These
  are the same 25 MCP cases, not 25 additional distinct tests. This environment
  was installed from public PyPI wheels and was not promoted or activated.
- Both runs exclude the two tests that start fixed-port listeners. Bearer,
  surface, schema and mocked lifecycle checks passed; live initialize/list/call,
  service ownership/cleanup and exact closure of the paired runtime remain open.
- Exact base CI and CodeQL runs 34803625970 / 34803625558 succeeded. They verify
  base `1173d1ab`, not these documentation changes or the new disposable runtime.

Reconcile PR1526/1525 as one owner-coordinated migration with the launcher pins,
then qualify a replacement runtime and its live lifecycle in an owned fixture.
Preserve the existing environment until its replacement is admitted. Chroma
deployment qualification/mitigation remains with the corresponding runtime owner;
the three alerts stay open. This completes the local preflight, not R03/R04.
The system re-score selects R11 authenticated mirror restoration (17/P0) while
the higher-scored integrated migration lacks current runtime/owner admission.
