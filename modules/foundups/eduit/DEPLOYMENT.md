# Story Time deployment

Final target: **https://storytime.eduit.org/**. App/codebase name: **Story Time**.
**Us Story Time** remains the YouTube channel name; preserve `eduit`,
`kids_episodes`, publisher `us_story_time` and `@Us_Story_Time`. Older hostnames
are superseded. DNS points this subdomain at Firebase; Firebase hosts the files.
This slice does not change the apex, aliases or FoundUps main hosting.

## Verified connections and current status

[Sanitized receipt](docs/DEPLOYMENT_RECEIPT_20261026.json) records before-state,
rollout and live verification. Check its final status before claiming HTTPS.
Source baseline: main `2c9c93ead` including PRs #2215/#2219; isolated branch
`agent/storytime-pwa-deploy-20261026`. No competing deployment PR was open.

- Authenticated Firebase project: `gen-lang-client-0061781628`.
- Dedicated created site: `storytime-eduit`; https://storytime-eduit.web.app/.
- Seven-day preview: https://storytime-eduit--storytime-poc-jomd07zq.web.app/.
- Module `.firebaserc` target `eduit-storytime` binds only that site.
- GoDaddy connector/API absent; existing authenticated Chrome session verified.
  Repository DNS provider is a scaffold, not a working mutation transport.
- Authoritative NS: `ns41.domaincontrol.com`, `ns42.domaincontrol.com`.
  Before-state: Story Time NXDOMAIN, no Story Time forwarding; zone 41 records,
  nine unrelated subdomain forwards, apex forwarding Not set up. Preserve them.

## Build, stage, publish

Reuse `requirements.txt`, Node, FFmpeg and system Cairo. Windows lacked Cairo;
this run used Ubuntu-24.04 WSL and venv
`/home/user/.local/share/storytime-build-venv`. No paid call or YouTube upload.

```powershell
node --test modules/foundups/eduit/tests/*.test.mjs
python -B -m unittest discover -s modules/foundups/eduit/tests -p "test_*.py"
node --test modules/communication/youtube_shorts/tests/kids_review.test.mjs
python -B modules/foundups/eduit/build_site.py --output-dir modules/foundups/eduit/build/eduit --pwa-origin https://storytime-eduit.web.app --pwa-origin https://storytime-eduit.firebaseapp.com --pwa-origin https://storytime-eduit--storytime-poc-jomd07zq.web.app
firebase target:apply hosting eduit-storytime storytime-eduit --project gen-lang-client-0061781628 --config modules/foundups/eduit/firebase.eduit.json
firebase hosting:channel:deploy storytime-poc --only eduit-storytime --project gen-lang-client-0061781628 --config modules/foundups/eduit/firebase.eduit.json --expires 7d
```

Output must be a new directory inside the module: Firebase rejects a public
directory outside the selected config's project directory. Binding must use the same `--config` as deploy:
a root-only binding was not found by this module config. Verify staging page,
game/media, headers, worker, installability and video ranges before live publish:

```powershell
firebase deploy --only hosting:eduit-storytime --project gen-lang-client-0061781628 --config modules/foundups/eduit/firebase.eduit.json
```

Deploy only this target. Historical `eduit`/`eduit-alias` targets have no cutover
authorization here. Do not deploy root functions/rules or `foundupscom`.

## DNS, HTTPS and rollback

Domain resource:
`projects/gen-lang-client-0061781628/sites/storytime-eduit/customDomains/storytime.eduit.org`.
Firebase returned CNAME `storytime` → `storytime-eduit.web.app`. Apply only current
provider-required records. Certificate DNS challenge TXT at
`_acme-challenge.storytime` may also be requested; obtain its current exact value
from Firebase. Record applied public DNS values in the receipt. No forwarding
is needed. Preserve unrelated MX/SPF/DKIM/DMARC and records.

Verify authoritative/public DNS, Firebase ownership/host/certificate states,
normal TLS, root redirect, /storytime/, /review/, /about/, media and range 206.
Never bypass a certificate warning. DNS success does not prove HTTPS readiness.

For later releases record this dedicated site's live release/version first;
rollback via Firebase release history or clone that prior version to live.
Never modify unrelated `foundupscom` baseline version `ff28e6dc9bc88a72`.
Initial before-state had no Story Time site/domain/records: undo only the new
`storytime` CNAME and exact challenge TXT added here, then detach this custom
domain. Preserve unrelated resources; retaining/disabling this site is safer
than deleting other resources.

## PWA and other-lane contracts

Root redirects to /storytime/; /about/ retains EDUIT introduction; /review/ mounts
Shorts-owned review assets. Existing scene/rig/engine/Shorts renderer are reused.
Provenance stays `rendered_unreviewed`; hosting does not promote editorial/audio
review. No public renderer, shell, provider credentials or agent backend.

Visible episode/review markers and /revision.json bind matching assets to a
16-hex revision under /revisions/<revision>/. Manifest scope /, start /storytime/,
actual 192/512 PNGs. Exact build allowlisted HTTPS origins may register the
worker; shared FoundUps origins cannot. Login, storage and SW scope do not carry
between origins. No /member/ worker copy or second Mall shell.

Only the fixed shell/game is cached. Video and ranges are network-only with an
honest offline message. Auth/APIs/queries/arbitrary routes/child records are not
cached. Offline game needs a successful first online install. Retain current
plus one prior owned shell; Update & restart requires an explicit click.
Install control only appears with a real browser prompt.

For later builds pass `--previous-build <last-deployed-build>` to retain one prior
immutable media revision (two total). Archive the deployed directory/receipt.
Older tabs eventually need explicit refresh; never substitute newer scene/media
at old immutable URLs. Creator Refresh latest reloads /review/ for its newest
paired revision.

[INTERFACE](INTERFACE.md) documents refs and mount/start/pause/resume/reset/dispose
and reference-only completion. Fixed return routes /about/ and /storytime/ accept
no arbitrary return URL. Future Mall return and Red Dog presentation use existing
owners; cross-origin messages require exact origin/source/payload validation.
No fake voice, auth, catalog, executable game payload or child analytics exists.

Changed files are recorded in the PR and ModLog: EDUIT page/controller, small
engine lifecycle adapter, PWA assets/build/config/docs/tests; Shorts review gets
naming/revision and whole-document refresh only. Editor/annotation engine,
renderer, uploader and scene ownership remain unchanged.

Retrieval evaluation: Holo failed `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`,
freshness UNKNOWN/index_gap true. Exact current owner docs were inspected,
narrowed and deduplicated; no reindex. README/INTERFACE/ROADMAP/ModLog present;
tests README/TestModLog and requirements missing, added here; optional memory
README absent. Semantic maintenance remains with admitted Holo/WRE/CI owner.
Qwen/Gemma Python dependency analysis was evaluated; authenticated hosting/DNS
and browser/JS behavior need direct provider/browser evidence. 0102 performed
this bounded work with parallel implementation and independent review agents.
