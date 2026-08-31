# tadw (Templeton Agentic Dev Workbench)

Personal Claude Code plugin: an agentic development workbench with custom agents, skills, and commands for Python, Ruby/Rails, JavaScript/TypeScript/React/Vue, Swift/iOS, and Terraform development.

## Installation

```bash
# Register marketplace
/plugin marketplace add jtemplet/templeton-agentic-marketplace

# Install this plugin
/plugin install tadw@templeton-agentic-marketplace
```

Everything in the plugin is namespaced under `tadw:`, so a skill or agent is addressed as
`tadw:fresh-eyes-cr`, `tadw:code-reviewer`, and so on. The namespace comes from the `name` field in
`.claude-plugin/plugin.json`.

The marketplace pins this plugin at `"version": "latest"` against its git URL, so an install follows
the default branch rather than a tag. The `vX.Y.Z` tags and the manifest version tell you which
published state you have; `/publish-plugin` is what creates them.

> **Upgrading from 1.x?** The namespace was `templeton-agentic-dev-workbench:` before 2.0.0.
> Uninstall the old plugin and install this one under its new name; see the 2.0.0 entry in
> [CHANGELOG.md](CHANGELOG.md).

## Workflow Pipelines

### Pipeline A: Business Planning

`/business-ideas` → `/grill-me` → `/write-plan` → `/plan-review` → `/plan-to-beads` → `/bead-audit-all`

| Command | What it does |
|---|---|
| `/business-ideas` | Analyze business model, surface 10 revenue-focused feature ideas |
| `/grill-me [topic]` | Interview you until the design tree is resolved, so the plan is drafted against your decisions rather than the agent's assumptions |
| `/write-plan` | Write what this conversation decided to `docs/plans/`, in the canonical 11-section shape; no interview, and it confirms the test seams before writing |
| `/plan-review <path>` | Gate on acceptance criteria, ground claims in the codebase, evaluate 7 dimensions (incl. MECE audit), render verdict; drafts missing criteria/test plan |
| `/plan-to-beads <path>` | Decompose plan into `bd` issues; each bead audited for Why, How, and Done when |
| `/bead-audit-all` | Score the new beads before anyone builds them, worst first |

`/write-plan` is the step after grilling, not `/plan-from-idea`. The agent behind
`/plan-from-idea` runs in its own context window and cannot see the interview, so it re-explores
the codebase and can re-ask questions you already answered. Reach for it only on a cold start.

`/grill-me` is optional only when the idea is already sharp. `/bead-audit-all` is not: `/build`
refuses a bead whose criteria are vague or whose `design` field is empty, and catching that here
costs seconds because the plan is still in the window.

**Run this whole pipeline in one context window.** Every step builds on the previous one's
thinking, so clearing or compacting before the audit throws away the reasoning the beads rest on.

### Pipeline B: Code Quality

`/build <bead-id>` → `/fresh-eyes-cr` → `/quality-gates` → `/verify-acceptance` → `/tadw:ship` → `/publish-plugin`

| Command | What it does |
|---|---|
| `/build <bead-id>` | Implement the bead: read its spec from `bd`, learn the repo's conventions and its ADRs, code criterion by criterion with a test each, simplify, lint, then label the bead `implemented` |
| `/fresh-eyes-cr` | Review changed code with fresh eyes, find and fix bugs directly |
| `/quality-gates` | QA the change, not the repository: runs the project's own checks, reads the diff to pick the QA method it earns (real curl requests against a local server for REST, a handoff to `/qa` for browser UI, a coverage review for the rest), and proves every case is exercised at the unit and end-to-end level across its input/state/outcome classes |
| `/verify-acceptance` | Grade the work against its bead's acceptance criteria and the QA gates; one verdict, and the `accepted` label when the verdict is ACCEPTED |
| `/tadw:ship` | Land the accepted branch on main locally: rebase, run the repo's own checks as the gate, squash-merge, close the bead, push, delete the branch; ends with `SHIP_DONE`/`SHIP_BLOCKED` |
| `/publish-plugin` | Turn what landed into a release: derive the semver bump from the diff, write the changelog section, bump the manifest, commit `chore(release): X.Y.Z`, tag `vX.Y.Z`, push main and the tag; ends with `PUBLISH_DONE`/`PUBLISH_BLOCKED` |

