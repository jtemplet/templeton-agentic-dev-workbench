---
name: quality-gates
description: "Run the project's QA gates against the change: tests, change coverage, lint, type check, doc freshness, secrets, hygiene. Scoped to what changed by default. Takes the gate list from what the project declares, not from guesswork. Proves the change is exercised at both the unit and the end-to-end level, and hands browser UI work to /qa rather than passing it silently. Report-only."
---

# Quality Gates

Runs the checks that decide whether a change is fit to commit, then reports one table with the exact command and the real numbers behind every row. It does not fix anything it finds.

The subject is **the change**, not the repository. A repository-wide sweep that says nothing about whether the new code is exercised has answered the wrong question.

## When to Use / When NOT to Use

Use when:

- Ending a work session, as step 2 of "Landing the Plane"
- Before opening a pull request, or before `br close`
- After a fresh-eyes review, as the last step of the code-quality pipeline
- When asked "does this pass QA?", "run the checks", or "is the build clean?"

Do NOT use when:

- The change is browser UI. Use `/qa`, which drives a real browser and fixes what it finds, or `/qa-only` for a report. Gate 2 below detects this and hands off.
- Looking for bugs in changed code (use `review-fresh-eyes`)
- Grading work against its acceptance criteria (use `verify-acceptance`, which runs a subset of these gates as part of its own report)
- Reviewing style or design (use the matching `review-*` or `style-*` skill)

## The Three Rules That Make This Worth Running

**1. The gate list comes from the project, not from the file extensions.** Guessing gates from language defaults finds `pytest` and `eslint` and misses everything a project actually runs. A repository with no `package.json` and no `pyproject.toml` is not a repository with no checks. Step 1 reads what the project declares before it guesses, and the report names the source it used.

**2. A green suite is not a tested change.** A suite passes whether or not anything touches the new code. Gate 2 asks the separate question: is every case this change introduces exercised, at both the unit level and the end-to-end level the project's shape demands, and do those tests span the case rather than hitting one point in it. That gate is the reason to run this skill rather than the test command by hand.

Its counterweight is in the same gate. Spanning a case means covering each class of input, state, and outcome once, not their cross-product. A gate that asks for exhaustive tests, or for defensive code around failures that cannot happen, costs more than the bugs it prevents.

**3. A gate that could not run is not a gate that passed.** "No linter is configured" and "the linter is configured but not installed" are different facts, and only the first is a skip. Collapsing them means a broken toolchain reports a clean bill of health. The second is BLOCKED, and BLOCKED fails the run.

## Status Model

Every gate ends in exactly one of these.

| Status | Means | Effect on overall |
|---|---|---|
| **PASS** | The gate ran and found nothing | None |
| **FAIL** | The gate ran and found a defect | Overall FAIL |
| **WARN** | The gate ran and found something below the fail bar | None, but it is reported |
| **SKIP** | The gate does not apply: nothing of that kind is configured, or the change has no such surface | None |
| **BLOCKED** | The gate applies but could not run: missing binary, exit 127, timeout, crash | Overall FAIL |
| **HANDOFF** | The change needs a check this skill cannot perform, and another tool owns it | Overall INCOMPLETE |

Never record BLOCKED or HANDOFF as SKIP to keep a report tidy. Those distinctions are the point.

## Required Workflow

### Step 1: Discover the Gate Set

Search these sources in order and stop at the first that yields commands. Record which one you used.

1. **`AGENTS.md` or `CLAUDE.md`**, for a section naming the project's own checks. This is the most reliable source, because a human wrote it for this purpose.
2. **CI config**, usually `.github/workflows/*.yml`. What CI runs is the authoritative definition of the gates, so prefer it over any inference.
3. **A task runner**: `Makefile` targets, `package.json` scripts, `justfile`, `Taskfile.yml`.
4. **Language auto-detect**, as the fallback. Detect by config file, not by binary: `pyproject.toml` or `setup.cfg` for Python, `Gemfile` for Ruby, `package.json` for Node, `go.mod` for Go, `Package.swift` for Swift.

A project command found in sources 1 to 3 **replaces** the auto-detected equivalent; it does not run beside it. If `AGENTS.md` names `rumdl fmt --check .` as the format check, that is the lint gate. Do not also run a linter the project never mentions.

Map every discovered command onto the gate it serves. A command that fits no gate below still runs, under a **Project checks** row.

