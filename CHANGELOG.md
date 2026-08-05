# Changelog

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.3.0] - 2026-08-05

### Added

- **`house-response-style` extends the no-jargon rule to self-reporting.** Rule 3 listed
  only words about system behavior ("tombstone", "reap", "drain"), so the words an agent
  uses for its *own* work read as allowed. That is the highest-drift case in a coding
  session: the model reports on itself constantly, and the reader cannot audit the
  shorthand. "The suite is green" hides the test count. "That was a flake" hides the whole
  argument for why a failure is unrelated, which is what failed, what was re-run, and why
  the change cannot be the cause. A replacement table now covers both, plus "smoke test",
  "round-trip", "surfaced", "lands", "wire up", and "quick win". Step 9 of the pre-send
  check makes re-reading every claim about your own work a required pass, and asks for a
  number wherever one exists.
- **`evals/cases/self-report-plainly`** hands the model the exact situation that produces
  those two words (a passing suite plus one test that failed once and then passed) and
  forbids them, while requiring the count, the re-run, and the reason the failure is
  unrelated. Verified to discriminate: 10 of 10 graders pass on a plain report and 6 fail on
  the jargon version.
- **Check 11 in `hooks/test-hooks.js`** pins the rule in both response-style sources, the
  skill and `preamble.js`'s fallback, so a failed file read cannot silently drop it.

### Changed

- **The standard is now named in full where the rule is stated.** The section is "Write in
  Simplified Technical English, which is specified in ASD-STE100", and its opening states
  that ASD-STE100 is the controlled-English standard published by the AeroSpace and Defence
  Industries Association of Europe. The two halves are now listed explicitly: follow the
  writing rules, never the licensed dictionary. Previously the name and the number appeared
  only in passing, so a reader could not tell what to look up, and the split between the
  rules and the dictionary was one clause easy to miss. A line records that the title is
  "Simplified", not "Simple". Check 11 asserts that both sources carry the full name, the
  number, and the dictionary exclusion.
- **Two rules now outrank the rest: accuracy beats brevity, and label your confidence.** The
  file had no tie-breaker for the case where a shorter answer would be less true, and nothing
  asking the model to separate what it verified from what it inferred. Both are now stated
  first, above every wording rule.
- **`house-response-style` is 20% shorter, with the repetition removed.** "Lead with the
  answer" was stated in four places and narration-cutting in three; each is now stated once,
  plus one deliberate reference (the exception list, and the pre-send check, which is a
  different action from the rule). Every Bad/Good example pair survives, because the evals
  show those are what change behavior.
- **Two absolute rules relaxed to match how engineers actually read.** Terminology
  consistency now applies "where ambiguity would cost the reader" rather than banning
  synonyms outright, and the jargon rule now targets borrowed metaphor while explicitly
  allowing domain terms an engineer reads fluently (`serialize`, `refactor`, `idempotent`,
  `bootstrap`). The metaphor examples are unchanged: "hydrate" and "tombstone" hide a
  mechanism, which is the case worth banning.
- **New "Match the reader" section:** depth follows the reader's demonstrated knowledge, and
  tone follows the task, since these rules target technical answers and not every response is
  one.
