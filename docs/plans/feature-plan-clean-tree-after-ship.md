# Feature Plan: Clean Tree After Ship

**Date:** 2026-09-28
**Status:** Draft. Decomposed: 2026-09-28, see bd tadw-fm1j, tadw-l6u4, tadw-8vnh, tadw-orrj,
tadw-2dih, tadw-zud5.

**Revised 2026-09-28** after `/plan-review` (Needs Revision). The real-bd test now sets
`export.interval` to `1s`. Added criterion 10, the rollout of the ship change, the
`--suggest-next` output, the `git update-ref` case in the sibling rollout, and the named sentence
in `docs/ship-gate-contract.md`.

## Summary

After `/tadw:ship` prints `SHIP_DONE`, `git status --porcelain` must print nothing. Today the bead
closes after the landing commit, so bd writes the close into `.beads/issues.jsonl` and leaves that
file changed. This plan closes the bead before the landing commit is built, so the close goes into
that commit. It also stops the pre-push hook from making tracker-only commits, and applies the bd
1.3.0 fixes to every sibling repository that uses beads.

## Motivation

The repository owner runs ship and then finds `.beads/issues.jsonl` changed in the tree. They
want every change to the export in the commit it belongs to, and never in a commit that holds
the export alone.

Three causes were measured on 2026-09-28:

1. **Ship closes the bead after the landing commit, by design.** The docstring of
   `skills/ship/scripts/ship_workflow.py` says "the next tracker export carries the close". Commit
   `ab046c6` landed tadw-6pyo at 23:50:08Z. The bead's `closed_at` is 23:53:08Z. The close first
   reached git in the release commit `cdb81fd`.
2. **bd writes the export by itself.** `export.auto` is `true` here, and it must stay `true`,
   because Manifest reads `.beads/issues.jsonl`. Tests in a scratch repository, with bd 1.2.2 and
   again with 1.3.0, showed three things:
   - A bd write in a linked worktree changes the export in the main checkout, never in the worktree.
   - `export.interval` defaults to 60 seconds, so bd skips writing the export for a bd write that
     comes within 60 seconds of the previous export. The skipped change appears only on a later
     write. A read such as `bd ready` or `bd show` does not write it.
   - `bd export -o` writes a file byte-identical to the file auto-export writes.
3. **Stage 3 of `.githooks/pre-push` commits the export by itself.** It makes the commit
   `chore(beads): refresh tracker export`, which holds nothing but the export.

A fourth source appeared on 2026-09-28. The beads section of the pre-commit hook
(`bd hooks run pre-commit`) also writes the export into the main checkout when the commit runs
in a linked worktree.

## Scope

### In Scope

- Ship closes the bead after the gate passes and before the landing commit is built. The landing
  commit carries the close.
- Ship reopens the bead when the run stops after the close and before the default branch moves.
- Ship prints a warning that names `.beads/issues.jsonl` when that file differs from `HEAD` at the
  end of a run.
- Stage 3 of `.githooks/pre-push` warns and never commits.
- A test through the real bd proves the tree is clean after `SHIP_DONE`.
- Each sibling repository that uses beads gets the bd 1.3.0 fixes: the `*.gate.lock*` pattern in
  `.gitignore`, and one commit that re-exports the tracker under bd 1.3.0.
- An ADR records the two decisions this plan reverses.

### Out of Scope

- Turning off `export.auto`. Manifest reads the export, so bd must keep writing it.
- Keeping other sessions' tracker changes out of the landing commit. The owner accepted on
  2026-09-28 that the landing commit carries every change in the tracker at that moment. Ships
  already do this: `ab046c6` changed 7 lines of the export.
- A bd write made after ship finishes, from any session. No commit owns that change, so it
  stays in the tree until the next commit or the next ship.
- A ship that stops (`SHIP_BLOCKED`). The reopen, and the `needs-human` label the skill adds, are
  bd writes, so they change the export. A stopped ship is not a finished one.
- `jtemplet.github.com`. bd 1.3.0 refuses its tracker with "historical SQLite workspace
  detected", so it needs a migration first. That work is separate.
