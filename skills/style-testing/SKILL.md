---
name: style-testing
description: Use when writing, reviewing, or restructuring tests in any language or framework (pytest, Vitest, Jest, XCTest, Swift Testing, Minitest, JUnit, Go testing) - one behavior per test, hoisted declarative setup, deterministic clocks and identification, scenario-named groups, and what not to test
---

# House Testing Style

The universal, framework-independent core for how tests are structured. Every rule below holds
whether the suite runs in Python, TypeScript, Swift, Ruby, Go, or anything else. Framework-specific
mechanics live in the matching delta skill; the idiom map in the appendix shows how each principle
is spelled in the common frameworks.

This is the *testing* core. It is a sibling of `hooks/style-core.md`, which is the *production
code* core (TRUE code plus nine design principles) and is injected separately each session. Apply
both; neither restates the other.

## When to Use / When NOT to Use

Use when:

- Writing new tests in any language.
- Reviewing or restructuring an existing suite.
- Diagnosing a flaky, slow, or uninformative test.
- Deciding what is worth testing and what is not.

Do NOT use when:

- You are told to match an existing suite's conventions verbatim. Honor the local pattern.
- The "test" is a benchmark, a fuzz harness, or a property-based generator. Some principles below
  (notably 4 and 11) are deliberately inverted in those; see Escape Hatches.
- You need framework mechanics rather than structure. Load the matching delta skill.

## Notation

Examples use a neutral pseudocode so no rule reads as belonging to one framework. It is not a real
test framework:

```text
group "<scenario>"        a scenario grouping
  given  name = <expr>    declarative setup, evaluated lazily on first use
  given! name = <expr>    declarative setup, forced before the action runs
  action     = <expr>     the single thing under test, named once
  test "<behavior>":      one case, asserting one behavior
    assert <one thing>
```

## Principles

1. **Test at the outermost seam that still runs fast.** Exercise the real stack (routing,
   serialization, middleware, persistence) rather than reaching past it to invoke an internal
   handler directly. A test that skips the seam passes while the feature is broken.

2. **Name the action under test once, and reuse it.** The thing being exercised belongs in one
   named place, not retyped in every case. When the call changes, it changes once.

   ```text
   # BAD - the action is retyped in every case
   test "returns success":  assert submit(form, input).ok
   test "creates a record": assert count(Record) increased by 1 after submit(form, input)

   # GOOD - named once
   action = submit(form, input)
   test "returns success":  assert action.ok
   test "creates a record": assert count(Record) increased by 1 after action
   ```

3. **Setup is declarative and lives outside the test body.** Arrange is hoisted; the body is Act
   and Assert only. Procedural construction inside a case hides what distinguishes one scenario
   from another and makes the case grow without bound.

   ```text
   # BAD - construction inside the case
   test "rejects an expired token":
     user  = create User(name: "x")
     token = create Token(user: user, expires: yesterday)
     assert authorize(token).denied

   # GOOD - setup hoisted, body is one act and one assert
   given user  = User(name: "x")
   given token = Token(user: user, expires: yesterday)
   action      = authorize(token)
   test "rejects an expired token": assert action.denied
   ```

4. **One behavior per test.** The case name alone should tell you what broke, without opening the
   body. Unrelated assertions bundled into one case turn a failure into an investigation.

   ```text
   # BAD - one case, four unrelated failures possible
   test "works":
     assert count(Item) increased by 1
     assert response.status == created
     assert response.body.title == "Test"

   # GOOD - each failure names itself
   test "creates the item":       assert count(Item) increased by 1
   test "returns created status": assert response.status == created
   test "echoes the title":       assert response.body.title == "Test"
   ```

5. **Group by scenario, named "when.../with.../for...".** One scenario per group, stated as a
   condition rather than an outcome. Vague group names ("it works", "bad data") describe nothing
   and cannot be scanned.

   ```text
   # BAD
   group "it works"
   group "bad data"

   # GOOD
   group "when the user is unauthorized"
   group "with a missing email field"
   group "for administrators"
   ```

6. **Use the lightest fixture that still proves the behavior.** Build in memory when only shape or
   validation matters; persist only when the behavior genuinely depends on storage, querying, or
   relationships. Needless I/O slows the suite and hides what the test actually relies on.

