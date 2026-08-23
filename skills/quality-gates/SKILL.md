---
name: quality-gates
description: "Run the project's QA gates against the change: tests, change coverage, live API probe, lint, type check, doc freshness, secrets, hygiene. Scoped to what changed by default. Reads the diff to pick the QA method the change actually needs: real curl requests against a local server for a REST change, a handoff to /qa for browser UI, or a test-coverage review for everything else. Takes the gate list from what the project declares, not from guesswork. Report-only, and it never addresses a host other than this machine."
---

# Quality Gates

Runs the checks that decide whether a change is fit to commit, then reports one table with the exact command and the real numbers behind every row. It does not fix anything it finds.

The subject is **the change**, not the repository. A repository-wide sweep that says nothing about whether the new code is exercised has answered the wrong question.

## When to Use / When NOT to Use

Use when:

- Ending a work session, as step 2 of "Landing the Plane"
- Before opening a pull request, or before closing the work in whatever tracker the project uses
- After a fresh-eyes review, as the last step of the code-quality pipeline
- When asked "does this pass QA?", "run the checks", or "is the build clean?"
- The change is REST or HTTP API work and you want the endpoints actually driven, not just counted

This skill needs no issue tracker, no bead, and no acceptance criteria. Its entire input is the
diff. `/verify-acceptance` is the skill that grades against written criteria, and it cites this
report rather than re-deriving it.

Do NOT use when:

- The change is browser UI and you want it fixed, not reported. Use `/qa`, which drives a real
  browser and fixes what it finds, or `/qa-only` for a report. Step 3 below detects browser UI from
  the diff and hands it off, so running this first still tells you that `/qa` is the tool.
- Looking for bugs in changed code (use `review-fresh-eyes`)
- Grading work against its acceptance criteria (use `verify-acceptance`, which runs a subset of these gates as part of its own report)
- Reviewing style or design (use the matching `review-*` or `style-*` skill)

## The Four Rules That Make This Worth Running

**1. The gate list comes from the project, not from the file extensions.** Guessing gates from language defaults finds `pytest` and `eslint` and misses everything a project actually runs. A repository with no `package.json` and no `pyproject.toml` is not a repository with no checks. Step 1 reads what the project declares before it guesses, and the report names the source it used.

**2. A green suite is not a tested change.** A suite passes whether or not anything touches the new code. Gate 2 asks the separate question: is every case this change introduces exercised, at both the unit level and the end-to-end level the project's shape demands, and do those tests span the case rather than hitting one point in it. That gate is the reason to run this skill rather than the test command by hand.

Its counterweight is in the same gate. Spanning a case means covering each class of input, state, and outcome once, not their cross-product. A gate that asks for exhaustive tests, or for defensive code around failures that cannot happen, costs more than the bugs it prevents.

**3. A gate that could not run is not a gate that passed.** "No linter is configured" and "the linter is configured but not installed" are different facts, and only the first is a skip. Collapsing them means a broken toolchain reports a clean bill of health. The second is BLOCKED, and BLOCKED fails the run.

**4. The QA method comes from the diff, not from what is convenient to run.** Counting tests is
cheap and it answers a different question than driving the endpoint does. A change that adds a
`POST /exports` route can have a unit test per branch and still 401 on every real request, because
nothing sent one. So Step 3 reads the changed files and picks the method the change earns: real
curl requests for a REST surface, a handoff to `/qa` for a browser surface, and a coverage review
alone for a library or a CLI. The report names the method and the evidence for it, so a reader can
see the routing was a decision rather than a default.

Its counterweight: the probe addresses **this machine unless the caller names somewhere else**. With
no URL given it probes `http://127.0.0.1:3000`, and it never infers a host from a config file, an
environment variable, or a URL it found in the repository. A host that arrives by inference is a host
nobody chose, and this gate sends DELETE.

A URL you supply is used as given, remote or not, because supplying it is you saying so. What the
tooling guarantees instead of a refusal is that it cannot go unmentioned: the host rides the probe
summary, marked when it is not this machine, and the report repeats it.

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

