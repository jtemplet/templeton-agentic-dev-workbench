# Feature Plan: Reconcile Skills

**Date:** 2026-09-13
**Status:** Draft. Decomposed: 2026-09-13, see bd `tadw-46w`, `tadw-6qd`, `tadw-s6d`, `tadw-gky`,
`tadw-bhi`, `tadw-gni`, `tadw-1v7`, `tadw-3vp`, `tadw-568`, and the follow-up `tadw-v6k`.

**Revised 2026-09-13,** applying that day's `/plan-review` verdict of Needs Revision:

- The three existing "writes only these files" rules are amended by name in milestones 2 and 3.
- verify-acceptance gains a scope step, and the orchestrator's scope step joins milestone 2.
- `tadw-4s5` blocks milestone 4 and one manual run, not the whole plan.
- Each milestone adds its own suites to the `AGENTS.md` check list.
- Each loader defines every reason token, and criterion 13 checks all of them.
- The `**Next:**` line prints only on `FAIL` and `NOT ACCEPTED`.
- New script commands use the plugin-root fallback, and milestone 2 has a positive "Done when".
- `docs/ROUTING.md` and `CHANGELOG.md` are out of scope.

**Revised again 2026-09-13,** after the user answered the open questions:

- The defaults stand for `NO GATES RAN`, `base: null`, a `null` report bead, `changed_files`, the
  exit code for an unresolved `--base`, and the `tadw-psm` duplicate. Each now lives in the body.
- A finding with a `null` file follows the rule acceptance gate rows follow: re-run, then check the
  files the output names.
- `uncommitted-changes` becomes reason 5, so the list has ten reasons.
- Two loaders stay, one per report shape.
- Two output rules cut the tokens a reconcile run reads: out-of-scope findings print without
  `evidence`, and each writer caps `evidence`.

## Summary

This plan adds two skills that fix what a failed check reported. `reconcile-quality-gates` fixes
the findings in `quality-gates-report.json`, and `reconcile-acceptance` fixes the findings in
`acceptance-report.json`. Each reads its findings only from that file, makes one commit per run,
and never grades its own fix.

## Motivation

Outrigger runs `/tadw:quality-gates` and `/tadw:verify-acceptance` with no person present. When
either check fails, no tadw skill can fix the failure and give the work back for another check.
Three facts, each checked against the current tree, block that loop.

**Neither report file carries findings.** `quality-gates-report.json` gives each gate one `detail`
line, such as "2 errors, 11 warnings" (`skills/quality-gates/SKILL.md:771-796`). The failing output
and the Action Items exist only in the markdown report. `acceptance-report.json` holds a bead id and
seven counts, with no criterion text (`skills/verify-acceptance/SKILL.md:114-123`).

**The markdown report does not reach the next step.** Outrigger runs each phase in a separate
`claude -p` process, so a transcript never reaches the phase after it. A file in the git directory
does.

**A stacked branch is checked as if it held its parent's commits.** A stacked branch is a branch
built on another unmerged branch. `skills/quality-gates/scripts/changed_set.py:99-124` always diffs
against the merge-base with `origin/HEAD` or `origin/main`, and nothing can name another base. So a
fix made for the child branch could change the parent's code.

**Who benefits.** Outrigger gets a fixer it can call up to 3 times per check before it gives the
bead to a person. A person working by hand calls the same fixer as `/tadw:<name>`.

## Scope

### In Scope

- Two new skills, `skills/reconcile-quality-gates/SKILL.md` and
  `skills/reconcile-acceptance/SKILL.md`. Each is called as `/tadw:<name> [bead-id]`. Neither has
  an agent or a command file.
- One `scripts/load_findings.py` per reconcile skill, with its regression suite.
- A `--base <ref>` argument for `skills/quality-gates/scripts/changed_set.py`.
- A scripted write of `quality-gates-report.json` at `version: 2`, through a new
  `skills/quality-gates/scripts/write_report_json.py`. This absorbs `tadw-6qd`.
- A scripted write of `acceptance-report.json` at `version: 2`, through a new
  `skills/verify-acceptance/scripts/write_acceptance_report.py`.
- A `**Next:**` line in the reports of both check skills. It names the matching reconcile skill,
  and prints only when the verdict is `FAIL` (quality-gates) or `NOT ACCEPTED` (verify-acceptance).
- A scope step in `skills/verify-acceptance/SKILL.md` that runs `changed_set.py` once, with
  `--base` when the caller gives one. Its three gates and its writer both use that one result.
- Updates to the documents that describe those writes: `agents/quality-gates-orchestrator.md`
  (its scope step and Step 5), `commands/quality-gates.md` step 9, `agents/acceptance-verifier.md`,
  and `commands/verify-acceptance.md`.
