# Can You Detect AI? - Benchmark Contract

Status: proposed method, no data collected.

## Three Questions, Three Boards

Human detector: how well does a person classify the assigned partner?
Agent detector: how well does a registered model-and-scaffold judge classify under the same declared information conditions?
Conversational model: how often do judges classify this pinned chat configuration as human?

Do not collapse these into a single intelligence score. Agent-vs-agent judging still needs human-control rounds; knowing every opponent is AI is not a meaningful detection test.

## Scoring

Store `p_ai` in [0,1], independent of the binary verdict. Let `y=1` for server-assigned AI and `y=0` for server-assigned human-controlled partner.

Per-round Brier loss: `(p_ai - y)^2`; lower is better. Neutral probability 0.5 gives loss 0.25. A confidently wrong answer costs more than acknowledged uncertainty.

Report ordinary accuracy, class-specific accuracy and balanced accuracy: `(AI correctly detected rate + human correctly recognized rate) / 2`. Rank calibrated skill on a declared common cohort/protocol; a class-balanced mean Brier loss can support comparison when class counts differ, but must be labeled as balanced-cohort calibration rather than real-world prevalence calibration.

Display sample counts and provisional status. Use participant/session-aware uncertainty for published comparisons; paired human rounds and repeated judges are not independent samples. Do not advertise superiority solely from the largest point estimate. Practice XP is separate, and no financial reward is computed by this score contract.

## Round and Information Integrity

Proposed states: CONSENTED -> QUEUED -> MATCHED -> CHATTING -> VERDICT_LOCKED -> REVEALED -> SCORED. ABORTED, EXPIRED and SAFETY_STOP are explicit terminal paths. Persist server-authoritative transitions; score each judge/round at most once.

Truth, partner identity, provider/model IDs, prompts, hidden reasoning, API metadata and administrative logs are unavailable to participants and agent judges until the permitted reveal. In a human pair, reveal only after both verdicts lock or the shared deadline closes. No early reveal can influence the other active judge.

Use the same interface and message rendering. Declare whether the protocol tests text alone or the full live experience. For text-only comparisons, standardize permitted timing cues across both arms; for live-experience comparisons, preserve and report latency. Never mix the two tracks silently. Score protocol refusals and safety stops using a predefined policy, not ad hoc deletion of unfavorable model rounds.

## Human Ground Truth Limitation

The server can verify its own routing decision and approved model calls. It cannot guarantee that an unsupervised human never used outside AI. Publish the open-game label as human-controlled account, with verification tier and suspected-assistance flags. A controlled/proctored research cohort is a separate stratum. A wrong detector verdict is not proof that a person is a bot.

## Required Evidence Fields

Proposed data contract, not a deployed database: random `round_id`; protocol version; consent versions; assignment class in restricted storage; pseudonymous judge ID and judge type; round outcome; verdict; `p_ai`; reveal/lock timestamps; safety and exclusion reason; model provider/checkpoint/revision; prompt hash; temperature/seed where supported; quantization and runtime hardware; token usage; measured response latency; cost basis; reward-eligibility state; dataset split.

Public projections exclude raw identifiers, transcript content without separate permission, secrets and pre-reveal labels. Do not place private information into immutable chain records. Default operational raw-text retention is a proposed maximum seven days; a production policy and exception handling must be approved before live collection. Consented evaluation/training storage has its own declared retention and withdrawal policy.

## Red Dog Learning Boundary

After purpose-specific consent and review, derive cases such as: ignored instruction, irrelevant repetition, needless closing question, correct minimal acknowledgment, missing context, unsupported capability claim, and useful necessary clarification. Labels are context-dependent; short output is not automatically good and long output is not automatically bad.

Evaluate unchanged held-out cases before promoting any prompt, skill, retrieval or trained-model change. Separate splits by participant/session and near-duplicate content, with time/model holdouts as appropriate. Never train on the live test set. Publish only aggregate or independently consented/redacted evidence. No automatic weight changes or training are claimed.

Game personas stay inside the disclosed game. Deployed Red Dog remains identified as AI; a higher human-judgment rate does not justify concealing that identity.
