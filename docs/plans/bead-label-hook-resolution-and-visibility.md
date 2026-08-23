# Feature Plan: the bead-labeling hook resolves real branches, and says when it cannot

**Date:** 2026-08-22
**Status:** Draft, not started.

**Revision, 2026-08-22, from `/tadw:plan-review`.** The review reproduced every claim in §2.1 and
found them exact. It also found three things this draft had wrong, all now fixed below: the
installer already does the drift detection M4 asked for, no milestone owned the test suite that
this change breaks, and the plan's line citations addressed a version of the file that exists
nowhere on disk. Citations are now by function name. See §9 for the full list of changes.

## 0. Grounding, and why it is stated this way

**This plan cites no line numbers.** During the review the target file existed in three different
lengths inside one hour, and every line citation in the first draft was wrong against all of them.
The file is under active concurrent edit. Function names have been stable across every version, so
each reference below names a function or quotes the code it means. Re-derive the line with
`grep -n` at the moment you edit.

Versions live at the time of writing:

| Where | Lines | Note |
|---|---|---|
| `main` @ `431db80`, `scripts/label_bead_on_skill_invocation.sh` | 400 | the source of record |
| `main` @ `431db80`, `.claude/scripts/label_bead_on_skill_invocation.sh` | 348 | this repo's own deployed copy, one generation behind |
| `outrigger/ci8/...` @ `690c43e` (worktree) | 465 | active concurrent work |
| `~/Dev/fathom/.claude/scripts/...` | 21,287 bytes, Aug 21 | dual `br` and `bd` detection |

**Before starting, re-check `git log --oneline -1` and re-read the file.** `main` moved backwards
during the review, from `1f3afea` to `431db80`; `1f3afea` now survives only inside the
`outrigger/ci8` branch. Reconcile with that branch before editing. It does not touch
`resolve_bead`, so M1 and M2 are clear of it. It does rewrite `classify_skill`, `run_label_flow`,
`handle_pre`, and `handle_stop`, and it edits the header comment, so M4 step 1 and both items of M5
collide with it directly. §4b has the order of operations.

**Origin.** A full build-and-ship session in `~/Dev/fathom` on 2026-08-22 ran `/tadw:fresh-eyes-cr`,
`/tadw:verify-acceptance`, and `/tadw:ship` against bead `fathom-zkc.5`. The hook was wired for all
three events and applied no label. The bead shipped carrying only its four original labels. Nothing
in the session surfaced the failure; it was found afterwards by inspection.

---

## 1. Goals

1. The hook resolves a bead from the branch shapes this ecosystem actually produces, in particular
   outrigger's `outrigger/<short-id>/<slug>`.
2. A hook that cannot do its job says so somewhere a person will read, rather than only on stderr.
3. Labeling does not leave the working tree dirty, because two other tools refuse to run on a dirty
   tree.
4. The file in this repository is the file that runs.

## 2. Problem, with evidence

### 2.1 The candidate regex cannot see short bead ids

Inside `resolve_bead`:

```text
grep -oE '[a-z][a-z0-9]*(-[a-z0-9]+)+(\.[0-9]+)*'
```

The `+` on `(-[a-z0-9]+)` makes at least one hyphen mandatory. The leading `[a-z]` rejects a digit.

`resolve_bead` builds its sources from the args and the branch with slashes replaced by spaces
(`sources="$args"$'\n'"${branch//\// }"`). For branch
`outrigger/zkc.5/rank-beads-and-reminders-deterministical` the sources are
`outrigger zkc.5 rank-beads-and-reminders-deterministical`, and the regex yields exactly one
candidate:

```text
rank-beads-and-reminders-deterministical
```

That is a slug, not a bead. `bd show` rejects it, the probe loop exhausts, and the handler logs
`no candidate resolved to a bead` and exits 0.

Measured against this tracker's real ids:

| Token | Regex emits it | `bd show <token>` resolves to |
|---|---|---|
| `zkc.5` | no | `fathom-zkc.5` |
| `e12` | no | `fathom-e12` |
| `yx5` | no | `fathom-yx5` |
| `9ma` | no, leading digit | resolves |
| `fathom-zkc.5` | yes | `fathom-zkc.5` |
| `life-os-eso` | yes | `life-os-eso` |

