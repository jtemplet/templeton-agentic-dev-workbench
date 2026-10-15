# Validation report contract

This contract fixes version 3 of the two validation reports, `quality-gates-report.json` and
`acceptance-report.json`. It names every field, the evidence each result must cite, and the
decision each reader makes from a report. It also fixes how version 3 replaces version 2, and what
a rollback does. The writers, the Stop hook, both reconcile loaders, the pre-push hook, acceptance
reuse, and Outrigger implement from this one document.
[ADR 0013](adr/0013-version-3-reports-reach-readers-before-producers.md) records why readers change
first. The validation reports plan, reviewed at commit `a31e94a`, chose the design.

## Terms

- **Report kind.** `quality-gates` or `acceptance`. Each kind has one writer and one validator.
  No loader reads both kinds, as ADR 0011 settled.
- **Invocation.** One run of `/tadw:quality-gates` or `/tadw:verify-acceptance`. It starts when
  its expected inputs are fixed. It ends when its consumer has read the report and finished the
  claim.
- **Expected inputs.** The checks, and for acceptance the criteria, that an invocation fixes before
  it runs or grades anything.
- **Evidence record.** One measured fact that a result cites: a process run, an inspection, or a
  result in another report.
- **Automatic consumer.** A reader that records success with no person deciding: the Stop hook,
  acceptance reuse, and Outrigger. The reconcile loaders and pre-push never record success.
- **Minimum version.** The lowest report version that an automatic consumer accepts as success.
  The consumer owns this number. No field in a report can lower it.
- **Current.** A valid report is current for a consumer when five things hold. Its `run_id` equals
  the ID the consumer kept outside the report. Its `expected` equals the copy in that invocation's
  descriptor. Its `head` equals `HEAD`. Its `dirty` is `false`. Every artifact it cites exists and
  matches its recorded digest.

## Where the files live

| Path | Holds | Written by |
|---|---|---|
| `<git-dir>/quality-gates-report.json` | The latest completed quality-gates report | The quality-gates writer |
| `<git-dir>/acceptance-report.json` | The latest completed acceptance report | The acceptance writer |
| `<git-dir>/validation-runs/<run_id>/invocation.json` | The invocation descriptor | The invocation helper, `tadw-0slj` |
| `<git-dir>/validation-runs/<run_id>/report.json` | A copy of the completed report for that invocation | The writer, before it replaces the latest report |
| `<git-dir>/validation-runs/<run_id>/<evidence-id>.log` | The captured output of one command | The capture adapter, `tadw-w5wp` |

`<git-dir>` is the output of `git rev-parse --path-format=absolute --git-dir`. So each linked
worktree reads and writes its own files. The caller passes that path to every writer and validator.
No writer, validator, or helper runs `git` or `bd`, by rule 4 of ADR 0011.

**The writer publishes in a fixed order.** It validates the whole report first. Then it writes
`report.json` into the run directory. Then it atomically replaces the latest report. A refused
write changes neither file. The run directory copy exists so that a citation still resolves after a
later invocation replaces the latest report.

**Evidence stays while a latest report cites it.** This release deletes no evidence automatically.
An explicit cleanup must keep every file that either latest completed report cites. Apply the
existing secret rules before storing output or writing an excerpt.

## Version 2, the legacy format

The writers produce version 2 today. This contract freezes it: no version 2 field changes. No reader
converts a version 2 report into version 3, because the missing identity and evidence would be
invented facts. Example 5 shows a version 2 report and the decision each reader makes.

| Kind | Fields |
|---|---|
| quality-gates | `version`, `head`, `dirty`, `timestamp`, `scope`, `gate_source`, `routing`, `bead`, `base`, `changed_files`, `verdict`, `gates`, `findings` |
| acceptance | `version`, `head`, `bead`, `base`, `changed_files`, `criteria_total`, `criteria_passed`, `criteria_failed`, `criteria_unverifiable`, `gates_total`, `gates_failed`, `gates_blocked`, `criteria`, `gates` |

The version 2 writer rules stay in force at version 3:

- Every field is present, and no unexpected field is present, at every level.
- `base` and `changed_files` are both null, or both set.
- The quality-gates `verdict` equals what the Verdict Rules give for the gate statuses.
- Each acceptance count equals the tally of its rows.
- Gate names and criterion numbers are unique.
- Each evidence text keeps at most 20 lines and 2,000 characters, then a `[trimmed: <n> more lines]`
  line.
- The writer replaces the file atomically, so no reader sees half-written JSON.

## Version 3 fields

A version 3 report holds every version 2 field of its kind, plus the fields below. Every field in
these tables is required. A field that no table names is invalid.