### Step 2: Set the Scope

**`--changed` is the default.** Run `--all` only when the caller asks for it, or when the base will not resolve.

Resolve the base once:

```bash
git merge-base HEAD "$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD || echo origin/main)"
```

If that fails, on a repository with no remote, a shallow clone, or a first commit, run at `--all` and say so. An unresolvable base is not an empty diff, and treating it as one narrows every gate to nothing.

Then build the changed set from the working tree:

```bash
git diff --name-only "$BASE"                # committed, staged, and unstaged
git ls-files --others --exclude-standard    # new files, not yet tracked
```

Both lines matter. This skill runs before a commit more often than after one, so `git diff "$BASE"...HEAD` is the wrong basis: it stops at the last commit and misses the very work being checked. Untracked files need the second command, because `git diff` never sees them.

| Gate | At `--changed` (default) | At `--all` |
|---|---|---|
| Tests | The tests that cover the changed code | The whole suite |
| Change coverage | The cases in the diff | The cases in the diff (unchanged; this gate is always about the change) |
| Lint, doc freshness, hygiene | Changed files only | Whole tree |
| Type checking | Analyze the whole project, report only errors in changed files | Analyze and report whole-project |
| Secrets | Whole tree | Whole tree |

Two rows need their reasoning stated, because getting them wrong produces a confident wrong answer:

- **Type checking always analyzes the whole project.** A type error usually surfaces in the file that consumes the changed one. Checking a subset of files reports clean while the project does not compile. Narrow the report, never the analysis.
- **Secrets always cover the whole tree.** The scan is cheap, and a key committed three months ago is still a key.

**Select the covering tests like this**, and keep what the selection tells you:

1. Map each changed source file to its test file by the project's convention: `foo.py` to `test_foo.py` or `foo_test.py`, `foo.rb` to `foo_spec.rb`, `Foo.ts` to `Foo.test.ts`.
2. Grep the test tree for the symbols the diff added or changed, to catch tests that live elsewhere.
3. Run that set by path or by name.

A changed source file that maps to no test and appears in no test is not a selection problem. It is a Gate 2 finding, and it carries into that gate.

**Say plainly in the report that the full suite did not run.** A scoped run is the right default and a partial answer, and a reader who takes it for a full one has been misled by the report, not by the scope.

### Step 3: Run Each Gate

Run them in order and keep going after a failure; a FAIL in gate 1 does not excuse skipping gate 6. Give every command a bounded timeout, 600 seconds unless the project says otherwise. On timeout, record BLOCKED with the elapsed time rather than waiting.

Capture, for every gate: the exact command, the exit code, and the counts. You need all three for the report.

#### Gate 1: Tests

Run the selected tests from Step 2. Record passed, failed, skipped, and errored counts, and name the selection.

An exit code of 127, a missing runner, or a collection error is BLOCKED, not FAIL. Zero tests collected in a project that has a test directory is BLOCKED too, because the runner found nothing to check.

#### Gate 2: Change Coverage

The gate that answers rule 2. A passing suite says the old code still works. This says the new code is exercised.

**A. Detect the shape of what changed.** Use the changed files, not the repository as a whole.

| Shape | Signals in the diff | What end-to-end means here |
|---|---|---|
| **CLI** | `console_scripts`, `bin/`, a shebang entry point, `argparse`, `click`, `thor`, `cobra` | Invoke the built command the way a user does: real argv, real exit code, real stdout and stderr |
| **API service** | Route or handler definitions, and no browser UI in the diff | Drive the route through the real HTTP stack: status code, body shape, auth, and the error responses |
| **Library** | An importable package with no entry point | The public API is the surface. There is no separate end-to-end level |
| **Browser UI** | Templates, components (`.tsx`, `.vue`, `.erb` views), stylesheets | This skill cannot settle it. HANDOFF |
| **Mobile UI** | App-target Swift or Kotlin screens | This skill cannot settle it. HANDOFF |
| **Prompt assets** | Skills, agents, commands, or other instructions an LLM reads at runtime | The structural invariants: the asset parses, it is registered where the project says, and its embedded commands are valid |

A change can touch two shapes. Grade each, and take the worst result.

The prompt-assets row is here because the table did not have it on first use, and this repository is one. A shape with no row does not mean the gate does not apply. It means the row is missing, so say so and grade what you can.

