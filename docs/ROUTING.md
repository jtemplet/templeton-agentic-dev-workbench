# Task Routing

The long form of the routing table in `AGENTS.md`: which command, skill, or agent to
reach for per task, and what each one does. The workflow pipelines live in `README.md`.

This covers 18 of the 30 commands. The twelve without a section here are named in the
`AGENTS.md` pointer, and each has a one-line description in `README.md`.

## Language-Specific Workflows

### Python Development

**Code Review:** Use `/python-code-review` or the `review-python` skill

- Checks PEP 8 and Google Python Style Guide compliance
- Reviews security, performance, and maintainability

**Feature Development:** Use `/build <bead-id>` or the `software-engineer` agent + `feature-development` skill

- 5-phase workflow: ground the bead, orient in the repo, implement, simplify, lint
- Reads the bead from `bd show <id> --json` rather than interviewing about what the bead records
- Loads `style-python` for Python file style decisions, plus `style-testing` for tests
- Runs `ruff` for linting, or the command the project declares
- Leaves the bead open; grading is `/quality-gates` then `/verify-acceptance`

**Code Simplification:** Use the `software-engineer` agent + `code-simplify` skill

- Works across Python, Ruby/Rails, Frontend, Swift
- Loads the matching language style skill automatically
- Reduces complexity while preserving functionality

### Rails Development

**Code Review:** Use `/rails-code-review` or `/code-review` (auto-detects Rails)

- Rails 8-aware with modern Hotwire/Turbo patterns
- Security-first approach with pragmatic severity assessment
- Understands `where.missing`, `broadcast_refresh_to`, Solid Stack patterns

**Testing:** Use the `style-testing` skill (language-agnostic), plus `style-rspec` if the project uses RSpec

- `style-testing` owns the principles: one behavior per test, hoisted declarative setup,
  deterministic clocks and identification, scenario-named groups, what not to test
- `style-rspec` adds only the RSpec/Rails spelling: request specs over controller specs,
  `let`/`let!`/`subject` mechanics, FactoryBot build strategies

**Conventions:** Use the `style-rails` skill

- Enforces Rails 8 conventions and best practices
- Ensures idiomatic Rails patterns

### Swift/iOS Development

**Code Review:** Use `/swift-code-review` or the `style-swift` skill

- Sandi Metz principles adapted for Swift
- Protocol-oriented design over class inheritance
- TRUE code (Transparent, Reasonable, Usable, Exemplary)

### Frontend Development

**Code Review:** Use `/frontend-code-review` (frontend-scoped shortcut for `/code-review`)

- Loads the `style-frontend` skill from the `code-reviewer` agent
- JavaScript/TypeScript, React, and Vue code reviews (read-only)
- Sandi Metz principles adapted for frontend
- Focuses on separation of concerns (logic vs presentation)
- Checks component design, TypeScript usage, and modern patterns
- Validates proper hook/composable patterns

**Style Guide:** Use the `style-frontend` skill

- TRUE components (Transparent, Reasonable, Usable, Exemplary)
- Wait for duplication before abstracting
- Small, focused components (~100-150 lines)
- Extract business logic to custom hooks (React) or composables (Vue)
- Composition over props explosion

### Go Development

**Style Guide:** Use the `style-go` skill

- Accept interfaces, return structs: interfaces declared at the consumer, narrow (one or two methods)
- Wrap errors with the failing operation (`fmt.Errorf("read %s: %w", ...)`); sentinels and error types only where a caller branches
- Make the zero value useful, so `var x T` works without a constructor
- `context.Context` first parameter of anything that blocks, never stored in a struct
- Every goroutine has a defined exit; the owner decides when it stops
- Exported identifiers carry a doc comment starting with their own name, since that is what `go doc` renders
- Table-driven tests on the standard library alone, comparing errors with `errors.Is`; load `style-testing` alongside
- Tooling in order: `gofmt -l -w .`, `go vet ./...`, `staticcheck ./...`, then `go test -race ./...`

### Markdown and Documentation

