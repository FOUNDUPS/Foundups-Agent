# EDUIT / Us Story Time agent deployment runbook

2026-10-26 JST. Operator explicitly requested landing/game and domain correction.
Source owner: FOUNDUPS/Foundups-Agent; existing Firebase hosting architecture.
Do not create an unrelated hosted Sites project or a second FoundUp identity.

## Built, not deployed

- `public/eduit/`: responsive EDUIT landing and `storytime/` two-tap game.
- `scene.mjs` + copied shared vector rig: same scene for browser and movie.
- `engine.mjs`: deterministic wake/root/timeout/retry/practice state machine.
- Local-only state: no account, advertising, analytics, child profiles or storage.
- `build_site.py`: renders three five-second clips with existing Shorts owners,
  produces 15-second MP4 and provenance, packages complete static output.
- Video/illustration assets are original code-generated; no third-party music.
- 012 selected a fictional sole-survivor story: chamber/other characters vanish
  into compacted brown earth. No bodies or injury shown. Parent note discloses
  collapse. Missed game cue stops before impact. No claim everyone survives.

## Verified observations

- HTTP and HTTPS `eduit.org` both resolved to
  `https://www.patreon.com/profile/creators?u=195537551` on 2026-10-26 JST.
- Main FoundUps hosting config uses Firebase site `foundupscom`, `public/`.
- This session's GoDaddy plugin discovery returned no connection. 012 reports
  GoDaddy is connected through local Codex; that installation is not disproven.
- Repository `foundups-mcp-p1/servers/dns_ops/provider_godaddy.py` returns scaffold
  responses, not actual mutations. Do not treat its return as applied DNS.
- GoDaddy browser is at sign-in. No DNS or forwarding changed in this session.

## Build and verify on the connected host

Use current merged source, not an old or unrelated dirty checkout. Install the
existing `youtube_shorts/requirements-local-preview.txt`, FFmpeg and Node.

```
node --test modules/foundups/eduit/tests/storytime.test.mjs
python modules/foundups/eduit/build_site.py --output-dir build/eduit
```

Output must be a NEW directory. Inspect MP4, listen to audio and test both inputs,
retry, practice, keyboard and phone layout. Do not commit credentials or generated
video intermediates. The source poster is SVG; MP4 is created at build time.

## Concrete hosting targets (IDs must be observed, not invented)

| Domain | Firebase target | Result |
|---|---|---|
| eduit.org (+ www if owned) | eduit | EDUIT landing |
| ourstorytime.eduit.org | eduit-storytime | root redirects to /storytime/ game |
| eduit.foundups.com | eduit-alias | permanent redirect to https://eduit.org/ |

`firebase.eduit.json` is a separate opt-in config: it does not alter existing
FoundUps/eSingularity hosting. On the authenticated Firebase project, create or
reuse three verified Hosting sites, and map these targets using the existing
Firebase CLI. Its public paths are relative to this config directory and resolve
to repository `build/eduit`. Deploy only these targets with this config after
confirming project/site identity. Do not deploy root Firebase functions/rules.

## GoDaddy work through local Codex's connected tool

1. Read `eduit.org` and `foundups.com` records AND forwarding. Export a before
   snapshot without secrets. Confirm nameservers/actual DNS owner.
2. Provision hosting sites and attach intended domains; obtain exact provider
   verification TXT and A/CNAME records. Do not guess IP addresses or set a CNAME
   to a URL/path. DNS alone cannot implement a URL redirect.
3. Remove only EDUIT's observed Patreon forwarding after staging is working.
   Apply only provider-requested records for these three names. Preserve MX,
   SPF/DKIM/DMARC, unrelated subdomains and unrelated FoundUps records.
4. Follow existing DNS owner's approval/admission flow if required. A saved plan
   is not authority; never fabricate an approval receipt. User authorized this
   deployment, but runtime policy still needs its authentic binding.
5. Verify TLS and final HTTP destinations for all three domains; verify landing,
   playable assets, and video range requests. Record rollback values and results.

BLOCKED: authenticated local Codex GoDaddy capability and Firebase target binding
are unavailable in this workspace. No public deployment or domain cutover claimed.
The landing currently uses relative game links so preview works before DNS; once
TLS is verified, change its Story Time CTA to https://ourstorytime.eduit.org/.

## 012 experience and existing Moshpit ownership

012 opens a browser URL; no download, build, ZIP extraction or manual deployment
is part of the product flow. The connected deployment agent owns the commands
above and verifies the live result before reporting completion. A local preview
is not evidence of a public domain cutover.

EDUIT.org introduces Education Using Information Technology as the educational
FoundUp. Us Story Time opens directly to Little Shrew's game, video and the
existing YouTube channel link. Keep the proof of concept to this single story.

Future story discovery belongs in the existing `public/member/` Moshpit PWA,
using its shared catalog, category rows and product adapter filter contracts
(see `public/member/README.md` and `INTERFACE.md`). Do not create a second catalog
or independent PWA shell. Story/video filtering and automatic tile population
remain planned; the current standalone game does not claim that integration.

## Current entry design supersedes introduction-first landing

The [episode architecture](docs/EPISODE_MALL_ARCHITECTURE.md) specifies video
above game as EDUIT.org’s POC entry, with parent access to the catalog/about
page. Implement through existing Mall owners before claiming shared-PWA
integration. The current build/target files still package the earlier layout;
this documentation does not change deployed routes or DNS.


## Private Storytime review milestone — 2026-10-26

Sites project `appgprj_6adea1a229dc81918f412edb117f0ba9` hosts the creator preview.
The deployment copies `public/eduit`, mounts the existing Shorts editor assets at
`review/`, and includes the exact latest local MP4 and scene sources. Its root
opens `review/director.html`. This is private staging, not the EDUIT custom domain.

The director supports video playback, the shared two-tap game, scene scrubbing,
and normalized pointer marks with episode revision and timestamp. Notes are
local to the browser; copy the feedback record to 0102. There is no automatic
Red Dog ingestion, microphone capture, or child profile collection.

Observed browser checks: MP4 displays 15 seconds; a pointer stroke and note
survive reload and reopen; scene seeks to 10 seconds; the game accepts wake
then root actions. Audio perception and physical phone testing remain unverified.
Creative revisions stay on the working branch; milestone PRs collect changes
after review rather than requiring a PR for each preview.