- Amendments to the three rules that list the only files a check skill writes, so each names the
  saved changed-set file: `agents/acceptance-verifier.md:15`,
  `skills/verify-acceptance/SKILL.md:238` and its frontmatter `description`, and
  `skills/quality-gates/SKILL.md:962`.
- A `version: 2` report case in `.githooks/test_prepush.py` and in the label-hook cases of
  `hooks/test-claude-scripts.sh`.
- Each milestone adds the suites it creates to the `AGENTS.md` check list, so the ship gate runs
  them from the day they land.
- Registration in `AGENTS.md`: the skill list, the Task Routing table, and the orphan paragraph.
  Also two rows in the `README.md` skills table.
- One manual end-to-end run of each reconcile skill in a throwaway repository, with the output
  recorded on the bead.
- Written during planning, before any bead: ADR 0011 for the report contract, and the terms
  **Findings**, **Reconcile**, and **Base** in `CONTEXT.md`.

### Out of Scope

- The outrigger side: its config keys, routing by verdict, the attempt cap, and its reconcile phase
  prompt. A note for a later outrigger session records the contract this plan settles.
- `/verify-acceptance` reading `quality-gates-report.json` itself, so a loop does not run the tests
  twice. That becomes its own bead, and it blocks nothing here.
- `tadw-c99` (bead-id resolution in verify-acceptance), `tadw-440` (where a `browser-ui` HANDOFF
  row goes), and `tadw-a6y` (a stale plugin cache withholds the label). Each stays a separate bead.
- An agent that runs either reconcile skill. One may come later, and its name must differ from the
  skill's name.
- Detecting a parent branch automatically. The caller names the base.
- Fixing review findings. Outrigger's own reconcile phase keeps that job.
- A test that pins the guardrail wording of the reconcile skills. Only the tokens a machine reads
  are pinned.
- `docs/ROUTING.md`, whose missing entries `tadw-routing-gaps-9wq` tracks, and `CHANGELOG.md`,
  which is written at release time.

## Technical Approach

### Architecture

Each check skill writes a report file. The caller reads the verdict and, on a failed verdict, calls
the matching reconcile skill. That skill reads the same file, fixes what is in scope, and commits.
Then the caller runs the check again.

```text
/tadw:quality-gates      -> <git-dir>/quality-gates-report.json -> /tadw:reconcile-quality-gates
/tadw:verify-acceptance  -> <git-dir>/acceptance-report.json     -> /tadw:reconcile-acceptance
                                                                   -> one commit
                                                                   -> the caller runs the check again
```

**Every new script is told its inputs and discovers nothing.** No new script runs `git` or `bd`,
and none reads a branch name. The skill runs those commands and passes each value as an argument,
through command substitution such as `--head "$(git rev-parse HEAD)"`. Each script is a thin
`main()` that parses arguments and reads the file it was named. Below it is a pure function that
decides, meaning its result depends only on its arguments. This is dependency injection, and it lets
every new suite run without a git repository.

`changed_set.py` is the one exception, because its job is to ask git for the changed set. It gains
a way to be told the base.

**Every documented script command uses the plugin-root fallback.** A fenced command that runs a new
script writes `${CLAUDE_PLUGIN_ROOT:-...}` and carries the `<!-- plugin-root-fallback -->` marker,
as `skills/quality-gates/SKILL.md` Step 2 does. Without both, `check_documented_paths.py` fails the
ship gate.

**The saved changed set.** Each check skill runs `changed_set.py` exactly once and saves its stdout
in the git directory, as `agents/quality-gates-orchestrator.md:40-45` already requires for the run
itself. The writer reads that file. The three rules that list the only files a check skill writes
are amended to name it, because a model given a rule and a step that disagree obeys one of them.

**The report path.** Each skill resolves the path with
`git rev-parse --path-format=absolute --git-dir` and passes it to the script. That command gives
each worktree its own directory, and gives `.git` in an ordinary clone. File names do not change.

**The staleness chain.** A reconcile skill starts only when the report's `head` equals the current
`HEAD`. Its commit moves `HEAD`, so the same report is stale on the next call. The caller must run
the check again before a second attempt, so every attempt gets checked.

**Who calls whom.** A check skill never calls a reconcile skill. On a `FAIL` or `NOT ACCEPTED`
verdict, its report ends with a `**Next:**` line that names one, for the caller to read. An
`INCOMPLETE` or `INCONCLUSIVE` verdict gets no such line, because a reconcile skill could only stop
with `needs-human-check`. The caller counts attempts; outrigger stops after 3 and gives the bead to
a person.

