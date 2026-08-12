# Feature Plan: quality-gates hardening, verify the gate and then enforce it

**Audience.** An agent executing this plan in the `templeton-agentic-dev-workbench` repository,
with no memory of the conversation that produced it. Everything needed is in this file plus the
files it names. Read `AGENTS.md` first; its "Common Tasks" and "Landing the Plane" sections
govern how work lands here.

**Context.** `skills/quality-gates/SKILL.md` was rebuilt in commit `a093acc` around the change
rather than the repository, with a status model (PASS/FAIL/WARN/SKIP/BLOCKED/HANDOFF), a
judgment-based change-coverage gate (Gate 2), and one bundled script
(`skills/quality-gates/scripts/check_doc_paths.py`, Gate 5). The skill is invoked through
`commands/quality-gates.md`, which **reads** the SKILL.md rather than invoking it by name
(command/skill namespace collision, documented in the command file). `verify-acceptance` reads
the same SKILL.md and runs a four-gate subset.

**The gap this plan closes.** The skill is prose an LLM executes, and almost nothing verifies
the execution. Only one of seven gates is scripted; the skill's own regression suites run only
when someone remembers; the coverage gate's claims are unverifiable after the fact; the verdict
is a markdown table that nothing downstream enforces; and no test anywhere exercises the skill's
behavior, so a regression in the prose ships silently.

**Revision history.**

- **2026-08-10, from a `/plan-review` pass.** Added sections 5a (Risks), 5b (Dependencies), and
  5c (Open Questions). M4 gained the `SKILL.md` edits that reconcile its JSON write with the
  skill's report-only rules. Added the release milestone. Sharpened acceptance criteria across
  M1, M3, M4, and the prompt-assets milestone.
- **2026-08-10, from author direction.** Three changes. Enforcement is now a **local git hook**
  rather than a GitHub Actions step, so M2 was rewritten and merged with M4's hook into one
  `pre-push` file. The **dependency-audit gate was dropped** from scope and moved to follow-up
  F2. The **fixture-repo eval work was promoted** from follow-up F2 to milestone M6, because it
  is the only check that exercises the skill's behavior rather than its scripts.

**Status.** Decomposed 2026-08-10 into 13 beads, all labeled `qg-hardening`. List them with
`br list --label qg-hardening`, or scope a subgraph with `bv --robot-plan --label qg-hardening`.
Re-running `/plan-to-beads` on this file must diff against that label rather than create a
second set.

---

## 1. Goals

| ID | Goal | Owning milestone |
|---|---|---|
| **G1** | The mechanical gates (secrets, hygiene, changed-set) run as tested scripts, not prose re-derived on every run. | M1 |
| **G2** | The repository's own checks run locally before any work leaves the machine, without depending on a hosted service. | M2 |
| **G3** | Every coverage claim in a Gate 2 table is verifiable after the fact, via citations. | M3 |
| **G4** | The verdict is machine-readable, and a FAIL verdict mechanically blocks a push in this repository. | M4 |
| **G5** | The prompt-assets change shape has a concrete checklist instead of a vague cell. | M5 |
| **G6** | The skill's behavior is under test, so a regression in its prose fails something instead of shipping. | M6 |
| **G7** | The work ships as a released version, so users of the plugin get it without pulling `main`. | M7 |

## 2. Problem, with evidence

1. **One scripted gate out of seven.** `ls skills/quality-gates/scripts/` shows
   `check_doc_paths.py` and its test, nothing else. Gate 6 (secrets) is prose regexes and
   exclusion lists in `SKILL.md`; Gate 7 (hygiene) is a one-line shell recipe; Step 2's
   changed-set resolution is a two-command recipe with a fallback rule. Each is reassembled by
   the model on every run, so two runs can disagree. The doc-freshness gate already learned
   this lesson: its prose version produced 194 false positives on first contact with a real
   repository, which is why it became a script with a pinned test suite (see the docstring in
   `check_doc_paths.py`).
2. **Nothing runs the checks before work leaves the machine.** `AGENTS.md` lists nine commands
   under "Commands for This Repo", and running them is a convention, not a mechanism. The only
   hard gate in this repository is `.githooks/reference-transaction`, which fires on `v*` tags
   alone. Commits and pushes ride entirely on the session remembering.
3. **Gate 2 is unverifiable.** The rule "Read each test you count" (`SKILL.md`, Gate 2 step C)
   leaves no artifact. A plausible-looking coverage table and a fabricated one are
   indistinguishable to the reader.
4. **The verdict enforces nothing.** The report is markdown only. "Landing the Plane" in
   `AGENTS.md` tells the session to run the gates before pushing, but a session that pushes
   despite a FAIL leaves no trace and hits no barrier.
5. **The prompt-assets shape is vague.** Gate 2's shape table says "the asset parses, it is
   registered where the project says, and its embedded commands are valid" without naming the
   checks. This repository is the primary user of that row.
