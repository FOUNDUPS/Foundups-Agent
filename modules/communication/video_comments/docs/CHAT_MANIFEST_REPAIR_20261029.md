# Chat manifest and reply inspection — source checkpoint

Principal directive, 2026-10-29: “Update the chat manifest with …” is a spoken behavioral command through Red Dog to 0102. Preserve the command privately, let the agent read it, then prove changed reply behavior. Do not publish receipt notices or repeat the operator's text. Repair both theme use and comment-reply quality using existing Skillz.

## Source and retrieval boundary

Base: FOUNDUPS/Foundups-Agent main `8b345ec206212b1e27868bdc4cacd06474b636a6`. Current GitHub source, AGENTS, WSP00/97, module interfaces, historical test inventories and the RedDog operations contract were retrieved. This environment has a source mirror, not the principal's Windows checkout. HoloIndex/native services and signed runtime model-role receipts were not available. Retrieval was lexical and direct-file; no semantic freshness or runtime authority is asserted. Historical docs claiming production do not override actual source or missing deployment proof.

## Existing owners and voice routing

| Purpose | Owner |
|---|---|
| Spoken instruction | Personal skill `operate-youtube-chat-manifest`; Red Dog interfaces with 012, 0102 retrieves/reasons before execution |
| Trusted runtime inbox | `memory/012_manifest.json`, or `YT_012_MANIFEST_FILE` |
| Private command receipt | `memory/012_manifest_acknowledgements.json`, or `YT_012_MANIFEST_ACK_FILE` |
| Active theme | `memory/012_manifest_state.json`, or `YT_012_MANIFEST_STATE_FILE` |
| Queue and lifecycle | `modules/communication/livechat/src/operator_command_queue.py`, `auto_moderator_dae.py` |
| Stored-comment consumer | `modules/communication/video_comments/src/commenting_control_plane.py` |
| Reply meaning and prompt | Existing `comment_content_analyzer.py`, `reply_context.py`, `intelligent_reply_generator.py` |
| Review and browser posting | Existing `skillz/tars_like_heart_reply/src/comment_processor.py`, `reply_executor.py` |

Do not write an example command into GitHub's tracked memory directory and call it a live update. Resolve the actual authorized runtime and its overrides, atomically append a unique command while preserving queued work, then read that command's receipt. A command ID with an unknown outcome must not be retried under a new ID. Public `announce` and private `set_context` are different actions.

The default watcher polls every 60 seconds only while its DAE runs. The source change makes `set_context` silent even when livechat is selected. Existing gates, dry-run, TTL, lock, deferred availability and replay rules remain. Shared clear still does not clear the legacy commenting broadcast. Surface scope exists; channel-specific scope is not added by this patch and must not be inferred.

## Candidate behavior

1. Activate theme privately and record `context_activated=true`, `public_message_sent=false` in the matching queue receipt.
2. Carry the theme into the writing prompt with the original comment, video title and existing memory. Answer the actual comment first; use theme only when relevant. No raw theme suffix is added to published text.
3. Use a general-language model for writing and a separate evaluation call for relevance, coherence, grounding and non-disclosure of private instructions. Missing/malformed/low judgments block posting. Ratings are model judgments, not calibrated probabilities.
4. Keep model-role name filtering as a conservative safeguard, not a replacement for signed runtime/provider admission. UI-TARS remains a visual role. A separate call to the same model is not independent-provider verification.
5. Bind and recheck the original Studio row, verify exact entered text, submit once, then require new creator-text DOM readback. Capture a post screenshot; when vision is enabled require its check too. A click alone remains unknown. Halt the current session on uncertainty. Nested reply submission remains blocked pending its own identity/readback qualification.
6. Preserve theme command identity and review outcome in private telemetry; never claim theme adoption from mere command acceptance. Relevant observed wording plus the same command ID is stronger behavior evidence, but it is not proof of causal learning or retained RSI.

## Offline evidence

`PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s modules/communication/video_comments/tests -p test_chat_manifest_inspection.py -v`: **15 passed**. Actual source definitions execute with controlled model/browser collaborators; queue persistence uses temporary files and a stubbed lock. Parser checks pass for materialized Python files. No model service, native browser, Google account or public YouTube action was used.

The existing 53-case context selector's fixtures were adapted for the new boundaries. It and the 116 adjacent cases were not rerun because pytest is unavailable here. The source mirror is incomplete; full startup, package import effects and Windows behavior remain unqualified.

## Required closure before deployment or merge

- Independent exact-head review under the repository's existing signed work-order/model-role authority. Do not treat this document or the voice phrase as authority to bypass those gates.
- Complete the semantic comment-assessment/routing qualification: intent, question, stance and uncertainty must be judged from the actual text, rather than identity alone. This patch removes a demonstrated false agreement but does not establish a calibrated commenter-rating system.
- Run original/adjacent tests, add the new selection through the canonical WRE test-registry/CI owner, and verify hosted results. Preserve original assertions and exact-case inventory rules.
- Regenerate `scripts/reddog_backend_manifest.json` with its existing generator in a complete checkout, inspect the dependency/hash delta, refresh both digest pins and run the owning extension/runtime checks. Do not hand-edit a partial runtime manifest or publish stale hashes.
- Qualify Studio selectors against the authorized channel. The creator badge, row marker, exact text and unresponded-filter behavior need live receipts; disappearance is uncertainty, not delivery proof.
- Persist unresolved post attempts across process restarts through the existing engagement-history owner before automatic recovery. Current halt prevents retries inside one session; it does not certify restart-safe exactly-once delivery.
- Connect the existing authorized Work-to-native runtime route. No Windows host, model endpoint or running DAE was established in this session. Test a private theme, match receipt and active source ID, generate a bounded draft, then inspect an authorized actual reply. Do not create a public test comment solely to prove polling.
- Validate current role capability and model-output quality. Model-name families are necessary filtering here, not a provider admission receipt or a measured quality guarantee.

Keep the candidate draft-only until these gates have concrete receipts. Do not say the running agent changed behavior based on this checkpoint.
