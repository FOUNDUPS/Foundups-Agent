# Private draft sender: host admission and proof

This process is separate from the existing read-only Holo MCP server. It has
one fixed mailbox, one configured From address and one exact draft revision.
No tenant, OAuth credential, address, draft ID, content or tunnel identity is
provided by this repository.

## Host and consent

1. Select an authorized private host and service identity, a supported
   security-patched Python 3.12+ with current TLS/CA support, and an isolated
   virtual environment. Install `requirements-draft-sender.txt`, verify
   `pip check`, audit the resolved dependency set, and record the interpreter
   and TLS version. Do not reuse the Holo environment. Review the
   [MCP SDK security advisories](https://github.com/modelcontextprotocol/python-sdk/security/advisories)
   during qualification. The current pin addresses known HTTP audience,
   session and request-size issues; production still requires host admission.
2. Obtain separate Google OAuth consent for the exact account using
   `gmail.compose` and `gmail.settings.basic`. Both are
   [restricted Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes);
   Google may require app verification. The first covers draft access, the
   second covers the [send-as lookup](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.settings.sendAs/list).
   The underlying grant can do more than this adapter. Use a dedicated grant
   and revoke it when the correction is complete. Do not reuse connector tokens.
3. Admit a separate OAuth issuer for MCP with browser-reachable discovery,
   Authorization Code + PKCE, a fixed ChatGPT client registration and an
   HTTPS RFC 7662 endpoint. Issue an access token for the exact tunnel MCP
   resource (including its path) and one admitted subject. Introspection must
   return active, issuer, subject, client, sole audience, expiry, token type
   and scopes. A distinct confidential introspection client is required. The
   Google access token is never a caller token and caller tokens are never sent to Google.
4. From a trusted private provider review, obtain the SHA-256 of the exact
   decoded Gmail raw MIME revision. Review all parts and confirm the target
   against the approved account and case. The service then independently
   lists drafts and proves exactly one byte-identical match. Missing,
   changing, oversize and ambiguous inventory all hold. The service never
   searches by subject or accepts a historical message ID as a draft ID.
5. Prepare a service-owned, absolute state directory outside Git. Restrict
   OS access to the service identity and authorized administrators (0700 on
   POSIX; independently verify the Windows ACL and no reparse points).
   Create a fresh Fernet key through the authorized secret store; keep it
   outside the journal and retain recovery access separately. Use one
   supervisor instance and one journal for this correction. The journal
   records one attempted operation and an authenticated encrypted pre-edit
   snapshot. It is not the correspondence continuity store. Review retention,
   encrypted backups and eventual destruction before admitting private data.

## Service configuration

The following are **environment variable names only**. The existing service
manager injects values from its private configuration and secret store;
avoid shell history, command-line flags, crash dumps, shared developer env
files, and verbose HTTP logging. The process does not load repository dotenv files.

| Variable (`FOUNDUPS_DRAFT_` prefix) | Meaning |
| --- | --- |
| `MCP_ISSUER`, `MCP_RESOURCE` | Exact HTTPS issuer and externally addressed MCP resource |
| `INTROSPECTION_URL` | Fixed trusted HTTPS RFC 7662 endpoint |
| `MCP_SUBJECT`, `MCP_CLIENT_ID` | One allowed issuer subject and ChatGPT OAuth client |
| `INTROSPECTION_CLIENT_ID`, `INTROSPECTION_CLIENT_SECRET` | Distinct introspection credential |
| `GMAIL_ACCOUNT`, `APPROVED_SENDER` | Exact canonical mailbox and allowed From address |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | Dedicated consented Google credential |
| `TARGET_SHA256` | Approved revision's 64-character raw MIME digest |
| `STATE_DIR`, `SNAPSHOT_KEY` | Private journal directory and separately stored Fernet key |
| `APPROVED_REQUEST_ID`, `APPROVAL_ISSUED`, `APPROVAL_EXPIRES` | Optional one-shot write approval; issue and expiry are UTC epoch seconds and the window is at most 900 seconds |

Leave all three approval variables unset for inspection and dry run. Only an
authorized operator can stage them after reviewing the exact preview. A new
request ID never resets a prior attempt. Approvals apply to the configured
account, exact original MIME digest, approved sender and admitted caller.

Use the [opt-in systemd example](private-draft-mcp.service.example) on an
authorized Linux host. Its environment file carries private nonsecret
configuration only; the four secret values come from the supervisor's
encrypted credential store. Alternatively, configure the existing Windows service manager to
run the same module command with the dedicated interpreter, working directory
and private configuration; inject the four secret values from an authorized vault. Do not bind to another interface. The
`/health` route is process liveness only. Run the tunnel as a separate
supervised process so neither process belongs to a Codex terminal.

## Tunnel and ChatGPT registration

Use an approved [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
associated with the exact Platform organization and target ChatGPT workspace.
The operator needs Tunnels Read + Use and workspace permission for custom
MCP. Configure a dedicated HTTP profile using the installed client's
`help quickstart` and the documented HTTP target option. The minimum private
[profile settings](https://github.com/openai/tunnel-client/blob/master/docs/configuration.md)
are `MCP_SERVER_URL=http://127.0.0.1:8178/mcp`, the approved
`CONTROL_PLANE_TUNNEL_ID`, and `MCP_OAUTH_TRUSTED_ORIGINS` limited to
the admitted issuer origin. Configure no additional MCP channels or generic
HTTP callout targets. Inject the approved control-plane key into the
tunnel process only. Run `tunnel-client doctor --profile <profile> --explain`,
then supervise `tunnel-client run --profile <profile>`. Leave the admin listener
private. Verify that the tunnel preserves OAuth discovery and forwards to the
configured loopback Host without adding an unapproved Origin.

In [ChatGPT custom MCP setup](https://developers.openai.com/api/docs/guides/custom-mcp-server),
register the private app **FoundUps Private Draft Sender**, select **Tunnel**
and the exact approved tunnel, choose **OAuth** (not anonymous or mixed),
and configure the approved registration for `draft:read` and, where allowed,
`draft:write`. A read token can inspect and preview on the server; ChatGPT may
request write scope for the preview tool because the same tool can commit.
Restrict installation to the approved account/workspace, review workspace
retention/compliance for addresses and metadata, and keep write confirmation
enabled. Tunnel connectivity is not caller authorization.

## Qualification and recovery

- First prove initialization, discovery of exactly the two tools, OAuth
  rejection and dry run with synthetic data. Verify denied routes, redaction,
  expected trust roots, service account, private state and supervision.
- With the independent runtime healthy, use the private ChatGPT app to
  inspect and preview. Confirm the draft ID, digest, sender and attachment
  manifest against provider evidence. Pause editing the draft elsewhere.
- After an authorized operator stages the one-shot grant, invoke the exact
  request with `dry_run=false`. Verify the same draft ID, new underlying
  message ID, exact after bytes, original provider thread ID and the approved
  sender. Gmail does not document a conditional PUT; a local reservation
  and immediate reread cannot eliminate a race with another Gmail client.
- If Gmail normalizes bytes, the update times out, the final compare fails,
  or readback differs, hold. Do not retry or restore via MCP. Retain the
  encrypted snapshot and reservation; a supervisor reconciles the mailbox
  and uses an independent, separately authorized recovery path. A repeated
  request can read back matching state; it cannot issue another PUT.
- Observe both supervisors from a separate operator session; stop Codex,
  invoke the ChatGPT inspection again, then restart the service and tunnel
  in turn and confirm reconnect and durable reservation. Record only
  redacted statuses and counts. Revoke the write approval and Google grant,
  unlink the app when appropriate, and stop the private supervisors when
  the authorized task ends.

Local synthetic transport checks do not prove tunnel admission, real OAuth
consent, a live sender correction, or operation with Codex stopped.
