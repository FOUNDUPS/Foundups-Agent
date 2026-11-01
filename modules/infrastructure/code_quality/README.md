# Legacy code-quality analysis tools

This owner preserves two manual tools with different purposes:
[orphan_analyzer.py](tools/orphan_analyzer.py) requests Qwen classifications for
an existing JSON batch, while [wsp90_analyzer.py](tools/wsp90_analyzer.py) probes
console redirection, logging and subprocess behavior. Neither is the canonical
FMAS audit or an automatic source-removal service.

The orphan analyzer's INTEGRATE/ARCHIVE/DELETE/STANDALONE outputs are model advice,
not authorized file operations. Its source imports `QwenInferenceEngine` through
a legacy path adjustment; runtime import resolution and inference compatibility
have not been qualified here. The WSP 90 probe writes a temporary log, adjusts
logging and invokes a child interpreter. Its final boolean only reflects its
narrow `risks_found` list, so a successful verdict does not establish that all
earlier printed checks passed or that mass rewriting is safe.

Read [INTERFACE.md](INTERFACE.md) before any execution. This change documents
existing code only; no model, process probe, repository scan or live qualification
was run, and no module-local regression suite is tracked.