7. **Prefer lazy setup; force it eagerly only when ordering matters.** Lazy setup is not
   constructed in cases that never reference it. Reach for eager setup when the state must exist
   *before* the action runs, such as a record the action is meant to find or collide with.

8. **Identify what you assert on deterministically, by unique key.** Never "the last one", "the
   first one", or a positional index. Those are undefined the moment another row exists or
   ordering changes, and the assertion silently checks the wrong thing.

   ```text
   # BAD - which one is last?
   test "creates the invitation": assert last(Invitation).email == "new@example.com"

   # GOOD - addressed by a key that identifies exactly one
   test "creates the invitation": assert find(Invitation, email: "new@example.com") exists
   ```

9. **Define shared setup at the scope every case that uses it can see.** Anything referenced by
   the named action, or by a shared/parameterized case, must be visible to every group that
   invokes it. Setup reachable from only one branch produces failures that look conditional.

10. **Prerequisite state exists before the action, and resources are addressed through their real
    addressing mechanism.** Build the parent before the child. Reach the resource through the
    route helper, the public constructor, or the documented entry point, never a hand-assembled
    string or a reached-into private field.

11. **Tests are deterministic.** No dependence on the wall clock, on unseeded randomness, on
    ambient locale or timezone, on the network, or on the order the suite happens to run in.
    Inject the clock and the seed so the value is chosen by the test, not observed by it.

    ```text
    # BAD - passes today, fails on the first of the month, fails abroad
    test "expires in 30 days":
      assert subscription.expires_at == today() + 30 days

    # GOOD - the clock is an input
    given clock = FixedClock("2026-01-15T00:00:00Z")
    given subscription = Subscription(started: clock.now, clock: clock)
    test "expires in 30 days":
      assert subscription.expires_at == "2026-02-14T00:00:00Z"
    ```

12. **Test names describe observable behavior, not implementation.** "returns 404 for a deleted
    post" survives a refactor; "calls the repository's find method" is a restatement of the code
    that breaks the moment the code changes without the behavior changing.

13. **Do not test framework internals, third-party libraries, generated code, or private methods.**
    Test your behavior through its public surface. A test that reaches into a private method locks
    the implementation in place and fails on every safe refactor, which is the opposite of what a
    test is for.

14. **Assert on one clear cause of failure.** Prefer the precise assertion over the broad one that
    could pass for the wrong reason. Asserting "the response is not empty" proves almost nothing;
    asserting the one field the behavior sets proves the behavior.

    ```text
    # BAD - passes for a hundred wrong reasons
    test "returns the user": assert response.body is not empty

    # GOOD - fails for exactly one reason
    test "returns the user": assert response.body.email == "known@example.com"
    ```

## Anti-Patterns

- **Constructing state inside the case body.** Setup state becomes implicit and re-derived per
  case, hiding what distinguishes scenarios. Fix: hoist into declarative setup (principle 3).
- **Repeating the action inline across cases.** The action drifts between near-identical cases.
  Fix: name it once (principle 2).
- **The catch-all case named "works" or "is correct".** A failure tells you nothing. Fix: split by
  behavior and let each name describe its own failure (principle 4).
- **Asserting on "last" or an index.** Silently checks the wrong record as soon as the suite grows.
  Fix: address by unique key (principle 8).
- **Persisting when constructing in memory would do.** Slow suites get run less, and the test no
  longer documents what it actually depends on. Fix: lightest sufficient fixture (principle 6).
- **Reading the real clock or unseeded randomness.** Produces a suite that fails on a date
  boundary, in another timezone, or one run in a hundred. Fix: inject both (principle 11).
- **Order-coupled cases.** One case leaves state another depends on, so the suite passes in
  sequence and fails when parallelized or filtered. Fix: each case establishes its own setup.
- **Mirroring the implementation's structure in the test's structure.** One test file per class,
  one case per method, produces tests that must be rewritten by any refactor. Fix: organize by
  behavior and scenario (principles 5 and 12).
- **Over-mocking until the test asserts only that the mocks were called.** Proves the test's model
  of the code, not the code. Fix: move outward to a real seam (principle 1).

## Escape Hatches

Break a rule when the rule fights the goal, and say why in a comment:

- **Genuinely order-dependent flows** (a migration sequence, a multi-step protocol handshake) may
  need ordered cases. Principle 11's order-independence yields; keep determinism otherwise.