- **The sentence limit keeps its number.** It was briefly relaxed to "short enough to read
  once" and then restored, because measurement contradicted the change: with no number, the
  model wrote 31- and 32-word sentences. The joiner guidance added alongside it ("cut at
  'which', 'so', 'but', 'since', 'because'") is what makes the number reachable, since length
  comes from two statements joined rather than one long statement.

### Fixed

- **`decision-matrix-trigger`'s grader demanded the literal word "recommend".** It failed 3
  of 3 runs on responses that were following the rule correctly: the model opened with
  `**Add the nullable column to `users`.**`, a bold imperative, which satisfies "lead with
  the answer" better than a labelled restatement. The check now asserts the response *opens*
  with a bold span or heading, which accepts every correct form and still rejects a response
  that builds up to its recommendation. The case remains failing for a separate,
  undiagnosed reason recorded in its `known_failing` field.
- **`max_sentence_words` raised from 25 to 35 in the two cases that use it.** The 25-word
  check failed every run, including on the file as it stood before this session (0 of 3,
  worst case 39 words), so it was reporting a permanent red rather than a regression. The
  skill still states 25 as the target; the grader is now a ceiling on runaway sentences. The
  gap is documented in `evals/README.md` and in each case's `why`.

## [2.2.0] - 2026-08-04

### Added

- **`house-response-style` now mandates Simplified Technical English.** A new "Write in
  Simplified Technical English" section adopts the ASD-STE100 writing rules: one word carries
  one meaning and one part of speech, no jargon or borrowed metaphor ("tombstone", "reap",
  "drain", "hydrate", "poison pill"), active voice with imperative instructions, simple verb
  tenses, one instruction per sentence, 20 words maximum for an instruction and 25 for an
  explanation, positive phrasing, no dropped articles, no noun stacks over three, English
  instead of Latin abbreviations, and condition-before-instruction ordering in warnings.
  Technical names and technical verbs (file paths, commands, settings, error text) stay
  verbatim, which is itself an STE allowance; an unavoidable term is defined in the same
  sentence that uses it.
  - **The section states its own limit.** It adopts the writing rules only and explicitly
    disclaims the controlled dictionary, which is licensed material that cannot be shipped
    here and would strip ordinary technical conversation down to manual-speak. Guessing at
    dictionary membership is called out as prohibited rather than left to inference.
  - Scoped explicitly to wording, not content, so no fact, caveat, number, or warning is
    dropped to make a sentence simpler.
- **American English is now mandatory, in both injected documents.** `hooks/style-core.md`
  gains a "Spelling" section covering identifiers, comments, documentation, commit messages,
  log lines, and user-facing strings, so the rule reaches sessions *and* subagents (the
  coding core is injected into both). `house-response-style` gains rule 14 for prose. Both
  carry the same exception: match the spelling of a name you do not own, so an API field
  called `colour` stays `colour` rather than being silently renamed across a boundary. The
  degraded-path fallbacks in `preamble.js` carry the rule too.
  - Existing British spellings in the repository were normalized in the same pass
    ("honoured", "honours", "honouring", "recognisable" across `AGENTS.md`, `CHANGELOG.md`,
    `hooks/test-hooks.js`, and `skills/style-testing/scripts/check_framework_leak.py`), so
    the repository now follows the rule it ships.
- **`house-response-style` now requires a decision matrix for hard choices.** A new "Put hard
  choices in a decision matrix" section with a three-part trigger test (2-4 real options,
  more than one factor that matters, expensive to undo or directly asked), an explicit skip
  rule so obvious calls stay prose, a column/cell format that bans bare scores, and a worked
  example ending in a bold recommendation plus the condition that would reverse it.

### Changed

- The "Why this shape" rationale gains a fourth fact (a word the reader has to decode costs
  more than a longer sentence), and the pre-send check gains three rewrite passes and a
  second verify question covering the matrix.
- **The decision matrix now fixes the order of its parts**, resolving a contradiction the
  eval suite caught. "Be concise" says lead with the answer; the matrix section said end
  with a bold recommendation. When the question is "which should I pick?", the
  recommendation *is* the answer, so the two rules pulled in opposite directions and the
  model could satisfy only one. The recommendation now leads in bold above the table, the
  table shows the work, and one line after it names what would change the answer. Stating
  it twice is called out as wrong.
- **The Simplified Technical English section is roughly half its previous length.** It no
  longer explains what ASD-STE100 is or recounts its history; the reader is a model that
  already knows the standard. What remains is the delta: which half of the standard applies
  (writing rules, not the licensed dictionary), that the rules govern wording and never
  content, the thirteen rules stated once each, and the four examples that actually steer
  behavior.
- `preamble.js`'s degraded-path response-style fallback carries the plain-language and
  decision-matrix rules, so a failed read of `SKILL.md` no longer silently drops them.

### Fixed

- `AGENTS.md` described the injected coding-style core as "nine cross-language principles";
  `hooks/style-core.md` ships ten.
