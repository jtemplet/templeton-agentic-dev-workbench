---
name: verify-app
description: "Prove that a change works in the running web application: launch it, sign in, drive one journey through the agent-browser CLI, and report PASS, FAIL, or a stale selector, step by step. Use when someone asks whether a change actually works in the app, asks to verify, check, or click through a feature in the browser, or when quality-gates hands off a browser-ui change. Reads the project's docs/verification/control.md and the How to drive this block of a leaf document under docs/products/. Ends with one machine line: VERIFY_PASS, VERIFY_FAIL <step>, VERIFY_STALE <step>, or VERIFY_BLOCKED <reason>. Report-only: it never edits a file. Not for judging design quality (ux-review) or for an iOS app."
---

# Verify App

This skill decides one question for a web application: does this journey work in the running
application, right now? It launches the application, signs in, drives the journey in a real
browser, and reports what it saw at each step. The person or agent who asked reads one verdict and
one machine line.

It reports and never edits. A failing journey is a finding for someone else to fix.

## When to Use / When NOT to Use

Use it when:

- Someone asks "does this change actually work in the app?", or asks to click through a feature.
- `/quality-gates` routed a `browser-ui` change, and the HANDOFF needs a result.
- A bug report names a screen, and the investigation needs an observation from the running page.

Do not use it when:

- The question is design quality, accessibility, or layout. That is `ux-review`.
- The application is an iOS app. This skill drives a web browser alone.
- The change has no screen, such as a library, a command-line tool, or a REST endpoint. Use
  `/quality-gates`, which probes a REST endpoint with real requests.

## The four outcomes

Every run ends with exactly one of these lines, as the last line of the report. A caller such as
`quality-gates` reads it, so print it verbatim and print nothing after it.

<!-- verify-outcomes:start -->

| Last line | Meaning |
|---|---|
| `VERIFY_PASS` | Every step ran, and every success signal appeared |
| `VERIFY_FAIL <step>` | The application misbehaved at that step: an error, or a success signal that never appeared |
| `VERIFY_STALE <step>` | The page rendered without an error, but the drive block's selector matched nothing at that step |
| `VERIFY_BLOCKED <reason>` | The run could not reach the journey. `<reason>` is one of `browser`, `control`, `journey`, `launch`, or `auth` |

<!-- verify-outcomes:end -->

`<step>` is the number from the report table, such as `3`. Use one line per run. When a run drives
several journeys, the worst outcome wins, in this order: BLOCKED, FAIL, STALE, PASS.

**A stale selector is never a FAIL.** A selector that matches nothing on a page that rendered
cleanly means the drive block is out of date. That is stale documentation, not a defect in the
application. Report it as STALE so nobody files a bug against working code.

## Step 1: Check the browser tool

Run this before you read anything else:

```bash
command -v agent-browser && agent-browser --version
```

When the command finds nothing, stop. Report that this skill drives the browser with the
`agent-browser` command-line tool, and give the install command:

```bash
npm i -g agent-browser && agent-browser install
```

End with `VERIFY_BLOCKED browser`. Do not fall back to another browser tool, and do not guess at
the page through `curl`. A run that cannot open the page has no verdict to give.

## Step 2: Read the control document and the journey

**Read `docs/verification/control.md` in the project.** It holds six fields: `launch`,
`ready_check`, `base_url`, `auth`, `browser`, and `teardown`. The template a project copies is
[references/control-template.md](references/control-template.md).

Stop with `VERIFY_BLOCKED control` in three cases, and name the field each time:

- The file does not exist. Point to the template.
- A field is empty, or too vague to run, such as `Command: start the server`.
- The `browser` field names a tool other than `agent-browser`.

**Then find the journey.** The input decides where it comes from.

| Input | Where the journey comes from |
|---|---|
| A journey name, such as `deals` | The leaf document under `docs/products/` whose filename or title matches the name |
| Nothing | The leaf documents whose `source_refs` frontmatter names a file in the changed set |
| A sentence | The sentence itself, when no leaf document covers the journey yet |