**Style Guide:** Use the `style-markdown` skill

- Write every sentence so a ten-year-old can follow it, and keep technical names exact
- Simplified Technical English: one word for one thing, 30 words per sentence, 20 for an instruction
- Name the mechanism, never a metaphor: write "add the hook to `settings.json`", not "wire it up"
- No jargon, no `i.e.`, no `e.g.`, no em-dash and no en-dash
- State the rule before the reason, and name the case you are excluding
- A number is a claim: write the command that derives it, or leave it out
- Mark a machine-read region with paired HTML comments, never with a heading
- Wrap prose at 100 columns, and never reflow a file you only came to patch
- Load `/response-style` when authoring Markdown inside a subagent, which never receives it

### Infrastructure as Code

**Terraform Review:** Use `/terraform-review` or the `terraform-iac-expert` skill

- Reviews Terraform configurations
- Checks for security and best practices
- Validates resource configurations

### Agentic Systems

**Design & Review:** Use the `agentic-clean-code` skill

- Clean Code (Uncle Bob) and POODR (Sandi Metz) principles transposed to the agentic context
- Covers tool design (SRP, explicit contracts, idempotency, no surprise side effects)
- Covers prompt architecture (small prompts, no implicit state, context objects)
- Covers orchestration (separation of planning from execution, explicit agent boundaries, fail-loud error policies)
- Includes a smell checklist for reviewing agents, tools, and prompts before ship
- Invoke with `/agentic-clean-code [target]`, or let it auto-detect the agent/skill/tool files changed on the branch

### Product Management

**Competitive Analysis:** Use `/competitive-analysis` or the `competitive-analysis` skill

- Deep competitor teardown with positioning maps
- Feature gap analysis (table-stakes, differentiation, over-investment)
- Strategic recommendations with priority actions

**A/B Test Design:** Use `/ab-test-design` or the `ab-test-design` skill

- Complete experiment spec with hypothesis, metrics, sample size
- Guardrails, stopping rules, and pre-registered analysis plan
- Decision framework for every possible outcome

**Product Research:** Use `/product-research` or the `product-research` skill

- Synthesizes user signals into Jobs-to-Be-Done
- Opportunity scoring (Importance + Importance - Satisfaction)
- Ranked feature concepts with validation approaches

**Product Roadmap:** Use `/product-roadmap` or the `product-roadmap` skill

- Theme-based prioritization with ICE scoring
- Now/Next/Later time horizons with dependencies
- Explicit "not doing" list to prevent scope creep

**Product Brief:** Use `/product-brief` or the `product-brief` skill

- PM-to-engineering handoff document
- Problem statement, success metrics, scope (MVP + full vision)
- Acceptance criteria and experiment tie-in

**Product Analysis:** Use `/product-analysis` or the `product-analyst` agent

- Objective product analysis (features, pricing, competitors, pain points)
- Market capture and positioning assessment

### Ideation & Planning

**Alignment Before Planning:** Use `/grill-me [topic]` or the `grilling` skill

- Interviews you until every branch of the design tree is resolved, so a plan is drafted against
  decisions you made rather than assumptions the agent invented
- Computes the **frontier** (the questions whose prerequisites are settled) and asks that whole set
  in one numbered round, with a recommended answer per question, then waits
- Defers any question that depends on another question still open in the same round, so no decision
  is put to you twice
- Finds every fact itself, dispatching subagents for the slow ones, and asks you only for decisions
- Stops when the frontier is empty and waits for you to confirm alignment before writing anything
- Feeds `/write-plan`, `/bead-create`, `/plan-to-beads`, or `/build`; it produces alignment, never
  an artifact

**Write the Plan a Conversation Decided:** Use `/write-plan` or the `write-plan` skill

- The step after `/grill-me` or `/grill-with-docs`, and the one that runs in the same context window
- Synthesizes what this conversation settled and never re-interviews you; a decision it cannot find
  goes to Open Questions rather than back to you as a question