**The reconcile workflow.** Both skills follow the same steps.

1. Run `load_findings.py` with `--report`, `--head "$(git rev-parse HEAD)"`,
   `--dirty-files <(git status --porcelain=v1 -z)`, and `--bead` when the caller named one. On
   exit 1, print its machine line and stop. On exit 3, print `RECONCILE_<NAME>_DONE 0` and stop.
2. Read `git log` for an earlier reconcile commit on this bead. A finding that comes back after a
   fix needs a different approach.
3. Load the style skill for each file type the in-scope findings touch, from
   `docs/style-routing.md`.
4. For a finding with no file, re-run its `command` first, and apply the outside-the-change rule
   and the uncommitted-changes rule to the files the output names.
5. Before editing any file, check it against `--dirty-files`. Fix each in-scope finding, re-run its
   `command` when it has one, and mark it fixed or not fixed.
6. When at least one finding is fixed, stage the changed files by path and make one commit. Never
   run `git add -A`.
7. Print a table that marks each finding fixed, out of scope, or not fixed. Then print the machine
   line as the last line.

**The commit.** The subject is `fix(quality-gates): reconcile <n> findings (<bead>)` or
`fix(acceptance): reconcile <n> findings (<bead>)`. Without a bead, the parenthetical is left out.
The body has one line per fixed finding, naming the gate or criterion, the `file:line`, and the
problem. The skill never amends, never pushes, and never rewrites history.

**Scope.** `reconcile-quality-gates` fixes FAIL gate rows only. It leaves BLOCKED, HANDOFF, WARN,
and SKIP rows alone. `reconcile-acceptance` fixes FAIL criteria and FAIL gates, and leaves
UNVERIFIABLE criteria alone. Neither fixes a finding in a file outside the report's
`changed_files`.

**A finding with no file.** Some findings name no file: a quality-gates finding whose `file` is
`null`, and every acceptance gate row. The loader counts such a finding as in scope. The skill
re-runs its `command`, then applies the outside-the-change rule and the uncommitted-changes rule to
the files the output names. One rule serves both skills, and the loader never guesses a file.

**No uncommitted changes in a file being fixed.** Staging a file by path would commit the
uncommitted changes already in it, which nobody asked for. So the skill refuses to edit such a file,
and stops with `uncommitted-changes`. A person working by hand commits first, runs the check, and
then calls the reconcile skill. Outrigger commits between phases, so it rarely meets the refusal.

**Two loaders, one per report shape.** Checks 1 to 5 are the same in both, and house rule 1 says to
wait for a third copy before sharing code. A shared loader would need a mode argument or a third
file. The runtime cost is the same either way, because the model reads the loader's output and never
its source.

**Keep what a run reads small.** A reconcile run reads the loader's output on every attempt, up to 3
per check per bead, so two rules bound it. First, the loader prints an out-of-scope finding without
its `evidence`, because the skill never fixes it. Second, each writer caps every `evidence` value at
20 lines and 2,000 characters. The writer keeps the first lines and appends
`[trimmed: <n> more lines]`, so one lint run with hundreds of warnings cannot fill the context.

**Nothing to fix.** A report whose verdict is `PASS` or `NO GATES RAN`, or whose counts make it
ACCEPTED, makes the loader exit 3, and the skill prints `RECONCILE_<NAME>_DONE 0`. Nothing failed,
and outrigger already treats `NO GATES RAN` as a skipped QA phase.

**Guardrails.** Both skills keep all four.

- Never weaken, skip, or delete a test or an assertion.
- Never edit the bead or its criteria.
- Build nothing beyond what the finding asks for. A missing test that the finding names is in
  scope.
- Never write `quality-gates-report.json` or `acceptance-report.json`.

**A partial run.** When one in-scope finding stays unfixed, the skill still commits the fixes that
worked. Then it prints the BLOCKED line with `finding-not-fixed`. The same holds when the skill stops
mid-run on `uncommitted-changes` or `failures-outside-change`.

### Key Components