**B. Enumerate the cases the change introduces.** Number them, because a case you did not list cannot be graded:

- Each new or changed function, and each branch inside it
- Each new CLI flag, subcommand, or positional argument
- Each new or changed route, status code, and error response
- Each error path: a raised exception, a non-zero exit, a 4xx or 5xx

**C. Find what exercises each case.** Two rules, both required for CLI and API shapes:

- **Unit.** Every case has a test that exercises it. Find it by symbol, run it by name, keep the output.
- **End to end.** Every surface the change touches has at least one test that drives it through the real entry point. A test that imports the handler and calls it directly is a unit test wherever it lives, and does not satisfy this.

Read each test you count. A test that runs the case without asserting anything about it does not cover it.

**D. Check the span, not just the presence.** A case has a span: the distinct classes of input, state, and outcome it can take. One test proves one point in that span. Ask which classes exist, then which are hit:

| Dimension | Classes worth naming |
|---|---|
| Input | Empty, one, many. Valid, invalid, malformed |
| Boundary | Zero, the edge and one past it, the maximum |
| State | First run against repeat, present against absent, permitted against refused |
| Outcome | Success, and each distinct failure the case can produce |

Report the span as classes covered out of classes identified, and name the ones with nothing on them. Five tests of the same class cover one point, not five, and a coverage percentage will not tell you that.

**E. Stay proportionate.** The span is a map of what matters, not a demand for the cross-product. This gate fails work that is untested, not work that is tested less than exhaustively.

- Cover each class once. Do not ask for combinations of classes without a reason to expect they interact.
- Do not ask for a test of a branch unreachable through the public interface.
- Do not ask for tests of code this change did not touch.
- Do not ask for a case that an existing test already covers at another level. Say which test, and move on.
- Do not ask for defensive code: a nil check the type already guarantees, a `try` around code that cannot raise, a re-validation the caller performed. This gate must not create pressure to add them.

When you are unsure whether a class is worth a test, ask what a real failure there would cost. Cheap and recoverable is a WARN at most.

**F. Grade.**

| Result | When |
|---|---|
| **PASS** | Every case has a unit test, every touched surface has an end-to-end test, and every span class you identified is covered |
| **WARN** | Every case is tested, but a span class is not, and a failure there would be cheap to notice and to recover from |
| **FAIL** | Any case has no test at all, any touched CLI command or HTTP route has no end-to-end test, or an uncovered span class would fail expensively: lost data, wrong money, a security hole, or silent corruption |
| **HANDOFF** | The diff touches browser or mobile UI. Name `/qa` for a test-and-fix pass, or `/qa-only` for a report |
| **SKIP** | The diff changes no behavior: documentation, comments, or formatting only |

Report the cases as a table: number, case, unit test, end-to-end test, span covered. An empty cell is the finding.

#### Gate 3: Lint and Format

Run the project's linter and formatter check. Record error and warning counts separately, because most linters fail on the first and not the second.

#### Gate 4: Type Checking

Run the project's type checker over the whole project, then report the errors in changed files. Record both numbers when they differ, so a pre-existing backlog does not read as new breakage. SKIP only when no type checker is configured; a configured checker that will not start is BLOCKED.

#### Gate 5: Documentation Freshness

