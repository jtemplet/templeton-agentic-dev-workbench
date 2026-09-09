---
name: style-python
description: Writes and reviews Python in the house style. Use when writing, editing, or reviewing any `.py` file, including a design or object-oriented-design review of Python.
---

# Templeton Python Style

This skill writes and reviews Python domain and application logic in the house style. It carries only the Python-specific deltas on top of the universal TRUE-code core that is injected separately into every session; it does not restate that core. Use it whenever Python style decisions are in play.

It carries only what a linter cannot decide. Rules ruff enforces on every project live in the boreas baseline (`linting/python/ruff.toml`), not here: lazy logging, modern type-hint syntax, mutable default arguments, and bare or blind `except`. Prose that repeats an enforced rule is read by a human who was going to be told by the linter anyway, and it goes stale the moment the rule changes.

## When to Use / When NOT to Use

Use this skill when:

- Writing new Python modules, functions, or classes that should match the house style.
- Reviewing Python code for style, structure, type hints, and object-oriented design.
- Refactoring or simplifying existing Python and you need the Python-specific deltas.

Do NOT use this skill when:

- The file is not Python (use `style-frontend`, `style-swift`, or the Rails skills instead).
- The code is a throwaway script, one-off REPL snippet, or scratch experiment where style is irrelevant.
- You only need the universal principles; those are already injected and apply on their own.

## Universal Core (injected)

The universal TRUE-code principles (Transparent, Reasonable, Usable, Exemplary) are injected via `hooks/style-core.md` and are assumed here; this skill does not repeat them. They are: wait for duplication before abstracting; small single-purpose units; simple interfaces (<=4 params, typed param objects); inject dependencies on interfaces; tell-don't-ask; compose over inherit; fail fast with explicit errors; read top-down (step-down rule); let names document. Default posture: correctness > speed, simplicity > cleverness, explicit > magic, start simple.

## Python Principles

These are the Python-specific deltas. Each pairs the rule with a concrete BAD -> why -> GOOD fix.

1. Prefer modules before classes. Introduce a class only when state, polymorphism, or lifecycle management genuinely requires it; otherwise group plain functions in a module.

   ```python
   # BAD: a stateless "service object" wrapping one method
   class PriceFormatter:
       def format(self, amount: decimal.Decimal) -> str:
           return f"${amount:,.2f}"

   # why: there is no state, no polymorphism, no lifecycle - the class is ceremony.

   # GOOD: a plain module-level function
   def format_price(amount: decimal.Decimal) -> str:
       return f"${amount:,.2f}"
   ```

2. Use dataclasses, TypedDict, or NamedTuple for complex parameter groups. Bundle related data instead of passing long positional argument lists.

   ```python
   # BAD: 5 positional params, easy to transpose
   def create_user(name, email, age, country, is_admin):
       ...

   # why: order-dependent, untyped, and grows worse with each new field.

   # GOOD: a typed parameter object
   @dataclasses.dataclass(frozen=True)
   class NewUser:
       name: str
       email: str
       age: int
       country: str
       is_admin: bool = False

   def create_user(user: NewUser) -> User:
       ...
   ```

3. Use protocols and type hints to express contracts without coupling. Depend on what an object can do, not on a concrete class.

   ```python
   # BAD: coupled to a concrete implementation
   class ReportJob:
       def __init__(self) -> None:
           self._store = S3Store()  # hardcoded concrete dependency

   # why: cannot test or swap the store; the job knows too much.

   # GOOD: depend on a Protocol, inject the concrete
   class BlobStore(Protocol):
       def put(self, key: str, data: bytes) -> None: ...

   class ReportJob:
       def __init__(self, store: BlobStore) -> None:
           self._store = store
   ```

4. Prefer duck typing over isinstance checks. Care about what an object does, not what it is.

   ```python
   # BAD: branching on concrete type
   def render(value):
       if isinstance(value, list):
           return ", ".join(value)
       return str(value)

   # why: brittle - every new type needs another branch.

   # GOOD: rely on behavior the caller already guarantees
   def render(items: Iterable[str]) -> str:
       return ", ".join(items)
   ```