**Clear the context between every bead.** `/build` reads its spec from `bd`, never from the
transcript, so a bead carries no dependency on the one before it. Running five builds back to back
in one window leaves the last one reasoning at the bottom of a full context.

**Give `/verify-acceptance` the `/quality-gates` output.** It cites those results rather than
re-deriving them, so passing them forward is the difference between running the suite once and
running it twice for one verdict.

**`/code-review` is the conventions pass, and it is not in this pipeline.** `/fresh-eyes-cr` hunts
real bugs and deliberately ignores style; `/build`'s own Simplify and Lint phases cover conventions
on the code it just wrote. Add `/code-review` when the diff is large or touches unfamiliar code.

### Bug On-Ramp

A bug does not arrive as a plan, so it needs its own route onto Pipeline B.

`/diagnose <bug>` → `/bead-create` → Pipeline B

| Command | What it does |
|---|---|
| `/diagnose <bug>` | Investigate thoroughly before fixing, gather evidence, test hypotheses, present root cause |
| `/bead-create` | Turn the confirmed root cause into one well-formed bead, with steps to reproduce and acceptance criteria |

### PR Maintenance

Keep a long-lived PR rebased on its parent branch and green on CI. Detects the PR's actual base from GitHub (so stacked PRs work), rebases with `--force-with-lease`, and applies minimal CI fixes scoped to files already in the PR diff.

| Command | What it does |
|---|---|
| `/pr-maintain` | One maintenance iteration: detect base branch, rebase, resolve conflicts, push with lease, diagnose and fix failing required CI checks, report |

Pair with `/loop` to run on a schedule:

```text
/loop 6h /pr-maintain
```

### Pipeline C: Product Strategy

`/competitive-analysis` → `/product-research` → `/product-roadmap` → `/product-brief <feature>` → `/ab-test-design <hypothesis>`

| Command | What it does |
|---|---|
| `/competitive-analysis` | Deep competitor teardown with positioning map, moat analysis, trajectory mapping, and feature gap analysis |
| `/product-research` | Synthesize user signals by segment into ranked opportunities using JTBD, anti-jobs, and evidence-weighted scoring |
| `/product-roadmap` | Prioritized roadmap with themes, capacity modeling, bet classification, and Now/Next/Later sequencing |
| `/product-brief <feature>` | PM-to-engineering handoff: problem, success metrics, scope (MVP + full vision), acceptance criteria |
| `/ab-test-design <hypothesis>` | Complete experiment spec with metrics, sample size, rollout plan, guardrails, and decision criteria |

### Product Research

| Command | What it does |
|---|---|
| `/product-analysis <product>` | Objective product analysis: features, pricing, competitors, pain points, market capture |
| `/research-ingest` | Ingest a new source into the Research wiki: read, discuss, summarize, create entity/concept pages |

### Design & UX

| Command | What it does |
|---|---|
| `/ux-audit <app-url>` | Playwright-driven UX audit of a web app, evaluates 7 dimensions (accessibility, design system, IA, interaction, content, emotional design, cognitive load), report saved to `docs/ux-audits/` |
| `/ux-audit-ios <app-name>` | iOS Simulator UX audit via `xcrun simctl`, tests Dynamic Type / Dark Mode / accessibility settings, evaluates same 7 dimensions against Apple HIG, report saved to `docs/ux-audits/` |

### App Store Optimization

| Command | What it does |
|---|---|
| `/aso-audit [app-id]` | ASO health audit across 10 weighted factors (title, subtitle, keyword field, description, screenshots, preview video, ratings, icon, keyword rankings, conversion signals), produces an ASO Score Card and prioritized action plan, report saved to `docs/aso-audits/` |

