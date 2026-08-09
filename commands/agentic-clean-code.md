---
description: "Design or review agentic systems (tools, prompts, orchestration) against Clean Code and POODR principles"
argument-hint: "[path or component to review, or a design question]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/agentic-clean-code/SKILL.md` and follow it to design or review agentic code: tool definitions, prompt architecture, orchestration logic, agent loops, and anything where an LLM drives execution.

Read the file rather than invoking the skill by name. `commands/agentic-clean-code.md` and
`skills/agentic-clean-code/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(agentic-clean-code)` returns this file and never reaches the skill. If that path does not resolve, locate the file with `Glob: **/skills/agentic-clean-code/SKILL.md` and read it from there.

Scope comes from `$ARGUMENTS`. If none is given, auto-detect: review the agent, skill, tool, and prompt files changed on this branch (`git diff main...HEAD --name-only`), and say which files were picked before reviewing them. If nothing is changed and no target is named, ask what to review rather than guessing.

The skill will:

1. Load the principles across its five areas: tool design (SRP, tell-don't-ask, explicit contracts, no surprise side effects, idempotency), prompt architecture (small prompts, no implicit state, parameters as arguments), orchestration (planning separated from execution, minimal footprint, explicit boundaries, fail loudly), naming (name for the model as well as the human, docstrings as contracts), and testability (isolation, step-level behavior)
2. Apply the smell checklist to each component in scope
3. Report findings with the principle each one violates and a concrete fix

**Two modes, decided by what you asked for:**

- **Design** (a question, or a component that does not exist yet): propose a structure and justify it against the principles. Do not write implementation files unless asked.
- **Review** (an existing path or changed files): report findings. This is read-only by default; apply fixes only when explicitly asked.

Order findings by what would actually break an agent at runtime (a tool that hides side effects or swallows errors) ahead of what reads poorly (naming, docstring phrasing). Ground every finding in the specific file and the named principle; "this prompt is too big" is useless, "this prompt carries three unrelated jobs, violating Small Prompts, split at the retrieval step" is useful.