| Field | Kind | Rule | Shown in |
|---|---|---|---|
| `version` | both | The integer `3`. A string, a float, or another integer is invalid | Examples 1, 2, 4 |
| `kind` | both | `quality-gates` or `acceptance`, matching the file the reader opened | Examples 1, 2, 4 |
| `run_id` | both | A lowercase random UUID, version 4. The reader compares it with an ID it kept itself | Examples 1, 2, 4 |
| `producer` | both | `name`, the writer's file name, and `version`, the plugin version. No decision reads it | Examples 1, 2 |
| `timestamp` | both | UTC `YYYY-MM-DDTHH:MM:SSZ`, the moment of publication. New for acceptance | Examples 1, 2 |
| `head` | both | 40 or 64 lowercase hexadecimal digits. The writer lowercases its input, `tadw-2yg` | Examples 1, 2, 4 |
| `dirty` | both | `true` when the checked tree held uncommitted work. New for acceptance | Examples 1, 2, 4, 5 |
| `bead` | both | A non-empty bead id, or null for a manual run with no bead. Null never earns a label | Examples 1, 2, 4 |
| `expected` | both | The frozen expected inputs, described below | Examples 1, 2, 3, 4 |
| `evidence` | both | The list of evidence records, described below | Examples 1, 2, 3, 4 |
| `gates[].evidence_ids` | both | The ids of the records that support this gate result | Examples 1, 2, 3, 4 |
| `criteria[].evidence_ids` | acceptance | The ids of the records that support this criterion result | Examples 1, 4 |
| `gates_handoff` | acceptance | The count of HANDOFF gate rows, from `tadw-do7x` | Examples 1, 3 |
| `gates[].status` | acceptance | Gains `HANDOFF`, so it is one of PASS, FAIL, BLOCKED, SKIP, HANDOFF | Example 3 |

The other version 2 fields keep their rules. `scope`, `gate_source`, `routing`, `verdict`, and
`findings` appear only in quality-gates reports, shown in Example 2. Acceptance keeps no top-level
verdict. A reader derives the acceptance conclusion from the counts, under "Derived conclusions"
below.

### Expected inputs

The invocation descriptor holds `expected` from the moment the invocation starts. The writer copies
it into the report unchanged. An automatic consumer refuses a report whose `expected` differs from
the descriptor's copy. Grading never adds, removes, or edits an expected check or criterion.

Each `expected.checks` object holds six fields:

| Field | Rule |
|---|---|
| `name` | The gate name its result carries, such as `Tests` or `Handoff: browser-ui` |
| `applies` | `false` when the scope rules already show that the check has nothing to examine |
| `reason` | Non-empty text when `applies` is `false`, and null otherwise |
| `evidence_kind` | `execution` when a command decides the result, and `observation` when an inspection decides it |
| `pass_exit_codes` | For `execution`, the exit codes that the success predicate of the gate accepts, usually `[0]`. Null for `observation` |
| `ui` | Null, except for a required UI check. Then it holds `surface`, the `journeys` with the fingerprint `journeys.py` gave each, and the `uncovered_files` |

An acceptance report also holds `expected.criteria`. A quality-gates `expected` has no `criteria`
key. Each criterion object holds three fields:

| Field | Rule |
|---|---|
| `number` | The number the bead gives the criterion |
| `text` | The authoritative text, verbatim |
| `source` | `acceptance_criteria` for the native field (ADR 0001), `notes` for the Done when block, or `injected` for a description the caller supplied |

Results must match the expected inputs exactly:

1. Each expected check has exactly one gate result with the same `name`, in the same order. A
   missing, duplicate, or unexpected result is invalid.
2. Each expected criterion has exactly one criterion result with the same `number` and `text`, in
   the same order. A missing, duplicate, edited, or unexpected criterion is invalid.
3. A check with `applies: false` has the status SKIP and no evidence.
4. If the acceptance input cannot be split into clear criteria, the expected list holds one
   criterion with the whole text. The run grades it UNVERIFIABLE, so the report is INCONCLUSIVE.
5. An empty `expected.criteria` list is valid, and it never earns ACCEPTED.

### Evidence records

Every record holds an `id`, unique within the report, and a `kind`: `execution`, `observation`, or
`citation`. Each `evidence_ids` entry must name a record in the same report.

An `execution` record holds what the process did:

| Field | Rule |
|---|---|
| `command` | The command as it ran |
| `cwd` | The working directory relative to the repository root, `.` for the root |
| `state` | `finished`, `timed_out`, `interrupted`, or `not_run`. The executor's `passed` and `failed` both map to `finished` |
| `exit_code` | An integer when `state` is `finished`, and null otherwise |
| `duration_ms` | A non-negative integer, or null when `state` is `not_run` |
| `output` | Null when `state` is `not_run`. Otherwise `path` relative to the run directory, `sha256`, `bytes`, a capped `excerpt`, and `omitted_lines` |
| `inputs` | `digest`, a SHA-256 over the checked file contents, the command, the tool identity, and the declared environment. `stable`, which is `false` when any of them changed or could not be read before publication |

