# Plan: Align agent naming and consolidate code agents

**Date:** 2026-04-30
**Status:** Ready
**Owner:** Jason Templeton

## Goals

1. Apply "agent = role (noun), skill = action" consistently across the plugin.
2. Reduce 13 agents to 10 by consolidating overlapping code-engineering agents.
3. Fix the immediate `/ux-audit` and `/ux-audit-ios` wiring issue that started this work.

## Resolved decisions

These were open questions in the prior draft. Resolving them up front avoids each stage inventing its own convention.

1. **Keep `/frontend-code-review` as a thin alias.** Discoverability matters; users searching for "frontend" should find a command. It will route to `code-reviewer` agent + `templeton-frontend-style` skill scoped to frontend files.
2. **Keep both UX audit agents.** They hold the tool permissions (Playwright MCP for web, plain Bash for iOS) and the role identity. The skill captures the audit technique; the agent decides who is doing the work and with what tools.
3. **Agent name `software-engineer`** (vs. `coder`, `engineer`, `developer`). Most descriptive; matches existing naming verbosity (`product-analyst`, `ux-product-designer`).
4. **`feature-development` skill preserves the 4-phase workflow** (discovery -> implementation -> simplification -> linting), generalized across languages. The skill owns WORKFLOW; language-specific style skills (`templeton-python-style`, `templeton-frontend-style`, etc.) own STYLE. The skill detects language and loads the right style skill in phase 2.

## Conventions

These two patterns are the contract for every command, agent, and skill in this plan.

### Pattern 1: Command -> Skill (preferred for slash commands)

A slash command is invoked in the main conversation. The command body invokes the Skill tool directly. The agent is named for context only.

**Example: `commands/ux-audit.md`**

```markdown
---
description: "Run a UX audit of a web app via Playwright"
argument-hint: "<app-url> [notes]"
---

Use the `ux-audit` skill to conduct a UX audit of $ARGUMENTS.

This audit operates from the `ux-product-designer` role: a senior product designer
working at the standard of Apple, Stripe, and Airbnb design teams.
```

### Pattern 2: Agent -> Skill (for parallel/isolated work via Task tool)

When an agent is invoked via the Task tool (`subagent_type: ux-product-designer`), the agent's body references the skill.

**Example: `agents/ux-product-designer.md`**

```markdown
---
name: ux-product-designer
description: Senior product designer who conducts UX audits of web apps...
model: inherit
tools: ["Read", "Write", "Bash", "Grep", "Glob", "Skill", "mcp__plugin_playwright_playwright__browser_navigate", ...]
---

# Role: UX Product Designer

You are a principal-level product designer... [role identity, beliefs, design hypotheses]

## Your primary technique

Use the `ux-audit` skill (loaded via the Skill tool) for the audit workflow,
7-dimension framework, and report template.
```

The skill owns the WORKFLOW (steps, framework, output format). The agent owns the IDENTITY (who they are, what they believe, what tools they wield).

## Files affected (all stages)

- `agents/` - 4 deletions, 2 renames, 1 new file, content updates to slim down extracted agents
- `skills/` - 7 new skill directories
- `commands/` - 5 commands updated to point at new agents/skills
- `AGENTS.md`, `README.md`, `docs/AGENTS.md`, `docs/AGENTS-IMPROVEMENTS.md` - documentation updates
- `.claude-plugin/plugin.json` - version bump (1.6.0 -> 1.7.0; this is breaking for anyone calling agents by name)

---

## Stage 1: Fix UX audit alignment

**Why first:** It's the smallest change, unblocks the original problem, and validates the conventions above before applying them broadly.

**Changes:**

1. Create `skills/ux-audit/SKILL.md` - extract the workflow, 7-dimension framework, and report template from `agents/ux-product-designer.md`.
2. Create `skills/ux-audit-ios/SKILL.md` - same extraction from `agents/ux-product-designer-ios.md`.
3. Slim down both `ux-product-designer*` agents per Pattern 2: keep the role identity, beliefs, and tool list; replace the workflow body with "Use the `ux-audit` (or `ux-audit-ios`) skill via the Skill tool." Add `Skill` to each agent's tools list.
4. Rewrite `commands/ux-audit.md` and `commands/ux-audit-ios.md` per Pattern 1: invoke the skill directly, mention the agent role for context.
5. Update `AGENTS.md` registry (add the two new skills under "Registered Skills").
6. Update `README.md` Skills table.