6. **Nothing tests the skill's behavior.** `evals/` holds six cases, all of them response-style
   checks on prose the model writes. No test runs the skill against a repository and asserts
   what it concluded. Every rule in `SKILL.md` that this plan does not convert into a script
   stays unprotected: a later edit can quietly reintroduce the exact bug commit `a093acc`
   fixed, where an all-skip run reported PASS.

## 3. Decisions

| ID | Decision | Rationale |
|---|---|---|
| **D1** | New scripts are stdlib-only Python 3, mirroring `check_doc_paths.py` conventions: argparse CLI, module docstring stating why the script exists, exit 0 clean / 1 findings / 2 operator error, and a sibling `test_*.py` runnable with bare `python3`. | The pre-push hook must run them with no install step, on any clone. Convention-matching keeps the scripts reviewable as a set. |
| **D2** | Gate 2 stays judgment-based prose. This plan adds evidence requirements to it, not a script. | Case enumeration and span grading are the LLM's job; the plan makes the claims auditable rather than pretending they can be computed. |
| **D3** | The JSON report is written to `quality-gates-report.json` inside the directory `git rev-parse --git-dir` names, in the repository the gates ran against. Its `dirty` field is recorded for a human reader and has no automated consumer. | Inside the git directory it is per-clone, never committed, needs no `.gitignore` entry, and survives until the push it is meant to inform. **Resolved by command, never as a literal `.git/`, and never with `--git-common-dir`.** `--git-dir` returns a distinct path per linked worktree, so two worktrees on two branches keep two verdicts about two trees; `--git-common-dir` would let them overwrite each other, and a literal `.git/` is a file rather than a directory inside a worktree. `dirty` is read-only on purpose: the hook must not block on it, because the skill runs before the commit almost every time, so nearly every honest report is dirty. |
| **D4** | **Enforcement is a local git hook, not a CI step.** `.github/workflows/lint.yml` keeps the checks it runs today and gains nothing new. | Author direction. A local hook fails in seconds at the moment of the mistake, needs no hosted service, and works the same in a repository with no remote. The tradeoff is real and accepted: hooks are per-clone config and `--no-verify` bypasses them. Recorded as R5. |
| **D5** | **One `.githooks/pre-push` file with two stages**, not two hook files. Stage 1 runs the repository's own suites (M2); stage 2 reads the recorded quality-gates verdict (M4). | Git calls exactly one `pre-push` hook, so two responsibilities on the same event must share a file. M2 creates it, M4 appends to it. |
| **D6** | The hook blocks on a failed suite, and on a recorded verdict of FAIL. A missing or stale verdict report allows the push with a one-line warning. A missing tool warns and allows. | Blocking every push without a fresh report would break trivial documentation pushes and teach users to disable the hook. The missing-tool rule follows the precedent `.githooks/reference-transaction` set: an unusable repository is worse than an unchecked push. |
| **D7** | The eval milestone runs its fixture cases **single-arm**, with the plugin loaded, and skips the no-plugin baseline. | These are regression tests, not efficacy tests. `/quality-gates` does not exist without the plugin, so a baseline arm would measure nothing and would double the cost of every run. |
| **D8** | The coverage-tool cross-check and the dependency-audit gate are deferred to follow-up beads. | Both are additive gates that answer questions this plan does not, and neither protects the work the other milestones do. Specified in section 7 so they can be filed without re-derivation. |

## 4. Scope

### In scope

- Three new gate scripts with regression suites (M1).
- A local `pre-push` hook running the repository's own checks (M2), extended with the verdict
  gate (M4).
- Evidence citations in Gate 2 (M3), a machine-readable verdict artifact (M4).
- A concrete prompt-assets checklist (M5), fixture-repo evals of the skill (M6).
- The release: version bump, `CHANGELOG.md` entry, and the `v*` tag (M7). Per Q2 in section 5c,
  this ships as one act with the work rather than as a separate follow-up.
- All registration and documentation the above requires: `AGENTS.md`, `README.md`,
  `commands/quality-gates.md`, and the SKILL.md frontmatter description.

### Out of scope

| Item | Why |
|---|---|
| A dependency-audit gate | Dropped by author direction; see section 7, follow-up F2. Nothing else in this plan depends on it, and dropping it removes the gate renumbering that would have rippled into `verify-acceptance`. |
| Adding anything to `.github/workflows/lint.yml` | D4. The existing workflow stays exactly as it is; it is neither extended nor deleted. |
| Mutation testing | Cost outruns the confidence it adds for this repository's shape. |
| Coverage-tool cross-check of Gate 2 | Deferred; see section 7, follow-up F1. |
| Any auto-fixing | The skill is report-only by design and stays that way. M4 narrows the rule from "writes nothing" to "writes nothing in the working tree", which is a wording fix, not a new power: the report artifact under `.git/` is the report, in a second form. |
| Wiring `verify-acceptance` to read the JSON report | Optional consumer; adds coupling for little gain now. With the dependency gate dropped, no gate is renumbered, so `verify-acceptance` needs no edit at all. |
| Editing `.claude-plugin/plugin.json` **for component registration** | Components are auto-discovered; `AGENTS.md` forbids editing it for that. The `version` field is a different matter and is in scope; see M7. |