- `README.md` was missing two registration rows that `AGENTS.md` already carried: the
  `house-response-style` skill and the `/response-style` command. Both surfaces now list all
  34 skills, 12 agents, and 36 commands.
- **Four components loaded with empty metadata.** `claude plugin validate --strict` (the
  official validator, which parses the YAML rather than pattern-matching it like
  `/validate-plugin` does) found unparseable frontmatter in `skills/production-ops/SKILL.md`,
  `skills/review-fresh-eyes/SKILL.md`, `agents/claude-md-reviewer.md`, and
  `agents/software-engineer.md`. All four had an unquoted `description` containing a colon
  followed by a space, which YAML reads as a nested key; the parse failed and every
  frontmatter field (`name`, `description`, `tools`) was silently dropped at load time. The
  three single-line descriptions are now quoted, and `claude-md-reviewer`'s multi-line
  description (which spans blank lines and contains double quotes) is now a block scalar.
  The repository validator missed these because it read frontmatter as text; the root cause
  was confirmed by validating a scratch plugin with and without the quotes.

## [2.1.0] - 2026-07-28

### Changed

- **`plan-review` now grounds plans in the codebase and drafts what is missing.** Shaped by a
  live run against a real plan (which caught a conditionally-wrong behavioral claim no
  text-only review could have seen):
  - **Codebase Grounding** is a required step: existence, pattern, stack, and behavior checks
    over every claim the design depends on; findings route to Feasibility (1-2 unverifiable
    claims YELLOW, approach hinges on code that does not exist or behave as described RED).
  - **Completeness is anchored to the `/plan-feature` canonical section list**, so a plan can no
    longer score GREEN by silently omitting a section (previously it was judged only against the
    headings it declared).
  - **Draft, don't instruct:** a missing or failed Acceptance Criteria section gets a paste-ready
    draft in the review (3-6 testable criteria derived from goals and scope), and a missing
    Testing Strategy gets a drafted test plan; never just "add criteria". The gate's
    where-to-look list now includes test-plan sections with objectively pass/fail assertions.
  - **Mechanical verdicts:** any RED is Major Rework; 2+ YELLOW or a milestone-1 blocker is
    Needs Revision; otherwise Ready. The summary must state whether milestone 1 is blocked.
  - **Open Questions** now score under Dependencies when work depends on them; the
    Roles-vs-stages MECE pairing applies only when the plan assigns owners (solo plans skip it).
  - **Report-only with an offer-to-apply handoff** that follows the plan's own revision
    conventions, plus a re-review protocol: verify a prior revision note against the body, and
    never re-litigate decisions the plan records with rationale and evidence.

## [2.0.0] - 2026-07-27

### Changed

- **BREAKING: the plugin is now named `tadw`.** Every skill, agent, and command was addressed
  through a 31-character prefix (`templeton-agentic-dev-workbench:fresh-eyes-cr`) before the part
  that carried any meaning. The invocation namespace is derived from the plugin's name, so shortening
  the name shortens every invocation: `tadw:fresh-eyes-cr`, `tadw:code-reviewer`, `/tadw:quality-gates`.

  There is no compatibility shim. Listing the plugin under both names would install every skill and
  command twice and fire the `SessionStart` hook twice per session, so this is a clean cut. To
  upgrade:

  ```bash
  /plugin marketplace update templeton-agentic-marketplace
  /plugin uninstall templeton-agentic-dev-workbench@templeton-agentic-marketplace
  /plugin install tadw@templeton-agentic-marketplace
  ```

  Then restart the session. Anything outside this repo that names a skill or agent by its full
  prefix (`.outrigger/config` files, `RALPH.md`/`AGENT.md` prose, `Skill(...)` and `Agent(...)`
  permission entries in `.claude/settings.local.json`) needs the prefix rewritten; a stale prefix
  fails to resolve rather than falling back.

  Unaffected: the repository name and its git remote, the `TADW_STYLE_CORE` environment variable and
  the `.tadw-style-core-off` flag file, and the `tadw-*` beads issue prefix. Those were never derived
  from the plugin name and keep working untouched.

## [1.19.2] - 2026-07-22

### Fixed