| Component | Purpose | New/Modified |
|---|---|---|
| `skills/quality-gates/scripts/changed_set.py` | Accept `--base <ref>`; keep `origin/HEAD`, then `origin/main`, as the default | Modified |
| `skills/quality-gates/scripts/write_report_json.py` | Validate and write `quality-gates-report.json` at version 2 | New |
| `skills/quality-gates/SKILL.md` | Step 2 saves the changed set to a file; Step 6 calls the writer; the report adds `**Next:**`; the rule at line 962 names the saved file | Modified |
| `agents/quality-gates-orchestrator.md` | Its scope step (lines 40-45) passes `--base` and saves the changed set; Step 5 calls the writer instead of building JSON | Modified |
| `commands/quality-gates.md` | Step 9 names the scripted write and `--base` | Modified |
| `skills/verify-acceptance/scripts/write_acceptance_report.py` | Validate and write `acceptance-report.json` at version 2 | New |
| `skills/verify-acceptance/SKILL.md` | A new scope step runs `changed_set.py` once; Step 5 calls the writer; the report adds `**Next:**`; accepts `--base`; line 238 and the frontmatter `description` name the saved file | Modified |
| `agents/acceptance-verifier.md` | Names the scripted write; line 15 names the saved file | Modified |
| `commands/verify-acceptance.md` | `argument-hint` gains `--base <ref>` | Modified |
| `skills/reconcile-quality-gates/SKILL.md` | The reconcile workflow for quality-gates findings | New |
| `skills/reconcile-quality-gates/scripts/load_findings.py` | Check the report, then split its findings into in scope and out of scope | New |
| `skills/reconcile-acceptance/SKILL.md` | The reconcile workflow for acceptance findings | New |
| `skills/reconcile-acceptance/scripts/load_findings.py` | The same check, for the acceptance report's shape | New |
| `hooks/test-claude-scripts.sh` | Update the verify-acceptance text case; add a version 2 label case | Modified |
| `.githooks/test_prepush.py` | Add a version 2 report case | Modified |
| `AGENTS.md`, `README.md` | Registration | Modified |

### Test Seams

| Seam | Existing or new | What it proves |
|---|---|---|
| The pure function inside each new script, called in-process with injected values | New | Writers: every refusal, the `evidence` cap, and the exact JSON shape. Loaders: reasons 1 to 8 in order, exit 3, the in-scope split, out-of-scope findings with no `evidence`, and that `SKILL.md` names all ten reason tokens and both machine lines |
| `changed_set.py` run as a process against a throwaway git repository | Existing: `test_changed_set.py` | `--base` diffs against the named ref; an unresolved named ref exits 2; no flag keeps today's default |
| The two existing hook readers, given a version 2 report | Existing: `.githooks/test_prepush.py`, `hooks/test-claude-scripts.sh` | The pre-push hook still reads the verdict, and the label hook still reads the seven counts |

The first seam replaces a git repository per case with plain values. `test_changed_set.py` runs 21
cases in 3.68 seconds, and each case builds two repositories (measured on 2026-09-13 with
`time python3 skills/quality-gates/scripts/test_changed_set.py`). A pure function needs no
repository. Only `--base` needs git, and it joins the suite that already builds repositories.

The model's fixing behavior has no deterministic seam, so one manual run per skill covers it. The
user confirmed the reader seam. The user questioned the cost of a git repository per case and asked
for injected inputs, so the first two seams were revised to match.

### Data Model

**`quality-gates-report.json`, version 2.** Every version 1 field stays, with its meaning
(`skills/quality-gates/SKILL.md:771-796`). These fields are new:

```json
{
  "version": 2,
  "bead": "tadw-abc",
  "base": {"ref": "origin/HEAD", "sha": "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"},
  "changed_files": ["src/api/exports.py", "tests/test_exports.py"],
  "findings": [
    {"gate": "Lint", "file": "src/api/exports.py", "line": 88,
     "problem": "F841 local variable 'rows' is assigned to but never used",
     "evidence": "src/api/exports.py:88:5: F841 local variable 'rows' is assigned to but never used"}
  ]
}
```

- `bead` is the id the caller named. When the caller named none, it is an id in the branch name
  that `bd show` confirms. Otherwise it is `null`. The skill never asks the user, and never guesses
  from beads in progress.
- `base` is the ref and SHA that `changed_set.py` used. It is `null` only when the base did not
  resolve and the run went to `--all`.
- `changed_files` is the changed set the run checked, as `changed_set.py` printed it. It is `null`
  when `base` is `null`. The field exists so that the loader is given the changed set and never
  runs git to build it.
- When `base` is `null`, the loader counts every FAIL finding as in scope and sets `scope_known` to
  `false` in its output. Refusing instead would block every repository with no remote.
- `findings` has one entry per Action Item. `file` and `line` are `null` when the Action Item names
  no place. `gate` names a row in `gates`.

**`acceptance-report.json`, version 2.** The seven counts stay, and the label hook keeps reading
them by name. These fields are new:

