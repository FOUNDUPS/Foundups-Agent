# Member Area Interface

**Module**: `public/member/`
**Version**: 2.0.0

## Public Interface

### Entry URL
```text
/member/
```

### Auth Requirements
- Clerk session required
- invite validation required
- username claim required before admitted users enter the Mall
- redirects to `/?signin=required` if not authenticated

### Runtime Surface

`/member/` is now the admitted-user p.fMALL shell hosted from Firebase static assets.

It owns:
- invite-gated post-auth landing
- swipe-driven FoundUp catalog
- tap-to-enter FoundUp entry page (deep-linkable)
- Red Dog concierge sheet for invite codes and account context

It does not yet own:
- direct tenant execution
- `/f/{foundup_id}` transport routing
- wallet or agent operations

### Hosted Assets

```text
/member/index.html
/member/foundup.html
/member/css/member.css
/member/mall-catalog.json
```

### JavaScript Surface

The page bootstraps these internal behaviors:
- `initClerkAuth()`
- `initializeMall(clerkUserId, userData, clerkUser)`
- `loadMallCatalog()`
- `loadInviteContext(clerkUserId, clerkUser)`

### Data Expectations

**Catalog source**
```json
/member/mall-catalog.json
```

**User document shape**
```typescript
interface UserDoc {
  email: string;
  username?: string;
  inviteValidated?: boolean;
  usedInviteCode?: string;
  inviteCodes: string[];
  waitlistJoined?: string;
  createdAt: string;
}
```

**Invite document shape**
```typescript
interface InviteDoc {
  code: string;
  status: "active" | "used";
  createdBy: string;
  createdAt: string;
  usedBy: string | null;
  usedAt: string | null;
}
```

### UI Contract

- primary navigation is horizontal swipe / scroll-snap movement across FoundUp cards
- primary explicit control is the Red Dog icon
- FoundUp cards are tappable and navigate to a dedicated entry page (`/member/foundup.html?id={foundup_id}`)
- invite gate and username claim remain blocking surfaces ahead of the Mall

---

*Last Updated: 2026-03-31*