The capture adapter fills these fields from `skills/ship/scripts/run_checks.py`. Saved-result reuse
in that executor stays off for capture in this release. `stable` is measured on every run, the
first run included.

An `observation` record holds what an inspection read:

| Field | Rule |
|---|---|
| `subject` | `code`, `journey`, or `artifact` |
| `ref` | A `path:line` for code, a journey name for a journey, or a short description for an artifact |
| `revision` | The lowercase commit that the inspection read |
| `artifact` | Null for code. Otherwise `root`, which is `git-dir` or `repo`, the `path` under that root, and the file's `sha256` |
| `fingerprint` | For a journey, the fingerprint its saved result carries. Null otherwise |
| `outcome` | For a journey, `VERIFY_PASS`, `VERIFY_FAIL`, `VERIFY_STALE`, or `VERIFY_BLOCKED`. Null otherwise |

A `citation` record lets acceptance reuse a quality-gates result, the work of `tadw-v6k`:

| Field | Rule |
|---|---|
| `report_kind` | `quality-gates` |
| `run_id` | The invocation whose `report.json` the citation names |
| `evidence_id` | The execution record inside that report |
| `report_sha256` | The SHA-256 of that `report.json` |
| `inputs_digest` | The digest the citing run measured for the same check |

A citation counts as execution evidence only when six things hold at consumption. The cited
`report.json` exists. It matches `report_sha256`. It is a valid version 3 report. It records
`dirty: false`. It holds `evidence_id`. That record's `inputs.digest` equals `inputs_digest`.
Copying a PASS string from an earlier report is never a citation.

### What a result must cite

A gate result for an `execution` check cites records by its status:

| Status | Evidence the result must cite |
|---|---|
| PASS | At least one record. Every cited record is `finished`, has an exit code in `pass_exit_codes`, and has `stable` inputs |
| WARN | Quality-gates only. At least one `finished` record with `stable` inputs |
| FAIL | At least one `finished` record. Unstable inputs do not change a measured failure |
| BLOCKED | At least one record that is `timed_out`, `interrupted`, or `not_run`, or that finished with exit 127 |
| HANDOFF | Nothing required. A check that would pass or warn with unstable inputs is HANDOFF |
| SKIP | No record. `evidence_ids` is empty |

A gate result for an `observation` check follows the UI precedence below when `ui` is set. Without
`ui`, PASS, WARN, and FAIL each cite at least one observation whose `revision` equals `head`.

A criterion result cites records by its verdict:

| Verdict | Evidence the result must cite |
|---|---|
| PASS | At least one record. An execution record is `finished` with `stable` inputs. A code observation has `revision` equal to `head` |
| FAIL | At least one record |
| UNVERIFIABLE | Nothing required |

A criterion's command can expect a nonzero exit, so the exit code alone never grades a criterion.
Judgment still decides whether the evidence proves the criterion. A test named after the criterion
is the strongest evidence. A `path:line` at the checked revision is enough for a structural
criterion, and no command has to run only to fill the report.

### UI precedence

A required UI check takes its status from the first rule that matches. A journey result is current
only when its `fingerprint` equals the fingerprint in `expected` for that journey. The UI status
counts with every other gate and criterion.

| Required UI evidence | UI gate status | Acceptance consequence |
|---|---|---|
| Any current `VERIFY_FAIL`, even when another journey is unfinished | FAIL | NOT ACCEPTED |
| No current failure, and at least one missing, stale, blocked, or uncovered journey | HANDOFF | INCONCLUSIVE, unless another criterion or gate fails |
| Every required journey has a current `VERIFY_PASS`, and no changed file is uncovered | PASS | ACCEPTED only when every other requirement passes |

An unavailable mobile verifier leaves its journeys missing, so the check is HANDOFF. Required UI
work is never SKIP. Example 3 shows the HANDOFF case.

### Derived conclusions

The quality-gates `verdict` follows the version 2 Verdict Rules, in order. FAIL when any gate is
FAIL or BLOCKED. INCOMPLETE when any gate is HANDOFF. NO GATES RAN when no gate is PASS, WARN, or
FAIL. PASS otherwise. The writer refuses a `verdict` that differs from this result.

An acceptance reader derives its conclusion from the counts, in order:

1. **NOT ACCEPTED** when `criteria_failed`, `gates_failed`, or `gates_blocked` is above zero.
2. **INCONCLUSIVE** when `criteria_unverifiable` or `gates_handoff` is above zero, or when
   `criteria_total` or `gates_total` is zero.
3. **ACCEPTED** otherwise. Every criterion is PASS, and every gate is PASS or SKIP.