```json
{
  "version": 2,
  "head": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
  "base": {"ref": "origin/HEAD", "sha": "9f8e7d6c5b4a39281706f5e4d3c2b1a098765432"},
  "changed_files": ["src/auth.py"],
  "criteria": [
    {"number": 1, "text": "a valid token returns 200", "verdict": "PASS",
     "evidence": "test_accepts_valid_token passed", "command": "pytest tests/test_auth.py::test_accepts_valid_token"},
    {"number": 2, "text": "an expired token returns 401", "verdict": "FAIL",
     "evidence": "test_rejects_expired_token failed: got 200", "command": "pytest tests/test_auth.py::test_rejects_expired_token"}
  ],
  "gates": [
    {"name": "Tests", "status": "FAIL", "command": "pytest -q", "detail": "217 passed, 1 failed"}
  ]
}
```

- `criteria` has one entry per criterion, PASS entries included. `command` is the narrowest command
  that proves the criterion. It is `null` when the criterion was graded by reading a `file:line`.
- `gates` has one entry per gate. `command` follows the quality-gates rule: `null` unless someone
  can re-run it.
- There is still no `verdict` field, and the writer refuses one.

### API / Interface

**The skills.** `/tadw:reconcile-quality-gates [bead-id]` and `/tadw:reconcile-acceptance [bead-id]`.
The only argument is the bead id. `head` and `base` come from the report, never from the caller.

**The machine lines.** The last line of a reconcile run is one of these:

- `RECONCILE_QUALITY_GATES_DONE <fixed-count>` or `RECONCILE_QUALITY_GATES_BLOCKED <reason>`
- `RECONCILE_ACCEPTANCE_DONE <fixed-count>` or `RECONCILE_ACCEPTANCE_BLOCKED <reason>`

**The BLOCKED reasons.** When several apply, the first in this order wins. Each `load_findings.py`
defines all ten tokens as constants, including the ones its skill decides, so one test can check
them against `SKILL.md`.

| # | Reason | Decided by | Condition |
|---|---|---|---|
| 1 | `report-missing` | `load_findings.py` | No file at `--report` |
| 2 | `report-unreadable` | `load_findings.py` | The file does not parse, lacks a version 2 field, or has a `version` other than 2; the message names the version found |
| 3 | `report-stale` | `load_findings.py` | The report's `head` differs from `--head` |
| 4 | `bead-mismatch` | `load_findings.py` | `--bead` was given and differs from the report's `bead`, `null` included |
| 5 | `uncommitted-changes` | `load_findings.py` for the files findings name; the skill for findings with no file and for any other file a fix must edit | A file that an in-scope finding names, or that a fix must edit, is listed in `--dirty-files` |
| 6 | `failures-outside-change` | `load_findings.py` for findings with a file; the skill for findings with no file | Every FAIL finding is in a file outside `changed_files` |
| 7 | `needs-environment` | `load_findings.py` | Nothing is in scope, and a BLOCKED gate row remains |
| 8 | `needs-human-check` | `load_findings.py` | Nothing is in scope, and a HANDOFF row or an UNVERIFIABLE criterion remains |
| 9 | `finding-not-fixed` | The skill | At least one in-scope finding stayed unfixed |
| 10 | `commit-failed` | The skill | `git commit` refused, for example because a hook failed |

**The scripts.**

| Script | Arguments | stdin | Exit status and output |
|---|---|---|---|
| `changed_set.py` | `--repo-root <path>`, new `--base <ref>` | None | Unchanged without `--base`. With it, the base is the merge-base of `HEAD` and that ref. A named ref that does not resolve exits 2 |
| `write_report_json.py` | `--out <path>`, `--head <sha>`, `--dirty true\|false`, `--timestamp <utc>`, `--changed-files <path>` | One JSON object: `scope`, `gate_source`, `routing`, `bead`, `base`, `verdict`, `gates`, `findings` | 0 after writing. 1 with a named reason, writing nothing: a field is missing, a status is not one of the six, the verdict breaks the Verdict Rules, or a finding names no gate row. 2 on a usage error |
| `write_acceptance_report.py` | `--out <path>`, `--head <sha>`, `--changed-files <path>` | One JSON object: `bead`, `base`, the seven counts, `criteria`, `gates` | 0 after writing. 1 with a named reason, writing nothing: a count disagrees with the arrays, a `verdict` field is present, or a field is missing. 2 on a usage error |
| `load_findings.py` | `--report <path>`, `--head <sha>`, `--dirty-files <path>`, optional `--bead <id>` | None | 0: prints JSON with `in_scope` (full entries), `out_of_scope` (each entry holds only its gate or criterion number, `file`, and `problem`), `base`, `bead`, and `scope_known`. 1: prints the BLOCKED machine line for reasons 1 to 8. 2: usage error. 3: nothing to fix |

