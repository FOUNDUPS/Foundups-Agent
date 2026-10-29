# Training adapter interfaces

[scripts/launch.py](scripts/launch.py) exposes run_training_system(), an
interactive menu that reads the configured corpus and uses pattern memory,
training and routing owners. The module imports PatternMemory; importing this
adapter is not a guarantee that all transitive imports are side-effect-free.

[scripts/training_commands.py](scripts/training_commands.py) exposes
execute_training_command(command: str, targets: Optional[str], json_output: bool)
-> None. It attempts PatternMemory construction, executes a command, and prints
JSON or human-readable output. Targets are comma-separated scopes.

| Command | Existing implementation and effects |
| --- | --- |
| utf8_scan | Canonical UTF-8 scanner; prints findings and count. |
| utf8_summary | Canonical UTF-8 summary; prints its returned statistics. |
| utf8_fix | UTF8RemediationCoordinator(Path(".")); auto_approve=True can rewrite scoped files. |
| batch | IdleAutomationDAE's pattern training operation. |

Unknown commands print an error mapping. Caught command exceptions populate an
error field; PatternMemory initialization failures become warnings. An utf8_fix
result may have status=ok while success=false, so printed status alone is not
acceptance. The CLI takes command and optional targets positionally and separately
checks for --json; it is not a general argument-parser contract.

Menu options 3/4 are unimplemented drills. Option 9 clears pattern memory and its
checkpoint after typed confirmation. See [README.md](README.md) and
[tests/README.md](tests/README.md). No live training or rewrite was validated here.