- **The failure marker ignored the off-switch.** The `|| echo <marker>` fallback added in 1.18.1
  fired whenever `node` failed, including for users who had deliberately disabled the style core.
  They got `<!-- house-style-core: FAILED to load -->` injected into every session, which is both
  noise and a lie: nothing failed, they turned it off. Hooks now run through `hooks/run-hook.sh`,
  which checks the off-switch **before** spawning `node`. That ordering is the fix, since no
  node-missing path can skip a check that already happened.
- **The wrapper depended on the environment it exists to survive.** Two defects found while
  iterating on the fix above, both the same silent-no-op class it was meant to eliminate. It
  lowercased with `tr`, so on a PATH without `tr` the substitution failed silently, the value read
  as empty, and `TADW_STYLE_CORE=off` was ignored entirely. And an unset `HOME` aborted it under
  `set -u`, emitting neither the core nor the marker. It now uses no external command and defaults
  `HOME`, verified under both `sh` and `dash`.
- **A temp-directory leak in the hook suite,** pre-existing and worsened by the new checks: roughly
  26 directories per run were left in the system temp dir, accumulating on every dev machine and
  CI push. All scratch directories now live under one root removed on exit.
- **`TypeError` instead of a clean assertion** when a manifest entry lacks a `hooks` array.

### Changed

- **The hook suite goes from 6 to 11 checks**, each added after a real defect shipped green under
  a narrower suite. The two most valuable are new kinds rather than new cases. One **executes the
  real manifest commands** against a working and a broken `node`; everything else tested the
  manifest as a string and the wrapper as a program, never together, so a shell-quoting error
  could ship green (it matters most for the `SubagentStart` fallback, which is JSON nested inside
  single quotes inside a JSON string). The other guards `commandWindows`, which cannot be executed
  on macOS or the Linux runner and had no guard at all, which is how it lost the off-switch in the
  first place; the suite now asserts it references both off-switch paths and a failure marker.
- **The check count documented in `AGENTS.md` is asserted, not remembered.** It drifted three
  times while this work was in progress, so the suite now compares the documented number against
  the number of checks it actually ran.

### Known limitations

- `runtime.js` resolves the default config dir with `os.homedir()`, which falls back to the
  password database, while `run-hook.sh` uses `$HOME` only. They diverge solely when `HOME` is
  unset **and** the flag file exists **and** `node` is broken. Closing it needs either an external
  command or tilde expansion, which `dash` does not perform with `HOME` unset, so it is documented
  in place rather than fixed by reintroducing the dependency the wrapper just removed.
- `commandWindows` is guarded structurally but remains unexecuted; no PowerShell is available on
  macOS or the CI runner.

## [1.19.1] - 2026-07-22

### Fixed

- **The sentinel markers could be widened to exempt the whole document, and the check reported
  OK.** Moving `<!-- leak-check:appendix-start -->` above the principles left both markers well
  formed and every required heading present, so nothing objected: the checker scanned one line and
  printed a clean pass. Unlike the five bypasses this design replaced, that needs a deliberate
  edit rather than ordinary markdown, but a self-check that can be silently disabled by moving one
  line is not much of a self-check. The required principle sections must now appear as `## `
  headings OUTSIDE the exempt region, so widening the markers past them fails with a named
  section rather than passing. Found by adversarial testing of the new design, not by review.

## [1.19.0] - 2026-07-22

### Changed

