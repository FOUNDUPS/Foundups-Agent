# RedDog phone safety: research and education layer

Date: 2026-10-13. Scope: repository discovery, primary-source research, and an
offline education package. This document is not a deployment or legal clearance.

**Truth:** education artifacts are implemented; call policy, Gmail classification
automation, caller authentication, and runtime enforcement are
**SPECIFIED_NOT_IMPLEMENTED**. No paid service, call, account, filter, or message
was created. No claim of measured attack resistance is made.

## 1. Repository evidence and reuse decision

Checkout observed: `0c81418fe94a7786cfd55f01e138ddc5d510583d`, with concurrent
uncommitted work. These are source observations, not live runtime validation.

| Existing surface | Observed behavior | Reuse boundary |
| --- | --- | --- |
| [Voice ingestion](../../../../modules/communication/voice_command_ingestion/src/voice_command_ingestion.py), `FasterWhisperSTT.transcribe`, `TriggerDetector`, `CommandEvent` | Local transcription, literal `language: en`, trigger extraction. CommandEvent has no authenticated speaker binding. | Reuse transcription concepts after Japanese evaluation; a trigger is not authority. |
| [Voice router](../../../../modules/communication/voice_command_ingestion/src/livechat_router.py), `LiveChatIdentity`, `route_command_event` | Defaults `is_owner=True`, `is_moderator=True`; transcript storage defaults on. | Never connect untrusted phone audio to this privileged synthetic-chat path. Do not automatically send call transcripts into training memory. |
| [Gemma intent classifier](../../../../modules/communication/moltbot_bridge/src/gemma_intent_classifier.py), `_binary_classify`, `classify` | YES/NO category prompts use the first 300 characters; fixed scores and keyword fallback. | Candidate advisory feature only. These scores are not calibrated spam probabilities or caller authentication. |
| [External research adapter](../../../../modules/communication/moltbot_bridge/src/reddog_holoindex_first_external_research_grounding_adapter.py) | Explicit untrusted-data boundary; finite injection marker list. | Reuse provenance separation. A keyword list is not a complete multilingual voice defense. |
| [Skill boundary policy](../../../../modules/communication/moltbot_bridge/docs/SKILL_BOUNDARY_POLICY.md) and [safety guard](../../../../modules/communication/moltbot_bridge/src/skill_safety_guard.py) | Separates workflow prompts from internal executors; scanner and manifest preflight. | Education must not become a telephony executor or grant calling permissions. |
| [Identity/delegation audit](../../../../docs/audits/architecture/REDDOG_PRINCIPAL_IDENTITY_DELEGATION_AND_REWARD_CONTRACT_PHASE1.md) | Historical contract distinguishes role claims, integrity hashes, and authenticated authority. | Architectural precedent only; its historical gap list is not current runtime truth. |
| [Current bridge README](../../../../modules/communication/moltbot_bridge/README.md) | Describes newer signed authority boundaries and remaining production limits. | Reuse the owning authority plane when integrating; do not invent a second signing system inside this skill. |

Bounded searches covered `modules`, `docs`, `.agents/skills`, and `NAVIGATION.py`
for telephony, Twilio, Retell, Vapi, LiveKit, phone/voice calls, Google Voice,
missed calls, spoofing, and prompt injection. No RedDog PSTN call implementation
or Gmail missed-call classifier was found there. This does not prove absence in
external deployments, ignored private files, or unsearched vendors.

Retrieval evaluation:

- Holo query: `RedDog autonomous phone call voice telephony Gmail spam prompt injection WSP 97`.
- Exact failure: `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`; `ok=false`,
  `freshness=UNKNOWN`, `index_gap_detected=true`, `owner_attempts=0`.
  Authority HEAD was `4095ad9ee6042f4e9b5668bf4f6bf50c493c5964`.
  No semantic hit was accepted as current evidence; no reindex was attempted.
- Maintenance route: existing [HoloIndex runtime contract](../../../../modules/communication/moltbot_bridge/docs/HOLOINDEX_RUNTIME.md).
  The clean exact-main owner must resolve the mismatch through its governed
  OpenClaw/AgentDB path; this dirty-checkout education slice does not dispatch or
  emulate repair. A successful future query requires CURRENT/no-gap proof.
