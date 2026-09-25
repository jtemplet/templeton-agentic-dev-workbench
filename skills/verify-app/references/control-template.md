# Verification Control Document Template

This template holds what every journey in one project shares: how to start the application, how to
sign in, and which browser tool to use. Copy it to `docs/verification/control.md` in the project
and fill each field once. The `verify-app` skill reads that copy, so it can start the application
and reach a signed-in session without asking you a question.

A field that is empty or vague makes `verify-app` stop and ask. Fill every field, even when the
answer is "nothing".

This file keeps the environment apart from the journey. The steps of one journey belong in the
**How to drive this** section of a leaf document under `docs/products/`, never here.

## How to fill it

Copy everything below the line into the project. Replace each example with the project's own
value. Keep the field names exactly as written, because the skill finds each field by its name.

---

## launch

**Holds:** the command that starts the application, and the port it answers on.

Write one command. Say whether it runs in the foreground or the background. Name the directory to
run it from when it is not the repository root.

```text
Command: bin/dev
Directory: repository root
Mode: background
Port: 3000
```

## ready_check

**Holds:** a command that exits 0 once the application answers, and non-zero before that.

`verify-app` runs this command in a loop after `launch`, and drives nothing until it exits 0. Do
not use a fixed wait. Give the number of seconds after which the loop stops and reports a failure.

```text
Command: curl -fsS http://localhost:3000/up
Give up after: 60 seconds
```

## base_url

**Holds:** the address to drive, on this machine.

Write the scheme, the host, and the port, with no trailing slash. A leaf document gives each route
relative to this address.

```text
http://localhost:3000
```

## auth

**Holds:** how to reach a signed-in session without clicking through a signup form.

Signing in is setup here, not the thing under test. Do not click through a signup form, an email
confirmation, or a password reset to get a session. Use a shortcut that skips them: a seeded
account, a development-only login route, a token in the environment, or a saved browser session.
Name the credentials or the file that holds them. Never write a real secret in this document.

When one journey tests signup or sign-in itself, that journey signs in by hand and says so in its
own leaf document. This field still holds the shortcut for every other journey.

```text
Method: development-only login route
Steps: navigate to {base_url}/dev/login?as=lender and wait for the dashboard heading
Account: the seeded lender from db/seeds.rb, no password needed on this route
Signed-in check: the text "Dashboard" is on the page
```

## browser

**Holds:** which browser tool to load, and the exact `ToolSearch` query that loads it.

Name one tool. `verify-app` runs the query before it drives the application, so write it in full.

```text
Tool: Claude in Chrome
Query: select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__tabs_create_mcp
```

## teardown

**Holds:** what to clean up after the run, or a plain statement that nothing needs cleaning.

Never leave this field empty. An empty field reads as a forgotten one, and the skill cannot tell
the difference. When the application leaves nothing behind, write `None needed:` and give the
reason on the same line.

List each step as one command. Say whether the run stops the application it started.

```text
Stop the application: kill the process that launch started
Remove test data: bin/rails runner "User.where(email: /@example.test\z/).destroy_all"
```

A project that needs no teardown fills the field like this:

```text
None needed: the application uses an in-memory database, and the process exits with the run.
```
