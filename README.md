# templeton-agentic-dev-workbench

Custom skills for Claude Code. Part of the [agent-marketplace](https://github.com/jtemplet/agent-marketplace).

## Installation

```bash
# Register marketplace
/plugin marketplace add jtemplet/agent-marketplace

# Install this plugin
/plugin install templeton-agentic-dev-workbench@agent-marketplace
```

## Skills

### rails-code-review

Systematic technique for comprehensive Rails 8 code reviews covering security vulnerabilities (XSS, SQL injection), Rails conventions, Hotwire/Turbo patterns, performance optimization, and DRY principles with priority-based issue categorization.

**Use when:**

- Reviewing Rails code before merge or PR
- Performing security audits
- Validating Rails 8 conventions and Hotwire patterns

**Output:** Prioritized list of issues with location, problem, fix, and verification steps.

See [SKILL.md](./skills/rails-code-review/SKILL.md) for full documentation.

### templeton-rspec-style

Opinionated RSpec testing style for Rails applications emphasizing request specs, clean test organization, and DRY principles.

**Use when:**

- Writing new RSpec tests for Rails applications
- Converting controller tests to request specs
- Refactoring existing tests to follow best practices
- Reviewing test code for style compliance

**Key principles:**

- Request specs over controller tests (always)
- Setup in `let`/`let!` blocks, not in `it` blocks
- HTTP requests in `subject` blocks
- Context-driven organization
- Concise assertions

See [SKILL.md](./skills/templeton-rspec-style/SKILL.md) for full documentation.

### terraform-iac-expert

Senior staff-level DevOps expertise for Terraform and Infrastructure as Code across AWS, Azure, and GCP with 10+ years of FAANG experience.

**Use when:**

- Writing or reviewing Terraform configurations
- Designing cloud infrastructure
- Creating reusable Terraform modules
- Debugging Terraform state or deployment issues
- Setting up CI/CD pipelines for infrastructure
- Implementing security and compliance best practices

**Key principles:**

- Infrastructure as Code (IaC) first approach
- Modular, reusable, maintainable infrastructure
- Security by default with least privilege
- Multi-cloud expertise
- Environment isolation and workspace management

See [SKILL.md](./skills/terraform-iac-expert/SKILL.md) for full documentation.

### python-code-review

Comprehensive Python code review following PEP 8 and Google Python Style Guide standards, with emphasis on security, type hints, and best practices.

**Use when:**

- Reviewing Python code before merge or PR
- Performing security audits (SQL injection, hardcoded secrets, unsafe functions)
- Validating PEP 8 and Google Style Guide compliance
- Checking type hints and documentation
- Analyzing performance and maintainability

**Key principles:**

- Consistency within project > rigid rule adherence
- Wait for third occurrence before flagging duplication (Sandi Metz principle)
- Prioritize: Critical (security/bugs) > High (readability) > Medium (style) > Low (nitpicks)
- Focus on changes being made, not rewriting entire codebase

**Output:** Structured review with severity levels, specific line numbers, before/after code examples, and rationale for each issue.

See [SKILL.md](./skills/python-code-review/SKILL.md) for full documentation.

### templeton-python-style

Write or refactor Python code following Sandi Metz's object-oriented design principles from "Practical Object-Oriented Design in Ruby" (POODR), adapted for Python.

**Use when:**

- Writing new Python code with strong OOD principles
- Refactoring Python code to improve design
- Reviewing Python code for architectural issues
- Learning object-oriented design patterns

**Core principles:**

- Wait for duplication (rule of three) before abstracting
- Methods should be small and do one thing
- Classes should have single, cohesive responsibilities
- Max 4 parameters per method
- Inject dependencies, never hardcode
- Tell, Don't Ask (avoid deep attribute chaining)
- Shallow inheritance (1-2 levels), prefer composition

**Output:** TRUE code (Transparent, Reasonable, Usable, Exemplary) with proper messaging, dependency injection, and clear responsibilities.

See [SKILL.md](./skills/templeton-python-style/SKILL.md) for full documentation.

### rails-conventions

Comprehensive Rails 8 conventions and best practices guide. Enforces "The Rails 8 Way": convention over configuration, Solid Stack over external dependencies, and Hotwire over React.

**Use when:**

- Generating or refactoring Rails code
- Evaluating whether to add a gem or framework
- Making architectural decisions
- Choosing between Rails-native vs third-party solutions

**Core principles:**

- Convention over configuration (Rails defaults)
- Vanilla Rails (thin controllers, rich domain models)
- Step-down rule (read code top-to-bottom)
- Many small controllers > few fat controllers
- Concerns for composition, service objects when truly needed
- Rails 8 Solid Stack (Solid Queue, Solid Cache, Solid Cable)
- Hotwire (Turbo + Stimulus) over React

**Includes detailed guidance on:**

- Controller/Model/Concern structure and ordering
- When to use service objects (POROs) vs models + concerns
- Method ordering (vertical invocation + step-down rule)
- Conditional returns and visibility modifiers
- ActiveRecord patterns and scopes
- Resource-oriented design

See [SKILL.md](./skills/rails-conventions/SKILL.md) for full documentation.

## Agents

### code-simplifier

Language-agnostic code simplification agent for Python and Ruby/Rails. Enhances code clarity and maintainability while preserving exact functionality.

**Use when:**

- Refactoring complex code
- Reducing nesting and cognitive load
- Simplifying after feature implementation
- Before committing changes

**Approach:**

- Python: Applies `templeton-python-style` skill (Sandi Metz principles)
- Ruby/Rails: Applies `rails-conventions` skill (Rails Way patterns)

**Key principles:**

- Preserve functionality (never change behavior)
- Reduce nesting with guard clauses
- Eliminate redundancy (wait for third occurrence)
- Improve naming and clarity
- Extract complex logic into focused methods
- Follow language-specific conventions

**Output:** Before/after examples with rationale for each simplification

### rails-code-reviewer

Specialized subagent for comprehensive Rails 8 code reviews. Loads the rails-code-review skill and executes systematic review workflow.

**Use via:** Manual invocation or Task tool (when registered as subagent type)

### python-feature-developer

Guided Python feature development agent that leads through a 4-phase workflow: discovery, implementation, simplification, and linting. Uses the templeton-python-style skill for implementation guidance.

**Triggers on:**

- "implement [feature] in Python"
- "create a Python [component]"
- "add [functionality] to Python code"

**Workflow phases:**

1. **Discovery** - Asks clarifying questions about inputs, outputs, and edge cases
2. **Implementation** - Writes code following Sandi Metz principles
3. **Simplification** - Refines code while preserving readability
4. **Linting** - Applies ruff for PEP8/Google Python Style compliance

**Output:** Production-ready Python code written to files with type hints, docstrings, and error handling

### rework-coding-style

Language-aware agent for applying opinionated coding style conventions. Detects code language and invokes the appropriate style skill.

**Use when:**

- Applying templeton style to Python code
- Styling Rails/Ruby code to follow conventions
- Standardizing code across multiple files
- Reworking code after feature implementation

**Approach:**

- Python: Invokes `templeton-python-style` skill
- Ruby/Rails: Invokes `rails-conventions` skill
- Detects language from file extension and context

**Output:** Styled code with clear summary of conventions applied

## Commands

### /rails-code-review

One-command trigger for instant Rails code reviews.

**Usage:** `/rails-code-review` - Automatically loads skill and agent workflow

### /python-code-review

One-command trigger for comprehensive Python code reviews following PEP 8 and Google Style Guide.

**Usage:** `/python-code-review` - Automatically loads skill and executes systematic review

### /python-feature-dev

Guided Python feature development with discovery, implementation, simplification, and linting phases.

**Usage:**

- `/python-feature-dev "add user authentication"` - With feature description
- `/python-feature-dev` - Interactive mode (prompts for feature description)

**Result:** Invokes python-feature-developer agent for structured workflow

## System Architecture

The workbench uses a three-layer architecture:

- **Commands** (e.g., `/rails-code-review`) provide quick access triggers
- **Agents** (e.g., `rails-code-reviewer`) define workflows and processes
- **Skills** (e.g., `rails-code-review`) contain systematic techniques and best practices

This layered approach ensures consistency, maintainability, and flexibility.

## Creating New Skills

Each skill should:

1. Live in its own directory under `skills/`
2. Have a `SKILL.md` file with YAML frontmatter
3. Follow the format shown in `skills/example-skill/SKILL.md`

### Skill Format

```markdown
---
name: skill-name
description: Brief description of when to use this skill
---

# Skill Name

## When to Use This Skill

[Describe triggering conditions...]

## The Process

[Step-by-step instructions...]
```

## License

MIT License