Run the bundled script. Do not hand-roll the base resolution or the file list.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/changed_set.py" --repo-root .
```

It prints one changed path per line on stdout, so a caller can pipe stdout without filtering it. The base goes to stderr, as `base: <sha> (merge-base of HEAD and <ref>)`. **Keep that SHA. Gate 7 takes its `--base` from it**, and re-deriving it with `git merge-base` is the hand-rolling this script exists to replace.

| Exit | Status |
|---|---|
| 0 | The base resolved. stdout is the changed set, and no output means nothing changed |
| 2 | BLOCKED. The operator gave it a root that is not a git repository, or git will not run |
| 3 | The base will not resolve. Run at `--all`, and say so in the report |

**Exit 3 and an empty exit 0 are different answers.** A repository with no remote, a shallow clone, or a first commit produces exit 3. An unresolvable base is not an empty diff, and treating it as one narrows every gate to nothing while the report still reads confidently.

**Why a script and not two git commands.** The script diffs the base against the working tree: `git diff "$BASE"`, with no `...HEAD`. Committed, staged, and unstaged changes all land in the set. This skill runs before a commit more often than after one, so `git diff "$BASE"...HEAD` is the wrong basis: it stops at the last commit and misses the very work being checked. It unions in `git ls-files --others --exclude-standard` as well, because `git diff` never sees an untracked file. Retyping those two commands and the base fallback on every run is how a scoped report comes to cover nothing.

| Gate | At `--changed` (default) | At `--all` |
|---|---|---|
| Tests | The tests that cover the changed code | The whole suite |
| Change coverage | The cases in the diff | The cases in the diff (unchanged; this gate is always about the change) |
| Live API probe | The endpoints the diff changed | Every endpoint the changed files define |
| Lint, doc freshness, hygiene | Changed files only | Whole tree |
| Type checking | Analyze the whole project, report only errors in changed files | Analyze and report whole-project |
| Secrets | Whole tree | Whole tree |

Three rows need their reasoning stated, because getting them wrong produces a confident wrong answer:

- **Type checking always analyzes the whole project.** A type error usually surfaces in the file that consumes the changed one. Checking a subset of files reports clean while the project does not compile. Narrow the report, never the analysis.
- **Secrets always cover the whole tree.** The scan is cheap, and a key committed three months ago is still a key.
- **The live probe narrows hard, and it is the one gate where `--all` costs real time.** Every probe
  is a round trip against a running server. Probing every route a touched controller defines turns a
  two-line change into thirty requests, most of them about code nobody edited.

**Select the covering tests like this**, and keep what the selection tells you:

1. Map each changed source file to its test file by the project's convention: `foo.py` to `test_foo.py` or `foo_test.py`, `foo.rb` to `foo_spec.rb`, `Foo.ts` to `Foo.test.ts`.
2. Grep the test tree for the symbols the diff added or changed, to catch tests that live elsewhere.
3. Run that set by path or by name.

A changed source file that maps to no test and appears in no test is not a selection problem. It is a Gate 2 finding, and it carries into that gate.

**Say plainly in the report that the full suite did not run.** A scoped run is the right default and a partial answer, and a reader who takes it for a full one has been misled by the report, not by the scope.

### Step 3: Route the QA Method

Rule 4 lives here. Run the bundled script against the changed set from Step 2. Do not classify the
diff by eye.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/changed_set.py" --repo-root . |
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/route_qa.py" \
    --repo-root . --paths-from - --base "$BASE"
```