5. Use context managers for resources. Acquire and release files, locks, and connections with `with`, never by hand.

   ```python
   # BAD: manual open/close leaks on exceptions
   f = open(path)
   data = f.read()
   f.close()

   # why: an exception before close() leaks the file handle.

   # GOOD: context manager guarantees cleanup
   with open(path) as f:
       data = f.read()
   ```

## Anti-Patterns

The top Python smells to flag in review, each as bad -> why -> fix. Ruff catches the rest.

- Deep inheritance: 3+ level class trees -> fragile, hard to trace behavior -> compose or use a Protocol/mixin.
- Premature abstraction: a base class or helper with one caller -> wrong abstraction is costlier than duplication -> wait for the third occurrence.

## Worked Examples

### Tell, Don't Ask

Before:

```python
# user_service.py:42 - deep attribute chaining
if user.account.subscription.is_active():
    process_payment(user.account.subscription.amount)
```

After:

```python
if user.has_active_subscription():
    user.process_subscription_payment()
```

Why: the "before" couples the caller to the internal structure of `Account` and `Subscription`, so any change to those classes breaks it. The "after" moves behavior to where the data lives and sends a message to `User` instead of reaching through it.

### Step Down Rule

Before:

```python
class OrderProcessor:
    def process(self, order):
        # high level
        if not order.items:
            return OrderResult.empty()

        # low level - suddenly drops to details
        db = get_database()
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT...")

        # medium level again
        total = self._calculate_total(order)

        # more low-level
        import hashlib
        signature = hashlib.sha256(str(order).encode()).hexdigest()
```

After:

```python
class OrderProcessor:
    def __init__(self, repository: OrderRepository, calculator: PricingCalculator):
        self._repository = repository
        self._calculator = calculator

    # high-level: business logic only
    def process(self, order: Order) -> OrderResult:
        if self._order_is_empty(order):
            return OrderResult.empty()

        total = self._calculate_total(order)
        signature = self._sign_order(order)
        return self._save_and_return(order, total, signature)

    # next level: orchestration
    def _order_is_empty(self, order: Order) -> bool:
        return not order.items

    def _calculate_total(self, order: Order) -> decimal.Decimal:
        return self._calculator.compute(order)

    def _sign_order(self, order: Order) -> str:
        return self._create_signature(str(order))

    def _save_and_return(self, order: Order, total: decimal.Decimal, signature: str) -> OrderResult:
        return self._repository.save(order, total, signature)

    # low-level: implementation details at the bottom
    def _create_signature(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()
```

Why: the "after" reads top-to-bottom like a story. Business intent sits at the top, orchestration in the middle, implementation details at the bottom, and each method stays at one abstraction level. Dependencies are injected, so the processor is testable and swappable.

## Review / Apply Workflow

When writing Python:

1. Start with a module of plain functions; introduce a class only when state, polymorphism, or lifecycle demands it.
2. Bundle related parameters into a dataclass/TypedDict/NamedTuple once the group passes the simple-interface threshold.
3. Express contracts with Protocols and type hints; inject concrete dependencies through `__init__` or parameters.
4. Use context managers for every resource from the first draft.
5. Order methods by the step-down rule so the unit reads top-down.

When reviewing Python:

1. Scan for the top anti-patterns: deep inheritance and single-use abstractions.
2. Flag deep attribute chaining (`a.b.c.d`) and suggest moving behavior to where the data lives.
3. Check that contracts use Protocols rather than coupling to a concrete class.
4. Report each finding with a `file:line` reference, a before/after pair, and the principle it violates.
5. When refactoring, state what flexibility is gained and what complexity (if any) is introduced.

## Quality Checklist

- [ ] Class introduced only where state/polymorphism/lifecycle justifies it; otherwise a module of functions.
- [ ] Complex parameter groups use a dataclass, TypedDict, or NamedTuple.
- [ ] Contracts expressed via Protocols/type hints; dependencies injected, not hardcoded.
- [ ] Every resource is managed with a context manager.
- [ ] Methods ordered by the step-down rule; each stays at one abstraction level.