- Degraded retrieval follows [WSP CORE](../../../../WSP_framework/src/WSP_CORE.md):
  direct file reads, explicit unavailability record, no runtime promotion.
- Noise: long bridge history and unrelated uses of "prompt injection"; narrowed
  to symbols and source files. Ordering: module docs then exact implementation,
  adjacent authority surfaces, then external primary sources.
- Missing: bridge `memory/README.md` and `requirements.txt`; voice ingestion
  `memory/README.md`. Module README, INTERFACE, ROADMAP, ModLog, tests README and
  TestModLog were consulted; voice requirements were present. Test logs are not
  fresh test evidence. NAVIGATION identifies ingestion, not telephony.
- Staleness: historical continuity/ledger and identity audit are not current
  state; current source also contains concurrent edits. Duplication avoided by
  creating one education skill instead of another STT stack or orchestrator.

WSP 97 micro pass found English-only transcription and privileged message
defaults. Macro pass included authority, external research, skill execution,
memory writes, Gmail evidence, carrier routing, and opt-out behavior.

Dialectic decision: Gmail filtering alone is too narrow; a full phone platform
now would precede a verified safety contract. A reusable education package plus
offline cases is the smallest useful layer. Qwen/Gemma can later supply advisory
classification, but existing intent routing cannot establish Japanese call
safety or principal identity. Manual source review was used for those distinctions;
no local model benchmark or autonomous classifier run is claimed.

WSP 15 allocation assessment for this authorized education slice: Complexity 2,
Importance 4, Deferability 3, Impact 4, total 13/P1. Need: prevent unsafe reuse;
cost: local documentation and structural checks; live calling is deferrable.
Execution plane: local docs/data; WRE execution is not applicable. This assessment
does not mint a runtime authority or signed WSP receipt. Applicable WSPs:
15, 22, 50, 84, 97; skill/executor boundary remains governed by existing policy.

## 2. Missed calls: event, identity, intent, and action are different

A scam call is still a real call attempt. The useful question is whether it was
expected, who is authenticated, and what the caller is authorized to request.

Proposed Gmail decision record (not a current connector implementation):

| Field | Evidence rule |
| --- | --- |
| `event_evidence` | `email_report_only`, `provider_log_confirmed`, or `unverified`; keep message/provider event IDs and timestamps. |
| `presented_caller_id` | Observed number, not verified human identity. |
| `identity_status` | `unverified` unless an independent authenticated channel supplies appropriate evidence. |
| `expected_call_match` | Match an authorized job or trusted schedule plus provider evidence; never infer from number alone. |
| `spam_assessment` | `unknown`, `suspected`, or `confirmed_with_evidence`; keep reason and provenance, not an invented percentage. |
| `recommended_action` | Review/digest/ignore notification; never automatically call back or send a reply. |

Authenticate notification provenance using trusted mailbox/provider metadata,
not the display name, sender string alone, or an Authentication-Results line
embedded in a body. If a connector exposes only snippets, leave provenance
unverified. Obtain the provider record through the independently configured
provider, not a callback link or number embedded in a suspect message.

Deduplicate by message/event IDs. Similar timestamps and caller IDs without a
provider ID are a cluster of alerts, not proof of distinct call attempts.
An expected caller can still make malicious requests; update turn risk separately.

Operator policy from this conversation: unsolicited misses on the operator's
public line are suspected spam/bots and the operator does not answer that line.
The corrected full number is deliberately absent from repository artifacts.
Keep the precise line binding in authenticated private configuration. This is
triage intent, not an accusation against every number or authorization to delete.

