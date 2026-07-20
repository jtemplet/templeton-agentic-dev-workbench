---
name: production-ops
description: Safely operate the production apps (atlas, meridian, compass, ...) running as Docker Compose stacks on a single Hetzner VPS, over SSH. Access is two-hop (SSH in as root, then su - deploy); each app is a Compose stack in the deploy user's home (~/atlas, ~/meridian, ...). Covers service ops (status, logs, restart, up/down) and PostgreSQL data ops (migrations, backups, one-off data fixes) under strong guardrails: read-only by default, secret-free connection, mandatory backup before any data mutation, verify-after, and a written rollback for every risky change. Use when asked to check, restart, deploy-restart, inspect, or change anything on the production VPS.
---

# Production Ops (Hetzner VPS)

A systematic, guardrailed technique for operating production apps that run as Docker
Compose stacks on a single VPS, reached over SSH. This skill covers two change categories:
**service ops** (status, logs, restart, recreate) and **PostgreSQL data ops** (migrations,
backups, one-off data fixes). The posture is deliberately conservative: you are touching
production, so read-only is the default and every mutation is confirmed, backed up, and
reversible.

Everything below is generic technique. The host-specific facts (which host, how you log
in, where the apps live) are pinned in the **Environment Profile** just below and nowhere
else, so the runbook reads from one source of truth. To retarget this skill at a different
setup, edit that block; the technique does not change.

## Environment Profile

The only host-specific facts. Command blocks in this skill are illustrations of this
profile; if a literal below (`su - deploy`, `~/atlas`, `PostgreSQL`) ever disagrees with
this table, this table wins. Discoverable facts (exact app paths, service names, DB
credentials) are intentionally left to runtime discovery in Step 2, not pinned here.

| Fact | Value |
| --- | --- |
| Connection | `hetzner-prod` SSH alias (defined in `~/.ssh/config`; see Step 0) |
| Login user | `root` |
| Post-login hop | `su - deploy` (log in as root, then drop to the `deploy` user for all work) |
| App location | `~/<app>` in the `deploy` user's home (e.g. `~/atlas`) |
| Known apps | `atlas`, `meridian`, `compass`, and any siblings found by `ls ~` |
| Runtime | Docker Compose v2 (one stack per app directory) |
| Compose services | `app`, `nginx`, `postgres`, `redis` per stack (confirm per app in Step 2; names can differ) |
| DB engine | PostgreSQL, service named `postgres` (not `db`) |
| Container names | prefixed `hdw-` (e.g. `hdw-app`, `hdw-postgres`, `hdw-nginx`, `hdw-redis`) for raw `docker` commands |
| Secrets policy | IP and keys live only in `~/.ssh/config` or a gitignored env file, never in this repo |

> **If you are adapting this skill to a host with no `deploy` hop**, delete "Post-login hop"
> and replace the `su - deploy ...` wrappers below with a direct command. If the runtime is
> not Compose or the DB is not PostgreSQL, the Step 4 runbooks are the parts to rewrite; the
> classification gate (Step 3) and the golden rules stay as-is.

## When to Use

- Checking the health, status, or logs of a production app
- Restarting a service, or recreating a stack to pick up a rebuilt image
- Running a database migration for an app
- Taking a database backup, or restoring from one
- Applying a one-off data fix in production (highest-risk category)

## When NOT to Use

- Local development or CI (this skill assumes the live production host)
- Editing application source code (do that in the repo, ship through your normal deploy;
  this skill operates what is already deployed)
- Anything on a host this skill has not been told about (it targets exactly one VPS)
- Bulk destructive operations (volume wipes, `prune`, `DROP`/`TRUNCATE`): these are
  hard-stops, see Critical Rules

## Golden Rules (read first, every time)

1. **Read-only until proven otherwise.** Classify every command before running it
   (see Step 3). Inspecting is free; mutating is not.
2. **Never mutate without an explicit go-ahead.** Print the exact command, state its blast
   radius, and get the user's confirmation before running anything that changes state.
3. **Back up before you change data.** No migration, no `UPDATE`/`DELETE`, no restore
   runs until a fresh `pg_dump` exists and its path is recorded.
4. **Have the rollback written down before you run the risky thing**, not after.
5. **One-shot, non-interactive commands only.** Run remote work through the exec pattern
   below; never open an interactive shell, never leave a background session, never pipe an
   editor over SSH.
6. **Redact the host.** Refer to it as `hetzner-prod` in all output. Never print the raw
   IP or `root@ip` in reports or chat.

## Step 0: Resolve the Connection (secret-free)

