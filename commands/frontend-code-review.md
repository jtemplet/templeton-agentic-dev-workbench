---
description: "Frontend code review (JS/TS/React/Vue) following Sandi Metz principles, focused on changed frontend files"
---

Use the `style-frontend` skill to review changed frontend code.

The review operates from the `code-reviewer` role: a read-only reviewer that detects languages and applies the matching style skill. Refer to `agents/code-reviewer.md` for the role's principles. This command is a frontend-scoped shortcut to `/code-review`; it focuses the review on JavaScript / TypeScript / React / Vue files in the diff.

**Workflow:**

1. Get the git diff for `.js`, `.jsx`, `.ts`, `.tsx`, and `.vue` files between the current branch and main
2. Load the `style-frontend` skill via the Skill tool
3. Review in the skill's priority order:
   - **Separation of Concerns (CRITICAL)** - Logic mixed in components, business logic in UI
   - **Component Design (HIGH)** - Size, single responsibility, premature abstraction
   - **TypeScript Usage (HIGH)** - Type safety, `any` usage, proper interfaces
   - **Frontend Patterns (MEDIUM)** - Hooks/composables, state management, composition
   - **Code Style (MEDIUM)** - Naming, organization, console.logs
   - **Testing (MEDIUM)** - Test coverage for logic, proper mocking

4. Document every issue with: Category, Priority, Location (file:line), Problem (with code), Why it matters, Concrete fix (before/after), Verification steps

5. Provide a summary with:
   - Issues by priority (table)
   - Critical actions required
   - Positive findings (what was done well)
   - Overall assessment (Code Quality, Type Safety, Architecture, Testability)
   - Merge recommendation with effort estimate

**Key principles:**

- Wait for the third occurrence before flagging duplication (Sandi Metz)
- Components should be small and focused (~100 to 150 lines)
- Extract business logic to custom hooks (React) or composables (Vue)
- Prefer composition over props explosion
- Use TypeScript properly: avoid `any`, define interfaces
- Focus on separation of concerns before style issues
- Be constructive and provide actionable recommendations
- Prioritize: Critical (architecture) > High (design/types) > Medium (patterns) > Low (style)

This is a read-only review. To fix issues directly, follow up with `/fresh-eyes-cr` (uses `software-engineer` role with Edit access).
