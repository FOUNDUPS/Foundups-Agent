# FoundUps Mosh Pit — Wave-style MVP

Status: **LOCAL_READ_ONLY_CANDIDATE / HOST_NOT_WIRED**
Research and source inspection: 2026-09-09.

## Product decision

Mosh Pit opens directly on the newest day and activity bullets. Each activity
is a small expandable conversation: short summary, details, replies, decisions,
evidence and follow-ups. It grows upward. Background and plans belong below the
history or in separate views, not in a prefixed dashboard. Routine copyright,
video-block, delivery and synchronization notices do not enter the activity feed.
An actual consequential response to a notice may be its own activity.

Build this interaction on the existing FoundUps event/memory system. Do not
resurrect Wave's server or create an independent Mosh Pit history database.

## Open-source comparison

| Option | Verified capability | Decision for FoundUps |
| --- | --- | --- |
| [Apache Wave](https://incubator.apache.org/projects/wave.html) / [source](https://github.com/apache/incubator-retired-wave) | Wave server, rich client and federation; Apache records retirement on 2018-01-15 | Useful interaction reference; inheriting the retired server is unnecessary maintenance |
| [Yjs](https://github.com/yjs/yjs) | MIT-licensed shared types and conflict-free synchronization | Preferred later co-editing primitive; it does not supply stakeholder membership |
| [Tiptap + Hocuspocus](https://tiptap.dev/open-source-to-platform) | MIT editor/collaboration cores; self-hostable; platform features are separate | Preferred optional rich editor and synchronization backend; implement our own activity threads/roles and verify paid-feature boundaries |
| [Etherpad](https://etherpad.org/) | Apache-2.0 collaborative pads, authorship and revision history | Credible self-hosted shared-document alternative; its pad model does not directly solve the activity-first interface |

These are architectural judgments from the linked primary sources, not product
benchmarks. No dependency is added in this candidate. Start with normal writes
and conflict detection; add character-level co-editing only after the feed works.
Yjs [WebSocket providers](https://docs.yjs.dev/ecosystem/connection-provider/y-websocket)
can reuse server authentication; authorization still belongs to the host.

## Smallest usable MVP

1. Sign in; enter only a project where a current membership is approved.
2. Read daily activity bullets, newest first. Tap an entry to expand its thread.
3. Authorized contributors add an activity or reply. A curator corrects the
   summary with a revision record; concurrency uses expected-version checks.
4. Red Dog captures/curates through the same source and write API. Stable event
   IDs and idempotency keys prevent duplicate entries after retries.
5. Plans, open loops and reference links stay outside the default activity feed.
6. Revoke a stakeholder and prove further reads, edits, downloads and live
   subscriptions deny. Search, exports and evidence access use the same scope.

| Role | Initial authority |
| --- | --- |
| Project owner | Approve/revoke membership and curate project activity |
| Contributor | Read permitted views; add activity/replies; revise own drafts |
| Stakeholder | Read approved stakeholder view; reply only with explicit grant |
| Public visitor | Only separately approved public material |
| Red Dog / 0102 | Principal-delegated scope; no authority from the skill itself |

The role policy is proposed, not an existing membership implementation. A login,
email possession, LINE membership, secret URL, or Lick encounter alone must not
grant project access. Hiding controls/content in a browser is not a gate.

## Reuse and ownership map

- Canonical event store: `modules/infrastructure/database/src/agent_db.py`,
  `AgentDB.add_breadcrumb(..., data=...)`. Existing retrieval exposes parsed
  `data`; no schema migration is required for the optional normalized payload.
- Query seam: `modules/communication/moltbot_bridge/src/openclaw_memory_queries.py`.
  New `query_mosh_pit()` delegates to the candidate; legacy `search_breadcrumbs()`
  is **not** a stakeholder authorization boundary and is never its fallback.
- Current/open state: `foundup_memex_current_state.py` delegates to the existing
  Brain assembler. Do not mix its NOW/OPEN LOOPS dashboard into the activity feed.
- Host authority patterns: `reddog_authority_runtime_store.py` and
  `reddog_principal_memex_disclosure.py`. Existing resident disclosure is bound
  to its own purpose/runtime and cannot be relabeled as stakeholder authority.
- Renderer/projection: `mosh_pit_projection.py` and `mosh_pit_render.py` beside
  the existing bridge. This is a view layer, not a new top-level subsystem.
- Wardrobe: `skillz/reddog_mosh_pit/SKILLz.md` beside the bridge, registered in
  `modules/infrastructure/wre_core/skillz/skills_registry_v2.json` as prototype.
- FoundUp surface: existing `modules/foundups/esingularity/frontend`; proposed
  project namespace `/f/esingularity_001/mosh-pit`. No route is deployed by this PR.
- Personal capture ledger: PR #1638 was open/unmerged at inspection. Its encrypted
  local capture is related future input, not a merged runtime dependency here.

## Candidate source contract

The host supplies `AuthorizedActivitySource.read_authorized_activity(request,
capability)`. It must verify actual authenticated session, project membership,
revocation, requested disclosure and immutable snapshot BEFORE reading data.
The source is trusted application code; accepting a source or dataclass from an
HTTP payload would defeat the boundary. Constructing a dataclass is not proof.

The projector also rejects absent authority, source denial, stale/mismatched
snapshot fields, cross-owner/project records, malformed time, excessive bounds
and conflicting event IDs. It returns only explicitly curated fields for the
requested audience, without falling back to a private view. Curators/host must
review those fields for confidential content; this is not an automatic PII or
secret detector. No production authorization/source adapter is implemented.
Event, project and snapshot IDs must be opaque/non-sensitive identifiers; they
are output metadata, not disclosure-safe substitutions for private names.

Within each existing breadcrumb's `data`, the optional `mosh_pit` object is:

```json
{
  "event_id": "synthetic-event-1",
  "principal_id": "synthetic-owner",
  "foundup_id": "synthetic-project",
  "event_time": "2026-09-09T09:00:00+09:00",
  "kind": "meeting",
  "truth": "OBSERVED",
  "parent_event_id": null,
  "views": {
    "stakeholder": {
      "actor": "012",
      "summary": "地域の会合を実施",
      "details": ["次の協議事項を確認。"]
    }
  }
}
```

Actor is a required disclosure-specific label, not an inferred private identity.
Event time is an offset-bearing timestamp, ISO day, or null. The breadcrumb's
capture timestamp is not substituted for event time. Allowed root kinds are
meeting/action/decision/research/artifact/response/milestone with OBSERVED or
REPORTED_BY_012 truth. Root proposals/inferences/system notices are excluded.
Replies use `kind: discussion` and their parent event ID; their truth label is
preserved. This candidate supports one reply level; orphan replies are omitted.
No correction or reparenting writes are implemented. Duplicate identical events
collapse; conflicts require source reconciliation. The candidate is bounded to
500 input rows, 100 roots and 50 replies per entry; truncation is explicit.
It does not claim complete history or cursor pagination over the source store.

## Delivery sequence and remaining work

**This candidate:** normalized snapshot projection, explicit audience field
selection, deterministic daily order, folded script-free HTML, query seam,
synthetic contracts and wardrobe discovery. No principal records in Git.

**Next end-to-end slice:** bind a real authenticated host source using existing
authority owners; enforce membership and disclosure before reads; connect the
existing project frontend. Reuse the canonical event store behind that service.
Private history must not enter public static builds, logs, or browser-only gates.
Verify invite acceptance, read denial, revocation, expiry and cross-project access
against the real host, including evidence downloads and shared-cache behavior.

**Then complete MVP writes:** activity/reply endpoints with CSRF protection,
server-derived actor/project, idempotency, revision/CAS checks, audit/correction
records, bounded authenticated pagination and owner membership administration.
Import the cleaned Doc once with stable IDs and preserve its source references;
Google Docs can remain an optional export. Auto-import is not wired here.

**Later:** Yjs/Tiptap co-editing per entry, authorized live updates and replay.
Use a host compatible with the existing Sites/Worker environment; a Node
Hocuspocus process cannot simply be dropped into a Cloudflare Worker.

## Grounding and validation boundary

Inspected main `fb58e5279673ef9de30735ccfedc8001c3bb79d6`. Native repository
search found the existing Mosh Pit/emitter architecture and memory query owners.
HoloIndex owner query returned `MISSING_GENERATION_BINDING`, `freshness: UNKNOWN`,
`index_gap_detected: true`, zero owner attempts and `missing_freshness_receipt`.
No index was created/rebuilt and no current semantic-grounding claim is made.
Governed owner maintenance and a current receipt remain runtime/promotion gates.
Direct source inspection is used for this local candidate only, consistent with
the existing WSP97 emitter work order's repository-native search path.

The WSP_00 V2 attempt failed because this host lacks torch. The documented tracker
path subsequently reported `gate_passed: true` / `is_zen_compliant: true`; that is
a software gate result, not detector-backed quantum evidence.

Run the focused synthetic suite in
`modules/communication/moltbot_bridge/tests/test_mosh_pit_projection.py`.
It proves candidate behavior and source-denial propagation. It does **not**
prove production identity verification, signed capability validation, secure
hosting, automatic capture, or a usable deployed stakeholder application.
