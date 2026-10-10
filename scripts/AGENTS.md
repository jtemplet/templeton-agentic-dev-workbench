# Portable hooks

`scripts/` holds hooks that belong to a project rather than to this plugin. The root `AGENTS.md`
keeps the one rule that applies everywhere: `scripts/label_bead_on_skill_invocation.sh` is the
copy of record, so change it here, never in a deployed copy. `CLAUDE.md` here is a symlink to
this file.

- `scripts/label_bead_on_skill_invocation.sh` labels the bead that a skill invocation acts on. It
  is wired to `PreToolUse` (matcher `Skill`), `UserPromptSubmit`, `Stop`, and `SubagentStop`.
  Deployed copies are downstream of it.
- `scripts/install_label_bead_on_skill_invocation.sh` installs it into whatever repository you
  run it from, under `.claude/scripts/`. It puts `scripts/run_codex_bead_hooks.sh` in
  `.codex/scripts/`, and removes a runner an older installer left in `.claude/scripts/`.
  Re-running it is safe. `--dest-dir` moves the label script and its module, never the runner.
- `... --check` reports whether each installed copy matches its source, and whether all four
  events reference the label script. It changes nothing, and exits 1 when any is out of step.
- `scripts/claim_bead_for_build.py` decides the `/build` claim: claim, adopt, already held,
  refuse, or leave alone. It labels nothing and is not a hook. The label script runs it as a
  sibling through `python3`, so the installer copies it too, and removes a copy under its old
  name, `label_bead_hook.py`. `python3 scripts/test_claim_bead_for_build.py` tests the decision
  directly.
- `scripts/guard_default_branch.sh` is a `PreToolUse` hook (matcher `Edit|Write|NotebookEdit`)
  that refuses an edit to a file on its repository's default branch. It reads the branch of the
  repository that holds the edited file, not the session's. It is also a copy of record: the
  deployed copy is `~/.claude/scripts/guard_default_branch.sh`, wired in `~/.claude/settings.json`.
  Change it here, then copy it over the deployed file. `scripts/test_guard_default_branch.sh`
  tests it against throwaway repositories. Run it by hand with
  `sh scripts/test_guard_default_branch.sh`.

Two properties matter to the target repository:

- **Labeling leaves the working tree as clean as it found it.** It writes to the `bd` database,
  and commits and pushes nothing. Refreshing `.beads/issues.jsonl` is conditional: it happens
  when the export is already modified, or when `TADW_BEAD_LABEL_EXPORT=1` is set.
- **Every failure path exits 0**, so a skill runs whether or not its bead could be labeled. Two
  records make an outage visible: the log at `<git-common-dir>/bead-label.log`, and `--doctor`,
  which resolves the current branch and prints what each labeled command would do.
- **One path stops a skill on purpose: `/build` on a bead somebody else holds.** The hook claims
  under a per-session actor, `<git user.name> (session <first 8 of session_id>)`. It then refuses
  `/build` when the bead is `in_progress` under any other assignee, an empty one included, since
  outrigger claims with none. A claim under the bare `user.name`, which a manual
  `bd update <id> --claim` makes, is the person's own: the session takes it over with
  `--if-assignee` rather than refusing it. A payload with no `session_id` keeps the old behavior
  and refuses nothing.

**A session can outlive the directory it was started in.** Landing a bead removes its worktree.
Each wired command guards on `test -x <path>`, so a missing script is a silent no-op rather than
a `Stop hook error` every turn. That guard only stops the noise. Such a session labels nothing,
so end it and start a new one in a directory that exists.

Rationale, incident history, and the candidate-narrowing filters live in
[docs/PORTABLE-HOOKS.md](../docs/PORTABLE-HOOKS.md).