Every short id in `fathom` is hyphen-free, and outrigger puts exactly that short id in the branch.
So the hook is blind to every outrigger branch in that repository. The comment above `resolve_bead`
states the intended design, that the pattern only narrows the search and verification decides. The
pattern is in fact deciding, by never offering the one candidate that resolves.

**Reproduced during review.** All six table rows and the single-candidate result above were
re-derived by running the regex, not by reading it.

### 2.2 Failures are invisible by design

The header comment states the contract: "Every failure path logs to stderr and exits 0, so a skill
runs whether or not the bead could be labeled." Hook stderr is not surfaced in normal use.

This has now hidden a total outage twice. The deployed copy's own comment records the first:

> ... which is what silently disabled this hook between the 2026-08-12 cutover and this fix: every
> label attempt logged a failure nobody was reading, and no bead was labeled in that window.

Exiting 0 is correct, because a skill must run whether or not its bead can be labeled. Logging only
to stderr is what makes the outage undetectable.

### 2.3 `refresh_export` dirties the tree, and two tools refuse a dirty tree

`refresh_export` runs `bd export -o .beads/issues.jsonl` after every successful label. The reasoning
in the comment above it is sound on its own terms: the export is passive, and leaving it stale makes
the label invisible to `bv` and Manifest.

The cost lands elsewhere. `apply` mode fires on `/simplify`, `/code-review`, and
`/tadw:fresh-eyes-cr` (see the `LABEL="reviewed"; MODE="apply"` arm of `classify_skill`), so an
ordinary review pass leaves the tree modified. In the 2026-08-22 session, both downstream tools hit
it:

- outrigger aborted its first run: `ABORT (pre-flight): tracked files are modified (uncommitted
  changes)`.
- `/tadw:ship` found `.beads/issues.jsonl` already modified in the main checkout before its
  squash-merge, and had to back the file up and discard it.

Both happened while the hook was **broken and labeling nothing**. Fixing 2.1 without fixing this
converts an intermittent collision into one that occurs on every review pass.

### 2.4 Deployed copies drift, including this repository's own

The first draft claimed the installer "installs by `cp`, and nothing afterwards compares the two."
**That is wrong.** `scripts/install_label_bead_on_skill_invocation.sh` already compares source
against destination before copying and reports the result:

```bash
if [[ -f "$DEST" ]] && cmp -s "$SOURCE" "$DEST"; then
  script_result="already current"
elif [[ -f "$DEST" ]]; then
  script_result="updated"
else
  script_result="installed"
fi
```

The result prints at the end as `hook script: $script_result at ...`. So M4 does not need to build
drift detection. What is genuinely missing is narrower: the installer never says *what* differs, and
it has no way to report drift without overwriting it.

Drift is real, and it is not only a fathom problem. **Both copies in this repository are committed
and clean at `431db80`, and they differ by 52 lines and four whole functions:**

| Copy | Lines | Functions absent | Events handled |
|---|---|---|---|
| `scripts/label_bead_on_skill_invocation.sh` | 400 | - | three |
| `.claude/scripts/label_bead_on_skill_invocation.sh` | 348 | `classify_skill`, `run_label_flow`, `handle_prompt`, `skill_for_command` | two |

The deployed copy is one generation behind, not broken: its own header says "Wired to two events",
`.claude/settings.json` wires exactly two (`PreToolUse` and `Stop`), and it parses cleanly. The
consequence is still a real behavior gap. A typed `/tadw:fresh-eyes-cr` in this repository reaches
no `UserPromptSubmit` handler and labels nothing, while the source in `scripts/` supports it.

Fathom drifts the other way: its copy is 21,287 bytes with dual `br` and `bd` detection, ahead of
this bd-only source in backend support and behind it in everything else.

### 2.5 `inject` mode can drop a label with no trace

`gate` mode writes a marker with a TTL and resolves it at Stop (the `gate)` arm of `run_label_flow`,
plus `handle_stop`). The `inject)` arm emits an instruction and keeps no state.

