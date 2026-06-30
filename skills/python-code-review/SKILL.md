---
name: python-code-review
description: Reviews Python code against PEP 8 and the Google Python Style Guide. Covers style, imports, naming, docstrings, type hints, code quality, security, performance, and maintainability. Use when reviewing, auditing, or checking the quality of Python code.
---

# Python Code Review (PEP 8 + Google Style Guide)

Perform systematic, pragmatic code reviews of Python files against PEP 8 and the Google Python Style Guide. Lead with security and correctness, then code quality, then style. Verify before flagging.

## When to Use / When NOT to Use

Use when:

- Reviewing a Python file, diff, or PR for quality, security, performance, or style compliance.
- Auditing existing Python code against PEP 8 / PEP 257 / PEP 484 and the Google Python Style Guide.
- A user asks to check, audit, or improve Python code quality.
- Verifying docstrings, type hints, import order, or naming conventions in `.py` files.

Do NOT use when:

- The file is not Python (e.g. Ruby, Swift, JS/TS, Terraform). Dispatch to the matching review skill instead.
- The request is a design / architecture / object-oriented-design review. Defer to `templeton-python-style`, which owns the house OOD and Python writing style.
- The only findings are auto-formattable nits (line length, spacing, quote consistency) that `black`/`ruff format` already fixes on save. Note the formatter; do not enumerate each nit as a finding.
- The task is writing new Python from scratch (use `feature-development`) rather than reviewing existing code.

## Universal Core (injected)