- **The framework-leak check no longer parses markdown.** It located the exempt appendix by
  finding a `## Appendix` heading, which meant it had to know whether that heading sat inside a
  fenced code block. Five bypasses shipped from that one decision: a fenced fake heading, a ````
  block containing ```, a closing fence carrying an info string, an over-indented fence, and an
  exemption that ran to end of file. Each was patched by adding another CommonMark rule to a
  hand-rolled scanner, and each patch left the next rule unimplemented. The exempt region is now
  delimited by explicit `<!-- leak-check:appendix-start -->` and `<!-- leak-check:appendix-end -->`
  sentinels, and the fence scanner is deleted. Two properties make that safe: exactly one of each
  marker is required, so a marker duplicated inside a code sample is an error rather than an
  ambiguous choice; and any marker problem disables the exemption entirely and scans the whole
  document, so the failure mode is a visible false positive rather than a silent pass.
- **The exemption is bounded.** It previously ran from the appendix heading to end of file, so a
  section appended after the appendix was silently exempt. It now covers only the region between
  the two markers.
- **The regression suite derives its cases from the design contract, not from known bugs.** The
  previous suite enumerated bugs already found and reported "All 15 checks passed" while three
  live bypasses existed in the function it covered. Cases are now grouped by contract (marker
  contract, exemption scope, parser independence) and cover 23 checks, including all five historic
  bypasses as parser-independence assertions and the previously untested frontmatter
  name-versus-directory branch.

### Fixed

- **CI ran no tests at all.** The only job was `rumdl fmt --check .`, so both `hooks/test-hooks.js`
  and the leak checker suite were run only when a human remembered. A `tests` job now runs both
  suites plus the leak check on the shipped skill. Both are stdlib-only, so no install step is
  needed.
- **Markdown linting was failing on `main`.** Files added earlier today carried five `rumdl`
  violations, so the one CI job that did exist was red and unnoticed. Fixed, including a
  line-initial `36.` in a plan document that markdown was rendering as an ordered list item.

## [1.18.3] - 2026-07-22

### Fixed

- **The 1.18.2 fence fix was incomplete and left a second bypass open.** It treated any
  fence-looking line as a toggle, so a ```` block containing a ``` line read as closed. The
  `## Appendix` heading inside that block was then seen as a real heading, split the document
  early, and exempted everything after it. A file with `pytest` in its body exited 0 again, the
  same failure the previous release claimed to fix. Fence matching now follows CommonMark: a block
  opened with N of a character closes only on a run of at least N of that same character, so a
  `~~~` line inside a ``` block is correctly treated as content.

### Added

- **A 15-case regression suite for the leak checker** at
  `skills/style-testing/scripts/test_check_framework_leak.py` (stdlib only, no install, mirroring
  `hooks/test-hooks.js`). Two bypasses shipped in consecutive releases because this script had no
  tests and each ad-hoc verification was thrown away. The suite pins both bypasses, the
  code-comment heading bug, the guard against false-positives on legitimate fenced pseudocode, and
  asserts the shipped `SKILL.md` satisfies its own checker. Reverting either fence fix now fails
  the suite.

## [1.18.2] - 2026-07-22

### Fixed

- **`check_framework_leak.py` could be silently disabled by a code fence.** The script split the
  document at the first line matching `## Appendix` without checking whether that line was inside
  a fenced code block. A fence containing that heading (entirely plausible in a document that
  shows its own structure) ended the body early, so every framework token after it was treated as
  appendix content and exempted. A file containing `pytest` in its body passed the check. The
  script is now fence-aware.
- **Required-section detection accepted code comments as headings.** `check_sections` collected
  every line starting with `#`, which includes shell and Python comments inside fenced examples.
  A file whose only real heading was the appendix passed the structural check because
  `# Principles` appeared in a code sample. Headings are now only counted outside fences.

Both bugs shared one root cause and were found by edge-case testing rather than review; the
regression cases are documented in the fix commit.

## [1.18.1] - 2026-07-22

### Fixed

- **The `SessionStart` matcher missed the `fork` session source, so forked sessions got no style
  injection at all.** Claude Code declares five `SessionStart` sources; the matcher listed four.
  Any session created by a conversation rewind, a branch, or `--fork-session` started with no
  coding-style core and no response style, silently, with no error and no marker to notice it by.
  The matcher is now `startup|resume|clear|compact|fork`.
- **`/response-style` was a no-op.** The command told the model to load the `house-response-style`
  skill, but that skill sets `disable-model-invocation: true`, so the Skill tool hard-refuses it.
  The one designed recovery path for style drift after a compaction, and the only way to get the
  response style inside a subagent, therefore did nothing. The command now **reads**
  `skills/house-response-style/SKILL.md` directly, which keeps the single source of truth while
  preserving the skill's non-model-invocable design.
