# Portable Hooks

The long form of the "Portable hooks for other repositories" section in `AGENTS.md`. That
section says what the hooks do. This one says why each decision was made, and what went wrong
before it was.

`scripts/` holds hooks that belong to a **project** rather than to this plugin. They are not
wired here, and `.claude-plugin/plugin.json` does not reference them.

## The copy of record

`scripts/label_bead_on_skill_invocation.sh` is the copy of record. Deployed copies are
downstream of it. Changes flow back only through a deliberate port.

This file used to name `atlas` as the copy of record. On 2026-08-23, `--check` disproved that.
Atlas held the oldest of the three copies. It still carried the `br` backend detection that this
hook dropped at the `bd` cutover.

`tadw-4fn` covers sweeping the other repositories for the same drift.

## The installer

`scripts/install_label_bead_on_skill_invocation.sh` installs the hook into whatever repository
you run it from. It copies the hook and its Codex runner to `.claude/scripts/`, backs up
`.claude/settings.json`, and wires the three events. Re-running it is safe. It repairs wiring
that names an older path instead of adding a second entry. `--dest-dir` moves the destination.

Only the label script is wired here. The runner is inert until somebody adds it to
`.codex/hooks.json`, so a repository that never runs Codex carries one unused file and loses
nothing. See "Codex" below.

A run that overwrites an existing copy first reports how the two differ, in line counts and
hashes. After the copy, that evidence is gone.

`--check` answers the same questions and changes nothing. It reports whether each installed copy
matches its source, and whether all three events reference the label script. It exits 1 if any of
those is out of step.

The two kinds of drift fail independently. The second is the one that is easy to miss: a current
script reached by only two events labels nothing on the third. `tadw-j80` covers wiring `--check`
into `.githooks/pre-push`.

## Codex

Codex reads project hooks from `.codex/hooks.json` when `[features].hooks` is `true` in
`.codex/config.toml`. Wire `run_codex_bead_hooks.sh` to `UserPromptSubmit` and `Stop`. That one
script runs the context refresh and the label behavior, because Codex runs one command per event
group and both behaviors need the prompt.

The dispatcher sends the same prompt payload to `bd codex-hook UserPromptSubmit` and the portable
label script.

### Where the two scripts live

`scripts/install_label_bead_on_skill_invocation.sh` copies **both** scripts into
`.claude/scripts/` of the target repository. Codex reads no file from that directory, so the name
is only where the pair happens to live; the installer puts them together on purpose. The runner
looks for the label script as a sibling first, then under `.claude/scripts/` of the main checkout,
resolved through the git common dir. Either layout works, and a linked worktree finds the main
checkout's copy.

The two used to be separable, and the failure was silent. The installer wrote the label script to
`.claude/scripts/` while the runner looked only for a sibling, so a repository set up the
documented way had working Claude labeling and Codex labeling that never ran. A runner that cannot
find its label script now writes one line to `<git-common-dir>/bead-label.log` before it returns,
so a split pair is visible rather than indistinguishable from a working one.

### The event comes from the wiring, not the payload

Each entry passes its event name as an argument, `... run_codex_bead_hooks.sh UserPromptSubmit`.
The script parses `hook_event_name` out of the payload only when no argument is given.

The order matters because of `jq`. Parsing the payload first put `jq` in charge of whether the
context refresh ran at all: with no `jq` on the hook's `PATH`, the event resolved empty, no branch
was taken, and the script exited 0. The refresh had needed only `bd` before that, so one missing
tool would have taken down a behavior it never touched.

### The command resolves its own path

Each entry is a short shell expression that resolves the repository root with
`git rev-parse --show-toplevel` and runs the script by absolute path. Codex's hook configuration
has no `cwd` field, and which directory it runs a project command from is not something the
configuration states, so a bare relative path would make the hook depend on where you started
`codex`. Every other entry in the file is a `bd` subcommand found on `PATH`, which has never had
that problem.

### Its stdout belongs to the context refresh

Codex validates a `UserPromptSubmit` hook's stdout against a schema that accepts no unknown keys.
The context refresh writes the one document that schema expects. The label script's stdout is sent
to `/dev/null`, because its `inject` mode emits Claude Code's own JSON shape, which Codex would
reject as a second document and would not act on anyway. No label mode is `inject` today; two were
until 2026-09-09.

### Prompt forms

Codex skill prompts start with `$`, such as `$verify-acceptance tadw-123`. The portable script
accepts that form and the Claude `/verify-acceptance tadw-123` form. Both forms use the same label
map and artifact gates.

