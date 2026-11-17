# Legacy Unicode utility interfaces

These are source-documented legacy utilities, not a supported automatic repair
service. Review the import/write boundaries in [README.md](README.md) first.

- [auto_cleaner.py](src/auto_cleaner.py): is_problematic_unicode(char) classifies
  character ranges; gemma_smart_replacements() returns a replacement dictionary;
  clean_unicode_text(text) returns transformed text. main() rewrites cwd/012.txt
  with a backup when its heuristic finds problems. Windows output wrapping occurs
  at import. Transformations can lose information; no round-trip contract exists.
- [unicode_campaign.py](src/unicode_campaign.py): QwenGemmaUnicodeCampaign has
  qwen_analyze_file(file_path), which reads UTF-8 and returns a success/error
  mapping; gemma_apply_cleanup(analysis_result), which can back up and rewrite
  source; get_unicode_files_list(), which walks the current directory; and async
  orchestrate_campaign()/analyze_results(), which execute work and print summaries.
  Failures may be returned as mappings rather than raised. Names do not establish
  Qwen/Gemma inference: these inspected paths use deterministic heuristics.
- [emoji_fixer.py](src/emoji_fixer.py): no callable public interface or main guard.
  Import executes the MCP manager source rewrite using a relative path.

No tracked dedicated tests, losslessness guarantee, concurrency isolation or
bounded tracked-inventory contract exists in this folder at this revision.
The maintained UTF-8 hygiene owner is elsewhere; legacy utilities were not run.