That pipe is why Step 2's script puts paths on stdout and everything else on stderr. `--paths-from
FILE` takes a file instead, and bare arguments take a handful of paths.

**Pass `--base`**, the SHA Step 2 printed: without it every endpoint the changed files define is
reported, including the ones the diff never touched, and the probe spec balloons to a dozen URLs.

It prints one JSON object on stdout and a summary on stderr. Exit 0 means it routed; exit 2 is
operator error, which is BLOCKED.

| Surface in the diff | Method | What it means here |
|---|---|---|
| **http-api** | `curl` | Gate 8 drives the endpoints through a real server on this machine |
| **browser-ui** | `handoff` to `/qa` | This skill cannot settle it. HANDOFF, and the run is INCOMPLETE |
| **mobile-ui** | `handoff` to `/ios-qa` | Same. HANDOFF |
| **cli** | `coverage` | Gate 2 alone, and its end-to-end rule means the real argv and the real exit code |
| **library** | `coverage` | Gate 2 alone. The public API is the surface, so there is no separate live level |
| **prompt-assets** | `coverage` | Gate 2 alone, on the structural invariants: it parses, it is registered, its embedded commands are valid |
| **infra** | `coverage` | Gate 2 alone. The live check is the tool's own `validate` or `plan`, which Step 1 discovered |
| **unknown** | `coverage` | No rule matched. Say so, classify it by hand, and grade what you can |
| **docs** | `none` | No behavior changed, so Gate 2 is SKIP |

**A change can route to several methods at once, and then it gets all of them.** A full-stack diff
is a `curl` gate and a `/qa` handoff, not a choice between them.

**Each `handoff` surface gets its own row in the gate table**, named for the surface and carrying
the owning tool. That is not cosmetic. A diff that adds a REST route and a React component produces
a Gate 2 finding and a browser handoff, and a single status cannot hold both: FAIL and HANDOFF mean
different next moves, and folding them together drops one. So Gate 2 grades the `curl` and
`coverage` surfaces, and browser-ui rides its own HANDOFF row. Gate 2 is itself HANDOFF only when
every surface routed to a handoff, leaving it nothing to grade.

Three things the script reports that the report must carry:

- **`ambiguous`** names a file whose strongest evidence pointed two ways. Read it and say which
  surface it really is, rather than repeating the tie.
- **`unresolved`** names an endpoint the script would not guess. `resources :exports` expands to
  seven routes, and the framework's own lister (`rails routes`, `manage.py show_urls`) is
  authoritative. Run it and fill them in.
- **`unread`** names a file routed on its path alone, because it was binary or too large.

**Every endpoint is a candidate until you read the definition.** The extractors are deliberately
conservative and they are not a router. An endpoint in the spec that does not exist reports a
failing API when the truth is a bad spec.

### Step 4: Run Each Gate

Run them in order and keep going after a failure; a FAIL in gate 1 does not excuse skipping gate 6. Give every command a bounded timeout, 600 seconds unless the project says otherwise. On timeout, record BLOCKED with the elapsed time rather than waiting.

Capture, for every gate: the exact command, the exit code, and the counts. You need all three for the report.

#### Who Runs Each Gate

This step has two shapes, and the gates are identical in both. Only who runs a row changes.

**One session runs all of it.** Read the gates below in order and run them. That is the standalone
shape, and it is the one `skills/verify-acceptance/SKILL.md` uses when it reads this file and runs
a subset of these gates with no agent involved. That skill decides which subset, and this one does
not restate the number.

**Or `tadw:quality-gates-orchestrator` partitions it across three lanes.** The orchestrator runs
Steps 1 through 3 once, dispatches `backend-unit`, `frontend`, and `integration` concurrently, keeps
the remaining rows itself, and aggregates every returned row into the one report Step 6 specifies.
Each lane reads this file for the technique, so a gate is defined once here rather than restated
per lane.

**The partition is by row, not by gate.** Gate 1 splits per test suite and Gate 2 splits per
surface, so naming one owner per gate would leave rows unowned, and an unowned row is one that
silently never appears. Every row the report can contain has an owner here.

| Row | Owner | Present when |
|---|---|---|
| Gate 1, one row per suite | `frontend` when Step 3 routed `browser-ui` and the suite is that surface's, else `backend-unit` | Step 1 discovered the suite |
| Gate 2 for `cli`, `library`, `prompt-assets`, `infra`, `unknown` | `backend-unit` | Step 3 routed one of those surfaces |
| Gate 2 for `http-api`, both the unit level and the end-to-end level | `integration` | Step 3 routed `http-api` |
| Gate 2 as SKIP, carrying the router's reason | Orchestrator | Every surface Step 3 routed was `docs`, so nothing changed behavior |
| Gate 2 as HANDOFF, in place of a graded row | Orchestrator | Every surface Step 3 routed was a handoff |
| Gate 8, the live API probe | `integration` | Step 3 routed a surface to `curl` |
| `Handoff: browser-ui`, naming `/qa` | `frontend` | Step 3 routed `browser-ui` |
| `Handoff: mobile-ui`, naming `/ios-qa` | Orchestrator | Step 3 routed `mobile-ui` |
| Gates 3, 4, 5, 6, and 7 | Orchestrator | Always |
| **Project checks** | Orchestrator | Step 1 discovered a command that maps to no gate |
| Any surface `route_qa.py` defines that no row above names | Orchestrator | Always, until a lane claims it |

**That last row is what keeps the table open.** The rule the enumeration follows is that a row
belongs to the lane whose surface or suite produced it, and every row no single lane can produce
belongs to the orchestrator. A surface added to `route_qa.py` later matches no row above, and
without the residual it would have no owner at all, which is the row that silently never appears.

When nothing routed to `curl`, Gate 8 is SKIP in its own wording, and the orchestrator emits it.

Gates 3 through 7 stay with the orchestrator because each is a single scripted command, and
dispatching a subagent to run one `python3` call costs more than it saves. Gate 5 is here for that
reason and no other: it is one `check_doc_paths.py` invocation that forbids prose judgment, so a
documentation lane would run one script and nothing else.

**A lane that was not dispatched still produces its rows.** The orchestrator emits them as SKIP
carrying the router's reason. A row that vanishes reads as a gate that passed.

**A lane that fails to return is BLOCKED, not PASS.** Treating a missing return as an absent
finding reports a clean sweep from a lane that never ran, which is the silent degradation the
six-status model exists to prevent.

**Hold every lane's result before aggregating.** Issue every dispatch the table calls for in one
message, so the lanes overlap, then wait for all of them. Dispatch is asynchronous by default. A caller that ends
its turn before the lanes return loses every row they produced and errors on nothing, so the failure
reads as a short report rather than as a bug. `tadw:quality-gates-orchestrator` owns the mechanism
that enforces this; naming a harness parameter here would date this file to one harness release.

**A lane never renders the report and never decides the verdict.** It returns its rows, each row's
`detail` string, its failing command's real output, its Step 5 attribution, and any evidence table
its gate requires. That list is the whole contract; Step 6 assumes no other field.

#### What Every Lane Is Given, and What It Must Not Re-derive

The orchestrator resolves these once and passes them in. A lane that re-derives any of them
produces an answer about a different scope than the report claims.

| Input | Resolved by |
|---|---|
| The base SHA | Step 2's `changed_set.py`, run exactly once |
| The changed path list | The same run |
| The discovered gate set | Step 1 |
| The numbered case list | Enumerated once over the whole changed set, per Gate 2 step B, before any case is graded |

Two runs of `changed_set.py` against a moving working tree can disagree, and Gate 7 shows what that
costs. A lane that re-discovers the gate set may pick a different source and run a command the
project replaced. Three lanes numbering cases independently produce three unrelated lists, and a
case nobody listed cannot be graded, which is what Gate 2 step B's numbering exists to prevent.

#### Reducing Two Change Coverage Rows

Only Gate 2 can produce two rows: `backend-unit` grades five surfaces and `integration` grades
`http-api`, so a file that classifies into one of each is graded twice. Every other gate has a
single owner and never reduces. Merge the two rows field by field, not on the status alone:

- **Status** takes the worse, ordered BLOCKED, FAIL, HANDOFF, WARN, PASS, SKIP, worst to best.
- **Counts** cover every numbered case, both lanes' together, not the survivor's alone.
- **Every evidence table** is spliced into the gate's report section in case-number order, whichever
  status survived. Dropping the losing lane's table silently ungrades the cases it covered, which is
  what the single numbered case list exists to prevent.
- **Raw output and attribution** come from both rows, not from the survivor alone.

**A `Handoff: <surface>` row never merges with anything.** Folding a handoff surface and a graded
surface into one status drops one of two different next moves, so each stays its own row and
Verdict Rule 2 still sees it.

#### Gate 1: Tests

Run the selected tests from Step 2. Record passed, failed, skipped, and errored counts, and name the selection.

**Every discovered suite gets its own row.** The report requires the exact command and real counts
in each row, so merging two suites into one discards a command and a count. One suite means one row.
Which lane owns which suite is in Step 4's ownership table.

An exit code of 127, a missing runner, or a collection error is BLOCKED, not FAIL. Zero tests collected in a project that has a test directory is BLOCKED too, because the runner found nothing to check.

#### Gate 2: Change Coverage

The gate that answers rule 2. A passing suite says the old code still works. This says the new code is exercised.

**A. Take the shape from Step 3.** The surfaces the router found are the shapes this gate grades,
and what "end to end" means depends on which:

| Surface | What end-to-end means here |
|---|---|
| **http-api** | Drive the route through the real HTTP stack: status code, body shape, auth, and the error responses. Gate 8 is where that happens, and this gate cites its result rather than repeating it |
| **cli** | Invoke the built command the way a user does: real argv, real exit code, real stdout and stderr |
| **library** | The public API is the surface. There is no separate end-to-end level |
| **browser-ui**, **mobile-ui** | This skill cannot settle it. HANDOFF |
| **prompt-assets** | The structural invariants: the asset parses, it is registered where the project says, and its embedded commands are valid |
| **infra** | The tool's own `validate` or `plan`, which Step 1 discovered |
| **unknown** | Say the surface has no row, and grade the unit level you can see |

A change can touch two surfaces. Grade each, and take the worst result. When two lanes each return
a row for this gate, they reduce per field, under "Reducing Two Change Coverage Rows" above. One row
survives, and every case table both lanes produced is carried into it.

The prompt-assets row is here because the table did not have it on first use, and this repository is one. A surface with no row does not mean the gate does not apply. It means the row is missing, so say so and grade what you can.

**B. Enumerate the cases the change introduces.** Number them, because a case you did not list cannot be graded:

- Each new or changed function, and each branch inside it
- Each new CLI flag, subcommand, or positional argument
- Each new or changed route, status code, and error response
- Each error path: a raised exception, a non-zero exit, a 4xx or 5xx

**C. Find what exercises each case.** Two rules, both required for CLI and API shapes:

- **Unit.** Every case has a test that exercises it. Find it by symbol, run it by name, keep the output.
- **End to end.** Every surface the change touches has at least one test that drives it through the real entry point. A test that imports the handler and calls it directly is a unit test wherever it lives, and does not satisfy this.

Read each test you count. A test that runs the case without asserting anything about it does not cover it.

**A green Gate 8 does not satisfy the end-to-end rule here.** The two answer different questions,
and merging them loses one of them:

| | Question it answers | What it leaves behind |
|---|---|---|
| Gate 8's probe | Does this endpoint behave correctly right now, on this build? | Nothing. It is a measurement, not a test |
| An end-to-end test | Will anyone notice when this endpoint stops behaving correctly? | A test that runs on every future change |

So a REST diff with a passing probe and no committed request-level test is still a Gate 2 finding.
Cite the probe as evidence that the endpoint works, and say the regression test is missing.

**Whoever grades one must hold the other**, which is why the `integration` lane owns both. Split
across contexts that cannot see each other, the citation either duplicates the probe or loses the
distinction this table draws. Losing it is how a green probe comes to read as an end-to-end test.

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
| **HANDOFF** | Step 3 routed *every* surface to `handoff`, so nothing is left here to grade. The orchestrator emits this row, since no single lane sees the union of surfaces. When only some surfaces routed to a handoff, grade the rest and let each handoff surface carry its own row, defined below |
| **SKIP** | Step 3 routed every surface to `none`: documentation, comments, or formatting only |

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

Prefer a scanner the project already configures (`gitleaks`, `detect-secrets`, `trufflehog`) and name it in the report. Otherwise run the bundled script, which is the fallback rather than a replacement for a scanner the project already runs. Either way, do not hand-roll this check.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_secrets.py" --repo-root .
```