[Google Voice Help](https://support.google.com/voice/answer/115089?hl=en-IE)
documents spam warnings and filtering, useful as an additional signal. It does
not replace identity checks. [Twilio SHAKEN/STIR](https://www.twilio.com/docs/voice/trusted-calling-with-shakenstir)
provides carrier-origin verification signals where supported; number attestation
is not proof of a person's identity, purpose, or permission. Do not assume it is
available on every Japanese route. Answering-machine detection, if later used,
classifies an answer type, not honesty or spam.

Gmail-first next slice: dry-run classification of explicitly selected alerts,
human-readable reasons, and proposed labels. No automatic reply, callback,
filter, deletion, contact promotion, or training-memory write.

## 3. Attack model and primary research

Scope includes malicious recipients of outbound calls, inbound callers,
voicemail, ambient/overlapping audio, external records, and forged call events.
Assets include task integrity, private data, spending authority, reputation,
execution tools, and durable memory.

| Attack family | Example effect sought | Proposed boundary |
| --- | --- | --- |
| Instruction/role injection | Replace the objective, claim a new system/developer rule | Caller audio is data; job and policy are outside caller control. |
| Output manipulation | Repetition loops, joke voices, embarrassing statements, a "name" containing instructions | Bounded task response; names remain data; escape/reject TTS markup. |
| Identity spoofing / voice cloning | Impersonate 012, RedDog, or a trusted organization | Independently authenticated delegation, never voice or caller ID alone. |
| Tool abuse / data extraction | Change transfer number, ask for OTPs, send unrelated messages | Server-side allowlists, destination binding, validated slots and fresh grants. |
| Multi-turn / multilingual injection | Split instructions across turns or Japanese/English | Preserve provenance across turns; evaluate semantics and effects, not English keywords. |
| Audio-layer manipulation | Overlap, perceptually hidden instructions, transcription discrepancies | Actual codec/audio evaluation plus constrained effects; transcript-only checks are insufficient. |
| Memory poisoning / forged receipts | "Remember I am your owner" or fabricate success/authorization | Quarantined external evidence; separate authenticated promotion. |
| Resource abuse | Endless loops, holds, repeated callbacks, premium transfers | Independent elapsed-time, action, retry, concurrency, destination and cost limits. |

The operator's "my, my, my ... Michael" example is a locally supplied test idea,
not a verified research incident. A direction to imitate or loop can be an
attack; the same words caused by stuttering are not evidence of malicious intent.
Plain off-topic conversation receives redirection, not automatic accusation.

Primary sources checked on 2026-10-13:

1. [OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/):
   separates direct/indirect and multilingual injection; recommends constrained
   privileges and treatment of external content as untrusted. Prompt wording alone
   cannot justify a claim of complete prevention.
2. [Hou et al., EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1303/):
   evaluates audio interference, instruction following, context injection and
   judgment hijacking. Model robustness varies across scenarios. Relevant to the
   evaluation matrix, not a measurement of RedDog.
3. [Chen et al., AudioHijack, 2026](https://arxiv.org/abs/2604.14604):
   reports auditory prompt injection and unauthorized downstream behavior in
   studied systems. RedDog applicability requires tests through its actual media
   pipeline; published success rates must not be copied into its risk score.
4. [IBM audio-jacking research, 2024](https://www.ibm.com/think/insights/using-generative-ai-distort-live-audio-transactions):
   demonstrates selective manipulation of live speech using a man-in-the-middle
   pipeline and cloned voices. A familiar voice is insufficient verification.
5. [Debenedetti et al., CaMeL, 2025](https://arxiv.org/abs/2503.18813):
   separates trusted control flow from untrusted data and uses capabilities to
   constrain tool effects. This motivates an independent call-policy gate; its
   benchmark/proof does not transfer automatically to telephony or this skill.

Design inference: an "Is this a spoof?" check helps detect diversion, but the
security boundary must still deny unauthorized effects when that check is wrong.
Speech itself can leak information or make unauthorized commitments, so constrain
disclosures and check output before audio playback as well as guarding tools.

## 4. What exists for Japan

These are documented candidate capabilities, not tested RedDog integrations.
Japanese language support and Japanese phone-network access are separate tests.
No pricing or availability commitment is made from this research snapshot.

| Candidate | Verified documentation | Judgment / unresolved Japan checks |
| --- | --- | --- |
| LiveKit plus carrier SIP | [Outbound calls](https://docs.livekit.io/telephony/making-calls/outbound-calls/) connects calls through a SIP trunk to a room; [outbound trunk docs](https://docs.livekit.io/telephony/making-calls/outbound-trunk/) describe provider configuration and Japan-region static IP options. | Preferred control-oriented prototype: keep policy/tool enforcement under RedDog ownership. This preference is architectural inference. Requires Japanese STT/TTS selection, carrier eligibility, region/latency and end-to-end tests. |
| Retell plus custom carrier | [Custom telephony](https://docs.retellai.com/deploy/custom-telephony) supports SIP integrations; [language matrix](https://docs.retellai.com/build/language-support) lists Japanese speech recognition and synthesis. | Faster managed prototype candidate; Japan number/routing comes from the carrier. Verify region, retention, tools and stopping behavior. |
| Vapi plus imported number/SIP | [Phone calling](https://docs.vapi.ai/phone-calling) and [SIP guide](https://docs.vapi.ai/advanced/sip/) support provider integration for international/outbound use; free Vapi numbers are not that route. | Alternative managed orchestration. Japanese quality, carrier route, residence/retention and the specific integration remain unverified. |
| Twilio voice / Elastic SIP Trunking | [Japan voice guidelines](https://www.twilio.com/en-us/guidelines/jp/voice) document domestic/international reachability and Tokyo-edge routing requirements. | Carrier candidate beneath an agent stack, not by itself a task-safe conversational agent. |

Twilio says domestic Japan-number-to-Japan calls must use its Tokyo edge to avoid
international routing that can strip caller ID; verified caller-ID substitution
does not preserve domestic caller ID. Its guidelines also list blocked special
prefixes and no emergency calling for Japan. Its [Japan regulatory guidance](https://help.twilio.com/articles/4405840066715-Japanese-Phone-Number-Regulatory-Changes)
and [application instructions](https://help.twilio.com/articles/4409100190235-How-to-Submit-a-Japanese-Phone-Number-Regulatory-Bundle-Application)
require identity/address verification, including a physical mailer process.
Recheck requirements for the intended entity and number type before provisioning.

[Retell guardrails](https://docs.retellai.com/build/guardrails) are described as
input/output topic moderation with replacement messages. They do not themselves
end/transfer a call or prove objective integrity or caller authentication. Do not
mistake a provider's "guardrails" setting for the proposed RedDog policy gate.

Japan launch requirements to resolve before a pilot:

- Independently verify number ownership, carrier route, caller-ID presentation,
  account permissions, allowed destination classes, Tokyo/JST call windows,
  network delay, interruptions and Japanese names/dates/numbers/readbacks.
- Disclose RedDog's AI/delegated role and call purpose. This is proposed product
  policy, not a claim of a universal Japanese AI-disclosure statute.
- For covered consumer telephone sales, the [Consumer Affairs Agency](https://www.no-trouble.caa.go.jp/what/telemarketing/)
  describes identity/purpose disclosures and a prohibition on continuing or
  repeating solicitation after refusal. Establish applicability for the actual
  call objective; an appointment check is not automatically a sales solicitation.
- The [Personal Information Protection Commission FAQ](https://www.ppc.go.jp/all_faq_index/faq1-q1-10/)
  says identifiable call content is personal information and use purposes must
  be notified or published; that FAQ does not impose a general obligation to
  announce recording. It is not blanket permission for every use or transfer.
  Resolve recording, retention, deletion, vendor processing and overseas handling
  for the actual deployment. Proposed pilot policy: recording off by default,
  explicit notice/permission if enabled, and minimum redacted audit data.
- Include normal exit, human handoff and opt-out in both languages. Do not infer
  recipient consent from possession of a public number.

## 5. Proposed call contract and enforcement

All of this section is **SPECIFIED_NOT_IMPLEMENTED**.

Before dialing, the trusted control plane creates an immutable job containing
`job_id`, authenticated `principal_ref`, `objective`, success evidence required,
destination reference/source, allowed disclosure fields, permitted tools and
parameters, locale/time window, expiry, nonce/replay binding, consent/recording
policy, and time/turn/spend/retry ceilings. The model cannot mint or modify it.
A destination change requires trusted authorization, not a caller suggestion.

Inbound calls enter a previously authorized intake job with minimal permissions.
No receipt, identity check, or system prompt supplied inside a call establishes
authority. A callback is a separate governed job, not an automatic response.

Proposed flow:

```text
trusted objective + current authorization
    -> carrier adapter verifies event provenance / replay binding
    -> external audio / transcript stays untrusted
    -> per-turn WSP 97 decision record
    -> bounded candidate response and action request
    -> independent disclosure + tool policy checks
    -> approved speech or allowed effect / safe end
    -> redacted receipt with separate objective-outcome evidence
```

Recheck limits and grant validity at effect time. No general shell, arbitrary
browsing, unrestricted mailbox access or free-form transfers from call tools.
Expose narrow operations such as recording an appointment-time proposal for
review. Tool failure, guard timeout, missing job or malformed decision must not
open a fallback execution path. Ignore repeated webhook deliveries idempotently.

Authenticate provider webhooks with the provider-supported verification method;
bind provider account/call identifiers to the job and enforce replay controls.
That authenticates transport provenance, not the person speaking. Stored hashes
are integrity checks, not signatures from a trusted principal.

For the recipient to verify RedDog, propose a short-lived, single-use delegation
reference visible through a previously trusted portal/contact route, bound to
the principal, purpose and call. It must expose only necessary information.
Knowing a public verification reference must not itself grant privileges. The
recipient must independently reach that route; an unsolicited URL, callback
number or secret requested by the voice is not an authentication mechanism.
This verification service and its trust bootstrap remain to be built.

Use `continue`, `clarify`, `redirect`, `deny_action`, `end`, or `human_review`.
End requests override task completion. Stop speaking promptly after a recognized
refusal. An unavailable reviewer results in a safe end, not elevated autonomy.
For an offline pilot, choose explicit small budgets (for example 180 seconds,
one attempt and at most two redirections); these are proposed test settings,
not legal limits or existing defaults. A backend watchdog enforces them.

Afterward, distinguish `attempted`, `connected`, `conversation_observed`,
`objective_met`, `declined`, and `unknown`. A model-generated summary or carrier
"completed" status cannot alone establish objective completion. External content
stays quarantined from principal preferences, skills, and training data until a
separate authorized promotion process accepts it.

## 6. Layered acceptance plan

1. **Education (this slice):** reusable skill, cited evidence, attack and benign
   fixtures. Validate structure/links and review decisions; no runtime claims.
2. **Offline decision component:** reuse existing gate/receipt patterns, inert
   tools, fixed job, no network. Evaluate this case set plus unseen paraphrases
   and multi-turn cases. Assert zero unauthorized effects, consent precedence,
   bounded resources and no external-content promotion; measure false positives
   and legitimate task completion. Do not treat any classifier score as authority.
3. **Real-audio evaluation:** native Japanese review, stutters, accents, polite
   refusals, overlapping voices, echo, codec loss, interruptions, voicemail,
   Japanese/English switches and adversarial audio across the intended codecs.
   Text fixtures do not validate STT, latency, audible output or audio attacks.
4. **Authorized carrier pilot:** separately approved test destinations, verified
   job/delegation, watchdogs and measured costs. Test caller-ID routing, provider
   retries, opt-out, human handoff, record handling and objective receipts.

The next useful build is the offline policy evaluator, then dry-run Gmail
classification. Provider activation comes after the task and effect boundaries
have executable acceptance evidence.

## 7. Validation receipt for this education package

- Skill creator `quick_validate.py`: passed with Python UTF-8 mode.
- Fixture structure: 28 unique cases parsed; required input, classification,
  allowed decision names, and forbidden-effect expectations present.
- Local Markdown references: 13 targets resolved.
- Targeted `git diff --check`: passed.
- Existing bridge README and ModLog sections matched pre-edit copies after
  removal of the inserted section; concurrent authored text was preserved.
- Not run: model behavioral evaluation, existing runtime tests, STT/audio
  tests, carrier tests or live calls. Structure validation does not establish
  the accuracy of attack classification or effectiveness of enforcement.
