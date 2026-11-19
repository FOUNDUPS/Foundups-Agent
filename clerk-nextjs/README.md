This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Residual PR #1762 qualification — 2026-11-19

Reconciled the original lint-tooling proposal onto main `908b47b369bb`:
`eslint-config-next` and `@next/eslint-plugin-next` now resolve to 16.3.4,
and fastq to 1.20.3. Next 16.4.6, sharp 0.35.5, js-yaml 4.3.2 and all
unrelated lockfile entries are preserved. The home header uses `next/link`
to resolve the previously recorded lint error without changing authentication.

On Node 24.22.1, strict `npm ci --ignore-scripts --strict-peer-deps
--include=dev --include=optional --no-audit --no-fund`, dependency constraint
checks, TypeScript and lint pass. Lint retains one unused StatCard warning.
A separate npm audit reports zero vulnerabilities for this lockfile as of this
observation; that is not a general security or deployed-runtime certification.

The production build compiles and typechecks, then still fails prerendering
`/` with `Missing publishableKey`. A deployment-owner-provided Clerk
configuration and a fresh successful build remain required. Qualification
excluded private environment files and provider credentials and disabled
keyless provisioning. No placeholder key, authentication bypass or lint-rule
exception was introduced. The earlier October observations below remain dated
history. Draft/merge hold, independent final review, hosted checks, deployment
and alert-closure verification remain separate gates.

## Dependency qualification — 2026-10-23

PR #1457 reconciles the original proposal with Next 16.4.1 and preserves its
20 GNU/musl selectors. Current PostCSS 8.5.23 and unrelated dependency versions
remain unchanged; #1762 retains its separate ESLint and project scope.

Qualification used Node 24.22.1/npm 11.6.2 in one disposable copy, with host
credentials and dotenv excluded, keyless provisioning/telemetry disabled and
package scripts disabled during installation. Baseline and candidate passed
strict `npm ci --ignore-scripts --strict-peer-deps --include=dev --include=optional
--no-audit --no-fund`, dependency-tree validation and `tsc --noEmit`.
Independent replay also passed the existing route/middleware/member-boundary
probes and all 20 platform-selector positive/opposite-libc checks.

Both `npm run lint` executions retain the same existing layout anchor/Link
error and unused StatCard warning. Both ordinary `npm run build` executions
compile and typecheck, then fail prerendering `/` with `Missing publishableKey`.
A successful production build requires the deployment owner's valid Clerk
configuration; no fake key, auth bypass or source substitution was used.
These unchanged limitations remain open, not passing acceptance results.

Linux x64/arm64 GNU/musl dry-runs verify package selection only. Actual Linux
native execution, live Clerk sessions, deployment and native RSI are unproved.
See the [existing backlog audit](../docs/audits/architecture/OPEN_PR_BACKLOG_DISPOSITION_AUDIT_PHASE1.md)
for exact source, retained requirements and the next action.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