It runs two checks over the whole tree: secret file names, and prefixed key formats in file content. `--exclude GLOB` is repeatable, for a path this project needs left out.

| Exit | Status |
|---|---|
| 0 | PASS |
| 1 | **FAIL**, with the reported findings. Unlike a stale doc reference, a key in the tree is not something to note and move past |
| 2 | BLOCKED. The operator gave it a root that is not a git repository, or git will not run |

Three rules the script encodes, stated here because the next person tempted to relax one reads this file rather than the script:

- **The untracked half of the file check is the point.** It scans `git ls-files --others --exclude-standard` beside `git ls-files`, because an untracked `.env` that git does not ignore is one `git add -A` away from being committed. That is the case this gate exists to catch.
- **Prefixed key formats only.** Generic long hex or base64 matching fires on lockfile hashes, test fixtures, and minified assets, and a gate that cries wolf gets ignored along with the real finding. Vendored, generated, minified, and fixture paths are excluded for the same reason.
- **The matched value never reaches output.** A finding carries `file:line` and the pattern name, and nothing else. A report that quotes the secret copies it into one more place. That rule binds your report too, not just the script's.

The script names any file it did not read, above its verdict, and a skipped file does not change the exit status. Carry that count into the report: "0 findings" above an unscanned file claims more than the gate checked.

#### Gate 7: Hygiene

