---
name: code-simplify
description: Simplify and refine code for clarity, consistency, and maintainability while preserving exact functionality. Detects the language and delegates to the appropriate style skill (templeton-python-style for Python, rails-conventions for Ruby/Rails, templeton-frontend-style for JS/TS, templeton-swift-style for Swift). Focuses on recently modified code unless instructed otherwise.
---

# Code Simplification

A systematic technique for improving code clarity and maintainability without changing behavior. The skill is language-agnostic at the workflow level and delegates to language-specific style skills for the actual rules.

## When to Use

- After feature implementation, as a refinement pass
- During code review, to improve before-merge quality
- After test-driven development, as the refactor step
- Before committing, as a final polish pass

## When NOT to Use

- On code that is broken or failing tests (fix first, then simplify)
- On legacy code that is working but ugly, unless explicitly asked (the bar for changing working code is high)
- On code that you do not own or that has no tests (you cannot verify behavior is preserved)

## Required Workflow

### Step 1: Identify Scope

Default to recently modified code:

```bash
git diff --name-only
git diff --cached --name-only
git diff main...HEAD --name-only  # if both above are empty
```

If the user specifies a path, use that instead. Never simplify the entire codebase by default.

### Step 2: Detect Language and Load the Right Style Skill

Detect by file extension and load the matching style skill via the Skill tool:

| Extension | Style Skill |
|---|---|
| `.py` | `templeton-python-style` |
| `.rb`, `.erb`, `.rake` | `rails-conventions` (or `fizzy-style` if working in the Fizzy codebase) |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `templeton-frontend-style` |
| `.swift` | `templeton-swift-style` |

The style skill owns the language-specific rules. This skill owns the simplification *process*. Do not restate language rules here.

### Step 3: Analyze for Opportunities

Walk the code looking for these (in priority order):

| Category | Examples |
|---|---|
| **Reduce nesting** | Replace nested conditionals with guard clauses or early returns |
| **Eliminate redundancy** | Remove duplicate code (only if it appears 3+ times), dead code, unused variables |
| **Improve naming** | Replace ambiguous names, extract magic numbers/strings to named constants |
| **Simplify conditionals** | Replace complex boolean expressions with well-named methods; avoid nested ternaries |
| **Extract methods** | Break long methods into smaller, focused ones |

### Step 4: Apply Simplifications

For each opportunity:

1. Use the Edit tool to apply the change
2. Run any relevant tests immediately to verify behavior is preserved
3. If tests fail, revert and reconsider

### Step 5: Report

Output a structured summary:

```markdown
## Code Simplification Summary

[Brief overview of what was simplified, e.g., "Simplified UserProcessor by extracting nested conditionals into guard clauses and renaming ambiguous variables."]

### Changes Made

- [Specific improvement 1]
- [Specific improvement 2]

### Key Transformations

#### Change 1: [Short title]

**Before:**

```[lang]
[before code]
```
```


```text

**After:**

```[lang]
[after code]
```

**Why:** [1-2 sentence rationale]

### Verification

- [ ] All tests pass
- [ ] Behavior unchanged
- [ ] [Other relevant checks]

```text

## Universal Simplification Principles

These apply to all languages (specific language rules live in the loaded style skill):

### Reduce nesting

Replace deep nesting with guard clauses or early returns. Flat code is easier to scan than pyramids.

### Wait for the third occurrence

Do not abstract on the second duplication. Two similar pieces of code are an observation; three are a pattern. (Sandi Metz rule.)

### Make names earn their length

Long, descriptive names beat short cryptic ones. But unused length is just noise.

### Tell, don't ask

Avoid deep attribute chaining (`a.b.c.d`). If you find yourself reaching through multiple layers, the design is leaking.

### Prefer composition over inheritance

Shallow inheritance (1-2 levels max). Deep hierarchies are a maintenance trap.

## What NOT to Simplify

These are anti-patterns disguised as simplification:

- **Nested ternaries**: `a ? (b ? c : d) : e` is not clever, it is hostile.
- **Dense one-liners**: a line you cannot read at a glance is not simpler than three you can.
- **Premature abstractions**: a base class for two uses is technical debt.
- **Removing helpful comments**: architecture decisions, complex algorithms, and "why this and not that" notes earn their place.
- **Combining unrelated concerns**: reducing line count by jamming things together is not simplification.

## Critical Rules

**Always:**
- Preserve exact functionality (run tests after every change)
- Load the appropriate language style skill before editing
- Focus on recently modified code by default
- Improve readability, not line count
- Use clear, descriptive names

**Never:**
- Change behavior or functionality
- Over-simplify at the expense of clarity
- Create premature abstractions
- Remove comments that explain *why*
- Introduce language anti-patterns

## Quality Checklist

Before declaring the simplification complete:

- [ ] All tests pass (if tests exist)
- [ ] Functionality is preserved
- [ ] Code is more readable than before
- [ ] Language-specific style skill was loaded and applied
- [ ] No premature abstractions introduced
- [ ] Variable/method names are clear
- [ ] Nesting is reduced where appropriate
- [ ] Comments explain "why" not "what"