## Commands

### Code Review

| Command | Description |
|---|---|
| `/code-review` | Auto-detect languages and apply correct review skill per file |
| `/python-code-review` | Python review (PEP 8, Google Style Guide) |
| `/rails-code-review` | Rails 8 review (security, conventions, Hotwire) |
| `/swift-code-review` | Swift/iOS review (Sandi Metz, protocol-oriented design) |
| `/frontend-code-review` | Frontend review (JS/TS/React/Vue, component design, patterns) |
| `/terraform-review` | Terraform/IaC review (security, best practices, modules) |
| `/review-claude-md` | Review and optimize CLAUDE.md/AGENTS.md files |

### Development

| Command | Description |
|---|---|
| `/grill-me [topic]` | Get interviewed until every branch of the design tree is resolved: one numbered round of questions per frontier, a recommended answer for each, facts found by the agent rather than asked of you |
| `/build <bead-id>` | Implement a bead's spec: read the bead, learn the repo's conventions, code criterion by criterion with a test each, simplify, lint. Accepts a free-text description when no bead exists |
| `/write-plan` | Write the design this conversation settled to `docs/plans/`; synthesis, not an interview |
| `/plan-from-idea <idea>` | Cold start: hand one sentence to a subagent that explores the codebase and drafts the plan. Use `/write-plan` instead when the design is already decided here |
| `/adr <topic>` | Record an architectural decision with context and rationale |
| `/agentic-clean-code [target]` | Design or review agentic code (tools, prompts, orchestration) against Clean Code + POODR |
| `/response-style` | Re-assert the house response style (answer-first, Simplified Technical English, decision matrices, owner-split "Next actions") after a compaction or inside a subagent |

### Maintenance

| Command | Description |
|---|---|
| `/bead-refine [topic]` | Loads the `bead-refine` skill: cluster the backlog into themes, pick one, then keep, shrink, merge, defer, kill, done, or promote each bead. Answers "does this bead deserve to exist?", not "can it be built?" |
| `/bead-audit-all [open\|all]` | Single-pass, report-only audit of the whole backlog: score and ground every bead once, ranked health table (worst first) |
| `/product-surface-docs [dir]` | Build/refresh a MECE/Pyramid product doc tree by surface under docs/products/; surfaces bugs/gaps/debt into a findings ledger |
| `/pr-maintain` | Keep the current branch's PR rebased on its parent and passing CI; safe to pair with `/loop` |
| `/roadmap-dashboard [jsonl]` | Build a self-contained interactive HTML project dashboard at `docs/roadmap.html` from the codebase and the `beads` tracker |
| `/validate-plugin` | Check plugin integrity and cross-references |

> **`/bead-create` is the skill, not a command.** Say "create a bead" and it loads on its own, or
> type `/bead-create` to load it directly. Use `/plan-to-beads` instead when a written plan needs
> decomposing into many beads.
>
> **`/bead-audit` is the skill, not a command.** The command file was removed because it
> shadowed the skill of the same name and returned a summary instead of the 661-line rubric.
> Typing `/bead-audit` now loads the skill itself. Use `/bead-audit-all` to sweep the whole
> backlog in one pass.

### Operations

| Command | Description |
|---|---|
| `/prod-ops` | Safely operate production apps on a Hetzner VPS over SSH (service ops + PostgreSQL data ops) under strong guardrails; loads the `production-ops` skill |

## Skills

Every skill below is invocable directly as `/<skill-name>`, so a skill needs no command file to
be reachable. Seven commands that did nothing but name their own skill were removed for that
reason: they shadowed the skill they pointed at. See "Commands and skills share one namespace".