The host is referenced only through an SSH alias, so no IP or key ever lands in this repo
or in chat. The live login is `ssh root@<ip>`, then `su - deploy`.

1. **Set up (one time, on the user's machine only).** The alias maps to the root login;
   the IP stays in `~/.ssh/config`, never in git:

   ```sshconfig
   Host hetzner-prod
       HostName <ip>          # the production IP; lives only here
       User root
       IdentityFile ~/.ssh/<key>
       IdentitiesOnly yes
   ```

2. **Verify it resolves and is reachable:**

   ```bash
   ssh -G hetzner-prod >/dev/null 2>&1 \
     && ssh -o BatchMode=yes -o ConnectTimeout=8 hetzner-prod true \
     && echo "reachable" || echo "NOT reachable"
   ```

3. **Fallback: gitignored env file.** If the alias is not configured, read the target from
   a local, gitignored file (never committed), still referring to the host as
   `hetzner-prod` in output:

   ```bash
   # ~/.config/hetzner-prod.env  ->  HETZNER_SSH_TARGET=root@<ip>
   set -a; . "$HOME/.config/hetzner-prod.env"; set +a
   ```

4. **If neither resolves, stop and ask the user to add the alias** (offer the snippet
   above). Do not paste a raw IP into the committed skill or the report.

## The Canonical Remote-Exec Pattern

This pattern is the Environment Profile's "Login user" and "Post-login hop" made concrete:
log in as `root`, then run everything as `deploy`. If the profile's hop changes, this is the
one place the wrapper changes. Two forms, both non-interactive and one-shot:

**Simple, quote-free commands** use `su - deploy -c`:

```bash
ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose ps"'
```

**Anything with its own quotes, SQL, or multiple statements** pipes a heredoc script into
`su - deploy` over stdin. This avoids nested-quote escaping entirely (root can `su` to
`deploy` without a password, so no TTY is needed):

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
docker compose exec -T postgres psql -U app -d app -c "SELECT count(*) FROM users;"
REMOTE
```

Use the quoted delimiter `<<'REMOTE'` so `$(...)` and `$VARS` evaluate **on the host**, not
locally. To substitute an app name, edit the script text before sending it. Throughout the
rest of this skill, remote command blocks assume this pattern; `~/<app>` means the stack
directory in the `deploy` user's home.

## Step 1: Preflight

Before any task, take a read-only snapshot of the host so you are operating on facts, not
assumptions:

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
whoami
uptime
df -h / /var/lib/docker 2>/dev/null | sort -u
docker version --format '{{.Server.Version}}'
docker compose version --short
echo "--- stacks ---"
docker compose ls 2>/dev/null || docker ps --format 'table {{.Names}}\t{{.Status}}'
REMOTE
```

Flag anything alarming before proceeding: disk over ~85%, Docker daemon unreachable, or
the target app not appearing. A near-full disk is a stop condition for any data op (a
`pg_dump` needs room). If `docker` is not runnable as `deploy`, stop and report it (the
deploy user may not be in the `docker` group).

## Step 2: Locate the Target Stack

Apps live one-directory-per-app in the `deploy` home (`~/atlas`, `~/meridian`, ...).
Discover, do not assume, the path and service names:

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
ls -1 ~                         # confirm the app dir names
cd ~/atlas                      # atlas | meridian | compass | ...
echo "--- services ---"
docker compose config --services
echo "--- status ---"
docker compose ps
REMOTE
```

Record for this task:

- The stack directory (e.g. `~/atlas`)
- The **app service name** (for logs, restarts, migrations; `app` on the atlas stack)
- The **database service name** — discover it, do not guess:

  ```bash
  ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose config --services | grep -iE \"postgres|pg|db|database\" || true"'
  ```

If the directory or a service cannot be found, stop and report what `ls ~` and
`docker compose ls` actually returned. Do not proceed on a guessed path.

## Step 3: Classify the Change (routing gate)

Put the intended change into exactly one bucket. This decides how much ceremony applies.

| Bucket | Examples | Ceremony |
| --- | --- | --- |
| **READ-ONLY** | `ps`, `logs`, `config`, `df`, `SELECT`, health checks | Run freely, no confirmation |
| **SERVICE-MUTATING** | `restart`, `up -d`, `stop`/`start`, `up -d --force-recreate` (no volume change) | Confirm + verify after (Step 4a) |
| **DATA-MUTATING** | migrations, `UPDATE`/`DELETE`, restore, anything touching a volume | Backup + confirm + verify + rollback (Step 4b) |
| **HARD-STOP** | `down -v`, `volume rm`, `system prune`, `DROP`/`TRUNCATE`, `UPDATE`/`DELETE` without `WHERE` | Refuse; escalate to user (see Critical Rules) |

If a request is ambiguous, treat it as the more dangerous bucket until clarified.

## Step 4a: Service Ops Runbook

**Read-only (run freely):**

```bash
ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose ps"'
ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose logs --tail=200 --no-color app"'
ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose config"'   # redact secrets before pasting
```

**Service-mutating (confirm first, verify after):**

1. State the intent and blast radius, e.g. "Restart `app` in `~/atlas`. Brief downtime for
   that service only; no data touched." Get confirmation.
2. Run the smallest command that achieves the goal:

   ```bash
   ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose restart app"'
   # or, to pick up a newly pulled/rebuilt image:
   ssh hetzner-prod 'su - deploy -c "cd ~/atlas && docker compose up -d app"'
   ```

   Prefer targeting a single service. A bare `docker compose up -d` (no service) is
   acceptable to reconcile a whole stack, but `--force-recreate` across a stack is
   service-mutating and must be confirmed as such.
3. **Verify** (Step 5).

Note: `docker compose down` (without `-v`) stops and removes containers but keeps named
volumes. It still causes downtime for the whole stack, so it is service-mutating and must
be confirmed. `down -v` is a HARD-STOP (it deletes data volumes).

## Step 4b: PostgreSQL Data Ops Runbook

This is the highest-risk category. Order is fixed: **backup, then confirm, then apply,
then verify, then hand over the rollback.**

**1. Take a fresh backup first (mandatory).** Fill in the db service/user/name discovered
in Step 2:

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
DB=postgres; DBUSER=app; DBNAME=app   # DBUSER/DBNAME: confirm from container env (below)
mkdir -p backups
TS=$(date -u +%Y%m%d-%H%M%SZ)
OUT="backups/${DBNAME}-${TS}.sql.gz"
docker compose exec -T "$DB" pg_dump -U "$DBUSER" -d "$DBNAME" --clean --if-exists | gzip > "$OUT"
ls -lh "$OUT"; echo "BACKUP=$OUT"
REMOTE
```

Record `BACKUP=<path>`. If the dump is suspiciously small or the command errors, **stop**
and do not proceed with the mutation. Discover DB user/name from the container env if not
known (password redacted):

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
docker compose exec -T postgres sh -lc 'printenv | grep -iE "POSTGRES_(USER|DB)"'
REMOTE
```

**2a. Migrations.** Run the app's own migration command inside the app container (do not
hand-write DDL). Identify it first (Rails `bin/rails db:migrate`, Django `manage.py migrate`,
node/knex/prisma, sqitch, etc.):

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
docker compose exec -T app <migrate-command>        # atlas is Python; use its migrator (alembic upgrade head, manage.py migrate, etc.)
REMOTE
```

**2b. One-off data fixes.** Never fire a bare `UPDATE`/`DELETE`. Preview, then apply inside
a single transaction so a wrong count can be rolled back:

```bash
# i. PREVIEW: count exactly what you are about to touch (read-only)
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
docker compose exec -T postgres psql -U app -d app -c "SELECT count(*) FROM widgets WHERE status = 'stale';"
REMOTE

# ii. APPLY in a transaction, same predicate; the UPDATE count MUST match the preview
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
docker compose exec -T postgres psql -U app -d app -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE widgets SET status = 'archived' WHERE status = 'stale';
-- inspect the reported UPDATE count; it MUST match the preview count from step i
COMMIT;
SQL
REMOTE
```

If the affected-row count does not match the preview, `ROLLBACK` instead of `COMMIT` and
re-investigate. Always include a `WHERE` clause. A `WHERE`-less `UPDATE`/`DELETE` is a
HARD-STOP.

**3. Verify** (Step 5).

**4. Hand over the rollback.** Every data op ends with a concrete restore command tied to
the backup from step 1:

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
gunzip -c backups/app-<ts>.sql.gz | docker compose exec -T postgres psql -U app -d app
REMOTE
```

State plainly that a full restore reverts *all* changes since the dump; for a targeted fix
a narrower corrective statement is usually preferable to a full restore.

## Step 5: Verify After Every Mutation

Confirm the change did what was intended and nothing else broke:

```bash
ssh hetzner-prod 'su - deploy' <<'REMOTE'
set -euo pipefail
cd ~/atlas
docker compose ps                                   # all expected services Up/healthy
docker compose logs --tail=80 --no-color app        # no new errors / crash loops
REMOTE
```

For data ops, re-run the preview `SELECT` and confirm the new state matches the intended
outcome. If a health endpoint exists, hit it from the host:

```bash
ssh hetzner-prod 'su - deploy -c "curl -fsS -m 10 http://localhost:<port>/health || echo HEALTHCHECK_FAILED"'
```

If verification fails, execute the rollback from Step 4b (or restart from Step 4a) and
report.

## Step 6: Report

Produce this every time, including read-only sessions:

```markdown
## Production Ops Session

**Host:** hetzner-prod        **App:** <app>  (~/<app>)
**Timestamp:** <ISO-8601 UTC>
**Change class:** read-only | service-mutating | data-mutating

### What I did
- <command / action>  ->  <result>

### Backup (data ops only)
- Path: ~/<app>/backups/<db>-<ts>.sql.gz  (size: <n>)

### Verification
- Services: <all up / details>
- Logs: <clean / notable lines>
- Data check: <preview vs. post-change counts>

### Rollback
- <exact command to revert, or "none needed (read-only)">

### Follow-ups for the user
- <anything manual / anything I refused and why>
```

## Command Reference

**Access:**

```bash
ssh hetzner-prod 'su - deploy -c "cd ~/<app> && <simple command>"'   # quote-free
ssh hetzner-prod 'su - deploy' <<'REMOTE' ... REMOTE                 # scripts / SQL / quotes
```

**Docker Compose (v2), run as deploy inside `~/<app>`:**

```bash
docker compose ls                       # all stacks
docker compose ps                       # services in this stack
docker compose config --services        # service names
docker compose logs --tail=N --no-color <svc>
docker compose restart <svc>            # service-mutating
docker compose up -d [<svc>]            # service-mutating (reconcile / pick up new image)
docker compose down                     # service-mutating (stops stack, KEEPS volumes)
docker compose exec -T <svc> <cmd>      # run inside a container, non-interactive
```

**PostgreSQL (via the db container):**

```bash
docker compose exec -T <db> pg_dump -U <user> -d <name> --clean --if-exists | gzip > backups/<name>-<ts>.sql.gz
gunzip -c <dump.gz> | docker compose exec -T <db> psql -U <user> -d <name>     # restore
docker compose exec -T <db> psql -U <user> -d <name> -c "<read-only SQL>"
docker compose exec -T <db> psql -U <user> -d <name> -v ON_ERROR_STOP=1 <<SQL ... SQL   # transactional write
```

## Critical Rules

**Always:**

- Reference the host only as `hetzner-prod`; never print the raw IP or `root@ip`
- Run one-shot, non-interactive commands through the exec pattern (`su - deploy -c` or the
  heredoc form); never an interactive shell
- Discover paths and service names (`ls ~`, `docker compose config --services`); never assume
- Classify every command (Step 3) before running it
- Take a fresh `pg_dump` and record its path before any data mutation
- Confirm the exact command and its blast radius before any service- or data-mutating op
- Wrap one-off data fixes in a transaction with a `WHERE` clause, previewing the row count first
- Verify after every mutation, and hand over a concrete rollback command
- Produce the session report every time, even for read-only work

**Never:**

- Run `docker compose down -v`, `docker volume rm`, `docker system prune`, or any
  volume-destroying command (HARD-STOP: refuse and escalate)
- Run `DROP`, `TRUNCATE`, or a `WHERE`-less `UPDATE`/`DELETE` (HARD-STOP)
- Mutate data without a fresh backup taken in the same session
- Open an interactive remote shell, leave a background process, or pipe an editor over SSH
- Commit the production IP or key to this repo (connection stays in `~/.ssh/config` or a
  gitignored env file)
- Proceed on a guessed app path or DB service name
- Restore over a live database without a fresh dump taken first

## Quality Checklist

Before reporting completion, verify:

- [ ] Connection resolved via the `hetzner-prod` alias (or gitignored fallback); host redacted
- [ ] Preflight snapshot taken; disk had headroom for any data op
- [ ] Target app directory and service names were discovered, not assumed
- [ ] Every command was classified; nothing in the HARD-STOP set was run
- [ ] For data ops: a fresh `pg_dump` exists and its path is in the report
- [ ] Every mutating command was confirmed with its blast radius stated
- [ ] One-off writes ran in a transaction with a `WHERE` clause and a matched row count
- [ ] Post-change verification passed (services up, logs clean, data check matches intent)
- [ ] A concrete rollback command is in the report
- [ ] Session report produced