- **Hook failures are now visible instead of silent.** Each command was `node "..."; exit 0`,
  which converted every possible failure (missing `node`, syntax error, bad permissions) into a
  successful no-op. Commands are now `node "..." || echo <failure marker>`, so a failure injects
  `<!-- house-style-core: FAILED to load ... -->` rather than nothing. The absence of any marker
  now means the hook did not run; a FAILED marker means it ran and could not execute. The
  `SubagentStart` fallback emits valid JSON so the wrapper contract still holds.
- **`AGENTS.md` claimed `plugin.json` performs component registration. It does not.** The file
  carries metadata plus the `hooks` field and lists zero components; skills, agents, and commands
  are auto-discovered from their directories. The "Adding a New Skill" and "Adding a New Agent"
  steps told readers to edit it, which had already produced one unsatisfiable acceptance criterion
  in the tracker. They now name the real registration surfaces, and the skill steps add the
  orphan-check requirement that `/validate-plugin` enforces.

### Changed

- **`hooks/test-hooks.js` now covers the manifest, not just the scripts.** The suite went from 4
  checks to 6, adding one that asserts the `SessionStart` matcher covers all five sources, that
  every referenced script exists, and that no command can fail silently; and one that guards
  `/response-style` against being routed back through the Skill tool. Both of the bugs fixed above
  shipped green under the old suite, which never opened `style-core-hooks.json`.

## [1.18.0] - 2026-07-22

### Added

- **`style-testing`, a universal framework-independent test-style core.** Until now the only
  test guidance in this workbench was `style-rspec`, so anyone working in pytest, Vitest, XCTest,
  or Minitest got nothing, even though most of what makes a good test is framework-independent.
  The new skill carries 14 principles: ten transposed from `style-rspec` (outermost fast seam,
  name the action once, hoisted declarative setup, one behavior per test, scenario-named groups,
  lightest sufficient fixture, lazy-unless-ordering-matters, deterministic identification by
  unique key, shared setup visible to every case, prerequisites before the action) and four
  net-new that nothing in the repo covered (determinism with injected clocks and seeds,
  behavior-not-implementation naming, what not to test, and one clear cause of failure per
  assertion). Examples use a declared neutral pseudocode so no rule reads as belonging to one
  framework, and a single fenced appendix maps every principle to its pytest, Vitest/Jest,
  XCTest/Swift Testing, and Minitest idiom.
- **`check_framework_leak.py`, enforcement for the above.** The core's value rests entirely on
  the principles staying framework-free while the appendix carries the concreteness. Author
  discipline does not hold that line across edits, so a stdlib-only script does: it scans
  everything between the frontmatter and the appendix for framework tokens and fails the build on
  any leak. It caught a `style-rspec` reference in the skill's own introduction on its first run.
- **An invocation battery for the skill's `description`.** For a model-invoked skill the
  description is the only thing that determines whether it ever fires, and `style-rspec` is the
  cautionary example: its description was scoped so narrowly ("RSpec tests in Rails apps") that it
  could not fire on this repo's current work. The battery at
  `skills/style-testing/references/invocation-battery.md` runs 8 realistic test prompts and 3
  controls against a 7-of-8 bar. First run passed 8/8 with 0/3 false fires.

### Changed

- **`style-rspec` is now a thin delta on `style-testing`, down from 496 lines to 119.** Everything
  that would still read as correct advice with the RSpec nouns stripped out moved into the core.
  What remains is the RSpec spelling of those principles as a mapping table, plus four genuinely
  Rails mechanics with no framework-free parent: `let` versus `let!` evaluation semantics,
  `expect { subject }` versus a bare `subject` call, FactoryBot's three build strategies, and
  `it_behaves_like` resolving variables at invocation rather than definition.
- **Test files now route to `style-testing` through the agents, not just the docs.**
  `software-engineer` and `code-reviewer` dispatch to style skills by file extension and had no
  entry for test files at all, so a skill wired only into `AGENTS.md` and `README.md` would have
  shipped unreachable, which is precisely the state `style-rspec` was in. Both agents plus
  `/python-feature-dev` now match test-file patterns across Python, TypeScript, Ruby, Swift, and
  Go. This also satisfies `/validate-plugin`'s orphan rule, which counts referrers in `agents/`
  and `commands/` but not `skills/`.