Run the bundled script. Do not hand-roll this check.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_hygiene.py" --base "$BASE"
```

`$BASE` is the SHA Step 2's script printed. The script counts the `TODO`, `FIXME`, `HACK`, and `XXX` markers the diff adds, and reports each with its `file:line`.

**Under a fan-out, re-deriving that SHA here costs more than the hand-rolling Step 2 forbids.** Two
resolutions against a moving working tree can disagree. The report's **Scope** line would then name
one base while this gate counted markers against another, and the report would still read clean.

| Exit | Status |
|---|---|
| 0 | PASS, at zero markers added |
| 1 | **WARN**, with the reported markers |
| 2 | BLOCKED. A missing, empty, or unresolvable `--base`, a root that is not a git repository, or a diff it could not parse |

**Exit 0 at zero markers is the rule the script exists to hold.** The recipe it replaces piped `git diff` into `grep -c`, which exits 1 when it counts zero. That line needed a `|| true` to stop the cleanest possible result from reading as BLOCKED, and retyping it without one reports a broken toolchain where the truth was good news.

`git diff` never sees an untracked file, so a new file's markers stay invisible here until it is added. Say so rather than reporting zero as clean when Step 2's changed set holds untracked files.

**Do not run it with no base.** Step 2 exits 3 on a repository with no remote, a shallow clone, or a first commit, and that run has no base, so a count of added markers does not exist. Record SKIP with that reason. Passing an empty `--base` exits 2, and BLOCKED fails the whole run, so mapping it that way would fail a push over a missing remote.

Under `--all` you may report the repository total instead, labeled as context rather than as a finding. A count of markers someone else added years ago changes nothing the reader can act on.

#### Gate 8: Live API Probe

**Runs only when Step 3 routed a surface to `curl`.** Otherwise it is SKIP, with the routed method
as the reason: "SKIP, Step 3 routed browser-ui to /qa and cli to coverage; no HTTP surface changed".

This is the gate that sends real requests. Every other gate reads code or counts things.

**A. Write the spec.** Author it from Step 3's endpoints, one probe per endpoint the diff changed,
and write it beside the report artifact inside the git directory:

```bash
git rev-parse --git-dir    # then write <git-dir>/quality-gates-probe.json
```

It lives there for the same reasons the report does: per-clone, per-worktree, never committed, no
`.gitignore` entry. The full format is in `probe_api.py`'s own docstring, and the short version is:

`base_url` is optional and defaults to `http://127.0.0.1:3000`. Write it only to change the port, or
because the caller named a different URL.

```json
{
  "base_url": "http://127.0.0.1:3000",
  "server": {"start": "bin/rails server -p 3000", "health_path": "/up", "ready_status": [200]},
  "probes": [
    {"name": "create an export", "method": "POST", "path": "/api/v1/exports",
     "headers": {"Content-Type": "application/json"}, "body": "{\"format\": \"csv\"}",
     "expect": {"status": 201, "body_json": true}, "capture": {"id": "id"}},
    {"name": "reject an unknown format", "method": "POST", "path": "/api/v1/exports",
     "body": "{\"format\": \"xlsx\"}", "expect": {"status": 422}},
    {"name": "fetch it back", "path": "/api/v1/exports/{id}", "expect": {"status": 200}}
  ]
}
```

Four rules for writing it:

- **Probe the cases, not the endpoints.** A route with a 201, a 422, and a 401 is three probes.
  One probe per route proves the happy path and nothing else, which is the shape of test suite this
  skill exists to refuse.
- **Never put a credential in the spec.** Write `${API_TOKEN}` and let the script expand it from the
  environment. A literal token gets redacted in the output, and the run says to fix the spec.
- **Order a write flow so it cleans up after itself.** Create, read, then delete. Nothing enforces
  this, and a dev database full of probe rows is the cost of skipping it.
- **`capture` chains one probe into the next.** `{"id": "data.id"}` reads a dot path out of the JSON
  response, and `{id}` substitutes it into any later path, header, or body.

**B. Find the server.** Take a start command from what the project declares, in the order Step 1
used: `AGENTS.md`, then a `Procfile`, `docker-compose.yml`, or a task runner's `dev`/`start`
script.

| What you found | What to do |
|---|---|
| Something is already listening on the port | Probe it. Omit `server` from the spec, and say in the report that you used a server you did not start |
| Nothing is listening, and the project declares a start command | Put it in `server.start` with a `health_path`. The script starts it, waits for it, and always stops it |
| Nothing is listening, and the project declares no start command | **SKIP**, with that exact reason. Do not invent `rails s` or `npm run dev` |

**Do not guess the start command.** A guessed command runs migrations against the wrong database,
or starts a second copy on a port the first one holds, and the failure looks like a broken endpoint.

**C. Run it.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/probe_api.py" \
  --spec "$(git rev-parse --git-dir)/quality-gates-probe.json" --repo-root .
```

| Exit | Status |
|---|---|
| 0 | PASS. Every probe met its expectation |
| 1 | **FAIL**, with each mismatch. This is the finding the gate exists to produce |
| 2 | **BLOCKED**. The gate could not run as specified |

Exit 2 covers a missing or unparseable spec, a spec with no probes, a scheme curl cannot speak, an
unset `${VAR}`, a server that never became healthy, an absent curl, a refused connection, and a
`{capture}` nothing captured. **A refused connection is BLOCKED, not FAIL**: no endpoint answered, so
telling the author their route is broken points at the wrong file.

`--base-url URL` overrides the spec's `base_url`, so one spec can be pointed somewhere else without
editing it.

When the script starts a server it prints `server log: <path>` on stderr. Read that file when the
server never became healthy; the reason is almost always the last few lines of it, and the script
quotes them in its error. Report what it says rather than guessing why the server would not come up.

**The host defaults to this machine, and only the caller changes it.** Omitting `base_url` probes
`http://127.0.0.1:3000`. Never fill it in from a URL you found in `AGENTS.md`, a `.env` file, a
compose file, or a deploy config: those name hosts other people share, and this gate sends POST, PUT,
PATCH, and DELETE. Use what the caller asked for, or the default.

