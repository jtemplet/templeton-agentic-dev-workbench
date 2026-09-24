---
name: review-python
description: Reviews Python code against PEP 8 and the Google Python Style Guide. Covers style, imports, naming, docstrings, type hints, code quality, security, performance, and maintainability. Use when reviewing, auditing, or checking the quality of Python code.
---

# Python Code Review (PEP 8 + Google Style Guide)

Perform systematic, pragmatic code reviews of Python files against PEP 8 and the Google Python Style
Guide. Lead with security and correctness, then code quality, then style. Verify before flagging.

## When to Use / When NOT to Use

Use when:

- Reviewing a Python file, diff, or PR for quality, security, performance, or style compliance.
- Auditing existing Python code against PEP 8 / PEP 257 / PEP 484 and the Google Python Style Guide.
- A user asks to check, audit, or improve Python code quality.
- Verifying docstrings, type hints, import order, or naming conventions in `.py` files.

Do NOT use when:

- The file is not Python (e.g. Ruby, Swift, JS/TS, Terraform). Dispatch to the matching review skill
  instead.
- The request is a design / architecture / object-oriented-design review. Defer to `style-python`,
  which owns the house OOD and Python writing style.
- The only findings are auto-formattable nits (line length, spacing, quote consistency) that
  `black`/`ruff format` already fixes on save. Note the formatter; do not enumerate each nit as a
  finding.
- The task is writing new Python from scratch (use `feature-development`) rather than reviewing
  existing code.

## Universal Core (injected)

The universal style core (TRUE code plus the universal principles, defined in `hooks/style-core.md`)
is injected separately into every session. Do not restate it; assume it. Design-level OOD concerns
(single-purpose units, dependency injection, tell-don't-ask, composition over inheritance,
rule-of-three abstraction) live in `style-python`, the companion writing-style skill. This skill
adds the PEP 8 / Google Style review specifics on top of that shared foundation.

## Review Principles

### Review Philosophy

"Code is read much more often than it is written." (Guido van Rossum)

A foolish consistency is the hobgoblin of little minds. Consistency within a project matters more
than rigid adherence to rules. When in doubt, prioritize in this order:

1. Consistency within one function/module (most important)
2. Consistency within the project
3. Consistency with PEP 8 / Google Style Guide

Know when to be inconsistent:

- When applying the guideline makes code less readable.
- To match surrounding code style (but consider refactoring).
- When code predates the guideline.
- For backwards compatibility.

### Review Specifics

Cite PEP 8, PEP 257, PEP 484, and the Google Python Style Guide by section. This skill adds only
where those sources differ or where this workbench takes a side:

- Where PEP 8 and Google differ, apply Google: 80-column lines, full package-path imports, no
  `@staticmethod`, `@property` only for cheap computation, and a function over about 40 lines is a
  prompt to consider splitting rather than a finding.
- Modern typing on 3.10+: `X | None` and built-in generics; flag implicit Optional
  (`a: str = None`). Confirm the project's Python version before flagging syntax.
- Logging takes %-style arguments, not f-strings. This is LOW to MEDIUM, never a correctness
  finding.
- Formatter-owned nits (line length, whitespace, quotes, import order) are one LOW note naming the
  formatter, not one finding each.
- Duplication is a finding only at the third occurrence; design-level OOD belongs to
  `style-python`.

### Security

#### SQL Injection

```python
# Bad - SQL injection risk!
query = f"SELECT * FROM users WHERE id = {user_id}"
query = "SELECT * FROM users WHERE id = " + user_id

# Good - Use parameterized queries
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### Input Validation

- Validate all external input.
- Use allowlists, not denylists.
- Sanitize before using in system commands.

#### Hardcoded Secrets

- Never hardcode passwords, API keys, or tokens.
- Use environment variables or secret management.
- Check for: `password = "..."`, `api_key = "..."`, etc.

#### Unsafe Functions

- Avoid: `eval()`, `exec()`, `compile()`, `__import__()`.
- Be careful with: `pickle`, `yaml.load()` (use `safe_load`).

## Anti-Patterns

The highest-signal Python review smells. For each: the bad code, why it is wrong, and the corrected
form.

### Mutable Default Argument

```python
# Bad - the default list is created once and shared across all calls
def foo(a, b=[]):
    b.append(a)
    return b
```

Why: default arguments are evaluated once at definition time. Mutating `b` leaks state between
calls, producing surprising accumulation bugs.

```python
# Corrected - sentinel default, create a fresh list per call
def foo(a, b=None):
    if b is None:
        b = []
    b.append(a)
    return b
```

### Bare `except`

```python
# Bad - also swallows SystemExit and KeyboardInterrupt
try:
    risky()
except:
    pass
