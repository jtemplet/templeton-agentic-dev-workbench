---
name: bead-create
description: "Author one well-crafted bead and file it. Use whenever someone asks to create a bead, file a bead, write a bead, open an issue, file a ticket, log a bug, capture a TODO, or track a piece of work in bd (beads), even if they do not say the word bead. Interviews for only what cannot be inferred, searches the tracker for a duplicate first, grounds every current-state claim in the code on main, picks the type, drafts the body against the canonical structure (Why, How, Done when, Acceptance Criteria, plus Steps to Reproduce for a bug and Success Criteria for an epic), estimates the diff-size band and splits anything too big, then self-audits the draft with the bead-audit rubric until it passes. Presents the bead and waits for confirmation before writing. Creates it in one call with the native design, notes, and acceptance fields populated, labels it, wires its dependencies, reads it back to prove it landed, and exports the tracker silently."
---

# Bead Create

A technique for authoring a single bead that passes `bead-audit` on the day it is filed.

`plan-to-beads` decomposes a written plan into many beads. This skill files one bead from a request, a bug report, a code observation, or a passing thought, and it does the work `plan-to-beads` gets for free from the plan: finding the context, grounding the claims, and asking the author only for what nothing else can supply.

**The standard lives in `bead-audit`, not here.** Before drafting, read `${CLAUDE_PLUGIN_ROOT}/skills/bead-audit/SKILL.md` and use its "Canonical Bead Structure" table for byte-exact headings and its Audit Dimensions for the quality bar. If that path does not resolve, locate it with `Glob: **/skills/bead-audit/SKILL.md`. This skill owns the *workflow*; that skill owns the *rubric*. Do not restate the rubric from memory, because a bead drafted against a remembered standard fails the real one.

## When to Use

- Someone asks to create, file, write, or open a bead, issue, or ticket
- A bug surfaces mid-session and needs to outlive the session
- A follow-up falls out of finished work ("file issues for remaining work" at session close)
- An audit, review, or QA gate produces a finding that deserves tracking
- A single work unit is known and no plan document exists

## When NOT to Use

- A written plan needs decomposing into many beads (use `plan-to-beads`)
- An existing bead needs grading or repair (use `bead-audit`)
- The change is one line and nothing depends on tracking it (commit it; see "Refuse the trivial bead")
- The work is already tracked (the duplicate check in Step 2 is what proves this)

## What a Good Bead Owes Its Reader

The reader is a person or an agent who picks the bead up weeks from now with no memory of this conversation. They must be able to start without asking you anything. Three failures make that impossible, and each has its own fix:

| Failure | What it looks like | The fix |
|---|---|---|
| **Under-specified** | No stakeholder in the Why, no approach in the How, "it works" as the Done when | Interview (Step 1) |
| **Ungrounded** | Names a file that moved, a bug already fixed, an approach the code no longer allows | Ground against main (Step 3) |
| **Oversized** | Two work units in one title, a 900-LOC estimate, "and" doing load-bearing work | Split (Step 5) |

Every step below exists to close one of those three.

## Required Workflow

### Step 0: Confirm the Tracker

```bash
bd list --limit 1
```

If `bd` is missing or the command fails, stop and say so. Do not draft a bead you cannot file.

Note whether the tracker has native structured fields. `bd` does: `design`, `notes`, and `acceptance_criteria` are separate from `description`, and per ADR 0001 (`docs/adr/0001-native-tracker-fields-are-canonical.md`) those fields are canonical. A plain-markdown tracker takes the whole body instead.

### Step 1: Capture the Request and Interview for the Gaps

Start from what the requester said, then find the rest yourself before asking. Read the code, the recent commits, the failing test, the review finding, whatever the request points at. Ask only for what no artifact can answer.

**Ask for these when you cannot infer them:**

| Missing | The question to ask |
|---|---|
| Why | "What breaks, or stays broken, if this is never done? Who is affected?" |
| How | "Is there an approach you have in mind, or should the implementer choose?" |
| Done when | "How would a second person know this is finished without asking you?" |
| Type | Infer it: a defect in existing behavior is a `bug`, new user-facing capability is a `feature`, everything else is a `task`, and an umbrella over child beads is an `epic` |
| Priority | Infer from impact and urgency; state your reasoning at the confirmation gate rather than asking |