- Verifies every file path, module, and API before naming it, because `/plan-review` checks each one
- Picks the **test seams**, the boundaries a test drives the feature through: existing over new,
  the highest one that still proves the behavior, and as few as possible. This is the only thing it
  asks you to confirm
- Reads `docs/adr/` and records the binding ADRs in the plan, so no plan quietly contradicts one
- Loads `style-markdown` before the first line, because a plan is a prompt asset that
  `/plan-to-beads` turns into bead text
- **Owns the canonical plan template.** `/plan-review` scores Completeness against it, so both plan
  writers read it from `skills/write-plan/SKILL.md` rather than from memory
- Writes `docs/plans/feature-plan-<name>.md`, then points at `/plan-review`

**Plan From One Sentence:** Use `/plan-from-idea` or the `feature-planner` agent

- The cold start: nothing decided, no interview behind you, one sentence to work from
- Runs in its own context window, so it explores the codebase from scratch and writes the same
  template through the same ADR and seam steps
- **It cannot see the conversation that invoked it.** When the design was already worked out in this
  window, use `/write-plan`; sending it here throws that thinking away and invites a second,
  different answer

**Review a Plan:** Use `/plan-review [path]` or the `plan-review` skill

- Runs the acceptance-criteria gate first: a plan with no testable criteria is Major Rework, and the
  review drafts the missing criteria for you rather than telling you to add some
- Grounds the plan in the repository, checking that every path, module, and API it names exists and
  behaves as described
- Scores 7 dimensions (completeness, feasibility, scope, risks, dependencies, MECE, actionability)
  and runs a dedicated MECE check for overlaps and gaps
- Report-only: it never edits the plan file, and it offers a paste-ready draft for anything missing
- Renders Ready, Needs Revision, or Major Rework, and points a Ready plan at `/plan-to-beads`

**Shared Language:** Use `mattpocock-skills:domain-modeling`

- **This plugin no longer ships a `domain-modeling` skill.** It shipped a fork until 2026-08-28,
  which existed only to send ADRs to the old docs/decisions directory. Moving this repository's ADRs to
  `docs/adr/` removed that reason, so the fork went and the upstream skill is used as it ships
- Builds and sharpens the project's glossary in `CONTEXT.md`: one word per concept, with the
  rejected synonyms listed so the choice is visible
- Challenges a term that conflicts with the glossary, sharpens an overloaded word, stress-tests
  relationships with edge-case scenarios, checks a claim against the code, and writes a resolved
  term down as it crystallizes rather than batching
- Offers an ADR only when all three hold: hard to reverse, surprising without context, and the
  result of a real trade-off. It writes that ADR itself, to `docs/adr/`, in its own lighter format
- Pairs with `grilling` when an interview is also teaching you the project's vocabulary
- **It is another plugin's skill.** Nothing here works without `mattpocock-skills` installed, and
  an update to that plugin can change this behavior without a change in this repository

**Idea Generation:** Use `/idea-wizard` or the `idea-wizard` skill

- Generates 30 improvement ideas for the current project
- Critically evaluates each, rejects weak candidates
- Distills to top 5 with confidence scores and actionable plans

**Decision Records:** Use `/adr` or the `architecture-decision-record` skill

- Records architectural decisions with context and rationale
- Tracks options considered and trade-offs
- Saves to `docs/adr/NNNN-<topic>.md`

### Multi-Language Reviews

**Auto-Detecting Review:** Use `/code-review` or the `code-reviewer` agent

- Detects languages from changed files automatically
- Dispatches to the correct skill per language
- Produces a single consolidated review report

### Quality Assurance

**Run the QA gates:** Use `/quality-gates` (reads the `quality-gates` skill from disk)

- **Scoped to the change by default.** `--changed` runs the tests covering the changed code and
  narrows lint, doc freshness, and hygiene to changed files; the report states that the full suite
  did not run. Type checking still analyzes the whole project and reports only changed files,
  because a type error surfaces in the consumer
- Discovers the gate set from `AGENTS.md`, then CI config, then a task runner, and falls back to
  language auto-detect only when none of those names a check; the report says which source it used