An all-SKIP gate list therefore still allows ACCEPTED, as the acceptance SKIP rule says today.

## Invocation identity

These rules let a consumer prove that a report belongs to the attempt it started. `tadw-0slj`
builds the helper, and `tadw-32s1` carries the ID through the Stop marker.

1. **Every invocation gets a new random UUID before any grading.** The caller keeps the ID outside
   the transcript. A consumer never reads its expected ID from the report it checks.
2. **Outrigger creates the ID before each cold Claude attempt.** It passes `--run-id <id>` to the
   TADW skill and to its own verifier.
3. **A direct invocation gets its ID from the Stop hook, or from the helper when no hook runs.** A
   bead-free run records `bead: null` and needs no pending label marker.
4. **The descriptor holds the fixed facts.** `invocation.json` holds `run_id`, `kind`, `bead`, the
   starting `head`, the consumer `mode`, and `expected`. The skill passes the descriptor path to the
   writer with `--invocation`. A direct writer call must pass one to request version 3.
5. **One git directory allows one active invocation per report kind.** The helper claims it
   atomically. A competing invocation stops before grading. Quality-gates and acceptance claim
   separately, and another worktree has its own git directory. Preparing the same ID again is
   idempotent and cannot change the fixed inputs. So a hook that fires twice for one run, as the
   label hook does for the Skill call and then the agent start, adopts the ID it already created.
6. **A retry gets a new ID.** That holds after a failure, an interruption, or a new cold call, even
   at the same `HEAD`. A report from an earlier attempt stays readable and never satisfies the new
   attempt.
7. **An interrupted invocation is abandoned explicitly before a replacement claims its kind.** The
   caller that owns the claim abandons it. The helper refuses to abandon another caller's live
   claim.
8. **The writer checks the active claim before publication.** The claim stays active until the
   consumer has read the report, so no replacement can publish in between.
9. **The consumer finishes the claim after it reads the report.** The Stop hook retires its marker
   and finishes the claim once it consumes the matching report. A caller with no marker, a
   bead-free direct run included, finishes the claim through the helper. An unfinished claim
   stops the next invocation of that kind until its owner finishes or abandons it.

## Consumer decisions

A reader first sorts a report into one of four classes. A **valid success** passes validation, is
current, and derives PASS or ACCEPTED. A **valid failure** derives FAIL or NOT ACCEPTED. A **valid
incomplete** derives INCOMPLETE, NO GATES RAN, or INCONCLUSIVE. **Not usable** covers a missing
file, an invalid report, a report that is not current, and a version below the consumer's minimum.

Validity never implies success. A valid report can describe failed checks, and that differs from a
report that fails validation.

"Current", as defined under Terms, binds the automatic consumers. The reconcile loaders keep their
own freshness rule instead: `head` equals `HEAD`, or the QA dirty-report exception holds. They do
not compare `run_id`, and no minimum version applies to them. Pre-push keeps its own stale-head
warning.

| Consumer | Valid success | Valid failure | Valid incomplete | Not usable |
|---|---|---|---|---|
| Stop hook | Apply the label for the matching bead and run only | No label | No label | No label, and log the reason |
| Reconcile loaders | Exit 3, nothing to fix | Select the in-scope FAIL findings by the existing rules | `needs-human-check`, or exit 3 for NO GATES RAN, as today | The existing reason order: `report-missing`, `report-unreadable`, `report-stale`, `bead-mismatch` |
| Pre-push | The existing push policy | Refuse the push on a recorded FAIL | Allow | Warn and allow, by ADR 0004; a recorded FAIL still refuses |
| Acceptance reuse | Cite the matching evidence | Carry the failure into acceptance | Carry the result into acceptance | Run the check again, or record it as incomplete |
| Outrigger | Advance after its own independent check | Follow its repair or human-decision route | Follow its human-decision route | Record ERROR, and apply its retry limit |

**Pre-push keeps its current refusal exactly.** It refuses when the file parses as JSON and
`verdict` reads FAIL, whatever else validation finds. Validation can add a warning. It never adds a
refusal and never removes one.

**The reconcile loaders keep their machine lines and reason order.** A version 3 report that fails
its validator is `report-unreadable`. A loader never writes a report and never certifies a fix, by
rule 2 of ADR 0011.

**Outrigger enables each check by configuration, never by report contents.** `acceptance_gate=tadw`
selects acceptance enforcement. The proposed key `qa_report_contract=tadw` selects quality-gates
enforcement at the QA outcome checkpoint. Other QA tools and the inline acceptance mode keep their
own contracts.

## Version matrix

A release is in one of two reader modes. The preparation release reads versions 2 and 3, with
minimum version 2. The strict release sets minimum version 3 in the automatic consumers.

