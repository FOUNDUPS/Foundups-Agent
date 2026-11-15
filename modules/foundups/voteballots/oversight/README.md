# Oversight Blueprint — a Vote workstream

> **Classification (2026-11-09):** Oversight is presently a **strategy, documentation and reference implementation workstream**, not an independent FoundUp. Its public domains are documentation/interactive reference surfaces, not evidence of a separate tenant, manifest, token, wallet or autonomous runtime. The existing Vote ownership is a source/workstream classification, not a claim that the Oversight strategy itself is a FoundUp.
>
> **Future option, not an approved build:** an interactive Oversight FoundUp could model the strategy as mobile-first, reusable Play FoundUps experiences rather than copying the heavy document site. Before creating a new manifest or tenant, WSP 97 must inspect the current strategy, routes and shared shell; WSP 109 must decide whether this is a genuine independent FoundUp or an extension of existing Vote/Voice capabilities. Preserve existing documentation, deep links, and provenance. No deployment or runtime promotion is implied.


Oversight is a **documented congressional oversight strategy and reference blueprint**, not a standalone FoundUp, civic-action app, investigative authority, or operating agent. Its public websites publish proposed procedures, model documents, maps, and research for people to review and adapt; they do not conduct investigations or authorize subpoenas. Hosting these documents as an interactive PWA does not turn the strategy into an executing system. The source is maintained within the existing `voteballots` workstream for organizational purposes only. This remains an `EXISTING_FOUNDUP_UPDATE`: it creates no separate FoundUp identity, token, governance authority or agent runtime. Vote and the proposed Voice product runtimes remain distinct from this reference material.

## Relationship to Vote and proposed Voice

Vote (`voteballots`) is the existing civic FoundUp and organizational umbrella for this Oversight **strategy/documentation** workstream. Voice is a **proposed separate FoundUp** for civic participation, designed to interoperate with Vote through governed Play FoundUps contracts. Oversight may provide reference material to either, but is not thereby a FoundUp, an internal Voice application, or a live cross-FoundUp integration.

A dedicated internal Voice/Oversight experience is an **unresolved possibility**, not an approved feature or architecture. Do not add a manifest, tenant, domain, route, agent authority or implementation on that basis. Preserve the existing documentation and reference-site behavior. This classification supersedes any implication in older landing plans that a Voice destination is already live.

## Phase One landing contract