| Skill | What it does | When to use |
|---|---|---|
| `review-python` | PEP 8 and Google Style Guide review technique | Reviewing a Python file, diff, or PR |
| `review-rails` | Rails 8 systematic review (security, conventions, performance) | Reviewing Rails code before a merge or deploy |
| `style-testing` | Universal test style, framework-independent (any language) | Writing tests in any language, or diagnosing a flaky one |
| `style-rspec` | RSpec/Rails delta on `style-testing` | Writing RSpec specs, or converting controller specs to request specs |
| `style-rails` | Rails 8 Way conventions and best practices | Generating Rails code, or deciding whether to add a gem |
| `style-python` | Python style (Sandi Metz principles adapted for Python) | Writing or refactoring Python in the house style |
| `style-swift` | Swift style (Sandi Metz, protocol-oriented design) | Writing or reviewing Swift and SwiftUI |
| `style-frontend` | Frontend style (JS/TS/React/Vue, Sandi Metz principles) | Writing React or Vue, or splitting logic out of a component |
| `style-go` | Go style: accept interfaces and return structs, wrapped errors over sentinels, useful zero values, goroutines with a defined exit, table-driven tests | Writing or reviewing Go, or deciding whether an interface earns its place |
| `style-markdown` | Markdown style for documents an agent reads and executes: link out instead of inlining, numbers derived not remembered, HTML comment sentinels for machine-read regions, a 100-column wrap | Composing, updating, or reviewing any knowledge-base document (`docs/`, wiki, runbook, README) or prompt asset (skill, agent, command, ADR, plan, `AGENTS.md`) |
| `terraform-iac-expert` | Terraform/IaC expertise across AWS, Azure, GCP | Writing Terraform, or debugging state and deployments |
| `style-fizzy` | Vanilla Rails conventions for the Fizzy codebase | Working anywhere in the Fizzy codebase |
| `idea-wizard` | Structured ideation: generate, evaluate, distill | Reviewing a codebase for improvements, or stuck and needing options |
| `architecture-decision-record` | ADR format with context, options, and rationale | You made a non-obvious choice future-you will question |
| `business-ideas` | Revenue-focused feature ideation with "who pays and why" thesis | A project needs to justify its investment or find revenue angles |
| `grilling` | Relentless interview that resolves a design tree branch by branch: computes the **frontier** (the questions whose prerequisites are settled), asks the whole frontier in one numbered round with a recommended answer each, finds every fact itself (dispatching subagents) and asks you only for decisions, then recomputes the frontier from your answers; stops when the frontier is empty and waits for you to confirm alignment | Before `/write-plan`, `/bead-create`, or `/build`, whenever you want the agent to interview you first |
| `plan-review` | Acceptance-criteria gate + codebase grounding + 7-dimension plan evaluation (completeness, feasibility, scope, risks, deps, MECE, actionability); report-only, drafts missing criteria/test plan | After writing a plan, as the gate before decomposing it |
| `aso-audit` | App Store Optimization audit across 10 weighted factors, ASO Score Card, prioritized action plan | Before an app launch, or when organic installs are low |
| `ux-audit` | Web UX audit via Playwright; 7-dimension evaluation with severity-ranked report | Auditing the UX of a running web app |
| `ux-audit-ios` | iOS UX audit via Simulator; Dynamic Type / Dark Mode / Bold Text testing against Apple HIG | Auditing the UX of an iOS app in the Simulator |
| `code-simplify` | Language-agnostic simplification workflow; loads the matching language style skill | After a feature lands, as the refinement pass before committing |
| `review-fresh-eyes` | Bug-and-correctness pass over recently changed code, fixes issues directly | After implementing or refactoring, before committing |
| `verify-acceptance` | Grade a finished unit of work against its bead's `acceptance_criteria` and the QA gates; every criterion graded against a named test, a command's output, or a `file:line`, never the diff; reports ACCEPTED / NOT ACCEPTED / INCONCLUSIVE and writes nothing but the `accepted` label, which only an ACCEPTED verdict earns | Deciding whether work is done, before `bd close` or a PR |
| `quality-gates` | QA the change rather than the repository: scoped to the diff by default, takes the gate list from `AGENTS.md`/CI/a task runner before guessing, and **routes the change to the QA method it earns** by classifying the changed files, so a REST surface gets real curl requests through a running server, browser UI gets a HANDOFF row naming `/qa`, and a CLI or library gets a coverage review; the change-coverage gate enumerates the cases the diff introduces, requires a unit test for each plus an end-to-end test through the real entry point, and grades the span (input, boundary, state, outcome classes) while refusing cross-products and defensive code; the live probe defaults to `http://127.0.0.1:3000` and never infers a host from the repository, uses a URL the caller supplies (marking a non-loopback host in its summary so a remote probe cannot go unmentioned), starts a server only when the project declares one and always stops it, and treats a refused connection as BLOCKED rather than a failing endpoint; needs no bead or acceptance criteria; report-only | Ending a session, before a PR, or before closing the work |
| `feature-development` | Implement a bead's spec in 5 phases (ground, orient, implement, simplify, lint): reads the spec from `bd` instead of re-interviewing, reads the repo's conventions before writing, one test per acceptance criterion; leaves the bead open | Building a bead that is ready to implement |
| `ship` | Land an accepted bead's feature branch on main locally, with no PR and no GitHub CI: rebases onto the base, resolves a `.beads/issues.jsonl` conflict by re-exporting from the database with `bd export` and no other conflict at all, runs the repository's own check suite on the rebased tip as the only gate, squash-merges as `<type>: <title> (<bead-id>)`, closes the bead and folds the export into the landing commit, pushes main without ever forcing, and deletes the branch after proving the content landed; unattended (it reports instead of asking) and ends with one `SHIP_DONE <hash>` / `SHIP_BLOCKED <slug>` line | Landing a bead that passed `/quality-gates` and `/verify-acceptance` |
| `publish-plugin` | Cut and publish a release: derives the semver bump from the diff since the last tag against a stated rubric (a renamed or removed component is MAJOR, a new component or a newly-failable check is MINOR, a fix or doc edit is PATCH), writes the Keep a Changelog section and its compare link from the log rather than trusting `Unreleased`, bumps `.claude-plugin/plugin.json` through a JSON round-trip and proves the diff is one line, delegates any branch land to `ship`, runs the repo's own gate on the tree about to be tagged, commits `chore(release): X.Y.Z` touching exactly two files, then tags and pushes main before the tag; treats the `reference-transaction` validation refusal as a stop and ends with one `PUBLISH_DONE` / `PUBLISH_BLOCKED` line | Turning what landed on main into a numbered, tagged release |
| `plan-to-beads` | Decompose a feature plan into `bd` issues; each bead audited for Why (L1), How (L2), and Done when (acceptance) | A reviewed plan needs breaking into trackable issues |
| `bead-create` | Author one bead and file it: interviews only for what cannot be inferred, searches for a duplicate first, grounds every current-state claim against `origin/main` with a sha, picks the type, drafts against the canonical structure, estimates the size band and splits or refuses, then self-audits with the `bead-audit` rubric until it passes; waits for confirmation, creates it in one `bd create` call with `--design`, `--notes`, and `--acceptance` populated, labels it, and reads it back to prove the native fields landed | Filing a single bead, bug, or follow-up with no plan behind it |
| `bead-audit` | Audit existing bead bodies against the Marr, size, and type-specific section standards, and ground their claims in the code on `main`; separates content from structure (format-only issues are auto-fixable) and both from grounding (a bead whose code moved is `drifted`, not under-specified); honors native tracker fields, optional 0-100 scorecard banded Poor→Excellent and capped by verdict and by grounding, JSON output for backlog grooming | Before claiming a bead, or grooming a backlog at scale |
| `bead-refine` | Refine the backlog by product value: clusters every non-closed bead into 4 to 8 themes plus an `Unclustered` bucket, ranks the themes by staleness, age, size, and grounding, then judges one theme in a single round and gives each bead one of seven verdicts (keep, shrink, merge, defer, kill, done, promote); grounds each bead only by checking that the paths and symbols it names still exist, writes every cell in plain English (15-word `Why`, evidence in a detail list), computes no score, files no bead, and applies the `bd` commands in one batch only after you confirm them | Pruning a backlog that has grown past what you can hold in your head |
| `triage-beads` | Rank the open `bd` backlog by ROI (value ÷ effort) into a one-screen readout: one top pick with its scoring arithmetic and claim command, a scored leaderboard naming what each runner-up lost on, a blocked list naming each blocker, and a capped ROI-ordered tail; takes readiness from `bd ready`/`bd blocked`, the measured graph facts (unblock counts, PageRank) from `bv --robot-triage`, and prices each bead on a fixed evidence-cited rubric so the same tracker state always yields the same pick; report-only, `bd`/`bv` CLI only, no MCP | Choosing the next bead to claim, or when `bd ready` output has stopped being scannable |
| `product-surface-docs` | Build/refresh a MECE/Pyramid product doc tree under `docs/products/` by surface; grounds claims in code, proactively hunts bugs/gaps/debt into `_findings.md` (cheap capture) and promotes actionable ones into bead-audit-compliant beads, ships a staleness checker (in-repo + multi-repo) | Standing up or refreshing `docs/products/`, or auditing for gaps |
| `research-ingest` | Ingest a new source into the Research wiki, with study quality assessment and cross-referencing | A new file appeared in `Research/sources/` |
| `competitive-analysis` | Competitor teardown with positioning map, moat analysis, trajectory, and feature gaps | Before a planning cycle, or when a competitor ships something notable |
| `ab-test-design` | A/B test design with hypothesis, metrics, sample size, rollout plan, and decision criteria | You have a hypothesis and want data to settle it, before building |
| `product-research` | User signal synthesis by segment using JTBD, anti-jobs, and evidence-weighted opportunity scoring | Scattered user feedback and no clear priorities |
| `product-roadmap` | Roadmap with themes, capacity modeling, bet classification, and Now/Next/Later sequencing | Start of a quarter, or stakeholders disagree on priorities |
| `product-brief` | PM-to-engineering handoff: problem, metrics, scope, acceptance criteria, experiment tie-in | A prioritized feature needs scoping for engineering |
| `agentic-clean-code` | Clean Code + POODR principles for agentic systems: tool design, prompt architecture, orchestration, naming, testability | Designing or reviewing tools, prompts, or agent orchestration |
| `pr-maintenance` | Keep a single PR rebased on its actual parent branch and green on CI with minimal, in-scope edits; designed to run on a loop | A long-lived or stacked PR needs to stay current and green |
| `roadmap-dashboard` | Synthesize the codebase and the `beads` tracker into one self-contained, zero-dependency interactive HTML dashboard at `docs/roadmap.html` (executive KPIs, pure HTML/CSS diagrams, Kanban board, prioritized roadmap); ships a `collect_beads.py` collector and versions the output | Showing project maturity and remaining work to a stakeholder |
| `production-ops` | Safely operate production Docker Compose apps on a single Hetzner VPS over SSH (two-hop `root` -> `su - deploy`); service ops and PostgreSQL data ops under strong guardrails: read-only by default, secret-free `hetzner-prod` alias, mandatory `pg_dump` before any data mutation, transactional one-off writes, verify-after, written rollback, and hard-stops on volume wipes / `prune` / `DROP` / `TRUNCATE` / `WHERE`-less writes | Checking, restarting, or changing data on the production VPS |
| `write-plan` | Turn a design this conversation already settled into `docs/plans/feature-plan-<name>.md`: synthesize rather than interview, verify every path it names, pick and confirm the test seams, honor the ADRs, and write the canonical 11-section template that `/plan-review` grades. Owns that template | Right after `/grill-me` or `/grill-with-docs`, or any time a settled design needs to become a document |
| `house-response-style` | The always-on response style, single-sourced for both the `SessionStart` hook and `/response-style`: lead with the answer, cut narration, write in Simplified Technical English (ASD-STE100 writing rules, not its licensed dictionary), put multi-factor choices in a decision matrix, and end open work with an owner-split "Next actions" section | Never chosen: injected into every session by the hook |