```

Why: a bare `except` catches `BaseException`, masking real bugs and making the program impossible to
interrupt or exit cleanly.

```python
# Corrected - catch the specific exception you can handle
try:
    risky()
except ValueError as e:
    logger.warning('risky failed: %s', e)
```

### SQL Injection via f-string

```python
# Bad - user input interpolated straight into SQL
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)
```

Why: any value in `user_id` becomes executable SQL. This is a CRITICAL injection vulnerability.

```python
# Corrected - parameterized query, driver handles escaping
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### String Concatenation in a Loop

```python
# Bad - O(n^2): a new string is allocated every iteration
employee_table = '<table>'
for last, first in employees:
    employee_table += f'<tr><td>{last}, {first}</td></tr>'
```

Why: strings are immutable, so `+=` copies the whole accumulator each pass, giving quadratic time on
large inputs.

```python
# Corrected - accumulate in a list, join once
items = ['<table>']
for last, first in employees:
    items.append(f'<tr><td>{last}, {first}</td></tr>')
employee_table = ''.join(items)
```

### f-strings in Logging

```python
# Bad - formats the message even when the log level is disabled
logger.info(f'TensorFlow version: {tf.__version__}')
```

Why: f-strings are evaluated eagerly, defeating the logging module's lazy formatting and wasting
work for suppressed levels.

```python
# Corrected - %-style deferred formatting
logger.info('TensorFlow version: %s', tf.__version__)
```

### `== None`

```python
# Bad
if foo == None:
    ...
```

Why: `None` is a singleton; `==` invokes `__eq__` and can be overridden or give the wrong answer.
Identity is the correct check.

```python
# Corrected
if foo is None:
    ...
```

### Premature Abstraction (before the 3rd occurrence)

```python
# Bad - extracting a shared helper from only two similar call sites,
# bending both to fit a speculative interface
def render(entity, *, mode, wrap, prefix, suffix):
    ...
```

Why: two instances of similar code may be coincidental. Abstracting early couples unrelated code to
a rigid interface that grows parameters as the cases diverge.

```python
# Corrected - keep the duplication until a third occurrence reveals
# the true pattern, then extract the real shared shape
def render_user(user):
    ...

def render_order(order):
    ...
```

## Worked Examples

### Logging f-string -> lazy %-formatting

Before:

```python
import logging

logger = logging.getLogger(__name__)


def process(batch):
    logger.debug(f'processing batch {batch.id} with {len(batch.items)} items')
    for item in batch.items:
        handle(item)
```

After:

```python
import logging

logger = logging.getLogger(__name__)


def process(batch):
    logger.debug('processing batch %s with %d items', batch.id, len(batch.items))
    for item in batch.items:
        handle(item)
```

Rationale: at `DEBUG` the f-string version always builds the message string and calls `len(...)`,
even in production where `DEBUG` is usually disabled. The `%`-style call passes the arguments to the
logging machinery, which only formats them if the record is actually emitted. On a hot path this
removes wasted work and keeps the call cheap. Severity here is LOW to MEDIUM (a non-standard but
working pattern), not a correctness bug.

### SQL injection -> parameterized query

Before:

```python
def get_user(cursor, user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()
```

After:

```python
def get_user(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()
```

Rationale: the before version concatenates caller-controlled input directly into the SQL string. A
`user_id` of `0 OR 1=1` (or worse, a `DROP`/`UNION` payload) executes as SQL. The after version
sends the query and the value separately so the driver escapes the parameter, closing the injection
vector. This is a CRITICAL finding regardless of whether current tests pass, because it is a
security vulnerability, not a style choice.

## Review Workflow

1. **Read the entire file first.** Understand its purpose, structure, dependencies, and surrounding
   conventions before judging any line.
2. **Verify the context.** Confirm the Python version (e.g. 3.10+ for `X | None` syntax), project
   conventions, and whether tests pass. Do not flag modern idioms as errors.
3. **Review in priority order:**
   - Security and correctness first (injection, unsafe functions, hardcoded secrets, mutable
     defaults, bare excepts, masked exceptions).
   - Then code quality (error handling, resource management, abstraction, comprehensions, return
     consistency).
   - Then maintainability (function length, main guard, assertions).
   - Then style last (line length, whitespace, quotes, import order, naming).
4. **Confirm each issue actually exists** before flagging it. If tests pass and the code works, a
   non-standard pattern is at most MEDIUM.
5. **Produce the report** in the Output Format below, grouped by category and severity-ranked.

Apply this guidance throughout:

- **Orient with `bulk-reader`, and read what you edit yourself.** When the review spans more files
  than you want to read, dispatch `tadw:bulk-reader` to find which ones matter, then read those
  here. It reads in its own context, so the files it opens never enter yours. `bulk-reader` orients,
  and never supplies the text an edit is based on. Its answer carries no reliable line numbers, so
  an edit built on it changes the wrong line.
