# p.fMALL External FoundUp Route Contract

**Status**: Architecture specification
**Owner**: 0102
**WSP References**: WSP 3 (Domains), WSP 11 (Interface Contract), WSP 49 (Structure), WSP 97 (Execution Discipline), WSP 102 (FoundUps Web Design)

---

## 1. Purpose

Define the runtime boundary between the installed p.fMALL shell and FoundUps
that may live in separate repositories.

This note locks the rule that repo separation does not require a fragmented user
experience.

---

## 2. Canonical Model

```text
Mall PWA = control shell
FoundUp = external product/app
Connection = metadata + task API + deep link
```

Not:

```text
FoundUp backend or product UI must live physically inside the Mall repo
```

The shell owns discovery, auth context, navigation, and cross-FoundUp control
surfaces.

The FoundUp owns its own product logic, task surface, data, and product-facing
UI.

---

## 3. Two Pipes

### 3.1 Control Pipe

The control pipe is how the Mall coordinates with a FoundUp's task and status
surface.

Preferred model:

```text
Mall -> FoundUp Registry API -> FoundUp metadata/task API -> Agent runtime
```

This pipe is used for:
- metadata
- preview/feed state
- task catalog
- agent assignment
- status updates
- join/follow/forum links
- permissions and auth context

Important:
- the Mall does not invent work for a FoundUp
- the Mall brokers requests into the FoundUp's exposed task/control surface

Example intent:

```text
assign my agent to this FoundUp using eligible default tasks
```

The implementation may use direct API calls, queue handoff, webhooks, or shell
brokering, but the contract boundary stays the same.

### 3.2 Experience Pipe

The experience pipe is how the user enters a FoundUp.

Preferred model:

```text
Mall -> in-scope route navigation -> FoundUp experience
```

This pipe is route-based, not repo-based.

If the FoundUp is entered through an in-scope route, it still feels like the
same installed app:
- shared app shell
- shared auth/session context where available
- shared gesture grammar
- shared AI/control shell

If the FoundUp is opened outside the app scope or on a separate origin, the
user experience degrades into an external browsing context.

That is fallback behavior, not the target model.

---

## 4. Route Contract

### 4.1 Preferred Route Family

Canonical route family:

```text
/f/{foundup_id}
/f/{foundup_id}/{path}
```

This matches the existing p.fMALL shell and routing documents.

### 4.2 Transitional Reality

Current static admitted entry flow still uses:

```text
/member/foundup.html?id={foundup_id}
```

Treat that as a transitional shell-owned entry surface.

It is not the long-term route contract for the full installed Mall experience.

### 4.3 In-Scope Rule

The FoundUp should be deployed to a route that remains inside the installed app
scope.

That preserves:
- same-app feel
- shared shell chrome
- cleaner double-tap enter behavior
- less auth/state friction

Out-of-scope or cross-origin navigation should be treated as an exception path,
not the primary architecture.

---

## 5. External Repo Model

Each FoundUp may live in its own repository.

That is acceptable and preferred once a FoundUp is externalized.

Correct model:

```text
Each FoundUp = separate repo
Each repo builds/deploys to a registered in-scope route
Mall indexes the route and metadata
Mall opens the FoundUp in-scope
```

Repo separation gives:
- independent code ownership
- independent deployment cadence
- cleaner FoundUp exfoliation

It does not require:
- separate installation per FoundUp
- separate top-level app identity
- loss of the Mall shell experience

---

## 6. Registry Contract

Each FoundUp should expose or be represented by one canonical registry record
containing at least:
- `foundup_id`
- `title`
- `route`
- `preview` or `video_feed`
- `geo`
- `tags`
- `capabilities`
- `task_endpoint`
- `forum` or `join_link`
- `repo_url`
- `deployment_status`

The shell uses this for:
- discovery
- routing
- permissions gating
- control-pipe targeting

---

## 7. Runtime Contract

Minimum external contract shape for FoundUps:
- `GET /metadata`
- `GET /feed`
- `GET /tasks`
- `POST /agent/assign`
- `GET /status`
- `GET /forum`

These do not need to be exposed directly to the public internet in phase 1.

They may sit behind shell mediation, API adapters, or authenticated service
contracts.

The important lock is:
- FoundUp business/runtime surfaces are contract-addressable
- the Mall shell does not absorb that business logic into itself

---

## 8. Relationship To Existing p.fMALL Docs

This note does not replace:
- `PFMALL_SHELL_CONTRACT.md`
- `PFMALL_ROUTING_DISCOVERY_MODEL.md`

Those documents already define:
- shell responsibilities
- route families
- shell-to-FoundUp messaging

This note adds the missing lock on:
- external repo compatibility
- in-scope deployment as the preferred experience path
- the split between control pipe and experience pipe

---

## 9. Relationship To SoftProto

SoftProto owns the shell-side interface layer.

It does not change this runtime boundary.

That means:
- SoftProto may reconfigure Mall, user panel, and shell controls
- SoftProto does not make external FoundUp business logic part of the Mall shell
- SoftProto command paths should target shell objects and shell-owned controls,
  not erase the product boundary between shell and FoundUp

---

## 10. Execution Rule

From this point forward, the correct architectural default is:

```text
Mall = installed shell
FoundUp repos = external or externalizable
Deployment = in-scope route
Control pipe = API/service contract
Entry pipe = route navigation
```

Do not collapse these roles into one repo-level assumption.
