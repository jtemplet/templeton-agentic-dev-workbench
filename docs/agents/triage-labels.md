# Triage Labels

The engineering skills speak in terms of five canonical triage roles. This table maps each role
to the label string used in this repo's tracker, which is bd (beads).

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill names a role, such as "apply the AFK-ready triage label", use the label string
from the right-hand column.

## Applying a label

```bash
bd update <id> --add-label ready-for-agent
bd update <id> --remove-label needs-triage
```

`--set-labels` replaces every label on the issue at once, so reach for `--add-label` and
`--remove-label` unless you mean to wipe the rest.

## `ready-for-human` is not `needs-human`

This tracker already uses a label called **`needs-human`**, and it means something else. Keep
the two apart.

| Label | Who applies it | What it means |
|---|---|---|
| `needs-human` | the `ship` skill, automatically, on any stop | A run halted part-way. A person must unblock it before anything else can proceed. |
| `ready-for-human` | triage, deliberately | The issue is fully specified. It is ready to build, but a person should build it rather than an agent. |

One is a stop signal, and the other is a routing decision. Merging them would hide a blocked
run inside the ordinary backlog.

## Other labels in this tracker

Triage labels sit alongside labels that carry different jobs, and none of them is a triage
role. They include area tags (`skills`, `tooling`, `docs`, `testing`, `evals`), lifecycle marks
written by the build pipeline (`implemented`, `reviewed`, `accepted`), plan groupings
(`plan:<name>`), and provenance (`source-bead:<id>`, `discovered:<date>`). Leave them alone
when triaging.
