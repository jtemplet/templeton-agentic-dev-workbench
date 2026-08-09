# Task Routing

The long form of the routing table in `AGENTS.md`: which command, skill, or agent to
reach for per task, and what each one does. The workflow pipelines live in `README.md`.

## Language-Specific Workflows

### Python Development

**Code Review:** Use `/python-code-review` or the `review-python` skill

- Checks PEP 8 and Google Python Style Guide compliance
- Reviews security, performance, and maintainability

**Feature Development:** Use `/python-feature-dev` or the `software-engineer` agent + `feature-development` skill

- 4-phase workflow: discovery, implementation, simplification, linting
- Loads `style-python` for Python file style decisions
- Runs `ruff` for linting

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
