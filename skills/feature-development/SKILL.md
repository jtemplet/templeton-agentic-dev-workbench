---
name: feature-development
description: "Implement a spec in the house style, invoked as /build. Takes a bead id (preferred) or a feature description, reads the spec from bd rather than re-interviewing you, learns the repo's language, framework, and local conventions before writing anything, loads the matching style skills, implements criterion by criterion with a test per criterion, then simplifies, lints, and labels the bead `implemented`. Stops at implemented; grading and closing belong to /quality-gates and /verify-acceptance."
---

# Feature Development

Turns a written spec into working code that matches this repository's conventions. The spec is normally a bead: `/build tadw-some-bead-xyz`.

Five phases: **Ground**, **Orient**, **Implement**, **Simplify**, **Lint**. The first two exist because code that ignores its spec or its repo is the expensive failure, and both are knowable before the first edit.

## Universal Core (injected)

The universal coding-style core (`hooks/style-core.md`) is injected into every session and subagent, so TRUE code and the cross-language principles (small units, wait for duplication, tell-don't-ask, compose over inherit, fail fast, names that document) are already in context while you implement. This skill owns the *workflow*; the style skills loaded in Phase 2 own the per-language rules. Do not restate either here.

## When to Use / When NOT to Use

Use this skill when:

- A bead describes work that is ready to build, and you have its id.
- Implementing a new feature, function, class, or module from a written spec.
- Asked to "build", "create", "add", or "implement" something.

Do NOT use this skill when:

- Fixing a one-line bug (just fix it).
- Refactoring without behavior change (use `code-simplify`).
- The spec does not exist yet (use `/write-plan`, then `/plan-to-beads`).
- The bead's criteria are too thin to build against. Run `bead-audit` first and stop; see Phase 1.
- Grading finished work (use `/verify-acceptance`).

## Phase 1: Ground the spec

**With a bead id.** Read it, and do not interview the user about what it already says.

```bash
bd show <id> --json
```

Read four fields: `title`, `description` (the Why), `design` (the How), and `acceptance_criteria` (the Done when). Check `notes` for a `## Estimated size` block and an out-of-scope list.

Then judge whether it is buildable, and say which:

| What you find | What to do |
|---|---|
| Criteria are specific and checkable, and `design` names an approach | Proceed. Restate the criteria as your build checklist. |
| Criteria exist but are vague, or `design` is empty | Load `bead-audit`, report what is missing, and **stop**. Ask the user to fill the gap or to confirm you should proceed on stated assumptions. |
| `notes` says the bead is too big, or says "split before claiming" | Say so and stop. Building a bead that its own audit called too big produces a diff nobody can review. |
| The bead does not exist, or is already closed | Say so and stop. Do not guess at a near-match id. |
| `status` is `in_progress` and `assignee` names someone other than you | Say so and ask before proceeding. `assignee` is absent from the JSON when nobody holds the bead. |

Do not claim the bead, do not change its status, and do not close it. This skill writes code. Tracker state is the user's to move, and self-grading is the failure `verify-acceptance` exists to prevent.

**Without a bead id.** Ask 3 to 7 focused questions covering inputs, outputs, edge cases, errors, dependencies, where the code lives, and what observable behavior means done. Wait for answers, then write the acceptance criteria yourself and get them confirmed before coding. A criterion must be checkable by someone other than you, without asking you.

**Output of this phase:**

```text
## Spec grounded

**Source:** bead <id> (or: interview, criteria confirmed above)
**Building:** [one sentence]
**Out of scope:** [what the bead excludes, or "not stated"]

**Acceptance criteria (the build checklist):**
1. [criterion, verbatim from the bead]
2. ...
```

## Phase 2: Orient in the repository

Language is not the same as convention. Two Python repositories with the same style skill can still disagree about where code lives, which test runner runs, and what the local house rules are. Read the repository before writing to it.

**Read, in this order:**

1. **`AGENTS.md` or `CLAUDE.md` at the repo root.** Project instructions outrank every style skill; the injected core says so. Note anything that constrains the change: forbidden dependencies, privacy or tenancy invariants, required commands.
2. **The repository's development workflow document, when it has one.** It is normally named `development_workflow.md`, and its directory differs per repository: `docs`, `.agent_docs`, and `agent_docs` are all in use. List those directories rather than guessing one path. The document states the branch and worktree convention, the route from branch to `main`, and which gate runs at which step. Read it here, before the first edit, because its first step is usually about where the code is supposed to be written.
3. **`docs/adr/`, when the repository has one.** These are the architecture decision records: choices already made and not up for re-litigation in this bead. Read the titles, then open any whose subject your change touches. An ADR that contradicts your plan outranks the plan, the same way `AGENTS.md` does; say so in the phase output rather than quietly working around it.
4. **The dependency manifest**, for the framework and the test runner, not just the language: `pyproject.toml`, `Gemfile`, `package.json`, `Package.swift`, `go.mod`, `*.csproj`.
5. **The two or three existing files nearest the change.** Find them with Grep or Glob on the closest existing behavior. These tell you the real conventions: module layout, error handling, logging, naming, how tests are structured.

**Then set up the branch, before you edit anything.** Reading the document does not satisfy it, and this phase is where the commands run. Phase 3 writes files, and code written on the wrong branch costs a rebase or a cherry-pick to move.

Two cases, and only the second one runs a command:

| Where you are | What to do |
|---|---|
| Already on the branch or worktree for this work | Nothing. Check with `git rev-parse --abbrev-ref HEAD` and `git worktree list` before you create a second one. |
| Anywhere else | Create the worktree or branch, named as below, and work from there. This covers the default branch and any unrelated branch you happen to be standing on. |

Branch in both cases. A repository with no workflow document has not said "work on `main`"; it has said nothing, and the fallback below covers it.

**Where the name comes from, in this order:**

1. **The workflow document's own pattern, whenever it spells one.** It is a project instruction, and step 1 above already ranks those over this skill. Follow its branch shape and its worktree directory, and name it in the phase output.
2. **Otherwise `<type>/<bead-id>/<slug>`,** with the worktree directory named after the branch. `<type>` is one of `chore`, `feature`, or `bugfix`, picked from what the bead is rather than from how large it is. `<bead-id>` is the full id, so the branch and the tracker read against each other. `<slug>` is two to four lower-case words joined by hyphens, naming the work and not the file it touches.

```bash
git worktree add .worktrees/<type>/<bead-id>/<slug> -b <type>/<bead-id>/<slug>
cd .worktrees/<type>/<bead-id>/<slug>
```

Two adjustments to the fallback shape:

- **No bead id, because the build came from a free-text description?** Drop that segment and use `<type>/<slug>`. Do not invent an id.
- **The worktree directory is not ignored?** Create a plain branch of the same name instead, with `git switch -c`, and say so. Do not commit a worktree into the tree.

**Branching is all you take from a workflow document.** Such a document usually runs on to code review, QA, merging into `main`, and pushing. This skill stops at implemented, so those later steps stay with `/quality-gates`, `/verify-acceptance`, and `/tadw:ship`. Reading them here does not make them yours to run.

**Then load the style skills.** Match on the extensions you will write:

| Extension | Style skill |
|---|---|
| `.py` | `style-python` |
| `.rb`, `.erb`, `.rake` | `style-rails` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `style-frontend` |
| `.swift` | `style-swift` |
| `.go` | `style-go` |
| `.md`, `.markdown` | `style-markdown`, when the document is the deliverable |

A Markdown file is the deliverable when the bead's acceptance criteria are satisfied by what the document says: a skill, an agent, a command, a `docs/` page, an ADR, or a plan. It is not the deliverable when you are adding a line to a changelog or a release note beside a code change. In a repository whose product is documentation, this row fires on most beads, and that is the intent.

Add these on top, when they apply:

- **`style-testing`** for any test file, in any language. Match on `test_*.py`, `*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`, `*_spec.rb`, `*_test.rb`, `*Tests.swift`, `*_test.go`, or anything under `tests/`, `test/`, `spec/`, or `__tests__/`.
- **`style-rspec`** on top of `style-testing` when the suite is RSpec.
- **A project-local style skill, when one exists and covers what you are about to write.** This is the difference between correct-for-the-language and correct-for-this-repo. Check the available skill list for one naming this project or this surface, and load it. `style-fizzy` for the Fizzy codebase and `jbuilder-style` for Loan Labs factory API views are examples of the kind. When one exists and contradicts the general language skill, the local skill wins.

For an unlisted language, say so, name what you will follow instead (the injected core plus the conventions you read in step 4), and continue.

**Output of this phase:**

```text
## Oriented

**Stack:** [language, framework, test runner, from the manifest]
**Project instructions:** [what AGENTS.md/CLAUDE.md constrains here, or "none found"]
**Workflow document:** [path read, and the branch rule it states, or "none found"]
**Decisions that bind this change:** [ADR number and the rule it sets, one line each, or "none found"]
**Building in:** [branch and directory, and which pattern named it: the workflow document's, the `<type>/<bead-id>/<slug>` fallback, or already on it]
**Patterns to match:** [file:line for each of the 2-3 files read, one clause each on what it establishes]
**Style skills loaded:** [names]
**Files to touch:** [paths, with new vs modified]
```

## Phase 3: Implement

Work criterion by criterion, in dependency order (lowest-level first). Each criterion gets code and a test that proves it.

1. Write the test first when the criterion states observable behavior. It fails, then the code makes it pass.
2. Name each test after the criterion it proves, so `/verify-acceptance` can cite it. A criterion whose evidence is only a diff grades UNVERIFIABLE, which makes the whole verdict INCONCLUSIVE rather than ACCEPTED.
3. Match the patterns from Phase 2. Match the surrounding code's comment density and naming, not a general ideal.
4. Handle the edge cases the bead names. Do not invent scope it excludes.
5. **Write to actual files with Write or Edit. Never show code in chat as the deliverable.**
6. Run the tests as you go, not once at the end.

Stop and ask when a criterion turns out to be unbuildable as written, or when it contradicts what you read in Phase 2. Do not silently reinterpret a criterion to make it satisfiable.

**Output of this phase:**

```text
## Implemented

| Criterion | Code | Test |
|---|---|---|
| 1. [short form] | `path:line` | `test_name` |

**Files written:** [paths]
**Design decisions:** [decision and why, for anything a reader would question]
**ADR candidates:** [any design decision that constrains work beyond this bead] (omit when none)
**Criteria not met:** [any, and why] (omit when none)
```

**Promote a design decision to an ADR when it constrains work beyond this bead.** The
`Design decisions` block above is read once and then lost with the transcript; a file in
`docs/adr/` is read by every later Phase 2. A decision earns one when reversing it would cost
more than a day *and* somebody would otherwise argue it again. Everything else belongs in the
bead's `design` field, where it already is.

List each one under `ADR candidates`, then run `/adr` on it before the work ships. Do not write the
ADR silently, and do not file one per bead: a directory of records nobody obeys is worse than none,
because it makes the ones that do carry rules harder to find.

## Phase 4: Simplify

Apply the `code-simplify` skill to the code you just wrote, via the Skill tool. It reduces nesting, improves naming, extracts where warranted, and removes redundancy after the third occurrence. It re-applies the same style skills, so do not restate their rules.

Run the tests again afterward. A simplification that breaks a test is not a simplification.

## Phase 5: Lint

**The linter must exit clean, with zero violations.** Auto-fixing starts this phase; it does not end it. Run the linter again after the fixes and read its output. A run that still reports a violation means the phase is unfinished.

| Language | Linter | Command |
|---|---|---|
| Python | ruff | `ruff check <file> --fix` then `ruff format <file>` |
| JavaScript / TypeScript | ESLint + Prettier | `eslint --fix <file>` then `prettier --write <file>` |
| Ruby | RuboCop | `rubocop -A <file>` |
| Swift | swift-format | `swift-format --in-place <file>` |
| Go | gofmt, go vet, staticcheck | `gofmt -l -w .`, then `go vet ./...`, then `staticcheck ./...` |

Prefer the command the project itself declares (a `lint.sh`, a task runner target, or the command named in `AGENTS.md`) over the generic one above.

**Fix by hand whatever the auto-fixer leaves behind.** Correct those violations in the code, one at a time, until a fresh run reports none. Re-run the tests after each correction, because a lint fix can change behavior.

Two states end this phase without a clean run. Both are stops, and neither is a pass:

- **A violation you cannot fix without contradicting the bead or the conventions from Phase 2.** Name the rule, give the `file:line`, say why the fix conflicts, and ask. Do not reach for an inline disable to drive the count to zero. Use one only where the repository already suppresses that same rule the same way, and write the reason in the comment beside it.
- **The linter is not installed.** Say so, offer to install it, and report the phase as not run. Manual reading is not a substitute, and a phase that never ran has not passed.

Report what the auto-fixer changed, what you fixed by hand, and the count from the final run. Never report a violation as fixed when it was suppressed.

## Phase 6: Label the bead

Add the `implemented` label to the bead as the last action of the run:

```bash
bd update <bead-id> --add-label implemented
```

**Apply it only when all three are true:** every acceptance criterion is met, the tests pass, and
the linter reports zero violations. A run that stopped in Phase 1 over a thin spec has not earned
the label. Neither has a run that left a criterion unmet, a test failing, or a violation standing.

**When the run misses that gate, add no label.** Name the failing condition on the `Label:` line of
the report instead.

This label is the only thing the run writes to the bead. It does not close the bead. It does not
set the bead's status either, because the labeling hook already moved the bead to `in_progress`
when the run started. A `Stop` hook reads the bead after the run and writes
`OWED implemented, the run never applied it` to `<git-common-dir>/bead-label.log` when the label is
missing, so a skipped phase leaves a record either way.

Skip this phase when the work has no bead. A free-text description has nothing to label.

**Output of the run**, written after Phase 6 applies or withholds the label:

```text
## Feature complete

**Bead:** <id> (still open, and still yours to close)
**Files delivered:** [paths]
**Tests:** [command, and the real count: "14 passed, 0 failed"]
**Linter:** [command, what it auto-fixed, what you fixed by hand, and the final count: "0 violations"]
**Criteria met:** N of M [name any not met]
**Label:** [`implemented` applied, or the condition that withheld it]

**Next:** /quality-gates for the full sweep, then /verify-acceptance to grade this against the bead.
```

## Workflow Management

Track the six phases with TodoWrite, marking each `in_progress` on entry and `completed` on exit:

```text
1. Ground: read the bead, confirm it is buildable
2. Orient: read the repo and its workflow document, set up the branch, load the style skills
3. Implement: code + a test per criterion
4. Simplify: apply code-simplify, re-run tests
5. Lint: run the project's linter, fix every violation, re-run it clean
6. Label: add `implemented` to the bead, or say which condition withheld it
```

## Edge Cases

**The bead's criteria and its design disagree.** Report both, say which you would follow and why, and ask. Do not average them.

**The change spans several languages.** Load one style skill per language and say which file each governs. A React component plus its Python endpoint needs both.

**A criterion cannot be tested automatically** (a visual result, a manual deploy step). Say so explicitly, write down the manual check, and mark that criterion as needing human verification rather than writing a test that asserts nothing.

**Existing code covers part of the bead.** Read it first, then use Edit rather than Write. Say what was already done, so the diff is not credited with work it did not do.

**The user asks to skip a phase.** Respect it, state the trade-off in one sentence, and note the skip in the final report. Never skip Phase 2 silently; unoriented code is how conventions drift.

## Critical Rules

**Always:**

- Read the bead before asking the user anything it already answers.
- Read `AGENTS.md`/`CLAUDE.md` and the nearest existing files before writing.
- Read the repository's development workflow document, and set up the branch or worktree it names, before the first edit.
- Load the language style skill, plus `style-testing` for tests and any project-local style skill.
- Write to files, and give real test counts, never "tests pass".
- End Phase 5 on a clean linter run, proven by re-running it: zero violations, or a named stop.
- Leave tracker state alone: no claim, no status change, no close.

**Never:**

- Interview the user about a spec the bead already states.
- Detect language by extension alone and call that understanding the repo.
- Restate language style rules here; they live in the style skills.
- Build a bead its own notes call too big, or one whose criteria you had to invent.
- Report a criterion as met without a named test, a command's output, or a `file:line`.
- Report the feature complete while the linter still reports a violation, or count a suppressed violation as a fixed one.
- Close the bead or declare the work accepted. That is `/verify-acceptance`, and it is a separate judgment for a reason.
