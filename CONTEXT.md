# Templeton Agentic Dev Workbench

A Claude Code plugin: a workbench of skills, agents, and commands for software development.
Its domain is the tooling itself, so the vocabulary below names the parts of the plugin, the
work it tracks, and the checks it runs. It does not name the languages the plugin reviews.

Every term here is already in use somewhere in this repository. Nothing was invented for the
glossary. Four collisions remain unresolved and are listed at the bottom.

## Language

### Components

**Component**:
Any one skill, agent, or command. Claude Code discovers all three from their directory layout,
so `.claude-plugin/plugin.json` lists none of them.

**Skill**:
The technique itself, written as `skills/<name>/SKILL.md`. It says how to do one kind of work.
_Avoid_: prompt, playbook, recipe

**Agent**:
A workflow definition in `agents/<name>.md` that references skills and runs in its own context
window, which is why it cannot see the conversation that launched it.
_Avoid_: persona, bot

**Command**:
A shortcut in `commands/<name>.md` that loads an agent or a skill. When a command and a skill
share a name, both resolve to `tadw:<name>` and the command wins.
_Avoid_: alias, slash command

**Registration**:
Naming a component in the AGENTS.md name list and the README description table. These are the
only two places; `plugin.json` registers nothing.

**Namespace**:
The `name` field of `.claude-plugin/plugin.json`, currently `tadw`. It prefixes every
invocation path, so changing it is a breaking change.
_Avoid_: prefix, which here means the `tadw-` on a bead id

**Orphan**:
A skill that no agent and no command references. Four are accepted as reachable by direct
invocation.

**Hook**:
A script Claude Code runs at a lifecycle event. A plugin hook belongs to this plugin and is
wired in `plugin.json`; a portable hook belongs to whatever repository installs it, and lives
in `scripts/`.

**Payload**:
One chunk of the text a `SessionStart` hook injects. A 10,000-character cap per hook output is
why the style core ships as several manifest entries rather than one.

### Style

**House style**:
This repository's rules for writing code and for writing to the user. A `SessionStart` hook
injects them into every session, coding or not.

**Style core**:
The universal, language-agnostic coding rules in `hooks/style-core.md`. It governs code.
_Avoid_: house rules

**Response style**:
The rules for writing responses to the user, in `skills/house-response-style`. It governs
prose, never code, which is what separates it from the style core.

**TRUE code**:
Transparent, Reasonable, Usable, Exemplary. The four properties the style core asks of every
unit of code.

**Delta**:
What a `style-*` skill adds on top of the style core for one language. A delta never repeats
or overrides the core.

### Work

**Bead**:
One unit of trackable work in bd. Every unit of work is a bead, and no other list is allowed.
`/build` reads the bead, never a separate document.
_Avoid_: issue, ticket, task, card, TODO, and bare "spec" for a bead's content

**Tracker**:
The bd (beads) database that holds every bead.
_Avoid_: backlog, which means only the non-closed beads

**Export**:
`.beads/issues.jsonl`, a passive text dump of the tracker. Never a source of truth, never
hand-edited, and never a person's responsibility.

**Native field**:
One of bd's first-class `design`, `notes`, and `acceptance_criteria` columns. Content belongs
in these rather than in the description body, per
[ADR 0001](docs/adr/0001-native-tracker-fields-are-canonical.md).

**Plan**:
A document in `docs/plans/` that describes a feature before it becomes beads. It fills the
canonical template that `write-plan` owns and `plan-review` grades.

**Criterion**:
One line of a bead's `acceptance_criteria`. `/build` writes a test per criterion, and
`/verify-acceptance` grades each one separately.

**Marr level**:
Which of three questions a bead section answers. Level 1 Computational is what problem this
solves and why it matters. Level 2 Algorithmic is the approach. Level 3 Implementation is the
exact files and code shapes, and may be left to the implementer.

**Size band**:
The estimated diff size of a bead. A bead whose band is too large gets split before it is
filed.

**Label**:
A string attached to a bead. Labels carry four unrelated jobs: triage state, area, lifecycle
(`implemented`, `reviewed`, `accepted`), and provenance.

### Checking

