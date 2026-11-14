# Complete module evidence map

Pinned main: `fb58e5279673ef9de30735ccfedc8001c3bb79d6`. See AUDIT.md for scope and readiness judgments.

This table inventories every tracked depth-two module group. Presence is not completion. A package initializer counts as source. Test detection covers `test_*.py`, `.test.ts`, `.test.tsx`, `.spec.ts`, and `.test.js`; alternate test conventions need owner review. Nested modules are aggregated under their parent. No test execution is implied outside the named WRE tier.

Memory gaps: R=README, I=INTERFACE, P=ROADMAP, M=ModLog, TR=tests/README, TM=tests/TestModLog. Requirements and memory/README presence are recorded separately in repository_inventory.json.

## ai_intelligence

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/ai_intelligence/0102_orchestrator` | module candidate | 10 | 8 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/agent_permissions` | module candidate | 4 | 2 | P,TR,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/ai_gateway` | module candidate | 87 | 51 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/ai_overseer` | module candidate | 57 | 32 | none | critical-path sample; see audit |
| `modules/ai_intelligence/audio_content_classifier` | module candidate | 4 | 2 | P | inventory only; runtime unassessed |
| `modules/ai_intelligence/banter_engine` | module candidate | 12 | 10 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/code_ai_integration` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/code_analyzer` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/consciousness_engine` | module candidate | 1 | 0 | P,TR,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/digital_twin` | module candidate | 16 | 7 | none | critical-path sample; see audit |
| `modules/ai_intelligence/holo_dae` | module candidate | 1 | 1 | P,TR | inventory only; runtime unassessed |
| `modules/ai_intelligence/livestream_coding_agent` | module candidate | 4 | 2 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/menu_handler` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/multi_agent_system` | module candidate | 8 | 1 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/openai_integration` | module candidate | 1 | 0 | TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/pfmall_discovery` | module candidate | 5 | 1 | P,M,TR,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/post_meeting_feedback` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/post_meeting_summarizer` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/pqn` | module candidate | 1 | 1 | R,I,P,M,TR | inventory only; runtime unassessed |
| `modules/ai_intelligence/pqn_alignment` | module candidate | 39 | 14 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/pqn_mcp` | module candidate | 1 | 1 | TR,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/priority_scorer` | module candidate | 9 | 1 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/rESP_o1o2` | module candidate | 17 | 15 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/ric_dae` | module candidate | 13 | 4 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/social_media_dae` | module candidate | 3 | 2 | P | inventory only; runtime unassessed |
| `modules/ai_intelligence/src` | structural/namespace group | 4 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/tests` | structural/namespace group | 0 | 1 | P,M,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/training_system` | module candidate | 2 | 1 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/utf8_hygiene` | module candidate | 1 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/ai_intelligence/video_indexer` | module candidate | 24 | 19 | none | inventory only; runtime unassessed |
| `modules/ai_intelligence/work_completion_publisher` | module candidate | 3 | 0 | P,M,TR,TM | inventory only; runtime unassessed |
## blockchain

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/blockchain/src` | structural/namespace group | 3 | 0 | none | inventory only; runtime unassessed |
| `modules/blockchain/tests` | structural/namespace group | 0 | 0 | none | inventory only; runtime unassessed |
## communication

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/communication/auto_meeting_orchestrator` | module candidate | 10 | 3 | none | inventory only; runtime unassessed |
| `modules/communication/channel_selector` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/communication/chat_rules` | module candidate | 7 | 3 | TR,TM | inventory only; runtime unassessed |
| `modules/communication/consent_engine` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/communication/headless_video_orchestrator` | module candidate | 3 | 0 | TR,TM | inventory only; runtime unassessed |
| `modules/communication/intent_manager` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/communication/liberty_alert` | module candidate | 8 | 4 | none | inventory only; runtime unassessed |
| `modules/communication/live_chat_poller` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/communication/live_chat_processor` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/communication/livechat` | module candidate | 63 | 72 | none | inventory only; runtime unassessed |
| `modules/communication/moderation` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/communication/moltbot_bridge` | module candidate | 551 | 397 | none | critical-path sample; see audit |
| `modules/communication/obai_discord_bot` | module candidate | 2 | 1 | P,TR,TM | inventory only; runtime unassessed |
| `modules/communication/presence_aggregator` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/communication/response_composer` | module candidate | 4 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/communication/universal_comments` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/communication/video_comments` | module candidate | 37 | 37 | TM | inventory only; runtime unassessed |
| `modules/communication/voice_command_ingestion` | module candidate | 6 | 2 | none | inventory only; runtime unassessed |
| `modules/communication/voice_engine` | module candidate | 4 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/communication/youtube_channel_pull` | module candidate | 7 | 3 | P,TR,TM | inventory only; runtime unassessed |
| `modules/communication/youtube_dae` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/communication/youtube_shorts` | module candidate | 16 | 11 | P,TR | inventory only; runtime unassessed |
## development

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/development/cursor_multi_agent_bridge` | module candidate | 22 | 27 | none | inventory only; runtime unassessed |
| `modules/development/ide_foundups` | module candidate | 30 | 6 | none | inventory only; runtime unassessed |
| `modules/development/mcp_testing` | module candidate | 0 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/development/module_creator` | module candidate | 3 | 0 | none | inventory only; runtime unassessed |
| `modules/development/unicode_tools` | module candidate | 3 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/development/wre_interface_extension` | module candidate | 5 | 2 | none | inventory only; runtime unassessed |
| `modules/development/wsp_tools` | module candidate | 3 | 0 | I,P,TR,TM | inventory only; runtime unassessed |
## economy

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/economy/src` | structural/namespace group | 2 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
## foundups

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/foundups/agent` | module candidate | 25 | 23 | none | critical-path sample; see audit |
| `modules/foundups/agent_market` | module candidate | 20 | 17 | none | critical-path sample; see audit |
| `modules/foundups/docs` | structural/namespace group | 0 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/foundups/ecosystem_animation` | module candidate | 0 | 0 | TM | inventory only; runtime unassessed |
| `modules/foundups/esingularity` | module candidate | 32 | 1 | none | critical-path sample; see audit |
| `modules/foundups/gotjunk` | module candidate | 104 | 8 | TR,TM | inventory only; runtime unassessed |
| `modules/foundups/holoindex_prod_01` | module candidate | 0 | 0 | I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/foundups/identity_shield` | module candidate | 0 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/foundups/kosei` | module candidate | 11 | 5 | TR,TM | inventory only; runtime unassessed |
| `modules/foundups/mobile_worker_skills` | module candidate | 0 | 0 | I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/foundups/move2japan` | module candidate | 2 | 2 | TM | inventory only; runtime unassessed |
| `modules/foundups/pfmall` | module candidate | 8 | 15 | none | inventory only; runtime unassessed |
| `modules/foundups/portfolio_validator` | module candidate | 4 | 1 | I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/foundups/pqn_portal` | module candidate | 4 | 0 | TM | inventory only; runtime unassessed |
| `modules/foundups/pqn_swarm_hub` | module candidate | 1 | 0 | TR,TM | inventory only; runtime unassessed |
| `modules/foundups/public_catalog_projector` | module candidate | 4 | 1 | P,TR,TM | inventory only; runtime unassessed |
| `modules/foundups/shield` | module candidate | 0 | 0 | TR,TM | inventory only; runtime unassessed |
| `modules/foundups/simulator` | module candidate | 83 | 42 | TR | critical-path sample; see audit |
| `modules/foundups/social_twin` | module candidate | 2 | 1 | none | inventory only; runtime unassessed |
| `modules/foundups/src` | structural/namespace group | 6 | 0 | none | inventory only; runtime unassessed |
| `modules/foundups/tests` | structural/namespace group | 0 | 5 | none | inventory only; runtime unassessed |
| `modules/foundups/trade` | module candidate | 11 | 11 | TR | inventory only; runtime unassessed |
| `modules/foundups/voteballots` | module candidate | 11 | 8 | none | inventory only; runtime unassessed |
## gamification

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/gamification/_archived_duplicates_per_wsp3` | module candidate | 10 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/gamification/games` | module candidate | 4 | 3 | P | inventory only; runtime unassessed |
| `modules/gamification/tests` | structural/namespace group | 0 | 1 | none | inventory only; runtime unassessed |
| `modules/gamification/whack_a_magat` | module candidate | 15 | 14 | TM | inventory only; runtime unassessed |
## infrastructure

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/infrastructure/activity_control` | module candidate | 2 | 1 | P,TM | inventory only; runtime unassessed |
| `modules/infrastructure/autoagent_lab` | module candidate | 5 | 4 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/autonomous_enhancements` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/browser_actions` | module candidate | 9 | 6 | TM | inventory only; runtime unassessed |
| `modules/infrastructure/cli` | module candidate | 17 | 6 | P | inventory only; runtime unassessed |
| `modules/infrastructure/code_quality` | module candidate | 2 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/codex_hooks` | module candidate | 3 | 1 | none | inventory only; runtime unassessed |
| `modules/infrastructure/container_isolation` | module candidate | 3 | 2 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/cross_platform_memory` | module candidate | 5 | 0 | TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/dae_components` | module candidate | 13 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/dae_daemon` | module candidate | 11 | 5 | P | inventory only; runtime unassessed |
| `modules/infrastructure/dae_infrastructure` | module candidate | 13 | 2 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/database` | module candidate | 36 | 15 | P | inventory only; runtime unassessed |
| `modules/infrastructure/debug_tools` | module candidate | 2 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/dependency_launcher` | module candidate | 7 | 4 | TM | inventory only; runtime unassessed |
| `modules/infrastructure/deployment` | module candidate | 2 | 0 | TM | inventory only; runtime unassessed |
| `modules/infrastructure/development_monitor_dae` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/doc_dae` | module candidate | 3 | 2 | I,P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/docs` | structural/namespace group | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/evade_net` | module candidate | 1 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/feed_integration` | module candidate | 2 | 1 | P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/foundups_mcp_bridge` | module candidate | 124 | 82 | none | critical-path sample; see audit |
| `modules/infrastructure/foundups_selenium` | module candidate | 12 | 7 | P,TR | inventory only; runtime unassessed |
| `modules/infrastructure/foundups_tokenization` | module candidate | 0 | 0 | I,P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/foundups_vision` | module candidate | 8 | 3 | TM | inventory only; runtime unassessed |
| `modules/infrastructure/git_push_dae` | module candidate | 4 | 3 | none | inventory only; runtime unassessed |
| `modules/infrastructure/git_social_posting` | module candidate | 1 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/github_orchestrator` | module candidate | 4 | 1 | TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/human_interaction` | module candidate | 5 | 1 | P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/idle_automation` | module candidate | 13 | 9 | none | inventory only; runtime unassessed |
| `modules/infrastructure/instance_lock` | module candidate | 3 | 4 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/instance_monitoring` | module candidate | 2 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/integration_tests` | module candidate | 2 | 0 | P,TM | inventory only; runtime unassessed |
| `modules/infrastructure/link_sentinel` | module candidate | 5 | 1 | TM | inventory only; runtime unassessed |
| `modules/infrastructure/logging` | module candidate | 2 | 0 | P | inventory only; runtime unassessed |
| `modules/infrastructure/mcp_daemon` | module candidate | 3 | 0 | TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/mcp_manager` | module candidate | 4 | 1 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/metrics_appender` | module candidate | 1 | 0 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/monitoring` | module candidate | 3 | 1 | P,M | inventory only; runtime unassessed |
| `modules/infrastructure/navigation` | module candidate | 3 | 0 | TM | inventory only; runtime unassessed |
| `modules/infrastructure/oauth_management` | module candidate | 3 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/openrouter_client` | module candidate | 0 | 0 | I,P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/orchestration_switchboard` | module candidate | 3 | 0 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/patch_executor` | module candidate | 1 | 0 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/patches` | module candidate | 0 | 0 | P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/pavs_mcp` | module candidate | 2 | 2 | TR,TM | critical-path sample; see audit |
| `modules/infrastructure/secrets_mcp` | module candidate | 4 | 2 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/security_scanner` | module candidate | 3 | 1 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/shared_src` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/shared_utilities` | structural/namespace group | 45 | 18 | P | inventory only; runtime unassessed |
| `modules/infrastructure/sim_workflows` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/supervisor` | module candidate | 2 | 1 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/system_health_monitor` | module candidate | 4 | 1 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/token_efficiency` | module candidate | 7 | 7 | P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/wardrobe_ide` | module candidate | 17 | 1 | P,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/wre_core` | module candidate | 120 | 94 | none | critical-path sample; see audit |
| `modules/infrastructure/wre_core_main` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/infrastructure/wsp_core` | module candidate | 4 | 0 | P,M,TR,TM | inventory only; runtime unassessed |
| `modules/infrastructure/wsp_framework_dae` | module candidate | 2 | 1 | P,TM | inventory only; runtime unassessed |
| `modules/infrastructure/wsp_orchestrator` | module candidate | 3 | 2 | P,TR | inventory only; runtime unassessed |
## platform_integration

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/platform_integration/acoustic_lab` | module candidate | 10 | 7 | TR,TM | inventory only; runtime unassessed |
| `modules/platform_integration/antifafm_broadcaster` | module candidate | 62 | 11 | none | inventory only; runtime unassessed |
| `modules/platform_integration/foundups_sdk` | module candidate | 3 | 0 | TM | inventory only; runtime unassessed |
| `modules/platform_integration/github_integration` | module candidate | 16 | 7 | none | inventory only; runtime unassessed |
| `modules/platform_integration/linkedin_agent` | module candidate | 39 | 30 | none | inventory only; runtime unassessed |
| `modules/platform_integration/linkedin_scheduler` | module candidate | 8 | 7 | none | inventory only; runtime unassessed |
| `modules/platform_integration/remote_builder` | module candidate | 5 | 2 | M | inventory only; runtime unassessed |
| `modules/platform_integration/session_launcher` | module candidate | 4 | 1 | none | inventory only; runtime unassessed |
| `modules/platform_integration/social_media_orchestrator` | module candidate | 37 | 39 | none | inventory only; runtime unassessed |
| `modules/platform_integration/stream_resolver` | module candidate | 16 | 12 | none | inventory only; runtime unassessed |
| `modules/platform_integration/tests` | structural/namespace group | 0 | 1 | none | inventory only; runtime unassessed |
| `modules/platform_integration/utilities` | structural/namespace group | 21 | 8 | P | inventory only; runtime unassessed |
| `modules/platform_integration/x_twitter` | module candidate | 7 | 4 | none | inventory only; runtime unassessed |
| `modules/platform_integration/x_twitter_dae` | module candidate | 2 | 0 | P,M,TM | inventory only; runtime unassessed |
| `modules/platform_integration/youtube_api_operations` | module candidate | 2 | 3 | P | inventory only; runtime unassessed |
| `modules/platform_integration/youtube_auth` | module candidate | 42 | 14 | none | inventory only; runtime unassessed |
| `modules/platform_integration/youtube_live_audio` | module candidate | 4 | 2 | none | inventory only; runtime unassessed |
| `modules/platform_integration/youtube_proxy` | module candidate | 21 | 7 | none | inventory only; runtime unassessed |
| `modules/platform_integration/youtube_shorts_scheduler` | module candidate | 34 | 27 | none | inventory only; runtime unassessed |
| `modules/platform_integration/zeroclaw` | module candidate | 1 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |
## telemetry

| Module/group | Kind | Source files | Matched test files | Core memory gaps | Review depth |
|---|---|---:|---:|---|---|
| `modules/telemetry/feedback` | module candidate | 0 | 0 | R,I,P,M,TR,TM | inventory only; runtime unassessed |

## Interpretation rules

- `0` means no file matched the census rules; it does not prove an external implementation is absent.
- An externalized stub should point to its external acceptance evidence; do not recreate it in this repository.
- A module without test docs may still have tests; a module with tests may still fail.
- Owners should add requirement-level acceptance evidence before giving any inventory-only module a completion grade.
- Non-module tracked surfaces are counted in top_level_inventory.json; no production readiness is inferred for them.