| Consumer | Preparation, version 2 | Preparation, version 3 | Strict, version 2 | Strict, version 3 |
|---|---|---|---|---|
| Stop hook | The existing labeling rules | Validate, then require the matching run and bead | No success label; log that a fresh version 3 run is needed | Validate, then require the matching run and bead |
| Acceptance reuse | The existing reuse rule | Reuse only matching validated evidence | Run again, or record incomplete | Reuse only matching validated evidence |
| Outrigger, TADW report mode | The existing acceptance check; the QA check is built and off | Run both checks in compatibility fixtures | Refuse automatic phase success | Check identity, evidence, and conclusion before advancing |
| Reconcile loaders | The existing repair rules | Validate, then select findings | Legacy manual repair only | Validate, then select findings |
| Pre-push | The existing warning and refusal rules | Validate; keep the warning and refusal rules | Warn on version 2 success evidence; a recorded FAIL still refuses | Validate; keep the warning and refusal rules |

**Legacy manual repair** means a reconcile skill selects findings from a version 2 report and
commits fixes. Repair never records success, so a fresh independent grade must follow. The QA
loader keeps its dirty-report exception for repair alone. That exception accepts a report with
`dirty: true` when its `head` is an ancestor of `HEAD` and every moved path is in `changed_files`.
The acceptance loader still requires `head` to equal `HEAD`.

**The order of releases is fixed.** First, readers that accept both versions ship, for both report
kinds and the Outrigger companion. Next, producers gain an explicit version 3 option, and version 2
stays their default. Last, the strict release (`tadw-31au`) changes the producer defaults and the
consumer minimums together. It ships only after the installer's `--check` confirms the strict
readers and their helpers, and after Outrigger confirms the installed producer and readers.

**A caller may raise the minimum version, never lower it.** The strict installed readers default to
3.

## Rollback

A rollback keeps the strict readers and minimum version 3:

- A producer reverted to version 2 pauses automatic success. The Stop hook, acceptance reuse, and
  Outrigger refuse its reports until a version 3 producer returns and the checks run again.
- A reader that cannot read version 3 stops the cutover. Do not change producer defaults while one
  is installed.
- No reader turns a version 2 report back into a success, and no reader fills in version 3 fields.

## Examples

Each example is one class of report. The digests and identifiers are illustrative.

### Example 1: a valid acceptance success

The run graded both criteria PASS. Tests and lint passed, and the type check did not apply. The
derived conclusion is ACCEPTED.

```json
{
  "version": 3,
  "kind": "acceptance",
  "run_id": "3b5d0c1e-7a24-4f69-9e8d-2c41a6b07f13",
  "producer": {"name": "write_acceptance_report.py", "version": "4.8.4"},
  "timestamp": "2026-10-15T18:04:11Z",
  "head": "4c1e9a7b2d5f8e0a3b6c9d2e5f8a1b4c7d0e3f6a",
  "dirty": false,
  "bead": "tadw-abc1",
  "base": {"ref": "origin/main", "sha": "9165ff5a0b1c2d3e4f5061728394a5b6c7d8e9f0"},
  "changed_files": ["tools/parse.py", "tools/test_parse.py"],
  "expected": {
    "checks": [
      {"name": "Tests", "applies": true, "reason": null, "evidence_kind": "execution", "pass_exit_codes": [0], "ui": null},
      {"name": "Lint and Format", "applies": true, "reason": null, "evidence_kind": "execution", "pass_exit_codes": [0], "ui": null},
      {"name": "Type Checking", "applies": false, "reason": "no type checker is configured", "evidence_kind": "execution", "pass_exit_codes": [0], "ui": null}
    ],
    "criteria": [
      {"number": 1, "text": "Given an empty file, the parser exits 2.", "source": "acceptance_criteria"},
      {"number": 2, "text": "The line ceiling stays at 35.", "source": "acceptance_criteria"}
    ]
  },
  "criteria_total": 2,
  "criteria_passed": 2,
  "criteria_failed": 0,
  "criteria_unverifiable": 0,
  "gates_total": 3,
  "gates_failed": 0,
  "gates_blocked": 0,
  "gates_handoff": 0,
  "criteria": [
    {"number": 1, "text": "Given an empty file, the parser exits 2.", "verdict": "PASS", "evidence": "test_empty_file_exits_2 passed", "command": "python3 tools/test_parse.py", "evidence_ids": ["e1"]},
    {"number": 2, "text": "The line ceiling stays at 35.", "verdict": "PASS", "evidence": "tools/parse.py:12 sets LINE_CEILING = 35", "command": null, "evidence_ids": ["e3"]}
  ],
  "gates": [
    {"name": "Tests", "status": "PASS", "command": "python3 tools/test_parse.py", "detail": "14 passed, 0 failed", "evidence_ids": ["e1"]},
    {"name": "Lint and Format", "status": "PASS", "command": "ruff check tools", "detail": "0 errors, 0 warnings", "evidence_ids": ["e2"]},
    {"name": "Type Checking", "status": "SKIP", "command": null, "detail": "no type checker is configured", "evidence_ids": []}
  ],
  "evidence": [
    {"id": "e1", "kind": "execution", "command": "python3 tools/test_parse.py", "cwd": ".", "state": "finished", "exit_code": 0, "duration_ms": 1840,
     "output": {"path": "e1.log", "sha256": "1762cfca52342586405e2cb05a2a1b89007aa153b03f4fae8b18502294995406", "bytes": 912, "excerpt": "Ran 14 tests in 1.7s\nOK", "omitted_lines": 0},
     "inputs": {"digest": "94a40f7283c5ea3151051ddfab9cab3fdd84847ec34935e26c7537e06cc42ea7", "stable": true}},
    {"id": "e2", "kind": "execution", "command": "ruff check tools", "cwd": ".", "state": "finished", "exit_code": 0, "duration_ms": 210,
     "output": {"path": "e2.log", "sha256": "729132c933b2bf10da75d6f2885a6a01a45d459476e04080202c24569ce892ce", "bytes": 19, "excerpt": "All checks passed!", "omitted_lines": 0},
     "inputs": {"digest": "ecf1e255b687f87239234abae5aa6348e55d1a759f758d669d6bc0b41a16608e", "stable": true}},
    {"id": "e3", "kind": "observation", "subject": "code", "ref": "tools/parse.py:12", "revision": "4c1e9a7b2d5f8e0a3b6c9d2e5f8a1b4c7d0e3f6a", "artifact": null, "fingerprint": null, "outcome": null}
  ]
}
```

