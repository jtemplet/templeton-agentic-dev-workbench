# 0002. The quality-gates orchestrator fans out to blocking subagents

**Date:** 2026-08-21
**Status:** Accepted

## Context

`docs/plans/quality-gates-agent-refactor.md` proposes replacing the single session that runs
`/quality-gates` today with `agents/quality-gates.md`, an orchestrator that resolves the scope once
and then dispatches four concurrent lanes: documentation, backend unit tests, frontend tests, and
integration tests.

The plan's Open Questions 0 through 3 block milestones 2 through 4. This ADR answers all four. It
also records what the Open Question 0 spike measured, because three of the four answers turn on
those measurements rather than on preference.

**The capability had no precedent here.** None of the twelve files in `agents/` carries a Task or
Agent tool, and none dispatches a subagent. Milestones 2 through 4 were speculative until the spike
returned an answer.

## The Open Question 0 spike

The spike installed throwaway agents into the live plugin cache
(`~/.claude/plugins/cache/templeton-agentic-marketplace/tadw/2.9.1/agents/`), not into a checkout,
so each was a real plugin agent addressed as `tadw:<name>`. Each was invoked from a headless
`claude -p` run with `--output-format stream-json`, and the transcript was read for nested tool
calls. Claude Code 2.1.239. Seven runs, six agents. All spike agents were deleted afterward; the
cache holds the same twelve agents it held before.

The transcript distinguishes nesting by `parent_tool_use_id`: a tool call carrying the spike agent's
own `tool_use` id as its parent is a dispatch made *by the spike agent*, not by the session that
invoked it.

### Finding 1: a plugin agent can dispatch a subagent and return its result

`tadw:spike-agent`, declared `tools: ["Agent"]`, called `Agent` with its own dispatch as the parent,
received the subagent's return, and emitted its contract line `SPIKE_RESULT PINEAPPLE`. The answer
to Open Question 0 is **yes**. The sequential fallback is not needed, and plan criterion 9 stays a
speedup check rather than degrading to a no-regression check.

### Finding 2: `Task` and `Agent` are the same tool, and its name is `Agent`

An agent declared `tools: ["Task"]` and an agent declared `tools: ["Agent"]` both reported the
identical inventory, `SPIKE_TOOLS Agent`. `Task` is accepted in the frontmatter and resolves to the
`Agent` tool. Neither agent received any other tool, so the array was honored rather than ignored.

### Finding 3: an unrecognized tool name refuses the dispatch, it does not degrade

An agent declared `tools: ["NotARealTool"]` never ran. The dispatch returned:

> Agent 'tadw:spike-tools-bogus' would be spawned with zero tools - refusing. Its tools list
> resolved to nothing: unrecognized [NotARealTool]. Fix the agent's tools frontmatter or pass a
> different subagent_type.

This is what makes Finding 2 trustworthy: an unrecognized name is not silently dropped, so the
`["Task"]` agent's single-tool inventory was a real resolution and not a fallback to everything.

### Finding 4: the fan-out silently loses its lanes unless every dispatch blocks

This is the spike's most consequential result, and it is a defect the plan did not anticipate.

`tadw:spike-fanout` was told to dispatch four subagents concurrently, wait for all four, and emit
`SPIKE_FANOUT ALPHA BRAVO CHARLIE DELTA`. It dispatched all four in one message. All four subagents
ran and returned their words. The orchestrating agent then **ended its turn** with the text "Four
subagents dispatched and running concurrently. Waiting for all four to complete before returning the
final result." The aggregate line was never emitted. Every lane succeeded and the report was lost.

`tadw:spike-fanout-block` was identical except that it was instructed to pass
`run_in_background: false` on each call. It dispatched the same four in one message, every dispatch
carried `run_in_background: false` in the transcript, and it emitted
`SPIKE_FANOUT ALPHA BRAVO CHARLIE DELTA`.

Two conclusions:

- **The default dispatch is asynchronous.** The tool returns "Async agent launched successfully. The
  agent is working in the background," and the caller may end its turn before the result arrives.
  Instructing the agent in prose to wait does not prevent this; both fan-out agents carried the same
  "wait for all four" instruction and only the one that set the flag collected.
- **Blocking does not cost concurrency.** Four blocking dispatches issued in one message still ran
  concurrently. The flag decides whether the caller waits, not whether the lanes overlap.

## Question 0: can an agent in this plugin dispatch a subagent?

### Options Considered

**Option A: four concurrent subagents.** The plan's design.

- **Pros:** the four lanes overlap, which is the entire point of the refactor. Proven to work.
- **Cons:** requires `run_in_background: false` on every dispatch, and Finding 4 shows the failure
  mode is silent: a run that omits the flag reports nothing rather than reporting an error.