- **Picks the QA method from the diff, not from what is cheap to run.** A bundled router classifies
  every changed file into a surface and routes each one: `http-api` to a live curl probe, `browser-ui`
  to `/qa`, `mobile-ui` to `/ios-qa`, and `cli`/`library`/`prompt-assets`/`infra` to a coverage review
  alone. A full-stack diff gets several methods at once, and each handoff surface takes its own row in
  the report so a FAIL and a HANDOFF never collapse into one status
- **Drives the endpoints for real when the change is REST.** It sends actual curl requests, one probe
  per case rather than per route, and grades status, headers, and body. It probes
  `http://127.0.0.1:3000` unless the caller names another URL, and never infers a host from a config
  file or a URL found in the repository, because it sends POST, PUT, PATCH, and DELETE. A supplied
  remote host is used as given and marked `(NOT this machine)` in the summary the report copies. It
  starts a server only when the project declares a start command, always stops it, and SKIPs rather
  than guessing one. A refused connection is BLOCKED, never a failing endpoint
- **Change coverage is the gate that earns the run.** It enumerates the cases the diff introduces,
  requires a unit test for each, and requires an end-to-end test through the real entry point for
  every CLI command or HTTP route touched; an in-process call of a handler does not count. A passing
  live probe does not satisfy it: the probe measures this build and leaves no test behind, so a REST
  change with a green probe and no committed request-level test is still a finding
- Grades the **span** of each case (input, boundary, state, and outcome classes) and names the
  classes nothing covers, weighing each by what a failure there would cost
- Stays proportionate on purpose: one test per span class, never the cross-product, never a test
  for an unreachable branch, and never defensive code around a failure that cannot happen
- Hands a browser or mobile UI change to `/qa` (or `/qa-only` for a report) as HANDOFF, which makes
  the overall verdict INCOMPLETE rather than PASS
- Needs no issue tracker: its whole input is the diff, so no bead and no written acceptance criteria
  are involved. `/verify-acceptance` is the skill that grades against criteria, and it cites this
  report rather than re-deriving it
- Records a configured gate it could not run as BLOCKED, which fails the run; a missing binary is
  not a skip, and an all-skip run reports NO GATES RAN rather than PASS
- Reports the exact command and real counts for every gate, and says whether each failure looks new
  by naming which changed files it involves
- Report-only: it never fixes, formats, or rewrites the working tree

**Grade work against its criteria:** Use `/verify-acceptance` or the `verify-acceptance` skill

- Resolves the bead from `bd`, the branch name, or the commit messages
- Grades each acceptance criterion against a named test, a command's output, or a `file:line`,
  never against the diff
- Runs the four gates from `quality-gates` that can invalidate an acceptance claim
- Report-only: it never edits code and never closes a bead

**Land the accepted branch:** Use `/tadw:ship` (the `ship` skill directly; there is no command file)

- The local counterpart of `/pr-maintain`: no pull request and no GitHub CI, so the repository's own
  check suite, run locally on the rebased tip, is the entire gate
- Refuses to start on the default branch, on a dirty tree, or with a rebase or merge already running
- Resolves the bead from the argument or the `outrigger/<short-id>/<slug>` branch name, verifying
  every candidate against `bd` and refusing when two real beads resolve, when a bead id given as an
  argument does not exist, or when the bead is already closed
- Ships **bead-free** when the branch names no bead, or when the repository has no tracker: it skips
  the close, `bd dolt push`, the bead id in the subject, and the `Closes` line, and says so twice in
  the report. Every gate, guard, and cleanup step still runs
- Rebases onto `origin/main` before gating, so the gate grades the tree the squash-merge produces
- Resolves a `.beads/issues.jsonl` conflict by re-exporting from the database with `bd export`,
  verifies the result parses, and aborts on any other conflict rather than judging code someone else
  wrote