A backslash used to open a third form by accident. The pattern was written inline as `[/\$]`, and
POSIX gives a backslash no special meaning inside a bracket expression, so the set was `/`, `\`,
and `$`. A pasted `\build tadw-1` claimed the bead and dropped a gate marker for a run that never
happened. The pattern is now held in a shell variable, where `$` needs no escape.

The Codex prompt hook sees only explicit skill names at the start of a prompt. Codex does not call
a `Skill` tool when it selects a skill from ordinary prose. That implicit selection cannot create
the pending label marker, so include the `$skill` name when automatic labeling matters.

## The working tree stays clean

Labeling a bead writes the label to the `bd` database. It commits nothing and pushes nothing.

The hook used to commit and push `.beads/issues.jsonl`. `tadw-0j8` was filed against that
behavior. The commit path went away at the `bd` cutover, and that bead is closed.

Refreshing the export used to happen after every label. The tree was then modified after every
`/simplify`, `/code-review`, and `/tadw:fresh-eyes-cr`. Two tools refuse to run on a dirty tree:
outrigger aborts its pre-flight, and `/tadw:ship` Step 4 aborts before its squash-merge.

So the refresh is now conditional. It runs in two cases:

- The export is **already** modified. Refreshing it then dirties nothing further.
- `TADW_BEAD_LABEL_EXPORT=1` is set. This restores the old unconditional behavior.

`bv` reads the `bd` database directly, so it loses nothing either way. `tadw-94u` covers
confirming which of the two Manifest reads. The environment variable exists to cover that
question until it is settled.

## Widening before narrowing

The candidate pattern takes a maximal hyphenated run. So a branch named `<bead-id>-<slug>` used to
arrive as one token, and it resolved to nothing: the whole of
`tadw-b14-hook-resolution-and-clean-tree` was offered, and the `tadw-b14` inside it never was.

Each token now also offers its own hyphen prefixes, longest first. The full token therefore still
wins where the id is itself a slug, such as `tadw-qg-prepush-verdict-gate-tug`.

A dotted epic-child suffix is never split off. `hdw-3fe4.3` and `hdw-3fe4` are different beads.

The probe cap bounds the added cost, and it falls on the shortest candidates. A branch of more than
twelve hyphen segments still resolves nothing.

`close_bead_on_pr_merge.sh` has no such decomposition. Its `BEAD_ID_RE` takes the same maximal run,
so it is blind to this branch shape too. That is deliberate rather than pending: it reads four
sources in order, so a branch name that resolves nothing falls through to the PR body and the
commits. Offering prefixes there would create new ways to trip its ambiguity refusal, which would
turn a working close into a refusal.

## Narrowing before probing

Each candidate bead id costs one `bd show`. That was measured at 0.53 seconds against fathom's
tracker, inside a hook that blocks `UserPromptSubmit`.

Two local filters cut the candidate list without a tracker call:

- A hyphenated candidate must carry a prefix the repository actually uses. The prefixes come
  from `.beads/config.yaml` and from the ids already in the export, so historical prefixes still
  resolve.
- A bare candidate must be short and must carry a digit.

The branch's positional segment is exempt from both filters. Outrigger put the id there on
purpose, rather than it happening to look like one.

A repository that can determine no prefixes disables the first filter. It does not reject every
candidate.

## Finding out whether it works

Every failure path in the hook exits 0, so a skill runs whether or not its bead could be
labeled. That is deliberate. It is also why two total outages went unnoticed: stderr was the only
record, and nothing surfaces it.

Two things now answer the question.

**After the fact.** Every invocation that had a job to do appends one tab-separated line to
`<git-common-dir>/bead-label.log`. The line carries the timestamp, the event, the skill, the
branch, the resolved bead id or `unresolved`, and the action.

A run of `unresolved` lines is an outage.

The file lives in the git directory. It is never tracked, and it never dirties the tree. It is
truncated to its last 1000 lines.

An unmapped skill writes nothing. A hook that correctly declines to label `/adr` is not an
outcome.

Each line ends with the hash of the copy that wrote it, so you can tell a stale copy from a
broken one.

A label that `/build` or `/verify-acceptance` was asked to apply, and never did, appears as
`OWED <label>`. That is the one failure that used to leave no trace anywhere.

**Before the fact.** Run
`.claude/scripts/label_bead_on_skill_invocation.sh --doctor` from a terminal when a label you
expected did not appear. It resolves against the current branch. It prints the bead, its labels,
and what each labeled command would do. It writes nothing at all: no label, no export, no
marker, no log line.

## A session can outlive the directory it was started in

Landing a bead removes its worktree. A session still open in that worktree keeps running, with
`$CLAUDE_PROJECT_DIR` naming a directory that is gone.

Every wired command then failed before it reached the script. `/bin/sh` reported
`No such file or directory` and exited 127. Claude Code showed `Stop hook error`,
`UserPromptSubmit hook error`, and `PostToolUse:Bash hook error` on nearly every turn.

So each wired command now reads `test -x <path> && exec <path> || exit 0`. A missing script is
now a silent no-op.

Two things follow from that fix.

First, the wiring was producing exactly the failure the script takes such care to avoid. The
hook's own failure paths all exit 0 so that a session continues.

Second, and this is the one to act on: the guard only stops the noise. A session whose project
directory is gone labels nothing, because the script that writes the log is the missing thing.
**End that session. Start a new one in a directory that exists.**

`hooks/test-claude-scripts.sh` pins both halves: the silent miss, and the run that still reaches
the script.
