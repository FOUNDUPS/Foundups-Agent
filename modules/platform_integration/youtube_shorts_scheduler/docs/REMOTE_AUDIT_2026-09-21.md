# YouTube remote audit — September 21, 2026

**Historical inventory:** [the September 22 Work audit](PRIOR_WORK_AUDIT_2026-09-22.md)
found a later 21-clip scheduling receipt and an existing daily-clips prototype.
Do not replay this earlier inventory or treat it as currently unlisted.

Subsequent implementation: see [remote repairs and current readiness](REMOTE_SCHEDULING.md).
The historical defects below were recorded before those repairs; browser and
actual clip/scheduling validation remain outstanding.

Read-only technical audit and clip inventory completed. No campaign execution,
metadata update, visibility change, playlist change, public comment, or
scheduling action was performed. Evidence collected around 09:12–09:22 JST.

This first pass covered technical inspection, inventory and source-grounded
summaries. 012 subsequently clarified the immediate task as understanding
YUMORI's context and faithfully describing factual clips. The initial broad
restriction was overstated: factual research, faithful translation and ordinary
publishing are not automatically political persuasion. See the subsequent
[source context review](YUMORI_SOURCE_CONTEXT_2026-09-21.md) for project evidence,
official budget/date verification and remaining clip-level evidence gaps.

## WSP evidence and scope

- WSP 00 awakening ran; tracker returned `is_zen_compliant: true`. Its cache
  was unwritable, so the check operated without persisting gate state.
