---
description: "Prove a change works in the running web app: launch it, sign in, drive one journey through agent-browser, and report PASS, FAIL, or a stale selector per step"
argument-hint: "[journey name | sentence describing the journey]"
---

**Read** `${CLAUDE_PLUGIN_ROOT}/skills/verify-app/SKILL.md` and follow it to verify the journey
given in $ARGUMENTS.

Read the file rather than invoking the skill by name. `commands/verify-app.md` and
`skills/verify-app/SKILL.md` share one `tadw:` invocation namespace and the command wins, so
`Skill(verify-app)` returns this file and never reaches the skill. If that path does not resolve,
locate the file with `Glob: **/skills/verify-app/SKILL.md` and read it from there.

`$ARGUMENTS` takes one of three forms:

1. A journey name, such as `deals`. The skill drives the drive block of the matching leaf document
   under `docs/products/`.
2. Nothing. The skill picks the leaf documents whose `source_refs` name a changed file.
3. A sentence. The skill derives the journey from it, when no leaf document covers it yet.

This command runs the skill in this session. To keep the browser output out of this window,
dispatch the `verify-app` agent instead (`agents/verify-app.md`). It runs the same skill on
`sonnet` and returns the same report.

The skill will:

1. Check that the `agent-browser` command-line tool is installed, and stop with the install
   command when it is not
2. Read `docs/verification/control.md` and the journey's drive block
3. Launch the application and poll its ready check
4. Open a named browser session and sign in through the `auth` shortcut
5. Drive the journey, taking a snapshot before each screen
6. Tear down, then report each step and end with `VERIFY_PASS`, `VERIFY_FAIL <step>`,
   `VERIFY_STALE <step>`, or `VERIFY_BLOCKED <reason>`

It reports and never edits a file.