- Syncing the Dolt remote.

## Technical Approach

### Architecture

The order of `candidate.land_candidate` changes. Today it squashes, exports, commits, gates, and
advances the default branch, and then `ship_workflow.publish` closes the bead. The new order:

1. Squash the feature branch in the temporary worktree, and commit it with the export as it
   stands. This is the gated commit.
2. Run the gate on the gated commit.
3. Run `bd close <bead-id> --suggest-next` in the temporary worktree. The runner prints its
   output, as `close_bead` does today.
4. Run `bd export -o` into the temporary worktree.
5. Build the landing commit with git plumbing: the gated tree, with `.beads/issues.jsonl`
   replaced by the export from step 4. Use `git commit-tree`. It runs no hook, so a pre-commit
   hook that is the gate (source 4 in `docs/ship-gate-contract.md`) does not run a second time.
6. Check that the landing commit differs from the gated commit in `.beads/issues.jsonl` only.
   Anything else stops the run.
7. Advance the default branch to the landing commit. `restore_stale_export` resets an export that
   bd wrote into the main checkout during steps 3 and 4. The fast-forward then writes the export
   from the landing commit into that checkout.
8. Push, sync the Dolt remote, record what comes next, and clean up, as today.

The bead closes after the gate passes, so a failed gate never closes it. That is the reason the
current docstring gives for its order, and the new order still meets it. A stop in steps 5 to 7
runs `bd reopen <bead-id>`. A failed push leaves the bead closed, because the default branch
already carries the landing commit locally. Today's run behaves the same.

The new order reaches every repository that uses the plugin when milestone 3 is pushed to
`main`, because a push to `main` is already published (ADR 0003). Ship one bead in this
repository with the new runner before shipping in a sibling repository.

`require_matching_export` goes away. It checked that the export did not change while the gate
ran. In the new order the export is taken after the gate, so there is nothing to compare.

Stage 3 of `.githooks/pre-push` exports into a temporary file and compares it with the committed
export. When the two differ, it warns that the tracker has changes that no commit holds, and says
that they go into the next commit. It never commits, and it never writes `.beads/issues.jsonl`.

Each sibling repository gets the bd 1.3.0 fixes the way this repository got them in `2051df2`:

1. In a new worktree, run `bd export -o .beads/issues.jsonl`.
2. Add `*.gate.lock*` to `.gitignore`.
3. Commit the two files as `chore(beads): Re-export the tracker under bd 1.3.0`.
4. Reset the main checkout's export to `HEAD`, fast-forward the default branch, and push. When
   no checkout holds the default branch, move it with `git update-ref`, as
   `advance_default_branch` does.

Never stage or change any other file in the sibling repository. Several have uncommitted work of
their own. List the sibling repositories with this command:

```bash
for d in ~/Dev/*/; do [ -d "$d.beads" ] && echo "$d"; done
```

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `skills/ship/scripts/candidate.py` | Gate first, then close, export, build the landing commit with `git commit-tree`, and check its diff | Modified |
| `skills/ship/scripts/ship_workflow.py` | Pass the close and the reopen to the candidate; drop the close from `publish`; warn when the export differs from `HEAD` at the end | Modified |
| `.githooks/pre-push` | Stage 3 warns and never commits | Modified |
| `skills/ship/scripts/test_tadw_ship.py` | New cases through the full-run fixture | Modified |
| `skills/ship/scripts/test_ship_with_real_bd.py` | End-to-end run of `tadw-ship` with the real bd | New |
| `.githooks/test_prepush.py` | Stage 3 cases now expect a warning, not a commit | Modified |
| `skills/ship/SKILL.md`, `docs/ship-gate-contract.md`, `AGENTS.md`, `.githooks/AGENTS.md` | Describe the new order and the new stage 3 | Modified |
| `docs/adr/0012-...md` | Record the two reversed decisions | New |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| The full-run fixture in `skills/ship/scripts/test_tadw_ship.py`, with `FAKE_BD` | Existing | The close runs after the gate and before the landing commit. A failed gate leaves the bead open. A stop before the advance reopens it. The tree is clean after `SHIP_DONE`. |
| `skills/ship/scripts/test_ship_with_real_bd.py`, with bd 1.3.0 | New | The facts `FAKE_BD` only copies: where bd writes the export, and the export from `bd hooks run pre-commit`. It sets `export.interval` to `1s`, the worst case. |
| `.githooks/test_prepush.py` | Existing | Stage 3 warns, and commits nothing. |

