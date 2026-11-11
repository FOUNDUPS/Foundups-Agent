# Legacy Git and social-posting utilities interface

[scripts/posting_utilities.py](scripts/posting_utilities.py)
exports three callables; its guarded command-line interface accepts `history` or
`post` and otherwise prints usage.

- `generate_x_content(commit_msg, file_count)` returns a randomized string. It
  selects fix/test/other wording using substring checks on the lowercased commit
  message, appends a CTA and hashtags, and trims strings longer than 280 characters
  to a 240-character prefix plus a fixed suffix. It does not send the result.
- `git_push_and_post()` adjusts `sys.path`, constructs
  `GitLinkedInBridge(company_id="foundups")`, calls `push_and_post()` and prompts
  before returning. Its delegated Git/provider effects are not mocked or qualified
  here; the wrapper does not return a structured delivery receipt.
- `view_git_post_history()` reads `memory/git_posted_commits.json` and
  `memory/git_post_log.json` relative to the current working directory, displays
  recent entries and rates, and catches display/read failures. If the subsequent
  clear-history response is `y`, it removes either existing file, then prompts
  again. Its name does not guarantee absence of mutation.

The module imports the shared LinkedIn account registry at import time. Provider
credentials, recipient/publisher identity, duplicate protection and actual delivery
remain the existing bridge's operational boundary; no live acceptance is claimed.