Run the bundled script. Do not hand-roll this check.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_doc_paths.py" --repo-root .
```

Pass document paths as arguments to narrow it under `--changed`. With none, it checks `README.md`, `AGENTS.md`, `CLAUDE.md`, and every markdown file under `docs/`.

**Why a script and not a method.** This gate was three prose steps until it met a real repository. Told to extract "tokens that look like a path", the first run reported **194 missing paths, none of them real**: slash commands, `<name>` placeholders, and a worked example in this file's own text. A gate that cries wolf gets ignored, and the real miss gets ignored with it. The script encodes the three rules that cut those 194 to zero, and `test_check_doc_paths.py` pins each one.

Map its exit status like this, and note that it differs from every other gate:

| Exit | Status |
|---|---|
| 0 | PASS |
| 1 | **WARN**, with the reported misses. A doc naming a path that does not exist is worth reporting and is not a reason to block a commit |
| 2 | BLOCKED. The operator gave it a document or a root that does not exist |

A path that a documented tool creates at runtime is not a broken reference. `docs/roadmap.html` does not exist until someone runs the dashboard. Those belong in `.docpaths-ignore` at the repository root, with a `doc:` prefix to skip a whole document, and the entry needs a reason beside it.

**Do not judge whether the prose still describes the behavior.** That is not checkable from here, and an invented answer is worse than an honest skip. If the project has its own doc-consistency check, Step 1 will have found it, and this gate defers to it.

#### Gate 6: Secrets

Prefer a scanner the project already configures (`gitleaks`, `detect-secrets`, `trufflehog`) and name it in the report. Otherwise run the built-in checks:

1. **Secret files.** Search both `git ls-files` and `git ls-files --others --exclude-standard` for `.env`, `.env.*`, `*.pem`, `*.p12`, `id_rsa`, `*.keystore`, `*credential*`. Exclude `.env.example`, `.env.sample`, and `.env.template`. Scan the untracked list too: an untracked `.env` that git does not ignore is one `git add -A` away from being committed, and that is the case this gate exists to catch.
2. **Prefixed key formats**, which are high-signal: `AKIA[0-9A-Z]{16}`, `ghp_`, `xox[baprs]-`, `sk-ant-`, `-----BEGIN [A-Z ]*PRIVATE KEY-----`.

Exclude lockfiles, `vendor/`, `node_modules/`, `dist/`, `build/`, `*.min.*`, and fixture directories from both.

Match on prefixed formats only. Generic long hex or base64 matching fires on lockfile hashes, test fixtures, and minified assets, and a gate that cries wolf gets ignored.

Either check hitting is FAIL. **Report the `file:line` and the pattern name, never the matched value.** A report that quotes the secret copies it into one more place.

#### Gate 7: Hygiene

Count `TODO`, `FIXME`, `HACK`, and `XXX` markers **added in the diff**:

```bash
git diff --unified=0 "$BASE" | grep -c '^+.*\(TODO\|FIXME\|HACK\|XXX\)' || true
```

Keep the `|| true`. `grep -c` exits 1 when it counts zero, which is the clean result, and a bare non-zero exit here would be read as BLOCKED.

Status is WARN when the count is above zero. Under `--all` you may report the repository total, labeled as context rather than as a finding. A count of markers someone else added years ago changes nothing the reader can act on.

### Step 4: Attribute Every Failure

For each FAIL, say whether it looks new. A failing test in a file the diff does not touch, exercising code the diff does not touch, is probably pre-existing, and the report should say so as evidence rather than as a verdict.

Write the evidence: "3 failures, all in `tests/legacy/`, which this diff does not touch." Do not write "pre-existing" alone.

Establish this by reading, never by rewriting the working tree. Do not stash, check out the base, or reset to get a baseline. If the caller needs certainty, say that re-running on the base commit would settle it.

### Step 5: Report

Emit the report below, then stop.

## Output Format

```markdown
## Quality Gates Report

**Gate source:** AGENTS.md "Commands for This Repo" | .github/workflows/lint.yml | auto-detected
**Scope:** changed (12 files vs `abc1234`). The full suite did not run.
**Change shape:** CLI

| Gate | Status | Command | Result |
|---|---|---|---|
| Tests | PASS | `pytest tests/test_export.py -q` | 14 passed, 0 failed (selected, not the full suite) |
| Change coverage | FAIL | case review over 6 cases | 5 of 6 have unit tests, 0 end-to-end, span 7 of 11 |
| Lint | FAIL | `ruff check src/export.py` | 2 errors, 11 warnings |
| Type checking | BLOCKED | `mypy .` | exit 127, mypy not installed |
| Doc freshness | WARN | path check over 3 docs | 1 missing path |
| Secrets | PASS | `gitleaks detect` | 0 findings |
| Hygiene | WARN | diff marker count | 2 TODOs added |
| Project checks | PASS | `node hooks/test-hooks.js` | 19 checks, 0 failed |

### Overall: FAIL

<One sentence naming what decided it.>

### Change Coverage

| # | Case | Unit test | End to end | Span covered |
|---|---|---|---|---|
| 1 | `--format=csv` flag | `test_export_csv` | - | 2 of 3: one row and many rows. Nothing covers an empty result set |
| 2 | `--format` rejects an unknown value | `test_export_bad_format` | - | 1 of 1 |
| 3 | Exit code 2 on a missing input file | - | - | 0 of 2 |

No test invokes the `export` command through its entry point, so argv parsing and
exit codes are unexercised. Case 3 has no test at either level.