Batch the questions into one exchange. Three questions asked together cost the author one interruption; asked separately they cost three.

**Never invent a stakeholder, an approach, or an acceptance criterion.** An invented Why reads exactly like a real one and is worse than an absent one, because nobody knows to question it. When you cannot infer and cannot ask, say what is missing and stop.

**An answer the author gives is not automatically usable.** If they answer the Done when question with "when it works", ask once more for the observable signal. That is the difference between an interview and a transcript.

### Step 2: Search for a Duplicate

```bash
bd search "<two or three distinctive words from the request>"
bd list --status=open --limit 50
```

Search before drafting, not after. A duplicate found after you have written a body wastes the drafting, and a duplicate found after `bd create` pollutes the backlog.

On a near-match, present it and ask which the author wants: update the existing bead, file this as a child of it, or file it separately because the two are genuinely different work. Do not decide alone; "these are the same thing" is a judgment about intent.

### Step 3: Ground Every Current-State Claim

The Why describes the world as it is, so every claim in it can be checked and must be. The Done when and Acceptance Criteria describe a world that does not exist yet, so they cannot be checked and must not be.

Check against **main**, not the working tree. The working tree on a feature branch already contains changes the bead has not asked for yet, and grounding against it files beads that are born satisfied.

```bash
git fetch origin main --quiet
git log -1 --format=%H origin/main
git show origin/main:path/to/file.py | sed -n '1,80p'
grep -rn "<symbol>" --include=<ext> .
```

For each load-bearing claim, record the evidence as a `path:line`, or as what you searched for and did not find. Three outcomes:

- **The claim holds.** Cite it in the Why so the next reader can re-check it cheaply.
- **The claim is false.** Fix the bead before filing it. A file that moved gets the current path; a bug that no longer reproduces gets no bead at all.
- **The claim is already satisfied.** The work is done. Say so, cite the sha, and do not file the bead.

Record the sha you grounded against in the body. A grounding claim without its commit is an assertion.

### Step 4: Choose the Type and Draft the Body

The type decides which sections are required. Take the headings byte-exact from `bead-audit`'s "Canonical Bead Structure" table:

| Type | Required sections |
|---|---|
| `task`, `feature` | Why, How, Done when, Acceptance Criteria, Estimated size |
| `bug` | the above, plus Steps to Reproduce |
| `epic` | Why, How, Done when, Success Criteria (no size estimate; an epic carries no direct diff) |

Operational beads (config, deploy, a manual production change) carry `N/A (operational)` as their size rather than a band.

**Done when and Acceptance Criteria are not duplicates.** Done when states the outcome in the implementer's words. Acceptance Criteria is the checklist QA walks, phrased so each line is pass/fail without interpretation. `bead-audit` carries the worked example; follow it.

Write the title as a single action with no conjunction bundling two work units. "Add user auth middleware" is a title. "Add user auth middleware and migrate the callers" is two beads wearing one.

### Step 5: Estimate the Size, Then Split or Refuse

Estimate files touched and LOC changed, tests and docs included, and place it in a band using `bead-audit`'s Size Audit table. Target is 1 to 5 files and 20 to 300 LOC. Stretch is up to 10 files and 600 LOC and needs a one-sentence justification.

**Split anything above Stretch.** The split line is usually already visible: a conjunction in the title, a How describing two approaches, or acceptance criteria that sort into two disjoint groups. Present the children as separate beads with the dependency between them, and re-run Step 4 on each.

**Refuse the trivial bead.** One file and under 20 LOC with nothing depending on it being trackable is a commit, not a bead. Say so and offer to make the change instead. File it anyway only when the author says the tracking itself is the point (a handoff, an audit trail, a dependency edge another bead needs).

### Step 6: Self-Audit the Draft Until It Passes

Run `bead-audit`'s dimensions against your own draft before showing it to anyone:

1. **Marr audit.** Does the Why name a stakeholder or constraint? Does the How state an approach with a decision in it, not an action? Is every Done when line verifiable by a second person?
2. **Type-specific audit.** Is every section this type requires present and substantive?
3. **Size audit.** Does the band pass, and does a Stretch band carry its justification?
4. **Structure.** Does every section sit under the byte-exact canonical heading, or in its native field?

A draft that fails any check gets rewritten, not annotated. Repeat until it passes. This is the one step that makes the skill's promise real: a bead this skill files passes the audit on day one.

If a gap survives the rewrite because only the author can close it, mark it `[AUTHOR TO COMPLETE: <what is needed>]`, and **do not file the bead**. The placeholder is the needs-human boundary and it must reach a person, never the tracker.

### Step 7: Present and Wait

Show the complete bead and stop:

```markdown
## Proposed bead: <Title>

**Type:** <type>  **Priority:** P<n> (<one-line reasoning>)  **Labels:** <category>
**Parent:** <epic id, or none>  **Depends on:** <ids, or none>
**Grounded against:** origin/main @ <sha>

**Why (Computational):** <text, with path:line evidence>

**How (Algorithmic):** <text>

**Done when (Acceptance):**
- <condition>

**Acceptance Criteria:**
1. Given <precondition>, when <action>, then <observable result>.

**Estimated size:** <files> files, <LOC> LOC, band: <band>

**Self-audit:** Marr pass, type-specific pass, size pass, structure canonical.
```

**Wait for confirmation before any write.** Filing a bead is a change to shared state. Treat any edit the author makes as a re-audit: confirm the edited version still passes Step 6 before creating.

Skip the wait only when the author has already authorized creation in this session ("file beads for the rest of this yourself"), and say in the report that you did.

### Step 8: Create It

One call. `bd create` accepts the native-field flags directly: `--design`, `--notes`, and
`--acceptance` (the flag is `--acceptance`, not `--acceptance-criteria`, which `bd` rejects as an
unknown flag). Setting them at creation keeps the bead from ever existing in a half-written state.

**task or feature:**

```bash
id=$(bd create "<Title>" -p <priority> -t <task|feature> -l "<category>" --silent \
  -d "$(cat <<'EOF'
## Why (Computational)
<L1 content, with the evidence and the grounding sha>

## Estimated size
<files> files, <LOC> LOC, band: <band>. <justification if Stretch>
EOF
)" \
  --design "<L2 content>" \
  --notes "$(cat <<'EOF'
## Done when (Acceptance)
- <criterion>
EOF
)" \
  --acceptance "$(cat <<'EOF'
1. Given <precondition>, when <action>, then <observable result>.
EOF
)"
```

**bug:** the same shape, with Steps to Reproduce in the description body alongside the Why (it has no native slot), carrying numbered steps plus expected against actual behavior.

**epic:** the same shape, with Success Criteria in the body, no size estimate, and no `--acceptance`.

On a tracker whose `create` cannot set a native field, create first and populate it with
`bd update <id> --design ... --notes ... --acceptance ...` immediately after, then treat the
window between the two calls as the hazard Step 8b describes.

Use the quoted `cat <<'EOF'` heredoc, never `printf`. Acceptance criteria routinely contain a literal `%` ("95% of requests return 200"), and `printf` reads it as a format directive and corrupts the text silently.

**A category label is not optional.** Pass one naming what the work touches. Run `bd label list-all` first and reuse an existing category rather than inventing a synonym; a tracker carrying both `evals` and `evaluation` is what label drift looks like.

When a bead needs a person rather than an agent, say so in the body, where it is read. A judgment call, a product or design decision, and a destructive or outward-facing action all belong there. Do not encode that in a label: a label carries no reason, and the next reader cannot tell which of the three applies.

**Wire the relationships** the author confirmed:

```bash
bd update "$id" --parent <epic-id>
bd dep add "$id" <depends-on-id>
```

### Step 8b: Handle a Partial Failure

A single `bd create` either files a complete bead or files nothing, so the body cannot land half-written. The follow-up calls can still fail: a `--parent` reparent or a `bd dep add` that errors leaves a complete bead with a missing edge.