In the session, `/tadw:verify-acceptance` reached an ACCEPTED verdict, which clears the gate its
`classify_skill` arm sets. No `accepted` label was applied, because resolution had already failed
and the inject branch was never reached. Nothing recorded that a label had been owed.

### 2.6 `ship` is unmapped

`skill_for_command` has no `ship` entry, and neither does `classify_skill`. Confirmed: the string
`ship` appears nowhere in the script. §3 decision 6 settles what to do about it.

## 3. Decisions

1. **Structure beats pattern for branch parsing.** Outrigger's convention is positional, so read the
   path segment rather than pattern-matching the whole branch. The regex stays as a secondary
   source.
2. **Widen the net, bound the cost.** `bd show` per candidate is a subprocess, so a wider pattern
   needs a probe cap. Twelve probes is well above any real branch and cheap enough.
3. **Keep exiting 0, add a durable log.** The skill must never be blocked by its own labeling. The
   fix for invisibility is a log file, not a non-zero exit.
4. **The export refresh becomes opt-in.** Correctness of the tracker database does not depend on it;
   only `bv` and Manifest freshness does, and `bv` reads the database directly (§5b Q1).
5. **No new tracker backends.** This is bd-only, matching the current source. Fathom's `br` branch
   is dead code there and gets deleted in M4, not preserved.
6. **`ship` stays unmapped, and says so.** `/tadw:ship` closes the bead outright, so a label added
   at the same moment carries no information the closed state does not. M5 adds a comment recording
   that, not an entry. This resolves the either/or the first draft left open.
7. **Cite by symbol, never by line.** §0 explains why. This applies to the executing agent's own
   commit messages and follow-up beads as well.

## 4. Scope

### In scope

- `scripts/label_bead_on_skill_invocation.sh`: candidate resolution, logging, export behavior,
  inject-mode markers, the `ship` comment.
- `scripts/install_label_bead_on_skill_invocation.sh`: reporting what differs, and a check mode.
- `hooks/test-claude-scripts.sh`: the new resolution cases, and the existing export case that this
  change inverts. See §5c.
- `~/Dev/fathom/tests/test_bead_label_hook.py`: the export case that this change inverts, and the
  `br` cases that M4's reinstall makes dead.
- Re-syncing this repository's own `.claude/scripts/` copy, which is 52 lines behind (§2.4).

### Out of scope

- The `/tadw:ship` skill defects found in the same session, in particular the zsh word-splitting bug
  in the `git diff HEAD origin/main -- $FILES` line of `skills/ship/SKILL.md`. Separate track,
  separate plan.
- Any change to what the labels mean, or to the `apply` / `gate` / `inject` taxonomy.
- Migrating repositories other than this one and `fathom` beyond re-running the installer.

## 4a. Dependencies

No external dependencies: no new packages, services, or tools. The change is confined to two shell
scripts and two test suites.

Four consumers depend on behavior this plan changes, and each is addressed:

| Consumer | Depends on | Handled by |
|---|---|---|
| `bv` | the tracker database, not the JSONL export (§5b Q1) | unaffected by M2 |
| Manifest | unconfirmed; may read the JSONL export | the `TADW_BEAD_LABEL_EXPORT=1` escape hatch in M2 |
| outrigger pre-flight | a clean tracked tree | M2 is the fix |
| `/tadw:ship` Step 4 | a clean tracked tree before its squash-merge | M2 is the fix |

One internal dependency: `.githooks/pre-push` runs `hooks/test-claude-scripts.sh`, so M2 cannot be
pushed until §5c's case changes land with it.

## 4b. Sequencing against work in flight

`outrigger/ci8/label-beads-from-the-verdict-file` @ `690c43e` is unmerged and edits the same file.
It is one commit ahead of `1f3afea`, which was briefly on `main` and was rolled back.

**What it already does.** At `690c43e` the two copies in this repository are byte-identical, the
deployed copy carries `classify_skill`, `run_label_flow`, `handle_prompt`, and `skill_for_command`,
and `.claude/settings.json` wires `UserPromptSubmit`. That is M4 step 3 in full. It also adds 100
lines and two cases to `hooks/test-claude-scripts.sh`.