**1b, the same gate through a citation.** Example 1 could reuse the Lint result of a passing,
clean quality-gates run at the same `head` rather than run lint again. The gate then cites `e5`,
and `e2` is not run. The citation holds because the citing run measured the same inputs digest that
the cited run's `e2` recorded, the digest Example 1's own `e2` shows. Example 2 cannot serve: it
checked the commit before the parser fix, so its Lint inputs digest differs.

```json
{
  "gates": [
    {"name": "Lint and Format", "status": "PASS", "command": "ruff check tools", "detail": "0 errors, 0 warnings, cited", "evidence_ids": ["e5"]}
  ],
  "evidence": [
    {"id": "e5", "kind": "citation", "report_kind": "quality-gates", "run_id": "5e9b3f27-0c6d-4a81-b2f4-9d3e7a1c6b05", "evidence_id": "e2",
     "report_sha256": "4a7480fa89f6ea9eaf2444615abbb1d196b67b5b91a00e79e243b551f4805509",
     "inputs_digest": "ecf1e255b687f87239234abae5aa6348e55d1a759f758d669d6bc0b41a16608e"}
  ]
}
```

### Example 2: a valid quality-gates failure

The run checked the commit before the parser fix, so its `head` differs from Example 1's. The test
command finished with exit 1, so Tests is FAIL and the verdict is FAIL. A gate with an unexpected
exit code cannot be PASS, because exit 1 is not in `pass_exit_codes`.

```json
{
  "version": 3,
  "kind": "quality-gates",
  "run_id": "c0a4e8d2-91b7-4f3e-8a65-7d2b0e9f4c18",
  "producer": {"name": "write_report_json.py", "version": "4.8.4"},
  "timestamp": "2026-10-15T17:52:40Z",
  "head": "7d2f0b9c4e1a8d3f6b5c2e9a0d7f4b1c8e3a6d5f",
  "dirty": false,
  "scope": "changed",
  "gate_source": "AGENTS.md",
  "routing": {"library": {"method": "coverage", "owner": null, "files": 2, "endpoints": 0}},
  "bead": "tadw-abc1",
  "base": {"ref": "origin/main", "sha": "9165ff5a0b1c2d3e4f5061728394a5b6c7d8e9f0"},
  "changed_files": ["tools/parse.py", "tools/test_parse.py"],
  "expected": {
    "checks": [
      {"name": "Tests", "applies": true, "reason": null, "evidence_kind": "execution", "pass_exit_codes": [0], "ui": null},
      {"name": "Lint", "applies": true, "reason": null, "evidence_kind": "execution", "pass_exit_codes": [0], "ui": null}
    ]
  },
  "verdict": "FAIL",
  "gates": [
    {"name": "Tests", "status": "FAIL", "command": "python3 tools/test_parse.py", "detail": "13 passed, 1 failed", "evidence_ids": ["e1"]},
    {"name": "Lint", "status": "PASS", "command": "ruff check tools", "detail": "0 errors, 0 warnings", "evidence_ids": ["e2"]}
  ],
  "findings": [
    {"gate": "Tests", "file": "tools/test_parse.py", "line": 31, "problem": "test_empty_file_exits_2 fails: the parser exits 0", "evidence": "AssertionError: 0 != 2"}
  ],
  "evidence": [
    {"id": "e1", "kind": "execution", "command": "python3 tools/test_parse.py", "cwd": ".", "state": "finished", "exit_code": 1, "duration_ms": 1902,
     "output": {"path": "e1.log", "sha256": "b3644e3dd0f870c210015ef8113cd99a19e1da1dad1ab1ef16f84f31369dd0e5", "bytes": 1430, "excerpt": "FAIL: test_empty_file_exits_2\nAssertionError: 0 != 2", "omitted_lines": 18},
     "inputs": {"digest": "1ef7af76f79b54cef25e04428aa3698f5cf058919206ff8a50316c36656cda9b", "stable": true}},
    {"id": "e2", "kind": "execution", "command": "ruff check tools", "cwd": ".", "state": "finished", "exit_code": 0, "duration_ms": 198,
     "output": {"path": "e2.log", "sha256": "e1e45b690c76463062cbf184a408c1e8947b9cbdf21deb72947c385ad0fa470e", "bytes": 19, "excerpt": "All checks passed!", "omitted_lines": 0},
     "inputs": {"digest": "a67ce6ac4294d720326907050dae3622da4facff79ef68fcd31ee284ef13c831", "stable": true}}
  ]
}
```

