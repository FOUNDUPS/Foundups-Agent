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

## Product differentiation hypothesis

Components exist separately:
- acute PTA instruments
- sports-concussion cognitive tests
- episodic picture-sequence tasks
- browser recognition tests
- high-frequency alternate-form cognitive testing
- browser experiment frameworks

The unvalidated hypothesis is that combining a branching micro-adventure, hidden event encoding, adaptive delayed probes, event retirement, observer markers and transparent retention curves provides a useful new research surface.

## Open research questions

1. Which game-event classes have equivalent memorability?
2. What delay scheduler gives useful resolution without excessive burden?
3. How much does an initial failed free-recall question itself refresh memory?
4. How should cued recall and recognition be modeled without inflating retention estimates?
5. What alternate-form pool size controls practice effects across repeated sessions?
6. How much do device, distraction and sleep/backgrounding affect timing and results?
7. Does the resulting curve correlate with validated instruments or outcomes in any target population?
