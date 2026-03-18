# Container Isolation Module

NanoClaw-inspired container isolation for secure skill execution.

## Overview

This module provides ephemeral Docker container isolation for skill execution, following patterns from [NanoClaw](https://github.com/qwibitai/nanoclaw):

- **Per-skill containers**: Each skill runs in its own isolated container
- **Ephemeral execution**: Container created per invocation, destroyed after
- **Mount policy**: Only allowlisted directories visible to container
- **Unprivileged user**: Runs as `nobody` inside container
- **Defense-in-depth**: Blocklist is hard security layer, allowlist is configurable

## Architecture

```
Container Isolation
├── MountPolicy          # Allowlist/blocklist for directory mounts
│   ├── DEFAULT_BLOCKLIST  # Always blocked (.ssh, .aws, .env, etc.)
│   └── DEFAULT_ALLOWLIST  # Repo directories (modules, docs, etc.)
│
└── ContainerExecutor    # Ephemeral Docker container runner
    ├── execute()         # Run command in container
    ├── execute_python()  # Run Python code
    └── execute_skill()   # Run skill with isolation
```

## Usage

### Basic Execution

```python
from modules.infrastructure.container_isolation.src.container_executor import (
    ContainerExecutor,
    ContainerConfig,
)

executor = ContainerExecutor(repo_root=Path("."))

# Run command in isolated container
result = await executor.execute(["python", "-c", "print('Hello')"])
print(result.stdout)  # "Hello"
```

### With Custom Config

```python
config = ContainerConfig(
    image="python:3.12-slim",
    timeout_sec=30.0,
    memory_limit="1g",
    mounts=["/path/to/allowed/dir"],
)

result = await executor.execute(["ls", "-la"], config)
```

### Mount Policy

```python
from modules.infrastructure.container_isolation.src.mount_policy import (
    MountPolicy,
    MountDecision,
)

policy = MountPolicy(repo_root=Path("."))

# Check if path can be mounted
decision = policy.check_mount("/home/user/.ssh")
# Returns: MountDecision.BLOCKED_SENSITIVE

decision = policy.check_mount("modules/test")
# Returns: MountDecision.ALLOWED
```

## Security Features

### Blocked by Default

The following paths are **always blocked** (hard security boundary):
- `.ssh`, `.gnupg`, `.gpg`
- `.aws`, `.azure`, `.gcloud`, `.kube`
- `.env`, `.env.local`, `.env.production`
- `credentials`, `secrets`, `private_key`
- `id_rsa`, `id_ed25519`
- `.netrc`, `.npmrc`, `.pypirc`
- `token`, `api_key`, `password`

### Container Hardening

Containers run with:
- `--user nobody` (unprivileged)
- `--network none` (no network access)
- `--read-only` (read-only filesystem)
- `--security-opt no-new-privileges`
- `--cap-drop ALL` (no capabilities)
- `--memory 512m` (memory limit)
- `--cpus 1.0` (CPU limit)

### Environment Variable Filtering

Sensitive environment variables are filtered:
- Any key containing: `key`, `token`, `secret`, `password`, `credential`, `auth`, `api_key`, `private`

## Configuration

### Mount Policy Config

Custom allowlist/blocklist at `~/.config/foundups/mount-policy.json`:

```json
{
  "allowlist": ["my_custom_dir"],
  "blocklist": ["my_secrets_dir"]
}
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| N/A | Container isolation has no env vars | Uses Docker defaults |

## WSP Compliance

- **WSP 71**: Secrets Management - blocklist prevents secret exposure
- **WSP 95**: Skills Wardrobe - skills run in isolated containers
- **WSP 49**: Module Structure - standard module layout

## NanoClaw Philosophy

From NanoClaw (~3,900 LOC, auditable):

> "The container boundary is the hard security layer — the agent can't escape it regardless of configuration. On top of that, a mount allowlist acts as an additional layer of defense-in-depth."

This module follows the same philosophy:
1. Container is the hard boundary
2. Mount policy is defense-in-depth
3. Code should be auditable (~400 LOC)
