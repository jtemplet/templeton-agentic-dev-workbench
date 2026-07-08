---
description: "Safely operate the production apps (atlas, meridian, compass, ...) on the Hetzner VPS over SSH: service ops and PostgreSQL data ops under strong guardrails."
---

Load the `production-ops` skill via the Skill tool and follow it end to end.

The skill connects to the production Hetzner VPS (two-hop: `ssh root@<host>` then
`su - deploy`), operates the Docker Compose stack for the requested app in the deploy
user's home (`~/atlas`, `~/meridian`, ...), and covers two change categories:

- **Service ops** - status, logs, restart, `up -d`, recreate
- **PostgreSQL data ops** - migrations, backups, one-off data fixes

Safety invariants enforced by the skill:

- Read-only by default; every mutating command is classified, confirmed, and verified
- Secret-free connection via the `hetzner-prod` SSH alias; the IP never lands in git or chat
- Mandatory fresh `pg_dump` before any data mutation, with the path recorded
- One-off writes run in a transaction with a `WHERE` clause and a matched row count
- Hard-stop (refuse + escalate) on `down -v`, volume/`prune` wipes, `DROP`/`TRUNCATE`,
  and `WHERE`-less `UPDATE`/`DELETE`
- A concrete rollback command handed over for every risky change

## Usage

```text
/prod-ops
```

Then describe the task, e.g. "restart the web service on atlas", "tail meridian logs",
"run pending migrations on compass", or "archive stale widgets in atlas".

## Prerequisite (one time)

Add a `hetzner-prod` alias to `~/.ssh/config` so the production IP stays on your machine
and out of this repo:

```sshconfig
Host hetzner-prod
    HostName <ip>
    User root
    IdentityFile ~/.ssh/<key>
    IdentitiesOnly yes
```

## When Not to Use

- Local development or CI (this targets the live production host)
- Editing application source code (ship through your normal deploy pipeline instead)
- Bulk destructive operations (the skill refuses these by design)