**Order of operations.**

1. M1 and M2 start now, whatever happens to that branch. Neither touches a function it edits;
   confirmed against `git diff 431db80..690c43e`, whose hunks land in the header, `classify_skill`,
   `run_label_flow`, `handle_pre`, `handle_stop`, and a block of new report functions.
2. Before M4, re-check whether it landed. If it did, M4 step 3 is a no-op: verify with
   `diff scripts/label_bead_on_skill_invocation.sh .claude/scripts/label_bead_on_skill_invocation.sh`
   and delete the step. If it did not, M4 step 3 stands as written.
3. Before M5, rebase onto it or wait for it. M5 edits `run_label_flow`, `handle_stop`, and
   `skill_for_command`; that branch rewrote the first two.
4. Re-derive §5c's case numbering after it lands. Its two new cases shift the count.

Verification: `git worktree list` and `git log --oneline -1` are re-read at the start of M4 and
again at the start of M5, and the answer is recorded in the commit message.

## 5. Milestones

### M1: Resolve the branch shapes that exist (blocks everything)

Rewrite `resolve_bead` to build candidates from three ordered sources:

1. **Positional.** When the branch has at least three slash-separated segments, offer segment two
   verbatim, first. This is outrigger's `outrigger/<short-id>/<slug>`.
2. **Pattern, widened.** `[a-z0-9][a-z0-9]*(-[a-z0-9]+)*(\.[0-9]+)*`. The hyphen group becomes
   optional and the leading class admits a digit, so `zkc.5`, `e12`, and `9ma` become candidates.
   Verified during review: against the real branch this emits `outrigger`, `zkc.5`, and the slug.
3. **Cap.** Take at most 12 unique candidates, longest first, preserving the ordering rationale in
   the comment above `resolve_bead`.

Add cases 1 through 5 of §5c to `hooks/test-claude-scripts.sh` in this same change. The regression
case that would have caught the whole outage is case 1, and it is a deliverable of this milestone,
not a follow-up.

Verification: `bash hooks/test-claude-scripts.sh` passes with zero failures, cases 1 through 5
included. Then, with the tracker in `~/Dev/fathom`, resolution from branch
`outrigger/zkc.5/rank-beads-and-reminders-deterministical` returns `fathom-zkc.5`.

### M2: Stop dirtying the working tree (ship with M1, not after)

1. Change `refresh_export` to skip the export unless the export file is already modified, or unless
   `TADW_BEAD_LABEL_EXPORT=1` is set. Record in the comment above it why the default flipped, naming
   outrigger pre-flight and `/tadw:ship` Step 4 as the two consumers that refuse a dirty tree.
2. **Invert the two tests that pin the old behavior.** They currently assert the export always runs,
   so this change fails them and the pre-push hook blocks the push:
   - `hooks/test-claude-scripts.sh`, case `label/bd: refreshes the export instead of committing it`,
     which asserts `export -o` reached `bd` on a freshly created clean repository.
   - `~/Dev/fathom/tests/test_bead_label_hook.py`, `test_bd_refreshes_the_export_so_local_readers
     _are_not_stale`.

   Replace each with §5c cases 6 through 9.

Verification: `bash hooks/test-claude-scripts.sh` passes with zero failures. Then run a labeled
skill on a clean tree in `fathom`; `git status --porcelain` stays empty and the label is present in
`bd show`.

**M1 and M2 land together.** M1 alone makes 2.3 fire on every review pass. M2 alone leaves the hook
dead.

### M3: Make a broken hook visible

1. Append every invocation outcome to `$GIT_COMMON/bead-label.log`: timestamp, event, skill, branch,
   resolved id or `unresolved`, action taken. Keep stderr logging as it is. Cap the file by
   truncating to its last 1000 lines when it exceeds that, checked once per invocation. The hook
   fires on every `/simplify` and `/code-review` in a long-lived checkout, so unbounded growth is
   not acceptable and a rotation scheme is more machinery than the problem needs.
