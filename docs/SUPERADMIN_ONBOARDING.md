# Foundups Superadmin Onboarding

> Historical runbook, preserved on 2026-10-29. Its bootstrap, branch, staging
> and startup-gate commands predate current controls and are not current
> operating instructions. Follow [CLAUDE.md](../CLAUDE.md) for qualified
> runtimes, isolated work, exact-main Holo retrieval and permission gates.


## Purpose
This runbook gets a new superadmin from zero to operational on `FOUNDUPS/Foundups-Agent` without leaking secrets.

First principle:
- `.gitignore` does not block cloning.
- `.gitignore` does prevent sensitive/local runtime files from being committed, so a fresh clone must be hydrated with approved local assets.

## 1. Access Prerequisites
1. Confirm GitHub org access to `FOUNDUPS/Foundups-Agent` with write/admin role.
2. Configure Git identity:
```powershell
git config --global user.name "YOUR_NAME"
git config --global user.email "YOUR_EMAIL"
```
3. Authenticate GitHub:
```powershell
gh auth login
```
or configure SSH key and test:
```powershell
ssh -T git@github.com
```

## 2. Clone And Verify
1. Clone:
```powershell
git clone https://github.com/FOUNDUPS/Foundups-Agent.git
cd Foundups-Agent
```
2. Verify remote:
```powershell
git remote -v
```
Expected:
- `origin https://github.com/FOUNDUPS/Foundups-Agent.git`

## 3. Python Environment Bootstrap
1. Create venv:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Install dependencies:
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Required Local Files Not In Git
Copy these from secure internal storage (never from chat/email plaintext):

- `.env` (or generate from `.env.example` and fill secrets)
- `credentials/client_secret*.json` (YouTube OAuth client secrets)
- `credentials/oauth_token*.json` (optional initially; can be generated later)
- `modules/platform_integration/browser_profiles/` (optional but needed for warm sessions)
- `holo_index/models/*.gguf` and related model assets

These are intentionally excluded by `.gitignore`.

## 5. Minimal `.env` Baseline
Start from:
```powershell
Copy-Item .env.example .env
```
Then set at minimum:
- `OPENCLAW_BRIDGE_PORT`
- `FOUNDUPS_CHROME_PORT`
- `FOUNDUPS_LIVECHAT_CHROME_PORT`
- `LM_STUDIO_PORT`
- Required API keys/tokens for channels you will operate

## 6. Security Rules
- Do not commit `.env`, `credentials/`, token JSONs, browser profiles, private keys.
- Keep model files local; do not push binary model assets to repo.
- Rotate shared keys when superadmin changes.
- Use least privilege for collaborator accounts.

## 7. Local Readiness Checks
Run from repo root:
```powershell
python -m py_compile main.py
```
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; python -m pytest modules/ai_intelligence/ai_overseer/tests/test_openclaw_security_sentinel.py -q
```
```powershell
python main.py --status
```

## 8. Preflight Expectations
On startup you should see:
- OpenClaw preflight PASS or warning with explicit reason
- WSP framework preflight summary line

If OpenClaw preflight fails due to real risky binding on OpenClaw port:
- Identify process:
```powershell
netstat -ano | findstr ":18800"
Get-Process -Id <PID>
```
- Resolve or rebind service before production run.

## 9. Clone Works But Runtime Fails: Fast Diagnosis
If clone succeeds but system is broken, usually missing local assets:
```powershell
$checks = @(
  '.env',
  'credentials/client_secret.json',
  'holo_index/models',
  'modules/platform_integration/browser_profiles'
)
foreach ($p in $checks) {
  "{0} -> {1}" -f $p, (Test-Path $p)
}
```

## 10. Git Workflow For Superadmin
1. Update local main:
```powershell
git checkout main
git pull origin main
```
2. Create working branch:
```powershell
git checkout -b cto/<short-change-name>
```
3. After validation:
```powershell
git add -A
git commit -m "clear scope message"
git push -u origin cto/<short-change-name>
```
4. Merge via PR (recommended for audit trail), even for admins.

## 11. Production Hardening Flags
For stricter startup gates in production:
- `OPENCLAW_SECURITY_PREFLIGHT_ENFORCED=1`
- `WSP_FRAMEWORK_PREFLIGHT_ENFORCED=1`

Keep these off during first bootstrap if environment is incomplete, then enable after stabilization.

## 12. Vocabulary Onboarding

Before contributing code, learn pAVS terminology:

**Required Reading**:
- [docs/vocabulary/IDENTITY.md](vocabulary/IDENTITY.md) - 012, 0102, 0201 state model
- [docs/vocabulary/ECONOMICS.md](vocabulary/ECONOMICS.md) - F_i, UPS, CABR token flow
- [docs/vocabulary/TECHNICAL.md](vocabulary/TECHNICAL.md) - WSP, WRE, HoloIndex

**Quick Reference**:
- [docs/vocabulary/README.md](vocabulary/README.md) - Full vocabulary index
- [docs/vocabulary/REGULATORY.md](vocabulary/REGULATORY.md) - "Distribution ratio" not "ROI"
- [docs/vocabulary/AGENTS.md](vocabulary/AGENTS.md) - Qwen, Gemma, Opus tiers

**HoloIndex Search**:
```powershell
python holo_index.py --search "what is CABR"
python holo_index.py --search "012 vs 0102"
```

## 13. Handoff Checklist
- Access validated in GitHub org
- Repo cloned from `FOUNDUPS/Foundups-Agent`
- `.env` and credentials hydrated securely
- Local model assets present
- Preflight and sentinel tests passing
- Superadmin can run `main.py --status` and core CLI paths
- **Vocabulary onboarding completed** (Identity, Economics, Technical)
