# Hasan Piker Coalition

HPC is an independent satirical FoundUp for discovering attributed political-media clips. The first collection is SchumerOUT, sourced from public Move2Japan Shorts. [Vote/Ballots](../voteballots/) is its civic parent in the FoundUp registry.

The PoC is a public projection of the existing Play FoundUps Mall. It uses the
shared grid, player, gestures and browsing state. On a phone, **Voice Your
Opinion** opens Vote's [Contact Congress](https://vote.mtrout.com/contact)
resource. The bottom microphone is for search dictation. Red Dog opens the
public HPC briefing. A fresh Home Screen install uses the HPC name and portrait.

- [Interface and source curation](INTERFACE.md)
- [Roadmap and release gates](ROADMAP.md)
- [WSP 109 intake](docs/intake/INTAKE_SOURCE.md)
- [Change history](ModLog.md)

## Route Namespace

`/f/hpc` is the canonical public landing. The shared Mall accepts the registered public projection at `/member/?foundup=hpc`.

## App Mount

The public video field mounts in p.fMALL. The WSP 104 `/f/hpc/app` path hands off to the existing member gate.

## AI Capability Hooks

The manifest's capability and agent-route lists are empty.

## DAEmon Outputs

The PoC is a browser view with no HPC DAEmon.

## Data / Telemetry Namespace

The manifest reserves `idb_hpc`. The browser stores tab-local scroll position through the Mall state owner.

## WSP References

WSP 91, WSP 97, WSP 102, WSP 104 and WSP 109 apply. The [FoundUp surface contract](../docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md) governs future hooks.
