# eSingularity tests

The test suite verifies the monorepo migration contract:

- canonical FoundUp identity and WSP 104 namespace;
- manifest/registry agreement;
- Sites configuration and frontend build metadata;
- explicit token deferral rather than an invented token;
- existing public routes remain present in source.

Run from the repository root:

```powershell
python -m pytest modules/foundups/esingularity/tests -q
```
