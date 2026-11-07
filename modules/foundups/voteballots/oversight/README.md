# Oversight Blueprint — a Vote workstream

Oversight is a civic research, preparation and review workstream of the existing
`voteballots` FoundUp. This is an `EXISTING_FOUNDUP_UPDATE`: it creates no separate
FoundUp identity, token, governance authority or agent runtime.

## Source and publication

`site/` preserves **all 155 tracked public source files** from the clean Oversight
Sites checkout at `c66d22afc5795874f4020661dcadfdd69d3ad129`. The import includes the
complete `dist/` tree, its `web/` copies, documents, research and review data,
instruction bundles, icons, and public `.openai/hosting.json` configuration.
Its first recorded source commit was
`a7bf6ab3f3685a0a905b04f5bc81fe4e4bab6081`.

The Vote module's `site/` directory is the canonical editable owner going forward.
The existing Sites repository remains the deployment mirror and retains the full
original Git history. The import does not replace or rewrite that history.

The owning publisher reported successful native Sites publication of version 5:

- Project: `appgprj_6aed5317a2e4819193b1fdfe340a1cea`
- Deployment: `appgdep_6aee654bd6308191a3f0bca480e9aad3`
- Published source: `c66d22afc5795874f4020661dcadfdd69d3ad129`
- Preferred workstream address: <https://oversight.mtrout.com/>
- Retained alias for the same workstream: <https://maga.mtrout.com/>
- Original Sites address: <https://oversight-hub-pwa.undaodu.chatgpt.site/>

The parent Vote informational landing uses <https://vote.mtrout.com/>.
These three `mtrout.com` addresses passed public DNS, strict TLS and HTTP 200
checks with their correct Vote/Oversight pages on both public endpoints on
7 November 2026 at 00:45 UTC. The previously configured `vote.foundups.com`
and `oversight.vote.foundups.com` aliases remain retained; they are not the
preferred public map. No existing alias or original Site is removed or
redirected by this documentation correction.

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

Retain both current aliases and the original Site. An additional Vote-branded
hostname may point at the same published project after its own hosting/DNS/TLS
verification; do not remove an existing alias merely because another is added.

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

1. Edit the canonical Vote-owned source in `site/`. Preserve every route,
   document/data/instruction asset, access boundary and root/`web/` mirror pair.
2. Run syntax, content, responsive and interaction checks appropriate to the
   change. Advance the public-shell cache version when shell assets change.
3. Open the **same** Sites project with the Sites skill's supported source
   helper. Inspect and reconcile any remote changes with the canonical Vote
   source **before copying into the mirror**; preserve unique work on both sides.
4. Synchronize only the reviewed public files into that reconciled checkout.
   Never copy `.git`, credentials or local state. Use the supported helper to
   validate, commit, push and package the exact mirror. Preserve `project_id`
   and the public audience; do not create a replacement project.
5. Save and deploy that pushed mirror commit through native Sites tools. Wait
   for the successful publication receipt before recording a new deployed state.
6. Then update the canonical inventory and source/release provenance to the
   actual mirror commit and deployment, and run snapshot verification with
   `--source-checkout` against that clean checkout. Keep historical snapshots
   and publication receipts in Git history; never relabel a failed check as a
   successful release. The current `c66d22af...` pin remains the import's history.
7. Verify DNS, valid HTTPS and actual page content separately. Maintain the
   aliases and original-source history unless an explicitly reviewed migration
   replaces them.

The manifest is a source-preservation receipt, not a secret store, runtime
authorization, proof that every declared feature operates, or a substitute for
the independent browser/domain checks of a release.