2. Add a `--doctor` mode that resolves against the current branch and prints what it would do,
   writing nothing: no label, no export, no log line. It takes no hook payload on stdin and no
   arguments; it reads the current branch itself. Guard it before the payload read at the bottom of
   the script, so a missing stdin cannot hang it.

Verification: §5c cases 10 through 12 pass. `--doctor` on an outrigger branch names the bead and the
label it would apply. `--doctor` on `main` reports no candidate, and exits 0.

### M4: Close the drift

1. Add a content hash near the top of the script, computed at build time by the installer and
   logged on every run. A hash rather than a `VERSION` string, because a hash self-maintains and a
   version needs a bump discipline nothing here enforces.
2. **The installer already reports `installed` / `updated` / `already current` (§2.4).** Extend it
   rather than rebuild it: print a one-line summary of what differs before overwriting, and add a
   `--check` flag that reports drift and exits non-zero without copying, so a pre-push hook can use
   it later.
3. **Conditional; check §4b first.** Re-sync this repository's own `.claude/scripts/` copy, which
   on `main` is missing `classify_skill`, `run_label_flow`, `handle_prompt`, and
   `skill_for_command`, then wire `UserPromptSubmit` in `.claude/settings.json`, which currently
   wires only two events. `outrigger/ci8` already does both. If that branch landed, verify with
   `diff` and skip this step.
4. Reinstall into `fathom`. **This deletes fathom's `br` support**, which is dead code there:
   `br` is not on that machine's PATH and fathom runs the `embeddeddolt` backend. The same change
   must delete the 18 `br` references in `fathom/tests/test_bead_label_hook.py`, including
   `test_a_database_file_of_any_name_resolves_to_br`, or that suite fails. This is a deliberate
   behavior removal, not incidental drift closure.

Verification: `diff` between source and each deployed copy is empty, the logged hash matches, and
both test suites pass in both repositories.

### M5: Inject-mode accounting, and the `ship` comment

**Rebase onto `outrigger/ci8` before starting, or wait for it to land (§4b).** Both items below
edit functions that branch rewrote.

1. `inject` mode writes a marker alongside `gate`'s, distinguished by mode. `handle_stop` reads it,
   applies no label, and logs when a requested inject label never appeared. Reuse
   `MARKER_TTL_SECONDS`.
2. Add a comment to `skill_for_command` recording that `ship` and `tadw:ship` are deliberately
   unmapped because `/tadw:ship` closes the bead, per §3 decision 6. No entry, no label.

Verification: §5c cases 15 through 17 pass. A `/tadw:verify-acceptance` run reaching ACCEPTED leaves
either the label or a log line saying it was owed and not applied.

## 5a. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The widened pattern floods `bd show` with junk candidates and slows every skill start | The 12-probe cap in M1, plus positional candidates first so the real id is usually probe one. §5c case 5 pins the cap |
| A widened pattern resolves the *wrong* bead from a slug that happens to match | Ordering is longest-first and positional-first; verification against the tracker is unchanged. §5c case 4 pins the ordering |
| M2 makes `bv` and Manifest read a stale export | `bv` reads the database directly (§5b Q1). The env var restores the old behavior for Manifest |
| Reinstalling into other repositories overwrites a locally patched copy | M4's drift report names the difference before overwriting, and `--check` reports without copying |
| **M2 fails two committed tests that assert the opposite, blocking the push** | M2 step 2 inverts both in the same change. This is why M2 is not a one-line edit |
| **M4's reinstall silently removes `br` support from fathom and fails 18 assertions there** | M4 step 4 deletes those cases in the same change, and records the removal as deliberate |
| **A concurrent branch is editing `resolve_bead` right now** | §0 requires re-reading the file and reconciling with `outrigger/ci8` before starting |

## 5b. Open questions

1. ~~**Does any consumer genuinely require the export to be fresh mid-session?**~~ **Answered
   during review, for `bv`.** `bv --db` takes a "path to beads database file or .beads directory",
   so `bv` reads the database and M2 costs it nothing. Manifest is still unconfirmed; the
   `TADW_BEAD_LABEL_EXPORT=1` escape hatch covers it either way, and M2 should not block on it.