**Verification:** Run `/ux-audit https://example.com` and `/ux-audit-ios <bundle-id>`; confirm each loads the correct skill cleanly and produces a report at `docs/ux-audits/<slug>.md`.

---

## Stage 2: Consolidate code agents into `software-engineer`

**Why:** Four agents (`code-simplifier`, `fresh-eyes-reviewer`, `python-feature-developer`, `frontend-code-reviewer`) share the same role: a software engineer making code changes. Their differences are in *how they work* (action), which belongs in skills.

**Keep separate:**

- `code-reviewer` - read-only review boundary stays intact (mirrors `diagnostician`'s safety pattern). Read-only access prevents an investigation/review from accidentally rewriting code.

### `software-engineer` routing logic

The agent body must include this decision tree explicitly. Without it the agent becomes a junk drawer.

| User intent | Skill to load | Notes |
|---|---|---|
| "Find bugs", "review for errors", "fresh eyes pass" | `fresh-eyes-review` | Read changed files, identify obvious bugs, fix directly |
| "Simplify", "clean up", "refactor for clarity" | `code-simplify` | Refactor without changing behavior; defer to language style skill |
| "Implement", "build", "add feature", "create" | `feature-development` | 4-phase workflow: discovery, implementation, simplification, linting |
| "Review code" (no edit intent) | Refuse and redirect to `/code-review` (uses `code-reviewer` agent) | Read-only review is a different role |
| Any of the above + a specific language | The skill above + the matching style skill (e.g., `templeton-python-style` for `.py` files) | Skills compose; never re-explain language style inline |

The agent body must end with: "If the request doesn't match one of the rows above, ask the user to clarify which mode you should operate in. Do not invent a workflow."

### `feature-development` skill scope

The skill preserves the 4-phase workflow currently in `python-feature-developer`, generalized across languages:

1. **Discovery** - ask clarifying questions about behavior, edge cases, integration points
2. **Implementation** - detect language, load the appropriate style skill (`templeton-python-style`, `templeton-frontend-style`, `templeton-swift-style`), write the code
3. **Simplification** - apply the `code-simplify` skill to the new code
4. **Linting** - run the project's configured linter for the language; fix issues

The skill explicitly delegates to style skills rather than restating their rules.

**Changes:**

1. Create `agents/software-engineer.md`:
   - Tools: `["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Skill"]`
   - Body: role identity + the routing decision tree above + delegation rule
2. Extract three skills:
   - `skills/code-simplify/SKILL.md` - from `agents/code-simplifier.md`
   - `skills/fresh-eyes-review/SKILL.md` - from `agents/fresh-eyes-reviewer.md`
   - `skills/feature-development/SKILL.md` - from `agents/python-feature-developer.md`, generalized across languages per the scope above
3. Delete: `agents/code-simplifier.md`, `agents/fresh-eyes-reviewer.md`, `agents/python-feature-developer.md`, `agents/frontend-code-reviewer.md`. The frontend reviewer is dropped entirely; `code-reviewer` already dispatches to `templeton-frontend-style`.
4. Rewire commands per Pattern 1:
   - `/fresh-eyes-cr` -> "Acting as `software-engineer`, use the `fresh-eyes-review` skill on $ARGUMENTS."
   - `/python-feature-dev` -> "Acting as `software-engineer`, use the `feature-development` skill to implement: $ARGUMENTS."
   - `/frontend-code-review` -> "Acting as `code-reviewer`, use the `templeton-frontend-style` skill to review changed frontend files."
5. Update `AGENTS.md`, `README.md`, `docs/AGENTS.md`.

**Verification:**
- `/fresh-eyes-cr` on a small uncommitted change - confirm it loads `fresh-eyes-review` and edits files.
- `/python-feature-dev "add a CLI argument parser"` - confirm 4-phase workflow runs.
- `/frontend-code-review` on a frontend file change - confirm it routes through `code-reviewer` and uses `templeton-frontend-style`.

---

## Stage 3: Rename remaining action-named agents and align `/review-plan`

**Changes:**

1. Rename `agents/plan-to-beads.md` -> `agents/project-manager.md`; update `name: project-manager`. Extract the decomposition workflow into `skills/plan-to-beads/SKILL.md`. Slim the agent body to role identity + "use the `plan-to-beads` skill."
2. Rename `agents/research-ingest.md` -> `agents/research-librarian.md`; update `name: research-librarian`. Extract the ingestion workflow into `skills/research-ingest/SKILL.md`. Slim the agent body to role identity + "use the `research-ingest` skill."
3. Update `commands/plan-to-beads.md` and `commands/research-ingest.md` per Pattern 1.
4. **Rename `commands/review-plan.md` -> `commands/plan-review.md`** to match the existing `plan-review` skill. Skills follow noun-noun naming convention (`aso-audit`, `code-review`, `research-ingest`); the command should match. Update references in `AGENTS.md` (lines 240, 316) and `README.md` (lines 19, 25). The Pipeline A flow becomes: `/business-ideas` -> `/plan-feature` -> `/plan-review` -> `/plan-to-beads`.
5. Update `AGENTS.md`, `README.md`, `docs/AGENTS.md`.

**Verification:**
- `/plan-to-beads docs/plans/<existing-plan>.md` - confirm it decomposes into `br` issues.
- `/research-ingest` - confirm it processes a source from `Research/sources/`.
- `/plan-review docs/plans/agent-naming-consolidation.md` - confirm the rename works and the skill loads.

---

## Stage 4: Sweep, validate, and ship

1. **Reference sweep:** `grep -rln -e 'code-simplifier' -e 'fresh-eyes-reviewer' -e 'frontend-code-reviewer' -e 'python-feature-developer' -e 'plan-to-beads' -e 'research-ingest' -e 'review-plan' --include='*.md' --include='*.json' .` Fix any stragglers in `docs/AGENTS.md`, `docs/AGENTS-IMPROVEMENTS.md`, `docs/claude-md-reviewer*.md`, or anywhere else.
2. **Validate:** Run `/validate-plugin`; must show zero errors.
3. **Version bump:** `.claude-plugin/plugin.json` to `1.7.0`.
4. **Update registries:** "Registered Agents/Skills/Commands" lists in `AGENTS.md` reflect final state.
5. **Migration note in README:** Add a short section noting (a) which agents were renamed/removed and what they map to, (b) marketplace cache impact - users with the plugin installed via marketplace will need `/plugin update` (or reinstall) to pick up the changes; active sessions referencing old agent names by Task `subagent_type` will fail until restart.
6. **Commit per stage:** Single commit per stage so any stage can be reverted independently.

---

## Final agent roster (after all stages)

| Agent | Role |
|---|---|
| `code-reviewer` | Read-only language-detecting reviewer |
| `software-engineer` | Editing role for review-and-fix, simplify, implement |
| `diagnostician` | Read-only investigator |
| `feature-planner` | Codebase-aware planner (writes to `docs/plans/`) |
| `project-manager` | Decomposes plans into `br` issues |
| `claude-md-reviewer` | CLAUDE.md / AGENTS.md specialist |
| `product-analyst` | External product research |
| `research-librarian` | Research wiki ingestion |
| `ux-product-designer` | Web UX audit role |
| `ux-product-designer-ios` | iOS UX audit role |

10 agents, all role-named.

## Skill additions

`ux-audit`, `ux-audit-ios`, `code-simplify`, `fresh-eyes-review`, `feature-development`, `plan-to-beads`, `research-ingest`. 7 new skills, each owning the workflow and output format that was previously embedded in agents.

## Risks and trade-offs

- **Breaking change for anyone scripting against agent names.** Mitigated by version bump to 1.7.0 and a migration note in the README.
- **Marketplace cache lag.** Installed users won't see the rename until they `/plugin update`. Active sessions using the Task tool with old `subagent_type` values will fail until restart.
- **`software-engineer` could become a junk drawer.** Mitigated by the explicit routing decision tree and the "ask, don't invent" delegation rule.
- **Skill duplication risk.** `code-simplify` and `fresh-eyes-review` both touch language-style skills. They must explicitly delegate to `templeton-{python,frontend,swift}-style` rather than re-explain those rules.
- **`feature-development` generalization.** The current `python-feature-developer` is Python-specific. Generalizing the 4-phase workflow across languages is straightforward in principle but the skill needs concrete examples for Python, JS/TS, and Swift to avoid being abstract.