`--changed-files` names the file where the check skill saved the stdout of `changed_set.py`. It is
left out when `base` is `null`. The check skills save that file inside the git directory, under a
name of their own: `quality-gates-changed.txt` and `acceptance-changed.txt`.

`--dirty-files` takes the output of `git status --porcelain=v1 -z` through process substitution, so
the reconcile skill writes no file to pass it.

**A named `--base` that does not resolve exits 2, not 3.** Exit 3 tells the caller to widen the run
to `--all`, which would check the parent branch's code. A bad value the caller gave is a usage
error, and a default that cannot resolve is not, so they get different exit codes.

## Decisions That Bind This Plan

| ADR | The rule it sets | How this plan honors it |
|---|---|---|
| [0001](../adr/0001-native-tracker-fields-are-canonical.md) | Native tracker fields are canonical | `verify-acceptance` still reads `acceptance_criteria`. The reconcile skills read the bead id and never write the bead |
| [0002](../adr/0002-the-quality-gates-orchestrator-fans-out-to-blocking-subagents.md) | The orchestrator renders the report and writes the artifact; a lane never does | `agents/quality-gates-orchestrator.md` Step 5 calls `write_report_json.py`. Lanes still return rows only |
| [0004](../adr/0004-the-pre-push-hook-forgives-by-design.md) | The pre-push hook warns and allows on a missing or unreadable report | Version 2 keeps `verdict`, `head`, and `timestamp`, and a version 2 case in `.githooks/test_prepush.py` proves the hook still reads them |
| [0005](../adr/0005-the-evals-are-a-measurement-not-a-gate.md) | The evals measure; they do not gate | The fixing behavior is checked by one manual run per skill, not by an eval in the ship gate |
| [0008](../adr/0008-delegated-work-runs-on-a-cheaper-model.md) | A job whose output nobody downstream can check keeps its judgment | A weakened test passes the next check unseen, so the reconcile skills run on the caller's model. `acceptance-verifier` stays on `sonnet` |
| [0009](../adr/0009-the-large-skill-documents-are-not-split.md) | Large skill documents stay whole | The new rules go straight into the two check skills' `SKILL.md` files, with no `references/` file |
| [0011](../adr/0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md) | A reconcile skill reads its findings from the report file and never grades its own fix | This plan is the first user of that contract |

## Implementation Milestones

| # | Milestone | Description | Effort | Done when |
|---|---|---|---|---|
| 1 | Name the base | `changed_set.py --base <ref>`, with cases in `test_changed_set.py` | S | `python3 skills/quality-gates/scripts/test_changed_set.py` passes, with cases for a named base, an unresolved named ref, and no flag |
| 2 | Scripted quality-gates report, version 2 | `write_report_json.py` and its suite, added to the `AGENTS.md` check list; `SKILL.md` Steps 2 and 6 and the rule at line 962; the orchestrator's scope step and Step 5; command step 9; the `**Next:**` line; a version 2 case in `.githooks/test_prepush.py`. Commands use the plugin-root fallback. Absorbs `tadw-6qd`. Depends on 1 | M | Both suites pass, and `grep -ln "write_report_json.py" skills/quality-gates/SKILL.md agents/quality-gates-orchestrator.md commands/quality-gates.md` lists all three files |
| 3 | Scripted acceptance report, version 2 | `write_acceptance_report.py` and its suite, added to the check list; the new scope step and Step 5 in `SKILL.md`; the one-file rules at `agents/acceptance-verifier.md:15`, `SKILL.md:238`, and the `description`; the command; the `**Next:**` line; the text case and a version 2 label case in `hooks/test-claude-scripts.sh`. Commands use the plugin-root fallback. Depends on 1 | M | Both suites pass, and the label hook applies `accepted` to a version 2 report whose criteria all PASS |
| 4 | `reconcile-quality-gates` | `SKILL.md`, `load_findings.py`, and its suite, added to the check list. Commands use the plugin-root fallback. Depends on 2 and on `tadw-4s5` | M | The suite passes, with a case per reason 1 to 8, a case for exit 3, and a case that `SKILL.md` names all ten reason tokens and both machine lines |
| 5 | `reconcile-acceptance` | `SKILL.md`, `load_findings.py`, and its suite, added to the check list. Commands use the plugin-root fallback. Depends on 3 | M | The same as milestone 4, against `acceptance-report.json` |
| 6 | Register and prove | The `AGENTS.md` skill list, Task Routing table, and orphan paragraph; the `README.md` rows; `/validate-plugin`; one manual run per reconcile skill. The `reconcile-quality-gates` run also waits on `tadw-4s5`. Depends on 4 and 5 | S | `claude plugin validate .` and `python3 skills/quality-gates/scripts/check_documented_paths.py` both exit 0, and each bead records the machine lines from its manual run |