For a journey name or for no input, read the drive block between `<!-- drive:start -->` and
`<!-- drive:end -->` in the leaf document. It holds five lines: Route, Precondition, Selector,
Action, and Success signal. Find the block by those comments, never by its heading.

For no input, resolve the changed set with `git diff --name-only "$(git merge-base HEAD main)"`
plus `git status --porcelain`. Use the repository's default branch in place of `main` when it has
another name.

Stop with `VERIFY_BLOCKED journey` when no leaf document matches, or when two match a journey name
and nothing tells them apart. Name the candidates.

**A block marked `Not drivable` is not a journey.** Report the reason it gives, drive nothing for
that document, and end with `VERIFY_BLOCKED journey` when it was the only one.

**A sentence becomes a drive block before the run.** Write the five lines yourself, from the
sentence and from what the page shows. Print them in the report under "Journey derived from the
request", so the reader can see what you drove.

## Step 3: Launch the application and wait for it

Run `ready_check` once first. When it already exits 0, the application is running. Do not launch a
second copy, and record that this run did not start it.

Otherwise run the `launch` command from the directory it names. Run a background launch with the
Bash tool's `run_in_background`, so it does not hold the shell. Then poll. This example uses the
template's `ready_check`, so put the project's own command in place of the `curl`:

```bash
for i in $(seq 1 30); do
  curl -fsS http://localhost:3000/up >/dev/null && echo READY && break
  sleep 2
done
```

Size the loop to the `Give up after` value in the control document: 30 rounds of 2 seconds give
up after 60 seconds, and a 20-second limit takes 10 rounds. Never replace the poll with a fixed
wait.

**Record the process this run started.** A background launch gives the Bash tool a task id, not a
process id. Once the poll prints `READY`, find the process that listens on the `Port` from the
`launch` field, and write its id in the report:

```bash
lsof -ti tcp:3000 -sTCP:LISTEN
```

Step 6 stops that process and no other.

When the loop ends without printing `READY`, the poll gave up. Stop. Quote the last lines the launch
command printed, run the teardown for whatever this run started, and end with
`VERIFY_BLOCKED launch`.

## Step 4: Open a browser session and sign in

**Name a session for this run, and pass it on every command.** The default session is one browser
shared with every other agent on the machine. A shell variable does not survive from one Bash call
to the next, so write the name out each time. Make the name from the `Session prefix` in the
`browser` field and the journey name. The template's prefix is `verify`, and this example drives
the journey `deals`:

```bash
agent-browser session id --scope worktree --prefix verify-deals
```

The id is the same every time it runs in one worktree with one prefix. The journey name keeps two
journeys apart. Never run the same journey twice at once in one worktree.

Every later command takes the form `agent-browser --session <id> <flags> <command>`. `<flags>` is
the `Flags` line of the `browser` field, left out when it says `none`.

**Sign in with the `auth` field, and never through a signup form.** Signing in is setup here, not
the thing under test. Follow the field's steps, then confirm its signed-in check. A sign-in that
fails ends the run with `VERIFY_BLOCKED auth`. Quote what the page showed instead.

A journey whose own leaf document says it tests sign-in or signup skips this step. Its drive block
signs in by hand.

## Step 5: Drive the journey

**A step is one table row in the report: one command, and what it showed.** Number the steps
from 1, and write each one down as you go. A Precondition of `none` takes no step. The step number
in `VERIFY_FAIL` or `VERIFY_STALE` is the number of the row that failed, such as the `get count`
row for a stale selector.

**Take a snapshot before each screen.** Run this after every navigation, and after every action
that changes the page:

```bash
agent-browser --session <id> snapshot -i
```

A snapshot lists the elements on the page with fresh references such as `@e3`. A reference is
stale as soon as the page changes, so take a new snapshot before you use one again.