This section owns the current MAGA/Oversight and Vote/Voice handoff. Read the
[release accounting](../docs/RELEASE_ACCOUNTING.md#2026-11-09-documentation-audit)
for dated observations and the [Vote roadmap](../ROADMAP.md#magaoversight-phase-one)
for sequencing. 012 scoped the 2026-11-09 slice to documentation.

### One application and its addresses

MAGA and Oversight are two names for the same public congressional accountability
application. Its preferred address is [oversight.mtrout.com](https://oversight.mtrout.com/).
[maga.mtrout.com](https://maga.mtrout.com/),
[oversight.vote.foundups.com](https://oversight.vote.foundups.com/) and the
[original Sites address](https://oversight-hub-pwa.undaodu.chatgpt.site/) serve the
same release directly. The proposed `oversight.voice.foundups.com` should reach
that same application after DNS, TLS, routing and deep-link verification. The
operator also mentioned `oversight.voice.mtrout.com` as a possible spelling.
Both Voice-branded Oversight names returned NXDOMAIN in this audit. Any future
alias or redirect uses the existing Sites project or an approved forwarding
mechanism and preserves every working alias, the original Sites address, path,
query and fragment behavior. Each browser origin has its own PWA state.

**Vote** is the existing informational civic Site. `vote.mtrout.com`,
`vote.foundups.com` and its original Sites address serve that separate public
surface under the same FoundUp identity. **Voice** is the planned public
stakeholder participation surface. 012's spoken direction names
`https://voice.houseoutis.com/` as the landing's outbound destination. The
copied prompt instead calls the first entry Vote and names `vote.foundups.com`.
For the handoff, use the more specific spoken direction and keep Vote available
in its existing role. Reopen the decision with 012 before substituting Vote for
Voice. The Voice destination returned NXDOMAIN, so a live Voice link is gated
on verifying that destination. The proposed `#SchumerOut` campaign copy is a
separate editorial decision. The entry label in this contract is **Voice**.

### Four-entry landing

The first screen gives a short purpose statement and four prominent entries in
the order below. The future change edits the existing `public/overview.html`
and shared presentation assets where needed. Use a single responsive landing,
with large labeled touch targets on phones and conventional keyboard-accessible
navigation on desktop. Place detailed materials behind these entries or below
the first screen. Keep the existing staff and public links discoverable.

| Order | Entry | Destination | Purpose |
|---|---|---|---|
| 01 | **Voice** | `https://voice.houseoutis.com/` | One outbound link after destination verification. The stakeholder PWA, messages to Congress, and participation flows are a later slice. |
| 02 | **House Rules** | [`/templates/appendix-a-house-rules`](https://oversight.mtrout.com/templates/appendix-a-house-rules) | Explain the current House authority and the proposed 120th Congress rule changes. Keep Senate procedure and federal statutes separately sourced. The [House readiness package](https://oversight.mtrout.com/11-house-first-pwa) remains the supporting entry. |
| 03 | **Team** | [`/templates/staffing-and-recruitment-plan`](https://oversight.mtrout.com/templates/staffing-and-recruitment-plan) | Connect staffing, counsel, investigators, forensic specialists and recruitment to the [hub charter](https://oversight.mtrout.com/templates/central-hub-charter) and [committee operating plan](https://oversight.mtrout.com/templates/committee-node-operating-plan). |
| 04 | **Execution** | [`/explore`](https://oversight.mtrout.com/explore) | Enter the existing maps for investigations, records requests and subpoenas, depositions, hearings, evidence review, congressional action and separately authorized state referrals. Keep the [five-stage roadmap](https://oversight.mtrout.com/legislative-roadmap) as the process underneath. |

The House Rules and Team entries explain how the **proposed** hub would reduce
duplicated work. Reuse the model charter and committee operating agreement to
show a shared intake and deconfliction process, a designated lead and liaison,
an evidence inventory, and approved custody, access and disclosure rules.
Staff should be able to tell which office owns each decision and when review is
required. Proposed House rule text requires adoption, and a House rule cannot
assign Senate powers, override statutory limits, or grant state enforcement
authority. Each chamber and receiving state office retains its own legal
authority. Sensitive evidence and official decisions belong in approved office
systems. [119th House rules resolution](https://www.govinfo.gov/content/pkg/BILLS-119hres5eh/html/BILLS-119hres5eh.htm) ·
[Senate rules](https://www.rules.senate.gov/rules-of-the-senate)

### Play FoundUps and release gates

The [external route contract](../../docs/PFMALL_EXTERNAL_FOUNDUP_ROUTE_CONTRACT.md#11-canonical-route-truth-summary-post-pr-655)
owns the separation between Play FoundUps shell discovery and the product's
experience. Oversight is a workstream of `voteballots`. Vote's public Sites
front door is external to the Mall shell. `/f/voteballots` and
`/f/voteballots/app` are the canonical route contract. An empty `entry_url`,
discoverable-only manifest and absent admitted catalog entry leave the tenant
launch gated. Public civic participation and the Mall's authenticated
stakeholder interior use separate authority and access checks.

For a future authorized landing implementation, retain the 155-file archive,
13 historical mirror pairs, the public allowlist, all existing routes and deep
links, the root and `/web/` worker scopes, the senator directory, both maps,
research and templates, metadata, and `/accountability.json`, `/llms.txt` and
`/map-data.json`. Recheck destination content and TLS, keyboard and touch
navigation, both PWA scopes, and phone and desktop layouts. Review the result
from public, House and Senate perspectives, with a separate verifier before
publication. Follow the existing release procedure below. Keep credentials and
confidential records out of both the reviewed stage and the publication log.
The landing, DNS or redirect changes and the Voice runtime each require their
own authorized slice and live readback.

## Source and publication

The current standalone accountability site is owned by `public/` and
assembled by `scripts/build_public_release.py` into a new staging directory.
The builder verifies the immutable archive, then publishes an explicit list
of reviewed staff documents, source indexes and app assets. Original archive
bytes and paths remain preserved in the repository. Exploratory records,
workspace branding and internal execution materials are archival only.
The root and `/web/` retain their existing install scopes.

The diagram on the landing opens `/explore`. The authority and investigation
maps share the five-stage roadmap, evidence review, templates and decision
gates. Boxes and connectors have separate fragment links, with a parent path,
Back one level and Full map on each screen. The map works with static HTML and
CSS. JavaScript moves focus on navigation. `/map-data.json` exposes the same
reviewed records and trust boundary.

The four `public/map-*.json` source files supply nodes and connecting gates.
Each node has a title, summary, parent, and optional fact, link and choice
pairs. The builder checks parent paths, choice reachability and public link
schemes. Fictional money links include clearly marked sample exhibits and
counterevidence. Review changes in the staged HTML and machine index together.
The public explorer handles only reviewed educational material. Confidential
records and actual authority decisions belong in approved office systems.

The staff roadmap at `/legislative-roadmap` documents how to scope an inquiry,
approve evidence collection, review findings and take legislative action if
DOJ does not act. It links to the existing model documents. The state referral
branch requires its own jurisdiction and disclosure decision. `/contact`
reuses the official congressional roster and provides state selection, optional
on-device state suggestion, native senator dial links and a private voicemail
draft. The cached roadmap and manual lookup work offline after initial loading.
Current deployment and verification are tracked in the release accounting and
its linked PR, separate from the historical import below.

`site/` preserves **all 155 tracked public source files** from the clean Oversight
Sites checkout at `c66d22afc5795874f4020661dcadfdd69d3ad129`. The import includes the
complete `dist/` tree, its `web/` copies, documents, research and review data,
instruction bundles, icons, and public `.openai/hosting.json` configuration.
Its first recorded source commit was
`a7bf6ab3f3685a0a905b04f5bc81fe4e4bab6081`.

The import designated `site/` as the Vote-owned source. It is now the pinned
historical base for the public overlay. The existing Sites repository remains
the deployment mirror and retains the full original Git history.

The owning publisher reported the following native Sites publication for the
historical version 5 import:

- Project: `appgprj_6aed5317a2e4819193b1fdfe340a1cea`
- Deployment: `appgdep_6aee654bd6308191a3f0bca480e9aad3`
- Published source: `c66d22afc5795874f4020661dcadfdd69d3ad129`

The roadmap inside the preserved snapshot describes the earlier owner-private
release stage and remains a dated planning record.

Per-file source/export mappings, Git blob identities, byte counts and SHA-256
digests are in [source-snapshot.json](source-snapshot.json). The imported bytes
are unchanged. The clean Windows checkout represents 144 text files with CRLF
where the original Git blobs use LF; the manifest records both identities and
confirms no other content difference. The local `.gitattributes` disables
newline conversion only for
`site/**`, and `.gitignore` explicitly allowlists only the 155 reviewed public
files and their parent directories despite the repository-wide `dist/` ignore.
Future files stay ignored until reviewed and listed. The verifier rejects private
credential paths, environment files and key-store/certificate file extensions.
No credentials, Git metadata, local helpers,
runtime state or build archives are included.

## Identity, routes and PWA boundary

Vote keeps its existing identity and shell contract:

- `foundup_id`: `voteballots`
- Canonical landing: `/f/voteballots`
- Canonical tenant app root: `/f/voteballots/app`
- Data namespace: `idb_voteballots`

The currently published Oversight PWA runs on a separate origin. A brand link or
custom-domain alias does not establish a shared Mall session, storage namespace,
service worker or installed PWA. This import does not claim a shell runtime
integration. A future in-scope mount must preserve the existing Vote namespace
and bound any worker/cache to its approved app subtree.

Use the [address contract above](#one-application-and-its-addresses) for any
later domain work.

## Instruction bundles and truth boundaries

The copied `SKILL.md` files and their supporting schemas/scripts are authored
research and review instruction content. Preserving or publishing them does not
admit them into WRE, enable OpenClaw/Hermes, or prove that any agent is running.
Runtime admission and execution require their existing independent controls.

Keep the source's prototype labels, no-government-affiliation statement, lawful
authority distinctions, evidence qualifications and human-review requirements.
This workstream runs no official investigation or confidential tip intake. It
does not activate Vote's live FEC adapter, ballots, payments or governance.

## Verify and release

From the repository root, verify the preserved inventory without network access:

```text
python -B modules/foundups/voteballots/oversight/scripts/verify_snapshot.py
```

To also compare against the retained original checkout, pass its local path with
`--source-checkout`. The script requires its HEAD to equal the recorded snapshot
commit, confirms the tracked-file inventory, checks each recorded blob ID and
file mode against the actual HEAD tree, and compares every source/export byte.
Without that checkout, it still derives each recorded Git blob ID from the
export's exact bytes or its documented CRLF-to-LF representation; file modes can
only be format-checked until the original Git tree is supplied.
It prints only file/count/hash diagnostics, never file contents or credentials.

For a subsequent change:

1. Edit `public/` or the reviewed document projection and run
   `python -B modules/foundups/voteballots/oversight/scripts/build_public_release.py --output NEW_DIRECTORY`.
   Preserve the historical `site/` snapshot and existing public professional
   URLs. Review the whole allowlist, including root/`web/` entry paths.
2. Run syntax, content, responsive and interaction checks appropriate to the
   change. Advance the public-shell cache version when shell assets change.
3. Open the **same** Sites project with the Sites skill's supported source
   helper. Inspect and reconcile any remote changes with the canonical Vote
   source **before copying into the mirror**; preserve unique work on both sides.
4. Synchronize only the reviewed public files into that reconciled checkout.
   Remove retired public paths from the mirror after comparing the exact stage
   inventory. A hidden link alone leaves its target publicly retrievable.
   Never copy `.git`, credentials or local state. Use the supported helper to
   validate, commit, push and package the exact mirror. Preserve `project_id`
   and the public audience; do not create a replacement project.
5. Save and deploy that pushed mirror commit through native Sites tools. Wait
   for the successful publication receipt before recording a new deployed state.
6. Record the actual staged inventory, mirror commit and deployment separately
   from the original pin. The `--source-checkout` option requires a clean
   checkout of the historical `c66d22af...` source. After the deployment mirror
   advances, use the verifier without that option or a separate checkout at
   the original commit.
7. Verify DNS, valid HTTPS and actual page content separately. Maintain the
   aliases and original-source history unless an explicitly reviewed migration
   replaces them.

The manifest is a source-preservation receipt, not a secret store, runtime
authorization, proof that every declared feature operates, or a substitute for
the independent browser/domain checks of a release.
