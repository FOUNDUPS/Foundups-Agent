# SoftProto live co-design and responsive preview extension

Date: 2026-11-14 UTC / 2026-11-15 JST
Status: proposed bounded extension; documentation only, not a deployed editor
Evidence baseline: main `0be2ae582020eab66b3aa8a1ab2deef802bebfeb`

## Preserved 012 intent

012 calls this "soft Proto": talk with 0102 while watching and interacting with
an evolving design, then switch desktop, tablet, mobile and full-browser views.
The interface should be reusable for any FoundUp, not hardcoded to 012 or one
publication. Preserve the work in the FoundUps development cycle. The reference
is an attached Substack preview photo (Library `libfile_ca5bec8653688191b43862c288efbca3`).
This audit received its metadata/caption, not inspectable image pixels. These
requirements come from 012's words; no pixel-fidelity finding is claimed.
The spoken "bill/build" domain is unresolved. No hostname, DNS or new public
route is selected by this document. Existing `/member/` is an integration
candidate, not a verified deployment destination.

## Reuse and ownership decision

Extend [SoftProto foundation](SOFTPROTO_FOUNDATION_ARCHITECTURE_2026-04-01.md)
and its [rollout](SOFTPROTO_ROLLOUT_PLAN_2026-04-01.md), not a parallel builder.
The existing decision is a Svelte/custom-element spike coexisting with the
static `public/member/` shell. This note does not claim that spike shipped.

| Concern | Existing owner / boundary |
|---|---|
| Editable UI schema, registry, preferences | SoftProto foundation and contracts in this directory |
| AI and direct-manipulation commands | [Shared command paths](SOFTPROTO_COMMAND_PATH_AND_PROTECTED_MODULE_CONTRACT.md); user editing takes precedence over AI commands |
| Escape, reset, protected modules | [Interior guardrails](SOFTPROTO_FOUNDUP_INTERIOR_GUARDRAIL_CONTRACT.md); preserve Mall navigation |
| Responsive/accessibility design | [WSP 102](../../../WSP_framework/src/WSP_102_FoundUps_Web_Design_Protocol.md) |
| Task admission, claims, execution, review, activation | Existing WRE/AgentDB path, not a new scheduler in the UI |
| Agent activity visualization | Audit `public/js/foundup-cube.js` and current Tertia work before changes; the inspected cube is a deterministic lifecycle animation with simulator integration, not proof of live workers |
| Reusable review procedure | Existing [interactive experience review](../eduit/skillz/interactive_experience_review/SKILLz.md), currently prototype; keep product-specific evidence in its owner |
| Skill placement / promotion | [WSP 95](../../../WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md), not a product skill embedded in WSP 97 |
| Completion / RSI claims | WSP 97 exact-revision acceptance; WSP 48 requires measured later reuse |

WSP 00 remains unchanged: it already supplies bootstrap, retrieval, role and
lifecycle obligations. A product co-design feature belongs here, with execution
following WSP 97, not in the identity/bootstrap protocol.

## Smallest implementation packet

First prove a **read-only responsive preview surface** for one existing admitted
FoundUp. Do not rewrite the Mall, create a new chat backend, or activate WRE.

1. Select one source-bound candidate artifact using the existing task/PR record.
2. Embed its actual rendered candidate in an isolated preview context. Desktop,
   tablet and mobile presets change the content viewport (CSS layout width), not
   merely scale a screenshot. Full-browser view opens the same revision.
3. Keep conversation/task status adjacent to the preview through the existing
   concierge/session integration. An absent transport must show unavailable,
   not a fake transcript or simulated agent activity.
4. Bind feedback to FoundUp ID, candidate revision, viewport, target command path
   and existing task ID. A click/annotation can propose a patch; it is not a
   publish instruction. Reuse existing work records instead of another queue.
5. Only after this packet is independently accepted, add shared AI/UI command
   edits, collaboration recovery and launch integration in separate packets.

Configurable inputs: FoundUp identity, admitted artifact reference, revision,
viewport presets, allowed origin and session/task references. Do not store
account credentials in preview manifests. Never put arbitrary untrusted URLs
into a privileged same-origin editor; enforce the host's origin/CSP policy and
explicit message origins. Blocked embedding stays blocked or opens the approved
candidate separately; do not disable browser protections.

## Collaboration and truth contract

- Show candidate revision and evidence timestamp; distinguish draft, rendering,
  preview-ready, stale, failed, reviewed and published. Preview-ready is not live.
- Keep viewport and preview navigation state separate from persisted app layout.
  Switching devices must not silently save edits, reload a draft into production,
  reset the conversation or steal focus from an active form.
- Bind mutations to expected revision and actor. Reject stale writes rather than
  overwrite a newer user edit. Queue AI commands during a user drag as the
  existing command contract requires; preserve escape/cancel/reset routes.
- Reconnect fetches authoritative current state. Replay/deduplicate only the
  affected command IDs; do not replay a publish operation on reconnection.
- A watcher/3D block is a projection of authenticated job/claim/result evidence.
  Distinguish queued, claimed, running, failed, cancelled and verified. No timer
  animation may be labeled a real swarm heartbeat or successful execution.
- Preview hosting follows WSP 71 build/security and WSP 91 bounded lifecycle:
  owner, deadline or lease, heartbeat, stop and descendant cleanup. No detached
  preview service was started for this documentation packet.
- Public launch remains a separate authorized action with exact source, checks,
  independent review, deployment receipt and live verification.

## Frozen acceptance for the next implementation packet

| Case | Required observable result |
|---|---|
| Device presets | Rendered CSS viewport matches configured dimensions; media-query layout changes; labels accessible and keyboard operable |
| Same candidate | Every preset and full-browser view identify the same source revision |
| Repeated switches | No lost form/annotation state, duplicate listeners or background previews |
| Interrupted work | Cancel, Escape, Back/Forward, hidden tab, offline/reconnect and failed embed retain safe recovery |
| Concurrent change | A newer revision is visibly stale until explicitly reselected; older feedback cannot overwrite it |
| Access boundary | Wrong origin, unauthorized candidate and malformed messages are rejected |
| Agent status | Real events or explicit unavailable state; no invented workers |
| Cleanup | Preview close/cancel stops owned resources without killing unrelated processes |
| Verification | Focused automated tests plus actual Chrome rendering; native phone/tablet QA recorded separately from viewport emulation |

A source-string assertion is not visual QA. A passing test is not proof of
publication, persistent runtime or RSI transfer. Preserve unknown device gates.

## Handoff, priority and audit receipt

012's sequencing remains: preserve/integrate branch work, qualify RSI/WRE, then
front-facing improvements. This documentation preserves the design now without
contending with Tertia's active lifecycle/runtime/observability lanes. Before
implementation, reconcile current lane owner, exact head and claimed files;
route one preview packet through existing task admission. Do not assume a shared
0102 identity is a shared write lease or claim Tertia has received this note.

Native WSP 00 awakening and strict tracker passed during this audit. Initial
Holo owner query failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; lexical fallback
is explicitly UNKNOWN freshness/index gap, not semantic-current evidence.
Direct reads at the recorded main revision grounded this note. Primary checkout
was dirty and preserved; this packet uses an isolated docs worktree. No runtime,
UI, permission, schema, DNS, public publishing or WSP 00 behavior changed.

Carry-forward: reconcile existing SoftProto spike/current owners; materialize
and inspect the reference photo; select the first existing product and approve
its frozen preview acceptance. Repository merge and runtime acceptance remain
separate receipts.
