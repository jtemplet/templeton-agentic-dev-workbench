# Issue tracker: bd (beads)

Issues for this repo live in **bd (beads)**, a local Dolt database. They do not live in
GitHub Issues, and the GitHub remote carries code alone.

Where a tadw skill and a `mattpocock-skills` skill overlap, the tadw one wins. See
[skill-precedence.md](./skill-precedence.md).

Read [docs/beads-workflow.md](../beads-workflow.md) before running any tracker command. It
carries the full `bd` and `bv` command set, the scoping recipes, and the git policy.

## The three rules that outrank everything else here

1. **`.beads/issues.jsonl` is a passive export, not a source file.** The database is the truth.
   Never hand-edit the export, and never ask a person to run `bd export` or to sync the Dolt
   remote. An agent that needs the export current runs it itself, silently.
2. **Never use TodoWrite, TaskCreate, or a markdown TODO list for task tracking.** Every unit
   of work is a bead.
3. **Never run `bd edit`.** It opens `$EDITOR`, which blocks an agent forever. Use the inline
   `--title`, `--description`, `--design`, `--notes`, and `--acceptance` flags instead.

## Conventions

- Issue ids are prefixed `tadw-`, for example `tadw-pdi`.
- Types in use: `task`, `bug`, `feature`, `epic`, `chore`.
- Priority is `0`-`4` or `P0`-`P4`, where 0 is critical and 2 is medium. The words "high",
  "medium", and "low" are not valid values.
- Acceptance criteria, design notes, and supplementary notes go in the **native fields**
  (`--acceptance`, `--design`, `--notes`), never in the description body. This is binding:
  see [ADR 0001](../adr/0001-native-tracker-fields-are-canonical.md).
- Triage state is a label. See [triage-labels.md](./triage-labels.md).

## When a skill says "publish to the issue tracker"

```bash
bd create --title="<one line>" \
          --description="<why this exists and what needs doing>" \
          --type=task --priority=2 \
          --acceptance="<how we know it is done>" \
          --design="<decisions already made>"
```

**Use the repo's own `/bead-create` skill rather than a raw `bd create`,** and use it rather
than `mattpocock-skills:to-tickets` or `to-spec`. It searches for a duplicate first, grounds every claim against the code on `main`, drafts against the canonical
body structure, self-audits the draft, and reads the bead back to prove it landed.

Wire dependencies after creating, where one exists:

```bash
bd dep add <issue> <depends-on>     # <issue> is blocked by <depends-on>
```

## When a skill says "fetch the relevant ticket"

```bash
bd show <id>            # human-readable
bd show <id> --json     # machine-readable
bd search <query>       # find one by keyword
```

## Finding and claiming work

```bash
bd ready                     # issues with no blockers
bd blocked                   # what is waiting, and on what
bd list --status=open
bd update <id> --claim       # claim before working
bd close <id> --reason="<why>"
```

**Use the repo's own `/triage-beads` skill, not `mattpocock-skills:triage`,** when the question
is "what should I pick up next". It ranks by value over effort with the evidence cited, and it is report-only.

## Git policy

`bd` never runs git commands and never auto-commits. Every git operation is explicit.

The one automation is `.githooks/pre-push`: every push exports the tracker and, when the export
changed, commits it as a follow-up commit that lands on the *next* push. A missing `bd` or a
failed export only warns; it never blocks the push.

The Dolt remote sync (`bd dolt push`) stays manual and is a machine's job, never the author's.