## 5. Milestones

Execute in order. **M2 before M4**, because M4 appends a second stage to the hook file M2
creates (D5). M3, M5, and M6 are independent of each other but M3 and M5 both edit `SKILL.md`,
so run them sequentially to avoid self-conflicts. M6 lands after M1 through M5, since it tests
what they produce. M7 is the release and runs after section 6's verification passes, since it is
the one step that cannot be undone quietly.

### M1: Script the mechanical gates

**Decompose this into three beads, one per script plus its suite.** M1 is three times the size
of every other milestone, and no script imports another, so each is independently reviewable and
independently mergeable. The shared `SKILL.md` edits at the end of this milestone belong to
whichever bead lands last, or to a fourth small bead; either works, as long as one bead owns
them rather than all three editing the same section.

Create, in `skills/quality-gates/scripts/`:

**`check_secrets.py` + `test_check_secrets.py`.** Encode Gate 6 exactly as `SKILL.md` states it
today:

- Secret-file check over both `git ls-files` and `git ls-files --others --exclude-standard`:
  patterns `.env`, `.env.*`, `*.pem`, `*.p12`, `id_rsa`, `*.keystore`, `*credential*`;
  exclusions `.env.example`, `.env.sample`, `.env.template`.
- Content check for prefixed key formats only: `AKIA[0-9A-Z]{16}`, `ghp_`, `xox[baprs]-`,
  `sk-ant-`, `-----BEGIN [A-Z ]*PRIVATE KEY-----`.
- Directory exclusions for both checks: lockfiles, `vendor/`, `node_modules/`, `dist/`,
  `build/`, `*.min.*`, and fixture directories.
- Output is `file:line` plus the pattern name. **The matched value must never appear in any
  output, including test failure messages.** Add a test asserting a planted fake key's value is
  absent from the script's stdout and stderr.
- Exit 0 clean, 1 findings (the skill maps this to FAIL), 2 operator error (BLOCKED).
- The test suite plants fixtures in a temp directory with its own `git init`, covering: a
  tracked `.env`, an untracked-but-unignored `.env` (the case the gate exists to catch, per the
  SKILL.md), an excluded `.env.example`, a fake `AKIA` key in a source file, the same fake key
  in `node_modules/` (must not fire), and a clean tree (exit 0).

**`check_hygiene.py` + `test_check_hygiene.py`.** Count `TODO`, `FIXME`, `HACK`, `XXX` markers
added in the diff against a `--base` argument, using added lines only (the `^+` behavior of the
current recipe, without counting the `+++` header line as a marker). Exit 0 at zero, 1 above
zero (the skill maps this to WARN), 2 operator error. Tests cover: a diff adding two markers, a
diff removing one (count 0), a marker on a `+++ b/TODO.md` header path (must not count), and a
clean diff.

**`changed_set.py` + `test_changed_set.py`.** Resolve the base with the SKILL.md's exact
recipe (merge-base against `origin/HEAD`, falling back to `origin/main`), then print the union
of `git diff --name-only "$BASE"` and `git ls-files --others --exclude-standard`, one path per
line, with the resolved base SHA on stderr. Exit 0 on success, 3 when the base will not resolve
(distinct code so the skill knows to fall back to `--all` rather than treating it as an empty
diff). Tests cover: committed plus staged plus unstaged plus untracked changes all appearing, a
repository with no remote (exit 3), and the base SHA landing on stderr rather than stdout.

Then edit `SKILL.md`:

- Gate 6 and Gate 7 each become "Run the bundled script. Do not hand-roll this check." with the
  invocation (`python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_secrets.py"`,
  same pattern as Gate 5) and an exit-status mapping table. Keep the existing rationale prose
  (why prefixed formats only, why the untracked `.env` matters); the script encodes the rules,
  the prose still explains them. Keep the "prefer a project-configured scanner" preference in
  Gate 6; the script is the built-in fallback.
- Step 2 replaces the two-command recipe with the `changed_set.py` invocation and the exit-3
  fallback rule. Keep the paragraph explaining why `git diff "$BASE"...HEAD` is the wrong basis.

Register: add the three new `test_*.py` invocations to the `AGENTS.md` "Commands for This Repo"
block.

**Acceptance criteria:**

- [ ] All three suites pass with bare `python3` and no third-party imports (grep the scripts
      for `import` lines; everything resolves in the standard library).