## Agents

| Agent | Description |
|---|---|
| `code-reviewer` | Auto-detects languages, dispatches to correct review skill (read-only) |
| `quality-gates-orchestrator` | Runs the quality gates across three concurrent subagent lanes (backend-unit, frontend, integration): resolves the gate set, scope, and QA routing once, keeps the gates no lane owns, then merges every returned row into the one report the `quality-gates` skill specifies. Report-only; it decides the verdict, no lane does |
| `software-engineer` | Editing role for code work; routes to code-simplify, review-fresh-eyes, or feature-development based on intent |
| `claude-md-reviewer` | CLAUDE.md optimization with quantitative scoring |
| `feature-planner` | Cold-start planner behind `/plan-from-idea`: explores the codebase in its own context and drafts a plan to `docs/plans/`. Cannot see the calling conversation, so use `/write-plan` when the design is already settled |
| `project-manager` | Decomposes plans into `bd` issues; ensures each bead has Why, How, and acceptance criteria (uses `plan-to-beads` skill) |
| `diagnostician` | Read-only investigation: evidence, hypotheses, root cause |
| `product-analyst` | Objective product analysis (features, pricing, competitors, pain points, market capture) |
| `research-librarian` | Ingests sources into Research wiki: reads, assesses study quality, generates summaries and entity/concept pages (uses `research-ingest` skill) |
| `ux-product-designer` | UX audit of a web app via Playwright, 7-dimension evaluation with severity-ranked report |
| `ux-product-designer-ios` | UX audit of an iOS app via Simulator, tests Dynamic Type / Dark Mode / accessibility, 7-dimension evaluation against Apple HIG |
| `product-manager` | Senior/Staff PM routing agent; dispatches to competitive-analysis, ab-test-design, product-research, product-roadmap, and product-brief skills |
| `product-cartographer` | Maps a codebase into a MECE/Pyramid `docs/products/` tree and proactively hunts for bugs/gaps/debt, logging each to a ledger and promoting actionable ones into bead-audit-compliant beads; refresh-first (uses `product-surface-docs` skill) |