**When the caller does name a remote host, say so three times.** The script warns on stderr, marks
the summary line `(NOT this machine)`, and you put the host in the report's probe section. A reader
who cannot tell which machine answered cannot judge the result at all, and a DELETE against a shared
database is the one finding in this skill that costs more than the bug it was looking for.

**D. Report each probe.** Name the probe, its status, and the exact curl command. The script prints
a runnable command per probe with credentials redacted, so copy that rather than rebuilding it.

A passing probe is evidence about this build, not a test. Gate 2's table above says why, and a REST
change with a green probe and no committed request-level test is still a Gate 2 finding.

#### Handoff Rows

Step 3 routes `browser-ui` to `/qa` and `mobile-ui` to `/ios-qa`. Each routed handoff surface gets
its own row here, named `Handoff: <surface>`, carrying the owning tool and a **null command**,
because no command was run. One HANDOFF row drives the whole run to INCOMPLETE by Verdict Rule 2.

| Row | Owner | What the lane does instead |
|---|---|---|
| `Handoff: browser-ui` | `frontend` lane | It runs the frontend test suite for Gate 1 and emits this row. It never attempts to settle browser UI itself |
| `Handoff: mobile-ui` | Orchestrator | No lane here runs iOS checks |

Why the row never merges and never becomes a SKIP is in Step 3, under "Each `handoff` surface gets
its own row in the gate table".

#### Project Checks

Step 1 maps every discovered command onto the gate it serves. A command that fits no gate still
runs, under a single **Project checks** row carrying its exact command and its real counts. The
orchestrator owns it. Omit the row only when Step 1 discovered no such command.

### Step 5: Attribute Every Failure

For each FAIL, say whether it looks new. A failing test in a file the diff does not touch, exercising code the diff does not touch, is probably pre-existing, and the report should say so as evidence rather than as a verdict.

Write the evidence: "3 failures, all in `tests/legacy/`, which this diff does not touch." Do not write "pre-existing" alone.

**The lane that produced a failure writes its attribution**, because attribution needs the failing
command's real output and only that lane holds it. The orchestrator renders the sentence beside the
failure; it never re-derives the evidence.

Establish this by reading, never by rewriting the working tree. Do not stash, check out the base, or reset to get a baseline. If the caller needs certainty, say that re-running on the base commit would settle it.

### Step 6: Report

Produce two things: the markdown report below, and a JSON artifact carrying the same result so a tool can act on the verdict the prose states.

**The orchestrator renders all of it.** A lane returns only what Step 4's contract lists. It never
renders a section, never writes the artifact, and never decides the verdict.

Aggregation is mechanical. Concatenate the rows in report order. Reduce two Change coverage rows
under Step 4's per-field rule. Leave every handoff row standing alone. Apply the Verdict Rules to
the union.

**Write the JSON first, then emit the report.** The report's **Artifact** line records what that write did, including a refusal, so emitting the report first would mean predicting it.

#### The JSON Artifact

Resolve the git directory first:

```bash
git rev-parse --git-dir
```

If that command fails, the tree is not a git repository. Skip the write, say so on the report's **Artifact** line, and leave the rest of the report unchanged. A missing artifact is not a finding about the code.

Write `<git-dir>/quality-gates-report.json`. It lives inside the git directory on purpose: it is per-clone, it is never committed, it needs no `.gitignore` entry, and it survives until the push it exists to inform.

**Resolve the path with that command. Never hardcode `.git/`, and never use `--git-common-dir`.** The three forms differ exactly where it matters:

| Form | In an ordinary clone | In a linked worktree |
|---|---|---|
| `git rev-parse --git-dir` | `.git` | `<main>/.git/worktrees/<name>`, one per worktree |
| A literal `.git/` | correct | `.git` is a file, not a directory, so the write fails with "not a directory" |
| `git rev-parse --git-common-dir` | `.git` | the shared `.git`, so every worktree overwrites the others |

Two worktrees checking out two branches produce two verdicts about two different trees. `--git-dir` gives each its own file, and a `pre-push` hook run from a worktree resolves the same path and reads that worktree's own report. `--git-common-dir` would let the last run to finish decide every worktree's push.

Collect the three facts the markdown report does not already carry:

```bash
git rev-parse HEAD                  # head
git status --porcelain              # dirty: true when this prints anything
date -u +%Y-%m-%dT%H:%M:%SZ         # timestamp
```

Then build the object in `python3` and `json.dump` it. Do not hand-assemble JSON text: one stray quote in a command string or a gate detail produces a file no reader can parse, and the pre-push consumer cannot tell an unparseable report from a missing one. It warns that no verdict was recorded, which reads as "you forgot to run the gates" rather than "your gate is broken", so the author fixes the wrong thing or nothing.

This example is the run the Output Format section below reports, so the two can be compared line for line:

```json
{
  "version": 1,
  "head": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
  "dirty": true,
  "timestamp": "2026-08-11T04:12:07Z",
  "scope": "changed",
  "gate_source": "AGENTS.md",
  "routing": {
    "http-api": {"method": "curl", "owner": null, "files": 2, "endpoints": 3},
    "browser-ui": {"method": "handoff", "owner": "/qa", "files": 1, "endpoints": 0}
  },
  "verdict": "FAIL",
  "gates": [
    {"name": "Tests", "status": "PASS", "command": "pytest tests/test_exports.py -q", "detail": "14 passed, 0 failed (selected, not the full suite)"},
    {"name": "Change coverage", "status": "FAIL", "command": null, "detail": "case review over 6 cases: 5 of 6 have unit tests, 0 request-level, span 7 of 11"},
    {"name": "Live API probe", "status": "FAIL", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/probe_api.py\" --spec .git/quality-gates-probe.json --repo-root .", "detail": "5 probes: 4 passed, 1 failed, 0 blocked"},
    {"name": "Handoff: browser-ui", "status": "HANDOFF", "command": null, "detail": "1 component changed; /qa owns it"},
    {"name": "Lint", "status": "FAIL", "command": "ruff check src/api/exports.py", "detail": "2 errors, 11 warnings"},
    {"name": "Type checking", "status": "BLOCKED", "command": "mypy .", "detail": "exit 127, mypy not installed"},
    {"name": "Doc freshness", "status": "WARN", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_doc_paths.py\" --repo-root .", "detail": "3 docs checked, 1 missing path"},
    {"name": "Secrets", "status": "PASS", "command": "gitleaks detect", "detail": "0 findings"},
    {"name": "Hygiene", "status": "WARN", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_hygiene.py\" --base abc1234", "detail": "2 TODOs added"},
    {"name": "Project checks", "status": "PASS", "command": "node hooks/test-hooks.js", "detail": "19 checks, 0 failed"}
  ]
}
```

Five rules the consumer depends on:

- **`verdict` is one of `PASS`, `FAIL`, `INCOMPLETE`, or `NO GATES RAN`,** verbatim from the Verdict Rules. No other string, no lowercase, no added punctuation.
- **`gates` carries one entry per row of the report table,** in the same order, with the same `status`. A SKIP, BLOCKED, or HANDOFF row gets its entry too. Count the array against the table before you write it: ten rows means ten entries. A short array contradicts a run the reader can see.
- **`command` is `null` unless the cell holds a command someone can re-run.** Change coverage describes a method rather than naming a command, so its `command` is `null` and the description moves into `detail`. A gate that never ran is `null` too. An invented command is worse than an absent one.
- **`scope` is `changed` or `all`,** matching what Step 2 set.
- **`routing` carries one key per surface Step 3 found,** with the method and owner verbatim from the
  router's output. A consumer reads it to know whether a live check happened at all, which `verdict`
  alone does not say: a PASS over a diff whose only surface was a handoff means much less than a PASS
  over a probed one. Write `{}` when the changed set had no surface.

`dirty` is for a human reader, and nothing automated reads it. It records that this skill runs before the commit most of the time, so `head` is usually the commit *before* the one that gets pushed. Nearly every honest report is dirty, and a gate blocking on that would block constantly.

## Output Format

```markdown
## Quality Gates Report

**Gate source:** AGENTS.md "Commands for This Repo" | .github/workflows/lint.yml | auto-detected
**Scope:** changed (9 files vs `abc1234`). The full suite did not run.
**QA method:** curl for http-api (2 files, 3 endpoints); handoff to `/qa` for browser-ui (1 file)

| Gate | Status | Command | Result |
|---|---|---|---|
| Tests | PASS | `pytest tests/test_exports.py -q` | 14 passed, 0 failed (selected, not the full suite) |
| Change coverage | FAIL | case review over 6 cases | 5 of 6 have unit tests, 0 request-level, span 7 of 11 |
| Live API probe | FAIL | `python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/probe_api.py" --spec .git/quality-gates-probe.json --repo-root .` | 5 probes: 4 passed, 1 failed, 0 blocked |
| Handoff: browser-ui | HANDOFF | - | 1 component changed; `/qa` owns it |
| Lint | FAIL | `ruff check src/api/exports.py` | 2 errors, 11 warnings |
| Type checking | BLOCKED | `mypy .` | exit 127, mypy not installed |
| Doc freshness | WARN | `python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_doc_paths.py" --repo-root .` | 3 docs checked, 1 missing path |
| Secrets | PASS | `gitleaks detect` | 0 findings |
| Hygiene | WARN | `python3 "${CLAUDE_PLUGIN_ROOT}/skills/quality-gates/scripts/check_hygiene.py" --base abc1234` | 2 TODOs added |
| Project checks | PASS | `node hooks/test-hooks.js` | 19 checks, 0 failed |

### Overall: FAIL

<One sentence naming what decided it.>

### Live API Probe

I started the server from `server.start`: `bin/rails server -p 3000`, waited for
`/up` to answer 200, and stopped it afterward.

| Probe | Status | Result |
|---|---|---|
| create an export | PASS | status 201 |
| reject an unknown format | FAIL | status 500, expected 422 |
| fetch it back | PASS | status 200 |
| fetch a missing export | PASS | status 404 |
| delete it | PASS | status 204 |

The failing probe:

```bash
curl -sS -i --max-time 10 -X POST -H 'Content-Type: application/json' \
  --data-binary '{"format":"xlsx"}' http://127.0.0.1:3000/api/v1/exports
```

An unknown format raises out of the serializer instead of being rejected, so the
route answers 500 where the unit test asserts a 422 on the validator alone. The
unit test passes and the endpoint is broken, which is the gap this gate exists to
find.

### Change Coverage

| # | Case | Unit test | Request level | Span covered |
|---|---|---|---|---|
| 1 | `POST /api/v1/exports` creates an export | `test_create_export` | - | 2 of 3: one row and many rows. Nothing covers an empty result set |
| 2 | The route rejects an unknown format | `test_bad_format` | - | 1 of 1 at the unit level, and the probe above shows it fails through the real stack |
| 3 | 404 on a missing export id | - | - | 0 of 2 |

No committed test drives these routes through the HTTP stack, so status codes and
error bodies are unexercised by anything that will run again. The probe above
measured them once, on this build; it leaves no test behind. Case 3 has no test at
either level.