## Acceptance Criteria

1. Given branch B stacked on branch A, when `changed_set.py --base A` runs on B, then it prints
   only the files B changed.
2. Given a `--base` ref that does not resolve, when `changed_set.py` runs, then it exits 2 and
   prints no path.
3. Given no `--base`, when `test_changed_set.py` runs, then every case that existed before this
   plan passes unchanged.
4. Given a finished `/tadw:quality-gates` run, when it writes its report, then the file has
   `version` 2, every version 1 field, and `bead`, `base`, `changed_files`, and `findings`.
5. Given a verdict that breaks the Verdict Rules for the gate statuses passed in, when
   `write_report_json.py` runs, then it exits 1, names the mismatch, and writes no file.
6. Given counts that disagree with the `criteria` or `gates` arrays, or a `verdict` field, when
   `write_acceptance_report.py` runs, then it exits 1 and writes no file.
7. Given a version 2 `acceptance-report.json` whose criteria all PASS with no failing or blocked
   gate, when the `Stop` hook runs, then it applies `accepted`.
8. Given a version 2 `quality-gates-report.json` with verdict FAIL for the commit being pushed, when
   `.githooks/pre-push` runs, then it refuses the push.
9. Given a `FAIL` verdict from quality-gates or a `NOT ACCEPTED` verdict from verify-acceptance,
   when that skill renders its report, then the report has a `**Next:**` line naming
   `/tadw:reconcile-quality-gates` or `/tadw:reconcile-acceptance`. An `INCOMPLETE` or
   `INCONCLUSIVE` verdict renders no `**Next:**` line.
10. Given each condition for reasons 1 to 8, when `load_findings.py` runs, then it exits 1 and
    prints the BLOCKED machine line with that reason. When several hold, it prints the first.
11. Given a report whose verdict is `PASS` or `NO GATES RAN`, or whose counts make it ACCEPTED,
    when `load_findings.py` runs, then it exits 3, and the skill prints `RECONCILE_<NAME>_DONE 0`.
12. Given a report with one FAIL finding in a file inside `changed_files` and one outside, when
    `load_findings.py` runs, then the first is in `in_scope` and the second is in `out_of_scope`.
13. Given the ten reason tokens and two machine-line names defined in `load_findings.py`, when its
    suite runs, then each one appears in the same skill's `SKILL.md`.
14. Given any new script, when `grep -n "subprocess" <script>` runs on it, then nothing prints.
15. Given a throwaway repository with one lint FAIL in a changed file, when
    `/tadw:reconcile-quality-gates` runs, then it makes one commit touching only the fixed files,
    the commit body names the finding, and the last line is `RECONCILE_QUALITY_GATES_DONE 1`.
16. Given that repository right after that commit, when `/tadw:reconcile-quality-gates` runs again
    with no new check, then it makes no commit and prints
    `RECONCILE_QUALITY_GATES_BLOCKED report-stale`.
17. Given a throwaway repository with one FAIL criterion that has a `command`, when
    `/tadw:reconcile-acceptance` runs, then it runs that command before its commit, and the last
    line is `RECONCILE_ACCEPTANCE_DONE 1`.
18. Given a run where one in-scope finding cannot be fixed and another can, when the skill ends,
    then the working fix is committed and the last line ends in `BLOCKED finding-not-fixed`.
19. Given any commit a reconcile skill made in criteria 15 to 18, when its diff is read, then it
    removes no test function and no assertion line, and it changes no bead field.
20. Given the plugin after milestone 6, when `claude plugin validate .` runs, then it exits 0, and
    `AGENTS.md` lists both reconcile skills among the accepted orphans.
21. Given the repository before the first bead, when `docs/adr/` and `CONTEXT.md` are read, then
    ADR 0011 records the report contract, and `CONTEXT.md` defines Findings, Reconcile, and Base.
22. Given a finished `/tadw:verify-acceptance` run for a resolved bead, when it writes its report,
    then the file has `version` 2, `head`, `base`, `changed_files`, `criteria`, `gates`, and the
    seven counts.
23. Given the orchestrator path of `/tadw:quality-gates`, when a run finishes, then `changed_set.py`
    ran once, and the report's `base` and `changed_files` match that one run.
24. Given `agents/acceptance-verifier.md`, `skills/verify-acceptance/SKILL.md`, and
    `skills/quality-gates/SKILL.md`, when each rule that lists the files the skill writes is read,
    then that rule names the saved changed-set file.
25. Given the plugin after milestone 6, when
    `python3 skills/quality-gates/scripts/check_documented_paths.py` runs, then it exits 0.