## Architecture

```text
commands/*.md → agents/*.md → skills/*/SKILL.md
     |               |              |
  Invokes       Follows        Implements
```

**Example flow:**

1. User invokes `/rails-code-review` command
2. Command loads `review-rails` skill via the Skill tool
3. Skill defines the systematic review technique
4. Output follows the skill's specified format

## Architecture Decision Records

`/adr` writes them to `docs/adr/`. The point of the directory is that other components read
it, not that it exists. It was named docs/decisions until 2026-08-28, and that directory is gone. It moved so that
`mattpocock-skills:domain-modeling`, which writes to `docs/adr/` and cannot be redirected, lands
its ADRs where everything here reads.

**`/build` reads it before the first edit.** Phase 2 opens the records whose subject the change
touches and reports which ones bind it. An ADR that contradicts the plan outranks the plan.

**`/build` proposes new ones.** Phase 3 lists any design decision that constrains work beyond the
current bead as an ADR candidate, so a choice worth keeping does not die in the transcript.

**Write one only when reversing the decision would cost more than a day, and somebody would
otherwise argue it again.** Everything smaller belongs in the bead's `design` field. Two moments
produce most of the ones worth having: when `/grill-me` resolves a hard-to-reverse choice, and when
`/plan-review` returns Needs Revision over a contested design choice.