- [ ] `check_secrets.py` run against this repository exits 0.
- [ ] The planted-value test proves no secret value reaches output.
- [ ] **Equivalence with the prose it replaces:** every file pattern, key format, and exclusion
      listed in the current Gate 6 text maps to a named test in `test_check_secrets.py`. Record
      the mapping as a comment block at the top of the test file, so a reviewer can check the
      script did not quietly narrow or widen detection. This is the criterion that discharges
      risk R1.
- [ ] `SKILL.md` Gates 6 and 7 and Step 2 invoke the scripts; the old inline recipes are gone.
- [ ] `rumdl fmt --check .` passes.

### M2: Run the repository's checks in a local pre-push hook

Create `.githooks/pre-push`, POSIX sh, executable bit set, modeled on the existing
`.githooks/reference-transaction`. This is stage 1 of the file; M4 appends stage 2.

**What it runs.** The same list section 6 verifies, which is the `AGENTS.md` "Commands for This
Repo" block minus the eval suite:

    rumdl fmt --check .
    node hooks/test-hooks.js
    python3 skills/style-testing/scripts/test_check_framework_leak.py
    python3 skills/style-testing/scripts/check_framework_leak.py
    python3 skills/quality-gates/scripts/test_check_doc_paths.py
    python3 skills/quality-gates/scripts/check_doc_paths.py --repo-root .
    python3 skills/quality-gates/scripts/test_check_secrets.py
    python3 skills/quality-gates/scripts/check_secrets.py
    python3 skills/quality-gates/scripts/test_check_hygiene.py
    python3 skills/quality-gates/scripts/test_changed_set.py

`python3 evals/run.py` is deliberately absent: each case is a real model call, which is far too
slow and too expensive to sit on a push. M6 states how the evals are run instead.

**How it behaves.**

- Off-switch: exit 0 immediately when `TADW_PREPUSH=off`. Document it beside the hook, the way
  `TADW_STYLE_CORE=off` is documented.
- Run every command even after one fails, then report all failures together and exit 1. A hook
  that stops at the first failure makes the author push, fail, fix, push, fail again.
- **A missing tool warns and allows**, following the `reference-transaction` precedent for a
  missing `claude`. `rumdl` and `node` are not universally installed, and a clone that cannot
  push is worse than a push that skipped a formatter. Name the missing tool in the warning.
- A push that only deletes refs has nothing to check; allow.
- Keep it quiet on success: one summary line, not ten.

**Note on `check_doc_paths.py`.** It exits 1 on misses, which the skill maps to WARN, but here a
documented path that does not exist is a real defect: let it fail the push. It lands green, since
as of 2026-08-10 that command exits 0 across all 13 documents it checks.

**Documentation.** `AGENTS.md` has a "Release gate (one-time setup per clone)" section
documenting `git config core.hooksPath .githooks`. Broaden that section to cover both hooks:
retitle it for git hooks generally, keep the existing `reference-transaction` explanation, and
add the pre-push hook with its off-switch. The `core.hooksPath` instruction now serves two
hooks, which strengthens the case for running it on a fresh clone.

**Acceptance criteria:**

- [ ] In a throwaway clone with `core.hooksPath` set, a `git push --dry-run` runs the checks;
      breaking one file's formatting makes the push fail and names that file.
- [ ] With `TADW_PREPUSH=off`, the same broken push proceeds.
- [ ] With `rumdl` removed from PATH, the push proceeds and warns by name.
- [ ] Two simultaneous failures both appear in the output; the hook does not stop at the first.
- [ ] `.github/workflows/lint.yml` is byte-identical to its state before this milestone.
- [ ] `AGENTS.md` documents both hooks under one setup section.

### M3: Evidence citations in Gate 2

Edit `SKILL.md`:

- **Step C (Find what exercises each case):** a counted unit test is cited as the test name
  plus the `file:line` of its key assertion. A counted end-to-end test additionally quotes the
  single line that drives the real entry point (the `subprocess.run`, the HTTP client call, the
  CLI runner invocation), because that line is what distinguishes it from an in-process call.
- **Output format:** update the Change Coverage table columns and the worked example so the
  unit-test cell reads like `test_export_csv` (`tests/test_export.py:41`) and the end-to-end
  cell carries the quoted driving line.
- **Critical Rules, Always:** add "Cite the `file:line` of the assertion behind every counted
  test, and quote the entry-point line behind every end-to-end claim".
- **Quality Checklist:** add a matching checkbox.

The point: "read each test you count" becomes auditable, and a fabricated table becomes
detectably wrong instead of merely plausible.

**Acceptance criteria:**

- [ ] The worked example in the Output Format section shows both citation forms: a unit cell
      carrying `file:line`, and an end-to-end cell carrying a quoted entry-point line.