2. **Should the positional rule be outrigger-specific or general?** Segment two is right for
   `outrigger/<id>/<slug>`. A repository using `feature/<slug>` would offer a slug as its first
   candidate, costing one wasted probe. Probably acceptable; confirm before generalizing further.
   Does not block M1: the cost of being wrong is one subprocess.

## 5c. Testing strategy

Two suites cover this script today, and both pin behavior this plan changes. The first draft
mentioned neither; both are in scope.

| Suite | Repository | Runs in | What it pins here |
|---|---|---|---|
| `hooks/test-claude-scripts.sh` | this one | `.githooks/pre-push`, and CI | the `label/*` cases, including `label/bd: refreshes the export instead of committing it` |
| `tests/test_bead_label_hook.py` | `~/Dev/fathom` | `uv run pytest -q`, via `lefthook.yml` pre-push | unit-level resolution, and `test_bd_refreshes_the_export_so_local_readers_are_not_stale` |

Case and line counts are deliberately absent from that table. They are the same class of hazard as
line numbers (§0), and `outrigger/ci8` shifts both (§4b).

**Level.** Shell integration tests against the real script, through the existing stub harness in
`hooks/test-claude-scripts.sh`. It already stubs `bd`, `git`, and `gh`, creates throwaway
repositories, and records argv, so no new harness is needed. No unit layer is added; the defect
this plan fixes lived between the units. That is precisely why fathom's suite stayed green through
the whole outage.

**Cases to add, by milestone.**

M1, resolution:

1. Branch `outrigger/zkc.5/rank-beads-and-reminders-deterministical` resolves to the bead whose
   short id is `zkc.5`. This is the regression case for the whole outage.
2. Branch `feature/tadw-alpha-one/x` still resolves, so the widened pattern breaks nothing the
   seven existing `add_branch` cases already cover.
3. Branch `main` resolves nothing, returns non-zero, and logs.
4. A branch whose slug alone matches a real bead resolves the positional segment first, not the
   slug, proving the ordering rule.
5. A branch offering more than twelve candidate tokens issues at most twelve `bd show` probes,
   asserted against the recorded argv.

M2, export:

6. On a clean tree, a labeled skill runs `bd update` and no `bd export`. This replaces the existing
   `label/bd: refreshes the export instead of committing it`, which asserts the opposite.
7. With `TADW_BEAD_LABEL_EXPORT=1`, the export runs.
8. With `.beads/issues.jsonl` already modified, the export runs without the env var.
9. After case 6, `git status --porcelain` is empty.

M3, visibility:

10. Every invocation appends exactly one line to `$GIT_COMMON/bead-label.log`, carrying the branch,
    the resolved id or `unresolved`, and the action.
11. An unresolved run still exits 0 and still writes its line.
12. `--doctor` on a resolvable branch names the bead and the label, calls no `bd update`, and
    writes no log line.

M4, drift:

13. The installer run twice reports `already current` the second time and copies nothing.
14. The installer against a modified destination reports what differs before overwriting, and
    `--check` exits non-zero without copying.

M5, inject accounting:

15. An inject-mode PreToolUse writes a marker distinguishable from a gate marker.
16. Stop with an unresolved inject marker applies no label and logs that one was owed.
17. An inject marker past `MARKER_TTL_SECONDS` is abandoned, not resolved.

