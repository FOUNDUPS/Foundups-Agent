# OBAI Discord Permission Boundary

Worker: Z
Date: 2026-04-07
Parent: OBAI_DISCORD_BOT_SPEC_PHASE1.md

## 1. Discord Application Permissions

OBAI's managed role permission integer: **311452617792**

### Granted Permissions

| Permission | Bit | Granted |
|------------|-----|---------|
| VIEW_CHANNEL | 1 << 10 | YES |
| SEND_MESSAGES | 1 << 11 | YES |
| SEND_TTS_MESSAGES | 1 << 12 | YES |
| EMBED_LINKS | 1 << 14 | YES |
| ATTACH_FILES | 1 << 15 | YES |
| READ_MESSAGE_HISTORY | 1 << 16 | YES |
| ADD_REACTIONS | 1 << 6 | YES |
| USE_EXTERNAL_EMOJIS | 1 << 18 | YES |
| USE_SLASH_COMMANDS | 1 << 31 | YES |
| CREATE_PUBLIC_THREADS | 1 << 35 | YES |
| CREATE_PRIVATE_THREADS | 1 << 36 | YES |
| SEND_MESSAGES_IN_THREADS | 1 << 38 | YES |
| CHANGE_NICKNAME | 1 << 26 | YES |
| CONNECT | 1 << 20 | YES |
| SPEAK | 1 << 21 | YES |
| USE_EXTERNAL_STICKERS | 1 << 37 | YES |

### Denied Permissions (NEVER grant these to OBAI)

| Permission | Bit | Status | Reason |
|------------|-----|--------|--------|
| ADMINISTRATOR | 1 << 3 | DENIED | OBAI must never have admin |
| KICK_MEMBERS | 1 << 1 | DENIED | No moderation |
| BAN_MEMBERS | 1 << 2 | DENIED | No moderation |
| MANAGE_CHANNELS | 1 << 4 | DENIED | No server mutation |
| MANAGE_GUILD | 1 << 5 | DENIED | No server mutation |
| MANAGE_MESSAGES | 1 << 13 | DENIED | No moderation |
| MANAGE_ROLES | 1 << 28 | DENIED | No role assignment |
| MANAGE_WEBHOOKS | 1 << 29 | DENIED | No webhook control |
| MANAGE_EXPRESSIONS | 1 << 30 | DENIED | No server mutation |
| MANAGE_NICKNAMES | 1 << 27 | DENIED | No moderation |
| MENTION_EVERYONE | 1 << 17 | DENIED | No mass pings |
| MANAGE_THREADS | 1 << 34 | DENIED | No thread moderation |
| MANAGE_EVENTS | 1 << 33 | DENIED | No event management |

## 2. Channel-Level Overrides

Beyond the managed role, channel permission overwrites further restrict OBAI:

| Channel | Override | Effect |
|---------|----------|--------|
| #swarm-work | SEND_MESSAGES denied for @everyone | OBAI cannot post in main channel; can post in threads |
| #swarm-github | SEND_MESSAGES denied for @everyone | OBAI cannot post; read-only feed |
| Operator channels | VIEW_CHANNEL denied for non-operators | OBAI cannot see these channels |

## 3. Runtime Permission Enforcement

The OBAI bot code MUST also enforce permission boundaries at the application level,
not relying solely on Discord's permission system:

| Rule | Enforcement |
|------|-------------|
| Never call admin API endpoints | Code-level blocklist |
| Never attempt role modifications | No Discord role API calls |
| Never attempt channel modifications | No channel PATCH/DELETE calls |
| Never attempt member kick/ban | No member removal API calls |
| Never DM users | No DM channel creation |
| Never mention @everyone or @here | Message content validation |

## 4. Token Security

| Rule | Detail |
|------|--------|
| Token env var | DISCORD_BOT_TOKEN_OBAI |
| Token storage | .env file only, never in code or config files |
| Token in logs | NEVER — redact in all log output |
| Token in chat | NEVER — do not display, reference, or hint at token value |
| Token rotation | Reset in Developer Portal if suspected compromise |
| Shared with 0102 | NEVER — separate tokens, separate applications |

## 5. Escalation Path

If OBAI encounters a situation requiring admin action:

1. OBAI does NOT attempt the action
2. OBAI responds with: "This requires operator action. Please contact the server operator."
3. Future: OBAI posts to an internal escalation channel readable by 0102
4. OBAI never claims it "will handle" admin tasks