- Detects the gate from `TADW_SHIP_CHECK`, then what `AGENTS.md`/`CLAUDE.md` declares, then a task
  runner `check` target, then the stack's conventional runner; an undetected gate is a stop, not a
  skip, and a non-zero exit stops the run before any merge
- Squash-merges as `<type>: <title> (<bead-id>)` with a `Closes <bead-id>` body, closes the bead, and
  folds the tracker export into the landing commit
- Lists every commit already sitting unpushed on the default branch before it merges, and names each
  one in the report, because the push publishes those commits too
- Pushes main without ever forcing; a rejected push refetches, re-rebases, and re-gates once, and it
  resets local main only after proving it carries nothing this run did not create
- Deletes the local branch and its remote ref only after checking that main holds the branch's
  version of every file the branch touched
- Unattended by design: it never asks a question, and it ends with exactly one machine-readable
  `SHIP_DONE <hash>` or `SHIP_BLOCKED <slug>` line. The hash is what an orchestrator checks against
  main; the slug is one of five categories (`gate`, `conflict`, `tracker`, `git-state`, `internal`)
  and the prose beside it carries the exact condition

**Publish a release:** Use `/publish-plugin` (the `publish-plugin` skill directly; there is no
command file)

- The step after `ship`. The marketplace pins this plugin at `"version": "latest"` against the
  repository URL, so a push to main is already published; the tag and the manifest version are how a
  human tells which published state they are running
- Derives the bump from `git log` and `git diff` since the last tag, and names the rule that decided
  it: a renamed or removed component, a changed `name` field, or a broken machine-readable contract
  is MAJOR; a new component, flag, environment variable, or newly-failable check is MINOR; a fix,
  doc, or test-only change is PATCH
- Reads the last tag with `--sort=-v:refname`, because lexical order puts `v2.10.1` above `v2.5.2`
  and a released tag then reads as missing
- Writes the `Unreleased` section into a dated version section, adds any entry the log holds and the
  section missed, and appends the compare link with the owner and repository read from `origin`
- Bumps `.claude-plugin/plugin.json` through a JSON round-trip and proves the diff is one line
- Delegates a branch land to the `ship` skill and passes its `SHIP_BLOCKED` reason through unchanged,
  rather than carrying a second copy of the rebase, gate, and worktree rules
- Runs the repository's declared gate on the tree that will be tagged, after the bump, and stops
  before the commit on any non-zero exit
- Commits `chore(release): X.Y.Z` touching exactly `CHANGELOG.md` and `.claude-plugin/plugin.json`,
  never folding the bump into a feature squash, since releases here batch several landings
- Lists every commit already sitting unpushed on the default branch before it commits, and names
  each one in the report, because the push publishes those too
- Pushes main before the tag, so the remote never holds a tag naming a commit it does not have, and
  pushes any older tag that was created locally and never left the machine
- Treats the `reference-transaction` hook's `claude plugin validate` refusal as a stop, and never
  moves or deletes a tag that exists on the remote
- Ends with exactly one `PUBLISH_DONE <version> <hash>` or `PUBLISH_BLOCKED <reason>` line

### Bead Authoring

**Decompose a plan into beads:** Use `/plan-to-beads` or the `project-manager` agent + `plan-to-beads` skill

- Reads a written plan (the path given as an argument, or the most recent file in `docs/plans/`) and
  splits it into self-contained work units of one to three days each
- Checks first whether beads already exist for the plan, and presents a diff of new, changed, and
  removed beads for confirmation instead of silently re-creating them
- Requires Marr Level 1 (Why) and Level 2 (How) plus a Done when a second person can verify, on
  every bead, before it is created; Level 3 implementation detail stays optional
- Traces each plan-level acceptance criterion to the bead that proves it, and names both failure
  modes: a criterion no bead proves (a decomposition gap) and a bead proving no criterion (scope the
  plan never asked for)
- Sizes every bead against the diff-size window (Target is 1 to 5 files and 20 to 300 LOC, Stretch up
  to 10 files and 600 LOC), splits anything above it, and demotes Trivial size-band units to direct commits
