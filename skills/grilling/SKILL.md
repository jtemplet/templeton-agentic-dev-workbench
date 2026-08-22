---
name: grilling
description: "Interview the user relentlessly about a plan, design, or decision until every branch of the design tree is resolved. Models the open questions as a tree, asks the whole frontier in one numbered round with a recommended answer per question, then recomputes the frontier from the answers. Finds every fact itself and asks the user only for decisions. Use before writing a plan, filing a bead, or starting a build, whenever the user says grill me, interview me, stress-test this, or ask me questions first, and as the alignment step another skill runs before it commits to a design"
---

# Grilling

Interview the user relentlessly until you reach a shared understanding. The most common failure in
software is misalignment: the author thinks the agent understood, then sees what it built. Close
that gap before writing anything.

Map the work as a **design tree**: every decision branches into the decisions that hang off it.

## The frontier

The **frontier** is every decision whose prerequisites are already settled: the questions you can
ask *now* without guessing at answers you have not heard yet.

Ask the whole frontier in one **round**. Number each question and give your recommended answer.
Then wait for the user's answers before the next round.

A question whose answer depends on another question still open in this round belongs to a *later*
round, not this one. Asking it now forces the user to answer twice.

Each round of answers reshapes the tree. Settled decisions push the frontier outward and unblock
the questions that depended on them. Recompute the frontier and ask the next round.

## Round format

This format overrides the house response style's preference for prose, for the duration of the
interview only. A round is genuinely multi-part, and the user scans back to a question by number.

```text
❓ **Q1** - **<question title>**: <question body. May be several paragraphs, and may offer
multiple choices.>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body>

➡️ <your recommended answer>
```

Always recommend an answer. A bare question makes the user do all the work; a recommendation gives
them something to push against, and a one-word "yes" settles the branch.

## Facts are yours, decisions are theirs

Finding **facts** is your job, never the user's. When a frontier question needs a fact from the
environment (the filesystem, the tracker, a running service, an external API), go get it. Dispatch
a subagent for anything that takes real digging. Never ask the user for something you could look
up yourself.

Do not block on it. A running exploration is an unsettled prerequisite, so only the questions
downstream of it wait for the subagent to report. Ask the rest of the frontier now.

The **decisions** are the user's. Put each one to them and wait.

## When the session is done

The session is done when the frontier is empty: every branch of the design tree visited, nothing
left silently assumed.

Do not act on the outcome until the user confirms you have reached a shared understanding.

## Where this fits

Grilling produces alignment, not artifacts. Hand the outcome to whichever skill owns the artifact:

| Next step | Skill or command |
|---|---|
| Write the plan | `/plan-feature` |
| File one bead | `/bead-create` |
| Break it into beads | `/plan-to-beads` |
| Build it | `/build <bead-id>` |
| Record a decision the interview settled | `architecture-decision-record` |
| Sharpen the terms the interview surfaced | `domain-modeling` |

Run `grilling` and `domain-modeling` together when the interview is also teaching you the
project's vocabulary. The interview settles the decisions; `domain-modeling` writes the terms
into `CONTEXT.md` as they crystallize.

---

Adapted from Matt Pocock's `grilling` skill, MIT licensed:
<https://github.com/mattpocock/skills>