- **Property-based and fuzz tests** deliberately use randomness. Principle 11 becomes "pin and log
  the seed so any failure is reproducible", not "no randomness".
- **Snapshot and approval tests** deliberately assert broadly. Principle 14 yields, provided the
  snapshot is reviewed rather than blindly regenerated on failure.
- **Characterization tests around legacy code** deliberately assert current behavior including its
  bugs. Principle 12 yields; name them so their purpose is unmistakable.
- **Setup that cannot be hoisted** (state that must vary per case in a way lazy setup would break)
  keeps its construction inline. Correctness beats principle 3.

## Apply Workflow

1. **Name the behavior.** What observable outcome is under test? If you cannot state it without
   naming an internal method, you are testing the wrong thing (principle 12).
2. **Pick the seam.** Choose the outermost boundary that still runs fast (principle 1).
3. **Enumerate scenarios.** Valid, invalid, unauthorized, empty, boundary, conflicting. Each
   becomes one group (principle 5).
4. **Decide what is shared and what varies.** Shared setup hoists to the enclosing scope; the
   varying part stays in its group (principles 3 and 9).
5. **Name the action once** (principle 2).
6. **Choose the lightest fixtures**, and inject the clock and seed if either is involved
   (principles 6, 7, 11).
7. **Write one case per behavior**, each with a precise assertion and deterministic identification
   (principles 4, 8, 14).
8. **Delete what should not be tested**: framework internals, third-party code, private methods
   (principle 13).

## Quality Checklist

- [ ] Every case asserts one behavior, and its name says what broke.
- [ ] The action under test is named once, not retyped per case.
- [ ] All setup is declarative and outside the case body.
- [ ] Groups are named "when.../with.../for..." and describe one scenario each.
- [ ] The lightest sufficient fixture is used; I/O only where the behavior depends on it.
- [ ] Setup is lazy unless the state must exist before the action.
- [ ] Assertions identify their target by unique key, never by "last", "first", or index.
- [ ] Shared setup is visible to every case that references it.
- [ ] No dependence on wall clock, unseeded randomness, locale, timezone, network, or case order.
- [ ] Names describe observable behavior, not implementation.
- [ ] No tests of framework internals, third-party libraries, or private methods.
- [ ] Each assertion has one clear cause of failure.
- [ ] Any deliberate rule break carries a comment saying why.

---

<!-- leak-check:appendix-start -->

## Appendix: Framework Idiom Map

Reference only. The principles above are the skill; this table is how they are spelled. Nothing
here is a rule.

The two `leak-check` comments around this section are load-bearing: they are what
`scripts/check_framework_leak.py` uses to decide which region may name a framework. Do not remove,
duplicate, or reorder them, and keep every framework name inside them.

| Principle | Python (pytest) | TypeScript (Vitest / Jest) | Swift (XCTest / Swift Testing) | Ruby (Minitest) |
|---|---|---|---|---|
| 2, name the action once | a fixture returning the call, or a local helper | a helper function in the suite scope | a `private func` on the test case | a private method on the test class |
| 3, declarative setup | `@fixture` functions | factory helpers called in the suite scope | `setUp()`, or `init` in Swift Testing | `setup do` or fixture files |
| 5, scenario groups | nested `class Test...` or `@mark.parametrize` | nested `suite` blocks | nested `XCTestCase` types, or `@Suite` | nested test classes |
| 6, lightest fixture | plain object over ORM `.create()` | plain object over a seeded database record | a value-type instance over a persisted model | `.new` over `.create` |
| 7, lazy vs eager setup | function-scoped fixture, requested only where used | lazily constructed inside the helper | `lazy var` on the test case | memoized private method |
| 8, deterministic identity | `Model.query.filter_by(key=...)`, not `[-1]` | `.find(x => x.key === ...)`, not `.at(-1)` | `first(where:)` on a unique key | `find_by(key:)`, not `.last` |
| 11, injected clock | pass a `Clock` protocol, or `freezegun` | inject a `now()` function, or fake timers | inject a `Date` provider closure | pass a clock object, or `travel_to` |
| 11, seeded randomness | `random.Random(seed)` passed in | a seeded generator passed in | a `RandomNumberGenerator` passed in | `Random.new(seed)` passed in |
| 13, public surface only | test the module's exports | test the module's exports | test `internal`/`public`, never `@testable` private access | test public methods only |

<!-- leak-check:appendix-end -->