- [ ] Gate 2 step C states the citation requirement for both test levels.
- [ ] The Critical Rules "Always" list carries the citation rule, and the Quality Checklist
      carries a matching checkbox. Grep for the word "Cite" and expect three hits: step C, the
      rule, and the checkbox.
- [ ] `rumdl fmt --check .` passes.

### M4: Machine-readable verdict, and the second hook stage

**JSON artifact.** Edit `SKILL.md` Step 5: after emitting the markdown report, write
`quality-gates-report.json` inside `git rev-parse --git-dir` (see D3; not a literal `.git/`, which
breaks inside a worktree) in the repository the gates ran against (skip this write, with
a note in the report, when the tree is not a git repository). Schema:

    {
      "version": 1,
      "head": "<git rev-parse HEAD at run time>",
      "dirty": true,
      "timestamp": "<UTC ISO-8601, from date -u>",
      "scope": "changed",
      "gate_source": "AGENTS.md",
      "verdict": "FAIL",
      "gates": [
        {"name": "tests", "status": "PASS", "command": "pytest tests/test_export.py -q", "detail": "14 passed, 0 failed"}
      ]
    }

`dirty` is whether the working tree had uncommitted changes, because the skill usually runs
before the commit and the recorded `head` therefore predates the pushed one. `verdict` is one
of the four Verdict Rules outcomes verbatim: `PASS`, `FAIL`, `INCOMPLETE`, `NO GATES RAN`.

**Reconcile the write with the report-only rules. Do this in the same change, not after.**
Writing the artifact contradicts two lines the skill states about itself today, and a skill that
violates its own Critical Rules on every run is worse than no artifact:

- `SKILL.md:356`, under Critical Rules "Never", reads "Fix, format, or edit anything (this skill
  is report-only, and its report is the deliverable)". Narrow it to the working tree, for
  example: "Fix, format, or edit anything in the working tree (this skill is report-only; its
  report is the deliverable, and the only file it writes is that report's JSON form under
  `.git/`)".
- `SKILL.md:387`, the last Quality Checklist item, reads "No file was edited". Restate it as "No
  file in the working tree was edited; the only write is the report artifact under `.git/`".

Check the same files for any other absolute phrasing of the rule before finishing:
`commands/quality-gates.md` line 22 says "It never fixes, formats, or edits anything", and
`skills/verify-acceptance/SKILL.md` may restate it. Every copy of the claim moves together, or
the next reader finds a contradiction and trusts the weaker one.

**Hook stage 2.** Append to the `.githooks/pre-push` file M2 created, after the suite stage:

- Read `quality-gates-report.json` from `$(git rev-parse --git-dir)` via `python3 -c`; do not parse
  JSON in sh, and do not hardcode `.git/`. The skill writes it to the same resolved path, so a
  worktree's hook reads that worktree's own verdict.
- No report, or unreadable report: print one warning line naming the file and `/quality-gates`,
  then allow. A missing report is not proof of a problem.
- Verdict `FAIL`: print the verdict, the recorded `head`, and the timestamp, then exit 1. Name
  the two exits in the message: re-run `/quality-gates` to refresh the verdict, or set
  `TADW_PREPUSH=off` for this push.
- Any other verdict: allow, and print a staleness warning when the recorded `head` is not an
  ancestor of the pushed commit (`git merge-base --is-ancestor`).

**Documentation.** In `AGENTS.md` "Landing the Plane" step 4, add one line noting the push is
refused when the last recorded verdict is FAIL. In `commands/quality-gates.md`, mention the JSON
artifact and its path.

**Acceptance criteria:**

- [ ] With a hand-written FAIL report in `.git/`, `git push --dry-run` in a throwaway clone is
      refused; with `TADW_PREPUSH=off`, it proceeds. Verify in a throwaway clone, never by
      pushing this repository anywhere.
- [ ] With no report file, a push proceeds with a single warning line.
- [ ] The suite stage and the verdict stage both live in one `.githooks/pre-push` file, and a
      failure in either is reported with its own message.
- [ ] No line in `skills/quality-gates/SKILL.md`, `commands/quality-gates.md`, or
      `skills/verify-acceptance/SKILL.md` still claims the skill writes nothing. Grep for
      "edit" and "No file" and confirm each hit carries the working-tree qualifier.
- [ ] `node hooks/test-hooks.js` still passes. Its `docs/HOOKS.md` assertion counts that
      suite's own JavaScript checks, not git hooks, and `docs/HOOKS.md` documents no git hook
      today, so adding `.githooks/pre-push` cannot move that number.

### M5: Concrete prompt-assets checklist

Edit the prompt-assets row of Gate 2's shape table (and add a short subsection below the table,
since a table cell cannot hold a checklist). For a prompt-asset change, "exercised" means:

1. `claude plugin validate .` passes, so the frontmatter parses.
2. The component is registered in both places `AGENTS.md` "Common Tasks" names: the name list
   in `AGENTS.md` and the description table in `README.md`.
