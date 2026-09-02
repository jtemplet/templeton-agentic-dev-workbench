# 0003. A push to main is already published

**Date:** 2026-09-01
**Status:** Accepted

## Context

This plugin has no publish step, and that surprises people who look for one.

The marketplace entry lives in the separate `jtemplet/templeton-agentic-marketplace`
repository. Its marketplace manifest, which lives in that repository and not this one, names this plugin as:

```json
{
  "name": "tadw",
  "source": { "source": "url", "url": "https://github.com/jtemplet/templeton-agentic-dev-workbench.git" },
  "version": "latest"
}
```

There is no ref, no tag, and no commit pin. Every consumer follows this repository's default
branch. `.github/workflows/` holds one file, `lint.yml`, which runs checks and uploads nothing.

So a `git push` to `main` has already shipped the change to everyone. The `version` field in
`.claude-plugin/plugin.json` and the `vX.Y.Z` tags do not gate distribution at all.

Leaving that implicit cost real state twice, and neither failure announced itself:

- `plugin.json` sat at 2.10.1 while `main` ran 13 commits past its release commit. Consumers were
  running code that no version number described.
- `v2.10.0` and `v2.10.1` were created locally and never pushed. Reading the tags on GitHub, the
  released state looked older than it was.

A third trap sits next to those. `git tag --list 'v*'` sorts lexically, which puts `v2.10.1`
above `v2.5.2`, so a released tag reads as missing unless the command passes `--sort=-v:refname`.

## Options Considered

### Option A: Accept it. Numbering is a label on a state that already shipped

Treat the push as the distribution event. Keep the version and the tag as a way for a person to
say which published state they are running, and automate producing them.

- **Pros:** Matches what the marketplace actually does, so nothing has to be kept in sync by
  hand. No release infrastructure to maintain. Several landings can batch into one number, which
  is how releases are usually cut anyway.
- **Cons:** No gate exists between a merge and every consumer. A bad push reaches everyone at
  once, and the only protection is the pre-push hook. "Released" stops meaning "tested more than
  the branch was".

### Option B: Pin the marketplace to a tag

Change the marketplace entry from `"version": "latest"` to a tag or a `ref`. A push then reaches
nobody until a tag moves.

- **Pros:** Restores a real release gate. A consumer can stay on a known version. A bad merge is
  survivable, because it is not distributed.
- **Cons:** Requires editing a second repository on every release, which is exactly the manual
  step that drifted twice already. Consumers stop getting fixes until somebody remembers to tag.
  For a personal plugin with one maintainer, the gate mostly delays fixes to that maintainer.

### Option C: Add a publish workflow that builds an artifact

Introduce a GitHub Actions workflow that packages a release on tag, and point the marketplace at
the artifact.

- **Pros:** The strongest separation between "merged" and "published". Room for a signing or
  verification step later.
- **Cons:** The most infrastructure for the least benefit here. Claude Code consumes a plugin
  from a git URL, so packaging adds a format nothing asked for. Solves a distribution problem
  this project does not have.

## Decision

**Option A. A push to `main` is the publication.** The `vX.Y.Z` tag and the `version` field are a
label on a state consumers already have, not a gate in front of it.

Two things follow from that, and they are the whole point of writing this down:

**`/publish-plugin` owns the numbering.** It derives the semver bump from the diff since the last
tag, writes the CHANGELOG section, bumps the manifest, commits `chore(release): X.Y.Z` touching
exactly those two files, then pushes `main` before the tag. Doing it by hand is what caused both
drift incidents, so the skill exists to remove the hand.

**The pre-push hook is the only gate there is.** With no release step between a merge and a
consumer, the check that runs at push time is doing the job a staging environment would do
elsewhere. That is why [ADR 0004](0004-the-pre-push-hook-forgives-by-design.md) is careful about
what it refuses.

Option B lost because the manual step it adds is the same manual step that already failed twice,
and it would delay fixes to reach the one person most likely to need them. Option C lost because
it builds distribution machinery for a consumer that reads a git URL directly.

## Consequences

**Easier:**

- Nothing needs syncing between two repositories on a release. The marketplace entry is written
  once and never touched again.
- A fix reaches consumers the moment it lands, with no second action required.
- Batching several landings into one version number is the normal case rather than a special one.

**Harder:**

- There is no undo. Reverting a bad change means another push, and every consumer saw the bad
  state in between.
- The pre-push hook carries more weight than a pre-push hook usually does. Turning it off with
  `TADW_PREPUSH=off` is publishing unchecked, and the variable is documented so nobody invents a
  worse workaround under deadline.
- Reading the last released version requires `git tag --list 'v*' --sort=-v:refname`. Without the
  sort flag the answer is wrong whenever a minor number reaches double digits, and it is wrong
  silently.
- "Publish" and "land" name different things and must stay apart in prose. `CONTEXT.md` defines
  both.
