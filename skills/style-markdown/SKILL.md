---
name: style-markdown
description: Writes and reviews Markdown in the house style. Use when the document is the deliverable - a skill, agent, command, doc page, ADR, plan, or README. Enforces Simplified Technical English, one meaning per word, no jargon, sentences under 30 words, and a ten-year-old reading level, because most of these documents are read and executed by an agent that cannot ask what you meant
---

# Templeton Markdown Style

Write every document so a ten-year-old can follow it. Keep technical names exact.

Most of these documents are instructions an agent executes. A person who hits an unclear
sentence asks what it means. An agent does not. It picks a reading and acts on it. The wrong
reading shows up later as behavior nobody asked for.

## When to Use / When NOT to Use

Use this skill when the document is the deliverable: a skill, agent, command, `docs/` page,
ADR, plan, or `README.md`.

Do not use it when:

- The Markdown is incidental, such as a changelog line beside a code change.
- Formatting is the question. Run `rumdl`.
- You are writing a reply to the user, not a file. That is `house-response-style`.

## Sentences: Simplified Technical English, specified in ASD-STE100

Simplified Technical English is a controlled-English standard. Use its writing rules, never its
licensed dictionary, which you cannot open. The ten rules below are the whole of what to apply.
Do not add a rule you half-remember from the standard itself.

They govern wording, not content. They apply to every sentence you write in a document.

1. **One word for one thing.** Pick a word for something and use only that word. A second word
   reads as a second thing. If you call it a bead in one line, do not call it a ticket later.

2. **Thirty words per sentence, maximum.** Twenty when the sentence tells the reader to do
   something. Long sentences are two statements joined. Cut them at "which", "so", "but",
   "because", ", meaning", and ", making".

3. **Name the thing, not a picture of it.** A reader cannot unpack a metaphor. Every word on the
   right below names a real mechanism.

   | Do not write | Write |
   |---|---|
   | wire it up | add the hook to `settings.json` |
   | surface it | show it |
   | handle it | retry it, or write it to the log and stop |
   | leverage | use |
   | the row, the entry, the item | the table row, the bead, the line in the report |
   | it lands in `main` | it merges into `main` |

4. **No jargon.** If a word needs a gloss, write the gloss instead. One exception: an exact
   technical name stays as it is, because the reader has to type or search for it. Keep
   `TADW_STYLE_CORE`, `git rebase`, and `skills/quality-gates/SKILL.md` verbatim.

5. **Define a term in the sentence that uses it.** Do this even for terms an engineer reads
   fluently. Write "the script is idempotent, meaning running it twice does what running it once
   does".

6. **Active voice, and the imperative for steps.** Write "the deploy job clears the cache", not
   "the cache is cleared".

7. **Positive form, and the condition before the instruction.** Write "Run this only when the
   backup is less than a day old".

8. **Plain words.** Write "that is" not `i.e.`, "for example" not `e.g.`, "and so on" not `etc.`
   Never stack more than three nouns. Write "the timeout for the connection pool".

9. **American spelling.** Write color, behavior, initialize, canceled, analyze. A name you do not
   own stays as it is, so an API field called `colour` keeps its spelling.

10. **No em-dash and no en-dash.** Use a comma, semicolon, colon, parentheses, or a new sentence.
    For a missing value use a plain hyphen. Quoted text and code samples keep their punctuation.

## Documents

These rules are about the whole document, not the sentence.

11. **The first paragraph says what the document decides, and for whom.** Never open by
    describing the document. "This document describes the quality gates" tells the reader
    nothing.

12. **State the rule before the reason.** A reader who stops early still has the instruction.

13. **Name the case you are excluding.** If you do not, an agent guesses. Write "Run the export
    after any command that creates, updates, or closes a bead. A read-only command such as
    `bd show` changes nothing, so it needs no export."

14. **A number is a claim. Derive it, or leave it out.** Counts and totals go stale in silence,
    and a stale number looks exactly like a fresh one. Write the command that produces it beside
    it.

15. **One job per document. Inline the decision, link the reference.** Inline what the reader
    needs to act. Link what they need to check.

16. **Mark a machine-read region with paired HTML comments.** A script must never find a region
    by its heading, because any edit to that heading breaks the script without a word. Use
    `<!-- name:start -->` and `<!-- name:end -->`.

17. **Match the shape to the content.** Use a table when every item has the same fields. Use a
    list when items are parallel but have no fields. Otherwise write sentences. A list of one
    item is a sentence. A table column that repeats one value carries nothing.

18. **A backticked path names a file. A link sends the reader to it.** Write
    `hooks/preamble.js` to name it. Write [docs/HOOKS.md](../../docs/HOOKS.md) to send someone
    there. Different checks read the two forms.

19. **Wrap prose at 100 columns.** Never reflow a file you came to patch. Reflowing turns a
    one-line change into a paragraph-sized diff and hides the edit. Tables, fenced code, and
    frontmatter are exempt.

20. **A frontmatter `description` is a trigger, not a summary.** The runtime reads it to decide
    whether to load the component. Write it in the third person and name the conditions that
    should fire it.

21. **Say what is true now.** Never ship a `TODO` or a `TBD`. Write an open question and name who
    owes the answer.

## What this skill does not repeat

Three layers already run underneath. Do not restate them.

- **rumdl** checks headings, fence tags, list markers, tables, blank lines, and links. Run
  `rumdl check .`. Never write prose that repeats a rumdl rule.
- **`hooks/style-core.md`** carries the coding principles. It loads in every session and every
  subagent.
- **`house-response-style`** carries these same sentence rules for replies to the user. It loads
  in parent sessions only.

**Load `/response-style` when you write Markdown inside a subagent.** A subagent never receives
`house-response-style`, and `/tadw:build` writes documents inside subagents.

## Checklist

- [ ] Every sentence is under 30 words, and under 20 when it gives an instruction.
- [ ] A ten-year-old could follow every sentence. Technical names are exact.
- [ ] Each thing has one name, used every time.
- [ ] No metaphors, no jargon, no `i.e.`, no `e.g.`
- [ ] No em-dash and no en-dash.
- [ ] The first paragraph says what the document decides.
- [ ] Every rule comes before its reason.
- [ ] Every number names the command that produces it.
- [ ] Excluded cases are stated, not implied.
- [ ] Machine-read regions use paired HTML comments, not headings.
- [ ] Prose wraps at 100 columns, and no untouched paragraph was reflowed.
- [ ] `rumdl check` on the file exits 0.

## Anti-Patterns

| Anti-pattern | Why it hurts | Instead |
|---|---|---|
| "This document describes..." | Wastes the most-read paragraph | Say what it decides |
| A 60-word sentence | The reader loses the subject | Two sentences |
| "the row", "the entry" | Names four possible things | Name the one you mean |
| "wire it up", "surface it" | The reader cannot unpack it | Name the mechanism |
| A count written from memory | Looks identical when stale | Derive it |
| A heading used as a script anchor | Renaming it breaks the script silently | Paired HTML comments |
| A link labeled "here" | Meaningless out of context | Label it with its target |
| A list of one item | Structure with nothing to structure | A sentence |
| `TODO` in a shipped document | Looks like an oversight | An open question with an owner |
| Reflowing a file you only patched | Hides the real change | Wrap what you wrote |

## Escape Hatches

- A project's own `AGENTS.md` or `CLAUDE.md` outranks this skill.
- Text you do not own keeps its exact form. A quoted error, an external field name, or a pasted
  log stays verbatim.