3. Some agent or command references the skill, or it is a documented accepted orphan (the
   `business-ideas` / `idea-wizard` precedent in `AGENTS.md`).
4. Every command embedded in the asset is valid: scripts it names exist at the stated paths,
   and flags it shows match the script's argparse.
5. Where the repository has an eval harness (`evals/` here), a change to behavior-bearing prose
   carries an eval case, and its absence is a WARN naming the harness.

Item 5 is what connects this gate to M6. After M6 lands, a change to `SKILL.md`'s verdict rules
with no matching eval case is a gap this gate reports.

**Acceptance criteria:**

- [ ] Each of the five checklist items names a command or a grep a second person can run, and
      none asks for a judgment about prose quality. Write the command beside each item in the
      SKILL.md subsection, not just the intent.
- [ ] Running the five items against this plan's own M1 output produces a pass on items 1, 3,
      and 4, and a defensible verdict on 2 and 5. New scripts are not components, so item 2 is
      N/A for them; state that in the subsection so the next reader does not report a false gap.
- [ ] `rumdl fmt --check .` passes.

### M6: Fixture-repo evals of the skill's behavior

This is the only milestone that tests what the skill concludes, rather than what its scripts
compute. It protects every rule M1 did not convert into a script, and it is the reason the
verdict rules cannot silently regress.

**Extend the harness.** `evals/run.py` today builds one command,
`claude -p <prompt> --model <model> [--plugin-dir REPO_ROOT]`, and always runs it with
`cwd=REPO_ROOT` (see `ask()`). Two additions, both small:

- An optional `fixture` key in `case.json`. When present, the harness copies
  `evals/fixtures/<fixture>/` to a temp directory, runs `git init` plus an initial commit there,
  applies the case's planted defect, and passes that directory as `cwd` instead of `REPO_ROOT`.
- An optional `single_arm` key. When true, run only the with-plugin arm. Per D7,
  `/quality-gates` does not exist without the plugin, so a baseline arm would measure nothing.

Keep the existing regex graders. They are enough: the assertions here are about which verdict
string and which status word appear in the report.

**Four fixture cases**, each planting one defect and asserting the specific status the skill's
rules demand, not merely that something failed:

| Case | Planted defect | Must report | Must not report |
|---|---|---|---|
| `gates-untested-change` | A new function with a branch and no test anywhere | Gate 2 FAIL, and the case enumerated | PASS |
| `gates-planted-secret` | A fake `AKIA` key in a source file | Secrets FAIL with a `file:line` | The matched value anywhere in the report |
| `gates-blocked-not-skip` | A type checker configured in `pyproject.toml` but absent from PATH | BLOCKED, and overall FAIL | SKIP |
| `gates-all-skip` | A repository where every gate legitimately skips | NO GATES RAN | PASS |

The last two are the regression tests for the exact bug commit `a093acc` fixed. They are the
cases most worth having and the ones no script can cover.

**How the evals are run.** By hand and in review, not on every push: each case is a real model
call, three runs per case per `evals/README.md`, so the suite is slow and costs money. Add
`python3 evals/run.py` to section 6's verification list, and leave it out of the pre-push hook
(M2 already states this).

**Acceptance criteria:**

- [ ] `python3 evals/run.py` still passes the six existing response-style cases unchanged, so
      the harness extension broke nothing.
- [ ] Each of the four fixture cases passes three runs out of three with the plugin loaded.
- [ ] `gates-blocked-not-skip` fails when the SKILL.md line mapping a missing binary to BLOCKED
      is reverted by hand. Prove the test detects the regression rather than passing by
      accident, then restore the line.
- [ ] `gates-planted-secret` asserts the fake key's value is absent from the report, matching
      the same rule `test_check_secrets.py` pins at the script level.
- [ ] `evals/README.md` documents the `fixture` and `single_arm` keys and says why fixture
      cases are single-arm.

### M7: Release

Runs last, after section 6's verification passes. Everything before this milestone is inert for
anyone consuming the plugin from the marketplace rather than from `main`.

- **Version.** Bump `version` in `.claude-plugin/plugin.json` from `2.5.2` to **`2.6.0`**. Minor,
  not patch: this adds three scripts, a git hook, a report artifact, and new eval machinery, all
  backward compatible with existing invocations.
- **Changelog.** Add a `## [2.6.0] - <date>` section to `CHANGELOG.md` above `## [2.5.2]`,
  in Keep a Changelog form, and move anything sitting under `## [Unreleased]` into it. Sections
  in the order the entries call for: `Added` for the three scripts, the pre-push hook, the JSON
  artifact, and the fixture evals; `Changed` for the Gate 2 citation requirement and the
  report-only rule narrowing. Match the existing entries' voice: each bullet leads with a bolded
  sentence stating what changed and why it mattered, not a bare feature name.
