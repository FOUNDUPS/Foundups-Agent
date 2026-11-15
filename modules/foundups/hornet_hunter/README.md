# Hornet Hunter — public website source handoff

Public site: https://hornethunter.com/  
LinkedIn company: https://www.linkedin.com/company/hornethunters/  
Main LinkedIn profile: https://www.linkedin.com/in/openstartup/

This bounded source snapshot brings the Hornet Hunter website work into
Foundups-Agent without importing conversations, production correspondence,
private records or the unpublished paid manual. It follows the FoundUp-owned
website placement used by `modules/foundups/esingularity`.

**Authority:** the existing Sites-managed repository remains the live deployment
source. This directory is a dated, reviewed import, not a second deployment or an
automatic synchronization service. Source revision:
`c8d742c5479007fd4d4fb325f44c17b0ce53ccf9` (28 October 2026, version 16).
Reconcile newer live changes before editing or transferring this snapshot back.
Do not create another Sites project or change DNS as part of this handoff.

## Read order

1. [Public/private boundary](docs/PUBLIC_PRIVATE_BOUNDARY.md)
2. [Work completed and remaining](docs/HANDOFF.md)
3. [Build and publication contract](INTERFACE.md)
4. [Roadmap](ROADMAP.md) and [change log](ModLog.md)
5. [Validation](tests/README.md)

Verified social identity and unresolved numeric company ID: [LinkedIn identity](docs/LINKEDIN_IDENTITY.md).

## Local build

From this module directory:

```sh
python -B frontend/build.py
python -B -m unittest discover -s tests
```

The generator is self-contained standard-library Python. The image manifest
contains only already-published assets and SHA-256 digests. Photo bytes are not
duplicated in this public repository. To restore those exact assets for preview,
run `python -B frontend/restore_public_assets.py`; mismatched downloads fail.
Original unblurred photos must never be substituted for privacy-edited assets.

`frontend/dist/` HTML is regenerated and ignored. CSS and JavaScript remain
tracked in `frontend/dist/assets/` to preserve the existing generator contract.
The sanitized video data retains only fields used in public rendering.

No payment, booking confirmation, certification, email sender, Google Forms
backend, LinkedIn publishing or WRE runtime integration is created here.

## Repository retrieval limits

GitHub lexical searches and direct reads found no existing Hornet Hunter website
owner. The existing FoundUp website pattern was reused. Search results contained
unrelated YouTube moderation and FoundUps LinkedIn records; those are not Hornet
Hunter company-page identity evidence. HoloIndex/WRE/Qwen/Gemma runtimes and the
repository bootstrap were unavailable in this connector-only integration lane;
no semantic freshness, awakening compliance or agent-runtime acceptance is
claimed. This is a source handoff for normal repository validation, not an
activated autonomous agent.
