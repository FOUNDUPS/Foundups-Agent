# Device validation — AI Edge Gallery × FoundUps mobile worker skills

**Purpose:** Real **on-device** proof that skills **load** and **run** in AI Edge Gallery. **Raw GitHub in a desktop browser is not Gallery proof.**

**Canonical spec:** [Gallery skills README](https://github.com/google-ai-edge/gallery/blob/main/skills/README.md)

---

## Recommended first skill (on-device)

1. **`foundups-code-task-parser`** — text-only, no JS; validates full instruction path.  
2. **`foundups-edge-load-smoke`** — optional **minimal** load check (see folder `foundups-edge-load-smoke/`).  
3. **`foundups-handoff-validator`** — second wave; paste JSON from E2E example.

**Do not** test JS / `run_js` skills in this phase.

---

## Test matrix (minimal)

| # | Mode | What to enter / do | Pass criteria | Fail criteria |
|---|------|-------------------|---------------|---------------|
| A | **Import local skill** | Copy skill folder to device; Gallery → Skills → (+) → **Import local skill** → pick folder containing `SKILL.md`. | Skill appears in list; name + description match frontmatter; opening chat with skill enabled shows instructions in context (or skill triggers on relevant prompt). | Import error; “Expected at least two `---` sections”; empty skill; crash. |
| B | **Load skill from URL** | Gallery → **Load skill from URL** → enter **folder base URL** only (see below). | Same as A for discoverability + at least one successful model turn using the skill. | 404; wrong MIME; HTML error page; timeout; skill not listed. |
| C | **Raw GitHub (sanity)** | Open in **mobile browser** (not Gallery): raw `SKILL.md` URL. | File displays as markdown text starting with `---`. | 404; HTML wrapper only; rate limit. |
| D | **GitHub Pages (folder URL)** | Use Pages-deployed base `.../mobile_worker_skills/<skill>/` per [Pages setup](#github-pages-setup-notes). | Gallery URL load behaves like row B **success**. | Same as B fail. |

**Critical distinction**

- **C passing** does **not** imply **B** passing.  
- **B/D passing** is **device Gallery proof**; **C** is only **content reachable** proof.

---

## Expected behavior when a skill loads correctly

1. **Skill Manager** shows the skill **name** (from YAML `name`, kebab-case).  
2. **Description** visible/trigger-ready (truncated in UI is OK).  
3. With skill **enabled** for a session, a prompt that matches the description (e.g. “Parse this coding request: …”) causes the model to follow **Role / Steps / Output format** (e.g. emit JSON for parser).  
4. No requirement to hit the network beyond what Gallery already uses for the model.

---

## Shortest URL candidates (copy-paste templates)

Replace `OWNER`, `REPO`, `BRANCH`, `<skill>` as appropriate.

| Kind | Template | Gallery “Load from URL” use? |
|------|------------|-------------------------------|
| Raw **file** (sanity) | `https://raw.githubusercontent.com/OWNER/REPO/BRANCH/modules/foundups/mobile_worker_skills/<skill>/SKILL.md` | **No** — this is a **file**, not a folder base. Use for row **C** only. |
| **tree/** (browse) | `https://github.com/OWNER/REPO/tree/BRANCH/modules/foundups/mobile_worker_skills/<skill>` | **Unlikely** — HTML UI, not static `{base}/SKILL.md`. |
| **Pages folder base** | `https://OWNER.github.io/REPO/mobile_worker_skills/<skill>/` | **Yes** — intended row **D** (after deploy). |

**First real Gallery URL test** should use **Pages** (row D) or whatever host exposes `SKILL.md` at `{base}/SKILL.md`.

**Local import** (row A) needs **no URL** — shortest path to **first device proof**.

---

## GitHub Pages setup notes (minimal)

1. Enable **Pages** for the repo (or a dedicated pages repo).  
2. Repo root (or `docs/` source): add **`.nojekyll`** (empty file) so Jekyll does not eat/transform `.md` unexpectedly.  
3. Publish a tree that includes:

   `mobile_worker_skills/<skill-name>/SKILL.md`

   e.g. copy or submodule the subtree from `modules/foundups/mobile_worker_skills/`.

4. Confirm in browser:  
   `https://<site>/mobile_worker_skills/foundups-code-task-parser/SKILL.md`  
   returns **raw markdown** (starts with `---`).

5. In Gallery **Load skill from URL**, use **folder base**:  
   `https://<site>/mobile_worker_skills/foundups-code-task-parser/`

**WSP 104:** Pages site is **not** p.fMALL shell routing; no new `public/` sprawl in the product tree is required for this experiment.

---

## 012 failure capture format (paste back to 0102)

```text
DEVICE_GALLERY_REPORT
date_utc: YYYY-MM-DDTHH:MMZ
device: <model + OS version>
gallery_app: <version if known>
test_row: A|B|C|D
skill_folder: <e.g. foundups-code-task-parser>
url_used: <exact string or LOCAL_IMPORT>
outcome: PASS|FAIL
pass_criteria_met: <which bullets from matrix>
failure_symptom: <one line>
screenshot_or_log: <optional; describe if not attached>
notes: <free text>
```

---

## Pre-flight repo checks (CI / desktop, not device)

- [ ] Each `SKILL.md` has **exactly one** YAML block: opening `---`, closing `---`, then body (Gallery parses frontmatter).  
- [ ] `name:` matches directory name (kebab-case).  
- [ ] `examples/E2E_HANDOFF_FLOW_EXAMPLE.md` still matches `schemas/worker-handoff-pipeline.v1.schema.json` for the envelope example.

---

## After device PASS

- Record outcome in `modules/foundups/ModLog.md` (one line + link to this file section).  
- Optionally pin **Gallery app version** and **model** (e.g. Gemma 4 E4B) in ModLog for reproducibility.
