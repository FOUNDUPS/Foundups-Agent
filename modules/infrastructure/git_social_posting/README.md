# Legacy Git and social-posting utilities

This owner preserves the [legacy posting utilities](scripts/posting_utilities.py),
not a separate publishing service. `generate_x_content` constructs randomized
short copy from a commit message and file count. `git_push_and_post` delegates
actual pushing/posting to the existing LinkedIn bridge and labels itself legacy.
Source comments recommend GitPushDAE; this documentation does not activate it.

The history viewer is not strictly read-only: after displaying working-directory
JSON history, it offers to delete both history files. Clearing those files can
remove duplicate-post protection. Do not invoke `post` or the interactive history
routine merely to inspect or validate documentation; any posting action still
requires the applicable publication authority and provider readback.

See [INTERFACE.md](INTERFACE.md) for exact call and file boundaries. There are no
tracked module-local tests. This source-only documentation change performed no
Git push, social post, history read or history deletion through these utilities.