The universal style core (TRUE code plus the 9 universal principles, defined in `hooks/style-core.md`) is injected separately into every session. Do not restate it; assume it. Design-level OOD concerns (single-purpose units, dependency injection, tell-don't-ask, composition over inheritance, rule-of-three abstraction) live in `templeton-python-style`, the companion writing-style skill. This skill adds the PEP 8 / Google Style review specifics on top of that shared foundation.

## Review Principles

### Review Philosophy

"Code is read much more often than it is written." (Guido van Rossum)

A foolish consistency is the hobgoblin of little minds. Consistency within a project matters more than rigid adherence to rules. When in doubt, prioritize in this order:

1. Consistency within one function/module (most important)
2. Consistency within the project
3. Consistency with PEP 8 / Google Style Guide

Know when to be inconsistent:

- When applying the guideline makes code less readable.
- To match surrounding code style (but consider refactoring).
- When code predates the guideline.
- For backwards compatibility.

### Style & Formatting (PEP 8)

#### Line Length

- Maximum 80 characters (Google).
- Docstrings/comments: 72 characters max.
- Use implicit line continuation (parentheses/brackets) over backslashes.

#### Indentation

- Always 4 spaces per level, never tabs.
- Continuation lines: align vertically or use 4-space hanging indent.
- Closing brackets: align under first non-whitespace or under opening bracket.

#### Blank Lines

- 2 blank lines between top-level functions/classes.
- 1 blank line between methods.
- Sparingly within functions for logical sections.
- No blank line after the `def` line.

#### Whitespace Rules

- No whitespace inside parentheses/brackets/braces: `spam(ham[1], {eggs: 2})`.
- No whitespace before comma/semicolon/colon (except in slices).
- No whitespace before function call parentheses: `spam(1)` not `spam (1)`.
- No whitespace before indexing brackets: `dct['key']` not `dct ['key']`.
- Single space around binary operators: `i = i + 1`.
- No spaces around `=` in keyword args: `complex(real, imag=0.0)`.
- BUT use spaces when combining annotation + default: `def munge(input: AnyStr = None)`.
- Don't align operators vertically across lines (maintenance burden).

#### String Quotes

- Be consistent: pick `'` or `"` and stick with it in a file.
- Use the other quote to avoid backslashes: `"He said 'hello'"`.
- Always use `"""` for docstrings (never `'''`).

#### Trailing Commas

- Recommended for multi-line structures when the closing bracket is on a new line.
- Mandatory for single-element tuples: `FILES = ('setup.cfg',)`.
- Not on the same line as the closing bracket (except singleton tuples).

### Imports (PEP 8 + Google)

Import order, with a blank line between groups:

1. `from __future__` imports
2. Standard library imports
3. Third-party imports
4. Local application/library imports

#### Import Style

- Separate lines: `import os` and `import sys` (not `import os, sys`).
- Exception: OK to import multiple items from one module: `from subprocess import Popen, PIPE`.
- Exception: typing imports: `from typing import Any, NewType`.
- Use absolute imports (recommended): `import mypkg.sibling`.
- Relative imports acceptable for complex packages: `from . import sibling`.
- Never use wildcard imports: `from module import *`.
- Import full package paths (Google): `from doctor.who import jodie` not `import jodie`.

#### Import Format

- `import x` for packages and modules.
- `from x import y` where x is the package prefix, y is the module name.
- `from x import y as z` if y conflicts or is inconveniently long.
- `import y as z` only for standard abbreviations: `import numpy as np`.

#### Module Dunders

- After the module docstring, before imports (except `__future__`).
- Order: `__all__`, `__version__`, `__author__`, etc.

### Naming Conventions (PEP 8 + Google)

| Type | Convention | Examples |
|------|------------|----------|
| **Modules** | `lower_with_under.py` | `my_module.py` |
| **Packages** | `lower_with_under` | `my_package` |
| **Classes** | `CapWords` | `MyClass`, `HTTPServerError` |
| **Exceptions** | `CapWords` + `Error` suffix | `ValueError`, `ConnectionError` |
| **Functions** | `lower_with_under()` | `my_function()` |
| **Methods** | `lower_with_under()` | `my_method()` |
| **Constants** | `CAPS_WITH_UNDER` | `MAX_OVERFLOW`, `TOTAL` |
| **Global/Class Variables** | `lower_with_under` | `global_var` |
| **Instance Variables** | `lower_with_under` | `instance_var` |
| **Parameters** | `lower_with_under` | `function_param` |
| **Local Variables** | `lower_with_under` | `local_var` |
| **Type Variables** | `_T`, `_P` (leading underscore) | `_T = TypeVar("_T")` |

#### Special Prefixes/Suffixes

- `_single_leading`: weak "internal use" indicator (not imported by `from M import *`).
- `single_trailing_`: avoid keyword conflicts (`class_`).
- `__double_leading`: name mangling in classes (discouraged by Google, impacts testability).
- `__double_leading_and_trailing__`: magic methods (never invent these).

#### Names to Avoid

- Never use `l` (lowercase L), `O` (uppercase o), `I` (uppercase i) as single-char names.
- No dashes in any package/module name.
- Avoid abbreviations unless well-known.
- No offensive terms.
- No needless type info: `id_to_name_dict` becomes `id_to_name`.

#### Descriptive Names

- Names should be descriptive and clear.
- Descriptiveness proportional to scope (wider scope = more descriptive).
- Single-char names OK for: counters (`i`, `j`, `k`), exceptions (`e`), file handles (`f`), type vars (`_T`, `_P`).
- Avoid vague names: `thing`, `stuff`, `data` (without context).

### Documentation (PEP 257 + Google)

Module docstrings are required:

```python
"""One-line summary ending with period.

Longer description of the module or program. May include usage
examples, exported classes/functions, etc.

Typical usage example:
  foo = ClassFoo()
  bar = foo.function_bar()
"""
```

Function/method docstrings are required for complex/public functions:

```python
def fetch_data(
    table: str,
    keys: Sequence[str],
    require_all: bool = False,
) -> Mapping[str, tuple[str, ...]]:
    """Fetches rows from database.

    Retrieves rows pertaining to given keys. Longer description
    of what the function does and any important details.

    Args:
        table: Name of the database table.
        keys: List of row keys to fetch. Strings will be UTF-8 encoded.
        require_all: If True, only return rows with all keys present.

    Returns:
        Dict mapping keys to row data. Each row is a tuple of strings.
        Returns empty dict if no rows found.

    Raises:
        IOError: Error accessing the database.
        ValueError: Invalid table name provided.
    """
```

Docstring sections (Google style):

- **Summary line**: one physical line (<=80 chars), ends with a period.
- **Blank line** after the summary (if more content follows).
- **Args**: describe each parameter (with type if not annotated).
- **Returns**: describe the return value (omit for None; generators use "Yields").
- **Raises**: document exceptions that callers should handle.
- **Yields**: for generators, document yielded values.

#### Class Docstrings

```python
class SampleClass:
    """Summary of class here.

    Longer class information describing what the class represents
    (not that it "is a class").

    Attributes:
        likes_spam: A boolean indicating spam preference.
        eggs: An integer count of eggs we have.
    """

    def __init__(self, likes_spam: bool = False):
        """Initializes the instance.

        Args:
            likes_spam: Defines instance preference.
        """
        self.likes_spam = likes_spam
        self.eggs = 0
```

#### Comments

- Block comments: full sentences, capitalized, period at the end.
- Inline comments: 2+ spaces from code, used sparingly.
- Tricky code: comment before the operation.
- Non-obvious code: comment at the end of the line.
- TODO format: `# TODO: bug-reference - Description` or `# TODO(username): Description`.
- Keep comments up-to-date with code changes.
- Comments in English unless 120% sure the code is never read by non-speakers.

#### Override Methods

- Use the `@override` decorator (from `typing_extensions`) when overriding.
- No docstring needed if behavior is unchanged.
- Add a docstring if behavior differs or side effects are added.

### Type Hints (PEP 484 + Google)

#### Basic Rules

- Strongly encouraged for function signatures.
- Use for complex functions, public APIs, and when types aren't obvious.
- Don't annotate `self` or `cls` (except when needed for proper type info, use `Self`).
- Don't annotate `__init__` return (always `None`).

#### Type Hint Style

```python
def my_method(
    self,
    first_var: int,
    second_var: Foo,
    third_var: Bar | None,
) -> int:
    ...
```

#### Modern Syntax (Python 3.10+)

- Use `|` for unions: `str | None` (not `Optional[str]` or `Union[str, None]`).
- Use built-in types: `list[int]`, `dict[str, int]` (not `List[int]`, `Dict[str, int]`).
- Use `collections.abc` for parameters: `Sequence`, `Mapping` (not concrete types).

#### Specific Guidelines

- Use explicit `X | None`, not implicit (`a: str = None` is wrong).
- Specify generic parameters: `list[int]` not bare `list`.
- Use `Any` when the best type is unknown (but prefer `TypeVar` when possible).
- Type aliases: `CapWords` naming, use the `TypeAlias` annotation.
- Forward references: use `from __future__ import annotations` or string quotes.
- Conditional imports: use `if TYPE_CHECKING:` for type-only imports.

#### Type Variable Naming

```python
_T = TypeVar("_T")  # Good: leading underscore, descriptive
_P = ParamSpec("_P")  # Good: leading underscore
AddableType = TypeVar("AddableType", int, float, str)  # Good: descriptive
```

### Code Quality & Best Practices

#### Abstraction and Duplication

- "Duplication is far cheaper than the wrong abstraction" (Sandi Metz).
- Wait for the **third** occurrence before extracting an abstraction.
- Two instances of similar code may be coincidental; three reveal a true pattern.
- When reviewing, consider whether the abstraction would add more complexity than the duplication.
- Premature abstraction creates rigid, hard-to-change code.
- Don't flag duplication as a problem unless there are 3+ instances or a clear benefit to abstracting.

#### Implicit False (PEP 8)

```python
# Good
if not seq:
if foo is None:
if not x:

# Bad
if len(seq) == 0:
if foo == None:
if x == False:
```

#### Comparisons

- Singletons: use `is`/`is not`: `if x is None:`.
- Use `is not` rather than `not ... is`.
- Don't compare booleans to True/False: `if greeting:` not `if greeting == True:`.
- Type checking: use `isinstance(obj, int)` not `type(obj) is int`.
- String prefixes/suffixes: use `.startswith()`/`.endswith()` not slicing.

#### Sequences

- Use the empty-sequence truth value: `if seq:` not `if len(seq):`.
- Works for strings, lists, tuples.

#### Exception Handling

- Never use bare `except:` (catches SystemExit/KeyboardInterrupt).
- Use specific exceptions: `except ValueError:` not `except Exception:`.
- Minimize try block scope (avoid masking bugs).
- Use `finally` for cleanup or prefer context managers.
- Exception chaining: `raise X from Y` or `raise X from None`.
- Derive from `Exception` not `BaseException`.
- Exception names end in `Error` (if they are errors).

#### String Formatting

```python
# Good - Modern (preferred)
x = f'name: {name}; score: {n}'

# Good - Classic
x = 'name: %s; score: %d' % (name, n)
x = 'name: {}; score: {}'.format(name, n)

# Bad - Don't concatenate in loops
employee_table = '<table>'
for last, first in employees:
    employee_table += f'<tr><td>{last}, {first}</td></tr>'  # BAD!

# Good - Use list + join
items = ['<table>']
for last, first in employees:
    items.append(f'<tr><td>{last}, {first}</td></tr>')
employee_table = ''.join(items)
```

#### Logging

```python
# Good - Use %-style (not f-strings!)
logger.info('TensorFlow version: %s', tf.__version__)

# Bad - Don't use f-strings (prevents lazy evaluation)
logger.info(f'TensorFlow version: {tf.__version__}')
```

#### Resource Management

```python
# Good - Always use context managers
with open('file.txt') as f:
    data = f.read()

# Good - For non-context objects
import contextlib
with contextlib.closing(urllib.urlopen("http://...")) as page:
    for line in page:
        print(line)

# Bad - Don't rely on __del__ or manual close
f = open('file.txt')
data = f.read()
f.close()  # May not run if exception occurs!
```

#### Function Defaults

```python
# Good - No mutable defaults
def foo(a, b=None):
    if b is None:
        b = []

# Good - Immutable default
def foo(a, b: Sequence = ()):
    ...

# Bad - Mutable default (shared across calls!)
def foo(a, b=[]):
    ...
```

#### Comprehensions

```python
# Good
result = [mapping_expr for value in iterable if filter_expr]

# Bad - Multiple for clauses
result = [(x, y) for x in range(10) for y in range(5) if x * y > 10]

# If complex, use a regular loop
result = []
for x in range(10):
    for y in range(5):
        if x * y > 10:
            result.append((x, y))
```

#### Lambdas & Operators

```python
# OK for simple cases
sorted_list = sorted(items, key=lambda x: x.name)

# Better - Use the operator module
from operator import attrgetter
sorted_list = sorted(items, key=attrgetter('name'))

# Bad - Multi-line lambda
complicated = lambda x: x.filter(something).map(
    another_thing).reduce(final_thing)

# Good - Use def
def complicated(x):
    return x.filter(something).map(another_thing).reduce(final_thing)
```

#### Statements

```python
# Good
if foo == 'blah':
    do_blah_thing()
do_one()
do_two()

# Bad - Compound statements
if foo == 'blah': do_blah_thing()
do_one(); do_two(); do_three()
```

#### Return Statements

- Be consistent: all return expressions or all return None.
- Explicit is better: use `return None` not a bare `return` if other returns have values.

#### Properties

- Use the `@property` decorator (not manual descriptors).
- Only for trivial computations (cheap, straightforward).
- Don't use for expensive operations or complex logic.
- Don't use just to wrap simple attribute access (make it public).

#### Decorators

- Use judiciously when there is a clear advantage.
- Never use `@staticmethod` (use a module-level function, per Google).
- Use `@classmethod` sparingly (named constructors, class-specific state).

#### Global State

- Avoid mutable global state.
- Module-level constants OK: `MAX_TIMEOUT = 30`.
- Name private globals with a leading underscore: `_internal_cache`.

#### Power Features (Avoid)

- No custom metaclasses.
- No bytecode manipulation.
- No `__del__` for cleanup.
- No reflection hacks (some `getattr` use is OK).
- No import hacks.
- The standard library can use these (e.g. `abc.ABCMeta`, `dataclasses`, `enum`).

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

### Performance

#### String Concatenation

- Never use `+` or `+=` in loops (quadratic time).
- Use `''.join(items)` or `io.StringIO`.

#### Generators

- Use generators for large sequences (memory efficient).
- Use comprehensions over `map()`/`filter()` with a lambda.

#### Default Iterators

```python
# Good
for key in adict:
for line in afile:
for k, v in adict.items():

# Bad
for key in adict.keys():
for line in afile.readlines():
```

### Maintainability

#### Function Length

- Prefer < 40 lines (Google guideline, not a hard limit).
- Break up long functions unless it harms structure.
- If > 40 lines, consider whether it can be split.

#### Main Guard

```python
# Good
def main():
    ...

if __name__ == '__main__':
    main()

# Or with absl
from absl import app

def main(argv):
    ...

if __name__ == '__main__':
    app.run(main)
```

#### Assertions

- Don't use `assert` for critical logic (can be disabled with `-O`).
- OK for validating test expectations.
- Use `if` + `raise` for preconditions.

## Anti-Patterns

The highest-signal Python review smells. For each: the bad code, why it is wrong, and the corrected form.

### Mutable Default Argument

```python
# Bad - the default list is created once and shared across all calls
def foo(a, b=[]):
    b.append(a)
    return b
```

Why: default arguments are evaluated once at definition time. Mutating `b` leaks state between calls, producing surprising accumulation bugs.

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

Why: a bare `except` catches `BaseException`, masking real bugs and making the program impossible to interrupt or exit cleanly.

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

Why: strings are immutable, so `+=` copies the whole accumulator each pass, giving quadratic time on large inputs.

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

Why: f-strings are evaluated eagerly, defeating the logging module's lazy formatting and wasting work for suppressed levels.

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

Why: `None` is a singleton; `==` invokes `__eq__` and can be overridden or give the wrong answer. Identity is the correct check.

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

Why: two instances of similar code may be coincidental. Abstracting early couples unrelated code to a rigid interface that grows parameters as the cases diverge.

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

Rationale: at `DEBUG` the f-string version always builds the message string and calls `len(...)`, even in production where `DEBUG` is usually disabled. The `%`-style call passes the arguments to the logging machinery, which only formats them if the record is actually emitted. On a hot path this removes wasted work and keeps the call cheap. Severity here is LOW to MEDIUM (a non-standard but working pattern), not a correctness bug.

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

Rationale: the before version concatenates caller-controlled input directly into the SQL string. A `user_id` of `0 OR 1=1` (or worse, a `DROP`/`UNION` payload) executes as SQL. The after version sends the query and the value separately so the driver escapes the parameter, closing the injection vector. This is a CRITICAL finding regardless of whether current tests pass, because it is a security vulnerability, not a style choice.

## Review Workflow

1. **Read the entire file first.** Understand its purpose, structure, dependencies, and surrounding conventions before judging any line.
2. **Verify the context.** Confirm the Python version (e.g. 3.10+ for `X | None` syntax), project conventions, and whether tests pass. Do not flag modern idioms as errors.
3. **Review in priority order:**
   - Security and correctness first (injection, unsafe functions, hardcoded secrets, mutable defaults, bare excepts, masked exceptions).
   - Then code quality (error handling, resource management, abstraction, comprehensions, return consistency).
   - Then maintainability (function length, main guard, assertions).
   - Then style last (line length, whitespace, quotes, import order, naming).
4. **Confirm each issue actually exists** before flagging it. If tests pass and the code works, a non-standard pattern is at most MEDIUM.
5. **Produce the report** in the Output Format below, grouped by category and severity-ranked.

Apply this guidance throughout:

- **Pragmatic approach.** Focus on the changes being made, not rewriting the entire codebase. Suggest incremental improvements. Consider team capacity and priorities. Perfect is the enemy of good.
- **Context matters.** Consider project conventions. Match surrounding code style when editing. Balance improvement with backwards compatibility. Know when rules have valid exceptions.
- **Be constructive.** Explain *why* something matters, provide specific actionable recommendations, include code examples for fixes, and acknowledge good practices.

Special cases:

- **Legacy code.** Focus on new/modified code. Don't require a full refactor to meet standards. Suggest incremental modernization.
- **Mathematical/scientific code.** Short variable names OK if they match notation (`i`, `j`, `x`, `y`). Reference the paper/algorithm in comments. Use `# pylint: disable=invalid-name` if needed.
- **Test files.** PEP 8-compliant names (`test_<method>_<state>`) or legacy style (`testMethodUnderTest_state`). Less strict docstring requirements.
- **Backwards compatibility.** Don't break compatibility just to comply with PEP 8. Consider a deprecation path for API changes.

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

- **pylint**: comprehensive linter ([Google's pylintrc](https://google.github.io/styleguide/pylintrc)).
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

The standardized scale used across the workbench's review skills:

- **CRITICAL**: security vulnerability, data loss, or correctness bug (e.g. SQL injection, `eval()` on untrusted input, mutable-default state corruption, masked exceptions hiding failures).
- **HIGH**: significant maintainability problem, missing error handling, or a performance blocker (e.g. unbounded string concatenation on a hot path, bare `except` swallowing errors in production).
- **MEDIUM**: non-standard pattern that still works, unnecessary duplication (3+ instances), or missing tests.
- **LOW**: style and nits (line length, whitespace, quote consistency, import order) that a formatter handles.

**If tests pass and the code works, the maximum severity is MEDIUM (a non-standard pattern), not HIGH or CRITICAL.**

The one exception is a genuine security vulnerability or latent correctness bug that the existing tests simply do not exercise; those remain CRITICAL even when the suite is green.

## Quality Checklist

Before completing the review, verify:

- [ ] Read the entire file (not just the diff) for purpose, structure, and surrounding conventions.
- [ ] Verified each claim (Python version, framework patterns, whether tests pass) before flagging it.
- [ ] Reviewed security and correctness first, then quality, then maintainability, then style.
- [ ] Applied the severity scale, including the rule that passing tests cap non-correctness/non-security issues at MEDIUM.
- [ ] Output is well-formed Markdown following the Output Format template (Summary, Detailed Findings, Positive Highlights, Recommendations, References, Enforcement Tools).
- [ ] Every finding has an actionable fix with a concrete code example.
- [ ] Deferred design-level OOD concerns to `templeton-python-style` rather than duplicating them here.