The working example in this repository is `docs/adr/0001-native-tracker-fields-are-canonical.md`.
The `plan-to-beads` skill cites it by name five times, including in its own checklist, so it is a
rule other components obey. A record nothing cites is a diary entry, and it buries the ones that
carry rules.

## Always-On Style Core

This plugin injects a small, universal coding-style core into **every session and every
spawned subagent** via Claude Code lifecycle hooks (`SessionStart` + `SubagentStart`). The
model-invoked `style-*` / `review-*` skills still carry the detailed per-language rules; the
always-on hook just guarantees the universal core (`hooks/style-core.md`) is present even when
a skill is not loaded and inside subagents that do not inherit the parent's skills. The core
also fixes spelling: American English throughout (identifiers, comments, docs, commit
messages), except when quoting a name you do not own. Injected text opens with a
`<!-- house-style-core: loaded -->` marker so you can see it is active.

`SessionStart` additionally injects a response style (`<!-- house-response-style: loaded -->`
marker): respond concisely, write in Simplified Technical English, the controlled-English
standard specified in ASD-STE100 (its writing rules only, never its licensed dictionary: one
word one meaning, active voice, no jargon or borrowed metaphor, sentences capped at twenty-five
words for an explanation and twenty for an instruction, with technical names like files and
settings kept verbatim), report your own work in a fixed shape
and never let a label like "green" or "a flake" stand without the facts it
stands for, put choices that trade off on more than
one factor into a decision matrix with a bold recommendation, suggest a follow-up question
only when the answer genuinely raises one, and end any response that leaves work open with a
"Next actions" section split into "Me (Claude)" and "You". Parent sessions only; subagents get the coding-style core
alone, since their output goes to the orchestrator, not a human. The rules live in one
place, `skills/house-response-style/SKILL.md`: the hook reads that file (stripping its
frontmatter) so the always-on injection can never drift from the on-demand `/response-style`
command, which loads the same skill to re-assert the style after a compaction or inside a
subagent.

