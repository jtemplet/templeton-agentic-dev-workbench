---
description: "Guided 4-phase feature development: discovery, implementation, simplification, linting"
argument-hint: "[feature-description]"
---

Use the `feature-development` skill to implement: $ARGUMENTS

The implementation operates from the `software-engineer` role: a working engineer who clarifies requirements before coding, applies the project's language style, and verifies before declaring success. Refer to `agents/software-engineer.md` for the role's beliefs and judgment principles.

The skill will:

1. **Discovery** - Ask 3 to 7 clarifying questions about inputs, outputs, edge cases, and integration points
2. **Implementation** - Detect the language, load the matching style skill (`templeton-python-style`, `templeton-frontend-style`, `templeton-swift-style`, or `rails-conventions`), write the code to actual files
3. **Simplification** - Apply the `code-simplify` skill to refine the new code
4. **Linting** - Run the language's standard linter (ruff for Python, ESLint+Prettier for JS/TS, RuboCop for Ruby, swift-format for Swift) with auto-fix

If no arguments are provided, the skill will ask the user to describe the feature.

Despite the historical command name, this workflow is language-agnostic. The 4-phase pattern works for Python, JavaScript/TypeScript, Swift, and Ruby; the skill picks the right style guide and linter from the file extensions.
