# FoundUp Federation Migration Plan

**WSP Reference**: WSP 103 (FoundUp Federation Protocol)
**Status**: DRAFT - Architect Review
**Date**: 2026-03-15

---

## Executive Summary

Migrate all federated FoundUps to dual-remote pattern:
- **origin**: FOUNDUPS/RepoName (org repo - primary)
- **backup**: Foundup/RepoName (personal repo - mirror)

This matches the established Foundups-Agent pattern and enables:
- Contributor-friendly org visibility
- Personal backup for disaster recovery
- Consistent sync workflow

---

## Phase 1: AutoPost Migration

### Current State
- `Foundup/AutoPost` (PRIVATE) - only copy

### Target State
- `FOUNDUPS/AutoPost` (PRIVATE) - origin
- `Foundup/AutoPost` (PRIVATE) - backup

### Migration Steps

```bash
# 1. Create FOUNDUPS/AutoPost (requires org admin)
gh repo create FOUNDUPS/AutoPost --private --description "AI AutoPost Camera - FoundUp Japan"

# 2. Clone existing repo locally
git clone git@github.com:Foundup/AutoPost.git
cd AutoPost

# 3. Add FOUNDUPS as origin, rename Foundup to backup
git remote rename origin backup
git remote add origin git@github.com:FOUNDUPS/AutoPost.git

# 4. Push to FOUNDUPS
git push -u origin main

# 5. Verify dual-remote
git remote -v
# Expected:
# backup  git@github.com:Foundup/AutoPost.git (fetch)
# backup  git@github.com:Foundup/AutoPost.git (push)
# origin  git@github.com:FOUNDUPS/AutoPost.git (fetch)
# origin  git@github.com:FOUNDUPS/AutoPost.git (push)

# 6. Add sync alias
git config alias.sync-both '!git push origin && git push backup'
```

### Post-Migration Verification
- [ ] Both remotes configured correctly
- [ ] `git sync-both` works
- [ ] README updated with contribution guidelines
- [ ] No secrets exposed in repo

---

## Phase 2: Spin-Out Queue

| FoundUp | Source | Target Origin | Target Backup | Priority |
|---------|--------|---------------|---------------|----------|
| AutoPost | Foundup/AutoPost | FOUNDUPS/AutoPost | Foundup/AutoPost | P0 (now) |
| GotJunk | modules/foundups/gotjunk | FOUNDUPS/GotJunk | Foundup/GotJunk | P1 |
| Move2Japan | modules/foundups/move2japan | FOUNDUPS/Move2Japan | Foundup/Move2Japan | P1 |
| SocialTwin | modules/foundups/social_twin | FOUNDUPS/SocialTwin | Foundup/SocialTwin | P2 |
| PQNPortal | modules/foundups/pqn_portal | FOUNDUPS/PQNPortal | Foundup/PQNPortal | P2 |

### Spin-Out Procedure (for monorepo modules)

```bash
# 1. Create repos in both locations
gh repo create FOUNDUPS/GotJunk --private
gh repo create Foundup/GotJunk --private

# 2. Extract subdirectory to new repo
cd modules/foundups/gotjunk
git init
git add .
git commit -m "Initial commit: GotJunk FoundUp (spun out from Foundups-Agent)"

# 3. Configure dual-remote
git remote add origin git@github.com:FOUNDUPS/GotJunk.git
git remote add backup git@github.com:Foundup/GotJunk.git
git push -u origin main
git push backup main

# 4. Leave stub in monorepo
# modules/foundups/gotjunk/
#   README.md -> "Migrated to FOUNDUPS/GotJunk"
#   MIGRATED.md -> Migration notes
```

---

## Phase 3: pAVS MCP Integration

After repos are in dual-remote pattern:

1. **Register with pAVS**
   ```typescript
   const result = await pavs.foundupRegister({
     foundup_id: 'autopost',
     repo_url: 'https://github.com/FOUNDUPS/AutoPost',
     owner_pubkey: '<ed25519-pubkey>'
   });
   // Returns: api_key, endpoint
   ```

2. **Add SDK dependency**
   ```bash
   npm install @foundups/pavs-sdk
   # or
   pip install foundups-pavs
   ```

3. **Configure environment**
   ```bash
   # .env (gitignored)
   PAVS_ENDPOINT=wss://pavs.foundups.com/mcp
   PAVS_API_KEY=fp_xxxxxxxxxxxx
   ```

4. **Integrate tools**
   ```typescript
   import { PAVSClient } from '@foundups/pavs-sdk';
   const pavs = new PAVSClient({ ... });

   // Use CABR, Gemma, Qwen, FAM, Pattern Memory
   ```

---

## Template: New FoundUp Repo Setup

For any new FoundUp created after this plan:

```bash
# 1. Create dual-remote repos
gh repo create FOUNDUPS/NewFoundUp --private
gh repo create Foundup/NewFoundUp --private

# 2. Initialize with template
git clone git@github.com:FOUNDUPS/NewFoundUp.git
cd NewFoundUp

# Copy from template (based on GotJunk structure)
# - README.md
# - INTERFACE.md
# - ROADMAP.md
# - ModLog.md
# - module.json
# - frontend/ or src/
# - .env.example
# - .gitignore

# 3. Configure backup remote
git remote add backup git@github.com:Foundup/NewFoundUp.git

# 4. Initial push
git add .
git commit -m "Initial commit: NewFoundUp FoundUp"
git push -u origin main
git push backup main

# 5. Register with pAVS (when SDK available)
```

---

## Governance

- **FOUNDUPS org**: Requires org admin to create repos
- **Foundup personal**: 012 can create directly
- **Contributor access**: Set on FOUNDUPS repos (org-level permissions)
- **Backup sync**: Responsibility of committer (`git sync-both`)

---

## Success Criteria

- [ ] AutoPost migrated to dual-remote
- [ ] GotJunk spun out to dual-remote
- [ ] At least one FoundUp integrated with pAVS MCP
- [ ] Template documented for future FoundUps
- [ ] WSP 103 reflects dual-remote requirement

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Lost commits during migration | Clone both remotes locally before migration |
| API key exposure | Use `.env` + `.gitignore`, never commit secrets |
| Sync drift between origin/backup | Use `git sync-both` alias, CI check for drift |
| Org permissions | 012 is FOUNDUPS admin |

---

**Next Action**: Execute Phase 1 (AutoPost migration) when 012 approves.
