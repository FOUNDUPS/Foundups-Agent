# GotJUNK? Security Guidelines

## API Key Management

### ❌ NEVER DO THIS:
- ❌ Commit `.env.local` to git
- ❌ Hardcode API keys in source code
- ❌ Share API keys in chat logs or screenshots
- ❌ Display API keys in documentation
- ❌ Store API keys in markdown files

### ✅ ALWAYS DO THIS:
- ✅ Use `.env.local` for local development (gitignored)
- ✅ Use environment variables in production
- ✅ Keep API keys in secure credential management systems
- ✅ Rotate API keys if exposed
- ✅ Use `.env.example` with placeholder values only

## Setting Up API Keys (Secure Method)

### Local Development:
```bash
# 1. Copy template
cp .env.example .env.local

# 2. Edit .env.local and add your key
# GEMINI_API_KEY=your_actual_key_here

# 3. Verify .gitignore includes *.local
cat .gitignore | grep "*.local"
```

### Cloud Run Deployment:
```bash
# Set via Cloud Run console:
# 1. Go to Cloud Run service
# 2. Edit & Deploy New Revision
# 3. Variables & Secrets tab
# 4. Add: GEMINI_API_KEY = your_actual_key

# Or via gcloud CLI:
gcloud run services update gotjunk \
  --update-env-vars GEMINI_API_KEY=your_actual_key
```

### AI Studio Deployment:
- AI Studio handles secrets automatically
- Set in AI Studio project settings
- Never commit to version control

## What's Protected

### Gitignored Files:
```
*.local           # All .env.local files
.env             # Environment files
dist/            # Build output
node_modules/    # Dependencies
```

### Secret Detection:
If you accidentally commit a secret:
1. **Immediately rotate** the API key
2. Revoke the old key at https://ai.google.dev/
3. Generate a new key
4. Update Cloud Run environment variables
5. Use `git filter-branch` or BFG Repo-Cleaner to remove from history

## API Key Rotation

If your API key is exposed:

1. **Revoke old key**:
   - Go to https://ai.google.dev/
   - Find the exposed key
   - Click "Revoke"

2. **Generate new key**:
   - Create new API key
   - Download securely

3. **Update everywhere**:
   - Local `.env.local`
   - Cloud Run environment variables
   - AI Studio project settings

4. **Clean git history** (if committed):
   ```bash
   # Install BFG Repo-Cleaner
   # Remove sensitive data from history
   bfg --replace-text sensitive.txt
   ```

## Conversation Logs

**WARNING**: This conversation may contain exposed API keys in earlier messages.

**Action Required**:
- Clear conversation history if API key was displayed
- Rotate the exposed key immediately
- Do not share conversation logs

## Cloud Run Security

### Environment Variables:
- Set via Cloud Run console (not in code)
- Use Secret Manager for production
- Enable VPC for private APIs

### IAM Permissions:
- Restrict who can view/edit environment variables
- Use service accounts with minimal permissions
- Enable Cloud Run authentication

## Monitoring

### Check for exposed secrets:
```bash
# Scan codebase for potential leaks
grep -r "AIza" . --exclude-dir=node_modules
grep -r "GEMINI_API_KEY.*AIza" . --exclude-dir=node_modules
```

### Use secret scanners:
- GitHub Secret Scanning (if using GitHub)
- GitGuardian
- TruffleHog

## WSP Compliance

**WSP 71: Secrets Management Protocol**
- All secrets must be externalized
- No hardcoded credentials
- Use secure credential stores
- Audit secret access

## Contact

If you discover a security issue:
1. Do NOT create a public issue
2. Rotate any exposed credentials immediately
3. Document the incident internally
4. Review and update security practices

---

**Last Updated**: GotJUNK? module integration
**Security Status**: ✅ No secrets in version control

## 2026-10-10 authorization remediation and release contract

- `firestore.rules` is the editing authority. Firebase forbids deployment rules
  outside its project root, so the frontend configuration uses its local
  `frontend/firestore.rules` mirror. The emulator suite checks exact equality;
  update both together and do not deploy a stale copy.
- Storage writes now use `items/{Firebase UID}/{item ID}` and require that UID.
  Existing device-ID image URLs stay publicly readable. Do not mass-delete or
  migrate old objects; they require a separate authenticated ownership migration.
- Public discussion threads allow one append-only message per transaction from
  its authenticated author. Only the thread owner changes lifecycle/deletes the
  thread. The client transaction preserves concurrent messages. Older local
  messages with placeholder author IDs are retained locally but are not claimed
  as authenticated messages or silently republished.
- Each principal can append one moderation vote. Clients cannot set global
  moderation outcomes or counters. Trusted aggregation is a separate backend
  capability; the existing local display threshold is not authoritative.
- Reservations bind the caller, cannot steal another live reservation, and expire
  within five minutes of server time. Client clock skew outside the allowed
  window fails closed. Whole-item synchronization preserves separately managed
  reservations/votes and does not claim another user's item.
- The separate Liberty Alert Python API verifies Firebase ID-token signatures,
  audience, issuer and subject. Configure `FIREBASE_PROJECT_ID` for the actual
  frontend Firebase project (`GOOGLE_CLOUD_PROJECT` is a fallback). Missing
  identity configuration returns 503. Send the current Firebase ID token in the
  Authorization Bearer header; never put tokens in URLs. Configure exact browser
  origins in `GOTJUNK_ALLOWED_ORIGINS`; absent configuration grants no cross-origin
  browser access. No production project/credential is guessed by this change.
- API bodies are limited to 1 MiB before parsing, including chunked uploads.
  Writes are limited to ten per minute per UID and direct peer address; the
  bounded limiter is per process, not a global distributed quota. Before public
  deployment, configure ingress/edge limits across replicas and verify the real
  proxy peer behavior. Caller-controlled forwarding headers are not trusted.
  The existing video endpoint remains a placeholder, not persistent video storage.
- Cesium's map test requires explicit `VITE_CESIUM_ION_TOKEN`. It is a public
  browser token and must have restricted scopes/origins. The committed fallback
  was removed. Previously published tokens still require issuer-side revocation.

### Repeatable offline security tests

Use an isolated tools directory outside the repository for `firebase-tools@14`,
`@firebase/rules-unit-testing@4`, `firebase@11` and `typescript@5.9.3`; Java 17 or newer
is required by that pinned emulator CLI. Set `SECURITY_NODE_MODULES` to that
installation's `node_modules`. No production credentials are needed.

```sh
firebase emulators:exec --only firestore,storage --project demo-gotjunk-security \
  --config modules/foundups/gotjunk/firebase.security-tests.json \
  'node modules/foundups/gotjunk/tests/security_rules.mjs'
python -m pytest modules/foundups/gotjunk/tests/test_backend_security.py -q --noconftest
```

The Python suite needs the backend requirements, pytest and httpx. Emulator tests
cover unauthorized storage overwrite/deletion, ownership changes, message
impersonation/history replacement, concurrent message/vote sync, forged votes,
reservation theft and excessive expiration, plus authorized control cases.
Local test success does not prove deployed Firebase rules, API authentication,
edge rate limits or old-token revocation. Deploy rules and matching clients in
one reviewed release and verify with two separate test identities.