- **Scope.** Review the changed code, suggest incremental improvements rather than a rewrite, and
  match the project's existing conventions.
- **Context matters.** Consider project conventions. Match surrounding code style when editing.
  Balance improvement with backwards compatibility. Know when rules have valid exceptions.

Special cases:

- **Legacy code.** Focus on new/modified code. Don't require a full refactor to meet standards.
  Suggest incremental modernization.
- **Mathematical/scientific code.** Short variable names OK if they match notation (`i`, `j`, `x`,
  `y`). Reference the paper/algorithm in comments. Use `# pylint: disable=invalid-name` if needed.
- **Test files.** PEP 8-compliant names (`test_<method>_<state>`) or legacy style
  (`testMethodUnderTest_state`). Less strict docstring requirements.
- **Backwards compatibility.** Don't break compatibility just to comply with PEP 8. Consider a
  deprecation path for API changes.

## Output Format

Structure the review exactly as follows:

````markdown
### Summary

- **Overall Assessment**: Excellent/Good/Fair/Needs Improvement
- **PEP 8 Compliance**: High/Medium/Low
- **Google Style Compliance**: High/Medium/Low
- **Key Strengths**: 2-4 well-implemented aspects
- **Critical Issues**: Issues requiring immediate attention (if any)

### Detailed Findings

Group by category. For each issue:

**[Category: Style/Documentation/Quality/Security/Performance/Maintainability]**

**Issue #**: Brief title

- **Severity**: Critical/High/Medium/Low
- **Lines**: Specific line numbers
- **PEP 8/Google Reference**: Section reference (if applicable)
- **Description**: Clear explanation of the issue
- **Current Code**:

  ```python
  # Problematic code excerpt
  ```

- **Recommended Fix**:

  ```python
  # Corrected code
  ```

- **Rationale**: Why this matters (readability/safety/performance/maintainability)

### Positive Highlights

- Well-implemented patterns worth noting
- Good adherence to standards
- Exemplary practices

### Recommendations

- Priority-ordered list of improvements
- Consider quick wins vs. larger refactors
- Balance consistency with practical constraints
````

### References

- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 257 Docstring Conventions](https://peps.python.org/pep-0257/)
- [PEP 484 Type Hints](https://peps.python.org/pep-0484/)

### Enforcement Tools

Recommended:

- **pylint**: comprehensive linter
  ([Google's pylintrc](https://google.github.io/styleguide/pylintrc)).
- **pytype**: type checker (Google's tool).
- **mypy**: alternative type checker.
- **Black** or **Pyink**: auto-formatters (Google uses these).
- **flake8**: alternative linter.
- **isort**: import sorting.

Suppression:

- Use `# pylint: disable=rule-name` with an explanation.
- Use `# type: ignore` for type checking (sparingly).
- Document why the suppression is needed.

## Severity Scale

Severity for this review:

- **CRITICAL**: security vulnerability, data loss, or correctness bug (e.g. SQL injection, `eval()`
  on untrusted input, mutable-default state corruption, masked exceptions hiding failures).
- **HIGH**: a correctness or error-handling defect the tests do not exercise, or a performance
  blocker on a real path (e.g. a bare `except` swallowing errors in production, unbounded string
  concatenation on a hot path).
- **MEDIUM**: non-standard pattern that still works, unnecessary duplication (3+ instances), or
  missing tests.
- **LOW**: style and nits (line length, whitespace, quote consistency, import order) that a
  formatter handles.

**If tests pass and the code works, the maximum severity is MEDIUM (a non-standard pattern), not
HIGH or CRITICAL.**

The one exception is a genuine security vulnerability or latent correctness bug that the existing
tests simply do not exercise; those remain CRITICAL even when the suite is green.

## Quality Checklist

Before completing the review, verify:

- [ ] Read the entire file (not just the diff) for purpose, structure, and surrounding conventions.
- [ ] Read every file an edit touched, rather than relying on `bulk-reader`'s bullets for it.
- [ ] Verified each claim (Python version, framework patterns, whether tests pass) before flagging
      it.
- [ ] Reviewed security and correctness first, then quality, then maintainability, then style.
- [ ] Applied the severity scale, including the rule that passing tests cap
      non-correctness/non-security issues at MEDIUM.
- [ ] Output is well-formed Markdown following the Output Format template (Summary, Detailed
  Findings, Positive Highlights, Recommendations).
- [ ] Every finding has an actionable fix with a concrete code example.
- [ ] Deferred design-level OOD concerns to `style-python` rather than duplicating them here.