- **`review-rails` defers to `style-testing` for test style,** naming `style-rspec` only when the
  project's suite is actually RSpec.
- **The `bv` agent-instructions block moved out of `AGENTS.md` into `docs/beads-workflow.md`.**
  Ninety lines of generated tracker documentation, largely duplicating the existing "Issue
  Tracking (br + bv)" section, had been appended to the top-level agent instructions. `AGENTS.md`
  drops from 727 to 642 lines and links to the extracted file, which records its own provenance
  including the marker `bv` uses, so a future re-injection is recognizable rather than mysterious.

## [1.17.0] - 2026-07-22

### Changed

- **Response style is now a single-source skill.** The always-on response style
  moved from a hooks-local copy (`hooks/response-style.md`) into a proper skill
  at `skills/house-response-style/SKILL.md`, and the `SessionStart` hook now
  reads that file (stripping its YAML frontmatter) as its source. The always-on
  injection and the new on-demand surface can no longer drift, mirroring the
  single-source pattern the coding-style core already uses for the `style-*`
  skills. Parent-session-only injection, the off-switch, the fallback, and the
  parent-only-not-subagent policy are unchanged.

### Added

- **`/response-style` command and `house-response-style` skill.** The response
  style is now directly invocable to re-anchor after a compaction or to load the
  rules inside a subagent (which does not inherit the parent session's injected
  style). The skill body is more thorough than the prior hooks copy: it states
  its persistence, grounds the rules in *why* (the answer is the payload, the
  reader scans rather than parses, structure is a signal), pairs each concise
  rule with a Bad/Good example, lists escape hatches (explain/walk-me-through,
  a rule that would delete the answer, destructive actions, real ambiguity), and
  closes with a pre-send check.
- `test-hooks.js` now asserts the response-style frontmatter is stripped before
  injection (no skill frontmatter keys leak into the injected text).

## [1.16.0] - 2026-07-20

### Added

- **Acceptance criteria enforced across the plan and bead pipeline.** Every
  plan and bead must now carry testable acceptance criteria, closing a gap
  where `/plan-feature` could emit a plan with none while `/plan-review` and
  `/plan-to-beads` required them. `feature-planner` gains an Acceptance
  Criteria section and a per-milestone "Done when" column; `plan-review` gains
  an Acceptance Criteria gate that runs before scoring (a plan with none, or
  only subjective ones, is Actionability RED → Major Rework); `project-manager`
  gains the matching belief and refusals; `feature-development` captures
  criteria in discovery.
- **`/agentic-clean-code` command**, giving the existing `agentic-clean-code`
  skill an entry point instead of leaving it an orphan.
- **`/bead-audit-all` command**: a bounded, report-only sweep of the whole
  backlog. Enumerates every bead via `br list --status open --limit 0 --json`,
  runs the `bead-audit` skill on each exactly once, and prints a ranked
  health table (worst band first). Distinct from `/goal`, it terminates on its
  own rather than installing a Stop hook, and never writes back.
- **Scorecard in `bead-audit`.** An optional weighted 0-100 score, banded
  Poor / Weak / Adequate / Great / Excellent, derived from the existing
  content and structure verdicts and capped so the band can never outrank the
  pass/fail verdict (Excellent is exactly equivalent to PASS). `score`, `band`,
  `score_denominator`, and `excluded_dimensions` added to the JSON output. Ships
  a fixture regression suite under `skills/bead-audit/references/fixtures/`.
- **ADR 0001: native tracker fields are canonical.** `br`'s `design`, `notes`,
  and `acceptance_criteria` fields are the canonical home for those sections,
  not the description body. `plan-to-beads` now writes each section to its
  native field (create-then-update), so generated beads pass `bead-audit`'s
  structure check on creation.
- **`docs/plans/feature-plan-bead-refine.md`**, the plan for a scored backlog
  refinement loop. Milestone 1 (the scorecard above) shipped; the driver is
  deferred pending a state-machine respecification of its termination logic.

### Fixed