Case 1's empty result set is the span gap worth closing: an export that writes a
header and no rows is the shape a caller is most likely to mishandle. I did not
ask for the format-by-row-count cross-product, since nothing suggests those
interact.

### Failures

**Lint** (`ruff check src/export.py`)

<the actual command output, trimmed to the failing lines>

`src/export.py:88` and `src/export.py:94`, both in files this diff touches.

**Type checking** (`mypy .`)

`mypy: command not found`. The gate is configured in `pyproject.toml`, so this is
not a skip. Install it or remove the configuration.

### Action Items

1. Add an end-to-end test that runs `export --format=csv` and asserts the exit code
2. Add a test for the missing-input-file path (case 3)
3. Fix the two ruff errors in `src/export.py`
4. Install mypy, then re-run the type gate
```

Omit the Failures section when nothing failed. Omit the Change Coverage table only when that gate is SKIP. Never omit a gate row; a gate that did not run gets its row with SKIP, BLOCKED, or HANDOFF and a reason.

## Verdict Rules

Apply these in order and stop at the first that matches. They are exhaustive, so every run gets exactly one verdict.

1. **FAIL** if any gate is FAIL or BLOCKED.
2. **INCOMPLETE** if any gate is HANDOFF. Name the tool that owns the rest.
3. **NO GATES RAN** if no gate reached PASS, WARN, or FAIL, meaning every gate skipped.
4. **PASS** otherwise: at least one gate ran, and none of them failed.

WARN never changes the overall result, and a run that is all WARN and SKIP is a PASS with warnings noted. SKIP never changes it either. A run where everything skipped proves nothing, and reporting that as PASS is the reading this skill exists to refuse.

The order is load-bearing. An all-BLOCKED run is a FAIL by rule 1 and never reaches rule 3, because a toolchain that cannot start is a worse result than no toolchain at all.

**INCOMPLETE is not a soft pass.** It means the part this skill can check is clean and the part it cannot check has not been checked by anyone yet.

## Critical Rules

**Always:**

- Name the source the gate list came from, and the scope you ran at
- Say the full suite did not run, whenever it did not
- Put the exact command in the table, so a reader can re-run it
- Report real counts in every non-SKIP row
- Enumerate the change's cases before grading coverage, and show the table
- Name each case's span classes, and which of them nothing covers
- Weigh an uncovered span class by what a failure there would cost
- Analyze types over the whole project, even when reporting only the changed files
- Record a configured-but-unrunnable gate as BLOCKED
- Give the reason beside every SKIP
- Print the failing command's real output for every FAIL
- Report `file:line` for a secret finding, never the matched value

**Never:**

- Fix, format, or edit anything (this skill is report-only, and its report is the deliverable)
- Report a gate as "green", "clean", or "passing" without its numbers
- Treat a passing suite as evidence that the change is tested
- Count a test you have not read, or one that exercises a case without asserting it
- Read one passing test as coverage of a case's whole span
- Call an in-process call of a handler an end-to-end test
- Ask for the cross-product of span classes, for a branch unreachable through the public interface, or for a test of code this change did not touch
- Ask for defensive code: a nil check the type guarantees, a `try` around code that cannot raise, or a re-validation the caller already performed
- Downgrade BLOCKED or HANDOFF to SKIP, or let an all-SKIP run report PASS
- Pass a browser UI change silently; hand it to `/qa`
- Run a language default beside a project command that serves the same gate
- Stash, reset, or check out another commit to establish a baseline
- Claim doc prose is stale without a missing path to point at

## Quality Checklist

Before reporting completion, verify:

- [ ] The gate source, the scope, and the change shape all appear in the report
- [ ] The report says whether the full suite ran
- [ ] Every gate has a row, including the ones that did not run
- [ ] Every non-SKIP row carries its exact command and a real count
- [ ] Every case the change introduces appears in the coverage table
- [ ] Every case names its span classes, and the uncovered ones are called out
- [ ] Every test counted as coverage was read, not just found by name
- [ ] Nothing asked for is a cross-product, an unreachable branch, or a defensive check
- [ ] No configured gate is recorded as SKIP
- [ ] A browser or mobile UI change is HANDOFF, never PASS
- [ ] Every FAIL shows real command output, and says whether it looks new
- [ ] No secret value was copied into the report
- [ ] The overall verdict follows the Verdict Rules mechanically
- [ ] No file was edited