If `ruff` were not installed, `e2` would hold `"state": "not_run"`, with `exit_code`,
`duration_ms`, and `output` all null. Lint would then be BLOCKED, and the verdict would stay FAIL.

### Example 3: valid incomplete reports

**3a, acceptance with an unfinished UI journey.** Example 1 gains one required browser check. The
`deals` journey has a current `VERIFY_PASS`. The `settings` journey has no result. No current
failure exists, so the gate is HANDOFF and the conclusion is INCONCLUSIVE. Only the changed fields
are shown.

```json
{
  "expected": {
    "checks": [
      {"name": "Handoff: browser-ui", "applies": true, "reason": null, "evidence_kind": "observation", "pass_exit_codes": null,
       "ui": {"surface": "browser-ui", "journeys": [{"name": "deals", "fingerprint": "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2"}, {"name": "settings", "fingerprint": "fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9"}], "uncovered_files": []}}
    ]
  },
  "gates_total": 4,
  "gates_handoff": 1,
  "gates": [
    {"name": "Handoff: browser-ui", "status": "HANDOFF", "command": null, "detail": "deals passed; settings has no current result", "evidence_ids": ["e4"]}
  ],
  "evidence": [
    {"id": "e4", "kind": "observation", "subject": "journey", "ref": "deals", "revision": "4c1e9a7b2d5f8e0a3b6c9d2e5f8a1b4c7d0e3f6a",
     "artifact": {"root": "git-dir", "path": "verify-app-report.json", "sha256": "8e2a1e635a22f68357c556632fadee3bd8412da58fb0bf9860e7325479cfcd3e"},
     "fingerprint": "c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2", "outcome": "VERIFY_PASS"}
  ]
}
```

If `e4` instead carried `VERIFY_FAIL` with the current fingerprint, the gate would be FAIL and the
conclusion NOT ACCEPTED, even with `settings` still unfinished.

**3b, quality-gates with an input that changed during the run.** Take Example 2 after the parser
fix, at Example 1's `head`, so Tests is PASS. The Lint command finished with exit 0, but a checked
file changed before publication. The record keeps the measured exit code, the gate becomes HANDOFF,
and the verdict becomes INCOMPLETE. The rule applies on a first run, with no saved result involved.
Only the changed fields are shown.

```json
{
  "head": "4c1e9a7b2d5f8e0a3b6c9d2e5f8a1b4c7d0e3f6a",
  "verdict": "INCOMPLETE",
  "gates": [
    {"name": "Lint", "status": "HANDOFF", "command": "ruff check tools", "detail": "inputs changed during the check; run it again", "evidence_ids": ["e2"]}
  ],
  "evidence": [
    {"id": "e2", "kind": "execution", "state": "finished", "exit_code": 0,
     "inputs": {"digest": "e77b46b6a4004738c531eb3b7bb1fb667a362ced8899500509e0e1ae1ed730e7", "stable": false}}
  ]
}
```

### Example 4: invalid and not-current reports

Each line changes one example. The writer refuses to publish the invalid ones. A reader that finds
any of them on disk treats it as not usable.