Case 1's empty result set is the span gap worth closing: an export that writes a
header and no rows is the shape a caller is most likely to mishandle. I did not
ask for the format-by-row-count cross-product, since nothing suggests those
interact.

### Failures

**Lint** (`ruff check src/api/exports.py`)

<the actual command output, trimmed to the failing lines>

`src/api/exports.py:88` and `src/api/exports.py:94`, both in files this diff touches.

**Type checking** (`mypy .`)

`mypy: command not found`. The gate is configured in `pyproject.toml`, so this is
not a skip. Install it or remove the configuration.

### Action Items

1. Fix the 500 on an unknown format; the route must answer 422 (probe 2)
2. Add a request-level test per route, so probe 2's bug cannot return unnoticed
3. Add a test for the missing-export 404 (case 3)
4. Fix the two ruff errors in `src/api/exports.py`
5. Install mypy, then re-run the type gate
6. Run `/qa` for the changed component; this run did not check it

**Artifact:** `.git/quality-gates-report.json`, verdict FAIL

```text

The Artifact line always appears, and states either the path written or why nothing was written: `**Artifact:** not written, the tree is not a git repository`.

Omit the Failures section when nothing failed. Omit the Live API Probe section when that gate is SKIP, and say in its table row which method Step 3 routed instead. Omit the Change Coverage table only when that gate is SKIP. Never omit a gate row; a gate that did not run gets its row with SKIP, BLOCKED, or HANDOFF and a reason.

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
- Take the QA method from `route_qa.py`, and name the routed surfaces in the report
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
- Probe this machine unless the caller named another URL, and one probe per case rather than one per route
- Name the probed host in the report, and mark it when it is not this machine
- Stop any server you started, and say in the report whether you started it or found it running
- Write the JSON artifact after the markdown report, with the verdict verbatim and one entry per table row
- Give every report row an owner from Step 4's table, including the residual row, so no row can go unclaimed
- When lanes ran: emit an undispatched lane's rows as SKIP with the router's reason, and record a lane that did not return as BLOCKED

**Never:**

- Fix, format, or edit anything in the working tree (this skill is report-only; its report is the deliverable, and the only files it writes are that report's JSON form and the probe spec, both inside the git directory)
- Fill in a `base_url` from a URL you found in the repository; use the caller's URL or the localhost default
- Guess a server start command the project does not declare; SKIP the probe with that reason instead
- Put a literal credential in the probe spec, or copy a token into the report
- Read a green probe as an end-to-end test; it measures this build and leaves nothing behind
- Report a refused connection as a failing endpoint; nothing answered, so it is BLOCKED
- Hand-assemble the artifact's JSON text, or record a verdict there that the report does not state
- Report a gate as "green", "clean", or "passing" without its numbers
- Treat a passing suite as evidence that the change is tested
- Count a test you have not read, or one that exercises a case without asserting it
- Read one passing test as coverage of a case's whole span
- Call an in-process call of a handler an end-to-end test
- Ask for the cross-product of span classes, for a branch unreachable through the public interface, or for a test of code this change did not touch
- Ask for defensive code: a nil check the type guarantees, a `try` around code that cannot raise, or a re-validation the caller already performed
- Downgrade BLOCKED or HANDOFF to SKIP, or let an all-SKIP run report PASS
- Pass a browser UI change silently; hand it to `/qa` on its own row
- Fold a handoff surface and a graded surface into one status
- Let a lane render a report section, write the artifact, or decide the verdict
- Re-derive the base SHA, the changed set, the gate set, or the numbered case list once the orchestrator has resolved it
- Run a language default beside a project command that serves the same gate
- Stash, reset, or check out another commit to establish a baseline
- Claim doc prose is stale without a missing path to point at

## Quality Checklist

Before reporting completion, verify:

- [ ] The gate source, the scope, and the routed QA method all appear in the report
- [ ] The report says whether the full suite ran
- [ ] Every gate has a row, including the ones that did not run
- [ ] Every row traces to one owner in Step 4's table
- [ ] Exactly one Change coverage row survives, and its counts and its case table cover every numbered case
- [ ] If lanes ran, every one of them returned, and its rows are in the report
- [ ] Every non-SKIP row carries its exact command and a real count
- [ ] Every routed surface is accounted for: probed, graded, or on its own HANDOFF row
- [ ] Every case the change introduces appears in the coverage table
- [ ] Every case names its span classes, and the uncovered ones are called out
- [ ] Every test counted as coverage was read, not just found by name
- [ ] Nothing asked for is a cross-product, an unreachable branch, or a defensive check
- [ ] No configured gate is recorded as SKIP
- [ ] A browser or mobile UI change is HANDOFF, never PASS
- [ ] The `base_url` was the localhost default or a URL the caller named, never one inferred from the repository
- [ ] A non-loopback host, if any, is named in the report and marked as not this machine
- [ ] No probe carried a literal credential
- [ ] Every server this run started is stopped, and the report says which servers it started
- [ ] A REST change with a passing probe and no committed request-level test is still a Gate 2 finding
- [ ] Every FAIL shows real command output, and says whether it looks new
- [ ] No secret value was copied into the report
- [ ] The overall verdict follows the Verdict Rules mechanically
- [ ] The artifact's `verdict` matches the report's, its `routing` matches the router's output, and its `gates` array matches the table row for row
- [ ] The Artifact line names the file written, or why the write was skipped
- [ ] No file in the working tree was edited; the only writes are the report artifact and the probe spec, both inside the git directory
