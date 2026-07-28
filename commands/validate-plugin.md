---
description: Validate plugin integrity - checks that all agents, skills, and commands are consistent and properly wired
---

You are a plugin integrity validator. Perform a comprehensive check of this plugin repository and report any issues found.

**Required checks:**

### 1. Structural Validation

- Verify `skills/*/SKILL.md` exists for every skill directory
- Verify each agent in `agents/*.md` has valid YAML frontmatter with `name`, `description`, and `tools`
- Verify each command in `commands/*.md` has valid YAML frontmatter with `description`
- Check for empty or near-empty files (< 5 lines of content)

### 2. Cross-Reference Validation

For each **agent**, check:

- Every skill it references (via `Skill` tool or by name) has a corresponding `skills/<name>/SKILL.md`
- Every tool listed in its `tools` frontmatter is a valid Claude Code tool name

For each **command**, check:

- If it references an agent, that agent exists in `agents/`
- If it references a skill, that skill exists in `skills/`

### 3. Orphan Detection

- Find skills in `skills/` that are not referenced by any agent or command
- Find agents in `agents/` that are not referenced by any command
- These are not necessarily errors, but should be flagged as warnings

### 4. Frontmatter Consistency

- Check that agent `name` fields match their filename (e.g., `code-simplifier.md` should have `name: code-simplifier`)
- Check that skill `name` fields match their directory name
- Flag any missing required frontmatter fields

### 5. Documentation Alignment

- Check that `AGENTS.md` mentions all agents, skills, and commands that exist on disk
- Flag any components documented in `AGENTS.md` that don't actually exist
- Flag any components on disk that aren't documented in `AGENTS.md`

**Output format:**

```markdown
## Plugin Validation Report

### Errors (must fix)

- [ ] [ERROR] description of issue

### Warnings (should review)

- [ ] [WARN] description of issue

### Summary

- Skills: X found, Y referenced, Z orphaned
- Agents: X found, Y referenced, Z orphaned
- Commands: X found
- Cross-references: X valid, Y broken
- Overall: PASS / FAIL (FAIL if any errors)
```

**Process:**

1. Use Glob to find all `skills/*/SKILL.md`, `agents/*.md`, and `commands/*.md` files
2. Use Read to check frontmatter of each file
3. Use Grep to find cross-references between components
4. Read `AGENTS.md` and compare against what exists on disk
5. Compile and output the report