- Presents the full list, including each bead's Why, How, Done when, type-specific sections, and size
  estimate, and waits for confirmation before the first `bd create`
- Writes each section to its canonical destination per ADR 0001
  (`docs/adr/0001-native-tracker-fields-are-canonical.md`): `--design`, `--notes`, and
  `--acceptance`, with the description body carrying only what has no native field
- Classifies a partial failure into fully written, created-but-unpopulated, and never attempted, and
  asks which recovery path to take rather than retrying blindly; it never re-runs `bd create` for a
  bead that already exists
- Wires dependencies with `bd dep add`, keeps the graph acyclic and shallow (longest chain at most 3),
  and prefers parallel tracks over deep chains

**File one bead:** Use `/bead-create` (the `bead-create` skill directly; there is no command file)

- The single-bead counterpart to `plan-to-beads`: it files one bead from a request, a bug report, a
  review finding, or a session-close follow-up, when no plan document exists to decompose
- Reads the rubric from `skills/bead-audit/SKILL.md` rather than restating it, so the bead is drafted
  against the same standard that will later grade it
- Infers what the code, the commits, and the failing test can answer, and batches what only a person
  can answer into one exchange; it never invents a stakeholder, an approach, or an acceptance criterion
- Searches the tracker for a duplicate before drafting, and hands a near-match back to the author to
  resolve instead of deciding alone
- Grounds every current-state claim against `origin/main` (never the working tree, which on a feature
  branch already contains the change), cites `path:line`, and records the sha; a claim that is already
  satisfied means the work is done and no bead is filed
- Estimates the size band, splits anything above Stretch, and refuses the trivial bead by offering to
  make the change instead
- Self-audits the draft against the `bead-audit` dimensions and rewrites until it passes, then presents
  the bead and waits for confirmation; a draft still carrying an `[AUTHOR TO COMPLETE]` placeholder is
  never filed
- Creates it in one `bd create` call with `--design`, `--notes`, and `--acceptance` populated, labels it
  with a category, wires parent and dependency edges, reads it back with `bd show` to
  prove the native fields landed, and exports the tracker silently

**Grade and repair beads that already exist:** Use `/bead-audit` (the `bead-audit` skill directly; there is no command file), or `/bead-audit-all` to sweep the whole backlog

- Audits the text of a bead body, so it works on `bd show` output, a file, or a pasted blob; the other
  two skills in this section write beads, this one grades them
- Separates three independent verdicts: content (is the substance there?), structure (is it under the
  byte-exact canonical heading, or in the native field?), and grounding (is it still true of the code
  on main?), so a substantively complete bead in the wrong format is an auto-fixable REFORMAT rather
  than a failure
- Treats `bd`'s native `design`, `notes`, and `acceptance_criteria` fields as canonical structure per
  ADR 0001, and drafts a fix into the field rather than embedding a heading in the description
- Runs the same Marr, size, and type-specific section audits as `plan-to-beads`, then adds a grounding
  audit that reads `origin/main` with `git show` and `git grep` and records the sha every claim was
  checked against
- Never marks a bead drifted because its acceptance criteria do not hold yet, since unmet criteria are
  the bead's reason to exist; it runs those sections the other way instead and reports `satisfied` when
  main already meets them, which is the cheapest finding in a backlog to resolve
- Produces an optional 0 to 100 scorecard, banded Poor to Excellent, derived from the verdicts and
  capped so a quality band can never outrank the pass/fail verdict or the grounding verdict
- Drafts corrected bodies, self-verifies each by re-auditing its own draft, and gates write-back behind
  an `applyable` flag: a placeholder-bearing draft, a drifted bead, or a satisfied bead goes to a person
  instead of the tracker
- `--json` mode emits per-bead verdicts, scores, corrected fields, and the `applyable` flag, so a
  grooming loop can apply the safe fixes and route the rest
- `/bead-audit-all` enumerates the backlog in one unlimited page (`bd list --status open --limit 0 --json`),
  resolves the grounding baseline once for every bead, and reports a health table ranked worst quality band
  first; it is report-only and does not write back