**Behavior change on upgrade.** Installing this version makes the style core fire in **every
session for every project** the plugin is loaded for, including non-coding ones (product,
research, ASO). This is intentional. Use the off-switch below for sessions where it is noise.

**Off-switch.** Set `TADW_STYLE_CORE=off` (also `0` / `false`), or create a flag file at
`${CLAUDE_CONFIG_DIR:-~/.claude}/.tadw-style-core-off`. Either disables both the session and
subagent injection.

**Requires `node` on PATH.** The hook runs `node` through `hooks/run-hook.sh`. If `node` is not
on the non-interactive shell's PATH (common with `fnm`/`nvm`), the core cannot be injected and
the wrapper says so: it emits `<!-- house-style-core: FAILED to load (node missing or script
error) -->` in place of the core. If you see that marker, fix your PATH so `node` resolves in a
non-interactive shell. If you see no marker at all, the hook did not run; check the matcher and
the off-switch.

**Test the hooks:** `node hooks/test-hooks.js` (no dependencies, no install).

## Commands and skills share one namespace

`commands/<name>.md` and `skills/<name>/SKILL.md` are addressed as the same `tadw:<name>`, and
the command wins. A command whose body says "Use the `<name>` skill" therefore resolves back to
itself and never reaches the skill.

**The rule: a command may share a skill's name, or delegate to that skill by name, but never
both.** Three ways to satisfy it:

- **Give the command a different name.** `/fresh-eyes-cr` loads `review-fresh-eyes`,
  `/prod-ops` loads `production-ops`. This is what most commands already do.
- **Delete the command.** If it only names its own skill, it adds nothing, and the skill takes
  the slash name once the shadow is gone.
- **Read the skill file instead of invoking it.** Commands that carry real per-invocation
  instructions do this: `**Read** ${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md`.

## Creating Components

### New Skill

1. Create `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`)
2. Add the name to the "Registered Skills" list in AGENTS.md
3. Add a description row to the Skills table above

### New Agent

1. Create `agents/<name>.md` with YAML frontmatter (`name`, `description`, `model`, `tools`)
2. Add the name to the "Registered Agents" list in AGENTS.md
3. Add a description row to the Agents table above

### New Command

1. Create `commands/<name>.md` with YAML frontmatter (`description`, optional `argument-hint`)
2. Reference an agent or skill in the body
3. Add the name to the "Registered Commands" list in AGENTS.md
4. Add a description row to the Commands table above

Run `/validate-plugin` after changes to verify integrity.

## License

MIT License
