# Memory Horizon - Research Record

Status: source map for product design, not clinical validation.

## Acute post-traumatic amnesia

**A-WPTAS — NSW Agency for Clinical Innovation**  
https://aci.health.nsw.gov.au/networks/eci/clinical/tools/head-injuries/awptas

The Abbreviated Westmead Post-Traumatic Amnesia Scale is an established instrument for identifying acute cognitive impairment/PTA after mild traumatic brain injury. It anchors the requirement that Memory Horizon must not present itself as a substitute clinical instrument.

## Sports concussion assessment

**SCAT6 / Concussion in Sport Group literature**  
https://bjsm.bmj.com/content/57/11/622

SCAT6 combines symptoms, cognition, neurological/balance elements and delayed recall. It is a multidomain clinical/sports tool, not the same problem as continuous event-grounded retention mapping.

## Episodic-memory design

**NIH Toolbox Picture Sequence Memory Test**  
https://nihtoolbox.org/test/picture-sequence-memory-test/  
https://pmc.ncbi.nlm.nih.gov/articles/PMC4254833/

The task measures episodic memory using sequences of pictured activities. Published development work emphasizes new learning, sequence reconstruction, test-retest reliability and alternate forms. Alternate forms are directly relevant to repeated Memory Horizon sessions.

## Longitudinal/high-frequency digital testing

**TestMyBrain**  
https://www.testmybrain.org/dashboard/tmb-tests.html  
https://www.testmybrain.org/using-tmb/tmb-toolkits.html

TestMyBrain provides self-administered browser/mobile cognitive tests, raw/summary data, alternate forms, ultra-brief forms and support for longitudinal/high-frequency/measurement-burst designs. This supports feasibility of repeated browser measurement while also showing that Memory Horizon must differentiate itself by the event-grounded adaptive-retention-game architecture.

## Continuous recognition comparator

**MemTrax**  
https://memtrax.com/

MemTrax runs in a browser and presents repeated images at varied intervals, capturing recognition accuracy and reaction time. It demonstrates low-friction browser memory measurement but targets continuous recognition rather than the proposed naturalistic event/free-cued-recognition retention curve.

## Browser experiment engine

**jsPsych**  
https://www.jspsych.org/

jsPsych is a JavaScript framework for behavioral experiments in web browsers. Its timeline/plugin/data model is a strong POC candidate for precise stimulus/response sequencing without building an experiment runtime from scratch.

## Wearable assistive-memory precedent: MIT MemPal

**MIT Media Lab — MemPal: Wearable Memory Assistant for Aging Population**  
https://www.media.mit.edu/projects/mempal/overview/

MemPal is the closest direct comparator to the proposed Companion. It uses a wearable camera plus AI to log actions in real time without storing image data, supports voice retrieval of misplaced objects (including the published example "where is my phone?"), provides contextual reminders, and was tested in the homes of 15 adults aged 65+. The reported study found improved object-finding performance with audio assistance and positive user perceptions.

Implication: Memory Horizon must not claim novelty for a wearable that logs actions and answers object-location questions. Our differentiation target is the shared measurement/assistance event model, event-to-retrieval-failure timing, graded cueing, transparent provenance/confidence and contamination-aware longitudinal research.

## Lifelogging / SenseCam

**Microsoft Research / SenseCam**  
https://www.microsoft.com/en-us/research/publication/sensecam-retrospective-memory-aid/  
https://pubmed.ncbi.nlm.nih.gov/21995708/  
https://pubmed.ncbi.nlm.nih.gov/24528204/

SenseCam automatically captured first-person life images plus sensor data. Research and reviews report that reviewing captured events can cue autobiographical recall, including studies in people with memory impairment. Evidence varies by study/population and does not establish a general treatment effect.

Implication: environmental cues can support recollection, but the Companion should retain provenance and study cue levels rather than assume every reminder restores memory.

## Earlier personal memory prostheses

**iRemember / audio-based personal memory aid**  
https://cs.brown.edu/people/stellex/publications/vemuri-ubicomp2004.pdf

Early ubiquitous-computing work described a wearable "memory prosthesis" that captured audio/context and provided retrieval tools for forgotten experiences. The concept predates current LLM wearables by decades and also documents social/legal concerns around ubiquitous recording.

## Current ambient AI wearable comparator

**Limitless Pendant**  
https://www.limitless.ai/new

Limitless markets an all-day wearable that captures spoken interactions and makes them searchable/summarizable. This demonstrates consumer availability of ambient audio-memory hardware, but conversation capture alone is not equivalent to physical-event inference, evidence-ranked breadcrumbs, or a validated memory-assistance system.

## FoundUps architectural reuse

WSP 60 already separates semantic, episodic, procedural and working memory, and defines Breadcrumb tracing. The RedDog/FoundUps Memex architecture treats Breadcrumbs as episodic continuity, Brain as durable consolidation and retrieval/nudge surfaces as separate responsibilities.

Memory Horizon Companion can reuse this architecture conceptually:
- lived event -> episodic Breadcrumb
- durable relevance -> Brain/Memex-like consolidation
- query -> evidence retrieval
- current situation -> working memory
- cue -> attention/nudge boundary

This is conceptual reuse only until an implementation contract proves compatible runtime reuse.

## Product differentiation hypothesis

Components exist separately:
- acute PTA instruments
- sports-concussion cognitive tests
- episodic picture-sequence tasks
- browser recognition tests
- high-frequency alternate-form cognitive testing
- browser experiment frameworks
- wearable lifelogging memory aids
- ambient AI conversation recorders

The unvalidated hypothesis is that **one event model can support both controlled retention measurement and privacy-preserving just-in-time memory assistance**, while explicitly recording event time, retrieval-failure time, cue strength and outcome.

## Open research questions

1. Which game-event classes have equivalent memorability?
2. What delay scheduler gives useful resolution without excessive burden?
3. How much does an initial failed free-recall question itself refresh memory?
4. How should cued recall and recognition be modeled without inflating retention estimates?
5. What alternate-form pool size controls practice effects across repeated sessions?
6. How much do device, distraction and sleep/backgrounding affect timing and results?
7. Does the resulting curve correlate with validated instruments or outcomes in any target population?
8. Can real-world event extraction reach useful accuracy without retaining raw audio/video?
9. What graded cue restores function while preserving user agency and minimizing false-memory risk?
10. Which retrieval failures can be detected safely beyond explicit voice queries?
