---
name: feature-development
description: Guided 4-phase feature implementation. Asks clarifying questions, implements following language-specific style principles, refines via the code-simplify skill, then runs the language's linter. Detects language and delegates to templeton-python-style, templeton-frontend-style, templeton-swift-style, or rails-conventions for the actual style rules.
---

# Feature Development

A structured 4-phase workflow for implementing new features: Discovery, Implementation, Simplification, Linting. Language-agnostic at the workflow level; delegates to language-specific style skills for what good code looks like in each language.

## Universal Core (injected)

The universal coding-style core (`hooks/style-core.md`) is injected into every session and
subagent, so TRUE code and the cross-language principles (small units, wait for duplication,
tell-don't-ask, compose over inherit, fail fast, names that document) are already in context
while you implement. This skill owns the *workflow*; the language style skill loaded in Phase 2
owns the per-language rules. Do not restate either here.

## When to Use

- When implementing a new feature, function, class, or module
- When asked to "build", "create", "add", or "implement" something
- When the requirements need clarification before any code is written
- When the user wants a guided workflow rather than ad-hoc coding

## When NOT to Use

- For one-line bug fixes (just fix it)
- For pure refactoring (use the `code-simplify` skill instead)
- For exploratory spikes where the goal is to learn, not to ship
- When the user has already done discovery and only wants implementation

## The 4 Phases

### Phase 1: Discovery

Before writing any code, gather complete requirements by asking 3 to 7 focused, technical questions.

**Required information:**

- **Inputs:** What does it accept? What types? Required vs. optional?
- **Outputs:** What does it return? What type? What format?
- **Edge cases:** Empty inputs? Invalid types? Boundary conditions?
- **Errors:** What errors might occur? How should they be handled?
- **Dependencies:** What existing code, libraries, or services does it interact with?
- **Context:** Where will this code live? What's the surrounding architecture?

**Process:**

1. Read the user's initial request carefully
2. Identify gaps in the specification
3. Ask focused, technical questions to fill the gaps
4. Wait for user responses before proceeding
5. Summarize understanding to confirm alignment

**Example questions:**

- "What types should the input accept? Strings only, or also Path objects?"
- "How should this behave if the file doesn't exist? Raise, or return None?"
- "Are there performance requirements? Should this handle large datasets?"
- "Should this integrate with your existing logging/error handling?"

**Output of this phase:**

```text
## Discovery Complete

**Requirements Summary:**
- Input: [description]
- Output: [description]
- Edge cases: [list]
- Error handling: [approach]

**Implementation Plan:**
[2-3 sentence overview of approach]
```

### Phase 2: Implementation

Once requirements are clear, detect the language and load the matching style skill via the Skill tool:

| Extension | Style Skill |
|---|---|
| `.py` | `templeton-python-style` |
| `.rb`, `.erb`, `.rake` | `rails-conventions` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `templeton-frontend-style` |
| `.swift` | `templeton-swift-style` |

The style skill owns the language-specific principles. This skill owns the *workflow*. Do not restate language rules here.

**Implementation process:**

1. Load the matching style skill
2. Design the solution following its principles
3. Write clear, explicit code with descriptive names
4. Include appropriate type annotations / interfaces / docstrings as the style skill prescribes
5. Add error handling for the edge cases identified in discovery
6. **Write to actual files using Write or Edit. Never just show code in chat.**

**Output of this phase:**

```text
## Implementation Complete

**Files Written:**
- `[absolute_path]` - [brief description]

**Key Design Decisions:**
- [Decision 1 and rationale]
- [Decision 2 and rationale]

**Next: Simplification review**
```

### Phase 3: Simplification

After initial implementation, apply the `code-simplify` skill to the new code via the Skill tool. This is a separate skill because simplification is a generalizable action; loading it here keeps the rules in one place.

**The code-simplify skill will:**

- Reduce nesting
- Improve naming
- Extract methods where appropriate
- Eliminate redundancy (after the third occurrence)
- Apply the same language style skill that was loaded in Phase 2

**Output of this phase:**

```text
## Simplification Complete

**Improvements Applied:**
- [Improvement 1]
- [Improvement 2]

**Next: Linting**
```

### Phase 4: Linting

Apply the language's standard linter:

| Language | Linter | Command |
|---|---|---|
| Python | ruff | `ruff check [file] --fix` then `ruff format [file]` |
| JavaScript / TypeScript | ESLint + Prettier | `eslint --fix [file]` then `prettier --write [file]` |
| Ruby | RuboCop | `rubocop -A [file]` |
| Swift | swift-format | `swift-format --in-place [file]` |

**Linting process:**

1. Check if the linter is installed (e.g., `ruff --version`)
2. If not installed:
   - Ask the user: "[Linter] is not installed. Install it? (Recommended for [language] linting)"
   - If yes, install
   - If no, skip linting and note manual review is recommended
3. Run the linter with auto-fix
4. Review output:
   - Report auto-fixed issues
   - Report issues that could not be auto-fixed
   - If issues remain, ask the user how to proceed

**Output of this phase:**

```text
## Feature Development Complete

**Files Delivered:**
- `[absolute_path]`

**Quality Checks:**
- ✓ Discovery completed
- ✓ Style skill applied: [skill-name]
- ✓ Simplification applied
- ✓ Linting passed (or noted issues)

**Summary:**
[1-2 sentences describing what was built]
```

## Workflow Management

Use TodoWrite to track the four phases:

```text
1. Discovery: Ask clarifying questions about requirements
2. Implementation: Write code following [language] style principles
3. Simplification: Refine code via code-simplify skill
4. Linting: Apply [linter] for style compliance
```

Mark each phase as `in_progress` when starting and `completed` when done. Update in real-time.

## Edge Cases

### User skips discovery

If the user provides incomplete requirements:

- Do not proceed to implementation
- State: "I need more information before implementing this feature."
- Ask minimum 3 clarifying questions
- Wait for responses

### User wants to skip a phase

Respect the preference but note the trade-off:

- "I'll skip [phase] as requested, but note that [potential consequence]."
- Proceed to the next phase
- Mark the skipped phase as completed in TodoWrite

### Existing code exists

When adding to existing code:

1. Read existing files first to understand context
2. Match existing code style and patterns
3. Use Edit instead of Write to preserve existing code
4. Ensure new code integrates smoothly

### Tests are mentioned

If the user mentions tests:

- Ask if they want tests written as part of implementation
- If yes, write tests following the same 4-phase workflow
- Use the language's standard test framework (pytest for Python, Jest/Vitest for JS, RSpec for Ruby, XCTest for Swift)
- Place tests in the appropriate test directory

### Linter finds unfixable issues

If the linter reports violations that cannot be auto-fixed:

1. List the specific violations
2. Explain what each one means
3. Offer to fix them manually
4. Ask the user how to proceed

### Multi-file features

For features that span multiple files:

1. Plan the file structure during discovery
2. Implement in dependency order (low-level first)
3. Update TodoWrite to track each file
4. Run linting on all written files

## Critical Rules

**Always:**

- Complete discovery before coding
- Write to actual files, never just chat
- Load the language-specific style skill in Phase 2
- Apply the code-simplify skill in Phase 3
- Run the linter in Phase 4
- Track progress with TodoWrite
- Provide rationale for design decisions

**Never:**

- Skip the discovery phase
- Write code in chat without writing to files
- Restate language style rules in this skill (they live in the style skills)
- Create premature abstractions
- Assume requirements are complete
- Ignore linting errors without explanation

## Integration with Project Context

If the project has a CLAUDE.md or AGENTS.md file:

- Read it during discovery
- Match existing code organization patterns
- Follow project-specific naming conventions
- Integrate with existing error handling/logging
- Respect project dependencies and tooling choices
