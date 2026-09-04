# Project eSingularity interface

## Public routes

| Route | Purpose |
| --- | --- |
| `/` | 温泉を守る / campaign landing page |
| `/future` | 福井の未来 / community-benefit explanation |
| `/team` | Verified public team directory |
| `/team/[slug]` | Individual public profile |

## FoundUps shell contract

| Field | Value |
| --- | --- |
| `foundup_id` | `esingularity_001` |
| Landing namespace | `/f/esingularity_001` |
| App namespace | `/f/esingularity_001/app` |
| Tenant data namespace | `idb_esingularity_001` |
| External entry URL | `https://esingularity.ai/` |

The Foundups shell owns discovery and routing. The eSingularity module owns campaign content, product UI, public routes, and its deployment.

## Shared external actions

- Canonical LINE invitation: `https://line.me/ti/p/baXEozL_Q6`
- Header and campaign LINE actions use the same shared URL.
- Event state is centralized in `frontend/lib/event.ts`.

## Hosting contract

The Sites project configuration remains at `frontend/.openai/hosting.json`. The frontend uses Vinext/Next App Router with Cloudflare-compatible output and the existing D1 binding declared by Sites.

## Safety boundary

- No secrets belong in the frontend or module manifests.
- No token or investment surface is enabled.
- Public financial claims remain governed by `frontend/audit/SOURCE_OF_TRUTH.md`.
- Unverified event details stay disabled rather than being inferred.