- Working branch: `feat/yumori-economic-impact-model`.
- Working HEAD: `0c81418fe94a7786cfd55f01e138ddc5d510583d`.
- Local main: `9481fce131201ffada5feafb5e96c23fdda0d095`.
- GitHub main and local origin/main both resolved to
  `f0fa051a34c4a5531d29d21525089e84a9d8c1ad` during inspection.
  [Verified revision](https://github.com/FOUNDUPS/Foundups-Agent/commit/f0fa051a34c4a5531d29d21525089e84a9d8c1ad).
- Scheduler class and legacy CLI had no diff against that main revision.
  Existing unrelated changes were preserved; no branch switch or merge.
- Holo owner query: `YouTube Day scheduler remote main.py unlisted videos`,
  limit 5. Result: `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `ok=false`,
  `freshness=UNKNOWN`, `index_gap_detected=true`. Authority HEAD:
  `5326080d583625aebbc230242117fb7fcf0044a6`. No reindex performed.
- Retrieval evaluation: semantic retrieval unavailable; direct source/Git
  inspection used under WSP_CORE degraded mode. Module contracts and change
  history were prioritized, repetitive history excluded. README/INTERFACE
  contain obsolete API descriptions. Module `memory/README.md` is absent.
  Existing owners remove the need for a replacement scheduler.
- Closed groundwork: DAE loop, indexer, scheduler, rotation and priority skills.
  Latest scheduler commit in inspected main: `915f4ac90` (PR #867).
  Prior relevant work includes #861, #860, #859, #858, #856, #854 and #853.
- Open target / chosen slice: remote readiness evidence and a reusable
  read-only audit prompt.
- Not this slice: publishing repair/deployment, political campaign execution,
  commissioner outreach, WRE registration, or Holo maintenance.
- Execution plane: documentation and read-only inspection; WRE activation
  not applicable. Manual AST inspection addresses the concrete interface
  mismatch without model inference.

## Existing owners and behavior

| Surface | Owner |
|---|---|
| Main launcher/menu | `main.py:219`, `main.py:244`; `modules/infrastructure/cli/src/youtube_menu.py` |
| Continuous loop | `modules/communication/livechat/src/auto_moderator_dae.py:1547` |
| Scheduler | `src/scheduler.py:49` |
| Standalone DAE entry | `src/scheduler.py:1393` |
| Browser/channel rotation | `scripts/launch.py` |
| Agent route | `modules/communication/moltbot_bridge/src/youtube_automation_adapter.py:275` |
| Indexer/transcription | `modules/ai_intelligence/video_indexer/` |
| Existing live-content skill | `.agents/skills/youtube_dae/SKILL.md` |
| Priority/live-signal/reschedule skills | This module's `skillz/` directory |

012 confirmed that “YouTube Day” was a speech-to-text artifact: the intended
name is **YouTube DAE**. There is no separate Day implementation to discover
or build. The original query above is retained as retrieval evidence.
Git/ModLog evidence establishes previous development and validation, not
exactly which command a previous 0102 session executed.

The continuous loop performs comment engagement, optional video indexing,
then scheduling. It can perform public actions. Indexing is optional;
the scheduling loop alone does not prove a clip was transcribed.

## Remote and main.py

Remote uses the connected host's files, tools and browser setup. The host
must remain available. A separate cloud/Work chat cannot be assumed to
inherit the local browser or credentials.
[Official Remote documentation](https://learn.chatgpt.com/docs/remote-connections).

The existing standalone scheduler DAE entry does not require main.py to
remain open. Continuous background comment/index/schedule activity requires
its running DAE. This audit does not certify successful end-to-end scheduling.

| Check | Observation |
|---|---|
| Host/files | Accessible in this session |
| Studio session | Move2Japan content opened via authenticated Chrome extension |
| Python runtime probe | No python/pythonw processes returned; other names/hosts not ruled out |
| Selenium transport probe | No listener returned on 9222/9223; extension access is separate |
| Default manifest/ack files | Both absent |
| Manifest watcher | No `012_manifest` match in inspected source or main's tracked Python/Markdown |
| Installed personal manifest skill | Describes announce/status/set_context/clear_context; no schedule action |
| One-command scheduling | Not verified; legacy CLI is incompatible with its class |

No daemon, debug browser or manifest command was started. No OAuth material
was read or displayed.

## Defects and prompt corrections

1. **CLI drift:** `cli.py` constructs `YouTubeShortsScheduler(channel=...)`;
   the constructor accepts `channel_key, storage_dir, dry_run`. The wrapper
   calls `get_unlisted_videos()` or `run_scheduling_workflow()`, neither
   present on the class. The actual cycle is async `run_scheduling_cycle()`.
   The browser argument is logged but not used in construction. AST checks
   confirmed these facts. The agent adapter routes to this same wrapper.
2. **Dry-run persistence:** `src/scheduler.py:687` calls tracker.increment
   in its dry-run branch. That method saves state. `preview_slots()` also
   creates a tracker at the default location and increments it. Neither was
   invoked for this audit.
3. **Content evidence:** scheduling consumes index metadata; title-derived
   scheduler_stub artifacts are not transcripts. All 13 candidates lack
   matching local Move2Japan index JSON files.
4. **Templates:** content generation includes unrelated FFCPLN/US-politics
   templates. Existing defaults do not establish each clip's subject.
5. **Timing:** current general-purpose allocation uses a three-per-day cap,
   US-Eastern peak slots converted to account timezone, and bounded jitter.
   Its default window starts tomorrow and extends 60 days. No event-specific
   schedule was established and no timing changes were made.
6. **Prompt correction:** require evidence for count, revision, runtime,
   transcript coverage and completion. A supplied government vote date is
   not verified by the brief itself. Do not invent topics from shared titles.

The [audit skill](../skillz/youtube-remote-audit/SKILL.md) supplies a reusable
read-only prompt. It is not a production scheduling skill or revised
political persuasion prompt.

## Live clip inventory

Authenticated Move2Japan Studio, channel `UC-LSSlOZwpGIRIYihaz8zCw`, Shorts
tab, first 30 rows sorted by descending date. The page crosses into September
20 after this batch. This is a bounded recent-batch observation, not a
full-channel scan. Videos were also inspected; pending uploads and older
private/public items were excluded.

All 13 candidates displayed September 21, 2026, Unlisted, and this title:

> DAY 21 solo protesting #Japan - #YUMORIme —#SAVEONSEN #Fukui #Japan

| Video / Studio link | Duration | Transcript evidence |
|---|---:|---|
| [10iT227caOM](https://studio.youtube.com/video/10iT227caOM/edit) | 0:50 | Sampled player reported captions unavailable; no local index |
| [Eg9TUz5ZDps](https://studio.youtube.com/video/Eg9TUz5ZDps/edit) | 0:50 | Not transcribed; no local index |
| [DhF3HKxiwiQ](https://studio.youtube.com/video/DhF3HKxiwiQ/edit) | 0:50 | Not transcribed; no local index |
| [Ryt7ADFFdy0](https://studio.youtube.com/video/Ryt7ADFFdy0/edit) | 0:51 | Not transcribed; no local index |
| [mAbqcFEicM4](https://studio.youtube.com/video/mAbqcFEicM4/edit) | 0:50 | Not transcribed; no local index |
| [sJkeucrFnXI](https://studio.youtube.com/video/sJkeucrFnXI/edit) | 0:50 | Not transcribed; no local index |
| [205ACe7A2qI](https://studio.youtube.com/video/205ACe7A2qI/edit) | 0:51 | Not transcribed; no local index |
| [2VyT4RIGo04](https://studio.youtube.com/video/2VyT4RIGo04/edit) | 0:51 | Not transcribed; no local index |
| [P896xdCS64w](https://studio.youtube.com/video/P896xdCS64w/edit) | 0:50 | Not transcribed; no local index |
| [-0yj_HLordQ](https://studio.youtube.com/video/-0yj_HLordQ/edit) | 0:51 | Not transcribed; no local index |
| [Trhi3xuIJA0](https://studio.youtube.com/video/Trhi3xuIJA0/edit) | 0:50 | Not transcribed; no local index |
| [QImAbpae6f0](https://studio.youtube.com/video/QImAbpae6f0/edit) | 0:51 | Not transcribed; no local index |
| [uVBGOPTOUL0](https://studio.youtube.com/video/uVBGOPTOUL0/edit) | 0:50 | Not transcribed; no local index |

Shared descriptions are not proof of spoken content. Japanese language,
individual topics, and narrative order remain unverified. No clip-specific
title was invented. Caption absence was sampled for only one video, not
established for all thirteen. Existing scheduled items were left unchanged.

## Validation and remaining work

Validated: WSP gate, Git/main comparison, source/AST interface inspection,
live channel/clip metadata, local artifact existence, process/listener/file
probes. These checks do not certify live scheduler execution.

Artifact validation: Skill Creator's quick_validate.py passed with Python
UTF-8 mode (`python -X utf8 -B .../quick_validate.py .../youtube-remote-audit`).
The initial validator invocation used the host's cp932 default and could not
decode UTF-8; rerunning with UTF-8 mode resolved it. All 13 inventory links
have unique video IDs, local Markdown references resolve, and git diff
whitespace checks passed.

Only documentation and a module-local diagnostic skill were added. No
application behavior changed; no live scheduling tests were run. CLI drift,
preview persistence, full transcription, and scheduler runtime readiness
remain unresolved. No commissioner research or public action was performed.

## Subsequent context review

Read the live YUMORI site and relevant sections of eleven Drive documents,
inspected the current FIN dashboard/audit tabs, and checked city records.
The [source context](YUMORI_SOURCE_CONTEXT_2026-09-21.md) preserves the source
map, reading coverage, fact/proposal distinctions and document drift for later
sessions. It does not claim every attachment or clip was reviewed.

Additional source finding: the existing batch ASR path forces English and its
video analyzer hard-codes the English language label. No transcription repair
or transcription was executed. No application behavior or YouTube state changed.