- **Link references.** Update the two lines at the foot of `CHANGELOG.md`: point `[Unreleased]`
  at `v2.6.0...HEAD`, and add a `[2.6.0]` line comparing `v2.5.2...v2.6.0`.
- **Tag.** `git tag v2.6.0`, which fires `.githooks/reference-transaction` and refuses the tag
  when `claude plugin validate` fails. Push the tag.

**Acceptance criteria:**

- [ ] `.claude-plugin/plugin.json` reads `"version": "2.6.0"`, and no other file still claims
      2.5.2 outside `CHANGELOG.md` history.
- [ ] `CHANGELOG.md` has a `2.6.0` section covering every user-visible change in M1 through M6,
      an empty `## [Unreleased]`, and both link-reference lines updated.
- [ ] `git tag v2.6.0` succeeds, meaning the release gate accepted it. If the hook refuses, fix
      what `claude plugin validate` reports; never bypass with `--no-verify`.
- [ ] `git push --follow-tags` leaves `git status` reporting up to date with origin.

## 5a. Risks and Mitigations

| ID | Risk | Likelihood | Mitigation |
|---|---|---|---|
| **R1** | `check_secrets.py` is stricter or looser than the prose it replaces, so a key the model would have caught now passes silently. | Medium | Every pattern and exclusion in the current Gate 6 prose maps to a named test in `test_check_secrets.py`, recorded as a comment block at the top of that file. This is an M1 acceptance criterion, and M6's `gates-planted-secret` case checks the same rule end to end. |
| **R2** | The pre-push hook misfires and gets disabled wholesale, losing the enforcement it exists to add. | Medium | D6 keeps it forgiving where forgiveness is right: a missing tool warns, a missing verdict report warns, and `TADW_PREPUSH=off` is a documented per-push escape rather than an undocumented workaround. It blocks only on a real failure or a recorded FAIL. |
| **R3** | The hook slows every push enough to be resented. | Medium | The suite is stdlib Python plus one small Node script and a formatter check, all of which run in seconds. `evals/run.py` is explicitly excluded, since it is the only slow one. Measure the hook's wall time during M2 and state it in the `AGENTS.md` section. |
| **R4** | M1 grows past one reviewable change, since it is three scripts and three suites. | High | Decompose into three beads, one per script plus its suite; each is independently mergeable because no script imports another. Stated at the head of M1. |
| **R5** | A local hook is per-clone config and `--no-verify` bypasses it, so enforcement is weaker than a CI check. | High | **Accepted, by author direction (D4).** The `core.hooksPath` setup is documented in `AGENTS.md` and now serves two hooks, which raises the odds a fresh clone runs it. `.github/workflows/lint.yml` keeps its existing checks, so the hosted safety net is not removed, only not extended. |
| **R6** | The four fixture evals pass for the wrong reason, since a model can produce the right verdict word by luck. | Medium | M6 requires proving `gates-blocked-not-skip` fails when the rule it tests is reverted by hand. A test never observed failing is not yet a test. |
| **R7** | M7 tags a version whose behavior nobody exercised. | Low | Weaker than it was: M6 now exercises the skill's behavior directly, and section 6 ends by running `/quality-gates` against this plan's own change. The `v*` release gate is the mechanical backstop. |
| **R8** | An `AGENTS.md` edit breaks the name-list parsing that `hooks/test-hooks.js:432` asserts. | Low | Accepted. The suite fails loudly, now on every push rather than only in CI, and this plan adds no component, so the counts 36/12/29 do not move. |

## 5b. Dependencies

| Dependency | Needed by | Status |
|---|---|---|
| Python 3, standard library only | M1, M2, M4, M6 | Available; already required by three shipped scripts, and D1 forbids third-party imports. |
| `git` with `core.hooksPath` support | M2, M4, M7 | Available; `.githooks/reference-transaction` already relies on it. Note that `core.hooksPath .githooks` is per-clone config, so a fresh clone must set it before either hook fires. This is R5. |
| `rumdl` | Every milestone | Available locally, and pinned at v0.2.18 in the existing workflow. The hook warns and allows when it is missing (D6). |
| `node` | M2's hook stage 1 | Available; runs `hooks/test-hooks.js`. Same warn-and-allow rule. |
| `claude` CLI | M5, M6, M7 | Available locally. M6 calls it for real on every eval run, which is what makes that suite slow and paid. `.githooks/reference-transaction` warns and allows when it is absent, so its absence degrades the release gate rather than blocking the work. |
| A scratch git remote for the hook tests | M2, M4 | Created on demand in a temp directory; nothing is pushed to a real remote. |

No dependency blocks milestone 1.

## 5c. Open Questions

Both questions are answered. They are kept here with their answers so a later reader sees the
decision and its reason rather than re-opening it.

