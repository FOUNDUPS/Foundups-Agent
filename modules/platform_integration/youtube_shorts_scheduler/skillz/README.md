# YouTube scheduling skill workflow

This is the routing contract for the existing WSP 95 skills. Compose these
owners in order; this document does not introduce a publisher, daemon, or
production qualification. Follow WSP 50 evidence checks, WSP 84 owner reuse,
WSP 22 change records, and WSP 97 source/host evidence boundaries.

## Ordered handoffs

| Stage | Existing owner | Input → output and next gate |
|---|---|---|
| 1. Inspect | [Remote audit](youtube-remote-audit/SKILL.md) | Channel, source revision and transport → read-only qualification; browser access does not qualify the native worker. |
| 2. Review coverage | [Scheduling priority](what_should_i_schedule/SKILLz.md) | Tracker snapshot and horizon → coverage deficit. Reconcile with live scheduled inventory before a write; stale tracker data is not capacity proof. |
| 3. Select batch | [Remote runbook](../docs/REMOTE_SCHEDULING.md) | Authorized channel, recording window and exact IDs → eligible unlisted batch. Preserve existing schedules and deduplicate by channel/video ID. |
| 4. Understand clip | Existing `video_indexer` / personal `index-youtube-training` skill | Exact video ID → matched retrieval-eligible Studio Ask/Gemini evidence or timestamped transcript. Failed, stub or title-only evidence cannot authorize new metadata. |
| 5. Prepare metadata | [Title enhancement](ffcpln_title_enhance/SKILLz.md), [classifier](gemma_content_type_classifier/SKILLz.md), `src/content_generator.py` | Evidence → grounded title/description and bounded M2M provenance. Music defaults require music evidence. Schedule-only preserves metadata. |
| 6. Allocate or rebalance | `src/schedule_tracker.py`, [plan](reschedule_plan/SKILLz.md) | Reconciled inventory and channel policy → collision-free proposed slots. Plan is read-only; unresolved IDs or ambiguous calendar dates block apply. |
| 7. Save | Existing scheduler CLI/adapter; [apply](reschedule_apply/SKILLz.md) only for moving scheduled videos | Authorized exact IDs/slots → attempted writes. Content-page Schedule/Save and detail-page Done then page Save have different persistence boundaries. |
| 8. Verify | Existing DOM readback and `src/schedule_dba.py` | Independently reopened channel/video/date/time/timezone → saved verification. Click success or a disappearing row is insufficient. |
| 9. Review outcomes | Existing PatternMemory outcome path | Verified operational receipt → operational feedback. Audience metrics and controlled policy promotion remain unimplemented. |

Pass the same channel ID, video ID, source/evidence reference, requested timezone,
full target date/time and metadata policy between stages. Keep private per-video
receipts outside public source control. A blocked stage must retain its reason
and resume point; never advance an attempted write to `saved_verified` without
readback. These are instruction-level handoffs, not a claim of an implemented
end-to-end orchestration engine.

## Scheduling policy and execution boundaries

Resolve policy from existing `peak_window.py` / `schedule_tracker.py` owners,
not hardcoded caps in individual skills. Move2Japan's requested cadence is every
two hours, 08:00–22:00 America/New_York (eight slots); other channels retain their
own defaults. Treat both date and time as timezone-aware, including DST and Japan
calendar rollover. Do not apply clock-only conversions where target dates are
ambiguous. Explicit lower limits still constrain the batch.

`reschedule_apply` requires its existing environment gate plus a connected live
driver. It moves already scheduled videos; it is not a public-video republisher.
The remote CLI supports exact selected IDs; automatic discovery of today's
uploads and continuous watching are not qualified. During an active user session,
use bounded scans and checkpoints described in the runbook. A resident loop needs
a verified service identity, revision, transport, interval, expiry and checkpoint.

## Low-view review handoff (proposed, not implemented)

Sorting by views supplies candidates only. Compare numeric views with publication
age, current relevance, restrictions, engaged views, retention and subscriber
outcomes before suggesting action. Give recent uploads time to collect evidence.
For public videos, propose a grounded metadata improvement, resurfacing, or a
meaningfully revised new cut; do not automatically toggle visibility, duplicate,
or repost removed content. The scheduled-video apply skill cannot perform this
recovery workflow. Capture baseline and follow-up metrics before claiming learning
or promoting a timing/title policy. No analytics collector or automatic recovery
job is installed by this workflow map.

## Existing source and status

Prior Work created `publish_daily_clips` on
`feat/move2japan-daily-clips-skill-20260921`; its source is not present here.
Retrieve it before extending discovery rather than creating a parallel publisher.
See the [prior Work audit](../docs/PRIOR_WORK_AUDIT_2026-09-22.md).

The enhancement, classifier, priority, planner and apply skills retain their
prototype status. Remote audit is a read-only module-local instruction artifact,
not WRE registration. Unit tests establish bounded source behavior; live receipts,
worker deployment and measured audience improvement require separate evidence.
