# 0013. Version 3 reports reach readers before producers, and success never downgrades

**Date:** 2026-10-15
**Status:** Accepted
**Amends:** [ADR 0011](0011-a-reconcile-skill-reads-its-findings-from-the-report-file.md): its
version rule, and the one exception to its rule 1

## Context

The quality-gates and acceptance reports move to version 3. Version 3 adds an invocation ID, frozen
expected inputs, and evidence records. The
[validation report contract](../validation-report-contract.md) specifies every field and every
reader decision. The owner chose version 3 on 2026-10-11, in the validation reports plan reviewed at
commit `a31e94a`.

Four facts decide how the change can ship.

**Every reader that checks the version refuses any version other than 2 today.** ADR 0011 says a
loader refuses another version with `report-unreadable`. Both reconcile loaders set
`REPORT_VERSION = 2`. Outrigger's acceptance reader, `cmd/outrigger-phased/verifyacceptance.go` in
the Outrigger repository, sets `acceptanceReportVersion = 2` and fails any other value. Two readers
check no version. The Stop hook decides from the seven acceptance counts or the quality-gates
`verdict` alone. Pre-push reads only `verdict`, `head`, and `timestamp`.

**A push to `main` is already published.** ADR 0003 records that every consumer follows the default
branch. A producer that writes version 3 reaches consumers before a reader in another repository
can follow it.

**The readers do not all update together.** Outrigger is a separate repository. The portable Stop
hook is a copy installed into each project. So some readers lag any TADW push.

**Version 2 carries no evidence to check.** A version 2 report holds no invocation ID and no
evidence records. A reader cannot validate those facts, and a writer cannot reconstruct them
afterward.

## Options Considered

### Option A: Readers first, then a strict cutover with no automatic downgrade

A preparation release teaches every reader both versions, with an automatic-success minimum of 2.
Producers then gain an explicit version 3 option. A strict release changes the producer defaults
and raises the minimum to 3 together.

- **Pros:** No reader meets a version it cannot read. The installer and Outrigger can confirm the
  readers before the cutover. A rollback cannot turn old evidence into a new success.
- **Cons:** Three releases instead of one. Readers carry two code paths until the strict release.

### Option B: One release that switches producers and readers together

- **Pros:** One release, and no period with two versions.
- **Cons:** It breaks every reader not in that push. Outrigger refuses version 3, so every TADW
  phase records ERROR until its companion ships. An installed Stop hook copy reads no version, so
  it labels a version 3 report from its counts alone and ignores any HANDOFF gate.

### Option C: Stay at version 2 and add optional fields

The verification-loop plan took this path for `gates_handoff`.

- **Pros:** No version change. Every current reader ignores a field it does not know, so nothing
  fails to parse.
- **Cons:** Ignoring a field is the danger. An installed Stop hook reads the seven counts by name,
  so it would label a report whose `gates_handoff` is 1 as accepted. The acceptance loader refuses
  the new HANDOFF status, so two readers would decide one file differently. The version number is
  the one signal that tells an old loader or Outrigger to stop. It does not stop an installed Stop
  hook copy, which never reads the version. Only installing the new hook before a writer emits
  HANDOFF protects that reader.

### Option D: Readers first, but a rollback restores version 2 success

- **Pros:** A producer rollback keeps the autonomous loop moving.
- **Cons:** A version 2 report would again earn success after the strict release. That silently
  restores the evidence-free path that version 3 exists to close.

## Decision

**Option A. Readers accept version 3 before producers write it, and no rollback restores version
2 success.**

Option B lost on ADR 0003, because a push reaches readers that cannot follow it. Option C lost because
an old reader would decide on fields it cannot read. Option D lost on the silent downgrade.

These rules follow from the decision, and other components obey them:

1. **The preparation release reads versions 2 and 3.** Its automatic-success minimum is 2. A
   version 2 report keeps its existing behavior in every reader.
2. **The strict release sets minimum version 3** in the Stop hook, acceptance reuse, and
   Outrigger's TADW report mode. The producer defaults change to version 3 in the same release.
   The installer's `--check` and Outrigger confirm the installed readers first.
3. **The consumer owns the minimum.** A caller may raise it and never lower it. No field in a
   report can lower it.
4. **Legacy manual repair stays.** After the strict release, both reconcile loaders still read
   version 2, so a person can repair from an old report. Repair never records success, and a fresh
   independent grade follows.
5. **Rollback keeps the strict readers.** A producer reverted to version 2 pauses automatic
   success until a version 3 producer returns and the checks run again. No reader converts a
   version 2 report into version 3.
6. **The UI handoff fields join version 3.** `gates_handoff` and the HANDOFF gate status ship with
   the coordinated transition. No separate version 2 UI release ships.

### The amendment to ADR 0011

ADR 0011 says "`version: 2` marks the shape, and a loader refuses any other version with
`report-unreadable`." This record replaces that sentence. A loader reads versions 2 and 3. It
validates a version 3 report with the validator of its own report kind. It refuses every other
version with `report-unreadable`. A version 3 report that fails its validator is also
`report-unreadable`.

ADR 0011's rule 1 has one existing exception, which this record now states. The QA loader accepts a
report with `dirty: true` when its `head` is an ancestor of `HEAD` and every moved path is in
`changed_files`. That exception serves repair alone. Neither path membership nor a reconcile result
can establish automatic success. The acceptance loader still requires `head` to equal `HEAD`.

Everything else in ADR 0011 stands. Findings travel in the report file. The fixer never writes a
report and never grades its own fix. A check never calls its fixer. Each new script receives its
inputs and runs neither `git` nor `bd`. The two loaders stay separate, one per report kind.

## Consequences

**Easier:**

- Each reader can be released and tested alone, against the fixtures that `tadw-oaxd` publishes.
- A report proves which invocation produced it and what evidence supports it.
- A rollback has one predictable effect: automatic success pauses, and nothing passes in silence.

**Harder:**

- **Readers carry two versions until the strict release.** Each reader keeps its version 2 path
  beside the version 3 path, and `tadw-31au` decides when the strict release ships.
- **The strict release waits on Outrigger.** Its companion reader must exist before the producer
  defaults change, which ties a TADW release to another repository.
- **A rolled-back producer stops the autonomous loop.** Outrigger records ERROR on every TADW phase
  until a version 3 producer returns. That cost is the point of rule 5.