**Fathom.** Case 6's equivalent replaces `test_bd_refreshes_the_export_so_local_readers_are_not
_stale`. M4 step 4 removes the `br` branch from the script, so the 18 `br` references in that suite
are deleted in the same change.

**Manual verification stays** as written in §6, as an end-to-end check after the automated suites
pass. It is evidence, not the gate.

**Gate.** `bash hooks/test-claude-scripts.sh` passes with zero failures before any commit, and
`.githooks/pre-push` enforces it.

## 6. Verification, whole plan

The plan is done when both automated suites pass with zero failures, and, in a fresh outrigger
worktree in `~/Dev/fathom`:

1. `/tadw:fresh-eyes-cr` applies `reviewed` to the branch's bead.
2. `git status --porcelain` is empty immediately afterwards.
3. `/tadw:verify-acceptance` reaching ACCEPTED results in the `accepted` label, or a log line saying
   it was owed.
4. `$GIT_COMMON/bead-label.log` holds one line per invocation.
5. `diff` between this repository's script and each deployed copy is empty, including this
   repository's own `.claude/scripts/` copy.
6. `bash hooks/test-claude-scripts.sh` reports zero failures here, and fathom's own gate,
   `uv run pytest -q` via `lefthook.yml` pre-push, reports zero failures there.

## 7. Follow-ups to file as beads, not to build now

- Audit the other repositories carrying a deployed copy for the same drift, using M4's `--check`.
- Wire `install_label_bead_on_skill_invocation.sh --check` into `.githooks/pre-push`, so a drifted
  deployed copy blocks a push rather than waiting to be noticed.
- Confirm whether Manifest reads the JSONL export or the database, and drop the
  `TADW_BEAD_LABEL_EXPORT` escape hatch if nothing needs it (§5b Q1).
- The `/tadw:ship` skill defects from the same session, tracked separately.

## 8. Constraints for the executing agent

- **Re-read the file before editing, and re-check `git log --oneline -1`.** See §0. The file changed
  length three times during the review, `main` moved backwards, and a concurrent branch
  (`outrigger/ci8`) is editing `resolve_bead`.
- **Cite by function name, never by line number**, in the code, the commit message, and any bead
  you file.
- The script declares `#!/usr/bin/env bash` and uses `BASH_REMATCH` in `handle_prompt`. Keep it
  bash; do not make it POSIX-portable, and do not assume zsh.
- Preserve the exit-0-on-every-failure contract stated in the header comment. M3 adds visibility,
  not a failure mode.
- Do not add a tracker backend. bd only, and M4 removes fathom's dead `br` branch.
- Do not hand-edit `.beads/issues.jsonl` in any repository.
- Land M1 and M2 in one change, including their test-case changes.

## 9. Review changes applied, 2026-08-22

From `/tadw:plan-review`. Each item below is a change to this document, not to code.

1. **Added §5c Testing strategy.** No milestone previously owned either test suite.
2. **Corrected §2.4.** The installer already reports `installed` / `updated` / `already current`;
   the first draft claimed it compares nothing. M4 step 2 narrowed accordingly.
3. **Added the in-repo drift to §2.4.** This repository's own deployed copy is 52 lines and four
   functions behind, committed and clean. M4 step 3 and §4 now cover it.
4. **Replaced all line citations with function names**, and added §0 explaining why.
5. **Moved the resolution test from §7 into M1.** §4 listed it in scope while §7 deferred it.
6. **Added the test-suite inversion to M2**, which otherwise fails the pre-push gate.
7. **Added the `br` removal to M4 step 4**, which otherwise breaks 18 assertions in fathom.
8. **Closed §5b Q1 for `bv`**, which reads the database directly.
9. **Decided the `ship` question in §3 decision 6**, which M5 previously left as an either/or.
10. **Added §4a Dependencies** and three risk rows to §5a.
11. **Bounded M3's log file** and gave `--doctor` an argument contract.
12. **Picked the content hash** over a `VERSION` string in M4 step 1.

### Second pass, same day

The re-review checked all twelve items above against the body and found them present. It then found
two claims this revision had introduced and got wrong, plus two brittle details.

13. **Corrected §0's collision claim.** `outrigger/ci8` does not touch `resolve_bead`. It rewrites
    `classify_skill`, `run_label_flow`, `handle_pre`, and `handle_stop`, which are M4 step 1 and
    both items of M5. §0 had pointed the executing agent at the one function that is safe.
14. **Added §4b Sequencing against work in flight.** M4 step 3 is already done on that branch, so
    nothing owned deciding whether to do it. M1 and M2 remain unblocked either way.
15. **Corrected §6 criterion 6.** Fathom's gate is `uv run pytest -q` through `lefthook.yml`, not a
    single-file `pytest` invocation.
16. **Removed the case and line counts from §5c's table**, which `outrigger/ci8` shifts.
