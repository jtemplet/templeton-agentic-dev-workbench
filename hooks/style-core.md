<!-- house-style-core: loaded -->
<!-- Injected by templeton-agentic-dev-workbench on every session and subagent. -->
<!-- Universal coding-style core. Language-specific deltas live in the style-* skills. -->

# House Coding-Style Core

These are the universal, language-agnostic principles for any code you write or review
in this session. They apply across Python, Ruby/Rails, JavaScript/TypeScript, and Swift.
When a `style-*` or `review-*` skill loads, it adds language-specific deltas on top of
this core; it does not repeat or override it. If a directive here conflicts with a
project's `AGENTS.md`/`CLAUDE.md`, the project file wins.

## The Goal: TRUE Code

Every unit you write should be:

- **Transparent** - the consequences of a change are easy to see.
- **Reasonable** - the cost of a change is proportional to its benefit.
- **Usable** - it works in new and unexpected contexts.
- **Exemplary** - its quality invites the next person to follow the pattern.

## The Principles

1. **Wait for duplication before abstracting.** Duplication is cheaper than the wrong
   abstraction. Leave code duplicated at two occurrences; extract only on the third, when
   the real pattern is visible. A base class or shared helper built for two callers is debt.

2. **Keep units small and single-purpose.** A function, method, component, or type does
   one thing. If you cannot name it without "and", it is doing too much. Aim for code that
   reads without scrolling. No hard line limit; clarity is the test.

3. **Keep interfaces simple.** Prefer four or fewer parameters. Replace long or
   boolean-flag parameter lists with a typed parameter object. A boolean that switches
   behavior usually wants to be two separate units.

4. **Inject dependencies; do not hardcode them.** Pass collaborators in rather than
   constructing or reaching for them inside. Depend on an interface/protocol/contract, not
   a concrete implementation. This is what makes code testable and changeable.

5. **Tell, don't ask.** Send an object a message; do not pull out its internals and decide
   for it. Deep chaining (`a.b.c.d`) couples you to structure that will change. Move the
   behavior to where the data lives.

6. **Compose over inherit.** Build behavior by combining small pieces. Keep any
   inheritance shallow (one or two levels) and reserve it for a true "is-a" relationship.
   Reach for protocols, mixins, modules, hooks, or composables before a class hierarchy.

7. **Fail fast and be explicit about errors.** Raise or return a structured error at the
   boundary; never swallow one silently. An error should add context, not hide the
   original. Do not use exceptions for ordinary control flow.

8. **Read top-down (the step-down rule).** Order code as a narrative: high-level intent at
   the top, supporting detail below, low-level implementation at the bottom. Each unit
   sits at one level of abstraction. A reader should grasp intent from the top without
   diving into details.

9. **Let names do the documenting.** Choose names that state intent so the code explains
   itself. Make a name's length match its scope. A name that needs a comment to say what it
   is usually wants to be renamed, not annotated.

10. **Comment only when necessary, and only the why.** Default to no comment: code with
    clear names and small units needs none. Add one only for what the code cannot say
    itself - a non-obvious decision, a tradeoff, a workaround, an external constraint. Keep
    it concise: one tight line beats a paragraph. Never narrate *what* the next line plainly
    does; a comment that restates the code is noise, and it rots into a lie the moment the
    code changes and the comment doesn't.

## Default Posture

Favor correctness over speed and simplicity over cleverness. When in doubt, be explicit
rather than magical. Start simple and let the design emerge; add structure only when you
have proof you need it.