| Change | Class | Rule it breaks |
|---|---|---|
| Example 1 without criterion 2 | Invalid | An expected criterion has no result |
| Example 1 with criterion 1 twice | Invalid | A criterion number repeats |
| Example 1 with criterion 2's text edited | Invalid | The text differs from `expected.criteria` |
| Example 2 with a third gate, `Security`, not in `expected` | Invalid | An unexpected result |
| Example 2 without the Lint result | Invalid | An expected check has no result |
| Example 1 with `criteria_passed` set to 1 | Invalid | A count disagrees with its rows |
| Example 2 with `verdict` set to PASS | Invalid | The verdict differs from the Verdict Rules |
| Example 2 with Tests PASS and `e1` still exit 1 | Invalid | The exit code is not in `pass_exit_codes` |
| Example 1 with `e1` in state `interrupted` | Invalid | A PASS cites an interrupted command |
| Example 1 with Type Checking PASS | Invalid | A check with `applies: false` must be SKIP |
| Example 1 with `"version": "3"` | Invalid | The version is a string |
| Example 1 read from `quality-gates-report.json` | Invalid | `kind` does not match the file |
| Example 1 with an uppercase digit in `head` | Invalid | `head` is not lowercase |
| Example 1 with `bead` set to `""` | Invalid | `bead` is empty rather than null |
| Example 1 with an `evidence_ids` entry `e9` | Invalid | No record has that id |
| Example 1 checked with a different retained `run_id` | Not current | The report belongs to another invocation, even at the same `HEAD` |
| Example 1 without Type Checking in `expected`, `gates`, and the counts | Not current | `expected` differs from the descriptor's copy |
| Example 1 after a new commit | Not current | `head` is not `HEAD` |
| Example 1 with `dirty: true` | Not current | Automatic success needs committed work |
| Example 3a after `verify-app-report.json` changes | Not current | The artifact no longer matches its digest |
| Example 1b after the cited `report.json` changes | Not current | The citation no longer matches `report_sha256` |

### Example 5: legacy version 2 reports

**5a, a version 2 acceptance success.** It holds no `run_id`, `expected`, or `evidence`.

```json
{
  "version": 2,
  "head": "4c1e9a7b2d5f8e0a3b6c9d2e5f8a1b4c7d0e3f6a",
  "bead": "tadw-abc1",
  "base": {"ref": "origin/main", "sha": "9165ff5a0b1c2d3e4f5061728394a5b6c7d8e9f0"},
  "changed_files": ["tools/parse.py", "tools/test_parse.py"],
  "criteria_total": 1, "criteria_passed": 1, "criteria_failed": 0, "criteria_unverifiable": 0,
  "gates_total": 1, "gates_failed": 0, "gates_blocked": 0,
  "criteria": [{"number": 1, "text": "Given an empty file, the parser exits 2.", "verdict": "PASS", "evidence": "test passed", "command": "python3 tools/test_parse.py"}],
  "gates": [{"name": "Tests", "status": "PASS", "command": "python3 tools/test_parse.py", "detail": "14 passed, 0 failed"}]
}
```

**5b, a version 2 quality-gates failure graded on a dirty tree.** It has `dirty: true` and a FAIL
verdict. After grading, the person committed exactly the files in `changed_files`, so its `head` is
an ancestor of `HEAD`. Only the QA loader's legacy exception reads it, and only for repair.

### Decisions for each example

| Example | Stop hook | Reconcile loaders | Pre-push | Acceptance reuse | Outrigger |
|---|---|---|---|---|---|
| 1, valid success | Apply `accepted` | Exit 3, nothing to fix | Not applicable | Not applicable | Advance |
| 1b, valid citation | Apply `accepted` | Exit 3, nothing to fix | Not applicable | Cite `e2` from the cited run | Advance |
| 2, valid failure | No label | Select the Tests finding | Refuse | Carry FAIL into acceptance | Repair route |
| 3a, UI unfinished | No label | `needs-human-check` | Not applicable | Not applicable | Human-decision route |
| 3b, input changed | No label | `needs-human-check` | Allow | Run Lint again | Human-decision route |
| 4, invalid | No label, and log | `report-unreadable` | Warn and allow; refuse when `verdict` reads FAIL | Run again | ERROR |
| 4, not current | No label, and log | `report-stale` when `head` is not `HEAD`. Otherwise the loaders treat it as current, because they compare no run ID, `dirty`, `expected`, or digest | Not applicable | Run again | ERROR |
| 5a, preparation | The existing count rules apply `accepted` | Exit 3, nothing to fix | Not applicable | Not applicable | The existing version 2 check |
| 5a, strict | No label; log that a version 3 run is needed | Exit 3, nothing to fix | Not applicable | Not applicable | ERROR, no phase success |
| 5b, preparation | No label | Select findings under the dirty-report exception | Refuse | Run again | The existing QA route |
| 5b, strict | No label | Select findings for repair only | Refuse | Run again | ERROR, no phase success |

Pre-push reads only the quality-gates report, so it has no decision for an acceptance example.
Acceptance reuse reads only quality-gates results, and a dirty one is never reused.