26. Given a throwaway repository where a Tests FAIL finding has a `null` file and its re-run output
    names only files outside `changed_files`, when `/tadw:reconcile-quality-gates` runs, then it
    edits no file and prints `RECONCILE_QUALITY_GATES_BLOCKED failures-outside-change`.
27. Given a throwaway repository where the file of an in-scope finding has uncommitted changes, when
    either reconcile skill runs, then it edits no file and prints its BLOCKED line with
    `uncommitted-changes`.
28. Given an `evidence` value of 21 lines or more, or over 2,000 characters, when either writer
    runs, then the written value holds at most 20 lines and 2,000 characters before a final
    `[trimmed: <n> more lines]` line, where `<n>` is the number of lines removed.
29. Given a report with an out-of-scope finding, when `load_findings.py` exits 0, then that
    finding's entry in `out_of_scope` has no `evidence` key.

**Coverage:** criteria 1 to 3 prove the base; 4 to 8, 22, 23, and 28 prove the two version 2 writes
and their readers; 9 proves the `**Next:**` line; 10 to 14 and 29 prove the loaders and the injected
inputs; 15 to 19, 26, and 27 prove the two skills and their guardrails; 20, 24, and 25 prove
registration and the amended documents; 21 proves the ADR and the glossary.

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| `/tadw:quality-gates` gives a different verdict on an unchanged tree (`tadw-4s5`), so the loop fixes, checks, and flips | High | Med | `tadw-4s5` blocks milestone 4 and its manual run. Outrigger's cap of 3 attempts bounds the cost until it is fixed |
| A manual run meets `uncommitted-changes` often, because a manual report is nearly always written before a commit (`skills/quality-gates/SKILL.md:816-818`) | Low | High for manual runs, Low in outrigger | Accepted. The refusal edits nothing, and `SKILL.md` tells a person the order: commit, run the check, then reconcile |
| A fix makes a check pass by weakening the check, and the next check cannot see that | High | Med | The guardrails forbid it. Each commit body lists its findings for review. Criterion 19 checks the manual runs |
| A stale plugin cache writes a version 1 report (`tadw-a6y`) | Med | Med | The loader refuses any version but 2 with `report-unreadable`, and names the version it found |
| The model mistypes a SHA or a file list into a writer | Med | Low | Values pass through command substitution and a file path, never retyped. The writer validates the shape |
| The work is spread over many files: two writers, two loaders, two skills, one script argument, and document updates | Med | High | Six milestones with explicit dependencies. The outrigger side and the double test run stay out of scope |
| A model reads the `**Next:**` line as an order and starts fixing inside the check | Med | Low | The line is addressed to the caller, and both check skills already forbid editing the working tree |

## Dependencies

- `tadw-4s5` blocks milestone 4 and the `reconcile-quality-gates` manual run in milestone 6.
  Milestones 1, 2, 3, and 5 do not wait on it, because only a loop over quality-gates suffers from a
  verdict that changes on an unchanged tree.
- `tadw-6qd` is absorbed into milestone 2. Its design says the script derives `head`, `dirty`, and
  `timestamp` from git. This plan replaces that: the skill passes them as arguments.
  `/plan-to-beads` must rewrite or close `tadw-6qd` to match.
- ADR 0011 and the three `CONTEXT.md` terms are written before the first bead.
- `tadw-psm` has the same subject as `tadw-4s5`: a verdict that changes on an unchanged tree.
  `/plan-to-beads` closes `tadw-psm` as a duplicate of `tadw-4s5`.
- Python 3 standard library only, the same as `changed_set.py`.

## Testing Strategy

- **Pure-function suites:** `test_write_report_json.py`, `test_write_acceptance_report.py`, and one
  `test_load_findings.py` in each reconcile skill's `scripts/` directory. They call the decision
  function in-process with dicts and strings, and use no git repository and no subprocess. Each
  suite joins the `AGENTS.md` check list, which is the ship gate, in the milestone that creates it.
- **Git-backed suite:** `test_changed_set.py` gains the `--base` cases, in the pattern it already
  uses.
- **Reader suites:** `.githooks/test_prepush.py` and `hooks/test-claude-scripts.sh` each gain a
  version 2 report case.
- **Manual runs:** one throwaway repository per reconcile skill drives criteria 15 to 19, 26, and
  27. The bead records the commands and the machine lines.
- **Before shipping:** the full `AGENTS.md` check list, minus `python3 evals/run.py`.

## Open Questions

None. The interview, two reviews, and the user's answers settled every decision this plan
depends on. ADR 0011 and the three `CONTEXT.md` terms are written.
