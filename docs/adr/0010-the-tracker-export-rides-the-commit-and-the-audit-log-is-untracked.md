# 0010. The tracker export rides the commit, and the audit log is untracked

**Date:** 2026-09-06
**Status:** Accepted

## Context

`bd` writes two JSONL files into `.beads/`, and they are different kinds of thing.

`issues.jsonl` is a passive export of the issues table. `bd export` regenerates it whole, it has a
merge driver, and it is the file a fresh clone reads to see the beads.

`interactions.jsonl` is an append-only audit log. `bd` adds a line on every field change, so it is
dirty in the working tree almost continuously. Nothing regenerates it, because `bd export` covers
the issues table only. Nothing in CI reads it. Every commit on every branch appends to it, so it
is the file two branches touch most often.

**The reason this decision was first given is wrong, in both repositories.** Commit `5a8a8ff`
here, and the comment ported with it, said `interactions.jsonl` had no merge driver and so
conflicted line by line. It has one, and it did not conflict:

| | What `.gitattributes` sets | What the ported comment claimed |
|---|---|---|
| atlas | `*.jsonl merge=union` covers it; a later line overrides `issues.jsonl` to `merge=beads-jsonl` | "no merge driver **in .gitattributes**" |
| here | both files named on their own lines, both `merge=union` | "no merge driver", the qualifier dropped in the port |

`git check-attr merge .beads/interactions.jsonl` returned `union` in both. Union merge takes lines
from both sides without a conflict, so the cost was never a conflict. It was a file that every
merge made longer, ordered by side rather than by time, that nothing reads.

**The decision survives its reason.** The evidence that actually carries it is the commit count,
and that was measured: in atlas the file was committed 16 times, every one a side effect of a
commit about something else. Nothing about that depends on how git merges it.

## Options Considered

### Option A: untrack `interactions.jsonl`, and export `issues.jsonl` at commit time

Add `interactions.jsonl` to `.beads/.gitignore`. Add an export block to `.githooks/pre-commit`
that refreshes `issues.jsonl` and stages it, so it rides along in whatever commit was already
being made.

- **Pros:** The working tree stops being continuously dirty over a file nobody reads. The export
  lands in the commit it belongs to rather than in a follow-up commit on the next push. Neither
  file is ever a person's responsibility.
- **Cons:** The forensic record leaves git. Two hooks now touch `.beads/`, and the pre-push stage
  becomes a backstop for a case pre-commit already covers.

### Option B: keep both tracked, and keep the export in `pre-push` alone

- **Pros:** One hook owns the export. Every field change is preserved in git history.
- **Cons:** Every merge unions two branches' audit lines into a file nothing reads, ordered by
  side rather than by time, and it grows without bound. The export also lands one push late, so a
  clone that pulls between the two pushes reads stale beads.

### Option C: untrack `interactions.jsonl`, and leave the export in `pre-push`

- **Pros:** Stops the audit log growing in git, with the smallest change.
- **Cons:** Keeps the one-push-late export, which is the part that actually misleads a reader.

## Decision

**Option A. `interactions.jsonl` is untracked, and `issues.jsonl` is exported and staged by
`.githooks/pre-commit`.** Ported from atlas (`atlas-xh3s`).

The forensic record `interactions.jsonl` held lives in the Dolt database, which is where `bd`
reads it from. Git was storing a second copy that nothing read, that every commit dirtied, and
that every merge made longer.

**Its `.gitattributes` line went with it.** Setting a merge driver for a file git does not track
is dead configuration, and leaving it would have kept the impression that the file is still
managed. The comment in `.beads/.gitignore` was corrected at the same time, because that is the
copy somebody reads when deciding whether to track it again. Commit `5a8a8ff` keeps its wrong
sentence: it is merged history, and rewriting it means force-pushing `main` over a message.

The pre-commit block has three deliberate properties:

- **It contains no `exit`.** It runs inside a hook whose own status decides the commit, and an
  `exit 0` there would turn a failing gate into a passing one. Every failure path leaves the status
  alone. The block sits before the `bd`-managed section, so the beads section still decides.
- **It times out.** `bd` can block on database lock contention, and a stuck `bd` would hang the
  commit with nothing on screen. The limit is shorter than `bd`'s own 300 seconds, because a commit
  should not stall for minutes over an export.
- **It writes a temp file first.** `bd export -o` truncates its target as it starts, so a killed
  export would leave a partial file, and staging that is worse than not exporting at all.

**`.githooks/pre-push` keeps its export stage, as a backstop.** After a pre-commit export the
tree is normally clean, so the pre-push stage finds nothing to commit and says nothing. It still
covers a commit made with `--no-verify`, or from a clone whose `core.hooksPath` was never set.
Both stages forgive on the same terms
([ADR 0004](0004-the-pre-push-hook-forgives-by-design.md)): a missing `bd`, or a failed export,
only warns.

Option B lost to the unbounded growth of a file nothing reads. Option C lost because it leaves
the stale-clone window open.

## Consequences

**Easier:**

- An append-only log that every commit dirties, and that every merge unions and lengthens, is no
  longer in git at all.
- The export is in the commit that changed the beads, so a clone reading `issues.jsonl` at any
  commit sees the tracker as of that commit.
- The working tree stops showing a permanently modified file, which was training people to ignore
  `git status` on `.beads/`.

**Harder:**

- **The audit log is per machine now.** A field change made on one clone leaves no trace on
  another except through the Dolt database. Anyone reconstructing history from git alone will not
  find it.
- **Two hooks touch `.beads/`, and only one is usually the one that acts.** A reader tracing why
  `issues.jsonl` changed has to check both, and the pre-push text in `AGENTS.md` describes a stage
  that now rarely fires.
- **`--no-verify` silently skips the export.** The pre-push backstop catches it on the way out,
  one push late, which is the behavior this record set out to remove.
- **The pre-commit block is untested by any suite.** `.githooks/test_prepush.py` pins the pre-push
  stages against real `git push --dry-run` runs. Nothing does the same for pre-commit; it was
  verified by running the patched hook once.
