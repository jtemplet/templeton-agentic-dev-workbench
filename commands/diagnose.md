---
description: "Investigate a bug or issue thoroughly before attempting any fix — gather evidence, test hypotheses, present root cause"
argument-hint: "[bug-description-or-error-message]"
---

Use the `diagnostician` agent to investigate this issue before attempting any fix.

The agent will:

1. Reproduce the problem and gather evidence (errors, recent changes, stack traces, logs)
2. Form 2-3 specific hypotheses for the root cause
3. Test each hypothesis with targeted searches and reads
4. Present a diagnosis with confidence levels, root cause, and recommended fix

The agent has NO ability to edit or write files — it can only investigate. This is intentional: understand the problem fully before touching any code.

After the diagnosis, you can decide whether to implement the recommended fix yourself or hand it off.