**Option B: one agent running four lanes sequentially in its own context.** The plan's written
fallback.

- **Pros:** no dependency on subagent dispatch at all. Keeps the lane contract, the step-ownership
  table, and the aggregation rule.
- **Cons:** drops the concurrency, which is the refactor's stated motivation, and keeps every gate's
  raw output in one context, which is the second stated motivation.

### Decision

**Option A. The orchestrator dispatches one concurrent subagent per lane, and every dispatch
passes `run_in_background: false`.**

`agents/quality-gates-orchestrator.md` (the name Question 1 selects) declares
`tools: ["Agent", ...]`, spelled `Agent` and not `Task`, since
Finding 2 shows both resolve to a tool named `Agent` and the frontmatter should name what the agent
actually receives.

The fallback in Option B is not taken. Plan criterion 9 stays a speedup check.

The lane count is left to Question 3, which reduces it from four to three. The blocking rule does
not depend on the count: every dispatch blocks, however many there are.

Milestone 2 must state the blocking requirement as a rule of the orchestrator, not as an
implementation note, and milestone 2's Done-when should require the transcript to show
`run_in_background: false` on every dispatch. Finding 4 is a silent-loss defect: without that
check, a regression looks like a short report rather than a failure.

## Question 1: does `commands/quality-gates.md` collide with `agents/quality-gates.md`?

`AGENTS.md:262-266` rules only on command-versus-skill, and `commands/quality-gates.md:6-10`
already documents the dodge it takes for the skill: it reads
`${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/SKILL.md` by path rather than invoking
`Skill(quality-gates)`, because the command wins the shared `tadw:quality-gates` name.

### Options Considered

**Option A: have the command read the agent by path**, extending the dodge it already uses.

- **Pros:** one consistent pattern in one file. No new name to register.
- **Cons:** reading an agent file by path is not dispatching it. An agent is dispatched by name
  through the `Agent` tool, and the spike confirms the tool takes a `subagent_type` (the transcript
  shows `subagent_type='tadw:spike-agent'`). A path read would inline the orchestrator's prompt into
  the calling session, which is exactly the single-context shape this refactor removes. The dodge
  works for a skill because a skill *is* a document to read; it does not transfer.
- **Fatal:** this option cannot produce the fan-out at all.

**Option B: name the agent `quality-gates-orchestrator`**, so no collision is possible.

- **Pros:** the command keeps `tadw:quality-gates`, the agent gets a name nothing else claims, and
  the command dispatches it by name through the `Agent` tool, which is how agents are meant to be
  reached. The name also states what the component does, which `quality-gates` alone does not now
  that a skill and a command share that phrase.
- **Cons:** a third name in the `quality-gates` family, and one more entry in the registration lists
  in `AGENTS.md` and `README.md`.

### Decision

**Option B. The agent is `agents/quality-gates-orchestrator.md`, addressed as
`tadw:quality-gates-orchestrator`.** `commands/quality-gates.md` dispatches it by that name.

Option A is rejected on a fact the spike established rather than on taste: dispatch happens by
`subagent_type`, so an agent reached by reading its file is not dispatched and the four lanes never
fan out. The command-reads-the-skill dodge solves a different problem and does not generalize to
agents.

The plan and its milestone table name the file `agents/quality-gates.md` throughout. Milestone 2
must use `agents/quality-gates-orchestrator.md` instead, and milestone 4's registration lists and
the Rollback line at the plan's `:133-136` name the same file.

## Question 2: how does bead labeling survive an agent dispatch?

`.claude/settings.json:29` wires `.claude/scripts/label_bead_on_skill_invocation.sh` to `PreToolUse`
with matcher `Skill`. The hook reads the skill name from `.tool_input.skill`
(`label_bead_on_skill_invocation.sh:173`) and exits silently when that field is empty. An `Agent`
tool call carries `subagent_type`, not `skill`, so the matcher never fires and the hook would exit
before reading anything.

The hook maps `quality-gates|tadw:quality-gates` to `label="qa-d"` in **inject** mode
(`:202-204`), gated on the overall verdict being PASS. Inject mode emits an instruction naming the
bead, the gate, and the command, and the model applies the label at the end of the turn.

### Options Considered

**Option A: add a `PreToolUse` matcher for `Agent`.**

- **Pros:** fires at dispatch time, which is when the current hook fires.
- **Cons:** matcher `Agent` fires on *every* agent dispatch in every project the hook is installed
  in, and the hook would have to re-derive which skill an arbitrary agent stands for. The hook's own
  comment at `:176-183` warns that the map holds skill names and never command names, precisely
  because the payload field is `tool_input.skill`; keying it on `subagent_type` adds a second,
  differently-shaped namespace to the same map. The distribution copy at
  `scripts/label_bead_on_skill_invocation.sh` would need the same change, and the two copies have
  already diverged once.