**Audit**:
Checking whether a bead can be built without mistakes. It asks whether the substance, the
structure, and the grounding are sound. The word is reserved for this discipline, which is why
the generic reviews are named `/ux-review`, `/ux-review-ios`, and `/aso-review`.
_Avoid_: audit for any ordinary thorough check; write review or check

**Refine**:
Checking whether a bead deserves to exist, by product value. It returns one of seven verdicts,
from keep to kill.

**Ground**:
Checking that a document's claims are still true of the code on `main` as it is today. A
well-written bead whose target code moved is stale, not under-specified.

**Verify**:
Grading finished work against its bead's acceptance criteria and the gate results. It cites
those results rather than re-deriving them.

**Review**:
Reading code for defects or for conventions. `/fresh-eyes-cr` hunts bugs; `/code-review` checks
conventions.

**Gate**:
A check that can refuse to let work proceed. The same word covers all three scales it appears
at: one shell command, a named list of commands such as the ship gate, and a pass-or-fail step
inside a larger skill.

**Size band**:
A bead's estimated diff size. Always written as the compound where a quality band is also in
play.
_Avoid_: bare "band"

**Quality band**:
A score range from Poor to Excellent that `bead-audit` reports. It refines a verdict and can
never outrank one.
_Avoid_: bare "band", grade, tier

**Verdict**:
The single categorical result a skill returns, such as PASS, Ready, or NOT ACCEPTED. A verdict
is never a score.

**Changed set**:
The files a change touches, resolved from a git base by a bundled script. Never classified by
eye.

**Hygiene**:
The gate that counts leftovers in the changed set: dead code, stray debugging output, and
committed scratch files.

### Landing

**Land**:
Merge a finished branch onto `main` locally and delete the branch. No pull request is involved.

**Ship**:
The whole act of landing, plus closing the bead and pushing `main`. The `ship` skill does this
unattended.

**Publish**:
Number and tag a state that consumers already have. The marketplace follows this repository's
default branch, so a push to `main` has already distributed the change.
_Avoid_: release as a verb, deploy

**Release**:
A `vX.Y.Z` tag and the CHANGELOG section that names it. It tells a person which published state
they are running; it does not gate distribution.

**Machine line**:
The single parseable last line of a skill's report, such as `SHIP_DONE <sha>`. A wrapper reads
that line and nothing else, so no prose may follow it.

**Occupant**:
A live process standing in a worktree that is about to be removed. An occupant is reported and
never killed, and never blocks the removal.

### Documents

**ADR**:
A record in `docs/adr/` of a decision that would cost more than a day to reverse and that
somebody would otherwise argue again. Thirteen files read this directory.

**Leaf document**:
The one document in `docs/products/` that names a single product feature. Only a leaf can say
how to reach the feature it names.

**Drive block**:
The "How to drive this" section every leaf document carries. It gives the steps that reach the
feature in the running product.

## Resolved collisions

Four terms carried more than one meaning. Each was decided on 2026-09-01, and the decision is
recorded here so it is not re-argued.

**gate**: kept as one concept at three scales. A gate is a check that can refuse to let work
proceed, whether it is a command, a list, or a step. No rename. 892 uses stand as written.

**band**: split into `size band` and `quality band`. The compound is required in the two live
documents that carry both senses, `skills/bead-audit/SKILL.md` and `docs/ROUTING.md`. The JSON
keys `band` and `band_ceiling` are a machine contract and keep their names. Filed plans under
`docs/plans/` are a historical record and were left alone.

**spec**: retired for a bead's content, which is now called the bead. `spec/` and `_spec.rb`
stay as they are, because that is Ruby's test directory and context always settles it. The probe
spec in `skills/quality-gates/SKILL.md` keeps its compound name.

**audit**: reserved for the bead-audit discipline. `/ux-audit`, `/ux-audit-ios`, and
`/aso-audit` were renamed to `/ux-review`, `/ux-review-ios`, and `/aso-review`, and the MECE
audit inside `plan-review` became the MECE check. The report output directories
`docs/ux-audits/` and `docs/aso-audits/` were deliberately left alone, so that a consumer's
existing reports do not scatter across two paths.