The full-run fixture is the highest seam CI can run. The real-bd test proves what a fake cannot,
and it skips itself when `bd` is not on `PATH`, so CI does not run it. The owner confirmed these
three seams on 2026-09-28.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| 0001 | Native tracker fields are canonical | The close uses `bd close --reason`, the native field. |
| 0003 | A push to `main` is already published | The rollout pushes each sibling's commit only after its checks pass. |
| 0004 | The pre-push hook forgives by design | Stage 3 warns and never refuses a push. |
| 0010 | The export rides the commit | The close now rides the landing commit. Stage 3 stops making the follow-up commit this ADR calls a backstop. |

This plan changes two earlier decisions, so milestone 1 writes ADR 0012 before any code changes.
The first is tadw-pm8, which made stage 3 commit the export. The second is the promise in
`candidate.py` that ship "gates the exact commit it lands". The new promise is that ship gates
the exact code tree, and the landing commit adds only the export.

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | ADR | Write ADR 0012 with `/adr`: the close goes into the landing commit, and stage 3 warns. | S | `docs/adr/0012-*.md` exists and names tadw-pm8 and the "exact commit" promise. |
| 2 | Real-bd test first | Write `test_ship_with_real_bd.py`, with `export.interval` at `1s`. It fails on today's ship, because the tree is changed after `SHIP_DONE`. | M | The test fails on `main` as of `2051df2` and names `.beads/issues.jsonl`. |
| 3 | Ship order | Change `candidate.py` and `ship_workflow.py` to the new order, with the reopen and the end-of-run warning. Extend `FAKE_BD` and add the fixture cases. | L | Every case in `test_tadw_ship.py` and `test_candidate.py` passes, and so does the milestone 2 test. |
| 4 | Stage 3 warns | Change stage 3 of `.githooks/pre-push` and its cases in `test_prepush.py`. | S | `python3 .githooks/test_prepush.py` passes, and no case expects a commit from stage 3. |
| 5 | Docs | Update `skills/ship/SKILL.md`, `docs/ship-gate-contract.md`, `AGENTS.md`, and `.githooks/AGENTS.md`. In `docs/ship-gate-contract.md`, change the sentence "The real push runs the pre-push hook a second time, on the same commit": that commit is now the landing commit. | S | `python3 skills/quality-gates/scripts/check_doc_paths.py` exits 0, and `grep -rn "next tracker export carries the close" skills docs` prints nothing. |
| 6 | Sibling rollout | Apply the bd 1.3.0 fixes to each sibling repository, one commit each. | M | In each sibling repository, `git check-ignore .beads.gate.lock` exits 0, and a fresh `bd export` matches `HEAD:.beads/issues.jsonl`. |

Milestone 6 does not depend on milestones 1 to 5, and it can run first.

## Acceptance Criteria

1. Given a repository with `export.auto` on and a feature branch for an open bead, when ship
   prints `SHIP_DONE`, then `git status --porcelain` prints nothing in the default-branch
   checkout.
2. Given the same run, when the landing commit is read with `git show`, then its
   `.beads/issues.jsonl` shows the bead with status `closed`.
3. Given the same run, when `git log` lists the commits after the landing commit, then none of
   them changes `.beads/issues.jsonl` alone.
4. Given a gate that fails, when ship prints `SHIP_BLOCKED gate`, then `bd show <bead-id>`
   reports the bead open, and the default branch has not moved.
5. Given a default branch that moves after the close and before the advance, when ship stops, then
   `bd show <bead-id>` reports the bead open.
