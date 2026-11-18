# Independent code audit — member experience and research queue

Review date: November 7, 2026 (Asia/Tokyo). Scope: current `web/app.js`, `web/explore.js`, `web/topics.json`, `scripts/validate_research_queue.py`, `schemas/research-queue.schema.json` and `investigations/research-queue.json`. Reviewer was separate from authoring context but within the same collaborating AI system. No application files were edited.

## Concrete findings

### C01 — public-source URL contract is too weak

The queue schema enforces `https://` and generic URI syntax but accepts literal private/metadata addresses and embedded credentials. Reproduced with `validate_queue`: `https://127.0.0.1/private`, `https://169.254.169.254/`, and `https://user:secret@example.com/` all returned no errors. This is a planning demonstration, so no observed outbound fetch or credential exposure occurred; nevertheless its declared public-source boundary should reject these before future worker use. Reuse the existing `validate_evidence.public_url` predicate for each allowed source and add adversarial regression cases. That helper is a syntax/address gate, not DNS resolution or rebinding protection; any future fetcher still needs host resolution/redirect/size/time restrictions.

`explore.js`’s `sourceUrl` similarly allows any credential-free HTTPS address, including private hosts. These are navigation links, not server fetches. Current checked-in topic URLs are official public sources, but the renderer should enforce a public-source or approved-host policy rather than imply the predicate verifies public reachability.

### C02 — existing route test expectation is stale

The existing 24-test run returned 23 passes and one failure in `test_unknown_inherited_route_does_not_execute_object`, because it expects the retired heading `Expose corruption.`. The actual route guard uses both `Object.hasOwn` and a function check. Separate Node VM probes for `#__proto__`, `#constructor`, `#toString`, `#hasOwnProperty` and `#unknown` each rendered the new home heading `Prepare the team.` without exceptions. Update the test’s expected fallback content and retain these inherited-key adversarial inputs. Do not remove the own-property guard to make a stale assertion pass.

### C03 — release inputs incomplete during audit

At audit time, `data/document-reviews.json` did not yet exist and new `explore.js`, topic/queue JSON and member-guide chapters were not yet in `PUBLICATION_MANIFEST.json`. They are needed by the new routes and must be generated, explicitly allowlisted and built before publication. This is an in-progress release gate, not evidence that the final deployment is broken. Verify all topic target documents, review hashes, script load order and output paths against the final build.

### C04 — one data load failure disables both explorers

The shared `Promise.all` makes a missing review manifest disable the otherwise available topic explorer, and vice versa. Current failure messaging is honest and does not claim success. Independent data loading or per-route resources would improve availability; not a safety blocker if all final inputs are supplied and verified.

## Checks that passed

- `node --check` passed for both JavaScript files.
- Current queue validates; assignments, `human_release: true`, plain HTTP and JavaScript URI mutations fail validation.
- Every `web/topics.json` document path resolves to an existing repository source file.
- Dynamic topic text, ticket text, source titles, review scopes and hashes are inserted using `createElement` and `textContent`; no source JSON is inserted as HTML.
- Local document paths accept only fixed `docs/` or `templates/` Markdown names and reject traversal. The renderer maps chapter URLs and template URLs separately.
- Core route execution rejects inherited object keys and non-functions. The exploration hydrator uses an own-property guard.
- The board visibly describes read-only planning; schema restricts state to proposed, worker/reviewer to null and human release to false. It grants no leases, performs no model calls and does not publish findings.
- No opening survey, confidential intake form, live claim API or automatic state referral was introduced in the audited files.

## Limits

This was source review and local Node/Python testing, not browser interaction, final artifact inspection, network source authentication, penetration testing or professional legal review. Root owns final browser QA, publication-manifest refresh, digest binding and deployment verification. Public URL syntax is not evidence that cited content supports a claim.

## Resolution verification — November 7, 2026

The same independently tasked code auditor re-read the repairs: URL gate rejects private/credential/malformed-port inputs; inherited-route probes pass; resource loading is separated; all new inputs are allowlisted; 24 exact-byte review entries validate; 28 tests pass and 33 skills validate. No remaining code blocker was found in that scope. Browser results were not independently repeated by this auditor. Future server-side source retrieval still requires DNS/redirect controls; no such retrieval service is present.
