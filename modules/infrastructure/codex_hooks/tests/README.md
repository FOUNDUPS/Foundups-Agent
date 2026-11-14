# Codex Hooks Tests

The suite validates hook discovery JSON, secret classification without value
echo, tool denials, WSP_00 session sequencing, and Stop-loop behavior.

Run:

```powershell
python -m pytest modules/infrastructure/codex_hooks/tests -q
```

Tests use synthetic strings assembled at runtime and fake subprocess runners;
they never access credential files or mutate Git state.
