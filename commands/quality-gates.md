---
description: "Run quality gates (tests, linting, type checks, docs freshness, security scan) and report pass/fail"
---

You are a quality gate runner. Execute each gate in sequence, skip gates that don't apply, and produce a consolidated report.

## Gate 1: Tests

Auto-detect the test framework and run tests:

```bash
# Check in order, run the first one found
# pytest / python -m pytest
# bundle exec rspec
# npm test / yarn test
# go test ./...
# make test (if Makefile has a test target)
```

Record: pass/fail, test count, error count. **SKIP** if no test framework is detected.

## Gate 2: Linting

Auto-detect the linter and run it:

```bash
# ruff check . / flake8
# rubocop
# eslint . / npx eslint .
# golangci-lint run
```

Record: warning count, error count. **SKIP** if no linter is detected.

## Gate 3: Type Checking

Run type checks if applicable:

```bash
# mypy . / pyright
# tsc --noEmit
```

Record: error count. **SKIP** if no type checker applies.

## Gate 4: Documentation Freshness

Check for stale documentation:

- Look for README.md, CLAUDE.md, AGENTS.md
- Check if these files reference files, functions, or commands that no longer exist
- Check if recently changed source files have corresponding doc updates needed

Record: stale references found. **WARN** if issues, don't FAIL.

## Gate 5: Security Quick Scan

Check for common security issues:

- Committed `.env` files or files matching `*.secret*`, `*credential*`
- Hardcoded strings that look like API keys, passwords, or tokens (long hex/base64 strings in source)
- `TODO`, `FIXME`, `HACK`, `XXX` comments (count them, report as warnings)

Record: findings. **WARN** for TODOs/FIXMEs. **FAIL** for committed secrets.

## Output

Present results as:

```markdown
## Quality Gates Report

| Gate | Status | Details |
|---|---|---|
| Tests | PASS/FAIL/SKIP | X passed, Y failed |
| Linting | PASS/FAIL/WARN/SKIP | X warnings, Y errors |
| Type Checking | PASS/FAIL/SKIP | X errors |
| Doc Freshness | PASS/WARN/SKIP | X stale references |
| Security Scan | PASS/FAIL/WARN | X findings |

### Overall: PASS / FAIL

### Action Items

1. [First thing to fix, if any]
2. ...
```

**Rules:**
- A single FAIL in any gate means overall FAIL
- WARN does not cause overall FAIL but should be noted
- SKIP gates don't affect the overall result
- Run gates sequentially (tests first — if tests fail, still run remaining gates)
- Report actual command output for failures so the user can debug