`snapshot -i` lists the elements a person can click or type in, and nothing else. Text that an
action writes into a plain block of the page does not show in it. Read that text with
`agent-browser --session <id> get text body`, or confirm it with the Success signal wait, never
from an unchanged snapshot.

Drive each block in this order:

1. **Route.** Run `agent-browser --session <id> open <base_url><Route>`, then take a snapshot.
2. **Precondition.** Confirm the state the block names from the snapshot. A precondition that does
   not hold is a FAIL at this step, unless the run can create it with a documented setup step.
3. **Selector.** Run `agent-browser --session <id> get count '<Selector>'`. A count of 0 needs
   the check below, before you report anything.
4. **Action.** Do what the block says, with `click`, `fill`, `select`, or `press`, then take a
   snapshot.
5. **Success signal.** Wait for it with a timeout, such as
   `agent-browser --session <id> wait --text "<signal>" --timeout 15000`. Exit 0 means the
   signal appeared. Exit 1 means it did not.

**Tell a stale selector from a broken page.** When the selector matches nothing, read the page:

```bash
agent-browser --session <id> get text body
agent-browser --session <id> errors
```

An `errors` command that prints nothing means the page raised no uncaught exception.

- The page shows an error message, an HTTP error page, or `errors` lists an uncaught exception.
  That is FAIL at this step.
- The page rendered cleanly, and the feature is still there under another selector or another
  label. That is STALE at this step. Name the element from the snapshot that looks like the
  intended one, so the author can update the block.
- The page rendered cleanly, and the feature is not there at all. That is STALE as well. The
  journey cannot tell a removed feature from a moved one, so it does not guess.

**On a FAIL, quote the screen.** Run `get text body` and `errors`, and copy the error text exactly
as the page shows it, in quotation marks. When the page shows no error text, write "no error text
on screen", and say what the page showed instead. Stop driving that journey after its first FAIL
or STALE step, because every later step depends on it.

## Step 6: Tear down and report

**Tear down first, then report.** Close the browser session with
`agent-browser --session <id> close`. Then run each step in the `teardown` field. Stop the
application only when this run started it in Step 3. A teardown step that fails goes in the report,
and it does not change the outcome.

**Report in this shape:**

```text
## Verify App: <journey>

**Application:** <base_url>, started by this run (or: already running)
**Journey from:** docs/products/<surface>/<leaf>.md (or: derived from the request)

| Step | Action | Observed | Result |
|---|---|---|---|
| 1 | open /deals | heading "Deals", 12 elements | PASS |
| 2 | get count [data-testid="deal-row"] | 3 matches | PASS |
| 3 | click the first row | page header "Acme loan" | PASS |
| 4 | wait for text "Acme loan details" | timed out after 15 s; on screen: "Error: deal could not be loaded (500)" | FAIL |

**Teardown:** browser session closed; application stopped
**Outcome:** FAIL at step 4

VERIFY_FAIL 4
```

Each `Observed` cell holds what the page showed, never what you expected it to show. The machine
line is the last line, alone, with nothing after it.

## Critical Rules

**Always:**

- Check for `agent-browser` before anything else, and stop with `VERIFY_BLOCKED browser` when it
  is missing.
- Poll `ready_check`, and never wait a fixed time.
- Use a named session on every `agent-browser` command, and close it at the end.
- Take a snapshot before each screen, and before you reuse a reference.
- Quote on-screen error text exactly, in quotation marks.
- Report a selector that matches nothing on a clean page as STALE, never as FAIL.
- End with exactly one machine line, as the last line.

**Never:**

- Edit a file. This skill reports and never edits: not the application, not a test, and not the
  drive block, even when the block is stale. Name the fix, and leave it to the author.
- Click through a signup form, an email confirmation, or a password reset to get a session.
- Drive any browser other than through `agent-browser`.
- Stop an application this run did not start.
- Report PASS for a step you did not observe. A step you skipped is not a step that passed.
