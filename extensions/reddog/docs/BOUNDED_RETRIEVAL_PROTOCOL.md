# RedDog Bounded Retrieval Protocol

Status: operational guidance; does not grant execution/effect authority.

## Problem

Large ModLogs, audit reports, repository trees, work ledgers, generated artifacts and spreadsheets can exceed a useful agent context window when retrieved wholesale. Oversized retrieval can truncate the evidence response or fail the reasoning/tool sequence before the relevant lines are reached.

## Default rule

RedDog/0102 uses progressive disclosure for repository evidence:

1. **Search first.** Use HoloIndex/GitHub search/find to identify the exact file, symbol, section, sheet or range.
2. **Read a bounded window.** Default text read is approximately 80-200 lines around the relevant hit. Spreadsheet reads target named sheets/ranges/formulas.
3. **Follow references selectively.** Read another window only when the current evidence points to a needed dependency, invariant or contradiction.
4. **Do not dump giant ModLogs/trees by default.** A full-file read requires a known bounded file size and a concrete reason the entire artifact is needed.
5. **Preserve traceability.** Record the exact file/range/line evidence used for the conclusion.

## WSP relationship

This is an implementation discipline for WSP 50/WSP 97 retrieval-before-stating and WSP 95 progressive disclosure. It changes no authority boundary.

## Large-file heuristic

- <= 200 text lines: full read is normally acceptable when relevant.
- > 200 lines: search, then bounded windows by default.
- Unknown/very large files: never full-read as the first action.
- Large JSON registries: locate the relevant object/tail first; prefer exact patch/update tooling when available instead of context-dumping the complete registry.
- Spreadsheets: inspect specific tabs/ranges/formulas; do not serialize every workbook cell into prompt context.

## Recovery after truncation/failure

If a retrieval is truncated or a tool/reasoning sequence fails:

1. stop repeating the same large read;
2. identify the specific fact/path that was still needed;
3. search for that term or retrieve a smaller line/range window;
4. resume only from verified evidence;
5. do not treat partial/truncated output as complete evidence.