| ID | Question | Answer |
|---|---|---|
| **Q1** | Should the dependency gate join `verify-acceptance`'s four-gate subset? | **Moot.** The dependency gate left this plan's scope entirely (section 7, F2). `verify-acceptance` needs no edit, because nothing renumbers a gate any more. The original answer, had the gate stayed, was no: each skill stays separate and atomic. |
| **Q2** | Should the release be part of this plan or a separate act? | **Part of this plan**, as M7, so the work ships without a second pass. It runs last, after section 6's verification. |

Resolved by grounding during review, recorded so neither is re-investigated:

- The `docs/HOOKS.md` count that `hooks/test-hooks.js:774` asserts counts that suite's own
  JavaScript checks, not git hooks, and `docs/HOOKS.md` documents no git hook today. Adding
  `.githooks/pre-push` cannot move that number.
- `python3 skills/quality-gates/scripts/check_doc_paths.py --repo-root .` exits 0 today across
  13 documents, so M2's hook stage lands green rather than red.
- `evals/run.py` builds its command in `ask()` and hardcodes `cwd=REPO_ROOT`, which is the exact
  line M6 must extend for fixture cases.

## 6. Verification, whole plan

After all milestones, from the repository root:

    rumdl fmt --check .
    node hooks/test-hooks.js
    python3 skills/style-testing/scripts/test_check_framework_leak.py
    python3 skills/style-testing/scripts/check_framework_leak.py
    python3 skills/quality-gates/scripts/test_check_doc_paths.py
    python3 skills/quality-gates/scripts/check_doc_paths.py --repo-root .
    python3 skills/quality-gates/scripts/test_check_secrets.py
    python3 skills/quality-gates/scripts/test_check_hygiene.py
    python3 skills/quality-gates/scripts/test_changed_set.py
    python3 evals/run.py
    claude plugin validate .

Every command above except `evals/run.py` also runs from the pre-push hook, so the hook firing
clean is itself most of this list. Run `evals/run.py` by hand here, since M2 excludes it from the
hook on cost grounds.

Then run `/validate-plugin`, and finally run `/quality-gates` itself against the finished
change: the skill grading its own hardening is the acceptance test, and its report should show
the new scripts under the Tests gate and the JSON artifact in `.git/`.

Land per "Landing the Plane" in `AGENTS.md`: file follow-up beads (section 7), close finished
beads, `git pull --rebase`, `br sync --flush-only`, push, and verify `git status` is clean and
up to date.

**Then execute M7.** The release is the last act, after every check above is green. Tagging a
broken version is the one mistake in this plan that reaches other people, which is why M7 sits
behind the verification rather than beside the work.

## 7. Follow-ups to file as beads, not to build now

File both with `br create`, category label per the tracker convention, referencing this plan.

**F1: Coverage-tool cross-check for Gate 2.** When the project configures a coverage tool
(`pytest --cov`, simplecov, istanbul), run the selected tests under it and report changed-line
coverage beside the case table as evidence, not as a threshold. A case the table calls covered
whose lines never executed is a finding, in either direction. Skip silently when no tool is
configured; never ask a project to add one.

**F2: Gate 8, dependency audit.** Add a gate for known-vulnerable dependencies, between Secrets
and Hygiene. Prefer a project-configured auditor found in the skill's Step 1 sources; otherwise
fall back by manifest (`npm audit --omit=dev`, `pip-audit`, `bundle audit check --update`,
`cargo audit`, or `osv-scanner` for any of them). Critical and high findings are FAIL; moderate
and low are WARN with counts per severity. SKIP when no manifest exists, or when a manifest
exists but no auditor is installed and the project configures none, with the reason stated.
BLOCKED only when the project itself configures an auditor that will not run, which deliberately
differs from Gate 4's stricter rule, because treating "`pip-audit` not installed" as BLOCKED
would fail nearly every Python repository. Scope it whole-manifest like Secrets, never narrowed
by `--changed`.

Note for whoever picks this up: adding a gate between Secrets and Hygiene renumbers Hygiene, and
`skills/verify-acceptance/SKILL.md:89-91` enumerates the gates by name. Update its skip line so
the new gate's absence from its four-gate subset reads as a decision rather than an oversight.
This repository has no dependency manifest, so the gate will grade SKIP here and cannot be
exercised end to end without a fixture.

## 8. Constraints for the executing agent

- Never use em-dashes or en-dashes anywhere: prose, code, comments, commit messages. Use a
  comma, colon, parentheses, or a plain hyphen.
- The skill stays report-only. No milestone gives it fixing behavior.
- Do not add anything to `.github/workflows/lint.yml`, and do not delete it either (D4).
- Do not edit `.claude-plugin/plugin.json` for component registration; components are
  auto-discovered. The `version` field in M7 is the one permitted edit.
- Match `check_doc_paths.py`'s conventions for every new script, including the docstring that
  states why the script exists.
- Every markdown edit must survive `rumdl fmt --check .` before commit.
