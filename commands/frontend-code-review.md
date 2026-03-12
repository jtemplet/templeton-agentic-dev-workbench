---
description: Perform comprehensive frontend code review (JavaScript/TypeScript/React/Vue) following Sandi Metz principles
---

You are acting as a frontend code review expert. Follow the frontend-code-reviewer agent workflow:

**Required workflow:**

1. Load the templeton-frontend-style skill using the Skill tool
2. Get the git diff between current branch and main for JS/TS/JSX/TSX/Vue files
3. Execute systematic review following the skill's priority order:
   - Separation of Concerns (CRITICAL) - Logic mixed in components, business logic in UI
   - Component Design (HIGH) - Size, single responsibility, premature abstraction
   - TypeScript Usage (HIGH) - Type safety, `any` usage, proper interfaces
   - Frontend Patterns (MEDIUM) - Hooks/composables, state management, composition
   - Code Style (MEDIUM) - Naming, organization, console.logs
   - Testing (MEDIUM) - Test coverage for logic, proper mocking

4. Document every issue using the skill's output format:
   - Category & Priority
   - Location (file:line)
   - Problem description with code
   - Why it matters (impact on maintainability/testability)
   - Concrete fix with before/after (using ❌ and ✅)
   - Verification steps

5. Provide summary with:
   - Issues by priority (table)
   - Critical actions required
   - Positive findings (what was done well)
   - Overall assessment with ratings for: Code Quality, Type Safety, Architecture, Testability
   - Merge recommendation with effort estimate

**Key Review Principles:**

- Follow Sandi Metz principles: Wait for third occurrence before flagging duplication
- Components should be small and focused (~100-150 lines)
- Extract business logic to custom hooks (React) or composables (Vue)
- Prefer composition over props explosion
- Use TypeScript properly - avoid `any`, define interfaces
- Focus on separation of concerns before style issues
- Be constructive and provide actionable recommendations
- Prioritize: Critical (architecture) > High (design/types) > Medium (patterns) > Low (style)

**Output must follow the exact format specified in the frontend-code-reviewer agent.**
