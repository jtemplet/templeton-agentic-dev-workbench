---
description: Auto-detecting code review that identifies languages and applies the correct review skill for each
---

Use the `code-reviewer` agent to perform a comprehensive code review.

**What it does:**

1. Identifies all changed files (git diff against main)
2. Detects the language/framework of each file
3. Loads the appropriate review skill:
   - Python -> `python-code-review`
   - Ruby/Rails -> `rails-code-review`
   - Swift/iOS -> `templeton-swift-style`
   - Terraform -> `terraform-iac-expert`
4. Produces a consolidated review report with severity, location, and fixes

**Usage:**

```text
# Review current branch changes against main
/code-review

# Review specific files
/code-review app/models/user.rb src/auth.py
```

If specific files are provided via arguments, review those files. Otherwise, review all changes on the current branch relative to main.
