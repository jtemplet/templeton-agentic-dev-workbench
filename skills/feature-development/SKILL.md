---
name: feature-development
description: "Implement a spec in the house style, invoked as /build. Takes a bead id (preferred) or a feature description, reads the spec from br rather than re-interviewing you, learns the repo's language, framework, and local conventions before writing anything, loads the matching style skills, implements criterion by criterion with a test per criterion, then simplifies and lints. Stops at implemented; grading and closing belong to /quality-gates and /verify-acceptance."
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
- The spec does not exist yet (use `/plan-feature`, then `/plan-to-beads`).
- The bead's criteria are too thin to build against. Run `bead-audit` first and stop; see Phase 1.
- Grading finished work (use `/verify-acceptance`).

## Phase 1: Ground the spec

**With a bead id.** Read it, and do not interview the user about what it already says.

```bash
br show <id> --json
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
2. **The dependency manifest**, for the framework and the test runner, not just the language: `pyproject.toml`, `Gemfile`, `package.json`, `Package.swift`, `go.mod`, `*.csproj`.
3. **The two or three existing files nearest the change.** Find them with Grep or Glob on the closest existing behavior. These tell you the real conventions: module layout, error handling, logging, naming, how tests are structured.

**Then load the style skills.** Match on the extensions you will write:

| Extension | Style skill |
|---|---|
| `.py` | `style-python` |
| `.rb`, `.erb`, `.rake` | `style-rails` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `style-frontend` |
| `.swift` | `style-swift` |
| `.go` | `style-go` |

Add these on top, when they apply:

- **`style-testing`** for any test file, in any language. Match on `test_*.py`, `*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`, `*_spec.rb`, `*_test.rb`, `*Tests.swift`, `*_test.go`, or anything under `tests/`, `test/`, `spec/`, or `__tests__/`.
- **`style-rspec`** on top of `style-testing` when the suite is RSpec.
- **A project-local style skill, when one exists and covers what you are about to write.** This is the difference between correct-for-the-language and correct-for-this-repo. Check the available skill list for one naming this project or this surface, and load it. `style-fizzy` for the Fizzy codebase and `jbuilder-style` for Loan Labs factory API views are examples of the kind. When one exists and contradicts the general language skill, the local skill wins.

For an unlisted language, say so, name what you will follow instead (the injected core plus the conventions you read in step 3), and continue.

**Output of this phase:**

```text
## Oriented

**Stack:** [language, framework, test runner, from the manifest]
**Project instructions:** [what AGENTS.md/CLAUDE.md constrains here, or "none found"]
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
**Criteria not met:** [any, and why] (omit when none)
```

## Phase 4: Simplify

Apply the `code-simplify` skill to the code you just wrote, via the Skill tool. It reduces nesting, improves naming, extracts where warranted, and removes redundancy after the third occurrence. It re-applies the same style skills, so do not restate their rules.

Run the tests again afterward. A simplification that breaks a test is not a simplification.

## Phase 5: Lint

| Language | Linter | Command |
|---|---|---|
| Python | ruff | `ruff check <file> --fix` then `ruff format <file>` |
| JavaScript / TypeScript | ESLint + Prettier | `eslint --fix <file>` then `prettier --write <file>` |
| Ruby | RuboCop | `rubocop -A <file>` |
| Swift | swift-format | `swift-format --in-place <file>` |
| Go | gofmt, go vet, staticcheck | `gofmt -l -w .`, then `go vet ./...`, then `staticcheck ./...` |

Prefer the command the project itself declares (a `lint.sh`, a task runner target, or the command named in `AGENTS.md`) over the generic one above. If the linter is not installed, say so, offer to install it, and note that manual review replaced it rather than reporting a pass.

Report what was auto-fixed and what was not. Unfixable violations go to the user with an explanation, never silently.

**Output of this phase:**

```text
## Feature complete

**Bead:** <id> (still open, and still yours to close)
**Files delivered:** [paths]
**Tests:** [command, and the real count: "14 passed, 0 failed"]
**Linter:** [command, and what it changed]
**Criteria met:** N of M [name any not met]

**Next:** /quality-gates for the full sweep, then /verify-acceptance to grade this against the bead.
```

## Workflow Management

Track the five phases with TodoWrite, marking each `in_progress` on entry and `completed` on exit:

```text
1. Ground: read the bead, confirm it is buildable
2. Orient: read the repo, load the style skills
3. Implement: code + a test per criterion
4. Simplify: apply code-simplify, re-run tests
5. Lint: run the project's linter
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
- Load the language style skill, plus `style-testing` for tests and any project-local style skill.
- Write to files, and give real test counts, never "tests pass".
- Leave tracker state alone: no claim, no status change, no close.

**Never:**

- Interview the user about a spec the bead already states.
- Detect language by extension alone and call that understanding the repo.
- Restate language style rules here; they live in the style skills.
- Build a bead its own notes call too big, or one whose criteria you had to invent.
- Report a criterion as met without a named test, a command's output, or a `file:line`.
- Close the bead or declare the work accepted. That is `/verify-acceptance`, and it is a separate judgment for a reason.