### Backlog Triage

**Decide what to work on next:** Use `/triage-beads` or the `triage-beads` skill directly

- Reads the tracker through the `bd` and `bv` command-line tools only; there is no MCP server
- Takes readiness from `bd ready` and `bd blocked`, never from `bv`, whose `blocked_count` reads 0
  on a backlog full of dependency-blocked work
- Takes every measured graph fact from one `bv --robot-triage` call (unblock counts, PageRank,
  betweenness, low-complexity flags) and degrades to `bd` alone, saying so, when `bv` is absent
- Ranks every candidate on one fixed rubric, `ROI = value ÷ effort`: value sums priority, user
  impact, unblock leverage, momentum, and a due-within-7-days bonus, and the size tier divides
  (S by 1, M by 1.5, L by 2.5, compressed on purpose so the least-evidenced input cannot outvote
  the four value components combined)
- Awards a point only when it can cite its evidence: a stored field, a count, a bead id, or a
  phrase from the body
- Prefers stored effort evidence (`estimated_minutes`, then a `plan-to-beads` size band, then `bv`'s
  own low-complexity flag) over a read of the prose, and says which source it used
- Checks three hard overrides before any arithmetic: an overdue ready bead is the pick, a ready P0
  outranks every non-P0, and a bead deferred into the future stays out
- Quotes PageRank as supporting evidence but never scores it, because unblock leverage already
  prices graph position and a high-PageRank chore can be invisible to a user
- Weights a dependency edge whose other end just closed above a shared label for "same thread"
- Excludes blocked, deferred, draft, epic, and other-assignee beads from the scored set, listing
  the blocked ones with the blocker that holds them
- Says in one line when its own top pick differs from `bv`'s, naming the component that moved it
- Caps the output at roughly one screen: one top pick with its arithmetic and its
  `bd update <id> --claim` command, a leaderboard of 5 naming what each runner-up lost on, and an
  ROI-ordered tail of 10 closed with `… and N more`
- Deterministic: the same tracker state always yields the same pick, with exact ties broken by
  priority, then unblock count, then effort, then age
- Report-only: it never claims, closes, defers, or re-prioritizes a bead

### Project Reporting

**Roadmap Dashboard:** Use `/roadmap-dashboard` or the `roadmap-dashboard` skill directly

- Synthesizes the codebase and the `beads` tracker into a single self-contained interactive HTML dashboard at `docs/roadmap.html`
- Collects tracker data with a bundled `collect_beads.py` script (refreshes JSONL, normalizes priorities, filters dependency edges to the blocking types, and annotates ready/blocked/blocked_by; always exits 0, emitting an empty shape when no tracker exists)
- Cross-references code against beads to classify each subsystem as Built / Partial / Stubbed / Planned and compute a blended, defensible completion percentage
- Renders zero-dependency pure HTML/CSS/vanilla-JS diagrams (architecture current-vs-target, data flow, DB relationships, dependency graph, milestone timeline + risk matrix), a Kanban board, collapsible deep-dives, a sticky TOC, and print CSS
- Versions the output (`docs/roadmap-vX.Y.html`) instead of overwriting a prior report; marks inferences with `[Inference]` tags and confidence scores

### PR Maintenance

**Keep a PR Green:** Use `/pr-maintain` or the `pr-maintenance` skill directly

- Detects the PR's actual base branch from GitHub (not hardcoded `origin/main`), so stacked PRs work
- Rebases with `git push --force-with-lease` (never plain `--force`)
- AI-assisted conflict resolution with hard-stops on migrations, lockfiles, and secrets
- Fixes failing required CI checks with edits scoped to files already in the PR diff
- Never modifies test assertions in files that were not already in the PR diff (prevents masking real failures)
- Idempotent per iteration, safe to run on a loop

**Running on a loop:**

```text
/loop 6h /pr-maintain
```

Each iteration reports rebase status, CI status, files touched, and any manual actions the user needs to take.