**Option B: have the orchestrator invoke the skill through the `Skill` tool**, so the existing
matcher fires.

- **Pros:** no hook change at all. `tadw:quality-gates` reaches `tool_input.skill` under a name the
  map already carries.
- **Cons:** the command wins the `tadw:quality-gates` namespace, so `Skill(quality-gates)` returns
  `commands/quality-gates.md` and never reaches the skill. This is the exact failure
  `commands/quality-gates.md:8-10` already documents. The orchestrator would be labeling a bead by
  invoking a command that tells it to read a file. It would also fire once per lane if each lane
  invoked the skill, producing repeat labeling attempts.

**Option C: label from the `Stop` event.**

- **Pros:** `Stop` already runs this hook (`:4-7`), fires after the work rather than before it, and
  is blind to which tool produced the run. It therefore does not care that dispatch replaced skill
  invocation. The hook's own header (`:9-11`) records that only `Stop` fires after the work.
- **Cons:** `Stop` currently resolves markers that `PreToolUse` dropped, so it has no path that
  starts from nothing. Something must still tell `Stop` that a quality-gates run happened.

### Decision

**Option C, taken through the artifact the skill already writes.** Labeling moves to the `Stop`
event, and the trigger is `quality-gates-report.json`.

The skill already writes a JSON artifact carrying the verdict verbatim, inside the git directory, on
every run (`commands/quality-gates.md:39`, item 9 of the same file's numbered list). That artifact is
exactly what **gate** mode is built to read: gate mode drops a pending marker at `PreToolUse` and at
`Stop` applies the label only when the report is newer than the marker and clears the gate
(`:16-20`). `/quality-gates` uses inject mode today only because the hook's author read it as
"report-only prose" with no artifact (`:27-29`), and that comment is now stale: the artifact exists,
it is machine-readable, and it carries the verdict.

Reading the verdict from `quality-gates-report.json` converts `qa-d` from inject mode, which the hook
itself calls "weaker than gate, and honest about being weaker" (`:36-37`), into a deterministic check
with no model involvement. That is a strict improvement independent of this refactor, and it is what
makes the dispatch irrelevant: `Stop` never asks which tool ran.

Option A is rejected for widening a `PreToolUse` matcher to every agent dispatch in every installed
project to solve one skill's problem. Option B is rejected because it cannot work: the namespace
collision it relies on defeating is the one `commands/quality-gates.md` already documents as
undefeatable from the `Skill` tool.

Milestone 4 must therefore change both copies of the hook, and the change is larger than the
"matcher" edit the plan's file list implies: `quality-gates|tadw:quality-gates` moves from inject
mode to gate mode, and gate mode's report reader gains a `quality-gates-report.json` path beside its
existing `.gstack/qa-reports/*.md` path. Plan criterion 7 should be restated to require that a
`/quality-gates` run still labels its bead `qa-d` on a PASS verdict and does not label it on any
other verdict, without naming the injected instruction, since the injected instruction is what this
decision removes.

## Question 3: does the documentation lane report drift, or fix it?

`commands/quality-gates.md:39` states "Report-only. It never fixes, formats, or edits anything in the
working tree." `skills/quality-gates/SKILL.md:695` states it as a **Never**: "Fix, format, or edit
anything in the working tree (this skill is report-only; its report is the deliverable...)".

### Options Considered

**Option A: report-only, unchanged.**

- **Pros:** two shipped guarantees stay true. The gate stays safe to run at any point, including on a
  dirty tree, mid-review, or from `.githooks/pre-push`, because it cannot alter what is being graded.
  A gate that edits the tree it is grading can make its own next run pass.
- **Cons:** documentation drift is reported and then fixed by hand.

**Option B: the documentation lane fixes drift.**

- **Pros:** the most mechanical finding the gate produces would stop needing a human.
- **Cons:** reverses a guarantee stated in two shipped files, one of them as a **Never**. It also
  gives one of four concurrent lanes write access to the working tree while the other three are
  grading that tree, which is a race the plan has no design for.

### Decision

**Option A. Report-only, unchanged.** Both guarantees stand, and the plan's Out-of-scope line at
`:130-131` is confirmed rather than revisited.

The concurrency argument is what settles it. Question 0 resolved to a real fan-out, so the four lanes
now genuinely overlap. A documentation lane that edits files while the test lane and the coverage
lane read the same tree would make the run's result depend on lane timing. Report-only is not merely
the incumbent guarantee here; it is the only shape that is safe under the concurrency this ADR just
adopted.

### The consequence the plan pre-commits to

The plan states it at `:56-58` and this ADR discharges it: **Gate 5 folds into the orchestrator and
the fan-out becomes three lanes.**

Gate 5 is one scripted command (`skills/quality-gates/SKILL.md:295-300`, a single
`check_doc_paths.py` invocation with the instruction "Do not hand-roll this check"). The
orchestrator's own test, which keeps Gates 3, 4, 6, and 7 in-process, is that a gate which is one
scripted command earns no lane. With Question 3 resolved to report-only, Gate 5 has no remaining
work beyond running that command, so it fails the same test and moves in-process.

Milestone 2 builds three lane contracts, not four: backend unit tests, frontend tests, and
integration tests. Milestones 2 and 3, the lane table, the step-ownership table for Step 4, and every
plan sentence reading "four subagents" or "four lanes" must be restated to three. Plan criterion 3
still holds for the frontend lane. The plan's Summary at `:75-79` names the documentation lane first
among the four and needs the same correction.

### The Gate 2 ownership rule this leaves behind

The `docs` lane owned two things, not one. The plan's lane table at `:174` gives it "Gate 5
(documentation freshness), **and Gate 2 for the `docs` surface**, which is a SKIP carrying its reason
(`route_qa.py:91`)". Deleting the lane rehomes Gate 5 and would orphan that second row, which is
exactly the defect class the plan's second and third review passes were spent closing: a partition
complete over surfaces but not over rows.

**The orchestrator owns Gate 2 for the `docs` surface**, on the same terms the lane held it: a SKIP
row carrying the router's reason from `route_qa.py:91`.

That gives the orchestrator every Gate 2 row no remaining lane claims, and the full Gate 2 partition
after this ADR reads:

| Gate 2 for | Owner |
|---|---|
| `cli`, `library`, `prompt-assets`, `infra`, `unknown` | `backend-unit` lane |
| `http-api`, both unit and end to end | `integration` lane |
| `docs` (a SKIP carrying its reason) | Orchestrator |
| `mobile-ui` (a handoff surface, so no graded Gate 2 row of its own) | Orchestrator, as the `Handoff: mobile-ui` row it already owned (plan `:188-189`) |
| `browser-ui` (a handoff surface, so no graded Gate 2 row of its own) | `frontend` lane, as the `Handoff: browser-ui` row it already owned (plan `:176`) |
| Gate 2's own HANDOFF status, when every routed surface is a handoff (`SKILL.md:180-181`) | Orchestrator, unchanged |

All nine surfaces `route_qa.py:83-93` defines still have an owner, and the reduction rule for a file
that classifies into two surfaces is untouched: it is defined per field across lanes, and the
orchestrator taking one more surface does not change how two graded rows for the same gate merge.

## Consequences

**Easier:**

- Milestones 2 through 4 are unblocked. The capability the whole approach rests on is measured, not
  assumed.
- The three-lane fan-out is smaller than the four-lane one the plan sized, and the lane that dropped
  out was the one the plan itself flagged as failing the orchestrator's own test.
- Bead labeling for `/quality-gates` becomes deterministic. Moving it to gate mode against
  `quality-gates-report.json` removes the model from the labeling decision, which is an improvement
  the refactor did not have to buy.
- The report-only guarantee is now defended by an argument (concurrent lanes cannot race on a tree
  nobody writes) rather than only by incumbency.

**Harder:**

- **The blocking-dispatch requirement is a silent-failure trap.** Finding 4 showed a fan-out where
  every lane succeeded and the aggregate report was simply never written. Nothing errored. Any future
  edit to the orchestrator that drops `run_in_background: false` reintroduces it, and it will look
  like a truncated report rather than a bug. The orchestrator must state the flag as a rule, and
  milestone 2's Done-when must check the transcript for it.
- **The plan needs a revision pass before milestone 2 starts.** Three of these four answers contradict
  what the plan currently says: the agent's filename changes to
  `agents/quality-gates-orchestrator.md`, the fan-out drops from four lanes to three, and criterion
  7's labeling mechanism changes. The plan is not merely unblocked; it is amended.
- **The hook change in milestone 4 is larger than its file list suggests.** Both copies move
  `quality-gates` from inject mode to gate mode, and gate mode's reader gains a second report format.
  The two copies have already diverged once, so this is the second change that must be made twice.
- **Three names now start with `quality-gates`**: the command, the skill, and the orchestrator agent.
  `AGENTS.md:262-266` covers command-versus-skill only, and this ADR adds the agent case by example
  rather than by amending that rule.

**Accepted risk:** the spike measured Claude Code 2.1.239 on this machine. `run_in_background` is
harness behavior, not a repository contract, and a future release could change the default. The
mitigation is the same as the trap above: milestone 2's Done-when checks the transcript, so a default
that changes underneath the orchestrator surfaces as a failing check rather than as a short report.
