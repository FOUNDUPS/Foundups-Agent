# FoundUps mobile worker skills

**Authority:** Higher agentic layer (0102) routes work; **phone/local model** runs these as **worker** skills only.

**ADR:** [`docs/adr/ADR_FOUNDUPS_MOBILE_WORKER_SKILL_SYSTEM.md`](../../../docs/adr/ADR_FOUNDUPS_MOBILE_WORKER_SKILL_SYSTEM.md)  
**Builder rules:** [`../docs/WSP_SKILL_BUILDER.md`](../docs/WSP_SKILL_BUILDER.md)  
**Device proof (Gallery):** [`DEVICE_EDGE_GALLERY_VALIDATION.md`](DEVICE_EDGE_GALLERY_VALIDATION.md) — **raw GitHub ≠ Gallery**; use this for on-device checklist.  
**Matrix A (local import only):** [`MATRIX_A_LOCAL_IMPORT_RUN.md`](MATRIX_A_LOCAL_IMPORT_RUN.md) — smoke → parser + exact test string `55108`.  
**Report Template:** [`DEVICE_GALLERY_REPORT_TEMPLATE.md`](DEVICE_GALLERY_REPORT_TEMPLATE.md) — 012 fills during on-device testing (WSP 97: SPECIFIED_NOT_IMPLEMENTED until executed).

## Skills

| Directory | Purpose |
|-----------|---------|
| [`foundups-edge-load-smoke`](foundups-edge-load-smoke/) | Minimal **load** check (`ping` → `LOAD_OK`); optional before parser |
| [`foundups-code-task-parser`](foundups-code-task-parser/) | NL → structured dev task |
| [`foundups-scope-locker`](foundups-scope-locker/) | Minimize scope / ambiguity |
| [`foundups-task-packet-writer`](foundups-task-packet-writer/) | Task → machine packet |
| [`foundups-result-interpreter`](foundups-result-interpreter/) | Logs/diffs/tests → summary |
| [`foundups-handoff-validator`](foundups-handoff-validator/) | Validate pipeline JSON before handoff to 0102 |
| [`wsp00-mobile-semantics`](wsp00-mobile-semantics/) | WSP 00 **semantic** subset for on-device boot (no Python gate) |

## Schemas & examples

| Path | Purpose |
|------|---------|
| [`schemas/worker-handoff-pipeline.v1.schema.json`](schemas/worker-handoff-pipeline.v1.schema.json) | Canonical `$defs` for worker JSON |
| [`examples/E2E_HANDOFF_FLOW_EXAMPLE.md`](examples/E2E_HANDOFF_FLOW_EXAMPLE.md) | Full pipeline walkthrough |

## URL loading (AI Edge Gallery) — exact notes

**Cannot be fully confirmed from CI:** the Gallery app resolves the **skill folder URL** on-device. Use this checklist before claiming “loads from URL”:

1. **Raw file sanity (any browser):**  
   `https://raw.githubusercontent.com/FOUNDUPS/Foundups-Agent/main/modules/foundups/mobile_worker_skills/<skill-name>/SKILL.md`  
   Must return **plain markdown** (starts with `---` frontmatter). Replace `FOUNDUPS/Foundups-Agent` / `main` if your fork or branch differs.

2. **“Folder URL” in Gallery:** the app expects a **base URL** where `SKILL.md` can be fetched as `{base}/SKILL.md`. **`github.com/.../tree/.../folder`** is an HTML UI, **not** a static folder API — do **not** assume it works as the load URL.

3. **Recommended for production URL loading:** mirror `mobile_worker_skills/` to **GitHub Pages** (or another static host) with **`.nojekyll`** so `.md` is not Jekyll-transformed; base = `https://<org>.github.io/<pages-site>/mobile_worker_skills/<skill-name>/`.

4. **JS skills:** execution needs correct MIME; **raw.githubusercontent.com** is often **wrong** for `run_js` — use Pages per [Gallery skills README](https://github.com/google-ai-edge/gallery/blob/main/skills/README.md).

5. **WSP 104:** do not add **bespoke** `public/` tenant sprawl for this; Pages mirror or approved CDN is separate from p.fMALL shell routes.

**Local import:** Gallery supports **Import local skill** (device file picker) — valid for dev without any URL.

## Attachment (WSP 83)

Listed in [`../README.md`](../README.md) canonical table and `modules/foundups/ModLog.md`.