Stop and report the id, the title, the exact error, and the edge that did not land. Re-run only the failed call; never re-run `bd create`, which produces a duplicate title. A bead missing only an edge is worth keeping, so say what is missing rather than deleting it.

If the create itself fails partway on a tracker that needs the two-call fallback above, the bead exists carrying a Why and nothing else. It looks real and fails its own audit, which is worse than no bead. Re-run only the `bd update`. If that cannot be made to work, close the bead with `bd update <id> --status closed` rather than leaving it half-written, and say that you did.

### Step 9: Verify and Report

Read the bead back and prove every section landed where it belongs:

```bash
bd show "$id"
```

Confirm `design`, `notes`, and `acceptance_criteria` are populated, not empty. A create that reported success and left the native fields blank is the exact defect ADR 0001 exists to prevent.

Then export, silently:

```bash
bd export -o .beads/issues.jsonl
```

The author never handles tracker plumbing. Do not ask them to run the export and do not report that it succeeded. Report it only if it fails, because then the bead exists on one machine only.

Close with the id, the title, and the claim command:

```markdown
Filed `<id>`: <Title> (<type>, P<n>, labels: <labels>)
Claim it with: bd update <id> --claim
```

## Critical Rules

**Always:**

- Read `bead-audit`'s "Canonical Bead Structure" before drafting, and use its headings byte-exact
- Search the tracker for a duplicate before drafting
- Ground every current-state claim against `origin/main` and record the sha
- Infer what the artifacts can answer; ask the author only for what they cannot
- Batch the interview questions into one exchange
- Self-audit the draft and rewrite until it passes, before showing it to anyone
- Present the complete bead and wait for confirmation before writing to the tracker
- Write each section to its canonical destination in the `bd create` call itself: `--design`, `--notes`, and `--acceptance` for the sections with native fields, `-d` only for the sections without one
- Pass a category label, reusing an existing category from `bd label list-all`
- Read the bead back after creating it and confirm the native fields are populated
- Run `bd export -o .beads/issues.jsonl` yourself, and mention it only on failure

**Never:**

- Invent a stakeholder, an approach, or an acceptance criterion. Ask, or mark `[AUTHOR TO COMPLETE]` and do not file
- File a bead whose draft still carries an `[AUTHOR TO COMPLETE]` placeholder
- File a bead in the Too-big or Hard-ceiling band. Split it
- File a Trivial-band bead when nothing depends on it being tracked. Make the change instead
- Ground against the working tree; on a feature branch it already contains the change the bead is asking for
- Treat an unmet acceptance criterion as a grounding failure. Unmet criteria are the bead's reason to exist
- Re-run `bd create` for a bead whose create already succeeded
- Put How, Done when, or Acceptance Criteria in the description body when the tracker has native fields for them
- Ask the author to run `bd export -o .beads/issues.jsonl` or to sync the tracker
- Use `bd edit`; it opens `$EDITOR` and blocks

## Quality Checklist

Before reporting completion, verify:

- [ ] The tracker was reachable and its native-field support was determined
- [ ] A duplicate search ran before drafting, and any near-match was presented to the author
- [ ] Every current-state claim in the Why is grounded against `origin/main`, with evidence and a sha
- [ ] The type is declared and every section that type requires is present and substantive
- [ ] Done when and Acceptance Criteria sit at different altitudes; neither restates the other
- [ ] The size estimate names files, LOC, and a band, and a Stretch band carries its justification
- [ ] The title names exactly one work unit
- [ ] The draft was self-audited against `bead-audit` and passes on content, structure, and size
- [ ] No `[AUTHOR TO COMPLETE]` placeholder reached the tracker
- [ ] The author confirmed before anything was written, or had already authorized it and the report says so
- [ ] `design`, `notes`, and `acceptance_criteria` were verified populated with `bd show`
- [ ] A category label is set, reused from the existing label set, and any need for a person is stated in the body
- [ ] Parent and dependency edges the author confirmed are wired
- [ ] `bd export -o .beads/issues.jsonl` ran, and was reported only if it failed
