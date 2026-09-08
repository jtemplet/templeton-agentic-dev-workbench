# Style Routing

Load the style skill that owns the file you are about to write or review, plus whatever stacks on
top of it. This file decides which, for anyone implementing, simplifying, or reviewing code here.

Three documents route through this file and keep no copy of the table:
`skills/code-simplify/SKILL.md`, `skills/feature-development/SKILL.md`, and
`agents/software-engineer.md`. This file wins wherever one of those three disagrees with it.
`AGENTS.md` outranks this file, as it outranks every page under `docs/`; its task table names the
same skills for a human choosing a command, and this file is the dispatch the three documents
above execute. Confirm all three still point here:

```bash
grep -l style-routing \
  skills/code-simplify/SKILL.md \
  skills/feature-development/SKILL.md \
  agents/software-engineer.md
```

## The extension table

Match on the extensions you are about to write or review, and load each matching skill with the
Skill tool.

| Extension | Style skill |
|---|---|
| `.py` | `style-python` |
| `.rb`, `.erb`, `.rake` | `style-rails`, or `style-fizzy` in the Fizzy codebase |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.vue` | `style-frontend` |
| `.swift` | `style-swift` |
| `.go` | `style-go` |
| `.md`, `.markdown` | `style-markdown`, when the document is the deliverable |

For an unlisted language, say so, name what you will follow instead (the injected style core plus
the conventions you read in the repository), and continue.

## What stacks on top

Load these in addition to the extension match, when they apply.

- **`style-testing`** for any test file, in any language. It is language-agnostic and applies to
  every framework. Match on `test_*.py`, `*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`,
  `*.spec.tsx`, `*_spec.rb`, `*_test.rb`, `*Tests.swift`, `*_test.go`, or anything under a
  `tests/`, `test/`, `spec/`, or `__tests__/` directory.
- **`style-rspec`** on top of `style-testing`, only when the suite is RSpec.
- **A project-local style skill**, when one exists and covers what you are about to write. This is
  the difference between correct-for-the-language and correct-for-this-repo. Check the available
  skill list for one naming this project or this surface, and load it. `style-fizzy` for the Fizzy
  codebase and `jbuilder-style` for Loan Labs factory API views are examples of the kind. When a
  local skill contradicts the general language skill, the local skill wins.

## When Markdown is the deliverable

The `.md` row fires when what the document says is the point of the work: a skill, an agent, a
command, a `docs/` page, an ADR, or a plan. It does not fire when you add a line to a changelog or
a release note beside a code change. In a repository whose product is documentation, this row fires
on most work, and that is the intent.
