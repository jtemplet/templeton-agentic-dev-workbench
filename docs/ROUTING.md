# Task Routing

The long form of the routing table in `AGENTS.md`: which command, skill, or agent to
reach for per task, and what each one does. The workflow pipelines live in `README.md`.

## Language-Specific Workflows

### Python Development

**Code Review:** Use `/python-code-review` or the `review-python` skill

- Checks PEP 8 and Google Python Style Guide compliance
- Reviews security, performance, and maintainability

**Feature Development:** Use `/build <bead-id>` or the `software-engineer` agent + `feature-development` skill

- 5-phase workflow: ground the spec, orient in the repo, implement, simplify, lint
- Reads the spec from `br show <id> --json` rather than interviewing about what the bead records
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

**Idea Generation:** Use `/idea-wizard` or the `idea-wizard` skill

- Generates 30 improvement ideas for the current project
- Critically evaluates each, rejects weak candidates
- Distills to top 5 with confidence scores and actionable plans

**Decision Records:** Use `/adr` or the `architecture-decision-record` skill

- Records architectural decisions with context and rationale
- Tracks options considered and trade-offs
- Saves to `docs/decisions/NNNN-<topic>.md`

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
  because a type error surfaces in the consumer. The secret scan always covers the whole tree
- Discovers the gate set from `AGENTS.md`, then CI config, then a task runner, and falls back to
  language auto-detect only when none of those names a check; the report says which source it used
- **Change coverage is the gate that earns the run.** It enumerates the cases the diff introduces,
  requires a unit test for each, and requires an end-to-end test through the real entry point for
  every CLI command or HTTP route touched; an in-process call of a handler does not count
- Grades the **span** of each case (input, boundary, state, and outcome classes) and names the
  classes nothing covers, weighing each by what a failure there would cost
- Stays proportionate on purpose: one test per span class, never the cross-product, never a test
  for an unreachable branch, and never defensive code around a failure that cannot happen
- Hands a browser or mobile UI change to `/qa` (or `/qa-only` for a report) as HANDOFF, which makes
  the overall verdict INCOMPLETE rather than PASS
- Records a configured gate it could not run as BLOCKED, which fails the run; a missing binary is
  not a skip, and an all-skip run reports NO GATES RAN rather than PASS
- Reports the exact command and real counts for every gate, and says whether each failure looks new
  by naming which changed files it involves
- Scans for secrets on prefixed key formats only, and reports `file:line` without the matched value
- Report-only: it never fixes, formats, or rewrites the working tree

**Grade work against its criteria:** Use `/verify-acceptance` or the `verify-acceptance` skill

- Resolves the bead from `br`, the branch name, or the commit messages
- Grades each acceptance criterion against a named test, a command's output, or a `file:line`,
  never against the diff
- Runs the four gates from `quality-gates` that can invalidate an acceptance claim
- Report-only: it never edits code and never closes a bead

### Backlog Triage

**Decide what to work on next:** Use `/triage-beads` or the `triage-beads` skill directly

- Reads the tracker through the `br` and `bv` command-line tools only; there is no MCP server
- Takes readiness from `br ready` and `br blocked`, never from `bv`, whose `blocked_count` reads 0
  on a backlog full of dependency-blocked work
- Takes every measured graph fact from one `bv --robot-triage` call (PageRank, betweenness, unblock
  counts, low-complexity flags) and degrades to `br` alone, saying so, when `bv` is absent
- Reads each bead body for the three axes `bv` does not score (effort, user impact, momentum) and
  reports them separately instead of averaging them into one number that hides the choice
- Prefers stored effort evidence (`estimated_minutes`, then a `plan-to-beads` size band, then `bv`'s
  own low-effort flag) over a read of the prose, and says which source it used
- Weights a dependency edge whose other end just closed above a shared label for "same thread"
- Excludes blocked, deferred, draft, and other-assignee beads from the actionable buckets, listing
  the blocked ones with the blocker that holds them
- Caps the output at roughly one screen: one Start-here pick with its `br update <id> --claim`
  command, three buckets of three, and a priority tail closed with `… and N more`
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