- `plan-to-beads`: replaced `printf` with quoted heredocs in the `br update`
  examples, so acceptance criteria containing a literal `%` are no longer
  silently corrupted; reworked Step 5b to handle the two-call model's
  created-but-unpopulated failure state without producing duplicate beads.
- `bead-audit`: corrected the JSON `score_denominator` documentation (a bug's
  base is 110, not 100) and clarified that per-check `points` exclude the
  separately-computed structure contribution.

### Changed

- `.beads/.gitignore` excludes `br`'s local `.br_history/`.

## [1.15.1] - 2026-07-13

### Added

- Always-on response style (`hooks/response-style.md`): the `SessionStart` hook
  now injects a second document alongside the coding-style core that governs
  how responses to the user are written. Three rule sets: be concise (lead
  with the answer, cut narration, selective rather than compressed); suggest
  one follow-up question ("Worth asking next: ...") only when the answer
  genuinely raises it, never as a ritual; and end any response that leaves
  work open with a "Next actions" section split by owner ("Me (Claude)" vs
  "You"), omitted entirely when nothing is open. Injected
  into parent sessions only; `SubagentStart` deliberately keeps injecting the
  coding-style core alone, since a subagent's final text is consumed by the
  orchestrator as data, not read by a human. Opens with its own
  `<!-- house-response-style: loaded -->` marker; covered by `test-hooks.js`
  (present in `SessionStart`, absent in `SubagentStart`); shares the existing
  off-switch (`TADW_STYLE_CORE=off` / flag file).

## [1.15.0] - 2026-07-08

### Added

- `production-ops` skill and `/prod-ops` command: safely operate the production
  apps (atlas, meridian, compass, ...) that run as Docker Compose stacks on a
  single Hetzner VPS, over a two-hop SSH login (`root`, then `su - deploy`).
  Covers service ops (status, logs, restart, `up -d`, recreate) and PostgreSQL
  data ops (migrations, backups, one-off data fixes) under strong guardrails:
  read-only by default, a secret-free `hetzner-prod` SSH alias (no IP in the
  repo), a mandatory `pg_dump` before any data mutation, transactional one-off
  writes with a matched row count, verify-after, a written rollback for every
  risky change, and hard-stops (refuse + escalate) on volume wipes, `prune`,
  `DROP`/`TRUNCATE`, and `WHERE`-less `UPDATE`/`DELETE`. Host-specific facts are
  pinned in a single Environment Profile block so the technique stays generic and
  retargetable.

## [1.14.0] - 2026-07-07

### Added

- `roadmap-dashboard` skill and `/roadmap-dashboard` command: synthesize the
  codebase and the `beads` tracker into one self-contained, zero-dependency
  interactive HTML dashboard at `docs/roadmap.html` (executive KPIs, pure
  HTML/CSS diagrams, Kanban board, prioritized roadmap). Ships a bundled
  `collect_beads.py` data-collection script and versions the output
  (`docs/roadmap-vX.Y.html`) instead of overwriting a prior report.

### Changed

- `product-surface-docs` skill and `/product-surface-docs` command are now
  refresh-first: when a `docs/products/` tree already exists, the run updates it
  in place (human prose preserved, facts corrected additively, `last_reviewed`
  bumped, findings reconciled against the ledger) rather than regenerating from
  scratch. Full generation happens only for a surface, or a tree, that does not
  yet exist, which makes the command safe to run on a schedule.
- Style core (`hooks/style-core.md`): promoted "comment the why, not the what"
  to its own standalone principle, and aligned the `review-rails` skill with it.
- Documentation: `AGENTS.md` and `README.md` updated to cover the new command
  and skill.

### Fixed

- `.gitignore` now excludes Python `__pycache__/` and `.pyc` build artifacts,
  and a previously tracked `.pyc` was removed from version control.

---

Releases prior to 1.14.0 predate this changelog; their history is recorded in
the git tags and commit log (latest prior tag: `v1.13.0`).

[Unreleased]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v1.14.0...HEAD
[1.14.0]: https://github.com/jtemplet/templeton-agentic-dev-workbench/compare/v1.13.0...v1.14.0
