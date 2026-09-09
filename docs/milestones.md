# Milestones

What this repository is working toward, and the label that maps a bead to each one.

**Every date is a plain hyphen, because no date has been decided.** A guessed date looks exactly
like a real one, so nothing writes a date here except the repository's owner. `/bead-refine` reads
the names in this file to decide whether a bead is on route, a detour, or hardening. It reads the
names only, never the dates, so a blank date blocks nothing.

This file is named `milestones.md` and not `roadmap.md`, because `roadmap-dashboard` generates
`docs/roadmap.html` from the tracker. Two files one letter apart, flowing in opposite directions,
would be confused.

## The milestones

| Milestone | Target date | What it delivers | Label |
|---|---|---|---|
| Verification loop | - | A `verify-app` skill that drives a running application, so a build proves itself against the real thing rather than against its own tests | `plan:verification-loop` |
| Readable beads | - | Every bead opens with an `**Ask:**` line, checked by a script, written at a fixed reading level | `plan:readable-beads` |
| Research brain upgrade | - | The Research wiki becomes a knowledge base you can ask a question of, rather than a pile of notes | `plan:research-brain-upgrade` |
| Quality-gates hardening | - | The QA gates stop reporting more confidence than they earned: a real API probe, a scripted artifact write, pinned verdict rules | `qg-hardening` |
| Quality-gates agent refactor | - | The gates run as one agent and return the same verdict twice on an unchanged tree | `qg-agent` |
| Style-markdown rollout | - | The repository's own Markdown obeys the style skill, and a linter holds the rule instead of a person | `plan:style-markdown` |
| Domain docs wiring | - | `check_domain_docs.py` runs in the push gate, so the domain documents cannot rot unnoticed | `plan:domain-docs-wiring` |
| Token routing | - | An opt-in hook caps how much a single read pulls into the context window | `plan:token-routing` |

## Two things this table does not say

**The `milestone-2` through `milestone-5` labels are not milestones.** They number the steps inside
two separate plans, and `milestone-5` sits on beads from both. Ignore them when routing.

**Five plans under `docs/plans/` have no live bead**, so they are read as finished and take no row:
`feature-plan-bead-refine.md`, `feature-plan-style-testing.md`,
`feature-plan-style-testing-part-2.md`, `bead-label-hook-resolution-and-visibility.md`, and
`style-hook-and-skill-hardening.md`.

## Keeping this file true

A new `plan:<name>` label needs a row here, or `/bead-refine` routes its beads as detours. Check
with:

```bash
bd list --status open,in_progress,blocked,deferred --limit 0 --json \
  | python3 -c "import json,sys;print(sorted({l for i in json.load(sys.stdin) for l in (i.get('labels') or []) if l.startswith('plan:')}))"
```