6. Given the landing commit and the gated commit, when `git diff --name-only` compares them, then
   it prints `.beads/issues.jsonl` and nothing else.
7. Given an export that differs from `HEAD` when ship finishes, when ship prints `SHIP_DONE`, then
   the output holds a warning line that names `.beads/issues.jsonl`.
8. Given a tracker change that no commit holds, when `git push` runs stage 3, then stage 3 prints
   a warning, makes no commit, and leaves `.beads/issues.jsonl` unchanged.
9. Given each sibling repository that uses beads, when the rollout is done, then
   `git check-ignore .beads.gate.lock` exits 0, and `bd export` matches
   `HEAD:.beads/issues.jsonl` byte for byte.
10. Given a repository whose gate is its pre-commit hook, when ship prints `SHIP_DONE`, then the
    call log of the full-run fixture shows that the hook ran exactly once.

**Coverage:** criteria 1 to 7 and 10 prove the ship change. Criterion 8 proves stage 3. Criterion 9
proves the rollout. Criteria 1 and 3 prove the motivation: a clean tree, and no tracker-only
commit.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| A bd write from another session lands between the export in step 4 and the end of the run, and the tree ends changed | Med | Med | The end-of-run warning names the file. The gap is seconds long, because no gate runs in it. |
| The run stops after the close, and the process dies before `bd reopen` runs, so the bead reads as closed with nothing landed | High | Low | Steps 3 to 7 are local operations of a few seconds. tadw-dur4 (resuming an interrupted ship) covers the crash case. |
| A bd release after 1.3.0 changes where auto-export writes, or the interval | Med | Med | The real-bd test proves those facts on the installed version. Run it after every bd upgrade. |
| A machine still on bd 1.2.2 writes the old comment ids back, and the export flips format on every write | Med | Unknown | Upgrade every machine that writes a tracker to 1.3.0 before milestone 6. |
| A sibling repository merges through pull requests, and a direct push to its default branch breaks its rules | Med | Unknown | Read the repository's `AGENTS.md` before each push. Open a pull request where it says so. |
| Scope: the rollout grows into repairing every sibling's other problems | Med | Med | Change only `.gitignore` and `.beads/issues.jsonl`. Record anything else found as a bead in that repository. |

## Dependencies

- bd 1.3.0 or later on every machine that writes a tracker.
- `2051df2`, which applied the bd 1.3.0 fixes to this repository.

## Testing Strategy

- **Full-run fixture (CI).** Extend `FAKE_BD` so that `close` and `reopen` rewrite the main
  checkout's export, like `REWRITE_MAIN_EXPORT` does for tadw-lndi. Add one case for each of
  criteria 1 to 7 and 10.
- **Real bd (local).** `test_ship_with_real_bd.py` creates a scratch repository and a feature
  worktree. It sets `export.auto` to `true` and `export.interval` to `1s`, so that every bd write
  exports. A longer interval can skip the export that shows today's bug, and the test would then
  pass on today's code. Then it runs `bin/tadw-ship` and checks criteria 1 to 3. It skips itself
  when `bd` is not on `PATH`. The owner runs it after every bd upgrade.
- **Pre-push (CI).** Change `case_tracker_export_is_committed_when_it_changes` in
  `.githooks/test_prepush.py` so it expects a warning and no commit. Keep the other tracker
  export cases.

## Open Questions

- Should each sibling repository without the pre-commit fold get it? That hook section adds the
  export to each commit. Today only this repository, `manifest`, and `reach` have it, and no
  installer exists under `scripts/`. Without it, a tracker change in a sibling stays in the tree
  until the next ship. The owner decides.
- `atlas-listing-1.6.5` and `templeton-consulting` set `core.hooksPath` to another directory's
  hooks (`atlas` and `consulting-website`). Is that intended? The owner decides before milestone 6.
- `foxhole`, `infra-builder`, `quadrant`, and `scripts` print "Smart gate (#4516): it could not
  read the remote" from `bd config get`. Milestone 6 checks whether this blocks `bd export` there.
- Which machines other than this one write a tracker, and are they on bd 1.3.0? The owner answers.
